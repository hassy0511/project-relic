"""町長トルーデ（trude）の服の部品と塗りの決まり（costume.py が読み込む。書式は chars/nico_parts.py・burton_parts.py と同じ）。

部品の表：docs/art_orders/W2_トルーデ3D化の結果.md の 1 章。寸法は calib.json のカメラで絵（W2-01・W2-01b の trude_*.png）に
1cm の格子を重ねて読んだ（build/trude/tools/grid.py。再構築の座標：身長 1.55m。本来の 1.40m へは骨付けの段で 0.903 倍）。
本人の左 = +X、正面 = −Y。
  赤錆の肩掛け（前は留め具の下で開く。首の後ろは立った襟）・肩掛けの暗い線・丸い真鍮の留め具と留め布・石墨の立ち襟（とっくり）・
  袖口の金の帯 ×2・革のベルトと真鍮の輪 ×2・腰の袋 ×2・前掛け（前・後ろ、金の裾の帯）・靴 ×2（底・かかと・胴・爪先・帯・留め具）・
  髪の房（額から後ろのお団子へ流れる面のはっきりした板）・お団子・耳の前の細い房 ×2。手は hand.py の開いた手（素手）、
  右手は杖（T 字の握り）を握る形（ai_character.py の --hand-part、HAND['GRIP']。杖は CANE）。
塗りの決まり（body_rules）：ベルトより上の胴と腕は生成りの上着（袖口の帯より先の前腕は石墨の内袖）、首は石墨、
ベルトより下は茶のスカート（裾の補修布は薄茶の四角）、スカートの裾より下の脚は石墨の靴下、頭は形の場。
"""
from __future__ import annotations

import math
import os

import numpy as np

# 色：spec（W2-01 の spec_townsfolk_3d.md・W2-01b の spec_townsfolk_3d_add.md）の色見本を基に、絵の平らに照らされた所の
# 中央値へ寄せた（build/trude/tools/colors.py。結果の文書 3 章に spec との違い）
PALETTE = {
    'rust': '#B4503A',        # 肩掛け（赤錆の厚布。絵 #BA4D32、spec #B75B43）
    'rust_line': '#6B4A3E',   # 肩掛けの裾の上の線（暗い茶）
    'ivory': '#EFD8B8',       # 上着・前掛け（生成りの木綿。絵 #FBDFBF、spec #F3E9D2）
    'brown': '#5E4031',       # スカート（焦げ茶の厚布。絵 #5F4030、spec #594333）
    'brown_dark': '#43301F',  # スカートの裾の内側
    'leather': '#5A3D2C',     # ベルト・腰の袋（革。絵 #644532・#5B3D2C）
    'graphite': '#433D38',    # 立ち襟・内袖・靴下（石墨。絵の立ち襟 #453E39、spec #444641）
    'brass': '#C2954F',       # 留め具・ベルトの輪・靴の留め具・杖の金具（くすんだ真鍮。絵 #DFA95D の照り、spec #A98749）
    'trim': '#C39050',        # 袖口・前掛けの裾の帯（黄土の布。絵 #C69152）
    'skin': '#E7B58D',
    'hair': '#C6B5AD',        # 灰白の髪：房の上の面（絵の照った面 #DCCAC1、spec #D6CCC4。描画で明るく見える分を下げた）
    'hair_dark': '#94857F',   # 髪の土台（房のすき間に見える内側の髪。生え際の近くは房と同じ色）
    'hair_shadow': '#A4938C',  # 房の横・下の面（絵の陰の面 #C0AFA7・耳の前の房 #B5A299）
    'boot': '#583D2C',        # 靴の胴（茶の革。絵 #50382A）
    'boot_light': '#76533A',  # 靴の爪先
    'sole': '#2E2724',        # 靴底・かかと
    'patch': '#976644',       # スカートの補修布（絵 #996746、spec #C6AB88）
    'wood': '#5A3829',        # 杖の木の軸・握り
}
NAMES = list(PALETTE)
CELLS = 24

X0 = 0.0        # 顔・首の左右の中心

# A ポーズの関節（chars/trude.json の joints.ART_XZ と同じ x・z。y は真横の絵）
J = {
    'upper_arm': (0.15, -0.007, 1.05), 'forearm': (0.285, 0.104, 0.875), 'hand': (0.40, 0.09, 0.735),
    'hand_end': (0.44, 0.103, 0.63), 'thigh': (0.09, 0.0, 0.66), 'shin': (0.12, 0.0, 0.37),
    'foot': (0.125, 0.0, 0.09),
}
# 肩掛けは近くの体の重みを写す（胸に剛体だと、杖をつく右腕の上腕が肩掛けの横を突き抜けた）
FOLLOW_BODY = ('turtleneck', 'belt', 'capelet', 'capelet_line', 'collar_base')
FOLLOW_TORSO_ONLY = ('turtleneck', 'belt')
BOX_RULES: list = []

NECK_TOP = 1.205                # 首の上（あごの下）
COLLAR_T0 = (1.172, 1.205)      # 立ち襟の下の縁（前, 後ろ）
COLLAR_T1 = (1.205, 1.238)      # 立ち襟の上の縁（前, 後ろ）
BELT_Z = (0.843, 0.890)         # ベルトの下・上
SLEEVE_T = (0.086, 0.106)       # 袖口の金の帯：前腕の軸に沿った肘からの長さ
SKIRT_HEM = 0.222               # スカートの裾（前。横・後ろは少し高い：hem_z）
APRON = dict(top=BELT_Z[0] + 0.006, hem=0.398, trim=0.024, x_top=(-0.112, 0.118), x_bot=(-0.134, 0.138))
APRON_BACK = dict(top=BELT_Z[0] + 0.006, hem=0.402, trim=0.024, x_top=(-0.072, 0.072), x_bot=(-0.096, 0.096))
# 顔のまわりの髪の塗りの下の線（|x − X0| → z）。正面の絵の生え際（額の真ん中 1.438、こめかみへ下がる）
HAIRLINE_PAINT = ([0.0, 0.04, 0.07, 0.09, 0.10, 0.11, 0.12, 0.13], [1.438, 1.425, 1.405, 1.385, 1.365, 1.335, 1.30, 1.27])
BOOT_CUT = 0.155        # この高さより下の脚の体は消して、靴の部品に置き換える
BOOT_RAMP = (0.06, 0.15)
BOOT_CUT_X = (0.03, 0.30)
RIGHT_HAND_PART = True

# 肩掛けの断面（高さ → 左右の半幅 a、前の端 yf、後ろの端 yb）。正面・右真横の絵の外形（格子）で読んだ
CAPE_Z = [0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.24]
CAPE_A = [0.296, 0.292, 0.276, 0.250, 0.214, 0.168, 0.122, 0.098]
CAPE_YF = [-0.188, -0.178, -0.162, -0.142, -0.120, -0.096, -0.074, -0.066]
CAPE_YB = [0.195, 0.192, 0.186, 0.179, 0.170, 0.158, 0.130, 0.110]
CAPE_N = 2.5
CLASP = (-0.022, 1.100)          # 留め具の中心（x, z）


# ---------------------------------------------------------------- 形の段のメッシュの測り

_MESH = None
_BVH = None


def _mesh_npz():
    global _MESH
    if _MESH is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'build', 'trude',
                         'trude_mesh.npz')
        d = np.load(p)
        _MESH = (np.asarray(d['verts'], float), np.asarray(d['tris'], np.int64))
    return _MESH


def _mesh() -> np.ndarray:
    return _mesh_npz()[0]


def _bvh():
    global _BVH
    if _BVH is None:
        from mathutils.bvhtree import BVHTree
        V, F = _mesh_npz()
        _BVH = BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in t) for t in F])
    return _BVH


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


def outer_r(th: np.ndarray, z: np.ndarray, cy: float = 0.0, R: float = 0.7) -> np.ndarray:
    """縦の軸 (X0, cy) から、正面からの角度 th（+ = 本人の左）・高さ z の水平な向きで、外から撃って最初に当たる体の面の半径"""
    from mathutils import Vector
    bvh = _bvh()
    out = np.zeros(len(th))
    for i, (t, zz) in enumerate(zip(th, z)):
        d = np.array([math.sin(t), -math.cos(t), 0.0])
        org = np.array([X0, cy, zz]) + d * R
        hit = bvh.ray_cast(Vector(org), Vector(-d), R)
        out[i] = R - hit[3] if hit[0] is not None else 0.0
    return out


