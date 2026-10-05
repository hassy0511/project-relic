"""頭を「形の部品」として作る：測った寸法の表から、左右対称のなめらかなアニメの頭（顔・あご・頭の骨）。

以前の頭（hair.skin_stack）は、あご〜ほおの左右の幅を正面の絵の肌の色の幅から読み、その上を節の表で
つないでいた。絵の肌の幅（あご）と節の表（ほお骨）の境で幅が 1cm で 1.4cm 跳び（ヤーナ：z 1.315 → 1.325）、
目の下のほおが横へ張り出した折れ目になった。さらに占有（中か外か）から距離を作ってぼかしたので、
断面の段が浅い横縞の陰になった。ユーザーの評価「ほお骨が張り出して気味が悪い」（2026-10-05）。

ここでは絵の色を読まない。頭の絵（顔の正面・頭の真横・背面・上・斜め）に 1cm の格子を重ねて測った数を、
人物ごとの表（chars/<id>.json の params "head.HEAD"）に書き、そこから作る：
  ・高さごとの断面は超楕円 |x/a|^n + |(y-cy)/b|^n = 1（前の半分と後ろの半分で b と n が別）。
  ・a（左右の半幅：あご〜ほお〜頭の骨）、yf（顔の前の端：真横の絵の輪郭、鼻を除く）、yb（後ろの端：あごの下〜首の後ろ〜
    後頭部）、nf（前の半分の指数：ほおの前の平らさ。あごの先で 2.0）を、少ない節から PCHIP でなめらかにつなぐ。
  ・あごの先と頭頂は楕円の弧で丸く閉じる（chin・top）。
  ・場は解析的に作る：ρ（断面の中の割合、面で 1）から f = (1 − ρ) / |∇ρ|（m、中が正）。占有を経ないので段ができない。
  ・左右の中心 x0 は 1 つの値（左右は厳密に鏡写し）。
耳・鼻・首は hair.py の部品（EAR・SKIN.nose・NECK）をそのまま使う。

使い方：hair.build_head・hair.part_fields_at が、"head.HEAD" があるときだけこの頭を使う（無いキャラクター
＝ハル・バートンは今までの hair.skin_stack のまま）。
  python tools/blender/recon/head.py      頭の断面の表と、正面・真横の輪郭の画像（build/<id>/head_profile.png）
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from scipy.interpolate import PchipInterpolator  # noqa: E402

from recon import char as CH  # noqa: E402

# 人物ごとの頭の寸法（再構築の座標、m）。None なら使わない（今までの頭）。
#   x0：左右の中心。z：節の高さ。a：左右の半幅。yf：前の端（-y が前）。yb：後ろの端。nf：前の半分の指数。nb：後ろの指数。
#   chin：(あごの先の下端 z, 丸めの上端 z)。top：(丸めの下端 z, 頭頂 z)。
HEAD = CH.p('head.HEAD', None)


def enabled() -> bool:
    return bool(HEAD)


def profiles(zs: np.ndarray, H: dict | None = None) -> dict:
    """高さ zs の断面の値（a, cx, cy, bf, bb, nf, nb）。あごの先と頭頂は楕円の弧で閉じる"""
    H = H or HEAD
    kz = np.asarray(H['z'], float)
    zc = np.clip(zs, kz[0], kz[-1])
    a = PchipInterpolator(kz, H['a'])(zc)
    yf = PchipInterpolator(kz, H['yf'])(zc)
    yb = PchipInterpolator(kz, H['yb'])(zc)
    nf = PchipInterpolator(kz, H['nf'])(zc)
    nb = np.full(len(zs), float(H.get('nb', 2.1)))
    (c0, c1), (t0, t1) = H['chin'], H['top']
    s_bot = np.sqrt(np.clip(1 - ((c1 - zs) / (c1 - c0)).clip(0, None) ** 2, 0, 1))
    s_top = np.sqrt(np.clip(1 - ((zs - t0) / (t1 - t0)).clip(0, None) ** 2, 0, 1))
    s = s_bot * s_top
    cy = (yf + yb) / 2
    # あごの下（丸め）では断面を前の端の側へ寄せて縮める（あごの先が後ろへ下がらない）
    w_front = np.clip((c1 - zs) / (c1 - c0), 0, 1) * float(H.get('chin_front', 0.6))
    cy_s = cy + (yf - cy) * w_front * (1 - s)
    bf = (cy - yf) * s
    bb = (yb - cy) * s
    # 縮めた断面の中心は前へ寄せた cy_s（前の端 = cy_s − bf）
    a = a * s
    inside = (zs >= c0) & (zs <= t1)
    a = np.where(inside, a, 0.0)
    return {'a': a, 'cx': np.full(len(zs), float(H['x0'])), 'cy': cy_s, 'bf': bf, 'bb': bb, 'nf': nf, 'nb': nb}


def stack(H: dict | None = None):
    """hair.Stack（2mm の高さごと）。hair.cap_stack（前髪の高さの前の端・刈り上げ）がそのまま使う"""
    from recon import hair as HR
    H = H or HEAD
    zs = np.arange(H['chin'][0], H['top'][1] + 1e-6, 0.002)
    p = profiles(zs, H)
    return HR.Stack(zs, p['a'], p['cx'], p['cy'], p['bf'], p['bb'], p['nf'], p['nb'])


def rho_grid(xs: np.ndarray, ys: np.ndarray, zs: np.ndarray, H: dict | None = None) -> np.ndarray:
    """格子 (z, x, y) の ρ（断面の中の割合。面で 1、中が 1 未満）。断面の外の高さは大きな値"""
    p = profiles(zs, H)
    out = np.full((len(zs), len(xs), len(ys)), 4.0, np.float32)
    for k in range(len(zs)):
        a = p['a'][k]
        if a < 2e-4:
            continue
        dx = np.abs(xs - p['cx'][k])[:, None] / a
        dy = (ys - p['cy'][k])[None, :]
        front = dy < 0
        b = np.maximum(np.where(front, p['bf'][k], p['bb'][k]), 2e-4)
        n = np.where(front, p['nf'][k], p['nb'][k])
        out[k] = np.minimum((dx ** n + (np.abs(dy) / b) ** n) ** (1 / n), 4.0)
    return out


def field(lo, vox: float, shape, H: dict | None = None) -> np.ndarray:
    """頭の場（m、中が正）：f = (1 − ρ) / |∇ρ|。格子は (z, x, y)、lo は (x, y, z) の角"""
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(nz) + 0.5) * vox
    r = rho_grid(xs, ys, zs, H)
    gz, gx, gy = np.gradient(r, vox)
    g = np.sqrt(gx * gx + gy * gy + gz * gz)
    f = (1.0 - r) / np.maximum(g, 1.0)
    # 遠く（ρ が大きい）は距離が不確かなので、外側を一定の負に
    return np.where(r > 2.5, np.minimum(f, -0.01), f).astype(np.float32)


def main() -> None:
    from PIL import Image, ImageDraw
    if not enabled():
        print('head.HEAD がありません（このキャラクターは今までの頭）')
        return
    H = HEAD
    zs = np.arange(H['chin'][0], H['top'][1], 0.005)
    p = profiles(zs)
    for k in range(0, len(zs), 2):
        print(f"z {zs[k]:.3f}  a {p['a'][k]:.4f}  yf {p['cy'][k] - p['bf'][k]:.4f}  yb {p['cy'][k] + p['bb'][k]:.4f}"
              f"  nf {p['nf'][k]:.2f}")
    # 輪郭の画像：正面（x-z）と真横（y-z）。1cm の格子
    S = 2000
    img = Image.new('RGB', (2 * 800, 900), 'white')
    d = ImageDraw.Draw(img)

    def P(u, z, ox):
        return ox + 400 + u * S, 900 - (z - 1.18) * S
    for ox in (0, 800):
        for i in range(-20, 21):
            u = i / 100
            d.line([P(u, 1.18, ox), P(u, 1.62, ox)], fill=(220, 220, 220) if i % 5 else (150, 150, 150))
        for j in range(0, 45):
            z = 1.18 + j / 100
            d.line([P(-0.2, z, ox), P(0.2, z, ox)], fill=(220, 220, 220) if j % 5 else (150, 150, 150))
    zz = np.arange(H['chin'][0], H['top'][1], 0.001)
    q = profiles(zz)
    d.line([P(q['cx'][i] + q['a'][i], zz[i], 0) for i in range(len(zz))], fill='black', width=3)
    d.line([P(q['cx'][i] - q['a'][i], zz[i], 0) for i in range(len(zz))], fill='black', width=3)
    d.line([P(q['cy'][i] - q['bf'][i], zz[i], 800) for i in range(len(zz))], fill='black', width=3)
    d.line([P(q['cy'][i] + q['bb'][i], zz[i], 800) for i in range(len(zz))], fill='black', width=3)
    out = os.path.join(CH.REPO, CH.CFG['work'], 'head_profile.png')
    img.save(out)
    print(out)


if __name__ == '__main__':
    main()
