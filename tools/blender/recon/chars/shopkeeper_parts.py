"""雑貨屋の店主（shopkeeper）の服の部品と塗りの決まり（costume.py が読み込む。書式は chars/nico_parts.py と同じ）。

部品の表：docs/art_orders/W2_店主3D化の結果.md の 1 章。寸法は calib.json のカメラで絵（W2-01 の shopkeeper_*.png）に
1cm の格子を重ねて読んだ（再構築の座標：身長 1.55m。本来の 1.60m へは骨付けの段で 1.032 倍）。本人の左 = +X、正面 = −Y。
  立ち襟（生成り、上の縁は焦げ茶の線、前の真鍮の留め）・肘の革の帯 ×2（鋲）・袖の折り返し ×2・手首の帯 ×2（石墨）・
  前掛けの胸当て・肩ひも ×2・肩ひもの留め金 ×2・腰の帯・背中の蝶結び（結び目・輪 ×2・垂れ ×2）・前掛けの前の布・
  後ろの布 ×2・ポケット ×2（蓋・鋲）・長いスカート（中が空の殻）・靴 ×2（底・胴・爪先・折り返し・鋲）・
  髪（帽子は形の段、お団子の房 9 個・頭の房・前髪・顔の横の房・えり足の房）。手は hand.py の開いた手（素手、肌）。
体の土台は、正面と真横の絵のスカートの範囲を脚の外形に置き換えて作った（build/shopkeeper/tools/prep_src.py）。
スカート・前掛けは体の面（形の段のメッシュ）から半径を測り、体より外に置く。待機だけの住人なので hips に剛体。
塗りの決まり（body_rules）：胴の上はブラウスの生成り（胸当て・肩ひもの下は前掛けの色）、肘の帯までの腕は生成りの袖、
その先は肌、スカートの下の脚は肌（すねが 2cm 見える）、スカートの中の脚・腰は焦げ茶、首は肌、頭は形の場。
"""
from __future__ import annotations

import math
import os

import numpy as np

# 色は spec_townsfolk_3d.md の色見本を基に、絵の平らに照らされた所の中央値（build/shopkeeper/tools/colors.py）へ寄せた
PALETTE = {
    'rust': '#96503A',       # 前掛け・腰の帯・蝶結び（spec #B75B43、絵 #B85838〜#BD5C3A。確認ページで明るい橙に見えたので明るさ・彩度を下げた）
    'rust_dark': '#844432',  # ポケットの袋（前掛けと同じ色では確認ページで輪郭が消えた。絵はポケットの縁に陰）
    'ivory': '#EEDCC0',      # ブラウス・立ち襟（spec #F3E9D2 は描画で白に見える。絵 #F8DFBB〜#FBE3C6）
    'skirt': '#62422F',      # スカート（spec #594333、絵 #68452E）
    'leather': '#6A4530',    # 肘の革の帯（絵 #794A31）
    'band': '#4B423E',       # 手首の帯（spec #444641、絵 #52433F〜#594940）
    'brass': '#B08D4C',      # 鋲・留め金・襟の留め
    'skin': '#E7B58D',
    'hair': '#66402F',       # 焦げ茶の髪（spec #594333 より赤い。絵の中央値）
    'hair_dark': '#4F3125',  # 帽子の下の縁（房のすき間の内側の髪）
    'trim': '#5A4034',       # 立ち襟の上の縁の線
    'boot': '#4A3F3A',       # 靴の胴・折り返し
    'toe': '#6E4E3C',        # 靴の爪先（茶）
    'sole': '#2F2825',       # 靴底・かかと
    'skirt_in': '#45301F',   # スカートの内側の面（下から見える）
    'strap_dark': '#3F3632',  # 留め金の中の暗い帯
}
NAMES = list(PALETTE)
CELLS = 16

X0 = 0.0105     # 顔・首の左右の中心（顔の絵の照合から）
CY_NECK = -0.014

# A ポーズの関節（chars/shopkeeper.json の joints.ART_XZ と同じ x・z。y は形の段のメッシュの腕の中心）
J = {
    'upper_arm': (0.165, 0.0, 1.10), 'forearm': (0.278, 0.025, 0.935), 'hand': (0.362, 0.023, 0.785),
    'hand_end': (0.41, 0.024, 0.648), 'thigh': (0.085, 0.013, 0.76), 'shin': (0.13, 0.015, 0.45),
    'foot': (0.153, 0.012, 0.085),
}
FOLLOW_BODY = ('collar', 'collar_trim', 'bib', 'strap.L', 'strap.R')
FOLLOW_TORSO_ONLY = ('collar', 'collar_trim', 'bib', 'strap.L', 'strap.R')
BOX_RULES: list = []

WAIST = (0.905, 0.955)          # 腰の帯（前掛けの幅広の紐）の下・上
SKIRT_TOP = 0.940               # スカートの上の端（腰の帯の下）
HEM = (0.226, 0.262)            # スカートの裾：前・横〜後ろ
APRON_BOT = 0.392               # 前掛けの前の布の下の縁
BACK_BOT = 0.420                # 後ろの布の下の縁
BIB_TOP = 1.105                 # 胸当ての上の縁
COLLAR_Z = (1.168, 1.225)       # 立ち襟の前の下・上（後ろは 1.244 まで）。2 周目に 7mm 上げた：上の縁の内に首の凸凹が見えた
NECK_TOP = 1.235                # 首の上（あごの下）
ELBOW_T = (0.148, 0.192, 0.214)  # 肘の帯の上・下、袖の折り返しの下（上腕の軸に沿った肩からの長さ）
WRIST_T = (0.112, 0.178)        # 手首の帯（前腕の軸に沿った肘からの長さ）
LEG_SKIN_Z = 0.245              # これより下（スカートの下）の脚は肌
# 顔のまわりの髪の塗りの下の線（|x − X0| → z）。正面の絵の生え際（額の真ん中 1.412、こめかみで下がる、耳の上 1.355）
HAIRLINE_PAINT = ([0.0, 0.03, 0.05, 0.065, 0.08, 0.10, 0.15], [1.412, 1.408, 1.398, 1.38, 1.36, 1.355, 1.355])
# 体の足と、スカートの中の脚・腰（見えない）を消す：z 0.85 より下、|x| 0.265 より内（手・前腕は |x| 0.28 より外）。
# スカートの下に見えるすね（0.197〜0.26）は肌の色の部品（leg_skin）に置き換える。三角形を約 9 千減らし、
# 歩き・走りで脚がスカートを突き抜けない
BOOT_CUT = 0.85
BOOT_RAMP = (0.06, 0.16)
BOOT_CUT_X = (-0.001, 0.265)
RIGHT_HAND_PART = True


# ---------------------------------------------------------------- 形の段のメッシュの測り

_MESH = None


def _mesh() -> np.ndarray:
    global _MESH
    if _MESH is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'build', 'shopkeeper',
                         'shopkeeper_mesh.npz')
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


