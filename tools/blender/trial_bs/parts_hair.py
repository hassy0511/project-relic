"""髪：hair-groom の地域（groom-flow-regions）ごとの塊。
ゲーム向けの髪は本来「髪のカード（アルファの帯）」だが、アニメ調では塊（anime-style：Hair = masses, not strands）、
しかもスマホの描画（gl_compatibility）では透明が使えないので、厚みのある葉の形の房（不透明）にした。
地域：前髪（hair.front）・頭頂（hair.top）・横（hair.side.L/R）・後ろ（hair.back.L/R）・えり足（hair.nape）。
各地域：流れの向き・房の数・長さの幅を決めてから房を置く（Flow first、Clumps、Silhouette）。
根元は地肌の殻（SM_Hair_Cap）に埋め、生え際の地肌が見えないようにする（Scalp bleed）。
"""
import math
from mathutils import Vector, Matrix

from parts_body import head_point
from meshkit import Part, tube, loft, frame_from_dir

CROWN = Vector((0.0, -0.015, 1.478))
HEAD_C = Vector((0.0, -0.015, 1.330))    # 頭頂のつむじ（真上の絵で、房が放射状に出る中心。後ろ寄り）


def cap():
    """髪の地肌の殻：頭の面から 1 cm 外。顔の側は生え際で開く"""
    N = 24
    K = 7

    def rim(a):
        # 生え際の高さ：正面（額）1.385、こめかみ 1.32、耳の上 1.30、後ろ 1.235
        c = math.cos(a)
        ad = abs(math.degrees(math.atan2(math.sin(a), c)))
        if 72 < ad < 116:
            return 1.336                    # 耳の上で生え際を上げる（耳を出す）
        if c >= 0:
            return 1.300 + 0.085 * c ** 1.4
        return 1.300 + (1.300 - 1.235) * c
    rings = []
    for k in range(K):
        t = k / K
        pts = []
        for j in range(N):
            a = math.pi + 2 * math.pi * j / N
            z0 = rim(a)
            z = z0 + (1.468 - z0) * (t ** 0.9)
            pts.append(head_point(a, z, 0.016 + 0.004 * t))
        rings.append(pts)
    return loft(rings, 'umber', cap0=False, tip1=Vector((0, 0.0, 1.492)))


def tuft(root, dirs, length, width, thick=0.016, n=6, twist_up=None):
    """葉の形の房：root から dirs（曲がりの向きの並び）へ。幅は根元の 1/3 で最大、先はとがる（hair-card-atlas の
    「根元を回転の中心に、先を細く」を塊に読み替えた）"""
    pts = [Vector(root)]
    seg = length / len(dirs)
    for d in dirs:
        pts.append(pts[-1] + Vector(d).normalized() * seg)
    m = len(pts)
    radii = []
    for i in range(m):
        t = i / (m - 1)
        wv = width * max(0.06, math.sin(math.pi * (0.25 + 0.75 * t))) ** 0.9
        radii.append((wv, max(0.003, thick * (1 - 0.75 * t))))
    # 房の幅は頭の面に沿わせる：up は頭の中心からの向き（芯の向きとほぼ直交するのでねじれない）
    up = (Vector(root) - HEAD_C).normalized()
    tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * seg * 0.30
    # 根元は暗く、外の真ん中は明るく（重なった房の境目が見える。stylized-style：陰は描く）
    col = lambda i, j: 'umber_dk' if (i == 0 or j >= 3) else ('umber_lt' if j == 1 else 'umber')
    return tube(pts, radii, n=n, col=col, up=up, sq=1.35, tips=(None, tip))


def _o(a):
    return Vector((math.sin(a), -math.cos(a), 0.0))


def _region(a_deg, z):
    """房の根元の角度と高さ → 揺れの骨（地域）"""
    a = abs(a_deg)
    side = 'L' if a_deg > 0 else 'R'
    if z >= 1.462:
        return 'hair.top'
    if a < 42:
        return 'hair.front'
    if z < 1.285 and a > 115:
        return 'hair.nape'
    if a < 102:
        return 'hair.side.' + side
    return 'hair.back.' + side


def _down_tangent(a, z0, zc=1.335, R=0.145):
    """頭の丸みに沿って下へ向かう向き（根元の高さの緯度で、上の方は外へ、横は下へ）"""
    phi = math.asin(max(-0.95, min(0.95, (z0 - zc) / R)))
    return (_o(a) * math.sin(phi) + Vector((0, 0, -math.cos(phi)))).normalized()


def leaf(a0, z0, z1, da, width, out0, out1, thick=0.032, steps=5):
    """頭の面に沿って流れる葉の房：角度 a0・高さ z0 の根元から、角度を da だけ回しながら高さ z1 まで。
    面からの浮き out0 → out1（先が外へはねる）。幅は頭の面に沿い、厚みは外向き"""
    pts = []
    for k in range(steps + 1):
        t = k / steps
        pts.append(head_point(a0 + da * t, z0 + (z1 - z0) * t, out0 + (out1 - out0) * t ** 1.7))
    m = len(pts)
    radii = []
    for k in range(m):
        t = k / (m - 1)
        wv = width * max(0.06, math.sin(math.pi * (0.22 + 0.78 * t))) ** 0.8
        radii.append((wv, max(0.004, thick * (1 - 0.7 * t))))
    up = (pts[0] - HEAD_C).normalized()
    tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.018
    def col(i, j):
        # 断面の 6 面：外の真ん中（j=1）は明るい段、外の両わき（0, 2）は中の段、頭を向く側（3〜5）と根元は暗い段。
        # 房の縁に暗い線ができ、重なった葉が 1 枚ずつ読める（絵の房の稜線と影）
        if i == 0 or j >= 3:
            return 'umber_dk'
        return 'umber_lt' if j == 1 else 'umber'
    return tube(pts, radii, n=6, col=col, up=up, sq=1.35, tips=(None, tip))