# ---------------------------------------------------------------- 小さな形（面をそのまま渡す部品）

def _orient(V, F):
    F = np.asarray(F, np.int64)
    vol = np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum()
    return V, (F[:, ::-1] if vol < 0 else F)


def disc_mesh(c, axis, up, r, depth, n=20, bevel=0.0):
    """軸 axis（前向き）の円板（厚み depth、前の縁は bevel だけ面取り）"""
    c, axis, up = (np.asarray(v, float) for v in (c, axis, up))
    axis = axis / np.linalg.norm(axis)
    e0 = up - axis * np.dot(up, axis)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(axis, e0)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(a)[:, None] * e0 + np.sin(a)[:, None] * e1
    prof = [(r, 0.0), (r, depth - bevel), (r - bevel, depth)]
    V = np.concatenate([c + axis * d + circ * rr for rr, d in prof] + [[c, c + axis * depth]])
    k = len(prof)
    F = []
    for j in range(k - 1):
        for i in range(n):
            i2 = (i + 1) % n
            F += [(j * n + i, (j + 1) * n + i, (j + 1) * n + i2), (j * n + i, (j + 1) * n + i2, j * n + i2)]
    cb, cf = k * n, k * n + 1
    for i in range(n):
        i2 = (i + 1) % n
        F += [(cb, i2, i), (cf, (k - 1) * n + i, (k - 1) * n + i2)]
    return _orient(V, F)


def box_mesh(c, half, ex=(1.0, 0.0, 0.0), ey=(0.0, 1.0, 0.0)):
    c = np.asarray(c, float)
    ex = np.asarray(ex, float) / np.linalg.norm(ex)
    ey = np.asarray(ey, float) - ex * np.dot(ey, ex)
    ey /= np.linalg.norm(ey)
    ez = np.cross(ex, ey)
    hx, hy, hz = half
    V = np.array([c + sx * hx * ex + sy * hy * ey + sz * hz * ez for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)])
    F = [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4), (2, 6, 7), (2, 7, 3), (0, 4, 6), (0, 6, 2),
         (1, 3, 7), (1, 7, 5)]
    return _orient(V, F)


def ell(cx, cy, rx, ry, n=10, rot=0.0):
    return [(cx + rx * math.cos(rot + 2 * math.pi * k / n), cy + ry * math.sin(rot + 2 * math.pi * k / n))
            for k in range(n)]


def thick_sheet(P: np.ndarray, Nrm: np.ndarray, thick: float, closed_u: bool = False):
    """格子 P (nu, nv, 3) の外の面と、法線 Nrm の逆へ thick だけ下げた内の面を、縁でつないだ閉じた板"""
    nu, nv = P.shape[:2]
    Q = P - Nrm * thick
    V = np.concatenate([P.reshape(-1, 3), Q.reshape(-1, 3)])
    off = nu * nv

    def idx(i, j, inner=False):
        return (off if inner else 0) + i * nv + j
    F = []
    iu = range(nu) if closed_u else range(nu - 1)
    for i in iu:
        i2 = (i + 1) % nu
        for j in range(nv - 1):
            F += [(idx(i, j), idx(i2, j), idx(i2, j + 1)), (idx(i, j), idx(i2, j + 1), idx(i, j + 1))]
            F += [(idx(i, j, 1), idx(i2, j + 1, 1), idx(i2, j, 1)), (idx(i, j, 1), idx(i, j + 1, 1), idx(i2, j + 1, 1))]
    # 縁（v の両端）
    for i in iu:
        i2 = (i + 1) % nu
        for j in (0, nv - 1):
            a, b, c, d = idx(i, j), idx(i2, j), idx(i2, j, 1), idx(i, j, 1)
            F += [(a, c, b), (a, d, c)] if j == 0 else [(a, b, c), (a, c, d)]
    if not closed_u:
        for i in (0, nu - 1):
            for j in range(nv - 1):
                a, b, c, d = idx(i, j), idx(i, j + 1), idx(i, j + 1, 1), idx(i, j, 1)
                F += [(a, b, c), (a, c, d)] if i == 0 else [(a, c, b), (a, d, c)]
    return _orient(V, np.array(F))


# ---------------------------------------------------------------- 肩掛け

def _cape_section(z):
    a = np.interp(z, CAPE_Z, CAPE_A)
    yf = np.interp(z, CAPE_Z, CAPE_YF)
    yb = np.interp(z, CAPE_Z, CAPE_YB)
    return a, yf, yb


def _se_point(th, a, yf, yb, n=CAPE_N):
    """超楕円の断面の点（th：正面からの角度、+ = 本人の左）"""
    s, c = np.sin(th), np.cos(th)
    x = X0 + a * np.sign(s) * np.abs(s) ** (2 / n)
    b = np.where(c > 0, -yf, yb)
    y = -np.sign(c) * b * np.abs(c) ** (2 / n)
    return x, y


def _cape_top(th):
    """肩掛けの上の縁の高さ：前の真ん中は留め具へ V に下がり、横・後ろは首を囲んで立つ（後ろが一番高い）"""
    a = np.abs(np.degrees(th))
    return np.interp(a, [0, 15, 30, 45, 90, 135, 180], [1.105, 1.150, 1.188, 1.204, 1.218, 1.232, 1.236])


def _cape_hem(th):
    c = np.cos(th)
    return 0.928 + 0.018 * np.clip(c, 0, None) ** 2


def _cape_open(z):
    """前の開き（留め具より下）の半分の角度"""
    f = np.clip((1.085 - z) / (1.085 - 0.93), 0, 1)
    return np.radians(26.0) * f ** 0.85


CAPE_VS = np.unique(np.concatenate([np.linspace(0.0, 1.0, 17), [0.875, 0.93]]))   # 裾の上の線の行を含む


def cape_surface(nu=64, vs=CAPE_VS):
    """肩掛けの外の面の格子 (nu, nv, 3)：u は前の開きの本人の左の縁 → 後ろ → 右の縁、v は上の縁 → 裾"""
    us = np.linspace(0.0, 1.0, nu)
    nv = len(vs)
    P = np.zeros((nu, nv, 3))
    TH = np.zeros((nu, nv))
    for j, v in enumerate(vs):
        # 開きの角度はその行の前の高さで決める
        z_est = 1.105 + (0.946 - 1.105) * (v ** 0.92)
        op = _cape_open(z_est)
        th = op + (2 * math.pi - 2 * op) * us          # 正面からの角度（+ = 本人の左）：op → π（後ろ）→ 2π − op
        thf = np.where(th > math.pi, th - 2 * math.pi, th)
        zt, zh = _cape_top(thf), _cape_hem(thf)
        z = zt + (zh - zt) * (v ** 0.92)
        a, yf, yb = _cape_section(z)
        x, y = _se_point(thf, a, yf, yb)
        P[:, j] = np.stack([x, y, z], 1)
        TH[:, j] = thf
    return P, TH