# 腰から下の体（腕・手を除く）の、縦の軸 (0, AX_Y) のまわりの半径の表：角度（正面 0、本人の左 +90）× 高さ
AX_Y = 0.01
_TH = np.radians(np.arange(-180.0, 180.0, 5.0))
_RTAB = None


def body_r(th: np.ndarray, z: float) -> np.ndarray:
    """角度 th（ラジアン）・高さ z の体の外の半径（前後 1.5cm・左右 7.5 度の範囲の最大）"""
    global _RTAB
    if _RTAB is None:
        v = _mesh()
        # 腕・手を除く（腰の下は |x| 0.26 まで、0.80〜0.88 は 0.20 まで、腰の帯の高さ（0.88 より上）は 0.165 まで：
        # 1 周目は上腕の内の縁（|x| 0.19）を拾い、腰の帯が横へ 0.22 まで張り出した）
        lim = np.where(v[:, 2] > 0.93, 0.14, np.where(v[:, 2] > 0.88, 0.165, np.where(v[:, 2] > 0.80, 0.20, 0.26)))
        v = v[(np.abs(v[:, 0]) < lim) & (v[:, 2] > 0.15) & (v[:, 2] < 1.0)]
        _RTAB = (v[:, 2], np.arctan2(v[:, 0], -(v[:, 1] - AX_Y)), np.hypot(v[:, 0], v[:, 1] - AX_Y))
    vz, vth, vr = _RTAB
    sel = np.abs(vz - z) < 0.015
    vth, vr = vth[sel], vr[sel]
    out = np.zeros(len(_TH))
    for i, t in enumerate(_TH):
        d = np.abs((vth - t + math.pi) % (2 * math.pi) - math.pi)
        m = d < math.radians(7.5)
        out[i] = vr[m].max() if m.any() else 0.0
    # 当たらない角度は隣で埋め、少しならす
    for _ in range(3):
        z0 = out <= 0
        if not z0.any():
            break
        out[z0] = np.maximum(np.roll(out, 1), np.roll(out, -1))[z0]
    out = np.maximum(out, 0.5 * (np.roll(out, 1) + np.roll(out, -1)))
    return np.interp((np.asarray(th) + math.pi) % (2 * math.pi) - math.pi, _TH, out, period=2 * math.pi)


# ---------------------------------------------------------------- 小さな形（面をそのまま渡す部品）

def _orient(V, F):
    F = np.asarray(F, np.int64)
    vol = np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum()
    return V, (F[:, ::-1] if vol < 0 else F)


def disc_mesh(c, axis, up, r, depth, n=12):
    c, axis, up = (np.asarray(v, float) for v in (c, axis, up))
    axis = axis / np.linalg.norm(axis)
    e0 = up - axis * np.dot(up, axis)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(axis, e0)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(a)[:, None] * e0 + np.sin(a)[:, None] * e1
    V = np.concatenate([c + circ * r, c + axis * depth + circ * r * 0.8, [c, c + axis * depth]])
    F = []
    for i in range(n):
        i2 = (i + 1) % n
        F += [(i, n + i, n + i2), (i, n + i2, i2), (2 * n, i2, i), (2 * n + 1, n + i, n + i2)]
    return _orient(V, F)


def box_mesh(c, half, R=None):
    c = np.asarray(c, float)
    hx, hy, hz = half
    V = np.array([(sx * hx, sy * hy, sz * hz) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], float)
    if R is not None:
        V = V @ np.asarray(R).T
    V = V + c
    F = [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4), (2, 6, 7), (2, 7, 3), (0, 4, 6), (0, 6, 2),
         (1, 3, 7), (1, 7, 5)]
    return _orient(V, F)


def slab(outer: np.ndarray, inner: np.ndarray, wrap: bool = False):
    """格子 (行, 列, 3) の外の面と内の面を、縁の壁でつないだ閉じた板。wrap は列が一周する（スカート・腰の帯）"""
    R, C, _ = outer.shape
    V = np.concatenate([outer.reshape(-1, 3), inner.reshape(-1, 3)])
    n = R * C

    def idx(r, c, k):
        return k * n + r * C + (c % C)

    F = []
    cmax = C if wrap else C - 1
    for r in range(R - 1):
        for c in range(cmax):
            for k in (0, 1):
                a, b, cc, d = idx(r, c, k), idx(r, c + 1, k), idx(r + 1, c + 1, k), idx(r + 1, c, k)
                F += [(a, b, cc), (a, cc, d)] if k == 0 else [(a, cc, b), (a, d, cc)]
    # 縁の壁：上・下の行、（一周しないときは）左右の列
    for r in (0, R - 1):
        for c in range(cmax):
            a, b = idx(r, c, 0), idx(r, c + 1, 0)
            a2, b2 = idx(r, c, 1), idx(r, c + 1, 1)
            F += [(a, a2, b2), (a, b2, b)]
    if not wrap:
        for c in (0, C - 1):
            for r in range(R - 1):
                a, b = idx(r, c, 0), idx(r + 1, c, 0)
                a2, b2 = idx(r, c, 1), idx(r + 1, c, 1)
                F += [(a, a2, b2), (a, b2, b)]
    return _orient(V, F)


def ell_pts(cx, cy, a, bf, bb, n_exp, th):
    """超楕円の断面の点（角度 th：正面 0、本人の左 +90）。前の半分は bf、後ろは bb"""
    s, c = np.sin(th), np.cos(th)
    e = 2.0 / n_exp
    x = cx + a * np.sign(s) * np.abs(s) ** e
    b = np.where(c >= 0, bf, bb)
    y = cy - b * np.sign(c) * np.abs(c) ** e
    return x, y


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- スカートと前掛け

# スカートの断面（正面・右真横の絵の外形から。前は前掛けの下の面）：高さ → 左右の半幅 a・前 bf・後ろ bb
SK = dict(z=[0.226, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.88, 0.94],
          a=[0.308, 0.300, 0.279, 0.256, 0.236, 0.214, 0.188, 0.150, 0.120],
          bf=[0.236, 0.228, 0.212, 0.195, 0.176, 0.156, 0.132, 0.105, 0.088],
          bb=[0.232, 0.224, 0.200, 0.176, 0.155, 0.138, 0.124, 0.112, 0.100])
SK_N = 2.15
N_SK = 40       # 周の点の数（絵の面のあるスカート。陰影は骨付けの段の角度で折れ目）
SK_CLEAR = 0.010


def hem_z(th):
    """裾の高さ：前 0.226 → 横・後ろ 0.262（正面の絵は前の真ん中が低い弧、真横の絵は前が低い）"""
    return HEM[0] + (HEM[1] - HEM[0]) * smoothstep(np.abs(np.asarray(th)) / math.radians(80.0))


