"""遺構 B3（駆動層）のキットの部品。絵：W2-06 ruins_kit_b3(_front/_side/_top/_assembled).png、ruins_mood_b3.png、ruins_gimmicks.png、
ruins_cracked_wall.png。寸法は spec_ruins_3d.md（2 m の格子。B1・B2 と同じ寸法・接続面）。B3 は「柱と壁に直線の琥珀の導光管、床の縁に駆動梁」：
白磁の大きな板を黒鉛の枠で囲み、柱の縦に琥珀の導光管（真鍮の継ぎ輪）。停止中は赤い非常灯、復電後は導光管が経路を示す（灯は別の材質 amber）。

原点・向きは B1（ruins_b1.py の冒頭）と同じ。壁に付く物は壁の面から RELIEF（0.35 m）まで。
材質の名前（Godot のキット ruins_b3.json・ruins_b4.json で置き換わる）：ivory・graphite・brass・amber・red・dark・grate・pipe・
ivory_stain（駆動部の足元・導光管の下の汚れた白磁）・stain_soot・glass（導光管の琥珀のガラス）
B4（心臓部）の部屋も、この部品を ruins_b4 のキット（色と汚れが別）で使う。B4 だけの部品は ruins_b4.py。
"""
from __future__ import annotations

import math

from geo import Part
from ruins_b1 import apply, lantern, rot

G, I, B, A, R = 'graphite', 'ivory', 'brass', 'amber', 'red'
P = 'pipe'
IS = 'ivory_stain'
GL = 'glass'
RELIEF = 0.35


def light_guide(p: Part, x, y, z0, z1, r=0.06):
    """縦の琥珀の導光管（ガラスの芯と真鍮の継ぎ輪・端の金具）。x, y は管の中心（部品の座標）"""
    p.cyl(GL, (x, y, z0 + 0.12), (x, y, z1 - 0.12), r, 10)
    for z in (z0, z1 - 0.12):
        p.cyl(B, (x, y, z), (x, y, z + 0.12), r + 0.035, 10)
    zm = (z0 + z1) / 2
    p.cyl(B, (x, y, zm - 0.05), (x, y, zm + 0.05), r + 0.03, 10)


def b3_post(p: Part, x, depth=0.32, w=0.3, guide=True):
    """壁の両端の柱：黒鉛の芯と白磁の板 2 段、真鍮の金具。guide なら前に縦の導光管"""
    p.box(G, (x - w / 2, -0.2, 0.0), (x + w / 2, 0, 4.0))
    p.cbox(IS, (x, -depth / 2 - 0.02, 0.62), (w + 0.06, depth - 0.02, 1.0), 0.03)
    p.cbox(I, (x, -depth / 2 - 0.02, 3.35), (w + 0.06, depth - 0.02, 1.1), 0.03)
    for z in (0.08, 1.2, 2.75, 3.95):
        p.cbox(B, (x, -depth * 0.5, z), (w + 0.08, depth + 0.0, 0.14), 0.03)
    if guide:
        light_guide(p, x, -0.25, 1.25, 2.75, 0.055)


def wall(name='b3_wall', guide=True):
    p = Part(name, '駆動層の壁 2×0.35×4：白磁の大きな板 2 枚（黒鉛の枠）、両端の柱に縦の琥珀の導光管、足元の黒鉛の台。原点：背面の下の端の中央'
             + ('' if guide else '（導光管なし。真ん中に縦の細い管）'))
    p.box('dark', (-1, -0.05, 0), (1, 0, 4))
    p.box(G, (-1, -0.24, 0), (1, 0, 0.34))
    p.box(B, (-1, -0.255, 0.28), (1, -0.235, 0.31))
    p.box(G, (-1, -0.2, 3.74), (1, 0, 4.0))
    # 白磁の板（下の板は足元が汚れる ivory_stain）と、板の間の黒鉛の目地
    p.cbox(IS, (0, -0.13, 1.1), (1.46, 0.1, 1.5), 0.04, 'y')
    p.cbox(I, (0, -0.13, 2.76), (1.46, 0.1, 1.76), 0.04, 'y')
    p.box(G, (-0.73, -0.16, 1.86), (0.73, -0.1, 1.9))
    if not guide:
        p.cyl(G, (0.0, -0.2, 0.34), (0.0, -0.2, 3.74), 0.05, 8)
        for z in (1.0, 2.6):
            p.cyl(B, (0.0, -0.2, z - 0.05), (0.0, -0.2, z + 0.05), 0.07, 8)
    b3_post(p, -0.85, guide=guide)
    b3_post(p, 0.85, guide=False)
    return p


