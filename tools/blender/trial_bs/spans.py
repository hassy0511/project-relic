"""絵とモデルの影の、高さごとの左右の端（m）を並べる（比べの輪の「違いの一覧」を数で出す）。

  .venv-blender/bin/python tools/blender/trial_bs/spans.py <pass> <view> [rows...]
"""
import os
import sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import bpy  # noqa: F401（mathutils を読むため）
import proportions as P

IMG = {'front': 'haru_3d_front.png', 'back': 'haru_3d_back.png', 'side_right': 'haru_3d_side_right.png',
       'three_quarter': 'haru_3d_three_quarter.png', 'side_left': 'haru_3d_side_left.png', 'front_left45': 'haru_3d_front_left45.png'}


def segs(row):
    xs = np.where(row)[0]
    if not len(xs):
        return []
    out = []
    s = p = xs[0]
    for x in xs[1:]:
        if x != p + 1:
            out.append((s, p))
            s = x
        p = x
    out.append((s, p))
    return [(a, b) for a, b in out if b - a > 2]


def main(tag, view, zs):
    art = np.array(Image.open(os.path.join(ROOT, 'build', 'art', IMG[view])).convert('RGBA').resize((1024, 1024)))[..., 3] > 128
    ren = np.array(Image.open(os.path.join(ROOT, 'build', 'trial_bs', 'cmp', tag, f'{view}_render.png')).convert('RGBA'))[..., 3] > 128
    s = P.PX * 2
    for z in zs:
        y = int(round((P.FEET_PX / 2) - z / s))
        f = lambda sg: [(round((a - 512) * s, 3), round((b - 512) * s, 3)) for a, b in sg]
        print(f'z {z:.2f}  絵 {f(segs(art[y]))}\n         模 {f(segs(ren[y]))}')


if __name__ == '__main__':
    tag, view = sys.argv[1], sys.argv[2]
    zs = [float(x) for x in sys.argv[3:]] or [1.50, 1.40, 1.30, 1.10, 1.00, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10, 0.03]
    main(tag, view, zs)
