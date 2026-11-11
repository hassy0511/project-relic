"""haru_f：外装フレーム（Frame_core・Frame_arm・Frame_legs）、手、スパーク、光刃。
フレームは体の上に重ねる別の物体（隠すと作業着だけになる）。"""
from __future__ import annotations

import math

import numpy as np

from . import geo
from .geo import V, norm, lerp
from .rigw import torso_w, arm_w, leg_w
from .spec import jp
from .parts_body import JACKET, leg_frame, foot_frame, arm_axis


def jacket_y(x, z, front=True, exp=2.6):
    """上着の面の y（x・z から）"""
    R = JACKET
    if z <= R[0][0]:
        r = R[0]
    elif z >= R[-1][0]:
        r = R[-1]
    else:
        for a, b in zip(R, R[1:]):
            if z <= b[0]:
                t = (z - a[0]) / (b[0] - a[0])
                r = tuple(a[k] + (b[k] - a[k]) * t for k in range(5))
                break
    _, hw, yf, yb, _ = r
    yc, hd = (yf + yb) / 2, (yb - yf) / 2
    q = min(0.999, abs(x) / hw)
    c = (1 - q ** exp) ** (1 / exp)
    return yc - hd * c if front else yc + hd * c


def band(path, width, thick, normal_of, name=None):
    """面に沿う帯：path の各点で、外向き normal_of(p) と進む向きから四角い断面を作る"""
    rings = []
    for i, item in enumerate(path):
        p = np.asarray(item[0], dtype=float)
        w = item[1] if len(item) > 1 else width
        t = item[2] if len(item) > 2 else thick
        a = np.asarray(path[max(0, i - 1)][0], dtype=float)
        b = np.asarray(path[min(len(path) - 1, i + 1)][0], dtype=float)
        d = norm(b - a)
        nrm = np.asarray(normal_of(p), dtype=float)
        nrm = norm(nrm - d * np.dot(nrm, d))
        s = np.cross(d, nrm)
        rings.append([p - s * w / 2 - nrm * 0.004, p + s * w / 2 - nrm * 0.004, p + s * w / 2 + nrm * t, p - s * w / 2 + nrm * t])
    return geo.loft(rings, True, True)


# ---------- Frame_core：肩ひも・背中の板・右肩の板 ----------

def build_core(m):
    def out(p):
        return norm(V(p[0] * 0.6, p[1] - 0.004, 0.0) + V(0, 0, 0.9 if p[2] > 1.135 else 0.0))
    for side in (1, -1):
        X = lambda x: side * x
        F = lambda x, z, off=0.003: V(X(x), jacket_y(x, z, True) - off, z)
        B = lambda x, z, off=0.003: V(X(x), jacket_y(x, z, False) + off, z)
        path = [(F(0.132, 0.965), 0.014, 0.008), (F(0.127, 1.000), 0.022, 0.009), (F(0.118, 1.035), 0.030, 0.010),
                (F(0.112, 1.046), 0.044, 0.014), (F(0.110, 1.085), 0.044, 0.014), (F(0.108, 1.118), 0.044, 0.014),
                (V(X(0.106), -0.040, 1.152), 0.040, 0.010), (V(X(0.104), 0.016, 1.166), 0.040, 0.010), (V(X(0.098), 0.062, 1.156), 0.040, 0.010),
                (B(0.086, 1.128), 0.040, 0.013), (B(0.080, 1.085), 0.040, 0.013), (B(0.080, 1.040), 0.040, 0.013), (B(0.080, 0.985), 0.036, 0.011)]
        v, f, _ = band(path, 0.04, 0.012, out)
        m.add(v, f, 'graphite', torso_w, smooth=False, name='strap')
        # 留め具の段（前の当て・後ろの当ての切れ目）
        for (c, sz) in ((F(0.111, 1.066, 0.014), (0.050, 0.010, 0.012)), (B(0.081, 1.062, 0.013), (0.046, 0.010, 0.012)), (B(0.083, 1.108, 0.013), (0.046, 0.010, 0.012))):
            v, f, _ = geo.box(c, sz, chamfer=0.002)
            m.add(v, f, 'graphite_dk', torso_w, smooth=False, name='strap_clip')
    # 背中の板（生成り、角を落とした四角）
    c = V(0, jacket_y(0, 1.072, False), 1.072)
    poly = [(-0.040, -0.036), (0.040, -0.036), (0.052, -0.026), (0.052, 0.026), (0.040, 0.036), (-0.040, 0.036), (-0.052, 0.026), (-0.052, -0.026)]
    v, f, _ = geo.prism(poly, c, V(-1, 0, 0), V(0, 0, 1), V(0, 1, 0), 0.016, bevel=0.005, back=0.01)
    m.add(v, f, 'ivory', 'chest', smooth=False, name='back_plate')
    # 右肩の板：肩の上に 42 度で載る厚い板
    C = V(-0.184, 0.036, 1.103)
    es, ey, n = norm(V(-0.76, 0, -0.65)), V(0, 1, 0), norm(V(-0.65, 0, 0.76))
    poly = [(-0.040, -0.084), (0.036, -0.084), (0.058, -0.054), (0.058, 0.050), (0.040, 0.082), (-0.042, 0.082), (-0.062, 0.050), (-0.062, -0.054)]
    wplate = {'shoulder.R': 0.8, 'upper_arm.R': 0.2}
    v, f, _ = geo.prism(poly, C, ey, es, n, 0.028, bevel=0.011, back=0.030)
    m.add(v, f, 'ivory', wplate, smooth=False, name='shoulder_plate')
    # 板を支える上腕の暗い帯（袖の上）
    S, E, W, T = arm_axis(-1)
    a = norm(E - S)
    path = [(S + a * 0.070, 0.073, 0.076), (S + a * 0.098, 0.071, 0.074)]
    v, f, _ = geo.tube(path, n=8, hint=(0, -1, 0), phase=0.5)
    m.add(v, f, 'graphite', lambda p: arm_w(p, -1, shoulder_mix=0.35), smooth=False, name='plate_band')


