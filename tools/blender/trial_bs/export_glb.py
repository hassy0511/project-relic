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