def corner():
    p = Part('b3_corner', '部屋の内角の柱 0.45×0.45×4（黒鉛の芯、白磁の板、真鍮の金具、角に縦の導光管）。原点：壁 2 面の交わる線の下。yaw 0 で +X・+Z が内側')
    p.box(G, (0, -0.4, 0), (0.4, 0, 4.0))
    for z0, z1, m in ((0.3, 1.3, IS), (2.9, 3.7, I)):
        p.box(m, (0.0, -0.46, z0), (0.3, -0.4, z1))
        p.box(m, (0.4, -0.3, z0), (0.46, 0.0, z1))
    for z in (0.1, 1.4, 2.8, 3.9):
        p.cbox(B, (0.2, -0.2, z), (0.5, 0.5, 0.14), 0.04)
    light_guide(p, 0.38, -0.38, 1.4, 2.8, 0.06)
    return p


def pillar():
    p = Part('b3_pillar', '柱 0.6×0.6×4（黒鉛の芯、白磁の板、四面に縦の琥珀の導光管、真鍮の台と冠）。原点：底の中央')
    p.box(G, (-0.24, -0.24, 0), (0.24, 0.24, 4.0))
    p.cbox(B, (0, 0, 0.12), (0.62, 0.62, 0.24), 0.05)
    p.cbox(B, (0, 0, 3.86), (0.62, 0.62, 0.28), 0.05)
    p.cbox(B, (0, 0, 2.0), (0.56, 0.56, 0.12), 0.04)
    for k in range(4):
        n0 = len(p.pieces)
        p.box(IS, (-0.22, -0.3, 0.3), (0.0, -0.24, 1.9))
        p.box(I, (-0.22, -0.3, 2.1), (0.0, -0.24, 3.7))
        light_guide(p, 0.13, -0.26, 0.3, 3.7, 0.045)
        p.transformed(apply(rot('z', 90 * k)), n0)
    return p


def door():
    p = Part('b3_door', '扉と枠 2×0.35×4（白磁の両開き、真ん中の継ぎ目、両脇に縦の琥珀の導光管、上に赤い非常灯）。原点：背面の下の端の中央')
    p.box(G, (-1, -0.08, 0), (1, 0, 4))
    for sx in (-1, 1):
        p.box(G, (sx * 0.85 - 0.15, -0.2, 0), (sx * 0.85 + 0.15, 0, 4))
        p.cbox(IS, (sx * 0.85, -0.31, 0.5), (0.34, 0.04, 0.8), 0.02, 'y')
        p.cbox(I, (sx * 0.85, -0.31, 3.4), (0.34, 0.04, 0.9), 0.02, 'y')
        light_guide(p, sx * 0.85, -0.25, 0.95, 2.95, 0.055)
        p.cbox(B, (sx * 0.85, -0.17, 0.08), (0.36, 0.34, 0.16), 0.03)
    p.box(G, (-0.7, -0.3, 2.9), (0.7, 0, 4.0))
    p.box(G, (-0.36, -0.315, 3.25), (0.36, -0.29, 3.45))
    p.box(R, (-0.3, -0.33, 3.29), (0.3, -0.31, 3.41))
    for sx in (-1, 1):
        p.box(IS, (min(0, sx * 0.69), -0.17, 0.0), (max(0, sx * 0.69), -0.09, 1.1))
        p.box(I, (min(0, sx * 0.69), -0.17, 1.1), (max(0, sx * 0.69), -0.09, 2.9))
        p.box(G, (sx * 0.09 - 0.02, -0.18, 0.2), (sx * 0.09 + 0.02, -0.165, 2.7))
    p.box('dark', (-0.012, -0.18, 0), (0.012, -0.16, 2.9))
    return p


