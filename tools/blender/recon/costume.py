"""服の硬い部品を、体の面に沿った別の形（殻）として作る（作り方の道具。部品の表はキャラクターごと）。

■ 部品の表：chars/<id>_parts.py（RECON_CHAR のキャラクター。ハル haru_parts.py、バートン burton_parts.py）。
  色見本 PALETTE、関節 J、pieces()・boot_pieces()、決まりの塗り body_rules()、手の寸法 HAND など。このファイルの最後で
  読み込み、その大文字の定数と関数をこのモジュールに入れる（CO.FOLLOW_BODY などはそのまま使える）。表が無いキャラクターは部品なし。

塗りでは直らない所（絵どうし・絵と形の食い違いで、板の縁がにじむ・別の絵の帯が板の上に載る）を、形で直す。
ゴーグル・ベルト・耳・番機・閂・ナゴミと同じく「別の形のものは、色を形から」：部品ごとに平らな 1 色なので、
縁は作りからくっきりする。

■ 形（build_all → ai_character.py の --costume）
  部品は「軸のまわりの円柱の座標」(s, t) の上の輪郭で決める：軸の点 a・向き d（t は a から d の向きへの長さ m）、
  基準の向き e0（s = 0、部品の中心の向き）、s は角度 × 名目の半径 RN（m）。輪郭は絵（正面・背面・真横）で測った
  多角形（凸）か、ぐるりと一周の帯（ring）。各点で軸から外へ光線を飛ばして体の面の半径 r を測り、なめらかにして、
  r + OFF（体から浮かす）＋ 厚み の所に上の面を置く。縁は BEVEL だけ下げ（面取り）、縁から体の中（r − SINK）まで壁を下ろす
  （底の面は作らない：体の中で見えない）。ポーチは箱。
  色は部品ごとに PALETTE の 1 色（材質 haru_parts の色見本の画像を UV で指す）。骨は部品が載る骨 1 本に重み 1（剛体）。
■ 下の体の塗り（cover_body → texture.py、flat.paint_body のあと）
  部品の真下（輪郭の中で、体の面が部品の内側の面の近く）は、下地の布の色（UNDER、無ければ周りの色）。
  輪郭のまわり MARGIN の帯では、部品の色（CLEAR：例 膝当ての白・暗い枠）だけを周りの色に替える（塗りの板が
  部品からはみ出して二重の縁にならない）。
座標は A ポーズの再構築の座標（texture.py のメッシュ・ai_character.py の --keep-frame の入力と同じ。本人の右は -X、正面は -Y）。
"""
from __future__ import annotations

import importlib.util
import json
import math
import os

import numpy as np

try:
    from recon import char as CH
except ImportError:          # ai_character.py は recon のフォルダを sys.path に入れて import costume する
    import char as CH

# ■ キャラクターごとの部品（chars/<id>_parts.py）。ここの既定は「部品なし」。ファイルの最後で読み込んで上書きする
PALETTE: dict = {}
CELLS = 8          # 色見本の画像：横に CELLS 区画（1 区画 32 画素）
J: dict = {}
FOLLOW_BODY: tuple = ()
FOLLOW_TORSO_ONLY: tuple = ()
BOX_RULES: list = []
BOOT_CUT = None
BOOT_RAMP = (0.095, 0.155)
BOOT_CUT_X = (0.03, 0.32)     # 体の足を消す |x| の範囲（手は含めない）
GOGGLE_STRAP = None
HAND: dict = {}
body_rules = None

H = 0.011         # 殻の点の間隔（m）


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def jp(name: str, side: float) -> np.ndarray:
    p = np.array(J[name], float)
    p[0] *= side
    return p


def unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(a, b, ref) -> dict:
    """軸 a → b、基準の向き ref（軸に直交させる）"""
    a = np.asarray(a, float)
    d = unit(np.asarray(b, float) - a)
    e0 = unit(np.asarray(ref, float) - d * np.dot(ref, d))
    e1 = np.cross(d, e0)
    return {'a': a, 'd': d, 'e0': e0, 'e1': e1}


def octagon(s0, s1, t0, t1, c) -> list:
    """角を c だけ切った長方形（凸の八角形、反時計回り）"""
    return [(s0 + c, t0), (s1 - c, t0), (s1, t0 + c), (s1, t1 - c), (s1 - c, t1), (s0 + c, t1), (s0, t1 - c),
            (s0, t0 + c)]


def circle(sc, tc, rad, n=12) -> list:
    return [(sc + rad * math.cos(2 * math.pi * k / n), tc + rad * math.sin(2 * math.pi * k / n)) for k in range(n)]




def rrect(x0, x1, y0, y1, rf, rb, k=3) -> list:
    """角を丸めた長方形（上から見て反時計回り、x 右・y 後ろ）。rf：前（y0）の角、rb：後ろ（y1）の角の半径。
    角は k+1 点（k=3 → 30 度ずつの面：絵の面のある靴）"""
    pts = []
    for (cx, cy, r, a0) in ((x0 + rf, y0 + rf, rf, 180), (x1 - rf, y0 + rf, rf, 270),
                            (x1 - rb, y1 - rb, rb, 0), (x0 + rb, y1 - rb, rb, 90)):
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts



