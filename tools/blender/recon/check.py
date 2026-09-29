"""再構築したメッシュの確認：外形の一致（IoU）と、元の絵と並べた Cycles の画像。

  python tools/blender/recon/check.py        （carve.py の最後でも呼ばれる）

- 外形の IoU：間引き後のメッシュ（build/recon/haru_mesh.npz）の三角形を calib.json のカメラで
  2048 角の画像へ塗り、元の絵の外形のマスクと比べる。背面は正面の反転なので確認用。
- geo_check_<視点>.png：左から「元の絵」「灰色のメッシュ（同じカメラ）」「外形の差」
  （差の色：白＝両方、赤＝絵だけ（メッシュが足りない）、青＝メッシュだけ（はみ出し））。
- geo_check_virtual.png：絵のない向き。左前斜め（右前斜めの絵を反転したものと並べる）、左前 45 度、
  右後ろ・左後ろ 45 度、真上から。
- topology：つながり（塊の数・オイラー数・種数）、縁・非多様体の辺、自己交差する三角形の組
  （頂点を共有しない組。Blender の BVH の重なりで調べる）、長い辺、細い三角形の数。
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from recon import views as V  # noqa: E402

RENDER = 1024   # 確認の画像の大きさ（元の絵の半分）


def load_mesh(out: str = V.WORK) -> tuple[np.ndarray, np.ndarray]:
    d = np.load(os.path.join(out, f'{V.CH.ID}_mesh.npz'))
    return d['verts'].astype(np.float64), d['tris'].astype(np.int64)


def rasterize(verts: np.ndarray, tris: np.ndarray, cam: V.Cam, size: int = V.IMG) -> np.ndarray:
    """メッシュの外形を画像へ塗る（三角形ごとに多角形として塗る）"""
    u, v = cam.project(verts)
    img = Image.new('L', (size, size), 0)
    dr = ImageDraw.Draw(img)
    pu, pv = u[tris], v[tris]
    for i in range(len(tris)):
        dr.polygon([(pu[i, 0], pv[i, 0]), (pu[i, 1], pv[i, 1]), (pu[i, 2], pv[i, 2])], fill=255)
    return np.asarray(img) > 127


def silhouette_report(verts: np.ndarray, tris: np.ndarray, cams: dict[str, V.Cam]) -> tuple[dict, dict]:
    out, diffs = {}, {}
    for name, cam in cams.items():
        m = V.load_mask(name)
        r = rasterize(verts, tris, cam)
        inter, union = (r & m).sum(), (r | m).sum()
        out[name] = {'iou': round(float(inter / union), 4),
                     'missing_px': int((m & ~r).sum()), 'extra_px': int((r & ~m).sum())}
        diff = np.zeros(m.shape + (3,), np.uint8) + 40
        diff[m & r] = (235, 235, 235)
        diff[m & ~r] = (230, 40, 40)
        diff[r & ~m] = (40, 110, 240)
        diffs[name] = diff
    return out, diffs


# ---------------------------------------------------------------- Cycles

def _setup_scene(verts: np.ndarray, tris: np.ndarray):
    import bpy
    from lib import common as C
    C.reset_scene()
    me = bpy.data.meshes.new('haru_check')
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    me.loops.add(len(tris) * 3)
    me.loops.foreach_set('vertex_index', tris.astype(np.int32).ravel())
    me.polygons.add(len(tris))
    me.polygons.foreach_set('loop_start', (np.arange(len(tris)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(tris), bool))
    obj = bpy.data.objects.new('haru_check', me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(C.material('check_grey', (0.55, 0.55, 0.55), roughness=0.9))

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x = RENDER
    scene.render.resolution_y = RENDER
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('check_world')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
    cam_data = bpy.data.cameras.new('check_cam')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('check_cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new('check_sun', 'SUN')
    sun_data.energy = 2.2
    sun_data.angle = math.radians(10)
    sun = bpy.data.objects.new('check_sun', sun_data)
    scene.collection.objects.link(sun)
    return scene, cam, sun


def _render(scene, cam, sun, center, d, r, ortho_scale, path):
    import bpy
    from mathutils import Matrix, Vector
    d = Vector(d).normalized()
    r = Vector(r).normalized()
    up = r.cross(d).normalized()   # 見下ろすときも画像の上が正しくなるように
    # カメラは自分の -Z を見る。+X が画像の右、+Y が画像の上
    rot = Matrix((r, up, -d)).transposed()
    cam.matrix_world = Matrix.Translation(Vector(center) - d * 5.0) @ rot.to_4x4()
    cam.data.ortho_scale = ortho_scale
    cam.data.clip_end = 20
    # 光はカメラの左上・手前から
    ldir = (-d + (-r) * 0.6 + Vector((0, 0, 1)) * 0.9).normalized()
    sun.matrix_world = ldir.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32)
    # 透明の背景を暗い灰色に
    a = img[..., 3:4] / 255
    rgb = img[..., :3] * a + np.array([40, 40, 40]) * (1 - a)
    return rgb.astype(np.uint8)


def render_cam(scene, cam, sun, c: V.Cam, path: str) -> np.ndarray:
    """calib.json のカメラと画素が一致するように描く（元の絵の半分の大きさ）"""
    b = c.blender_camera()
    return _render(scene, cam, sun, b['center'], b['direction'], b['right'], b['ortho_scale'], path)


def render_az(scene, cam, sun, az: float, path: str, elev: float = 0.0) -> np.ndarray:
    """方位角 az（度、0=正面、90=本人の右）から見る。elev は上からの角度"""
    a, e = math.radians(az), math.radians(elev)
    d = np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e)])
    r = np.array([math.cos(a), -math.sin(a), 0.0])
    if abs(elev) > 80:
        r = np.array([1.0, 0.0, 0.0])
    return _render(scene, cam, sun, [0, 0, V.HEIGHT / 2], d, r, V.IMG / 1161.3, path)


def render_region(scene, cam, sun, center, size: float, az: float, path: str) -> np.ndarray:
    """一部分の近写（中心 center、幅 size m、方位角 az）。512 画素四方"""
    a = math.radians(az)
    d = np.array([math.sin(a), math.cos(a), 0.0])
    r = np.array([math.cos(a), -math.sin(a), 0.0])
    rx, ry = scene.render.resolution_x, scene.render.resolution_y
    scene.render.resolution_x = scene.render.resolution_y = 512
    img = _render(scene, cam, sun, list(center), d, r, size, path)
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    return img


def _src_on_grey(view: str, size: int = RENDER, mirror: bool = False) -> np.ndarray:
    rgba = V.load_rgba(view).astype(np.float32)
    a = rgba[..., 3:4] / 255
    rgb = (rgba[..., :3] * a + 40 * (1 - a)).astype(np.uint8)
    im = Image.fromarray(rgb).resize((size, size), Image.LANCZOS)
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return np.asarray(im)


def _label(arr: np.ndarray, text: str) -> np.ndarray:
    im = Image.fromarray(arr)
    ImageDraw.Draw(im).text((10, 10), text, fill=(255, 255, 0))
    return np.asarray(im)


def topology(verts: np.ndarray, tris: np.ndarray) -> dict:
    """メッシュのつながりと質（本文の topology）"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), 1)
    ue, cnt = np.unique(e, axis=0, return_counts=True)
    n = len(verts)
    ncomp, _ = connected_components(coo_matrix((np.ones(len(ue)), (ue[:, 0], ue[:, 1])), shape=(n, n)), directed=False)
    used = np.unique(tris)
    chi = len(used) - len(ue) + len(tris)
    out = {'components': int(ncomp - (n - len(used))), 'euler': int(chi),
           'genus': float((2 * (ncomp - (n - len(used))) - chi) / 2),
           'boundary_edges': int((cnt == 1).sum()), 'nonmanifold_edges': int((cnt > 2).sum())}
    L = np.linalg.norm(verts[ue[:, 0]] - verts[ue[:, 1]], axis=1)
    out['max_edge_m'] = round(float(L.max()), 4)
    out['edges_longer_than_80mm'] = int((L > 0.08).sum())
    out['edges_longer_than_50mm'] = int((L > 0.05).sum())
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2
    ssq = ((b - a) ** 2).sum(1) + ((c - b) ** 2).sum(1) + ((a - c) ** 2).sum(1)
    q = 4 * math.sqrt(3) * area / np.maximum(ssq, 1e-20)          # 1 = 正三角形
    out['tris_quality_below_0.1'] = int((q < 0.1).sum())
    try:
        from mathutils.bvhtree import BVHTree
        bvh = BVHTree.FromPolygons([tuple(v) for v in verts.tolist()], [tuple(t) for t in tris.tolist()],
                                   all_triangles=True)
        pairs = bvh.overlap(bvh)
        bad = [(i, j) for i, j in pairs if i < j and not (set(tris[i]) & set(tris[j]))]
        out['self_intersecting_pairs'] = len(bad)
        if bad:
            cen = np.array([verts[tris[i]].mean(0) for i, _ in bad])
            out['self_intersection_examples'] = [[round(float(v), 3) for v in c] for c in cen[:8]]
    except ImportError:
        out['self_intersecting_pairs'] = None
    return out


