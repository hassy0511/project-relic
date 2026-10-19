"""ジャンク屋（junker）の服の部品と塗りの決まり（costume.py が読み込む。書式は chars/shopkeeper_parts.py・trude_parts.py と同じ）。

部品の表：docs/art_orders/W2_ジャンク屋3D化の結果.md の 1 章。寸法は calib.json のカメラで絵（W2-01・W2-01b の junker_*.png）に
1cm の格子を重ねて読んだ（build/junker/tools/grid.py。再構築の座標：身長 1.55m。本来の 1.65m へは骨付けの段で 1.065 倍）。
本人の左 = +X、正面 = −Y。
  二重の首巻き（生成りの太い輪 2 段）・ベストの襟（下襟 ×2）・ベストの前の縁 ×2・ベストの裾の帯・前のポケット ×2（蓋・鋲）・
  後ろのポケット ×2（蓋）・背中の切り替えの線・ポケットの道具（本人の右：灰の筒と真鍮の筒、左：穴のある灰の塊）・
  ベルトとバックル（前の開きだけ）・胸のルーペ（真鍮の輪・ガラス・吊り金具・首ひも）・シャツの袖の折り返し ×2・
  ズボンの裾の折り返し ×2・膝の当て布 ×2（縫い目）・靴 ×2（底・爪先・胴・足首の帯・留め具）・
  髪（帽子は形の段、房は葉の形の部品：つむじから放射状の 3 段・前髪・右目にかかる長い房・耳の前の房）・あごひげ。
  手は hand.py の開いた手（素手、肌）。
塗りの決まり（body_rules）：ベストの裾より上の胴は焦げ茶のベスト（前の開きはシャツの生成り、ベルトより下はズボン）、
腕はシャツの生成り（袖の折り返しより先は肌）、裾より下はズボンの赤錆、首は肌、頭は形の場。
"""
from __future__ import annotations

import math
import os

import numpy as np

# 色：spec（W2-01 spec.md・spec_townsfolk_3d.md、W2-01b spec_townsfolk_3d_add.md）の色見本を基に、絵の平らに照らされた所の
# 中央値（build/junker/tools/colors.py）へ寄せた。spec と違う色は結果の文書の 4 章
PALETTE = {
    'vest': '#5F4434',        # ベスト（焦げ茶の厚布。絵 #644735・#604432、spec #594333）
    'vest_light': '#6E4F3B',  # 下襟・ポケット・蓋（絵 #6F4F3A・#704F3B。同じ色では輪郭が消える）
    'vest_dark': '#3B2B21',   # 切り替えの線・裾の帯の下の面・ポケットの口
    'ivory': '#EDD5B9',       # シャツ（生成りの木綿。絵 #F2D2B2、spec #F3E9D2）
    'wrap': '#E3C6A6',        # 首巻き（絵 #E7C5A3・#EBC9A6。シャツと分かれるよう少し暗く）
    'wrap_in': '#A88A70',     # 首巻きの内側（上の口の中）
    'roll': '#E2C2A2',        # シャツの袖の折り返し（絵 #E9C5A4）
    'rust': '#9C5038',        # ズボン（赤錆の厚布。絵 #A65638、spec #B75B43。店主の前掛けと同じく確認ページで明るく見える分を下げた）
    'cuff': '#C49A74',        # ズボンの裾の折り返し（絵 #D09F74）
    'patch': '#B88C66',       # 膝の当て布（絵 #C69569、spec #C6AB88）
    'stitch': '#5A4034',      # 当て布の縫い目
    'belt': '#332A23',        # ベルト（絵 #332A23）
    'brass': '#B48548',       # バックル・ルーペの輪・鋲（絵 #C68E48・#C78A3F、spec #A98749）
    'glass': '#C2C8C0',       # ルーペのガラス（非発光の鈍い薄灰。絵 #CEC8B7、spec #B9C8C7）
    'cord': '#2E2A27',        # ルーペの首ひも
    'tool': '#7C7A74',        # ポケットの道具（くすんだ金属。絵 #83776B、spec #7F8381）
    'tool_dark': '#4A4844',   # 道具の穴・端
    'tool_brass': '#A8743A',  # 真鍮の筒（絵 #A36932）
    'skin': '#E7B58D',
    'hair': '#A8917C',        # 砂灰の髪：房の上の面（絵の照った面 #D4B195・#CCAC8F、spec #C6B9A4。確認ページの描画は絵より明るく、
                              # 1 回目の #BCA48E は白に見えた）
    'hair_shadow': '#8A7462',  # 房の横・下の面（絵の陰の面 #A07B63〜#AE8D71）
    'hair_dark': '#7D6858',   # 髪の土台（房のすき間に見える内側の髪。房の陰の色に近く：1 回目は房との差でまだらに見えた）
    'boot': '#4E3C30',        # 靴の胴（絵 #513E30）
    'boot_strap': '#5F4535',  # 足首の帯（絵 #664936）
    'toe': '#8E664C',         # 爪先（絵 #9C7052）
    'sole': '#3B322C',        # 靴底（絵 #433831、spec #444641）
}
NAMES = list(PALETTE)
CELLS = 32

X0 = 0.0015     # 顔・首の左右の中心（正面の絵の 2 つの目の中点）
AX_Y = 0.005    # 胴の縦の軸の前後

# A ポーズの関節（chars/junker.json の joints.ART_XZ と同じ x・z。y は形の段のメッシュの腕の中心）
J = {
    'upper_arm': (0.195, 0.0, 1.135), 'forearm': (0.298, 0.02, 0.94), 'hand': (0.39, 0.02, 0.775),
    'hand_end': (0.455, 0.02, 0.615), 'thigh': (0.10, 0.0, 0.75), 'shin': (0.152, 0.0, 0.42),
    'foot': (0.183, 0.0, 0.09),
}
FOLLOW_BODY = ('wrap', 'wrap_in', 'lapel0.L', 'lapel0.R', 'lapel1.L', 'lapel1.R', 'cord.L', 'cord.R')
FOLLOW_TORSO_ONLY = FOLLOW_BODY
BOX_RULES: list = []

VEST_HEM = (0.742, 0.772)       # ベストの裾の帯の下・上
VEST_SIDE = ([0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20],      # ベストの横の縁（正面の絵）：高さ → |x|
             [0.240, 0.240, 0.235, 0.230, 0.228, 0.220, 0.205, 0.190, 0.180, 0.170])
BELT_Z = (0.857, 0.905)         # ベルト（前の開きに見える所）
SHIRT_TOP = 1.215               # 前の開きのシャツの上（首巻きの下）
NECK_TOP = 1.272                # あごの下
ROLL_T = (-0.020, 0.085)        # シャツの袖の折り返し：前腕の軸に沿った肘からの長さ
TROUSER_CUFF = (0.205, 0.290)   # ズボンの裾の折り返しの下・上
# 前の開き（シャツが見える所）の半幅：高さ → |x|。正面の絵：首巻きの下 0.075、胸 0.068、ベルトの上 0.070、裾 0.072
OPEN = ([0.74, 0.86, 0.95, 1.05, 1.15, 1.22], [0.072, 0.070, 0.070, 0.066, 0.072, 0.080])
# 顔のまわりの髪の塗りの下の線（|x − X0| → z）。正面の絵の生え際（額 1.455、こめかみ 1.40、耳の上 1.395）
HAIRLINE_PAINT = ([0.0, 0.03, 0.05, 0.065, 0.08, 0.10, 0.15], [1.458, 1.452, 1.440, 1.422, 1.400, 1.395, 1.395])
BOOT_CUT = 0.215        # この高さより下の脚の体は消して、靴の部品に置き換える（ズボンの裾の折り返しの中で切る）
BOOT_RAMP = (0.07, 0.16)
BOOT_CUT_X = (0.02, 0.40)
RIGHT_HAND_PART = True


