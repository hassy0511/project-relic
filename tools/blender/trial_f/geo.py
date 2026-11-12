"""haru_f：形を作る道具（numpy だけ。Blender は使わない）。

座標は Blender と同じ：x = 本人の左が正、y = 後ろが正（正面は -y）、z = 上。単位は m。
部品は Mesh.add で足す：頂点・面（多角形）・色の名前（面ごとでもよい）・なめらか／平ら・重み。
閉じた部品は符号つきの体積で面の向きを外向きにそろえる。
"""
from __future__ import annotations

import math

import numpy as np

V = lambda *a: np.array(a, dtype=float)


def norm(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def lerp(a, b, t):
    return np.asarray(a, dtype=float) * (1 - t) + np.asarray(b, dtype=float) * t


def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def rot_axis(axis, ang):
    """軸まわりの回転行列（ラジアン、右ねじ）"""
    a = norm(axis)
    c, s = math.cos(ang), math.sin(ang)
    x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def frame_from(t, hint=(0, -1, 0)):
    """接線 t に直角な 2 本（u, v）。u × v = t。hint にいちばん近い向きを v にする"""
    t = norm(t)
    h = np.asarray(hint, dtype=float)
    v = h - t * np.dot(h, t)
    if np.linalg.norm(v) < 1e-6:
        h = V(1, 0, 0)
        v = h - t * np.dot(h, t)
    v = norm(v)
    u = np.cross(v, t)
    return u, v, t


class Mesh:
    """部品の集まり（1 つの物体になる）"""

    def __init__(self, name):
        self.name = name
        self.v = []          # 頂点
        self.f = []          # 面（頂点の番号の並び）
        self.col = []        # 面ごとの色の名前
        self.smooth = []     # 面ごと：なめらかに陰を付けるか
        self.w = []          # 頂点ごとの重み {骨: 値}
        self.uv = []         # 頂点ごとの顔の UV（顔の材質の面だけ。None = 色見本）
        self.piece = []      # 面ごとの部品の名前（確かめ用）
        self.fuv = []        # 面ごとの角の UV（顔の材質。None = 頂点の UV か肌の点）

    def add(self, verts, faces, color, weights, smooth=False, closed=True, name='', uv=None, flip=False, face_uv=None):
        verts = [np.asarray(p, dtype=float) for p in verts]
        faces = [list(f) for f in faces]
        if not closed:
            # 開いた殻：面が重心から外を向くようにそろえる
            cen = sum(verts) / len(verts)
            tot = 0.0
            for f in faces:
                fc = sum(verts[k] for k in f) / len(f)
                nrm = np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])
                tot += float(np.dot(nrm, fc - cen))
            if tot < 0:
                faces = [f[::-1] for f in faces]
                if face_uv is not None:
                    face_uv = [u[::-1] if u is not None else None for u in face_uv]
        if closed:
            vol = 0.0
            for f in faces:
                a = verts[f[0]]
                for k in range(1, len(f) - 1):
                    vol += np.dot(a, np.cross(verts[f[k]], verts[f[k + 1]]))
            if vol < 0:
                faces = [f[::-1] for f in faces]
                if face_uv is not None:
                    face_uv = [u[::-1] if u is not None else None for u in face_uv]
        if flip:
            faces = [f[::-1] for f in faces]
        base = len(self.v)
        self.v.extend(verts)
        for i, f in enumerate(faces):
            self.f.append([base + k for k in f])
            self.col.append(color[i] if isinstance(color, (list, tuple)) else color)
            self.smooth.append(smooth[i] if isinstance(smooth, (list, tuple)) else bool(smooth))
            self.piece.append(name)
            self.fuv.append(face_uv[i] if face_uv is not None else None)
        if callable(weights):
            ws = [weights(p) for p in verts]
        elif isinstance(weights, str):
            ws = [{weights: 1.0} for _ in verts]
        elif isinstance(weights, dict):
            ws = [dict(weights) for _ in verts]
        else:
            ws = [dict(w) for w in weights]
        self.w.extend(ws)
        self.uv.extend(uv if uv is not None else [None] * len(verts))
        return base

    def tri_count(self):
        return sum(len(f) - 2 for f in self.f)


