"""オルドのリフトの踊り場（下段の東の口から出る、脚を見下ろす展望の台。2026-10-20）。

ordo_landing：原点 = オルドの原点（背の歩行面の真ん中）、+Z が船首、+X が左舷（ordo.glb と同じ座標。town_backdrop.ordo_back と同じ約束）。
  床    ：板張り（材質 deck：キットでは町の板の絵 town_wood と汚れの層。上段の展望台の床と同じ絵）を黒鉛の帯で区切り、縁は白磁の鼻隠しと真鍮の縁金具。
          内の端は下段の床に続く黒鉛の敷居。かごの口のふたは白磁の 2 枚の扉（板 3 枚ずつ、継ぎ目は黒鉛）、縁は真鍮と黒の縞（下段のリフトと同じ）。
  手すり：町の手すりと同じ作り（真鍮の柱と上の棒、黒鉛の中の棒 2 本、足元の板）。高さ 1.45 m（当たり判定の柵の高さ）、外の手すりは 4 m ごとに琥珀の灯。
  日よけ：柱 4 本（当たり判定の柱と同じ所・高さ）に梁と垂木、赤と生成りの縞の帆布（垂木の間でたるみ、風で揺れる：town_geo.sway）、
          外の縁の垂れ（波形）、内の柱の上の小旗、垂木から吊った灯 2 つ。帆布だけは別の部品 ordo_landing_awning（影を落とす）。
  小物  ：ベンチ 2 つ（日よけの下で南向き、北東の角で外向き）、木箱 3 つと携行灯、巻いた綱、「見下ろす」の端末の所の望遠鏡（端末の箱は描かない）。
  台    ：黒鉛の台の箱、白磁の鼻隠し、外の面の琥珀の灯、舷へ下りる斜めの支え 2 本（リフトのガイド・かごの通り道の外）。
部屋（ch1.lower・ch1.mid）では飾り（dress）として、オルドと同じ pos（tools/dress_town.py の ORDO_POS）に置く。オルドのモデル（ordo.py）も
同じ形を部品 lift_landing として持ち（町の部屋の外・確認ページ・紹介の画像）、飾りを置く部屋では OrdoView がその部品を隠す（同じ所に 2 つ描かない）。
寸法はオルドの踊り場（ordo.py の LIFT_Y・LANDING_TOP・landing_x）と、下段の当たり判定の形（ch1_town.json：床の箱 x 47.9〜71・z -13〜+5、柵 3 つ
（高さ 1.45 m）、日よけの柱 4 本、端末）に合わせる。下段の部屋の座標 = この座標 + (0, -1.5, 8)。
当たり判定（ベンチ・木箱・携行灯）は dress_town.py が部品の中の箱（landing_solid）で付ける。手すり・柱・端末の箱は部屋の形のまま。
"""
from __future__ import annotations

import math

import numpy as np

import town_parts as P
from town_geo import Part, Piece, _orient_dir, beam, boxb, cyl, lathe, sheet, sway, tube

# ---------------------------------------------------------------- 寸法（オルドの座標、m）