# ---------- Frame_arm：左の籠手 ----------

def gauntlet_frame():
    S, E, W, T = arm_axis(1)
    a = norm(W - E)
    o = norm(V(a[2] * -1.0, 0, a[0]))       # 腕の軸に直角・外（+x）で上
    if o[0] < 0:
        o = -o
    y = np.cross(o, a)                        # 前後
    return E, W, a, o, y


def build_gauntlet(m):
    E, W, a, o, y = gauntlet_frame()
    L = float(np.linalg.norm(W - E))
    bone = 'forearm.L'
    P = lambda s: E + a * s
    v, f, _ = geo.tube([(P(0.050), 0.049, 0.050), (P(0.105), 0.049, 0.049), (P(L - 0.040), 0.043, 0.044)], n=8, hint=(0, -1, 0), phase=0.5)
    m.add(v, f, 'ivory', bone, smooth=False, name='gauntlet')
    v, f, _ = geo.tube([(P(0.022), 0.047, 0.048), (P(0.027), 0.055, 0.056), (P(0.060), 0.055, 0.056), (P(0.064), 0.050, 0.051)], n=8, hint=(0, -1, 0), phase=0.5)
    m.add(v, f, 'graphite', bone, smooth=False, name='gauntlet_band')
    v, f, _ = geo.tube([(P(L - 0.052), 0.044, 0.045), (P(L - 0.047), 0.048, 0.049), (P(L - 0.010), 0.045, 0.046), (P(L - 0.004), 0.040, 0.041)], n=8, hint=(0, -1, 0), phase=0.5)
    m.add(v, f, 'graphite', bone, smooth=False, name='gauntlet_band')
    # 外側のレール：真鍮の台と琥珀の射出口
    c = E + V(0, 0, 0)
    yc = 0.0
    rail = [(0.030, -0.016), (0.186, -0.014), (0.192, 0.0), (0.186, 0.014), (0.030, 0.016), (0.024, 0.0)]
    v, f, _ = geo.prism(rail, E + o * 0.042, a, y, o, 0.022, bevel=0.004)
    m.add(v, f, 'brass', bone, smooth=False, name='rail')
    amber = [(0.074, -0.009), (0.178, -0.008), (0.184, 0.0), (0.178, 0.008), (0.074, 0.009), (0.068, 0.0)]
    v, f, _ = geo.prism(amber, E + o * 0.060, a, y, o, 0.011, bevel=0.004)
    m.add(v, f, 'amber', bone, smooth=False, name='emitter')
    return E + a * 0.188 + o * 0.066


