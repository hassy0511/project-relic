"""硬い部品（体と別のメッシュ。character-artist：体と硬い外装を 1 つのメッシュにしない）。
ゴーグルと帯、外装フレーム（core：背中の板・肩ひも・右肩の板、arm：左の籠手、legs：膝当て・すねの板・右太ももの板）、
スパーク（銃）、光刃。hard-surface の考え：塊 → 面の段（板の面取り・継ぎ目）→ 細部（レール・窓）。
"""
import math
from mathutils import Vector, Matrix

from proportions import J
from meshkit import Part, tube, loft, ring, frame_from_dir, slab, poly_ring, rounded_rect, chamfer_rect
from parts_body import head_point
from parts_cloth import torso_point


# ---------------------------------------------------------------- ゴーグル
def goggles():
    p = Part()
    tilt = math.radians(18)            # レンズは前・少し上を向く
    for side in (1, -1):
        c = Vector((side * 0.066, -0.148, 1.440))
        xa = Vector((1, 0, 0))
        ya = Matrix.Rotation(-tilt, 3, 'X') @ Vector((0, 0, 1))
        # 外へ少し回す（額の丸みに沿う）
        rz = Matrix.Rotation(side * math.radians(26), 3, 'Z')
        xa, ya = rz @ xa, rz @ ya
        nrm = xa.cross(ya)            # 前（外・少し上）向き
        fr = slab(chamfer_rect(0.118, 0.070, 0.018), c, xa, ya, 0.036, 'graphite', bevel=0.005)
        lens = slab(chamfer_rect(0.092, 0.048, 0.013), c + nrm * 0.0155, xa, ya, 0.010, 'amber', bevel=0.003)
        p.extend(fr).extend(lens)
    # 鼻の上の橋
    br = slab(chamfer_rect(0.034, 0.036, 0.006), Vector((0, -0.168, 1.438)), Vector((1, 0, 0)), Matrix.Rotation(-tilt, 3, 'X') @ Vector((0, 0, 1)), 0.026, 'graphite', bevel=0.004)
    p.extend(br)
    return p


def goggle_strap():
    """暗い 1 本の帯：レンズの脇から耳の上を通り、後頭部を水平に回る（髪の上に乗る）"""
    N = 28
    path = []
    for k in range(N + 1):
        a = math.radians(-118) + math.radians(236) * k / N     # 左のレンズの脇 → 後ろ → 右のレンズの脇
        a = math.pi + a
        c = math.cos(a)
        z = 1.372 + 0.050 * max(0.0, c) ** 1.2 + 0.010 * c
        path.append(head_point(a, z, 0.036 + 0.012 * (1 - max(0.0, c))))
    xs = []
    rr = [(0.004, 0.018)] * len(path)
    return tube(path, rr, n=4, col='graphite', up=Vector((0, 0, 1)), sq=2.0)


# ---------------------------------------------------------------- 外装フレーム：胴の核（Frame_core）
def _torso_at_x(x, z, grow, back):
    """胴の面で、横の位置 x にある前（back=False）か後ろ（back=True）の点"""
    best = None
    for k in range(181):
        a = (math.pi / 2 + math.pi / 2 * k / 180) if back else (math.pi / 2 * k / 180)
        a = a if x >= 0 else -a
        q = torso_point(a, z, grow)
        if best is None or abs(q.x - x) < abs(best.x - x):
            best = q
    return best


def shoulder_straps():
    """2 本の暗い肩ひも：前の裾から肩を越えて背中の裾へ（背中でも平行、X にしない）。上着の面の外に乗せる"""
    p = Part()
    for side in (1, -1):
        x = side * 0.100
        path = [_torso_at_x(x, z, 0.024, False) for z in (0.925, 0.99, 1.06, 1.10)]
        path.append(Vector((side * 0.102, -0.058, 1.146)))
        path.append(Vector((side * 0.104, -0.012, 1.160)))
        path.append(Vector((side * 0.102, 0.034, 1.128)))
        path += [_torso_at_x(x, z, 0.024, True) for z in (1.06, 0.99, 0.925)]
        rr = [(0.020, 0.0055)] * len(path)
        p.extend(tube(path, rr, n=4, col='graphite', up=Vector((0, 0, 1))))   # 幅は横（x）へ
    return p


def back_panel():
    """背中の白い板（帯の間、上背部）。ナゴミの受け口"""
    z = 1.074
    q = torso_point(math.pi, z, 0.020)
    c = Vector((0, q.y + 0.006, z))
    xa, ya = Vector((-1, 0, 0)), Vector((0, 0.06, 1)).normalized()
    return slab(chamfer_rect(0.118, 0.082, 0.016), c, xa, ya, 0.014, 'ivory', bevel=0.004)