def ring_at(z, th):
    """高さ z（数か角度ごとの配列）・角度 th のスカートの外の面の点 (n, 3)。体の面より SK_CLEAR 外"""
    z = np.broadcast_to(np.asarray(z, float), np.shape(th))
    a = np.interp(z, SK['z'], SK['a'])
    bf = np.interp(z, SK['z'], SK['bf'])
    bb = np.interp(z, SK['z'], SK['bb'])
    x, y = ell_pts(0.0, AX_Y, a, bf, bb, SK_N, th)
    r = np.hypot(x, y - AX_Y)
    f = np.clip((SKIRT_TOP - z) / (SKIRT_TOP - HEM[0]), 0, 1)
    rb = body_r(th, float(np.mean(z))) + SK_CLEAR * (0.4 + 0.6 * f)
    k = np.maximum(r, rb) / np.maximum(r, 1e-6)
    return np.stack([x * k, AX_Y + (y - AX_Y) * k, z], 1)


_TH_F = np.radians(np.linspace(-90.0, 90.0, 91))
_TH_B = np.radians(np.linspace(90.0, 270.0, 91))


def front_y(x, z):
    """スカートの前の面の y（x・z で）"""
    p = ring_at(z, _TH_F)
    return np.interp(x, p[:, 0], p[:, 1])


def back_y(x, z):
    p = ring_at(z, _TH_B)
    return np.interp(x, p[::-1, 0], p[::-1, 1])


def radial_offset(P, d):
    """点を縦の軸 (0, AX_Y) から外へ d だけ動かす"""
    v = P[..., :2] - np.array([0.0, AX_Y])
    v = v / np.linalg.norm(v, axis=-1, keepdims=True)
    Q = P.copy()
    Q[..., :2] = P[..., :2] + v * np.asarray(d)[..., None]
    return Q


def skirt() -> list[dict]:
    th = np.linspace(-math.pi, math.pi, N_SK, endpoint=False) + math.pi / N_SK
    fr = np.concatenate([np.linspace(0.0, 0.08, 3), np.linspace(0.16, 1.0, 9)])
    hz = hem_z(th)
    outer = np.array([ring_at(SKIRT_TOP + (hz - SKIRT_TOP) * f, th) for f in fr])
    outer[-1] = radial_offset(outer[-1], np.full(len(th), 0.002))     # 裾の縁を少し外へ
    inner = radial_offset(outer, np.full(outer.shape[:2], -0.007))
    V, F = slab(outer, inner, wrap=True)
    n = outer.shape[0] * outer.shape[1]
    is_in = (F.min(1) >= n)
    return [dict(name='skirt', bone='hips', color='skirt', mesh=(V, F[~is_in])),
            dict(name='skirt_inner', bone='hips', color='skirt_in', mesh=(V, F[is_in]))]


def apron_off(z):
    """前掛けの前の布のスカートからの浮き：上 1.0cm → 下の縁 3.0cm（真横の絵：下の縁は y −0.249）"""
    return 0.010 + 0.020 * smoothstep((0.915 - np.asarray(z)) / (0.915 - APRON_BOT))


def apron_pt(x, z, lift=0.0):
    """前掛けの前の布の外の面の点（その上に lift だけ浮かせる）"""
    x = np.atleast_1d(np.asarray(x, float))
    return np.stack([x, front_y(x, z) - apron_off(z) - lift, np.full(len(x), float(z))], 1)


def apron() -> list[dict]:
    P = []
    # 前の布：上（腰の帯の下）x ±0.108 → 下の縁 0.392 で ±0.215
    zs = np.linspace(0.915, APRON_BOT, 11)
    outer = np.array([apron_pt(np.linspace(-1, 1, 13) * (0.108 + 0.107 * (0.915 - z) / (0.915 - APRON_BOT)), z)
                      for z in zs])
    inner = outer.copy()
    inner[..., 1] += 0.005
    V, F = slab(outer, inner)
    P.append(dict(name='apron_front', bone='hips', color='rust', mesh=(V, F)))
    # ポケット ×2（前掛けの上、x 0.035〜0.175、z 0.535〜0.785。外へ 5 度傾く）・蓋（0.700〜0.792、下の縁は真ん中が 1.2cm 下）・鋲 ×2
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        tilt = math.radians(5.0) * side

        def rect(u, v, x0, x1, z0, z1):
            xc, zc = (x0 + x1) / 2, (z0 + z1) / 2
            dx, dz = (u - 0.5) * (x1 - x0), (v - 0.5) * (z1 - z0)
            return xc + dx * math.cos(tilt) - dz * math.sin(tilt), zc + dx * math.sin(tilt) + dz * math.cos(tilt)

        def panel(U, Vv, x0, x1, z0, z1, lift, dip=0.0):
            X, Z = rect(U, Vv, x0, x1, z0, z1)
            Z = Z - dip * (1 - Vv) * (1 - np.abs(U - 0.5) * 2)
            o = np.array([[apron_pt(X[i, j], Z[i, j], lift)[0] for j in range(X.shape[1])] for i in range(X.shape[0])])
            if side < 0:
                o = o[:, ::-1]
            inn = o.copy()
            inn[..., 1] += 0.006
            return slab(o, inn)
        U, Vv = np.meshgrid(np.linspace(0, 1, 7), np.linspace(1, 0, 9))
        x0, x1 = sorted((0.035 * side, 0.175 * side))
        V, F = panel(U, Vv, x0, x1, 0.535, 0.785, 0.007)
        P.append(dict(name='pocket' + sx, bone='hips', color='rust_dark', mesh=(V, F)))
        U2, V2 = np.meshgrid(np.linspace(0, 1, 7), np.linspace(1, 0, 4))
        fx0, fx1 = sorted((0.031 * side, 0.179 * side))
        V, F = panel(U2, V2, fx0, fx1, 0.700, 0.792, 0.014, dip=0.012)
        P.append(dict(name='pocket_flap' + sx, bone='hips', color='rust', mesh=(V, F)))
        for k, u in enumerate((0.17, 0.83)):
            xs_, zs_ = rect(u, 0.55, fx0, fx1, 0.700, 0.792)
            c = apron_pt(xs_, zs_, 0.0205)[0]
            Vd, Fd = disc_mesh(c, (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), 0.0075, 0.004, 10)
            P.append(dict(name=f'pocket_stud{k}' + sx, bone='hips', color='brass', mesh=(Vd, Fd)))
    # 後ろの布 ×2：腰の帯の下から 0.42 まで、真後ろの x 0.004〜0.140（下で 0.150）。絵の背面：赤錆は真ん中の 2 枚、
    # 横は焦げ茶のスカートが見える（1 周目は横から後ろへ回る 68〜176 度にして、背中が全部赤錆になった）。スカートから 8〜18mm
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        zs = np.linspace(0.915, BACK_BOT, 12)
        rows = []
        for z in zs:
            g = (0.915 - z) / (0.915 - BACK_BOT)
            xs = side * np.linspace(0.004, 0.140 + 0.010 * g, 9)
            if side < 0:
                xs = xs[::-1]
            P0 = np.stack([xs, back_y(xs, z), np.full(len(xs), z)], 1)
            rows.append(radial_offset(P0, np.full(len(xs), 0.008 + 0.010 * smoothstep(g))))
        outer = np.array(rows)
        inner = radial_offset(outer, np.full(outer.shape[:2], -0.005))
        V, F = slab(outer, inner)
        P.append(dict(name='apron_back' + sx, bone='hips', color='rust', mesh=(V, F)))
    return P