L = 1.5                       # 床の上の面（背の面の 1.5 m 上 = 下段の床）
X_IN, X_OUT = 48.0, 71.0      # 床の内の端（下段の床の箱の東の端）・外の端（外の柵の外の面）
X_SLAB = 48.5                 # 台の箱の内の端（ordo.landing_x()）
Z_S, Z_N = -21.0, -3.0        # 南（船尾）・北（船首）の端
HULL = 55.0                   # 舷の外の面（ordo.half_w(LIFT_Y)）
BAND = 0.45                   # 北・南の縁の黒鉛の帯の幅（柵の下）
RAIL_X, RAIL_ZN, RAIL_ZS = 70.75, -3.35, -20.65   # 柵の真ん中の線（下段の柵の箱 x 70.5〜71・z 4.3〜5.0・-13〜-12.3）
RAIL_H = 1.45                 # 柵の高さ（当たり判定の箱と同じ）
RAIL_IN = 49.2                # 北・南の手すりの内の端（下段の東の低い壁の面 x 49 の前）
# 日よけの柱（x, z, 高さ）：下段の体だけの柱の箱（0.6 × 0.5）と同じ所・高さ
POSTS = ((53.0, -3.95, 7.0), (62.5, -3.95, 5.2), (53.0, -20.05, 7.0), (62.5, -20.05, 5.2))
CANOPY_X = (52.2, 63.6)       # 帆布の内・外の端
CANOPY_Z = (-20.4, -3.6)
RAFTERS = (-20.05, -14.68, -9.32, -3.95)
HATCH = (61.2, 69.2, -17.6, -6.4)   # かごの口（ordo.py：hw + 6.2〜14.2、LIFT_Y ± 5.6）
HATCH_RIM = 0.4
TERMINAL = (70.2, -18.5)      # 「見下ろす」の端末（下段の (70.2, 0, -10.5)、yaw 270。当たり判定 x 69.9〜70.5・z -18.9〜-18.1・高さ 1.2）
BENCH_S = (57.75, -4.06)      # 日よけの下のベンチ（南向き：背を北の柵へ 2 cm）
BENCH_E = (68.6, -4.71)       # 北東の角のベンチ（外向き：端を北の柵へ 2 cm）
CRATES = ((57.5, -19.81), (58.46, -19.81))   # 南の柵の前の木箱（柵・隣の箱と 2 cm）
COIL = (59.62, -19.86)        # 巻いた綱（床の上の薄い物。当たり判定なし）

SWAY_CANOPY = 0.22            # 帆布の垂木の間のふくらみの重み（town_parts.SWAY_CANVAS より少し大きい：広い帆布）
SWAY_EDGE = 0.25              # 帆布の外の縁（梁から 1.1 m 出た所）


def _slope_y(x):
    """垂木の下の線（内の梁の上 L + 7.26 → 外の梁の上 L + 5.46）"""
    return L + 7.26 + (x - 53.0) * (5.46 - 7.26) / (62.5 - 53.0)


def _quad_up(x0, x1, z0, z1, y, mat, p: Part):
    v = np.array([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]], float)
    p.add(mat, _orient_dir(Piece(v, [[0, 1, 2, 3]]), (0, 1, 0)))


# ---------------------------------------------------------------- 台（床の下）

def _slab(p: Part):
    """黒鉛の台の箱・白磁の鼻隠し（2.8 m ごとの板、すき間は黒鉛）・外の面の琥珀の灯・舷へ下りる斜めの支え"""
    p.add('graphite', boxb(X_SLAB, X_OUT - 0.1, L - 3.4, L - 0.06, Z_S + 0.1, Z_N - 0.1))
    # 下の縁の真鍮の帯（外の縁と北・南の縁）
    p.add('brass', boxb(X_OUT - 0.5, X_OUT - 0.06, L - 3.48, L - 3.38, Z_S + 0.14, Z_N - 0.14))
    for z0, z1 in ((Z_S + 0.14, Z_S + 0.5), (Z_N - 0.5, Z_N - 0.14)):
        p.add('brass', boxb(HULL + 0.3, X_OUT - 0.5, L - 3.48, L - 3.38, z0, z1))
    # 鼻隠し：外の面（x）と北・南の面（z）
    n = int(round((Z_N - Z_S) / 2.8))
    for k in range(n):
        a = Z_S + (Z_N - Z_S) * k / n + 0.05
        b = Z_S + (Z_N - Z_S) * (k + 1) / n - 0.05
        p.add('ivory', boxb(X_OUT - 0.1, X_OUT, L - 0.62, L - 0.08, a, b))
    n = int(round((X_OUT - X_SLAB - 0.1) / 2.8))
    for z0, z1 in ((Z_S, Z_S + 0.1), (Z_N - 0.1, Z_N)):
        for k in range(n):
            a = X_SLAB + 0.6 + (X_OUT - 0.1 - X_SLAB - 0.6) * k / n + 0.05
            b = X_SLAB + 0.6 + (X_OUT - 0.1 - X_SLAB - 0.6) * (k + 1) / n - 0.05
            p.add('ivory', boxb(a, b, L - 0.62, L - 0.08, z0, z1))
    # 外の面の琥珀の灯（夜に台の縁が分かる）と、北・南の面の真鍮の留め板
    for z in (Z_S + 1.2, (Z_S + Z_N) / 2, Z_N - 1.2):
        p.add('graphite', boxb(X_OUT - 0.1, X_OUT + 0.06, L - 2.75, L - 1.25, z - 0.55, z + 0.55))
        p.add('amber', boxb(X_OUT + 0.06, X_OUT + 0.1, L - 2.55, L - 1.45, z - 0.4, z + 0.4))
    # 舷へ下りる斜めの支え（リフトのガイド z -19〜-5・かごの通り道の外）：黒鉛の角材と真鍮の受け。下の端は帯の下の梁の上の弦材
    # （ordo.frame_x：背の面の 13.9 m 下で x 52.6）の外の面
    for z in (Z_S + 0.45, Z_N - 0.45):
        a, b = np.array([HULL - 2.2, L - 15.4, z]), np.array([67.5, L - 3.4, z])
        p.add('graphite', beam(a, b, 0.5, 0.6, up=(0, 0, 1)))
        p.add('brass', boxb(HULL - 2.45, HULL - 2.05, L - 16.3, L - 14.5, z - 0.4, z + 0.4))
        p.add('brass', boxb(66.6, 68.4, L - 3.5, L - 3.36, z - 0.4, z + 0.4))


