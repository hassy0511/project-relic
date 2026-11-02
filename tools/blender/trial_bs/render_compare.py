"""絵と同じカメラで haru_bs を描き、絵と並べる（reference-image-match の比べの輪）。

  .venv-blender/bin/python tools/blender/trial_bs/render_compare.py [views...] [--pass N] [--face]

スキル集は Blender MCP の get_viewport_screenshot を使うが、ここでは MCP も画面も無い。頭なしの Blender では
EEVEE・Workbench が動かない（EGL が無い）ので、Cycles で描く。陰は cel-shader-setup の「拡散 → 段の ColorRamp」を
発光の材質で作り直したもの（法線と光の向きの内積を 3 段に切る。光はカメラの左上の前）。
出力：build/trial_bs/cmp/<view>.png（絵｜モデル｜影の重なり）と IoU の表。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'build', 'trial_bs')
ART = os.path.join(ROOT, 'build', 'art')

import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler
from PIL import Image, ImageDraw, ImageFont

import proportions as P

FULL_SCALE = 2048 * P.PX
FULL_CZ = (P.FEET_PX - 1024) * P.PX

# 絵ごとのカメラ：向き（カメラの回転 Z、X）、全身なら中心、頭なら合わせる物体
VIEWS = {
    'front': dict(img='haru_3d_front.png', rz=0, rx=90, full=True, cx=0.0),
    'back': dict(img='haru_3d_back.png', rz=180, rx=90, full=True, cx=0.0),
    'side_right': dict(img='haru_3d_side_right.png', rz=-90, rx=90, full=True, cx=(1024 - P.SIDE_CX) * P.PX),
    'side_left': dict(img='haru_3d_side_left.png', rz=90, rx=90, full=True, cx=(1024 - (2048 - P.SIDE_CX)) * P.PX),
    'three_quarter': dict(img='haru_3d_three_quarter.png', rz=-30, rx=90, full=True, cx=None),
    'front_left45': dict(img='haru_3d_front_left45.png', rz=30, rx=90, full=True, cx=None),
    'head_side_right': dict(img='haru_head_side_right.png', rz=-90, rx=90, full=False),
    'head_back': dict(img='haru_head_back.png', rz=180, rx=90, full=False),
    'head_front_right45': dict(img='haru_head_front_right45.png', rz=-45, rx=90, full=False),
    'head_top': dict(img='haru_head_top.png', rz=0, rx=0, full=False),
    'face_front': dict(img='haru_face_front.png', rz=0, rx=90, full=False),
    'expr0': dict(img='expr_q0.png', rz=0, rx=90, full=False, expr=0),
    'expr1': dict(img='expr_q1.png', rz=0, rx=90, full=False, expr=1),
    'expr2': dict(img='expr_q2.png', rz=0, rx=90, full=False, expr=2),
    'expr3': dict(img='expr_q3.png', rz=0, rx=90, full=False, expr=3),
}
HEAD_SCALE = 0.481
HEAD_SCALE_Q = 0.473
HEAD_PARTS = ('SM_Char_HaruBS_Head', 'SM_Hair_', 'SM_Acc_HaruBS_Goggle')


def cam_basis(rz, rx):
    m = Euler((math.radians(rx), 0, math.radians(rz)), 'XYZ').to_matrix()
    right = m @ Vector((1, 0, 0))
    up = m @ Vector((0, 1, 0))
    back = m @ Vector((0, 0, 1))
    return m, right, up, back


def alpha_bbox(a):
    ys, xs = np.where(a > 128)
    return xs.min(), ys.min(), xs.max(), ys.max()


def head_verts():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name.startswith(HEAD_PARTS) and not ob.hide_render:
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            mw = ob.matrix_world
            pts += [mw @ v.co for v in me.vertices]
            ev.to_mesh_clear()
    return pts


def all_verts():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and not ob.hide_render:
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            mw = ob.matrix_world
            pts += [mw @ v.co for v in me.vertices]
            ev.to_mesh_clear()
    return pts


def setup_camera(view, art_alpha):
    cfg = VIEWS[view]
    m, right, up, back = cam_basis(cfg['rz'], cfg['rx'])
    sc = bpy.context.scene
    cam = bpy.data.objects.get('CAM_Ref')
    if cam is None:
        cam = bpy.data.objects.new('CAM_Ref', bpy.data.cameras.new('CAM_Ref'))
        sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    sc.camera = cam
    x0, y0, x1, y1 = alpha_bbox(art_alpha)
    W = art_alpha.shape[1]
    if cfg['full']:
        scale = FULL_SCALE
        pts = all_verts()
        if cfg['cx'] is None:
            # 横の位置は影の箱の中心で合わせる（全身の高さと大きさは絵の画素の寸法で決まっている）
            sx = [p.dot(right) for p in pts]
            mid = (min(sx) + max(sx)) / 2
            art_mid = ((x0 + x1) / 2 - W / 2) / W * scale
            cx = mid - art_mid
        else:
            cx = cfg['cx']
        center = right * cx + Vector((0, 0, FULL_CZ)) if cfg['rx'] == 90 else right * cx
        center = Vector((center.x, center.y, FULL_CZ))
    else:
        pts = head_verts()
        sx = [p.dot(right) for p in pts]
        sy = [p.dot(up) for p in pts]
        # 頭の絵はどれも同じ大きさで描かれている（髪の先 145 px、首の切れ目 1902 px）。大きさは全身の絵の頭の幅から決めた
        # 1 つの値（画像の幅 = 0.481 m。2×2 の表情の区画は 0.473 m）。位置は髪の上の端と、影の箱の横の中心で合わせる
        scale = HEAD_SCALE_Q if cfg.get('expr') is not None else HEAD_SCALE
        top_model = max(sy)
        art_top = (W / 2 - y0) / W * scale
        mid = (min(sx) + max(sx)) / 2
        art_mid = ((x0 + x1) / 2 - W / 2) / W * scale
        if cfg['rx'] == 0:
            midy = (min(sy) + max(sy)) / 2
            art_midy = (W / 2 - (y0 + y1) / 2) / W * scale
            center = right * (mid - art_mid) + up * (midy - art_midy)
        else:
            center = right * (mid - art_mid) + up * (top_model - art_top)
    cam.data.ortho_scale = scale
    cam.matrix_world = Matrix.Translation(center + back * 6.0) @ m.to_4x4()
    cam.data.clip_end = 20
    return cam, back


TOON_KEYS = {}


def toon_materials(light_dir, expr=0):
    """材質を発光のトゥーンに差し替える（描くときだけ。保存しない）"""
    for mat in bpy.data.materials:
        nt = mat.node_tree
        if nt is None or mat.name.startswith('TOON_'):
            continue
        tm = bpy.data.materials.get('TOON_' + mat.name) or bpy.data.materials.new('TOON_' + mat.name)
        tm.use_nodes = True
        t = tm.node_tree
        t.nodes.clear()
        out = t.nodes.new('ShaderNodeOutputMaterial')
        em = t.nodes.new('ShaderNodeEmission')
        # 色の元：画像があれば画像、なければ色の属性
        img = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.label != 'emit'), None)
        if img is not None:
            src = t.nodes.new('ShaderNodeTexImage')
            src.image = img.image
            src.interpolation = 'Closest' if 'face' not in mat.name else 'Linear'
            uvn = t.nodes.new('ShaderNodeUVMap')
            uvn.uv_map = 'UVMap'
            if 'face' in mat.name and expr:
                # ゲームの set_expression と同じ：区画をずらす（Blender の v は上向きなので下の段は -0.5）
                add = t.nodes.new('ShaderNodeVectorMath')
                add.operation = 'ADD'
                add.inputs[1].default_value = ((expr % 2) * 0.5, -(expr // 2) * 0.5, 0)
                t.links.new(uvn.outputs['UV'], add.inputs[0])
                t.links.new(add.outputs['Vector'], src.inputs['Vector'])
            else:
                t.links.new(uvn.outputs['UV'], src.inputs['Vector'])
            col = src.outputs['Color']
        else:
            src = t.nodes.new('ShaderNodeVertexColor')
            src.layer_name = 'paint_col'
            col = src.outputs['Color']
        geo = t.nodes.new('ShaderNodeNewGeometry')
        dot = t.nodes.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        dot.inputs[1].default_value = light_dir
        t.links.new(geo.outputs['Normal'], dot.inputs[0])
        ramp = t.nodes.new('ShaderNodeValToRGB')
        cr = ramp.color_ramp
        cr.interpolation = 'CONSTANT'
        cr.elements[0].position = 0.0
        cr.elements[0].color = (0.70, 0.70, 0.72, 1)
        cr.elements[1].position = 0.12
        cr.elements[1].color = (0.86, 0.86, 0.87, 1)
        e3 = cr.elements.new(0.45)
        e3.color = (1, 1, 1, 1)
        t.links.new(dot.outputs['Value'], ramp.inputs['Fac'])
        mul = t.nodes.new('ShaderNodeMix')
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        t.links.new(col, mul.inputs['A'])
        t.links.new(ramp.outputs['Color'], mul.inputs['B'])
        t.links.new(mul.outputs['Result'], em.inputs['Color'])
        t.links.new(em.outputs['Emission'], out.inputs['Surface'])
        TOON_KEYS[mat.name] = tm
        for n in list(t.nodes):
            pass
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            for slot in ob.material_slots:
                if slot.material and slot.material.name in TOON_KEYS:
                    slot.material = TOON_KEYS[slot.material.name]


def render(view, out_png, res=1024):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 6
    # 1 本のスレッドで描く（ほかの作業と CPU を分け合う。発光だけ・反射なしなので軽い）
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 1
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


def font(sz):
    for p in ('/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf',):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def compose(view, art_path, ren_path, out_path, res=1024):
    art = Image.open(art_path).convert('RGBA').resize((res, res), Image.LANCZOS)
    ren = Image.open(ren_path).convert('RGBA')
    bg = (200, 200, 200, 255)
    a = Image.new('RGBA', (res, res), bg)
    a.alpha_composite(art)
    b = Image.new('RGBA', (res, res), bg)
    b.alpha_composite(ren)
    aa = np.array(art)[..., 3] > 128
    rr = np.array(ren)[..., 3] > 128
    ov = np.full((res, res, 3), 235, np.uint8)
    ov[aa & rr] = (120, 120, 120)
    ov[aa & ~rr] = (230, 60, 50)     # 絵だけ（モデルが足りない）
    ov[~aa & rr] = (40, 110, 230)    # モデルだけ（はみ出し）
    iou = (aa & rr).sum() / max(1, (aa | rr).sum())
    sheet = Image.new('RGB', (res * 3, res + 40), (255, 255, 255))
    sheet.paste(a.convert('RGB'), (0, 40))
    sheet.paste(b.convert('RGB'), (res, 40))
    sheet.paste(Image.fromarray(ov), (res * 2, 40))
    d = ImageDraw.Draw(sheet)
    f = font(26)
    d.text((10, 6), f'{view}：絵', fill=(0, 0, 0), font=f)
    d.text((res + 10, 6), 'haru_bs（同じカメラ）', fill=(0, 0, 0), font=f)
    d.text((2 * res + 10, 6), f'影の重なり IoU {iou:.3f}（赤＝絵だけ、青＝モデルだけ）', fill=(0, 0, 0), font=f)
    sheet.save(out_path)
    return iou


def expr_quadrants():
    src = os.path.join(ART, 'haru_face_expressions.png')
    im = Image.open(src).convert('RGBA')
    for k in range(4):
        p = os.path.join(ART, f'expr_q{k}.png')
        if not os.path.exists(p):
            im.crop(((k % 2) * 1024, (k // 2) * 1024, (k % 2) * 1024 + 1024, (k // 2) * 1024 + 1024)).save(p)


def main(views, tag):
    expr_quadrants()
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'haru_bs.blend'))
    os.makedirs(os.path.join(OUT, 'cmp', tag), exist_ok=True)
    res = []
    for v in views:
        cfg = VIEWS[v]
        art_path = os.path.join(ART, cfg['img'])
        art_alpha = np.array(Image.open(art_path).convert('RGBA'))[..., 3]
        # 頭の絵には首から下が無いので、頭の向きでは頭・髪・ゴーグル・首（体）だけを描く
        for ob in bpy.data.objects:
            if ob.type == 'MESH':
                ob.hide_render = (not cfg['full']) and not ob.name.startswith(HEAD_PARTS + ('SM_Char_HaruBS_Body',))
                # 全身の絵には銃と光刃が無い（発注書：全身では外した）
                if cfg['full'] and ob.name in ('SM_Weapon_HaruBS_SparkGun', 'LightBlade'):
                    ob.hide_render = True
        cam, back = setup_camera(v, art_alpha)
        m, right, up, back = cam_basis(cfg['rz'], cfg['rx'])
        L = (back * 0.85 + up * 0.45 - right * 0.30).normalized()
        for m in [m for m in bpy.data.materials if m.name.startswith('TOON_')]:
            bpy.data.materials.remove(m)
        TOON_KEYS.clear()
        toon_materials(L, cfg.get('expr', 0))
        rp = os.path.join(OUT, 'cmp', tag, f'{v}_render.png')
        render(v, rp)
        iou = compose(v, art_path, rp, os.path.join(OUT, 'cmp', tag, f'{v}.png'))
        res.append((v, iou))
        # 次の向きのために材質を戻す
        for ob in bpy.data.objects:
            if ob.type == 'MESH':
                for slot in ob.material_slots:
                    if slot.material and slot.material.name.startswith('TOON_'):
                        slot.material = bpy.data.materials[slot.material.name[5:]]
    for v, iou in res:
        print(f'IOU {v:22s} {iou:.3f}')


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    tag = 'p0'
    if '--pass' in argv:
        i = argv.index('--pass')
        tag = 'p' + argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    views = [a for a in argv if a in VIEWS] or list(VIEWS)
    main(views, tag)
