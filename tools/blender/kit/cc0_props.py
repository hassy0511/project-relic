"""BlenderKit の CC0 の小物を、キットの画風に直して部品にする（docs/art_orders/BlenderKit検討.md 11 章）。

元の素材は tools/blenderkit_fetch.py が build/blenderkit/props/<名前>_<id8>/ に落とした物（git に入らない所）。CC0 の物だけを読む
（asset.json の license が cc_zero でなければ止まる）。Royalty Free の stylized_wooden_barrel は読まない・写さない。
直し方（どれも数値で決まり、何度流しても同じ物ができる）：
  1. 元の材質ごとに、キットの材質の名前（wood・wood2・brass・graphite・ivory・cloth・linen・dark・amber）を決める（表 SPEC の "mats"）。
     写実の物（絵の材質）は、面ごとに絵の色を読んで、明るさと鮮やかさで振り分ける（"classify"）。写真の色・模様は使わない
  2. 三角形を減らす：同じ平面の細かい面をまとめ（材質の境は残す）、残りを縮約（collapse）で目当ての数まで。
     樽（"lathe"）は縮約すると板と輪がばらばらに崩れるので、元の形の高さごとの半径と輪の高さを読み取り、回転体で組み直す
  3. 2 m の格子に合わせた大きさ（"height" か "width"）、原点は底の中心、正面は +Z
  4. town_geo.write_glb で書き出す（平らな色は頂点の色の flat、黒鉛と真鍮は metal、灯の芯は amber。町と遺構のキットの同じ名前の材質と汚れの層が付く）
出所は godot/assets/kit/cc0/SOURCES.json（名前・id・作者・ライセンス・取得日、作った道具と日付）。CC0 でなければ書かない。

  .venv-blender/bin/python tools/blender/kit/cc0_props.py              残す物（KEEP）を godot/assets/kit/cc0/ に
  .venv-blender/bin/python tools/blender/kit/cc0_props.py --only cask
  .venv-blender/bin/python tools/blender/kit/cc0_props.py --all        残さないと決めた物（DROPPED）も build/cc0_props/ に作る（比べの画像用）
  .venv-blender/bin/python tools/blender/kit/cc0_props.py --gallery    確認ページ用の tools/model_viewer/kit_cc0.glb も作る
"""
from __future__ import annotations

import argparse
import colorsys
import datetime
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SRC = os.path.join(REPO, 'build', 'blenderkit', 'props')
OUT = os.path.join(REPO, 'godot', 'assets', 'kit', 'cc0')
TRY = os.path.join(REPO, 'build', 'cc0_props')
NEVER = ('stylized_wooden_barrel_8ff2cdb8',)       # Royalty Free：読まない


def _wood_or_metal(rgb):
    """写実の樽・木箱の面の色 → 材質。灰色で暗い所は金物（黒鉛）、茶色は木（明るい板は wood2）"""
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    if s < 0.28 and v < 0.5:
        return 'graphite'
    return 'wood2' if v > 0.42 else 'wood'


