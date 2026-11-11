"""haru_f：体と作業着（胴・首・上着・襟・袖・腕・ベルト・ポーチ・ズボン・すね・足首のカフ・靴）。
寸法は絵の格子（measure.py）から。面は絵と同じく大きな平らな面で組む（肌だけなめらか）。"""
from __future__ import annotations

import math

import numpy as np

from . import geo
from .geo import V, norm, lerp, smoothstep
from .rigw import torso_w, arm_w, leg_w
from .spec import jp


def bring(z, hw, yf, yb, n=12, exp=2.4, phase=0.0):
    """水平の胴の輪：正面（-y）から、上から見て反時計回り"""
    yc, hd = (yf + yb) / 2, (yb - yf) / 2
    e = 2.0 / exp
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + phase) / n
        s, c = math.sin(a), math.cos(a)
        pts.append(V(hw * math.copysign(abs(s) ** e, s), yc - hd * math.copysign(abs(c) ** e, c), z))
    return pts


# 胴の輪（z, 半幅, 前の y, 後ろの y）
TORSO = [(0.80, 0.110, -0.086, 0.078), (0.87, 0.110, -0.086, 0.078), (0.93, 0.113, -0.087, 0.081),
         (1.00, 0.121, -0.085, 0.085), (1.07, 0.130, -0.077, 0.087), (1.112, 0.112, -0.064, 0.080),
         (1.132, 0.078, -0.050, 0.068)]


def torso_at(z):
    """胴の輪の値を高さで補間（上着・ベルトが沿う）"""
    T = TORSO
    if z <= T[0][0]:
        return T[0][1:]
    for a, b in zip(T, T[1:]):
        if z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return tuple(a[k] + (b[k] - a[k]) * t for k in (1, 2, 3))
    return T[-1][1:]


def build_torso(m):
    n = 12
    rings = [bring(z, hw, yf, yb, n) for (z, hw, yf, yb) in TORSO]
    v, f, kinds = geo.loft(rings, True, True)
    cols = []
    k = 0
    for i in range(len(rings) - 1):
        for j in range(n):
            front = j in (0, n - 1)
            cols.append('ivory' if (front and TORSO[i + 1][0] > 0.86) else 'brick')
    cols += ['brick', 'ivory']
    m.add(v, f, cols, torso_w, smooth=False, name='torso')
    # 首（肌）：鎖骨のあたりから頭の中まで
    NECK = [(1.108, 0.066, -0.044, 0.062), (1.130, 0.050, -0.037, 0.054), (1.152, 0.040, -0.031, 0.049),
            (1.20, 0.037, -0.029, 0.046), (1.25, 0.037, -0.029, 0.046)]
    rings = [bring(z, hw, yf, yb, 12, 2.0) for (z, hw, yf, yb) in NECK]
    v, f, _ = geo.loft(rings, True, True)
    m.add(v, f, 'skin', torso_w, smooth=True, name='neck')


# 上着の輪（z, 半幅, 前, 後ろ, 前の開きの半幅）
JACKET = [(0.898, 0.132, -0.102, 0.097, 0.050), (0.95, 0.131, -0.101, 0.097, 0.050), (1.02, 0.139, -0.099, 0.100, 0.050),
          (1.08, 0.156, -0.092, 0.102, 0.052), (1.124, 0.162, -0.078, 0.097, 0.062), (1.142, 0.134, -0.064, 0.090, 0.072)]


def jacket_ring(z, hw, yf, yb, edge, exp=2.6):
    yc, hd = (yf + yb) / 2, (yb - yf) / 2
    e = 2.0 / exp
    a0 = math.asin(min(1.0, (edge / hw) ** (1 / e)))
    angs = [a0] + [math.radians(d) for d in (32, 60, 90, 120, 150, 180, 210, 240, 270, 300, 328)] + [2 * math.pi - a0]
    pts = []
    for a in angs:
        s, c = math.sin(a), math.cos(a)
        pts.append(V(hw * math.copysign(abs(s) ** e, s), yc - hd * math.copysign(abs(c) ** e, c), z))
    return pts


