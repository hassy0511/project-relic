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
    'rust': '#B65A40',        # 肩掛け（赤錆の厚布）
    'rust_line': '#6E4A3C',   # 肩掛けの裾の上の線（暗い茶）
    'ivory': '#EEDDBF',       # 上着・前掛け（生成りの木綿）
    'brown': '#6A4935',       # スカート（焦げ茶の厚布）
    'brown_dark': '#4C3427',  # スカートの裾の内側
    'leather': '#4D3629',     # ベルト・腰の袋（革）
    'graphite': '#454441',    # 立ち襟・内袖・靴下（石墨）
    'brass': '#B48D4C',       # 留め具・ベルトの輪・靴の留め具・杖の金具（くすんだ真鍮）
    'trim': '#C09858',        # 袖口・前掛けの裾の帯（黄土の布）
    'skin': '#E7B58D',
    'hair': '#D3C9C1',        # 灰白の髪
    'hair_dark': '#ADA29A',   # 髪の土台（房のすき間に見える内側の髪）
    'boot': '#6B4A36',        # 靴の胴（茶の革）
    'boot_light': '#86603F',  # 靴の爪先
    'sole': '#3A3330',        # 靴底・かかと
    'patch': '#9F7853',       # スカートの補修布
    'wood': '#5A3829',        # 杖の木の軸・握り
}
NAMES = list(PALETTE)
CELLS = 24

X0 = 0.0        # 顔・首の左右の中心

# A ポーズの関節（chars/trude.json の joints.ART_XZ と同じ x・z。y は真横の絵）
J = {
    'upper_arm': (0.15, 0.0, 1.05), 'forearm': (0.285, 0.02, 0.875), 'hand': (0.40, 0.03, 0.735),
    'hand_end': (0.44, 0.03, 0.63), 'thigh': (0.09, 0.0, 0.66), 'shin': (0.12, 0.0, 0.37),
    'foot': (0.125, 0.0, 0.09),
}
FOLLOW_BODY = ('turtleneck', 'belt')
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
    return np.interp(a, [0, 20, 45, 90, 135, 180], [1.135, 1.165, 1.198, 1.218, 1.232, 1.236])


def _cape_hem(th):
    c = np.cos(th)
    return 0.928 + 0.018 * np.clip(c, 0, None) ** 2


def _cape_open(z):
    """前の開き（留め具より下）の半分の角度"""
    f = np.clip((1.085 - z) / (1.085 - 0.93), 0, 1)
    return np.radians(26.0) * f ** 0.85


CAPE_VS = np.unique(np.concatenate([np.linspace(0.0, 1.0, 24), [0.875, 0.93]]))   # 裾の上の線の行を含む


def cape_surface(nu=96, vs=CAPE_VS):
    """肩掛けの外の面の格子 (nu, nv, 3)：u は前の開きの本人の左の縁 → 後ろ → 右の縁、v は上の縁 → 裾"""
    us = np.linspace(0.0, 1.0, nu)
    nv = len(vs)
    P = np.zeros((nu, nv, 3))
    TH = np.zeros((nu, nv))
    for j, v in enumerate(vs):
        # 開きの角度はその行の前の高さで決める
        z_est = 1.135 + (0.946 - 1.135) * (v ** 0.92)
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
    th = TH.ravel()
    z = P[..., 2].ravel()
    rb = outer_r(th, z, 0.0)
    rc = np.hypot(P[..., 0].ravel() - X0, P[..., 1].ravel())
    push = np.clip(rb + 0.006 - rc, 0, 0.05).reshape(nu, nv)
    from scipy import ndimage as NDI
    push = NDI.grey_dilation(push, size=(5, 3))
    push = NDI.gaussian_filter(push, (2.0, 1.0), mode='nearest')
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
                  rmax=0.3, n_ring=120, sink=0.014))
    for xc in (-0.075, 0.075):
        P.append(dict(name=f'belt_loop{"L" if xc > 0 else "R"}', bone='hips', color='brass', frame=fw,
                      outline=octagon(xc - 0.010, xc + 0.010, BELT_Z[0] - 0.008, BELT_Z[1] + 0.006, 0.003),
                      off=0.018, thick=0.005, bevel=0.0015, rmax=0.3, h=0.004))
    # 腰の袋 ×2（箱。ベルトの下、両脇の少し前）
    for name, ang in (('pouch.R', -82.0), ('pouch.L', 82.0)):
        P.append(dict(name=name, bone='hips', color='leather', box=True, frame=fw, ang=ang, zc=0.775,
                      size=(0.066, 0.032, 0.128), rmax=0.35))
    return P