# 素材ごとの直し方。mats：元の材質の名前の頭 → キットの材質。tris：三角形の目当て。height / width：大きさ（m）。yaw：正面を +Z へ
SPEC = {
    'cask': dict(dir='barrel_053353d1', file='model.glb', height=1.0, tris=300, dissolve=False,
                 lathe={'body': 'wood2', 'hoop': 'brass', 'hoop_from': ('graphite', 'brass'), 'lid': 'wood', 'rows': 8, 'segs': 12},
                 mats={'barrel': 'wood2', 'grid wooden': 'wood', 'wooden clip': 'graphite', 'metal clip': 'brass'},
                 note='膨らみの大きい樽。縮約すると板と輪が崩れたので、元の輪郭（高さごとの半径）と輪の高さから回転体で組み直した。胴は明るい板、輪は真鍮'),
    'slat_crate': dict(dir='lp_box_140d036b', file='model.glb', height=0.62, tris=600, dissolve=False,
                       mats={'Wood_B': 'wood2', 'Wood_C': 'wood', 'Wood_D': 'graphite'},
                       note='板を打ち付けた木箱'),
    'light_shack': dict(dir='lp_light_shack_abe78b87', file='model.glb', height=2.9, tris=1500,
                        mats={'Wood_A': 'wood2', 'Wood_B': 'wood2', 'Wood_C': 'wood', 'Wood_D': 'graphite', 'Tarp': 'cloth'},
                        note='帆布の屋根の小屋（露店）'),
    'power_unit': dict(dir='power_unit_02_0e47dc25', file='resolution_1K.blend', width=1.3, tris=600,
                       drop_mods=('BEVEL', 'NODES', 'WEIGHTED_NORMAL'), drop_objects=('wall plate fans', 'stud'),
                       mats={'GWC Go green': 'ivory', 'Tube light': 'amber', 'Easy glass': 'dark', 'GWC S grating': 'graphite',
                             'GWC Warning red': 'cloth', 'Pipe04': 'graphite', 'Metal tiles': 'graphite', 'Round metal': 'graphite',
                             'Bronze': 'brass', 'Neon green': 'amber', 'RED Stripes': 'cloth', 'Wall plate': 'graphite', 'Stud': 'brass'},
                       note='床に置く機械の箱（先史の白磁・黒鉛・真鍮、琥珀の灯）'),
    'wine_barrel': dict(dir='wine_barrel_01_05d7206c', file='model.glb', height=1.0, tris=500, dissolve=False, classify=_wood_or_metal,
                        note='写実の樽を平らな色に（比べ）'),
    'plank_box': dict(dir='wooden_crate_01_bc3c8bf5', file='model.glb', height=0.6, tris=500, dissolve=False, classify=_wood_or_metal,
                      note='写実の木箱（長持ち形）を平らな色に。絵の色を面ごとに読んで、木と金物に振り分けた'),
}


def asset_of(name):
    d = os.path.join(SRC, SPEC[name]['dir'])
    if os.path.basename(d) in NEVER:
        sys.exit(f'{d} は Royalty Free：使わない')
    a = json.load(open(os.path.join(d, 'asset.json')))
    if a.get('license') != 'cc_zero':
        sys.exit(f"{a.get('name')} は {a.get('license')}：CC0 でない物は部品にしない")
    return d, a


# ---------------------------------------------------------------- Blender

def _reset():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _load(path, spec):
    """素材を開いて、見えるメッシュを 1 つの物体（Blender の座標、変形を当てたもの）にする"""
    import bpy
    if path.endswith('.blend'):
        bpy.ops.wm.open_mainfile(filepath=path, use_scripts=False)
        for ob in list(bpy.context.scene.objects):
            low = ob.name.lower()
            if ob.type == 'MESH' and any(k in low for k in spec.get('drop_objects', ())):
                bpy.data.objects.remove(ob, do_unlink=True)
                continue
            if ob.type == 'MESH':
                for m in list(ob.modifiers):
                    if m.type in spec.get('drop_mods', ()):
                        ob.modifiers.remove(m)
    else:
        _reset()
        bpy.ops.import_scene.gltf(filepath=path)
    meshes = [ob for ob in bpy.context.scene.objects if ob.type == 'MESH' and (ob.visible_get() or not ob.hide_render)]
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for ob in meshes:
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        me.transform(ob.matrix_world)
        out.append((ob.name, me))
    return out


