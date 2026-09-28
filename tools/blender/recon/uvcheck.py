"""UV の確認画像：UV の島の並び（部位ごとに色）と、市松模様を UV で貼ったメッシュ（Cycles）。

  python tools/blender/recon/uvcheck.py      build/recon/haru_mesh.blend → build/recon/uv_check.png

市松の升目の大きさがそろっていれば、細かさ（テクセル密度）が均一（頭は 2 倍に細かい）。升目がゆがむ所は
展開の伸び、升目がずれる線がシーム（部位の切れ目）。島の間のすき間の最小（2048 角の画素）も測る。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from recon import views as V  # noqa: E402


def uv_islands(me) -> tuple[np.ndarray, np.ndarray]:
    """三角形ごとの UV (n, 3, 2) と、UV でつながった島の番号"""
    nl = len(me.loops)
    uv = np.empty(nl * 2, np.float32)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 3, 2)
    vi = np.empty(nl, np.int32)
    me.loops.foreach_get('vertex_index', vi)
    vi = vi.reshape(-1, 3)
    # UV の点（頂点と UV の組）でつなぐ
    key = np.round(uv.reshape(-1, 2) * 1e6).astype(np.int64)
    ids = np.unique(np.concatenate([vi.reshape(-1, 1), key], 1), axis=0, return_inverse=True)[1].reshape(-1, 3)
    from scipy import sparse
    n = int(ids.max()) + 1
    e = np.concatenate([ids[:, [0, 1]], ids[:, [1, 2]]])
    A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    _, comp = sparse.csgraph.connected_components(A, directed=False)
    return uv, comp[ids[:, 0]]


def layout_image(uv: np.ndarray, isl: np.ndarray, size: int = 1024) -> tuple[np.ndarray, float]:
    """島の並びの画像と、島の間のすき間の最小（2048 角の画素）"""
    rng = np.random.default_rng(1)
    cols = rng.integers(70, 255, (int(isl.max()) + 1, 3))
    im = Image.new('RGB', (size, size), (30, 30, 30))
    dr = ImageDraw.Draw(im)
    lab = Image.new('I', (2048, 2048), 0)
    dl = ImageDraw.Draw(lab)
    for t, i in zip(uv, isl):
        dr.polygon([(p[0] * size, (1 - p[1]) * size) for p in t], fill=tuple(int(c) for c in cols[i]))
        dl.polygon([(p[0] * 2048, (1 - p[1]) * 2048) for p in t], fill=int(i) + 1)
    L = np.asarray(lab)
    gaps = []
    for i in range(1, int(isl.max()) + 2):
        m = L == i
        if not m.any():
            continue
        sl = ndi.find_objects(m.astype(np.int32))[0]
        pad = 12
        ys = slice(max(0, sl[0].start - pad), sl[0].stop + pad)
        xs = slice(max(0, sl[1].start - pad), sl[1].stop + pad)
        sub = L[ys, xs]
        d = ndi.distance_transform_edt(sub != i)
        other = (sub > 0) & (sub != i)
        if other.any():
            gaps.append(float(d[other].min()))
    return np.asarray(im), (min(gaps) if gaps else float('inf'))


def checker_renders(path_blend: str, tmp: str, res: int = 512) -> list[np.ndarray]:
    import bpy
    from recon import surfcheck
    bpy.ops.wm.open_mainfile(filepath=path_blend)
    obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    mat = bpy.data.materials.new('uv_checker')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ck = nt.nodes.new('ShaderNodeTexChecker')
    ck.inputs['Scale'].default_value = 64.0          # 2048 角で 32 画素の升目
    ck.inputs['Color1'].default_value = (0.85, 0.85, 0.85, 1)
    ck.inputs['Color2'].default_value = (0.15, 0.25, 0.55, 1)
    nt.links.new(tc.outputs['UV'], ck.inputs['Vector'])
    nt.links.new(ck.outputs['Color'], bsdf.inputs['Base Color'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('uv_world')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    cam_data = bpy.data.cameras.new('uv_cam')
    cam_data.type = 'ORTHO'
    cam_data.clip_end = 20
    cam = bpy.data.objects.new('uv_cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.lights.new('uv_sun', 'SUN')
    sun.energy = 1.5
    so = bpy.data.objects.new('uv_sun', sun)
    scene.collection.objects.link(so)
    out = []
    for center, size, az in (((0, 0, 0.78), 1.62, 0), ((0, 0, 0.78), 1.62, 180), ((0, 0, 1.36), 0.42, -35),
                             ((0, 0, 1.36), 0.42, 150)):
        img = surfcheck.shot(scene, cam, [so, so], center, size, az, 0, res, os.path.join(tmp, 'uv.png'))
        out.append(img)
    return out


def run(out: str = V.WORK) -> dict:
    """out の haru_mesh.blend を調べて uv_check.png を書く。島の数・使われる面積・すき間の最小を返す"""
    import bpy
    path = os.path.join(out, 'haru_mesh.blend')
    bpy.ops.wm.open_mainfile(filepath=path)
    obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    uv, isl = uv_islands(obj.data)
    lay, gap = layout_image(uv, isl)
    area = float(np.abs(np.cross(uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0])).sum() / 2)
    tmp = os.path.join(out, 'render')
    os.makedirs(tmp, exist_ok=True)
    rens = checker_renders(path, tmp)
    lay = np.asarray(Image.fromarray(lay).resize((1024, 1024)))
    ImageDraw.Draw(im := Image.fromarray(lay)).text(
        (8, 8), f'islands {int(isl.max()) + 1}  used {area:.3f}  min gap {gap:.1f}px@2048', fill=(255, 255, 0))
    right = np.concatenate([np.concatenate(rens[:2], 1), np.concatenate(rens[2:], 1)], 0)
    Image.fromarray(np.concatenate([np.asarray(im), right], 1)).save(os.path.join(out, 'uv_check.png'))
    return {'islands_check': int(isl.max()) + 1, 'uv_area_used_check': round(area, 4),
            'min_gap_px_2048': round(gap, 2)}


if __name__ == '__main__':
    print(run())
