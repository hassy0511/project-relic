"""面の質の確認：なめる光（斜め上の横から浅い角度で当てる強い光＋弱い補助の光）で、灰色のメッシュを描く。

正面から均一に当てる光では、面の段・横筋・こぶが見えない。なめる光だと、横筋は明暗の縞に、
こぶは影の点になってはっきり見える。carve.py の最後で呼ばれる（単独でも動く）。

  python tools/blender/recon/surfcheck.py                   build/recon/haru_mesh.npz を描く
  python tools/blender/recon/surfcheck.py --mesh X.npz --prefix build/recon/exp/sc   別のメッシュ・出力先

出力（build/recon/）：
  surf_check_body.png   全身。方位角 0/45/90/135/180/-135/-90/-45 度（0 = 正面、90 = 本人の右）と、
                        左前の上から・右後ろの上から（35 度見下ろす）・真上から・右前の下から（30 度見上げる）
  surf_check_head.png   頭と髪の近写（8 方位＋左前の見下ろし＋後ろの見下ろし＋真上＋下から）
  surf_check_face.png   顔の近写（正面・左右の斜め・横・上下から）
  surf_check_sections.png  水平の断面（頭 6 つ、胴・腕 3 つ、脚 3 つ。前 = -Y が上）
  surf_check_torso.png  胴（前・後ろ・斜め後ろ・肩の上からの見下ろし）
  surf_check_arms.png   両前腕（左の籠手と右の前腕。外側・後ろ・前）
  surf_check_hands.png  両手（前・後ろ・外側・内側）
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from recon import views as V  # noqa: E402

BG = 40   # 背景の灰色


def setup(verts: np.ndarray, tris: np.ndarray, samples: int = 16):
    """灰色のメッシュ・正投影カメラ・なめる光（主）と補助の光の場面を作る"""
    import bpy
    from lib import common as C
    C.reset_scene()
    me = bpy.data.meshes.new('surf')
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    me.loops.add(len(tris) * 3)
    me.loops.foreach_set('vertex_index', tris.astype(np.int32).ravel())
    me.polygons.add(len(tris))
    me.polygons.foreach_set('loop_start', (np.arange(len(tris)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(tris), bool))
    obj = bpy.data.objects.new('surf', me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(C.material('surf_grey', (0.6, 0.6, 0.6), roughness=0.85))

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 2
    scene.render.use_persistent_data = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('surf_world')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.06
    cam_data = bpy.data.cameras.new('surf_cam')
    cam_data.type = 'ORTHO'
    cam_data.clip_end = 20
    cam = bpy.data.objects.new('surf_cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    lights = []
    for name, energy, ang in (('key', 3.2, 3.0), ('fill', 0.45, 20.0)):
        ld = bpy.data.lights.new('surf_' + name, 'SUN')
        ld.energy = energy
        ld.angle = math.radians(ang)
        lo = bpy.data.objects.new('surf_' + name, ld)
        scene.collection.objects.link(lo)
        lights.append(lo)
    return scene, cam, lights


def shot(scene, cam, lights, center, size: float, az: float, elev: float, res: int, path: str,
         key_side: float = 1.0) -> np.ndarray:
    """方位角 az（度、0 = 正面、90 = 本人の右）・見下ろし elev（度）から、幅 size m の範囲を描く。

    主の光は画像の右上（key_side=-1 で左上）から、視線とほぼ直角に近い浅い角度で当てる。
    """
    import bpy
    from mathutils import Matrix, Vector
    a, e = math.radians(az), math.radians(elev)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e))).normalized()
    r = Vector((math.cos(a), -math.sin(a), 0.0)).normalized()
    up = r.cross(d).normalized()
    rot = Matrix((r, up, -d)).transposed()
    cam.matrix_world = Matrix.Translation(Vector(center) - d * 5.0) @ rot.to_4x4()
    cam.data.ortho_scale = size
    # 主の光：上 1.3・横 1.0・手前 0.25 の向きから（視線と約 80 度）。補助：反対の横・手前・少し下から
    key = (up * 1.3 + r * key_side * 1.0 - d * 0.25).normalized()
    fill = (-r * key_side * 1.0 - d * 0.9 - up * 0.2).normalized()
    for lo, ldir in zip(lights, (key, fill)):
        # 太陽の光は自分の -Z の向きに進む → +Z を光の来る向きへ
        lo.matrix_world = ldir.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32)
    al = img[..., 3:4] / 255
    return (img[..., :3] * al + BG * (1 - al)).astype(np.uint8)


def _label(arr: np.ndarray, text: str) -> np.ndarray:
    im = Image.fromarray(arr)
    ImageDraw.Draw(im).text((8, 6), text, fill=(255, 255, 0))
    return np.asarray(im)


def _grid(imgs: list[np.ndarray], cols: int) -> np.ndarray:
    h, w = imgs[0].shape[:2]
    rows = []
    for i in range(0, len(imgs), cols):
        row = imgs[i:i + cols]
        row += [np.full((h, w, 3), BG, np.uint8)] * (cols - len(row))
        rows.append(np.concatenate(row, 1))
    return np.concatenate(rows, 0)


# 近写の範囲（中心・幅）。前腕と手の位置は A ポーズの絵から（本人の左 = +X）
HEAD = ((0.0, 0.0, 1.36), 0.46)
FACE = ((0.0, -0.02, 1.32), 0.30)
TORSO = ((0.0, 0.0, 0.98), 0.62)
FOREARM_L = ((0.30, 0.0, 0.83), 0.34)
FOREARM_R = ((-0.30, 0.0, 0.83), 0.34)
HAND_L = ((0.41, 0.0, 0.69), 0.22)
HAND_R = ((-0.41, 0.0, 0.69), 0.22)


def section_segments(verts: np.ndarray, tris: np.ndarray, z: float) -> np.ndarray:
    """高さ z の水平面でメッシュを切った線分 (n, 2, 2)（x, y）"""
    zz = verts[tris][:, :, 2]
    sel = tris[(zz.min(1) < z) & (zz.max(1) > z)]
    P = verts[sel]
    out = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = P[:, i], P[:, j]
        cross = (a[:, 2] - z) * (b[:, 2] - z) < 0
        t = (z - a[:, 2]) / np.where(cross, b[:, 2] - a[:, 2], 1.0)
        out.append((a + t[:, None] * (b - a))[:, :2] * np.where(cross, 1, np.nan)[:, None])
    Q = np.stack(out, 1)                                  # (n, 3, 2)、交わらない辺は nan
    segs = []
    for q in Q:
        pts = q[~np.isnan(q[:, 0])]
        if len(pts) == 2:
            segs.append(pts)
    return np.array(segs).reshape(-1, 2, 2)


def sections_image(verts: np.ndarray, tris: np.ndarray, path: str, cell: int = 420) -> None:
    """水平の断面の画像（前 = -Y が画像の上、本人の左 = +X が右）"""
    rows = [
        [(z, (0.0, 0.03), 0.42) for z in (1.22, 1.28, 1.34, 1.40, 1.46, 1.52)],
        [(1.08, (0.0, 0.0), 0.9), (1.00, (0.0, 0.0), 0.9), (0.84, (0.0, 0.0), 0.9),
         (0.66, (0.0, 0.0), 0.9), (0.40, (0.0, 0.0), 0.5), (0.14, (0.0, 0.0), 0.5)],
    ]
    img = Image.new('RGB', (cell * 6, cell * 2), (BG, BG, BG))
    dr = ImageDraw.Draw(img)
    for r, row in enumerate(rows):
        for c, (z, (cx, cy), size) in enumerate(row):
            ox, oy = c * cell, r * cell
            k = cell / size
            dr.rectangle([ox, oy, ox + cell - 1, oy + cell - 1], outline=(70, 70, 70))
            for a, b in section_segments(verts, tris, z):
                dr.line([(ox + cell / 2 + (a[0] - cx) * k, oy + cell / 2 + (a[1] - cy) * k),
                         (ox + cell / 2 + (b[0] - cx) * k, oy + cell / 2 + (b[1] - cy) * k)], fill=(235, 235, 235), width=2)
            dr.text((ox + 6, oy + 5), f'z={z:.2f}  box {size * 100:.0f}cm  front(-Y) up', fill=(255, 255, 0))
    img.save(path)


def run(verts: np.ndarray, tris: np.ndarray, prefix: str, res: int = 640, samples: int = 16,
        which: tuple[str, ...] = ('body', 'head', 'face', 'torso', 'arms', 'hands', 'sections')) -> list[str]:
    """確認画像を描いて <prefix>_<名前>.png に書く。書いたファイルの一覧を返す"""
    scene, cam, lights = setup(verts, tris, samples)
    tmp = os.path.join(os.path.dirname(prefix) or '.', 'render')
    os.makedirs(tmp, exist_ok=True)
    tp = os.path.join(tmp, 'surf.png')
    out = []

    def save(name, imgs, cols):
        p = f'{prefix}_{name}.png'
        Image.fromarray(_grid(imgs, cols)).save(p)
        out.append(p)

    if 'body' in which:
        imgs = []
        for az, el in ((0, 0), (45, 0), (90, 0), (135, 0), (180, 0), (-135, 0), (-90, 0), (-45, 0),
                       (-60, 35), (150, 35), (0, 89), (30, -30)):
            side = -1.0 if az > 0 else 1.0   # 光は、見えている側の反対（体の輪郭の内側を浅くなめる）
            img = shot(scene, cam, lights, (0, 0, V.HEIGHT / 2 + 0.01), 1.72, az, el, res, tp, side)
            imgs.append(_label(img, f'az {az}  elev {el}'))
        save('body', imgs, 6)
    if 'head' in which:
        imgs = []
        for az, el in ((0, 0), (45, 0), (90, 0), (135, 0), (180, 0), (-135, 0), (-90, 0), (-45, 0),
                       (-30, 60), (160, 50), (0, 89), (20, -35)):
            img = shot(scene, cam, lights, HEAD[0], HEAD[1], az, el, res // 2 * 1 + res // 4, tp)
            imgs.append(_label(img, f'head az {az} elev {el}'))
        save('head', imgs, 6)
    if 'face' in which:
        imgs = []
        for az, el in ((0, 0), (30, 0), (-30, 0), (-70, 0), (0, 30), (0, -25)):
            img = shot(scene, cam, lights, FACE[0], FACE[1], az, el, res // 2 + res // 4, tp, 1.0 if az <= 0 else -1.0)
            imgs.append(_label(img, f'face az {az} elev {el}'))
        save('face', imgs, 6)
    if 'sections' in which:
        p = f'{prefix}_sections.png'
        sections_image(verts, tris, p)
        out.append(p)
    if 'torso' in which:
        imgs = []
        for az, el, s in ((0, 0, 1), (-45, 0, 1), (180, 0, 1), (150, 0, -1), (-150, 0, 1),
                          (90, 0, -1), (-60, 40, 1), (160, 40, -1)):
            img = shot(scene, cam, lights, TORSO[0], TORSO[1], az, el, res // 2 + res // 4, tp, s)
            imgs.append(_label(img, f'torso az {az} elev {el}'))
        save('torso', imgs, 4)
    if 'arms' in which:
        imgs = []
        for (c, w), nm in ((FOREARM_L, 'L gauntlet'), (FOREARM_R, 'R forearm')):
            outer = -90 if c[0] > 0 else 90
            for az in (0, outer, 180, outer * 1.5, -outer * 0.5):
                img = shot(scene, cam, lights, c, w, az, 0, res // 2, tp, 1.0 if az <= 0 else -1.0)
                imgs.append(_label(img, f'{nm} az {az:.0f}'))
        save('arms', imgs, 5)
    if 'hands' in which:
        imgs = []
        for (c, w), nm in ((HAND_L, 'L hand'), (HAND_R, 'R hand')):
            outer = -90 if c[0] > 0 else 90
            for az in (0, outer, 180, -outer, outer * 0.5):
                img = shot(scene, cam, lights, c, w, az, 0, res // 2, tp, 1.0 if az <= 0 else -1.0)
                imgs.append(_label(img, f'{nm} az {az:.0f}'))
        save('hands', imgs, 5)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--mesh', default=os.path.join(V.WORK, f'{V.CH.ID}_mesh.npz'))
    ap.add_argument('--prefix', default=os.path.join(V.WORK, 'surf_check'))
    ap.add_argument('--res', type=int, default=640)
    ap.add_argument('--samples', type=int, default=16)
    ap.add_argument('--only', default='', help='body,head,face,torso,arms,hands,sections のうち描くもの（カンマ区切り）')
    args = ap.parse_args()
    d = np.load(args.mesh)
    which = tuple(args.only.split(',')) if args.only else ('body', 'head', 'face', 'torso', 'arms', 'hands', 'sections')
    for p in run(d['verts'], d['tris'], args.prefix, args.res, args.samples, which):
        print(p)


if __name__ == '__main__':
    main()