# ---------- 断面と積み重ね ----------

def sring(n, rx, ry, exp=2.0, phase=0.0):
    """超楕円の 2D の輪（n 点）。phase は 1 点目の角度（辺の数ぶんの割合。0.5 で辺が正面）"""
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + phase) / n
        c, s = math.cos(a), math.sin(a)
        e = 2.0 / exp
        pts.append((rx * math.copysign(abs(c) ** e, c), ry * math.copysign(abs(s) ** e, s)))
    return pts


def place(pts2, center, u, v):
    c = np.asarray(center, dtype=float)
    return [c + u * p[0] + v * p[1] for p in pts2]


def loft(rings, cap0=True, cap1=True, split_caps=False):
    """同じ点数の輪を順につなぐ。戻り値：頂点、面、面の種類（'side'/'cap0'/'cap1'）"""
    n = len(rings[0])
    verts = [p for r in rings for p in r]
    faces, kinds = [], []
    for i in range(len(rings) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            c, d = (i + 1) * n + (j + 1) % n, (i + 1) * n + j
            faces.append([a, b, c, d])
            kinds.append('side')
    if cap0:
        if split_caps:
            base = len(verts)
            verts += list(rings[0])
            faces.append([base + k for k in range(n)][::-1])
        else:
            faces.append(list(range(n))[::-1])
        kinds.append('cap0')
    if cap1:
        o = (len(rings) - 1) * n
        if split_caps:
            base = len(verts)
            verts += list(rings[-1])
            faces.append([base + k for k in range(n)])
        else:
            faces.append([o + k for k in range(n)])
        kinds.append('cap1')
    return verts, faces, kinds


def tube(path, n=8, exp=2.0, hint=(0, -1, 0), phase=0.0, cap0=True, cap1=True, twist=0.0, split_caps=False):
    """path = [(中心, rx, ry), …] を通る筒。断面の rx は u（横）、ry は v（hint の向き）"""
    cs = [np.asarray(p[0], dtype=float) for p in path]
    rings = []
    for i, p in enumerate(path):
        if i == 0:
            t = cs[1] - cs[0]
        elif i == len(path) - 1:
            t = cs[-1] - cs[-2]
        else:
            t = norm(cs[i + 1] - cs[i]) + norm(cs[i] - cs[i - 1])
        u, v, _ = frame_from(t, hint)
        if len(p) > 3 and p[3] is not None:
            u, v, _ = frame_from(p[3], hint)      # 断面の向きを指定（斜めに切る）
        if twist:
            r = rot_axis(norm(t), twist * i / (len(path) - 1))
            u, v = r @ u, r @ v
        e = p[4] if len(p) > 4 else exp
        rings.append(place(sring(n, p[1], p[2], e, phase), cs[i], u, v))
    return loft(rings, cap0, cap1, split_caps)


def prism(poly, origin, ex, ey, ez, depth, bevel=0.0, back=0.0):
    """平らな多角形（2D、反時計回り）を ez の向きに厚み depth で押し出す板。
    bevel > 0 なら表の面を内へ縮めて面取り（縁に斜めの面）。back：裏を ez の逆へ下げる量"""
    o = np.asarray(origin, dtype=float)
    P = lambda p, h: o + ex * p[0] + ey * p[1] + ez * h
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    rings = [[P(p, -back) for p in poly]]
    if bevel > 0:
        rings.append([P(p, depth - bevel) for p in poly])
        ins = inset_poly(poly, bevel)
        rings.append([P(p, depth) for p in ins])
    else:
        rings.append([P(p, depth) for p in poly])
    return loft(rings, True, True)


def inset_poly(poly, d):
    """凸に近い多角形を内へ d だけ縮める（辺を平行に動かして交点を取る）"""
    n = len(poly)
    out = []
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    lines = []
    for i in range(n):
        a, b = np.array(poly[i], float), np.array(poly[(i + 1) % n], float)
        t = norm(b - a)
        nrm = np.array([-t[1], t[0]]) * sgn     # 内向き
        lines.append((a + nrm * d, t))
    for i in range(n):
        p1, t1 = lines[i - 1]
        p2, t2 = lines[i]
        den = t1[0] * t2[1] - t1[1] * t2[0]
        if abs(den) < 1e-9:
            out.append(tuple(p2))
        else:
            s = ((p2[0] - p1[0]) * t2[1] - (p2[1] - p1[1]) * t2[0]) / den
            out.append(tuple(p1 + t1 * s))
    return out


def box(center, size, ex=V(1, 0, 0), ey=V(0, 1, 0), ez=V(0, 0, 1), chamfer=0.0):
    """面取りした箱（chamfer > 0 で角を落とした八角柱を上下も絞る）"""
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    c = np.asarray(center, dtype=float)
    if chamfer <= 0:
        poly = [(-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)]
        return prism(poly, c - ez * sz, ex, ey, ez, size[2])
    ch = chamfer
    poly = [(-sx + ch, -sy), (sx - ch, -sy), (sx, -sy + ch), (sx, sy - ch), (sx - ch, sy), (-sx + ch, sy), (-sx, sy - ch), (-sx, -sy + ch)]
    ins = inset_poly(poly, ch)
    P = lambda p, h: c + ex * p[0] + ey * p[1] + ez * h
    rings = [[P(p, -sz) for p in ins], [P(p, -sz + ch) for p in poly], [P(p, sz - ch) for p in poly], [P(p, sz) for p in ins]]
    return loft(rings, True, True)


def grid_shell(grid, thickness, inward):
    """点の格子（行 × 列）の面に厚みを付けた殻。inward(p) = その点で内へ向かう単位の向き"""
    rows, cols = len(grid), len(grid[0])
    outer = [np.asarray(p, dtype=float) for r in grid for p in r]
    inner = [p + np.asarray(inward(p), dtype=float) * thickness for p in outer]
    verts = outer + inner
    N = rows * cols
    faces, kinds = [], []
    idx = lambda i, j: i * cols + j
    for i in range(rows - 1):
        for j in range(cols - 1):
            faces.append([idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)])
            kinds.append('outer')
            faces.append([N + idx(i, j), N + idx(i + 1, j), N + idx(i + 1, j + 1), N + idx(i, j + 1)])
            kinds.append('inner')
    # 縁
    edge = [(0, j, 0, j + 1) for j in range(cols - 1)] + [(i, cols - 1, i + 1, cols - 1) for i in range(rows - 1)] \
        + [(rows - 1, j + 1, rows - 1, j) for j in range(cols - 1)] + [(i + 1, 0, i, 0) for i in range(rows - 1)]
    for (i0, j0, i1, j1) in edge:
        a, b = idx(i0, j0), idx(i1, j1)
        faces.append([b, a, N + a, N + b])
        kinds.append('edge')
    return verts, faces, kinds