def apron() -> list[dict]:
    """前掛け（前・後ろ）：ベルトの下から垂れる板（高さの断面を積む。上は体に沿い、下へ行くほど離す）と、裾の金の帯"""
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
                yb = min(body_front_y(q, x0, x1) for q in zz)
            else:
                yb = max(body_back_y(q, x0, x1) for q in zz)
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
    P = []
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        P += boot_pieces(side, sx)
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

BUN_C = np.array([X0, 0.180, 1.312])     # お団子の中心（右真横・背面の絵）
BUN_R = (0.064, 0.050, 0.058)            # 半径（左右・前後・上下）


def bun() -> list[dict]:
    """後ろの低いお団子：房が渦に巻いた丸い塊（経緯の格子の球を、渦の筋でふくらませる。面のはっきりした低い多面体）"""
    nl, nm = 9, 14
    V = []
    for i in range(1, nl):
        ph = math.pi * i / nl - math.pi / 2          # 緯度（−90 = 前の付け根、+90 = 後ろの端）
        for k in range(nm):
            lam = 2 * math.pi * k / nm
            w = 1.0 + 0.10 * math.cos(6 * lam + 1.6 * ph) * math.cos(ph)
            cx = math.cos(ph) * math.cos(lam) * BUN_R[0] * w
            cz = math.cos(ph) * math.sin(lam) * BUN_R[2] * w
            cy = math.sin(ph) * BUN_R[1] * (1.0 + 0.05 * math.cos(6 * lam))
            V.append(BUN_C + np.array([cx, cy, cz]))
    V.append(BUN_C + np.array([0.0, -BUN_R[1], 0.0]))
    V.append(BUN_C + np.array([0.0, BUN_R[1] * 1.04, 0.0]))
    V = np.array(V)
    F = []
    for i in range(nl - 2):
        for k in range(nm):
            a, b = i * nm + k, i * nm + (k + 1) % nm
            F += [(a, b + nm, b), (a, a + nm, b + nm)]
    s0, s1 = len(V) - 2, len(V) - 1
    last = (nl - 2) * nm
    for k in range(nm):
        F.append((s0, k, (k + 1) % nm))
        F.append((s1, last + (k + 1) % nm, last + k))
    return [dict(name='hair_bun', bone='head', color='hair', mesh=_orient(V, F))]