def build_loft(spec: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """断面（高さ z ごとの凸の多角形、同じ点の数）を積んだ閉じた形。上下はふた。外向きにそろえる"""
    secs = spec['loft']
    n = len(secs[0][1])
    V = np.array([(x, y, z) for z, pts in secs for (x, y) in pts], float)
    F = []
    for j in range(len(secs) - 1):
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            c, d = (j + 1) * n + (i + 1) % n, (j + 1) * n + i
            F += [(a, b, c), (a, c, d)]
    # ふた：中心の点からの扇
    for j, flip in ((0, True), (len(secs) - 1, False)):
        ci = len(V)
        V = np.vstack([V, V[j * n:(j + 1) * n].mean(0)])
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            F.append((ci, b, a) if flip else (ci, a, b))
    F = np.array(F)
    p = V[F]
    vol = np.einsum('ij,ij->i', p[:, 0], np.cross(p[:, 1], p[:, 2])).sum() / 6
    if vol < 0:
        F = F[:, [0, 2, 1]]
    return V, F, {}


def boot_cut_mask(co: np.ndarray) -> np.ndarray:
    """消す体の頂点（脚の BOOT_CUT より下）"""
    return (co[:, 2] < BOOT_CUT) & (np.abs(co[:, 0]) > BOOT_CUT_X[0]) & (np.abs(co[:, 0]) < BOOT_CUT_X[1])


def ramp_w(z: np.ndarray) -> np.ndarray:
    """靴の頂点の shin の重み（0 = foot）"""
    f = np.clip((z - BOOT_RAMP[0]) / (BOOT_RAMP[1] - BOOT_RAMP[0]), 0, 1)
    return f * f * (3 - 2 * f)


# ---------------------------------------------------------------- 幾何

def inside_poly(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    x, y = pts[:, 0], pts[:, 1]
    ins = np.zeros(len(pts), bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        c = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0)
        ins ^= c
    return ins


def poly_dist(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """輪郭までの距離（符号なし）"""
    best = np.full(len(pts), np.inf)
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ab = b - a
        tt = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        best = np.minimum(best, np.linalg.norm(pts - (a + np.outer(tt, ab)), axis=1))
    return best


def t_range(spec: dict, s: np.ndarray, which: str) -> np.ndarray:
    v = spec[which]
    if isinstance(v, tuple):   # 前・後ろの値を角度で混ぜる（帯の傾き）
        th = s / spec['frame']['RN']
        f = (1 - np.cos(th)) / 2
        return v[0] * (1 - f) + v[1] * f
    return np.full(len(s), float(v))


def param_of(spec: dict, pos: np.ndarray):
    fr = spec['frame']
    rel = pos - fr['a']
    if fr.get('kind') == 'sphere':
        r = np.linalg.norm(rel, axis=1)
        b = np.arcsin(np.clip((rel @ fr['e2']) / np.maximum(r, 1e-9), -1, 1))
        a = np.arctan2(rel @ fr['e1'], rel @ fr['e0'])
        return a * fr['RN'], b * fr['RN'], r
    t = rel @ fr['d']
    x, y = rel @ fr['e0'], rel @ fr['e1']
    th = np.arctan2(y, x)
    return th * fr['RN'], t, np.hypot(x, y)


def ray_dirs(fr: dict, s: np.ndarray, t: np.ndarray):
    if fr.get('kind') == 'sphere':   # 経度 a（e0 → e1）、緯度 b（e2 の向き）
        a, b = s / fr['RN'], t / fr['RN']
        dirs = (np.outer(np.cos(a) * np.cos(b), fr['e0']) + np.outer(np.sin(a) * np.cos(b), fr['e1'])
                + np.outer(np.sin(b), fr['e2']))
        return np.repeat(fr['a'][None], len(s), 0), dirs
    th = s / fr['RN']
    org = fr['a'] + np.outer(t, fr['d'])
    dirs = np.outer(np.cos(th), fr['e0']) + np.outer(np.sin(th), fr['e1'])
    return org, dirs


def cast(bvh, org: np.ndarray, dirs: np.ndarray, rmax: float) -> np.ndarray:
    from mathutils import Vector
    r = np.full(len(org), np.nan)
    for i in range(len(org)):
        hit = bvh.ray_cast(Vector(org[i]), Vector(dirs[i]), rmax)
        if hit[0] is not None:
            r[i] = hit[3]
    return r


def smooth_r(r: np.ndarray, edges: np.ndarray, iters: int = 4) -> np.ndarray:
    n = len(r)
    for _ in range(40):           # 当たらなかった点は隣の平均で埋める
        bad = np.isnan(r)
        if not bad.any():
            break
        acc = np.zeros(n)
        cnt = np.zeros(n)
        for a, b in ((edges[:, 0], edges[:, 1]), (edges[:, 1], edges[:, 0])):
            ok = ~np.isnan(r[b])
            np.add.at(acc, a[ok], r[b[ok]])
            np.add.at(cnt, a[ok], 1)
        fill = bad & (cnt > 0)
        r[fill] = acc[fill] / cnt[fill]
    r = np.nan_to_num(r, nan=float(np.nanmedian(r)) if np.isfinite(r).any() else 0.05)
    for _ in range(iters):
        acc = np.zeros(n)
        cnt = np.zeros(n)
        np.add.at(acc, edges[:, 0], r[edges[:, 1]])
        np.add.at(acc, edges[:, 1], r[edges[:, 0]])
        np.add.at(cnt, edges[:, 0], 1)
        np.add.at(cnt, edges[:, 1], 1)
        r = 0.5 * r + 0.5 * acc / np.maximum(cnt, 1)
    return r


def tri_edges(F: np.ndarray) -> np.ndarray:
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e.sort(1)
    return np.unique(e, axis=0)


def sample_patch(spec: dict):
    """凸の輪郭の中の (s, t) の点と三角形。最初の nb 個が輪郭の上（反時計回り）。
    点の間隔は H か、小さい部品（ボルト・レールの芯）では短い辺の 1/4"""
    from scipy.spatial import Delaunay
    poly = np.array(spec['outline'], float)
    H = min(spec.get('h', globals()['H']), float((poly.max(0) - poly.min(0)).min()) / 4)
    bnd = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        m = max(1, int(math.ceil(np.linalg.norm(b - a) / H)))
        for k in range(m):
            bnd.append(a + (b - a) * k / m)
    bnd = np.array(bnd)
    lo, hi = poly.min(0), poly.max(0)
    gs, gt = np.meshgrid(np.arange(lo[0], hi[0] + H, H), np.arange(lo[1], hi[1] + H, H))
    g = np.stack([gs.ravel(), gt.ravel()], 1)
    g = g[inside_poly(g, poly) & (poly_dist(g, poly) > 0.45 * H)]
    pts = np.concatenate([bnd, g])
    tri = Delaunay(pts).simplices
    cen = pts[tri].mean(1)
    tri = tri[inside_poly(cen, poly) | (poly_dist(cen, poly) < 1e-6)]
    # 反時計回りにそろえる
    p = pts[tri]
    cr = (p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1]) - (p[:, 1, 1] - p[:, 0, 1]) * (p[:, 2, 0] - p[:, 0, 0])
    tri[cr < 0] = tri[cr < 0][:, [0, 2, 1]]
    loops = [np.arange(len(bnd))]
    return pts, tri, loops


def sample_ring(spec: dict):
    fr = spec['frame']
    n = spec.get('n_ring', 64)
    th = np.arange(n) * 2 * math.pi / n
    th = np.where(th > math.pi, th - 2 * math.pi, th)
    s = th * fr['RN']
    t0, t1 = t_range(spec, s, 't0'), t_range(spec, s, 't1')
    m = max(3, int(math.ceil(float(np.max(t1 - t0)) / H)) + 1)
    f = np.linspace(0, 1, m)
    S = np.repeat(s[None, :], m, 0)
    T = t0[None, :] + (t1 - t0)[None, :] * f[:, None]
    pts = np.stack([S.ravel(), T.ravel()], 1)
    idx = np.arange(m * n).reshape(m, n)
    tris = []
    for j in range(m - 1):
        for i in range(n):
            a, b, c, d = idx[j, i], idx[j, (i + 1) % n], idx[j + 1, (i + 1) % n], idx[j + 1, i]
            tris += [(a, b, c), (a, c, d)]
    loops = [idx[0], idx[-1][::-1]]
    return pts, np.array(tris), loops


def build_shell(spec: dict, bvh) -> tuple[np.ndarray, np.ndarray, dict]:
    fr = spec['frame']
    pts, tri, loops = sample_ring(spec) if spec.get('ring') else sample_patch(spec)
    org, dirs = ray_dirs(fr, pts[:, 0], pts[:, 1])
    r = cast(bvh, org, dirs, spec.get('rmax', 0.2))
    edges = tri_edges(tri)
    r = smooth_r(r, edges, 0)
    raw = np.clip(r, spec.get('rmin', 0.0), spec.get('rmax', 1.0))
    # 包む面：近所の最大（2 輪）→ なめらかに → 元の半径より内へは入れない（体の凸凹が板を突き抜けない）
    env = raw.copy()
    for _ in range(spec.get('env_rings', 2)):
        m = env.copy()
        np.maximum.at(m, edges[:, 0], env[edges[:, 1]])
        np.maximum.at(m, edges[:, 1], env[edges[:, 0]])
        env = m
    env = smooth_r(env, edges, spec.get('smooth_iters', 4))
    r = np.maximum(env, raw - spec.get('raw_tol', 0.0))
    n = len(pts)
    bmask = np.zeros(n, bool)
    for lp in loops:
        bmask[lp] = True
    top = r + spec['off'] + spec['thick'] - np.where(bmask, spec.get('bevel', 0.0), 0.0)
    V = [org + dirs * top[:, None]]
    F = [tri]
    sink = spec.get('sink', 0.004)
    for lp in loops:
        base = sum(len(v) for v in V)
        bot = org[lp] + dirs[lp] * (r[lp] - sink)[:, None]
        V.append(bot)
        k = len(lp)
        for i in range(k):
            j = (i + 1) % k
            ti, tj = lp[i], lp[j]
            bi, bj = base + i, base + j
            F.append(np.array([[ti, bi, bj], [ti, bj, tj]]))
    info = {'r': r, 'pts': pts}
    return np.concatenate(V), np.concatenate(F), info


def build_box(spec: dict, bvh) -> tuple[np.ndarray, np.ndarray, dict]:
    fr = spec['frame']
    ang = math.radians(spec['ang'])
    s = np.array([ang * fr['RN']])
    t = np.array([spec['zc']])
    org, dirs = ray_dirs(fr, s, t)
    r = cast(bvh, org, dirs, spec.get('rmax', 0.25))
    r0 = float(r[0]) if np.isfinite(r[0]) else 0.15
    w, dep, h = spec['size']
    rad = dirs[0]
    up = fr['d']
    tan = np.cross(up, rad)
    out = []
    faces = []
    # 本体と、上の蓋（少し大きく前へ出る）
    for (cw, cd, ch, zo) in ((w, dep, h, 0.0), (w + 0.006, dep + 0.006, h * 0.32, h * 0.36)):
        c = org[0] + rad * (r0 + cd / 2 - 0.006) + up * zo
        base = sum(len(o) for o in out)
        corners = []
        for sz in (-1, 1):
            for sy in (-1, 1):
                for sx in (-1, 1):
                    corners.append(c + tan * sx * cw / 2 + rad * sy * cd / 2 + up * sz * ch / 2)
        out.append(np.array(corners))
        q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for a, b, cc, d in q:
            faces.append((base + a, base + b, base + cc))
            faces.append((base + a, base + cc, base + d))
    V = np.concatenate(out)
    F = np.array(faces)
    # 外向きにそろえる（箱の中心から面の中心への向き）
    for k in range(0, len(F), 12):
        cen = V[F[k:k + 12]].reshape(-1, 3).mean(0)
        for i in range(k, k + 12):
            p = V[F[i]]
            nrm = np.cross(p[1] - p[0], p[2] - p[0])
            if nrm @ (p.mean(0) - cen) < 0:
                F[i] = F[i][[0, 2, 1]]
    return V, F, {'r': np.array([r0]), 'pts': np.stack([s, t], 1)}


# ---------------------------------------------------------------- ゴーグルのヒモ（8 回目）

FIT = {}   # 当てはめの数値の記録（build_all の json に書く）



def build_goggle_strap(spec: dict, bvh) -> tuple[np.ndarray, np.ndarray, dict]:
    """髪の上を回る帯：断面は一定（幅 2·half・厚み thick、角は bevel で面取り）。縦の軸のまわりの角度 θ ごとに、
    帯の高さの範囲の髪の外の面（外から軸へ向けた光線の最初の当たり）の最大の半径を測り、角度で「近所の最大 → ぼかし」
    でなめらかにして（房ごとに波打たない）、その外に置く。帯の上下の縁の半径は別に当てはめる（頭の丸みに沿って傾く）"""
    from mathutils import Vector
    ax = np.array(spec['axis'], float)
    (y0, y1), (z0, z1) = spec['y'], spec['z']

    def zc_of(y):
        # 折れ線（下がる → 後ろは水平）の角を丸める（角のままだと斜め後ろから帯が折れて見えた）
        u = np.clip((np.asarray(y, float) - y0) / (y1 - y0), 0, None)
        a, b = 0.7, 1.3
        g = np.where(u < a, u, np.where(u > b, 1.0, u - (u - a) ** 2 / (2 * (b - a))))
        return z0 + (z1 - z0) * g

    def surf_r(th, z):
        """外から軸へ水平に撃って、最初に当たる面の軸からの距離（無ければ nan）"""
        d = np.array([math.sin(th), math.cos(th), 0.0])     # θ = 0 は後ろ（+Y）、+ は本人の左（+X）
        org = np.array([ax[0], ax[1], z]) + d * spec['rmax']
        hit = bvh.ray_cast(Vector(org), Vector(-d), spec['rmax'])
        return spec['rmax'] - hit[3] if hit[0] is not None else np.nan

    # 端の角度：中心の線が y = ends_y になる所（半径は 1 回目の測りで決める）
    th_all = np.linspace(-math.pi, math.pi, 721)[:-1]
    r0 = np.array([surf_r(t, 1.40) for t in th_all])
    r0 = np.where(np.isfinite(r0), r0, np.nanmedian(r0))
    yy = ax[1] + r0 * np.cos(th_all)
    side = np.abs(th_all)
    ok = yy > spec['ends_y']
    th_end = float(side[ok].max())
    n = spec['n']
    th = np.linspace(-th_end, th_end, n)
    half = spec['half']
    rows = np.linspace(-half, half, 7)
    # 2 回：中心の高さは帯の y（半径で決まる）に依る
    R = np.interp(np.abs(th), side[np.argsort(side)], r0[np.argsort(side)])
    for _ in range(2):
        yc = ax[1] + R * np.cos(th)
        zc = zc_of(yc)
        req = np.array([[surf_r(t, z + dz) for dz in rows] for t, z in zip(th, zc)])    # (n, rows)
        req = np.where(np.isfinite(req), req, np.nanmin(req))
        R = np.nanmax(req, 1)
    # 上・下の縁の半径：各列の面を「下の縁 rb・上の縁 rt の直線」より外に収める
    w = (rows + half) / (2 * half)

    def env(v, deg):
        k = max(1, int(round(deg / math.degrees(th[1] - th[0]))))
        out = v.copy()
        for s_ in range(1, k + 1):            # 近所の最大（端は端の値で延ばす）
            out = np.maximum(out, np.concatenate([v[s_:], np.repeat(v[-1], s_)]))
            out = np.maximum(out, np.concatenate([np.repeat(v[0], s_), v[:-s_]]))
        from scipy.ndimage import gaussian_filter1d
        return gaussian_filter1d(out, k * 0.6, mode='nearest')

    # 髪の「全体の丸み」：房の先は 5cm も外へ出る（とげの髪）ので、外の面の最大に合わせると帯が輪のように浮いた。
    # 角度の窓（±win_deg）の中の半径の分位（pct）をなめらかにした面を帯の内の面にし、そこより外へ出る房の先は
    # 帯の下へ押し込む（strap_push：帯が髪を押さえる。帯の上下の房はそのまま）
    def overall(v):
        from scipy.ndimage import gaussian_filter1d
        k = max(1, int(round(spec['win_deg'] / math.degrees(th[1] - th[0]))))
        pad = np.concatenate([np.repeat(v[0], k), v, np.repeat(v[-1], k)])
        o = np.array([np.percentile(pad[i:i + 2 * k + 1], spec['pct']) for i in range(len(v))])
        return gaussian_filter1d(o, k * 0.5, mode='nearest')
    rb = overall(np.median(req[:, :3], 1))
    rt = overall(np.median(req[:, -3:], 1))
    # 両端：ゴーグルの枠の横（|x| = end_x：右・左。枠の外の縁より 2mm 内。枠は左右で 9mm ずれている）へ入るように、最後の end_deg で半径を寄せる
    # （寄せないと髪のふくらみの外で、正面から枠の横に帯の端が耳のように出た）
    r_end = np.where(th > 0, spec['end_x'][1], spec['end_x'][0]) / np.maximum(np.abs(np.sin(th)), 0.3)
    fe = np.clip((np.abs(th) - (th_end - math.radians(spec['end_deg']))) / math.radians(spec['end_deg']), 0, 1)
    fe = fe * fe * (3 - 2 * fe)
    rb = np.where(fe > 0, rb * (1 - fe) + np.minimum(rb, r_end) * fe, rb)
    rt = np.where(fe > 0, rt * (1 - fe) + np.minimum(rt, r_end) * fe, rt)
    off, T, bv = spec['off'], spec['thick'], spec['bevel']
    yc = ax[1] + 0.5 * (rb + rt) * np.cos(th)
    zc = zc_of(yc)
    # 断面（帯の外向き u = 水平の外、縦 v = +z を、帯の傾きに合わせて回す）：内下 → 外下 → 外上 → 内上（面取り 8 点）
    sec = [(0.0, -half + bv), (bv, -half), (T - bv, -half), (T, -half + bv), (T, half - bv), (T - bv, half), (bv, half),
           (0.0, half - bv)]
    V = []
    for i, t in enumerate(th):
        d = np.array([math.sin(t), math.cos(t), 0.0])
        tilt = math.atan2(rt[i] - rb[i], 2 * half)     # 上が外へ出る角度
        u = d * math.cos(tilt) - np.array([0, 0, 1.0]) * math.sin(tilt)
        v = d * math.sin(tilt) + np.array([0, 0, 1.0]) * math.cos(tilt)
        rm = 0.5 * (rb[i] + rt[i]) + off
        c = np.array([ax[0], ax[1], zc[i]]) + d * rm
        for (a, b) in sec:
            V.append(c + u * a + v * b)
    V = np.array(V)
    m = len(sec)
    F = []
    for i in range(n - 1):
        for k in range(m):
            k2 = (k + 1) % m
            a, b, c, d_ = i * m + k, i * m + k2, (i + 1) * m + k2, (i + 1) * m + k
            F += [(a, b, c), (a, c, d_)]
    for i, flip in ((0, False), (n - 1, True)):       # 両端のふた
        ci = len(V)
        V = np.vstack([V, V[i * m:(i + 1) * m].mean(0)])
        for k in range(m):
            k2 = (k + 1) % m
            F.append((ci, i * m + k2, i * m + k) if not flip else (ci, i * m + k, i * m + k2))
    F = np.array(F)
    # 外向きにそろえる（閉じた形の符号つきの体積）
    vol = np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum()
    if vol < 0:
        F = F[:, [0, 2, 1]]
    PUSH.clear()
    PUSH.update(th=th, rb=rb + off, rt=rt + off, half=half, axis=ax, zc=zc_of, fall=spec['push_fall'],
                gap=spec['push_gap'], y_min=spec['push_y_min'])
    info = {'th_end_deg': round(math.degrees(th_end), 1), 'r_min': round(float(min(rb.min(), rt.min())), 4),
            'r_max': round(float(max(rb.max(), rt.max())), 4), 'z_range': [round(float(zc.min()), 3), round(float(zc.max()), 3)],
            'over_mm_p90': round(float(np.percentile(np.clip(req - (rb[:, None] * (1 - w[None]) + rt[:, None] * w[None]), 0, None), 90)) * 1000, 1)}
    return V, F, info


PUSH = {}


def strap_push(co: np.ndarray, hair: np.ndarray | None = None) -> tuple[np.ndarray, int]:
    """帯の高さで、帯の内の面（−gap）より外へ出ている髪の頂点を、軸へ向けて内の面まで押し込む（帯の縁の外 fall で
    なめらかに 0 へ）。返り値：(新しい座標, 動かした頂点の数)"""
    if not PUSH:
        return co, 0
    P = PUSH
    ax = P['axis']
    rel = co[:, :2] - ax
    r = np.linalg.norm(rel, axis=1)
    th = np.arctan2(rel[:, 0], rel[:, 1])        # 0 = 後ろ（+Y）、+ = 本人の左
    fy = np.clip((co[:, 1] - P['y_min']) / 0.015, 0, 1)        # ゴーグルの側へなめらかに 0（枠は押さない）
    inside = fy * fy * (3 - 2 * fy) * ((co[:, 2] > 1.25) & (co[:, 2] < 1.5) & (r > 0.05))
    if hair is not None:          # 髪の色の頂点だけ（ゴーグルの枠は押さない）
        inside = inside * hair
    rb = np.interp(th, P['th'], P['rb'])
    rt = np.interp(th, P['th'], P['rt'])
    zc = P['zc'](co[:, 1])
    dz = co[:, 2] - zc
    f = np.clip((dz + P['half']) / (2 * P['half']), 0, 1)
    line = rb * (1 - f) + rt * f - P['gap']
    a = np.clip((P['half'] + P['fall'] - np.abs(dz)) / P['fall'], 0, 1)
    a = a * a * (3 - 2 * a)
    over = np.clip(r - line, 0, None) * a * inside
    out = co.copy()
    scale = (r - over) / np.maximum(r, 1e-9)
    out[:, 0] = ax[0] + rel[:, 0] * scale
    out[:, 1] = ax[1] + rel[:, 1] * scale
    return out, int((over > 1e-4).sum())


def build_tube(spec: dict, bvh) -> tuple[np.ndarray, np.ndarray, dict]:
    """房の形の部品（白髪の房など）：頭の縦の軸のまわりの (正面からの角度, 高さ) の道に沿って、外の面（体の面＝髪の外側）の上に
    葉の形の断面（根元の 30% で最も広く、先がとがる）を並べた管。spec['tube'] = {axis: (x, y), side: ±1, path: [(角度, z), ...],
    width, thick, lift: (根, 先)}。色は部品ごとの 1 色なので、房全体が 1 色になる（塗りの縁が無い）"""
    tb = spec['tube']
    ax = np.array(tb['axis'], float)
    side = float(tb.get('side', 1.0))
    path = np.array(tb['path'], float)
    n = int(tb.get('n', 28))
    t = np.linspace(0.0, 1.0, n)
    kp = np.linspace(0.0, 1.0, len(path))
    th = np.radians(np.interp(t, kp, path[:, 0]))
    zz = np.interp(t, kp, path[:, 1])
    dirs = np.stack([side * np.sin(th), -np.cos(th), np.zeros(n)], 1)
    R0 = 0.30
    org = np.stack([ax[0] + R0 * dirs[:, 0], ax[1] + R0 * dirs[:, 1], zz], 1)
    d = cast(bvh, org, -dirs, R0)
    rs = R0 - np.where(np.isfinite(d), d, R0 - 0.08)
    rs = np.convolve(np.pad(rs, 2, mode='edge'), np.ones(5) / 5, mode='valid')     # 面の凸凹で波打たないように
    lift = tb['lift'][0] + (tb['lift'][1] - tb['lift'][0]) * t ** 2
    w = tb['width'] * 0.5 * (1 - t) ** 0.8 * (0.75 + 0.8 * t) + 0.0012
    h = np.maximum(w * tb.get('thick', 0.35), 0.0015)
    C = np.stack([ax[0] + (rs + lift + 0.25 * h) * dirs[:, 0], ax[1] + (rs + lift + 0.25 * h) * dirs[:, 1], zz], 1)
    T = np.gradient(C, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = dirs - (dirs * T).sum(1, keepdims=True) * T
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    B = np.cross(T, N)
    k = 12
    a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    rings = C[:, None] + B[:, None] * (w[:, None, None] * np.cos(a)[None, :, None]) \
        + N[:, None] * (h[:, None, None] * np.sin(a)[None, :, None])
    V = np.concatenate([rings.reshape(-1, 3), C[:1], C[-1:]])
    F = []
    for i in range(n - 1):
        for j in range(k):
            a0, a1 = i * k + j, i * k + (j + 1) % k
            b0, b1 = a0 + k, a1 + k
            F += [(a0, b0, b1), (a0, b1, a1)]
    c0, c1 = n * k, n * k + 1
    for j in range(k):
        F.append((c0, (j + 1) % k, j))
        F.append((c1, (n - 1) * k + j, (n - 1) * k + (j + 1) % k))
    F = np.array(F, np.int64)
    # 面の向きを外へ（閉じた形の符号つきの体積が正）
    vol = np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum()
    if vol < 0:
        F = F[:, ::-1]
    return V, F, {'hit': int(np.isfinite(d).sum()), 'n': n}


def build_all(verts: np.ndarray, tris: np.ndarray, out_npz: str | None = None, skip: tuple = ()) -> dict:
    """部品の形をすべて作る（skip の名前の部品は作らない：右手を部品にしたときの右の手袋のカフ）。
    返り値：{V, F, color（面ごとの色の番号）, bone（頂点ごとの骨の名前の番号）, bones, names}"""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([tuple(v) for v in verts], [tuple(int(i) for i in t) for t in tris])
    Vs, Fs, cols, vb, pn, sw = [], [], [], [], [], []
    bones = []
    report = {}
    off = 0
    for spec in pieces():
        if spec.get('clear_only') or spec['name'] in skip:   # 塗りだけを直す範囲（形は作らない）
            continue
        if spec.get('loft'):
            V, F, _ = build_loft(spec)
        elif spec.get('tube'):
            V, F, FIT[spec['name']] = build_tube(spec, bvh)
        elif spec.get('goggle_strap'):
            V, F, ginfo = build_goggle_strap(spec, bvh)
            FIT['goggle_strap'] = ginfo
        else:
            V, F, _ = build_box(spec, bvh) if spec.get('box') else build_shell(spec, bvh)
        if spec['bone'] not in bones:
            bones.append(spec['bone'])
        Vs.append(V)
        Fs.append(F + off)
        cols.append(np.full(len(F), NAMES.index(spec['color'])))
        vb.append(np.full(len(V), bones.index(spec['bone'])))
        if spec.get('ramp'):      # 靴：shin の重み（高さで foot からなめらかに）
            if spec['ramp'][0] not in bones:
                bones.append(spec['ramp'][0])
            sw.append(ramp_w(V[:, 2]))
        else:
            sw.append(np.full(len(V), -1.0))
        pn.append(np.full(len(F), len(report)))
        report[spec['name']] = len(F)
        off += len(V)
    res = {'V': np.concatenate(Vs), 'F': np.concatenate(Fs), 'color': np.concatenate(cols),
           'vbone': np.concatenate(vb), 'bones': np.array(bones), 'piece': np.concatenate(pn),
           'shin_w': np.concatenate(sw),
           'names': np.array(list(report))}
    if out_npz:
        np.savez(out_npz, **res)
        with open(os.path.splitext(out_npz)[0] + '.json', 'w') as fp:
            json.dump({'tris': int(len(res['F'])), 'pieces': report, 'fit': FIT}, fp, indent=1)
    return res


# ---------------------------------------------------------------- 下の体の塗り

def cover_body(pos: np.ndarray, col: np.ndarray, verts: np.ndarray, tris: np.ndarray) -> dict:
    """部品の下・まわりの体の色を替える（texture.py の res['pos']・res['col']。col は sRGB 0..1、その場で書き換える）"""
    from mathutils.bvhtree import BVHTree
    from scipy.spatial import cKDTree
    bvh = BVHTree.FromPolygons([tuple(v) for v in verts], [tuple(int(i) for i in t) for t in tris])
    pal = np.stack([hex_rgb(PALETTE[n]) for n in NAMES])
    lab = np.argmin(((col[:, None, :] - pal[None]) ** 2).sum(-1), 1)
    under = np.full(len(pos), -1)        # 部品の真下：決まった色（-2 = 周りの色）
    clear = np.zeros(len(pos), bool)     # まわりの帯：部品の色だけ周りの色へ
    stats = {}
    ins_by = {}
    for spec in pieces():
        if not spec.get('under') and not spec.get('clear'):
            continue
        s, t, r = param_of(spec, pos)
        fr = spec['frame']
        near = r < spec.get('rmax', 0.2) + 0.02
        if spec.get('box'):
            ang = math.radians(spec['ang'])
            w, dep, h = spec['size']
            ds = np.abs(s - ang * fr['RN'])
            dt = np.abs(t - spec['zc'])
            ins = near & (ds < w / 2) & (dt < h / 2)
            band = near & (ds < w / 2 + spec['margin']) & (dt < h / 2 + spec['margin'])
        else:
            if spec.get('ring'):
                t0, t1 = t_range(spec, s, 't0'), t_range(spec, s, 't1')
                ins0 = (t > t0) & (t < t1)
                dist = np.where(ins0, 0.0, np.minimum(np.abs(t - t0), np.abs(t - t1)))
            else:
                poly = np.array(spec['outline'], float)
                st = np.stack([s, t], 1)
                cand = near & (np.abs(s) < 4) & (t > poly[:, 1].min() - 0.06) & (t < poly[:, 1].max() + 0.06)
                ins0 = np.zeros(len(pos), bool)
                dist = np.full(len(pos), np.inf)
                ci = np.nonzero(cand)[0]
                ins0[ci] = inside_poly(st[ci], poly)
                dist[ci] = np.where(ins0[ci], 0.0, poly_dist(st[ci], poly))
            # 体の面が部品の内側の面の近くにある所だけ（同じ向きの奥の面・別の手足は除く）
            org, dirs = ray_dirs(fr, s, t)
            cand = np.nonzero(near & (dist < spec.get('margin', 0.0) + 1e-9))[0]
            ok = np.zeros(len(pos), bool)
            if len(cand):
                rr = cast(bvh, org[cand], dirs[cand], spec.get('rmax', 0.2) + 0.03)
                ok[cand] = np.isfinite(rr) & (np.abs(rr - r[cand]) < 0.006)
            ins = ok & ins0
            band = ok & (dist < spec.get('margin', 0.0))
        ins_by[spec['name']] = ins.copy()
        if spec.get('under'):
            under[ins] = NAMES.index(spec['under'])
        elif spec.get('clear') and not spec.get('clear_only'):
            under[ins & (under == -1)] = -2
        if spec.get('clear'):
            cl = np.isin(lab, [NAMES.index(c) for c in spec['clear']])
            if spec.get('fill'):      # 決まった色で埋める（近い色の写しだと放射状の筋になる所）
                fm = band & cl & (under < 0)
                under[fm] = NAMES.index(spec['fill'])
            else:
                clear |= band & cl
        stats[spec['name']] = int(ins.sum())
    for rule in BOX_RULES:
        (x0, x1), (y0, y1), (z0, z1) = rule['box']
        inb = ((pos[:, 0] > x0) & (pos[:, 0] < x1) & (pos[:, 1] > y0) & (pos[:, 1] < y1)
               & (pos[:, 2] > z0) & (pos[:, 2] < z1))
        if 'keep' in rule:
            kp = np.isin(lab, [NAMES.index(c) for c in rule['keep']])
            dpal = np.linalg.norm(col - pal[lab], axis=1)
            cl = inb & ~(kp & (dpal < rule['tol'])) & (under < 0)
        else:
            cl = inb & np.isin(lab, [NAMES.index(c) for c in rule['clear']]) & (under < 0)
        src = inb & ~cl
        if rule.get('fill'):
            under[cl] = NAMES.index(rule['fill'])
        elif cl.any() and src.any():
            tree = cKDTree(pos[src])
            _, nn = tree.query(pos[cl], k=1)
            col[cl] = col[np.nonzero(src)[0][nn]]
            lab[cl] = lab[np.nonzero(src)[0][nn]]
        stats[rule['name']] = int(cl.sum())
    if body_rules is not None:      # キャラクターの決まりの塗り（脚・胴・首など。chars/<id>_parts.py）
        body_rules(pos, col, lab, under, ins_by, stats)
    fixed = under >= 0
    col[fixed] = pal[under[fixed]]
    lab[fixed] = under[fixed]
    todo = (under == -2) | (clear & ~fixed)
    src = ~todo & ~fixed
    if todo.any() and src.any():
        tree = cKDTree(pos[src])
        _, nn = tree.query(pos[todo], k=1)
        si = np.nonzero(src)[0][nn]
        col[todo] = col[si]
    stats['under_texels'] = int(fixed.sum())
    stats['cleared_texels'] = int(todo.sum())
    return stats


def palette_image(path: str) -> str:
    from PIL import Image
    img = np.zeros((32, 32 * CELLS, 3), np.uint8)
    for i, n in enumerate(NAMES):
        img[:, i * 32:(i + 1) * 32] = (hex_rgb(PALETTE[n]) * 255).round().astype(np.uint8)
    Image.fromarray(img).save(path)
    return path


def palette_uv(color_idx: np.ndarray) -> np.ndarray:
    """色の番号 → UV（Blender の UV、区画の中心）"""
    return np.stack([(color_idx + 0.5) / CELLS, np.full(len(color_idx), 0.5)], 1)


# ---------------------------------------------------------------- キャラクターの部品を読み込む

PARTS_MAT = f'{CH.ID}_parts'      # 部品の材質の名前（haru_parts）
_TOOLS = ('hex_rgb', 'jp', 'unit', 'frame', 'octagon', 'circle', 'rrect', 'param_of', 'inside_poly', 'poly_dist')


def _load_parts(char_id: str):
    """chars/<id>_parts.py を読み込み、その大文字の定数と pieces・boot_pieces・body_rules をこのモジュールに入れる。
    ファイルが無ければ部品なし（pieces() は空）"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chars', f'{char_id}_parts.py')
    if not os.path.exists(path):
        return None
    spec = importlib.util.spec_from_file_location(f'costume_parts_{char_id}', path)
    mod = importlib.util.module_from_spec(spec)
    for k in _TOOLS:               # 道具を先に渡す（部品の表が import しないで使える）
        setattr(mod, k, globals()[k])
    spec.loader.exec_module(mod)
    g = globals()
    for k, v in vars(mod).items():
        if (k.isupper() and not k.startswith('_')) or k in ('pieces', 'boot_pieces', 'body_rules'):
            g[k] = v
    return mod


def pieces() -> list[dict]:       # 部品の表が無いキャラクター（読み込みで上書きされる）
    return []


PARTS = _load_parts(CH.ID)
NAMES = list(PALETTE)