def _face_colors(me):
    """面ごとの元の色（材質の絵があれば、面の UV の真ん中の絵の色。無ければ材質の下地の色）。sRGB の 0〜1"""
    cols = []
    img_px = {}
    uv = me.uv_layers.active.data if me.uv_layers.active else None
    for pl in me.polygons:
        mat = me.materials[pl.material_index] if me.materials else None
        rgb = (0.5, 0.5, 0.5)
        if mat is not None and mat.use_nodes:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is not None:
                sock = bsdf.inputs['Base Color']
                img = None
                if sock.links:
                    n = sock.links[0].from_node
                    for _ in range(4):
                        if n.type == 'TEX_IMAGE':
                            img = n.image
                            break
                        lk = next((i.links[0] for i in n.inputs if i.links), None)
                        if lk is None:
                            break
                        n = lk.from_node
                if img is not None and uv is not None:
                    if img.name not in img_px:
                        w, h = img.size
                        a = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
                        img_px[img.name] = a
                    a = img_px[img.name]
                    h, w = a.shape[:2]
                    samples = []
                    for li in pl.loop_indices:
                        u, v = uv[li].uv
                        samples.append(a[int((v % 1.0) * (h - 1)), int((u % 1.0) * (w - 1)), :3])
                    c = np.mean(samples, 0)
                    # 絵は線形の色で入っている：sRGB に直す
                    rgb = tuple(float(x) ** (1 / 2.2) for x in c)
                else:
                    c = sock.default_value
                    rgb = tuple(float(c[i]) ** (1 / 2.2) for i in range(3))
        cols.append(rgb)
    return cols


def _palette_index(names, want):
    if want not in names:
        names.append(want)
    return names.index(want)


def restyle(name, out_path):
    import bpy  # noqa: F401（bmesh より先に読む）
    import bmesh

    import town_geo as geo
    spec = SPEC[name]
    d, a = asset_of(name)
    src = os.path.join(d, spec['file'])
    parts = _load(src, spec)
    # 面ごとにキットの材質を決めて、1 つの bmesh にまとめる
    pal: list[str] = []
    bm = bmesh.new()
    src_tris = 0
    for obname, me in parts:
        src_tris += sum(len(p.vertices) - 2 for p in me.polygons)
        if 'classify' in spec:
            cols = _face_colors(me)
            idx = [_palette_index(pal, spec['classify'](c)) for c in cols]
        else:
            idx = []
            for pl in me.polygons:
                mat = me.materials[pl.material_index] if me.materials else None
                mname = mat.name if mat else obname
                hit = next((v for k, v in spec['mats'].items() if mname.lower().startswith(k.lower()) or obname.lower().startswith(k.lower())), None)
                if hit is None:
                    raise SystemExit(f'{name}：材質 {mname}（{obname}）の行き先が表に無い')
                idx.append(_palette_index(pal, hit))
        for pl, i in zip(me.polygons, idx):
            pl.material_index = i
        bm.from_mesh(me)         # 何度でも足せる（面の材質の番号はキットの材質の並び）
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in pal:
        me.materials.append(bpy.data.materials.get(p) or bpy.data.materials.new(p))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for o in list(bpy.context.scene.objects):
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    # 三角形を減らす：重なった頂点をつなぎ、同じ平面の面をまとめ（材質の境は残す）、縮約で目当てまで
    co = np.array([vt.co[:] for vt in me.vertices], float)
    diag = float(np.linalg.norm(co.max(0) - co.min(0)))
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # 板・金具の継ぎ目の重なった頂点をつなぐ（つながっていない小さな塊は、縮約で減らせない）
    bpy.ops.mesh.remove_doubles(threshold=diag * spec.get('weld', 0.0002))
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.select_all(action='SELECT')
    if spec.get('dissolve', True):
        bpy.ops.mesh.dissolve_limited(angle_limit=math.radians(4.0), delimit={'MATERIAL'})
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode='OBJECT')
    for _ in range(0 if spec.get('lathe') else 3):       # 回転体で組み直す物は縮約しない（頂点の位置だけを使う）
        if len(me.polygons) <= spec['tris'] * 1.05:
            break
        mod = ob.modifiers.new('dec', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = spec['tris'] / len(me.polygons)
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete_loose()
    bpy.ops.object.mode_set(mode='OBJECT')
    # ゲームの座標へ：Blender (x, y, z) → ゲーム (x, z, -y)
    v = np.array([vt.co[:] for vt in me.vertices], float)
    g = np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)
    yaw = spec.get('yaw', 0.0)
    if yaw:
        g = g @ geo.rot_y(yaw).T
    lo, hi = g.min(0), g.max(0)
    if 'height' in spec:
        s = spec['height'] / (hi[1] - lo[1])
    else:
        s = spec['width'] / max(hi[0] - lo[0], hi[2] - lo[2])
    c = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    g = (g - c) * s
    if spec.get('lathe'):
        part = _lathe_rebuild(name, spec, g, me, pal)
        info = geo.write_glb(part, out_path)
        info.update({'src_tris': src_tris, 'mats_used': sorted(part.by_mat)})
        return info, a
    part = geo.Part(name)
    for mi, mname in enumerate(pal):
        faces = [list(p.vertices) for p in me.polygons if p.material_index == mi]
        if not faces:
            continue
        used = sorted({i for f in faces for i in f})
        remap = {o: k for k, o in enumerate(used)}
        smooth = [bool(p.use_smooth) for p in me.polygons if p.material_index == mi]
        piece = geo.Piece(g[used], [[remap[i] for i in f] for f in faces], sm=smooth)
        part.add(mname, piece)
    info = geo.write_glb(part, out_path)
    info.update({'src_tris': src_tris, 'mats_used': pal})
    return info, a


