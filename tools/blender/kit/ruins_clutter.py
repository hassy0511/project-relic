"""W2-06b 遺構の散らかりと砂の吹きだまり（origin/art/w2-ruins の ruins_clutter*・spec_ruins_clutter.md）の残り 12 点。
01 sand_wall・02 sand_corner・09 pipe_broken・10 panel_fallen は ruins_common.py（先に作った 4 点）。

作り方は model-from-art の 2.2：spec の寸法表から単純な形で組み、部品ごとに平らな色（geo.PALETTE。spec の hex）。陰は焼かない。
材質はキットの JSON の名前（sand・graphite・brass・dark・ivory・cloth・red と、足した wood・leather・red_off）を通るので、
階層ごとの汚れの層が掛かる（42 の 14.2・14.2.1）。描画は「部品の種類 × 材質の数」なので、部品の材質は 1〜3 個にする。
座標は Blender（x 右、y 奥 = ゲームの -Z、z 上）。正面（部屋の内側・通路の側）は -Y（ゲームの +Z）。原点は各部品の説明。

  sand_door     戸口の砂（最大 2×3×0.3。戸口の敷居の線から室内へ扇に広がる。真ん中の通り道は低く 0.1、両脇の枠に寄って 0.3）。原点：戸口の壁の面・床
  sand_stairs   階段の段の砂（1 段 2×0.6×0.12。蹴上げの足元にたまり、手前で 0）。原点：蹴上げの面の下の端の中央。段ごとに count/step で並べる
  sand_floor    床の薄い砂（直径 2・厚さ 0.06 の不規則な丸。scale で 1〜3 m）。原点：底の中央
  sand_fall     天井からの落砂（床の山 1×1×0.28・細い流れ・天井の割れた板 2×2×0.2 の高さ 8 m）。原点：床の山の底の中央
  sand_stream   落砂の流れと床の山だけ（天井の板なし。天井にもう穴・割れ目がある所。scale の y で天井の高さに）
  cable_floor   床のケーブルの束 4 本（2.6×0.5×0.11、真鍮の留め、端に継ぎ手の箱。前の b1_cables と同じ大きさ・同じ置き場所）。原点：底の中央、X に沿う
  cable_bend    床のケーブルの曲がり（1×1、90 度。X- から入って +Y（ゲームの -Z）へ）。原点：曲がりの角の床
  cable_hang    垂れたケーブル（支持端の間 2 m、垂れ 0.8。両端は壁の留め金）。原点：壁の面・留め金の高さの中央。壁から 0.12〜0.2 m
  cable_hang_cut  片方が切れて垂れたケーブル（破断端は接続しない。垂れ 1.4）。原点は cable_hang と同じ
  rail_bent     曲がった手すり（2×0.4×1。真鍮の管、左の柱は立ち、右は床へ曲がって倒れる）と外れた格子板（床置き 1.6×0.9）。原点：底の中央
  lamp_red      壁の赤い非常灯（0.5×0.32×1：黒鉛の背板、真鍮の上下の笠、赤い灯体 #D4433D の発光）。原点：壁の面・灯の中心
  lamp_red_off  同じ形の消えた灯（灯体は暗い赤、発光なし）
  lamp_red_ceil 天井の赤い非常灯（0.5×0.5×0.5：白磁の天井の板、黒鉛の軸、赤い灯体）。原点：天井の面の中央（下へ下がる）
  steam_vent    壁の蒸気口（真鍮のラッパの口と格子、黒鉛の座、横に赤い弁の輪。壁から 0.34 m まで）。原点：壁の面・口の中心。
                蒸気は B2 の b2_steam を口の前に置く（"rot": [90, yaw, 0] で前へ）
  tarp_crate    布をかけた木箱 1×1×1（赤錆色の布が上と四方に垂れる）。原点：底の中央
  tarp_crate_stack  積み重ね 2×1×2（下に木箱 2、上に 1、布は上の箱と下の箱の肩にかかる）
  salvager_kit  回収屋の道具一式（工具箱 1×0.5×0.5・消えたランタン・ロープの束・背負い枠 1×0.5×1。1.6×0.9 の中）。原点：底の中央
  barricade     砂袋の囲い 2×0.6×1（板の壁と黒鉛の帯、両端に砂袋の山）。原点：底の中央。板は X に沿う、正面は -Y
"""
from __future__ import annotations