def build_jacket(m):
    grid = [jacket_ring(*r) for r in JACKET]

    def inward(p):
        d = V(-p[0], -(p[1] - 0.004), 0)
        return norm(d)
    v, f, kinds = geo.grid_shell(grid, 0.010, inward)
    cols = ['brick_dk' if k == 'inner' else 'brick' for k in kinds]
    m.add(v, f, cols, torso_w, smooth=False, name='jacket')
    # 背中の中心の縫い目・すその折り返しは形にしない（絵でも線だけ）


def build_collar(m):
    """フードのような厚い襟：首のまわりを後ろで立ち、前の鎖骨へ開く"""
    # 角度（正面 0、左 90、後ろ 180）ごとの断面：内の下・内の上・外の上・外の下（半径は首の軸 (0, 0.012) から）
    # (角度, r内下, z内下, r内上, z内上, r外上, z外上, r外下, z外下)
    K = [(20, 0.052, 1.085, 0.058, 1.098, 0.074, 1.092, 0.080, 1.076),
         (38, 0.050, 1.112, 0.072, 1.136, 0.096, 1.122, 0.108, 1.100),
         (60, 0.048, 1.130, 0.090, 1.166, 0.122, 1.146, 0.136, 1.118),
         (90, 0.048, 1.142, 0.104, 1.190, 0.132, 1.166, 0.146, 1.128),
         (120, 0.048, 1.150, 0.110, 1.206, 0.132, 1.180, 0.142, 1.130),
         (150, 0.050, 1.156, 0.098, 1.210, 0.118, 1.186, 0.126, 1.128),
         (180, 0.050, 1.158, 0.090, 1.210, 0.108, 1.188, 0.114, 1.128)]
    full = K + [(360 - k[0],) + k[1:] for k in K[-2::-1]]
    ax = V(0, 0.010, 0)
    rows = [[], [], [], []]
    for k in full:
        a = math.radians(k[0])
        d = V(math.sin(a), -math.cos(a), 0)
        # 前へ行くほど首の軸を前へ（襟の口が鎖骨へ下りる）
        for r_i in range(4):
            r, z = k[1 + 2 * r_i], k[2 + 2 * r_i]
            sc = V(1.0, 0.86 if d[1] > 0 else 1.0, 1.0)     # 後ろは少し浅く
            rows[r_i].append(ax + d * r * sc + V(0, 0, z))
    # 行：内の下 → 内の上 → 外の上 → 外の下 → 内の下（閉じた帯）
    rings = [[rows[r][c] for r in (0, 1, 2, 3)] for c in range(len(full))]
    v, f, kinds = geo.loft(rings, True, True)
    cols = []
    for i in range(len(rings) - 1):
        cols += ['brick_dk', 'brick', 'brick', 'brick_dk']
    cols += ['brick', 'brick']
    m.add(v, f, cols, torso_w, smooth=False, name='collar')


def arm_axis(side):
    S, E, W, T = jp('upper_arm', side), jp('forearm', side), jp('hand', side), jp('hand_end', side)
    return S, E, W, T


def build_sleeves(m):
    for side in (1, -1):
        S, E, W, T = arm_axis(side)
        a = norm(E - S)
        up = V(0, 0, 1)
        # 肩の上を少し持ち上げた円すいの袖。折り返しの段と暗い袖口
        P = lambda s, lift=0.0: S + a * s + up * lift
        path = [(P(-0.045, 0.004), 0.030, 0.046), (P(0.000, 0.004), 0.046, 0.058), (P(0.055, 0.002), 0.058, 0.066),
                (P(0.112), 0.063, 0.067), (P(0.116), 0.068, 0.071), (P(0.168), 0.066, 0.069)]
        v, f, kinds = geo.tube(path, n=8, hint=(0, -1, 0), phase=0.5)
        w = lambda p, side=side: arm_w(p, side, shoulder_mix=0.35)
        cols = ['brick_dk' if k == 'cap1' else 'brick' for k in kinds]
        m.add(v, f, cols, w, smooth=False, name='sleeve')
        # 暗い袖口（中の服の端）
        path = [(P(0.156), 0.050, 0.052), (P(0.196), 0.049, 0.051)]
        v, f, kinds = geo.tube(path, n=8, hint=(0, -1, 0), phase=0.5)
        m.add(v, f, 'graphite', w, smooth=False, name='sleeve_cuff')