def run(out: str = V.WORK) -> dict:
    """out：haru_mesh.npz があり、確認画像を書くフォルダ（既定は build/recon）"""
    cams = V.load_calib()
    verts, tris = load_mesh(out)
    sil, diffs = silhouette_report(verts, tris, cams)
    print('外形の IoU', {k: v['iou'] for k, v in sil.items()}, flush=True)
    topo = topology(verts, tris)
    print('つながりと質', topo, flush=True)
    scene, cam, sun = _setup_scene(verts, tris)
    tmp = os.path.join(out, 'render')
    os.makedirs(tmp, exist_ok=True)
    for name, c in cams.items():
        ren = render_cam(scene, cam, sun, c, os.path.join(tmp, f'{name}.png'))
        diff = np.asarray(Image.fromarray(diffs[name]).resize((RENDER, RENDER), Image.NEAREST))
        row = np.concatenate([_label(_src_on_grey(name), f'art: {name}'),
                              _label(ren, f'mesh (az {c.azimuth:.1f})'),
                              _label(diff, f'IoU {sil[name]["iou"]:.4f}  red=art only  blue=mesh only')], 1)
        Image.fromarray(row).save(os.path.join(out, f'geo_check_{name}.png'))
    # 絵のない向き
    tq = cams['three_quarter']
    virt = [
        (_src_on_grey('three_quarter', mirror=True), 'art: three_quarter mirrored (= front-left if symmetric)'),
        (render_az(scene, cam, sun, -tq.azimuth, os.path.join(tmp, 'v_mirror34.png')), f'mesh az {-tq.azimuth:.1f}'),
        (render_az(scene, cam, sun, -45, os.path.join(tmp, 'v_fl45.png')), 'mesh front-left 45'),
    ]
    row1 = np.concatenate([_label(a, t) for a, t in virt], 1)
    virt2 = [
        (render_az(scene, cam, sun, 135, os.path.join(tmp, 'v_br.png')), 'mesh back-right 45 (az 135)'),
        (render_az(scene, cam, sun, -135, os.path.join(tmp, 'v_bl.png')), 'mesh back-left 45 (az -135)'),
        (render_az(scene, cam, sun, -60, os.path.join(tmp, 'v_high.png'), elev=35), 'mesh front-left, 35 deg above'),
    ]
    row2 = np.concatenate([_label(a, t) for a, t in virt2], 1)
    Image.fromarray(np.concatenate([row1, row2], 0)).save(os.path.join(out, 'geo_check_virtual.png'))
    # 近写：頭（正面・右前斜め・右真横・背面・左前 45 度）と両手（正面・右前斜め・左前 45 度）
    close = []
    for az in (0, tq.azimuth, 90, 180, -45):
        close.append(_label(render_region(scene, cam, sun, (0, 0, 1.38), 0.42, az, os.path.join(tmp, 'c.png')),
                            f'head az {az:.0f}'))
    row_h = np.concatenate(close, 1)
    close = []
    for x in (-0.43, 0.43):
        for az in (0, tq.azimuth, -45):
            close.append(_label(render_region(scene, cam, sun, (x, 0, 0.70), 0.30, az, os.path.join(tmp, 'c.png')),
                                f'{"right" if x < 0 else "left"} hand az {az:.0f}'))
    row_a = np.concatenate(close[:3], 1)
    row_b = np.concatenate(close[3:], 1)
    w = max(row_h.shape[1], row_a.shape[1])

    def padw(a):
        return np.pad(a, ((0, 0), (0, w - a.shape[1]), (0, 0)), constant_values=40)
    Image.fromarray(np.concatenate([padw(row_h), padw(row_a), padw(row_b)], 0)).save(
        os.path.join(out, 'geo_check_closeup.png'))
    return {'silhouette': sil, 'topology': topo, 'mesh_tris': int(len(tris)), 'mesh_verts': int(len(verts))}


if __name__ == '__main__':
    import json
    r = run()
    print(json.dumps(r, indent=2))