def build_blade():
    """光刃：射出口から前腕と平行に 47 cm。板の面は腕の軸と外向きを含む（手の甲の外に立つ）"""
    E, W, a, o, y = gauntlet_frame()
    origin = E + a * 0.186 + o * 0.064
    prof = [(0.0, -0.013), (0.035, -0.019), (0.30, -0.016), (0.42, -0.008), (0.47, 0.004), (0.40, 0.013), (0.25, 0.019), (0.035, 0.021), (0.0, 0.015)]
    small = geo.inset_poly(prof, 0.006)
    rings = []
    for t, poly in ((-0.0045, small), (0.0, prof), (0.0045, small)):
        rings.append([a * p[0] + o * p[1] + y * t for p in poly])
    v, f, _ = geo.loft(rings, True, True)
    world = np.eye(4)
    world[:3, 3] = origin
    return {'verts': v, 'faces': f, 'world': world}


# ---------- Frame_legs：膝当て・蝶番・すね当て・右太ももの板 ----------

LEG_YAW = 9.0      # 膝から下の部品は少し外を向く（絵の正面で内側のすね当てが広く見える）


def build_legs(m):
    for side in (1, -1):
        sfx = '.L' if side > 0 else '.R'
        K, A, a = leg_frame(side)
        w = lambda p, side=side: leg_w(p, side)
        shin = 'shin' + sfx
        Rz = geo.rot_axis(V(0, 0, 1), math.radians(LEG_YAW) * side)
        piv = V(K[0], K[1] + 0.010, 0)
        yaw = lambda vs: [piv + Rz @ (np.asarray(q, dtype=float) - piv) for q in vs]
        # 膝の後ろの暗い当て（膝を回る短い筒）
        P = lambda s: K + a * s + V(0, 0.006, 0)
        v, f, _ = geo.tube([(P(-0.052), 0.060, 0.066), (P(-0.046), 0.064, 0.071), (P(0.046), 0.063, 0.071), (P(0.054), 0.058, 0.067)], n=8, hint=(0, -1, 0), phase=0.5)
        m.add(v, f, 'graphite', w, smooth=False, name='knee_wrap')
        # 膝当て：前へ張り出す厚い八角の板
        c = V(K[0] + side * 0.004, K[1] + 0.004, K[2] - 0.004)
        ex, ez, ey = V(1, 0, 0), V(0, 0, 1), V(0, -1, 0)
        o8 = lambda hw, hh, cx, cz: [(-hw + cx, -hh), (hw - cx, -hh), (hw, -hh + cz), (hw, hh - cz), (hw - cx, hh), (-hw + cx, hh), (-hw, hh - cz), (-hw, -hh + cz)]
        v, f, _ = geo.prism(o8(0.062, 0.072, 0.022, 0.026), c, ex, ez, ey, 0.062, bevel=0.008)
        m.add(yaw(v), f, 'graphite', shin, smooth=False, name='knee_base')
        v, f, _ = geo.prism(o8(0.050, 0.061, 0.020, 0.024), c + V(0, 0, 0.001), ex, ez, ey, 0.086, bevel=0.022)
        m.add(yaw(v), f, 'ivory', shin, smooth=False, name='knee_pad')
        # 蝶番：左右の暗い輪と琥珀の丸
        for s2 in (1, -1):
            hc = V(K[0] + side * 0.004, K[1] + 0.020, K[2])
            d = V(s2, 0, 0)
            v, f, _ = geo.tube([(hc + d * 0.056, 0.038, 0.038), (hc + d * 0.080, 0.038, 0.038), (hc + d * 0.084, 0.033, 0.033)], n=10, hint=(0, 0, 1))
            m.add(yaw(v), f, 'graphite', shin, smooth=False, name='hinge')
            v, f, _ = geo.tube([(hc + d * 0.082, 0.026, 0.026), (hc + d * 0.091, 0.024, 0.024), (hc + d * 0.095, 0.014, 0.014)], n=10, hint=(0, 0, 1))
            m.add(yaw(v), f, 'amber', shin, smooth=False, name='hinge_amber')
            # すね当て：内と外の細長い板（上が広く下が細い六角）
            pd = [(-5.6, 22.6), (-0.2, 22.6), (1.4, 31.5), (-1.4, 36.8), (-4.8, 36.8), (-7.0, 33.2)]
            poly = [(0.021 - q[0] / 100.0, q[1] / 100.0) for q in pd]
            top_x = K[0] + a[0] / abs(a[2]) * (K[2] - 0.36) + s2 * 0.050
            bot_x = K[0] + a[0] / abs(a[2]) * (K[2] - 0.23) + s2 * 0.042
            tilt = (top_x - bot_x) / 0.13
            ez2 = norm(V(tilt, 0, 1))
            ex2 = norm(V(1, 0, -tilt)) * s2
            org = V(bot_x - tilt * 0.23, 0, 0)
            v, f, _ = geo.prism(poly, org, V(0, 1, 0), ez2, ex2, 0.014, bevel=0.004, back=0.008)
            m.add(yaw(v), f, 'ivory', shin, smooth=False, name='shin_plate')
        # 足首の上の暗い細い帯
        c = V(A[0], A[1] + 0.004, 0)
        rings = [[V(c[0] + q[0] - side * 0.002, c[1] + q[1], z) for q in geo.sring(8, r1, r2, 2.6, 0.5)] for z, r1, r2 in ((0.204, 0.050, 0.060), (0.228, 0.049, 0.058))]
        v, f, _ = geo.loft(rings, True, True)
        m.add(v, f, 'graphite', shin, smooth=False, name='ankle_band')
    # 右太ももの板（前・外の斜め）と、ベルトへの支え
    n = norm(V(-0.36, -0.93, 0))
    u = V(-n[1], n[0], 0)              # 前の中心へ向かう水平
    if u[0] < 0:
        u = -u
    c = V(-0.114, 0.010, 0.652) + n * 0.102
    poly = [(-0.064, -0.072), (0.058, -0.100), (0.066, 0.084), (0.044, 0.102), (-0.058, 0.102), (-0.070, 0.078)]
    wt = {'thigh.R': 0.7, 'hips': 0.3}
    v, f, _ = geo.prism(poly, c, u, V(0, 0, 1), n, 0.017, bevel=0.006, back=0.006)
    m.add(v, f, 'ivory', wt, smooth=False, name='thigh_plate')
    v, f, _ = geo.box(c + V(0, 0, 0.125) - n * 0.004 - u * 0.012, (0.034, 0.012, 0.070), u, n, V(0, 0, 1), chamfer=0.003)
    m.add(v, f, 'graphite', {'hips': 0.7, 'thigh.R': 0.3}, smooth=False, name='thigh_plate_strap')