def capelet() -> list[dict]:
    """赤錆の肩掛け（絵 trude_3d_front・side_right・back・trude_neck）：首から肩・上腕の上を覆う短い外套。断面は超楕円（外形の
    格子で読んだ表 CAPE_*）、上の縁は首を囲んで立ち（後ろ 1.236、前は留め具へ V に下がる）、裾は 0.93、前は留め具の下で開く。
    体の面（外から撃って最初に当たる所）より 6mm 外へ押し出す。厚み 8mm。裾の 2.5cm 上に暗い線（別の薄い帯）"""
    P, TH = cape_surface()
    nu, nv = P.shape[:2]
    # 体より外へ（外から撃った体の面 + 6mm）。押し出しはならす
    # 点の実の向き（超楕円の媒介変数の角度とは違う。媒介変数の角度で測ると前の肩で体が突き抜けた）
    th = np.arctan2(P[..., 0] - X0, -P[..., 1]).ravel()
    z = P[..., 2].ravel()
    rb = outer_r(th, z, 0.0)
    rc = np.hypot(P[..., 0].ravel() - X0, P[..., 1].ravel())
    need = np.clip(rb + 0.007 - rc, 0, 0.08).reshape(nu, nv)
    from scipy import ndimage as NDI
    # 近所の最大 → ならす → 元の必要な量より内へは入れない（ならしで山が下がると体が突き抜けた）
    push = NDI.gaussian_filter(NDI.grey_dilation(need, size=(7, 5)), (2.0, 1.2), mode='nearest')
    push = np.maximum(push, need)
    rad = np.stack([P[..., 0] - X0, P[..., 1], np.zeros((nu, nv))], -1)
    rad /= np.maximum(np.linalg.norm(rad, axis=-1, keepdims=True), 1e-9)
    P = P + rad * push[..., None]
    # 法線（外向き）：格子の差分
    du = np.gradient(P, axis=0)
    dv = np.gradient(P, axis=1)
    N = np.cross(dv, du)
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-9)
    flip = (N * rad).sum(-1) < 0
    N[flip] *= -1
    V, F = thick_sheet(P, N, 0.008)
    out = [dict(name='capelet', bone='chest', color='rust', mesh=(V, F))]
    # 裾の上の線：v の 0.875〜0.93 の行の帯を 1.8mm 外へ（裾の 2〜3.3cm 上）
    j0, j1 = int(np.argmin(np.abs(CAPE_VS - 0.875))), int(np.argmin(np.abs(CAPE_VS - 0.93)))
    S, nS = P[:, j0:j1 + 1], N[:, j0:j1 + 1]
    Vs, Fs = thick_sheet(S + nS * 0.0018, nS, 0.0016)
    out.append(dict(name='capelet_line', bone='chest', color='rust_line', mesh=(Vs, Fs)))
    # 留め具（丸い真鍮）と留め布（本人の左へ）
    cx, cz = CLASP
    a, yf, yb = _cape_section(cz)
    yc = yf - 0.004
    Vc, Fc = disc_mesh((cx, yc + 0.002, cz), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), 0.024, 0.010, n=24, bevel=0.004)
    out.append(dict(name='clasp', bone='chest', color='brass', mesh=(Vc, Fc)))
    Vt, Ft = box_mesh((cx + 0.040, yc + 0.003, cz - 0.004), (0.024, 0.004, 0.010))
    out.append(dict(name='clasp_tab', bone='chest', color='rust', mesh=(Vt, Ft)))
    # 2 周目：前の開きの中の上着の前（生成りの板）。体の土台の肩掛けのかさの丸いふくらみが、胸の丸い塊に見えた。
    # 開きの中ほどの体の前の端の少し前に、左右へゆるく後ろへ曲がる板を置き、両の縁は肩掛けの下へ入れる
    zs = np.linspace(0.925, 1.095, 9)
    xs = np.linspace(-1.0, 1.0, 9)
    Pn = np.zeros((len(xs), len(zs), 3))
    for j, z in enumerate(zs):
        f = float(np.clip((1.095 - z) / (1.095 - 0.93), 0, 1))
        hw = 0.035 + 0.075 * f
        y0 = body_front_y(z, -0.06, 0.06) - 0.004
        for i, u in enumerate(xs):
            x = X0 + u * hw
            Pn[i, j] = (x, y0 + 1.6 * (x - X0) ** 2, z)
    Nn = np.zeros_like(Pn)
    Nn[..., 1] = -1.0
    Vn, Fn = thick_sheet(Pn, Nn, 0.004)
    out.append(dict(name='blouse_front', bone='chest', color='ivory', mesh=(Vn, Fn)))
    return out


# ---------------------------------------------------------------- えり・袖口・ベルト・前掛け

def collar_sleeves() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    # 石墨の立ち襟（とっくり）：首の縦の軸のまわりの輪。前が低く後ろが高い
    fc = frame((X0, 0.0, 0.0), (X0, 0.0, 1.0), front)
    fc['RN'] = 0.06
    P.append(dict(name='turtleneck', bone='neck', color='graphite', frame=fc, ring=True,
                  t0=COLLAR_T0, t1=COLLAR_T1, off=0.003, thick=0.006, bevel=0.002, under='graphite',
                  rmax=0.085, rmin=0.042, n_ring=56, sink=0.010, smooth_iters=10))
    # 立ち襟の下〜肩掛けの襟の内の、肩の上の面を覆う石墨の殻：首の付け根の中心から斜め上へ撃った体の面の外。体の土台の
    # 首の付け根は UV のつぶれた三角形が隣の島の色を拾い、生成り・肌・石墨の斑点になった（SKILL 3 章：塗りで追わず部品で覆う）
    fsb = {'kind': 'sphere', 'a': np.array([X0, 0.0, 1.10]), 'e0': np.array([0.0, -1.0, 0.0]),
           'e1': np.array([1.0, 0.0, 0.0]), 'e2': np.array([0.0, 0.0, 1.0]), 'RN': 0.1}
    P.append(dict(name='collar_base', bone='chest', color='graphite', frame=fsb, ring=True,
                  t0=math.radians(30.0) * 0.1, t1=math.radians(64.0) * 0.1, off=0.001, thick=0.0025, bevel=0.001,
                  rmax=0.25, rmin=0.04, n_ring=72, sink=0.010, smooth_iters=8))
    # 袖口の金の帯（生成りの広い袖の端）：前腕の軸
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        s, e = jp('forearm', side), jp('hand', side)
        fs = frame(s, e, front)
        fs['RN'] = 0.06
        P.append(dict(name='sleeve_trim' + sx, bone='forearm' + sx, color='trim', frame=fs, ring=True,
                      t0=SLEEVE_T[0], t1=SLEEVE_T[1], off=0.002, thick=0.006, bevel=0.002, under='trim',
                      rmax=0.12, rmin=0.03, n_ring=48, sink=0.012))
    return P


def belt_items() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    fw = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), front)
    fw['RN'] = 0.15
    P.append(dict(name='belt', bone='hips', color='leather', frame=fw, ring=True,
                  t0=BELT_Z[0], t1=BELT_Z[1], off=0.010, thick=0.006, bevel=0.002, under='brown',
                  rmax=0.3, n_ring=72, sink=0.014))
    for xc in (-0.075, 0.075):
        P.append(dict(name=f'belt_loop{"L" if xc > 0 else "R"}', bone='hips', color='brass', frame=fw,
                      outline=octagon(xc - 0.010, xc + 0.010, BELT_Z[0] - 0.008, BELT_Z[1] + 0.006, 0.003),
                      off=0.018, thick=0.005, bevel=0.0015, rmax=0.3, h=0.004))
    # 腰の袋 ×2（箱。ベルトの下、両脇の少し前）
    for name, ang in (('pouch.R', -82.0), ('pouch.L', 82.0)):
        P.append(dict(name=name, bone='hips', color='leather', box=True, frame=fw, ang=ang, zc=0.775,
                      size=(0.066, 0.032, 0.128), rmax=0.35))
    return P


SKIRT_TOP = BELT_Z[0] + 0.004
SKIRT_CY = 0.02                 # スカートの縦の軸の前後の位置（裾は後ろへ広い）
_SKIRT = None


def inner_r(th: np.ndarray, z: np.ndarray, cy: float = SKIRT_CY, R: float = 0.6) -> np.ndarray:
    """縦の軸 (X0, cy) から外へ、正面からの角度 th・高さ z の水平な向きに撃って、最初に当たる体の面の半径（軸は体の中）"""
    from mathutils import Vector
    bvh = _bvh()
    out = np.full(len(th), np.nan)
    for i, (t, zz) in enumerate(zip(th, z)):
        d = np.array([math.sin(t), -math.cos(t), 0.0])
        hit = bvh.ray_cast(Vector((X0, cy, zz)), Vector(d), R)
        if hit[0] is not None:
            out[i] = hit[3]
    return out


def skirt_table(nu: int = 120):
    """スカートの面の半径の表 (θ, z) → R。高さごとに軸から撃った体の面（レンズの体）＋4mm で、下へ行くほど半径を減らさない
    （レンズの体は裾の高さで内へ丸まり、風船・ちょうちんのズボンのように見えた）"""
    global _SKIRT
    if _SKIRT is None:
        from scipy import ndimage as NDI
        th = np.linspace(-math.pi, math.pi, nu, endpoint=False)
        zs = np.linspace(SKIRT_TOP, 0.19, 44)
        TH, Z = np.meshgrid(th, zs, indexing='ij')
        # 上（z ≥ 0.40）は軸から撃って最初に当たる面（外から撃つと手・腕を拾う）。裾の近く（z < 0.40）は外から撃って
        # 最初に当たる面（軸から撃つと脚の間の面を拾い、裾の近くで体が殻を突き抜けた。この高さに手は無い）
        R = np.zeros(TH.shape)
        lo = Z < 0.40
        R[lo] = outer_r(TH[lo], Z[lo], SKIRT_CY, R=0.60)
        ri = inner_r(TH[~lo], Z[~lo])
        R[~lo] = np.where(np.isfinite(ri), ri, 0.0)
        for j in range(1, len(zs)):
            R[:, j] = np.maximum(R[:, j], R[:, j - 1])
        # ならしても元の半径より内へは入れない（脚のふくらみが裾の近くで殻を突き抜けた）
        # 角度の向きだけ周期で（高さの向きを周期にすると、裾の半径が上の縁へ回り込み、ベルトの高さにつばができた）
        Rd = NDI.grey_dilation(NDI.grey_dilation(R, size=(3, 1), mode='wrap'), size=(1, 3), mode='nearest')
        R = np.maximum(NDI.gaussian_filter1d(Rd, 1.2, axis=0, mode='wrap'), R) + 0.006
        _SKIRT = (th, zs, R)
    return _SKIRT


