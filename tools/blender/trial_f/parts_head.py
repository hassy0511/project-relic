"""haru_f：頭（肌）・耳・髪（土台と葉の房）・ゴーグルとヒモ。
頭は高さごとの断面（半幅・前・後ろ）の表から作る。顔は正面から絵（face_tex.py）を貼る。"""
from __future__ import annotations

import math

import numpy as np

from . import geo
from .geo import V, norm, lerp, smoothstep

# 頭の断面（z, 半幅, 前の y, 後ろの y）。全身の絵の寸法（あご 120.5 cm、目 131 cm、頭頂 149 cm）
HEAD = [(1.203, 0.022, -0.096, -0.052), (1.211, 0.046, -0.108, -0.022), (1.224, 0.070, -0.115, 0.018),
        (1.240, 0.088, -0.119, 0.050), (1.258, 0.101, -0.1205, 0.076), (1.267, 0.106, -0.1205, 0.087),
        (1.276, 0.110, -0.120, 0.096), (1.295, 0.116, -0.118, 0.110), (1.315, 0.120, -0.116, 0.120),
        (1.335, 0.123, -0.114, 0.126), (1.360, 0.124, -0.111, 0.130), (1.390, 0.122, -0.105, 0.130),
        (1.420, 0.114, -0.095, 0.124), (1.450, 0.098, -0.079, 0.110), (1.475, 0.072, -0.055, 0.086),
        (1.490, 0.040, -0.027, 0.054)]
HEAD_TOP = V(0, 0.014, 1.497)
# 列の角度（正面 0、左 90、後ろ 180）。鼻のまわりを細かく
COLS = [0, 3.5, 7.5, 15, 27, 40, 53, 66, 78, 90, 104, 118, 132, 146, 160, 170, 180]
COLS = COLS + [360 - a for a in COLS[-2:0:-1]]
FACE_EXP, BACK_EXP = 2.35, 2.0
# 顔の地図（区画 1 つ）が覆う範囲：x（m）と z（m）
FACE_X = (-0.14, 0.14)
FACE_Z = (1.19, 1.47)


def profile(z, table=HEAD):
    if z <= table[0][0]:
        return table[0][1:]
    for a, b in zip(table, table[1:]):
        if z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return tuple(a[k] + (b[k] - a[k]) * t for k in (1, 2, 3))
    return table[-1][1:]


def surf(phi_deg, z, grow=0.0, back_grow=None):
    """頭の面の点（grow：外へふくらませる量。髪の土台用）"""
    w, yf, yb = profile(z)
    bg = grow if back_grow is None else back_grow
    w, yf, yb = w + grow, yf - grow, yb + bg
    yc, hd = (yf + yb) / 2, (yb - yf) / 2
    a = math.radians(phi_deg)
    s, c = math.sin(a), math.cos(a)
    e = 2.0 / (FACE_EXP if c > 0 else BACK_EXP)
    ex = 2.0 / FACE_EXP if c > 0 else 2.0 / BACK_EXP
    return V(w * math.copysign(abs(s) ** ex, s), yc - hd * math.copysign(abs(c) ** e, c), z)


def radial(p):
    """頭の軸から外へ向かう向き（上の方は上向きを混ぜる）"""
    d = V(p[0], p[1] - 0.010, (p[2] - 1.36) * 0.9)
    return norm(d)