def build_arms(m):
    for side in (1, -1):
        S, E, W, T = arm_axis(side)
        a1, a2 = norm(E - S), norm(W - E)
        w = lambda p, side=side: arm_w(p, side)
        path = [(S + a1 * 0.10, 0.036, 0.037), (S + a1 * 0.17, 0.035, 0.036), (E, 0.0335, 0.0345),
                (E + a2 * 0.05, 0.036, 0.036), (E + a2 * 0.12, 0.033, 0.033), (W - a2 * 0.02, 0.0275, 0.029), (W + a2 * 0.01, 0.027, 0.028)]
        v, f, _ = geo.tube(path, n=10, hint=(0, -1, 0))
        m.add(v, f, 'skin', w, smooth=True, name='arm')
        # 手袋のカフ（手首の暗い帯）
        path = [(W - a2 * 0.048, 0.036, 0.037), (W - a2 * 0.044, 0.039, 0.040), (W - a2 * 0.006, 0.037, 0.038), (W + a2 * 0.004, 0.033, 0.034)]
        v, f, _ = geo.tube(path, n=8, hint=(0, -1, 0), phase=0.5)
        m.add(v, f, 'graphite', 'forearm' + ('.L' if side > 0 else '.R'), smooth=False, name='glove_cuff')


def build_belt(m):
    z0, z1 = 0.822, 0.872
    rings = []
    for z, off in ((z0, 0.004), (z0 + 0.004, 0.011), (z1 - 0.004, 0.011), (z1, 0.004)):
        hw, yf, yb = torso_at(0.85)
        rings.append(bring(z, hw + 0.006 + off, yf - 0.006 - off, yb + 0.006 + off, 12, 2.6))
    v, f, _ = geo.loft(rings, True, True)
    m.add(v, f, 'graphite', 'hips', smooth=False, name='belt')
    # バックル：真鍮の四角い枠（中は帯）
    yb = -0.086 - 0.017
    c = V(0.004, yb, 0.846)
    ex, ez, ey = V(1, 0, 0), V(0, 0, 1), V(0, -1, 0)
    outer = [(-0.036, -0.033), (0.036, -0.033), (0.036, 0.033), (-0.036, 0.033)]
    for (x0, x1, y0, y1) in ((-0.036, 0.036, 0.020, 0.033), (-0.036, 0.036, -0.033, -0.020), (-0.036, -0.022, -0.020, 0.020), (0.022, 0.036, -0.020, 0.020)):
        poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        v, f, _ = geo.prism(poly, c, ex, ez, ey, 0.012, back=0.006)
        m.add(v, f, 'brass', 'hips', smooth=False, name='buckle')
    # ベルト通し（左右の前）
    for sx in (-0.078, 0.082):
        v, f, _ = geo.box(V(sx, -0.092, 0.847), (0.016, 0.02, 0.060), chamfer=0.003)
        m.add(v, f, 'graphite_dk', 'hips', smooth=False, name='belt_loop')


def build_pouches(m):
    # 右の腰（本人の右、横）：前後 9.5 × 厚み 5 × 高さ 11
    def pouch(center, size, ex, ey, bone, flap_h):
        ez = V(0, 0, 1)
        v, f, _ = geo.box(center, size, ex, ey, ez, chamfer=0.008)
        m.add(v, f, 'graphite', bone, smooth=False, name='pouch')
        # ふた：上の 4 割を覆う、少し大きい板
        fc = center + ez * (size[2] / 2 - flap_h / 2 + 0.004) + ey * 0.004
        v, f, _ = geo.box(fc, (size[0] + 0.008, size[1] + 0.004, flap_h), ex, ey, ez, chamfer=0.006)
        m.add(v, f, 'graphite_dk', bone, smooth=False, name='pouch_flap')
    # 右：外向き（-x）に厚み
    pouch(V(-0.142, 0.016, 0.768), (0.092, 0.050, 0.108), V(0, -1, 0), V(-1, 0, 0), 'pouch.R', 0.044)
    # 左：前寄りの斜め（+x と -y の間）
    ey = norm(V(0.80, -0.60, 0))
    ex = V(-ey[1], ey[0], 0)
    pouch(V(0.118, -0.058, 0.795), (0.066, 0.046, 0.094), ex, ey, 'pouch.L', 0.038)


