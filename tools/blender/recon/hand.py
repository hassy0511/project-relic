"""ハルの右手を、銃の握りを握った形の部品として作る（6 回目。ai_character.py の --hand-part）。

前（5 回目まで）は、絵から起こした体の開いた手をシェイプキー 'fist' で曲げていた。GLB の既定の重みは 0 なので、
Godot 以外（確認ページの model-viewer など）では手が開いたまま銃が横に浮き、拳もミトンのような塊だった。
今は体の右手（手首から先）を消し、この部品に置き換える（基準の姿勢のまま握っている。切り替えは要らない）。

■ 形（すべて銃の座標で作る：銃身 +X、上 +Z、+Y は本人の左＝掌の向き。原点は握りの中ほど）
  - 指（人さし指〜小指）：3 つの節（基節・中節・末節）を、丸い棒（カプセル）でつなぐ。中指・薬指・小指は、
    その高さの握りの断面（銃のメッシュを高さで切った凸の多角形）の外側に沿って、節ごとに「握りに触れるまで
    曲げる」（節の棒が握りの面から半径＋GAP 離れる最大の角度）。人さし指は用心金に沿ってまっすぐ前へ（引き金の外）。
  - 親指：中手骨・基節・末節。握りの後ろ（背）を回って、左の側面を前へ。
  - 掌：手首の輪・指の付け根の玉・掌の内側の面・母指球・小指球の点の凸包（面のある手袋の板の見た目）。
    掌の点はすべて握りの右の面より外（y ≤ −(半幅 + GAP)）に置くので、凸包は握りに入らない。
  - 手袋：掌・母指球・各指の基節（絵 haru_hands.png：指の付け根の節だけ手袋、中節・末節は肌）は暗い灰、
    基節の手袋は少し太い筒で、端はまっすぐ切る（きれいな縁）。親指は基節まで手袋、末節は肌。
  - カフ：手首の太い暗い帯（体の前腕の断面と掌の手首の輪を覆う、角のある筒）。
色は costume.py の色見本（PALETTE）の番号。重みは ai_character.py が付ける（掌・指は hand.R に 1、
カフと手首の体は手首の前後でなめらかに）。
"""
from __future__ import annotations

import math

import numpy as np

try:
    from recon import costume as _CO
except ImportError:          # ai_character.py は recon のフォルダを sys.path に入れて import する
    import costume as _CO

# 寸法はキャラクターの部品の設定（chars/<id>_parts.py の HAND。ハルの値は haru_parts.py）
_H = _CO.HAND
GAP = _H.get('GAP', 0.0012)                 # 握りの面と指・掌の面の間（めり込まない・浮かない）
FINGERS = _H.get('FINGERS', [])             # 握る手の指：（名前, 高さ z, 半径, 節の長さ（基節・中節・末節））
THUMB = _H.get('THUMB', {})
GLOVE_FRAC = _H.get('GLOVE_FRAC', 0.80)     # 基節の手袋の筒は、付け根からこの割合まで（その先は肌）
GLOVE_THICK = _H.get('GLOVE_THICK', 0.0009)  # 手袋の筒の厚み（肌の棒より太い分）
MAX_BEND = math.radians(100)
SEG = 14              # 棒の周りの分割
SKIN = 'skin'
GRAPHITE = _H.get('GLOVE') or SKIN          # 手袋の色（手袋なしは肌）
HAS_GLOVE = bool(_H.get('GLOVE'))
LID = _H.get('LID', GRAPHITE)               # 開いた手のカフのふたの色


# ---------------------------------------------------------------- 2D の道具

def hull2d(p: np.ndarray) -> np.ndarray:
    """凸包（反時計回り）"""
    p = np.unique(np.round(p, 5), axis=0)
    p = p[np.lexsort((p[:, 1], p[:, 0]))]

    def half(pts):
        h = []
        for q in pts:
            while len(h) >= 2 and np.cross(h[-1] - h[-2], q - h[-2]) <= 0:
                h.pop()
            h.append(q)
        return h
    lo, up = half(p), half(p[::-1])
    return np.array(lo[:-1] + up[:-1])


