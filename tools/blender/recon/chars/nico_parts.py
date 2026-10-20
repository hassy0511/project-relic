"""ニコ（nico）の服の部品と塗りの決まり（costume.py が読み込む。書式は chars/burton_parts.py・yana_parts.py と同じ）。

部品の表：docs/art_orders/W2_ニコ3D化の結果.md の 1 章。寸法は calib.json のカメラで絵（W2-01 の r2、nico_*_r2.png）に
1cm の格子を重ねて読んだ（再構築の座標：身長 1.55m。本来の 1.20m へは骨付けの段で 0.774 倍）。本人の左 = +X、正面 = −Y。
  シャツのえり（砂色、前は V に開く）・半袖の折り返し ×2（砂色）・つなぎの胸当て・背当て・肩ひも ×2・胴の帯（青緑）・
  胸ポケット（青緑）・肩ひものボタン ×2・腰のボタン ×2（木）・裾の折り返し ×2（青緑）・布靴 ×2（底・胴）・
  木の玩具ゴーグル（縁 ×2・レンズ ×2・橋・首の後ろを回る帯）・後ろの結び髪と結び帯・髪の房と前髪（hair.lock_parts）。
  手は hand.py の開いた手（素手、肌）。
塗りの決まり（body_rules）：胴の上はシャツの砂色（胸当て・背当て・肩ひもの下はつなぎの色）、腰の帯（z 0.84）より下は
つなぎの青緑、半袖の折り返しより先の腕は肌、裾の折り返しより下の脚（くるぶし）は肌、首は肌、頭は形の場。
"""
from __future__ import annotations

import math
import os

import numpy as np

# 色は spec_nico_r2.md の色見本（主要 6 色）を基に、確認ページ・ゲームで違って見えた所は絵の平らに照らされた所の中央値へ寄せた
# （build/nico/tools/colors.py・colors2.py。つなぎは絵も #54777B）：
#   髪：spec #E8C58D は肌 #E7B58D と見分けにくく、1 周目に #E0B475 へ寄せたら黄色すぎた（統括の確認）。絵の髪の中央値 #EBC696〜#EFCA9B
#       （明るい砂色の金髪）を、描画で明るく見える分だけ下げた #E1BE8E。肌との見分けは房の面の陰で出す
#   シャツ：spec #DCC7A7 は描画で生成りの白に見えた（統括の確認）。絵の首・袖の中央値 #E8C498（明るい黄土）から、肌と見分けられる
#       よう彩度を下げたカーキ #D4BE98
#   靴底：spec はシャツと同じ #DCC7A7。絵の靴底 #E4C69C に近い淡い色のまま（シャツの色とは別の 'sole'）
#   布靴：#A98749 は黄色に見えた（絵 #B48B5D）→ #A88559。ゴーグルの木の縁・ボタン：絵は橙の木（#DB8727・#AF6C1A）→ #C47F2C
PALETTE = {
    'teal': '#54777B',       # つなぎ（くすんだ青緑の帆布）
    'sand': '#D4BE98',       # シャツ（明るい黄土・カーキ。#D9B487 は確認ページで肌と同じ桃色に見えた）
    'canvas': '#A88559',     # 布靴
    'wood': '#C47F2C',       # ゴーグルの木の縁・ボタン
    'dark': '#594333',       # ゴーグルの内側（レンズ）・橋・結び帯・ゴーグルの帯（発光しない）
    'skin': '#E7B58D',
    'hair': '#E1BE8E',       # 麦わら色（明るい砂色）の髪
    'teal_dark': '#466569',  # 裾の折り返しの下（脚の筒の内側）
    'sole': '#E0CAA4',       # 靴底
    'tie': '#C26A2E',        # 結び帯（絵は橙の布。spec の #594333 より絵に合わせる）
    'hair_dark': '#BF9A6A',  # 帽子（髪の土台）の下の縁：房の先のすき間に見える内側の髪（絵の髪の暗い面）
}
NAMES = list(PALETTE)
CELLS = 16

X0 = -0.008     # 顔・首の左右の中心

# A ポーズの関節（chars/nico.json の joints.ART_XZ と同じ x・z。y は真横の絵）
J = {
    'upper_arm': (0.13, 0.0, 1.02), 'forearm': (0.258, 0.01, 0.86), 'hand': (0.355, 0.0, 0.738),
    'hand_end': (0.41, -0.01, 0.648), 'thigh': (0.085, 0.0, 0.64), 'shin': (0.13, 0.01, 0.38),
    'foot': (0.165, 0.0, 0.085),
}
# 胸当て・背当て・肩ひも・えりは近くの体の重みを写す（胸から腰へ曲がる・首と胸の骨で曲がる所）
FOLLOW_BODY = ('collar', 'bib', 'bib_back', 'strap.L', 'strap.R', 'waistband')
FOLLOW_TORSO_ONLY = ('collar', 'bib', 'bib_back', 'strap.L', 'strap.R', 'waistband')
BOX_RULES: list = []

