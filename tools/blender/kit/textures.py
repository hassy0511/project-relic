"""遺構の表面の絵（Codex W2-06 の tex_ruins_*.png、1 枚 = 2m×2m）を、ゲーム用に繰り返しのつなぎ目を消して縮める。

  .venv-blender/bin/python tools/blender/kit/textures.py [絵のフォルダ]
絵のフォルダの既定：build/intake/w2ruins（git archive origin/art/w2-ruins art/concepts/W2_back_ruins で取り出したもの）
出力：godot/assets/kit/tex/ruins_<名前>.jpg（1024×1024）

つなぎ目：spec_ruins_3d.md のとおり、生成画像の端は数学的には一致しない（RGB 平均差 4〜19/255）。
半分ずらした絵を、端に近いほど強く重ねる（中央は元の絵のまま）ことで、繰り返しても境目が出ないようにする。
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(REPO, 'godot', 'assets', 'kit', 'tex')
NAMES = ['ancient_floor', 'aged_ivory', 'sandy_floor', 'rust_grate', 'pipe_metal']
SIZE = 1024
# ずらし量（絵の幅に対する割合）。格子のある床板は格子の周期（3 枚 = 1/3）でずらして線を重ねる。
# 細かい格子（rust_grate）は周期が測れないので重ねない（格子の線が境目を隠す）
SHIFT = {'ancient_floor': 1 / 3, 'rust_grate': 0.0}


def tileable(a: np.ndarray, shift: float = 0.5, edge: float = 0.18) -> np.ndarray:
    h, w = a.shape[:2]
    if shift <= 0:
        return a
    b = np.roll(a, (int(round(h * shift)), int(round(w * shift))), axis=(0, 1))
    def ramp(n):
        t = np.minimum(np.arange(n), np.arange(n)[::-1]) / (n * edge)
        return np.clip(t, 0.0, 1.0)
    wy = ramp(h)[:, None]
    wx = ramp(w)[None, :]
    m = (np.minimum(wy, wx))[..., None]
    m = m * m * (3 - 2 * m)
    return a * m + b * (1 - m)


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'build', 'intake', 'w2ruins')
    os.makedirs(OUT, exist_ok=True)
    for n in NAMES:
        im = Image.open(os.path.join(src, f'tex_ruins_{n}.png')).convert('RGB')
        a = np.asarray(im, np.float32)
        a = tileable(a, SHIFT.get(n, 0.5))
        out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS)
        p = os.path.join(OUT, f'ruins_{n}.jpg')
        out.save(p, quality=88)
        print('書き出し', p)


if __name__ == '__main__':
    main()
