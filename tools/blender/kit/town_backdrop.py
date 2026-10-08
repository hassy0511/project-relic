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

from town_geo import Part, Piece, _orient, beam, box, boxb, cyl, lathe

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