def leaf(root, tip, ctrl, width, thick, out, segs=4, wpos=0.38, ridge=1.0, root_w=0.45, tip_cut=0.0):
    """葉の形の房：root → ctrl → tip の曲線に沿う、菱形の断面。out は房の表（外）の向きの目安。
    width・thick は最大の幅・厚み。wpos は幅が最大になる位置（0〜1）"""
    root, tip, ctrl = (np.asarray(p, dtype=float) for p in (root, tip, ctrl))
    rings = []
    for i in range(segs + 1):
        t = i / segs * (1.0 - tip_cut)
        p = (1 - t) ** 2 * root + 2 * (1 - t) * t * ctrl + t * t * tip
        d = norm(2 * (1 - t) * (ctrl - root) + 2 * t * (tip - ctrl))
        o = np.asarray(out(p) if callable(out) else out, dtype=float)
        o = norm(o - d * np.dot(o, d))
        s = np.cross(d, o)
        # 幅：根で root_w、wpos で 1、先で 0
        if t < wpos:
            w = root_w + (1 - root_w) * math.sin(t / wpos * math.pi / 2)
        else:
            w = (1.0 - (t - wpos) / (1 - wpos)) ** 0.78
        w = max(w, 0.0)
        hw, ht = width * 0.5 * w, thick * (0.30 + 0.70 * w)
        if i == segs and tip_cut == 0.0:
            rings.append([p, p, p, p])
        else:
            rings.append([p - s * hw, p + o * ht * ridge, p + s * hw, p - o * ht * 0.22])
    verts, faces = [], []
    n = 4
    for r in rings:
        verts += r
    for i in range(segs):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            c, d2 = (i + 1) * n + (j + 1) % n, (i + 1) * n + j
            if i == segs - 1 and tip_cut == 0.0:
                faces.append([a, b, c])
            else:
                faces.append([a, b, c, d2])
    faces.append([0, 1, 2, 3][::-1])
    if tip_cut:
        o2 = segs * n
        faces.append([o2, o2 + 1, o2 + 2, o2 + 3])
    return verts, faces