def shoulder_plate():
    """本人右肩だけの白磁の厚い板と、上腕の暗い固定帯"""
    sh, el = J['upper_arm.R'], J['forearm.R']
    d = (el - sh).normalized()
    out = Vector((-0.86, 0, 0.5)).normalized()          # 肩の外・上
    c = sh + d * 0.030 + out * 0.047 + Vector((0, 0.008, 0.012))
    xa = Vector((0, -1, 0))                              # 板の幅は前後
    ya = (-d).normalized()                               # 板の長さは腕に沿う
    ya = (ya - xa * ya.dot(xa)).normalized()
    plate = slab(chamfer_rect(0.124, 0.135, 0.024), c, xa, ya, 0.028, 'ivory', bevel=0.007)
    # 上腕の帯
    band = tube([sh + d * 0.10, sh + d * 0.125], [(0.064, 0.060), (0.062, 0.058)], n=10, col='graphite', start=-math.pi / 2)
    # 板と帯をつなぐ暗い支え
    sup = slab(chamfer_rect(0.028, 0.060, 0.004), sh + d * 0.085 + out * 0.055, xa, ya, 0.014, 'graphite')
    return plate.extend(band).extend(sup)


# ---------------------------------------------------------------- 左の籠手（Frame_arm）と光刃
def gauntlet():
    el, wr = J['forearm.L'], J['hand.L']
    d = (wr - el).normalized()
    a0 = el + d * 0.050
    a1 = wr - d * 0.010
    shell = tube([a0, a0.lerp(a1, 0.5), a1], [(0.044, 0.040), (0.043, 0.039), (0.039, 0.035)], n=8, col='ivory', start=-math.pi / 2, sq=2.4)
    bands = Part()
    for t0, t1 in ((-0.006, 0.020), (0.150 - 0.025, 0.150)):
        bands.extend(tube([a0 + d * t0, a0 + d * t1], [(0.047, 0.043), (0.046, 0.042)], n=8, col='graphite', start=-math.pi / 2, sq=2.4))
    # 小指側の真鍮のレール（外・後ろ寄り）
    xa, ya = frame_from_dir(d)
    side_dir = (ya * 0.75 + xa * 0.65).normalized()     # 外（上腕の外側）と後ろの間
    rail = tube([a0 + d * 0.01 + side_dir * 0.046, a1 + d * 0.012 + side_dir * 0.042], [(0.007, 0.0045), (0.007, 0.0045)], n=6, col='brass', up=side_dir)
    emitter = tube([a1 + side_dir * 0.042, a1 + d * 0.02 + side_dir * 0.042], [0.009, 0.008], n=6, col='graphite')
    return shell.extend(bands).extend(rail).extend(emitter), (a1 + d * 0.02 + side_dir * 0.042, d, side_dir)


def light_blade(start, d, side_dir):
    """琥珀の光刃：籠手の射出口から拳の先へ、前腕と平行に約 45 cm（指や掌を貫かない：外へ 2 cm 離す）"""
    s0 = start + side_dir * 0.012
    L = 0.47
    n_ = d.cross(side_dir).normalized()
    pts = [s0, s0 + d * 0.05, s0 + d * (L - 0.06), s0 + d * L]
    radii = [(0.010, 0.004), (0.014, 0.004), (0.013, 0.004), (0.004, 0.002)]
    return tube(pts, radii, n=6, col='amber', up=side_dir, tips=(None, s0 + d * (L + 0.04)))


# ---------------------------------------------------------------- 脚のフレーム（Frame_legs）
def knee_parts(side):
    s = '.L' if side > 0 else '.R'
    kn = J['shin' + s]
    p = Part()
    # 暗い固定帯（膝のまわり、後ろも暗い）
    p.extend(tube([kn + Vector((0, 0, -0.032)), kn + Vector((0, 0, 0.032))], [(0.072, 0.066), (0.074, 0.068)], n=10, col='graphite', start=-math.pi / 2))
    # 前の白い膝当て（厚い盾の形）
    c = kn + Vector((0, -0.066, 0.005))
    cap = slab([(0.056, 0.044), (0.0, 0.074), (-0.056, 0.044), (-0.062, -0.036), (-0.034, -0.080), (0.034, -0.080), (0.062, -0.036)],
               c, Vector((1, 0, 0)), Vector((0, -0.12, 1)).normalized(), 0.030, 'ivory', bevel=0.010)
    p.extend(cap)
    # 横の琥珀の丸い継ぎ目（内と外）
    for sx in (1, -1):
        hc = kn + Vector((sx * 0.074, -0.006, 0.006))
        p.extend(tube([hc - Vector((sx * 0.008, 0, 0)), hc + Vector((sx * 0.009, 0, 0))], [0.027, 0.027], n=10, col='graphite'))
        p.extend(tube([hc + Vector((sx * 0.009, 0, 0)), hc + Vector((sx * 0.012, 0, 0))], [0.018, 0.016], n=10, col='amber'))
    return p