def skirt_r(th: np.ndarray, z: np.ndarray) -> np.ndarray:
    """表から (θ, z) の半径（θ は周期、z は線形）"""
    T, Zs, R = skirt_table()
    nu = len(T)
    u = (np.asarray(th) + math.pi) / (2 * math.pi) * nu
    i0 = np.floor(u).astype(int) % nu
    i1 = (i0 + 1) % nu
    fu = u - np.floor(u)
    zc = np.clip(np.asarray(z), Zs[-1], Zs[0])
    j = np.clip(np.searchsorted(-Zs, -zc) - 1, 0, len(Zs) - 2)
    fz = (Zs[j] - zc) / (Zs[j] - Zs[j + 1])
    r0 = R[i0, j] * (1 - fz) + R[i0, j + 1] * fz
    r1 = R[i1, j] * (1 - fz) + R[i1, j + 1] * fz
    return r0 * (1 - fu) + r1 * fu


def skirt_point(th, z, lift=0.0):
    r = skirt_r(th, z) + lift
    return np.stack([X0 + r * np.sin(th), SKIRT_CY - r * np.cos(th), np.asarray(z, float) * np.ones_like(r)], -1)


def skirt() -> list[dict]:
    """スカート（ベルトの下〜裾、焦げ茶の厚布）：体の面の外の殻（厚み 6mm）。裾は hem_z の高さでまっすぐ切る。
    補修布は殻の上の薄い板（絵の正面・真横・背面・左前 45 度。spec は平らな色だが、殻の 1 色に塗れないので板にした）"""
    nu, nv = 72, 18
    th = np.linspace(-math.pi, math.pi, nu, endpoint=False)
    vs = np.linspace(0.0, 1.0, nv)
    TH = np.repeat(th[:, None], nv, 1)
    Z = SKIRT_TOP + (hem_z(np.degrees(TH)) - SKIRT_TOP) * vs[None, :]
    P = skirt_point(TH, Z)
    rad = np.stack([np.sin(TH), -np.cos(TH), np.zeros_like(TH)], -1)
    V, F = thick_sheet(P, rad, 0.006, closed_u=True)
    out = [dict(name='skirt', bone='hips', color='brown', mesh=(V, F))]
    # 2 周目：絵のように少し傾いた四角に、縁をまたぐ縫い目（暗い茶の短い棒、1 辺 3 本）
    def on_skirt(thc, zc, rc, u, v, tilt, lift):
        ct, st = math.cos(tilt), math.sin(tilt)
        uu, vv = u * ct - v * st, u * st + v * ct
        TT = thc + uu / rc
        ZZ = zc + vv
        return skirt_point(TT, ZZ, lift), np.stack([np.sin(TT), -np.cos(TT), np.zeros_like(TT)], -1)

    for k, (thd, zc, pw, ph, tdeg) in enumerate(PATCH_PARTS):
        thc, tilt = math.radians(thd), math.radians(tdeg)
        rc = float(skirt_r(np.array([thc]), np.array([zc]))[0])
        U, Vv = np.meshgrid(np.linspace(-pw / 2, pw / 2, 7), np.linspace(-ph / 2, ph / 2, 6), indexing='ij')
        Pp, rp = on_skirt(thc, zc, rc, U, Vv, tilt, 0.0022)
        Vp, Fp = thick_sheet(Pp, rp, 0.0016)
        out.append(dict(name=f'skirt_patch{k}', bone='hips', color='patch', mesh=(Vp, Fp)))
        # 縫い目：各辺の 1/4・2/4・3/4 に、辺をまたぐ長さ 1.6cm・幅 3mm の棒
        bars = []
        for (cu, cv, du, dv) in ((0.0, -ph / 2, 0, 1), (0.0, ph / 2, 0, 1), (-pw / 2, 0.0, 1, 0), (pw / 2, 0.0, 1, 0)):
            along = pw if du == 0 else ph
            for f in (-0.25, 0.0, 0.25):
                bu = cu + (f * along if du == 0 else 0.0)
                bv = cv + (f * along if dv == 0 else 0.0)
                hu = 0.0015 if du == 0 else 0.008
                hv = 0.008 if du == 0 else 0.0015
                Ub, Vb = np.meshgrid(np.array([bu - hu, bu + hu]), np.array([bv - hv, bv + hv]), indexing='ij')
                Pb, rb_ = on_skirt(thc, zc, rc, Ub, Vb, tilt, 0.0042)
                bars.append(thick_sheet(Pb, rb_, 0.0015))
        Vb_all = np.concatenate([b[0] for b in bars])
        offs = np.cumsum([0] + [len(b[0]) for b in bars[:-1]])
        Fb_all = np.concatenate([b[1] + o for b, o in zip(bars, offs)])
        out.append(dict(name=f'skirt_stitch{k}', bone='hips', color='brown_dark', mesh=(Vb_all, Fb_all)))
    return out


# 補修布の部品（2 周目）：(正面からの角度 度, 中心の高さ, 幅 m, 高さ m, 傾き 度)。正面・左右の真横・背面・左前 45 度の絵
PATCH_PARTS = [(-49.0, 0.392, 0.130, 0.120, -7.0), (54.0, 0.350, 0.080, 0.088, 9.0), (-108.0, 0.405, 0.100, 0.140, 5.0),
               (108.0, 0.432, 0.080, 0.075, -8.0), (158.0, 0.418, 0.080, 0.100, 6.0), (-159.0, 0.418, 0.072, 0.075, -6.0)]


def skirt_y(z: float, x0: float, x1: float, front: bool) -> float:
    """スカートの殻の外の面の、高さ z・左右 x0〜x1 の前の端（front）か後ろの端の y"""
    th = np.linspace(-math.pi, math.pi, 721)
    P = skirt_point(th, np.full(len(th), z), 0.006)
    m = (P[:, 0] > x0) & (P[:, 0] < x1) & ((P[:, 1] < SKIRT_CY) if front else (P[:, 1] > SKIRT_CY))
    return float(P[m, 1].min() if front else P[m, 1].max())


def apron() -> list[dict]:
    """前掛け（前・後ろ）：ベルトの下から垂れる板（高さの断面を積む。上はスカートに沿い、下へ行くほど離す）と、裾の金の帯"""
    P = []
    for nm, sg, A in (('apron', -1.0, APRON), ('apron_back', 1.0, APRON_BACK)):
        z_top, hem = A['top'], A['hem']
        zs = np.linspace(z_top, hem, 10)
        secs, secs_t = [], []
        for z in zs:
            f = (z_top - z) / (z_top - hem)
            x0 = A['x_top'][0] + (A['x_bot'][0] - A['x_top'][0]) * f
            x1 = A['x_top'][1] + (A['x_bot'][1] - A['x_top'][1]) * f
            zz = np.linspace(z, z_top, 6)
            if sg < 0:
                yb = min(min(body_front_y(q, x0, x1), skirt_y(q, x0, x1, True)) for q in zz)
            else:
                yb = max(max(body_back_y(q, x0, x1), skirt_y(q, x0, x1, False)) for q in zz)
            gap = 0.003 + 0.010 * f ** 1.3
            y_in = yb + sg * gap
            y_out = y_in + sg * 0.006
            c = ((x0 + x1) / 2, (y_in + y_out) / 2)
            secs.append((float(z), rect_sec(c, (1.0, 0.0), (x1 - x0) / 2, 0.003, 0.0015)))
            if z < hem + A['trim'] + 0.02:
                secs_t.append((float(z), c, (x1 - x0) / 2))
        P.append(dict(name=nm, bone='hips', color='ivory', loft=secs[::-1]))
        # 裾の金の帯（前掛けの下の縁、少し厚い）
        cb = secs_t[-1]
        zt0, zt1 = hem - 0.002, hem + A['trim']
        c = (cb[1][0], cb[1][1] + sg * 0.0012)
        tsec = [(zt0, rect_sec(c, (1.0, 0.0), cb[2] + 0.002, 0.0048, 0.0015)),
                (zt1, rect_sec(c, (1.0, 0.0), cb[2] + 0.002, 0.0048, 0.0015))]
        P.append(dict(name=nm + '_trim', bone='hips', color='trim', loft=tsec))
    return P