# ズボンの脚（左）：(z, 中心 x, 中心 y, rx, ry)
LEG = [(0.80, 0.060, 0.000, 0.066, 0.086), (0.74, 0.078, 0.002, 0.082, 0.094), (0.68, 0.100, 0.005, 0.094, 0.098),
       (0.60, 0.112, 0.012, 0.097, 0.098), (0.52, 0.124, 0.022, 0.099, 0.100), (0.487, 0.128, 0.026, 0.098, 0.099),
       (0.458, 0.126, 0.028, 0.084, 0.086)]


def build_trousers(m):
    n = 10
    # 腰（ベルトの下〜股）
    rings = [bring(z, hw, yf, yb, 12, 2.6) for (z, hw, yf, yb) in
             ((0.700, 0.150, -0.088, 0.096), (0.760, 0.146, -0.094, 0.096), (0.815, 0.128, -0.094, 0.090), (0.885, 0.116, -0.091, 0.084))]
    v, f, _ = geo.loft(rings, True, True)
    m.add(v, f, 'brick', 'hips', smooth=False, name='pelvis')
    for side in (1, -1):
        w = lambda p, side=side: leg_w(p, side)
        rings = []
        for (z, cx, cy, rx, ry) in LEG:
            rings.append([V(side * cx + q[0], cy + q[1], z) for q in geo.sring(n, rx, ry, 2.5, 0.5 if side > 0 else 0.5)])
        # すその内へ折り返す底
        z, cx, cy, rx, ry = LEG[-1]
        rings.append([V(side * cx + q[0], cy + q[1], z + 0.012) for q in geo.sring(n, rx * 0.74, ry * 0.74, 2.5, 0.5)])
        rings = rings[::-1]
        v, f, kinds = geo.loft(rings, True, True)
        cols = []
        for i in range(len(rings) - 1):
            cols += ['brick_dk' if i == 0 else 'brick'] * n
        cols += ['graphite_dk', 'brick']
        m.add(v, f, cols, w, smooth=False, name='trouser_leg')


def leg_frame(side):
    K, A = jp('shin', side), jp('foot', side)
    return K, A, norm(A - K)


def build_shins(m):
    n = 8
    for side in (1, -1):
        K, A, a = leg_frame(side)
        w = lambda p, side=side: leg_w(p, side)
        P = lambda s: K + a * s
        path = [(P(-0.11), 0.056, 0.062), (P(-0.02), 0.057, 0.064), (P(0.06), 0.054, 0.066, None), (P(0.13), 0.049, 0.060),
                (P(0.205), 0.043, 0.051), (P(0.25), 0.043, 0.050)]
        path = [(c + V(0, 0.006, 0), rx, ry) for (c, rx, ry, *_) in path]
        v, f, _ = geo.tube(path, n=n, hint=(0, -1, 0), phase=0.5)
        m.add(v, f, 'boot', w, smooth=False, name='shin')
        # 足首のカフ（れんが色の太い輪）と、その重なりの端
        sfx = '.L' if side > 0 else '.R'
        c = V(A[0], A[1] + 0.004, 0)
        rings = []
        for z, k in ((0.148, 0.90), (0.156, 1.0), (0.198, 1.0), (0.208, 0.88)):
            rings.append([V(c[0] + q[0], c[1] + q[1], z) for q in geo.sring(n, 0.062 * k, 0.074 * k, 2.6, 0.5)])
        v, f, _ = geo.loft(rings, True, True)
        m.add(v, f, 'brick', 'shin' + sfx, smooth=False, name='ankle_cuff')
        v, f, _ = geo.box(V(c[0] - side * 0.012, c[1] - 0.070, 0.178), (0.058, 0.014, 0.050), chamfer=0.004)
        m.add(v, f, 'brick', 'shin' + sfx, smooth=False, name='ankle_cuff_tab')