def shin_plates(side):
    """すねの両側の細い白い板（中央は暗いすねが見える）"""
    s = '.L' if side > 0 else '.R'
    kn, an = J['shin' + s], J['foot' + s]
    d = (an - kn).normalized()
    p = Part()
    for sx in (1, -1):
        a = kn + d * 0.095
        b = kn + d * 0.270
        off = Vector((sx * 0.044, -0.030, 0))
        p.extend(tube([a + off, b + off * 0.92], [(0.012, 0.016), (0.010, 0.013)], n=6, col='ivory', up=Vector((0, -1, 0)), sq=2.5))
    return p


def thigh_plate():
    """本人右の太ももの外の大きい白い板（前・外向き、少し斜め）と、腰帯からの短い支え"""
    nrm = Vector((-0.30, -0.95, 0.0)).normalized()
    c = Vector((-0.082, -0.036, 0.672)) + nrm * 0.094
    ya = Vector((0.10, 0.0, 1.0)).normalized()       # 上がわずかに内へ
    xa = ya.cross(nrm).normalized()
    ya = nrm.cross(xa).normalized()
    plate = slab(chamfer_rect(0.110, 0.200, 0.012), c, xa, ya, 0.018, 'ivory', bevel=0.006)
    sup = slab(chamfer_rect(0.026, 0.060, 0.004), c + ya * 0.120 - nrm * 0.008, xa, ya, 0.012, 'graphite')
    return plate.extend(sup)


# ---------------------------------------------------------------- スパーク（銃）。銃の座標：銃身 +X、上 +Z、原点 = 握りの中心
MUZZLE = Vector((0.222, 0.0, 0.074))


def spark_gun():
    p = Part()
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    # 後ろの高い箱（遊底の後ろ）
    p.extend(slab(chamfer_rect(0.110, 0.060, 0.010), Vector((-0.032, 0, 0.078)), X, Z, 0.040, 'graphite', bevel=0.004))
    # 銃身の箱（前へ）
    p.extend(slab(chamfer_rect(0.200, 0.048, 0.008), Vector((0.115, 0, 0.074)), X, Z, 0.036, 'graphite_lt', bevel=0.004))
    # 銃口の太い先
    p.extend(slab(chamfer_rect(0.030, 0.054, 0.008), Vector((0.205, 0, 0.074)), X, Z, 0.040, 'graphite', bevel=0.004))
    # 握り（後ろへ傾く）
    g = Matrix.Rotation(math.radians(-14), 3, 'Y')
    gx, gz = g @ X, g @ Z
    p.extend(slab(chamfer_rect(0.046, 0.110, 0.010), Vector((-0.012, 0, -0.008)), gx, gz, 0.032, 'graphite', bevel=0.004))
    # 用心金（引き金の囲い）
    guard = [Vector((0.012, 0, 0.044)), Vector((0.058, 0, 0.040)), Vector((0.062, 0, 0.018)), Vector((0.044, 0, 0.004)), Vector((0.018, 0, 0.006))]
    p.extend(tube(guard, [(0.004, 0.007)] * len(guard), n=4, col='graphite', up=Vector((0, 1, 0))))
    p.extend(tube([Vector((0.030, 0, 0.044)), Vector((0.038, 0, 0.022))], [(0.004, 0.003), (0.003, 0.003)], n=4, col='graphite_lt'))
    # 後ろの白いブロック
    p.extend(slab(chamfer_rect(0.026, 0.040, 0.006), Vector((-0.083, 0, 0.088)), X, Z, 0.042, 'ivory', bevel=0.004))
    # 琥珀の窓（両側）と真鍮のレール（両側）
    for sy in (1, -1):
        p.extend(slab(chamfer_rect(0.036, 0.020, 0.003), Vector((-0.045, sy * 0.0205, 0.088)), X if sy < 0 else -X, Z, 0.003, 'amber'))
        p.extend(slab(chamfer_rect(0.090, 0.008, 0.001), Vector((0.120, sy * 0.0185, 0.060)), X if sy < 0 else -X, Z, 0.003, 'brass'))
    # 銃口の穴（暗い円）
    p.extend(tube([MUZZLE - Vector((0.004, 0, 0)), MUZZLE + Vector((0.0015, 0, 0))], [0.010, 0.010], n=8, col='umber_dk', up=Z))
    return p
