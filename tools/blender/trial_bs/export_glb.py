"""ゲームの形にまとめて GLB に書き出す（段 1 は骨なしの確認用。段 4 で骨・動作つきに広げる）。

.blend の中は部品ごとの SM_ 物体（スキル集の character-artist：服・硬い物は別のメッシュ）。書き出しでは
描く回数（スマホの draw call）を減らすため、材質の同じ部品を 1 つにまとめる（asset-optimization の考え）：
  SM_Char_HaruBS ……体・服・髪・ゴーグル（材質 2：MAT_Cloth_HaruBS、MAT_face_HaruBS）
  Frame_core / Frame_arm / Frame_legs ……外装フレームの段（ゲームが名前で探して出し入れ）
  LightBlade ……光刃（ゲームが探す。ふだんは隠す）
  SM_Weapon_HaruBS_SparkGun ＋ muzzle ……スパーク（材質名は spark_gun で始まる）
合わせて 7 つの面（描く回数 7）。
"""
import bpy


def _baked_copy(ob, coll, name=None):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    me.transform(ob.matrix_world)
    cp = bpy.data.objects.new(name or (ob.name + '_x'), me)
    coll.objects.link(cp)
    return cp


def _join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    # 色の属性（下塗りの確認用）は書き出さない
    for ca in list(ob.data.color_attributes):
        ob.data.color_attributes.remove(ca)
    return ob


def build_export_collection():
    sc = bpy.context.scene
    col = bpy.data.collections.get('COL_Export') or bpy.data.collections.new('COL_Export')
    if col.name not in sc.collection.children:
        sc.collection.children.link(col)
    geo = [o for o in bpy.data.objects if o.type == 'MESH' and o.users_collection and
           o.users_collection[0].name in ('COL_Geo', 'COL_Hair_HaruBS')]
    out = {}
    out['SM_Char_HaruBS'] = _join([_baked_copy(o, col) for o in geo], 'SM_Char_HaruBS')
    for g in ('Frame_core', 'Frame_arm', 'Frame_legs'):
        kids = [o for o in bpy.data.objects[g].children if o.type == 'MESH']
        out[g] = _join([_baked_copy(o, col) for o in kids], g + '_x')
    blade = bpy.data.objects['LightBlade']
    out['LightBlade'] = _join([_baked_copy(blade, col)], 'LightBlade_x')
    gun = bpy.data.objects['SM_Weapon_HaruBS_SparkGun']
    g2 = _join([_baked_copy(gun, col)], 'SM_Weapon_HaruBS_SparkGun_x')
    mz = bpy.data.objects.new('muzzle_x', None)
    col.objects.link(mz)
    mz.matrix_world = bpy.data.objects['muzzle'].matrix_world.copy()
    out['SparkGun'] = g2
    out['muzzle'] = mz
    return col, out


def export_static(path):
    """骨なしの確認用 GLB（ゲームの形にまとめた物）。.blend は保存しない（呼ぶ側で開き直す）"""
    col, out = build_export_collection()
    # 元の物体の名前を空けてから、約束の名前に付け直す
    for nm in ('Frame_core', 'Frame_arm', 'Frame_legs', 'LightBlade', 'muzzle', 'SM_Weapon_HaruBS_SparkGun'):
        o = bpy.data.objects.get(nm)
        if o is not None:
            o.name = nm + '_src'
            if o.type == 'MESH':
                o.data.name = nm + '_src'
    for nm, ob in (('Frame_core', out['Frame_core']), ('Frame_arm', out['Frame_arm']), ('Frame_legs', out['Frame_legs']),
                   ('LightBlade', out['LightBlade']), ('SM_Weapon_HaruBS_SparkGun', out['SparkGun']), ('muzzle', out['muzzle'])):
        ob.name = nm
        if ob.type == 'MESH':
            ob.data.name = nm
    # 銃口は銃の子（ゲームは find_child で探す）
    mz, gun = out['muzzle'], out['SparkGun']
    mw = mz.matrix_world.copy()
    mz.parent = gun
    mz.matrix_world = mw
    bpy.ops.object.select_all(action='DESELECT')
    for o in col.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_animations=False, export_vertex_color='NONE')
    return out


# ---------------------------------------------------------------- 段 2：骨・重み・14 の動作つき（ゲームの GLB）
GAME_OBJECTS = ('SM_Char_HaruBS', 'Frame_core', 'Frame_arm', 'Frame_legs', 'LightBlade', 'SM_Weapon_HaruBS_SparkGun', 'muzzle')