def waistband_bow() -> list[dict]:
    """腰の帯（前掛けの幅広の紐、ぐるり）と背中の蝶結び（結び目・輪 ×2・垂れ ×2）。絵 shopkeeper_3d_back・side"""
    P = []
    th = np.linspace(-math.pi, math.pi, 48, endpoint=False)
    # 行ごとの半径：体の 1.2cm 外、スカートの上の端（0.94 より下）の 0.6cm 外（1 周目は帯の高さ全体の最大で、上の縁が体から 3cm 浮いた）
    zs = np.linspace(WAIST[0], WAIST[1], 4)
    rows = []
    for z in zs:
        r = body_r(th, z) + 0.012
        if z < SKIRT_TOP:
            r = np.maximum(r, np.hypot(*(ring_at(z, th)[:, :2] - np.array([0.0, AX_Y])).T) + 0.006)
        r = 0.5 * r + 0.25 * (np.roll(r, 1) + np.roll(r, -1))
        rows.append(r)
    rows = np.maximum.accumulate(np.array(rows)[::-1], 0)[::-1]      # 下の行ほど太い（上の縁が下の縁より外へ出ない）
    outer = np.array([np.stack([np.sin(th) * r, AX_Y - np.cos(th) * r, np.full(len(th), z)], 1) for z, r in zip(zs, rows)])
    inner = radial_offset(outer, np.full(outer.shape[:2], -0.009))
    V, F = slab(outer, inner, wrap=True)
    P.append(dict(name='waistband', bone='hips', color='rust', mesh=(V, F)))
    yb = AX_Y + float(rows[1][0])        # 真後ろ（th = −π）の帯の外
    zc = 0.900
    Vk, Fk = box_mesh((0.0, yb + 0.014, zc), (0.020, 0.014, 0.022))
    P.append(dict(name='bow_knot', bone='hips', color='rust', mesh=(Vk, Fk)))
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        # 輪：結び目から横へ 7.4cm、高さ 5〜6cm の平たいしずく（8 角の断面を積む）
        secs = []
        for t, h, d in ((0.0, 0.016, 0.010), (0.25, 0.030, 0.013), (0.55, 0.027, 0.012), (0.85, 0.017, 0.010),
                        (1.0, 0.004, 0.006)):
            xc = side * (0.012 + 0.062 * t)
            zcc = zc + 0.012 * math.sin(math.pi * t)
            yc = yb + 0.014 - 0.014 * t * t
            ang = np.linspace(0, 2 * math.pi, 8, endpoint=False) + math.pi / 8
            secs.append(np.stack([np.full(8, xc), yc + d * np.cos(ang), zcc + h * np.sin(ang)], 1))
        V, F = _loft_x(np.array(secs))
        P.append(dict(name='bow_loop' + sx, bone='hips', color='rust', mesh=(V, F)))
        # 垂れ：結び目から 0.625 まで、外へ少し開く板（後ろの布の外）
        zs_t = np.linspace(zc - 0.012, 0.625, 9)
        g = (zc - zs_t) / (zc - 0.625)
        xc = side * (0.012 + 0.030 * g)
        w = 0.017 + 0.006 * g
        ro, ri = [], []
        for z_, x_, w_ in zip(zs_t, xc, w):
            xs = np.linspace(x_ - w_, x_ + w_, 3)
            yy = np.maximum(back_y(xs, z_) + 0.026, yb + 0.006 - 0.04 * (zc - z_))
            ro.append(np.stack([xs, yy + 0.004, np.full(3, z_)], 1))
            ri.append(np.stack([xs, yy, np.full(3, z_)], 1))
        V, F = slab(np.array(ro), np.array(ri))
        P.append(dict(name='bow_tail' + sx, bone='hips', color='rust', mesh=(V, F)))
    return P


def _loft_x(secs: np.ndarray):
    """断面（同じ点の数の輪）を並べた閉じた形（両端は扇でふさぐ）"""
    k, n, _ = secs.shape
    V = list(secs.reshape(-1, 3))
    F = []
    for j in range(k - 1):
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            c, d = (j + 1) * n + (i + 1) % n, (j + 1) * n + i
            F += [(a, b, c), (a, c, d)]
    for j, flip in ((0, True), (k - 1, False)):
        ci = len(V)
        V.append(secs[j].mean(0))
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            F.append((ci, b, a) if flip else (ci, a, b))
    return _orient(np.array(V), F)


# ---------------------------------------------------------------- 胴・腕の部品（体の面に沿う殻）

