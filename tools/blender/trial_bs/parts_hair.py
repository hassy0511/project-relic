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

CROWN = Vector((0.0, -0.015, 1.478))    # 頭頂のつむじ（真上の絵で、房が放射状に出る中心。後ろ寄り）


def cap():
    """髪の地肌の殻：頭の面から 1 cm 外。顔の側は生え際で開く"""
    N = 24
    K = 7

    def rim(a):
        # 生え際の高さ：正面（額）1.385、こめかみ 1.32、耳の上 1.30、後ろ 1.235
        c = math.cos(a)
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
    up = twist_up if twist_up is not None else Vector((0, 0, 1))
    tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * seg * 0.45
    return tube(pts, radii, n=n, col='umber', up=up, sq=1.35, tips=(None, tip))


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


def hair_regions():
    """地域ごとの房の Part を返す：{骨の名前: Part}。
    groom-flow-regions の順（生え際・前髪 → 頭頂 → 横 → 後ろ・えり足）に、流れの向き・房の数・長さを決める。
    絵の髪は太い葉の形の房が瓦のように重なる：根元は頭の丸みに沿って下へ流れ、先が外へはねる。
    頭頂のつむじ（後ろ寄り）からは上・後ろへ立つ房が数本"""
    R = {}

    def add(bone, part):
        R.setdefault(bone, Part()).extend(part)

    # 頭頂：上・後ろへ立つ房（頭の上の輪郭のとがり）
    for a_deg, ln, up_k, wd in ((170, 0.125, 0.8, 0.072), (-145, 0.115, 0.7, 0.068), (135, 0.110, 0.6, 0.066),
                                (10, 0.135, 1.30, 0.064), (-25, 0.115, 1.0, 0.060), (35, 0.110, 0.9, 0.060), (90, 0.110, 0.55, 0.064), (-95, 0.110, 0.55, 0.064)):
        a = math.radians(a_deg)
        o = _o(a)
        root = CROWN + o * 0.015 + Vector((0, 0, -0.016))
        dirs = [o * 0.45 + Vector((0, 0, up_k)), o + Vector((0, 0, up_k * 0.45)), o * 1.0 + Vector((0, 0, -0.10))]
        add('hair.top', tuft(root, dirs, ln, wd, 0.030, twist_up=Vector((0, 0, 1))))
    # 横へ張り出す房（正面の絵で、ゴーグルの高さの髪の幅 ±0.185 m）
    for side in (1, -1):
        for a_deg, z0, ln, dn in ((78, 1.440, 0.105, 0.30), (100, 1.430, 0.105, 0.42), (120, 1.425, 0.100, 0.50)):
            a = math.radians(a_deg * side)
            o = _o(a)
            root = head_point(a, z0, 0.004)
            dirs = [(o + Vector((0, 0, 0.10))), (o + Vector((0, 0, -dn))), (o + Vector((0, 0, -dn * 1.4)))]
            add('hair.side.' + ('L' if side > 0 else 'R'), tuft(root, dirs, ln, 0.064, 0.028, twist_up=o))
    # 重なる段：根元の高さ・数・ずらし（度）・長さ・幅・先のはね・前を空ける角度（前髪の所）
    rows = [
        (1.452, 9, 20, 0.130, 0.068, 0.70, 34),
        (1.412, 12, 0, 0.140, 0.070, 0.75, 42),
        (1.368, 14, 13, 0.140, 0.068, 0.90, 54),
        (1.322, 12, 0, 0.122, 0.064, 0.60, 100),
        (1.280, 10, 16, 0.085, 0.060, 0.30, 112),
        (1.245, 8, 0, 0.065, 0.056, 0.10, 122),
    ]
    for z0, cnt, off, ln, wd, flick, skip in rows:
        for j in range(cnt):
            a_deg = -180 + off + 360 * j / cnt
            a_deg = ((a_deg + 180) % 360) - 180
            if abs(a_deg) < skip:
                continue
            a = math.radians(a_deg)
            o = _o(a)
            root = head_point(a, z0, 0.004)
            t0 = _down_tangent(a, z0)
            t1 = _down_tangent(a, z0 - ln * 0.5)
            d0 = (t0 + o * 0.25).normalized()
            fk = flick * (0.35 if abs(a_deg) > 125 else 1.0)  # 後ろは外へはねすぎない（真横の絵の後頭部の輪郭）
            d1 = (t1 + o * fk * 0.6).normalized()
            d2 = (t1 + o * fk * 1.4).normalized()        # 先が外へはねる
            add(_region(a_deg, z0), tuft(root, [d0, d1, d2], ln, wd, 0.030, twist_up=o))
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
        for a_deg, z0, ln in ((56, 1.405, 0.170), (72, 1.395, 0.160)):
            a = math.radians(a_deg * side)
            o = _o(a)
            root = head_point(a, z0, 0.004)
            dirs = [(o * 0.9 + Vector((0, 0, -0.2))), (o * 0.35 + Vector((0, 0, -1.0))), (o * 0.45 + Vector((0, 0, -1.0)))]
            add('hair.side.' + ('L' if side > 0 else 'R'), tuft(root, dirs, ln, 0.052, 0.024, twist_up=o))
    return R