WAIST_Z = (0.783, 0.801)        # 胴の帯（つなぎの腰の縫い目）の下・上
SIDE_TOP = 0.838                # つなぎの横の上の縁（これより下はぐるりと青緑。上は胸当て・背当ての部品）
BIB = dict(top=0.968, x_top=(-0.112, 0.114), x_mid=(-0.165, 0.165))
BACK = dict(top=0.988, x_top=(-0.088, 0.088), x_mid=(-0.165, 0.165))
SLEEVE_T = (0.122, 0.168)       # 半袖の折り返し：上腕の軸に沿った肩からの長さ
CUFF_Z = (0.203, 0.268)         # 裾の折り返しの下・上
LEG_C = (0.165, 0.035)          # 裾の折り返しの軸（|x|, y）
NECK_TOP = 1.155                # 首の上（あごの下）
COLLAR_Z = (1.064, 1.136)       # えりの前の下・後ろの上
# 顔のまわりの髪の塗りの下の線（|x − X0| → z）。正面の絵の生え際・ほおの横の髪の縁
# 3 周目：額の上の帽子の縁（前髪の房の先より下）が髪の色の帯に見えた → 線を 1〜1.5cm 上げ、生え際は房の先が作る
HAIRLINE_PAINT = ([0.0, 0.05, 0.08, 0.10, 0.12, 0.135, 0.15], [1.398, 1.394, 1.378, 1.358, 1.326, 1.28, 1.22])
BOOT_CUT = 0.122        # この高さより下の脚の体は消して、靴の部品に置き換える（0.088・0.100 では靴の口の外・甲の上に体の足の肌が出た）
BOOT_RAMP = (0.05, 0.13)
BOOT_CUT_X = (0.03, 0.34)
RIGHT_HAND_PART = True


# ---------------------------------------------------------------- 形の段のメッシュの測り

_MESH = None


def _mesh() -> np.ndarray:
    global _MESH
    if _MESH is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'build', 'nico',
                         'nico_mesh.npz')
        _MESH = np.load(p)['verts']
    return _MESH


def _band(z, dz=0.007):
    v = _mesh()
    return v[np.abs(v[:, 2] - z) < dz]


def body_front_y(z: float, x0: float, x1: float) -> float:
    p = _band(z)
    p = p[(p[:, 0] > x0) & (p[:, 0] < x1)]
    return float(p[:, 1].min())


def body_back_y(z: float, x0: float, x1: float) -> float:
    p = _band(z)
    p = p[(p[:, 0] > x0) & (p[:, 0] < x1)]
    return float(p[:, 1].max())


# ---------------------------------------------------------------- 小さな形（面をそのまま渡す部品）

def _orient(V, F):
    F = np.asarray(F, np.int64)
    vol = np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum()
    return V, (F[:, ::-1] if vol < 0 else F)


def ring_mesh(c, axis, up, r_out, r_in, depth, n=20, bevel=0.0):
    """軸 axis（前向き）のまわりの太い輪（ゴーグルの縁）：外の半径 r_out・内の半径 r_in・奥行き depth（前の面は面取り）"""
    c, axis, up = (np.asarray(v, float) for v in (c, axis, up))
    axis = axis / np.linalg.norm(axis)
    e0 = up - axis * np.dot(up, axis)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(axis, e0)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(a)[:, None] * e0 + np.sin(a)[:, None] * e1
    # 輪の断面（前 → 後ろ）：(半径, 前からの距離)
    prof = [(r_out - bevel, 0.0), (r_out, bevel), (r_out, depth), (r_in, depth), (r_in, bevel), (r_in + bevel, 0.0)]
    V = np.concatenate([c - axis * d + circ * r for r, d in prof])
    k = len(prof)
    F = []
    for j in range(k):
        j2 = (j + 1) % k
        for i in range(n):
            i2 = (i + 1) % n
            a0, a1, b0, b1 = j * n + i, j * n + i2, j2 * n + i, j2 * n + i2
            F += [(a0, b0, b1), (a0, b1, a1)]
    return _orient(V, F)


def disc_mesh(c, axis, up, r, depth, n=20):
    c, axis, up = (np.asarray(v, float) for v in (c, axis, up))
    axis = axis / np.linalg.norm(axis)
    e0 = up - axis * np.dot(up, axis)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(axis, e0)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(a)[:, None] * e0 + np.sin(a)[:, None] * e1
    V = np.concatenate([c + circ * r, c + axis * depth + circ * r, [c, c + axis * depth]])
    F = []
    for i in range(n):
        i2 = (i + 1) % n
        F += [(i, n + i, n + i2), (i, n + i2, i2), (2 * n, i2, i), (2 * n + 1, n + i, n + i2)]
    return _orient(V, F)


def box_mesh(c, half, up=(0.0, 0.0, 1.0)):
    c = np.asarray(c, float)
    hx, hy, hz = half
    V = np.array([(sx * hx, sy * hy, sz * hz) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], float) + c
    F = [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4), (2, 6, 7), (2, 7, 3), (0, 4, 6), (0, 6, 2),
         (1, 3, 7), (1, 7, 5)]
    return _orient(V, F)


def ell(cx, cy, rx, ry, n=10, rot=0.0):
    return [(cx + rx * math.cos(rot + 2 * math.pi * k / n), cy + ry * math.sin(rot + 2 * math.pi * k / n))
            for k in range(n)]


# ---------------------------------------------------------------- 部品

