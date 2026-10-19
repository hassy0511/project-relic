"""店主の絵を src に置く（絵のブランチから取り出した build/shopkeeper/art から）。

- 全身の真横の絵は、ファイル名と顔の向きが逆（spec_townsfolk_3d_add.md）：
    shopkeeper_3d_side_right.png は顔が画像の左 → 方位角 −90（本人の左から見た図）として side_left に、
    shopkeeper_3d_side_left.png は顔が画像の右 → 方位角 +90 として side_right に使う。
  腕なしの真横（顔が画像の左）は左右反転して side_right_noarms（+90）に。
- 左前 45 度は無いので、右前 45 度を左右反転（左右対称の人物）。
- 形の段の外形用に、正面と side_right（顔が右）の絵のスカートの範囲（z 0.20〜0.95）を、脚と腰の外形に置き換えた絵
  （_legs.png、不透明度だけを変える）を作る。スカート・前掛けは部品で作り、体の土台は脚にする。
usage: python3 tools/blender/recon/chars/shopkeeper_prep.py build/shopkeeper/art build/shopkeeper/src
  （art は絵のブランチの art/concepts/W2_townsfolk/ の shopkeeper_*・spec*.md を取り出したフォルダ。views の段の前に 1 回）
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageOps

ART, SRC = sys.argv[1], sys.argv[2]
os.makedirs(SRC, exist_ok=True)
for f in os.listdir(ART):
    if f.startswith('shopkeeper_') or f.startswith('spec'):
        shutil.copy(os.path.join(ART, f), os.path.join(SRC, f))

for src, dst in (('shopkeeper_3d_side_right_noarms.png', 'shopkeeper_3d_side_right_noarms_mirror.png'),
                 ('shopkeeper_3d_front_right45.png', 'shopkeeper_3d_front_left45_mirror.png')):
    ImageOps.mirror(Image.open(os.path.join(ART, src))).save(os.path.join(SRC, dst))

PPM, V0 = 1147.7, 1915.0
Z0, Z1 = 0.20, 0.95


def zrow(v):
    return (V0 - (v + 0.5)) / PPM


# 正面：脚（中心 xc・半幅 w）→ 股（0.72）より上は腰の 1 つの帯（半幅 hw）
LEG = dict(z=[0.20, 0.25, 0.35, 0.45, 0.55, 0.62, 0.68, 0.72],
           xc=[0.148, 0.145, 0.137, 0.127, 0.114, 0.103, 0.090, 0.080],
           w=[0.036, 0.038, 0.043, 0.050, 0.057, 0.063, 0.072, 0.080])
HIP = dict(z=[0.72, 0.80, 0.88, 0.95], hw=[0.160, 0.165, 0.150, 0.128])
# 真横（顔が右、方位角 +90。画像の右 = 前 = −y）：前の端・後ろの端（y）
SIDE = dict(z=[0.20, 0.25, 0.35, 0.45, 0.55, 0.62, 0.70, 0.80, 0.88, 0.95],
            yf=[-0.020, -0.024, -0.032, -0.042, -0.052, -0.060, -0.070, -0.080, -0.083, -0.082],
            yb=[0.071, 0.074, 0.079, 0.085, 0.092, 0.100, 0.110, 0.122, 0.116, 0.104])


def edit(fname, out, kind, u0, sgn=1.0):
    im = np.array(Image.open(os.path.join(ART, fname)).convert('RGBA'))
    a = im[..., 3]
    H, W = a.shape
    u = np.arange(W) + 0.5
    for v in range(H):
        z = zrow(v)
        if not (Z0 <= z <= Z1):
            continue
        h = (u - u0) / PPM
        if kind == 'front':
            # 手・手首の帯（z 0.62〜0.83、|x| 0.30 より外）・肘の帯（z 0.90〜0.98、|x| 0.24 より外）は残す
            win = np.abs(h) < (0.335 if z < 0.55 else (0.29 if z < 0.80 else 0.235))
            if z < 0.72:
                xc, w = np.interp(z, LEG['z'], LEG['xc']), np.interp(z, LEG['z'], LEG['w'])
                keep = np.abs(np.abs(h) - xc) <= w
            else:
                keep = np.abs(h) <= np.interp(z, HIP['z'], HIP['hw'])
        else:
            win = np.abs(h) < 0.32
            y = -h * sgn
            keep = (y >= np.interp(z, SIDE['z'], SIDE['yf'])) & (y <= np.interp(z, SIDE['z'], SIDE['yb']))
        clear = win & ~keep
        a[v, clear] = 0
    im[..., 3] = a
    Image.fromarray(im).save(os.path.join(SRC, out))
    # 縁の確かめ：z 0.205（すねの見える高さ）の元の外形の区間
    a0 = np.asarray(Image.open(os.path.join(ART, fname)))[..., 3] >= 128
    vv = int(round(V0 - 0.205 * PPM))
    row = a0[vv]
    d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
    runs = list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))
    print(out, 'z0.205 runs (m):', [(round((s - u0) / PPM, 3), round((e - u0) / PPM, 3)) for s, e in runs])


edit('shopkeeper_3d_front.png', 'shopkeeper_3d_front_legs.png', 'front', 1022.5)
edit('shopkeeper_3d_side_left.png', 'shopkeeper_3d_side_left_legs.png', 'side', 1023.5)
# 顔が画像の左（方位角 −90。画像の右 = 後ろ = +y）
edit('shopkeeper_3d_side_right.png', 'shopkeeper_3d_side_right_legs.png', 'side', 1023.5, -1.0)

# 真横の絵の頭：額・顔の前に垂れる前髪の房の先（z 1.30〜1.44 で顔の前 1〜4cm）を外形から外す。髪の帽子（外形から作る）が顔の前まで
# 張り出すと、顔の材質（texture.FACE_SKIN_ONLY：帽子の場の上の三角形は顔にしない）から額・眉・目の上半分が外れた（2 周目）。
# 頭の寸法の表（head.HEAD の yf）の前 4mm で切り、生え際（1.405）より上は前髪のふくらみの分だけゆるめる。前髪は部品の房
HEAD_YF = dict(z=[1.228, 1.236, 1.25, 1.265, 1.28, 1.295, 1.31, 1.33, 1.35, 1.37, 1.39, 1.41, 1.43, 1.45, 1.47],
               yf=[-0.070, -0.100, -0.111, -0.117, -0.120, -0.121, -0.120, -0.116, -0.116, -0.118, -0.116, -0.105, -0.090, -0.072, -0.048])


def head_clip(fname, u0, ppm, sgn):
    path = os.path.join(SRC, fname)
    im = np.array(Image.open(path).convert('RGBA'))
    u = np.arange(im.shape[1]) + 0.5
    n = 0
    for v in range(im.shape[0]):
        z = (V0 - (v + 0.5)) / ppm
        if not (1.30 <= z <= 1.44):
            continue
        y = -(u - u0) / ppm * sgn
        t = min(1.0, max(0.0, (z - 1.405) / 0.035))
        lim = np.interp(z, HEAD_YF['z'], HEAD_YF['yf']) - 0.004 - 0.015 * t * t * (3 - 2 * t)
        cut = (y < lim) & (im[v, :, 3] > 0)
        n += int(cut.sum())
        im[v, cut, 3] = 0
    Image.fromarray(im).save(path)
    print(fname, 'head clip px', n)


# 較正（calib.json）の値：side_right（顔が右）ppm 1158.7・u0 1017.0、side_left（顔が左）ppm 1149.7・u0 1030.5
head_clip('shopkeeper_3d_side_left_legs.png', 1017.0, 1158.7, 1.0)
head_clip('shopkeeper_3d_side_right_legs.png', 1030.5, 1149.7, -1.0)


def temple_clip(fname, u0, ppm, x0=0.0105):
    """正面の絵のこめかみ・ほおの横に垂れる房（z 1.28〜1.44、|x−x0| 0.088 より外）を外形から外す（2 周目）。
    帽子（外形から作る髪の土台）の幅がこの房で広がり、目と眉の外の端 5mm が帽子の場に入って顔の材質から外れた。耳は部品（hair.EAR）"""
    path = os.path.join(SRC, fname)
    im = np.array(Image.open(path).convert('RGBA'))
    u = np.arange(im.shape[1]) + 0.5
    xr = np.abs((u - u0) / ppm - x0)
    n = 0
    for v in range(im.shape[0]):
        z = (V0 - (v + 0.5)) / ppm
        if not (1.28 <= z <= 1.44):
            continue
        cut = (xr > 0.088) & (xr < 0.30) & (im[v, :, 3] > 0)
        n += int(cut.sum())
        im[v, cut, 3] = 0
    Image.fromarray(im).save(path)
    print(fname, 'temple clip px', n)


# 較正の値：front ppm 1148.4・u0 1019.5
temple_clip('shopkeeper_3d_front_legs.png', 1019.5, 1148.4)