def nose_push(x, z):
    """鼻：中心の列だけ前へ"""
    if abs(x) > 0.03:
        return 0.0
    prof = [(1.240, 0.0), (1.258, 0.005), (1.267, 0.0175), (1.276, 0.011), (1.295, 0.004), (1.315, 0.0)]
    h = 0.0
    for a, b in zip(prof, prof[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            h = a[1] + (b[1] - a[1]) * t
    return h * math.exp(-(x / 0.0125) ** 2)


def face_uv_of(p):
    u = (p[0] - FACE_X[0]) / (FACE_X[1] - FACE_X[0]) * 0.5
    v = 0.5 + (p[2] - FACE_Z[0]) / (FACE_Z[1] - FACE_Z[0]) * 0.5
    return (u, v)


def build_head(m):
    rows = []
    for (z, w, yf, yb) in HEAD:
        row = []
        for a in COLS:
            p = surf(a, z)
            p = p + V(0, -nose_push(p[0], z), 0)
            row.append(p)
        rows.append(row)
    n = len(COLS)
    verts = [p for r in rows for p in r] + [HEAD_TOP]
    faces = []
    for i in range(len(rows) - 1):
        for j in range(n):
            faces.append([i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j])
    top = len(verts) - 1
    o = (len(rows) - 1) * n
    for j in range(n):
        faces.append([o + j, o + (j + 1) % n, top])
    faces.append(list(range(n))[::-1])
    fuv = []
    for f in faces:
        pts = [verts[k] for k in f]
        if all(p[1] < -0.012 and abs(p[0]) < 0.122 for p in pts) and len(f) == 4:
            fuv.append([face_uv_of(p) for p in pts])
        else:
            fuv.append(None)
    cols = ['face' if u is not None else 'skin' for u in fuv]
    m.add(verts, faces, cols, 'head', smooth=True, name='head', face_uv=fuv)
    # 耳
    for side in (1, -1):
        poly = [(-0.012, -0.034), (0.008, -0.037), (0.021, -0.020), (0.026, 0.010), (0.019, 0.031), (0.003, 0.038), (-0.013, 0.028), (-0.016, -0.008)]
        c = V(side * 0.110, 0.022, 1.296)
        ex = norm(V(side * 0.30, 1.0, 0))            # 前後（後ろへ行くほど外へ開く）
        ez = norm(V(side * 1.0, -0.30, 0))            # 外
        v, f, _ = geo.prism(poly, c, ex, V(0, 0, 1), ez, 0.030, bevel=0.010)
        m.add(v, f, 'skin', 'head', smooth=True, name='ear')


# ---------- 髪 ----------

def hairline(phi):
    """生え際の高さ（正面からの角度ごと）"""
    a = abs(((phi + 180) % 360) - 180)
    pts = [(0, 1.408), (45, 1.404), (62, 1.372), (78, 1.345), (95, 1.318), (108, 1.262), (125, 1.240), (180, 1.236)]
    for p, q in zip(pts, pts[1:]):
        if a <= q[0]:
            t = (a - p[0]) / (q[0] - p[0])
            t = t * t * (3 - 2 * t)
            return p[1] + (q[1] - p[1]) * t
    return pts[-1][1]


CAP_GROW = 0.026


def cap_pt(phi, z, extra=0.0):
    return surf(phi, min(z, 1.489), CAP_GROW + extra, CAP_GROW + 0.012 + extra)


def build_cap(m):
    cols_a = [a for a in range(0, 360, 12)]
    K = 9
    rows = []
    for k in range(K):
        row = []
        for a in cols_a:
            z0 = hairline(a)
            t = k / (K - 1)
            z = z0 + (1.489 - z0) * (1 - (1 - t) ** 1.6)
            row.append(cap_pt(a, z))
        rows.append(row)
    n = len(cols_a)
    verts = [p for r in rows for p in r] + [HEAD_TOP + V(0, 0, CAP_GROW)]
    faces = []
    for i in range(K - 1):
        for j in range(n):
            faces.append([i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j])
    top = len(verts) - 1
    o = (K - 1) * n
    for j in range(n):
        faces.append([o + j, o + (j + 1) % n, top])
    m.add(verts, faces, 'hair_dk', 'head', smooth=True, closed=False, name='hair_cap')


def lock(m, root, tip, width, thick=0.016, lift=0.02, bone=None, sway=0.0, wpos=0.40, segs=4, root_w=0.5, col='hair', ctrl_t=0.5, ridge=1.0):
    """葉の房。root・tip は (角度, z, 外への浮き) か座標。lift：真ん中を外へふくらませる量"""
    def pt(q):
        if q[0] == 'a':                               # 角度の指定：('a', 度, z, 外への浮き)
            p = cap_pt(q[1], q[2])
            return p + radial(p) * q[3]
        return V(*q)
    r, t = pt(root), pt(tip)
    mid = lerp(r, t, ctrl_t)
    c = mid + radial(mid) * lift
    v, f = geo.leaf(r, t, c, width, thick, radial, segs=segs, wpos=wpos, root_w=root_w, ridge=ridge)
    if bone and sway > 0:
        ws = []
        for i in range(len(v)):
            tt = (i // 4) / segs
            s = sway * smoothstep(0.15, 1.0, tt)
            ws.append({'head': 1 - s, bone: s})
    else:
        ws = 'head'
    m.add(v, f, col, ws, smooth=False, name='lock')


def strap_z(phi):
    """ゴーグルのヒモの高さ（こめかみで高く、耳の後ろからは水平）"""
    a = abs(((phi + 180) % 360) - 180)
    t = max(0.0, min(1.0, (128 - a) / 62.0))
    return 1.350 + (1.432 - 1.350) * t ** 1.15


def build_hair(m):
    build_cap(m)
    L = lambda *a, **k: lock(m, *a, **k)
    crown = (0.0, 0.040, 1.512)

    def bone_of(a):
        a = a % 360
        if a < 50 or a > 310:
            return 'hair.front'
        if a < 115:
            return 'hair.side.L'
        if a <= 180:
            return 'hair.back.L'
        if a < 245:
            return 'hair.back.R'
        return 'hair.side.R'
    # --- 頭頂の立った房（前へ・上へ。絵の頭のてっぺんのとげ） ---
    L((0.030, 0.005, 1.502), (-0.055, -0.090, 1.562), 0.100, 0.022, lift=0.030, bone='hair.top', sway=0.7, root_w=0.7, wpos=0.40)
    L((0.055, 0.040, 1.502), (0.050, -0.030, 1.558), 0.086, 0.020, lift=0.026, bone='hair.top', sway=0.7, root_w=0.7, wpos=0.40)
    L((-0.035, 0.045, 1.502), (-0.112, 0.005, 1.534), 0.084, 0.020, lift=0.024, bone='hair.top', sway=0.65, root_w=0.7)
    # --- 1 段目：つむじから放射状（太い葉。先はヒモの上の方で外へとがる） ---
    for a in (50, 90, 130, 167, 205, 242, 280, 318):
        zt = strap_z(a) + 0.078
        L(crown, ('a', a, zt, 0.050), 0.124, 0.020, lift=0.030, bone=bone_of(a), sway=0.45, wpos=0.52, root_w=0.5, segs=5)
    # --- 2 段目：ヒモのすぐ上で外へ張り出す（いちばん外の輪郭） ---
    for a in (70, 110, 148, 186, 224, 262, 298):
        zr, zt = strap_z(a) + 0.110, strap_z(a) + 0.006
        L(('a', a - 5 if a < 180 else a + 5, zr, 0.010), ('a', a, zt, 0.072), 0.118, 0.022, lift=0.036, bone=bone_of(a), sway=0.55, wpos=0.46, root_w=0.55, segs=5)
    # --- 3 段目：ヒモの下から下・外へ（真横は外へはっきり張り出す） ---
    for a in (106, 136, 166, 194, 224, 254):
        zr, zt = strap_z(a) - 0.000, strap_z(a) - 0.098
        tip = ('a', a, zt, 0.058)
        wd = 0.108
        if a in (106, 254):
            tip = ((1 if a == 106 else -1) * 0.196, 0.085, 1.300)
            wd = 0.112
        L(('a', a, zr, 0.006), tip, wd, 0.020, lift=0.030, bone=bone_of(a), sway=0.55, wpos=0.44, root_w=0.55, segs=5)
    # --- 4 段目：えり足（下へとがる） ---
    for (a, zt, out, w) in ((108, 1.226, 0.030, 0.078), (138, 1.208, 0.034, 0.086), (166, 1.196, 0.032, 0.088), (194, 1.196, 0.032, 0.088), (222, 1.208, 0.034, 0.086), (252, 1.226, 0.030, 0.078)):
        L(('a', a, strap_z(a) - 0.066, 0.004), ('a', a, zt, out), w, 0.018, lift=0.024, bone='hair.nape', sway=0.5, wpos=0.42, root_w=0.6)
    L(('a', 180, 1.275, 0.004), ('a', 180, 1.190, 0.022), 0.074, 0.016, lift=0.018, bone='hair.nape', sway=0.5, root_w=0.65)
    # --- 前髪：真ん中のくさび、こめかみの房（顔の窓の縁）、耳の前の房、額の横のとげ ---
    L((0.0, -0.118, 1.432), (-0.006, -0.131, 1.318), 0.076, 0.012, lift=0.006, bone='hair.front', sway=0.2, wpos=0.20, root_w=0.95)
    for s in (1, -1):
        A = lambda a: a if s > 0 else 360 - a
        sb = 'hair.side.L' if s > 0 else 'hair.side.R'
        L(('a', A(44), 1.458, 0.008), (s * 0.110, -0.084, 1.256), 0.066, 0.012, lift=0.010, bone='hair.front', sway=0.15, wpos=0.30, root_w=0.9)
        L(('a', A(60), 1.452, 0.008), (s * 0.138, -0.052, 1.286), 0.072, 0.014, lift=0.018, bone=sb, sway=0.3, wpos=0.42, root_w=0.65)
        L(('a', A(44), 1.490, 0.006), (s * 0.172, -0.100, 1.402), 0.086, 0.018, lift=0.028, bone=sb, sway=0.4, wpos=0.46, root_w=0.6)
        L(('a', A(84), strap_z(84) + 0.004, 0.006), (s * 0.188, 0.012, 1.352), 0.090, 0.018, lift=0.026, bone=sb, sway=0.45, wpos=0.46, root_w=0.6)
        L(('a', A(24), 1.489, 0.004), (s * 0.098, -0.128, 1.516), 0.070, 0.016, lift=0.016, bone='hair.front', sway=0.3, wpos=0.46, root_w=0.7)


# ---------- ゴーグル ----------

def ring_frame(m, outer, inner, o, ex, ey, ez, depth, recess, back, bone, col_frame, col_lens, bevel=0.006):
    """枠（外の輪と内の輪）とレンズ。前の面は ez の向き"""
    n = len(outer)
    P = lambda p, h: o + ex * p[0] + ey * p[1] + ez * h
    ob = [P(p, -back) for p in outer]
    of = [P(p, depth - bevel) for p in outer]
    oi = [P(p, depth) for p in geo.inset_poly(outer, bevel)]
    inn = [P(p, depth) for p in inner]
    inr = [P(p, depth - recess) for p in inner]
    verts = ob + of + oi + inn + inr
    faces = []
    for k in range(4):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            c, d = (k + 1) * n + (j + 1) % n, (k + 1) * n + j
            faces.append([a, b, c, d])
    m.add(verts, faces, col_frame, bone, smooth=False, closed=False, name='goggle_frame')
    lens = [P(p, depth - recess + 0.0005) for p in inner]
    # レンズ：真ん中を少し前へ出した 2 面の折れ（絵の斜めの折れ目）
    cx = sum(p[0] for p in inner) / n
    cy = sum(p[1] for p in inner) / n
    cen = P((cx, cy), depth - recess + 0.004)
    lv = lens + [cen]
    lf = [[j, (j + 1) % n, n] for j in range(n)]
    nrm = np.cross(lv[1] - lv[0], lv[2] - lv[0])
    if np.dot(nrm, ez) < 0:
        lf = [f[::-1] for f in lf]
    m.add(lv, lf, col_lens, bone, smooth=False, closed=False, name='goggle_lens', flip=False)
    # 向きを確かめる（開いた殻の決まりは重心から外。枠は前を向けばよい）


def build_goggles(m):
    bone = 'head'
    for side in (1, -1):
        yaw, pitch = math.radians(19) * side, math.radians(20)
        ez = norm(V(math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch)))      # レンズの前
        ex = norm(V(math.cos(yaw), math.sin(yaw), 0))                     # 本人の左へ
        ey = norm(np.cross(ez, ex))
        if ey[2] < 0:
            ey = -ey
        o = V(side * 0.064, -0.104, 1.442)
        # 絵の輪郭（本人の右のレンズ。鼻の側 = +x が高い六角）。cm → m
        pts = [(-5.2, 0.5), (-4.7, 3.0), (4.3, 5.2), (5.3, 4.5), (5.1, -1.0), (2.8, -3.8), (-4.0, -5.5), (-5.2, -3.5)]
        outer = [(p[0] * 0.0102, p[1] * 0.0100) for p in pts]
        if side > 0:
            outer = [(-p[0], p[1]) for p in outer]
        area = sum(outer[i][0] * outer[(i + 1) % 8][1] - outer[(i + 1) % 8][0] * outer[i][1] for i in range(8))
        if area < 0:
            outer = outer[::-1]
        gc = (sum(p[0] for p in outer) / 8, sum(p[1] for p in outer) / 8)
        inner = [(gc[0] + (p[0] - gc[0]) * 0.70, gc[1] + (p[1] - gc[1]) * 0.66) for p in outer]
        ring_frame(m, outer, inner, o, ex, ey, ez, 0.040, 0.008, 0.03, bone, 'graphite', 'amber', bevel=0.007)
        # こめかみへ回る横の部品（小さい琥珀の窓つき）
        c = V(side * 0.127, -0.060, 1.434)
        bx = norm(V(side * 0.93, -0.36, 0.05))
        by = norm(V(side * 0.36, 0.93, 0.0))
        bz = norm(np.cross(bx, by))
        if bz[2] < 0:
            bz = -bz
        v, f, _ = geo.box(c, (0.024, 0.060, 0.070), bx, by, bz, chamfer=0.009)
        m.add(v, f, 'graphite', bone, smooth=False, name='goggle_side')
        v, f, _ = geo.box(c + bx * 0.0125, (0.004, 0.030, 0.036), bx, by, bz, chamfer=0.0015)
        m.add(v, f, 'amber', bone, smooth=False, name='goggle_side_lens')
    # 鼻の上の橋
    by = norm(V(0, 1, -0.36))
    v, f, _ = geo.box(V(0, -0.126, 1.452), (0.034, 0.026, 0.056), V(1, 0, 0), by, norm(np.cross(V(1, 0, 0), by)), chamfer=0.006)
    m.add(v, f, 'graphite', bone, smooth=False, name='goggle_bridge')
    # ヒモ：こめかみから後ろへ下がりながら一周
    path = []
    for a in range(66, 295, 12):
        p = cap_pt(a, strap_z(a))
        path.append((p + radial(p) * 0.012,))
    from .parts_gear import band
    v, f, _ = band(path, 0.032, 0.009, radial)
    m.add(v, f, 'graphite', bone, smooth=False, name='goggle_strap')


def build(groups):
    m = groups['Haru']
    build_head(m)
    build_hair(m)
    build_goggles(m)
    return {}
