"""町の遠景：オルドの体（背の外殻・持ち上がった頭と尾・4 対の脚）と砂漠の床（ordo_far）、空の絵（sky_*.jpg）。

ordo_far：W2-04 spec_ordo_3d.md の寸法（全長 400 m・幅 135 m（町の部屋の外の縁が近く見えるよう 120 m に詰めた）・背の歩行面から地面まで約 120 m・脚 8 本は前から 15・38・62・85 %、
肩・膝・足首は真鍮の円板）。遠くから見る影絵なので、形は箱と回転体だけ、材質は白磁・黒鉛・真鍮・琥珀（頭の細い窓）・砂。
原点 = 町の真ん中の背の面（y=0）。+Z が頭（町の上の段の向き）。中段の部屋では y=-6.5 に置く（下の段の床の下）。

sky_day / sky_night / sky_dusk：bg_desert_*.png（4096×1024、水平に一周、地平線はほぼ中央）を、Godot の
PanoramaSkyMaterial 用の正距円筒（4096×2048）の真ん中の帯に置き、上は空の色、下は砂の色でなだらかに埋める。
"""
from __future__ import annotations

import math
import os

import numpy as np

from town_geo import Part, Piece, _orient, _orient_dir, beam, box, boxb, cyl, lathe

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
INTAKE = os.path.join(REPO, 'build', 'intake', 'w2town')


