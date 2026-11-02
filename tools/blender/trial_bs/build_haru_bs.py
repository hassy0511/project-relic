"""haru_bs を作り直す入口（段 1：骨なしのモデル）。

  .venv-blender/bin/python tools/blender/trial_bs/build_haru_bs.py [--no-tex] [--no-glb]

出力：build/trial_bs/haru_bs.blend、build/trial_bs/haru_bs_static.glb（骨なしの確認用）、
テクスチャ build/trial_bs/tex/haru_bs_T_*.png。
外部のスキル集 arjun988/blender-skills の手順に沿う（docs/art_orders/W1_ハル_blender-skills試作.md）：
集まりは COL_、メッシュは SM_、材質は MAT_（ゲームが探す名前は約束の名前）。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'build', 'trial_bs')

import bpy
from mathutils import Vector, Matrix

import proportions as P
from meshkit import Part, to_object, PAINT_KEYS
import parts_body as B
import parts_cloth as C
import parts_hair as H
import parts_hard as K


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def paint_colors(ob):
    """面の色（paint）を色の属性 paint_col にも書く（下塗りの確認と、テクスチャの元）"""
    me = ob.data
    ca = me.color_attributes.new('paint_col', 'BYTE_COLOR', 'CORNER')
    pa = me.attributes['paint']
    for poly in me.polygons:
        key = PAINT_KEYS[pa.data[poly.index].value]
        r, g, b = P.RGB[key]
        col = (r / 255.0, g / 255.0, b / 255.0, 1.0)
        for li in poly.loop_indices:
            ca.data[li].color_srgb = col


def material(name, color_attr=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Metallic'].default_value = 0.0
    if color_attr:
        ca = nt.nodes.new('ShaderNodeVertexColor')
        ca.layer_name = 'paint_col'
        nt.links.new(ca.outputs['Color'], bsdf.inputs['Base Color'])
    return m


def build(with_tex=True, with_glb=True):
    reset()
    top = coll('COL_HaruBS')
    c_ref = coll('COL_Reference', top)
    c_geo = coll('COL_Geo', top)
    c_hair = coll('COL_Hair_HaruBS', c_geo)
    c_frame = coll('COL_Frame', top)
    c_props = coll('COL_Props', top)
    coll('COL_Cameras', top)
    coll('COL_Lights', top)

    M = {
        'cloth': material('MAT_Cloth_HaruBS'),
        'face': material('MAT_face_HaruBS'),
        'frame': material('MAT_Ceramic_FrameBS'),
        'gun': material('spark_gun_HaruBS'),
        'blade': material('MAT_Emissive_BladeBS'),
    }
    objs = {}

    def mk(part, name, c, mat, smooth=True, angle=40.0, parent=None):
        ob = to_object(part, name, c, M[mat], smooth=smooth, angle=angle, parent=parent)
        paint_colors(ob)
        objs[name] = ob
        return ob

    # ---- 体・頭
    body = B.neck().extend(B.arm(1)).extend(B.arm(-1))
    lh_skin, lh_glove = B.open_hand(1)
    body.extend(lh_skin)
    gm = K_gun_matrix = B.gun_frame()
    fs, fg = B.fist_in_gun()
    body.extend(fs.transformed(gm))
    mk(body, 'SM_Char_HaruBS_Body', c_geo, 'cloth', angle=60)
    mk(lh_glove.extend(fg.transformed(gm)), 'SM_Cloth_HaruBS_Gloves', c_geo, 'cloth', angle=45)
    mk(B.head().extend(B.ears()), 'SM_Char_HaruBS_Head', c_geo, 'face', angle=70)

    # ---- 髪（地域ごとの塊）
    mk(H.cap(), 'SM_Hair_HaruBS_Cap', c_hair, 'cloth', angle=50)
    for bone, part in H.hair_regions().items():
        nm = 'SM_Hair_HaruBS_' + bone.replace('hair.', '').replace('.', '_').title().replace('_L', '_L').replace('_R', '_R')
        ob = mk(part, nm, c_hair, 'cloth', angle=55)
        ob['sway_bone'] = bone

    # ---- 服
    mk(C.shirt(), 'SM_Cloth_HaruBS_Shirt', c_geo, 'cloth', angle=50)
    jk = mk(C.jacket(), 'SM_Cloth_HaruBS_Jacket', c_geo, 'cloth', angle=40)
    sol = jk.modifiers.new('Solidify', 'SOLIDIFY')
    sol.thickness = 0.008
    sol.offset = 1.0
    mk(C.collar(), 'SM_Cloth_HaruBS_Collar', c_geo, 'cloth', angle=50)
    sl = Part()
    cuffs = Part()
    for side in (1, -1):
        a, b = C.sleeve(side)
        sl.extend(a)
        cuffs.extend(b)
    mk(sl.extend(cuffs), 'SM_Cloth_HaruBS_Sleeves', c_geo, 'cloth', angle=40)
    bt = mk(C.belt(), 'SM_Cloth_HaruBS_Belt', c_geo, 'cloth', angle=40)
    sol = bt.modifiers.new('Solidify', 'SOLIDIFY')
    sol.thickness = 0.008
    sol.offset = -1.0
    mk(C.buckle(), 'SM_Cloth_HaruBS_Buckle', c_geo, 'cloth', angle=30)
    for side, part in C.pouches():
        ob = mk(part, 'SM_Cloth_HaruBS_Pouch_' + ('L' if side > 0 else 'R'), c_geo, 'cloth', angle=30)
        ob['sway_bone'] = 'pouch.' + ('L' if side > 0 else 'R')
    mk(C.trouser_leg(1).extend(C.trouser_leg(-1)), 'SM_Cloth_HaruBS_Trousers', c_geo, 'cloth', smooth=True, angle=25)
    mk(C.legging(1).extend(C.legging(-1)), 'SM_Cloth_HaruBS_Leggings', c_geo, 'cloth', angle=40)
    mk(C.ankle_cuff(1).extend(C.ankle_cuff(-1)), 'SM_Cloth_HaruBS_AnkleCuffs', c_geo, 'cloth', angle=35)
    bd = Part()
    so = Part()
    for side in (1, -1):
        a, b = C.boot(side)
        bd.extend(a)
        so.extend(b)
    mk(bd, 'SM_Cloth_HaruBS_Boots', c_geo, 'cloth', angle=30)
    mk(so, 'SM_Cloth_HaruBS_Soles', c_geo, 'cloth', angle=30)
    mk(K.goggles(), 'SM_Acc_HaruBS_Goggles', c_geo, 'cloth', angle=30)
    mk(K.goggle_strap(), 'SM_Acc_HaruBS_GoggleStrap', c_geo, 'cloth', angle=60)

    # ---- 外装フレーム（ゲームが名前で探す群：Frame_core・Frame_arm・Frame_legs）
    groups = {}
    for g in ('Frame_core', 'Frame_arm', 'Frame_legs'):
        e = bpy.data.objects.new(g, None)
        e.empty_display_size = 0.05
        c_frame.objects.link(e)
        groups[g] = e
    mk(K.shoulder_straps(), 'SM_Frame_HaruBS_ShoulderStraps', c_frame, 'frame', angle=40, parent=groups['Frame_core'])
    mk(K.back_panel(), 'SM_Frame_HaruBS_BackPanel', c_frame, 'frame', angle=30, parent=groups['Frame_core'])
    mk(K.shoulder_plate(), 'SM_Frame_HaruBS_ShoulderPlate_R', c_frame, 'frame', angle=30, parent=groups['Frame_core'])
    gpart, (bstart, bdir, bside) = K.gauntlet()
    mk(gpart, 'SM_Frame_HaruBS_Gauntlet_L', c_frame, 'frame', angle=35, parent=groups['Frame_arm'])
    kp = K.knee_parts(1).extend(K.knee_parts(-1))
    mk(kp, 'SM_Frame_HaruBS_KneePads', c_frame, 'frame', angle=30, parent=groups['Frame_legs'])
    mk(K.shin_plates(1).extend(K.shin_plates(-1)), 'SM_Frame_HaruBS_ShinPlates', c_frame, 'frame', angle=30, parent=groups['Frame_legs'])
    mk(K.thigh_plate(), 'SM_Frame_HaruBS_ThighPlate_R', c_frame, 'frame', angle=30, parent=groups['Frame_legs'])

    # ---- 持ち物：スパーク（右手）と光刃（左の籠手）
    gun = mk(K.spark_gun(), 'SM_Weapon_HaruBS_SparkGun', c_props, 'gun', angle=30)
    gun.matrix_world = gm
    mz = bpy.data.objects.new('muzzle', None)
    mz.empty_display_size = 0.02
    c_props.objects.link(mz)
    mz.parent = gun
    mz.location = K.MUZZLE
    blade = mk(K.light_blade(bstart, bdir, bside), 'LightBlade', c_props, 'blade', angle=30)

    if with_tex:
        import textures
        textures.make_all(objs, M, OUT)

    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'haru_bs.blend'))
    report(objs)
    if with_glb:
        import export_glb
        export_glb.export_static(os.path.join(OUT, 'haru_bs_static.glb'))


def report(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    rows = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        t = len(me.loop_triangles)
        ev.to_mesh_clear()
        total += t
        rows.append((ob.name, t))
    for n, t in sorted(rows, key=lambda r: -r[1]):
        print(f'  {n:40s} {t:6d}')
    print('TOTAL TRIS', total, 'objects', len(rows), 'materials', len([m for m in bpy.data.materials if m.users]))


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    build(with_tex='--no-tex' not in argv, with_glb='--no-glb' not in argv)