# ---------- 手 ----------

def finger(m, pts, r, cols_seg, bone, n=6, hint=(0, 0, 1), tip=0.55, name='finger'):
    """節の点を通る指。cols_seg：節ごとの色。先は細く閉じる"""
    path = []
    for i, p in enumerate(pts):
        k = 1.0 if i < len(pts) - 1 else tip
        path.append((p, r * k, r * k))
    v, f, kinds = geo.tube(path, n=n, hint=hint)
    cols = []
    for i in range(len(pts) - 1):
        cols += [cols_seg[i]] * n
    cols += [cols_seg[0], cols_seg[-1]]
    m.add(v, f, cols, bone, smooth=[c == 'skin' for c in cols], name=name)


def build_left_hand(m):
    S, E, W, T = arm_axis(1)
    h = norm(T - W)
    p0 = norm(V(-h[2] * -1.0, 0, -h[0]))        # 腕の軸に直角・内（体の側）
    if p0[0] > 0:
        p0 = -p0
    back = V(0, 1, 0)
    ang = math.radians(35)
    pn = norm(math.cos(ang) * p0 + math.sin(ang) * back)       # 掌の向き
    pn = norm(pn - h * np.dot(pn, h))
    wd = norm(np.cross(pn, h))                                    # 親指の側
    if wd[1] > 0:
        wd = -wd
    cb = -pn                                                      # 手の甲の向き
    bone = 'hand.L'
    HS = 1.10
    H = lambda a, b, c=0.0: W + (h * a + wd * b + cb * c) * HS
    rings = []
    for a, hb, hc in ((-0.004, 0.030, 0.019), (0.030, 0.041, 0.018), (0.070, 0.044, 0.016), (0.090, 0.042, 0.013)):
        rings.append([H(a, q[0], q[1]) for q in geo.sring(8, hb, hc, 3.0, 0.5)])
    v, f, _ = geo.loft(rings, True, True)
    m.add(v, f, 'graphite', bone, smooth=False, name='palm')
    for b, ln, r, sp in ((0.031, 0.068, 0.0100, 0.10), (0.011, 0.076, 0.0102, 0.02), (-0.010, 0.070, 0.0098, -0.06), (-0.030, 0.056, 0.0090, -0.16)):
        d = norm(h + wd * sp)
        base = H(0.084, b)
        ln, r = ln * HS, r * HS
        pts = [base, base + d * ln * 0.38 - pn * 0.000, base + d * ln * 0.70 + pn * 0.004, base + d * ln + pn * 0.012]
        finger(m, [pts[0], pts[1]], r + 0.0016, ['graphite'], bone, tip=1.0)
        finger(m, [pts[0] + d * ln * 0.30, pts[2], pts[3]], r, ['skin', 'skin'], bone)
    # 親指
    d = norm(h * 0.62 + wd * 0.74 + pn * 0.28)
    base = H(0.026, 0.036, -0.004)
    finger(m, [base, base + d * 0.037], 0.0140, ['graphite'], bone, tip=1.0)
    finger(m, [base + d * 0.029, base + d * 0.055, base + d * 0.072 + h * 0.004], 0.0123, ['skin', 'skin'], bone)