# ---------------------------------------------------------------- 床

def _strip(p: Part, x0, x1, z0, z1, top=0.02, mat='graphite'):
    """床の黒鉛の帯（板より top だけ上。下は台の上の面）"""
    p.add(mat, boxb(x0, x1, L - 0.06, L + top, z0, z1))


def _hazard(p: Part, x0, x1, z0, z1, top, seg=0.6):
    """真鍮と黒の縞の縁（下段のリフトと同じ）"""
    along_x = (x1 - x0) >= (z1 - z0)
    length = (x1 - x0) if along_x else (z1 - z0)
    n = max(2, int(round(length / seg)))
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        mat = 'brass' if k % 2 == 0 else 'dark'
        if along_x:
            p.add(mat, boxb(x0 + (x1 - x0) * t0, x0 + (x1 - x0) * t1, L - 0.06, L + top, z0, z1))
        else:
            p.add(mat, boxb(x0, x1, L - 0.06, L + top, z0 + (z1 - z0) * t0, z0 + (z1 - z0) * t1))


def _field(p: Part, x0, x1, z0, z1, planks: bool):
    """板の面。キットの部品（planks=False）は 1 枚の面（板の模様と汚れはキットの材質 deck の絵）。オルドのモデルの部品
    （planks=True：頂点の色の 1 色で描く）は、幅 0.3 m の板（x の向き。絵の板と同じ向き）を 3 cm のすき間を空けて並べ、すき間から暗い下地が見える"""
    if not planks:
        _quad_up(x0, x1, z0, z1, L, 'deck', p)
        return
    _quad_up(x0, x1, z0, z1, L - 0.012, 'dark', p)
    n = max(1, int(round((z1 - z0) / 0.33)))
    for k in range(n):
        a = z0 + (z1 - z0) * k / n + 0.015
        b = z0 + (z1 - z0) * (k + 1) / n - 0.015
        _quad_up(x0, x1, a, b, L, 'deck', p)