def seg_dist(P: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """点の列 P から線分 ab への距離"""
    d = b - a
    t = np.clip(((P - a) @ d) / max(d @ d, 1e-12), 0, 1)
    return np.linalg.norm(P - (a + np.outer(t, d)), axis=1)


def poly_clear(poly: np.ndarray, a: np.ndarray, b: np.ndarray, n: int = 24) -> float:
    """線分 ab と凸多角形 poly の間の距離（中に入っていれば負）"""
    pts = a + np.outer(np.linspace(0, 1, n), b - a)
    E = np.roll(poly, -1, 0) - poly
    nrm = np.stack([E[:, 1], -E[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    inside_d = ((pts[:, None, :] - poly[None]) * nrm[None]).sum(-1).max(1)   # 外なら正（凸）
    best = np.inf
    for p, q in zip(poly, np.roll(poly, -1, 0)):
        best = min(best, float(seg_dist(np.array([p, q]), a, b).min()))
        best = min(best, float(seg_dist(pts, p, q).min()))
    if (inside_d < 0).any():
        return float(inside_d.min())
    return best


def section(P: np.ndarray, z: float, half: float) -> np.ndarray:
    """銃の点 P の高さ z±half の断面（XY の凸包）"""
    s = P[np.abs(P[:, 2] - z) < half]
    return hull2d(s[:, :2])


def wrap_chain(poly: np.ndarray, start: np.ndarray, d0: float, lens, clear: float, turn: float) -> list[np.ndarray]:
    """start から、節ごとに向きを turn の向き（+1 = 反時計回り）へ、握り（poly）から clear 離れる最大の角度まで曲げる"""
    J = [start]
    ang = d0
    for L in lens:
        best = None
        for k in range(0, int(math.degrees(MAX_BEND)) + 1):
            a = ang + turn * math.radians(k)
            b = J[-1] + L * np.array([math.cos(a), math.sin(a)])
            if poly_clear(poly, J[-1], b) >= clear:
                best = a
            else:
                break
        if best is None:
            best = ang
        ang = best
        J.append(J[-1] + L * np.array([math.cos(ang), math.sin(ang)]))
    return J


# ---------------------------------------------------------------- 3D の形

class Mesh:
    def __init__(self):
        self.V, self.F, self.C = [], [], []
        self.n = 0

    def add(self, V, F, color: str):
        V = np.asarray(V, float)
        F = np.asarray(F, int)
        # 面の向きを外へ（閉じた形の符号つきの体積が負なら裏返す。model-viewer・Godot は裏の面を描かない）
        vol = np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum()
        if vol < 0:
            F = F[:, ::-1]
        self.V.append(V)
        self.F.append(F + self.n)
        self.C += [color] * len(F)
        self.n += len(V)

    def arrays(self):
        return np.concatenate(self.V), np.concatenate(self.F), np.array(self.C)


def ortho(d: np.ndarray, ref=np.array([0.0, 0.0, 1.0])):
    u = ref - d * (ref @ d)
    if np.linalg.norm(u) < 1e-6:
        u = np.array([1.0, 0.0, 0.0]) - d * d[0]
    u /= np.linalg.norm(u)
    return u, np.cross(d, u)


def capsule(a, b, r0, r1, seg=SEG, rings=4):
    """a → b の丸い棒（端は半球）。半径は a で r0、b で r1"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.linalg.norm(d)
    d /= L
    u, v = ortho(d)
    prof = []   # (軸の位置, 半径)
    for i in range(rings, 0, -1):
        t = math.pi / 2 * i / rings
        prof.append((-r0 * math.sin(t), r0 * math.cos(t)))
    prof.append((0.0, r0))
    prof.append((L, r1))
    for i in range(1, rings + 1):
        t = math.pi / 2 * i / rings
        prof.append((L + r1 * math.sin(t), r1 * math.cos(t)))
    return lathe(a, d, u, v, prof, seg)


def lathe(a, d, u, v, prof, seg, close_ends=True):
    V, F = [], []
    th = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    ring_idx = []
    for (s, r) in prof:
        if r < 1e-7:
            ring_idx.append([len(V)])
            V.append(a + d * s)
            continue
        ids = list(range(len(V), len(V) + seg))
        for t in th:
            V.append(a + d * s + r * (math.cos(t) * u + math.sin(t) * v))
        ring_idx.append(ids)
    for r0, r1 in zip(ring_idx[:-1], ring_idx[1:]):
        # 向きをそろえる（どの辺も、隣の 2 枚の面で逆の向きにたどる）。外か内かは Mesh.add が体積で直す
        if len(r0) == 1:
            for k in range(seg):
                F.append((r0[0], r1[(k + 1) % seg], r1[k]))
        elif len(r1) == 1:
            for k in range(seg):
                F.append((r0[k], r0[(k + 1) % seg], r1[0]))
        else:
            for k in range(seg):
                k2 = (k + 1) % seg
                F.append((r0[k], r1[k2], r1[k]))
                F.append((r0[k], r0[k2], r1[k2]))
    if close_ends:
        for ids, first in ((ring_idx[0], True), (ring_idx[-1], False)):
            if len(ids) > 1:
                c = len(V)
                V.append(np.mean([V[i] for i in ids], 0))
                for k in range(seg):
                    k2 = (k + 1) % seg
                    F.append((c, ids[k2], ids[k]) if first else (c, ids[k], ids[k2]))
    return np.array(V), np.array(F)


def sleeve(a, b, r, seg=SEG, bevel=0.0006):
    """手袋の筒（端はまっすぐ、少し面取り）"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    L = np.linalg.norm(d)
    d /= L
    u, v = ortho(d)
    prof = [(0.0, r - bevel), (bevel, r), (L - bevel, r), (L, r - bevel)]
    return lathe(a, d, u, v, prof, seg)


def convex_hull3(P: np.ndarray):
    from scipy.spatial import ConvexHull
    h = ConvexHull(P)
    F = h.simplices.copy()
    c = P[h.vertices].mean(0)
    for i, f in enumerate(F):   # 外向きにそろえる
        n = np.cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]])
        if n @ (P[f[0]] - c) < 0:
            F[i] = f[::-1]
    used = np.unique(F)
    remap = -np.ones(len(P), int)
    remap[used] = np.arange(len(used))
    return P[used], remap[F]


def sphere_pts(c, r, n=40):
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * k / n)
    th = math.pi * (1 + 5 ** 0.5) * k
    return np.asarray(c) + r * np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def ring_shell(x0, x1, ys, zs, thick, bevel=0.002, sink=0.0):
    """X 軸に沿った角のある筒（断面は (ys, zs) の多角形、外へ thick）。外・内・両端の面。
    sink：後ろ（x0）の端の内の面を、これだけ内へ（体の中へ）すぼめる（カフと腕の間のすき間が見えない）"""
    n = len(ys)
    c = np.stack([ys, zs], 1)
    cen = c.mean(0)
    dirs = c - cen
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    inner, outer = c, c + dirs * thick
    outer_b = c + dirs * (thick - bevel)
    inner0 = c - dirs * sink
    rings = [(x0, inner0), (x0, outer_b), (x0 + bevel, outer), (x1 - bevel, outer), (x1, outer_b), (x1, inner)]
    V, F = [], []
    for x, ring in rings:
        for q in ring:
            V.append((x, q[0], q[1]))
    R = len(rings)
    for i in range(R):
        j = (i + 1) % R
        for k in range(n):
            k2 = (k + 1) % n
            a, b, cc, d = i * n + k, j * n + k, j * n + k2, i * n + k2
            F.append((a, cc, b))
            F.append((a, d, cc))
    return np.array(V), np.array(F)