def beam():
    p = Part('b3_beam', '天井の梁 2×0.5×0.5（黒鉛の枠に白磁の板、下に琥珀の灯 2 つ、両端の真鍮）。原点：上の面の中央')
    p.box(G, (-1, -0.25, -0.5), (1, 0.25, -0.38))
    p.box(G, (-1, -0.25, -0.1), (1, 0.25, 0))
    for sy in (-1, 1):
        p.box(I, (-0.85, sy * 0.24 - 0.02, -0.38), (0.85, sy * 0.24 + 0.02, -0.1))
    p.box(G, (-1, -0.06, -0.38), (1, 0.06, -0.1))
    for sx in (-1, 1):
        p.cbox(B, (sx * 0.92, 0, -0.25), (0.16, 0.56, 0.54), 0.04)
        p.box(A, (sx * 0.45 - 0.12, -0.08, -0.52), (sx * 0.45 + 0.12, 0.08, -0.5))
    return p


def pipe():
    p = Part('b3_pipe', '直線の管 2 m（黒鉛、半径 0.24、両端の厚い真鍮の継ぎ輪と黒鉛の受け、背面へ 0.4 m）。原点：中心線')
    r = 0.24
    p.cyl(P, (-0.86, 0, 0), (0.86, 0, 0), r, 14)
    for xe in (-1.0, 0.82):
        p.cyl(B, (xe, 0, 0), (xe + 0.18, 0, 0), r + 0.07, 14)
        p.cbox(G, (xe + 0.09, 0.12, 0), (0.24, 0.24, r * 2 + 0.2), 0.04)
    for x in (-0.5, 0.5):
        p.box(G, (x - 0.05, 0.15, -0.06), (x + 0.05, 0.4, 0.06))
    return p


def drive():
    p = Part('b3_drive', '床の縁の駆動梁 2×0.4×0.3（黒鉛の梁、真鍮の留め、上に琥珀の小さな灯）。壁ぎわの床に置く（壁の帯の内）。原点：背面（壁）の下の端の中央')
    p.box(G, (-1, -0.34, 0), (1, 0, 0.26))
    p.box(B, (-1, -0.35, 0.2), (1, -0.33, 0.23))
    for x in (-0.6, 0.6):
        p.cbox(B, (x, -0.17, 0.27), (0.2, 0.3, 0.04), 0.01)
        p.box(A, (x - 0.05, -0.355, 0.08), (x + 0.05, -0.34, 0.16))
    for x in (-0.95, 0.95):
        p.box('dark', (x - 0.03, -0.345, 0.02), (x + 0.03, -0.335, 0.24))
    return p


def gear(name='b3_gear', R0=2.0, th=0.35, teeth=20):
    p = Part(name, f'大きな歯車（直径 {2 * R0:.1f} m・厚さ {th} m、黒鉛の輪と歯、真鍮の軸、6 本の腕）。原点：歯車の中心。歯車の面は XZ（前 -Y を向く）。'
             '壁・穴の縁の飾り（当たり判定なし）')
    y0, y1 = -th / 2, th / 2
    # 輪（外の輪と歯）
    ring = [(R0 * 0.86 * math.cos(2 * math.pi * k / 36), 0.0, R0 * 0.86 * math.sin(2 * math.pi * k / 36)) for k in range(37)]
    p.sweep(G, ring, R0 * 0.1, 8)
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        n0 = len(p.pieces)
        p.box(G, (-R0 * 0.07, y0, R0 * 0.88), (R0 * 0.07, y1, R0 * 1.0))
        p.transformed(apply(rot('y', math.degrees(a))), n0)
    for k in range(6):
        a = 2 * math.pi * k / 6
        n0 = len(p.pieces)
        p.box(G, (-0.08, y0 * 0.6, 0.2), (0.08, y1 * 0.6, R0 * 0.8))
        p.transformed(apply(rot('y', math.degrees(a))), n0)
    p.cyl(B, (0, y0 - 0.06, 0), (0, y1 + 0.06, 0), R0 * 0.16, 16)
    p.cyl(G, (0, y0 - 0.12, 0), (0, y0 - 0.04, 0), R0 * 0.07, 12)
    return p