def rect_sec(c, tan, hw, ht, bev):
    """中心 c・横の向き tan の、角を bev だけ切った長方形の断面（8 点、上から見て反時計回り）"""
    tx, ty = tan
    nx, ny = -ty, tx
    loc = [(-hw + bev, -ht), (hw - bev, -ht), (hw, -ht + bev), (hw, ht - bev), (hw - bev, ht), (-hw + bev, ht),
           (-hw, ht - bev), (-hw, -ht + bev)]
    return [(c[0] + u * tx + v * nx, c[1] + u * ty + v * ny) for u, v in loc]


def legs() -> list[dict]:
    """靴と、裾と靴の間の靴下（石墨の筒。体の土台の脚は裾の下で細く裂けた形になり、灰の切れ端に見えた）"""
    P = []
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        P += boot_pieces(side, sx)
        cx, cy = side * 0.125, 0.028
        secs = [(z, ell(cx, cy, r, r * 0.95, 12)) for z, r in ((0.150, 0.039), (0.172, 0.041), (0.215, 0.045),
                                                                  (0.270, 0.050))]
        P.append(dict(name='stocking' + sx, bone='shin' + sx, color='graphite', loft=secs))
    return P


def boot_pieces(side: float, sx: str) -> list[dict]:
    """片足の靴（左の値で書き、右は x を反転）。絵 trude_shoes と全身の絵（正面・右真横）：底 x 0.070〜0.182・y −0.172〜0.138、
    暗い厚い底（かかとは高い）、茶の胴、明るい茶の爪先、足首の帯と真鍮の留め具（外側）"""
    X0_, X1_ = 0.070, 0.182
    YF, YB = -0.172, 0.138
    P = []

    def sec(z, x0, x1, y0, y1, rf, rb, k=3):
        return (z, rrect(x0, x1, y0, y1, rf, rb, k))

    sole = [sec(0.000, X0_ + 0.003, X1_ - 0.003, YF + 0.004, YB - 0.003, 0.050, 0.030),
            sec(0.004, X0_, X1_, YF, YB, 0.052, 0.032),
            sec(0.020, X0_, X1_, YF, YB, 0.052, 0.032)]
    heel = [sec(0.018, X0_ + 0.002, X1_ - 0.002, 0.050, YB, 0.004, 0.030),
            sec(0.034, X0_ + 0.002, X1_ - 0.002, 0.052, YB, 0.004, 0.030)]
    upper = [sec(0.018, X0_ + 0.006, X1_ - 0.006, YF + 0.006, YB - 0.006, 0.046, 0.028, 4),
             sec(0.050, X0_ + 0.007, X1_ - 0.008, YF + 0.012, YB - 0.008, 0.044, 0.028, 4),
             sec(0.075, X0_ + 0.012, X1_ - 0.014, -0.090, YB - 0.012, 0.036, 0.030, 4),
             sec(0.100, 0.086, 0.166, -0.050, 0.110, 0.032, 0.032, 4),
             sec(0.135, 0.084, 0.166, -0.044, 0.100, 0.036, 0.036, 4),
             sec(0.172, 0.083, 0.167, -0.042, 0.098, 0.038, 0.038, 4)]
    toe = [sec(0.020, X0_ + 0.004, X1_ - 0.004, YF + 0.003, -0.075, 0.046, 0.004),
           sec(0.052, X0_ + 0.005, X1_ - 0.006, YF + 0.008, -0.080, 0.044, 0.004),
           sec(0.074, X0_ + 0.012, X1_ - 0.014, YF + 0.034, -0.088, 0.034, 0.004)]
    strap = [sec(0.118, 0.080, 0.170, -0.048, 0.104, 0.038, 0.038, 4),
             sec(0.148, 0.080, 0.170, -0.047, 0.103, 0.038, 0.038, 4)]
    for name, color, secs in (('sole', 'sole', sole), ('heel', 'sole', heel), ('upper', 'boot', upper),
                              ('toe', 'boot_light', toe), ('strap', 'leather', strap)):
        if side < 0:
            secs = [(z, [(-x, y) for (x, y) in pts][::-1]) for z, pts in secs]
        P.append(dict(name=f'boot_{name}{sx}', bone='foot' + sx, color=color, loft=secs,
                      ramp=('shin' + sx, 'foot' + sx)))
    # 足首の帯の真鍮の留め具（外側、少し後ろ）
    xb = side * 0.172
    Vb, Fb = box_mesh((xb, 0.040, 0.133), (0.004, 0.012, 0.017))
    P.append(dict(name='boot_buckle' + sx, bone='foot' + sx, color='brass', mesh=(Vb, Fb)))
    return P


# ---------------------------------------------------------------- 髪（お団子・房）

BUN_C = np.array([X0, 0.192, 1.308])     # お団子の中心（右真横・背面の絵：後ろへ 0.13〜0.25、上下 1.24〜1.375）
BUN_R = (0.084, 0.062, 0.068)            # 半径（左右・前後・上下。2 周目：絵の大きさ＝1 周目の 1.3 倍）


def bun() -> list[dict]:
    """後ろの低いお団子：房が渦に巻いた丸い塊（経緯の格子の球を、6 本の渦の筋でふくらませた低い多面体）。
    筋の山は髪の色、谷（筋の間）は陰の色（2 周目：1 色では白い玉に見えた）"""
    nl, nm = 9, 18
    V = []
    for i in range(1, nl):
        ph = math.pi * i / nl - math.pi / 2          # 緯度（−90 = 前の付け根、+90 = 後ろの端）
        for k in range(nm):
            lam = 2 * math.pi * k / nm
            w = 1.0 + 0.13 * math.cos(6 * lam + 1.8 * ph) * math.cos(ph)
            cx = math.cos(ph) * math.cos(lam) * BUN_R[0] * w
            cz = math.cos(ph) * math.sin(lam) * BUN_R[2] * w
            cy = math.sin(ph) * BUN_R[1] * (1.0 + 0.06 * math.cos(6 * lam))
            V.append(BUN_C + np.array([cx, cy, cz]))
    V.append(BUN_C + np.array([0.0, -BUN_R[1], 0.0]))
    V.append(BUN_C + np.array([0.0, BUN_R[1] * 1.05, 0.0]))
    V = np.array(V)
    F, val = [], []
    for i in range(nl - 2):
        ph = math.pi * (i + 1.5) / nl - math.pi / 2
        for k in range(nm):
            a, b = i * nm + k, i * nm + (k + 1) % nm
            F += [(a, b + nm, b), (a, a + nm, b + nm)]
            lam = 2 * math.pi * (k + 0.5) / nm
            v = math.cos(6 * lam + 1.8 * ph)
            val += [v, v]
    s0, s1 = len(V) - 2, len(V) - 1
    last = (nl - 2) * nm
    for k in range(nm):
        F.append((s0, k, (k + 1) % nm))
        F.append((s1, last + (k + 1) % nm, last + k))
        val += [1.0, 1.0]
    V, F = _orient(V, F)
    val = np.array(val)
    lit, dark = F[val > -0.35], F[val <= -0.35]
    return [dict(name='hair_bun', bone='head', color='hair', mesh=(V, lit)),
            dict(name='hair_bun_shadow', bone='head', color='hair_shadow', mesh=(V, dark))]


