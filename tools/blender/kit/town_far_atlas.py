"""背の上の遠くの町（town_far.py）の絵の帳（アトラス）：1024 × 1024 の RGBA、128 画素の升目が 8 × 8。

升目 1 つ = 繰り返しの 1 単位（家の正面なら 1 間（約 3 m）× 1 階（3.2 m）、屋根・床なら 4 m 四方など）。
升目の中身は 112 画素で、まわりの 8 画素は中身を回り込ませた余白（遠くの縮んだ絵で隣の升目の色がにじまないように）。
RGB = 色（sRGB。ゲームでは頂点の色を掛けて家ごとの色の違いを出す）、A = 夜に光る所（窓のガラス・扉の上の明かり取り・灯。0〜1）。
色と絵は町のキットと同じ（白磁の壁 tex_town_shell、帆布 tex_town_canvas、板 tex_town_wood、錆 tex_town_rust。spec_town_3d.md の色見本）。

  .venv-blender/bin/python tools/blender/kit/town_far.py --atlas-only    帳だけ作って build/kit_town/far_atlas_preview.jpg に拡大を出す
"""
from __future__ import annotations

import math
import os

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TEX = os.path.join(REPO, 'godot', 'assets', 'kit', 'tex')

CELL, PAD = 128, 8
IN = CELL - 2 * PAD
GRID = 8
SIZE = CELL * GRID


def _hex(h: str) -> np.ndarray:
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


C = {k: _hex(v) for k, v in dict(
    ivory='#EFE7D6', ivory2='#D8CCB2', graphite='#4A4B46', graphite_d='#33342F', brass='#B08D4E', brass_d='#7E6233',
    rust='#B75B43', cloth2='#93432F', wood='#5E4636', wood2='#7E5F45', dark='#2A2723', glass='#2E3236', glass_hi='#59605F',
    green='#6E7A3C', green_d='#4B5A2C', linen='#E6DAC0', amber='#FFBC52', warm='#F2C27A', shadow='#B9AE98',
    tile='#B25A40', tile_d='#8E4130', sand='#D9C7A6').items()}

# 升目の名前 → (列, 行)
CELLS: dict[str, tuple[int, int]] = {}


def _reg(name, col, row):
    CELLS[name] = (col, row)


# 0 行：上の階の正面（1 間 3.0 m × 1 階 3.2 m）
for i, n in enumerate(['win', 'win2', 'balcony', 'arch', 'pipes', 'shut', 'panel', 'flower']):
    _reg('up_' + n, i, 0)
# 1 行：1 階の正面（同じ大きさ）
for i, n in enumerate(['door', 'shop', 'win', 'shutter', 'archdoor', 'door2', 'plain', 'goods']):
    _reg('gr_' + n, i, 1)
# 2 行：目印の建物・塔（ギルド・町長の家・塔・工房・食堂・門）
for i, n in enumerate(['guild', 'mayor', 'tower', 'tower2', 'workshop', 'diner', 'gate', 'cornice']):
    _reg('lm_' + n, i, 2)
# 3 行：段の擁壁・階段・床・縁（4 m 四方）
for i, n in enumerate(['ret', 'ret_door', 'stair', 'pave', 'pave2', 'deck', 'coping', 'ring']):
    _reg('st_' + n, i, 3)
# 4 行：屋根（4 m 四方。瓦は 3 m）
for i, n in enumerate(['flat', 'flat2', 'tile', 'wood', 'garden', 'metal', 'tar', 'gravel']):
    _reg('rf_' + n, i, 4)
# 5 行：布（帆布の縞・無地・旗・小旗）
for i, n in enumerate(['stripe', 'red', 'dark', 'linen', 'banner', 'banner2', 'white', 'stripe2']):
    _reg('cl_' + n, i, 5)
# 6 行：材の色（黒鉛・真鍮・板・緑・錆・白磁・暗い所・水槽）
for i, n in enumerate(['graphite', 'brass', 'wood', 'green', 'green2', 'rust', 'ivory', 'dark']):
    _reg('mt_' + n, i, 6)
# 7 行：光る物（灯の芯・明るい窓・塔の細い窓）
for i, n in enumerate(['amber', 'lit', 'slit', 'lantern']):
    _reg('em_' + n, i, 7)


def uv_rect(name: str) -> tuple[float, float, float, float]:
    """升目の中身の UV（u0, v0, u1, v1）。v は下向き（glTF・Godot と同じ：v0 が絵の上）"""
    c, r = CELLS[name]
    return ((c * CELL + PAD) / SIZE, (r * CELL + PAD) / SIZE, (c * CELL + PAD + IN) / SIZE, (r * CELL + PAD + IN) / SIZE)


# ---------------------------------------------------------------- 描く道具（升目の中身 IN × IN、座標は m、y は上向き）