def hair_locks() -> list[dict]:
    """髪の房：額の生え際から頭の上・横を通って後ろのお団子へ流れる、面のはっきりした厚い板（ニコの 2 周目の作り）。
    絵 trude_head_top：房は前の生え際から放射状に出て、後ろのお団子へ集まる。trude_face_front：額の真ん中で左右に分かれ、
    こめかみの房は耳の上を後ろへ。耳は見える（横の髪は耳の上と後ろ）。耳の前に細い房が 1 本ずつ垂れる。
      ・道：根（生え際の少し上、帽子の中へ沈める）→ 中（根とお団子の向きの間の帽子の面の外）→ 先（お団子の縁）。
        どの点も帽子の面より外へ押し出す（頭の中心からの向きで測る）。
      ・断面：峰と左右の縁・内の面の 6 角（峰の両側は 20 度の平らな面）。根で細く、中ほどで最も広く、先へ細る"""
    from scipy import ndimage as NDI

    from recon import hair as HR
    from recon import views as V
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    phi, lo, vox = np.asarray(d['phi'], np.float32), d['lo'], float(d['vox'])
    C = np.array(HR.HEAD_C, float)

    def inside(P):
        idx = ((P[:, [2, 0, 1]] - lo[[2, 0, 1]]) / vox - 0.5).T
        return NDI.map_coordinates(phi, idx, order=1, mode='constant', cval=-1.0) > 0

    def radial(dirs, r_max=0.40, step=0.002):
        rs = np.arange(r_max, 0.0, -step)
        P = C[None, None] + rs[None, :, None] * dirs[:, None, :]
        ins = inside(P.reshape(-1, 3)).reshape(len(dirs), len(rs))
        k = np.argmax(ins, 1)
        return np.where(ins.any(1), rs[k], 0.10)

    prof = [(0.0, 0.40), (1.0, 0.07), (0.94, -0.07), (0.0, -0.22), (-0.94, -0.07), (-1.0, 0.07)]
    widths = np.array([0.40, 0.70, 0.88, 0.97, 1.0, 1.0, 0.97, 0.90, 0.80, 0.66, 0.48, 0.0])
    n = len(widths)

    def plank(P, w, lift_min, sink_root=0.010, bun_tip=False):
        t = np.linspace(0.0, 1.0, n)
        dv = P - C
        rr = np.linalg.norm(dv, axis=1)
        dn = dv / rr[:, None]
        rs = radial(dn)
        need = rs + lift_min + 0.20 * w * widths - np.where(t < 0.01, sink_root, 0.0)
        if bun_tip:       # 先はお団子の中へ（押し出さない）
            need = np.where(t > 0.85, rr, need)
        P = C + dn * np.maximum(rr, need)[:, None]
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        N = (P - C) - ((P - C) * T).sum(1, keepdims=True) * T
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        B = np.cross(T, N)
        ww = w * widths
        rings = np.stack([P + B * (ww * px)[:, None] + N * (ww * py)[:, None] for px, py in prof], 1)
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

    def bezier(pts):
        """制御点の列（3〜4 点）を通るなめらかな道（Catmull-Rom を n 点に）"""
        pts = np.asarray(pts, float)
        seg = np.linspace(0, len(pts) - 1, n)
        out = []
        for s in seg:
            i = min(int(s), len(pts) - 2)
            u = s - i
            p0 = pts[max(i - 1, 0)]
            p1, p2 = pts[i], pts[i + 1]
            p3 = pts[min(i + 2, len(pts) - 1)]
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
        return np.array(out)

    def on_cap(th_deg, z, lift):
        """正面からの角度 th・高さ z の、頭の中心から見た帽子の面の外 lift の点"""
        th = math.radians(th_deg)
        dvec = np.array([math.sin(th), -math.cos(th), 0.0]) * 0.1 + np.array([0, 0, z - C[2]])
        dvec /= np.linalg.norm(dvec)
        r = radial(dvec[None])[0]
        return C + dvec * (r + lift)

    def hairline_z(th_deg):
        x = abs(math.sin(math.radians(th_deg))) * 0.11
        return float(np.interp(x, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]))

    out = []
    # 額から後ろへ流れる房：(名前, 根の角度, 根の高さの上げ, 中の角度, 中の高さ, 先の角度（お団子のまわり）, 先の高さ, 幅, 浮き)
    sweep = [
        ('c_r', -6, 0.006, -10, 1.545, -12, 1.355, 0.070, 0.010),
        ('c_l', 6, 0.006, 10, 1.545, 12, 1.355, 0.070, 0.010),
        ('f_r', -24, 0.006, -36, 1.525, -38, 1.345, 0.072, 0.010),
        ('f_l', 24, 0.006, 36, 1.525, 38, 1.345, 0.072, 0.010),
        ('t_r', -44, 0.004, -64, 1.48, -70, 1.330, 0.074, 0.012),
        ('t_l', 44, 0.004, 64, 1.48, 70, 1.330, 0.074, 0.012),
        ('s_r', -64, 0.000, -95, 1.42, -105, 1.315, 0.072, 0.012),
        ('s_l', 64, 0.000, 95, 1.42, 105, 1.315, 0.072, 0.012),
        ('e_r', -78, 0.000, -112, 1.37, -122, 1.300, 0.066, 0.010),
        ('e_l', 78, 0.000, 112, 1.37, 122, 1.300, 0.066, 0.010),
    ]
    bun_front = BUN_C + np.array([0.0, -0.030, 0.0])
    for name, th0, dz0, thm, zm, tht, zt, w, lift in sweep:
        z0 = hairline_z(th0) + 0.010 + dz0
        R0 = on_cap(th0, z0, -0.004)
        M = on_cap(thm, zm, lift + 0.2 * w)
        # 先：お団子の縁（お団子の中心から、先の角度の向きへ半径の 8 割）
        tv = np.array([math.sin(math.radians(tht)) * 0.9, 0.0, (zt - BUN_C[2]) / 0.06])
        tv[0] = np.clip(tv[0], -0.95, 0.95)
        tv /= max(np.linalg.norm(tv), 1e-6)
        T2 = bun_front + np.array([tv[0] * BUN_R[0] * 0.85, 0.0, tv[2] * BUN_R[2] * 0.85])
        # 中と先の間：後頭部の面（先の角度・中と先の間の高さ）
        M2 = on_cap((thm + tht) / 2 if abs(tht) < 150 else thm, (zm + zt) / 2 + 0.02, lift + 0.15 * w)
        Pth = bezier([R0, M, M2, T2])
        Vm, Fm = plank(Pth, w, lift, bun_tip=True)
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(Vm, Fm)))
    # 頭頂から後ろのお団子へ（上の房）と、えり足からお団子へ上がる房
    for name, R0, M, T2, w, lift in (
            ('crown', on_cap(0, 1.548, -0.004), on_cap(180, 1.47, 0.012), BUN_C + [0.0, -0.02, 0.045], 0.07, 0.010),
            ('nape_r', on_cap(-150, 1.255, -0.004), on_cap(-160, 1.285, 0.008), BUN_C + [-0.035, -0.025, -0.03], 0.055, 0.006),
            ('nape_l', on_cap(150, 1.255, -0.004), on_cap(160, 1.285, 0.008), BUN_C + [0.035, -0.025, -0.03], 0.055, 0.006),
            ('nape_c', on_cap(180, 1.245, -0.004), on_cap(180, 1.27, 0.006), BUN_C + [0.0, -0.02, -0.045], 0.05, 0.006)):
        Vm, Fm = plank(bezier([R0, M, T2]), w, lift, bun_tip=True)
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(Vm, Fm)))
    # 耳の前の細い房 ×2（こめかみから下へ、ほおの横で細る）
    for side, sx in ((1.0, 'l'), (-1.0, 'r')):
        R0 = on_cap(side * 70, 1.395, -0.002)
        M = on_cap(side * 76, 1.33, 0.004)
        T2 = on_cap(side * 74, 1.265, 0.003)
        Vm, Fm = plank(bezier([R0, M, T2]), 0.026, 0.003, sink_root=0.004)
        out.append(dict(name='hair_side_' + sx, bone='head', color='hair', mesh=(Vm, Fm)))
    return out


def pieces() -> list[dict]:
    P = []
    P += capelet()
    P += collar_sleeves()
    P += belt_items()
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
    head = (z > NECK_TOP + 0.01) | ((z > 1.17) & (r_neck > 0.075) & (y < 0.0))
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
    neck = free & ~head & (z > 1.10) & (r_neck < 0.085)
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
    hb = (z > 1.15) & (z < 1.62) & (np.hypot(x - X0, y - 0.01) < np.where(z > 1.21, 0.30, 0.10))
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
        lab_h[hair] = NAMES.index('hair_dark')
        lab_h[ear] = NAMES.index('skin')
        ctop = np.where(yh < 0, COLLAR_T1[0], COLLAR_T1[1])
        lab_h[(zh < ctop) & ~hair] = NAMES.index('graphite')
        keep = under[hi] >= 0
        under[hi[~keep]] = lab_h[~keep]
    stats['trude_rule_texels'] = int((blouse | cuff | neck | skirt | low).sum())


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