def _deck(p: Part, planks=False):
    """板張りの床（材質 deck）を黒鉛の帯で区切る。ふたは白磁の 2 枚の扉"""
    hx0, hx1, hz0, hz1 = HATCH
    r = HATCH_RIM
    zs, zn = Z_S + BAND, Z_N - BAND
    # 縁の帯（北・南・外。外は柵の下）と内の敷居（下段の床に続く）、梁の帯 2 本（日よけの内の柱の下・真ん中）
    _strip(p, X_IN, X_OUT - 0.1, Z_S, zs)
    _strip(p, X_IN, X_OUT - 0.1, zn, Z_N)
    _strip(p, X_OUT - 0.5, X_OUT - 0.1, zs, zn)
    _strip(p, X_IN, X_IN + 0.6, zs, zn, top=0.025)
    p.add('brass', boxb(X_IN + 0.6, X_IN + 0.66, L - 0.06, L + 0.03, zs, zn))
    p.add('brass', boxb(X_OUT - 0.12, X_OUT + 0.02, L - 0.1, L + 0.035, Z_S - 0.02, Z_N + 0.02))      # 外の縁金具
    for z0, z1 in ((Z_S - 0.02, Z_S + 0.02), (Z_N - 0.02, Z_N + 0.02)):
        p.add('brass', boxb(X_SLAB + 0.6, X_OUT, L - 0.1, L + 0.035, z0, z1))
    beams = ((52.75, 53.25), (56.88, 57.12))
    for a, b in beams:
        _strip(p, a, b, zs, zn)
        for z in np.arange(zs + 0.6, zn - 0.3, 1.2):
            for x in ((a + 0.09, b - 0.09) if b - a > 0.3 else ((a + b) / 2,)):
                p.add('brass', boxb(x - 0.035, x + 0.035, L + 0.02, L + 0.035, z - 0.035, z + 0.035))
    # かごの口のふたの縁（真鍮と黒の縞、板より 4 cm 上）
    _hazard(p, hx0 - r, hx1 + r, hz0 - r, hz0, 0.04)
    _hazard(p, hx0 - r, hx1 + r, hz1, hz1 + r, 0.04)
    _hazard(p, hx0 - r, hx0, hz0, hz1, 0.04)
    _hazard(p, hx1, hx1 + r, hz0, hz1, 0.04)
    # 板の面（帯とふたの縁の間）
    xs = [X_IN + 0.66, beams[0][0], beams[0][1], beams[1][0], beams[1][1], hx0 - r]
    for a, b in ((xs[0], xs[1]), (xs[2], xs[3]), (xs[4], xs[5])):
        _field(p, a, b, zs, zn, planks)
    _field(p, hx0 - r, hx1 + r, hz1 + r, zn, planks)
    _field(p, hx0 - r, hx1 + r, zs, hz0 - r, planks)
    _field(p, hx1 + r, X_OUT - 0.5, zs, zn, planks)
    # ふた：下の黒鉛の受け、白磁の扉 2 枚（板 3 枚ずつ。継ぎ目 6 cm）、扉の合わせ目の真鍮の桟、蝶番と吊り環
    p.add('graphite', boxb(hx0, hx1, L - 0.06, L - 0.005, hz0, hz1))
    xm = (hx0 + hx1) / 2
    for a, b in ((hx0 + 0.04, xm - 0.05), (xm + 0.05, hx1 - 0.04)):
        for j in range(2):
            x0 = a + (b - a) * j / 2 + (0.035 if j else 0.0)
            x1 = a + (b - a) * (j + 1) / 2 - (0.035 if j == 0 else 0.0)
            for k in range(3):
                z0 = hz0 + 0.04 + (hz1 - hz0 - 0.08) * k / 3 + (0.035 if k else 0.0)
                z1 = hz0 + 0.04 + (hz1 - hz0 - 0.08) * (k + 1) / 3 - (0.035 if k < 2 else 0.0)
                p.add('ivory2', boxb(x0, x1, L - 0.04, L + 0.025, z0, z1))
    p.add('brass', boxb(xm - 0.05, xm + 0.05, L - 0.04, L + 0.035, hz0 + 0.04, hz1 - 0.04))
    for x in (hx0 + 0.04, hx1 - 0.04):
        for z in np.linspace(hz0 + 1.2, hz1 - 1.2, 4):
            p.add('brass', cyl((x, L + 0.045, z - 0.22), (x, L + 0.045, z + 0.22), 0.05, 8))
    for x in (hx0 + 1.2, hx1 - 1.2):
        for z in (hz0 + 2.6, hz1 - 2.6):
            p.add('brass', boxb(x - 0.16, x + 0.16, L + 0.025, L + 0.04, z - 0.05, z + 0.05))
            p.add('brass', tube([(x - 0.13, L + 0.04, z), (x - 0.1, L + 0.045, z + 0.12), (x + 0.1, L + 0.045, z + 0.12),
                                 (x + 0.13, L + 0.04, z)], 0.018, 5))


# ---------------------------------------------------------------- 手すり

