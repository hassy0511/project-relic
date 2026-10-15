"""遺構 B4（心臓部）だけの部品。絵：W2-06 ruins_mood_b4.png（円形の広間・外周のレール・4 本の柱・奥の炉心の扉）、ruins_core.png（炉心の停止と再始動）。
壁・梁・管・扉は B3 の部品（ruins_b3.py）を B4 のキット（ruins_b4.json：床と柱は白磁で読みやすく、外周は黒鉛と真鍮、赤い非常灯は外周、
琥珀は柱と扉）で使う。ここは B4 にしか無い形：炉心、太い柱の白磁の覆い、円形の広間の壁の区画と天井、炉心の扉の丸い枠、床の同心の輪。

材質の名前は B3 と同じ（ivory・graphite・brass・amber・red・dark・grate・pipe・ivory_stain・glass）と、core_glow（炉心の窓。再始動の琥珀の光）。
"""
from __future__ import annotations

import math

from geo import Part
from ruins_b1 import apply, rot

G, I, B, A, R = 'graphite', 'ivory', 'brass', 'amber', 'red'
IS = 'ivory_stain'


def core():
    p = Part('b4_core', '炉心（直立した円筒の発電装置。当たり判定：台 5×0.6×5、芯 2.4×3.4×2.4（0.6〜4.0）、冠 3.2×0.4×3.2（4.0〜4.4）に合わせる）：'
             '芯の下は白磁の四角い覆い（通風の格子）、上は黒鉛の円筒（半径 1.15）に琥珀の窓の輪 3 段と真鍮の継ぎ輪、天井 10 m まで。原点：台の底の中央')
    # 台（5×0.6×5）の縁と段の黒鉛・真鍮（台の上の面 0.6 に 1.5 cm 載せる）
    for k in range(4):
        n0 = len(p.pieces)
        p.box(G, (-2.52, -2.52, 0.0), (2.52, -2.5, 0.6))
        p.box(B, (-2.5, -2.5, 0.6), (2.5, -2.3, 0.615))
        p.box(A, (-1.2, -2.535, 0.26), (1.2, -2.52, 0.32))
        p.transformed(apply(rot('z', 90 * k)), n0)
    # 芯の下の白磁の覆い（芯の箱 2.4 角の面から 2 cm 外、0.6〜2.2）と通風の格子
    p.cbox(IS, (0, 0, 1.4), (2.44, 2.44, 1.6), 0.05)
    for k in range(4):
        n0 = len(p.pieces)
        p.box('grate', (-0.75, -1.235, 0.85), (-0.15, -1.22, 1.85))
        p.box('grate', (0.15, -1.235, 0.85), (0.75, -1.22, 1.85))
        p.box(G, (-0.06, -1.24, 0.7), (0.06, -1.22, 2.1))
        p.box(A, (-0.03, -1.25, 1.15), (0.03, -1.238, 1.55))
        p.transformed(apply(rot('z', 90 * k)), n0)
    # 黒鉛の円筒（2.2〜10）、琥珀の窓の輪 3 段、真鍮の継ぎ輪
    p.cyl(G, (0, 0, 2.2), (0, 0, 10.0), 1.15, 24)
    for z0, z1 in ((2.5, 3.6), (5.2, 6.6), (7.6, 8.8)):
        p.cyl('core_glow', (0, 0, z0), (0, 0, z1), 1.18, 24)
        for k in range(8):
            a = 2 * math.pi * k / 8
            x, y = 1.2 * math.cos(a), 1.2 * math.sin(a)
            p.box(G, (x - 0.06, y - 0.06, z0), (x + 0.06, y + 0.06, z1))
            p.transformed(apply(rot('z', math.degrees(a))), len(p.pieces) - 1)
    for z in (2.2, 3.62, 4.4, 5.0, 6.62, 7.4, 8.82, 9.7):
        p.cyl(B, (0, 0, z), (0, 0, z + 0.16), 1.27, 24)
    # 冠（3.2 角・4.0〜4.4）の真鍮の板の縁
    p.cbox(G, (0, 0, 4.2), (3.24, 3.24, 0.42), 0.08)
    return p