import math

import numpy as np

from geo import Part
from ruins_common import _heightfield

G, B, D = 'graphite', 'brass', 'dark'


def rot_z(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return lambda v: v @ R.T


def moved(off):
    o = np.asarray(off, float)
    return lambda v: v + o


# ---------------------------------------------------------------- 砂（03〜06）

def sand_door():
    p = Part('sand_door', '戸口の砂（W2-06b の 03）：戸口の壁の面から室内へ 3 m の扇（幅は敷居で 2 m、奥で 3.4 m）。両脇の枠に寄って高さ 0.3、'
             '真ん中の通り道は 0.1 で踏まれて低い。床から 0.5 cm 浮かせる。原点：戸口の壁の面・床の中央。当たり判定なし（歩いて通る砂）')

    def h(x, y):
        d = -y                                       # 壁の面からの距離（Blender の -Y が部屋の内側）
        if d < 0:
            return 0.0
        hw = 1.0 + 0.24 * d                          # 扇の半幅
        u = abs(x) / hw
        if u >= 1.0:
            return 0.0
        fall = max(0.0, 1 - d / 3.0) ** 1.5
        side = 0.1 + 0.2 * min(1.0, max(0.0, (u - 0.25) / 0.45)) * (1 - max(0.0, (u - 0.7) / 0.3))   # 真ん中は低く、枠の側で高い
        ripple = 0.02 * math.sin(5.0 * d + 1.7 * x) * (1 - d / 3.0)
        edge = 1 - u ** 4
        return (side * fall + ripple * fall) * edge + 0.005
    _heightfield(p, 'sand', 15, 9, -1.75, 1.75, -3.0, 0.0, h)
    return p


def sand_stairs():
    p = Part('sand_stairs', '階段の段の砂（W2-06b の 04、1 段版）：蹴上げの足元にたまった砂（幅 2・奥行き 0.6・高さ 0.12、手前と両端で 0）。'
             '原点：蹴上げの面の下の端の中央（段の踏み面）。手前（-Y）が下の段の側。段ごとに count/step で並べる。当たり判定なし')

    def h(x, y):
        d = -y
        if d < 0:
            return 0.0
        w = 1 - (abs(x) / 1.0) ** 4
        return (0.12 * max(0.0, 1 - d / 0.6) ** 1.3 + 0.012 * math.sin(7 * x)) * max(0.0, w) + 0.004
    _heightfield(p, 'sand', 11, 5, -1.0, 1.0, -0.62, 0.0, h)
    return p


def sand_floor():
    p = Part('sand_floor', '床の薄い砂（W2-06b の 05）：直径 2 m・厚さ 0.06 の不規則な丸、真ん中ほど厚い。scale で直径 1〜3 m。'
             '原点：底の中央。当たり判定なし（床の上の薄い物）')

    def h(x, y):
        r = math.hypot(x, y)
        a = math.atan2(y, x)
        reach = 1.0 * (1 + 0.16 * math.sin(3 * a + 0.5) + 0.08 * math.sin(5 * a + 1.9))
        return 0.06 * max(0.0, 1 - r / reach) ** 1.2 + 0.004 if r < reach else 0.0
    _heightfield(p, 'sand', 11, 11, -1.2, 1.2, -1.2, 1.2, h)
    return p


# 落砂の流れの太さ（下の端・上の端で少し太い。前は 0.045〜0.1 m で、近くから見ると柱に見えた）
STREAM = [(0, 0.07), (0.05, 0.03), (0.95, 0.024), (1, 0.045)]


def _stream_motion(mat, v):
    """落砂の流れの動きの重み（geo.Part.motion）：床の山の上（0.28 m）から上の細い流れだけ 1。キットの "sand" の "flow" が
    そこにだけ下へ流れる模様を描く（床の山と吹きだまりは動かない）"""
    if mat != 'sand':
        return np.zeros(len(v))
    r = np.hypot(v[:, 0], v[:, 1])
    return np.where(r < 0.1, np.clip((v[:, 2] - 0.28) / 0.05, 0.0, 1.0), 0.0)


def sand_stream():
    p = Part('sand_stream', '天井の穴からの落砂（W2-06b の 06 の流れと床の山だけ。天井の板の無い版：天井にもう割れ目・穴がある所）：'
             '床の山（直径 1.2・高さ 0.28）と高さ 8 m までの細い流れ。原点：床の山の底の中央。scale の y で天井の高さに。当たり判定なし')
    p.mound('sand', (0, 0, 0), 0.62, 0.58, 0.28, 12, 4)
    p.lathe('sand', (0, 0, 0.2), (0, 0, 8.0), STREAM, 6)
    p.motion = _stream_motion
    return p


def sand_fall():
    p = Part('sand_fall', '天井からの落砂（W2-06b の 06）：床の山（直径 1.2・高さ 0.28）、天井の割れ目から落ちる細い砂の流れ（太さ 0.05〜0.1）、'
             '高さ 8 m の天井の割れた白磁の板（2×2×0.2、黒鉛の枠、暗い割れ目）。原点：床の山の底の中央。当たり判定なし（低い砂の山）')
    p.mound('sand', (0, 0, 0), 0.62, 0.58, 0.28, 12, 4)
    p.lathe('sand', (0, 0, 0.2), (0, 0, 7.9), STREAM, 6)
    p.motion = _stream_motion
    H = 8.0
    p.box('ivory', (-0.9, -0.9, H - 0.14), (0.9, 0.9, H - 0.02))
    for (x0, y0, x1, y1) in ((-1.0, -1.0, 1.0, -0.88), (-1.0, 0.88, 1.0, 1.0), (-1.0, -0.88, -0.88, 0.88), (0.88, -0.88, 1.0, 0.88)):
        p.box(G, (x0, y0, H - 0.2), (x1, y1, H))
    # 割れ目（白磁の板の下の面から 1.5 cm 下の暗い板。中心から 3 方向へ）
    for a, L in ((0.3, 0.75), (2.4, 0.6), (4.1, 0.7)):
        c, s = math.cos(a), math.sin(a)
        v = np.array([(0.06 * -s, 0.06 * c), (L * c - 0.015 * s, L * s + 0.015 * c), (L * c + 0.015 * s, L * s - 0.015 * c), (0.06 * s, -0.06 * c)])
        p.prism(G, [tuple(q) for q in v], H - 0.16, H - 0.155)
    return p


# ---------------------------------------------------------------- ケーブル（07・08）

def cable_floor():
    p = Part('cable_floor', '床のケーブルの束（W2-06b の 07 の直線）：黒い被覆のケーブル 4 本（太さ 0.035〜0.05）を真鍮の留め 3 つで束ね、'
             '+X の端に黒鉛の継ぎ手の箱（2.6×0.5×0.11。前の b1_cables と同じ大きさ）。原点：底の中央、X に沿う。当たり判定なし（踏んで歩ける薄い物）')
    rs = (0.045, 0.04, 0.036, 0.034)
    ys = (-0.13, -0.04, 0.05, 0.13)
    for k, (r, y0) in enumerate(zip(rs, ys)):
        path = []
        for i in range(7):
            t = i / 6
            x = -1.25 + 2.4 * t
            y = y0 + 0.05 * math.sin(t * math.pi * 1.5 + k) * (1 - abs(2 * t - 1))
            path.append((x, y, r))
        p.sweep(D, path, r, 5)
    for x in (-0.95, 0.0, 0.85):
        p.box(B, (x - 0.05, -0.2, 0.0), (x + 0.05, 0.2, 0.1))
    p.box(G, (1.15, -0.24, 0.0), (1.4, 0.24, 0.09))
    p.box(B, (1.2, -0.18, 0.09), (1.35, 0.18, 0.1))
    return p


def cable_bend():
    p = Part('cable_bend', '床のケーブルの曲がり（W2-06b の 07 の曲がり 1×1）：4 本が 90 度に曲がる（X- から入って +Y へ。ゲームでは -Z へ）、'
             '角に真鍮の留め。原点：曲がりの角の床。当たり判定なし')
    for k, r in enumerate((0.045, 0.04, 0.036, 0.034)):
        p.sweep(D, _arc(k, r), r, 5)
    p.boxc(B, (-0.12, 0.12, 0.055), (0.12, 0.12, 0.11))
    return p


def _arc(k, r):
    """cable_bend の 1 本の道（角の内側の半径を本ごとに 9 cm 大きく）"""
    R = 0.3 + 0.09 * k
    cx, cy = -0.35, 0.35                         # 曲がりの中心
    pts = [(-0.6, cy - R, r)]
    for i in range(7):
        a = math.pi / 2 * i / 6
        pts.append((cx + R * math.sin(a), cy - R * math.cos(a), r))
    pts.append((cx + R, 0.6, r))
    return pts


def _hang(p: Part, sag_m, cut=False):
    """支持端の間 2 m の垂れたケーブル 3 本（壁から 0.12〜0.2 m）と、両端の黒鉛の留め金・真鍮の帯"""
    for x in (-1.0, 1.0):
        p.box(G, (x - 0.09, -0.24, -0.12), (x + 0.09, 0.0, 0.12))
        p.box(B, (x - 0.1, -0.25, -0.03), (x + 0.1, -0.01, 0.03))
    for k, (r, y, extra) in enumerate(((0.045, -0.13, 0.0), (0.035, -0.19, 0.18), (0.03, -0.09, 0.32))):
        sag = sag_m + extra
        n = 12
        pts = []
        for i in range(n + 1):
            t = i / n
            x = -0.92 + 1.84 * t
            z = -sag * 4 * t * (1 - t) - 0.02 * k
            pts.append((x, y, z))
        if cut and k == 0:
            # 切れた 1 本：真ん中より右で切れて、両方の端が下へ垂れる
            left = [q for q in pts if q[0] < 0.25]
            left.append((left[-1][0] + 0.05, y, left[-1][2] - 0.55))
            p.sweep(D, left, r, 5)
            p.cyl(B, (left[-1][0], y, left[-1][2]), (left[-1][0], y, left[-1][2] - 0.07), r * 0.6, 5)       # 切れた芯（銅色は真鍮で）
            right = [(0.92, y, 0.0), (0.7, y, -0.3), (0.62, y, -0.75)]
            p.sweep(D, right, r, 5)
            continue
        p.sweep(D, pts, r, 5)


def _cable_motion(mat, v):
    """垂れたケーブルの揺れの重み（geo.Part.motion）：留め金の高さ（z 0）から下へ、深さ 1.25 m で 1。ケーブル（dark）と
    切れた芯（brass）だけ。キットの "dark"・"brass" の "sway" が、下ほど大きく振り子のように揺らす（留め金は動かない）"""
    if mat not in (D, B):
        return np.zeros(len(v))
    return np.clip((-v[:, 2] - 0.05) / 1.2, 0.0, 1.0)


def cable_hang():
    p = Part('cable_hang', '垂れたケーブル（W2-06b の 08）：支持端の間 2 m、垂れ 0.8〜1.1 m の 3 本、両端の黒鉛の留め金（壁から 0.24 m）。'
             '原点：壁の面・留め金の高さの中央。正面（-Y）が部屋の内側。当たり判定なし（頭の上の高い所に付ける）')
    _hang(p, 0.8)
    p.motion = _cable_motion
    return p


def cable_hang_cut():
    p = Part('cable_hang_cut', '片方が切れた垂れたケーブル（W2-06b の 08 の破断。切れた端は接続しない）。原点は cable_hang と同じ。当たり判定なし')
    _hang(p, 1.1, cut=True)
    p.motion = _cable_motion
    return p


# ---------------------------------------------------------------- 11 曲がった手すりと外れた格子

def rail_bent():
    p = Part('rail_bent', '曲がった手すり（W2-06b の 11）：真鍮の管の手すり 2 m（左の柱は立ち、右の柱は根元から床へ曲がって倒れる）と、'
             '外れて床に置かれた格子板（1.6×0.9、厚さ 4 cm）。原点：底の中央。手すりは X に沿う（壁ぎわに置く：-Y が部屋の内側）')
    r = 0.035
    # 左の柱と台
    p.box(G, (-1.08, -0.08, 0.0), (-0.92, 0.08, 0.04))
    p.cyl(B, (-1.0, 0.0, 0.04), (-1.0, 0.0, 1.0), r, 8)
    p.cyl(B, (-0.45, 0.0, 0.04), (-0.45, 0.0, 0.95), r, 8)
    p.box(G, (-0.53, -0.08, 0.0), (-0.37, 0.08, 0.04))
    # 上の手すり：左の柱の上から右へ、右の 3 分の 1 で下へ曲がって床へ
    top = [(-1.0, 0.0, 1.0), (-0.45, 0.0, 0.98), (0.1, 0.0, 0.9), (0.45, -0.05, 0.62), (0.7, -0.12, 0.25), (0.95, -0.18, 0.05)]
    p.sweep(B, top, r, 6)
    mid = [(-1.0, 0.0, 0.55), (-0.45, 0.0, 0.54), (0.05, -0.02, 0.48), (0.35, -0.08, 0.28), (0.55, -0.15, 0.06)]
    p.sweep(B, mid, r * 0.8, 6)
    p.box(G, (0.88, -0.28, 0.0), (1.04, -0.12, 0.04))
    # 外れた格子板（床の上 1 cm。黒鉛の枠と暗い格子）
    gx, gy = 0.0, -0.75
    p.box(G, (gx - 0.8, gy - 0.45, 0.01), (gx + 0.8, gy - 0.37, 0.05))
    p.box(G, (gx - 0.8, gy + 0.37, 0.01), (gx + 0.8, gy + 0.45, 0.05))
    p.box(G, (gx - 0.8, gy - 0.37, 0.01), (gx - 0.72, gy + 0.37, 0.05))
    p.box(G, (gx + 0.72, gy - 0.37, 0.01), (gx + 0.8, gy + 0.37, 0.05))
    for k in range(1, 6):
        x = gx - 0.72 + 1.44 * k / 6
        p.box(G, (x - 0.018, gy - 0.37, 0.015), (x + 0.018, gy + 0.37, 0.042))
    for k in (-1, 0, 1):
        y = gy + 0.12 * k * 2
        p.box(G, (gx - 0.72, y - 0.018, 0.02), (gx + 0.72, y + 0.018, 0.045))
    return p


# ---------------------------------------------------------------- 12 赤い非常灯

def _lamp_wall(p: Part, lens):
    """壁の非常灯（原点：壁の面・灯の中心。-Y が前）"""
    p.cbox(G, (0, -0.04, 0), (0.34, 0.08, 0.9), 0.04, 'y')                # 背板
    p.box(G, (-0.1, -0.16, -0.36), (0.1, -0.06, 0.36))                     # 背板から灯への腕
    for z0, z1 in ((0.26, 0.4), (-0.4, -0.26)):
        p.lathe(B, (0, -0.2, z0), (0, -0.2, z1), [(0, 0.12), (1, 0.12)] if z0 > 0 else [(0, 0.12), (1, 0.12)], 10)
    p.cyl(lens, (0, -0.2, -0.27), (0, -0.2, 0.27), 0.095, 10)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        p.box(G, (0.105 * math.cos(a) - 0.012, -0.2 + 0.105 * math.sin(a) - 0.012, -0.27),
              (0.105 * math.cos(a) + 0.012, -0.2 + 0.105 * math.sin(a) + 0.012, 0.27))


def lamp_red():
    p = Part('lamp_red', '壁の赤い非常灯（W2-06b の 12 の壁用、点灯）：黒鉛の背板 0.34×0.9、真鍮の上下の笠、赤い灯体（#D4433D の発光）と 4 本の格子。'
             '壁から 0.32 m まで（壁の帯の内）。原点：壁の面・灯の中心')
    _lamp_wall(p, 'red')
    return p


def lamp_red_off():
    p = Part('lamp_red_off', '壁の赤い非常灯（消灯）：lamp_red と同じ形、灯体は暗い赤（発光なし）。原点は lamp_red と同じ')
    _lamp_wall(p, 'red_off')
    return p


def lamp_red_ceil():
    p = Part('lamp_red_ceil', '天井の赤い非常灯（W2-06b の 12 の天井用、点灯）：白磁の天井の板 0.5 角、黒鉛の軸、真鍮の笠、赤い灯体。'
             '原点：天井の面の中央（下へ 0.5 m 下がる）')
    p.cbox('ivory', (0, 0, -0.04), (0.5, 0.5, 0.08), 0.03)
    p.cyl(G, (0, 0, -0.08), (0, 0, -0.16), 0.06, 8)
    p.lathe(G, (0, 0, -0.16), (0, 0, -0.22), [(0, 0.08), (1, 0.12)], 10)
    p.cyl('red', (0, 0, -0.22), (0, 0, -0.44), 0.085, 10)
    p.lathe(G, (0, 0, -0.44), (0, 0, -0.5), [(0, 0.1), (1, 0.05)], 10)
    return p


# ---------------------------------------------------------------- 13 蒸気口

def steam_vent():
    p = Part('steam_vent', '壁の蒸気口（W2-06b の 13）：黒鉛の座（0.5 角）、真鍮のラッパの口（壁から 0.34 m、直径 0.4）と暗い格子、'
             '座の横に赤い弁の輪（直径 0.36）。原点：壁の面・口の中心。蒸気は b2_steam を口の前に（"rot": [90, yaw, 0]）')
    p.cbox(G, (0, -0.04, 0), (0.5, 0.08, 0.5), 0.04, 'y')
    p.cyl(G, (0, -0.08, 0), (0, -0.16, 0), 0.12, 10)
    p.lathe(B, (0, -0.16, 0), (0, -0.34, 0), [(0, 0.12), (0.5, 0.14), (1, 0.2)], 12)
    p.cyl(G, (0, -0.335, 0), (0, -0.34, 0), 0.18, 12)
    for k in (-1, 0, 1):
        p.box(G, (k * 0.08 - 0.012, -0.345, -0.17), (k * 0.08 + 0.012, -0.335, 0.17))
    # 弁の輪（座の右下。赤い塗りの鉄＝ cloth の赤、発光しない）
    cx, cz = 0.42, -0.12
    p.box(G, (cx - 0.06, -0.08, cz - 0.06), (cx + 0.06, 0.0, cz + 0.06))
    p.cyl(B, (cx, -0.08, cz), (cx, -0.2, cz), 0.03, 6)
    ring = [(cx + 0.18 * math.cos(2 * math.pi * k / 16), -0.2, cz + 0.18 * math.sin(2 * math.pi * k / 16)) for k in range(17)]
    p.sweep('cloth', ring, 0.022, 6)
    for k in range(3):
        a = math.pi / 2 + k * 2 * math.pi / 3
        p.cyl('cloth', (cx, -0.2, cz), (cx + 0.17 * math.cos(a), -0.2, cz + 0.17 * math.sin(a)), 0.014, 5)
    return p


# ---------------------------------------------------------------- 14 布をかけた木箱

def _crate(p: Part, c, s=1.0):
    """乾いた木の箱（板の面 wood、黒鉛の帯と角）。c は底の中心"""
    x, y, z = c
    h = s / 2
    p.box('wood', (x - h + 0.04, y - h + 0.04, z), (x + h - 0.04, y + h - 0.04, z + s - 0.02))
    for zz in (z + 0.1 * s, z + s * 0.62):
        p.box(G, (x - h, y - h, zz), (x + h, y + h, zz + 0.08 * s))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box(G, (x + sx * h - (0.07 if sx > 0 else 0), y + sy * h - (0.07 if sy > 0 else 0), z),
                  (x + sx * h + (0 if sx > 0 else 0.07), y + sy * h + (0 if sy > 0 else 0.07), z + s))


def _tarp(p: Part, c, w, d, top, drop, seed=0.0):
    """箱にかけた布：上の面（少したるむ）と四方の垂れ（裾は波打つ）。c は箱の上の面の中心"""
    x, y = c[0], c[1]
    hw, hd = w / 2 + 0.04, d / 2 + 0.04
    nx, ny = 6, 6
    # 上の面（厚さ 3 cm の板を格子に。真ん中が 2 cm 下がる）
    pts = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            pts.append((x - hw + 2 * hw * u, y - hd + 2 * hd * v, top + 0.02 - 0.02 * math.sin(math.pi * u) * math.sin(math.pi * v)))
    top_v = np.array(pts)
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append([a, a + 1, a + nx + 2, a + nx + 1])
    bot_v = top_v.copy()
    bot_v[:, 2] -= 0.03
    n = len(top_v)
    allv = np.concatenate([top_v, bot_v])
    f = faces + [[q + n for q in fc[::-1]] for fc in faces]
    # 縁の帯（上と下をつなぐ）
    ring = [(0, i) for i in range(nx)] + [(j, nx) for j in range(ny)] + [(ny, nx - i) for i in range(nx)] + [(ny - j, 0) for j in range(ny)]
    idx = [j * (nx + 1) + i for j, i in ring]
    for k in range(len(idx)):
        a, b = idx[k], idx[(k + 1) % len(idx)]
        f.append([b, a, a + n, b + n])
    # 面の向きは書いたとおり（外向き）。geo.Part.add の向きそろえ（体積の符号）は、薄く広い板では縁の帯に引っぱられて全部を裏返した
    # （上の面が消え、真ん中に下の木箱の上の面が丸く透けた）
    p.pieces.append(('cloth', allv, f, False))
    # 四方の垂れ：面ごとに縦の布（厚さ 2 cm、裾は波打つ長さ）
    for side in range(4):
        L = 2 * (hw if side % 2 == 0 else hd)
        m = 5
        vv = []
        for i in range(m + 1):
            t = i / m
            dl = drop * (0.75 + 0.25 * math.sin(t * 7 + side * 1.3 + seed))
            if side == 0:
                px, py = x - hw + L * t, y - hd
            elif side == 1:
                px, py = x + hw, y - hd + L * t
            elif side == 2:
                px, py = x + hw - L * t, y + hd
            else:
                px, py = x - hw, y + hd - L * t
            vv.append((px, py, top + 0.0))
            vv.append((px, py, top - dl))
        V = np.array(vv)
        nrm = {0: (0, -1, 0), 1: (1, 0, 0), 2: (0, 1, 0), 3: (-1, 0, 0)}[side]
        outer = V + np.array(nrm) * 0.012
        inner = V - np.array(nrm) * 0.008
        k2 = len(V)
        allv2 = np.concatenate([outer, inner])
        f2 = []
        for i in range(m):
            a = 2 * i
            f2.append([a, a + 1, a + 3, a + 2])                       # 外の面（外向き）
            f2.append([k2 + a, k2 + a + 2, k2 + a + 3, k2 + a + 1])   # 内の面
            f2.append([a + 1, k2 + a + 1, k2 + a + 3, a + 3])         # 裾（下向き）
            f2.append([a, a + 2, k2 + a + 2, k2 + a])                 # 上の縁（上向き）
        f2.append([0, k2 + 0, k2 + 1, 1])
        f2.append([2 * m, 2 * m + 1, k2 + 2 * m + 1, k2 + 2 * m])
        p.pieces.append(('cloth', allv2, f2, False))


def tarp_crate():
    p = Part('tarp_crate', '布をかけた木箱（W2-06b の 14 の単体 1×1×1）：乾いた木の箱、黒鉛の帯と角、赤錆色の布が上と四方に垂れる（裾は 0.35〜0.55 m）。'
             '原点：底の中央。当たり判定 1.1×1.1×1.05')
    _crate(p, (0, 0, 0), 0.98)
    _tarp(p, (0, 0), 0.98, 0.98, 0.98, 0.5, 0.3)
    return p


def tarp_crate_stack():
    p = Part('tarp_crate_stack', '布をかけた木箱の積み重ね（W2-06b の 14 の 2×1×2）：下に木箱 2、上に 1（左寄り）、布は上の箱にかかって下の箱の肩まで。'
             '原点：底の中央。当たり判定は下の段 2.1×1.1×1.0 と上の段 1.1×1.1×2.05')
    _crate(p, (-0.5, 0, 0), 0.98)
    _crate(p, (0.5, 0, 0), 0.98)
    _crate(p, (-0.48, 0.0, 0.98), 0.96)
    _tarp(p, (-0.48, 0.0), 0.96, 0.96, 1.94, 0.8, 1.1)
    return p


# ---------------------------------------------------------------- 15 回収屋の道具一式

def salvager_kit():
    p = Part('salvager_kit', '回収屋の道具一式（W2-06b の 15）：黒鉛の工具箱 0.9×0.45×0.45（真鍮の留め金と取っ手）、消えたランタン（真鍮の枠、暗いガラス）、'
             'ロープの束（古革色、工具箱のふたの上）、背負い枠 0.8×0.45×1（黒鉛の枠と古革の袋・肩ひも。工具箱の後ろに立てる）。0.95×0.76 の中。原点：底の中央')
    # 工具箱（左手前）
    tx, ty = -0.35, -0.12
    p.cbox(G, (tx, ty, 0.2), (0.9, 0.45, 0.4), 0.03)
    p.box(G, (tx - 0.46, ty - 0.235, 0.36), (tx + 0.46, ty + 0.235, 0.4))
    for x in (tx - 0.25, tx + 0.25):
        p.box(B, (x - 0.05, ty - 0.24, 0.28), (x + 0.05, ty - 0.22, 0.36))
    p.sweep(B, [(tx - 0.15, ty, 0.4), (tx - 0.12, ty, 0.47), (tx + 0.12, ty, 0.47), (tx + 0.15, ty, 0.4)], 0.015, 5)
    # ランタン（工具箱の上）
    lx, ly = tx + 0.25, ty + 0.02
    p.lathe(B, (lx, ly, 0.4), (lx, ly, 0.44), [(0, 0.08), (1, 0.08)], 8)
    p.cyl(G, (lx, ly, 0.44), (lx, ly, 0.6), 0.055, 8)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        p.box(B, (lx + 0.065 * math.cos(a) - 0.01, ly + 0.065 * math.sin(a) - 0.01, 0.44),
              (lx + 0.065 * math.cos(a) + 0.01, ly + 0.065 * math.sin(a) + 0.01, 0.6))
    p.lathe(B, (lx, ly, 0.6), (lx, ly, 0.67), [(0, 0.08), (1, 0.02)], 8)
    # ロープの束（工具箱のふたの左に載せる、平たい輪 3 つ。床に置くと箱の無い低い所ができて、まわりにすき間ができた）
    rx, ry = tx - 0.24, ty + 0.0
    for k in range(3):
        ring = [(rx + (0.17 - 0.025 * k) * math.cos(2 * math.pi * i / 12), ry + (0.17 - 0.025 * k) * math.sin(2 * math.pi * i / 12) * 0.85,
                 0.42 + 0.03 * k) for i in range(13)]
        p.sweep('leather', ring, 0.022, 5)
    # 背負い枠（奥、立てて置く）
    bx, by = -0.38, 0.22
    for x in (bx - 0.36, bx + 0.36):
        p.box(G, (x - 0.025, by - 0.02, 0.0), (x + 0.025, by + 0.03, 1.0))
    for z in (0.12, 0.62, 0.96):
        p.box(G, (bx - 0.36, by - 0.02, z - 0.02), (bx + 0.36, by + 0.03, z + 0.02))
    p.cbox('leather', (bx, by - 0.12, 0.42), (0.58, 0.22, 0.5), 0.05)
    p.cbox('leather', (bx, by - 0.16, 0.22), (0.4, 0.16, 0.2), 0.04)
    for x in (bx - 0.2, bx + 0.2):
        p.sweep('leather', [(x, by + 0.04, 0.95), (x, by + 0.16, 0.8), (x, by + 0.14, 0.45), (x, by + 0.04, 0.3)], 0.022, 4)
    return p


# ---------------------------------------------------------------- 16 砂袋の囲い

def barricade():
    p = Part('barricade', '砂袋の囲い（W2-06b の 16）2×0.6×1：乾いた木の板の壁（横板 4 枚）と黒鉛の縦の帯 2 本、両端と後ろに砂袋の山（3 段）。'
             '原点：底の中央。板は X に沿い、正面（-Y）が部屋の内側。当たり判定 2.05×0.65×1.0')
    # 板の壁
    for k in range(4):
        z0 = 0.06 + k * 0.23
        p.box('wood', (-0.62, -0.06, z0), (0.62, 0.04, z0 + 0.21))
    for x in (-0.45, 0.45):
        p.box(G, (x - 0.06, -0.09, 0.0), (x + 0.06, 0.07, 0.98))
    p.box(G, (-0.64, -0.08, 0.0), (0.64, 0.06, 0.06))
    # 両端の砂袋（3 段、少し互い違い）。袋は角を落とした低い箱（面は sand）
    for sx in (-1, 1):
        for k in range(3):
            z = k * 0.3
            for j in range(2 - (k == 2)):
                yy = -0.13 + 0.27 * j + (0.06 if k % 2 else 0.0)
                p.cbox('sand', (sx * 0.82, yy, z + 0.15), (0.36, 0.26, 0.28), 0.07)
    # 後ろの低い袋の列（板の裏）
    for x in (-0.3, 0.3):
        p.cbox('sand', (x, 0.2, 0.14), (0.55, 0.28, 0.26), 0.07)
    return p


PARTS = [sand_door, sand_stairs, sand_floor, sand_fall, sand_stream, cable_floor, cable_bend, cable_hang, cable_hang_cut, rail_bent,
         lamp_red, lamp_red_off, lamp_red_ceil, steam_vent, tarp_crate, tarp_crate_stack, salvager_kit, barricade]
