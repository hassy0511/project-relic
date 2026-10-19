"""ジャンク屋の絵を src に置く（絵のブランチから取り出した build/junker/art から）。

- 全身の真横の絵は、ファイル名と顔の向きが逆（spec_townsfolk_3d_add.md。店主と同じ）：
    junker_3d_side_right.png は顔が画像の左 → 方位角 −90（本人の左から見た図）として side_left に、
    junker_3d_side_left.png は顔が画像の右 → 方位角 +90 として side_right に使う。
  腕なしの真横（顔が画像の左）は左右反転して side_right_noarms（+90）に。
- 左前 45 度は無いので、右前 45 度を左右反転（ほぼ左右対称の人物。ポケットの道具の違いは部品で作る）。
- 真横の絵の、胸の前に下がるルーペ（z 1.01〜1.14、胸の面より前）を外形から外す（_cut.png、不透明度だけを変える）。
  外形に残すと体の土台の胸が前へ 6cm ふくらみ、ルーペの部品がこぶの上に載る。ルーペ・首ひもは部品。
usage: python3 tools/blender/recon/chars/junker_prep.py build/junker/art build/junker/src
  （art は絵のブランチの art/concepts/W2_townsfolk/ の junker_*・spec*.md を取り出したフォルダ。views の段の前に 1 回）
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageOps

ART, SRC = sys.argv[1], sys.argv[2]
os.makedirs(SRC, exist_ok=True)
for f in os.listdir(ART):
    if f.startswith('junker_') or f.startswith('spec'):
        shutil.copy(os.path.join(ART, f), os.path.join(SRC, f))

for src, dst in (('junker_3d_side_right_noarms.png', 'junker_3d_side_right_noarms_mirror.png'),
                 ('junker_3d_front_right45.png', 'junker_3d_front_left45_mirror.png')):
    ImageOps.mirror(Image.open(os.path.join(ART, src))).save(os.path.join(SRC, dst))

PPM, V0 = 1147.7, 1914.5
LOUPE_Z = (1.005, 1.145)


def cut_loupe(fname, out, sgn, fwd_max, u0=1023.5):
    """sgn：顔が画像の右なら +1（前 = 画像の右）、左なら −1。fwd_max より前（胴の軸から）を外す"""
    im = np.array(Image.open(os.path.join(ART, fname)).convert('RGBA'))
    u = np.arange(im.shape[1]) + 0.5
    fwd = (u - u0) / PPM * sgn
    n = 0
    for v in range(im.shape[0]):
        z = (V0 - (v + 0.5)) / PPM
        if not (LOUPE_Z[0] <= z <= LOUPE_Z[1]):
            continue
        cut = (fwd > fwd_max) & (im[v, :, 3] > 0)
        n += int(cut.sum())
        im[v, cut, 3] = 0
    Image.fromarray(im).save(os.path.join(SRC, out))
    print(out, 'loupe cut px', n)


# 胸の前の面：顔が右の絵は z 1.00 で前 0.129（ルーペが胸に重なる）、顔が左の絵は 1.05 で 0.108（ルーペは 0.114〜0.158 で離れる）
cut_loupe('junker_3d_side_left.png', 'junker_3d_side_left_cut.png', 1.0, 0.125)
cut_loupe('junker_3d_side_right.png', 'junker_3d_side_right_cut.png', -1.0, 0.112)