def column(name='b4_column', w=1.0, h=9.0):
    p = Part(name, f'太い柱の覆い（当たり判定 {w}×{h}×{w} の柱に、白磁の大きな覆いの塊 3 段（柱の面から 0.1 m 外）、黒鉛の芯と脚、真鍮の金具、'
             '琥珀の縦の灯）。原点：底の中央')
    hw = w / 2
    p.box(G, (-hw, -hw, 0), (hw, hw, h))
    jw = hw + 0.1
    for z0, z1, m in ((0.0, 1.3, IS), (2.6, 4.4, I), (5.8, 7.2, I)):
        if z1 > h:
            continue
        p.cbox(m, (0, 0, (z0 + z1) / 2), (2 * jw, 2 * jw, z1 - z0), 0.08)
        p.cbox(B, (0, 0, z1 + 0.06), (2 * jw - 0.1, 2 * jw - 0.1, 0.12), 0.03)
    for k in range(4):
        n0 = len(p.pieces)
        p.box(A, (-0.05, -jw - 0.012, 3.0), (0.05, -jw + 0.01, 4.0))
        p.box(G, (-0.14, -hw - 0.05, 1.3), (0.14, -hw + 0.01, 2.6))
        p.transformed(apply(rot('z', 90 * k)), n0)
    return p


def arena_panel():
    p = Part('b4_arena_panel', '円形の広間の壁の区画（幅 3.3・高さ 16。当たり判定の壁の区画の内の面に付く）：白磁の板 2 段、黒鉛の枠、'
             '高さ 3 m と 8.5 m の外周の通路の手すりと赤い非常灯の帯、上の黒鉛の冠。どれも面から 0.3 m まで。原点：内の面の下の端の中央')
    W = 3.3
    hw = W / 2
    p.box('dark', (-hw, -0.04, 0), (hw, 0, 16))
    p.box(G, (-hw, -0.25, 0), (hw, 0, 0.4))
    p.box(B, (-hw, -0.262, 0.34), (hw, -0.248, 0.37))
    # 白磁の板（下は汚れ）
    p.cbox(IS, (0, -0.12, 1.55), (W - 0.5, 0.1, 2.1), 0.05, 'y')
    p.cbox(I, (0, -0.12, 5.6), (W - 0.5, 0.1, 3.6), 0.05, 'y')
    p.cbox(I, (0, -0.12, 11.5), (W - 0.5, 0.1, 4.2), 0.05, 'y')
    # 黒鉛の柱（両端）と真鍮の金具
    for sx in (-1, 1):
        x0, x1 = sorted((sx * hw, sx * (hw - 0.2)))
        p.box(G, (x0, -0.28, 0), (x1, -0.02, 16))
    # 外周の通路（高さ 3.0 と 8.5 の黒鉛の帯）と赤い非常灯の帯
    for z in (3.0, 8.5, 13.8):
        p.box(G, (-hw, -0.3, z - 0.3), (hw, 0, z))
        p.box(R, (-hw + 0.3, -0.315, z - 0.22), (hw - 0.3, -0.3, z - 0.1))
        p.box(B, (-hw, -0.31, z), (hw, -0.05, z + 0.05))
    p.box(G, (-hw, -0.3, 15.4), (hw, 0, 16))
    # 琥珀の小さな灯（柱の足元）
    p.box(A, (-0.05, -0.27, 0.45), (0.05, -0.255, 0.7))
    return p


def ceiling(R0=17.5):
    p = Part('b4_ceiling', f'円形の広間の天井（半径 {R0} m の黒鉛の円板と、真ん中の輪、放射の梁 12 本、外周の赤い灯の輪）。下向き。原点：天井の下の面の中心')
    n = 36
    import numpy as np
    v = [(0.0, 0.0, 0.0)] + [(R0 * math.cos(2 * math.pi * k / n), R0 * math.sin(2 * math.pi * k / n), 0.0) for k in range(n)]
    vv = np.asarray(v, float)
    faces = []
    for k in range(n):
        tri = [0, 1 + k, 1 + (k + 1) % n]
        a, b, c = vv[tri]
        faces.append(tri if np.cross(b - a, c - a)[2] < 0 else tri[::-1])
    p.pieces.append(('dark', vv, faces, False))
    for k in range(12):
        a = 2 * math.pi * k / 12
        n0 = len(p.pieces)
        p.box(G, (-0.3, 3.0, -0.9), (0.3, R0, -0.02))
        p.box(B, (-0.32, 3.0, -0.95), (0.32, R0, -0.9))
        p.transformed(apply(rot('z', math.degrees(a))), n0)
    ring = [(3.0 * math.cos(2 * math.pi * k / 24), 3.0 * math.sin(2 * math.pi * k / 24), -0.6) for k in range(25)]
    p.sweep(G, ring, 0.5, 8)
    p.cyl(A, (0, 0, -0.3), (0, 0, -0.5), 1.2, 16)
    return p