def hair_locks() -> list[dict]:
    """髪の房（2 周目）：額の生え際から頭の上・横を通って後ろのお団子へ流れる、面のはっきりした板。
    絵 trude_head_top・back・side_right：房は額の真ん中の分け目から左右へ分かれ、頭の上と横を後ろへ流れてお団子へ集まる。
    耳は見える（横の房は耳の上を通る）。耳の前に細い房が 1 本ずつ垂れる。
      ・帽子（髪の土台）を外形より 1.4cm 内にし（`hair.PARAMS.cap_inset_m`）、房が外の形を決める（ニコの 2 周目の作り）。
      ・道：頭の中心から見た根（生え際）→（経由の向き）→ 先（お団子の縁）の向きを大円でつなぎ、各点をその向きの帽子の面
        ＋浮きに置く（帽子に沿い、ねじれない）。耳の上を通る房は経由の向きで耳より上へ（耳を出す）。
      ・断面：峰・左右の縁・内の面の 6 角。厚みは幅と切り離して 1.2cm（1 周目は幅に比例して 3cm を超え、丸めた紙の塊に見えた）。
        峰の両側の 2 面は髪の色、縁と内の面は陰の色（照った面と陰の面の明るさの差）"""
    from scipy import ndimage as NDI

    from recon import hair as HR
    from recon import views as V
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    phi, lo, vox = np.asarray(d['phi'], np.float32), d['lo'], float(d['vox'])
    C = np.array(HR.HEAD_C, float)

    def inside(P):
        idx = ((P[:, [2, 0, 1]] - lo[[2, 0, 1]]) / vox - 0.5).T
        return NDI.map_coordinates(phi, idx, order=1, mode='constant', cval=-1.0) > 0

    def radial(dirs, r_max=0.40, step=0.0015):
        rs = np.arange(r_max, 0.0, -step)
        P = C[None, None] + rs[None, :, None] * dirs[:, None, :]
        ins = inside(P.reshape(-1, 3)).reshape(len(dirs), len(rs))
        k = np.argmax(ins, 1)
        return np.where(ins.any(1), rs[k], 0.10)

    def unit(v):
        v = np.asarray(v, float)
        return v / np.linalg.norm(v)

    def dir_at(th_deg, z, ref=0.1):
        th = math.radians(th_deg)
        return unit(np.array([math.sin(th) * ref, -math.cos(th) * ref, z - C[2]]))

    # 断面：(横 × 幅, 縦 × 厚み)。峰 → 本人の左の縁の上 → 縁の下 → 内の真ん中 → 右の縁の下 → 右の縁の上
    PX = [0.0, 1.0, 0.94, 0.0, -0.94, -1.0]
    PY = [1.0, 0.22, -0.22, -0.40, -0.22, 0.22]
    TOP_SEG = (0, 5)          # 峰の両側の面（髪の色）。ほかは陰の色
    n = 15
    tt = np.linspace(0.0, 1.0, n)

    def slerp_path(dirs_key, frac_key):
        """向きの列を大円でつなぐ（frac_key：各向きの道の上の割合）"""
        out = []
        for t in tt:
            j = min(int(np.searchsorted(frac_key, t, side='right')) - 1, len(dirs_key) - 2)
            u = (t - frac_key[j]) / (frac_key[j + 1] - frac_key[j])
            a, b = dirs_key[j], dirs_key[j + 1]
            om = math.acos(float(np.clip(np.dot(a, b), -1, 1)))
            so = math.sin(om) if om > 1e-4 else 1.0
            v = (math.sin((1 - u) * om) * a + math.sin(u * om) * b) / so if om > 1e-4 else a
            out.append(v / np.linalg.norm(v))
        return np.array(out)

    def centre_line(dkeys, lift, r_tip=None, thick=0.012, w_prof=None, sink=0.004, fkeys=None, r_max=0.40):
        """房の中心の線（帽子の面＋浮き）・厚み・幅の形"""
        dirs = slerp_path(dkeys, fkeys if fkeys is not None else np.linspace(0, 1, len(dkeys)))
        r = radial(dirs, r_max=r_max)
        r = NDI.gaussian_filter1d(r, 1.0, mode='nearest')
        wp = w_prof if w_prof is not None else np.interp(tt, [0, 0.10, 0.4, 0.8, 1.0], [0.45, 0.85, 1.0, 0.75, 0.10])
        th_ = thick * np.clip(wp * 1.2, 0.35, 1.0)
        rr = r + lift + 0.40 * th_ - sink * np.clip(1 - tt / 0.12, 0, 1)
        if r_tip is not None:      # 先はお団子へ
            f = np.clip((tt - 0.74) / 0.26, 0, 1) ** 1.5
            rr = rr * (1 - f) + r_tip * f
        return dirs, C + dirs * rr[:, None], th_, wp

    def ribbon(dirs, P, ww, th_):
        """中心の線に 6 角の断面を流した板。(頂点, 峰の両側の面, ほかの面)"""
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        N = dirs - (dirs * T).sum(1, keepdims=True) * T
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        B = np.cross(T, N)
        rings = np.stack([P + B * (ww * px)[:, None] + N * (th_ * py)[:, None] for px, py in zip(PX, PY)], 1)
        k = len(PX)
        Vs = np.concatenate([rings[:-1].reshape(-1, 3), P[-1:], P[:1] - T[:1] * 0.002])
        tip, root = (n - 1) * k, (n - 1) * k + 1
        F, seg = [], []
        for i in range(n - 2):
            for j in range(k):
                a0, a1 = i * k + j, i * k + (j + 1) % k
                F += [(a0, a0 + k, a1 + k), (a0, a1 + k, a1)]
                seg += [j, j]
        last = (n - 2) * k
        for j in range(k):
            F.append((last + j, tip, last + (j + 1) % k))
            F.append((root, (j + 1) % k, j))
            seg += [j, j]
        Vs, F = _orient(Vs, F)
        seg = np.array(seg)
        top = np.isin(seg, TOP_SEG)
        return Vs, F[top], F[~top]

    def band(dkeys, w, lift, r_tip=None, thick=0.012, w_prof=None, sink=0.004, fkeys=None, r_max=0.40):
        dirs, P, th_, wp = centre_line(dkeys, lift, r_tip, thick, w_prof, sink, fkeys, r_max)
        return ribbon(dirs, P, w * wp, th_)

    def add(name, V_, Ft, Fu):
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(V_, Ft)))
        out.append(dict(name='hair_' + name + '_u', bone='head', color='hair_shadow', mesh=(V_, Fu)))

    def hairline_z(th_deg):
        x = abs(math.sin(math.radians(th_deg))) * 0.11
        return float(np.interp(x, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]))

    def bun_edge(ang, k=0.82, fy=-0.55):
        a = math.radians(ang)
        return BUN_C + np.array([math.sin(a) * BUN_R[0] * k, BUN_R[1] * fy, math.cos(a) * BUN_R[2] * k])

    out = []
    # 額から後ろのお団子へ：(名前, 根の角度, 経由（角度, 高さ）, 先の角度（お団子の縁、0 = 上、+ = 本人の左）)。右から左の順
    # 真ん中の 2 本は根を ±9 度に離し、頭頂で外へ開いてから集まる（分け目の線が帽子の暗い色で見える）
    sweep = [('e_r', -77, (-102, 1.392), -102), ('s_r', -62, (-88, 1.43), -80), ('t_r', -45, (-66, 1.475), -58),
             ('f_r', -27, (-42, 1.515), -36), ('c_r', -9, (-14, 1.535), -14), ('c_l', 9, (14, 1.535), 14),
             ('f_l', 27, (42, 1.515), 36), ('t_l', 45, (66, 1.475), 58), ('s_l', 62, (88, 1.43), 80),
             ('e_l', 77, (102, 1.392), 102)]
    lines = []
    for name, th0, via, ang in sweep:
        d0 = dir_at(th0, hairline_z(th0) + 0.004)
        tip = bun_edge(ang, 0.55, -0.15)      # 先はお団子の中へ（縁に置くと先が浮いてとげに見えた）
        lines.append(centre_line([d0, dir_at(via[0], via[1]), unit(tip - C)], 0.002, r_tip=float(np.linalg.norm(tip - C)),
                                 fkeys=np.array([0.0, 0.42, 1.0]), sink=0.010))
    # 幅：となりの房の中心までの距離の 0.62 倍（となり合う房は縁で少し重なり、間が浅い谷になる。メロンの筋のように）。
    # 1 周目〜2 周目の初めは幅が一定で 4〜5 本が重なり、くしゃくしゃの紙に見えた
    for i, (name, *_r) in enumerate(sweep):
        dirs, P, th_, wp = lines[i]
        nb = [j for j in (i - 1, i + 1) if 0 <= j < len(sweep)]
        dist = np.min([np.linalg.norm(P - lines[j][1], axis=1) for j in nb], 0)
        hw = NDI.gaussian_filter1d(np.clip(0.62 * dist, 0.006, 0.040), 1.0, mode='nearest')
        hw = hw * np.interp(tt, [0, 0.10, 0.9, 1.0], [0.35, 1.0, 1.0, 0.55])   # 根は細く、帽子へ沈める（板の切り口を見せない）
        add(name, *ribbon(dirs, P, hw, th_))
    # 額の縁の房 ×2：分け目から左右へ生え際に沿って流れ、こめかみで耳の上を後ろへ回ってお団子へ（正面の絵：分け目から
    # 左右へなでつけた房が額の縁を作る）。ほかの房の根（板の切り口）を上から覆い、生え際の線をすっきりさせる
    for side, sx in ((1.0, 'l'), (-1.0, 'r')):
        tip = bun_edge(side * 96, 0.55, -0.15)
        keys = [dir_at(side * 3, hairline_z(3) + 0.010), dir_at(side * 38, hairline_z(38) + 0.012),
                dir_at(side * 72, hairline_z(72) + 0.022), dir_at(side * 100, 1.405), unit(tip - C)]
        Vm, Ft, Fu = band(keys, 0.017, 0.005, r_tip=float(np.linalg.norm(tip - C)), sink=0.006,
                          fkeys=np.array([0.0, 0.16, 0.36, 0.58, 1.0]),
                          w_prof=np.interp(tt, [0, 0.08, 0.5, 0.85, 1.0], [0.35, 1.0, 1.0, 0.8, 0.4]))
        add('front_' + sx, Vm, Ft, Fu)
    # 頭頂の後ろからお団子の上へ放射状に集まる房（背面の絵の扇）。真ん中の 2 本の房の間を埋める
    for name, th0, z0, ang, w in (('b_l', 172, 1.54, 7, 0.024), ('b_r', -172, 1.54, -7, 0.024), ('b_c', 180, 1.556, 0, 0.020)):
        tip = bun_edge(ang, 0.55, -0.15)
        Vm, Ft, Fu = band([dir_at(th0, z0), unit(tip - C)], w, 0.0015, r_tip=float(np.linalg.norm(tip - C)),
                          w_prof=np.interp(tt, [0, 0.15, 0.5, 1.0], [0.6, 0.9, 1.0, 0.35]))
        add(name, Vm, Ft, Fu)
    # えり足からお団子の下へ上がる房（後ろの低い所）。探す半径を頭の大きさに限る（下向きの道が背中の面に届き、首から離れた板になった）
    for name, th0, ang, w in (('n_l', 140, 140, 0.040), ('n_r', -140, -140, 0.040), ('n_c', 180, 180, 0.038)):
        tip = bun_edge(ang, 0.75, -0.40)
        Vm, Ft, Fu = band([dir_at(th0, 1.262), unit(tip - C)], w, 0.002, r_tip=float(np.linalg.norm(tip - C)), r_max=0.15)
        add(name, Vm, Ft, Fu)
    # 耳の前の細い房 ×2（こめかみの上から耳の前を下へ、あごの高さで細る。絵 trude_head_side_right・turnaround の正面）。
    # 探す半径を頭の大きさに限る（2 周目の初め：下向きの道が肩の面まで届き、肩まで垂れる長いひげになった）
    for side, sx in ((1.0, 'l'), (-1.0, 'r')):
        Vm, Ft, Fu = band([dir_at(side * 64, 1.44), dir_at(side * 75, 1.37), dir_at(side * 80, 1.30)], 0.013, 0.004,
                          thick=0.007, sink=0.002, r_max=0.15,
                          w_prof=np.interp(tt, [0, 0.2, 0.6, 1.0], [0.8, 1.0, 0.75, 0.15]))
        add('side_' + sx, Vm, Ft, Fu)
    return out