def _rail_line(p: Part, a, b, lamps=False, skip_first=False):
    """a → b（(x, z)）の手すり：真鍮の柱（2 m 以下ごと、黒鉛の座金と真鍮の笠）・真鍮の上の棒・黒鉛の中の棒 2 本・黒鉛の足元の板。
    lamps：柱 1 本おきに琥珀の灯（町の段々の手すり town_terrace._rail と同じ）"""
    a3, b3 = np.array([a[0], L, a[1]], float), np.array([b[0], L, b[1]], float)
    d = b3 - a3
    length = float(np.linalg.norm(d))
    n = max(1, int(math.ceil(length / 2.0)))
    side = np.array([-d[2], 0.0, d[0]]) / length
    for k in range(n + 1):
        if skip_first and k == 0:
            continue
        c = a3 + d * (k / n)
        p.add('graphite', boxb(c[0] - 0.08, c[0] + 0.08, L + 0.02, L + 0.06, c[2] - 0.08, c[2] + 0.08))
        p.add('brass', cyl(c + [0, 0.06, 0], c + [0, RAIL_H - 0.08, 0], 0.04, 8))
        p.add('brass', cyl(c + [0, RAIL_H - 0.1, 0], c + [0, RAIL_H - 0.005, 0], 0.056, 8))
        if lamps and k % 2 == 1:
            p.add('amber', boxb(c[0] - 0.05, c[0] + 0.05, L + RAIL_H, L + RAIL_H + 0.12, c[2] - 0.05, c[2] + 0.05))
            p.add('brass', boxb(c[0] - 0.07, c[0] + 0.07, L + RAIL_H + 0.12, L + RAIL_H + 0.16, c[2] - 0.07, c[2] + 0.07))
    top = RAIL_H - 0.045
    p.add('brass', cyl(a3 + [0, top, 0], b3 + [0, top, 0], 0.045, 8, cap=False))
    for y in (0.95, 0.52):
        p.add('graphite', cyl(a3 + [0, y, 0], b3 + [0, y, 0], 0.028, 6, cap=False))
    # 足元の板（柱の間、2 cm 上から 0.16 m）
    w = 0.035
    q0, q1 = a3 + side * w / 2, b3 - side * w / 2
    p.add('graphite', boxb(min(q0[0], q1[0], a3[0] - w / 2, b3[0] - w / 2), max(q0[0], q1[0], a3[0] + w / 2, b3[0] + w / 2),
                           L + 0.02, L + 0.18,
                           min(q0[2], q1[2], a3[2] - w / 2, b3[2] - w / 2), max(q0[2], q1[2], a3[2] + w / 2, b3[2] + w / 2)))


def _railing(p: Part):
    _rail_line(p, (RAIL_X, RAIL_ZS), (RAIL_X, RAIL_ZN), lamps=True)
    _rail_line(p, (RAIL_X, RAIL_ZN), (RAIL_IN, RAIL_ZN), skip_first=True)
    _rail_line(p, (RAIL_X, RAIL_ZS), (RAIL_IN, RAIL_ZS), skip_first=True)


# ---------------------------------------------------------------- 日よけ

def _canopy_t(z):
    """z → (垂木の間の割合 0〜1、帆布の上かどうか)。垂木の外（張り出し）は -1"""
    for z0, z1 in zip(RAFTERS[:-1], RAFTERS[1:]):
        if z0 - 1e-6 <= z <= z1 + 1e-6:
            return (z - z0) / (z1 - z0)
    return -1.0


def _canopy_weight(v):
    """帆布の揺れの重み（位置だけ：x・z）：垂木の上で 0、垂木の間の真ん中で SWAY_CANOPY、外の張り出しで SWAY_EDGE まで、
    北・南の張り出しは端ほど大きく"""
    x, z = v[:, 0], v[:, 2]
    out = np.zeros(len(v))
    for i in range(len(v)):
        t = _canopy_t(z[i])
        w = SWAY_CANOPY * math.sin(math.pi * t) if t >= 0 else 0.15 * min(1.0, min(abs(z[i] - RAFTERS[0]), abs(z[i] - RAFTERS[-1])) / 0.35)
        w += SWAY_EDGE * float(np.clip((x[i] - 62.5) / (CANOPY_X[1] - 62.5), 0.0, 1.0))
        out[i] = w
    return out


