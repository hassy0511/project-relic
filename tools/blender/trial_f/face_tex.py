"""haru_f：顔の地図（2×2 の表情）。絵（haru_face_front.png・haru_face_expressions.png）から目・眉・口だけを取り出し、
肌は 1 色にする。区画：左上 通常、右上 笑顔、左下 驚き、右下 痛み（ゲームは uv1_offset で切り替える）。

  python3 -m tools.blender.trial_f.face_tex            # build/f/tex/haru_f_face.png と確かめ用の画像
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import spec
from .textures import hex_rgb

ART = 'build/art_f/'
PPC = 40.7                  # 顔の絵：画素/cm。頭頂 146 行 = 155 cm、中心 1024 列
TOP, CX = 146, 1024
S = 0.0098                  # 絵の 1 cm → モデルの m
EYE_Z_IMG, EYE_Z = 130.3, 1.310
FACE_X, FACE_Z = (-0.14, 0.14), (1.19, 1.47)
CELL = 1024
SKIN_ART = np.array([246, 180, 135], dtype=float)


def cm_to_px(x, z):
    return CX + x * PPC, TOP + (155 - z) * PPC


def cell_window_cm():
    x0, x1 = FACE_X[0] / S, FACE_X[1] / S
    z0, z1 = EYE_Z_IMG + (FACE_Z[0] - EYE_Z) / S, EYE_Z_IMG + (FACE_Z[1] - EYE_Z) / S
    return x0, x1, z0, z1


def crop_cell(img, xform=None):
    """絵から区画の範囲を CELL の大きさで切り出す。xform：顔の絵の画素 → この絵の画素（表情の絵用）"""
    x0, x1, z0, z1 = cell_window_cm()
    l, t = cm_to_px(x0, z1)
    r, b = cm_to_px(x1, z0)
    if xform is not None:
        (l, t), (r, b) = xform(l, t), xform(r, b)
    return img.transform((CELL, CELL), Image.EXTENT, (l, t, r, b), Image.BICUBIC)


def cell_xy(x, z):
    """絵の cm → 区画の画素"""
    x0, x1, z0, z1 = cell_window_cm()
    return (x - x0) / (x1 - x0) * CELL, (z1 - z) / (z1 - z0) * CELL


def poly_mask(pts_cm, blur=0.0):
    m = Image.new('L', (CELL, CELL), 0)
    ImageDraw.Draw(m).polygon([cell_xy(*p) for p in pts_cm], fill=255)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return np.array(m, dtype=float) / 255.0


def nonskin(rgb, lo=26.0, hi=58.0):
    d = np.sqrt(((rgb - SKIN_ART) ** 2).sum(-1))
    # 肌の陰（赤みが強く暗い）は肌に数える：青の差で白目、明るさで線を拾う
    lum = rgb @ np.array([0.30, 0.59, 0.11])
    skin_lum = SKIN_ART @ np.array([0.30, 0.59, 0.11])
    dark = np.clip((skin_lum - lum - 34.0) / 40.0, 0, 1)
    white = np.clip((rgb[..., 2] - SKIN_ART[2] - 40.0) / 40.0, 0, 1)
    return np.clip(np.maximum(dark, white), 0, 1)


# 通常の顔の、目・眉・口・鼻の範囲（絵の cm）
EYE_L = [(-8.9, 131.2), (-8.2, 132.6), (-6.9, 133.3), (-5.0, 133.45), (-3.4, 132.9), (-2.35, 131.9), (-2.3, 130.4), (-2.6, 129.2),
         (-3.4, 128.0), (-4.9, 127.55), (-6.6, 127.7), (-7.8, 128.7), (-8.5, 129.8)]
EYE_R = [(-p[0] + 0.12, p[1]) for p in EYE_L]
BROW_L = [(-7.62, 134.35), (-6.7, 135.42), (-5.1, 135.35), (-3.7, 134.95), (-2.75, 134.35), (-2.48, 133.75), (-2.62, 133.3), (-3.3, 133.6),
          (-4.6, 134.2), (-5.9, 134.48), (-7.0, 134.45)]
BROW_R = [(2.2, 133.3), (2.42, 134.2), (3.5, 134.75), (4.9, 135.2), (6.3, 135.42), (7.05, 135.42), (7.85, 134.5), (7.0, 134.6),
          (5.9, 134.62), (4.6, 134.4), (3.4, 134.0), (2.6, 133.42)]
MOUTH = [(-3.3, 124.25), (3.4, 124.25), (3.4, 123.1), (-3.3, 123.1)]
NOSE = [(-1.5, 126.35), (1.4, 126.35), (1.4, 125.2), (-1.5, 125.2)]
# 顔の窓（表情の絵で目・眉・口を拾う範囲）
WINDOW = [(-9.0, 127.6), (-9.0, 133.6), (-7.9, 136.2), (-3.4, 137.2), (3.2, 137.2), (8.1, 136.2), (9.1, 133.6), (9.1, 127.6), (3.8, 121.6), (-3.8, 121.6)]
WEDGE = [(-3.9, 140.5), (3.5, 140.5), (2.3, 136.0), (0.2, 131.9), (-0.55, 130.7), (-1.2, 131.9), (-3.2, 136.0)]


def compose(rgb, alpha, skin):
    a = np.clip(alpha, 0, 1)[..., None]
    return rgb * a + skin * (1 - a)


def blush(canvas, skin):
    out = canvas.copy()
    col = np.array([238, 150, 122], dtype=float)
    yy, xx = np.mgrid[0:CELL, 0:CELL]
    for sx in (-6.4, 6.4):
        cx, cy = cell_xy(sx, 126.9)
        rx, ry = 2.3 * CELL / (cell_window_cm()[1] - cell_window_cm()[0]), 1.15 * CELL / (cell_window_cm()[1] - cell_window_cm()[0])
        g = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
        out = out * (1 - 0.30 * g[..., None]) + col * (0.30 * g[..., None])
    return out


def build(out_dir='build/f/tex', debug=True):
    skin = np.array(hex_rgb(spec.SKIN_HEX), dtype=float)
    face = Image.open(ART + 'haru_face_front.png').convert('RGB')
    c0 = np.array(crop_cell(face), dtype=float)
    ns0 = nonskin(c0)
    feat0 = np.maximum.reduce([poly_mask(EYE_L, 1.2), poly_mask(EYE_R, 1.2), poly_mask(BROW_L, 1.0), poly_mask(BROW_R, 1.0), poly_mask(MOUTH, 1.5)])
    # 鼻は淡い陰だけ（弱い閾値）
    d = np.sqrt(((c0 - SKIN_ART) ** 2).sum(-1))
    nose_a = np.clip((d - 10.0) / 30.0, 0, 1) * poly_mask(NOSE, 3.0) * 0.8
    mouth_a = np.clip((d - 22.0) / 30.0, 0, 1) * poly_mask(MOUTH, 1.5)
    a0 = np.maximum.reduce([ns0 * feat0, nose_a, mouth_a])
    a0 = np.array(Image.fromarray((a0 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), dtype=float) / 255.0
    cells = [blush(compose(c0, a0, skin), skin)]
    # 髪の覆い：通常の顔で、肌でなく、目・眉・口でもない所（少し太らせる）
    hair = ((ns0 > 0.5) & (feat0 < 0.05)).astype(np.uint8) * 255
    hair = np.array(Image.fromarray(hair).filter(ImageFilter.MaxFilter(5)), dtype=float) / 255.0
    wedge = poly_mask(WEDGE, 2.0)
    window = poly_mask(WINDOW, 4.0)
    # 表情の絵：区画ごとの頭の外接の箱を、顔の絵の箱に合わせる
    ex = Image.open(ART + 'haru_face_expressions.png').convert('RGBA')
    A = np.array(ex.getchannel('A'))
    fa = np.array(Image.open(ART + 'haru_face_front.png').convert('RGBA').getchannel('A'))
    ys, xs = np.where(fa > 128)
    fb = (xs.min(), ys.min(), xs.max(), ys.max())
    exr = ex.convert('RGB')
    dbg = []
    shift = (0.0, 0.0)
    for qi, (r0, q0) in enumerate(((0, 0), (0, 1024), (1024, 0), (1024, 1024))):
        sub = A[r0:r0 + 1024, q0:q0 + 1024]
        ys, xs = np.where(sub > 128)
        qb = (xs.min() + q0, ys.min() + r0, xs.max() + q0, ys.max() + r0)
        k = (qb[2] - qb[0]) / (fb[2] - fb[0])
        xf = lambda x, y, qb=qb, k=k, sh=shift: (qb[0] + (x - fb[0]) * k + sh[0], qb[1] + (y - fb[1]) * k + sh[1])
        ce = np.array(crop_cell(exr, xf), dtype=float)
        if qi == 0:
            # 通常の顔どうし（顔の絵と、表情の絵の左上）を重ねて、箱合わせのずれを測る。ほかの区画にも同じずれを使う
            a_ref = (ns0 > 0.5).astype(float)
            b = (nonskin(ce) > 0.5).astype(float)
            best, bs = -1.0, (0, 0)
            for dy in range(-24, 25, 2):
                for dx in range(-24, 25, 2):
                    sc = float((a_ref * np.roll(np.roll(b, dy, 0), dx, 1)).sum())
                    if sc > best:
                        best, bs = sc, (dx, dy)
            px = (cm_to_px(1, 0)[0] - cm_to_px(0, 0)[0]) * (cell_window_cm()[1] - cell_window_cm()[0]) / CELL * k
            shift = (-bs[0] * px, -bs[1] * px)
            print('expression sheet alignment shift (cell px):', bs)
            xf = lambda x, y, qb=qb, k=k, sh=shift: (qb[0] + (x - fb[0]) * k + sh[0], qb[1] + (y - fb[1]) * k + sh[1])
            ce = np.array(crop_cell(exr, xf), dtype=float)
        dbg.append(ce)
        if qi == 0:
            continue
        ns = nonskin(ce)
        de = np.sqrt(((ce - SKIN_ART) ** 2).sum(-1))
        soft = np.clip((de - 24.0) / 30.0, 0, 1)          # 口の中・歯・赤い線も拾う
        low = poly_mask([(-5.2, 126.0), (5.2, 126.0), (5.2, 121.0), (-5.2, 121.0)], 3.0)
        a = np.maximum(ns, soft * low) * window * (1 - np.clip(hair, 0, 1)) * (1 - wedge)
        # 目・眉の高さでは、細い線（髪の房の縁の残り）を消す（太さ 5 画素より細い物）
        from scipy import ndimage
        opened = ndimage.binary_dilation(ndimage.binary_erosion(a > 0.35, iterations=5), iterations=7)
        a = np.where(low > 0.5, a, a * opened)
        # 小さい切れ端（髪の縁・あごの陰）を捨てる
        lab, nlab = ndimage.label(a > 0.35)
        if nlab:
            sizes = ndimage.sum(np.ones_like(a), lab, index=np.arange(1, nlab + 1))
            keep = np.isin(lab, [i + 1 for i, sz in enumerate(sizes) if sz >= 220])
            keep = ndimage.binary_dilation(keep, iterations=3)
            a = a * keep
        a = np.array(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), dtype=float) / 255.0
        cells.append(blush(compose(ce, a, skin), skin))
    atlas = np.zeros((CELL * 2, CELL * 2, 3), dtype=float)
    for i, c in enumerate(cells):
        y, x = (i // 2) * CELL, (i % 2) * CELL
        atlas[y:y + CELL, x:x + CELL] = c
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, 'haru_f_face.png')
    Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8)).save(p)
    if debug:
        prev = np.concatenate([np.concatenate([dbg[0], dbg[1]], 1), np.concatenate([dbg[2], dbg[3]], 1)], 0)
        both = np.concatenate([prev, atlas], 1)
        Image.fromarray(np.clip(both, 0, 255).astype(np.uint8)).resize((1600, 800), Image.LANCZOS).save('build/f/face_debug.jpg', quality=88)
    print('face atlas', p)
    return p


if __name__ == '__main__':
    build()
