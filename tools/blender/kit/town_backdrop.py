"""町の遠景：背の上の遠くの町（ordo_back・ordo_town）と空の絵（sky_*.jpg）。オルドの体・縁・脚は ordo.glb（OrdoView、部屋の "ordo"）が描く。

ordo_back：中段・下段の部屋から見える、下の段の家並みの向こうの遠くの町と塔。ordo_town：船首の頭の上の部屋から見下ろす背の町の全体。
原点 = 背の歩行面（町を載せる平らな面）の真ん中、+Z が船首（町の上の段の向き）。
前の遠景 ordo_far（箱の外殻・持ち上がった頭と尾・4 対の脚の影絵）は 2026-10-16 に部屋から外し、2026-10-18 に部品と作るコードも消した。

sky_day / sky_night / sky_dusk：bg_desert_*.png（4096×1024、水平に一周、地平線はほぼ中央）を、Godot の
PanoramaSkyMaterial 用の正距円筒（4096×2048）の真ん中の帯に置き、上は空の色、下は砂の色でなだらかに埋める。
"""
from __future__ import annotations

import os

import numpy as np

from town_geo import Part, Piece, _orient_dir, boxb, cyl, lathe

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
INTAKE = os.path.join(REPO, 'build', 'intake', 'w2town')


# ---------------------------------------------------------------- 背の上の遠くの町（2026-10-16：オルドの体は OrdoView（ordo.glb）が描く）

def _houses(p: Part, z_hi: float, z_lo: float, base, seed: int, x_max: float = 47.0, windows: bool = True):
    """背の上の遠くの家並み（大通りの両側に、白磁の箱の家・帆布の屋根・水槽、北の面に暗い窓）。base(z) は家の床の高さ（背の面から）"""
    rng = np.random.default_rng(seed)
    for sx in (-1, 1):
        for z in np.arange(z_hi, z_lo, -9.0):
            x = 3.5
            while x < x_max:
                w, d = rng.uniform(4.5, 8.5), rng.uniform(5.0, 8.0)
                h = rng.uniform(3.0, 7.5) * (1.0 if x < 30 else 0.8)
                zc = z + rng.uniform(-1.0, 1.0)
                cx = sx * (x + w / 2)
                y0 = base(zc)
                if rng.uniform() < 0.82:
                    p.add('ivory', boxb(cx - w / 2, cx + w / 2, y0 - 0.2, y0 + h, zc - d / 2, zc + d / 2))
                    p.add('graphite', boxb(cx - w / 2 - 0.15, cx + w / 2 + 0.15, y0 + h, y0 + h + 0.35, zc - d / 2 - 0.15, zc + d / 2 + 0.15))
                    roll = rng.uniform()
                    if roll < 0.35:
                        p.add('cloth', boxb(cx - w / 2 + 0.6, cx + w / 2 - 0.6, y0 + h + 0.35, y0 + h + 0.9, zc - d / 2 + 0.6, zc + d / 2 - 0.6))
                    elif roll < 0.55:
                        p.add('wood', cyl((cx, y0 + h + 0.35, zc), (cx, y0 + h + 2.2, zc), 1.1, 8))
                    if windows:
                        zf = zc + d / 2 + 0.04
                        for wx in np.arange(cx - w / 2 + 1.0, cx + w / 2 - 0.6, 1.6):
                            for wy in ([1.2, 3.6] if h > 5 else [1.4]):
                                q = np.array([[wx - 0.3, y0 + wy, zf], [wx + 0.3, y0 + wy, zf], [wx + 0.3, y0 + wy + 0.8, zf], [wx - 0.3, y0 + wy + 0.8, zf]])
                                p.add('dark', _orient_dir(Piece(q, [[0, 1, 2, 3]]), (0, 0, 1)))
                x += w + rng.uniform(0.6, 2.5)


def _tower(p: Part, cx: float, z: float, h: float, y0: float = 0.0):
    """町の黒鉛の塔（真鍮の帯と尖塔、琥珀の細い灯。絵の背の町の暗い塔）"""
    p.add('graphite', boxb(cx - 2.6, cx + 2.6, y0 - 0.2, y0 + h, z - 2.6, z + 2.6))
    p.add('brass', boxb(cx - 3.0, cx + 3.0, y0 + h * 0.62, y0 + h * 0.62 + 0.8, z - 3.0, z + 3.0))
    p.add('graphite', boxb(cx - 1.6, cx + 1.6, y0 + h, y0 + h + 4.0, z - 1.6, z + 1.6))
    p.add('brass', lathe((cx, y0 + h + 4.0, z), (cx, y0 + h + 9.0, z), [(0, 1.3), (1, 0.08)], 8))
    p.add('amber', boxb(cx - 1.65, cx + 1.65, y0 + h - 3.0, y0 + h - 2.4, z + 2.6, z + 2.75))


BACK_TOWERS = ((-1, 9.0, -112.0, 26.0), (-1, 30.0, -106.0, 19.0), (1, 12.0, -110.0, 23.0), (1, 34.0, -104.0, 17.0),
               (-1, 44.0, -92.0, 14.0), (1, 42.0, -84.0, 15.0))


def ordo_back() -> Part:
    """中段・下段の部屋の遠景：下の段の家並みの向こう（背の上の z -60〜-114。原点 = 背の面の真ん中、+Z が船首）の遠くの町と、
    町の端の黒鉛の塔、真ん中の大通り。オルドの体・縁・脚・尾の板と機械は ordo.glb（OrdoView、部屋の "ordo"）が描く。
    背の面は z -118〜+100 で平ら（ordo.py）なので、町は尾の持ち上がりの手前で止める"""
    p = Part('ordo_back')
    p.add('graphite', boxb(-1.6, 1.6, -0.3, 0.35, -114.0, -58.0))
    _houses(p, -62.0, -114.0, lambda z: 0.0, 7)
    for sx, x, z, h in BACK_TOWERS:
        _tower(p, sx * x, z, h)
    return p


def ordo_town() -> Part:
    """船首の頭の上の部屋（夜明けの甲羅 ch1.opening）から見下ろす背の町の全体（z -114〜+95）：3 段（下 +1.5・中 +6.5・上 +11.5、
    段の境に擁壁）の床の板と家並み、塔。遠く（150〜300 m）から見る影絵なので、窓は付けない"""
    p = Part('ordo_town')

    def base(z):
        return 11.5 if z > 34.0 else (6.5 if z > -15.0 else 1.5)
    for (z0, z1, y) in ((-60.0, -15.0, 1.5), (-15.0, 34.0, 6.5), (34.0, 95.0, 11.5)):
        p.add('ivory', boxb(-48.5, 48.5, -0.2, y, z0, z1))
        p.add('graphite', boxb(-48.9, 48.9, y - 0.05, y + 0.25, z1 - 0.4, z1 + 0.4))
    p.add('graphite', boxb(-1.6, 1.6, -0.3, 0.35, -114.0, -60.0))
    _houses(p, 92.0, -114.0, base, 11, windows=False)
    for sx, x, z, h in BACK_TOWERS + ((-1, 20.0, 10.0, 24.0), (1, 22.0, 18.0, 20.0), (-1, 8.0, 60.0, 30.0), (1, 30.0, 72.0, 18.0)):
        _tower(p, sx * x, z, h, base(z))
    return p


PARTS = {'ordo_back': ordo_back, 'ordo_town': ordo_town}


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