def top_parts() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    back = np.array([0.0, 1.0, 0.0])
    # 立ち襟：首の縦の軸のまわり、後ろが s = 0。前は細い切れ込み（下 |x| 0.005、上 0.010）。後ろは高い
    fc = frame((X0, CY_NECK, 0.0), (X0, CY_NECK, 1.0), back)
    fc['RN'] = 0.05
    sb = 0.05 * (math.pi - math.asin(0.005 / 0.042))
    st_ = 0.05 * (math.pi - math.asin(0.011 / 0.045))
    out = [(-sb, COLLAR_Z[0]), (sb, COLLAR_Z[0]), (st_, COLLAR_Z[1]), (0.07, 1.238), (0.0, 1.244), (-0.07, 1.238),
           (-st_, COLLAR_Z[1])]
    P.append(dict(name='collar', bone='neck', color='ivory', frame=fc, outline=out, off=0.003, thick=0.006,
                  bevel=0.002, under='ivory', rmax=0.07, rmin=0.036, h=0.007, env_rings=2, smooth_iters=30,
                  raw_tol=0.003))
    # 上の縁の焦げ茶の線（襟の上 6mm）
    P.append(dict(name='collar_trim', bone='neck', color='trim', frame=fc,
                  outline=[(-st_, COLLAR_Z[1] - 0.006), (st_, COLLAR_Z[1] - 0.006), (st_, COLLAR_Z[1] + 0.001),
                           (0.07, 1.2395), (0.0, 1.2455), (-0.07, 1.2395), (-st_, COLLAR_Z[1] + 0.001)],
                  off=0.0045, thick=0.006, bevel=0.0015, rmax=0.07, rmin=0.036, h=0.004, env_rings=2,
                  smooth_iters=30, raw_tol=0.003))
    # 前の真鍮の留め（横の棒）
    yb = body_front_y(1.158, X0 - 0.02, X0 + 0.02) - 0.006
    V, F = box_mesh((X0, yb, 1.158), (0.017, 0.004, 0.0045))
    P.append(dict(name='collar_toggle', bone='chest', color='brass', mesh=(V, F)))
    # 前掛けの胸当て：腰の帯の上の縁から 1.105 まで、x ±0.103
    fw = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), front)
    fw['RN'] = 0.13
    P.append(dict(name='bib', bone='chest', color='rust', frame=fw,
                  outline=[(-0.104, WAIST[1] - 0.02), (0.104, WAIST[1] - 0.02), (0.104, BIB_TOP), (-0.104, BIB_TOP)],
                  off=0.004, thick=0.006, bevel=0.002, under='rust', rmax=0.25, h=0.010, env_rings=2,
                  smooth_iters=6))
    # 肩ひも ×2（左右の軸のまわり：胸当ての上の角 → 肩の上 → 背中を下りて腰の帯まで）。t = |x|
    up = np.array([0.0, 0.0, 1.0])
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        ax_y, ax_z = 0.0, 1.06
        fst = frame((0.0, ax_y, ax_z), (side, ax_y, ax_z), up)
        fst['RN'] = 0.1
        (tf0, tf1), (tb0, tb1) = (0.068, 0.100), (0.050, 0.082)
        xs = sorted((side * tf0, side * tf1))
        xb = sorted((side * tb0, side * tb1))
        zf, zb = BIB_TOP - 0.012, WAIST[0]
        af = math.atan2(ax_y - body_front_y(zf, *xs), zf - ax_z)
        ab = math.atan2(body_back_y(zb, *xb) - ax_y, zb - ax_z)
        sf, sb2 = af * 0.1, -ab * 0.1
        if side < 0:
            sf, sb2 = -sf, -sb2
        out = [(sb2, tb0), (sf, tf0), (sf, tf1), (sb2, tb1)]
        if side < 0:
            out = out[::-1]
        P.append(dict(name='strap' + sx, bone='chest', color='rust', frame=fst, outline=out, off=0.006,
                      thick=0.005, bevel=0.0015, under='rust', rmax=0.25, env_rings=1, h=0.008, smooth_iters=40,
                      raw_tol=0.0))
        # 肩ひもの留め金（胸当ての上の角）：真鍮の枠 4 本 ＋ 中の暗い帯
        xc, zc = side * 0.084, BIB_TOP - 0.004
        yf = body_front_y(zc, xc - 0.025, xc + 0.025) - 0.017
        for nm, c, h in (('t', (xc, yf, zc + 0.022), (0.024, 0.004, 0.0045)), ('b', (xc, yf, zc - 0.022), (0.024, 0.004, 0.0045)),
                         ('l', (xc - 0.020, yf, zc), (0.0045, 0.004, 0.022)), ('r', (xc + 0.020, yf, zc), (0.0045, 0.004, 0.022))):
            V, F = box_mesh(c, h)
            P.append(dict(name=f'buckle_{nm}' + sx, bone='chest', color='brass', mesh=(V, F)))
        V, F = box_mesh((xc, yf + 0.002, zc), (0.016, 0.003, 0.009))
        P.append(dict(name='buckle_bar' + sx, bone='chest', color='strap_dark', mesh=(V, F)))
    # 肘の革の帯・袖の折り返し（上腕の軸）・手首の帯（前腕の軸）
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        s, e = jp('upper_arm', side), jp('forearm', side)
        fs = frame(s, e, front)
        fs['RN'] = 0.06
        P.append(dict(name='elbow_band' + sx, bone='upper_arm' + sx, color='leather', frame=fs, ring=True,
                      t0=ELBOW_T[0], t1=ELBOW_T[1], off=0.006, thick=0.009, bevel=0.003, under='leather',
                      rmax=0.14, rmin=0.03, n_ring=32, sink=0.012))
        P.append(dict(name='sleeve_fold' + sx, bone='upper_arm' + sx, color='ivory', frame=fs, ring=True,
                      t0=ELBOW_T[1] - 0.004, t1=ELBOW_T[2], off=0.003, thick=0.007, bevel=0.002, under='ivory',
                      rmax=0.14, rmin=0.03, n_ring=32, sink=0.012))
        # 帯の外の真鍮の鋲
        L = float(np.linalg.norm(e - s))
        d = (e - s) / L
        c = s + d * (ELBOW_T[0] + ELBOW_T[1]) / 2
        out_dir = np.array([side, 0.0, 0.0]) - d * (side * d[0])
        out_dir /= np.linalg.norm(out_dir)
        p = _band(c[2], 0.02)
        p = p[(side * p[:, 0] > 0.18) & (np.abs(p[:, 1] - c[1]) < 0.03)]
        rx = float((side * (p[:, 0] - c[0])).max()) if len(p) else 0.045
        Vd, Fd = disc_mesh(c + out_dir * (rx + 0.016), out_dir, (0.0, 0.0, 1.0), 0.008, 0.005, 10)
        P.append(dict(name='elbow_stud' + sx, bone='upper_arm' + sx, color='brass', mesh=(Vd, Fd)))
        s2, e2 = jp('forearm', side), jp('hand', side)
        fs2 = frame(s2, e2, front)
        fs2['RN'] = 0.05
        P.append(dict(name='wristband' + sx, bone='forearm' + sx, color='band', frame=fs2, ring=True,
                      t0=WRIST_T[0], t1=WRIST_T[1], off=0.004, thick=0.010, bevel=0.003, under='band',
                      rmax=0.12, rmin=0.02, n_ring=32, sink=0.012))
    return P


def legs_lid() -> list[dict]:
    """スカートの下に見えるすね（肌、靴の折り返しの中 0.15 からスカートの中 0.33 まで）と、体を消した切り口のふた（スカートの中 0.845）"""
    P = []
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        secs = []
        for z, rx, ry in ((0.150, 0.035, 0.043), (0.200, 0.036, 0.045), (0.260, 0.039, 0.048), (0.330, 0.043, 0.052)):
            ang = np.linspace(0, 2 * math.pi, 12, endpoint=False)
            secs.append(np.stack([side * 0.148 + rx * np.sin(ang), 0.025 - ry * np.cos(ang), np.full(12, z)], 1))
        V, F = _loft_x(np.array(secs))
        P.append(dict(name='leg_skin' + sx, bone='shin' + sx, color='skin', mesh=(V, F)))
    th = np.linspace(-math.pi, math.pi, 24, endpoint=False)
    ring = radial_offset(ring_at(0.845, th), np.full(len(th), -0.012))
    V, F = _loft_x(np.array([ring, ring + np.array([0.0, 0.0, 0.004])]))
    P.append(dict(name='skirt_lid', bone='hips', color='skirt_in', mesh=(V, F)))
    return P


def pieces() -> list[dict]:
    P = []
    P += top_parts()
    P += waistband_bow()
    P += apron()
    P += skirt()
    P += legs_lid()
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        P += boot_pieces(side, sx)
    P += hair_parts()
    return P


