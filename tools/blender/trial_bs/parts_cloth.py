"""服（別のメッシュ）：シャツ、上着（襟・袖）、ベルトとバックル、ポーチ、ズボン、すね（レギンス）、足首のカフ、靴。
character-artist の Clothing Workflow：体の芯の形（胴の輪）を少し大きくして服の元にし、服は体と UV を分ける。
絵の服は面が平らに折れた塊なので、ズボン・靴は 8 角の輪で、平らな陰（角度で硬い辺）にする。
"""
import math
from mathutils import Vector, Matrix

from proportions import J
from meshkit import Part, tube, loft, ring, frame_from_dir, slab, poly_ring, rounded_rect, chamfer_rect

# 胴の芯（高さ z、半幅 w、前 f、後ろ b：y は絶対値）。正面・真横の絵の影から
TORSO = [
    (0.840, 0.122, -0.134, 0.034),
    (0.880, 0.120, -0.134, 0.034),
    (0.930, 0.122, -0.139, 0.040),
    (0.990, 0.126, -0.145, 0.046),
    (1.040, 0.129, -0.148, 0.050),
    (1.085, 0.126, -0.142, 0.050),
    (1.120, 0.112, -0.126, 0.046),
    (1.148, 0.070, -0.092, 0.028),
]


def torso_point(a, z, grow=0.0):
    """胴の面の点。a：0 = 正面、+π/2 = 左（+X）"""
    rs = TORSO
    if z <= rs[0][0]:
        w, f, b = rs[0][1:]
    elif z >= rs[-1][0]:
        w, f, b = rs[-1][1:]
    else:
        for p, q in zip(rs, rs[1:]):
            if p[0] <= z <= q[0]:
                t = (z - p[0]) / (q[0] - p[0])
                w, f, b = (p[k] + (q[k] - p[k]) * t for k in (1, 2, 3))
                break
    c, s = math.cos(a), math.sin(a)
    e = 2.0 / 2.8
    x = (w + grow) * math.copysign(abs(s) ** e, s)
    y = ((f - grow) * abs(c) ** e) if c >= 0 else (-(b + grow) * c)
    return Vector((x, y, z))


def shirt():
    N = 16
    zs = [0.835, 0.88, 0.93, 0.99, 1.04, 1.085, 1.12, 1.148]
    rings = [[torso_point(math.pi + 2 * math.pi * j / N, z, -0.004) for j in range(N)] for z in zs]
    # えりぐり（首のまわり）
    top = [Vector((0.050 * math.sin(math.pi + 2 * math.pi * j / N), -0.020 - 0.055 * math.cos(math.pi + 2 * math.pi * j / N) * (1 if math.cos(math.pi + 2 * math.pi * j / N) < 0 else 0.75), 1.168)) for j in range(N)]
    rings.append(top)
    return loft(rings, 'ivory', cap0=True, cap1=False)


def jacket():
    """短い上着：前が開いた胴（C の形の輪）＋襟の返り。厚みは Solidify（build で付ける）"""
    N = 18
    gap = 0.30   # 前の開き（正面の角度の幅、rad）
    zs = [0.915, 0.95, 0.99, 1.04, 1.085, 1.120, 1.150]
    rings = []
    for z in zs:
        g = gap * (1.0 if z < 1.10 else 0.85)
        pts = []
        for j in range(N):
            a = g + (2 * math.pi - 2 * g) * j / (N - 1)
            pts.append(torso_point(a, z, 0.010 + (0.004 if z < 0.94 else 0.0)))
        rings.append(pts)
    p = loft(rings, lambda i, j: 'brick', cap0=False, cap1=False, closed=False)
    return p


