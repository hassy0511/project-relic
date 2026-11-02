"""体（首・腕・手）と頭。character-artist：比率 → 体の形 → 手足のつなぎ → 顔 → 輪の計画。

- 腕：肘のまわりに 3 本の輪（elbow の 3-loop）、継ぎ目は体の側（内側）。
- 頭：横の輪を下（あご）から上（頭頂）へ並べたロフト。顔の目・眉・口はテクスチャ（2×2 の表情）なので、
  口や目のまわりの輪は作らない（retopology/game-cinematic-topo：「台詞の口の動きが無ければ少なくてよい」）。
- 体は服の下で見えない所を作らない（polycount-budgets の Validation：見えない面を消す）。胴と脚の芯は服の側で作る。
"""
import math
from mathutils import Vector, Matrix

from proportions import J
from meshkit import Part, tube, loft, ring, frame_from_dir, slab, poly_ring

# ---------------------------------------------------------------- 頭の形（横の輪：高さ z、半幅 w、前 f、後ろ b。y は絶対値）
HEAD_RINGS = [
    # z      w      f       b
    (1.205, 0.020, -0.130, -0.104),
    (1.212, 0.040, -0.141, -0.060),
    (1.225, 0.062, -0.151, -0.005),
    (1.241, 0.078, -0.158, 0.045),
    (1.259, 0.088, -0.163, 0.068),
    (1.282, 0.091, -0.162, 0.086),
    (1.310, 0.098, -0.158, 0.096),
    (1.345, 0.103, -0.152, 0.102),
    (1.380, 0.103, -0.142, 0.102),
    (1.415, 0.096, -0.124, 0.096),
    (1.445, 0.080, -0.098, 0.080),
    (1.468, 0.052, -0.062, 0.052),
]
HEAD_TOP = Vector((0, 0.0, 1.480))
HEAD_N = 32