# ---------------------------------------------------------------- 形の段のメッシュの測り

_MESH = None
_BVH = None


def _mesh_npz():
    global _MESH
    if _MESH is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'build', 'junker',
                         'junker_mesh.npz')
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


def surf_r(th, z, cy: float = AX_Y, cx: float = 0.0, r_max: float = 0.45, last: bool = False) -> np.ndarray:
    """縦の軸 (cx, cy) から、正面からの角度 th（ラジアン、+ = 本人の左）・高さ z の水平な向きへ撃って最初に当たる体の面の半径。
    軸から外へ撃つので、胴の横に下がる腕より先に胴の面に当たる。last：r_max までで一番外の面（首のまわりは頭の首の殻が
    体の土台の殻の中に重なっていて、最初に当たるのは首の殻だった）"""
    from mathutils import Vector
    bvh = _bvh()
    th = np.atleast_1d(np.asarray(th, float))
    z = np.broadcast_to(np.asarray(z, float), th.shape)
    out = np.zeros(th.shape)
    for i, (t, zz) in enumerate(zip(th.ravel(), z.ravel())):
        d = Vector((math.sin(t), -math.cos(t), 0.0))
        o = Vector((cx, cy, float(zz)))
        best, start = None, 0.0
        while True:
            hit = bvh.ray_cast(o + d * start, d, r_max - start)
            if hit[0] is None:
                break
            best = start + hit[3]
            if not last:
                break
            start = best + 1e-4
        out.ravel()[i] = best if best is not None else 0.12
    return out


def front_hit(x, z, y0: float = -0.6) -> np.ndarray:
    """前（−Y）から +Y へ撃って最初に当たる体の面の y"""
    from mathutils import Vector
    bvh = _bvh()
    x = np.atleast_1d(np.asarray(x, float))
    z = np.broadcast_to(np.asarray(z, float), x.shape)
    out = np.zeros(x.shape)
    for i, (xx, zz) in enumerate(zip(x.ravel(), z.ravel())):
        hit = bvh.ray_cast(Vector((float(xx), y0, float(zz))), Vector((0.0, 1.0, 0.0)), 1.2)
        out.ravel()[i] = hit[0][1] if hit[0] is not None else -0.10
    return out


def smooth_grid(a: np.ndarray, it: int = 3, wrap: bool = False) -> np.ndarray:
    """格子の値を近所でならす（行・列の両方。wrap は列が一周）"""
    a = a.copy()
    for _ in range(it):
        b = a.copy()
        b[1:-1] = 0.5 * a[1:-1] + 0.25 * (a[:-2] + a[2:])
        if wrap:
            b = 0.5 * b + 0.25 * (np.roll(b, 1, 1) + np.roll(b, -1, 1))
        else:
            b[:, 1:-1] = 0.5 * b[:, 1:-1] + 0.25 * (b[:, :-2] + b[:, 2:])
        a = b
    return a


# ---------------------------------------------------------------- 小さな形（面をそのまま渡す部品）

def _orient(V, F):
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    vol = np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum()
    return V, (F[:, ::-1] if vol < 0 else F)


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