def overalls() -> list[dict]:
    """つなぎ：胸当て（前）・背当て（後ろ）・肩ひも ×2・胴の帯・胸ポケット・ボタン。絵 nico_3d_front/back/side_right_noarms"""
    P = []
    front = np.array([0.0, -1.0, 0.0])
    back = np.array([0.0, 1.0, 0.0])
    fw = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), front)
    fw['RN'] = 0.135
    fb = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), back)
    fb['RN'] = 0.135
    b = BIB
    P.append(dict(name='bib', bone='chest', color='teal', frame=fw,
                  outline=[(b['x_mid'][0], WAIST_Z[0] + 0.004), (b['x_mid'][1], WAIST_Z[0] + 0.004),
                           (b['x_mid'][1], SIDE_TOP), (b['x_top'][1], b['top']), (b['x_top'][0], b['top']),
                           (b['x_mid'][0], SIDE_TOP)],
                  off=0.003, thick=0.006, bevel=0.002, under='teal', rmax=0.25, h=0.007, env_rings=2,
                  smooth_iters=6))
    k = BACK
    P.append(dict(name='bib_back', bone='chest', color='teal', frame=fb,
                  outline=[(-k['x_mid'][1], WAIST_Z[0] + 0.004), (-k['x_mid'][0], WAIST_Z[0] + 0.004),
                           (-k['x_mid'][0], SIDE_TOP), (-k['x_top'][0], k['top']), (-k['x_top'][1], k['top']),
                           (-k['x_mid'][1], SIDE_TOP)],
                  off=0.003, thick=0.006, bevel=0.002, under='teal', rmax=0.25, h=0.007, env_rings=2,
                  smooth_iters=6))
    # 胴の帯（腰の縫い目、ぐるり）：胸当て・背当ての下の縁を覆う
    P.append(dict(name='waistband', bone='hips', color='teal', frame=fw, ring=True,
                  t0=WAIST_Z[0], t1=WAIST_Z[1], off=0.009, thick=0.005, bevel=0.002, under='teal',
                  rmax=0.3, n_ring=96, sink=0.012))
    # 胸ポケット（胸当ての上、14cm 幅。下の角は丸い）
    P.append(dict(name='pocket', bone='chest', color='teal', frame=fw,
                  outline=[(-0.090, 0.825), (-0.078, 0.812), (0.074, 0.812), (0.086, 0.825), (0.086, 0.925),
                           (-0.090, 0.925)],
                  off=0.010, thick=0.004, bevel=0.0015, rmax=0.25, h=0.006))
    # 肩ひも ×2（左右の軸のまわり：胸当ての上の角 → 肩の上 → 背当ての上の角）。t = |x|
    up = np.array([0.0, 0.0, 1.0])
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        ax_y, ax_z = 0.0, 0.965
        fst = frame((0.0, ax_y, ax_z), (side, ax_y, ax_z), up)
        fst['RN'] = 0.1
        (tf0, tf1), (tb0, tb1) = (0.074, 0.116), (0.058, 0.094)
        xs = sorted((side * tf0, side * tf1))
        xb = sorted((side * tb0, side * tb1))
        zf, zb = BIB['top'] - 0.012, BACK['top'] - 0.012
        af = math.atan2(ax_y - body_front_y(zf, *xs), zf - ax_z)
        ab = math.atan2(body_back_y(zb, *xb) - ax_y, zb - ax_z)
        sf, sb = af * 0.1, -ab * 0.1
        if side < 0:
            sf, sb = -sf, -sb
        out = [(sb, tb0), (sf, tf0), (sf, tf1), (sb, tb1)]
        if side < 0:
            out = out[::-1]
        P.append(dict(name='strap' + sx, bone='chest', color='teal', frame=fst, outline=out, off=0.008,
                      thick=0.005, bevel=0.0015, under='teal', rmax=0.25, env_rings=1, h=0.0045, smooth_iters=40,
                      raw_tol=0.0))
        # 肩ひものボタン（胸当ての上の角）・腰のボタン（横、正面から 79 度）
        xc = side * 0.095
        P.append(dict(name='strap_button' + sx, bone='chest', color='wood', frame=fw,
                      outline=octagon(xc - 0.015, xc + 0.015, 0.937, 0.966, 0.006), off=0.014, thick=0.007,
                      bevel=0.003, rmax=0.25, h=0.004))
        sc = side * math.radians(79.0) * fw['RN']
        P.append(dict(name='side_button' + sx, bone='hips', color='wood', frame=fw,
                      outline=octagon(sc - 0.014, sc + 0.014, 0.792, 0.820, 0.006), off=0.010, thick=0.007,
                      bevel=0.003, rmax=0.3, h=0.004))
    return P


def collar_sleeves() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    back = np.array([0.0, 1.0, 0.0])
    # シャツのえり：首の縦の軸のまわり、後ろが s = 0。前は V に開く（下 |x| 0.022、上 |x| 0.06）
    fc = frame((X0, 0.0, 0.0), (X0, 0.0, 1.0), back)
    fc['RN'] = 0.07
    sb, st_ = 0.07 * (math.pi - math.asin(0.022 / 0.065)), 0.07 * (math.pi - math.asin(0.060 / 0.07))
    P.append(dict(name='collar', bone='neck', color='sand', frame=fc,
                  outline=[(-sb, COLLAR_Z[0]), (sb, COLLAR_Z[0]), (st_, 1.103), (0.12, 1.128), (0.0, COLLAR_Z[1]),
                           (-0.12, 1.128), (-st_, 1.103)],
                  off=0.003, thick=0.007, bevel=0.0025, under='sand', rmax=0.082, rmin=0.052, h=0.005,
                  env_rings=3, smooth_iters=30, raw_tol=0.004))
    # 2 周目：えりの縁が首の面の凸凹で波打った → 近所の最大 3 輪・よくならし、面より 4mm 内まで許す
    # 1 周目は rmax 0.2 で、首の根元の肩の面まで光線が届き、えりが肩の上の平たい翼（セーラーの襟）になった → 首から 8.2cm まで
    # 半袖の折り返し（砂色）：上腕の軸（肩 → 肘）
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        s, e = jp('upper_arm', side), jp('forearm', side)
        fs = frame(s, e, front)
        fs['RN'] = 0.06
        P.append(dict(name='sleeve_cuff' + sx, bone='upper_arm' + sx, color='sand', frame=fs, ring=True,
                      t0=SLEEVE_T[0], t1=SLEEVE_T[1], off=0.003, thick=0.010, bevel=0.003, under='sand',
                      rmax=0.14, rmin=0.035, n_ring=48, sink=0.012))
    return P