def _loft(sections: list[tuple[float, list[tuple[float, float]]]]) -> Piece:
    """z ごとの断面 [(x, y)...]（同じ点の数・凸）をつないだ閉じた形"""
    n = len(sections[0][1])
    v, f = [], []
    for z, poly in sections:
        v += [(x, y, z) for x, y in poly]
    for i in range(len(sections) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            f.append([a, b, b + n, a + n])
    f.append(list(range(n))[::-1])
    f.append([len(sections) * n - n + k for k in range(n)])
    return _orient(Piece(np.array(v, float), f))


def _rise(z: float) -> float:
    """背の面の持ち上がり（頭 +Z は 34 m、尾 -Z は 22 m まで、端の 60 m でなめらかに）"""
    if z > 140:
        t = (z - 140) / 60
        return 34 * t * t
    if z < -140:
        t = (-140 - z) / 60
        return 22 * t * t
    return 0.0


def _narrow(z: float) -> float:
    if abs(z) > 160:
        t = (abs(z) - 160) / 40
        return 1.0 - 0.28 * t * t
    return 1.0


def ordo_far() -> Part:
    p = Part('ordo_far')
    zs = list(np.linspace(-200, 200, 33))
    hull, under = [], []
    for z in zs:
        r, k = _rise(z), _narrow(z)
        hull.append((z, [(-52 * k, r), (52 * k, r), (60 * k, r - 5), (60 * k, r - 22), (55 * k, r - 28), (-55 * k, r - 28), (-60 * k, r - 22), (-60 * k, r - 5)]))
        under.append((z, [(-48 * k, r - 27), (48 * k, r - 27), (44 * k, r - 38), (-44 * k, r - 38)]))
    p.add('hull', _loft(hull))
    p.add('graphite', _loft(under))
    # 外殻の継ぎ目（側面の黒鉛の帯、40 m ごとの縦の帯）と、背の縁の真鍮の帯
    for sx in (-1, 1):
        for z in np.arange(-180, 181, 40):
            r = _rise(z)
            p.add('graphite', boxb(sx * 60.2 - 0.8, sx * 60.2 + 0.8, r - 22, r - 5, z - 1.2, z + 1.2))
        p.add('graphite', boxb(sx * 60.4 - 0.6, sx * 60.4 + 0.6, -12, -10, -140, 140))
    # 頭の面（+Z の端）：琥珀の細い窓（航行スリット）
    zf = 200
    p.add('graphite', boxb(-26, 26, _rise(zf) - 22, _rise(zf) - 6, zf - 3, zf + 1.5))
    p.add('amber', boxb(-20, 20, _rise(zf) - 14.5, _rise(zf) - 12.5, zf + 1.4, zf + 2.0))
    # 尾の禁足扉
    zt = -200
    p.add('graphite', boxb(-16, 16, _rise(zt) - 28, _rise(zt) + 2, zt - 1.5, zt + 3))
    p.add('brass', boxb(-12, 12, _rise(zt) - 26, _rise(zt) - 1, zt - 2.0, zt))
    # 脚：4 対（前から 15・38・62・85 %）
    for zc in (140.0, 48.0, -48.0, -140.0):
        for sx in (-1, 1):
            _leg(p, sx, zc)
    _back(p)
    # 砂の床は作らない（霞のかかった平らな面は壁のように見える。下は空の絵の下の帯＝砂丘と遺構が見える）
    return p


def _leg(p: Part, sx: float, zc: float):
    sh = np.array([sx * 61.0, -14.0, zc])
    kn = np.array([sx * 80.0, -62.0, zc + 6])
    an = np.array([sx * 76.0, -110.0, zc])
    p.add('brass', cyl(sh - [sx * 2, 0, 0], sh + [sx * 3.5, 0, 0], 10.0, 16))
    p.add('graphite', cyl(sh + [sx * 3.5, 0, 0], sh + [sx * 4.5, 0, 0], 5.0, 12))
    p.add('ivory', beam(sh + [sx * 4, 0, 0], kn, 10.0, 11.0, up=(0, 0, 1)))
    p.add('graphite', beam(sh + [sx * 6.5, -6, 0], kn + [sx * 2.5, 4, 0], 4.0, 13.0, up=(0, 0, 1)))
    p.add('brass', cyl(kn - [sx * 6, 0, 0], kn + [sx * 6, 0, 0], 7.0, 14))
    p.add('ivory', beam(kn, an, 9.0, 10.0, up=(0, 0, 1)))
    p.add('graphite', beam(kn + [sx * 4.5, -4, 0], an + [sx * 4.5, 6, 0], 3.0, 10.0, up=(0, 0, 1)))
    p.add('brass', cyl(an - [sx * 5.5, 0, 0], an + [sx * 5.5, 0, 0], 5.5, 12))
    # 足：前後に長い（38 × 24 m）
    p.add('ivory', boxb(an[0] - 12, an[0] + 12, -122, -114, zc - 19, zc + 19))
    p.add('graphite', boxb(an[0] - 12.5, an[0] + 12.5, -122, -119, zc - 19.5, zc + 19.5))
    p.add('ivory', boxb(an[0] - 7, an[0] + 7, -114, -108, zc - 9, zc + 9))
    p.add('amber', boxb(an[0] - 8, an[0] + 8, -116.5, -115.5, zc + 19, zc + 19.4))


def _strip(z0, z1, x0, x1, y0, y1):
    """背の面の上に沿った帯（z0〜z1、横 x0〜x1、背の面からの高さ y0〜y1）。持ち上がった頭・尾（|z| > 140）では 5 m ごとに面に沿って曲がる"""
    knots = [z for z in list(np.arange(-200.0, -139.0, 5.0)) + list(np.arange(140.0, 201.0, 5.0)) if z0 < z < z1]
    secs = []
    for z in sorted({z0, z1, *knots}):
        r, k = _rise(z), _narrow(z)
        secs.append((z, [(x0 * k, r + y0), (x1 * k, r + y0), (x1 * k, r + y1), (x0 * k, r + y1)]))
    return _loft(secs)


def _back(p: Part):
    """背の上（町の部屋の南の胸壁から見える、下の段の家並みの向こう〜持ち上がった尾）。
    前は背の面が何も無い白い板のまま尾へ持ち上がり、胸壁から南を見ると、格子の模様の大きな坂（と上の箱 1 つ）に見えた。
    絵（ordo_3d_side_right・ordo_3d_top）：背の両側の縁は外殻の高い縁（舷）、町は尾の手前まで続き、町の端に黒鉛の塔、
    持ち上がった尾の上は白磁の板の継ぎ目と、禁足扉の機械の箱（琥珀の細い灯）"""
    # 両側の縁（舷）：背の縁の斜面（|x| 54〜58.5）に立つ、背の面より 2.5 m 高い外殻の低い壁。頭から尾まで、持ち上がりに沿う。
    # 上の両側の縁に黒鉛の細い笠木、内側に 20 m ごとの付け柱。町の部屋（東西の壁 |x| 49、上 1.2 m）の外 5 m・4.7 m 下で、広場から見て壁にならない高さ
    for sx in (-1, 1):
        xa, xb = sorted((sx * 54.0, sx * 58.5))
        p.add('hull', _strip(-198, 198, xa, xb, -6.0, 2.5))
        for a, b in ((53.85, 54.35), (58.0, 58.65)):        # 笠木は内と外の縁の細い帯だけ（広い黒鉛の板は、東西の壁の外に重い黒い帯に見えた）
            xa, xb = sorted((sx * a, sx * b))
            p.add('graphite', _strip(-198, 198, xa, xb, 2.45, 2.9))
        for z in np.arange(-180, 181, 20.0):
            xa, xb = sorted((sx * 53.5, sx * 54.1))
            p.add('graphite', _strip(z - 1.0, z + 1.0, xa, xb, -0.5, 2.8))
    # 真ん中の大通り（絵の上から見た黒い線）：町の部屋の向こう（z < -58）から尾の上まで
    p.add('graphite', _strip(-196, -58, -1.6, 1.6, -0.3, 0.35))
    # 持ち上がった尾の上の板の継ぎ目（横の黒鉛の帯、8 m ごと）と、縦の継ぎ目
    for z in np.arange(-192, -139, 8.0):
        p.add('graphite', _strip(z - 0.6, z + 0.6, -50.5, 50.5, -0.3, 0.3))
    for x in (-34.0, -17.0, 17.0, 34.0):
        p.add('graphite', _strip(-196, -140, x - 0.5, x + 0.5, -0.3, 0.25))
    # 遠くの町（下の段の家並みの向こう、z -60〜-132）：白磁の箱の家、赤い帆布の屋根、屋上の水槽。大通りの両側に 2〜3 列
    rng = np.random.default_rng(7)
    for sx in (-1, 1):
        for z in np.arange(-62.0, -132.0, -9.0):
            x = 3.5
            while x < 47.0:
                w, d = rng.uniform(4.5, 8.5), rng.uniform(5.0, 8.0)
                h = rng.uniform(3.0, 7.5) * (1.0 if x < 30 else 0.8)
                zc = z + rng.uniform(-1.0, 1.0)
                cx = sx * (x + w / 2)
                if rng.uniform() < 0.82:
                    p.add('ivory', boxb(cx - w / 2, cx + w / 2, -0.2, h, zc - d / 2, zc + d / 2))
                    p.add('graphite', boxb(cx - w / 2 - 0.15, cx + w / 2 + 0.15, h, h + 0.35, zc - d / 2 - 0.15, zc + d / 2 + 0.15))
                    roll = rng.uniform()
                    if roll < 0.35:
                        p.add('cloth', boxb(cx - w / 2 + 0.6, cx + w / 2 - 0.6, h + 0.35, h + 0.9, zc - d / 2 + 0.6, zc + d / 2 - 0.6))
                    elif roll < 0.55:
                        p.add('wood', cyl((cx, h + 0.35, zc), (cx, h + 2.2, zc), 1.1, 8))
                    # 北の面（町の部屋の胸壁から見える面）に暗い窓の列（1 枚の面。面より 4 cm 前）
                    zf = zc + d / 2 + 0.04
                    for wx in np.arange(cx - w / 2 + 1.0, cx + w / 2 - 0.6, 1.6):
                        for wy in ([1.2, 3.6] if h > 5 else [1.4]):
                            q = np.array([[wx - 0.3, wy, zf], [wx + 0.3, wy, zf], [wx + 0.3, wy + 0.8, zf], [wx - 0.3, wy + 0.8, zf]])
                            p.add('dark', _orient_dir(Piece(q, [[0, 1, 2, 3]]), (0, 0, 1)))
                x += w + rng.uniform(0.6, 2.5)
    # 町の端（尾の持ち上がりの手前）の黒鉛の塔（絵：尾の手前に暗い塔が並ぶ）
    for sx, x, z, h in ((-1, 9.0, -136.0, 26.0), (-1, 30.0, -128.0, 19.0), (1, 12.0, -134.0, 23.0), (1, 34.0, -126.0, 17.0), (-1, 44.0, -110.0, 14.0), (1, 42.0, -98.0, 15.0)):
        cx = sx * x
        p.add('graphite', boxb(cx - 2.6, cx + 2.6, -0.2, h, z - 2.6, z + 2.6))
        p.add('brass', boxb(cx - 3.0, cx + 3.0, h * 0.62, h * 0.62 + 0.8, z - 3.0, z + 3.0))
        p.add('graphite', boxb(cx - 1.6, cx + 1.6, h, h + 4.0, z - 1.6, z + 1.6))
        p.add('brass', lathe((cx, h + 4.0, z), (cx, h + 9.0, z), [(0, 1.3), (1, 0.08)], 8))
        p.add('amber', boxb(cx - 1.65, cx + 1.65, h - 3.0, h - 2.4, z + 2.6, z + 2.75))
    # 尾の上の禁足扉の機械の箱：黒鉛の箱、真鍮の枠、町の側（+Z）の面に琥珀の細い灯 2 本（絵の上から見た尾の琥珀の線）
    zt, rt = -186.0, _rise(-186.0)
    p.add('graphite', boxb(-24, 24, rt - 2, rt + 9, zt - 10, zt + 6))
    p.add('brass', boxb(-25, 25, rt + 9, rt + 10, zt - 10.5, zt + 6.5))
    for x in (-15.0, 15.0):
        p.add('brass', boxb(x - 1.0, x + 1.0, rt - 1, rt + 9.5, zt + 6, zt + 7))
    for y in (rt + 3.0, rt + 6.0):
        p.add('amber', boxb(-12, 12, y, y + 0.6, zt + 6, zt + 6.6))
    for x in (-21.0, 21.0):
        p.add('graphite', boxb(x - 2.5, x + 2.5, rt + 9, rt + 16, zt - 6, zt + 2))
        p.add('brass', lathe((x, rt + 16, zt - 2), (x, rt + 20, zt - 2), [(0, 1.4), (1, 0.1)], 8))


PARTS = {'ordo_far': ordo_far}


# ---------------------------------------------------------------- 空（正距円筒）

def _horizon_row(a: np.ndarray) -> int:
    """遠景の絵の地平線の行：空（青み）と砂（赤み）の差が最も大きく変わる行（中央の ±20 % で探す）"""
    h = a.shape[0]
    rb = (a[..., 0] - a[..., 2]).mean(1)
    lo, hi = int(h * 0.3), int(h * 0.7)
    d = np.gradient(np.convolve(rb, np.ones(9) / 9, mode='same'))
    return lo + int(np.argmax(d[lo:hi]))


def _fix_seam(a: np.ndarray, k: int = 6, block: int = 48) -> np.ndarray:
    """bg_desert_* の左右の端（一周のつなぎ目）の直し。絵は左右を鏡に映してつないであり、つなぎ目の 2 列ずつが 1 割ほど暗く、
    その外の 2 列が明るい（ゲームでは真南の空に縦の細い線、見上げると天頂を斜めに横切る線に見えた）。
    つなぎ目の両側 k 列を、列ごとの明るさの倍率だけ外側の列に合わせる（模様はそのまま。倍率は block 行ごとに滑らかに変える）"""
    H, W, _ = a.shape
    r = np.roll(a, W // 2, axis=1)                  # つなぎ目を真ん中（c-1 と c の間）へ
    c = W // 2
    band = slice(c - k, c + k)
    ker = np.ones(block) / block

    def vsmooth(x):                                 # 縦にならす（列・色ごと）
        pad = np.concatenate([x[:block // 2][::-1], x, x[-(block // 2):][::-1]], 0)
        out = np.apply_along_axis(lambda col: np.convolve(col, ker, mode='same'), 0, pad)
        return out[block // 2:block // 2 + H]

    cur = vsmooth(r[:, band])                                       # (H, 2k, 3)
    left = vsmooth(r[:, c - k - 3:c - k].mean(1, keepdims=True))     # 外側の 3 列ずつ
    right = vsmooth(r[:, c + k:c + k + 3].mean(1, keepdims=True))
    t = ((np.arange(2 * k) + 0.5) / (2 * k))[None, :, None]
    want = left * (1 - t) + right * t
    gain = np.clip(want / np.maximum(cur, 1.0), 0.75, 1.35)
    r = r.copy()
    r[:, band] = r[:, band] * gain
    return np.roll(r, -(W // 2), axis=1)


def make_sky(out_dir: str, src: str = INTAKE, width: int = 4096) -> None:
    from PIL import Image
    for name in ('day', 'night', 'dusk'):
        path = os.path.join(src, f'bg_desert_{name}.png')
        if not os.path.exists(path):
            print('[town] 遠景の絵が無い', path)
            continue
        a = _fix_seam(np.asarray(Image.open(path).convert('RGB'), np.float32))
        H, W = a.shape[:2]
        hz = _horizon_row(a)
        # 地平線を少し上へ：町は背の上 120 m なので、地平線は目の高さより少し下（-3 度）に見える
        out_h = W // 2
        horizon_out = out_h // 2 + int(out_h * 3 / 180)
        top = horizon_out - hz
        img = np.zeros((out_h, W, 3), np.float32)
        img[top:top + H] = a
        # 上：空の上の帯の色 → 天頂は少し濃く
        sky_row = a[:16].mean(0).mean(0)
        zenith = sky_row * (0.78 if name != 'night' else 0.7)
        for y in range(top):
            t = y / max(1, top)
            img[y] = zenith * (1 - t) + sky_row * t
        blend = 48
        for i in range(blend):
            w = i / blend
            img[top + i] = img[top + i] * w + sky_row * (1 - w)
        # 下：砂の下の帯の色 → 真下は少し暗く
        ground = a[-16:].mean(0).mean(0)
        bot = top + H
        for y in range(bot, out_h):
            t = (y - bot) / max(1, out_h - bot)
            img[y] = ground * (1 - 0.25 * t)
        for i in range(blend):
            w = i / blend
            img[bot - 1 - i] = img[bot - 1 - i] * w + ground * (1 - w)
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        p = os.path.join(out_dir, f'sky_{name}.jpg')
        im.save(p, quality=86)
        print(f'[town] 空 {p}（地平線 {hz} 行 → {horizon_out} 行）', flush=True)
