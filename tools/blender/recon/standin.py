"""組み込みの試験用の「代役」：色の付いた A ポーズのハル（テクスチャの段が仕上がるまでの仮のもの）。

  .venv-blender/bin/python tools/blender/recon/standin.py
      [--mesh build/recon/haru_mesh.glb]  形（fair / carve の出力）
      [--out build/recon/prep/standin_textured.glb]

本物（texture.py が作る build/recon/haru_textured_apose.glb）と同じ約束で書き出す：
  - A ポーズ、身長 1.55m、正面 -Y、靴底 z=0、物体 1 つ
  - 材質 'haru_body'：下地の色のテクスチャ＋発光のテクスチャ（琥珀の部分）
  - 材質 'haru_face'：face_atlas.png。UV は区画 0（Blender の u∈[0,0.5]、v∈[0.5,1]）
色の付け方はわざと素朴：面の向きで正面の絵か背面の絵をまっすぐ投影するだけ（横向きの面は流れる）。
骨・動作・銃・光刃・Godot の組み込み・確認画像の流れを、形が仕上がる前に通して試すためのもの。

入力のメッシュは最初に build/recon/prep/ へ写してから使う（ほかの作業が書き換えている最中でも崩れないように）。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from lib import common as C  # noqa: E402

REPO = C.REPO
RECON = os.path.join(REPO, 'build', 'recon')
PREP = os.path.join(RECON, 'prep')
SRC = os.path.join(RECON, 'src')
IMG = 2048


def load_json(name: str) -> dict:
    with open(os.path.join(RECON, name)) as f:
        return json.load(f)


def filled_rgba(view: str) -> np.ndarray:
    """絵の RGB。透明な所は一番近い不透明な画素の色で埋める（外形から少しはみ出た頂点が黒くならないように）"""
    a = np.asarray(Image.open(os.path.join(SRC, f'haru_3d_{view}.png')).convert('RGBA'))
    hole = a[..., 3] < 128
    _, (iy, ix) = ndi.distance_transform_edt(hole, return_indices=True)
    rgb = a[..., :3][iy, ix]
    return rgb


def make_textures() -> tuple[str, str]:
    """横長 4096×2048：左半分が正面の絵、右半分が背面の絵。発光は琥珀色の所だけ"""
    rgb = np.concatenate([filled_rgba('front'), filled_rgba('back')], 1)
    f = rgb.astype(np.float32) / 255
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    amber = (r > 0.85) & (g > 0.55) & (g < 0.9) & (b < 0.5) & (r - b > 0.45)
    emit = (rgb * amber[..., None]).astype(np.uint8)
    base_p = os.path.join(PREP, 'standin_base.png')
    emit_p = os.path.join(PREP, 'standin_emit.png')
    Image.fromarray(rgb).save(base_p)
    Image.fromarray(emit).save(emit_p)
    return base_p, emit_p


def textured_material(name: str, base: str, emit: str | None) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Metallic'].default_value = 0.0
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(base)
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    if emit:
        et = nt.nodes.new('ShaderNodeTexImage')
        et.image = bpy.data.images.load(emit)
        nt.links.new(et.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 1.0
    return mat


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--mesh', default=os.path.join(RECON, 'haru_mesh.glb'))
    ap.add_argument('--out', default=os.path.join(PREP, 'standin_textured.glb'))
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    os.makedirs(PREP, exist_ok=True)
    copy = os.path.join(PREP, 'haru_mesh_copy.glb')
    shutil.copyfile(args.mesh, copy)

    cal = load_json('calib.json')['views']
    atlas = load_json('face_atlas.json')
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=copy)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    obj = C.join(meshes, 'haru') if len(meshes) > 1 else meshes[0]
    obj.name = 'haru'
    me = obj.data
    for o in list(bpy.context.scene.objects):
        if o is not obj:
            bpy.data.objects.remove(o, do_unlink=True)
    # UV は 1 組だけにする
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')

    nv, nl, npoly = len(me.vertices), len(me.loops), len(me.polygons)
    co = np.empty(nv * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    lv = np.empty(nl, np.int32)
    me.loops.foreach_get('vertex_index', lv)
    ls = np.empty(npoly, np.int32)
    me.polygons.foreach_get('loop_start', ls)
    lt = np.empty(npoly, np.int32)
    me.polygons.foreach_get('loop_total', lt)
    pn = np.empty(npoly * 3)
    me.polygons.foreach_get('normal', pn)
    pn = pn.reshape(-1, 3)
    poly_of_loop = np.repeat(np.arange(npoly), lt)
    p = co[lv]

    # 正面／背面の投影（横長のテクスチャの左右の半分）
    fr, bk = cal['front'], cal['back']
    fu = fr['u0'] + fr['pixels_per_meter'] * p[:, 0]
    fv = fr['v0'] - fr['pixels_per_meter'] * p[:, 2]
    bu = bk['u0'] + bk['pixels_per_meter'] * (-p[:, 0])
    bv = bk['v0'] - bk['pixels_per_meter'] * p[:, 2]
    front = pn[poly_of_loop, 1] <= 0.0
    uv = np.empty((nl, 2))
    uv[:, 0] = np.where(front, fu / (2 * IMG), (IMG + bu) / (2 * IMG))
    uv[:, 1] = np.where(front, 1 - fv / IMG, 1 - bv / IMG)

    # 顔：頭の前向きの面のうち、正面へ投影して顔の窓に入るもの
    wx0, wy0, wx1, wy1 = atlas['window_front_px']
    qx0, qy0 = atlas['window_atlas_px'][:2]
    k = atlas['atlas_px_per_front_px']
    inside = (fu >= wx0) & (fu <= wx1) & (fv >= wy0) & (fv <= wy1)
    all_in = np.logical_and.reduceat(inside, ls)
    face_poly = all_in & (pn[:, 1] < -0.25)
    face_loop = face_poly[poly_of_loop]
    ax = qx0 + (fu - wx0) * k
    ay = qy0 + (fv - wy0) * k
    uv[face_loop, 0] = ax[face_loop] / IMG
    uv[face_loop, 1] = 1 - ay[face_loop] / IMG
    me.uv_layers[0].data.foreach_set('uv', uv.ravel())

    base_p, emit_p = make_textures()
    old = [m for m in me.materials if m]
    me.materials.clear()
    for m in old:  # 名前を空ける（同じ名前だと 'haru_body.001' になる）
        bpy.data.materials.remove(m)
    me.materials.append(textured_material('haru_body', base_p, emit_p))
    me.materials.append(textured_material('haru_face', os.path.join(RECON, atlas['atlas_file']), None))
    me.polygons.foreach_set('material_index', face_poly.astype(np.int32))
    me.update()

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=args.out, export_format='GLB', export_yup=True, export_animations=False,
                              use_selection=True)
    print(json.dumps({'out': args.out, 'tris': int(sum(lt - 2)), 'face_polys': int(face_poly.sum())}))


if __name__ == '__main__':
    main()