def boot_pieces(side: float, sx: str) -> list[dict]:
    """片足の靴（左の値で書き、右は x を反転）。絵 shopkeeper_shoes と全身の絵（正面・右真横）：
    底 x 0.094〜0.249・y −0.169〜0.101、厚い底（かかと 3cm）、暗い胴、茶の爪先、足首の折り返し（0.14〜0.195）と真鍮の鋲"""
    X0_, X1_ = 0.096, 0.248
    YF, YB = -0.168, 0.100
    P = []

    def sec(z, x0, x1, y0, y1, rf, rb, k=3):
        return (z, rrect(x0, x1, y0, y1, rf, rb, k))

    sole = [sec(0.000, X0_ + 0.004, X1_ - 0.004, YF + 0.006, YB - 0.004, 0.060, 0.040),
            sec(0.005, X0_, X1_, YF, YB, 0.064, 0.044),
            sec(0.026, X0_, X1_, YF, YB, 0.064, 0.044),
            sec(0.031, X0_ + 0.003, X1_ - 0.003, YF + 0.004, YB - 0.003, 0.061, 0.041)]
    toe = [sec(0.026, X0_ + 0.006, X1_ - 0.006, YF + 0.006, -0.060, 0.058, 0.02, 4),
           sec(0.050, X0_ + 0.008, X1_ - 0.009, YF + 0.010, -0.058, 0.055, 0.02, 4),
           sec(0.068, X0_ + 0.016, X1_ - 0.018, YF + 0.030, -0.054, 0.045, 0.02, 4),
           sec(0.080, X0_ + 0.026, X1_ - 0.028, YF + 0.060, -0.050, 0.035, 0.02, 4)]
    upper = [sec(0.026, X0_ + 0.007, X1_ - 0.007, -0.075, YB - 0.006, 0.03, 0.040, 4),
             sec(0.060, X0_ + 0.009, X1_ - 0.010, -0.085, YB - 0.008, 0.03, 0.040, 4),
             sec(0.085, X0_ + 0.016, X1_ - 0.020, -0.075, YB - 0.012, 0.035, 0.040, 4),
             sec(0.110, 0.112, 0.200, -0.050, 0.085, 0.040, 0.040, 4),
             sec(0.140, 0.110, 0.196, -0.034, 0.084, 0.040, 0.040, 4),
             sec(0.158, 0.112, 0.194, -0.030, 0.082, 0.040, 0.040, 4)]
    cuff = [sec(0.136, 0.100, 0.206, -0.040, 0.092, 0.050, 0.050, 4),
            sec(0.142, 0.096, 0.210, -0.044, 0.096, 0.052, 0.052, 4),
            sec(0.192, 0.096, 0.210, -0.044, 0.096, 0.052, 0.052, 4),
            sec(0.197, 0.100, 0.206, -0.040, 0.092, 0.050, 0.050, 4)]
    for name, color, secs in (('sole', 'sole', sole), ('toe', 'toe', toe), ('upper', 'boot', upper), ('cuff', 'boot', cuff)):
        if side < 0:
            secs = [(z, [(-x, y) for (x, y) in pts][::-1]) for z, pts in secs]
        P.append(dict(name=f'boot_{name}{sx}', bone='foot' + sx, color=color, loft=secs,
                      ramp=('shin' + sx, 'foot' + sx)))
    # 折り返しの外の真鍮の鋲
    c = np.array([side * 0.211, 0.026, 0.168])
    Vd, Fd = disc_mesh(c, (side, 0.0, 0.0), (0.0, 0.0, 1.0), 0.009, 0.004, 10)
    P.append(dict(name='boot_stud' + sx, bone='foot' + sx, color='brass', mesh=(Vd, Fd), ramp=('shin' + sx, 'foot' + sx)))
    return P


# ---------------------------------------------------------------- 髪（お団子・房・前髪・顔の横の房）

BUN_C = np.array([X0, 0.078, 1.503])     # お団子の中心（頭の真横・背面・真上の絵。2 周目に 1.5cm 上げた：正面から下半分が頭の房に隠れた）


def _petal(c, axis, up, L, W, T, n=8, k=6):
    """お団子の房：c から axis の向きへ長さ L、幅 W・厚み T の、面のある丸い房（断面 n 角を k 個）"""
    c, axis, up = (np.asarray(v, float) for v in (c, axis, up))
    axis = axis / np.linalg.norm(axis)
    e0 = up - axis * np.dot(up, axis)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(axis, e0)
    secs = []
    for t in np.linspace(0.0, 1.0, k):
        s = math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.7
        ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
        p = c + axis * (L * (t - 0.5)) + (np.cos(ang)[:, None] * e0 * T * s + np.sin(ang)[:, None] * e1 * W * s)
        secs.append(p)
    return _loft_x(np.array(secs))


def bun() -> list[dict]:
    """お団子：頭頂の後ろの、丸い房 8 個の輪 ＋ 上の房 1 個（絵の真上の図：花のように重なる）"""
    out = []
    ring = 8
    for i in range(ring):
        a = 2 * math.pi * i / ring + 0.2
        d = np.array([math.sin(a), -math.cos(a) * 0.95, 0.0])
        c = BUN_C + d * 0.047 + np.array([0.0, 0.0, 0.005 * math.cos(2 * a)])
        tang = np.array([math.cos(a), math.sin(a) * 0.95, 0.15])
        V, F = _petal(c, tang, (0.0, 0.0, 1.0), 0.072, 0.033, 0.029)
        out.append(dict(name=f'hair_bun{i}', bone='head', color='hair', mesh=(V, F)))
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.6
        d = np.array([math.sin(a), -math.cos(a) * 0.95, 0.0])
        c = BUN_C + d * 0.024 + np.array([0.0, 0.0, 0.022])
        tang = np.array([math.cos(a), math.sin(a) * 0.95, 0.25])
        V, F = _petal(c, tang, (0.0, 0.0, 1.0), 0.052, 0.025, 0.022)
        out.append(dict(name=f'hair_bun_in{i}', bone='head', color='hair', mesh=(V, F)))
    V, F = _petal(BUN_C + np.array([0.0, 0.006, 0.036]), (1.0, 0.25, 0.0), (0.0, 0.0, 1.0), 0.066, 0.038, 0.027)
    out.append(dict(name='hair_bun_top', bone='head', color='hair', mesh=(V, F)))
    V, F = _petal(BUN_C + np.array([0.0, -0.012, 0.030]), (0.2, -1.0, 0.1), (0.0, 0.0, 1.0), 0.058, 0.034, 0.025)
    out.append(dict(name='hair_bun_top2', bone='head', color='hair', mesh=(V, F)))
    return out