def cyl_mesh(a, b, r, n=12, r2=None):
    """a → b の円柱（両端はふた）。r2：b の端の半径（円すい台）"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    d /= np.linalg.norm(d)
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e0 = np.cross(d, ref)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(d, e0)
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(ang)[:, None] * e0 + np.sin(ang)[:, None] * e1
    r2 = r if r2 is None else r2
    V = np.concatenate([a + circ * r, b + circ * r2, [a, b]])
    F = []
    for i in range(n):
        i2 = (i + 1) % n
        F += [(i, i2, n + i2), (i, n + i2, n + i), (2 * n, i2, i), (2 * n + 1, n + i, n + i2)]
    return _orient(V, F)


def ring_mesh(c, axis, up, r_out, r_in, depth, n=24):
    """軸 axis の向きの平たい輪（外径 r_out・内径 r_in・厚み depth）"""
    c, axis, up = (np.asarray(v, float) for v in (c, axis, up))
    axis = axis / np.linalg.norm(axis)
    e0 = up - axis * np.dot(up, axis)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(axis, e0)
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(ang)[:, None] * e0 + np.sin(ang)[:, None] * e1
    rings = [c + circ * r_out, c + axis * depth + circ * r_out, c + axis * depth + circ * r_in, c + circ * r_in]
    V = np.concatenate(rings)
    F = []
    for k in range(4):
        k2 = (k + 1) % 4
        for i in range(n):
            i2 = (i + 1) % n
            F += [(k * n + i, k2 * n + i, k2 * n + i2), (k * n + i, k2 * n + i2, k * n + i2)]
    return _orient(V, F)


def disc_mesh(c, axis, up, r, depth, n=16):
    c, axis, up = (np.asarray(v, float) for v in (c, axis, up))
    axis = axis / np.linalg.norm(axis)
    e0 = up - axis * np.dot(up, axis)
    e0 /= np.linalg.norm(e0)
    e1 = np.cross(axis, e0)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    circ = np.cos(a)[:, None] * e0 + np.sin(a)[:, None] * e1
    V = np.concatenate([c + circ * r, c + axis * depth + circ * r * 0.85, [c, c + axis * depth]])
    F = []
    for i in range(n):
        i2 = (i + 1) % n
        F += [(i, n + i, n + i2), (i, n + i2, i2), (2 * n, i2, i), (2 * n + 1, n + i, n + i2)]
    return _orient(V, F)


def slab(outer: np.ndarray, inner: np.ndarray, wrap: bool = False):
    """格子 (行, 列, 3) の外の面と内の面を、縁の壁でつないだ閉じた板。wrap は列が一周"""
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


def _loft(secs: np.ndarray):
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


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def wrap_panel(th0, th1, z0, z1, off, thick, nth=9, nz=7, cy=AX_Y, cx=0.0, zb=None, zt=None):
    """縦の軸のまわりの、体の面に沿った板（角度 th0〜th1（度）、高さ z0〜z1）。zb(th)・zt(th)：下・上の縁の高さを角度で変える。
    体の面（軸から撃った半径）＋ off に内の面、その thick 外に外の面"""
    degs = np.linspace(th0, th1, nth)
    ths = np.radians(degs)
    Z = np.array([[(zb(t) if zb else z0) * (1 - f) + (zt(t) if zt else z1) * f for t in degs]
                  for f in np.linspace(0.0, 1.0, nz)])
    Rr = np.array([surf_r(ths, Z[k], cy, cx) for k in range(nz)])
    Rr = smooth_grid(Rr, 2) + off
    S, Cc = np.sin(ths)[None], np.cos(ths)[None]
    inner = np.stack([cx + Rr * S, cy - Rr * Cc, Z], -1)
    outer = np.stack([cx + (Rr + thick) * S, cy - (Rr + thick) * Cc, Z], -1)
    return slab(outer, inner)


# ---------------------------------------------------------------- 首巻き（二重の太い輪）

# 首巻きの断面（正面・右真横の絵）：高さ → 左右の半幅 a・前 bf・後ろ bb。下の輪（1.165〜1.232）と上の輪（1.228〜1.288）、
# 間に浅い溝。上の口は首の 8mm 外まで内へ巻き込む
WRAP = dict(z=[1.160, 1.172, 1.190, 1.208, 1.222, 1.230, 1.240, 1.255, 1.268, 1.279, 1.286, 1.290],
            a=[0.090, 0.100, 0.106, 0.106, 0.100, 0.096, 0.098, 0.098, 0.095, 0.090, 0.083, 0.074],
            bf=[0.070, 0.080, 0.088, 0.090, 0.086, 0.082, 0.085, 0.087, 0.085, 0.080, 0.073, 0.064],
            bb=[0.085, 0.095, 0.102, 0.104, 0.100, 0.097, 0.100, 0.103, 0.103, 0.100, 0.094, 0.085])
WRAP_CY = 0.0
WRAP_MID = 1.232    # 2 つの輪の間の溝
NECK_R = (0.046, 0.050)     # 首の半径（x, y）：上の口の内側


def wrap_parts() -> list[dict]:
    n = 48
    th = np.linspace(-math.pi, math.pi, n, endpoint=False)
    s, c = np.sin(th), np.cos(th)
    e = 2.0 / 2.3
    secs = []
    for i, z in enumerate(WRAP['z']):
        a, bf, bb = WRAP['a'][i], WRAP['bf'][i], WRAP['bb'][i]
        x = X0 + a * np.sign(s) * np.abs(s) ** e
        b = np.where(c >= 0, bf, bb)
        y = WRAP_CY - b * np.sign(c) * np.abs(c) ** e
        P = np.stack([x, y, np.full(n, z)], 1)
        if z >= 1.172:
            # 体の土台（外形のレンズ。首巻きの外形を含む）より外へ：体の面 + 6mm。肩（決めた断面より 3.5cm 以上外）では
            # 決めた断面のまま肩の中へ沈める（1 回目は 1.20 より下を決めた断面のままにし、体の土台が首巻きの下の輪から
            # ベスト・肌の色の斑点で出た）
            rb = surf_r(th, np.full(n, z), WRAP_CY, X0, 0.16, last=True) + 0.006
            rr = np.hypot(x - X0, y - WRAP_CY)
            # 1.195 より上は体の土台を必ず覆う（体の土台の首は外形のレンズで、斜め 45 度の角が断面より 3cm 外に出ていた）
            want = np.maximum(rr, rb) if z >= 1.195 else np.where(rb < rr + 0.035, np.maximum(rr, rb), rr)
            k = want / np.maximum(rr, 1e-6)
            for _ in range(3):
                k = 0.5 * k + 0.25 * (np.roll(k, 1) + np.roll(k, -1))
            P[:, 0] = X0 + (x - X0) * k
            P[:, 1] = WRAP_CY + (y - WRAP_CY) * k
        secs.append(P)
    # 上の口：内へ巻き込み、首の 8mm 外を下りる
    for z, f in ((1.287, 0.55), (1.280, 0.0), (1.250, 0.0)):
        x_in = X0 + (NECK_R[0] + 0.008) * s
        y_in = WRAP_CY - (NECK_R[1] + 0.008) * c
        last = secs[-1] if f > 0 else None
        if last is not None:
            x_in = x_in * (1 - f) + last[:, 0] * f
            y_in = y_in * (1 - f) + last[:, 1] * f
        secs.append(np.stack([x_in, y_in, np.full(n, z)], 1))
    secs = np.array(secs)
    # 上の輪は前で低い（正面の絵：あごの下で上の縁が V に 1.26 まで下がる。横・後ろは 1.285〜1.29）
    ztop = 1.290 - 0.028 * np.cos(th / 2.0) ** 4
    k = (ztop - WRAP_MID) / (1.290 - WRAP_MID)
    zz = secs[:, :, 2]
    secs[:, :, 2] = np.where(zz > WRAP_MID, WRAP_MID + (zz - WRAP_MID) * k[None, :], zz)
    V, F = _loft(secs)
    # 内側の面（上の口から下）は暗い色
    k_in = len(WRAP['z'])
    is_in = np.array([min(a, b, c_) >= k_in * n for a, b, c_ in F]) | (F.max(1) >= len(secs) * n)
    out = [dict(name='wrap', bone='neck', color='wrap', mesh=(V, F[~is_in])),
           dict(name='wrap_in', bone='neck', color='wrap_in', mesh=(V, F[is_in]))]
    return out


# ---------------------------------------------------------------- ベスト

def vest_parts() -> list[dict]:
    P = []
    # 下襟 ×2：正面の絵の多角形（x, z）。前から撃った胸の面の 4〜10mm 前の板（厚み 6mm）
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        # 上の縁（首巻きの下）→ 肩の外の角 → 刻み → 下の先（前の開きの縁）
        quads = [
            [(0.070, 1.200), (0.150, 1.178), (0.142, 1.150), (0.076, 1.150)],     # 上の襟（首巻きの下から肩へ）
            [(0.076, 1.152), (0.140, 1.140), (0.100, 1.060), (0.068, 1.030)],     # 下襟（刻みの下から前の開きの先へ）
        ]
        for qi, q in enumerate(quads):
            q = np.array(q)
            U, Vv = np.meshgrid(np.linspace(0, 1, 7), np.linspace(0, 1, 6))
            # 双一次の 4 隅：0=左下... ここでは q の順（上の左, 上の右, 下の右, 下の左）
            pts = ((1 - U) * (1 - Vv))[..., None] * q[0] + (U * (1 - Vv))[..., None] * q[1] + \
                  (U * Vv)[..., None] * q[2] + ((1 - U) * Vv)[..., None] * q[3]
            xs, zs = side * pts[..., 0], pts[..., 1]
            yb = front_hit(xs.ravel(), zs.ravel()).reshape(xs.shape)
            yb = smooth_grid(yb, 2)
            lift = 0.005 + 0.004 * (1 - Vv) if qi == 0 else 0.005 + 0.003 * (1 - U)
            inner = np.stack([xs, yb - lift, zs], -1)
            outer = np.stack([xs, yb - lift - 0.006, zs], -1)
            if side < 0:
                inner, outer = inner[:, ::-1], outer[:, ::-1]
            V, F = slab(outer, inner)
            P.append(dict(name=f'lapel{qi}{sx}', bone='chest', color='vest_light', mesh=(V, F)))
        # 前の開きの縁（下襟の先から裾まで）：幅 2cm の帯
        zs = np.linspace(VEST_HEM[0] + 0.004, 1.045, 14)
        xo = np.interp(zs, OPEN[0], OPEN[1])
        xs = np.stack([xo, xo + 0.022], 1) * side
        zz = np.stack([zs, zs], 1)
        yb = front_hit(xs.ravel(), zz.ravel()).reshape(xs.shape)
        yb = smooth_grid(yb, 2)
        inner = np.stack([xs, yb - 0.003, zz], -1)
        outer = np.stack([xs, yb - 0.008, zz], -1)
        if side < 0:
            inner, outer = inner[:, ::-1], outer[:, ::-1]
        V, F = slab(outer, inner)
        P.append(dict(name='vest_edge' + sx, bone='spine', color='vest', mesh=(V, F)))
        # 前のポケット：胴の角（正面から 33〜84 度、z 0.765〜0.905）。体の面から 6mm、厚み 1.4cm の袋
        sgn = side
        V, F = wrap_panel(sgn * 33.0, sgn * 84.0, 0.765, 0.902, 0.004, 0.014, nth=11, nz=7)
        P.append(dict(name='pocket' + sx, bone='hips', color='vest_light', mesh=(V, F)))
        # 蓋（0.862〜0.916、下の縁の角を少し上げる）
        V, F = wrap_panel(sgn * 31.5, sgn * 85.5, 0.862, 0.916, 0.019, 0.006, nth=13, nz=4,
                          zb=lambda t: 0.862 + 0.010 * smoothstep((abs(t) - 70.0) / 15.0) + 0.006 * smoothstep((40.0 - abs(t)) / 8.0))
        P.append(dict(name='pocket_flap' + sx, bone='hips', color='vest_light', mesh=(V, F)))
        # 蓋の真鍮の鋲 ×2
        for k, a_ in enumerate((40.0, 76.0)):
            t_ = math.radians(sgn * a_)
            r_ = float(surf_r([t_], [0.874])[0]) + 0.026
            cpt = np.array([r_ * math.sin(t_), AX_Y - r_ * math.cos(t_), 0.874])
            nrm = np.array([math.sin(t_), -math.cos(t_), 0.0])
            Vd, Fd = disc_mesh(cpt - nrm * 0.002, nrm, (0, 0, 1), 0.0055, 0.004, 10)
            P.append(dict(name=f'pocket_stud{k}' + sx, bone='hips', color='brass', mesh=(Vd, Fd)))
        # 後ろのポケット（正面から 122〜166 度、z 0.775〜0.93）と、真ん中が下がった蓋（0.865〜0.935）
        V, F = wrap_panel(sgn * 122.0, sgn * 166.0, 0.775, 0.928, 0.004, 0.013, nth=10, nz=7)
        P.append(dict(name='pocket_back' + sx, bone='hips', color='vest_light', mesh=(V, F)))
        mid = 144.0
        V, F = wrap_panel(sgn * 120.5, sgn * 167.5, 0.868, 0.936, 0.017, 0.006, nth=13, nz=4,
                          zb=lambda t: 0.866 + 0.020 * min(1.0, abs(abs(t) - mid) / 23.0))
        P.append(dict(name='pocket_back_flap' + sx, bone='hips', color='vest_light', mesh=(V, F)))
    # 裾の帯（ぐるり、前の開き ±24 度は除く）：体の面から 3mm、厚み 9mm。後ろの真ん中と左右の 3 枚
    P.append(dict(name='vest_hem_back', bone='hips', color='vest', mesh=wrap_panel(157.0, 203.0, VEST_HEM[0], VEST_HEM[1],
                                                                                    0.003, 0.009, nth=9, nz=3)))
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        P.append(dict(name='vest_hem' + sx, bone='hips', color='vest',
                      mesh=wrap_panel(side * 24.0, side * 157.5, VEST_HEM[0], VEST_HEM[1], 0.003, 0.009, nth=30, nz=3)))
    # 背中の切り替えの線（肩甲骨の上、z 1.12〜1.13 の弧）：細い暗い帯
    V, F = wrap_panel(132.0, 228.0, 1.118, 1.126, 0.002, 0.003, nth=21, nz=2,
                      zb=lambda t: 1.112 + 0.012 * (1 - ((t - 180.0) / 48.0) ** 2),
                      zt=lambda t: 1.120 + 0.012 * (1 - ((t - 180.0) / 48.0) ** 2))
    P.append(dict(name='vest_seam', bone='chest', color='vest_dark', mesh=(V, F)))
    return P


def belt_loupe_tools() -> list[dict]:
    P = []
    # ベルト（前の開きの中だけ）とバックル
    xs = np.linspace(-0.085, 0.085, 13)
    zs = np.array([BELT_Z[0], BELT_Z[1]])
    X, Z = np.meshgrid(xs, zs)
    yb = smooth_grid(front_hit(X.ravel(), Z.ravel()).reshape(X.shape), 1)
    V, F = slab(np.stack([X, yb - 0.007, Z], -1), np.stack([X, yb - 0.001, Z], -1))
    P.append(dict(name='belt', bone='hips', color='belt', mesh=(V, F)))
    yf = float(front_hit([0.0], [0.88])[0]) - 0.008
    for nm, c, h in (('t', (0.002, yf, 0.914), (0.043, 0.004, 0.0055)), ('b', (0.002, yf, 0.854), (0.043, 0.004, 0.0055)),
                     ('l', (-0.037, yf, 0.884), (0.0055, 0.004, 0.030)), ('r', (0.041, yf, 0.884), (0.0055, 0.004, 0.030))):
        V, F = box_mesh(c, h)
        P.append(dict(name=f'buckle_{nm}', bone='hips', color='brass', mesh=(V, F)))
    V, F = box_mesh((0.010, yf - 0.001, 0.884), (0.003, 0.005, 0.016))
    P.append(dict(name='buckle_pin', bone='hips', color='brass', mesh=(V, F)))
    # ルーペ：真鍮の輪（外径 4.4cm・内径 3.2cm）、ガラス、上の吊り金具、首ひも（首巻きの横から V に下りる）
    zc = 1.057
    yc = float(front_hit([X0], [zc])[0]) - 0.016
    axis = np.array([0.0, -1.0, -0.12])
    V, F = ring_mesh((X0, yc, zc), axis, (0, 0, 1), 0.044, 0.031, 0.011, 28)
    P.append(dict(name='loupe_ring', bone='chest', color='brass', mesh=(V, F)))
    V, F = disc_mesh((X0, yc + 0.003, zc), axis, (0, 0, 1), 0.032, 0.006, 24)
    P.append(dict(name='loupe_glass', bone='chest', color='glass', mesh=(V, F)))
    V, F = box_mesh((X0, yc + 0.002, zc + 0.050), (0.008, 0.005, 0.008))
    P.append(dict(name='loupe_bail', bone='chest', color='brass', mesh=(V, F)))
    top = np.array([X0, yc + 0.004, zc + 0.056])
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        end = np.array([X0 + side * 0.074, -0.060, 1.205])     # 首巻きの下の縁の中へ
        pts = [top + (end - top) * f + np.array([0.0, -0.010 * math.sin(math.pi * f), 0.0]) for f in np.linspace(0, 1, 7)]
        secs = []
        for i, p in enumerate(pts):
            d = pts[min(i + 1, 6)] - pts[max(i - 1, 0)]
            d /= np.linalg.norm(d)
            e0 = np.cross(d, [0.0, 1.0, 0.0])
            e0 /= np.linalg.norm(e0)
            e1 = np.cross(d, e0)
            ang = np.linspace(0, 2 * math.pi, 6, endpoint=False)
            secs.append(p + 0.0028 * (np.cos(ang)[:, None] * e0 + np.sin(ang)[:, None] * e1))
        V, F = _loft(np.array(secs))
        P.append(dict(name='cord' + sx, bone='chest', color='cord', mesh=(V, F)))
    # ポケットの道具（本人の右のポケット：灰の筒（金づちの頭）と真鍮の筒。左：穴のある灰の塊）。袋の口から 4〜9cm 出る
    def pocket_pt(side, deg, z, out=0.0):
        t_ = math.radians(side * deg)
        r_ = float(surf_r([t_], [z])[0]) + out
        return np.array([r_ * math.sin(t_), AX_Y - r_ * math.cos(t_), z])
    # 右（−x）：灰の筒は外寄り（正面の絵 x −0.21〜−0.165、z 0.92〜1.00、外へ 15 度傾く）、真鍮の筒は内寄り（x −0.16〜−0.11）
    b = pocket_pt(-1.0, 70.0, 0.875, 0.012)
    V, F = cyl_mesh(b, b + np.array([-0.022, 0.004, 0.115]), 0.0175, 14)
    P.append(dict(name='tool_grey', bone='hips', color='tool', mesh=(V, F)))
    V, F = cyl_mesh(b + np.array([-0.019, 0.004, 0.100]), b + np.array([-0.023, 0.005, 0.118]), 0.0182, 14)
    P.append(dict(name='tool_grey_end', bone='hips', color='tool_dark', mesh=(V, F)))
    b = pocket_pt(-1.0, 46.0, 0.875, 0.012)
    V, F = cyl_mesh(b, b + np.array([0.012, -0.002, 0.105]), 0.0150, 14)
    P.append(dict(name='tool_brass', bone='hips', color='tool_brass', mesh=(V, F)))
    # 左（+x）：灰の塊（6 × 3 × 7cm、外へ 12 度傾く）と穴
    b = pocket_pt(1.0, 58.0, 0.900, 0.010)
    t_ = math.radians(58.0)
    ex = np.array([math.cos(t_), math.sin(t_), 0.0])
    ey = np.array([math.sin(t_), -math.cos(t_), 0.0])
    tilt = math.radians(-12.0)
    ex2 = ex * math.cos(tilt) + np.array([0, 0, 1.0]) * math.sin(tilt)
    V, F = box_mesh(b + np.array([0.0, 0.0, 0.050]), (0.031, 0.014, 0.038), ex2, ey)
    P.append(dict(name='tool_block', bone='hips', color='tool', mesh=(V, F)))
    V, F = disc_mesh(b + np.array([0.0, 0.0, 0.062]) + ey * 0.0135, ey, (0, 0, 1), 0.007, 0.002, 10)
    P.append(dict(name='tool_block_hole', bone='hips', color='tool_dark', mesh=(V, F)))
    return P


# ---------------------------------------------------------------- 袖・ズボンの裾・膝の当て布

def sleeve_trouser_parts() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        # シャツの袖の折り返し（肘の少し上〜前腕の上 8.5cm）：太い輪
        s2, e2 = jp('forearm', side), jp('hand', side)
        fs2 = frame(s2, e2, front)
        fs2['RN'] = 0.05
        P.append(dict(name='sleeve_roll' + sx, bone='forearm' + sx, color='roll', frame=fs2, ring=True,
                      t0=ROLL_T[0], t1=ROLL_T[1], off=0.005, thick=0.013, bevel=0.005, under='ivory',
                      rmax=0.14, rmin=0.03, n_ring=32, sink=0.014))
        # ズボンの裾の折り返し（z 0.205〜0.29）：すねの軸の太い輪
        k = jp('shin', side)
        fb = frame(k, jp('foot', side), front)
        fb['RN'] = 0.07
        dz = -fb['d'][2]
        P.append(dict(name='trouser_cuff' + sx, bone='shin' + sx, color='cuff', frame=fb, ring=True,
                      t0=(k[2] - TROUSER_CUFF[1]) / dz, t1=(k[2] - TROUSER_CUFF[0]) / dz, off=0.005, thick=0.013,
                      bevel=0.005, under='rust', rmax=0.20, rmin=0.04, n_ring=40, sink=0.02))
        # 膝の当て布（正面の絵の 4 隅、少し傾いた四角）：脚の縦の軸のまわりの角度・高さで板に
        P += knee_patch(side, sx)
    return P


# 当て布の 4 隅（正面の絵の x, z。本人の左。右は鏡写しの少し違う形）：左上・右上・右下・左下（画像の向き）
PATCH_L = [(0.105, 0.505), (0.228, 0.510), (0.236, 0.372), (0.128, 0.352)]
PATCH_R = [(-0.215, 0.512), (-0.104, 0.500), (-0.120, 0.352), (-0.234, 0.370)]


def knee_patch(side, sx) -> list[dict]:
    q = np.array(PATCH_L if side > 0 else PATCH_R)
    U, Vv = np.meshgrid(np.linspace(0, 1, 8), np.linspace(0, 1, 9))
    pts = ((1 - U) * (1 - Vv))[..., None] * q[0] + (U * (1 - Vv))[..., None] * q[1] + \
          (U * Vv)[..., None] * q[2] + ((1 - U) * Vv)[..., None] * q[3]
    xs, zs = pts[..., 0], pts[..., 1]
    yb = smooth_grid(front_hit(xs.ravel(), zs.ravel()).reshape(xs.shape), 2)
    inner = np.stack([xs, yb - 0.0040, zs], -1)
    outer = np.stack([xs, yb - 0.0070, zs], -1)
    V, F = slab(outer, inner)
    P = [dict(name='knee_patch' + sx, bone='shin' + sx, color='patch', mesh=(V, F))]
    # 縫い目：左右の縁をまたぐ短い横の線（1 辺 3 本）。当て布の外の面の縁の点に置く（1 回目は前から撃った点で、横の縁では脚から浮いた）
    for edge in (0, -1):
        for k, f in enumerate((0.2, 0.5, 0.8)):
            r_ = f * (outer.shape[0] - 1)
            i0_ = int(r_)
            i1_ = min(i0_ + 1, outer.shape[0] - 1)
            w_ = r_ - i0_
            c = outer[i0_, edge] * (1 - w_) + outer[i1_, edge] * w_
            tan = outer[i0_, 1 if edge == 0 else -2] - outer[i0_, edge]
            tan /= np.linalg.norm(tan)
            V, F = box_mesh(c + np.array([0.0, -0.0008, 0.0]), (0.008, 0.0013, 0.0016), ex=tan, ey=(0.0, 1.0, 0.0))
            P.append(dict(name=f'stitch{edge}{k}' + sx, bone='shin' + sx, color='stitch', mesh=(V, F)))
    return P


# ---------------------------------------------------------------- 靴

def boot_pieces(side: float, sx: str) -> list[dict]:
    """片足の靴（左の値で書き、右は x を反転）。絵 junker_shoes と全身の絵（正面・右真横）：
    底 x 0.110〜0.318・y −0.200〜0.150、厚い暗い底（3.4cm）、明るい茶の爪先、暗い茶の胴（足首 0.21 まで）、足首の帯（0.155〜0.205）と留め具"""
    X0_, X1_ = 0.112, 0.316
    YF, YB = -0.198, 0.148
    P = []

    def sec(z, x0, x1, y0, y1, rf, rb, k=3):
        return (z, rrect(x0, x1, y0, y1, rf, rb, k))

    sole = [sec(0.000, X0_ + 0.004, X1_ - 0.004, YF + 0.006, YB - 0.004, 0.060, 0.034),
            sec(0.005, X0_, X1_, YF, YB, 0.064, 0.038),
            sec(0.030, X0_, X1_, YF, YB, 0.064, 0.038),
            sec(0.035, X0_ + 0.004, X1_ - 0.004, YF + 0.005, YB - 0.004, 0.060, 0.034)]
    toe = [sec(0.030, X0_ + 0.007, X1_ - 0.007, YF + 0.007, -0.050, 0.058, 0.02, 4),
           sec(0.062, X0_ + 0.009, X1_ - 0.010, YF + 0.011, -0.052, 0.055, 0.02, 4),
           sec(0.088, X0_ + 0.020, X1_ - 0.024, YF + 0.034, -0.050, 0.045, 0.02, 4),
           sec(0.100, X0_ + 0.034, X1_ - 0.040, YF + 0.064, -0.048, 0.034, 0.02, 4)]
    upper = [sec(0.030, X0_ + 0.008, X1_ - 0.008, -0.066, YB - 0.007, 0.03, 0.045, 4),
             sec(0.070, X0_ + 0.010, X1_ - 0.012, -0.078, YB - 0.010, 0.03, 0.045, 4),
             sec(0.100, X0_ + 0.020, X1_ - 0.040, -0.062, YB - 0.016, 0.035, 0.045, 4),
             sec(0.130, 0.128, 0.244, -0.048, 0.118, 0.045, 0.045, 4),
             sec(0.170, 0.124, 0.242, -0.044, 0.112, 0.048, 0.048, 4),
             sec(0.222, 0.122, 0.240, -0.042, 0.110, 0.050, 0.050, 4)]
    strap = [sec(0.150, 0.118, 0.248, -0.050, 0.118, 0.052, 0.052, 4),
             sec(0.156, 0.115, 0.251, -0.053, 0.121, 0.054, 0.054, 4),
             sec(0.200, 0.115, 0.251, -0.053, 0.121, 0.054, 0.054, 4),
             sec(0.206, 0.118, 0.248, -0.050, 0.118, 0.052, 0.052, 4)]
    for name, color, secs in (('sole', 'sole', sole), ('toe', 'toe', toe), ('upper', 'boot', upper),
                              ('strap', 'boot_strap', strap)):
        if side < 0:
            secs = [(z, [(-x, y) for (x, y) in pts][::-1]) for z, pts in secs]
        P.append(dict(name=f'boot_{name}{sx}', bone='foot' + sx, color=color, loft=secs,
                      ramp=('shin' + sx, 'foot' + sx)))
    # 足首の帯の留め具（外側の前寄り、絵 junker_shoes：帯の上の四角い留め）
    V, F = box_mesh((side * 0.252, -0.010, 0.178), (0.004, 0.016, 0.016))
    P.append(dict(name='boot_buckle' + sx, bone='foot' + sx, color='boot_strap', mesh=(V, F),
                  ramp=('shin' + sx, 'foot' + sx)))
    return P


# ---------------------------------------------------------------- 髪（房）・あごひげ

def hair_locks() -> list[dict]:
    """髪の房（1 周目から 2 周目の作り：帽子は外形の 1.4cm 内、房の幅はとなりとの距離の 0.6 倍、下で巻き込まない、色は絵から）。
    絵 junker_head_back・side_right・top：つむじ（頭頂の少し後ろ）から葉の形の房が放射状に重なり、先は外・後ろ・下へとがる。
    横の房は後ろへ流れて先が外へはねる（耳の上で止まり、耳は見える）。後ろの房はえり足へ。前は頭頂から右目の前へ垂れる長い房と、
    額の左の上へはねる房、頭頂の前の立った房 2 本、こめかみの前の房（耳の前）。
      道：頭の中心から見た根 →（経由）→ 先の向きを大円でつなぎ、各点をその向きの帽子の面＋浮きに置く。先の 35% で帽子から離れる
      （浮き lift_tip。房の先がとがって外へ出る：絵の毛先のはね）。
      断面：峰・左右の縁・内の面の 6 角。峰の両側は髪の色、縁と内の面は陰の色"""
    from scipy import ndimage as NDI

    from recon import hair as HR
    from recon import views as V
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    phi, lo, vox = np.asarray(d['phi'], np.float32), d['lo'], float(d['vox'])
    C = np.array(HR.HEAD_C, float)

    def inside(P):
        idx = ((P[:, [2, 0, 1]] - lo[[2, 0, 1]]) / vox - 0.5).T
        return NDI.map_coordinates(phi, idx, order=1, mode='constant', cval=-1.0) > 0

    def radial(dirs, r_max=0.20, step=0.0015):
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

    PX = [0.0, 1.0, 0.94, 0.0, -0.94, -1.0]
    PY = [1.0, 0.22, -0.22, -0.45, -0.22, 0.22]
    TOP_SEG = (0, 5)
    n = 15
    tt = np.linspace(0.0, 1.0, n)

    def slerp_path(dkeys, fkeys):
        out = []
        for t in tt:
            j = min(int(np.searchsorted(fkeys, t, side='right')) - 1, len(dkeys) - 2)
            u = (t - fkeys[j]) / (fkeys[j + 1] - fkeys[j])
            a, b = dkeys[j], dkeys[j + 1]
            om = math.acos(float(np.clip(np.dot(a, b), -1, 1)))
            v = (math.sin((1 - u) * om) * a + math.sin(u * om) * b) / math.sin(om) if om > 1e-4 else a
            out.append(v / np.linalg.norm(v))
        return np.array(out)

    def centre(dkeys, lift_root, lift_tip, thick, fkeys=None, r_max=0.20, tip_start=0.62, sink=0.010):
        dirs = slerp_path(dkeys, fkeys if fkeys is not None else np.linspace(0, 1, len(dkeys)))
        dirs = NDI.gaussian_filter1d(dirs, 1.2, axis=0, mode='nearest')
        dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        r = NDI.gaussian_filter1d(radial(dirs, r_max=r_max), 1.0, mode='nearest')
        # 一番外の半径より先は軸から離れる一方（下の縁で内へ巻き込まない）
        k_wide = int(np.argmax(r))
        r[k_wide:] = np.maximum.accumulate(r[k_wide:])
        f = smoothstep((tt - tip_start) / (1.0 - tip_start)) ** 1.3
        lift = lift_root + (lift_tip - lift_root) * f
        th_ = thick * np.interp(tt, [0, 0.12, 0.6, 1.0], [0.55, 1.0, 1.0, 0.45])
        rr = r + lift + 0.45 * th_ - sink * np.clip(1 - tt / 0.12, 0, 1)
        return dirs, C + dirs * rr[:, None], th_

    def ribbon(dirs, P, ww, th_):
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

    out = []

    def add(name, V_, Ft, Fu):
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(V_, Ft)))
        out.append(dict(name='hair_' + name + '_u', bone='head', color='hair_shadow', mesh=(V_, Fu)))

    WPROF = (np.array([0, 0.10, 0.45, 0.75, 1.0]), np.array([0.40, 0.90, 1.0, 0.70, 0.05]))

    def tier(spec, k_w=0.60, thick=0.013, w_max=0.040):
        """spec：[(名前, [(角度, 高さ), ...] の道の節, 根の浮き, 先の浮き, 節の割合)]。幅はとなりの房との距離から"""
        lines = []
        for name, keys, l0, l1, fk in spec:
            dk = [dir_at(a, z) for a, z in keys]
            lines.append(centre(dk, l0, l1, thick, fkeys=np.array(fk) if fk is not None else None))
        for i, (name, *_r) in enumerate(spec):
            dirs, P, th_ = lines[i]
            nb = [j for j in range(len(spec)) if j != i]
            dist = np.min([np.linalg.norm(P - lines[j][1], axis=1) for j in nb], 0)
            hw = NDI.gaussian_filter1d(np.clip(k_w * dist, 0.007, w_max), 1.0, mode='nearest')
            hw = hw * np.interp(tt, *WPROF)
            add(name, *ribbon(dirs, P, hw, th_))

    # つむじ：頭頂の少し後ろ（絵 junker_head_top・back：房はここから放射状に重なる）
    crown = (180.0, 1.535)
    # 上の房（つむじから前・横へ扇に。頭頂を覆う）
    top = []
    for i, a in enumerate((-62, -26, 12, 48)):
        root = (180.0 - a * 0.30 if a < 0 else -180.0 - a * 0.30, crown[1] - 0.004)
        top.append((f'top{i}', [root, (a, 1.545)], 0.001, 0.006, None))
    tier(top, k_w=0.62, thick=0.013, w_max=0.040)
    # 頭頂の左右で外・上へはねる大きな房 2 本（絵の正面：髪の外形は上の左右が張った炎の形）
    flare = [('flare_l', [(18.0, 1.548), (46.0, 1.536), (76.0, 1.515)], 0.002, 0.036, [0.0, 0.5, 1.0]),
             ('flare_r', [(-18.0, 1.548), (-48.0, 1.532), (-80.0, 1.505)], 0.002, 0.036, [0.0, 0.5, 1.0])]
    tier(flare, k_w=0.66, thick=0.014, w_max=0.034)
    # 横の房（片側 4 段）：こめかみの上の根から後ろへほぼ水平に流れ、先は後ろ・外へはねる（絵の右真横：葉の先は後ろを向く）。
    # 一番下の段は耳の上（1.40）を通る
    for side, sx in ((1.0, 'l'), (-1.0, 'r')):
        rows = []
        for k, (a0, z0, am, zm, a1, z1, lt) in enumerate(((38, 1.522, 88, 1.522, 136, 1.508, 0.022),
                                                           (50, 1.495, 92, 1.490, 130, 1.472, 0.040),
                                                           (60, 1.462, 96, 1.454, 125, 1.436, 0.040),
                                                           (70, 1.428, 100, 1.420, 120, 1.402, 0.030))):
            rows.append((f'side{k}_{sx}', [(side * a0, z0), (side * am, zm), (side * a1, z1)], 0.002, lt,
                         [0.0, 0.45, 1.0]))
        tier(rows, k_w=0.70, thick=0.014, w_max=0.040)
    # 後ろの房（つむじから下へ。先はえり足 1.33〜1.37 で下・外へ）と、その下の段
    back = []
    for i, (a, zt) in enumerate(((-152, 1.375), (-166, 1.35), (180, 1.335), (166, 1.35), (152, 1.375))):
        root = ((180.0 + (a - 180.0) * 0.25) if a > 0 else (-180.0 + (a + 180.0) * 0.25), crown[1] - 0.004)
        back.append((f'back{i}', [root, (a, 1.47), (a + (-6 if a < 0 else 6), zt)], 0.001,
                     0.022 if abs(a) > 160 else 0.014, [0.0, 0.4, 1.0]))
    tier(back, k_w=0.66, thick=0.013, w_max=0.042)
    nape = []
    for i, (a, zt) in enumerate(((-142, 1.33), (-172, 1.305), (172, 1.305), (142, 1.33))):
        nape.append((f'nape{i}', [(a * 0.97, 1.45), (a, 1.40), (a + (-5 if a < 0 else 5), zt)], 0.002, 0.016,
                     [0.0, 0.45, 1.0]))
    tier(nape, k_w=0.66, thick=0.012, w_max=0.036)
    # 前：頭頂から本人の右目の前へ垂れる長い房（先は右目の内の端の上 z 1.372）、右のこめかみへ流れる房、
    #     額の左の上へはねる房、立った房 2 本、こめかみの前の房（耳の前、右は低い）
    front = [
        ('f_long', [(-2.0, 1.548), (-16.0, 1.49), (-8.0, 1.372)], 0.004, 0.012, [0.0, 0.5, 1.0]),
        ('f_right', [(-8.0, 1.548), (-42.0, 1.485), (-64.0, 1.405)], 0.004, 0.016, [0.0, 0.5, 1.0]),
        ('f_left', [(10.0, 1.548), (36.0, 1.525), (60.0, 1.505)], 0.003, 0.026, [0.0, 0.5, 1.0]),
        ('f_up_r', [(-28.0, 1.51), (-22.0, 1.545), (-16.0, 1.575)], 0.002, 0.024, [0.0, 0.5, 1.0]),
        ('f_up_l', [(24.0, 1.51), (32.0, 1.54), (42.0, 1.57)], 0.002, 0.024, [0.0, 0.5, 1.0]),
        ('temple_r', [(-56.0, 1.47), (-74.0, 1.40), (-81.0, 1.345)], 0.004, 0.008, [0.0, 0.5, 1.0]),
        ('temple_l', [(56.0, 1.47), (73.0, 1.41), (79.0, 1.37)], 0.004, 0.008, [0.0, 0.5, 1.0]),
    ]
    tier(front, k_w=0.70, thick=0.013, w_max=0.030)
    # 額の生え際を覆う短い房（1 回目は帽子の縁が額の上に暗い帯で見えた）
    edge = [('fh_c', [(4.0, 1.536), (10.0, 1.466)], 0.003, 0.007, None),
            ('fh_l', [(26.0, 1.532), (40.0, 1.452)], 0.003, 0.008, None),
            ('fh_r', [(-24.0, 1.532), (-36.0, 1.452)], 0.003, 0.008, None)]
    tier(edge, k_w=0.66, thick=0.011, w_max=0.026)
    return out


def goatee() -> list[dict]:
    """あごひげ（短い三角、髪の色）：口の下 z 1.296 からあごの先の下 1.255 へ。顔の絵の幅（上 4.4cm → 先へ細る）。
    頭の表の前の端（あご）の 3〜9mm 前"""
    from recon import head as HD
    out = []
    zs = np.array([1.297, 1.288, 1.278, 1.268, 1.259, 1.252])
    hw = np.array([0.020, 0.022, 0.020, 0.014, 0.007, 0.0015])
    dep = np.array([0.004, 0.007, 0.009, 0.009, 0.007, 0.003])
    tbl = HD.HEAD
    secs = []
    for z, w, dp in zip(zs, hw, dep):
        zq = max(z, tbl['z'][0])
        yf = float(np.interp(zq, tbl['z'], tbl['yf']))
        ang = np.linspace(-1.0, 1.0, 7)
        xs = X0 + w * ang
        ybase = yf + 0.010 * ang ** 2 - (0.004 if z < tbl['z'][0] else 0.0)
        top = np.stack([xs, ybase - dp * (1 - 0.5 * ang ** 2), np.full(7, z)], 1)
        bot = np.stack([xs[::-1], ybase[::-1] + 0.006, np.full(7, z)], 1)
        secs.append(np.concatenate([top, bot]))
    V, F = _loft(np.array(secs))
    out.append(dict(name='goatee', bone='head', color='hair', mesh=(V, F)))
    return out


def pieces() -> list[dict]:
    P = []
    P += wrap_parts()
    P += vest_parts()
    P += belt_loupe_tools()
    P += sleeve_trouser_parts()
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        P += boot_pieces(side, sx)
    P += hair_locks()
    P += goatee()
    return P


# ---------------------------------------------------------------- 決まりの塗り（cover_body から）

def body_rules(pos: np.ndarray, col: np.ndarray, lab: np.ndarray, under: np.ndarray, ins: dict, stats: dict) -> None:
    """ベストの裾より上の胴は焦げ茶のベスト（前の開きはシャツ、ベルトより下はズボン）、腕はシャツの袖（折り返しより先は肌）、
    裾より下はズボンの赤錆、首は肌。頭と首の帯は形の場（hair.part_fields_at）で髪・肌・耳を決める"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    free = under < 0
    r_neck = np.hypot(x - X0, y)
    head = (z > NECK_TOP + 0.01) | ((z > 1.25) & (r_neck > 0.075) & (y < 0.0) & (np.abs(x) < 0.15))
    # 腕：上腕の軸の近く（肩の外、ベストの袖ぐりより外）
    arm = np.zeros(len(pos), bool)
    skin_arm = np.zeros(len(pos), bool)
    vest_half = np.interp(z, VEST_SIDE[0], VEST_SIDE[1])
    for side in (1.0, -1.0):
        S, E = np.array(jp('upper_arm', side)), np.array(jp('forearm', side))
        dv = (E - S) / np.linalg.norm(E - S)
        t = (pos - S) @ dv
        rr = np.linalg.norm((pos - S) - np.outer(t, dv), axis=1)
        # 上腕：腕の軸の近くで、ベストの横の縁（正面の絵）より外（1 回目は軸からの距離だけで、胴の横が生成りの四角になった）
        a_ = free & (side * x > vest_half - 0.004) & (rr < 0.085) & (t > -0.02) & (z < 1.22)
        S2, E2 = np.array(jp('forearm', side)), np.array(jp('hand', side))
        d2 = (E2 - S2) / np.linalg.norm(E2 - S2)
        t2 = (pos - S2) @ d2
        r2 = np.linalg.norm((pos - S2) - np.outer(t2, d2), axis=1)
        fa = free & (side * x > 0.22) & (r2 < 0.10) & (t2 > -0.02)
        arm |= a_ | fa
        skin_arm |= fa & (t2 > ROLL_T[1] - 0.012)
    skin_arm |= free & (np.abs(x) > 0.34) & (z > 0.55) & (z < 0.86)
    # 胴（ベストの裾より上）
    torso = free & ~head & ~arm & ~skin_arm & (z >= VEST_HEM[0])
    under[torso] = NAMES.index('vest')
    half = np.interp(z, OPEN[0], OPEN[1])
    opening = torso & (y < -0.02) & (np.abs(x) < half) & (z < SHIRT_TOP + 0.04)
    under[opening & (z >= BELT_Z[0])] = NAMES.index('ivory')
    under[opening & (z < BELT_Z[0])] = NAMES.index('rust')
    under[arm & ~skin_arm] = NAMES.index('ivory')
    under[skin_arm] = NAMES.index('skin')
    # 首巻きのまわり（首巻きの部品の 1.2cm 外まで）：首巻きの色。部品と体の土台が交わる所で、ベスト・肌の斑点に見えた（1 回目）
    wa = np.interp(z, WRAP['z'], WRAP['a']) + 0.012
    wb = np.where(y < WRAP_CY, np.interp(z, WRAP['z'], WRAP['bf']), np.interp(z, WRAP['z'], WRAP['bb'])) + 0.012
    # 1.20 より上は首の軸から 16cm まで全部（体の土台の首は外形のレンズで、斜めの角・頭の首の殻が首巻きの部品の外へ出て、
    # 肌・ベストの色の斑点になった。2 回目）。上の端は首巻きの上の縁（前 1.262・横と後ろ 1.29）
    th_w = np.arctan2(x - X0, -(y - WRAP_CY))
    ztop_w = 1.290 - 0.028 * np.cos(th_w / 2.0) ** 4 + 0.003
    wz = free & (z > WRAP['z'][0] + 0.004) & (z < ztop_w) & ~arm & (
        (((x - X0) / (wa + 0.018)) ** 2 + ((y - WRAP_CY) / (wb + 0.018)) ** 2 < 1.0) | ((z > 1.20) & (np.hypot(x - X0, y - WRAP_CY) < 0.16)))
    under[wz] = NAMES.index('wrap')
    # 首（首巻きの口より上）：肌
    neck = free & ~head & (z > 1.255) & (r_neck < 0.065) & ~arm
    under[neck] = NAMES.index('skin')
    # 脚（ベストの裾より下）：ズボン
    legs = free & (z < VEST_HEM[0]) & ~skin_arm
    under[legs] = NAMES.index('rust')
    # 頭と首の帯：形の場で（店主・トルーデと同じ作り）
    from recon import hair as HR
    hb = (z > 1.20) & (z < 1.66) & (np.hypot(x - X0, y) < np.where(z > 1.26, 0.30, 0.10))
    hi = np.nonzero(hb)[0]
    if len(hi):
        f = HR.part_fields_at(pos[hi], x_half=0.30, z0=1.18)
        xh, yh, zh = x[hi], y[hi], z[hi]
        ear = f['ear'] > -0.002
        hair = (f['hair'] > -0.004) & ~ear
        ax = np.abs(xh - X0)
        th_f = np.degrees(np.arctan2(ax, -(yh - 0.0)))
        flush = (f['hair'] - f['skin']) < 0.009
        line = np.where(th_f < 72.0, np.interp(ax, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]),
                        np.where(th_f < 112.0, 1.395, 1.31))
        hair &= ~(flush & (zh < line))
        lab_h = np.full(len(hi), NAMES.index('skin'))
        near_line = (th_f < 80.0) & (zh < np.interp(ax, HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]) + 0.020)
        lab_h[hair] = NAMES.index('hair_dark')
        lab_h[hair & near_line] = NAMES.index('hair')
        lab_h[ear] = NAMES.index('skin')
        lab_h[(zh < 1.21) & ~hair] = NAMES.index('wrap')
        keep = under[hi] >= 0
        under[hi[~keep]] = lab_h[~keep]
    stats['junker_rule_texels'] = int((torso | arm | skin_arm | neck | legs).sum())