def mirror_x(verts):
    return [np.array([-p[0], p[1], p[2]]) for p in verts]


def transform(verts, R=None, t=None, s=None):
    out = []
    for p in verts:
        q = np.asarray(p, dtype=float)
        if s is not None:
            q = q * s
        if R is not None:
            q = R @ q
        if t is not None:
            q = q + t
        out.append(q)
    return out


def split_groups(verts, faces, groups):
    """面の組（groups[i]）が違う面どうしで頂点を分ける（なめらかな陰でも、組の境は折れ目のまま残る）"""
    out_v, out_f, remap = [], [], {}
    for f, g in zip(faces, groups):
        nf = []
        for k in f:
            key = (g, k)
            if key not in remap:
                remap[key] = len(out_v)
                out_v.append(verts[k])
            nf.append(remap[key])
        out_f.append(nf)
    return out_v, out_f


def petal(root, tip, ctrl, width, thick, out, segs=6, wpos=0.42, root_w=0.55, dome=0.74, under=0.16, sharp=0.85):
    """花びら形の房：root → ctrl → tip の曲線に沿う、幅の広い葉。表は真ん中の稜で 2 つのなめらかな面に分かれ、裏は平ら。
    戻り値：頂点、面、面の種類（'L'・'R'＝表の左右、'U'＝裏、'C'＝根のふた）、頂点ごとの位置 t（0 = 根、1 = 先）"""
    root, tip, ctrl = (np.asarray(p, dtype=float) for p in (root, tip, ctrl))
    rings = []
    for i in range(segs):
        t = i / segs
        p = (1 - t) ** 2 * root + 2 * (1 - t) * t * ctrl + t * t * tip
        d = norm(2 * (1 - t) * (ctrl - root) + 2 * t * (tip - ctrl))
        o = np.asarray(out(p) if callable(out) else out, dtype=float)
        o = norm(o - d * np.dot(o, d))
        s = np.cross(d, o)
        if t < wpos:
            w = root_w + (1 - root_w) * math.sin(t / wpos * math.pi / 2)
        else:
            w = (1.0 - (t - wpos) / (1 - wpos)) ** sharp
        hw, h = width * 0.5 * w, thick * (0.25 + 0.75 * w)
        rings.append({'eL': p - s * hw, 'mL': p - s * hw * 0.52 + o * h * dome, 'r': p + o * h,
                      'mR': p + s * hw * 0.52 + o * h * dome, 'eR': p + s * hw, 'b': p - o * h * under})
    verts, faces, kinds, ts = [], [], [], []
    for kind, keys in (('L', ('eL', 'mL', 'r')), ('R', ('r', 'mR', 'eR')), ('U', ('eR', 'b', 'eL'))):
        base = len(verts)
        for i, rg in enumerate(rings):
            for k in keys:
                verts.append(rg[k])
                ts.append(i / segs)
        tip_i = len(verts)
        verts.append(tip)
        ts.append(1.0)
        for i in range(segs - 1):
            for k in range(2):
                a, b = base + i * 3 + k, base + i * 3 + k + 1
                c, e = base + (i + 1) * 3 + k + 1, base + (i + 1) * 3 + k
                faces.append([a, b, c, e])
                kinds.append(kind)
        o2 = base + (segs - 1) * 3
        for k in range(2):
            faces.append([o2 + k, o2 + k + 1, tip_i])
            kinds.append(kind)
    base = len(verts)
    order = ('eL', 'mL', 'r', 'mR', 'eR', 'b')
    for k in order:
        verts.append(rings[0][k])
        ts.append(0.0)
    faces.append([base + k for k in range(6)][::-1])
    kinds.append('C')
    return verts, faces, kinds, ts