def collar():
    """焦げ茶の返った襟（フード状）：首の後ろから肩を回って前の縁へ下りる太い輪"""
    N = 14
    path = []
    for k in range(N + 1):
        a = -math.pi * 0.80 + 1.60 * math.pi * k / N    # 前の左 → 後ろ → 前の右
        a = a + math.pi
        z = 1.150 + 0.018 * math.cos(a - math.pi) * -1
        r = 0.082
        x = r * math.sin(a)
        y = -0.025 - 0.075 * math.cos(a) * (0.9 if math.cos(a) > 0 else 1.0)
        path.append(Vector((x, y, z)))
    # 前の両端は胸へ下りる（襟の返り）
    l0 = path[0] + Vector((0.008, -0.015, -0.07))
    l1 = path[-1] + Vector((-0.008, -0.015, -0.07))
    path = [l0] + path + [l1]
    radii = [(0.020, 0.010)] + [(0.026, 0.020)] * (len(path) - 2) + [(0.020, 0.010)]
    return tube(path, radii, n=6, col='umber', up=Vector((0, 0, 1)))


def sleeve(side):
    s = '.L' if side > 0 else '.R'
    sh, el = J['upper_arm' + s], J['forearm' + s]
    d = (el - sh).normalized()
    out = Vector((side, 0, 0))
    base = sh - d * 0.04 + Vector((-side * 0.01, 0, 0.012))
    path = [base, sh + d * 0.03, sh + d * 0.10, sh + d * 0.150, sh + d * 0.168]
    radii = [(0.066, 0.062), (0.070, 0.065), (0.066, 0.062), (0.060, 0.056), (0.058, 0.055)]
    sl = tube(path, radii, n=10, col='brick', start=-math.pi / 2, caps=(False, False))
    cuff = tube([sh + d * 0.148, sh + d * 0.172], [(0.061, 0.058), (0.059, 0.056)], n=10, col='graphite', start=-math.pi / 2)
    return sl, cuff


def belt():
    N = 20
    rings = [[torso_point(math.pi + 2 * math.pi * j / N, z, 0.020) for j in range(N)] for z in (0.828, 0.872)]
    p = loft(rings, 'graphite', cap0=False, cap1=False)
    # 内側の面（厚み）は Solidify で付ける
    return p


def buckle():
    """真鍮の四角いバックル（枠）"""
    c = torso_point(0.0, 0.850, 0.026)
    xa, ya = Vector((1, 0, 0)), Vector((0, 0, 1))
    outer = slab(chamfer_rect(0.054, 0.044, 0.004), c + Vector((0, -0.004, 0)), xa, -Vector((0, 0, 1)) if False else ya, 0.008, 'brass', bevel=0.002)
    # 帯が通る暗い中（枠の内側）
    inner = slab(chamfer_rect(0.034, 0.026, 0.002), c + Vector((0, -0.007, 0)), xa, ya, 0.006, 'graphite')
    return outer.extend(inner)


def pouches():
    out = []
    for side, x, z, w, h in ((1, 0.150, 0.810, 0.058, 0.085), (-1, -0.150, 0.800, 0.056, 0.080)):
        a = math.atan2(x, -0.11)
        c = torso_point(math.radians(55) * side, z, 0.050)
        nrm = Vector((c.x, c.y + 0.035, 0)).normalized()
        xa = Vector((0, 0, 1)).cross(nrm).normalized()
        box = slab(chamfer_rect(w, h, 0.008), c, -xa if side > 0 else -xa, Vector((0, 0, 1)), 0.040, 'graphite', bevel=0.004)
        flap = slab(chamfer_rect(w + 0.004, 0.030, 0.006), c + Vector((0, 0, h / 2 - 0.012)) + nrm * 0.004, -xa, Vector((0, 0, 1)), 0.044, 'graphite', bevel=0.004)
        clip = slab(chamfer_rect(0.014, 0.010, 0.002), c + Vector((0, 0, h / 2 - 0.022)) + nrm * 0.027, -xa, Vector((0, 0, 1)), 0.004, 'brass')
        p = box.extend(flap).extend(clip)
        out.append((side, p))
    return out


def trouser_leg(side):
    """太いズボン（膝まで）。腰の中心をまたいで左右が重なる（股の V は重なりの形）。8 角で平らな面"""
    s = '.L' if side > 0 else '.R'
    th, sn = J['thigh' + s], J['shin' + s]
    d = (sn - th).normalized()
    top = Vector((side * 0.070, -0.038, 0.875))
    path = [top, Vector((side * 0.080, -0.040, 0.80)), Vector((side * 0.092, -0.036, 0.70)), Vector((side * 0.104, -0.028, 0.60)), Vector((side * 0.112, -0.022, 0.53)), Vector((side * 0.117, -0.020, 0.495))]
    radii = [(0.090, 0.088), (0.100, 0.093), (0.104, 0.094), (0.100, 0.092), (0.093, 0.086), (0.082, 0.076)]
    return tube(path, radii, n=8, col='brick', start=math.pi / 8 + (0 if side > 0 else 0), caps=(False, True))