def _lathe_rebuild(name, spec, g, me, pal):
    """回転体の物（樽）：縮約すると板と輪がばらばらに崩れるので、元の形の「高さごとの半径」（外側の輪郭）と
    金具の輪の高さを読み取り、town_geo.lathe で組み直す（三角形はキットの樽と同じくらい）。色は材質の表のとおり"""
    import town_geo as geo
    body = spec['lathe']['body']
    hoop = spec['lathe']['hoop']
    lo, hi = g.min(0), g.max(0)
    h = float(hi[1] - lo[1])
    r = np.hypot(g[:, 0], g[:, 2])
    mat_of = np.zeros(len(g), int) - 1
    for p in me.polygons:
        for vi in p.vertices:
            mat_of[vi] = p.material_index
    n = spec['lathe'].get('rows', 8)
    prof = []
    for k in range(n + 1):
        y = lo[1] + h * k / n
        sel = np.abs(g[:, 1] - y) < h / n * 0.6
        prof.append((k / n, float(np.percentile(r[sel], 92)) if sel.any() else 0.3))
    rmax = max(q for _, q in prof)
    part = geo.Part(name)
    segs = spec['lathe'].get('segs', 12)
    part.add(body, geo.lathe((0, lo[1], 0), (0, hi[1], 0), [(t, q * 0.985) for t, q in prof], segs))
    # 金具の輪：輪の材質の頂点の高さの固まり
    src = spec['lathe'].get('hoop_from', (hoop,))
    hy = sorted(float(y) for y, m in zip(g[:, 1], mat_of) if m >= 0 and pal[m] in src)
    bands = []
    for y in hy:
        if bands and y - bands[-1][-1] < h * 0.04:
            bands[-1].append(y)
        else:
            bands.append([y])
    bands = [b for b in bands if len(b) >= 6]
    for b in bands:
        y0, y1 = min(b), max(b)
        yc = (y0 + y1) / 2
        th = max(min(y1 - y0, h * 0.06), h * 0.035)
        t = (yc - lo[1]) / h
        k = min(int(t * n), n - 1)
        rr = prof[k][1] + (prof[k + 1][1] - prof[k][1]) * (t * n - k)
        part.add(hoop, geo.cyl((0, yc - th / 2, 0), (0, yc + th / 2, 0), rr * 0.985 + 0.012, segs, cap=False))
    lid = spec['lathe'].get('lid')
    if lid:
        part.add(lid, geo.cyl((0, hi[1] - 0.012, 0), (0, hi[1] + 0.006, 0), prof[-1][1] * 0.9, segs))
    print(f'[cc0] {name}: 回転体で組み直し（半径 {rmax:.2f} m、輪 {len(bands)} 本）', flush=True)
    return part


