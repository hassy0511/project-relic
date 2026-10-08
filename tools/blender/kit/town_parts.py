"""オルド背町の部品（W2-05 town_kit_buildings / town_kit_walls_* / town_kit_ground_* / town_props*）。

寸法は spec_town_3d.md の表（2 m 升目）、形と色は絵から。部品ごとに平らな 1 色（geo.MATERIALS）、陰は焼かない。
座標はゲームの向き（X 右、Y 上、Z 手前 = 部品の正面）。原点は底の中心。壁は厚みの中心。

PARTS = {名前: 作る関数}。名前は godot/assets/kit/town/<名前>.glb になる。
"""
from __future__ import annotations

import math

import numpy as np

from town_geo import Part, beam, box, boxb, cyl, lathe, merge, sag, sheet, tube

# ---------------------------------------------------------------- 共通の小さな形

POST = 0.2          # 黒鉛の柱の太さ（絵：壁 2 m に対して約 1 割）
SKIRT = 0.4         # 壁の下の木の帯
BR = 0.04           # 真鍮の金具の出っ張り


def post(p: Part, x, z, y0, y1, w=POST, d=None, bands=(0.08, None)):
    """黒鉛の柱＋真鍮の金具（下と上の帯）。bands=(下の高さ, 上の高さ or None=上端)"""
    d = w + 0.04 if d is None else d
    p.add('graphite', boxb(x - w / 2, x + w / 2, y0, y1, z - d / 2, z + d / 2))
    lo = y0 + bands[0]
    hi = y1 - 0.08 if bands[1] is None else bands[1]
    for yy in (lo, hi - 0.2):
        p.add('brass', boxb(x - w / 2 - BR / 2, x + w / 2 + BR / 2, yy, yy + 0.2, z - d / 2 - BR / 2, z + d / 2 + BR / 2))


def plates(p: Part, xs, ys, z, face=1):
    """壁の面の小さな真鍮の留め板"""
    for x in xs:
        for y in ys:
            p.add('brass', boxb(x - 0.05, x + 0.05, y - 0.09, y + 0.09, z, z + 0.025 * face) if face > 0
                  else boxb(x - 0.05, x + 0.05, y - 0.09, y + 0.09, z - 0.025, z))


def lantern(p: Part, x, y, z, s=1.0):
    """吊り灯（小物 10）：真鍮の笠・発光の芯・4 本の格子・底。(x, y, z) は芯の中心"""
    p.add('brass', lathe((x, y + 0.13 * s, z), (x, y + 0.26 * s, z), [(0, 0.13 * s), (0.5, 0.11 * s), (1, 0.03 * s)], 10))
    p.add('amber', cyl((x, y - 0.12 * s, z), (x, y + 0.13 * s, z), 0.075 * s, 8))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        dx, dz = 0.095 * s * math.cos(a), 0.095 * s * math.sin(a)
        p.add('brass', boxb(x + dx - 0.012 * s, x + dx + 0.012 * s, y - 0.13 * s, y + 0.14 * s, z + dz - 0.012 * s, z + dz + 0.012 * s))
    p.add('brass', lathe((x, y - 0.19 * s, z), (x, y - 0.12 * s, z), [(0, 0.05 * s), (1, 0.11 * s)], 10))
    p.add('brass', cyl((x, y + 0.26 * s, z), (x, y + 0.34 * s, z), 0.02 * s, 6))