def piston():
    p = Part('b3_piston', '縦のピストン（飾り。黒鉛の筒 0.8 m 角の台から、真鍮の継ぎ輪の太い軸が上へ、上の受け）高さ 6 m。原点：底の中央。当たり判定なし（壁の奥・穴の中に置く）')
    p.cbox(G, (0, 0, 0.6), (1.0, 1.0, 1.2), 0.08)
    p.cbox(I, (0, 0, 1.6), (0.9, 0.9, 0.8), 0.06)
    p.cyl(P, (0, 0, 2.0), (0, 0, 4.6), 0.3, 14)
    for z in (2.0, 3.0, 4.0):
        p.cyl(B, (0, 0, z), (0, 0, z + 0.14), 0.36, 14)
    p.cyl(B, (0, 0, 4.6), (0, 0, 5.2), 0.16, 10)
    p.cbox(G, (0, 0, 5.6), (0.9, 0.9, 0.8), 0.06)
    p.box(GL, (-0.06, -0.46, 0.4), (0.06, -0.45, 1.0))
    return p


def rib(name='b3_rib', h=8.0):
    p = Part(name, f'縦穴・高い壁の縦の梁（黒鉛の芯と白磁の板、真鍮の金具、途中に赤い非常灯）0.6×0.3×{h:g}。原点：背面（壁）の下の端の中央。'
             '壁から 0.3 m（壁の帯の内）')
    p.box(G, (-0.2, -0.24, 0), (0.2, 0, h))
    for z0 in range(0, int(h), 2):
        p.cbox(I if z0 % 4 else IS, (0, -0.27, z0 + 1.0), (0.3, 0.05, 1.6), 0.02, 'y')
        p.cbox(B, (0, -0.15, z0 + 0.1), (0.46, 0.3, 0.12), 0.03)
    p.box(R, (-0.03, -0.305, h * 0.5 - 0.3), (0.03, -0.295, h * 0.5 + 0.3))
    return p


def rail():
    p = Part('b3_rail', '手すり 2×0.3×1.1（黒鉛の柱と台、真鍮の横棒 2 本、柱の上に琥珀の灯）。原点：底の中央')
    p.box(G, (-1, -0.13, 0), (1, 0.13, 0.2))
    for sx in (-1, 1):
        p.cbox(B, (sx * 0.9, 0, 0.5), (0.2, 0.2, 1.0), 0.03)
        lantern(p, (sx * 0.9, 0, 1.2))
    for z in (0.55, 0.9):
        p.cyl(B, (-0.8, 0, z), (0.8, 0, z), 0.03, 8)
    return p


def lift_frame():
    p = Part('b3_lift_frame', '昇降台のガイドの枠（黒鉛の 4 本の柱と上の梁、真鍮の継ぎ輪、柱に赤い非常灯）2.6×2.6×4。足場の外に立つ飾り。原点：底の中央')
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box(G, (sx * 1.3 - 0.12, sy * 1.3 - 0.12, 0), (sx * 1.3 + 0.12, sy * 1.3 + 0.12, 4.0))
            for z in (0.1, 1.9, 3.9):
                p.cbox(B, (sx * 1.3, sy * 1.3, z), (0.32, 0.32, 0.14), 0.03)
    for k in range(4):
        n0 = len(p.pieces)
        p.box(G, (-1.3, -1.36, 3.8), (1.3, -1.24, 4.0))
        p.transformed(apply(rot('z', 90 * k)), n0)
    return p


PARTS = [
    lambda: wall('b3_wall', True), lambda: wall('b3_wall_plain', False), corner, pillar, door, beam, pipe, drive,
    lambda: gear('b3_gear', 2.0, 0.35, 20), lambda: gear('b3_gear_small', 1.0, 0.25, 12), piston,
    lambda: rib('b3_rib', 8.0), rail, lift_frame,
]