# ---------------------------------------------------------------- 全体

def build(gun_pts: np.ndarray, wrist: np.ndarray, wrist_section: np.ndarray | None = None) -> dict:
    """銃の座標で手を作る。

    gun_pts：銃の表面の点（銃の座標）。wrist：手首の関節（銃の座標、手の骨の元）。
    wrist_section：体の前腕の手首の近くの断面の点（銃の座標の (y, z)）。カフの中心（外接の箱の中心）と大きさに使う
    （体の手首の関節は前腕の断面の中心から 1〜2cm ずれている）
    返り値：{V, F, color（面ごとの名前）, report}
    """
    M = Mesh()
    rep = {}
    gy_half = float(np.percentile(np.abs(gun_pts[(gun_pts[:, 2] < 0.0) & (gun_pts[:, 2] > -0.075), 1]), 99.5))
    y_side = -(gy_half + GAP)
    knuckles = []
    for name, z, r, lens in FINGERS:
        clear = r + GAP
        if name == 'index':
            # 用心金に沿ってまっすぐ前へ（右の側面の外）。少しだけ内へ寄せて側面に触れる
            j0 = np.array([0.006, y_side - r])
            J2 = [j0]
            for L in lens:
                J2.append(J2[-1] + np.array([L, 0.0]))
        else:
            poly = section(gun_pts, z, r * 0.85)
            x_front = poly[:, 0].max()
            ymin = poly[:, 1].min()
            j0 = np.array([x_front - 0.78 * lens[0], ymin - clear])
            J2 = wrap_chain(poly, j0, math.radians(-8), lens, clear, +1.0)
        J3 = [np.array([p[0], p[1], z]) for p in J2]
        rr = [r * 1.0, r * 0.97, r * 0.93, r * 0.86]
        for k in range(3):
            V, F = capsule(J3[k], J3[k + 1], rr[k], rr[k + 1])
            M.add(V, F, SKIN)
        dvec = (J3[1] - J3[0]) / np.linalg.norm(J3[1] - J3[0])
        V, F = sleeve(J3[0] - dvec * r * 0.9, J3[0] + (J3[1] - J3[0]) * GLOVE_FRAC, rr[0] + GLOVE_THICK)
        M.add(V, F, GRAPHITE)
        knuckles.append((J3[0], r))
        rep[name] = [p.round(4).tolist() for p in J3]

    # 親指：握りの後ろを回って左の側面へ（時計回り）
    zt, rt = THUMB['z'], THUMB['r']
    poly = section(gun_pts, zt, rt * 0.85)
    x_back = poly[:, 0].min()
    t0 = np.array([x_back - rt - 0.003, y_side - rt - 0.004])
    T2 = wrap_chain(poly, t0, math.radians(95), THUMB['lens'], rt + GAP, -1.0)
    T3 = [np.array([p[0], p[1], zt - 0.010 * (k == 0)]) for k, p in enumerate(T2)]
    rr = [rt * 1.15, rt, rt * 0.95, rt * 0.85]
    for k in range(3):   # 中手骨は手袋、基節・末節は肌（基節は手袋の筒をかぶせる。同じ半径の玉が重なって色がちらつかない）
        V, F = capsule(T3[k], T3[k + 1], rr[k], rr[k + 1])
        M.add(V, F, GRAPHITE if k == 0 else SKIN)
    d2 = (T3[2] - T3[1]) / np.linalg.norm(T3[2] - T3[1])
    V, F = sleeve(T3[1] - d2 * rt * 0.5, T3[1] + (T3[2] - T3[1]) * GLOVE_FRAC, rr[1] + GLOVE_THICK)
    M.add(V, F, GRAPHITE)
    rep['thumb'] = [p.round(4).tolist() for p in T3]

    # 掌：点の凸包（すべて y ≤ y_side）
    pts = []
    for c, r in knuckles:
        pts.append(sphere_pts(c, r))
        pts.append(sphere_pts(c + np.array([-0.012, -0.004, 0.0]), r))
    ztop = FINGERS[0][1] + FINGERS[0][2]
    zbot = FINGERS[-1][1] - FINGERS[-1][2]
    xk = min(c[0] for c, _ in knuckles)
    for x in (-0.036, xk - 0.004):
        for z in (ztop, zbot):
            pts.append(np.array([[x, y_side, z]]))
    # 手首の輪（前腕の断面の中心のまわりの楕円）。上下（z）は掌の幅、左右（y）は厚み
    if wrist_section is not None and len(wrist_section) > 8:
        lo, hi = np.percentile(wrist_section, 2, axis=0), np.percentile(wrist_section, 98, axis=0)
        cy, cz = (lo + hi) / 2
    else:
        cy, cz = wrist[1], wrist[2]
    wy, wz = 0.018, 0.027
    th = np.linspace(0, 2 * math.pi, 16, endpoint=False)
    for dx in (-0.014, 0.004):
        ring = np.stack([np.full(16, wrist[0] + dx), cy + wy * np.cos(th), cz + wz * np.sin(th)], 1)
        ring[:, 1] = np.minimum(ring[:, 1], y_side)
        pts.append(ring)
    # 母指球（親指の付け根）・小指球（掌の下の後ろ）
    pts.append(sphere_pts([T3[0][0] - 0.002, min(T3[0][1], y_side - 0.012), T3[0][2] - 0.004], 0.012))
    pts.append(sphere_pts([wrist[0] + 0.03, y_side - 0.011, zbot + 0.012], 0.011))
    P = np.concatenate(pts)
    P[:, 1] = np.minimum(P[:, 1], y_side)
    V, F = convex_hull3(P)
    M.add(V, F, GRAPHITE)

    # カフ（手首の暗い帯）：前腕の断面と掌の手首の輪を覆う角のある筒
    n = 16
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rad = np.sqrt((wy * np.cos(ang)) ** 2 + (wz * np.sin(ang)) ** 2) + 0.003
    if wrist_section is not None and len(wrist_section) > 8:
        rel = wrist_section - np.array([cy, cz])
        a = np.arctan2(rel[:, 1], rel[:, 0])
        rr_ = np.linalg.norm(rel, axis=1)
        for i, t in enumerate(ang):
            dd = np.abs((a - t + math.pi) % (2 * math.pi) - math.pi)
            m = dd < math.radians(25)
            if m.sum() >= 2:
                rad[i] = max(rad[i], float(np.percentile(rr_[m], 90)) + 0.0025)
        for _ in range(2):
            rad = np.maximum(rad, (np.roll(rad, 1) + np.roll(rad, -1) + 2 * rad) / 4)
    ys, zs = cy + rad * np.cos(ang), cz + rad * np.sin(ang)
    V, F = ring_shell(wrist[0] - 0.032, wrist[0] + 0.010, ys, zs, 0.0055, sink=0.012)
    M.add(V, F, GRAPHITE)
    rep['cuff_radius'] = [round(float(rad.min()), 4), round(float(rad.max()), 4)]

    V, F, C = M.arrays()
    return {'V': V, 'F': F, 'color': C, 'report': rep, 'y_side': y_side}