def _join_keep(objs, name):
    """部品を 1 つにまとめる（頂点の群＝重みは名前でそろう。骨格の修飾子は先頭の物の 1 つを残す）"""
    ob = _join(objs, name)
    mods = [m for m in ob.modifiers if m.type == 'ARMATURE']
    for m in mods[1:]:
        ob.modifiers.remove(m)
    return ob


def export_rigged(arm, path):
    """骨格・皮（重み）・動作（NLA の帯 = ゲームの動作の名前）を GLB に。.blend は保存しない。
    godot-export：GLB、+Y 上、修飾子を適用（骨格の修飾子は皮として残る）、動作は帯ごとの clip。
    export-pipeline：骨格と皮のメッシュを同じファイルに、拡大の残る骨格は無し、制約は焼いてから（anim.bake_legs）"""
    import anim
    anim.remove_ik(arm)
    sc = bpy.context.scene
    geo = [o for o in bpy.data.objects if o.type == 'MESH' and o.users_collection and
           o.users_collection[0].name in ('COL_Geo', 'COL_Hair_HaruBS')]
    char = _join_keep(geo, 'SM_Char_HaruBS')
    groups = {}
    for g in ('Frame_core', 'Frame_arm', 'Frame_legs'):
        e = bpy.data.objects[g]
        kids = [o for o in e.children if o.type == 'MESH']
        for k in kids:
            mw = k.matrix_world.copy()
            k.parent = arm
            k.matrix_world = mw
        bpy.data.objects.remove(e)
        groups[g] = _join_keep(kids, g)
    gun = bpy.data.objects['SM_Weapon_HaruBS_SparkGun']
    for ca in list(gun.data.color_attributes):
        gun.data.color_attributes.remove(ca)
    blade = bpy.data.objects['LightBlade']
    for ca in list(blade.data.color_attributes):
        blade.data.color_attributes.remove(ca)
    arm.data.pose_position = 'REST'
    arm.animation_data.action = None
    for tr in arm.animation_data.nla_tracks:
        tr.mute = False
    bpy.ops.object.select_all(action='DESELECT')
    for n in (arm.name,) + GAME_OBJECTS:
        bpy.data.objects[n].select_set(True)
    bpy.context.view_layer.objects.active = arm
    arm.data.pose_position = 'POSE'
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_frame_step=1,
        export_def_bones=True, export_skins=True, export_influence_nb=4, export_all_influences=False,
        export_vertex_color='NONE', export_reset_pose_bones=True, export_rest_position_armature=True,
        export_anim_slide_to_zero=False, export_bake_animation=False, export_optimize_animation_size=True)
    strip_scale_tracks(path)
    return path


def strip_scale_tracks(path, eps=1e-5):
    """書き出しの標本化（sampling）は、キーの無い骨の大きさにも一定の 1 の道を書く。値がすべて 1 なのを確かめてから
    道（channel・sampler）を外す（animation・rigging：骨の大きさのキーを持たない）。中身の数の列は残る（数 KB）"""
    import json
    import struct
    b = open(path, 'rb').read()
    ln = struct.unpack_from('<I', b, 8)[0]
    off = 12
    chunks = []
    while off < ln:
        cl, ct = struct.unpack_from('<II', b, off)
        chunks.append([ct, b[off + 8: off + 8 + cl]])
        off += 8 + cl
    js = json.loads(chunks[0][1])
    binc = chunks[1][1]
    removed = 0
    for a in js.get('animations', []):
        keep_ch, keep_s, remap = [], [], {}
        for ch in a['channels']:
            s = a['samplers'][ch['sampler']]
            if ch['target']['path'] == 'scale':
                acc = js['accessors'][s['output']]
                bv = js['bufferViews'][acc['bufferView']]
                base = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
                vals = struct.unpack_from('<%df' % (acc['count'] * 3), binc, base)
                if all(abs(v - 1.0) < eps for v in vals):
                    removed += 1
                    continue
                raise RuntimeError('scale animated on ' + js['nodes'][ch['target']['node']]['name'])
            if ch['sampler'] not in remap:
                remap[ch['sampler']] = len(keep_s)
                keep_s.append(s)
            ch['sampler'] = remap[ch['sampler']]
            keep_ch.append(ch)
        a['channels'], a['samplers'] = keep_ch, keep_s
    out = json.dumps(js, separators=(',', ':')).encode()
    out += b' ' * ((4 - len(out) % 4) % 4)
    body = struct.pack('<II', len(out), 0x4E4F534A) + out
    for ct, data in chunks[1:]:
        body += struct.pack('<II', len(data), ct) + data
    open(path, 'wb').write(struct.pack('<III', 0x46546C67, 2, 12 + len(body)) + body)
    print('removed constant scale tracks:', removed)