def hair_parts() -> list[dict]:
    """房（nico_parts.hair_locks の厚い板の作り）：まとめ髪なので、房はお団子の付け根から頭の面に沿って下り、
    先は生え際（前は額・横は耳の上・後ろはえり足）。前髪は真ん中の分け目から左右へ流れ、こめかみ・ほおの横へ。
    顔の横の長い房（耳の前、あごまで）。えり足の小さな房 ×2"""
    from scipy import ndimage as NDI

    from recon import hair as HR
    from recon import views as V
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    phi, lo, vox = np.asarray(d['phi'], np.float32), d['lo'], float(d['vox'])
    C = np.array(HR.HEAD_C, float)

    def inside(P):
        idx = ((P[:, [2, 0, 1]] - lo[[2, 0, 1]]) / vox - 0.5).T
        return NDI.map_coordinates(phi, idx, order=1, mode='constant', cval=-1.0) > 0

    def radial(dirs, r_max=0.30, step=0.002):
        rs = np.arange(r_max, 0.0, -step)
        P = C[None, None] + rs[None, :, None] * dirs[:, None, :]
        ins = inside(P.reshape(-1, 3)).reshape(len(dirs), len(rs))
        k = np.argmax(ins, 1)
        return np.where(ins.any(1), rs[k], 0.10)

    def horiz(th_deg, z, r_max=0.30, step=0.002):
        th = np.radians(th_deg)
        rs = np.arange(r_max, 0.0, -step)
        P = np.stack([C[0] + rs * np.sin(th), C[1] - rs * np.cos(th), np.full(len(rs), z)], 1)
        ins = inside(P)
        return float(rs[np.argmax(ins)]) if ins.any() else 0.0

    # 断面：峰（外）・左右の縁・内の 6 角（ニコより薄い：まとめ髪の房は頭に沿う。帽子は外形より 2cm 内）
    prof = [(0.0, 0.30), (1.0, 0.06), (0.94, -0.05), (0.0, -0.14), (-0.94, -0.05), (-1.0, 0.06)]
    widths = np.array([0.45, 0.82, 0.97, 1.0, 1.0, 0.98, 0.90, 0.62, 0.0])
    n = len(widths)

    def plank(P, w, lift_min, push=True, wscale=None, thick=1.0):
        t = np.linspace(0.0, 1.0, n)
        wv = widths if wscale is None else widths * wscale
        dv = P - C
        rr = np.linalg.norm(dv, axis=1)
        dn = dv / rr[:, None]
        if push:
            rs = radial(dn)
            need = rs + lift_min + 0.10 * w * wv - np.where(t < 0.01, 0.010, 0.0)
            P = C + dn * np.maximum(rr, need)[:, None]
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        N = (P - C) - ((P - C) * T).sum(1, keepdims=True) * T
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        B = np.cross(T, N)
        ww = w * wv
        rings = np.stack([P + B * (ww * px)[:, None] + N * (ww * py * thick)[:, None] for px, py in prof], 1)
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
        Q = 2.0 * M - 0.5 * (R0 + T2)
        return (1 - t) ** 2 * R0 + 2 * (1 - t) * t * Q + t ** 2 * T2

    out = bun()
    # 頭を覆う房：根はお団子の付け根のまわり（z 1.475）、その向き・高さの帽子の面 ＋ 浮きを通って、先は生え際。
    # (名前, 角度（正面 0・本人の左 +）, 先の高さ, 幅, 浮き)
    # 2 周目：頭の帽子を頭の面から 6mm に締めたので、房が髪の形を決める。絵（head_back・side_right）：横と後ろの髪はえり足・耳の上から
    # お団子へまとめ上げ、房はお団子の下へ放射状に集まる。房を細く（4〜5cm）本数を多く（19 本）、後ろの房の先はえり足の真ん中へ寄る。
    # (名前, 根の角度, 先の角度, 先の高さ, 幅, 浮き)。角度は正面 0・本人の左 +
    sweep = [
        ('front_l', 12, 12, 1.410, 0.050, 0.003), ('front_r', -12, -12, 1.410, 0.050, 0.003),
        ('front_l2', 34, 34, 1.398, 0.050, 0.003), ('front_r2', -34, -34, 1.398, 0.050, 0.003),
        ('side_l', 56, 58, 1.384, 0.046, 0.003), ('side_r', -56, -58, 1.384, 0.046, 0.003),
        ('side_l2', 78, 80, 1.368, 0.046, 0.003), ('side_r2', -78, -80, 1.368, 0.046, 0.003),
        ('ear_l', 98, 102, 1.352, 0.044, 0.003), ('ear_r', -98, -102, 1.352, 0.044, 0.003),
        ('back_l', 118, 132, 1.322, 0.042, 0.003), ('back_r', -118, -132, 1.322, 0.042, 0.003),
        ('back_l2', 136, 150, 1.296, 0.042, 0.003), ('back_r2', -136, -150, 1.296, 0.042, 0.003),
        ('back_l3', 152, 164, 1.272, 0.042, 0.003), ('back_r3', -152, -164, 1.272, 0.042, 0.003),
        ('back_l4', 166, 174, 1.258, 0.040, 0.003), ('back_r4', -166, -174, 1.258, 0.040, 0.003),
        ('back_c', 180, 180, 1.246, 0.048, 0.004),
    ]
    sgrid = np.linspace(0.0, 1.0, n)
    for name, thd, tht, zt, w, lift in sweep:
        z0 = 1.478
        zz = z0 - (z0 - zt) * sgrid ** 1.1
        th = thd + (tht - thd) * np.clip((sgrid - 0.25) / 0.75, 0, 1)
        rho_s = np.array([horiz(a, b) for a, b in zip(th, zz)])
        rho = rho_s + lift + 0.10 * w * widths
        k_wide = int(np.argmax(rho))
        rho[k_wide:] = np.maximum.accumulate(rho[k_wide:])
        P = np.stack([C[0] + rho * np.sin(np.radians(th)), C[1] - rho * np.cos(np.radians(th)), zz], 1)
        # 根はお団子の付け根（中心から 4cm、その向き）
        a = math.radians(thd)
        P[0] = BUN_C + np.array([0.030 * math.sin(a), -0.030 * math.cos(a), -0.012])
        Vm, Fm = plank(P, w, lift, push=False)
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(Vm, Fm)))
    # 前髪（真ん中の分け目から左右へ流れる）・顔の横の長い房（耳の前、あごまで）・えり足の房。(名前, 根, 先, 幅, 浮き)
    xr = X0
    # (名前, 根, 先, 幅, 浮き, 先のはね（外へ m）, 厚みの倍率)。2 周目：前髪は厚く（1.5 倍）、先の 4 割で外へはねる（絵のとがった房）
    top = [
        ('fringe_l', [xr + 0.014, -0.104, 1.448], [xr + 0.086, -0.098, 1.360], 0.034, 0.004, 0.010, 1.5),
        ('fringe_r', [xr - 0.014, -0.104, 1.448], [xr - 0.086, -0.098, 1.360], 0.034, 0.004, 0.010, 1.5),
        ('fringe_l2', [xr + 0.034, -0.096, 1.452], [xr + 0.102, -0.072, 1.302], 0.034, 0.005, 0.012, 1.5),
        ('fringe_r2', [xr - 0.034, -0.096, 1.452], [xr - 0.102, -0.072, 1.302], 0.034, 0.005, 0.012, 1.5),
        ('fringe_l3', [xr + 0.004, -0.108, 1.446], [xr + 0.052, -0.121, 1.392], 0.026, 0.004, 0.007, 1.4),
        ('fringe_r3', [xr - 0.004, -0.108, 1.446], [xr - 0.052, -0.121, 1.392], 0.026, 0.004, 0.007, 1.4),
        ('cheek_l', [xr + 0.074, -0.066, 1.415], [xr + 0.098, -0.046, 1.245], 0.026, 0.005, 0.006, 1.2),
        ('cheek_r', [xr - 0.074, -0.066, 1.415], [xr - 0.098, -0.046, 1.245], 0.026, 0.005, 0.006, 1.2),
        ('nape_l', [xr + 0.046, 0.072, 1.300], [xr + 0.060, 0.050, 1.232], 0.024, 0.003, 0.004, 1.0),
        ('nape_r', [xr - 0.046, 0.072, 1.300], [xr - 0.060, 0.050, 1.232], 0.024, 0.003, 0.004, 1.0),
    ]
    for name, r0, r1, w, lift, flick, thk in top:
        R0, T2 = np.asarray(r0, float), np.asarray(r1, float)
        dm = (R0 - C) / np.linalg.norm(R0 - C) + (T2 - C) / np.linalg.norm(T2 - C)
        dm /= np.linalg.norm(dm)
        M = C + dm * (radial(dm[None])[0] + lift + 0.10 * w)
        P = curve(R0, M, T2)
        # 先の 4 割で外へはねる（頭の縦の軸から外の水平の向き）
        t = np.linspace(0.0, 1.0, n)
        od = P[:, :2] - C[:2]
        od /= np.maximum(np.linalg.norm(od, axis=1, keepdims=True), 1e-6)
        P[:, :2] += od * (flick * np.clip((t - 0.6) / 0.4, 0, 1) ** 2)[:, None]
        Vm, Fm = plank(P, w, lift, thick=thk)
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(Vm, Fm)))
    return out