def vault(R0=3.6):
    p = Part('b4_vault', f'炉心の扉の丸い枠（外の半径 {R0}、黒鉛の輪に真鍮の留め 12、琥珀の灯 4、両脇の黒鉛の柱と赤い非常灯）。扉の板（ゲームの扉）を囲む。'
             '原点：壁の面の、扉の下の端の中央。輪の中心は 3 m の高さ。壁から 0.3 m まで')
    cz = 3.0
    ring = [(R0 * 0.9 * math.cos(2 * math.pi * k / 40), -0.16, cz + R0 * 0.9 * math.sin(2 * math.pi * k / 40)) for k in range(41)]
    p.sweep(G, ring, R0 * 0.1, 8)
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        x, z = R0 * 0.9 * math.cos(a), cz + R0 * 0.9 * math.sin(a)
        if z < 0.2:
            continue
        p.cbox(B, (x, -0.28, z), (0.34, 0.08, 0.34), 0.04)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        x, z = R0 * 0.9 * math.cos(a), cz + R0 * 0.9 * math.sin(a)
        if z < 0.2:
            continue
        p.box(A, (x - 0.1, -0.31, z - 0.1), (x + 0.1, -0.29, z + 0.1))
    for sx in (-1, 1):
        x = sx * (R0 + 0.3)
        p.box(G, (x - 0.25, -0.28, 0), (x + 0.25, 0, 7.0))
        p.box(R, (x - 0.04, -0.295, 2.0), (x + 0.04, -0.28, 4.6))
        p.cbox(B, (x, -0.15, 7.05), (0.6, 0.32, 0.14), 0.03)
    # 扉の上の琥珀の灯（扉の板 4.5 m の上）
    p.box(G, (-0.6, -0.3, 4.85), (0.6, 0, 5.05))
    p.box(A, (-0.5, -0.315, 4.9), (0.5, -0.3, 5.0))
    return p


def floor_rings():
    p = Part('b4_floor_rings', '円形の床の同心の輪（床から 1.5 cm の薄い板：真ん中の円 r 2.5、黒鉛の輪 r 6.2・14.2、真鍮の細い輪 r 6.6）。原点：床の中心')
    import numpy as np

    def annulus(mat, r0, r1, z, n=48):
        v = []
        for k in range(n):
            a = 2 * math.pi * k / n
            v.append((r0 * math.cos(a), r0 * math.sin(a), z))
            v.append((r1 * math.cos(a), r1 * math.sin(a), z))
        vv = np.asarray(v, float)
        f = []
        for k in range(n):
            q = [2 * k, 2 * ((k + 1) % n), 2 * ((k + 1) % n) + 1, 2 * k + 1]
            a_, b_, c_ = vv[q[0]], vv[q[1]], vv[q[2]]
            f.append(q if np.cross(b_ - a_, c_ - a_)[2] > 0 else q[::-1])
        p.pieces.append((mat, vv, f, False))
    annulus(G, 2.3, 2.6, 0.015)
    annulus(B, 6.5, 6.7, 0.015)
    annulus(G, 6.0, 6.4, 0.015)
    annulus(G, 13.9, 14.5, 0.015)
    annulus(B, 2.6, 2.75, 0.015)
    # 真ん中の円（黒鉛）と放射の継ぎ目
    n = 32
    v = [(0.0, 0.0, 0.015)] + [(2.3 * math.cos(2 * math.pi * k / n), 2.3 * math.sin(2 * math.pi * k / n), 0.015) for k in range(n)]
    vv = np.asarray(v, float)
    f = []
    for k in range(n):
        tri = [0, 1 + k, 1 + (k + 1) % n]
        a_, b_, c_ = vv[tri]
        f.append(tri if np.cross(b_ - a_, c_ - a_)[2] > 0 else tri[::-1])
    p.pieces.append(('dark', vv, f, False))
    for k in range(8):
        a = 2 * math.pi * k / 8
        n0 = len(p.pieces)
        p.box(G, (-0.05, 2.75, 0.0), (0.05, 6.0, 0.012))
        p.box(G, (-0.05, 6.7, 0.0), (0.05, 13.9, 0.012))
        p.transformed(apply(rot('z', math.degrees(a) + 22.5)), n0)
    return p


PARTS = [core, lambda: column('b4_column', 1.0, 9.0), lambda: column('b4_column_wide', 1.4, 8.0), arena_panel, ceiling, vault, floor_rings]