def legs() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        cx = side * LEG_C[0]
        fb = frame((cx, LEG_C[1], 0.0), (cx, LEG_C[1], 1.0), front)
        fb['RN'] = 0.10
        # 後ろは下の縁を 0.168 まで下げる（体の土台の脚の筒の下の面が、裾の下に暗いとがった切れ端として垂れていた）
        P.append(dict(name='trouser_cuff' + sx, bone='shin' + sx, color='teal', frame=fb, ring=True,
                      t0=(CUFF_Z[0], 0.168), t1=CUFF_Z[1], off=0.004, thick=0.012, bevel=0.004, under='teal',
                      rmax=0.2, rmin=0.08, n_ring=56, sink=0.02))
        P += boot_pieces(side, sx)
    return P


def goggles() -> list[dict]:
    """木の玩具ゴーグル（首の前に下げる）：木の縁 ×2（外径 7.8cm・内径 5cm、奥行き 2.2cm）、暗いレンズ、橋、
    首の後ろを回る布帯。絵 nico_3d_front・side_right・nico_neck：縁の中心 (±0.058, z 1.035)、胸の前 y −0.115"""
    P = []
    fwd = np.array([0.0, -1.0, -0.12])
    up = np.array([0.0, 0.0, 1.0])
    yc = -0.124       # 縁の前の面（1 周目の −0.112 では、胸の前のこぶの中に縁が隠れた。こぶは views.MASK_CUT で外形から消す）
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        c = np.array([side * 0.058, yc, 1.035])
        V, F = ring_mesh(c, fwd, up, 0.039, 0.024, 0.022, n=24, bevel=0.004)
        P.append(dict(name='goggle_rim' + sx, bone='chest', color='wood', mesh=(V, F)))
        Vl, Fl = disc_mesh(c + np.array([0.0, 0.004, 0.0]), -fwd, up, 0.0255, 0.010, n=24)
        P.append(dict(name='goggle_lens' + sx, bone='chest', color='dark', mesh=(Vl, Fl)))
    Vb, Fb = box_mesh((0.0, yc + 0.010, 1.034), (0.022, 0.008, 0.010))
    P.append(dict(name='goggle_bridge', bone='chest', color='dark', mesh=(Vb, Fb)))
    # 帯：首のまわりの傾いた輪（後ろは襟の上 z 1.11、前は縁の外の横 z 1.035）。えりの外に立てる（rmin）
    A = np.array([0.10, -0.105, 1.035])
    B = np.array([-0.10, -0.105, 1.035])
    C = np.array([0.0, 0.07, 1.112])
    nrm = np.cross(B - A, C - A)
    nrm = nrm / np.linalg.norm(nrm)
    if nrm[2] < 0:
        nrm = -nrm
    cen = np.array([X0, -0.012, 0.0])
    cen[2] = A[2] + (np.dot(nrm, A - np.array([cen[0], cen[1], 0.0]))) / nrm[2]
    fst = frame(cen, cen + nrm, np.array([0.0, 1.0, 0.0]))
    fst['RN'] = 0.08
    P.append(dict(name='goggle_strap', bone='chest', color='dark', frame=fst, ring=True,
                  t0=-0.008, t1=0.008, off=0.004, thick=0.004, bevel=0.0015, rmax=0.2, rmin=0.068,
                  n_ring=64, sink=0.004))
    return P


def ponytail() -> list[dict]:
    """後ろの結び髪：結び帯（暗い茶の輪）と、下へ垂れる小さな房（8 角の断面を積む。絵 nico_head_back・side_right）"""
    P = []
    cx = X0
    # 2 周目：1 周目の房は小さく、帽子の下の縁に隠れて横・後ろから見えなかった（統括の確認）→ 帯を後ろへ、房を太く長く（絵の真横・背面：
    # 帯 z 1.165〜1.19・y 0.10〜0.14、房は z 1.07 まで後ろ下へ垂れ、最も太い所で幅 7cm）
    tie = [(1.166, ell(cx, 0.132, 0.021, 0.019, 10)), (1.170, ell(cx, 0.133, 0.024, 0.022, 10)),
           (1.188, ell(cx, 0.130, 0.024, 0.022, 10)), (1.192, ell(cx, 0.129, 0.021, 0.019, 10))]
    P.append(dict(name='hair_tie', bone='head', color='tie', loft=tie))
    tail = []
    for z, cy, rx, ry in ((1.170, 0.134, 0.019, 0.017), (1.156, 0.143, 0.032, 0.027), (1.134, 0.157, 0.042, 0.034),
                          (1.110, 0.170, 0.040, 0.032), (1.090, 0.181, 0.028, 0.023), (1.074, 0.189, 0.012, 0.010),
                          (1.064, 0.193, 0.003, 0.003)):
        tail.append((z, ell(cx, cy, rx, ry, 8, rot=math.pi / 8)))
    P.append(dict(name='hair_tail', bone='head', color='hair', loft=tail[::-1]))
    # 帯の上の、頭から帯へ集まる髪
    gather = [(1.186, ell(cx, 0.127, 0.020, 0.018, 8, math.pi / 8)), (1.202, ell(cx, 0.120, 0.027, 0.022, 8, math.pi / 8)),
              (1.220, ell(cx, 0.110, 0.031, 0.024, 8, math.pi / 8))]
    P.append(dict(name='hair_gather', bone='head', color='hair', loft=gather))
    return P