# ---------------------------------------------------------------- 左の開いた手（8 回目）

# 手の座標（手首の関節が原点）：+X = 手の骨の向き（指の先へ）、+Y = 掌の向き（体の内側）、+Z = 親指の側（正面）。
# 寸法は右手の部品と同じ指の太さ・節の長さ（絵 haru_hands.png：力を抜いて開いた手。手袋は掌と指の付け根の節、
# 中節・末節と親指の先は肌）。指は節ごとに少しずつ掌へ曲げ、少し扇に開く
OPEN_FINGERS = _H.get('OPEN_FINGERS', [])   # 名前, 付け根の z, 付け根の x, 半径, 節の長さ, 扇の角度（度、+ = 親指の側）
OPEN_CURL = _H.get('OPEN_CURL', (12.0, 16.0, 12.0))    # 節ごとの掌への曲げ（度、付け根の節から）
CUFF_LID = _H.get('CUFF_LID', (-0.004, 0.016))        # カフのふたの x の範囲（手首からの距離）
OPEN_THUMB = _H.get('OPEN_THUMB', {})
PALM_HALF_T = _H.get('PALM_HALF_T', 0.0115)            # 掌の厚みの半分（指の付け根）
PALM_WRIST = _H.get('PALM_WRIST', (0.002, 0.0, 0.0125, 0.024))
THENAR = _H.get('THENAR', ((0.026, 0.006, 0.020), 0.012))
HYPOTHENAR = _H.get('HYPOTHENAR', ((0.032, 0.004, -0.018), 0.011))
PALM_X = _H.get('PALM_X', (0.012, 0.040))            # 掌の甲・内の面の点の x（手首からの距離）