def legging(side):
    s = '.L' if side > 0 else '.R'
    kn, an = J['shin' + s], J['foot' + s]
    d = (an - kn).normalized()
    path = [kn - d * 0.08, kn, kn + d * 0.10, kn + d * 0.20, an + Vector((0, 0, 0.04))]
    radii = [(0.058, 0.060), (0.056, 0.058), (0.054, 0.058), (0.048, 0.052), (0.044, 0.048)]
    return tube(path, radii, n=10, col='umber', start=-math.pi / 2, caps=(False, False))


def ankle_cuff(side):
    s = '.L' if side > 0 else '.R'
    an = J['foot' + s]
    c0 = Vector((an.x, an.y - 0.002, 0.163))
    c1 = Vector((an.x, an.y - 0.004, 0.205))
    rings = [ring(c, Vector((1, 0, 0)), Vector((0, -1, 0)), 0.060, 0.066, 10, 0.0, 2.6) for c in (c0, c0 + Vector((0, 0, 0.004)), c1 - Vector((0, 0, 0.004)), c1)]
    # 上と下の縁を少し細く（折り返しの厚み）
    for k in (0, 3):
        cc = sum(rings[k], Vector()) / len(rings[k])
        rings[k] = [cc + (q - cc) * 0.93 for q in rings[k]]
    return loft(rings, 'brick')


def boot(side):
    """靴：焦げ茶の胴、爪先だけ白いブロック、厚い黒鉛の底（踵と爪先の間に浅い切り欠き）"""
    s = '.L' if side > 0 else '.R'
    an = J['foot' + s]
    x0 = an.x + math.copysign(0.006, an.x)
    # 足の胴：踵（+Y）→ 爪先（-Y）へ、XZ の断面（幅、底の高さ、上の高さ）
    sec = [
        (0.090, 0.064, 0.030, 0.185),   # y, 半幅, 下, 上（踵の後ろ）
        (0.060, 0.069, 0.030, 0.190),
        (0.010, 0.072, 0.030, 0.172),
        (-0.040, 0.073, 0.030, 0.122),
        (-0.085, 0.076, 0.030, 0.104),
        (-0.130, 0.078, 0.030, 0.096),
        (-0.170, 0.074, 0.030, 0.086),
        (-0.194, 0.060, 0.034, 0.070),
    ]
    rings = []
    for y, w, lo, hi in sec:
        pts = []
        mid = (lo + hi) / 2
        hh = (hi - lo) / 2
        for k in range(10):
            a = 2 * math.pi * k / 10
            c, sn = math.cos(a), math.sin(a)
            e = 2.0 / 3.2
            xx = w * math.copysign(abs(c) ** e, c)
            zz = hh * math.copysign(abs(sn) ** e, sn)
            pts.append(Vector((x0 + xx, y + an.y, mid + zz)))
        rings.append(pts)

    def col(i, j):
        return 'ivory' if i >= 4 else 'umber'
    body = loft(rings, col)
    # 底：踵の塊と前の塊、間は浅く上がる
    sole = Part()
    sole_pts = [
        (0.094, 0.067, 0.000, 0.034), (0.020, 0.071, 0.000, 0.034), (0.008, 0.069, 0.010, 0.034),
        (-0.040, 0.071, 0.010, 0.034), (-0.052, 0.076, 0.000, 0.034), (-0.150, 0.081, 0.000, 0.034),
        (-0.198, 0.068, 0.000, 0.040), (-0.208, 0.054, 0.006, 0.040),
    ]
    rings = []
    for y, w, lo, hi in sole_pts:
        rings.append([Vector((x0 + w * xs, y + an.y, z)) for xs, z in ((1, lo), (1, hi), (-1, hi), (-1, lo))])
    sole = loft(rings, 'graphite')
    return body, sole