def _interp_ring(z):
    rs = HEAD_RINGS
    if z <= rs[0][0]:
        return rs[0][1:]
    for a, b in zip(rs, rs[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return tuple(a[k] + (b[k] - a[k]) * t for k in (1, 2, 3))
    return rs[-1][1:]


def head_point(a, z, out=0.0):
    """頭の面の点：角度 a（0 = 正面、+π/2 = 本人の左 +X）、高さ z。out だけ外へ"""
    w, f, b = _interp_ring(z)
    c, s = math.cos(a), math.sin(a)
    # 前は平ら気味（顔）、後ろは丸い
    if c >= 0:
        e = 2.0 / 2.6
        cc = c ** e
        y = f * cc
    else:
        y = -b * c
    x = w * math.copysign(abs(s) ** (2.0 / 2.3), s)
    p = Vector((x, y, z))
    if out:
        cen = Vector((0, (f + b) / 2 * 0 + (f + b) / 2, z))
        d = Vector((p.x, p.y - (f + b) / 2, 0))
        if d.length > 1e-6:
            p += d.normalized() * out
    return p


def head():
    rings = []
    for z, w, f, b in HEAD_RINGS:
        rings.append([head_point(math.pi + 2 * math.pi * j / HEAD_N, z) for j in range(HEAD_N)])
    p = loft(rings, 'skin', cap0=False, tip0=Vector((0, -0.120, 1.201)), tip1=HEAD_TOP)
    # 鼻：小さいくさび（面の光の当たりで鼻筋が見える程度）
    nz, ny = 1.268, -0.163
    nose = Part()
    a = nose.add_v((0, ny - 0.014, nz - 0.004))
    b_ = nose.add_v((-0.009, ny + 0.002, nz - 0.010))
    c = nose.add_v((0.009, ny + 0.002, nz - 0.010))
    d = nose.add_v((0, ny + 0.002, nz + 0.022))
    for f in ((a, c, d), (a, d, b_), (a, b_, c)):
        nose.add_f(f, [(0, 0), (0.01, 0), (0.01, 0.01)], 'skin')
    p.extend(nose)
    return p


def ears():
    out = Part()
    for side in (1, -1):
        c = Vector((side * 0.104, 0.008, 1.292))
        xa = Vector((0, -1, 0))
        ya = Vector((0, 0, 1))
        # 外へ少し開く
        rot = Matrix.Rotation(side * math.radians(32), 3, 'Z')
        xa, ya = rot @ xa, rot @ ya
        prof = [(0.0, 0.032), (-0.018, 0.025), (-0.024, 0.005), (-0.018, -0.020), (-0.005, -0.031), (0.010, -0.022), (0.013, 0.007), (0.010, 0.025)]
        e = slab(prof, c + Vector((side * 0.006, 0, 0)), xa if side > 0 else -xa, ya, 0.012, 'skin', bevel=0.003)
        out.extend(e)
    return out


def neck():
    a = J['neck'] + Vector((0, 0.0, -0.04))
    b = J['head'] + Vector((0, 0.01, 0.06))
    path = [a, a.lerp(b, 0.5), b]
    return tube(path, [0.050, 0.040, 0.037], n=12, col='skin', start=math.pi / 2)


# ---------------------------------------------------------------- 腕（袖の中から手首まで）
def arm(side):
    s = '.L' if side > 0 else '.R'
    sh, el, wr = J['upper_arm' + s], J['forearm' + s], J['hand' + s]
    d1 = (el - sh).normalized()
    d2 = (wr - el).normalized()
    path = [sh + d1 * 0.02, sh + d1 * 0.12, el - d1 * 0.03, el, el + d2 * 0.03, el + d2 * 0.10, wr - d2 * 0.02, wr + d2 * 0.012]
    radii = [(0.044, 0.044), (0.039, 0.040), (0.033, 0.033), (0.032, 0.031), (0.033, 0.031), (0.035, 0.032), (0.028, 0.023), (0.027, 0.022)]
    return tube(path, radii, n=10, col='skin', start=-math.pi / 2)


def _hand_frame(side):
    """手の座標：a = 指の向き、t = 親指の側（前 -Y）、n = 手のひらの向き（体の側）"""
    s = '.L' if side > 0 else '.R'
    a = (J['hand_end' + s] - J['hand' + s]).normalized()
    t = Vector((0, -1, 0))
    t = (t - a * t.dot(a)).normalized()
    n = a.cross(t).normalized()
    if n.x * side > 0:      # 手のひらは体の側（左手は -X）
        n = -n
    return a, t, n


def open_hand(side, glove=True):
    """開いた手（A ポーズの絵）。指の出る手袋（手のひら・甲と指の付け根を覆う）"""
    s = '.L' if side > 0 else '.R'
    a, t, n = _hand_frame(side)
    w0 = J['hand' + s]
    skin, glv = Part(), Part()

    def P(x, y, z):  # 手の座標 → 世界
        return w0 + a * x + t * y + n * z

    # 手のひら（手首 → 指の付け根）
    rings = []
    for x, wd, th in ((-0.005, 0.029, 0.018), (0.030, 0.037, 0.019), (0.068, 0.041, 0.016)):
        c = P(x, 0.004, 0)
        rings.append(ring(c, t, n, wd, th, 8, 0.0, 3.0))
    palm = loft(rings, 'skin')
    # 指：人差し指（親指の側）→ 小指
    fingers = [(0.028, 0.062, 0.0102, -7), (0.009, 0.068, 0.0105, -1), (-0.010, 0.064, 0.0102, 5), (-0.028, 0.052, 0.0094, 12)]
    for y0, ln, r, spread in fingers:
        base = P(0.062, y0, 0.0)
        sp = math.radians(spread)
        dirv = (a * math.cos(sp) - t * math.sin(sp)).normalized()
        curl = math.radians(12)
        pts = [base]
        d = dirv
        for k, seg in enumerate((0.45, 0.30, 0.25)):
            d = (d * math.cos(curl) + n * math.sin(curl)).normalized()
            pts.append(pts[-1] + d * ln * seg)
        rr = [r * 1.05, r, r * 0.92, r * 0.80]
        f = tube(pts, rr, n=6, col='skin', up=n, tips=(None, pts[-1] + d * r * 0.6))
        skin.extend(f)
        if glove:
            g = tube([pts[0] - d * 0.004, pts[0].lerp(pts[1], 0.75)], [r * 1.35, r * 1.3], n=6, col='graphite', up=n)
            glv.extend(g)
    # 親指
    tb = P(0.016, 0.030, 0.010)
    td = (a * 0.55 + t * 0.75 + n * 0.35).normalized()
    pts = [tb, tb + td * 0.026, tb + td * 0.045 + a * 0.008]
    skin.extend(tube(pts, [0.011, 0.0095, 0.008], n=6, col='skin', up=n, tips=(None, pts[-1] + td * 0.006)))
    if glove:
        glv.extend(tube([tb - td * 0.004, tb + td * 0.022], [0.0135, 0.0125], n=6, col='graphite', up=n))
    skin.extend(palm)
    if glove:
        # 手袋の手のひらと手首のカフ
        rings = []
        for x, wd, th in ((-0.040, 0.033, 0.029), (-0.012, 0.034, 0.029), (-0.004, 0.033, 0.023), (0.030, 0.0405, 0.023), (0.066, 0.0445, 0.020)):
            rings.append(ring(P(x, 0.004, 0), t, n, wd, th, 8, 0.0, 3.0))
        glv.extend(loft(rings, 'graphite'))
    return skin, glv


# ---------------------------------------------------------------- 右手：銃を握る拳（銃の座標で作って、手の骨の基準の向きへ置く）
GUN_WRIST = Vector((-0.062, -0.040, -0.010))   # 手首（hand.R の元）の、銃の座標での位置（ゲームの HAND_WRIST_IN_GUN と同じ）


def gun_frame():
    """銃の座標（銃身 +X、上 +Z、+Y = 掌の側）→ 世界（Blender）の行列。
    ゲームの PlayerView.hand_gun_frame と同じ式：銃身 = 手の骨の向き、+Y = 体の +X から銃身の成分を除いた向き"""
    wr, he = J['hand.R'], J['hand_end.R']
    gx = (he - wr).normalized()
    gy = (Vector((1, 0, 0)) - gx * gx.x).normalized()
    gz = gx.cross(gy)
    rot = Matrix((gx, gy, gz)).transposed()
    org = wr - rot @ GUN_WRIST
    return Matrix.Translation(org) @ rot.to_4x4()


def fist_in_gun():
    """拳（銃の座標）。握りの中心が原点。手は握りの -Y 側、指は握りの前を回って +Y 側へ"""
    skin, glv = Part(), Part()
    x_ax, y_ax, z_ax = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    # 手の甲〜手のひら：手首から指の付け根まで。指の付け根の並びは縦（握りに沿って）
    rings = []
    for x, wz, wy in ((-0.075, 0.026, 0.020), (-0.045, 0.034, 0.021), (-0.010, 0.040, 0.020), (0.018, 0.041, 0.018)):
        rings.append(ring(Vector((x, -0.036, -0.012)), z_ax, y_ax, wz, wy, 8, 0.0, 3.0))
    glv.extend(loft(rings, 'graphite'))
    # 指：付け根から握りの前を回る（4 本、上が人差し指）
    for k, zc in enumerate((0.022, 0.002, -0.018, -0.036)):
        r = 0.0085 if k < 3 else 0.0075
        pts = [Vector((0.016, -0.034, zc)), Vector((0.034, -0.020, zc - 0.002)), Vector((0.036, 0.004, zc - 0.003)), Vector((0.022, 0.020, zc - 0.003))]
        skin.extend(tube(pts, [r, r * 0.98, r * 0.92, r * 0.85], n=6, col='skin', up=Vector((0, 0, 1)), tips=(None, pts[-1] + Vector((-0.006, 0.002, 0)))))
        glv.extend(tube([pts[0] - Vector((0.004, 0, 0)), pts[0].lerp(pts[1], 0.85)], [r * 1.35, r * 1.3], n=6, col='graphite', up=Vector((0, 0, 1))))
    # 親指：+Y 側、握りの上をまたぐ
    pts = [Vector((-0.030, -0.020, 0.020)), Vector((-0.010, 0.006, 0.030)), Vector((0.010, 0.022, 0.024))]
    skin.extend(tube(pts, [0.011, 0.0095, 0.0085], n=6, col='skin', up=Vector((0, 0, 1)), tips=(None, pts[-1] + Vector((0.006, 0.003, -0.002)))))
    glv.extend(tube([pts[0] - Vector((0.004, 0.004, 0)), pts[0].lerp(pts[1], 0.6)], [0.0135, 0.0125], n=6, col='graphite', up=Vector((0, 0, 1))))
    # 手首のカフ
    rings = [ring(Vector((x, -0.040, -0.010)), z_ax, y_ax, wz, wy, 8, 0.0, 3.0) for x, wz, wy in ((-0.110, 0.029, 0.026), (-0.078, 0.030, 0.026))]
    glv.extend(loft(rings, 'graphite'))
    return skin, glv