def hair_locks() -> list[dict]:
    """髪の房（2 周目）：絵（nico_head_back・side_right・top・face_front・front_right45）の、面のはっきりした太い房のボブ。
    1 周目の hair.lock_mesh（帽子の面に沿う薄い葉）は、帽子の丸みに沿って下の端が内へ巻き込み、きのこの笠・縁のめくれに見え、
    葉の縁が紙のように薄くぎざぎざに見えた（統括の確認）。ここでは房を「厚い板」にする：
      ・道：根（つむじのそば）→ 中（その向き・高さの帽子の面の外）→ 先（あごの高さ。外へ少しはねる。後ろの真ん中の 2 本は
        結び髪へ集まる）を通る 2 次の曲線。どの点も帽子の面より外へ押し出す（頭の中心からの向きで測る）。
      ・断面：峰（外）と左右の縁（厚み 0.14・幅）・内の面の 6 角。峰の両側の面は 20 度傾き、骨付けの段で折れ目の立った平らな面になる。
      ・幅：根で 0.55、3〜5 割の所で最も広く、先はとがる。輪は 9 本（長い平らな面）
    色は髪の 1 色、骨は head（剛体）"""
    from scipy import ndimage as NDI

    from recon import hair as HR
    from recon import views as V
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    phi, lo, vox = np.asarray(d['phi'], np.float32), d['lo'], float(d['vox'])
    C = np.array(HR.HEAD_C, float)

    def inside(P):
        idx = ((P[:, [2, 0, 1]] - lo[[2, 0, 1]]) / vox - 0.5).T
        return NDI.map_coordinates(phi, idx, order=1, mode='constant', cval=-1.0) > 0

    def radial(dirs, r_max=0.42, step=0.002):
        """頭の中心から向き dirs へ、外から内へ進んで最初に面に当たる距離"""
        rs = np.arange(r_max, 0.0, -step)
        P = C[None, None] + rs[None, :, None] * dirs[:, None, :]
        ins = inside(P.reshape(-1, 3)).reshape(len(dirs), len(rs))
        k = np.argmax(ins, 1)
        return np.where(ins.any(1), rs[k], 0.10)

    def horiz(th_deg, z, r_max=0.42, step=0.002):
        """縦の軸 (C.x, C.y) から、正面からの角度 th・高さ z の水平な向きへ、外から内へ進んで最初に面に当たる距離"""
        th = np.radians(th_deg)
        rs = np.arange(r_max, 0.0, -step)
        P = np.stack([C[0] + rs * np.sin(th), C[1] - rs * np.cos(th), np.full(len(rs), z)], 1)
        ins = inside(P)
        return float(rs[np.argmax(ins)]) if ins.any() else 0.0

    def at(th_deg, z, rho):
        th = np.radians(th_deg)
        return np.array([C[0] + rho * np.sin(th), C[1] - rho * np.cos(th), z])

    W_TOP = np.array([X0, 0.065, 1.545])     # つむじ（絵の真上の図：頭頂の少し後ろ）
    prof = [(0.0, 0.42), (1.0, 0.07), (0.94, -0.07), (0.0, -0.20), (-0.94, -0.07), (-1.0, 0.07)]
    widths = np.array([0.45, 0.82, 0.97, 1.0, 1.0, 0.98, 0.90, 0.62, 0.0])   # 先の近くまで広く、最後にとがる（絵の房）
    n = len(widths)

    def plank(P, w, lift_min, push=True, tmax=None):
        """tmax：断面の厚みに使う幅の上限（3 周目。幅の広い房が幅に比例して厚くならない。None は今までどおり）"""
        t = np.linspace(0.0, 1.0, n)
        # 帽子の面より外へ（頭の中心からの向きで）。根は少し沈める。垂れる房は道を面から作るので押し出さない
        dv = P - C
        rr = np.linalg.norm(dv, axis=1)
        dn = dv / rr[:, None]
        if push:
            rs = radial(dn)
            need = rs + lift_min + 0.20 * w * widths - np.where(t < 0.01, 0.012, 0.0)
            P = C + dn * np.maximum(rr, need)[:, None]
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        N = (P - C) - ((P - C) * T).sum(1, keepdims=True) * T
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        B = np.cross(T, N)
        ww = w * widths
        wt = ww if tmax is None else np.minimum(ww, tmax)
        rings = np.stack([P + B * (ww * px)[:, None] + N * (wt * py)[:, None] for px, py in prof], 1)
        k = len(prof)
        Vs = np.concatenate([rings[:-1].reshape(-1, 3), P[-1:], P[:1] - T[:1] * 0.002])
        tip, root = (n - 1) * k, (n - 1) * k + 1
        F = []
        for i in range(n - 2):
            for j in range(k):
                a0, a1 = i * k + j, i * k + (j + 1) % k
                F += [(a0, a0 + k, a1 + k), (a0, a1 + k, a1)]
        last = (n - 2) * k
        for j in range(k):
            F.append((last + j, tip, last + (j + 1) % k))
            F.append((root, (j + 1) % k, j))
        return _orient(Vs, F)

    def curve(R0, M, T2):
        t = np.linspace(0.0, 1.0, n)[:, None]
        Q = 2.0 * M - 0.5 * (R0 + T2)       # 中の点を t = 0.5 で通る 2 次の曲線
        return (1 - t) ** 2 * R0 + 2 * (1 - t) * t * Q + t ** 2 * T2

    # 垂れる房：(名前, 中の角度, 中の高さ, 先の角度, 先の高さ, 幅, 浮き, 先のはね, 先の軸からの距離（None は中の面の距離 + はね）)
    # 絵の頭の真横：横の髪は耳の後ろ（耳は見える）、耳の前は顔の横の房だけ（耳の高さは帽子が頭の横を覆うので、今は房で覆う）。
    # 背面：大きな房が結び髪へ V に集まり、外の房ほど
    # 先が高い（下の縁は逆 V）。正面：あごの高さで外へ少しはねる
    # 3 周目（会話のカメラの近写から）：房 19 本は 2.5 重に重なり、1 本ずつは細い帯にしか見えなかった（絵は太い房 5〜6 本）。
    # 垂れる房を 11 本に減らし（となりと半分ずつ重なる）、耳を出す：耳（θ 81〜99 度、z 1.227〜1.297）の前は細いこめかみの房
    # （θ 58 度、後ろの縁 約 75 度）、耳の上は耳の上の端（1.30）で終わり後ろへ流れる房、耳の後ろは前の縁が 100 度より後ろの房
    TMAX = 0.066     # 断面の厚みは幅 0.066 の房と同じまで（幅を広げても厚くしない）
    hang = [
        ('back_c', 180, 1.36, 180, 1.188, 0.078, 0.012, 0.0, 0.112),
        ('back_m_l', 155, 1.33, 158, 1.186, 0.078, 0.012, 0.004, None),
        ('back_m_r', 205, 1.33, 202, 1.186, 0.078, 0.012, 0.004, None),
        ('back_o_l', 130, 1.31, 131, 1.205, 0.074, 0.012, 0.012, None),
        ('back_o_r', 230, 1.31, 229, 1.205, 0.074, 0.012, 0.012, None),
        # 耳の上：耳の上の端で終わり、先は後ろ・外へはねる（絵の真横：耳の上を髪が弧で通る）
        ('side_l', 90, 1.36, 108, 1.300, 0.074, 0.012, 0.014, None),
        ('side_r', -90, 1.36, -108, 1.300, 0.074, 0.012, 0.014, None),
        # 耳の前：こめかみから垂れる細くとがった房（絵の真横・正面）
        ('side_fl', 55, 1.31, 57, 1.250, 0.034, 0.010, 0.010, None),
        ('side_fr', -55, 1.31, -57, 1.250, 0.034, 0.010, 0.010, None),
        # 下の層（上の層の房の間の帽子を覆う。浮きを小さく）
        ('back_i_l', 167, 1.32, 169, 1.192, 0.064, 0.005, 0.0, None),
        ('back_i_r', 193, 1.32, 191, 1.192, 0.064, 0.005, 0.0, None),
    ]
    out = []
    # 垂れる房の道は、縦の軸のまわりの円柱の座標で作る：高さは根（つむじの横 1.536）から先へ、角度は中 → 先、軸からの距離は
    # その高さ・角度の帽子の面 ＋ 浮き。一番張り出した高さより下は距離を減らさない（帽子の下の丸みに沿って内へ巻き込まない）、
    # 先の 3 割で外へはねる。後ろの真ん中の房（先の距離を決めたもの）は結び髪へ集まる。
    # 2 次の曲線で中の点を通す作り（2 周目の最初）は、帽子の面への押し出しが輪ごとに跳び、横に棚のような段ができた
    sgrid = np.linspace(0.0, 1.0, n)
    for name, thm, zm, tht, zt, w, lift, flick, rho_t in hang:
        z0 = 1.522        # 根はつむじの横で帽子の中に沈める（1.536 では頭頂に房の根の束が立った）
        zz = z0 - (z0 - zt) * sgrid ** 1.25
        th = thm + (tht - thm) * np.clip((sgrid - 0.2) / 0.8, 0, 1)
        rho_s = np.array([horiz(a, b) for a, b in zip(th, zz)])
        rho = rho_s + lift + 0.2 * w * widths
        k_wide = int(np.argmax(rho))
        if rho_t is None:
            rho[k_wide:] = np.maximum.accumulate(rho[k_wide:])
            rho += flick * np.clip((sgrid - 0.65) / 0.35, 0, 1) ** 2
        else:
            rho[-1] = rho_t        # 先だけ結び髪へ向かう（手前の輪は帽子の外のまま。帽子の下の丸みの外を通る）
            rho[-2] = max(rho[-2], rho[-3])
        # つむじの近く（根）は、つむじの点の横へ寄せる（全部の房がつむじから出る）
        rho[0] = min(rho[0], 0.06)
        P = np.stack([C[0] + rho * np.sin(np.radians(th)), C[1] - rho * np.cos(np.radians(th)), zz], 1)
        P[0] = W_TOP + 0.03 * np.array([np.sin(np.radians(thm)), -np.cos(np.radians(thm)), 0.0])
        P[0, 2] = z0
        Vm, Fm = plank(P, w, lift, push=False, tmax=TMAX)
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(Vm, Fm)))
    # 上の房（つむじから前・横へ。頭頂のふくらみ）と前髪（本人の左の分け目から、本人の右の眉の上へ流れる。絵 nico_face_front_r2）。
    # (名前, 根, 先, 幅, 浮き)。中は根と先の向きの間（頭の中心から）の面の外
    top = [
        ('top_f', W_TOP + [0.0, -0.035, -0.012], [X0 + 0.02, -0.110, 1.458], 0.068, 0.006),
        ('top_l', W_TOP + [0.03, -0.015, -0.012], [0.160, -0.040, 1.425], 0.066, 0.006),
        ('top_r', W_TOP + [-0.03, -0.015, -0.012], [-0.175, -0.040, 1.425], 0.066, 0.006),
        # 前髪：本人の左の分け目（x 0.05〜0.07）から、本人の右の眉の上へ斜めに流れる大きな房 2 本と、両のこめかみの房
        ('fringe_a', [0.060, -0.080, 1.528], [-0.085, -0.140, 1.362], 0.062, 0.008),
        ('fringe_b', [0.040, -0.092, 1.515], [-0.028, -0.148, 1.374], 0.050, 0.008),
        # 3 周目：本人の左の額の生え際（x 0.07〜0.135、z 1.36〜1.39）に帽子の縁の髪の色の帯が見えた → こめかみの房を広げ、
        # 分け目からその内側へ下りる房を 1 本足す（絵：分け目から本人の左のこめかみへ弧を描く房が額の左の縁を作る）
        ('fringe_c', [0.085, -0.070, 1.505], [0.120, -0.116, 1.334], 0.056, 0.007),
        ('fringe_e', [0.068, -0.082, 1.520], [0.084, -0.134, 1.360], 0.048, 0.008),
        ('fringe_d', [-0.055, -0.082, 1.505], [-0.128, -0.100, 1.318], 0.044, 0.007),
    ]
    for name, r0, r1, w, lift in top:
        R0, T2 = np.asarray(r0, float), np.asarray(r1, float)
        dm = (R0 - C) / np.linalg.norm(R0 - C) + (T2 - C) / np.linalg.norm(T2 - C)
        dm /= np.linalg.norm(dm)
        M = C + dm * (radial(dm[None])[0] + lift + 0.2 * w)
        Vm, Fm = plank(curve(R0, M, T2), w, lift)
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(Vm, Fm)))
    return out