class Canvas:
    def __init__(self, w_m: float, h_m: float, base=None):
        self.w, self.h = w_m, h_m
        self.rgb = np.zeros((IN, IN, 3), np.float32)
        self.a = np.zeros((IN, IN), np.float32)
        if base is not None:
            self.rgb[:] = base

    def _px(self, x0, y0, x1, y1):
        """m の範囲 → 画素の範囲（行は上から）"""
        sx, sy = IN / self.w, IN / self.h
        c0, c1 = int(round(x0 * sx)), int(round(x1 * sx))
        r0, r1 = int(round((self.h - y1) * sy)), int(round((self.h - y0) * sy))
        return max(r0, 0), min(max(r1, r0 + 1), IN), max(c0, 0), min(max(c1, c0 + 1), IN)

    def rect(self, x0, y0, x1, y1, col, glow=None, mul=None, alpha=1.0):
        r0, r1, c0, c1 = self._px(x0, y0, x1, y1)
        if mul is not None:
            self.rgb[r0:r1, c0:c1] *= mul
        else:
            col = np.asarray(col, np.float32)
            self.rgb[r0:r1, c0:c1] = self.rgb[r0:r1, c0:c1] * (1 - alpha) + col * alpha
        if glow is not None:
            self.a[r0:r1, c0:c1] = glow

    def frame(self, x0, y0, x1, y1, t, col):
        self.rect(x0, y0, x1, y0 + t, col)
        self.rect(x0, y1 - t, x1, y1, col)
        self.rect(x0, y0, x0 + t, y1, col)
        self.rect(x1 - t, y0, x1, y1, col)

    def grad(self, x0, y0, x1, y1, top, bot):
        r0, r1, c0, c1 = self._px(x0, y0, x1, y1)
        t = np.linspace(0, 1, r1 - r0)[:, None, None]
        self.rgb[r0:r1, c0:c1] = np.asarray(top) * (1 - t) + np.asarray(bot) * t

    def paste(self, x0, y0, x1, y1, img):
        """img（H, W, 3）を範囲へ引き伸ばして貼る"""
        from PIL import Image
        r0, r1, c0, c1 = self._px(x0, y0, x1, y1)
        im = Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8)).resize((c1 - c0, r1 - r0), Image.LANCZOS)
        self.rgb[r0:r1, c0:c1] = np.asarray(im, np.float32) / 255.0

    def ellipse(self, cx, cy, rx, ry, col, glow=None):
        sx, sy = IN / self.w, IN / self.h
        yy, xx = np.mgrid[0:IN, 0:IN]
        X = (xx + 0.5) / sx
        Y = self.h - (yy + 0.5) / sy
        m = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1.0
        self.rgb[m] = col
        if glow is not None:
            self.a[m] = glow
        return m

    def noise(self, amount, scale_px=6, seed=0):
        rng = np.random.default_rng(seed)
        n = rng.standard_normal((IN // scale_px + 2, IN // scale_px + 2)).astype(np.float32)
        from PIL import Image
        im = Image.fromarray(((n - n.min()) / (np.ptp(n) + 1e-6) * 255).astype(np.uint8)).resize((IN, IN), Image.BICUBIC)
        m = np.asarray(im, np.float32) / 255.0 - 0.5
        self.rgb *= (1.0 + amount * m)[..., None]

    def streaks(self, x0, x1, y_top, length, amount=0.12, seed=0):
        """汚れの縦の筋（窓の下・笠木の下）：上が濃く、下へ薄く"""
        rng = np.random.default_rng(seed)
        r0, r1, c0, c1 = self._px(x0, max(y_top - length, 0), x1, y_top)
        if r1 <= r0 or c1 <= c0:
            return
        cols = rng.uniform(0.3, 1.0, c1 - c0).astype(np.float32)
        cols = np.convolve(cols, np.ones(3) / 3, mode='same')
        t = np.linspace(1, 0, r1 - r0)[:, None] ** 1.5
        self.rgb[r0:r1, c0:c1] *= (1.0 - amount * t * cols[None, :])[..., None]


_SRC: dict[str, np.ndarray] = {}


def src(name: str) -> np.ndarray:
    """町の表面の絵（1024 画素 = 2 m 四方、上下左右がつながる）"""
    if name not in _SRC:
        from PIL import Image
        _SRC[name] = np.asarray(Image.open(os.path.join(TEX, f'town_{name}.jpg')).convert('RGB'), np.float32) / 255.0
    return _SRC[name]


def src_region(name: str, w_m: float, h_m: float, contrast=1.0, mean=None, ox=0.0, oy=0.0) -> np.ndarray:
    """表面の絵の w_m × h_m の所（繰り返してつなぐ）を IN × IN へ。contrast で模様の濃さ、mean で平均の色"""
    from PIL import Image
    a = src(name)
    S = a.shape[0]
    pw, ph = int(round(w_m / 2.0 * S)), int(round(h_m / 2.0 * S))
    x0, y0 = int(ox / 2.0 * S) % S, int(oy / 2.0 * S) % S
    reps = (math.ceil((ph + y0) / S) + 1, math.ceil((pw + x0) / S) + 1, 1)
    big = np.tile(a, reps)[y0:y0 + ph, x0:x0 + pw]
    im = Image.fromarray(np.clip(big * 255, 0, 255).astype(np.uint8)).resize((IN, IN), Image.LANCZOS)
    out = np.asarray(im, np.float32) / 255.0
    m = out.mean((0, 1))
    out = (out - m) * contrast + (np.asarray(mean, np.float32) if mean is not None else m)
    return np.clip(out, 0, 1)


# ---------------------------------------------------------------- 升目の絵

W_BAY, H_ST = 3.0, 3.2     # 正面の 1 間・1 階（m）


def wall(seed=0) -> Canvas:
    """白磁の壁（タイルの継ぎ目のうすい模様）と両端の黒鉛の付け柱、上の帯（黒鉛と真鍮の線）"""
    c = Canvas(W_BAY, H_ST)
    c.rgb[:] = src_region('shell_soft', W_BAY, H_ST, contrast=0.32, mean=C['ivory'], ox=seed * 0.37)
    c.noise(0.06, 10, seed)
    # 付け柱（隣の升目と合わせて 1 本）
    c.rect(0, 0, 0.09, H_ST, C['graphite'])
    c.rect(W_BAY - 0.09, 0, W_BAY, H_ST, C['graphite'])
    # 階の帯
    c.rect(0, H_ST - 0.2, W_BAY, H_ST, C['graphite'])
    c.rect(0, H_ST - 0.24, W_BAY, H_ST - 0.2, C['brass'])
    c.streaks(0.1, W_BAY - 0.1, H_ST - 0.24, 1.2, 0.08, seed + 3)
    # 足元の汚れ
    c.grad(0, 0, W_BAY, 0.25, C['ivory'] * 0.97, C['shadow'])
    return c


def window(c: Canvas, x0, y0, w, h, shutters=None, glow=1.0, sill=True, mullion=True, arch=False, seed=0):
    """窓：黒鉛の枠、ガラス（夜に光る）、桟、窓台、雨戸（'wood' か 'rust'、開いて両脇に）"""
    t = 0.08
    if shutters:
        sc = C['wood2'] if shutters == 'wood' else C['rust'] * 0.9
        sw = w * 0.42
        for xa in (x0 - sw - 0.02, x0 + w + 0.02):
            c.rect(xa, y0, xa + sw, y0 + h, sc)
            for k in range(1, 6):
                yy = y0 + h * k / 6
                c.rect(xa + 0.03, yy - 0.015, xa + sw - 0.03, yy + 0.015, sc * 0.72)
            c.frame(xa, y0, xa + sw, y0 + h, 0.03, sc * 0.6)
    c.rect(x0 - t, y0 - t, x0 + w + t, y0 + h + t, C['graphite'])
    c.grad(x0, y0, x0 + w, y0 + h, C['glass_hi'], C['glass'])
    c.rect(x0, y0, x0 + w, y0 + h, None, glow=glow, mul=np.float32(1.0))
    if arch:
        c.ellipse(x0 + w / 2, y0 + h, w / 2 + t, w * 0.35 + t, C['graphite'])
        c.ellipse(x0 + w / 2, y0 + h, w / 2, w * 0.35, C['glass_hi'], glow=glow)
    if mullion:
        c.rect(x0 + w / 2 - 0.025, y0, x0 + w / 2 + 0.025, y0 + h, C['graphite'], glow=0.0)
        c.rect(x0, y0 + h * 0.62 - 0.025, x0 + w, y0 + h * 0.62 + 0.025, C['graphite'], glow=0.0)
    if sill:
        c.rect(x0 - 0.14, y0 - 0.16, x0 + w + 0.14, y0 - t, C['ivory2'] * 0.92)
        c.streaks(x0 - 0.1, x0 + w + 0.1, y0 - 0.16, 0.9, 0.1, seed)


def door(c: Canvas, x0, w, h, col='wood', double=False, transom=True):
    t = 0.1
    c.rect(x0 - t, 0, x0 + w + t, h + t, C['graphite'])
    base = C['wood'] if col == 'wood' else (C['rust'] * 0.85 if col == 'rust' else C['brass_d'])
    c.rect(x0, 0, x0 + w, h, base)
    n = 5 if col == 'wood' else 8
    for k in range(1, n):
        xx = x0 + w * k / n
        c.rect(xx - 0.012, 0, xx + 0.012, h, base * 0.7)
    if double:
        c.rect(x0 + w / 2 - 0.03, 0, x0 + w / 2 + 0.03, h, C['graphite'])
    c.rect(x0 + w * (0.42 if double else 0.8), h * 0.45, x0 + w * (0.42 if double else 0.8) + 0.06, h * 0.52, C['brass'])
    if transom:
        c.rect(x0, h + t, x0 + w, h + t + 0.32, C['glass_hi'], glow=0.9)
        c.rect(x0 - t, h + t + 0.32, x0 + w + t, h + t + 0.4, C['graphite'])


def lamp(c: Canvas, x, y):
    c.rect(x - 0.04, y - 0.05, x + 0.2, y + 0.02, C['graphite'])
    c.rect(x + 0.06, y - 0.32, x + 0.26, y - 0.06, C['amber'], glow=1.0)
    c.rect(x + 0.04, y - 0.06, x + 0.28, y, C['brass'])


def crate(c: Canvas, x, w, h):
    c.rect(x, 0, x + w, h, C['wood2'])
    c.frame(x, 0, x + w, h, 0.05, C['wood'] * 0.8)
    c.rect(x, h * 0.48, x + w, h * 0.52, C['wood'] * 0.8)


def cell_up(kind: str, seed: int) -> Canvas:
    c = wall(seed)
    mid = W_BAY / 2
    if kind == 'win':
        window(c, mid - 0.5, 0.95, 1.0, 1.45, shutters='wood', seed=seed)
    elif kind == 'win2':
        window(c, 0.55, 1.0, 0.7, 1.35, seed=seed)
        window(c, W_BAY - 1.25, 1.0, 0.7, 1.35, seed=seed + 1)
    elif kind == 'balcony':
        window(c, mid - 0.45, 0.25, 0.9, 2.2, mullion=True, sill=False, seed=seed)
        c.rect(mid - 1.1, 0.2, mid + 1.1, 0.32, C['graphite'])           # 床
        c.rect(mid - 1.1, 1.18, mid + 1.1, 1.24, C['brass'])             # 手すり
        for k in range(9):
            xx = mid - 1.05 + 2.1 * k / 8
            c.rect(xx - 0.02, 0.32, xx + 0.02, 1.2, C['brass_d'])
        c.ellipse(mid - 0.8, 0.55, 0.22, 0.22, C['green'])
        c.ellipse(mid + 0.82, 0.5, 0.2, 0.18, C['green_d'])
    elif kind == 'arch':
        window(c, mid - 0.45, 0.95, 0.9, 1.25, arch=True, sill=True, seed=seed)
        c.rect(0.25, 2.65, W_BAY - 0.25, 2.72, C['brass'])
    elif kind == 'pipes':
        window(c, 0.4, 1.1, 0.65, 1.2, seed=seed)
        for xx, r in ((2.05, 0.07), (2.35, 0.05)):
            c.rect(xx - r, 0, xx + r, H_ST, C['graphite'])
            c.rect(xx - r * 0.4, 0, xx - r * 0.1, H_ST, C['glass_hi'])
        c.rect(1.9, 1.6, 2.5, 1.75, C['brass'])
        c.rect(2.6, 2.35, 2.85, 2.6, C['graphite_d'])
    elif kind == 'shut':
        window(c, mid - 0.5, 0.95, 1.0, 1.45, glow=0.0, seed=seed)
        c.rect(mid - 0.5, 0.95, mid + 0.5, 2.4, C['rust'] * 0.88)
        for k in range(1, 9):
            yy = 0.95 + 1.45 * k / 9
            c.rect(mid - 0.48, yy - 0.015, mid + 0.48, yy + 0.015, C['rust'] * 0.6)
        c.rect(mid - 0.012, 0.95, mid + 0.012, 2.4, C['rust'] * 0.5)
    elif kind == 'panel':
        c.frame(0.35, 0.5, W_BAY - 0.35, 2.7, 0.06, C['graphite'])
        c.rect(0.35, 1.58, W_BAY - 0.35, 1.64, C['graphite'])
        for xx in (0.35, W_BAY - 0.35):
            for yy in (0.5, 1.6, 2.7):
                c.rect(xx - 0.07, yy - 0.07, xx + 0.07, yy + 0.07, C['brass'])
    elif kind == 'flower':
        window(c, mid - 0.5, 1.05, 1.0, 1.35, shutters='rust', sill=False, seed=seed)
        c.rect(mid - 0.62, 0.78, mid + 0.62, 1.0, C['wood2'])
        for k in range(7):
            c.ellipse(mid - 0.55 + k * 0.18, 1.02 + 0.05 * (k % 2), 0.12, 0.1, C['green'] if k % 3 else C['tile'])
    return c


def cell_ground(kind: str, seed: int) -> Canvas:
    c = wall(seed + 50)
    c.rect(0, 0, W_BAY, 0.35, C['ivory2'] * 0.85)          # 足元の板（腰）
    c.rect(0, 0.35, W_BAY, 0.4, C['graphite'])
    mid = W_BAY / 2
    if kind == 'door':
        door(c, mid - 0.55, 1.1, 2.15)
        lamp(c, mid + 0.75, 2.5)
    elif kind == 'shop':
        c.rect(0.25, 0, W_BAY - 0.25, 2.45, C['graphite'])
        c.grad(0.35, 0.0, W_BAY - 0.35, 2.35, C['warm'] * 0.55, C['wood'] * 0.6)
        c.rect(0.35, 0.0, W_BAY - 0.35, 2.35, None, glow=0.75, mul=np.float32(1.0))
        rng = np.random.default_rng(seed)
        for k in range(10):                                    # 棚の品物
            x = 0.45 + k * 0.22
            col = [C['tile'], C['brass'], C['green'], C['linen'], C['rust']][int(rng.integers(5))]
            c.rect(x, 1.45, x + 0.16, 1.45 + rng.uniform(0.15, 0.32), col, glow=0.0)
            c.rect(x, 0.9, x + 0.16, 0.9 + rng.uniform(0.12, 0.3), col * 0.85, glow=0.0)
        c.rect(0.35, 0.0, W_BAY - 0.35, 0.75, C['wood2'], glow=0.0)    # 台
        c.rect(0.35, 0.72, W_BAY - 0.35, 0.8, C['wood'], glow=0.0)
        c.grad(0.25, 2.1, W_BAY - 0.25, 2.45, C['dark'] * 0.8, C['graphite'])
    elif kind == 'win':
        window(c, mid - 0.55, 0.95, 1.1, 1.3, shutters='wood', seed=seed)
        crate(c, 0.15, 0.55, 0.55)
        crate(c, 0.25, 0.45, 0.45 + 0.55)
    elif kind == 'shutter':
        c.rect(0.3, 0, W_BAY - 0.3, 2.5, C['graphite'])
        c.paste(0.4, 0, W_BAY - 0.4, 2.35, src_region('rust', 2.2, 2.35, contrast=0.6))
        for k in range(1, 16):
            yy = 2.35 * k / 16
            c.rect(0.4, yy - 0.012, W_BAY - 0.4, yy + 0.012, C['graphite_d'])
        lamp(c, W_BAY - 0.5, 2.85)
    elif kind == 'archdoor':
        c.ellipse(mid, 2.0, 0.75, 0.6, C['graphite'])
        c.rect(mid - 0.75, 0, mid + 0.75, 2.0, C['graphite'])
        c.ellipse(mid, 2.0, 0.65, 0.5, C['dark'], glow=0.0)
        c.rect(mid - 0.65, 0, mid + 0.65, 2.0, C['dark'])
        c.grad(mid - 0.65, 0, mid + 0.65, 1.3, C['dark'], C['warm'] * 0.35)
        c.rect(mid - 0.65, 0, mid + 0.65, 1.3, None, glow=0.5, mul=np.float32(1.0))
    elif kind == 'door2':
        door(c, mid - 0.75, 1.5, 2.3, col='brass', double=True, transom=False)
        c.rect(mid - 0.85, 2.4, mid + 0.85, 2.52, C['brass'])
        lamp(c, 0.25, 2.5)
        lamp(c, W_BAY - 0.55, 2.5)
    elif kind == 'plain':
        window(c, mid - 0.4, 1.35, 0.8, 0.9, sill=True, seed=seed)
        c.rect(0.2, 0.4, 0.5, 2.2, C['graphite'])               # 縦の管
        c.rect(0.28, 0.4, 0.33, 2.2, C['glass_hi'])
        crate(c, 2.1, 0.6, 0.5)
    elif kind == 'goods':
        door(c, 0.3, 1.0, 2.1)
        c.rect(1.6, 0.6, 2.85, 2.3, C['graphite'])
        c.rect(1.68, 0.68, 2.77, 2.22, C['warm'] * 0.6, glow=0.7)
        c.rect(1.68, 0.68, 2.77, 1.0, C['wood2'], glow=0.0)
        for k in range(5):
            c.rect(1.75 + k * 0.2, 1.0, 1.88 + k * 0.2, 1.25, [C['tile'], C['green'], C['brass'], C['linen'], C['rust']][k], glow=0.0)
    return c


def cell_landmark(kind: str, seed: int) -> Canvas:
    if kind in ('tower', 'tower2'):
        c = Canvas(W_BAY, H_ST)
        c.rgb[:] = C['graphite']
        c.noise(0.12, 8, seed)
        for xx in (0.0, W_BAY / 2, W_BAY):
            c.rect(xx - 0.05, 0, xx + 0.05, H_ST, C['graphite_d'])
        c.rect(0, H_ST - 0.12, W_BAY, H_ST, C['graphite_d'])
        for xx in (0.25, W_BAY / 2 + 0.25):
            for yy in (0.3, 1.9):
                c.rect(xx, yy, xx + 0.08, yy + 0.08, C['brass'])
        if kind == 'tower':
            c.rect(W_BAY / 2 - 0.16, 0.7, W_BAY / 2 + 0.16, 2.4, C['amber'] * 0.75, glow=1.0)
            c.frame(W_BAY / 2 - 0.22, 0.64, W_BAY / 2 + 0.22, 2.46, 0.06, C['brass'])
        else:
            c.rect(0, 1.4, W_BAY, 1.75, C['brass'])
            c.rect(0, 1.48, W_BAY, 1.52, C['brass_d'])
        return c
    c = wall(seed + 90)
    mid = W_BAY / 2
    if kind == 'guild':
        # 大きな丸窓（歯車の真鍮の縁）
        c.ellipse(mid, 1.7, 1.15, 1.15, C['brass'])
        c.ellipse(mid, 1.7, 1.0, 1.0, C['graphite'])
        c.ellipse(mid, 1.7, 0.86, 0.86, C['glass_hi'], glow=1.0)
        c.rect(mid - 0.86, 1.68, mid + 0.86, 1.72, C['graphite'], glow=0.0)
        c.rect(mid - 0.02, 0.84, mid + 0.02, 2.56, C['graphite'], glow=0.0)
        for k in range(12):
            a = k * math.pi / 6
            c.ellipse(mid + math.cos(a) * 1.15, 1.7 + math.sin(a) * 1.15, 0.12, 0.12, C['brass_d'])
    elif kind == 'mayor':
        for xx in (0.35, W_BAY - 0.35):
            c.rect(xx - 0.18, 0, xx + 0.18, H_ST - 0.24, C['ivory2'])
            c.rect(xx - 0.24, H_ST - 0.5, xx + 0.24, H_ST - 0.24, C['brass'])
            c.rect(xx - 0.24, 0, xx + 0.24, 0.2, C['brass_d'])
        window(c, mid - 0.45, 0.6, 0.9, 1.9, shutters='wood', arch=True, sill=True, seed=seed)
    elif kind == 'workshop':
        c.rect(0.15, 0, W_BAY - 0.15, 2.7, C['graphite'])
        c.paste(0.25, 0, W_BAY - 0.25, 2.55, src_region('rust', 2.5, 2.55, contrast=0.7))
        for k in range(1, 6):
            xx = 0.25 + (W_BAY - 0.5) * k / 6
            c.rect(xx - 0.03, 0, xx + 0.03, 2.55, C['graphite_d'])
        c.rect(0.25, 2.0, W_BAY - 0.25, 2.55, C['warm'] * 0.5, glow=0.8)
        for k in range(1, 6):
            xx = 0.25 + (W_BAY - 0.5) * k / 6
            c.rect(xx - 0.03, 2.0, xx + 0.03, 2.55, C['graphite_d'], glow=0.0)
        c.rect(0, 2.75, W_BAY, 2.95, C['brass'])
    elif kind == 'diner':
        c.rect(0.15, 0.0, W_BAY - 0.15, 2.6, C['graphite'])
        c.grad(0.25, 0.4, W_BAY - 0.25, 2.5, C['warm'] * 0.75, C['warm'] * 0.45)
        c.rect(0.25, 0.4, W_BAY - 0.25, 2.5, None, glow=1.0, mul=np.float32(1.0))
        for k in range(1, 4):
            xx = 0.25 + (W_BAY - 0.5) * k / 4
            c.rect(xx - 0.03, 0.4, xx + 0.03, 2.5, C['graphite'], glow=0.0)
        c.rect(0.25, 1.85, W_BAY - 0.25, 1.9, C['graphite'], glow=0.0)
        c.rect(0.15, 0, W_BAY - 0.15, 0.4, C['wood2'])
        for xx in (0.7, 1.5, 2.3):                               # 卓と人影
            c.rect(xx - 0.25, 0.4, xx + 0.25, 0.75, C['wood'], glow=0.0)
            c.ellipse(xx, 1.05, 0.12, 0.28, C['dark'] * 1.2, glow=0.0)
    elif kind == 'gate':
        c.rect(0.2, 0, W_BAY - 0.2, 2.9, C['graphite'])
        door(c, 0.35, W_BAY - 0.7, 2.6, col='wood', double=True, transom=False)
        c.ellipse(mid, 2.9, 1.3, 0.25, C['brass'])
    elif kind == 'cornice':
        c.rect(0, 0, W_BAY, H_ST * 0.3, C['ivory2'])
        c.rect(0, H_ST * 0.3, W_BAY, H_ST * 0.36, C['brass'])
        c.rect(0, H_ST * 0.36, W_BAY, H_ST * 0.5, C['graphite'])
    return c


def cell_struct(kind: str, seed: int) -> Canvas:
    if kind in ('ret', 'ret_door'):
        # 段の擁壁（4 m × 4 m）：大きな白磁の板、2 m ごとの黒鉛の柱、上の真鍮の帯と黒鉛の笠木
        c = Canvas(4.0, 4.0)
        c.rgb[:] = src_region('shell', 4.0, 4.0, contrast=0.32, mean=C['ivory'] * 0.96, ox=seed * 0.21)
        for xx in (0.0, 2.0, 4.0):
            c.rect(xx - 0.12, 0, xx + 0.12, 4.0, C['graphite'])
            c.rect(xx - 0.16, 3.0, xx + 0.16, 3.25, C['brass'])
        c.rect(0, 3.7, 4.0, 4.0, C['graphite'])
        c.rect(0, 3.62, 4.0, 3.7, C['brass'])
        c.streaks(0.2, 3.8, 3.6, 2.4, 0.1, seed)
        c.grad(0, 0, 4.0, 0.5, C['ivory'] * 0.9, C['shadow'] * 0.95)
        if kind == 'ret_door':
            door(c, 0.55, 1.0, 2.1, col='rust', transom=False)
            lamp(c, 1.62, 2.55)
            c.rect(2.6, 0, 2.66, 3.0, C['graphite_d'])                   # はしご
            c.rect(3.3, 0, 3.36, 3.0, C['graphite_d'])
            for k in range(10):
                c.rect(2.6, 0.2 + k * 0.29, 3.36, 0.24 + k * 0.29, C['graphite_d'])
        return c
    if kind == 'stair':
        # 階段の段（上から見た斜めの面。段 1 つ = 0.4 m、縦は斜面の長さ 4 m）
        c = Canvas(4.0, 4.0)
        c.rgb[:] = src_region('shell_soft', 4.0, 4.0, contrast=0.5, mean=C['ivory2'])
        for k in range(10):
            y = 4.0 * k / 10
            c.rect(0, y, 4.0, y + 0.06, C['graphite'] * 1.2)
            c.rect(0, y + 0.06, 4.0, y + 0.14, C['shadow'] * 0.8)
        return c
    if kind in ('pave', 'pave2', 'ring'):
        c = Canvas(4.0, 4.0)
        mean = C['sand'] if kind == 'pave' else (C['ivory2'] if kind == 'pave2' else C['sand'] * 1.03)
        c.rgb[:] = src_region('shell_soft', 4.0, 4.0, contrast=0.6, mean=mean, ox=0.3 * seed)
        c.noise(0.14, 14, seed)
        if kind == 'ring':
            for k in range(1, 4):
                c.rect(0, 4.0 * k / 4 - 0.04, 4.0, 4.0 * k / 4 + 0.04, C['brass_d'])
        return c
    if kind == 'deck':
        c = Canvas(4.0, 4.0)
        c.rgb[:] = src_region('wood', 4.0, 4.0, contrast=0.8)
        return c
    if kind == 'coping':
        c = Canvas(2.0, 2.0)
        c.rgb[:] = C['graphite']
        c.noise(0.1, 6, seed)
        c.rect(0, 0.85, 2.0, 1.15, C['brass'])
        for xx in (0.5, 1.5):
            c.rect(xx - 0.05, 0.9, xx + 0.05, 1.1, C['brass_d'])
        return c
    raise KeyError(kind)


def cell_roof(kind: str, seed: int) -> Canvas:
    c = Canvas(4.0, 4.0)
    if kind in ('flat', 'flat2', 'gravel'):
        c.rgb[:] = src_region('shell_soft', 4.0, 4.0, contrast=0.45, mean=C['ivory2'] * (1.0 if kind != 'gravel' else 0.92), ox=seed)
        c.noise(0.18, 16, seed)
        if kind == 'flat2':
            c.rect(0.6, 0.8, 1.7, 1.6, C['graphite'])       # 天窓・通気口
            c.rect(0.7, 0.9, 1.6, 1.5, C['glass_hi'])
            c.rect(2.6, 2.6, 3.0, 3.0, C['graphite_d'])
    elif kind == 'tile':
        c.rgb[:] = C['tile']
        for k in range(12):
            y = 4.0 * k / 12
            c.grad(0, y, 4.0, y + 4.0 / 12, C['tile'] * 1.08, C['tile_d'])
            off = 0.0 if k % 2 else 0.17
            for j in range(13):
                xx = off + j * 0.34
                c.rect(xx - 0.015, y, xx + 0.015, y + 4.0 / 12, C['tile_d'] * 0.8)
        c.noise(0.12, 10, seed)
    elif kind == 'wood':
        c.rgb[:] = src_region('wood', 4.0, 4.0, contrast=0.8)
    elif kind == 'garden':
        c.rgb[:] = src_region('shell_soft', 4.0, 4.0, contrast=0.45, mean=C['ivory2'])
        rng = np.random.default_rng(seed)
        for k in range(14):
            c.ellipse(rng.uniform(0.3, 3.7), rng.uniform(0.3, 3.7), rng.uniform(0.25, 0.55), rng.uniform(0.25, 0.55),
                      C['green'] * rng.uniform(0.75, 1.1))
        for k in range(6):
            c.ellipse(rng.uniform(0.3, 3.7), rng.uniform(0.3, 3.7), 0.09, 0.09, C['tile'] * 1.1)
    elif kind == 'metal':
        c.rgb[:] = C['graphite'] * 1.15
        for k in range(16):
            xx = 4.0 * k / 16
            c.rect(xx, 0, xx + 0.08, 4.0, C['graphite_d'])
        c.noise(0.1, 8, seed)
    elif kind == 'tar':
        c.rgb[:] = src_region('shell_soft', 4.0, 4.0, contrast=0.4, mean=C['ivory2'] * 0.95)
        c.rect(0.4, 0.4, 3.6, 3.6, src_region('canvas', 3.2, 3.2, contrast=0.6, mean=C['linen'] * 0.9).mean((0, 1)))
        c.noise(0.2, 12, seed)
    return c


def cell_cloth(kind: str, seed: int) -> Canvas:
    c = Canvas(2.0, 2.0)
    red = src_region('canvas', 2.0, 2.0, contrast=0.8, mean=C['rust'])
    if kind in ('stripe', 'stripe2'):
        lin = src_region('canvas', 2.0, 2.0, contrast=0.6, mean=C['linen'])
        c.rgb[:] = red
        n = 4 if kind == 'stripe' else 6
        for k in range(n):
            x0 = 2.0 * (2 * k + 1) / (2 * n)
            r0, r1, c0, c1 = c._px(x0, 0, x0 + 2.0 / (2 * n), 2.0)
            c.rgb[:, c0:c1] = lin[:, c0:c1]
    elif kind == 'red':
        c.rgb[:] = red
    elif kind == 'dark':
        c.rgb[:] = src_region('canvas', 2.0, 2.0, contrast=0.8, mean=C['cloth2'])
    elif kind == 'linen':
        c.rgb[:] = src_region('canvas', 2.0, 2.0, contrast=0.6, mean=C['linen'])
    elif kind in ('banner', 'banner2'):
        base = red if kind == 'banner' else src_region('canvas', 2.0, 2.0, contrast=0.6, mean=C['linen'])
        c.rgb[:] = base
        em = C['brass'] if kind == 'banner' else C['rust']
        c.rect(0.0, 1.75, 2.0, 2.0, C['graphite'])
        c.ellipse(1.0, 1.15, 0.5, 0.5, em)
        c.ellipse(1.0, 1.15, 0.33, 0.33, base.mean((0, 1)))
        c.ellipse(1.0, 1.15, 0.16, 0.16, em)
        c.rect(0.2, 0.35, 1.8, 0.42, em)
    elif kind == 'white':
        c.rgb[:] = src_region('canvas', 2.0, 2.0, contrast=0.4, mean=np.array([0.93, 0.92, 0.9], np.float32))
    return c


def cell_mat(kind: str, seed: int) -> Canvas:
    c = Canvas(2.0, 2.0)
    if kind == 'graphite':
        c.rgb[:] = C['graphite']
        c.noise(0.12, 8, seed)
    elif kind == 'brass':
        c.rgb[:] = C['brass']
        c.noise(0.15, 8, seed)
        c.rect(0, 1.9, 2.0, 2.0, C['brass_d'])
    elif kind == 'wood':
        c.rgb[:] = src_region('wood', 2.0, 2.0, contrast=0.8)
    elif kind in ('green', 'green2'):
        rng = np.random.default_rng(seed)
        c.rgb[:] = C['green_d'] * (0.9 if kind == 'green' else 0.75)
        for k in range(60):
            col = C['green'] * rng.uniform(0.7, 1.25)
            if kind == 'green2' and k % 9 == 0:
                col = [C['tile'] * 1.2, C['brass'] * 1.2, C['linen']][k % 3]
            c.ellipse(rng.uniform(0, 2), rng.uniform(0, 2), rng.uniform(0.08, 0.22), rng.uniform(0.08, 0.2), col)
    elif kind == 'rust':
        c.rgb[:] = src_region('rust', 2.0, 2.0, contrast=0.7)
    elif kind == 'ivory':
        c.rgb[:] = src_region('shell_soft', 2.0, 2.0, contrast=0.4, mean=C['ivory'])
    elif kind == 'dark':
        c.rgb[:] = C['dark']
    return c


def cell_emit(kind: str, seed: int) -> Canvas:
    c = Canvas(1.0, 1.0)
    if kind == 'amber':
        c.rgb[:] = C['amber']
        c.a[:] = 1.0
    elif kind == 'lit':
        c.rgb[:] = C['warm'] * 0.8
        c.a[:] = 1.0
    elif kind == 'slit':
        c.rgb[:] = C['graphite']
        c.rect(0.35, 0.1, 0.65, 0.9, C['amber'] * 0.8, glow=1.0)
    elif kind == 'lantern':
        c.rgb[:] = C['brass']
        c.rect(0.15, 0.15, 0.85, 0.85, C['amber'], glow=1.0)
    return c


def build(out_path: str) -> np.ndarray:
    """帳を描いて PNG に書く。返り値は RGBA（0〜1）"""
    from PIL import Image
    atlas = np.zeros((SIZE, SIZE, 4), np.float32)
    makers = {'up': cell_up, 'gr': cell_ground, 'lm': cell_landmark, 'st': cell_struct, 'rf': cell_roof, 'cl': cell_cloth,
              'mt': cell_mat, 'em': cell_emit}
    for name, (col, row) in CELLS.items():
        pre, kind = name.split('_', 1)
        cv = makers[pre](kind, seed=col * 7 + row * 13)
        rgba = np.concatenate([np.clip(cv.rgb, 0, 1), np.clip(cv.a, 0, 1)[..., None]], -1)
        padded = np.pad(rgba, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='wrap')
        atlas[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL] = padded
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    Image.fromarray((atlas * 255 + 0.5).astype(np.uint8), 'RGBA').save(out_path, optimize=True)
    return atlas


def preview(atlas: np.ndarray, path: str) -> None:
    """確かめの画像：左に色、右に光る所（A）"""
    from PIL import Image
    rgb = (atlas[..., :3] * 255).astype(np.uint8)
    a = (np.repeat(atlas[..., 3:4], 3, -1) * 255).astype(np.uint8)
    im = Image.fromarray(np.concatenate([rgb, a], 1))
    im.save(path, quality=90)