def hair_regions():
    """地域ごとの房の Part を返す：{骨の名前: Part}。
    groom-flow-regions の順（生え際・前髪 → 頭頂 → 横 → 後ろ・えり足）に、流れの向き・房の数・長さを決める。
    絵の髪は大きい葉の形の房が瓦のように重なる。真上の絵ではつむじから風車のように放射し、頭の丸みに沿って
    流れて先が外へはねる。房の数を絞って大きく（Clumps：束で読ませる、細い毛を足さない）"""
    R = {}

    def add(bone, part):
        R.setdefault(bone, Part()).extend(part)

    # 1 段目（頭頂の風車）：つむじから放射、先は横・後ろへはねる
    for k in range(9):
        a_deg = -160 + 40 * k
        if abs(a_deg) < 25:
            continue                        # 正面はゴーグルと前髪
        a = math.radians(a_deg)
        reg = 'hair.top' if abs(a_deg) > 60 else 'hair.front'
        add(reg, leaf(a, 1.478, 1.365, math.radians(16), 0.082, 0.010, 0.085, 0.040))
    # 頭頂の立つ房（上の輪郭のとがり）
    for a_deg, ln, up_k, wd in ((10, 0.162, 1.45, 0.066), (-25, 0.110, 1.0, 0.060), (170, 0.115, 0.8, 0.070), (-140, 0.100, 0.7, 0.064)):
        a = math.radians(a_deg)
        o = _o(a)
        root = CROWN + o * 0.015 + Vector((0, 0, -0.016))
        dirs = [o * 0.45 + Vector((0, 0, up_k)), o + Vector((0, 0, up_k * 0.45)), o * 1.0 + Vector((0, 0, -0.10))]
        add('hair.top', tuft(root, dirs, ln, wd, 0.030))
    # 2 段目：耳の上・後頭部。耳のあたり（|a| 70〜115）は短く
    for k in range(11):
        a_deg = -180 + 18 + 360 * k / 11
        a_deg = ((a_deg + 180) % 360) - 180
        if abs(a_deg) < 48:
            continue
        a = math.radians(a_deg)
        near_face = abs(a_deg) < 118      # 目・耳より前（真横の絵で、目と耳の上で止まる）
        z1 = 1.340 if near_face else 1.265
        add(_region(a_deg, 1.40), leaf(a, 1.420, z1, math.radians(8), 0.080, 0.008, 0.070 if not abs(a_deg) > 130 else 0.040, 0.038))
    # 3 段目：後ろ・えり足（下へ短く、えりに沿う）
    for k in range(12):
        a_deg = 180 - 30 * k
        a_deg = ((a_deg + 180) % 360) - 180
        if abs(a_deg) < 100:
            continue
        a = math.radians(a_deg)
        add('hair.nape' if abs(a_deg) > 125 else _region(a_deg, 1.30), leaf(a, 1.330, 1.228, 0.0, 0.074, 0.006, 0.026, 0.032))
    for a_deg in (-125, 125, -150, 150, 180):
        a = math.radians(a_deg)
        add(_region(a_deg, 1.36), leaf(a + math.radians(12), 1.370, 1.262, 0.0, 0.074, 0.010, 0.036, 0.034))
    # 横へ張り出す房（正面の絵で、ゴーグルの高さの髪の幅 ±0.185 m）
    for side in (1, -1):
        for a_deg, z0, ln, dn in ((78, 1.440, 0.105, 0.30), (100, 1.430, 0.105, 0.42), (120, 1.425, 0.100, 0.50)):
            a = math.radians(a_deg * side)
            o = _o(a)
            root = head_point(a, z0, 0.004)
            dirs = [(o + Vector((0, 0, 0.10))), (o + Vector((0, 0, -dn))), (o + Vector((0, 0, -dn * 1.4)))]
            add('hair.side.' + ('L' if side > 0 else 'R'), tuft(root, dirs, ln, 0.066, 0.028))
    # 前髪：額の上（ゴーグルの下）から前・下へ。真ん中が目の間まで下りる
    for a_deg, z0, ln, wd in ((0, 1.440, 0.170, 0.056), (-19, 1.436, 0.145, 0.054), (19, 1.436, 0.145, 0.054),
                              (-37, 1.425, 0.135, 0.052), (37, 1.425, 0.135, 0.052)):
        a = math.radians(a_deg)
        o = _o(a)
        root = head_point(a, z0, 0.004)
        dirs = [(o * 1.0 + Vector((0, 0, -0.15))), (o * 0.45 + Vector((0, 0, -1.0))), (o * 0.20 + Vector((0, 0, -1.0)))]
        add('hair.front', tuft(root, dirs, ln, wd, 0.024, twist_up=o))
    # 顔の横の房（耳の前へ下りる）
    for side in (1, -1):
        for a_deg, z0, ln in ((74, 1.400, 0.150), (84, 1.395, 0.135)):
            a = math.radians(a_deg * side)
            o = _o(a)
            root = head_point(a, z0, 0.004)
            dirs = [(o * 0.9 + Vector((0, 0, -0.2))), (o * 0.35 + Vector((0, 0, -1.0))), (o * 0.45 + Vector((0, 0, -1.0)))]
            add('hair.side.' + ('L' if side > 0 else 'R'), tuft(root, dirs, ln * 0.85, 0.040, 0.022, twist_up=o))
    return R