def pieces() -> list[dict]:
    P = []
    P += capelet()
    P += collar_sleeves()
    P += belt_items()
    P += skirt()
    P += apron()
    P += legs()
    P += bun()
    P += hair_locks()
    return P


# ---------------------------------------------------------------- 決まりの塗り（cover_body から）

def hem_z(th: np.ndarray) -> np.ndarray:
    """スカートの裾の高さ（正面からの角度 th、度）。前 0.222、横 0.245、後ろ 0.235"""
    a = np.abs(th)
    return np.interp(a, [0, 45, 90, 135, 180], [0.222, 0.232, 0.245, 0.240, 0.235])


# 裾の補修布（正面からの角度の範囲（度）・高さの範囲）。絵の正面・左右の真横・背面・左前 45 度
PATCHES = [(-62.0, -36.0, 0.330, 0.455), (46.0, 62.0, 0.305, 0.395), (-118.0, -98.0, 0.330, 0.480),
           (100.0, 116.0, 0.395, 0.470), (150.0, 166.0, 0.365, 0.470), (-166.0, -152.0, 0.380, 0.455)]


def body_rules(pos: np.ndarray, col: np.ndarray, lab: np.ndarray, under: np.ndarray, ins: dict, stats: dict) -> None:
    """ベルトより上の胴・腕は生成り、袖口の帯より先の前腕は石墨、首は石墨、ベルトより下は茶のスカート（補修布は薄茶）、
    裾より下は石墨の靴下（裾の内側は暗い茶）。頭と首の帯は形の場（hair.part_fields_at）で髪・肌・耳を決める"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    free = under < 0
    r_neck = np.hypot(x - X0, y)
    head = (z > NECK_TOP + 0.01) | ((z > 1.19) & (r_neck > 0.075) & (y < 0.0))
    th = np.degrees(np.arctan2(x - X0, -y))
    # 上着（胴・腕）：ベルトの上の縁より上
    blouse = free & ~head & (z >= BELT_Z[0])
    under[blouse] = NAMES.index('ivory')
    # 前腕：袖口の帯より先は石墨の内袖
    cuff = np.zeros(len(pos), bool)
    for side in (1.0, -1.0):
        S, E = np.array(jp('forearm', side)), np.array(jp('hand', side))
        d = (E - S) / np.linalg.norm(E - S)
        t = (pos - S) @ d
        rr = np.linalg.norm((pos - S) - np.outer(t, d), axis=1)
        cuff |= free & (side * x > 0.2) & (rr < 0.13) & (t > (SLEEVE_T[0] + SLEEVE_T[1]) / 2)
    under[cuff] = NAMES.index('graphite')
    # 首（立ち襟の下〜肩掛けの中）：石墨
    # 肩掛けの立った襟の内（襟と立ち襟の間に見える体の上の面）も石墨（生成りと肌の斑点に見えた）
    neck = free & ~head & (((z > 1.10) & ((r_neck < 0.085) | ((r_neck < 0.115) & (np.abs(th) < 60.0))))
                          | ((z > 1.13) & (r_neck < 0.16)))
    under[neck] = NAMES.index('graphite')
    # スカート（ベルトより下、裾まで）
    hz = hem_z(th)
    hand = (np.abs(x) > 0.36) & (z > 0.55)
    skirt = free & (z < BELT_Z[0]) & (z >= hz) & ~hand & ~cuff
    under[skirt] = NAMES.index('brown')
    patch = np.zeros(len(pos), bool)
    for a0, a1, z0, z1 in PATCHES:
        patch |= skirt & (th > a0) & (th < a1) & (z > z0) & (z < z1)
    under[patch] = NAMES.index('patch')
    # 裾より下：脚は石墨の靴下、裾の内側（脚の軸から離れた面）は暗い茶
    low = free & (z < hz)
    under[low] = NAMES.index('graphite')
    rl = np.hypot(np.abs(x) - 0.125, y)
    under[low & (rl > 0.075) & (z > 0.15)] = NAMES.index('brown_dark')
    # 頭と首の帯：形の場で（ニコと同じ作り）
    from recon import hair as HR
    hb = (z > 1.15) & (z < 1.62) & (np.hypot(x - X0, y - 0.01) < np.where(z > 1.21, 0.30, 0.16))
    hi = np.nonzero(hb)[0]
    if len(hi):
        f = HR.part_fields_at(pos[hi], x_half=0.30, z0=1.13)
        xh, yh, zh = x[hi], y[hi], z[hi]
        ear = f['ear'] > -0.002
        hair = (f['hair'] > -0.004) & ~ear
        ax = np.abs(xh - X0)
        th_f = np.degrees(np.arctan2(ax, -(yh - 0.01)))
        flush = (f['hair'] - f['skin']) < 0.009
        line = np.where(th_f < 72.0, np.interp(ax, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]),
                        np.where(th_f < 112.0, 1.335, 1.25))
        hair &= ~(flush & (zh < line))
        lab_h = np.full(len(hi), NAMES.index('skin'))
        # 帽子（髪の土台）は内側の暗い髪（房のすき間が陰に見え、房の形が分かる）。生え際の 2.5cm 上までは房と同じ色
        # （ニコは帽子の縁が額の帯に見えた）
        near_line = (th_f < 80.0) & (zh < np.interp(ax, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]) + 0.025)
        lab_h[hair] = NAMES.index('hair_dark')
        lab_h[hair & near_line] = NAMES.index('hair')
        lab_h[ear] = NAMES.index('skin')
        ctop = np.where(yh < 0, COLLAR_T1[0], COLLAR_T1[1])
        lab_h[(zh < ctop) & ~hair] = NAMES.index('graphite')
        keep = under[hi] >= 0
        under[hi[~keep]] = lab_h[~keep]
    stats['trude_rule_texels'] = int((blouse | cuff | neck | skirt | low).sum())


# ---------------------------------------------------------------- 杖と、それを握る右手（ai_character.py の HAND['GRIP']）

# 杖（絵 cane_front・side・top・3q）：まっすぐな焦げ茶の木の軸、T 字の横棒の握り（幅 18cm）、握りとの継ぎ目と先の石突きは真鍮。
# spec の全長は 92cm だが、140cm のトルーデでは握りが肩の高さ（0.92m、肩 0.95m）になり、trude_grip.png のように上から
# 握って寄りかかれない。杖の普通の長さ（手を下ろした手首の高さ、身長の約 0.49 倍）の全長 68cm にした（結果の文書 3 章）
CANE_LEN = 0.68 / 0.9032       # 再構築の座標（身長 1.55m）。骨付けの段で 1.40m へ 0.903 倍
CANE_BAR_HALF = 0.09 / 0.9032  # 横棒の半分の長さ
CANE_SHAFT_R = 0.0105
GRIP_CURL = (50.0, 62.0, 46.0)  # 握る指の節ごとの曲げ（度）


def _cyl(a, b, r, n=12, caps=True, round_end=0.0):
    """a → b の円柱（端は平ら。round_end > 0 は端の縁を面取り）"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.linalg.norm(d)
    d /= L
    e0 = np.cross(d, [0.0, 0.0, 1.0] if abs(d[2]) < 0.9 else [1.0, 0.0, 0.0])
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(d, e0)
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(ang)[:, None] * e0 + np.sin(ang)[:, None] * e1
    prof = [(0.0, r - round_end), (round_end, r), (L - round_end, r), (L, r - round_end)] if round_end > 0 \
        else [(0.0, r), (L, r)]
    V = np.concatenate([a + d * t + circ * rr for t, rr in prof] + [[a, b]])
    k = len(prof)
    F = []
    for j in range(k - 1):
        for i in range(n):
            i2 = (i + 1) % n
            F += [(j * n + i, (j + 1) * n + i2, (j + 1) * n + i), (j * n + i, j * n + i2, (j + 1) * n + i2)]
    ca, cb = k * n, k * n + 1
    for i in range(n):
        i2 = (i + 1) % n
        F += [(ca, i, i2), (cb, (k - 1) * n + i2, (k - 1) * n + i)]
    return _orient(V, F)