def gun_frame():
    """右手の銃の座標（ゲームの PlayerView.hand_gun_frame と同じ式）：原点＝握りの中心、X＝銃身、Y＝掌が向く側、Z＝上"""
    S, E, W, T = arm_axis(-1)
    gx = norm(T - W)
    right = V(1, 0, 0)                     # Godot の +X ＝ 本人の左
    gy = norm(right - gx * gx[0])
    gz = np.cross(gx, gy)
    wrist_in_gun = V(-0.062, -0.040, -0.010)
    R = np.stack([gx, gy, gz], axis=1)
    o = W - R @ wrist_in_gun
    return o, R


def build_right_hand_and_gun(m):
    o, R = gun_frame()
    G = lambda x, y, z: o + R @ (V(x, y, z) / 100.0)      # cm → 世界
    gx, gy, gz = R[:, 0], R[:, 1], R[:, 2]
    bone = 'hand.R'
    pieces = []

    def gbox(x0, x1, y0, y1, z0, z1, col, ch=0.4, name='gun'):
        c = G((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        v, f, _ = geo.box(c, ((x1 - x0) / 100, (y1 - y0) / 100, (z1 - z0) / 100), gx, gy, gz, chamfer=ch / 100)
        m.add(v, f, col, bone, smooth=False, name=name)

    def gprism(poly_xz, y0, y1, col, bevel=0.3, name='gun'):
        """横から見た輪郭（X, Z）を Y の厚みで。両側を面取り"""
        small = geo.inset_poly(poly_xz, bevel)
        rings = []
        for yy, poly in ((y0, small), (y0 + bevel, poly_xz), (y1 - bevel, poly_xz), (y1, small)):
            rings.append([G(p[0], yy, p[1]) for p in poly])
        v, f, _ = geo.loft(rings, True, True)
        m.add(v, f, col, bone, smooth=False, name=name)

    # --- スパーク（絵 spark_gun_side.png：全長 30 cm、握りの中心が原点） ---
    gprism([(7.0, 5.6), (21.4, 5.6), (21.4, 12.6), (8.2, 12.6), (7.0, 11.4)], -2.5, 2.5, 'gun', 0.5)                 # 銃身の箱
    gprism([(21.0, 5.2), (24.6, 5.2), (25.4, 6.0), (25.4, 12.2), (24.6, 13.0), (21.0, 13.0)], -2.8, 2.8, 'gun', 0.6)   # 銃口の枠
    gbox(24.9, 25.5, -1.3, 1.3, 7.9, 10.5, 'graphite_dk', 0.3)                                                          # 銃口の穴
    gprism([(-4.6, 6.0), (-3.4, 4.9), (8.4, 4.9), (9.6, 6.4), (9.6, 12.6), (8.0, 13.9), (0.2, 13.9), (-1.0, 13.0), (-4.6, 13.0)], -2.9, 2.9, 'gun', 0.6)  # 後ろの本体
    gprism([(-1.0, 13.4), (0.4, 14.4), (6.4, 14.4), (7.6, 13.4)], -1.9, 1.9, 'gun', 0.3)                                # 上の照準の台
    gbox(-4.95, -1.2, -2.2, 2.2, 7.4, 11.4, 'ivory', 0.4)                                                              # 後ろの生成りの板
    for sy in (-1, 1):
        gbox(1.6, 5.4, sy * 2.75, sy * 3.05, 9.3, 11.1, 'amber', 0.1)                                                  # 琥珀の窓
        gbox(11.6, 21.6, sy * 2.35, sy * 2.75, 6.2, 7.5, 'brass', 0.1)                                                 # 真鍮の帯
    gprism([(8.6, 4.2), (20.6, 4.2), (21.4, 5.0), (21.4, 6.0), (8.6, 6.0)], -2.2, 2.2, 'gun', 0.3)                    # 銃身の下の枠
    # 用心金（細い枠）と引き金
    gprism([(3.4, 4.9), (10.6, 4.9), (10.9, 4.0), (9.6, 0.4), (4.2, 0.4), (4.2, 1.2), (9.0, 1.2), (9.9, 4.0), (3.4, 4.0)], -1.0, 1.0, 'gun', 0.2)
    gprism([(6.6, 4.9), (7.6, 4.9), (7.0, 2.4), (6.1, 2.6)], -0.6, 0.6, 'graphite_dk', 0.15)
    # 握り（後ろへ傾く）
    gprism([(-3.8, 5.6), (3.6, 5.6), (1.9, -4.9), (1.2, -5.6), (-3.6, -5.6), (-4.4, -4.8)], -1.7, 1.7, 'gun', 0.4)
    muzzle = np.eye(4)
    muzzle[:3, :3] = R
    muzzle[:3, 3] = G(25.4, 0, 9.2)
    # --- 握る右手（手袋。指先は素手） ---
    gbox(-6.4, 3.4, -4.7, -1.7, -5.0, 4.4, 'graphite', 0.8, 'fist')        # 掌
    gbox(-6.6, -3.9, -4.4, 1.4, -3.8, 4.6, 'graphite', 0.8, 'fist')        # 握りの後ろ（親指の付け根）
    zs = (3.4, 1.15, -1.05, -3.2)
    for i, z in enumerate(zs):
        k = 3.4 - 0.19 * (5.6 - z)          # 握りの前の面の X
        if i == 0:   # 人さし指：用心金の中の引き金へ
            pts = [G(2.8, -3.5, z), G(5.6, -2.4, z), G(6.9, -0.2, z - 0.1), G(5.9, 1.6, z - 0.2)]
            cols = ['graphite', 'skin', 'skin']
        else:
            pts = [G(2.6, -3.6, z), G(k + 1.9, -2.2, z), G(k + 2.1, 0.8, z), G(k + 0.4, 2.7, z), G(k - 1.8, 2.7, z)]
            cols = ['graphite', 'graphite', 'skin', 'skin']
        finger(m, pts, 0.0106 if i < 3 else 0.0098, cols, bone, n=6, hint=tuple(gz), name='fist')
    pts = [G(-4.8, -1.4, 3.9), G(-3.6, 2.0, 4.3), G(-0.2, 2.8, 4.4), G(2.9, 2.6, 4.3)]
    finger(m, pts, 0.0118, ['graphite', 'skin', 'skin'], bone, n=6, hint=tuple(gz), name='fist')
    return muzzle


def build(groups):
    build_core(groups['Frame_core'])
    build_gauntlet(groups['Frame_arm'])
    build_legs(groups['Frame_legs'])
    build_left_hand(groups['Haru'])
    muzzle = build_right_hand_and_gun(groups['Haru'])
    return {'gun_pieces': ('gun',), 'blade': build_blade(), 'muzzle': muzzle}