def pieces() -> list[dict]:
    P = []
    P += collar_sleeves()
    P += overalls()
    P += legs()
    P += goggles()
    P += ponytail()
    P += hair_locks()
    return P


def boot_pieces(side: float, sx: str) -> list[dict]:
    """片足の布靴（左の値で書き、右は x を反転）。絵 nico_shoes と全身の絵（正面・右真横）：
    底 x 0.085〜0.265・y −0.150〜0.125、淡い砂色の平らな底（厚さ 2cm）、砂茶の布の胴（爪先は低く、足首の口は 0.10）"""
    X0_, X1_ = 0.086, 0.264
    YF, YB = -0.150, 0.124
    P = []

    def sec(z, x0, x1, y0, y1, rf, rb, k=3):
        return (z, rrect(x0, x1, y0, y1, rf, rb, k))

    sole = [sec(0.000, X0_ + 0.004, X1_ - 0.004, YF + 0.005, YB - 0.004, 0.06, 0.05),
            sec(0.004, X0_, X1_, YF, YB, 0.064, 0.054),
            sec(0.022, X0_, X1_, YF, YB, 0.064, 0.054),
            sec(0.026, X0_ + 0.003, X1_ - 0.003, YF + 0.003, YB - 0.003, 0.061, 0.051)]
    upper = [sec(0.020, X0_ + 0.007, X1_ - 0.007, YF + 0.007, YB - 0.007, 0.058, 0.048, 4),
             sec(0.045, X0_ + 0.008, X1_ - 0.009, YF + 0.010, YB - 0.008, 0.056, 0.047, 4),
             sec(0.062, X0_ + 0.013, X1_ - 0.015, YF + 0.034, YB - 0.010, 0.050, 0.045, 4),
             sec(0.078, X0_ + 0.022, X1_ - 0.024, -0.080, YB - 0.014, 0.045, 0.042, 4),
             sec(0.094, 0.115, 0.230, -0.040, 0.105, 0.040, 0.040, 4),
             sec(0.108, 0.120, 0.224, -0.018, 0.098, 0.038, 0.038, 4),
             sec(0.126, 0.128, 0.214, -0.004, 0.088, 0.034, 0.034, 4)]   # 足首の口（体を 0.122 で切る所を覆う）
    for name, color, secs in (('sole', 'sole', sole), ('upper', 'canvas', upper)):
        if side < 0:
            secs = [(z, [(-x, y) for (x, y) in pts][::-1]) for z, pts in secs]
        P.append(dict(name=f'boot_{name}{sx}', bone='foot' + sx, color=color, loft=secs,
                      ramp=('shin' + sx, 'foot' + sx)))
    return P