def foot_frame(side):
    A = jp('foot', side)
    ang = math.radians(13.0) * side
    fwd = V(math.sin(ang), -math.cos(ang), 0)
    sd = V(math.cos(ang), math.sin(ang), 0)      # 本人の左へ
    o = V(A[0], A[1], 0)
    return o, sd, fwd


def profile_extrude(profile, o, sd, fwd, half, inset=0.010, lin=0.010):
    """横から見た輪郭（前後 l, 高さ z）を左右へ押し出す。左右の端は輪郭を少し縮めて角を落とす"""
    up = V(0, 0, 1)
    cl = sum(p[0] for p in profile) / len(profile)
    cz = sum(p[1] for p in profile) / len(profile)
    small = geo.inset_poly(profile, lin)
    rings = []
    for s, poly in ((-half, small), (-half + inset, profile), (half - inset, profile), (half, small)):
        rings.append([o + sd * s + fwd * p[0] + up * p[1] for p in poly])
    return geo.loft(rings, True, True)


def build_boots(m):
    for side in (1, -1):
        sfx = '.L' if side > 0 else '.R'
        o, sd, fwd = foot_frame(side)
        bone = 'foot' + sfx
        # 靴底：かかとが厚く、土踏まずに浅い切り欠き
        sole = [(-0.094, 0.004), (-0.090, 0.0), (-0.022, 0.0), (-0.014, 0.015), (0.006, 0.015), (0.014, 0.0), (0.194, 0.0),
                (0.202, 0.010), (0.198, 0.034), (0.030, 0.036), (-0.020, 0.060), (-0.094, 0.060)]
        v, f, _ = profile_extrude(sole, o, sd, fwd, 0.066, inset=0.010, lin=0.006)
        m.add(v, f, 'graphite', bone, smooth=False, name='sole')
        # 甲（茶）：かかと〜足首
        up = V(0, 0, 1)
        rings = []
        for z, l0, l1, hw in ((0.034, -0.084, 0.150, 0.058), (0.062, -0.086, 0.150, 0.059), (0.105, -0.082, 0.085, 0.056), (0.152, -0.074, 0.060, 0.053)):
            cl, hl = (l0 + l1) / 2, (l1 - l0) / 2
            rings.append([o + sd * q[0] + fwd * (cl + q[1]) + up * z for q in geo.sring(8, hw, hl, 3.2, 0.5)])
        v, f, _ = geo.loft(rings, True, True)
        m.add(v, f, 'boot', bone, smooth=False, name='boot_upper')
        # 爪先（生成り）
        toe = [(0.072, 0.036), (0.193, 0.036), (0.197, 0.066), (0.184, 0.092), (0.150, 0.103), (0.088, 0.110), (0.072, 0.104)]
        v, f, _ = profile_extrude(toe, o, sd, fwd, 0.066, inset=0.014, lin=0.010)
        m.add(v, f, 'ivory', bone, smooth=False, name='toe_cap')
        # 甲の暗い帯（ベロ）
        strap = [(0.004, 0.150), (0.052, 0.110), (0.064, 0.118), (0.016, 0.160)]
        v, f, _ = profile_extrude(strap, o, sd, fwd, 0.030, inset=0.004, lin=0.002)
        m.add(v, f, 'graphite', bone, smooth=False, name='boot_strap')


def build_body(m):
    build_torso(m)
    build_jacket(m)
    build_collar(m)
    build_sleeves(m)
    build_arms(m)
    build_belt(m)
    build_pouches(m)
    build_trousers(m)
    build_shins(m)
    build_boots(m)