# ---------------------------------------------------------------- 手の部品（hand.py）

# 両手とも力を抜いて開いた手（hand.build_open）。素手。絵 junker_hands.png：大人の男の手（バートンより少し細い）。
# （絵の手首の生成りの袖口は、全身の 6 枚の絵では肘の上の袖の折り返しなので作らない）
_S, _R = 1.05, 1.08
HAND = dict(
    GLOVE=None,
    LID='skin',
    OPEN_FINGERS=[(n, z * _S, x * _S, r * _R, tuple(v * _S for v in L), fan) for n, z, x, r, L, fan in (
        ('index', 0.0255, 0.070, 0.0080, (0.036, 0.023, 0.019), 6.0),
        ('middle', 0.0085, 0.073, 0.0083, (0.038, 0.025, 0.020), 1.0),
        ('ring', -0.0085, 0.070, 0.0078, (0.035, 0.023, 0.019), -4.0),
        ('pinky', -0.0240, 0.063, 0.0068, (0.028, 0.019, 0.016), -9.0))],
    OPEN_CURL=(14.0, 20.0, 14.0),
    CUFF_LID=(-0.012, 0.006),
    OPEN_THUMB=dict(base=(0.026, 0.008, 0.024), r=0.0088 * _R, lens=(0.035, 0.030, 0.025), out_deg=22.0,
                    palm_deg=34.0, curl=(8.0, 12.0, 10.0)),
    PALM_HALF_T=0.0115 * _R,
    PALM_WRIST=(0.002, 0.0, 0.016, 0.030),
    PALM_X=(0.012, 0.046),
    THENAR=((0.029, 0.007, 0.023), 0.0145),
    HYPOTHENAR=((0.035, 0.005, -0.021), 0.013),
    LEFT_HAND_CUT=-0.004,
    LEFT_HAND_RAMP=(-0.014, 0.006),
)