# ---------------------------------------------------------------- 決まりの塗り（cover_body から）

def body_rules(pos: np.ndarray, col: np.ndarray, lab: np.ndarray, under: np.ndarray, ins: dict, stats: dict) -> None:
    """胴の上はシャツの砂色、つなぎの横の上の縁より下は青緑、半袖の折り返しより先の腕は肌、裾の折り返しより下の脚は肌
    （裾の下の面は暗い青緑）、首は肌。頭と首の帯は形の場（hair.part_fields_at）で髪・肌・耳を決める"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    free = under < 0
    r_neck = np.hypot(x - X0, y)
    head = (z > NECK_TOP + 0.01) | ((z > 1.12) & (r_neck > 0.075) & (y < 0.0))
    shirt = free & ~head & (z >= SIDE_TOP)
    under[shirt] = NAMES.index('sand')
    # 腕：半袖の折り返しの中ほどより先は肌
    arm_skin = np.zeros(len(pos), bool)
    for side in (1.0, -1.0):
        S, E = np.array(jp('upper_arm', side)), np.array(jp('forearm', side))
        d = (E - S) / np.linalg.norm(E - S)
        t = (pos - S) @ d
        rr = np.linalg.norm((pos - S) - np.outer(t, d), axis=1)
        m = free & (side * x > 0.12) & (rr < 0.10) & (t > (SLEEVE_T[0] + SLEEVE_T[1]) / 2) & (z < 1.0)
        arm_skin |= m
    under[arm_skin] = NAMES.index('skin')
    # 首（えりの下の縁より上）：肌
    neck = free & ~head & (z > COLLAR_Z[0] - 0.01) & (r_neck < 0.075)
    under[neck] = NAMES.index('skin')
    # つなぎ（腰の帯より下、手は除く）
    hand = (np.abs(x) > 0.30) & (z > 0.55)
    over = free & (z < SIDE_TOP) & ~hand & ~arm_skin
    under[over] = NAMES.index('teal')
    # くるぶし（裾の折り返しより下）：肌。裾の下の面（脚の軸から離れた所）は暗い青緑
    rl = np.hypot(np.abs(x) - LEG_C[0], y - LEG_C[1])
    ankle = free & (z < CUFF_Z[0] + 0.004)
    under[ankle] = NAMES.index('skin')
    under[ankle & (rl > 0.055) & (z > 0.15)] = NAMES.index('teal_dark')
    # 頭と首の帯：形の場で（ヤーナと同じ作り）
    from recon import hair as HR
    hb = (z > 1.10) & (z < 1.62) & (np.hypot(x - X0, y - 0.01) < np.where(z > 1.16, 0.30, 0.10))
    hi = np.nonzero(hb)[0]
    if len(hi):
        f = HR.part_fields_at(pos[hi], x_half=0.30, z0=1.08)
        xh, yh, zh = x[hi], y[hi], z[hi]
        ear = f['ear'] > -0.002
        hair = (f['hair'] > -0.004) & ~ear
        # 頭の面に沿った帽子（顔の範囲の縁・耳の前）は、線より下なら肌（ヤーナと同じ）。1 周目は顔のまわり・あごの横に
        # 髪の色、髪の縁に肌の色のまだらが出た。前（正面から 75 度まで）は生え際の線、耳のあたりは耳の上、耳より後ろは帽子の下の端
        ax = np.abs(xh - X0)
        th_f = np.degrees(np.arctan2(ax, -(yh - 0.01)))
        flush = (f['hair'] - f['skin']) < 0.009
        line = np.where(th_f < 75.0, np.interp(ax, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]),
                        np.where(th_f < 108.0, 1.300, 1.17))
        hair &= ~(flush & (zh < line))
        lab_h = np.full(len(hi), NAMES.index('skin'))
        lab_h[hair] = NAMES.index('hair')
        # 帽子の下の縁（あごの高さ）は内側の髪の暗い色：房の先のすき間から見える（絵の房の先の間の暗い面）
        lab_h[hair & (zh < 1.232) & (zh > 1.16)] = NAMES.index('hair_dark')
        lab_h[ear] = NAMES.index('skin')
        lab_h[zh < COLLAR_Z[0] - 0.01] = NAMES.index('sand')
        keep = under[hi] >= 0
        under[hi[~keep]] = lab_h[~keep]
    stats['nico_rule_texels'] = int((shirt | arm_skin | neck | over | ankle).sum())


# ---------------------------------------------------------------- 手の部品（hand.py）

# 両手とも力を抜いて開いた手（hand.build_open）。素手（掌も指も肌）。絵 nico_hands_r2.png：子どもの丸い手、短めの太い指。
# 再構築の座標では手首から指先まで約 15cm（ハルの開いた手とほぼ同じ長さ）。指の太さ 1.12 倍
_S, _R = 1.0, 1.12
HAND = dict(
    GLOVE=None,
    LID='skin',
    OPEN_FINGERS=[(n, z * _S, x * _S, r * _R, tuple(v * _S for v in L), fan) for n, z, x, r, L, fan in (
        ('index', 0.0255, 0.068, 0.0080, (0.033, 0.021, 0.017), 6.0),
        ('middle', 0.0085, 0.071, 0.0083, (0.035, 0.023, 0.018), 1.0),
        ('ring', -0.0085, 0.068, 0.0078, (0.032, 0.021, 0.017), -4.0),
        ('pinky', -0.0240, 0.061, 0.0068, (0.026, 0.017, 0.014), -9.0))],
    OPEN_CURL=(14.0, 20.0, 14.0),
    CUFF_LID=(-0.012, 0.006),
    OPEN_THUMB=dict(base=(0.026, 0.008, 0.024), r=0.0088 * _R, lens=(0.032, 0.027, 0.022), out_deg=22.0,
                    palm_deg=34.0, curl=(8.0, 12.0, 10.0)),
    PALM_HALF_T=0.0120 * _R,
    PALM_WRIST=(0.002, 0.0, 0.016, 0.029),
    PALM_X=(0.012, 0.045),
    THENAR=((0.029, 0.007, 0.023), 0.0145),
    HYPOTHENAR=((0.035, 0.005, -0.021), 0.013),
    LEFT_HAND_CUT=-0.004,
    LEFT_HAND_RAMP=(-0.014, 0.006),
)