def _canopy(p: Part):
    """日よけの骨組み：柱 4 本・内と外の梁・垂木 4 本・外の縁の竿・内の柱の上の小旗・吊り灯 2 つ（帆布は _awning：影を落とす別の部品）"""
    for x, z, h in POSTS:
        top = L + h
        p.add('graphite', boxb(x - 0.24, x + 0.24, L + 0.02, L + 0.07, z - 0.21, z + 0.21))
        p.add('graphite', boxb(x - 0.15, x + 0.15, L + 0.07, top, z - 0.13, z + 0.13))
        for y in (L + 0.07, L + 1.05, top - 0.55):
            p.add('brass', boxb(x - 0.18, x + 0.18, y, y + 0.14, z - 0.16, z + 0.16))
    for x, h in ((53.0, 7.0), (62.5, 5.2)):
        p.add('graphite', boxb(x - 0.18, x + 0.18, L + h, L + h + 0.26, CANOPY_Z[0] + 0.15, CANOPY_Z[1] - 0.15))
        for z in (RAFTERS[0], RAFTERS[-1]):
            p.add('brass', boxb(x - 0.2, x + 0.2, L + h - 0.12, L + h + 0.02, z - 0.17, z + 0.17))
    x0, x1 = CANOPY_X
    for z in RAFTERS:
        a = np.array([x0 + 0.05, _slope_y(x0 + 0.05) + 0.08, z])
        b = np.array([x1 - 0.05, _slope_y(x1 - 0.05) + 0.08, z])
        p.add('graphite', beam(a, b, 0.12, 0.16))
    ye = _slope_y(x1) + 0.16
    xd = x1 + 0.02
    p.add('brass', cyl((xd, ye + 0.01, CANOPY_Z[0]), (xd, ye + 0.01, CANOPY_Z[1]), 0.03, 6))
    # 内の柱の上の小旗（竿は梁の上から 1.5 m。風下 -Z へなびく：町は船首からの風）
    for z in (RAFTERS[0], RAFTERS[-1]):
        y0 = L + 7.26
        p.add('brass', cyl((53.0, y0, z), (53.0, y0 + 1.55, z), 0.045, 8))
        p.add('brass', lathe((53.0, y0 + 1.55, z), (53.0, y0 + 1.75, z), [(0, 0.09), (1, 0.02)], 8))
        top, width, length = y0 + 1.45, 1.1, 0.75

        def flag(u, v, z=z, top=top, width=width, length=length):
            return (53.0 + 0.05 * math.sin(u * 4 + v), top - length * v, z - (0.06 + width * u))
        p.add('cloth', sway(sheet(flag, 4, 3, 0.02), lambda q, z=z, width=width: np.clip((z - 0.06 - q[:, 2]) / width, 0, 1) ** 1.2))
    # 吊り灯（真ん中の垂木 2 本から。灯の下の端は床から 5.2 m：跳んでも頭が届かない）
    for z in RAFTERS[1:3]:
        x = 57.75
        yb = _slope_y(x)
        yl = yb - 0.95
        p.add('graphite', cyl((x, yl + 0.42, z), (x, yb, z), 0.012, 5))
        p.add('brass', boxb(x - 0.08, x + 0.08, yb - 0.04, yb + 0.005, z - 0.08, z + 0.08))
        P.lantern(p, x, yl, z, 1.25)


