"""町の遠景の空の絵（sky_*.jpg）。オルドの体・縁・脚は ordo.glb（OrdoView、部屋の "ordo"）が描き、背の上の遠くの町（ordo_back・ordo_town）は
town_far.py が作る（2026-11-01。前はここの箱の家の影絵）。
前の遠景 ordo_far（箱の外殻・持ち上がった頭と尾・4 対の脚の影絵）は 2026-10-16 に部屋から外し、2026-10-18 に部品と作るコードも消した。

sky_day / sky_night / sky_dusk：bg_desert_*.png（4096×1024、水平に一周、地平線はほぼ中央）を、Godot の
PanoramaSkyMaterial 用の正距円筒（4096×2048）の真ん中の帯に置き、上は空の色、下は砂の色でなだらかに埋める。
"""
from __future__ import annotations

import os

import numpy as np


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
INTAKE = os.path.join(REPO, 'build', 'intake', 'w2town')


# 背の上の遠くの町（ordo_back・ordo_town）は 2026-11-01 から town_far.py が作る（町のキットの絵の帳を貼った 1 つのメッシュ。
# 前の白磁の箱の家・帆布の屋根・黒鉛の塔の影絵は消した）。ここに残るのは空の絵だけ
PARTS: dict = {}


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