def grip_prop() -> dict:
    """杖（手の座標：+X 指の向き、+Y 掌の側、+Z 親指の側。原点は手首）。横棒は指の付け根の列（Z）に沿って掌の下に置き、
    曲げた中指の 3 つの節と掌の面からの距離がそろう所を中心にする。軸は掌の側（+Y）へまっすぐ下りる"""
    # 中指の節（hand.build_open と同じ作り）
    _, z_m, x_m, r_m, L_m, _ = HAND['OPEN_FINGERS'][1]
    J = [np.array([x_m, 0.001])]
    ang = 0.0
    for L, c in zip(L_m, GRIP_CURL):
        ang += math.radians(c)
        J.append(J[-1] + L * np.array([math.cos(ang), math.sin(ang)]))
    palm_y = HAND['PALM_HALF_T']

    def seg_d(p, a, b):
        ab = b - a
        t = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0, 1)
        return np.linalg.norm(p - (a + t * ab))
    best = None
    for cx in np.arange(0.05, 0.10, 0.0005):
        for cy in np.arange(0.015, 0.045, 0.0005):
            p = np.array([cx, cy])
            ds = [seg_d(p, J[k], J[k + 1]) - r_m for k in range(3)] + [cy - palm_y]
            R = float(np.mean(ds))
            err = max(abs(d - R) for d in ds)
            if R > 0.008 and (best is None or err < best[0]):
                best = (err, cx, cy, R)
    _, cx, cy, R = best
    R = max(R - 0.0008, 0.010)
    parts = []
    # 横棒（Z に沿う）・継ぎ目の真鍮・軸・石突き
    parts.append(('wood', _cyl((cx, cy, -CANE_BAR_HALF), (cx, cy, CANE_BAR_HALF), R, n=14, round_end=0.004)))
    y_c0, y_c1 = cy + R * 0.55, cy + R + 0.020
    parts.append(('brass', _cyl((cx, y_c0, 0.0), (cx, y_c1, 0.0), CANE_SHAFT_R + 0.0025, n=14, round_end=0.0015)))
    y_tip = cy - R + CANE_LEN
    parts.append(('wood', _cyl((cx, y_c1 - 0.002, 0.0), (cx, y_tip - 0.028, 0.0), CANE_SHAFT_R, n=12)))
    parts.append(('brass', _cyl((cx, y_tip - 0.030, 0.0), (cx, y_tip, 0.0), CANE_SHAFT_R + 0.0012, n=12,
                                round_end=0.002)))
    V, F, col = [], [], []
    off = 0
    for c, (v, f) in parts:
        V.append(v)
        F.append(np.asarray(f) + off)
        col += [c] * len(f)
        off += len(v)
    return {'V': np.concatenate(V), 'F': np.concatenate(F), 'color': col,
            'points': {'bar_c': [cx, cy, 0.0], 'tip': [cx, y_tip, 0.0], 'bar_axis_end': [cx, cy, 1.0],
                       'bar_r': [R, 0.0, 0.0]}}


# ---------------------------------------------------------------- 手の部品（hand.py）

# 両手とも素手（hand.build_open）。絵 trude_hands.png：細めの大人の手。再構築の座標で手首から指先まで約 15cm
_S, _R = 1.0, 1.05
HAND = dict(
    GLOVE=None,
    LID='graphite',
    OPEN_FINGERS=[(n, z * _S, x * _S, r * _R, tuple(v * _S for v in L), fan) for n, z, x, r, L, fan in (
        ('index', 0.0255, 0.068, 0.0078, (0.034, 0.022, 0.018), 6.0),
        ('middle', 0.0085, 0.071, 0.0081, (0.037, 0.024, 0.019), 1.0),
        ('ring', -0.0085, 0.068, 0.0076, (0.034, 0.022, 0.018), -4.0),
        ('pinky', -0.0240, 0.061, 0.0066, (0.027, 0.018, 0.015), -9.0))],
    OPEN_CURL=(14.0, 20.0, 14.0),
    CUFF_LID=(-0.012, 0.006),
    OPEN_THUMB=dict(base=(0.026, 0.008, 0.024), r=0.0086 * _R, lens=(0.033, 0.028, 0.023), out_deg=22.0,
                    palm_deg=34.0, curl=(8.0, 12.0, 10.0)),
    PALM_HALF_T=0.0115 * _R,
    PALM_WRIST=(0.002, 0.0, 0.016, 0.029),
    PALM_X=(0.012, 0.045),
    THENAR=((0.029, 0.007, 0.023), 0.014),
    HYPOTHENAR=((0.035, 0.005, -0.021), 0.0125),
    LEFT_HAND_CUT=-0.004,
    LEFT_HAND_RAMP=(-0.014, 0.006),
)
# 右手：杖の横棒を上から握る（trude_grip.png：指は横棒の前を回って下へ巻き、親指は反対の側）。ai_character.py が
# 右の開いた手を、この曲げの値で作り、杖（grip_prop）を同じ部品に足す
HAND['GRIP'] = dict(
    hand={'OPEN_CURL': GRIP_CURL,
          'OPEN_THUMB': dict(HAND['OPEN_THUMB'], out_deg=14.0, palm_deg=52.0, curl=(12.0, 26.0, 22.0))},
    prop=grip_prop)
