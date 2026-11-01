"""背の上の遠くの町（キットの部品 ordo_town・ordo_back）を、町のキットと同じ絵（白磁の壁と黒鉛の枠、真鍮の帯、赤錆の帆布、板）で作る。

前（town_backdrop.py の箱の家）は「白い箱に赤い蓋と黒い塔」で、オープニングの町の上・停止の夜の見下ろしで町に見えなかった（W2_オルド3D化の結果.md 11.10）。
ここでは本物の部屋（content/areas/ch1_town.json）の並びに合わせて、3 つの段・段の間の擁壁と階段・広場の輪・市場の露店・工房と食堂・
町長の家とギルド・塔・街灯を、1 間 × 1 階ごとの正面の絵（窓・扉・店・雨戸・バルコニー）で組む。

  ordo_town：船首の頭の上の部屋（オープニング）と停止の場面の舞台から見る背の町の全体（z -114〜+95）
  ordo_back：中段・下段の部屋の胸壁の向こう（z -114〜-57。中段の部屋の下の段の家並み（〜-54）と重ならない）。ordo_town の南の区画と同じ形

作り：面は四角形 1 つ = 絵の帳の升目 1 つ（town_far_atlas.py、1024 × 1024、128 画素 × 8 × 8）。材質は 1 つ（"far"）で、ゲームは
OrdoView がシェーダー assets/shaders/town_far.gdshader に置き換える（描画は部品 1 つで 1 回）。頂点の色：RGB = 家ごとの色（線形の倍率。
白磁・生成り・砂色・薄い赤土など）と足元の陰、A = 夜の灯の順（0 = 光らない。0〜1 の値が、停止の場面の「消えた割合」を超えている間だけ光る）。
灯の点（TownLights）の位置は ordo_town_lights.json に書く（光る窓・街灯・塔の灯。同じ灯の順なので、窓と点が一緒に消える）。
座標はオルドの座標（原点 = 背の歩行面の真ん中、+Z が船首、+X が左舷）。GLB は numpy で直に書く（Blender は使わない）。

  .venv-blender/bin/python tools/blender/kit/town_far.py              帳・ordo_town・ordo_back・灯の表を作る
  .venv-blender/bin/python tools/blender/kit/town_far.py --atlas-only 帳だけ（build/kit_town/far_atlas_preview.jpg も）
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import town_far_atlas as A  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.environ.get('FAR_OUT') or os.path.join(REPO, 'godot', 'assets', 'kit', 'town')
ATLAS = os.path.join(os.environ['FAR_OUT'], 'town_far.png') if os.environ.get('FAR_OUT') else \
    os.path.join(REPO, 'godot', 'assets', 'kit', 'tex', 'town_far.png')
WORK = os.path.join(REPO, 'build', 'kit_town')

ST = A.H_ST          # 1 階の高さ（3.2 m）
BAY = A.W_BAY        # 1 間（3.0 m）
LOW, MID, UP = 1.5, 6.5, 11.5          # 下・中・上の段の床の高さ（背の面から。部屋の床と同じ）
TOWN_X = 48.5                          # 町の東西の端（段の床の端。部屋の東西の低い壁 |x| 48.5〜49）
STERN_Z = -114.0                       # 町の南の端（背の面は z -118 から持ち上がる）
BACK_Z = -57.0                         # ordo_back の北の端（中段の部屋の下の段の家並み lower_block は z -54 まで）
MID_S, MID_N = -14.5, 16.0             # 中段の広場の南の胸壁・北の段の擁壁（中段の部屋）
GATE_Z = 34.0                          # 北の階段の門（上の段の広場の南の端）
BOW_Z = 95.0                           # 上の段の北の端（船首の頭の手前）
PARA = 0.45                            # 屋上の縁の低い壁の高さ
NO_LIGHT = 0.0


def _lin(h: str) -> np.ndarray:
    h = h.lstrip('#')
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# 壁の色（絵の色に掛ける倍率。sRGB で書いて線形にする）：白磁を主に、生成り・砂色・薄い赤土・灰白・黄土を少し（絵の町の家の色の幅）
WALL_TINTS = [(_lin(h), w) for h, w in (('#FFFFFF', 5), ('#FBF1DE', 4), ('#F4E0C4', 3), ('#F7D9C6', 2), ('#E8E6E0', 2),
                                        ('#F0D7A6', 1.5), ('#E9C9AE', 1))]
WHITE = np.ones(3)


# ---------------------------------------------------------------- メッシュ（四角形と三角形をためる）

class Mesh:
    def __init__(self, name: str):
        self.name = name
        self.P: list = []
        self.N: list = []
        self.UV: list = []
        self.C: list = []
        self.I: list = []

    def poly(self, pts, uvs, cols, normal=None):
        """凸の多角形（外から見て反時計回り）。cols は頂点ごとの RGBA か 1 つの RGBA"""
        pts = [np.asarray(p, float) for p in pts]
        if normal is None:
            n = np.zeros(3)
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
            ln = np.linalg.norm(n)
            if ln < 1e-9:
                return
            normal = n / ln
        cols = cols if isinstance(cols, list) else [cols] * len(pts)
        base = len(self.P)
        self.P += pts
        self.UV += list(uvs)
        self.C += [np.asarray(c, float) for c in cols]
        self.N += [np.asarray(normal, float)] * len(pts)
        for k in range(1, len(pts) - 1):
            self.I += [base, base + k, base + k + 1]

    def quad(self, p0, p1, p2, p3, cell, col, sub=(0.0, 0.0, 1.0, 1.0), shade=(1.0, 1.0, 1.0, 1.0)):
        """p0 左下・p1 右下・p2 右上・p3 左上（外から見て）。sub = 升目の中の (左, 下, 右, 上) の割合。shade = 頂点ごとの明るさ"""
        u0, v0, u1, v1 = A.uv_rect(cell)
        s0, t0, s1, t1 = sub
        uv = lambda s, t: (u0 + (u1 - u0) * s, v1 - (v1 - v0) * t)  # noqa: E731
        col = np.asarray(col, float)
        cols = [np.array([*(col[:3] * k), col[3]]) for k in shade]
        self.poly([p0, p1, p2, p3], [uv(s0, t0), uv(s1, t0), uv(s1, t1), uv(s0, t1)], cols)

    def tris(self) -> int:
        return len(self.I) // 3

    def merge(self, other: 'Mesh'):
        base = len(self.P)
        self.P += other.P
        self.N += other.N
        self.UV += other.UV
        self.C += other.C
        self.I += [i + base for i in other.I]


def rgba(tint, order=NO_LIGHT):
    return np.array([*tint, order])


# ---------------------------------------------------------------- 形の道具

def wall(m: Mesh, a, b, y0, y1, cell, col, sub=(0, 0, 1, 1), shade_lo=1.0, shade_hi=1.0):
    """a → b（(x, z)、外から見て左 → 右）の縦の面。外向きの法線は (-dz, 0, dx)"""
    p0 = (a[0], y0, a[1])
    p1 = (b[0], y0, b[1])
    p2 = (b[0], y1, b[1])
    p3 = (a[0], y1, a[1])
    m.quad(p0, p1, p2, p3, cell, col, sub, (shade_lo, shade_lo, shade_hi, shade_hi))


def strip(m: Mesh, a, b, y0, y1, cell, col, cell_w, shade_lo=1.0, shade_hi=1.0, sub_t=(0.0, 1.0)):
    """長い面を cell_w m ごとの升目に分けて貼る（絵の大きさをそろえる）"""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(round(L / cell_w)))
    for i in range(n):
        pa = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
        pb = (a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n)
        wall(m, pa, pb, y0, y1, cell, col, (0.0, sub_t[0], 1.0, sub_t[1]), shade_lo, shade_hi)


def floor(m: Mesh, x0, x1, z0, z1, y, cell, col, cell_m=4.0, up=True):
    """水平の面（上向き。up=False で下向き）を cell_m ごとの升目に分ける（端は升目の一部）"""
    nx = max(1, int(math.ceil((x1 - x0) / cell_m - 0.25)))
    nz = max(1, int(math.ceil((z1 - z0) / cell_m - 0.25)))
    for i in range(nx):
        for j in range(nz):
            a0, a1 = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            b0, b1 = z0 + (z1 - z0) * j / nz, z0 + (z1 - z0) * (j + 1) / nz
            fs, ft = min(1.0, (a1 - a0) / cell_m), min(1.0, (b1 - b0) / cell_m)
            if up:
                m.quad((a0, y, b1), (a1, y, b1), (a1, y, b0), (a0, y, b0), cell, col, (0, 0, fs, ft))
            else:
                m.quad((a0, y, b0), (a1, y, b0), (a1, y, b1), (a0, y, b1), cell, col, (0, 0, fs, ft))


def box(m: Mesh, x0, x1, y0, y1, z0, z1, cell, col, top_cell=None, faces='nsewt', cell_w=None, shade_lo=1.0):
    """箱（横の面は cell、上は top_cell）。faces：n(+z) s(-z) e(+x) w(-x) t(上)"""
    cw = cell_w or 1e9
    if 'n' in faces:
        strip(m, (x0, z1), (x1, z1), y0, y1, cell, col, cw, shade_lo)
    if 'e' in faces:
        strip(m, (x1, z1), (x1, z0), y0, y1, cell, col, cw, shade_lo)
    if 's' in faces:
        strip(m, (x1, z0), (x0, z0), y0, y1, cell, col, cw, shade_lo)
    if 'w' in faces:
        strip(m, (x0, z0), (x0, z1), y0, y1, cell, col, cw, shade_lo)
    if 't' in faces:
        floor(m, x0, x1, z0, z1, y1, top_cell or cell, col, cell_m=cw if cell_w else 4.0)


def cylinder(m: Mesh, cx, cz, y0, y1, r, cell, col, segs=8, top_cell=None, top=True):
    for k in range(segs):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * (k + 1) / segs
        pa = (cx + r * math.cos(a1), cz + r * math.sin(a1))
        pb = (cx + r * math.cos(a0), cz + r * math.sin(a0))
        wall(m, pa, pb, y0, y1, cell, col, (k / segs, 0, (k + 1) / segs, 1))
    if top:
        u0, v0, u1, v1 = A.uv_rect(top_cell or cell)
        pts = [(cx + r * math.cos(2 * math.pi * k / segs), y1, cz + r * math.sin(2 * math.pi * k / segs)) for k in range(segs)][::-1]
        uvs = [(u0 + (u1 - u0) * (0.5 + 0.5 * math.cos(2 * math.pi * k / segs)), v0 + (v1 - v0) * (0.5 + 0.5 * math.sin(2 * math.pi * k / segs)))
               for k in range(segs)][::-1]
        m.poly(pts, uvs, np.asarray(col, float))


def cone(m: Mesh, cx, cz, y0, y1, r, cell, col, segs=8):
    u0, v0, u1, v1 = A.uv_rect(cell)
    for k in range(segs):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * (k + 1) / segs
        m.poly([(cx + r * math.cos(a1), y0, cz + r * math.sin(a1)), (cx + r * math.cos(a0), y0, cz + r * math.sin(a0)), (cx, y1, cz)],
               [(u0, v1), (u1, v1), ((u0 + u1) / 2, v0)], np.asarray(col, float))


def blob(m: Mesh, cx, cy, cz, rx, ry, rz, cell, col, seed=0):
    """木の葉・植え込みの塊（つぶれた八面体を 1 段細かくした 16 面）"""
    rng = np.random.default_rng(abs(int(seed)))
    u0, v0, u1, v1 = A.uv_rect(cell)
    ring = []
    for k in range(6):
        a = 2 * math.pi * (k + rng.uniform(-0.15, 0.15)) / 6
        ring.append(np.array([cx + rx * math.cos(a) * rng.uniform(0.85, 1.1), cy + ry * rng.uniform(-0.1, 0.15), cz + rz * math.sin(a) * rng.uniform(0.85, 1.1)]))
    top = np.array([cx, cy + ry, cz])
    bot = np.array([cx, cy - ry * 0.7, cz])
    col = np.asarray(col, float)
    for k in range(6):
        a, b = ring[k], ring[(k + 1) % 6]
        uvs = [(u0 + (u1 - u0) * k / 6, v1), (u0 + (u1 - u0) * (k + 1) / 6, v1), ((u0 + u1) / 2, v0)]
        m.poly([b, a, top], uvs, col)
        dark = np.array([*(col[:3] * 0.7), col[3]])
        m.poly([a, b, bot], uvs, dark)


def tree(m: Mesh, x, y, z, h, seed):
    seed = abs(int(seed))
    rng = np.random.default_rng(seed)
    box(m, x - 0.12, x + 0.12, y, y + h * 0.5, z - 0.12, z + 0.12, 'mt_wood', rgba(WHITE), faces='nsew')
    r = h * rng.uniform(0.28, 0.36)
    blob(m, x, y + h * 0.66, z, r, h * 0.3, r, 'mt_green' if rng.random() < 0.7 else 'mt_green2', rgba(WHITE), seed)


def pot_plants(m: Mesh, x0, x1, z, y, rng, out=+1):
    """縁に並べた鉢植え（小さな緑の塊）"""
    x = x0 + 0.6
    while x < x1 - 0.5:
        blob(m, x, y + 0.35, z, 0.35, 0.35, 0.35, 'mt_green2' if rng.random() < 0.4 else 'mt_green', rgba(WHITE), int(rng.integers(1 << 30)))
        x += rng.uniform(1.0, 2.2)


# ---------------------------------------------------------------- 家

class Lights:
    """灯の点の表（TownLights）：[x, y, z, 灯の順, 種類]（種類 0 = 窓、1 = 街灯、2 = 塔・目印の灯）"""

    def __init__(self):
        self.pts: list = []

    def add(self, p, order, kind):
        self.pts.append([round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2), round(float(order), 3), kind])


GROUND_HOUSE = ['gr_win', 'gr_plain', 'gr_win', 'gr_goods', 'gr_shutter', 'gr_plain']
GROUND_SHOP = ['gr_shop', 'gr_goods', 'gr_shop', 'gr_win']
UP_SETS = [['up_win', 'up_win', 'up_flower'], ['up_win2', 'up_win2', 'up_pipes'], ['up_balcony', 'up_win', 'up_win'],
           ['up_arch', 'up_arch', 'up_panel'], ['up_win', 'up_shut', 'up_win2'], ['up_flower', 'up_balcony', 'up_win']]
GLOW = {'up_win', 'up_win2', 'up_balcony', 'up_arch', 'up_pipes', 'up_flower', 'gr_door', 'gr_shop', 'gr_win', 'gr_archdoor',
        'gr_goods', 'gr_plain', 'gr_shutter', 'gr_door2', 'lm_guild', 'lm_mayor', 'lm_tower', 'lm_workshop', 'lm_diner', 'st_ret_door'}


class House:
    def __init__(self, x0, x1, z0, z1, y0, storeys, rng, kind='house', roof=None, tint=None, order=None, faces='nsew'):
        self.x0, self.x1, self.z0, self.z1, self.y0 = x0, x1, z0, z1, y0
        self.n = storeys
        self.kind = kind
        self.rng = rng
        self.top = y0 + storeys * ST
        self.tint = tint if tint is not None else pick_tint(rng)
        self.order = order if order is not None else float(rng.uniform(0.03, 1.0))
        self.roof = roof or pick_roof(rng)
        self.faces = faces
        self.ups = UP_SETS[int(rng.integers(len(UP_SETS)))]
        self.lit = float(rng.uniform(0.45, 0.8))


def pick_tint(rng):
    w = np.array([t[1] for t in WALL_TINTS])
    return WALL_TINTS[int(rng.choice(len(WALL_TINTS), p=w / w.sum()))][0]


def pick_roof(rng):
    r = rng.random()
    return 'tile' if r < 0.2 else ('garden' if r < 0.32 else ('flat2' if r < 0.55 else ('wood' if r < 0.63 else 'flat')))


def facade(m: Mesh, h: House, a, b, lights: Lights, from_st=0, ground='house', door=True, street=True):
    """家の 1 つの面（a → b、外から見て左 → 右）を 1 間 × 1 階の升目で。1 階は扉・店・窓、上の階は家ごとの窓の組。
    光る升目は家の灯の順（h.order）を頂点の色の A に入れ、窓の灯の点を表に足す"""
    rng = h.rng
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L < 0.8:
        return
    nb = max(1, int(round(L / BAY)))
    nx, nz = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
    door_i = int(rng.integers(nb)) if door else -1
    for s in range(from_st, h.n):
        y0 = h.y0 + s * ST
        for i in range(nb):
            pa = (a[0] + (b[0] - a[0]) * i / nb, a[1] + (b[1] - a[1]) * i / nb)
            pb = (a[0] + (b[0] - a[0]) * (i + 1) / nb, a[1] + (b[1] - a[1]) * (i + 1) / nb)
            if s == 0:
                if i == door_i:
                    cell = 'gr_door' if ground != 'shop' or rng.random() < 0.4 else 'gr_door2'
                elif ground == 'shop':
                    cell = GROUND_SHOP[int(rng.integers(len(GROUND_SHOP)))]
                elif ground == 'blank':
                    cell = 'gr_plain'
                else:
                    cell = GROUND_HOUSE[int(rng.integers(len(GROUND_HOUSE)))]
            else:
                cell = h.ups[int(rng.integers(len(h.ups)))]
            lit = cell in GLOW and (rng.random() < h.lit or cell in ('gr_door', 'gr_shop', 'gr_door2'))
            order = h.order if lit else NO_LIGHT
            # 足元の陰（1 階の下の端を暗く）と上の階ほど少し明るく
            lo = 0.72 if s == 0 else 0.97 + 0.01 * s
            hi = 0.95 if s == 0 else 1.0
            wall(m, pa, pb, y0, y0 + ST, cell, rgba(h.tint, order), shade_lo=lo, shade_hi=hi)
            if lit and street and cell.startswith('up_') or (lit and street and cell in ('gr_shop', 'gr_door2')):
                cx, cz = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
                lights.add((cx + nx * 0.25, y0 + 1.7, cz + nz * 0.25), h.order, 0)


def parapet(m: Mesh, h: House, sides='nsew'):
    """屋上の縁：外の面（壁の続き）・上の笠木（黒鉛と真鍮。上から見て家の輪郭）・内の面"""
    x0, x1, z0, z1, top = h.x0, h.x1, h.z0, h.z1, h.top
    t = 0.28
    col = rgba(h.tint)
    y1 = top + PARA
    edges = {'n': ((x0, z1), (x1, z1)), 'e': ((x1, z1), (x1, z0)), 's': ((x1, z0), (x0, z0)), 'w': ((x0, z0), (x0, z1))}
    for k, (a, b) in edges.items():
        if k in sides:
            wall(m, a, b, top, y1, 'mt_ivory', col, (0, 0, min(1.0, math.dist(a, b) / 2.0), 0.22))
    # 笠木（上の面の帯）
    for (a0, a1, b0, b1) in ((x0, x1, z1 - t, z1), (x0, x1, z0, z0 + t), (x0, x0 + t, z0 + t, z1 - t), (x1 - t, x1, z0 + t, z1 - t)):
        m.quad((a0, y1, b1), (a1, y1, b1), (a1, y1, b0), (a0, y1, b0), 'st_coping', rgba(WHITE), (0, 0.3, min(1.0, (a1 - a0) / 2), 0.7))
    # 内の面（屋根から笠木まで。暗め）
    ry = top + 0.08
    inner = {'n': ((x1 - t, z1 - t), (x0 + t, z1 - t)), 's': ((x0 + t, z0 + t), (x1 - t, z0 + t)),
             'e': ((x1 - t, z0 + t), (x1 - t, z1 - t)), 'w': ((x0 + t, z1 - t), (x0 + t, z0 + t))}
    for k, (a, b) in inner.items():
        wall(m, a, b, ry, y1, 'mt_ivory', col, (0, 0, min(1.0, math.dist(a, b) / 2.0), 0.18), 0.7, 0.85)


def hip_roof(m: Mesh, h: House, cell='rf_tile'):
    """瓦の寄棟（四角い家の上に、長い辺に沿った棟）"""
    x0, x1, z0, z1 = h.x0 - 0.3, h.x1 + 0.3, h.z0 - 0.3, h.z1 + 0.3
    y = h.top
    w, d = x1 - x0, z1 - z0
    rise = min(w, d) * 0.38
    u0, v0, u1, v1 = A.uv_rect(cell)
    col = rgba(WHITE)
    if w >= d:
        ra, rb = (x0 + d / 2, z0 + d / 2), (x1 - d / 2, z0 + d / 2)
        faces = [([(x0, y, z1), (x1, y, z1), (rb[0], y + rise, rb[1]), (ra[0], y + rise, ra[1])], w),
                 ([(x1, y, z0), (x0, y, z0), (ra[0], y + rise, ra[1]), (rb[0], y + rise, rb[1])], w),
                 ([(x1, y, z1), (x1, y, z0), (rb[0], y + rise, rb[1])], d), ([(x0, y, z0), (x0, y, z1), (ra[0], y + rise, ra[1])], d)]
    else:
        ra, rb = (x0 + w / 2, z0 + w / 2), (x0 + w / 2, z1 - w / 2)
        faces = [([(x1, y, z1), (x1, y, z0), (ra[0], y + rise, ra[1]), (rb[0], y + rise, rb[1])], d),
                 ([(x0, y, z0), (x0, y, z1), (rb[0], y + rise, rb[1]), (ra[0], y + rise, ra[1])], d),
                 ([(x0, y, z1), (x1, y, z1), (rb[0], y + rise, rb[1])], w), ([(x1, y, z0), (x0, y, z0), (ra[0], y + rise, ra[1])], w)]
    for pts, L in faces:
        s = min(1.0, L / 3.0)
        if len(pts) == 4:
            e = math.dist((pts[0][0], pts[0][2]), (pts[1][0], pts[1][2]))
            r = math.dist((pts[3][0], pts[3][2]), (pts[2][0], pts[2][2]))
            k = (1 - r / max(e, 1e-6)) / 2
            uvs = [(u0, v1), (u0 + (u1 - u0) * s, v1), (u0 + (u1 - u0) * s * (1 - k), v0), (u0 + (u1 - u0) * s * k, v0)]
        else:
            uvs = [(u0, v1), (u0 + (u1 - u0) * s, v1), (u0 + (u1 - u0) * s / 2, v0)]
        m.poly(pts, uvs, col)
    # 軒の下の黒鉛の帯（下から見える縁）
    for a, b in (((h.x0, h.z1), (h.x1, h.z1)), ((h.x1, h.z1), (h.x1, h.z0)), ((h.x1, h.z0), (h.x0, h.z0)), ((h.x0, h.z0), (h.x0, h.z1))):
        wall(m, a, b, y - 0.01, y + 0.3, 'st_coping', col, (0, 0.6, 1, 0.75))


def roof(m: Mesh, h: House, lights: Lights, sides='nsew'):
    """屋根（瓦の寄棟か、縁のある平らな屋根と屋上の物：日よけ・給水塔・煙突・鉢植え・洗濯物）"""
    rng = h.rng
    if h.roof == 'tile':
        hip_roof(m, h)
        return
    parapet(m, h, sides)
    t = 0.28
    cell = {'flat': 'rf_flat', 'flat2': 'rf_flat2', 'garden': 'rf_garden', 'wood': 'rf_wood', 'metal': 'rf_metal'}.get(h.roof, 'rf_flat')
    floor(m, h.x0 + t, h.x1 - t, h.z0 + t, h.z1 - t, h.top + 0.08, cell, rgba(WHITE), 4.0)
    w, d = h.x1 - h.x0, h.z1 - h.z0
    cx, cz = (h.x0 + h.x1) / 2, (h.z0 + h.z1) / 2
    r = rng.random()
    y = h.top + 0.08
    if h.roof == 'garden':
        for k in range(int(rng.integers(1, 3))):
            tree(m, cx + rng.uniform(-w, w) * 0.25, y, cz + rng.uniform(-d, d) * 0.25, rng.uniform(2.2, 3.4), int(rng.integers(1 << 30)))
    if r < 0.32 and w > 3.5 and d > 3.5:
        canopy(m, cx - w * 0.3, cx + w * 0.3, cz - d * 0.3, cz + d * 0.3, y, rng.uniform(2.0, 2.4), rng)
    elif r < 0.5:
        water_tank(m, cx + w * rng.uniform(-0.2, 0.2), cz + d * rng.uniform(-0.2, 0.2), y, rng.uniform(0.7, 1.1), rng)
    elif r < 0.62:
        for k in range(int(rng.integers(1, 3))):
            px, pz = cx + rng.uniform(-w, w) * 0.3, cz + rng.uniform(-d, d) * 0.3
            box(m, px - 0.2, px + 0.2, y, y + rng.uniform(1.2, 2.4), pz - 0.2, pz + 0.2, 'mt_graphite', rgba(WHITE), faces='nsewt')
    elif r < 0.72:
        # 屋上の小屋（階段の出口）：屋根に上る戸
        sx0 = cx + rng.uniform(-0.3, 0.1) * w
        sz0 = cz + rng.uniform(-0.3, 0.1) * d
        hh = House(sx0, sx0 + 2.4, sz0, sz0 + 2.2, y, 1, rng, tint=h.tint, order=h.order, roof='flat')
        hh.top = y + 2.4
        for a, b in (((hh.x0, hh.z1), (hh.x1, hh.z1)), ((hh.x1, hh.z1), (hh.x1, hh.z0)), ((hh.x1, hh.z0), (hh.x0, hh.z0)), ((hh.x0, hh.z0), (hh.x0, hh.z1))):
            wall(m, a, b, y, y + 2.4, 'gr_door' if a == (hh.x0, hh.z1) else 'mt_ivory', rgba(h.tint), (0, 0, 1, 0.75), 0.8, 1.0)
        floor(m, hh.x0 - 0.15, hh.x1 + 0.15, hh.z0 - 0.15, hh.z1 + 0.15, y + 2.4, 'mt_graphite', rgba(WHITE), 2.0)
    if rng.random() < 0.35 and h.roof != 'garden':
        pot_plants(m, h.x0 + 0.3, h.x1 - 0.3, h.z1 - 0.7, y, rng)


def canopy(m: Mesh, x0, x1, z0, z1, y, hgt, rng):
    """屋上の帆布の日よけ（柱 2 本と、縞か無地の布。下の面は暗い布）"""
    cell = ['cl_stripe', 'cl_red', 'cl_stripe2', 'cl_linen'][int(rng.integers(4))]
    y1 = y + hgt
    for px, pz in ((x0 + 0.1, z0 + 0.1), (x1 - 0.1, z1 - 0.1), (x0 + 0.1, z1 - 0.1), (x1 - 0.1, z0 + 0.1)):
        box(m, px - 0.06, px + 0.06, y, y1, pz - 0.06, pz + 0.06, 'mt_graphite', rgba(WHITE), faces='nsew')
    sag = 0.12
    m.quad((x0, y1, z1), (x1, y1, z1), (x1, y1 - sag, z0), (x0, y1 - sag, z0), cell, rgba(WHITE), (0, 0, 1, 1))
    m.quad((x0, y1 - sag, z0), (x1, y1 - sag, z0), (x1, y1, z1), (x0, y1, z1), 'cl_dark', rgba(WHITE * 0.7), (0, 0, 1, 1))


def water_tank(m: Mesh, cx, cz, y, r, rng, legs=1.4):
    """真鍮の水槽（脚つき、黒鉛のふた）"""
    for dx, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        px, pz = cx + dx * r * 0.65, cz + dz * r * 0.65
        box(m, px - 0.07, px + 0.07, y, y + legs, pz - 0.07, pz + 0.07, 'mt_graphite', rgba(WHITE), faces='nsew')
    cylinder(m, cx, cz, y + legs, y + legs + r * 1.6, r, 'mt_brass', rgba(WHITE), 8, top=False)
    cone(m, cx, cz, y + legs + r * 1.6, y + legs + r * 2.0, r * 1.06, 'mt_graphite', rgba(WHITE), 8)


def awning(m: Mesh, a, b, y, depth, drop, rng, cell=None):
    """1 階の正面の日よけ（a → b の面から depth 出て drop 下がる帆布、前の垂れ。下の面は暗い布）"""
    cell = cell or ['cl_stripe', 'cl_red', 'cl_dark', 'cl_stripe2'][int(rng.integers(4))]
    L = math.dist(a, b)
    nx, nz = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
    n = max(1, int(round(L / 2.0)))
    for i in range(n):
        pa = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
        pb = (a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n)
        fa = (pa[0] + nx * depth, pa[1] + nz * depth)
        fb = (pb[0] + nx * depth, pb[1] + nz * depth)
        y1 = y - drop
        m.quad((fa[0], y1, fa[1]), (fb[0], y1, fb[1]), (pb[0], y, pb[1]), (pa[0], y, pa[1]), cell, rgba(WHITE))
        m.quad((pa[0], y, pa[1]), (pb[0], y, pb[1]), (fb[0], y1, fb[1]), (fa[0], y1, fa[1]), 'cl_dark', rgba(WHITE * 0.55))
        wall(m, fa, fb, y1 - 0.35, y1, cell, rgba(WHITE * 0.9), (0, 0, 1, 0.2))
        wall(m, fb, fa, y1 - 0.35, y1, 'cl_dark', rgba(WHITE * 0.5), (0, 0, 1, 0.2))


def banner(m: Mesh, a, b, y_top, length, cell=None, rng=None):
    """壁に下げた縦の旗（a → b の面から 0.08 m 前）"""
    cell = cell or ('cl_banner' if rng is None or rng.random() < 0.6 else 'cl_banner2')
    L = math.dist(a, b)
    nx, nz = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
    fa = (a[0] + nx * 0.1, a[1] + nz * 0.1)
    fb = (b[0] + nx * 0.1, b[1] + nz * 0.1)
    wall(m, fa, fb, y_top - length, y_top, cell, rgba(WHITE))
    wall(m, fb, fa, y_top - length, y_top, 'cl_dark', rgba(WHITE * 0.6))
    box(m, min(fa[0], fb[0]) - 0.05, max(fa[0], fb[0]) + 0.05, y_top, y_top + 0.1, min(fa[1], fb[1]) - 0.05, max(fa[1], fb[1]) + 0.05,
        'mt_brass', rgba(WHITE), faces='nsewt')


def lamp_post(m: Mesh, lights: Lights, x, y, z, rng, h=3.6):
    """街灯（黒鉛の柱と琥珀の灯。灯の点も足す）"""
    order = float(rng.uniform(0.03, 1.0))
    box(m, x - 0.09, x + 0.09, y, y + h, z - 0.09, z + 0.09, 'mt_graphite', rgba(WHITE), faces='nsew')
    box(m, x - 0.22, x + 0.22, y + h, y + h + 0.45, z - 0.22, z + 0.22, 'em_lantern', rgba(WHITE, order), faces='nsew')
    floor(m, x - 0.3, x + 0.3, z - 0.3, z + 0.3, y + h + 0.45, 'mt_graphite', rgba(WHITE), 1.0)
    lights.add((x, y + h + 0.22, z), order, 1)


def bunting(m: Mesh, a, b, y, sag_m, rng):
    """通りを渡る小旗の綱（三角の布を色を替えて並べる）"""
    L = math.dist(a, b)
    n = max(3, int(L / 0.9))
    cols = [_lin('#C8553C'), _lin('#E8DCC0'), _lin('#B08D4E'), _lin('#93432F'), _lin('#6E7A3C')]
    u0, v0, u1, v1 = A.uv_rect('cl_white')
    for i in range(n):
        t0, t1 = i / n, (i + 0.8) / n
        p = [np.array([a[0] + (b[0] - a[0]) * t, y - sag_m * 4 * t * (1 - t), a[1] + (b[1] - a[1]) * t]) for t in (t0, t1)]
        tip = (p[0] + p[1]) / 2 + np.array([0, -0.55, 0])
        col = rgba(cols[(i + int(rng.integers(5))) % 5] if rng.random() < 0.3 else cols[i % 5])
        m.poly([p[0], p[1], tip], [(u0, v0), (u1, v0), ((u0 + u1) / 2, v1)], col)
        m.poly([p[1], p[0], tip], [(u0, v0), (u1, v0), ((u0 + u1) / 2, v1)], col)


def laundry(m: Mesh, a, b, y, rng, sag_m=0.35):
    """洗濯物の綱（a → b、高さ y）：たるんだ綱に、生成り・赤・砂色の布を間をあけて吊る（両面）"""
    L = math.dist(a, b)
    n = max(2, int(L / 1.1))
    cols = [_lin('#EDE3CC'), _lin('#C8553C'), _lin('#E2CFA6'), _lin('#9BA7A0'), _lin('#F4EEE0')]
    for i in range(n):
        if rng.random() < 0.3:
            continue
        t0 = (i + 0.15) / n
        t1 = t0 + rng.uniform(0.45, 0.75) / n
        pa = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
        pb = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
        ya = y - sag_m * 4 * t0 * (1 - t0)
        yb = y - sag_m * 4 * t1 * (1 - t1)
        hgt = rng.uniform(0.5, 0.9)
        col = rgba(cols[int(rng.integers(len(cols)))])
        m.quad((pa[0], ya - hgt, pa[1]), (pb[0], yb - hgt, pb[1]), (pb[0], yb, pb[1]), (pa[0], ya, pa[1]), 'cl_white', col, (0, 0, 0.5, 0.5))
        m.quad((pb[0], yb - hgt, pb[1]), (pa[0], ya - hgt, pa[1]), (pa[0], ya, pa[1]), (pb[0], yb, pb[1]), 'cl_white', col * np.array([0.8, 0.8, 0.8, 1]),
               (0, 0, 0.5, 0.5))


def house(m: Mesh, h: House, lights: Lights, neighbours=(), street_faces='nsew', ground='house', awn=0.3, ban=0.12):
    """家の箱：見える面の正面（隣の家に隠れる所は、隣より高い階だけ）、屋根、日よけ・旗"""
    rng = h.rng
    edges = {'n': ((h.x0, h.z1), (h.x1, h.z1)), 'e': ((h.x1, h.z1), (h.x1, h.z0)), 's': ((h.x1, h.z0), (h.x0, h.z0)),
             'w': ((h.x0, h.z0), (h.x0, h.z1))}
    covered = {}
    for k in 'nsew':
        # 同じ面に接する隣の家の階の数（一番低いもの。半分以上覆うときだけ）
        cov = 0
        for o in neighbours:
            if k == 'n' and abs(o.z0 - h.z1) < 0.05 and min(o.x1, h.x1) - max(o.x0, h.x0) > 0.5 * (h.x1 - h.x0):
                cov = max(cov, o.n)
            if k == 's' and abs(o.z1 - h.z0) < 0.05 and min(o.x1, h.x1) - max(o.x0, h.x0) > 0.5 * (h.x1 - h.x0):
                cov = max(cov, o.n)
            if k == 'e' and abs(o.x0 - h.x1) < 0.05 and min(o.z1, h.z1) - max(o.z0, h.z0) > 0.5 * (h.z1 - h.z0):
                cov = max(cov, o.n)
            if k == 'w' and abs(o.x1 - h.x0) < 0.05 and min(o.z1, h.z1) - max(o.z0, h.z0) > 0.5 * (h.z1 - h.z0):
                cov = max(cov, o.n)
        covered[k] = cov
    for k, (a, b) in edges.items():
        if k not in h.faces:
            continue
        if covered[k] >= h.n:
            continue
        on_street = k in street_faces and covered[k] == 0
        facade(m, h, a, b, lights, from_st=covered[k], ground=ground if on_street else 'house', door=on_street, street=True)
        if on_street and h.n >= 1 and rng.random() < awn and math.dist(a, b) > 3.0:
            L = math.dist(a, b)
            s0 = rng.uniform(0.05, 0.3)
            s1 = min(1.0, s0 + rng.uniform(0.4, 0.7))
            pa = (a[0] + (b[0] - a[0]) * s0, a[1] + (b[1] - a[1]) * s0)
            pb = (a[0] + (b[0] - a[0]) * s1, a[1] + (b[1] - a[1]) * s1)
            awning(m, pa, pb, h.y0 + 2.75, rng.uniform(1.1, 1.6), 0.45, rng)
        if on_street and h.n >= 2 and rng.random() < ban:
            L = math.dist(a, b)
            s = rng.uniform(0.2, 0.75)
            pa = (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)
            pb = (a[0] + (b[0] - a[0]) * (s + 0.9 / L), a[1] + (b[1] - a[1]) * (s + 0.9 / L))
            banner(m, pa, pb, h.top - 0.3, min(2.6, h.n * ST - 3.0), rng=rng)
    roof(m, h, lights, sides=''.join(k for k in 'nsew' if covered[k] < h.n))


# ---------------------------------------------------------------- 区画（通りに挟まれた家の塊）

def block(m: Mesh, lights: Lights, x0, x1, z0, z1, y, rng, storeys=(1, 3), lot=(4.5, 8.0), streets='nsew', ground='house',
          skip=None, awn=0.3, tall=0.0):
    """x0〜x1・z0〜z1 の区画を家で埋める。長い辺に沿って間口 lot の家を並べ、奥行きが 11 m を超えたら背中合わせの 2 列。
    streets：通りに面した辺（扉・店・日よけを付ける）。skip(x, z) が真の所には建てない（広場・目印の建物の場所）"""
    houses = []
    along_x = (x1 - x0) >= (z1 - z0)
    depth = (z1 - z0) if along_x else (x1 - x0)
    rows = 2 if depth > 11.0 else 1
    for r in range(rows):
        if along_x:
            ra, rb = (z0 + depth * r / rows, z0 + depth * (r + 1) / rows)
        else:
            ra, rb = (x0 + depth * r / rows, x0 + depth * (r + 1) / rows)
        pos = x0 if along_x else z0
        end = x1 if along_x else z1
        while pos < end - 0.5:
            w = rng.uniform(*lot)
            if end - (pos + w) < lot[0] * 0.7:
                w = end - pos
            n = int(rng.integers(storeys[0], storeys[1] + 1))
            if rng.random() < tall:
                n += 1
            # 奥行きを少し変える（通りの側を 0〜0.8 m 引っ込める）
            inset = rng.uniform(0.0, 0.8) if rows == 1 or True else 0.0
            if along_x:
                hz0, hz1 = ra, rb
                if r == 0 and rows == 2:
                    hz0 += inset
                elif r == rows - 1:
                    hz1 -= inset
                hb = (pos, pos + w, hz0, hz1)
            else:
                hx0, hx1 = ra, rb
                if r == 0 and rows == 2:
                    hx0 += inset
                elif r == rows - 1:
                    hx1 -= inset
                hb = (hx0, hx1, pos, pos + w)
            if skip is None or not skip((hb[0] + hb[1]) / 2, (hb[2] + hb[3]) / 2):
                houses.append(House(hb[0], hb[1], hb[2], hb[3], y, n, np.random.default_rng(int(rng.integers(1 << 30)))))
            pos += w
    for h in houses:
        # 通りに面した辺：区画の外の辺に接する面
        sf = ''
        if 'n' in streets and h.z1 > z1 - 1.0:
            sf += 'n'
        if 's' in streets and h.z0 < z0 + 1.0:
            sf += 's'
        if 'e' in streets and h.x1 > x1 - 1.0:
            sf += 'e'
        if 'w' in streets and h.x0 < x0 + 1.0:
            sf += 'w'
        house(m, h, lights, [o for o in houses if o is not h], street_faces=sf, ground=ground, awn=awn)
    return houses


# ---------------------------------------------------------------- 段・擁壁・階段・通り

def tier_floor(m: Mesh, x0, x1, z0, z1, y, cell='st_pave'):
    floor(m, x0, x1, z0, z1, y, cell, rgba(WHITE), 4.0)


def retaining(m: Mesh, a, b, y0, y1, rng, doors=0.25, lights: Lights | None = None, order_rng=None):
    """段の擁壁（a → b の面。4 m ごとの升目、ところどころ扉とはしご）"""
    L = math.dist(a, b)
    n = max(1, int(round(L / 4.0)))
    for i in range(n):
        pa = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
        pb = (a[0] + (b[0] - a[0]) * (i + 1) / n, a[1] + (b[1] - a[1]) * (i + 1) / n)
        h = y1 - y0
        nv = max(1, int(round(h / 4.0)))
        for j in range(nv):
            ya, yb = y0 + h * j / nv, y0 + h * (j + 1) / nv
            door = j == 0 and rng.random() < doors
            order = float(rng.uniform(0.03, 1.0)) if door else NO_LIGHT
            wall(m, pa, pb, ya, yb, 'st_ret_door' if door else 'st_ret', rgba(WHITE, order), shade_lo=0.8 if j == 0 else 1.0)


def stairs(m: Mesh, x0, x1, z_lo, z_hi, y_lo, y_hi):
    """+Z へ上る階段（斜めの段の面と両側の擁壁の面）"""
    n = max(1, int(round(math.hypot(z_hi - z_lo, y_hi - y_lo) / 4.0)))
    for i in range(n):
        za, zb = z_lo + (z_hi - z_lo) * i / n, z_lo + (z_hi - z_lo) * (i + 1) / n
        ya, yb = y_lo + (y_hi - y_lo) * i / n, y_lo + (y_hi - y_lo) * (i + 1) / n
        k = max(1, int(round((x1 - x0) / 4.0)))
        for j in range(k):
            a0, a1 = x0 + (x1 - x0) * j / k, x0 + (x1 - x0) * (j + 1) / k
            m.quad((a0, ya, za), (a1, ya, za), (a1, yb, zb), (a0, yb, zb), 'st_stair', rgba(WHITE), (0, 0, min(1, (a1 - a0) / 4), 1))


def stairs_down_z(m: Mesh, x0, x1, z_hi, z_lo, y_hi, y_lo):
    """-Z へ下る階段（南の階段）"""
    n = max(1, int(round(math.hypot(z_hi - z_lo, y_hi - y_lo) / 4.0)))
    for i in range(n):
        za, zb = z_hi - (z_hi - z_lo) * i / n, z_hi - (z_hi - z_lo) * (i + 1) / n
        ya, yb = y_hi - (y_hi - y_lo) * i / n, y_hi - (y_hi - y_lo) * (i + 1) / n
        m.quad((x1, yb, zb), (x0, yb, zb), (x0, ya, za), (x1, ya, za), 'st_stair', rgba(WHITE), (0, 0, 1, 1))


# ---------------------------------------------------------------- 目印（塔・広場の輪・露店・天幕・工房・食堂・町長の家・ギルド）

def tower(m: Mesh, lights: Lights, cx, cz, y0, h, rng, w=2.6):
    """黒鉛の塔（真鍮の帯、細い窓の灯、上の見張りの箱と真鍮の尖塔）"""
    order = float(rng.uniform(0.03, 1.0))
    hw = w / 2
    n = max(1, int(round(h / ST)))
    for k, (a, b) in enumerate((((cx - hw, cz + hw), (cx + hw, cz + hw)), ((cx + hw, cz + hw), (cx + hw, cz - hw)),
                               ((cx + hw, cz - hw), (cx - hw, cz - hw)), ((cx - hw, cz - hw), (cx - hw, cz + hw)))):
        for s in range(n):
            ya, yb = y0 + h * s / n, y0 + h * (s + 1) / n
            cell = 'lm_tower' if (s % 2 == 1 and s < n - 1) else 'lm_tower2'
            o = order if cell == 'lm_tower' else NO_LIGHT
            wall(m, a, b, ya, yb, cell, rgba(WHITE, o), (0.0, 0.0, min(1.0, w / BAY), 1.0), 0.8 if s == 0 else 1.0)
    # 見張りの箱（少し張り出す）と灯の帯
    box(m, cx - hw - 0.4, cx + hw + 0.4, y0 + h, y0 + h + 0.6, cz - hw - 0.4, cz + hw + 0.4, 'mt_brass', rgba(WHITE), faces='nsewt')
    top = y0 + h + 0.6
    box(m, cx - hw * 0.7, cx + hw * 0.7, top, top + 2.2, cz - hw * 0.7, cz + hw * 0.7, 'em_slit', rgba(WHITE, order), faces='nsew', cell_w=1.0)
    box(m, cx - hw * 0.8, cx + hw * 0.8, top + 2.2, top + 2.5, cz - hw * 0.8, cz + hw * 0.8, 'mt_graphite', rgba(WHITE), faces='nsewt')
    cone(m, cx, cz, top + 2.5, top + 2.5 + h * 0.22, hw * 0.75, 'mt_brass', rgba(WHITE), 8)
    lights.add((cx, top + 1.1, cz + hw * 0.7 + 0.2), order, 2)
    lights.add((cx, top + 1.1, cz - hw * 0.7 - 0.2), order, 2)


def stack(m: Mesh, cx, cz, y0, h, r=0.55):
    """細い煙突・換気の筒（黒鉛に真鍮の輪）"""
    cylinder(m, cx, cz, y0, y0 + h, r, 'mt_graphite', rgba(WHITE), 6, top=False)
    for f in (0.35, 0.7, 0.98):
        cylinder(m, cx, cz, y0 + h * f - 0.25, y0 + h * f, r * 1.25, 'mt_brass', rgba(WHITE), 6, top=f > 0.9)


def plaza_ring(m: Mesh, lights: Lights, cx, cz, y, rng):
    """広場の輪（輪の敷石・真ん中の記念の柱と吊り灯）。中段の部屋の plaza_ring（中心 z 2）と monument"""
    u0, v0, u1, v1 = A.uv_rect('st_ring')
    segs = 16
    for r0, r1, cell, tint in ((6.5, 8.0, 'st_coping', WHITE), (2.2, 6.5, 'st_ring', WHITE), (1.6, 2.2, 'mt_brass', WHITE)):
        uu0, vv0, uu1, vv1 = A.uv_rect(cell)
        for k in range(segs):
            a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * (k + 1) / segs
            pts = [(cx + r1 * math.cos(a0), y + 0.04, cz + r1 * math.sin(a0)), (cx + r1 * math.cos(a1), y + 0.04, cz + r1 * math.sin(a1)),
                   (cx + r0 * math.cos(a1), y + 0.04, cz + r0 * math.sin(a1)), (cx + r0 * math.cos(a0), y + 0.04, cz + r0 * math.sin(a0))][::-1]
            m.poly(pts, [(uu0, vv1), (uu1, vv1), (uu1, vv0), (uu0, vv0)], rgba(tint))
    cylinder(m, cx, cz, y, y + 0.9, 1.6, 'st_ret', rgba(WHITE), 12, top_cell='mt_graphite')
    stack(m, cx, cz, y + 0.9, 5.2, 0.45)
    order = float(rng.uniform(0.03, 1.0))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        px, pz = cx + math.cos(a) * 0.9, cz + math.sin(a) * 0.9
        box(m, px - 0.2, px + 0.2, y + 4.2, y + 4.7, pz - 0.2, pz + 0.2, 'em_lantern', rgba(WHITE, order), faces='nsew')
        lights.add((px, y + 4.45, pz), order, 1)
    for k in (0, 2, 3, 5):
        a = k * math.pi / 3 + 0.3
        tree(m, cx + math.cos(a) * 10.5, y, cz + math.sin(a) * 10.5 * 0.7, 3.4, 900 + k)


def stall(m: Mesh, lights: Lights, cx, cz, w, d, y, rng, yaw_front='-z'):
    """市場の露店（台と品物、赤い縞の屋根、前の吊り灯）"""
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    box(m, x0 + 0.2, x1 - 0.2, y, y + 0.9, z0 + 0.3, z1 - 0.3, 'mt_wood', rgba(WHITE), faces='nsewt')
    for i in range(int(w / 0.6)):
        gx = x0 + 0.4 + i * 0.6
        col = [_lin('#BF4737'), _lin('#728052'), _lin('#D69E57'), _lin('#E6C398'), _lin('#555A5F')][int(rng.integers(5))]
        box(m, gx, gx + 0.45, y + 0.9, y + 0.9 + rng.uniform(0.2, 0.45), z0 + 0.5, z1 - 0.6, 'mt_ivory', rgba(col), faces='nsewt')
    for px, pz in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
        box(m, px - 0.07, px + 0.07, y, y + 2.6, pz - 0.07, pz + 0.07, 'mt_wood', rgba(WHITE), faces='nsew')
    cell = 'cl_stripe' if rng.random() < 0.6 else 'cl_red'
    y1, y2 = y + 2.4, y + 2.95
    zf, zb = (z0 - 0.5, z1 + 0.2) if yaw_front == '-z' else (z1 + 0.5, z0 - 0.2)
    n = max(1, int(round(w / 2.0)))
    for i in range(n):
        a0, a1 = x0 - 0.2 + (w + 0.4) * i / n, x0 - 0.2 + (w + 0.4) * (i + 1) / n
        # 上の面（上と前を向く）と下の面（暗い布）
        if yaw_front == '-z':
            m.quad((a1, y1, zf), (a0, y1, zf), (a0, y2, zb), (a1, y2, zb), cell, rgba(WHITE))
            m.quad((a0, y1, zf), (a1, y1, zf), (a1, y2, zb), (a0, y2, zb), 'cl_dark', rgba(WHITE * 0.55))
        else:
            m.quad((a0, y1, zf), (a1, y1, zf), (a1, y2, zb), (a0, y2, zb), cell, rgba(WHITE))
            m.quad((a1, y1, zf), (a0, y1, zf), (a0, y2, zb), (a1, y2, zb), 'cl_dark', rgba(WHITE * 0.55))
    order = float(rng.uniform(0.03, 1.0))
    box(m, cx - 0.18, cx + 0.18, y1 - 0.45, y1 - 0.05, zf - 0.18, zf + 0.18, 'em_lantern', rgba(WHITE, order), faces='nsew')
    lights.add((cx, y1 - 0.25, zf), order, 1)


def crates(m: Mesh, cx, cz, y, rng, n=3):
    """木箱と樽の小さな山（露店の裏・店の前）"""
    for k in range(n):
        x = cx + rng.uniform(-0.9, 0.9)
        z = cz + rng.uniform(-0.6, 0.6)
        s = rng.uniform(0.45, 0.7)
        if rng.random() < 0.6:
            box(m, x - s / 2, x + s / 2, y, y + s, z - s / 2, z + s / 2, 'mt_wood', rgba(_lin('#D9B48A')), faces='nsewt')
        else:
            cylinder(m, x, z, y, y + s * 1.3, s * 0.42, 'mt_wood', rgba(_lin('#B98A60')), 6, top_cell='mt_wood')


def planter(m: Mesh, cx, cz, y, rng, w=1.6):
    """四角い植え込み（白磁の箱と緑）"""
    box(m, cx - w / 2, cx + w / 2, y, y + 0.6, cz - 0.45, cz + 0.45, 'st_ret', rgba(WHITE), top_cell='mt_green', faces='nsewt', cell_w=None)
    blob(m, cx, y + 0.9, cz, w * 0.45, 0.45, 0.4, 'mt_green2' if rng.random() < 0.5 else 'mt_green', rgba(WHITE), int(rng.integers(1 << 30)))


def tent(m: Mesh, cx, cz, w, d, y, h, cell='cl_red'):
    """四角い帆布の天幕（4 本の柱と四角錐の屋根）"""
    x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
    for px, pz in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
        box(m, px - 0.07, px + 0.07, y, y + h, pz - 0.07, pz + 0.07, 'mt_wood', rgba(WHITE), faces='nsew')
    u0, v0, u1, v1 = A.uv_rect(cell)
    apex = (cx, y + h + min(w, d) * 0.35, cz)
    for a, b in (((x0, z1), (x1, z1)), ((x1, z1), (x1, z0)), ((x1, z0), (x0, z0)), ((x0, z0), (x0, z1))):
        m.poly([(a[0], y + h, a[1]), (b[0], y + h, b[1]), apex], [(u0, v1), (u1, v1), ((u0 + u1) / 2, v0)], rgba(WHITE))
        m.poly([(b[0], y + h, b[1]), (a[0], y + h, a[1]), apex], [(u0, v1), (u1, v1), ((u0 + u1) / 2, v0)], rgba(WHITE * 0.5))
        wall(m, a, b, y + h - 0.4, y + h, cell, rgba(WHITE * 0.9), (0, 0, 1, 0.2))


def landmark(m: Mesh, lights: Lights, x0, x1, z0, z1, y, storeys, front_cell, rng, front='-z', roof_kind='flat', tint=None,
             ground_cell=None):
    """目印の建物（工房・食堂・町長の家・ギルド）：正面の 1 階を目印の升目、上の階は窓"""
    h = House(x0, x1, z0, z1, y, storeys, rng, roof=roof_kind, tint=tint)
    h.lit = 0.85
    edges = {'+z': ((x0, z1), (x1, z1)), '+x': ((x1, z1), (x1, z0)), '-z': ((x1, z0), (x0, z0)), '-x': ((x0, z0), (x0, z1))}
    for k, (a, b) in edges.items():
        if k == front:
            L = math.dist(a, b)
            nb = max(1, int(round(L / BAY)))
            for s in range(storeys):
                for i in range(nb):
                    pa = (a[0] + (b[0] - a[0]) * i / nb, a[1] + (b[1] - a[1]) * i / nb)
                    pb = (a[0] + (b[0] - a[0]) * (i + 1) / nb, a[1] + (b[1] - a[1]) * (i + 1) / nb)
                    if s == 0:
                        cell = ground_cell(i, nb) if ground_cell else front_cell
                    else:
                        if front_cell == 'lm_mayor' or (front_cell == 'lm_guild' and i == nb // 2):
                            cell = front_cell
                        else:
                            cell = h.ups[i % len(h.ups)]
                    o = h.order if cell in GLOW else NO_LIGHT
                    wall(m, pa, pb, y + s * ST, y + (s + 1) * ST, cell, rgba(h.tint, o), shade_lo=0.75 if s == 0 else 1.0)
                    if o and s > 0:
                        cx, cz = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
                        nx, nz = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
                        lights.add((cx + nx * 0.25, y + s * ST + 1.7, cz + nz * 0.25), h.order, 0)
        else:
            facade(m, h, a, b, lights, ground='house', door=False)
    roof(m, h, lights)
    return h


# ---------------------------------------------------------------- 町の並び

def stern_district(m: Mesh, lights: Lights) -> None:
    """南の区画（z -114〜-57。ordo_back と ordo_town の両方）：下の段の床・大通り・横の通り・家並み・黒鉛の塔・街灯・小旗"""
    rng = np.random.default_rng(57)
    y = LOW
    z0, z1 = STERN_Z, BACK_Z
    # 床（通りの敷石）。家の下も同じ床
    tier_floor(m, -TOWN_X, TOWN_X, z0, z1, y)
    # 床の縁（南の端・東西の端）の擁壁の面（背の面から 1.5 m）
    retaining(m, (TOWN_X, z0), (-TOWN_X, z0), 0.0, y, rng, doors=0)
    for sx in (-1, 1):
        a, b = ((sx * TOWN_X, z0), (sx * TOWN_X, z1)) if sx > 0 else ((sx * TOWN_X, z1), (sx * TOWN_X, z0))
        retaining(m, a, b, 0.0, y, rng, doors=0)
    # 区画：大通り |x| < 3.5、横の通り（4 m）z -100〜-96・-84〜-80・-70〜-66、東西の小路 |x| 21.5〜24.5
    zb = [(z0 + 1.0, -100.0), (-96.0, -84.0), (-80.0, -70.0), (-66.0, z1 - 1.0)]
    xb = [(3.5, 21.5), (24.5, TOWN_X - 1.2)]
    towers = {(-1, 1, 0): 22.0, (1, 0, 1): 18.0, (-1, 0, 2): 15.0, (1, 1, 2): 16.0}
    for zi, (za, zc) in enumerate(zb):
        for sx in (-1, 1):
            for xi, (xa, xc) in enumerate(xb):
                bx0, bx1 = (xa, xc) if sx > 0 else (-xc, -xa)
                key = (sx, xi, zi)
                skip = None
                if key in towers:
                    tx = (bx0 + bx1) / 2 + (2.5 if sx > 0 else -2.5)
                    tz = (za + zc) / 2
                    tower(m, lights, tx, tz, y, towers[key], rng, w=3.0)
                    skip = (lambda tx, tz: (lambda x, z: abs(x - tx) < 4.0 and abs(z - tz) < 4.5))(tx, tz)
                streets = 'nsew'
                block(m, lights, bx0, bx1, za, zc, y, rng, storeys=(1, 3), streets=streets, skip=skip, awn=0.35, tall=0.1)
    # 大通りの街灯と並木・横の通りを渡る小旗
    z = z1 - 4.0
    k = 0
    while z > z0 + 3.0:
        for sx in (-1, 1):
            lamp_post(m, lights, sx * 3.0, y, z, rng)
            if k % 2 == 1:
                tree(m, sx * 2.6, y, z - 5.5, rng.uniform(2.8, 3.6), int(rng.integers(1 << 30)))
        z -= 11.0
        k += 1
    for zc in (-108.0, -92.0, -88.0, -76.0, -62.0):
        for sx in (-1, 1):
            if rng.random() < 0.75:
                laundry(m, (sx * 21.5, zc), (sx * 24.5, zc + rng.uniform(-1.0, 1.0)), y + rng.uniform(4.0, 6.0), rng)
    for zc in (-98.0, -82.0, -68.0):
        bunting(m, (-3.5, zc + 1.0), (3.5, zc - 1.0), y + 6.4, 0.8, rng)
        bunting(m, (21.5 if zc > -90 else -21.5, zc), (24.5 if zc > -90 else -24.5, zc), y + 5.6, 0.4, rng)
    # 大通りの真ん中の小さな広場（給水塔と木）
    water_tank(m, 0.0, -90.0, y, 1.5, rng, legs=5.0)
    for dx in (-2.0, 2.0):
        tree(m, dx, y, -76.0, 3.2, 40 + int(dx))


def lower_district(m: Mesh, lights: Lights) -> None:
    """下の段の北（z -57〜-14.5。ordo_town だけ）：家並み・訓練場・ハルの家のあたり・南の階段の両側の棟"""
    rng = np.random.default_rng(15)
    y = LOW
    z0, z1 = BACK_Z, MID_S
    tier_floor(m, -TOWN_X, TOWN_X, z0, z1, y)
    for sx in (-1, 1):
        a, b = ((sx * TOWN_X, z0), (sx * TOWN_X, z1)) if sx > 0 else ((sx * TOWN_X, z1), (sx * TOWN_X, z0))
        retaining(m, a, b, 0.0, y, rng, doors=0)
    # 訓練場（西 x -32〜-12、z -50〜-33：開けた砂の庭、的の柱、門の棟）
    tx0, tx1, tz0, tz1 = -32.0, -12.0, -50.0, -33.0
    floor(m, tx0, tx1, tz0, tz1, y + 0.02, 'rf_gravel', rgba(_lin('#E9D3B0')), 4.0)
    for k in range(4):
        px = tx0 + 3.0 + k * 4.5
        box(m, px - 0.2, px + 0.2, y, y + 1.8, tz0 + 3.0, tz0 + 3.4, 'mt_wood', rgba(WHITE), faces='nsewt')
        cylinder(m, px, tz0 + 3.2, y + 1.6, y + 2.0, 0.55, 'cl_banner2', rgba(WHITE), 8)
    for a, b in (((tx0, tz1), (tx1, tz1)), ((tx1, tz0), (tx0, tz0))):
        retaining(m, a, b, y, y + 2.0, rng, doors=0.0)
    for a, b in (((tx1, tz1), (tx1, tz0)), ((tx0, tz0), (tx0, tz1))):
        retaining(m, a, b, y, y + 2.0, rng, doors=0.0)
    landmark(m, lights, tx0 + 5.0, tx1 - 5.0, tz1, tz1 + 6.0, y, 2, 'lm_gate', rng, front='-z', roof_kind='flat2')
    banner(m, (tx0 + 5.6, tz1 - 0.02), (tx0 + 4.6, tz1 - 0.02), y + 6.0, 2.6, 'cl_banner', rng)
    banner(m, (tx1 - 4.6, tz1 - 0.02), (tx1 - 5.6, tz1 - 0.02), y + 6.0, 2.6, 'cl_banner', rng)
    skip_train = lambda x, z: tx0 - 0.5 < x < tx1 + 0.5 and tz0 - 0.5 < z < tz1 + 6.5  # noqa: E731
    # 南の階段（x -4〜4、z -32〜-14.5 を中段から下る）の両側の棟
    for sx in (-1, 1):
        x0, x1 = (4.0, 9.5) if sx > 0 else (-9.5, -4.0)
        h = House(x0, x1, -32.0, MID_S, y, 3, np.random.default_rng(300 + sx), roof='flat2')
        house(m, h, lights, (), street_faces='nsewt')
    stairs_down_z(m, -4.0, 4.0, MID_S, -32.0, MID, y)
    # 区画
    zb = [(z0 + 1.0, -45.0), (-41.0, -33.0)]
    xb = [(3.5, 21.5), (24.5, TOWN_X - 1.2)]
    for zi, (za, zc) in enumerate(zb):
        for sx in (-1, 1):
            for xi, (xa, xc) in enumerate(xb):
                bx0, bx1 = (xa, xc) if sx > 0 else (-xc, -xa)
                block(m, lights, bx0, bx1, za, zc, y, rng, storeys=(1, 3), skip=skip_train, awn=0.35)
    # 階段の両側の棟より南、胸壁の下の家並み（z -29〜-16）
    for sx in (-1, 1):
        for (xa, xc) in ((11.0, 21.5), (24.5, TOWN_X - 1.2)):
            bx0, bx1 = (xa, xc) if sx > 0 else (-xc, -xa)
            block(m, lights, bx0, bx1, -29.0, -16.0, y, rng, storeys=(1, 2), skip=skip_train, streets='sew')
    z = -20.0
    while z > z0 + 2.0:
        for sx in (-1, 1):
            if z < -33.0:
                lamp_post(m, lights, sx * 3.0, y, z, rng)
        z -= 11.0
    for zc in (-43.0,):
        bunting(m, (-3.5, zc), (3.5, zc), y + 6.0, 0.7, rng)
    for zc in (-52.0, -38.0, -24.0):
        for sx in (-1, 1):
            laundry(m, (sx * 21.5, zc), (sx * 24.5, zc + rng.uniform(-1.0, 1.0)), y + rng.uniform(4.0, 5.5), rng)


def mid_tier(m: Mesh, lights: Lights) -> None:
    """中段（z -14.5〜16、床 6.5）：広場の輪と記念の柱・壇・天幕・東（+X）の市場の露店と給水塔・西（-X）の食堂と工房。中段の部屋の並び"""
    rng = np.random.default_rng(65)
    y = MID
    # 床の下の擁壁（南の胸壁の面 z -14.5、y 1.5〜6.5）と胸壁
    for sx in (-1, 1):
        a, b = ((sx * 4.0, MID_S), (sx * TOWN_X, MID_S)) if sx < 0 else ((sx * TOWN_X, MID_S), (sx * 4.0, MID_S))
        retaining(m, a, b, LOW, MID, rng, doors=0.35)
        wall(m, a, b, MID, MID + 1.2, 'st_coping', rgba(WHITE), (0, 0.2, 1, 0.8))
        floor(m, min(a[0], b[0]), max(a[0], b[0]), MID_S, MID_S + 0.3, MID + 1.2, 'st_coping', rgba(WHITE), 2.0)
    for sx in (-1, 1):
        a, b = ((sx * TOWN_X, MID_S), (sx * TOWN_X, MID_N)) if sx > 0 else ((sx * TOWN_X, MID_N), (sx * TOWN_X, MID_S))
        retaining(m, a, b, 0.0, MID, rng, doors=0)
    # 広場の床
    tier_floor(m, -TOWN_X, TOWN_X, MID_S, MID_N, y, 'st_pave2')
    plaza_ring(m, lights, 0.0, 2.0, y, rng)
    box(m, -4.0, 4.0, y, y + 0.8, 7.5, 10.5, 'st_ret', rgba(WHITE), top_cell='rf_wood', faces='nsewt')      # 壇
    tent(m, -9.0, 11.2, 4.5, 3.5, y, 2.4, 'cl_red')
    tent(m, 9.0, 11.2, 4.5, 3.5, y, 2.4, 'cl_dark')
    # 市場（+X）：露店・天幕・給水塔
    for cx, cz in ((24.0, 6.3), (38.0, 6.3), (17.5, -2.0), (24.5, -6.5), (31.0, -2.0), (38.5, -7.0), (45.0, -1.0)):
        stall(m, lights, cx, cz, rng.uniform(3.6, 4.6), 2.6, y, rng)
    tent(m, 45.7, 5.6, 3.6, 4.0, y, 2.4, 'cl_stripe2')
    water_tank(m, 31.0, 13.6, y, 1.6, rng, legs=5.5)
    for x0 in (18.0, 34.0):
        bunting(m, (x0, 4.0), (x0 + 12.0, 4.0), y + 4.2, 0.6, rng)
    # 西（-X）：食堂（x -25〜-15、z 0.5〜9.5、高さ 5.5）と工房（x -41〜-27、z 4〜13、高さ 7）
    landmark(m, lights, -25.0, -15.0, 0.5, 9.5, y, 2, 'lm_diner', rng, front='-z', roof_kind='wood')
    awning(m, (-15.5, 0.5), (-24.5, 0.5), y + 3.0, 2.2, 0.5, rng, 'cl_stripe')
    landmark(m, lights, -41.0, -27.0, 4.0, 13.0, y, 2, 'lm_workshop', rng, front='-z', roof_kind='metal')
    stack(m, -38.0, 11.0, y + 2 * ST, 6.0, 0.6)
    stack(m, -35.5, 11.5, y + 2 * ST, 4.5, 0.45)
    banner(m, (-33.4, 3.98), (-34.6, 3.98), y + 6.2, 2.4, 'cl_banner', rng)
    # 西の端と東の端の家（部屋の外の壁ぎわ）
    for (bx0, bx1) in ((-TOWN_X + 0.5, -42.5), (40.0, TOWN_X - 0.5)):
        block(m, lights, bx0, bx1, 6.0, MID_N, y, rng, storeys=(2, 3), streets='sw' if bx0 < 0 else 'se', awn=0.4)
    # 広場の街灯（輪のまわりと通り）
    for (lx, lz) in ((-8.0, -10.0), (8.0, -10.0), (-14.0, 4.0), (14.0, 4.0), (-30.0, -8.0), (30.0, 12.0), (-44.0, -8.0), (44.0, 9.0)):
        lamp_post(m, lights, lx, y, lz, rng)
    for x in (-40.0, -28.0, -16.0, 16.0, 28.0, 40.0):
        tree(m, x, y, -12.0, 3.0, int(x * 10) + 7)
    # 広場の植え込み・露店の裏の木箱と樽
    for (px, pz) in ((-12.0, -6.0), (12.0, -6.0), (-6.0, 13.5), (6.0, 13.5), (-44.0, 2.0), (20.0, 13.0)):
        planter(m, px, pz, y, rng)
    for (cx, cz) in ((24.0, 8.6), (38.0, 8.6), (17.5, 0.3), (31.0, 0.3), (45.0, 1.3), (-20.0, -2.5), (-34.0, 2.5)):
        crates(m, cx, cz, y, rng, 3)


def terraces(m: Mesh, lights: Lights) -> None:
    """北の段々（z 16〜34）：擁壁（5 m）・段ごとに奥へ下がる家の列・真ん中の北の階段と門の棟。中段の部屋の town_terrace と同じ並び"""
    rng = np.random.default_rng(16)
    # 段 0：擁壁 z 16（y 6.5〜11.5）。階段の口 |x| < 4 は開ける
    for sx in (-1, 1):
        a, b = ((sx * 4.0, MID_N), (sx * TOWN_X, MID_N)) if sx > 0 else ((sx * TOWN_X, MID_N), (sx * 4.0, MID_N))
        retaining(m, a, b, MID, UP, rng, doors=0.4)
        pot_plants(m, min(a[0], b[0]), max(a[0], b[0]), MID_N + 0.6, UP, rng)
    tier_floor(m, -TOWN_X, TOWN_X, MID_N, GATE_Z, UP)
    stairs(m, -4.0, 4.0, MID_N, 28.0, MID, UP)
    for sx in (-1, 1):
        retaining(m, (sx * 4.0, 28.0) if sx > 0 else (sx * 4.0, MID_N), (sx * 4.0, MID_N) if sx > 0 else (sx * 4.0, 28.0), MID, UP, rng, doors=0)
    # 段 1〜3：正面 z 18.5（高さ 4.4 = 1 階 + 縁）・22（2 階＋）・27（3 階＋）。奥は z 34
    rows = [(18.5, 22.0, 1), (22.0, 27.0, 2), (27.0, GATE_Z, 3)]
    for sx in (-1, 1):
        prev = []
        for (za, zc, n) in rows:
            x = 8.0 if n >= 2 else 4.0
            row = []
            while x < TOWN_X - 1.0:
                w = rng.uniform(5.0, 8.0)
                if TOWN_X - 1.0 - (x + w) < 3.5:
                    w = TOWN_X - 1.0 - x
                nn = n + (1 if rng.random() < 0.25 else 0)
                bx0, bx1 = (x, x + w) if sx > 0 else (-(x + w), -x)
                h = House(bx0, bx1, za, zc, UP, nn, np.random.default_rng(int(rng.integers(1 << 30))))
                row.append(h)
                x += w
            for h in row:
                house(m, h, lights, [o for o in row if o is not h] + prev, street_faces='s', ground='house', awn=0.25)
            prev = row
        # 段 1 の屋根の上の通路の手すりの鉢
    # 階段の両側の角の棟（|x| 4〜8、z 16〜34、高さ 9 m → 階は 3）と門の棟（|x| < 8、z 34、高さ 12）
    for sx in (-1, 1):
        x0, x1 = (4.0, 8.0) if sx > 0 else (-8.0, -4.0)
        h = House(x0, x1, 28.0, GATE_Z, MID, 4, np.random.default_rng(160 + sx), roof='flat')
        house(m, h, lights, (), street_faces='s' + ('w' if sx > 0 else 'e'))
    landmark(m, lights, -8.0, 8.0, GATE_Z, GATE_Z + 5.0, UP, 2, 'lm_gate', rng, front='-z', roof_kind='flat2',
             ground_cell=lambda i, nb: 'lm_gate' if i == nb // 2 else 'gr_plain')
    banner(m, (-5.2, GATE_Z - 0.02), (-6.4, GATE_Z - 0.02), UP + 6.0, 3.0, 'cl_banner', rng)
    banner(m, (6.4, GATE_Z - 0.02), (5.2, GATE_Z - 0.02), UP + 6.0, 3.0, 'cl_banner', rng)
    for (lx, lz) in ((-5.0, 17.0), (5.0, 17.0)):
        lamp_post(m, lights, lx, MID, lz - 1.5, rng)


def upper_tier(m: Mesh, lights: Lights) -> None:
    """上の段（z 34〜95、床 11.5）：広場（|x| < 40、z 34〜64）・町長の家（x -29〜-15、z 52〜61）・ギルド（x 12〜28、z 52〜61）・
    北の展望台（|x| < 8、z 64〜76）・東西の家並み・船首の側の家と塔。上段の部屋の並び（部屋の z + 48）"""
    rng = np.random.default_rng(95)
    y = UP
    tier_floor(m, -TOWN_X, TOWN_X, GATE_Z, BOW_Z, y, 'st_pave2')
    # 東西と北（船首の側）の段の壁：下の 4 m に扉と灯（外から見る面。夜に明かりがともる）
    for sx in (-1, 1):
        a, b = ((sx * TOWN_X, MID_N), (sx * TOWN_X, BOW_Z)) if sx > 0 else ((sx * TOWN_X, BOW_Z), (sx * TOWN_X, MID_N))
        retaining(m, a, b, 0.0, y, rng, doors=0.3)
    retaining(m, (-TOWN_X, BOW_Z), (TOWN_X, BOW_Z), 0.0, y, rng, doors=0.35)
    # 町長の家：落ち着いた家（緑の屋上の庭、真鍮の帯、両開きの扉）
    landmark(m, lights, -29.0, -15.0, 52.0, 61.0, y, 2, 'lm_mayor', rng, front='-z', roof_kind='garden', tint=_lin('#F6EEDC'),
             ground_cell=lambda i, nb: 'gr_door2' if i == nb // 2 else 'lm_mayor')
    canopy(m, -24.4, -19.6, 56.5, 59.5, y + 2 * ST + 0.08, 2.0, np.random.default_rng(3))
    water_tank(m, -17.0, 59.5, y + 2 * ST + 0.08, 0.9, rng)
    # ギルド：3 階、正面の真ん中に大きな丸窓、上に真鍮の看板と旗
    landmark(m, lights, 12.0, 28.0, 52.0, 61.0, y, 3, 'lm_guild', rng, front='-z', roof_kind='flat2', tint=_lin('#F2E4CC'),
             ground_cell=lambda i, nb: 'gr_door2' if i == nb // 2 else 'gr_shop')
    for bx in (14.0, 25.0):
        banner(m, (bx + 0.6, 51.98), (bx - 0.6, 51.98), y + 3 * ST - 0.4, 4.2, 'cl_banner', rng)
    awning(m, (23.0, 52.0), (17.0, 52.0), y + 2.9, 1.8, 0.45, rng, 'cl_stripe')
    tower(m, lights, 26.0, 59.0, y + 3 * ST, 6.0, rng, w=2.4)
    # 広場の南の木と街灯、北の胸壁と展望台
    for (lx, lz) in ((-12.0, 40.0), (12.0, 40.0), (-12.0, 50.0), (12.0, 50.0), (-36.0, 62.0), (36.0, 62.0)):
        lamp_post(m, lights, lx, y, lz, rng)
    for x in (-34.0, -6.0, 6.0, 34.0):
        tree(m, x, y, 44.0, 3.4, int(x) + 300)
    for sx in (-1, 1):
        a, b = ((sx * 8.0, 64.5), (sx * 40.0, 64.5)) if sx < 0 else ((sx * 40.0, 64.5), (sx * 8.0, 64.5))
        wall(m, a, b, y, y + 1.2, 'st_coping', rgba(WHITE), (0, 0.2, 1, 0.8))
    floor(m, -8.0, 8.0, 64.0, 76.0, y + 0.02, 'st_deck', rgba(WHITE), 4.0)
    for sx in (-1, 1):
        stack(m, sx * 7.5, 75.5, y, 1.4, 0.15)
    tower(m, lights, 0.0, 79.0, y, 10.0, rng, w=3.2)
    # 東西の家並み（|x| 40.5〜48、z 34〜95）と船首の側（z 64〜95、|x| 8〜40）
    for sx in (-1, 1):
        bx0, bx1 = (40.5, TOWN_X - 0.5) if sx > 0 else (-TOWN_X + 0.5, -40.5)
        block(m, lights, bx0, bx1, GATE_Z, 64.0, y, rng, storeys=(2, 3), streets='w' if sx > 0 else 'e', lot=(5.0, 7.5))
        for (xa, xc) in ((10.0, 24.0), (27.0, TOWN_X - 0.5)):
            bx0, bx1 = (xa, xc) if sx > 0 else (-xc, -xa)
            block(m, lights, bx0, bx1, 67.0, 79.0, y, rng, storeys=(1, 3), streets='nsew')
            block(m, lights, bx0, bx1, 82.0, BOW_Z - 1.0, y, rng, storeys=(1, 2), streets='nsew')
    for (cx, cz, h) in ((-44.5, 80.5, 22.0), (44.5, 87.0, 17.0)):
        tower(m, lights, cx, cz, y, h, rng, w=2.8)
    # 上の段の小さな煙突・給水塔
    water_tank(m, 34.0, 88.0, y + ST + 0.1, 1.2, rng, legs=2.0)
    for (cx, cz) in ((-20.0, 70.0), (18.0, 92.0)):
        stack(m, cx, cz, y, 12.0, 0.5)


def build_town() -> tuple[Mesh, Lights]:
    m = Mesh('ordo_town')
    lights = Lights()
    stern_district(m, lights)
    lower_district(m, lights)
    mid_tier(m, lights)
    terraces(m, lights)
    upper_tier(m, lights)
    return m, lights


def build_back() -> tuple[Mesh, Lights]:
    m = Mesh('ordo_back')
    lights = Lights()
    stern_district(m, lights)
    return m, lights


# ---------------------------------------------------------------- GLB（numpy で直に書く）

def write_glb(m: Mesh, path: str) -> dict:
    P = np.asarray(m.P, np.float32)
    N = np.asarray(m.N, np.float32)
    # 絵の帳の UV は 16 bit、頂点の色は 8 bit（どちらも glTF の正規化した整数）、頂点が 65536 より少なければ番号も 16 bit（ファイルを小さく）
    UV = np.round(np.clip(np.asarray(m.UV, np.float64), 0.0, 1.0) * 65535).astype(np.uint16)
    Cc = np.round(np.clip(np.asarray(m.C, np.float64), 0.0, 1.0) * 255).astype(np.uint8)
    small = len(P) < 65536
    I = np.asarray(m.I, np.uint16 if small else np.uint32)
    blobs = [P.tobytes(), N.tobytes(), UV.tobytes(), Cc.tobytes(), I.tobytes()]
    views, off = [], 0
    data = b''
    for b in blobs:
        pad = (-len(data)) % 4
        data += b'\0' * pad
        views.append({'buffer': 0, 'byteOffset': len(data), 'byteLength': len(b)})
        data += b
    data += b'\0' * ((-len(data)) % 4)
    for i, v in enumerate(views):
        v['target'] = 34963 if i == 4 else 34962
    nv = len(P)
    gl = {
        'asset': {'version': '2.0', 'generator': 'project-relic town_far.py'},
        'scene': 0, 'scenes': [{'nodes': [0]}],
        'nodes': [{'name': m.name, 'mesh': 0}],
        'materials': [{'name': 'far', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.85}}],
        'meshes': [{'name': m.name, 'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1, 'TEXCOORD_0': 2, 'COLOR_0': 3},
                                                     'indices': 4, 'material': 0, 'mode': 4}]}],
        'buffers': [{'byteLength': len(data)}],
        'bufferViews': views,
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': nv, 'type': 'VEC3', 'min': P.min(0).tolist(), 'max': P.max(0).tolist()},
            {'bufferView': 1, 'componentType': 5126, 'count': nv, 'type': 'VEC3'},
            {'bufferView': 2, 'componentType': 5123, 'normalized': True, 'count': nv, 'type': 'VEC2'},
            {'bufferView': 3, 'componentType': 5121, 'normalized': True, 'count': nv, 'type': 'VEC4'},
            {'bufferView': 4, 'componentType': 5123 if small else 5125, 'count': len(I), 'type': 'SCALAR'},
        ],
    }
    js = json.dumps(gl, separators=(',', ':')).encode()
    js += b' ' * ((-len(js)) % 4)
    total = 12 + 8 + len(js) + 8 + len(data)
    with open(path, 'wb') as fh:
        fh.write(struct.pack('<III', 0x46546C67, 2, total))
        fh.write(struct.pack('<II', len(js), 0x4E4F534A))
        fh.write(js)
        fh.write(struct.pack('<II', len(data), 0x004E4942))
        fh.write(data)
    return {'tris': m.tris(), 'mats': 1, 'verts': nv, 'min': [round(float(x), 2) for x in P.min(0)], 'max': [round(float(x), 2) for x in P.max(0)]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--atlas-only', action='store_true')
    a = ap.parse_args()
    build_all(atlas_only=a.atlas_only)


def build_all(atlas_only=False):
    os.makedirs(WORK, exist_ok=True)
    atlas = A.build(ATLAS)
    A.preview(atlas, os.path.join(WORK, 'far_atlas_preview.jpg'))
    print('[far] 帳', ATLAS, flush=True)
    if atlas_only:
        return
    index_path = os.path.join(OUT, 'parts.json')
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    for name, fn in (('ordo_town', build_town), ('ordo_back', build_back)):
        m, lights = fn()
        info = write_glb(m, os.path.join(OUT, f'{name}.glb'))
        info['lights'] = len(lights.pts)
        index[name] = info
        with open(os.path.join(OUT, f'{name}_lights.json'), 'w') as fh:
            json.dump({'points': lights.pts}, fh, separators=(',', ':'))
        print(f'[far] {name}: {info}', flush=True)
    with open(index_path, 'w') as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