def build_open(wrist_section: np.ndarray | None = None) -> dict:
    """力を抜いて開いた手（手の座標）。wrist_section：体の手首の断面の点（手の座標の (y, z)）。
    返り値：{V, F, color, report}"""
    M = Mesh()
    rep = {}
    knuckles = []

    def chain(p0, d, n_palm, lens, curl):
        J = [np.asarray(p0, float)]
        d = np.asarray(d, float) / np.linalg.norm(d)
        for L, c in zip(lens, curl):
            a = math.radians(c)       # 掌の向き（n_palm）へ曲げる
            d = d * math.cos(a) + n_palm * math.sin(a)
            d /= np.linalg.norm(d)
            n_palm = n_palm - d * (n_palm @ d)
            n_palm /= np.linalg.norm(n_palm)
            J.append(J[-1] + L * d)
        return J

    for name, z, x, r, lens, fan in OPEN_FINGERS:
        f = math.radians(fan)
        d0 = np.array([math.cos(f), 0.0, math.sin(f)])
        J = chain((x, 0.001, z), d0, np.array([0.0, 1.0, 0.0]), lens, OPEN_CURL)
        rr = [r, r * 0.96, r * 0.92, r * 0.85]
        for k in range(3):
            V, F = capsule(J[k], J[k + 1], rr[k], rr[k + 1])
            M.add(V, F, SKIN)
        dv = (J[1] - J[0]) / np.linalg.norm(J[1] - J[0])
        if HAS_GLOVE:
            V, F = sleeve(J[0] - dv * r * 0.9, J[0] + (J[1] - J[0]) * GLOVE_FRAC, rr[0] + GLOVE_THICK)
            M.add(V, F, GRAPHITE)
        knuckles.append((J[0], r))
        rep[name] = [p.round(4).tolist() for p in J]
    # 親指：掌の付け根から、親指の側（+Z）へ out_deg・掌（+Y）へ palm_deg 傾けて伸ばす
    th = OPEN_THUMB
    a, b = math.radians(th['out_deg']), math.radians(th['palm_deg'])
    d0 = np.array([math.cos(a) * math.cos(b), math.sin(b), math.sin(a) * math.cos(b)])
    T = chain(th['base'], d0, np.array([0.0, 1.0, -0.4]) / np.linalg.norm([0.0, 1.0, -0.4]), th['lens'], th['curl'])
    rt = th['r']
    rr = [rt * 1.15, rt, rt * 0.95, rt * 0.85]
    for k in range(3):     # 中手骨は手袋（掌の凸包にも入る）、基節は手袋の筒、末節は肌
        V, F = capsule(T[k], T[k + 1], rr[k], rr[k + 1])
        M.add(V, F, GRAPHITE if k == 0 else SKIN)
    d2 = (T[2] - T[1]) / np.linalg.norm(T[2] - T[1])
    if HAS_GLOVE:
        V, F = sleeve(T[1] - d2 * rt * 0.5, T[1] + (T[2] - T[1]) * GLOVE_FRAC, rr[1] + GLOVE_THICK)
        M.add(V, F, GRAPHITE)
    rep['thumb'] = [p.round(4).tolist() for p in T]
    # 掌：指の付け根の玉・掌の甲と内の面・手首の輪・母指球・小指球の凸包
    pts = []
    for c, r in knuckles:
        pts.append(sphere_pts(c, r * 1.05))
        pts.append(sphere_pts(c + np.array([-0.014, 0.0, 0.0]), r * 1.1))
    zt = OPEN_FINGERS[0][1] + OPEN_FINGERS[0][3]
    zb = OPEN_FINGERS[-1][1] - OPEN_FINGERS[-1][3]
    for x in PALM_X:
        for z in (zt, zb + 0.002):
            for y in (-PALM_HALF_T + 0.002, PALM_HALF_T - 0.001):
                pts.append(np.array([[x, y, z]]))
    # 掌の手首の側は掌の太さ（体の手首の断面は手袋のカフのふくらみで直径 9cm もあり、掌が円すいになった）
    cy, cz, wy, wz = PALM_WRIST
    ang = np.linspace(0, 2 * math.pi, 20, endpoint=False)
    for x in (0.004, 0.014):
        pts.append(np.stack([np.full(20, x), cy + wy * np.cos(ang), cz + wz * np.sin(ang)], 1))
    pts.append(sphere_pts(THENAR[0], THENAR[1]))      # 母指球
    pts.append(sphere_pts(HYPOTHENAR[0], HYPOTHENAR[1]))     # 小指球
    V, F = convex_hull3(np.concatenate(pts))
    M.add(V, F, GRAPHITE)
    # カフのふた：手袋のカフ（costume の glove_cuff.L）の先の口をふさぐ暗い栓（体の手首の断面＋2mm、先の縁は面取り）
    if wrist_section is not None and len(wrist_section) > 8:
        sec = np.asarray(wrist_section, float)
        c0 = np.median(sec, 0)
        rel = sec - c0
        a = np.arctan2(rel[:, 1], rel[:, 0])
        rr = np.linalg.norm(rel, axis=1)
        n = 24
        an = np.linspace(-math.pi, math.pi, n, endpoint=False)
        rad = np.array([np.percentile(rr[np.abs((a - t + math.pi) % (2 * math.pi) - math.pi) < math.radians(30)], 90)
                        if (np.abs((a - t + math.pi) % (2 * math.pi) - math.pi) < math.radians(30)).sum() >= 2
                        else np.median(rr) for t in an]) + 0.002
        lid = []
        for x, k in ((CUFF_LID[0], 1.0), (CUFF_LID[1] - 0.002, 1.0), (CUFF_LID[1], 0.88)):
            lid.append(np.stack([np.full(n, x), c0[0] + k * rad * np.cos(an), c0[1] + k * rad * np.sin(an)], 1))
        V, F = convex_hull3(np.concatenate(lid))
        M.add(V, F, LID)
        rep['cuff_lid_radius'] = [round(float(rad.min()), 4), round(float(rad.max()), 4)]
    rep['wrist_ellipse'] = [round(float(v), 4) for v in (cy, cz, wy, wz)]
    V, F, C = M.arrays()
    return {'V': V, 'F': F, 'color': C, 'report': rep}
