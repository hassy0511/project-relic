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

# 色は spec_nico_r2.md の色見本（主要 6 色）。つなぎの影の色は使わない
PALETTE = {
    'teal': '#54777B',       # つなぎ（くすんだ青緑の帆布）
    'sand': '#DCC7A7',       # シャツ・靴底
    'canvas': '#A98749',     # 布靴・ゴーグルの木の縁・ボタン
    'dark': '#594333',       # ゴーグルの内側・結び帯・ゴーグルの帯
    'skin': '#E7B58D',
    'hair': '#E8C58D',       # 麦わら色の髪
    'lens': '#3F2E25',       # ゴーグルのレンズ（暗い樹脂。発光しない）
    'teal_dark': '#466569',  # 裾の折り返しの内側・ポケットの縁（つなぎの影の側）
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
BOOT_CUT = 0.088        # この高さより下の脚の体は消して、靴の部品に置き換える
BOOT_RAMP = (0.05, 0.10)
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
        P.append(dict(name='strap_button' + sx, bone='chest', color='canvas', frame=fw,
                      outline=octagon(xc - 0.015, xc + 0.015, 0.937, 0.966, 0.006), off=0.014, thick=0.007,
                      bevel=0.003, rmax=0.25, h=0.004))
        sc = side * math.radians(79.0) * fw['RN']
        P.append(dict(name='side_button' + sx, bone='hips', color='canvas', frame=fw,
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
                  off=0.003, thick=0.007, bevel=0.0025, under='sand', rmax=0.2, rmin=0.052, h=0.005))
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
        P.append(dict(name='trouser_cuff' + sx, bone='shin' + sx, color='teal', frame=fb, ring=True,
                      t0=CUFF_Z[0], t1=CUFF_Z[1], off=0.004, thick=0.012, bevel=0.004, under='teal',
                      rmax=0.2, rmin=0.08, n_ring=56, sink=0.02))
        P += boot_pieces(side, sx)
    return P


def goggles() -> list[dict]:
    """木の玩具ゴーグル（首の前に下げる）：木の縁 ×2（外径 7.8cm・内径 5cm、奥行き 2.2cm）、暗いレンズ、橋、
    首の後ろを回る布帯。絵 nico_3d_front・side_right・nico_neck：縁の中心 (±0.058, z 1.035)、胸の前 y −0.115"""
    P = []
    fwd = np.array([0.0, -1.0, -0.12])
    up = np.array([0.0, 0.0, 1.0])
    yc = -0.112
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        c = np.array([side * 0.058, yc, 1.035])
        V, F = ring_mesh(c, fwd, up, 0.039, 0.024, 0.022, n=24, bevel=0.004)
        P.append(dict(name='goggle_rim' + sx, bone='chest', color='canvas', mesh=(V, F)))
        Vl, Fl = disc_mesh(c + np.array([0.0, 0.004, 0.0]), -fwd, up, 0.0255, 0.010, n=24)
        P.append(dict(name='goggle_lens' + sx, bone='chest', color='lens', mesh=(Vl, Fl)))
    Vb, Fb = box_mesh((0.0, yc + 0.010, 1.034), (0.022, 0.008, 0.010))
    P.append(dict(name='goggle_bridge', bone='chest', color='dark', mesh=(Vb, Fb)))
    # 帯：首のまわりの傾いた輪（後ろは襟の上 z 1.11、前は縁の外の横 z 1.035）。えりの外に立てる（rmin）
    A = np.array([0.10, -0.095, 1.035])
    B = np.array([-0.10, -0.095, 1.035])
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
    tie = [(1.168, ell(cx, 0.118, 0.019, 0.017, 10)), (1.172, ell(cx, 0.119, 0.021, 0.019, 10)),
           (1.188, ell(cx, 0.116, 0.021, 0.019, 10)), (1.192, ell(cx, 0.115, 0.019, 0.017, 10))]
    P.append(dict(name='hair_tie', bone='head', color='dark', loft=tie))
    tail = []
    for z, cy, rx, ry in ((1.172, 0.118, 0.016, 0.014), (1.160, 0.128, 0.026, 0.022), (1.140, 0.142, 0.034, 0.028),
                          (1.118, 0.155, 0.035, 0.028), (1.098, 0.166, 0.026, 0.021), (1.084, 0.174, 0.012, 0.010),
                          (1.076, 0.178, 0.003, 0.003)):
        tail.append((z, ell(cx, cy, rx, ry, 8, rot=math.pi / 8)))
    P.append(dict(name='hair_tail', bone='head', color='hair', loft=tail[::-1]))
    # 結び帯の上の、頭から帯へ集まる髪（帯の上の短い房）
    gather = [(1.186, ell(cx, 0.112, 0.018, 0.016, 8, math.pi / 8)), (1.200, ell(cx, 0.106, 0.024, 0.020, 8, math.pi / 8)),
              (1.216, ell(cx, 0.098, 0.028, 0.022, 8, math.pi / 8))]
    P.append(dict(name='hair_gather', bone='head', color='hair', loft=gather))
    return P


def hair_locks() -> list[dict]:
    """髪の房と前髪を 1 本ずつの面の部品にする（hair.LOCKS_AS_PARTS、hair.lock_mesh）。色は髪の 1 色、骨は head"""
    from recon import hair as HR
    from recon import views as V
    if not HR.LOCKS_AS_PARTS:
        return []
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    out = []
    for name, Vm, Fm in HR.lock_parts(d['phi'], d['lo'], float(d['vox'])):
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
             sec(0.092, 0.115, 0.230, -0.040, 0.105, 0.040, 0.040, 4),
             sec(0.102, 0.118, 0.226, -0.020, 0.100, 0.038, 0.038, 4)]
    for name, color, secs in (('sole', 'sand', sole), ('upper', 'canvas', upper)):
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
        zh = z[hi]
        ear = f['ear'] > -0.002
        hair = (f['hair'] > -0.004) & ~ear
        lab_h = np.full(len(hi), NAMES.index('skin'))
        lab_h[hair] = NAMES.index('hair')
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