def pipe_run(p: Part, a, b, r=0.12, collars=1.0):
    """黒鉛の管＋真鍮の継ぎ輪（collars m ごと）。両端の継ぎ輪は管の端より 2 cm 外へ出して管の口をふさぐ
    （前は継ぎ輪のふたと管のふたが同じ面にあり、端がまだらにちらついた。管にはふたを付けない）"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    p.add('graphite', cyl(a, b, r, 10, cap=False))
    L = float(np.linalg.norm(b - a))
    n = max(1, int(L / collars))
    d = (b - a) / L
    for k in range(n + 1):
        t = k * L / n
        if k == 0:
            p.add('brass', cyl(a - d * 0.02, a + d * 0.1, r * 1.25, 10))
        elif k == n:
            p.add('brass', cyl(b - d * 0.1, b + d * 0.02, r * 1.25, 10))
        else:
            c = a + d * t
            p.add('brass', cyl(c - d * 0.06, c + d * 0.06, r * 1.25, 10))


# ---------------------------------------------------------------- 建物キット（town_kit_walls_*）

def wall(w=2.0, h=2.0, kind='plain', posts=True, back_plates=False) -> Part:
    """1 通常壁 / 2 高壁 / 4 扉壁 / 5 窓壁。白磁の板、黒鉛の柱、下に木の帯、真鍮の金具"""
    p = Part(f'wall_{kind}')
    hw = w / 2
    x0, x1 = (-hw + POST, hw - POST) if posts else (-hw, hw)
    if posts:
        for x in (-hw + POST / 2, hw - POST / 2):
            post(p, x, 0, 0, h)
            if h > 2.5:
                p.add('brass', boxb(x - 0.12, x + 0.12, 1.9, 2.1, -0.14, 0.14))
    # 段の区切り（高壁は 2 m ごと）
    bands = [k * 2.0 for k in range(1, int(round(h / 2)))]
    for y in bands:
        p.add('graphite', boxb(x0, x1, y - 0.05, y + 0.05, -0.1, 0.1))
    p.add('graphite', boxb(x0, x1, h - 0.06, h, -0.09, 0.09))
    # 開口
    hole = None
    if kind == 'door':
        hole = (-0.45, 0.45, 0.0, 1.75)
    elif kind == 'window':
        hole = (-0.42, 0.42, 0.85, 1.5)
    # 木の帯と白磁の板（開口を避けて切る）
    def span(ya, yb, mat, zt):
        if hole and ya < hole[3] and yb > hole[2]:
            p.add(mat, boxb(x0, hole[0], ya, yb, -zt, zt), boxb(hole[1], x1, ya, yb, -zt, zt))
            if yb > hole[3]:
                p.add(mat, boxb(hole[0], hole[1], hole[3], yb, -zt, zt))
            if ya < hole[2]:
                p.add(mat, boxb(hole[0], hole[1], ya, hole[2], -zt, zt))
        else:
            p.add(mat, boxb(x0, x1, ya, yb, -zt, zt))
    span(0, SKIRT, 'wood', 0.1)
    span(SKIRT, (bands[0] - 0.05) if bands else h - 0.06, 'ivory', 0.08)
    for i, y in enumerate(bands):
        top = bands[i + 1] - 0.05 if i + 1 < len(bands) else h - 0.06
        p.add('ivory', boxb(x0, x1, y + 0.05, top, -0.08, 0.08))
    # 留め板（絵：板の四隅寄りに縦長の真鍮）
    for k in range(int(round(h / 2))):
        ys = (k * 2 + 0.75, k * 2 + 1.6)
        xs = (x0 + 0.2, x1 - 0.2) if hole is None else (x0 + 0.15,)
        plates(p, xs, ys, 0.08)
        if back_plates:
            plates(p, xs, ys, -0.08, -1)
    if kind == 'door':
        p.add('graphite', boxb(-0.53, -0.45, 0, 1.83, -0.12, 0.12), boxb(0.45, 0.53, 0, 1.83, -0.12, 0.12),
              boxb(-0.53, 0.53, 1.75, 1.83, -0.12, 0.12))
        for k in range(4):
            xa = -0.44 + k * 0.22
            p.add('wood', boxb(xa + 0.005, xa + 0.215, 0.02, 1.74, -0.05, 0.03))
        p.add('brass', boxb(0.24, 0.3, 0.8, 1.05, 0.03, 0.08),                     # 取っ手は右
              boxb(-0.44, -0.3, 0.35, 0.42, 0.03, 0.06), boxb(-0.44, -0.3, 1.4, 1.47, 0.03, 0.06))
        p.add('graphite', boxb(0.6, 0.78, 1.0, 1.14, 0.08, 0.12))                   # 扉の横の小さな箱（絵の右）
    if kind == 'window':
        p.add('dark', boxb(-0.42, 0.42, 0.85, 1.5, -0.02, 0.02))
        p.add('graphite', boxb(-0.5, -0.42, 0.78, 1.57, -0.12, 0.13), boxb(0.42, 0.5, 0.78, 1.57, -0.12, 0.13),
              boxb(-0.5, 0.5, 0.78, 0.85, -0.12, 0.16), boxb(-0.5, 0.5, 1.5, 1.57, -0.12, 0.13))
        p.add('graphite', boxb(-0.02, 0.02, 0.85, 1.5, -0.03, 0.05), boxb(-0.42, 0.42, 1.16, 1.2, -0.03, 0.05))
        # 雨戸：上の蝶番で外へ開いた木の板（絵：上へ開く）
        hinge = np.array([0, 1.57, 0.13])
        ang = math.radians(55)
        d = np.array([0, -math.cos(ang), math.sin(ang)])
        for k in range(4):
            xa = -0.46 + k * 0.23
            a = hinge + np.array([xa + 0.115, 0, 0])
            p.add('wood', beam(a, a + d * 0.72, 0.21, 0.04, up=(0, 0, 1)))
        p.add('brass', beam(hinge + [-0.4, -0.55, -0.12], hinge + d * 0.6 + [-0.4, 0, 0], 0.025),
              beam(hinge + [0.4, -0.55, -0.12], hinge + d * 0.6 + [0.4, 0, 0], 0.025))
    return p


def roof(kind='flat') -> Part:
    """6 平屋根 / 7 木板屋根 / 8 帆布屋根（2×2×0.2 m）。原点は下面の中心"""
    p = Part(f'roof_{kind}')
    e = 0.14
    p.add('graphite', boxb(-1, 1, 0, 0.2, -1, -1 + e), boxb(-1, 1, 0, 0.2, 1 - e, 1),
          boxb(-1, -1 + e, 0, 0.2, -1 + e, 1 - e), boxb(1 - e, 1, 0, 0.2, -1 + e, 1 - e))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('brass', boxb(sx * 1 - 0.13 - sx * 0.0, sx * 1 + 0.03 if sx > 0 else -1 + 0.13, -0.01, 0.23,
                                sz * 1 - 0.13 if sz > 0 else -1 - 0.03, sz * 1 + 0.03 if sz > 0 else -1 + 0.13))
    if kind == 'flat':
        p.add('ivory', boxb(-1 + e, 1 - e, 0.02, 0.17, -1 + e, 1 - e))
        p.add('graphite', boxb(-0.02, 0.02, 0.17, 0.19, -1 + e, 1 - e), boxb(-1 + e, 1 - e, 0.17, 0.19, -0.02, 0.02))
    elif kind == 'wood':
        for k in range(5):
            xa = -1 + e + k * (2 - 2 * e) / 5
            p.add('wood', boxb(xa + 0.01, xa + (2 - 2 * e) / 5 - 0.01, 0.04, 0.2, -1 + e, 1 - e))
    else:
        p.add('ivory', boxb(-1 + e, 1 - e, 0.0, 0.06, -1 + e, 1 - e))
        p.add('cloth', sheet(lambda u, v: (-0.92 + 1.84 * u, 0.22 - 0.12 * math.sin(math.pi * u) * math.sin(math.pi * v),
                                            -0.92 + 1.84 * v), 6, 6, 0.02))
    return p


def awning(kind='hard', w=2.0, depth=1.6, drop=0.5) -> Part:
    """9 固いひさし / 10 柔らかい日よけ。原点 = 壁に付く上の縁の中心（壁の面 z=0）。手前（+Z）へ出る"""
    p = Part(f'awning_{kind}')
    hw = w / 2
    if kind == 'hard':
        p.add('graphite', boxb(-hw, hw, -0.08, 0.06, 0, 0.1))                     # 壁の受け
        p.add('brass', beam((-hw + 0.06, -drop, depth), (hw - 0.06, -drop, depth), 0.07))   # 前の棒
        for x in (-hw + 0.08, hw - 0.08):
            p.add('brass', beam((x, 0, 0.05), (x, -drop, depth), 0.06))            # 横の枠
            p.add('graphite', beam((x, -0.8, 0.04), (x, -drop - 0.02, depth * 0.62), 0.05))   # 斜めの支え
            p.add('graphite', boxb(x - 0.06, x + 0.06, -0.92, -0.7, 0, 0.08))
        p.add('cloth', sheet(lambda u, v: (-hw + 0.1 + (w - 0.2) * u, -drop * v - 0.05 * math.sin(math.pi * u) * math.sin(math.pi * v) + 0.02,
                                            0.06 + (depth - 0.06) * v), 6, 4, 0.025))
        # 前の垂れ（短い）
        p.add('cloth', sheet(lambda u, v: (-hw + 0.06 + (w - 0.12) * u, -drop - 0.22 * v * (0.75 + 0.25 * math.cos(u * math.pi * 6)),
                                            depth + 0.04), 12, 1))
    else:
        for x in (-hw, hw):
            p.add('graphite', boxb(x - 0.06, x + 0.06, -0.3, 0.12, 0, 0.1))
            p.add('brass', cyl((x, 0, 0.12), (x, 0, 0.2), 0.045, 8))
            p.add('rope', tube([(x, 0.0, 0.16), (x * 0.98, -drop + 0.05, depth)], 0.015, 5))
        p.add('cloth', sheet(lambda u, v: (-hw + w * u, -drop * v - 0.18 * math.sin(math.pi * u) * (0.4 + 0.6 * v),
                                            0.16 + (depth - 0.16) * v), 8, 4))
        for x in (-hw, hw):
            p.add('brass', lathe((x, -drop - 0.03, depth), (x, -drop + 0.05, depth), [(0, 0.05), (1, 0.05)], 8))
    return p


def railing(w=2.0, h=1.0, brass_top=True) -> Part:
    """12 手すり（2×0.2×1 m）：黒鉛の柱、3 本の横棒、白磁の足元の板"""
    p = Part('railing')
    hw = w / 2
    for x in (-hw + 0.07, hw - 0.07):
        p.add('graphite', boxb(x - 0.06, x + 0.06, 0, h, -0.06, 0.06))
        p.add('brass', boxb(x - 0.08, x + 0.08, h - 0.06, h + 0.02, -0.08, 0.08), boxb(x - 0.08, x + 0.08, 0, 0.1, -0.08, 0.08))
    p.add('ivory', boxb(-hw + 0.13, hw - 0.13, 0, 0.14, -0.05, 0.05))
    for k, y in enumerate((h * 0.38, h * 0.64, h * 0.9)):
        top = k == 2 and brass_top
        p.add('brass' if top else 'graphite', cyl((-hw + 0.13, y, 0), (hw - 0.13, y, 0), 0.04 if top else 0.03, 8, cap=False))
        for x in (-hw + 0.2, hw - 0.2):
            p.add('brass', cyl((x - 0.04, y, 0), (x + 0.04, y, 0), 0.05 if top else 0.042, 8))
    return p


def stairs() -> Part:
    """11 階段（2×2×2 m、蹴上げ 0.25 m × 8 段）。手前が低い（+Z が下の段）"""
    p = Part('stairs')
    n = 8
    for i in range(n):
        y = (i + 1) * 0.25
        z1 = 1 - i * 0.25
        p.add('ivory2', boxb(-0.8, 0.8, y - 0.25, y - 0.05, z1 - 0.25, z1))
        p.add('wood', boxb(-0.8, 0.8, y - 0.05, y, z1 - 0.27, z1))
    for x in (-0.9, 0.9):
        pts = [(x - 0.1, 0, 1), (x - 0.1, 0, -1), (x - 0.1, 2, -1)]
        p.add('ivory', _wedge(x - 0.1, x + 0.1))
        p.add('graphite', beam((x, 0.1, 1.05), (x, 2.1, -0.95), 0.2, 0.12), boxb(x - 0.1, x + 0.1, 0, 2.15, -1.05, -0.85))
        p.add('brass', boxb(x - 0.12, x + 0.12, 0, 0.25, 0.85, 1.07), boxb(x - 0.12, x + 0.12, 1.9, 2.15, -1.07, -0.85))
    return p


def _wedge(x0, x1):
    v = np.array([[x0, 0, 1], [x0, 0, -1], [x0, 2, -1], [x1, 0, 1], [x1, 0, -1], [x1, 2, -1]], float)
    f = [[0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [0, 3, 5, 2]]
    from town_geo import Piece, _orient
    return _orient(Piece(v, f))


# ---------------------------------------------------------------- 地面キット（town_kit_ground_*）

def ledge(w=2.0, h=2.0) -> Part:
    """2 段の縁（2×0.2×2 m）：高床の縁の壁。上に黒鉛の笠木"""
    p = wall(w, h)
    p.name = 'ledge'
    p.add('graphite', boxb(-w / 2, w / 2, h, h + 0.08, -0.14, 0.14))
    return p


def ladder(h=2.0) -> Part:
    """4 はしご（0.5×0.5×2 m）"""
    p = Part('ladder')
    for x in (-0.22, 0.22):
        p.add('graphite', boxb(x - 0.04, x + 0.04, 0, h + 0.3, -0.04, 0.04))
        p.add('brass', boxb(x - 0.06, x + 0.06, 0, 0.1, -0.06, 0.06), boxb(x - 0.06, x + 0.06, h - 0.1, h, -0.1, 0.06))
    for k in range(1, int(h / 0.3) + 1):
        p.add('brass', cyl((-0.2, k * 0.3, 0), (0.2, k * 0.3, 0), 0.025, 6, cap=False))
    return p


def pipes(w=2.0) -> Part:
    """5 配管 2 本組（2×0.5×0.5 m）：床に置く足つき"""
    p = Part('pipes')
    for y, z in ((0.32, -0.12), (0.32, 0.14)):
        pipe_run(p, (-w / 2, y, z), (w / 2, y, z), 0.11, 0.65)
    for x in (-w / 2 + 0.3, w / 2 - 0.3):
        p.add('graphite', boxb(x - 0.08, x + 0.08, 0, 0.22, -0.26, 0.28))
        p.add('brass', boxb(x - 0.14, x + 0.14, 0, 0.05, -0.3, 0.32))
    return p


def power_pole(h=4.0) -> Part:
    """6 電線柱（0.5×0.5×4 m）"""
    p = Part('power_pole')
    p.add('ivory', boxb(-0.3, 0.3, 0, 0.45, -0.3, 0.3))
    p.add('graphite', boxb(-0.32, -0.24, 0, 0.47, -0.32, 0.32), boxb(0.24, 0.32, 0, 0.47, -0.32, 0.32))
    p.add('graphite', boxb(-0.07, 0.07, 0.45, h, -0.07, 0.07))
    p.add('graphite', cyl((0.16, 0.45, 0), (0.16, h - 0.4, 0), 0.04, 6))
    for y in (1.2, 2.2, h - 0.7):
        p.add('brass', boxb(-0.1, 0.1, y, y + 0.12, -0.1, 0.1))
    p.add('graphite', boxb(-0.6, 0.6, h - 0.35, h - 0.25, -0.05, 0.05))
    for x in (-0.5, 0, 0.5):
        p.add('brass', cyl((x, h - 0.25, 0), (x, h - 0.1, 0), 0.035, 6))
    p.add('graphite', boxb(0.08, 0.3, 1.5, 1.85, -0.1, 0.1))
    return p


def lamp_tall() -> Part:
    """背の高い外灯（4.4 m）：広場の角・階段の上。芯の位置は (0.55, 3.92, 0)"""
    return lamp_post(4.4, 'lamp_tall')


def lamp_post(h=2.0, name='lamp_post') -> Part:
    """7 外灯（0.5×0.5×2 m、基部は白磁の台）。吊り腕は +X（絵の右）。芯の位置は (0.5, h-0.48, 0)"""
    p = Part(name)
    p.add('ivory', boxb(-0.28, 0.28, 0, 0.42, -0.28, 0.28))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('graphite', boxb(sx * 0.28 - 0.05, sx * 0.28 + 0.05, 0, 0.44, sz * 0.28 - 0.05, sz * 0.28 + 0.05))
    p.add('brass', boxb(-0.33, 0.33, 0.42, 0.48, -0.33, 0.33))
    p.add('graphite', boxb(-0.07, 0.07, 0.48, h + 0.1, -0.07, 0.07))
    for y in (0.6, h * 0.55, h - 0.05):
        p.add('brass', boxb(-0.09, 0.09, y, y + 0.1, -0.09, 0.09))
    p.add('graphite', beam((0, h, 0), (0.55, h, 0), 0.07), beam((0.05, h - 0.4, 0), (0.42, h - 0.02, 0), 0.04))
    p.add('brass', boxb(0.5, 0.6, h - 0.06, h + 0.06, -0.05, 0.05))
    p.add('brass', cyl((0.55, h - 0.18, 0), (0.55, h - 0.04, 0), 0.015, 5))
    lantern(p, 0.55, h - 0.48, 0, 1.15)
    return p


# ---------------------------------------------------------------- 小物（town_props*：5 列 × 4 段）

def crate() -> Part:
    """1 木箱 1 m：白磁の板＋黒鉛の角＋真鍮の取っ手"""
    p = Part('crate')
    s = 0.9
    p.add('ivory', boxb(-s / 2 + 0.06, s / 2 - 0.06, 0.06, s * 0.82 - 0.06, -s / 2 + 0.02, s / 2 - 0.02),
          boxb(-s / 2 + 0.02, s / 2 - 0.02, 0.06, s * 0.82 - 0.06, -s / 2 + 0.06, s / 2 - 0.06))
    p.add('wood', boxb(-s / 2 + 0.06, s / 2 - 0.06, s * 0.82 - 0.08, s * 0.82, -s / 2 + 0.06, s / 2 - 0.06),
          boxb(-s / 2 + 0.02, s / 2 - 0.02, 0, 0.12, -s / 2 + 0.02, s / 2 - 0.02))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('graphite', boxb(sx * s / 2 - 0.07, sx * s / 2 + 0.01, 0, s * 0.82, sz * s / 2 - 0.07, sz * s / 2 + 0.01) if sx > 0 and sz > 0
                  else boxb(min(sx * s / 2, sx * s / 2 + -sx * 0.08), max(sx * s / 2, sx * s / 2 - sx * 0.08), 0, s * 0.82,
                            min(sz * s / 2, sz * s / 2 - sz * 0.08), max(sz * s / 2, sz * s / 2 - sz * 0.08)))
    p.add('brass', boxb(-0.16, 0.16, 0.42, 0.52, s / 2 - 0.02, s / 2 + 0.02), boxb(-0.16, 0.16, 0.42, 0.52, -s / 2 - 0.02, -s / 2 + 0.02))
    return p


def barrel() -> Part:
    """2 樽 1 m（木の胴・真鍮の輪・黒鉛の台・蛇口）"""
    p = Part('barrel')
    p.add('wood', lathe((0, 0.12, 0), (0, 1.0, 0), [(0, 0.3), (0.5, 0.36), (1, 0.3)], 12))
    for t in (0.18, 0.5, 0.82):
        y = 0.12 + 0.88 * t
        r = 0.3 + 0.06 * math.sin(math.pi * t) + 0.015
        p.add('brass', cyl((0, y - 0.035, 0), (0, y + 0.035, 0), r, 12, cap=False))
    p.add('graphite', boxb(-0.36, 0.36, 0, 0.12, -0.08, 0.08), boxb(-0.08, 0.08, 0, 0.12, -0.36, 0.36))
    p.add('brass', cyl((0, 0.3, 0.3), (0, 0.3, 0.44), 0.035, 6), cyl((0, 0.3, 0.42), (0, 0.2, 0.42), 0.03, 6))
    return p


def clothesline() -> Part:
    """3 洗濯綱 2 m：2 本の柱・綱・布 2 枚"""
    p = Part('clothesline')
    for x in (-1, 1):
        p.add('ivory', boxb(x - 0.14, x + 0.14, 0, 0.25, -0.14, 0.14))
        p.add('graphite', boxb(x - 0.06, x + 0.06, 0.25, 1.9, -0.06, 0.06))
        p.add('brass', boxb(x - 0.08, x + 0.08, 1.75, 1.85, -0.08, 0.08))
    pts = sag((-1, 1.75, 0), (1, 1.75, 0), 8, 0.12)
    p.add('rope', tube(pts, 0.015, 5))
    for x0, x1, mat, ln in ((-0.6, -0.15, 'cloth', 0.75), (-0.08, 0.32, 'linen', 0.6), (0.4, 0.7, 'cloth2', 0.45)):
        def f(u, v, x0=x0, x1=x1, ln=ln):
            x = x0 + (x1 - x0) * u
            top = 1.75 - 0.12 * 4 * ((x + 1) / 2) * (1 - (x + 1) / 2)
            return (x, top - ln * v, 0.03 * math.sin(u * 6 + v * 2))
        p.add(mat, sheet(f, 3, 3))
    return p


def planter(w=0.8, bush=0.55) -> Part:
    """4 鉢植え 1 m：白磁の箱＋黒鉛の角＋緑の茂み（低い多面体）"""
    p = Part('planter')
    h = 0.5
    p.add('ivory', boxb(-w / 2, w / 2, 0.04, h, -w / 2, w / 2))
    p.add('graphite', boxb(-w / 2 - 0.03, w / 2 + 0.03, 0, 0.06, -w / 2 - 0.03, w / 2 + 0.03),
          boxb(-w / 2 - 0.02, w / 2 + 0.02, h - 0.05, h + 0.02, -w / 2 - 0.02, w / 2 + 0.02))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('brass', boxb(sx * w / 2 - 0.05, sx * w / 2 + 0.05, 0.06, h - 0.05, sz * w / 2 - 0.05, sz * w / 2 + 0.05))
    p.add('wood', cyl((0, h, 0), (0, h + 0.3, 0), 0.04, 5))
    rng = np.random.default_rng(int(w * 100))
    for k in range(5):
        a = k * 2 * math.pi / 5
        c = (math.cos(a) * w * 0.18, h + 0.4 + rng.uniform(0, 0.25) * bush, math.sin(a) * w * 0.18)
        p.add('green', _blob(c, bush * rng.uniform(0.45, 0.6)))
    p.add('green', _blob((0, h + 0.55 + bush * 0.3, 0), bush * 0.6))
    return p


def _blob(c, r):
    """茂みの塊（八面体をつぶした低い形）"""
    return lathe((c[0], c[1] - r * 0.6, c[2]), (c[0], c[1] + r * 0.7, c[2]), [(0, 0.0001), (0.35, r), (0.75, r * 0.7), (1, 0.0001)], 6, cap=False)


def stall_table(w=2.0) -> Part:
    """5 露店台 2 m：木の天板、黒鉛の脚、赤い掛け布"""
    p = Part('stall_table')
    hw = w / 2
    p.add('wood', boxb(-hw, hw, 0.85, 0.95, -0.5, 0.5))
    p.add('graphite', boxb(-hw, hw, 0.78, 0.85, -0.48, 0.48))
    for x in (-hw + 0.1, hw - 0.1):
        for z in (-0.4, 0.4):
            p.add('graphite', boxb(x - 0.05, x + 0.05, 0, 0.8, z - 0.05, z + 0.05))
        p.add('graphite', beam((x, 0.15, -0.4), (x, 0.15, 0.4), 0.05))
    p.add('graphite', beam((-hw + 0.1, 0.15, 0), (hw - 0.1, 0.15, 0), 0.05))
    for x in (-hw, hw):
        for z in (-0.5, 0.5):
            p.add('brass', boxb(x - 0.06 if x > 0 else x, x if x > 0 else x + 0.06, 0.8, 0.97, z - 0.06 if z > 0 else z, z if z > 0 else z + 0.06))
    p.add('cloth', sheet(lambda u, v: (-0.35 + 0.7 * u, 0.955 if v < 0.5 else 0.955 - (v - 0.5) * 2 * 0.5,
                                        -0.5 + 1.0 * min(v, 0.5) * 2 + (0.02 if v >= 0.5 else 0)), 2, 4))
    p.add('brass', cyl((-0.3, 0.95, -0.15), (-0.3, 1.15, -0.15), 0.08, 8), cyl((0.35, 0.95, 0.1), (0.35, 1.08, 0.1), 0.1, 8))
    return p


def water_tower() -> Part:
    """6 給水塔 2 m：真鍮の槽、黒鉛の脚、白磁の台"""
    p = Part('water_tower')
    p.add('ivory', boxb(-0.75, 0.75, 0, 0.2, -0.75, 0.75))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('graphite', beam((sx * 0.6, 0.2, sz * 0.6), (sx * 0.45, 1.3, sz * 0.45), 0.08))
    for y in (0.6, 1.0):
        k = (y - 0.2) / 1.1
        r = 0.6 - 0.15 * k
        for a, b in (((-r, r), (r, r)), ((r, r), (r, -r)), ((r, -r), (-r, -r)), ((-r, -r), (-r, r))):
            p.add('graphite', beam((a[0], y, a[1]), (b[0], y, b[1]), 0.05))
    p.add('brass', lathe((0, 1.3, 0), (0, 2.2, 0), [(0, 0.55), (0.9, 0.55), (1, 0.5)], 12))
    p.add('brass', lathe((0, 2.2, 0), (0, 2.45, 0), [(0, 0.52), (1, 0.08)], 12))
    p.add('graphite', cyl((0, 1.5, 0), (0, 1.56, 0), 0.57, 12, cap=False), cyl((0, 2.0, 0), (0, 2.06, 0), 0.57, 12, cap=False))
    p.add('graphite', cyl((0.7, 0.2, 0), (0.7, 2.3, 0), 0.05, 6))
    return p


def bench() -> Part:
    """8 ベンチ 2 m：木の座面、白磁の背板、黒鉛の脚"""
    p = Part('bench')
    p.add('wood', boxb(-0.95, 0.95, 0.42, 0.5, -0.25, 0.22))
    p.add('ivory', boxb(-0.85, 0.85, 0.65, 1.0, -0.3, -0.24))
    for x in (-0.9, 0.9):
        p.add('graphite', boxb(x - 0.07, x + 0.07, 0, 1.05, -0.32, -0.2), boxb(x - 0.07, x + 0.07, 0, 0.45, 0.1, 0.22))
        p.add('brass', boxb(x - 0.09, x + 0.09, 0, 0.1, -0.34, 0.24), boxb(x - 0.09, x + 0.09, 0.95, 1.07, -0.34, -0.18))
    return p


def junk_pile() -> Part:
    """9 ガラクタの山 2 m：樽・木箱・板・管・歯車の寄せ集め"""
    p = Part('junk_pile')
    p.place(barrel(), (-0.7, 0, -0.1), 0, (0.8, 0.8, 0.8))
    p.place(crate(), (0.5, 0, -0.2), 20, (0.8, 0.8, 0.8))
    p.place(crate(), (0.0, 0, 0.35), -10, (0.55, 0.55, 0.55))
    p.add('cloth', box((-0.1, 0.75, -0.3), (0.7, 0.75, 0.06), 15).moved((0, 0, 0)))
    p.add('graphite', lathe((0.2, 0.45, 0.45), (0.2, 0.45, 0.6), [(0, 0.42), (1, 0.42)], 12),
          cyl((0.9, 0.12, 0.3), (0.4, 0.12, 0.7), 0.12, 8), box((-0.4, 0.3, 0.45), (0.5, 0.6, 0.2), 30))
    p.add('brass', cyl((0.2, 0.45, 0.6), (0.2, 0.45, 0.63), 0.18, 10))
    p.add('linen', box((0.55, 0.78, -0.15), (0.5, 0.08, 0.5), 10))
    return p


def tool_rack() -> Part:
    """11 工具棚 2 m：白磁の背板、真鍮の掛け棒、工具（黒鉛）、下に木箱"""
    p = Part('tool_rack')
    p.add('ivory', boxb(-0.9, 0.9, 0.2, 1.6, -0.06, 0.0))
    for x in (-0.95, 0.95):
        post(p, x, 0, 0, 1.75, 0.12)
    p.add('graphite', boxb(-1, 1, 0, 0.1, -0.3, 0.2))
    p.add('brass', cyl((-0.85, 1.35, 0.05), (0.85, 1.35, 0.05), 0.025, 6))
    for k, x in enumerate(np.linspace(-0.65, 0.65, 6)):
        ln = 0.35 + 0.12 * (k % 3)
        p.add('graphite', boxb(x - 0.03, x + 0.03, 1.33 - ln, 1.36, 0.02, 0.07))
        p.add('graphite' if k % 2 else 'brass', boxb(x - 0.07, x + 0.07, 1.33 - ln - 0.08, 1.33 - ln + 0.02, 0.0, 0.08))
    p.add('wood', boxb(-0.6, 0.0, 0.1, 0.42, -0.05, 0.3))
    return p


def chest() -> Part:
    """12 収納箱 1 m：白磁、黒鉛の枠、赤い帯"""
    p = Part('chest')
    p.add('ivory', boxb(-0.45, 0.45, 0.05, 0.95, -0.4, 0.4))
    for x in (-0.47, 0.47):
        for z in (-0.42, 0.42):
            p.add('graphite', boxb(x - 0.05, x + 0.05, 0, 1.0, z - 0.05, z + 0.05))
    for x in (-0.22, 0.22):
        p.add('cloth', boxb(x - 0.05, x + 0.05, 0.05, 0.9, -0.42, 0.42))
    p.add('graphite', boxb(-0.47, 0.47, 0.9, 0.97, -0.43, 0.43))
    p.add('brass', boxb(-0.06, 0.06, 0.6, 0.78, 0.4, 0.44))
    return p


def tank() -> Part:
    """13 水筒形タンク 1 m：横倒しの白磁の筒、真鍮の帯、蛇口"""
    p = Part('tank')
    p.add('ivory', cyl((-0.5, 0.45, 0), (0.5, 0.45, 0), 0.32, 12))
    p.add('graphite', lathe((0.5, 0.45, 0), (0.62, 0.45, 0), [(0, 0.34), (1, 0.28)], 12))
    for x in (-0.3, 0.2):
        p.add('brass', cyl((x - 0.05, 0.45, 0), (x + 0.05, 0.45, 0), 0.34, 12, cap=False))
        p.add('graphite', boxb(x - 0.06, x + 0.06, 0, 0.2, -0.3, 0.3))
    p.add('brass', cyl((0.62, 0.35, 0), (0.75, 0.35, 0), 0.03, 6), cyl((0.0, 0.77, 0), (0.0, 0.85, 0), 0.08, 8))
    return p


def pipe_bend() -> Part:
    """14 曲がり管 1 m：床から立ち上がって横へ曲がる（絵：左が床の足、右へ出る）"""
    p = Part('pipe_bend')
    r0 = 0.32
    arc = [(-0.35 + r0 - r0 * math.cos(a), 0.25 + r0 * math.sin(a), 0) for a in np.linspace(0, math.pi / 2, 7)]
    path = [(-0.35, 0.08, 0)] + arc + [(0.45, 0.25 + r0, 0)]
    p.add('graphite', tube(path, 0.15, 10))
    for c, d in (((-0.35, 0.16, 0), (0, 1, 0)), ((0.38, 0.25 + r0, 0), (1, 0, 0))):
        c, d = np.array(c, float), np.array(d, float)
        p.add('brass', cyl(c - d * 0.06, c + d * 0.06, 0.2, 10))
    p.add('graphite', boxb(-0.6, -0.1, 0, 0.08, -0.25, 0.25))
    p.add('brass', boxb(-0.62, -0.08, 0, 0.03, -0.27, 0.27))
    return p


def canvas_roll() -> Part:
    """16 巻き上げ帆布 2 m（壁付け）：原点 = 壁の面、上の巻きの中心の高さ 0"""
    p = Part('canvas_roll')
    p.add('cloth', cyl((-0.9, 0, 0.18), (0.9, 0, 0.18), 0.14, 10))
    p.add('cloth', sheet(lambda u, v: (-0.88 + 1.76 * u, -0.1 - 1.1 * v, 0.3 + 0.7 * v), 4, 3, 0.02))
    for x in (-1.0, 1.0):
        p.add('brass', cyl((x - 0.06 * np.sign(x), 0, 0.18), (x, 0, 0.18), 0.17, 10))
        p.add('graphite', boxb(x - 0.06, x + 0.06, -0.15, 0.15, 0, 0.18), beam((x * 0.97, -0.9, 0.02), (x * 0.97, -1.2, 1.0), 0.05))
    return p


def sand_screen() -> Part:
    """17 防砂の編み幕 2 m：黒鉛の柱と枠、麻の布"""
    p = Part('sand_screen')
    for x in (-1, 1):
        post(p, x, 0, 0, 2.0, 0.14)
    p.add('linen', sheet(lambda u, v: (-0.88 + 1.76 * u, 0.25 + 1.55 * v, 0.03 * math.sin(u * math.pi)), 4, 3))
    p.add('rope', tube([(-0.9, 1.8, 0), (0.9, 1.8, 0)], 0.02, 5), tube([(-0.9, 0.25, 0), (0.9, 0.25, 0)], 0.02, 5))
    return p


def hand_lantern() -> Part:
    """18 携行灯 0.5 m（床置き）"""
    p = Part('hand_lantern')
    p.add('graphite', boxb(-0.13, 0.13, 0, 0.06, -0.13, 0.13))
    lantern(p, 0, 0.25, 0, 1.0)
    p.add('brass', tube([(-0.08, 0.6, 0), (-0.06, 0.68, 0), (0.06, 0.68, 0), (0.08, 0.6, 0)], 0.012, 5))
    return p


def stool() -> Part:
    """20 折り畳み踏み台 1 m"""
    p = Part('stool')
    for z in (-0.3, 0.3):
        p.add('ivory', _wedge_s(z))
    for k, (y, z) in enumerate(((0.3, 0.3), (0.6, 0.0), (0.9, -0.25))):
        p.add('wood', boxb(-0.32, 0.32, y - 0.05, y, z - 0.2, z + 0.12))
    p.add('graphite', beam((-0.36, 0, 0.45), (-0.36, 0.95, -0.3), 0.05), beam((0.36, 0, 0.45), (0.36, 0.95, -0.3), 0.05))
    return p


def _wedge_s(x):
    from town_geo import Piece, _orient
    v = np.array([[x - 0.03, 0, 0.45], [x - 0.03, 0, -0.45], [x - 0.03, 0.95, -0.35], [x + 0.03, 0, 0.45], [x + 0.03, 0, -0.45], [x + 0.03, 0.95, -0.35]])
    v = v[:, [0, 1, 2]]
    v2 = v.copy()
    v2[:, 0] = v[:, 0] * 0 + np.array([-0.35, -0.35, -0.35, 0.35, 0.35, 0.35]) * (1 if x > 0 else 1)
    f = [[0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [0, 3, 5, 2]]
    pv = np.array([[-0.35, 0, 0.45], [-0.35, 0, -0.45], [-0.35, 0.95, -0.35], [0.35, 0, 0.45], [0.35, 0, -0.45], [0.35, 0.95, -0.35]])
    # 側板（左右 2 枚）：x の位置で薄い三角柱
    pv[:, 0] = np.where(pv[:, 0] < 0, -0.36, -0.30) if x < 0 else np.where(pv[:, 0] < 0, 0.30, 0.36)
    return _orient(Piece(pv, f))


# ---------------------------------------------------------------- 看板

def sign_board(w=2.2, h=0.8, mount='wall', post_len=1.7) -> Part:
    """看板（town_kit_buildings 最下段の右）：上の棒から吊る板。原点 = 棒の中心。板の中心は (0, -0.62, 0)、
    文字は板の表（z = +0.08）にゲームが貼る（props_view の看板の "board"）。
    mount：wall = 棒の両端から壁（z = -0.5）へ腕、post = 棒の両端から下へ柱（post_len、屋根や梁の上に立てる）"""
    p = Part(f'sign_{mount}')
    hw = w / 2
    p.add('graphite', beam((-hw - 0.15, 0, 0), (hw + 0.15, 0, 0), 0.08))
    p.add('brass', cyl((-hw - 0.2, 0, 0), (-hw - 0.12, 0, 0), 0.07, 8), cyl((hw + 0.12, 0, 0), (hw + 0.2, 0, 0), 0.07, 8))
    cy = -0.22 - h / 2
    for x in (-hw * 0.8, hw * 0.8):
        p.add('brass', beam((x, -0.02, 0), (x, cy + h / 2 + 0.02, 0), 0.025))
    p.add('graphite', boxb(-hw, hw, cy - h / 2, cy + h / 2, -0.05, 0.05))
    p.add('ivory', boxb(-hw + 0.06, hw - 0.06, cy - h / 2 + 0.06, cy + h / 2 - 0.06, -0.055, 0.055))
    p.add('cloth', boxb(-hw + 0.12, hw - 0.12, cy - h / 2 + 0.12, cy + h / 2 - 0.12, -0.06, 0.06))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0 = sx * hw - 0.08 if sx > 0 else -hw - 0.02
            y0 = cy + h / 2 - 0.08 if sy > 0 else cy - h / 2 - 0.02
            p.add('brass', boxb(x0, x0 + 0.1, y0, y0 + 0.1, -0.07, 0.07))
    for sx in (-1, 1):
        x = sx * (hw + 0.1)
        if mount == 'wall':
            p.add('graphite', beam((x, 0, 0), (x, 0, -0.5), 0.07), beam((x, -0.45, -0.5), (x, -0.02, -0.08), 0.05))
            p.add('brass', boxb(x - 0.1, x + 0.1, -0.55, 0.12, -0.53, -0.49))
        else:
            p.add('graphite', boxb(x - 0.05, x + 0.05, -post_len, 0.05, -0.05, 0.05))
            p.add('brass', boxb(x - 0.09, x + 0.09, -post_len, -post_len + 0.12, -0.09, 0.09))
    return p