def sources(entries):
    """godot/assets/kit/cc0/SOURCES.json：tools/blenderkit_fetch.py の install と同じ項目（名前・id・ライセンス・作者・型・ページ・取得日）＋作り方"""
    path = os.path.join(OUT, 'SOURCES.json')
    data = json.load(open(path)) if os.path.exists(path) else {}
    for fname, (a, spec, info) in entries.items():
        if a['license'] != 'cc_zero':
            sys.exit(f"{a['name']} は {a['license']}：書かない")
        data[fname] = {k: a[k] for k in ('name', 'id', 'license', 'author', 'style', 'page', 'fetched', 'file_type')} | {
            'made_from': spec['file'], 'made_by': 'tools/blender/kit/cc0_props.py', 'made': datetime.date.today().isoformat(),
            'tris': info['tris'], 'src_tris': info['src_tris'], 'note': spec['note']}
    with open(path, 'w') as fp:
        json.dump(dict(sorted(data.items())), fp, ensure_ascii=False, indent=1)
        fp.write('\n')


# 比べた結果、部品として残す物（ほかは build/cc0_props/ に作るだけ）。理由は 11 章
KEEP = ('cask', 'plank_box')
DROPPED = tuple(n for n in SPEC if n not in KEEP)


def gallery():
    """確認ページ（tools/model_viewer）用：残した部品を横に並べた 1 つの GLB（tools/model_viewer/kit_cc0.glb）"""
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    x = 0.0
    for n in KEEP:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, f'{n}.glb'))
        new = [o for o in bpy.data.objects if o not in before]
        lo, hi = SPEC_BOUNDS[n]
        for o in new:
            o.location.x += x - lo
        x += (hi - lo) + 0.6
    bpy.ops.object.select_all(action='SELECT')
    path = os.path.join(REPO, 'tools', 'model_viewer', 'kit_cc0.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, use_selection=True, export_animations=False,
                              export_apply=True, export_vertex_color='ACTIVE', export_active_vertex_color_when_no_material=True)
    print('[cc0] 確認ページ用', path, flush=True)


SPEC_BOUNDS: dict = {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', default='')
    ap.add_argument('--all', action='store_true', help='残さない物も build/cc0_props/ に作る')
    ap.add_argument('--gallery', action='store_true', help='確認ページ用に残した部品を並べた tools/model_viewer/kit_cc0.glb も作る')
    a = ap.parse_args()
    names = [n for n in a.only.split(',') if n] or (list(SPEC) if a.all else list(KEEP))
    index_path = os.path.join(OUT, 'parts.json')
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    entries = {}
    for n in names:
        keep = n in KEEP
        path = os.path.join(OUT if keep else TRY, f'{n}.glb')
        info, asset = restyle(n, path)
        print(f"[cc0] {n}{'' if keep else '（比べだけ）'}: {asset['name']} / {asset['author']} / {asset['license']}  三角形 {info['src_tris']} → {info['tris']}  "
              f"大きさ {info['min']}〜{info['max']}  材質 {info['mats_used']}", flush=True)
        if keep:
            index[n] = {k: info[k] for k in ('tris', 'mats', 'min', 'max')}
            entries[f'{n}.glb'] = (asset, SPEC[n], info)
    if a.gallery:
        idx = json.load(open(index_path)) if os.path.exists(index_path) else index
        for n in KEEP:
            SPEC_BOUNDS[n] = (idx[n]['min'][0], idx[n]['max'][0])
    if entries:
        os.makedirs(OUT, exist_ok=True)
        with open(index_path, 'w') as fh:
            json.dump({k: index[k] for k in sorted(index)}, fh, ensure_ascii=False, indent=1)
            fh.write('\n')
        sources(entries)
    if a.gallery:
        gallery()


if __name__ == '__main__':
    main()