# ---------------------------------------------------------------- 決まりの塗り（cover_body から）

def body_rules(pos: np.ndarray, col: np.ndarray, lab: np.ndarray, under: np.ndarray, ins: dict, stats: dict) -> None:
    """胴の上はブラウスの生成り、腕は肘の帯まで生成りの袖・その先は肌、スカートの中の腰・脚は焦げ茶、スカートの下の脚は肌、
    首は肌。頭と首の帯は形の場（hair.part_fields_at）で髪・肌・耳を決める"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    free = under < 0
    r_neck = np.hypot(x - X0, y - CY_NECK)
    head = (z > NECK_TOP + 0.01) | ((z > 1.20) & (r_neck > 0.07) & (y < 0.0) & (np.abs(x) < 0.15))
    blouse = free & ~head & (z >= WAIST[0])
    under[blouse] = NAMES.index('ivory')
    # 腕：肘の帯の下（袖の折り返し）より先は肌
    arm_skin = np.zeros(len(pos), bool)
    for side in (1.0, -1.0):
        S, E = np.array(jp('upper_arm', side)), np.array(jp('forearm', side))
        dv = (E - S) / np.linalg.norm(E - S)
        t = (pos - S) @ dv
        rr = np.linalg.norm((pos - S) - np.outer(t, dv), axis=1)
        m = free & (side * x > 0.15) & (rr < 0.12) & (t > ELBOW_T[2] - 0.004) & (z < 1.0)
        arm_skin |= m
    hand_zone = (np.abs(x) > 0.30) & (z > 0.55) & (z < 0.86)
    arm_skin |= free & hand_zone
    under[arm_skin] = NAMES.index('skin')
    # 首（襟の下の縁より上）：肌
    neck = free & ~head & (z > COLLAR_Z[0] - 0.01) & (r_neck < 0.07)
    under[neck] = NAMES.index('skin')
    # 腰・脚（スカートの中）：焦げ茶。スカートの下（すね）は肌
    legs = free & (z < WAIST[0]) & ~arm_skin
    under[legs] = NAMES.index('skirt')
    shin = free & (z < LEG_SKIN_Z) & ~arm_skin
    under[shin] = NAMES.index('skin')
    # 頭と首の帯：形の場で
    from recon import hair as HR
    hb = (z > 1.16) & (z < 1.62) & (np.hypot(x - X0, y) < np.where(z > 1.22, 0.30, 0.10))
    hi = np.nonzero(hb)[0]
    if len(hi):
        f = HR.part_fields_at(pos[hi], x_half=0.30, z0=1.14)
        xh, yh, zh = x[hi], y[hi], z[hi]
        ear = f['ear'] > -0.002
        hair = (f['hair'] > -0.004) & ~ear
        ax = np.abs(xh - X0)
        th_f = np.degrees(np.arctan2(ax, -(yh - 0.0)))
        flush = (f['hair'] - f['skin']) < 0.009
        line = np.where(th_f < 70.0, np.interp(ax, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]),
                        np.where(yh < 0.045, 1.355, 1.255))
        hair &= ~(flush & (zh < line))
        lab_h = np.full(len(hi), NAMES.index('skin'))
        lab_h[hair] = NAMES.index('hair')
        lab_h[hair & (zh < 1.29) & (yh > 0.04)] = NAMES.index('hair_dark')
        lab_h[ear] = NAMES.index('skin')
        lab_h[zh < COLLAR_Z[0] - 0.01] = NAMES.index('ivory')
        keep = under[hi] >= 0
        under[hi[~keep]] = lab_h[~keep]
    stats['shopkeeper_rule_texels'] = int((blouse | arm_skin | neck | legs | shin).sum())


# ---------------------------------------------------------------- 手の部品（hand.py）

# 両手とも力を抜いて開いた手（hand.build_open）。素手。絵 shopkeeper_hands.png：大人の女性の細めの手。
# （絵の手首の生成りの袖口は、全身の 6 枚の絵では石墨の手首の帯なので作らない）
_S, _R = 1.0, 0.95
HAND = dict(
    GLOVE=None,
    LID='skin',
    OPEN_FINGERS=[(n, z * _S, x * _S, r * _R, tuple(v * _S for v in L), fan) for n, z, x, r, L, fan in (
        ('index', 0.0255, 0.068, 0.0080, (0.035, 0.022, 0.018), 6.0),
        ('middle', 0.0085, 0.071, 0.0083, (0.037, 0.024, 0.019), 1.0),
        ('ring', -0.0085, 0.068, 0.0078, (0.034, 0.022, 0.018), -4.0),
        ('pinky', -0.0240, 0.061, 0.0068, (0.027, 0.018, 0.015), -9.0))],
    OPEN_CURL=(14.0, 20.0, 14.0),
    CUFF_LID=(-0.012, 0.006),
    OPEN_THUMB=dict(base=(0.026, 0.008, 0.024), r=0.0088 * _R, lens=(0.033, 0.028, 0.023), out_deg=22.0,
                    palm_deg=34.0, curl=(8.0, 12.0, 10.0)),
    PALM_HALF_T=0.0115 * _R,
    PALM_WRIST=(0.002, 0.0, 0.016, 0.029),
    PALM_X=(0.012, 0.045),
    THENAR=((0.029, 0.007, 0.023), 0.0145),
    HYPOTHENAR=((0.035, 0.005, -0.021), 0.013),
    LEFT_HAND_CUT=-0.004,
    LEFT_HAND_RAMP=(-0.014, 0.006),
)