def _awning(p: Part):
    """日よけの帆布（部品 ordo_landing_awning。帆布だけを、影を落とす別の部品にする：踊り場の全部に影を付けると、影の描画が
    面 4 つ × 影の段 4 つ = 16 回増えた。帆布は面 1 つなので 4 回）"""
    x0, x1 = CANOPY_X
    # 帆布：垂木の上（垂木の上の面 + 1.5 cm）、垂木の間で 0.1 m たるむ。北・南は垂木の外へ 0.35 m。
    # 斜面に沿った縞（赤い帆布と生成りの麻を交互に、垂木の間に 4 本ずつ）：上の中段から見下ろすと 1 枚の大きな赤い板に見えたので
    def cloth_y(x, z):
        t = _canopy_t(z)
        sag = 0.1 * math.sin(math.pi * t) if t >= 0 else 0.03 * min(1.0, min(abs(z - RAFTERS[0]), abs(z - RAFTERS[-1])) / 0.35)
        return _slope_y(x) + 0.16 + 0.015 - sag
    edges = [CANOPY_Z[0]]
    for z0, z1 in zip(RAFTERS[:-1], RAFTERS[1:]):
        edges += [z0 + (z1 - z0) * k / 4 for k in range(4)]
    edges += [RAFTERS[-1], CANOPY_Z[1]]
    stripes = [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
    for i, (za, zb) in enumerate(stripes):
        mat = 'cloth' if (i - 1) % 2 == 0 or i == 0 or i == len(stripes) - 1 else 'linen'

        def cloth(u, v, za=za, zb=zb):
            x = x0 + (x1 - x0) * u
            z = za + (zb - za) * v
            return (x, cloth_y(x, z), z)
        p.add(mat, sway(sheet(cloth, 8, 2, 0.03), _canopy_weight))
    # 外の縁の垂れ（波形、0.45 m）：上の端は帆布の縁と同じ重み、下へ SWAY_DROP まで
    ye = _slope_y(x1) + 0.16
    xd = x1 + 0.02

    def valance(u, v):
        z = CANOPY_Z[0] + (CANOPY_Z[1] - CANOPY_Z[0]) * u
        return (xd, ye - 0.45 * v * (0.74 + 0.26 * math.cos(u * math.pi * 2 * (CANOPY_Z[1] - CANOPY_Z[0]) / 1.1)), z)

    def valance_w(v):
        edge = _canopy_weight(np.stack([np.full(len(v), x1), v[:, 1], v[:, 2]], 1))
        return edge + P.SWAY_DROP * np.clip((ye - v[:, 1]) / 0.45, 0.0, 1.0)
    p.add('cloth2', sway(sheet(valance, int((CANOPY_Z[1] - CANOPY_Z[0]) * 2.2), 1, 0.02), valance_w))


# ---------------------------------------------------------------- 小物

def _coil(p: Part, x, z):
    """巻いた綱（床の上、高さ 0.16 m）：3 段の輪と、上から垂れた端"""
    for k, (r, y) in enumerate(((0.42, 0.035), (0.36, 0.09), (0.27, 0.13))):
        pts = [(x + r * math.cos(a), L + y, z + r * math.sin(a)) for a in np.linspace(0.15 * k, 0.15 * k + 2 * math.pi, 15)]
        p.add('rope', tube(pts, 0.035, 5))
    p.add('rope', tube([(x + 0.25, L + 0.15, z + 0.05), (x + 0.5, L + 0.07, z + 0.2), (x + 0.72, L + 0.035, z + 0.12)], 0.033, 5))


def _scope(p: Part, x, z):
    """「見下ろす」の望遠鏡（端末の当たり判定の箱 0.6 × 0.8 の中に立つ）：黒鉛の台と柱、真鍮の首、外（+X）へ 22 度下を向いた双眼の箱、
    手前の接眼の筒 2 本、琥珀の小さな灯"""
    p.add('graphite', boxb(x - 0.27, x + 0.27, L + 0.02, L + 0.09, z - 0.36, z + 0.36))
    p.add('brass', boxb(x - 0.29, x + 0.29, L + 0.02, L + 0.045, z - 0.38, z + 0.38))
    p.add('graphite', lathe((x, L + 0.09, z), (x, L + 1.02, z), [(0, 0.15), (0.12, 0.1), (0.85, 0.09), (1, 0.12)], 10))
    p.add('brass', cyl((x, L + 0.98, z), (x, L + 1.08, z), 0.13, 10))
    for s in (-1, 1):
        p.add('brass', boxb(x - 0.05, x + 0.05, L + 1.06, L + 1.32, z + s * 0.2 - 0.025, z + s * 0.2 + 0.025))
    p.add('amber', boxb(x - 0.095, x - 0.08, L + 0.62, L + 0.72, z - 0.04, z + 0.04))
    ang = math.radians(-22.0)
    d = np.array([math.cos(ang), math.sin(ang), 0.0])
    c = np.array([x + 0.02, L + 1.3, z])
    a, b = c - d * 0.24, c + d * 0.26
    p.add('graphite', beam(a, b, 0.36, 0.22, up=(0, 1, 0)))
    p.add('brass', beam(c - d * 0.03, c + d * 0.03, 0.39, 0.25, up=(0, 1, 0)))
    for s in (-1, 1):
        o = np.array([0.0, 0.0, s * 0.085])
        p.add('brass', cyl(b - d * 0.02 + o, b + d * 0.06 + o, 0.075, 10))
        p.add('dark', cyl(b + d * 0.06 + o, b + d * 0.065 + o, 0.06, 10))
        p.add('graphite', cyl(a - d * 0.1 + o, a + d * 0.02 + o, 0.04, 8))
    p.add('brass', cyl((x - 0.02, L + 1.3, z - 0.21), (x - 0.02, L + 1.3, z + 0.21), 0.03, 6))


def _props(p: Part):
    """ベンチ 2 つ・木箱 3 つ・携行灯・巻いた綱・望遠鏡（当たり判定は landing_solid）"""
    p.place(P.bench(), (BENCH_S[0], L, BENCH_S[1]), 180)
    p.place(P.bench(), (BENCH_E[0], L, BENCH_E[1]), 90)
    for x, z in CRATES:
        p.place(P.crate(), (x, L, z), 0)
    p.place(P.crate(), (CRATES[0][0] + 0.02, L + 0.74, CRATES[0][1] + 0.01), 4, 0.8)
    # 携行灯は上の小さな木箱の真ん中（隣の木箱の上に置くと、上の木箱との間 0.41 m に体の丸い底が挟まって宙に止まった：test_traps）
    p.place(P.hand_lantern(), (CRATES[0][0] + 0.02, L + 0.74 + 0.592, CRATES[0][1] + 0.01))
    _coil(p, *COIL)
    _scope(p, *TERMINAL)


def ordo_landing(planks=False) -> Part:
    """踊り場の全部（帆布のほか）。帆布は ordo_landing_awning。planks：床を板 1 枚ずつの形にする（オルドのモデルの部品 lift_landing。
    頂点の色の 1 色で描くので、絵の板の代わりに形の板とすき間）"""
    p = Part('ordo_landing')
    _slab(p)
    _deck(p, planks)
    _railing(p)
    _canopy(p)
    _props(p)
    return p


def ordo_landing_awning() -> Part:
    p = Part('ordo_landing_awning')
    _awning(p)
    return p


# 当たり判定（部品の中の箱 = オルドの座標。dress_town.py が下段の dress の "solid" に書く。tools/dress_solid.py の B の書き方）：
# ベンチ（town/bench の箱を回した所）・木箱（town/crate）・上の小さな木箱・携行灯（体だけ）。手すり・日よけの柱・端末の箱は部屋の形のまま
def landing_solid():
    import dress_solid as DS
    bx, bz = BENCH_S
    ex, ez = BENCH_E
    (c1x, c1z), (c2x, c2z) = CRATES
    return [
        DS.B(bx - 0.99, bx + 0.99, L, L + 0.56, bz - 0.24, bz + 0.34), DS.B(bx - 0.99, bx + 0.99, L, L + 1.07, bz + 0.18, bz + 0.34),
        DS.B(ex - 0.34, ex + 0.24, L, L + 0.56, ez - 0.99, ez + 0.99), DS.B(ex - 0.34, ex - 0.18, L, L + 1.07, ez - 0.99, ez + 0.99),
        DS.B(c1x - 0.47, c1x + 0.47, L, L + 0.74, c1z - 0.47, c1z + 0.47), DS.B(c2x - 0.47, c2x + 0.47, L, L + 0.74, c2z - 0.47, c2z + 0.47),
        DS.R(c1x + 0.02, c1z + 0.01, 0.752, 0.752, L + 0.74, L + 0.74 + 0.592, 4),
        DS.B(c1x + 0.02 - 0.13, c1x + 0.02 + 0.13, L + 1.332, L + 1.332 + 0.69, c1z + 0.01 - 0.13, c1z + 0.01 + 0.13, cam=False),
    ]


PARTS = {'ordo_landing': ordo_landing, 'ordo_landing_awning': ordo_landing_awning}
