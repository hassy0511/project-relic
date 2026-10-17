"""W2-05b 市場のにぎわいの小物（16 点。origin/art/w2-town の town_goods*・spec_town_goods.md）。

作り方は model-from-art の 2.2（機械・小物）：絵に格子を重ねて測る代わりに、spec の寸法表（m）から単純な形で直接組み、
部品ごとに平らな 1 色（town_geo.MATERIALS。spec の色見本の hex）。陰は焼かない。編み目・布の柄・作物の細部は形にせず、
大きな面と、色の帯・面から 1.5 cm 浮かせた平らな色の板（柄）で表す。段差は少なく、三角形は 1 点で数百まで。
真鍮の角の金具は「硬い売り物」（区切り箱・帳場台・かめの帯・ジャンクの陳列箱・看板・机・旗竿・鉢）だけに付け、
柔らかい物（かご・麻袋・布・玩具）には付けない（絵では付いているが、ユーザーの見直し：使いすぎ）。
上面図の吊り布・看板・旗は正面図と同じ描き方になっているので、奥行きは寸法表の値で作る。

座標・原点は town_parts と同じ（X 右、Y 上、Z 手前 = 正面、原点は底の中心）。壁に付く物は壁の面。

部品（godot/assets/kit/town/<名前>.glb）
  1 つずつの小物（確認ページ・ほかの部屋で使う）：goods_basket・goods_basket_s・goods_sacks・goods_jar・goods_cloth・goods_cloth_wall・
    goods_roll・goods_bins・goods_scale・goods_hanging・junk_goods・sign_hang・sign_round・sign_stand・sign_cloth・seat_small・seat_mat・
    pot_succulent・pot_shrub・pot_vine・diner_table・diner_set_2・diner_set_4・toy_banki・laundry_basket・wind_flag・laundry_goods・laundry_goods_8
  露店の組（描画の数を増やさないため 1 つの部品にまとめる）：market_general・market_junk（台の上の品・前の梁の吊り物と看板・台の前の床の品）
"""
from __future__ import annotations

import math

import numpy as np

import town_parts as P
from town_geo import Part, Piece, _orient, beam, boxb, cyl, lathe, sag, sheet, tube

V = np.array
EPS = 0.015          # 柄の板を面から浮かせる距離（ちらつき防止。check_coplanar の 1.5 cm と同じ）


# ---------------------------------------------------------------- 共通の形

def ov(prof, y0, y1, c=(0.0, 0.0), r=(1.0, 1.0), segs=8, cap=True, yaw=0.0) -> Piece:
    """縦の軸の回転体（輪郭の半径は 1 で書き、r で x・z の半径に伸ばす）。8 角なら角の丸い四角に近い"""
    pc = lathe((0, y0, 0), (0, y1, 0), prof, segs, cap)
    return pc.moved((c[0], 0, c[1]), yaw, (r[0], 1, r[1]))


def ball(c, r, segs=6, squash=1.0) -> Piece:
    """小さな粒（実・玉）：上下のとがった 6 角の玉"""
    x, y, z = c
    return lathe((x, y - r * squash, z), (x, y + r * squash, z), [(0, 1e-4), (0.3, r * 0.9), (0.7, r * 0.9), (1, 1e-4)], segs, cap=False)


def flat_box(c, size, yaw=0.0) -> Piece:
    """中心 c・大きさ size の箱を yaw 度回す（ゲームの yaw）"""
    h = np.asarray(size, float) / 2
    v = V([[sx * h[0], sy * h[1], sz * h[2]] for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)])
    f = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return _orient(Piece(v, f)).moved(c, yaw)


def tilt_x(pc: Piece, deg: float) -> Piece:
    """原点のまわりに X 軸で傾ける（+ で上の端が手前 +Z へ）"""
    a = math.radians(deg)
    v = pc.v.copy()
    y, z = v[:, 1].copy(), v[:, 2].copy()
    v[:, 1], v[:, 2] = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
    return Piece(v, pc.f, sm=pc.sm)


def caps(p: Part, x0, x1, y0, y1, z0, z1, s=0.07):
    """硬い売り物の角の真鍮の金具（上の 4 隅だけ。下の隅は付けない：使いすぎない）"""
    for x in (x0, x1):
        for z in (z0, z1):
            xa, xb = (x - 0.01, x + s - 0.01) if x == x0 else (x - s + 0.01, x + 0.01)
            za, zb = (z - 0.01, z + s - 0.01) if z == z0 else (z - s + 0.01, z + 0.01)
            p.add('brass', boxb(xa, xb, y1 - s, y1 + 0.01, za, zb))


# ---------------------------------------------------------------- 01 かご（作物）

def basket(p: Part, c=(0.0, 0.0), w=1.0, d=1.0, h=0.5, y=0.0, crop='crop_red', handles=True, grains=6, seed=1, leaves=False):
    """角の丸い四角のかご（8 角の筒、下が少し細い）。編み目は色の帯 2 本、縁は綱の色。上に作物の山と粒。真鍮なし（柔らかい物）"""
    rx, rz = w / 2, d / 2
    p.add('wicker', ov([(0, 0.84), (1, 1.0)], y, y + h, c, (rx, rz)))
    for t in (0.33, 0.66):
        rr = 0.84 + 0.16 * t + 0.02
        p.add('rope', ov([(0, rr), (1, rr)], y + h * t - 0.022, y + h * t + 0.022, c, (rx, rz), cap=False))
    p.add('rope', ov([(0, 1.05), (1, 1.05)], y + h - 0.045, y + h + 0.01, c, (rx, rz)))
    top = y + h
    hh = 0.03 + 0.07 * min(w, d)
    if crop:
        # 作物の低い山（かごの縁の少し上まで）と、山の面に半分出た大きめの粒（実の形は粒で読む）
        p.add(crop, ov([(0, 0.95), (0.6, 0.7), (1, 0.15)], top - 0.03, top + hh, c, (rx, rz)))
        rng = np.random.default_rng(seed)
        gr = 0.05 + 0.06 * min(w, d)
        for k in range(grains):
            a = 2 * math.pi * k / grains + rng.uniform(-0.3, 0.3)
            rr = 0.55 if k % 2 else 0.25
            gx, gz = c[0] + math.cos(a) * rx * rr, c[1] + math.sin(a) * rz * rr
            gy = top + hh * (1 - rr) + gr * 0.35
            p.add(crop, ball((gx, gy, gz), gr))
        if leaves:
            for k in range(2):
                a = 0.6 + k * 2.5
                p.add('crop_green', flat_box((c[0] + math.cos(a) * rx * 0.5, top + hh * 0.8, c[1] + math.sin(a) * rz * 0.5),
                                             (0.16 * w, 0.02, 0.07 * w), math.degrees(a)))
    if handles:
        for sx in (-1, 1):
            xe = c[0] + sx * rx * 0.98
            pts = [(xe, top - 0.02, c[1] - rz * 0.3), (xe + sx * 0.04, top + 0.1 * h / 0.5, c[1] - rz * 0.15),
                   (xe + sx * 0.04, top + 0.1 * h / 0.5, c[1] + rz * 0.15), (xe, top - 0.02, c[1] + rz * 0.3)]
            p.add('rope', tube(pts, 0.022 * max(0.6, min(w, d)), 5))


def goods_basket() -> Part:
    """01 大かご 1×1×0.5（赤い実と葉）"""
    p = Part('goods_basket')
    basket(p, (0, 0), 0.95, 0.95, 0.45, crop='crop_red', grains=8, leaves=True)
    return p


def goods_basket_s() -> Part:
    """01 小かご 0.5（根菜・乾燥果実を差し替え）：3 つ並べた組（0.5 m 升目 2 つ分）"""
    p = Part('goods_basket_s')
    basket(p, (-0.26, 0.0), 0.46, 0.46, 0.32, crop='crop_yellow', seed=2)
    basket(p, (0.26, 0.05), 0.46, 0.46, 0.3, crop='crop_red', seed=3, grains=5)
    basket(p, (0.0, -0.4), 0.44, 0.4, 0.26, crop='wood2', seed=4, grains=4, handles=False)
    return p


# ---------------------------------------------------------------- 02 麻袋

SACK_CLOSED = [(0.0, 0.68), (0.14, 0.95), (0.5, 1.0), (0.78, 0.86), (0.9, 0.5), (1.0, 0.22)]
SACK_OPEN = [(0.0, 0.72), (0.16, 0.97), (0.7, 1.0), (0.84, 1.08), (1.0, 1.04)]


def sack(p: Part, c, rx, rz, h, y=0.0, yaw=0.0, kind='closed', tie='rope', mat='burlap', fill='crop_yellow'):
    """立てた袋：閉じた袋（口を紐で縛る。tie='cloth' は赤い布の口）／開いた袋（縁を折り返し、中の豆）"""
    if kind == 'open':
        p.add(mat, ov(SACK_OPEN, y, y + h, c, (rx, rz), yaw=yaw))
        p.add(fill, ov([(0, 0.98), (1, 0.4)], y + h * 0.96, y + h * 1.06, c, (rx, rz), yaw=yaw))
        return
    p.add(mat, ov(SACK_CLOSED, y, y + h, c, (rx, rz), yaw=yaw))
    k = min(rx, rz)
    p.add(tie, ov([(0, 0.32), (1, 0.32)], y + h * 0.84, y + h * 0.9, c, (k, k), 6, cap=False))
    if tie == 'cloth':
        p.add('cloth', ov([(0, 0.25), (0.4, 0.55), (1, 0.15)], y + h * 0.88, y + h * 1.12, c, (k, k), 6))
    else:
        p.add(mat, ov([(0, 0.2), (0.5, 0.42), (1, 0.12)], y + h * 0.88, y + h * 1.1, c, (k, k), 6))


def sack_lying(p: Part, c, L, r, y=0.0, yaw=0.0, mat='burlap'):
    """寝かせた袋（横の軸の回転体を上下に 0.7 につぶす）"""
    pc = lathe((-L / 2, 0, 0), (L / 2, 0, 0), [(t, r * k) for t, k in SACK_CLOSED], 8)
    p.add(mat, pc.moved((c[0], y + r * 0.7, c[1]), yaw, (1, 0.72, 1)))


def goods_sacks() -> Part:
    """02 麻袋の山（麻袋の仮の部品 town/sacks と同じ置き場所・同じ広さ 1.2×0.9）：閉じた袋（赤い口）・開いた豆の袋と匙・灰色の袋・寝かせた袋。
    原点は底の中心。当たり判定は dress_solid の town/goods_sacks"""
    p = Part('goods_sacks')
    sack(p, (-0.32, -0.12), 0.26, 0.24, 0.82, tie='cloth')
    sack(p, (0.3, -0.16), 0.27, 0.25, 0.62, kind='open')
    p.add('brass', beam((0.36, 0.6, -0.12), (0.5, 0.78, 0.02), 0.04, 0.012), ov([(0, 0.6), (1, 1.0)], 0.6, 0.66, (0.35, -0.13), (0.06, 0.05), 6))
    sack(p, (0.05, -0.3), 0.22, 0.2, 0.7, mat='slate', yaw=20)
    sack_lying(p, (-0.05, 0.22), 0.9, 0.22, yaw=-6)
    return p


# ---------------------------------------------------------------- 03 かめ

JAR = [(0, 0.55), (0.08, 0.78), (0.42, 1.0), (0.74, 0.8), (0.86, 0.46), (0.94, 0.42), (1.0, 0.5)]


def _jar_r(t):
    for (t0, r0), (t1, r1) in zip(JAR, JAR[1:]):
        if t0 <= t <= t1:
            return r0 + (r1 - r0) * (t - t0) / max(t1 - t0, 1e-6)
    return JAR[-1][1]


def jar(p: Part, c, r, h, y=0.0, body='cloth', band='linen', lid='brass', stand=True, straps=True, segs=10):
    """かめ：赤い胴（cloth）と生成りの帯、真鍮の揺れ止めの帯（硬い物なので真鍮）。stand：黒鉛の四角い台と真鍮の留め"""
    y0 = y
    if stand:
        s = r * 0.85
        p.add('graphite', boxb(c[0] - s, c[0] + s, y, y + 0.06, c[1] - s, c[1] + s))
        y0 = y + 0.06
    p.add(body, ov(JAR, y0, y0 + h, c, (r, r), segs))
    # 帯（胴の太い所）：生成りの帯と真ん中の赤い線（柄は色で）
    t0, t1 = 0.32, 0.52
    rb = max(_jar_r(t0), _jar_r(t1)) * r + 0.012
    p.add(band, lathe((c[0], y0 + h * t0, c[1]), (c[0], y0 + h * t1, c[1]), [(0, rb), (1, rb)], segs, cap=False))
    p.add(body, lathe((c[0], y0 + h * 0.405, c[1]), (c[0], y0 + h * 0.435, c[1]), [(0, rb + 0.01), (1, rb + 0.01)], segs, cap=False))
    if lid:
        p.add(lid, ov([(0, 0.52), (0.5, 0.45), (1, 0.12)], y0 + h, y0 + h + 0.09 * h / 1.0 + 0.03, c, (r, r), segs))
        p.add(lid, ball((c[0], y0 + h + 0.1 * h + 0.05, c[1]), 0.035 + 0.02 * r))
    if straps:
        ts = [0.1, 0.3, 0.42, 0.6, 0.78]
        for a in (0.0, math.pi):
            pts = [(c[0] + math.cos(a) * (_jar_r(t) * r + 0.012), y0 + h * t, c[1] + math.sin(a) * (_jar_r(t) * r + 0.012)) for t in ts]
            p.add('brass', tube(pts, 0.018, 4))
        p.add('brass', lathe((c[0], y0 + h * 0.76, c[1]), (c[0], y0 + h * 0.8, c[1]), [(0, _jar_r(0.78) * r + 0.016)] * 2, segs, cap=False))


def bowl(p: Part, c, r, y=0.0, mat='cloth', food=None):
    p.add(mat, ov([(0, 0.55), (1, 1.0)], y, y + r * 0.6, c, (r, r), 8))
    if food:
        p.add(food, ov([(0, 0.92), (1, 0.4)], y + r * 0.5, y + r * 0.72, c, (r, r), 8))


def goods_jar() -> Part:
    """03 大がめ 1×1×1.5（蓋・台座・真鍮の帯）と小壺 0.5・灰色のかめ・鉢"""
    p = Part('goods_jar')
    jar(p, (-0.25, 0.0), 0.48, 1.28)
    jar(p, (0.52, 0.12), 0.18, 0.4, body='cloth', stand=False, straps=False, lid=None)
    jar(p, (0.62, -0.32), 0.3, 0.55, body='slate', band='slate', stand=True, straps=False, lid='brass')
    bowl(p, (0.95, 0.2), 0.16)
    return p


# ---------------------------------------------------------------- 04 吊り布

def cloth_panel(p: Part, x0, x1, ytop, L, z, kind='a', fringe=False, t=0.02):
    """平らな布 1 枚（厚さ 2 cm）と柄（面から 1.5 cm 前の色の板。表だけ）。
    a：赤地に生成りの山形と下の帯、b：生成り地に灰色の帯と赤い 2 本の印（房つき）"""
    w = x1 - x0
    yb = ytop - L
    zf = z + t / 2 + EPS / 2
    if kind == 'a':
        p.add('cloth', boxb(x0, x1, yb, ytop, z - t / 2, z + t / 2))
        xm = (x0 + x1) / 2
        yp = ytop - L * 0.3
        for xs in (x0 + w * 0.12, x1 - w * 0.12):
            p.add('linen', beam((xs, ytop - L * 0.62, zf), (xm, yp, zf), w * 0.13, 0.008, up=(0, 0, 1)))
        p.add('linen', boxb(x0, x1, yb + L * 0.1, yb + L * 0.2, zf - 0.004, zf + 0.004))
        p.add('slate', boxb(x0, x1, yb + L * 0.03, yb + L * 0.075, zf - 0.004, zf + 0.004))
    else:
        p.add('linen', boxb(x0, x1, yb, ytop, z - t / 2, z + t / 2))
        p.add('slate', boxb(x0, x1, ytop - L * 0.42, ytop - L * 0.3, zf - 0.004, zf + 0.004))
        for k in range(2):
            xa = x0 + w * (0.18 + 0.14 * k)
            p.add('cloth', beam((xa, ytop - L * 0.78, zf), (xa + w * 0.08, ytop - L * 0.55, zf), w * 0.07, 0.008, up=(0, 0, 1)))
    if fringe:
        n = max(3, int(w / 0.14))
        for k in range(n):
            xx = x0 + w * (k + 0.5) / n
            p.add('rope', boxb(xx - 0.02, xx + 0.02, yb - 0.1, yb, z - 0.012, z + 0.012))


def goods_cloth() -> Part:
    """04 吊り布の枠 2×0.5×2：黒鉛の柱 2 本と上の棒に、赤い布と生成りの布（房つき）"""
    p = Part('goods_cloth')
    for x in (-1.0, 1.0):
        p.add('graphite', boxb(x - 0.05, x + 0.05, 0, 2.0, -0.05, 0.05), boxb(x - 0.14, x + 0.14, 0, 0.05, -0.2, 0.2))
        p.add('brass', boxb(x - 0.065, x + 0.065, 1.94, 2.04, -0.065, 0.065))
    p.add('graphite', cyl((-1.0, 1.9, 0), (1.0, 1.9, 0), 0.03, 6, cap=False))
    cloth_panel(p, -0.9, -0.08, 1.88, 1.25, 0.0, 'a')
    cloth_panel(p, 0.06, 0.88, 1.88, 1.1, 0.0, 'b', fringe=True)
    for x in (-0.86, -0.12, 0.1, 0.84):
        p.add('rope', cyl((x, 1.86, 0), (x, 1.95, 0), 0.035, 5))
    return p


def goods_cloth_wall() -> Part:
    """04 の壁掛け（壁の垂れ幕 town/banner の差し替え。同じ置き場所）：原点 = 壁の面・棒の高さの中心。壁から 0.08 m まで
    （壁から 0.15 m 以内の薄い物なので当たり判定なし）。赤い布 0.9×1.6 と山形・下の帯、黒鉛の棒と留め金"""
    p = Part('goods_cloth_wall')
    p.add('graphite', cyl((-0.52, 0, 0.05), (0.52, 0, 0.05), 0.022, 6))
    for x in (-0.5, 0.5):
        p.add('graphite', boxb(x - 0.03, x + 0.03, -0.05, 0.05, 0.0, 0.05))
    cloth_panel(p, -0.45, 0.45, -0.03, 1.6, 0.05, 'a', t=0.015)
    for x in (-0.38, 0.0, 0.38):
        p.add('rope', cyl((x, -0.06, 0.05), (x, 0.03, 0.05), 0.03, 5))
    return p


# ---------------------------------------------------------------- 05 布巻き

def roll(p: Part, a, b, r, mat, band=None, bands=(0.25, 0.75)):
    p.add(mat, cyl(a, b, r, 8))
    if band:
        a, b = np.asarray(a, float), np.asarray(b, float)
        for t in bands:
            m = a + (b - a) * t
            d = (b - a) / np.linalg.norm(b - a)
            p.add(band, cyl(m - d * 0.035, m + d * 0.035, r + 0.008, 8, cap=False))


def folded(p: Part, c, w, d, y, colors, th=0.08, stripe=True):
    """畳んだ布の積み重ね：平らな板を色を替えて重ね、前の面に別の色の筋（柄は色で）"""
    for k, (mat, st) in enumerate(colors):
        y0 = y + k * th
        sh = 0.02 * (1 if k % 2 else -1)
        p.add(mat, boxb(c[0] - w / 2 + sh, c[0] + w / 2 + sh, y0 + 0.003, y0 + th, c[1] - d / 2, c[1] + d / 2))
        if stripe and st:
            p.add(st, boxb(c[0] - w / 2 + sh + 0.06, c[0] + w / 2 + sh - 0.06, y0 + th * 0.35, y0 + th * 0.65, c[1] + d / 2, c[1] + d / 2 + 0.012))


def goods_roll() -> Part:
    """05 布巻きの立て束 1×0.5×1.5（黒鉛の枠）と横積み 1×1×0.5（低い木の台の上に畳んだ布）"""
    p = Part('goods_roll')
    # 立て束：枠（柱 2 本・下の板・上の横木）と布巻き 4 本
    for x in (-1.0, -0.12):
        p.add('graphite', boxb(x - 0.04, x + 0.04, 0, 1.45, -0.22, -0.14))
    p.add('wood', boxb(-1.04, -0.08, 0, 0.08, -0.25, 0.2))
    p.add('graphite', boxb(-1.04, -0.08, 1.1, 1.16, -0.24, -0.14))
    for k, (mat, band, ht) in enumerate((('slate', 'linen', 1.4), ('linen', 'cloth', 1.3), ('cloth', 'linen', 1.45), ('slate', 'cloth', 1.25))):
        x = -0.88 + k * 0.22
        roll(p, (x, 0.08, 0.0), (x, ht, 0.0), 0.1, mat, band, (0.2, 0.62))
    # 横積み：低い木の台と畳んだ布 5 枚
    p.add('wood', boxb(0.05, 1.0, 0, 0.16, -0.42, 0.42))
    p.add('graphite', boxb(0.05, 1.0, 0.16, 0.19, -0.42, 0.42))
    folded(p, (0.53, 0.0), 0.86, 0.7, 0.19, [('linen', 'cloth'), ('cloth', 'linen'), ('slate', 'linen'), ('cloth', 'slate'), ('linen', 'slate')], 0.07)
    return p


# ---------------------------------------------------------------- 06 区切り箱

SPICES = ('crop_red', 'crop_yellow', 'crop_green', 'cloth2', 'wood2', 'linen')


def bins(p: Part, c=(0.0, 0.0), w=2.0, d=1.0, h=0.5, y=0.0, cols=3, rows=2, legs=True, scoop=True, brass=True):
    """06 区切り箱：木の枠と仕切り、区画ごとに香辛料・木の実・乾物の山（色で読む）、真鍮の匙"""
    x0, x1 = c[0] - w / 2, c[0] + w / 2
    z0, z1 = c[1] - d / 2, c[1] + d / 2
    yb = y + (0.08 if legs else 0.0)
    t = 0.05
    if legs:
        for x in (x0 + 0.06, x1 - 0.06):
            for z in (z0 + 0.06, z1 - 0.06):
                p.add('graphite', boxb(x - 0.04, x + 0.04, y, yb, z - 0.04, z + 0.04))
    p.add('wood', boxb(x0, x1, yb, yb + 0.05, z0, z1))
    top = y + h
    p.add('wood', boxb(x0, x1, yb, top, z1 - t, z1), boxb(x0, x1, yb, top, z0, z0 + t),
          boxb(x0, x0 + t, yb, top, z0 + t, z1 - t), boxb(x1 - t, x1, yb, top, z0 + t, z1 - t))
    p.add('graphite', boxb(x0 - 0.005, x1 + 0.005, top - 0.05, top - 0.02, z1, z1 + 0.012))
    for k in range(1, cols):
        x = x0 + w * k / cols
        p.add('wood', boxb(x - 0.02, x + 0.02, yb, top - 0.04, z0 + t, z1 - t))
    for k in range(1, rows):
        z = z0 + d * k / rows
        p.add('wood', boxb(x0 + t, x1 - t, yb, top - 0.04, z - 0.02, z + 0.02))
    cw, cd = (w - 2 * t) / cols, (d - 2 * t) / rows
    k = 0
    for j in range(rows):
        for i in range(cols):
            cx = x0 + t + cw * (i + 0.5)
            cz = z0 + t + cd * (j + 0.5)
            mat = SPICES[k % len(SPICES)]
            p.add(mat, ov([(0, 0.72), (0.6, 0.52), (1, 0.12)], top - 0.12, top + 0.04 + 0.03 * (k % 2), (cx, cz),
                          (cw * 0.62, cd * 0.62), 4, yaw=45))
            k += 1
    if scoop:
        p.add('brass', beam((x1 - cw * 0.5, top + 0.04, z0 + cd * 0.4), (x1 - cw * 0.1, top + 0.14, z0 + cd * 0.1), 0.035, 0.012))
        p.add('brass', ov([(0, 0.6), (1, 1.0)], top + 0.0, top + 0.06, (x1 - cw * 0.55, z0 + cd * 0.45), (0.07, 0.06), 6))
    if brass:
        caps(p, x0, x1, yb, top, z0, z1, 0.06)


def goods_bins() -> Part:
    """06 区切り箱 2×1×0.5（露店台の天板の上）"""
    p = Part('goods_bins')
    bins(p)
    return p


# ---------------------------------------------------------------- 07 天秤と帳場台

def balance(p: Part, c=(0.0, 0.0), y=0.0, s=1.0):
    """07 天秤（真鍮）：台・柱・竿・皿 2 枚と吊り紐（同じ重さで水平）"""
    x, z = c
    p.add('brass', ov([(0, 1.0), (0.6, 0.85), (1, 0.4)], y, y + 0.07 * s, c, (0.14 * s, 0.11 * s), 8))
    p.add('brass', cyl((x, y + 0.06 * s, z), (x, y + 0.62 * s, z), 0.022 * s, 6))
    p.add('brass', ball((x, y + 0.66 * s, z), 0.04 * s))
    arm = 0.3 * s
    p.add('brass', boxb(x - arm, x + arm, y + 0.6 * s, y + 0.63 * s, z - 0.012 * s, z + 0.012 * s))
    for sx in (-1, 1):
        px = x + sx * arm
        pan_y = y + 0.32 * s
        p.add('brass', ov([(0, 0.35), (1, 1.0)], pan_y, pan_y + 0.04 * s, (px, z), (0.11 * s, 0.11 * s), 8))
        for k in range(3):
            a = math.pi / 2 + k * 2 * math.pi / 3
            p.add('graphite', beam((px, y + 0.6 * s, z), (px + math.cos(a) * 0.09 * s, pan_y + 0.04 * s, z + math.sin(a) * 0.09 * s), 0.006 * s))


def counter(p: Part, c=(0.0, 0.0), w=2.0, d=1.0, h=1.0, y=0.0, runner=True):
    """07 帳場台 2×1×1（露店台と取り替えられる）：木の天板と前板、黒鉛の脚、赤い掛け布（生成りの 2 本の筋）、真鍮の角"""
    x0, x1, z0, z1 = c[0] - w / 2, c[0] + w / 2, c[1] - d / 2, c[1] + d / 2
    for x in (x0 + 0.08, x1 - 0.08):
        for z in (z0 + 0.08, z1 - 0.08):
            p.add('graphite', boxb(x - 0.06, x + 0.06, y, y + h - 0.08, z - 0.06, z + 0.06))
    p.add('wood', boxb(x0, x1, y + h - 0.08, y + h, z0, z1))
    p.add('wood2', boxb(x0 + 0.1, x1 - 0.1, y + 0.25, y + h - 0.08, z1 - 0.14, z1 - 0.1))
    p.add('graphite', boxb(x0 + 0.06, x1 - 0.06, y + 0.12, y + 0.18, z0 + 0.1, z1 - 0.1))
    if runner:
        rw = w * 0.32
        p.add('cloth', boxb(c[0] - rw / 2, c[0] + rw / 2, y + h, y + h + 0.015, z0 - 0.01, z1 + 0.012),
              boxb(c[0] - rw / 2, c[0] + rw / 2, y + h * 0.45, y + h + 0.015, z1 + 0.0, z1 + 0.012))
        for sx in (-1, 1):
            xs = c[0] + sx * rw * 0.32
            p.add('linen', boxb(xs - 0.025, xs + 0.025, y + h * 0.45, y + h + 0.002, z1 + 0.012, z1 + 0.024))
    caps(p, x0, x1, y + h - 0.08, y + h, z0, z1, 0.08)


def ledger(p: Part, c, y, yaw=0.0):
    p.add('wood', flat_box((c[0], y + 0.03, c[1]), (0.42, 0.06, 0.32), yaw))
    p.add('linen', flat_box((c[0], y + 0.03, c[1]), (0.4, 0.045, 0.335), yaw))


def coin_box(p: Part, c, y, s=0.4):
    """小銭箱（区切りの木の箱、中に真鍮と灰色の粒）"""
    x0, x1, z0, z1 = c[0] - s / 2, c[0] + s / 2, c[1] - s * 0.35, c[1] + s * 0.35
    p.add('wood', boxb(x0, x1, y, y + 0.03, z0, z1), boxb(x0, x1, y, y + 0.13, z1 - 0.03, z1), boxb(x0, x1, y, y + 0.13, z0, z0 + 0.03),
          boxb(x0, x0 + 0.03, y, y + 0.13, z0, z1), boxb(x1 - 0.03, x1, y, y + 0.13, z0, z1), boxb(c[0] - 0.015, c[0] + 0.015, y, y + 0.11, z0, z1))
    p.add('brass', boxb(x0 + 0.04, c[0] - 0.03, y + 0.03, y + 0.08, z0 + 0.04, z1 - 0.04))
    p.add('slate', boxb(c[0] + 0.03, x1 - 0.04, y + 0.03, y + 0.07, z0 + 0.04, z1 - 0.04))


def goods_scale() -> Part:
    """07 天秤 1×0.5×1・帳場台 2×1×1・帳簿・小銭箱"""
    p = Part('goods_scale')
    counter(p, (0, 0), 2.0, 1.0, 1.0)
    balance(p, (-0.55, -0.05), 1.0, 1.0)
    ledger(p, (0.05, 0.05), 1.015, 6)
    coin_box(p, (0.62, -0.05), 1.0)
    return p


# ---------------------------------------------------------------- 08 吊るした乾物

def bundle(p: Part, x, ytop, z, kind, L=0.85):
    """吊り紐の結び目と乾物の束 1 つ（chili 赤い実・fish 干し魚・grain 穀物）。ytop は梁の中心"""
    p.add('rope', cyl((x, ytop + 0.06, z), (x, ytop - 0.16, z), 0.03, 5))
    y0 = ytop - 0.16
    if kind == 'chili':
        p.add('crop_green', ov([(0, 0.05), (1, 0.12)], y0 - 0.08, y0, (x, z), (1, 1), 6))
        p.add('crop_red', ov([(0, 0.12), (0.3, 0.17), (0.75, 0.09), (1, 0.01)], y0 - L, y0 - 0.06, (x, z), (1, 1), 6))
        for k in range(4):
            a = k * math.pi / 2 + 0.4
            p.add('crop_red', lathe((x + math.cos(a) * 0.1, y0 - 0.25 - 0.12 * k, z + math.sin(a) * 0.1),
                                    (x + math.cos(a) * 0.14, y0 - 0.5 - 0.1 * k, z + math.sin(a) * 0.14), [(0, 0.04), (1, 0.005)], 5))
    elif kind == 'fish':
        for k in range(3):
            dx = (k - 1) * 0.09
            lk = L * (0.9 + 0.08 * (k % 2))
            pc = lathe((0, y0, 0), (0, y0 - lk, 0), [(0, 0.03), (0.25, 0.08), (0.8, 0.035), (0.92, 0.02), (1, 0.07)], 6)
            p.add('slate', pc.moved((x + dx, 0, z + 0.02 * (k - 1)), 0, (1, 1, 0.45)))
    else:
        p.add('crop_yellow', ov([(0, 0.1), (0.3, 0.16), (0.8, 0.1), (1, 0.02)], y0 - L, y0, (x, z), (1, 1), 6))
        for k in range(3):
            a = k * 2 * math.pi / 3
            p.add('crop_green', beam((x, y0 - 0.05, z), (x + math.cos(a) * 0.16, y0 - 0.45, z + math.sin(a) * 0.16), 0.06, 0.012))


def goods_hanging() -> Part:
    """08 吊るした乾物：横梁 2×0.5×0.5（木、両端に黒鉛の留め）に 3 組。原点 = 梁の中心。日よけ・軒の横梁に結ぶ"""
    p = Part('goods_hanging')
    p.add('wood', boxb(-1.0, 1.0, -0.06, 0.06, -0.06, 0.06))
    for x in (-1.0, 1.0):
        p.add('graphite', boxb(x - 0.05, x + 0.05, -0.08, 0.08, -0.08, 0.08))
    for x, k in ((-0.6, 'chili'), (0.0, 'fish'), (0.6, 'grain')):
        bundle(p, x, 0.0, 0.0, k)
    return p


# ---------------------------------------------------------------- 09 ジャンク

def gear(p: Part, c, r, th, axis='z', mat='graphite', teeth=8, hub='brass'):
    x, y, z = c
    d = {'z': (0, 0, th / 2), 'x': (th / 2, 0, 0), 'y': (0, th / 2, 0)}[axis]
    a, b = (x - d[0], y - d[1], z - d[2]), (x + d[0], y + d[1], z + d[2])
    p.add(mat, cyl(a, b, r * 0.82, 10))
    for k in range(teeth):
        ang = 2 * math.pi * k / teeth
        if axis == 'z':
            q = (x + math.cos(ang) * r * 0.9, y + math.sin(ang) * r * 0.9, z)
            p.add(mat, flat_box(q, (r * 0.22, r * 0.22, th * 0.9)))
        elif axis == 'x':
            q = (x, y + math.sin(ang) * r * 0.9, z + math.cos(ang) * r * 0.9)
            p.add(mat, flat_box(q, (th * 0.9, r * 0.22, r * 0.22)))
        else:
            q = (x + math.cos(ang) * r * 0.9, y, z + math.sin(ang) * r * 0.9)
            p.add(mat, flat_box(q, (r * 0.22, th * 0.9, r * 0.22)))
    if hub:
        e = {'z': (0, 0, th * 0.7), 'x': (th * 0.7, 0, 0), 'y': (0, th * 0.7, 0)}[axis]
        p.add(hub, cyl((x - e[0], y - e[1], z - e[2]), (x + e[0], y + e[1], z + e[2]), r * 0.25, 8))


def coil(p: Part, c, r, h, turns=2.0, mat='brass', wire=0.025):
    pts = []
    n = int(turns * 8)
    for k in range(n + 1):
        a = 2 * math.pi * k / 8
        pts.append((c[0] + math.cos(a) * r, c[1] + h * k / n, c[2] + math.sin(a) * r))
    p.add(mat, tube(pts, wire, 4))


def heap(p: Part, x0, x1, z0, z1, y, h, seed=5):
    """陳列箱の中の部品の山：低い黒鉛の塊の上に、歯車・管・ばね・小箱"""
    rng = np.random.default_rng(seed)
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    w, d = x1 - x0, z1 - z0
    p.add('graphite', ov([(0, 1.0), (0.7, 0.8), (1, 0.45)], y, y + h * 0.45, (cx, cz), (w / 2, d / 2), 6))
    gear(p, (cx - w * 0.18, y + h * 0.62, cz + d * 0.15), h * 0.42, 0.08, 'z', 'graphite')
    gear(p, (cx + w * 0.28, y + h * 0.48, cz + d * 0.22), h * 0.26, 0.06, 'z', 'brass', hub='graphite')
    for k in range(4):
        px = x0 + w * (0.15 + 0.22 * k)
        pz = cz - d * 0.18 + rng.uniform(-0.05, 0.05)
        ph = h * rng.uniform(0.55, 0.95)
        p.add('graphite' if k % 2 else 'slate', cyl((px, y + h * 0.3, pz), (px, y + ph, pz), 0.05 + 0.025 * (k % 2), 8))
        p.add('brass', cyl((px, y + ph - 0.03, pz), (px, y + ph + 0.005, pz), 0.065 + 0.025 * (k % 2), 8, cap=False))
    coil(p, (cx + w * 0.05, y + h * 0.4, cz + d * 0.25), h * 0.16, h * 0.22, 2.0, 'brass')
    p.add('cloth', flat_box((x0 + w * 0.12, y + h * 0.62, cz - d * 0.1), (w * 0.14, h * 0.4, 0.02), 15))
    p.add('ivory', flat_box((cx + w * 0.36, y + h * 0.5, cz - d * 0.2), (0.16, 0.12, 0.14), 20))


def crate_open(p: Part, c, w, d, h, y=0.0, brass=True):
    """板の陳列箱（上が開いた木の箱、黒鉛の縁、真鍮の角）"""
    x0, x1, z0, z1 = c[0] - w / 2, c[0] + w / 2, c[1] - d / 2, c[1] + d / 2
    t = 0.05
    p.add('wood', boxb(x0, x1, y, y + 0.06, z0, z1))
    p.add('wood', boxb(x0, x1, y, y + h, z1 - t, z1), boxb(x0, x1, y, y + h, z0, z0 + t),
          boxb(x0, x0 + t, y, y + h, z0 + t, z1 - t), boxb(x1 - t, x1, y, y + h, z0 + t, z1 - t))
    p.add('graphite', boxb(x0 - 0.01, x1 + 0.01, y + h * 0.45, y + h * 0.55, z1, z1 + 0.012),
          boxb(x0 - 0.01, x1 + 0.01, y + h * 0.45, y + h * 0.55, z0 - 0.012, z0))
    if brass:
        caps(p, x0, x1, y, y + h, z0, z1, 0.07)


def figurine(p: Part, c, y=0.0, s=1.0):
    """09 無銘の置物（0.5×0.5×1）：黒鉛の台と柱、真鍮の玉と輪、赤い房"""
    x, z = c
    p.add('graphite', boxb(x - 0.14 * s, x + 0.14 * s, y, y + 0.05 * s, z - 0.14 * s, z + 0.14 * s))
    p.add('graphite', cyl((x, y + 0.05 * s, z), (x, y + 0.62 * s, z), 0.025 * s, 6))
    p.add('brass', ball((x, y + 0.75 * s, z), 0.13 * s, 8))
    ring = [(x + math.cos(a) * 0.17 * s, y + 0.75 * s + math.sin(a) * 0.17 * s, z) for a in np.linspace(0, 2 * math.pi, 11)]
    p.add('brass', tube(ring, 0.014 * s, 4))
    p.add('brass', ball((x, y + 0.93 * s, z), 0.035 * s))
    p.add('cloth', ov([(0, 0.02), (0.3, 0.035), (1, 0.06)], y + 0.3 * s, y + 0.55 * s, (x + 0.14 * s, z), (s, s), 6))
    p.add('rope', beam((x, y + 0.62 * s, z), (x + 0.14 * s, y + 0.55 * s, z), 0.012 * s))


def goods_junk_crate(p: Part, c=(0.0, 0.0), w=2.0, d=1.0, h=0.55, y=0.0, seed=5, cloth=True):
    crate_open(p, c, w, d, h, y)
    heap(p, c[0] - w / 2 + 0.06, c[0] + w / 2 - 0.06, c[1] - d / 2 + 0.06, c[1] + d / 2 - 0.06, y + 0.06, h * 1.25, seed)
    if cloth:
        # 前の縁に掛けた生成りの布（2 枚）
        for xa in (c[0] - w * 0.38, c[0] + w * 0.22):
            p.add('linen', sheet(lambda u, v, xa=xa: (xa + 0.3 * w / 2 * u, y + h + 0.02 - 0.42 * h * v * 1.6 if v > 0.3 else y + h + 0.02,
                                                       c[1] + d / 2 - 0.08 + (0.1 + 0.012 if v > 0.3 else v / 0.3 * 0.1)), 2, 3, 0.012))


def junk_goods() -> Part:
    """09 部品を盛った陳列箱 2×1×1（歯車・ばね・管・小箱、前の縁の布）と無銘の置物 0.5×0.5×1"""
    p = Part('junk_goods')
    goods_junk_crate(p, (-0.25, 0.0), 1.5, 0.9, 0.5)
    figurine(p, (0.78, 0.0), 0.0, 1.0)
    return p


# ---------------------------------------------------------------- 10 看板（絵記号と架空の記号だけ。文字は置かない）

def sym_basket(p: Part, cx, cy, z, s=1.0):
    p.add('graphite', _flat_poly([(-0.15 * s, 0.05 * s), (0.15 * s, 0.05 * s), (0.11 * s, -0.08 * s), (-0.11 * s, -0.08 * s)], cx, cy, z))
    arc = [(cx + math.cos(a) * 0.1 * s, cy + 0.05 * s + math.sin(a) * 0.09 * s, z) for a in np.linspace(0.15, math.pi - 0.15, 6)]
    p.add('graphite', tube(arc, 0.012 * s, 4))


def _flat_poly(pts2, cx, cy, z, th=0.008) -> Piece:
    """看板の面の上の平らな多角形（凸、x・y で書く）。z は板の表の位置"""
    n = len(pts2)
    v = [(cx + x, cy + y, z + dz) for dz in (0.0, th) for x, y in pts2]
    f = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)] + [list(range(n))[::-1], list(range(n, 2 * n))]
    return _orient(Piece(V(v, float), f))


def sym_marks(p: Part, cx, cy, z, s=1.0, mat='graphite'):
    """架空の非言語記号：三角・丸・四角の並び"""
    p.add(mat, _flat_poly([(-0.05 * s, -0.04 * s), (0.05 * s, -0.04 * s), (0.0, 0.05 * s)], cx - 0.13 * s, cy, z))
    p.add(mat, _flat_poly([(math.cos(a) * 0.045 * s, math.sin(a) * 0.045 * s) for a in np.linspace(0, 2 * math.pi, 9)[:-1]], cx, cy, z))
    p.add(mat, _flat_poly([(-0.04 * s, -0.04 * s), (0.04 * s, -0.04 * s), (0.04 * s, 0.04 * s), (-0.04 * s, 0.04 * s)], cx + 0.13 * s, cy, z))


def sym_gear(p: Part, cx, cy, z, s=1.0, mat='graphite'):
    pts = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        r = 0.13 * s if k % 2 == 0 else 0.1 * s
        pts.append((math.cos(a) * r, math.sin(a) * r))
    p.add(mat, _flat_poly(pts, cx, cy, z))
    p.add('linen', _flat_poly([(math.cos(a) * 0.04 * s, math.sin(a) * 0.04 * s) for a in np.linspace(0, 2 * math.pi, 9)[:-1]], cx, cy, z + 0.008))


def sym_wrench(p: Part, cx, cy, z, s=1.0, mat='graphite'):
    p.add(mat, beam((cx - 0.12 * s, cy - 0.16 * s, z + 0.004), (cx + 0.08 * s, cy + 0.1 * s, z + 0.004), 0.05 * s, 0.008, up=(0, 0, 1)))
    p.add(mat, _flat_poly([(math.cos(a) * 0.08 * s, math.sin(a) * 0.08 * s) for a in np.linspace(0, 2 * math.pi, 9)[:-1]],
                          cx + 0.1 * s, cy + 0.13 * s, z))
    p.add('linen', _flat_poly([(-0.025 * s, -0.03 * s), (0.025 * s, -0.03 * s), (0.025 * s, 0.06 * s), (-0.025 * s, 0.06 * s)],
                              cx + 0.13 * s, cy + 0.16 * s, z + 0.008))


def sym_bowl(p: Part, cx, cy, z, s=1.0, mat='linen'):
    half = [(math.cos(a) * 0.16 * s, math.sin(a) * 0.12 * s) for a in np.linspace(math.pi, 2 * math.pi, 7)]
    p.add(mat, _flat_poly(half, cx, cy, z))
    p.add(mat, _flat_poly([(-0.06 * s, -0.16 * s), (0.06 * s, -0.16 * s), (0.06 * s, -0.12 * s), (-0.06 * s, -0.12 * s)], cx, cy + 0.0, z))
    for k in (-1, 0, 1):
        p.add(mat, beam((cx + k * 0.06 * s, cy + 0.04 * s, z + 0.004), (cx + k * 0.06 * s + 0.02 * s, cy + 0.15 * s, z + 0.004),
                        0.022 * s, 0.008, up=(0, 0, 1)))


def sym_house(p: Part, cx, cy, z, s=1.0, mat='linen'):
    p.add(mat, _flat_poly([(-0.12 * s, -0.1 * s), (0.12 * s, -0.1 * s), (0.12 * s, 0.04 * s), (0.0, 0.14 * s), (-0.12 * s, 0.04 * s)], cx, cy, z))
    p.add('cloth', _flat_poly([(-0.035 * s, -0.1 * s), (0.035 * s, -0.1 * s), (0.035 * s, -0.01 * s), (-0.035 * s, -0.01 * s)], cx, cy, z + 0.008))


def board(p: Part, cx, cy, z, w, h, face='linen', frame='wood', t=0.05):
    """看板の板：木の枠と生成りの面（面は z + t/2 の前）。返り値は記号を置く面の z"""
    p.add(frame, boxb(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, z - t / 2, z + t / 2))
    p.add(face, boxb(cx - w / 2 + 0.05, cx + w / 2 - 0.05, cy - h / 2 + 0.05, cy + h / 2 - 0.05, z - t / 2 - EPS, z + t / 2 + EPS))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0 = cx + sx * w / 2 - (0.07 if sx > 0 else 0.0)
            y0 = cy + sy * h / 2 - (0.07 if sy > 0 else 0.0)
            p.add('brass', boxb(x0 - 0.005, x0 + 0.075, y0 - 0.005, y0 + 0.075, z - t / 2 - 0.02, z + t / 2 + 0.02))
    return z + t / 2 + EPS + 0.004


def hang_board(p: Part, cx, ytop, z, w=0.9, h=0.45, sym='basket', drop=0.32):
    """10 吊り札 1×0.1×0.5：上の留め（ytop）から 2 本の鎖で吊る板と記号（両面）"""
    cy = ytop - drop - h / 2
    for sx in (-1, 1):
        x = cx + sx * w * 0.35
        p.add('graphite', beam((x, ytop, z), (x, cy + h / 2, z), 0.018))
    zf = board(p, cx, cy, z, w, h)
    zb = z - (zf - z)
    for zz, back in ((zf, False), (zb - 0.008, True)):
        if sym == 'basket':
            sym_basket(p, cx, cy + 0.04, zz, 0.9)
            sym_marks(p, cx, cy - 0.12, zz, 0.7)
        elif sym == 'gear':
            sym_gear(p, cx - 0.12, cy, zz, 1.0)
            sym_marks(p, cx + 0.14, cy, zz, 0.55)
        elif sym == 'wrench':
            sym_wrench(p, cx, cy, zz, 1.0)


def sign_hang() -> Part:
    """10 吊り札（雑貨：かごの絵と三角・丸・四角）。原点 = 上の留め（梁・腕の下の面）"""
    p = Part('sign_hang')
    p.add('graphite', boxb(-0.45, 0.45, -0.03, 0.03, -0.03, 0.03))
    hang_board(p, 0.0, 0.0, 0.0, 0.9, 0.45, 'basket')
    return p


def sign_round() -> Part:
    """10 丸い食堂の札（赤い面に生成りの鉢と湯気）：壁に平らに付ける。原点 = 壁の面・札の中心。壁から 0.08 m まで"""
    p = Part('sign_round')
    r = 0.42
    p.add('wood', lathe((0, 0, 0.0), (0, 0, 0.05), [(0, r), (1, r)], 16))
    p.add('cloth', lathe((0, 0, 0.05), (0, 0, 0.05 + EPS), [(0, r - 0.06), (1, r - 0.06)], 16))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        p.add('brass', flat_box((math.cos(a) * (r - 0.02), math.sin(a) * (r - 0.02), 0.035), (0.07, 0.07, 0.04)))
    sym_bowl(p, 0.0, 0.02, 0.05 + EPS + 0.004, 1.5)
    return p


def sign_stand() -> Part:
    """10 立て札 1×0.5×1（工房：レンチの絵と丸）：A 字の 2 枚の板。原点 = 底の中心、正面 +Z"""
    p = Part('sign_stand')
    lean = math.radians(14)
    h = 0.95
    for sz in (1, -1):
        zb = sz * 0.24
        top = (0, h, sz * 0.02)
        for sx in (-1, 1):
            p.add('wood', beam((sx * 0.4, 0, zb), (sx * 0.4, h, sz * 0.02), 0.06))
        p.add('wood', beam((-0.4, h - 0.02, sz * 0.03), (0.4, h - 0.02, sz * 0.03), 0.06))
        # 板：脚の間の斜めの板
        v = V([(-0.36, 0.12, zb - sz * 0.0), (0.36, 0.12, zb), (0.36, h - 0.08, sz * 0.04), (-0.36, h - 0.08, sz * 0.04)], float)
        n = V([0, math.sin(lean) * 0 + 0.0, sz * 1.0])
        th = 0.025
        nn = np.cross(v[1] - v[0], v[3] - v[0])
        nn = nn / np.linalg.norm(nn) * (1 if nn[2] * sz > 0 else -1)
        vv = np.concatenate([v - nn * th / 2, v + nn * th / 2])
        f = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
        p.add('linen', _orient(Piece(vv, f)))
        # 記号（板の面に平行に置く：板の傾きに合わせて回す）
        sub = Part('s')
        sym_wrench(sub, 0.0, 0.08, 0.0, 1.2)
        sym_marks(sub, 0.0, -0.22, 0.0, 0.8)
        mid = (v[0] + v[2]) / 2 + nn * (th / 2 + EPS)
        ang = math.degrees(math.atan2(0.22, h - 0.2)) * sz
        for m, pcs in sub.by_mat.items():
            for pc in pcs:
                q = tilt_x(Piece(pc.v.copy() if sz > 0 else pc.v * V([-1, 1, -1]), pc.f if sz > 0 else pc.f, sm=pc.sm), -ang)
                p.add(m, q.moved(mid))
        p.add('brass', boxb(-0.44, -0.36, 0.0, 0.05, zb - 0.04, zb + 0.04), boxb(0.36, 0.44, 0.0, 0.05, zb - 0.04, zb + 0.04))
    p.add('graphite', beam((-0.4, 0.45, 0.13), (-0.4, 0.45, -0.13), 0.02), beam((0.4, 0.45, 0.13), (0.4, 0.45, -0.13), 0.02))
    return p


def sign_cloth() -> Part:
    """10 布札 1×0.1×1（宿：赤い布に生成りの家の絵）：壁に平らに。原点 = 壁の面・棒の高さの中心。壁から 0.08 m まで"""
    p = Part('sign_cloth')
    p.add('graphite', cyl((-0.5, 0, 0.05), (0.5, 0, 0.05), 0.02, 6))
    for x in (-0.47, 0.47):
        p.add('graphite', boxb(x - 0.03, x + 0.03, -0.05, 0.05, 0.0, 0.05))
    p.add('cloth', boxb(-0.4, 0.4, -1.0, -0.03, 0.045, 0.06))
    p.add('linen', boxb(-0.4, 0.4, -0.86, -0.8, 0.06, 0.06 + EPS * 0.6), boxb(-0.4, 0.4, -0.97, -0.93, 0.06, 0.06 + EPS * 0.6))
    sym_house(p, 0.0, -0.42, 0.06 + EPS * 0.6, 1.6)
    p.add('linen', _flat_poly([(-0.05, 0.0), (0.05, 0.0), (0.0, -0.07)], -0.12, -0.72, 0.06 + EPS * 0.6))
    p.add('linen', _flat_poly([(-0.05, 0.0), (0.05, 0.0), (0.0, -0.07)], 0.12, -0.72, 0.06 + EPS * 0.6))
    return p


# ---------------------------------------------------------------- 11 腰掛け・ござ・座布団

def stool_small(p: Part, c, w=0.9, d=0.45, h=0.48, yaw=0.0):
    sub = Part('s')
    for sx in (-1, 1):
        for sz in (-1, 1):
            sub.add('wood', boxb(sx * (w / 2 - 0.06) - 0.035, sx * (w / 2 - 0.06) + 0.035, 0, h - 0.06, sz * (d / 2 - 0.05) - 0.035,
                                 sz * (d / 2 - 0.05) + 0.035))
    sub.add('wood', boxb(-w / 2, w / 2, h - 0.08, h - 0.04, -d / 2, d / 2))
    sub.add('cloth', boxb(-w / 2 + 0.03, w / 2 - 0.03, h - 0.04, h, -d / 2 + 0.03, d / 2 - 0.03))
    sub.add('graphite', boxb(-w / 2 + 0.06, w / 2 - 0.06, 0.12, 0.16, -0.02, 0.02))
    p.place(sub, (c[0], 0, c[1]), yaw)


def cushion(p: Part, c, s=0.5, y=0.0, kind='red', yaw=0.0):
    """座布団（四角を 45 度回した 4 角の回転体。赤に生成りの菱形／生成りに灰色の 2 本の筋）"""
    base, mark = ('cloth', 'linen') if kind == 'red' else ('linen', 'slate')
    p.add(base, ov([(0, 0.62), (0.45, 0.72), (1, 0.5)], y, y + s * 0.34, c, (s * 0.7, s * 0.7), 4, yaw=45 + yaw))
    top = y + s * 0.34
    if kind == 'red':
        p.add(mark, ov([(0, 0.2), (1, 0.2)], top - 0.006, top + 0.008, c, (s * 0.7, s * 0.7), 4, yaw=yaw))
    else:
        for k in (-1, 1):
            q = flat_box((0, top - 0.004, k * s * 0.1), (s * 0.68, 0.016, 0.05)).moved((c[0], 0, c[1]), yaw)
            p.add(mark, q)


def mat_rug(p: Part, c, w=2.0, d=1.0, y=0.0, yaw=0.0):
    """ござ 2×1×0.1：生成りの織物、赤い縁の帯（色）"""
    sub = Part('m')
    sub.add('burlap', boxb(-w / 2, w / 2, y, y + 0.025, -d / 2, d / 2))
    b = 0.1
    for (x0, x1, z0, z1) in ((-w / 2, w / 2, -d / 2, -d / 2 + b), (-w / 2, w / 2, d / 2 - b, d / 2), (-w / 2, -w / 2 + b, -d / 2 + b, d / 2 - b),
                             (w / 2 - b, w / 2, -d / 2 + b, d / 2 - b)):
        sub.add('cloth', boxb(x0, x1, y + 0.025, y + 0.032, z0, z1))
    sub.add('cloth2', boxb(-w / 2 + 0.16, w / 2 - 0.16, y + 0.025, y + 0.03, -d / 2 + 0.16, -d / 2 + 0.2),
            boxb(-w / 2 + 0.16, w / 2 - 0.16, y + 0.025, y + 0.03, d / 2 - 0.2, d / 2 - 0.16))
    p.place(sub, (c[0], 0, c[1]), yaw)


def seat_small() -> Part:
    """11 腰掛け 1×0.5×0.5・ござ 2×1×0.1・座布団 0.5×0.5×0.2（赤・生成り）"""
    p = Part('seat_small')
    mat_rug(p, (0.2, 0.0), 2.0, 1.0)
    stool_small(p, (-0.45, -0.1), 0.9, 0.45, 0.48)
    cushion(p, (0.3, 0.15), 0.5, 0.032, 'red', 10)
    cushion(p, (0.85, 0.05), 0.5, 0.032, 'cream', -8)
    return p


def seat_mat() -> Part:
    """店番の床：ござと座布団 2 つだけ（高さ 0.2 以下。当たり判定なし：床の上の薄い物）。露店の中・屋内の床に"""
    p = Part('seat_mat')
    mat_rug(p, (0.0, 0.0), 1.8, 0.95)
    cushion(p, (-0.35, 0.05), 0.48, 0.032, 'red', 6)
    cushion(p, (0.35, -0.05), 0.48, 0.032, 'cream', -10)
    return p


# ---------------------------------------------------------------- 12 鉢植え（W2-05 の角形白磁鉢と同じ鉢）

def pot(p: Part, w=0.8, h=0.5):
    """town_parts.planter と同じ鉢（白磁の箱・黒鉛の縁と台・真鍮の角）"""
    p.add('ivory', boxb(-w / 2, w / 2, 0.04, h, -w / 2, w / 2))
    p.add('graphite', boxb(-w / 2 - 0.03, w / 2 + 0.03, 0, 0.06, -w / 2 - 0.03, w / 2 + 0.03),
          boxb(-w / 2 - 0.02, w / 2 + 0.02, h - 0.05, h + 0.02, -w / 2 - 0.02, w / 2 + 0.02))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('brass', boxb(sx * w / 2 - 0.05, sx * w / 2 + 0.05, 0.06, h - 0.05, sz * w / 2 - 0.05, sz * w / 2 + 0.05))
    p.add('wood2', boxb(-w / 2 + 0.03, w / 2 - 0.03, h - 0.02, h + 0.025, -w / 2 + 0.03, w / 2 - 0.03))


def pot_succulent() -> Part:
    """12 多肉（全高 1）：外の葉は赤、内は緑。葉は 4 角のとがった棒"""
    p = Part('pot_succulent')
    pot(p)
    base = 0.53
    for ring, (n, rr, hh, mat, tl) in enumerate(((7, 0.36, 0.3, 'crop_red', 0.25), (5, 0.2, 0.42, 'crop_red', 0.12), (4, 0.06, 0.48, 'crop_green', 0.0))):
        for k in range(n):
            a = 2 * math.pi * (k + ring * 0.37) / n
            tip = (math.cos(a) * rr, base + hh, math.sin(a) * rr)
            p.add(mat, lathe((math.cos(a) * 0.05, base, math.sin(a) * 0.05), tip, [(0, 0.075), (0.35, 0.085), (1, 0.004)], 4))
    return p


def pot_shrub() -> Part:
    """12 低木（全高 1.5）：曲がった幹と 4 つの葉の塊"""
    p = Part('pot_shrub')
    pot(p)
    p.add('wood', tube([(0, 0.5, 0), (0.05, 0.78, 0.02), (-0.06, 1.0, -0.02), (0.02, 1.15, 0.0)], 0.05, 6))
    p.add('wood', tube([(-0.04, 0.95, -0.02), (-0.25, 1.1, 0.05)], 0.03, 5), tube([(0.03, 0.85, 0.02), (0.26, 1.02, -0.04)], 0.03, 5))
    for c, r in (((0.0, 1.3, 0.0), 0.32), ((-0.3, 1.15, 0.06), 0.24), ((0.3, 1.08, -0.05), 0.24), ((0.08, 1.18, 0.25), 0.2)):
        p.add('crop_green', P._blob(c, r))
    return p


def pot_vine() -> Part:
    """12 つる（全高 1）：上の低い茂みと、鉢の縁から垂れる 4 本のつると葉"""
    p = Part('pot_vine')
    pot(p)
    p.add('crop_green', P._blob((0.0, 0.72, 0.0), 0.32), P._blob((0.12, 0.85, -0.08), 0.22))
    for k, (x, z) in enumerate(((0.42, 0.25), (-0.42, 0.1), (0.15, 0.42), (-0.2, -0.42))):
        nx, nz = (1 if abs(x) > abs(z) else 0) * np.sign(x), (1 if abs(z) >= abs(x) else 0) * np.sign(z)
        top = (x, 0.53, z)
        pts = [top, (x + nx * 0.06, 0.4, z + nz * 0.06), (x + nx * 0.07, 0.22 - 0.05 * (k % 2), z + nz * 0.07),
               (x + nx * 0.05, 0.05 + 0.08 * (k % 2), z + nz * 0.05)]
        p.add('crop_green', tube(pts, 0.016, 4))
        for t, q in enumerate(pts[1:]):
            p.add('crop_green', ball((q[0] + nx * 0.03, q[1], q[2] + nz * 0.03), 0.06 - 0.008 * t, 5, 0.7))
    return p


# ---------------------------------------------------------------- 13 食堂の卓

def dishes(p: Part, x0, x1, z0, z1, y, seed=7):
    """卓の上の食器：鉢 2（料理の色）・真鍮の水差し・灰色の杯 2・実を盛った皿"""
    w, d = x1 - x0, z1 - z0
    bowl(p, (x0 + w * 0.22, z0 + d * 0.3), 0.11, y, 'ivory', 'crop_green')
    bowl(p, (x0 + w * 0.7, z0 + d * 0.72), 0.11, y, 'ivory', 'crop_yellow')
    jug = (x0 + w * 0.48, z0 + d * 0.42)
    p.add('brass', ov([(0, 0.7), (0.45, 1.0), (0.8, 0.55), (1, 0.7)], y, y + 0.24, jug, (0.08, 0.08), 8))
    p.add('brass', tube([(jug[0] + 0.07, y + 0.18, jug[1]), (jug[0] + 0.13, y + 0.16, jug[1]), (jug[0] + 0.1, y + 0.07, jug[1])], 0.012, 4))
    for cx, cz in ((x0 + w * 0.28, z0 + d * 0.72), (x0 + w * 0.76, z0 + d * 0.28)):
        p.add('slate', ov([(0, 0.8), (1, 1.0)], y, y + 0.09, (cx, cz), (0.045, 0.045), 6))
    pl = (x0 + w * 0.5, z0 + d * 0.78)
    p.add('wood2', ov([(0, 0.8), (1, 1.0)], y, y + 0.03, pl, (0.14, 0.14), 8))
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        p.add('crop_yellow', ball((pl[0] + math.cos(a) * 0.06, y + 0.06, pl[1] + math.sin(a) * 0.06), 0.045))
    p.add('crop_red', ball((pl[0], y + 0.1, pl[1]), 0.045))


def diner_table_top(p: Part, x0, x1, z0, z1, h, runner_axis='x'):
    """食堂の机：木の天板、黒鉛の脚、床留めの真鍮の金具、赤い掛け布（生成りの筋）"""
    for x in (x0 + 0.08, x1 - 0.08):
        for z in (z0 + 0.08, z1 - 0.08):
            p.add('graphite', boxb(x - 0.05, x + 0.05, 0, h - 0.07, z - 0.05, z + 0.05))
            p.add('brass', boxb(x - 0.09, x + 0.09, 0, 0.03, z - 0.09, z + 0.09))
    p.add('wood', boxb(x0, x1, h - 0.07, h, z0, z1))
    p.add('graphite', boxb(x0 + 0.05, x1 - 0.05, h - 0.15, h - 0.07, z0 + 0.05, z1 - 0.05))
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    if runner_axis == 'x':
        rw = (z1 - z0) * 0.36
        p.add('cloth', boxb(x0 - 0.012, x1 + 0.012, h, h + 0.012, cz - rw / 2, cz + rw / 2),
              boxb(x0 - 0.012, x0, h - 0.24, h + 0.012, cz - rw / 2, cz + rw / 2), boxb(x1, x1 + 0.012, h - 0.24, h + 0.012, cz - rw / 2, cz + rw / 2))
        for s in (-1, 1):
            p.add('linen', boxb(x0 - 0.012, x1 + 0.012, h + 0.012, h + 0.016, cz + s * rw * 0.3 - 0.02, cz + s * rw * 0.3 + 0.02))
    else:
        rw = (x1 - x0) * 0.36
        p.add('cloth', boxb(cx - rw / 2, cx + rw / 2, h, h + 0.012, z0 - 0.012, z1 + 0.012),
              boxb(cx - rw / 2, cx + rw / 2, h - 0.24, h + 0.012, z0 - 0.012, z0), boxb(cx - rw / 2, cx + rw / 2, h - 0.24, h + 0.012, z1, z1 + 0.012))
        for s in (-1, 1):
            p.add('linen', boxb(cx + s * rw * 0.3 - 0.02, cx + s * rw * 0.3 + 0.02, h + 0.012, h + 0.016, z0 - 0.012, z1 + 0.012))


def diner_table() -> Part:
    """13 食堂の机（中段の食堂の前の卓。前の露店台 stall_table と同じ大きさ 2×1・天板 0.95 で、同じ当たり判定）と食器"""
    p = Part('diner_table')
    diner_table_top(p, -1.0, 1.0, -0.5, 0.5, 0.95, 'x')
    dishes(p, -0.8, 0.8, -0.4, 0.4, 0.962)
    return p


def stool_round(p: Part, c, h=0.45, s=0.42):
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('wood', boxb(c[0] + sx * s * 0.32 - 0.03, c[0] + sx * s * 0.32 + 0.03, 0, h - 0.06, c[1] + sz * s * 0.32 - 0.03,
                               c[1] + sz * s * 0.32 + 0.03))
    p.add('wood', boxb(c[0] - s / 2, c[0] + s / 2, h - 0.08, h - 0.04, c[1] - s / 2, c[1] + s / 2))
    p.add('cloth', boxb(c[0] - s / 2 + 0.02, c[0] + s / 2 - 0.02, h - 0.04, h + 0.02, c[1] - s / 2 + 0.02, c[1] + s / 2 - 0.02))


def diner_set_2() -> Part:
    """13 2 席の組 2×2×1：机 1.2×0.8 と腰掛け 2"""
    p = Part('diner_set_2')
    diner_table_top(p, -0.6, 0.6, -0.4, 0.4, 0.8, 'z')
    dishes(p, -0.5, 0.5, -0.32, 0.32, 0.812)
    for x in (-0.82, 0.82):
        stool_round(p, (x, 0.0))
    return p


def diner_set_4() -> Part:
    """13 4 席の組 2×2×1：机 1.6×0.9 と腰掛け 4"""
    p = Part('diner_set_4')
    diner_table_top(p, -0.8, 0.8, -0.45, 0.45, 0.8, 'x')
    dishes(p, -0.7, 0.7, -0.36, 0.36, 0.812)
    for x in (-0.42, 0.42):
        for z in (-0.72, 0.72):
            stool_round(p, (x, z))
    return p


# ---------------------------------------------------------------- 14 木の玩具（番機を簡単に真似た人形と、こま）

def toy_banki() -> Part:
    """14 人形 0.5（座った姿勢。白い塗りの木の角張った頭と手足、木の関節。武器・発光なし）とこま 0.5。真鍮なし（柔らかい物ではないが、
    子どもの木の玩具なので金具は付けない）。原点 = 底の中心、人形は -X、こまは +X"""
    p = Part('toy_banki')
    ox = -0.12
    # 脚（前へ投げ出す）と足
    for sx in (-1, 1):
        x = ox + sx * 0.07
        p.add('ivory', boxb(x - 0.045, x + 0.045, 0.0, 0.08, -0.02, 0.17))
        p.add('wood', boxb(x - 0.035, x + 0.035, 0.02, 0.07, 0.17, 0.2))
        p.add('ivory', boxb(x - 0.05, x + 0.05, 0.0, 0.12, 0.2, 0.27))
    # 胴・首・頭
    p.add('ivory', boxb(ox - 0.11, ox + 0.11, 0.05, 0.27, -0.08, 0.06))
    p.add('wood', boxb(ox - 0.12, ox + 0.12, 0.13, 0.16, -0.085, 0.065))
    p.add('wood', cyl((ox, 0.27, -0.01), (ox, 0.3, -0.01), 0.035, 6))
    p.add('ivory', boxb(ox - 0.12, ox + 0.12, 0.3, 0.5, -0.11, 0.09))
    for sx in (-1, 1):
        p.add('dark', boxb(ox + sx * 0.05 - 0.018, ox + sx * 0.05 + 0.018, 0.39, 0.43, 0.09, 0.1))
    p.add('wood', boxb(ox - 0.03, ox + 0.03, 0.34, 0.355, 0.09, 0.1))
    p.add('wood', cyl((ox, 0.5, -0.01), (ox, 0.58, -0.01), 0.015, 5))
    p.add('wood2', ball((ox, 0.6, -0.01), 0.03))
    # 腕（下ろして少し前）
    for sx in (-1, 1):
        x = ox + sx * 0.15
        p.add('wood', ball((x, 0.24, -0.01), 0.035))
        p.add('ivory', boxb(x - 0.035, x + 0.035, 0.1, 0.24, -0.04, 0.03))
        p.add('ivory', boxb(x - 0.04, x + 0.04, 0.05, 0.11, -0.02, 0.07))
    # こま：赤と生成りの帯、木の軸と先
    cx = 0.3
    prof_r = [(0.0, 0.01), (0.25, 0.12), (0.55, 0.15), (0.75, 0.12), (1.0, 0.04)]
    y0, y1 = 0.04, 0.24
    p.add('wood2', cyl((cx, 0.0, 0.0), (cx, 0.05, 0.0), 0.012, 5))
    bands = (('cloth', 0.0, 0.4), ('linen', 0.4, 0.55), ('cloth', 0.55, 0.7), ('linen', 0.7, 1.0))
    for mat, t0, t1 in bands:
        sub = [(0.0, np.interp(t0, [q[0] for q in prof_r], [q[1] for q in prof_r])),
               (1.0, np.interp(t1, [q[0] for q in prof_r], [q[1] for q in prof_r]))]
        p.add(mat, lathe((cx, y0 + (y1 - y0) * t0, 0), (cx, y0 + (y1 - y0) * t1, 0), sub, 10))
    p.add('wood2', cyl((cx, y1, 0), (cx, y1 + 0.09, 0), 0.02, 6))
    return p


# ---------------------------------------------------------------- 15 洗濯かご

def laundry_basket() -> Part:
    """15 洗濯かご 1×0.5×0.5：かご（編み目は色の帯）と畳んだ布・縁に掛けた布。真鍮なし"""
    p = Part('laundry_basket')
    basket(p, (0, 0), 1.0, 0.55, 0.42, crop=None, handles=True)
    folded(p, (-0.12, -0.02), 0.5, 0.36, 0.36, [('linen', None), ('cloth', None), ('slate', None)], 0.06, stripe=False)
    folded(p, (0.24, 0.02), 0.36, 0.32, 0.36, [('cloth', None), ('linen', None)], 0.065, stripe=False)
    # 縁から垂れた布（生成りに灰色の筋）
    p.add('linen', sheet(lambda u, v: (0.02 + 0.3 * u, 0.5 - (0.36 * (v - 0.35) / 0.65 if v > 0.35 else -0.02 * v), 0.16 + (0.13 if v > 0.35 else v / 0.35 * 0.13)),
                         2, 3, 0.015))
    p.add('slate', boxb(0.1, 0.16, 0.22, 0.46, 0.3, 0.315), boxb(0.2, 0.26, 0.22, 0.46, 0.3, 0.315))
    return p


# ---------------------------------------------------------------- 16 風の旗

def wind_flag(name='wind_flag') -> Part:
    """16 竿 0.5×0.5×2（床の基部に固定）、旗幅 1・吹き流し 2。旗と吹き流しは +X（風下）へ。原点 = 基部の底の中心"""
    p = Part(name)
    p.add('graphite', boxb(-0.22, 0.22, 0, 0.06, -0.22, 0.22))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('brass', boxb(sx * 0.16 - 0.025, sx * 0.16 + 0.025, 0.06, 0.08, sz * 0.16 - 0.025, sz * 0.16 + 0.025))
    H = 2.3
    p.add('graphite', cyl((0, 0.06, 0), (0, H, 0), 0.045, 8))
    for y in (0.35, 1.4):
        p.add('brass', cyl((0, y, 0), (0, y + 0.08, 0), 0.06, 8))
    p.add('brass', ball((0, H + 0.04, 0), 0.06, 8))
    # 旗：上の腕から吊る 1.0×0.7 の布（上半分は赤に生成りの半円、下は灰色、真ん中に生成りの下向きの三角）
    p.add('graphite', beam((0, 1.98, 0), (1.06, 1.98, 0), 0.035))
    x0, x1, yt, yb = 0.06, 1.04, 1.95, 1.25
    ym = (yt + yb) / 2 + 0.06
    p.add('cloth', boxb(x0, x1, ym, yt, -0.01, 0.01))
    p.add('slate', boxb(x0, x1, yb, ym, -0.01, 0.01))
    for zs in (1, -1):
        zf = zs * (0.01 + EPS / 2)
        half = [(math.cos(a) * 0.2, math.sin(a) * 0.17) for a in np.linspace(0, math.pi, 7)]
        q = _flat_poly(half, (x0 + x1) / 2, ym + 0.02, zf if zs > 0 else zf - 0.008)
        p.add('linen', q)
        p.add('linen', _flat_poly([(-0.18, 0.0), (0.18, 0.0), (0.0, -0.24)], (x0 + x1) / 2, ym - 0.02, zf if zs > 0 else zf - 0.008))
    # 吹き流し：竿の上から +X へ 2 m、先へ細く、ゆるい波（赤と生成りの 2 本）
    for k, mat in enumerate(('cloth', 'linen')):
        def f(u, v, k=k):
            w0 = 0.36 * (1 - 0.8 * u)
            x = 0.06 + 2.0 * u
            y = H - 0.05 - 0.25 * u * u - w0 * (k + v) / 2
            return (x, y, 0.08 * math.sin(u * 5.0))
        p.add(mat, sheet(f, 8, 1, 0.012))
    p.add('graphite', cyl((0, H - 0.08, 0), (0.1, H - 0.08, 0), 0.03, 6))
    return p


# ---------------------------------------------------------------- 洗濯物の綱（town/laundry_line の差し替え。同じ高さ・同じ長さ）

def laundry_goods(w=2.0) -> Part:
    """壁から壁への洗濯物の綱（town_parts.laundry_line と同じ原点・長さ・たるみ・布の下の端の高さ）。布は W2-05b の柄（赤に山形・生成りに灰色の帯）、
    畳んだ布の色（灰色）。綱の目と留め金は前と同じ"""
    p = Part('laundry_goods' if w == 2.0 else f'laundry_goods_{int(w)}')
    hw = w / 2
    for x in (-hw, hw):
        p.add('brass', boxb(x - 0.02 if x > 0 else x, x if x > 0 else x + 0.02, -0.12, 0.12, -0.07, 0.07))
        d = -1 if x > 0 else 1
        p.add('graphite', cyl((x, 0, 0), (x + d * 0.09, 0, 0), 0.02, 5))
    dip = 0.14 * max(1.0, w / 4)
    pts = sag((-hw + 0.08, 0, 0), (hw - 0.08, 0, 0), max(8, int(w * 3)), dip)
    p.add('rope', tube(pts, 0.014, 5))
    pat = ((0.38, 'a', 0.5), (0.37, 'b', 0.6), (0.3, 'slate', 0.42), (0.3, 'b', 0.55))
    n = max(4, int(round(w * 2)))
    step = (w - 0.4) / n
    for k in range(n):
        cw, kind, ln = pat[k % 4]
        x0 = -hw + 0.2 + k * step + (step - min(cw, step * 0.85)) / 2
        x1 = x0 + min(cw, step * 0.85)
        xm = (x0 + x1) / 2
        t = -dip * 4 * ((xm + hw) / w) * (1 - (xm + hw) / w) - 0.01
        if kind == 'slate':
            p.add('slate', boxb(x0, x1, t - ln, t, -0.01, 0.01))
            p.add('linen', boxb(x0, x1, t - ln * 0.8, t - ln * 0.7, 0.01, 0.01 + EPS * 0.6))
        else:
            cloth_panel(p, x0, x1, t, ln, 0.0, kind, t=0.02)
        p.add('graphite', boxb(x0 + 0.03, x0 + 0.06, t - 0.04, t + 0.03, -0.02, 0.02), boxb(x1 - 0.06, x1 - 0.03, t - 0.04, t + 0.03, -0.02, 0.02))
    return p


# ---------------------------------------------------------------- 露店の組（台の上・前の梁・台の前の床）

def market_general() -> Part:
    """雑貨屋の露店の品（town_goods_assembled の密度）。原点 = 台（7×0.8、上の面 1.1）の上の面の中心、+Z が客の側。
    台の上：大かごと小かご・区切り箱・天秤と帳簿・かめと鉢・開いた豆の袋・畳んだ布、前へ垂らした赤い掛け布。
    前の梁（原点の 2.25 m 上、z -0.05）：乾物の束 4 つと、かごの絵の吊り札。
    台の前の床（y -1.1）：左にかご 2 つ、右に麻袋の山（真ん中 3 m は店主と話すために空ける）。当たり判定は dress_solid の town/market_general"""
    p = Part('market_general')
    # 掛け布（台の上の面と前の面から 1.5 cm）
    p.add('cloth', boxb(-0.7, 0.7, 0.015, 0.03, -0.42, 0.43), boxb(-0.7, 0.7, -0.62, 0.03, 0.415, 0.43))
    for x in (-0.45, 0.45):
        p.add('linen', boxb(x - 0.04, x + 0.04, -0.62, 0.034, 0.43, 0.442))
    # 台の上
    basket(p, (-3.0, -0.02), 0.78, 0.62, 0.3, crop='crop_red', grains=7, leaves=True, seed=11)
    basket(p, (-2.35, 0.2), 0.42, 0.36, 0.22, crop='crop_yellow', seed=12, grains=4)
    basket(p, (-2.3, -0.2), 0.4, 0.34, 0.2, crop='cloth2', seed=13, grains=4, handles=False)
    bins(p, (-1.25, 0.0), 1.3, 0.66, 0.28, 0.03, 3, 2, legs=False)
    balance(p, (0.0, -0.12), 0.03, 0.85)
    ledger(p, (0.05, 0.2), 0.03, 8)
    jar(p, (0.85, -0.12), 0.17, 0.42, 0.03, stand=False, straps=False, lid=None)
    jar(p, (1.3, -0.1), 0.2, 0.38, 0.03, body='slate', band='slate', stand=False, straps=False)
    bowl(p, (1.05, 0.22), 0.13, 0.03, 'cloth', 'crop_yellow')
    sack(p, (2.0, 0.0), 0.24, 0.22, 0.42, 0.03, kind='open')
    folded(p, (2.85, 0.0), 0.62, 0.5, 0.03, [('linen', 'cloth'), ('cloth', 'linen'), ('slate', 'linen'), ('linen', 'slate')], 0.075)
    # 前の梁の吊り物（梁は y 2.25・z -0.05。吊り灯は x ±2.0 にあるので避ける）
    for x, k in ((-3.0, 'chili'), (-1.1, 'fish'), (1.1, 'grain'), (3.0, 'chili')):
        bundle(p, x, 2.25, -0.05, k, 0.8)
    hang_board(p, 0.0, 2.2, -0.05, 0.8, 0.4, 'basket', drop=0.28)
    # 台の前の床（y -1.1）。左：かご（根菜）と小かご（赤い実）、右：麻袋の山
    basket(p, (-2.85, 0.73), 0.9, 0.56, 0.42, y=-1.1, crop='crop_yellow', seed=14)
    basket(p, (-2.0, 0.72), 0.5, 0.5, 0.34, y=-1.1, crop='crop_red', seed=15, grains=5)
    sack(p, (1.92, 0.72), 0.26, 0.25, 0.82, -1.1, tie='cloth')
    sack(p, (2.5, 0.78), 0.27, 0.25, 0.6, -1.1, kind='open')
    sack(p, (3.05, 0.7), 0.24, 0.23, 0.74, -1.1, mat='slate', yaw=15)
    return p


def market_junk() -> Part:
    """ジャンク屋の露店の品。原点・向きは market_general と同じ。
    台の上：部品を盛った箱 2 つ・歯車・ばね・置物・小箱・計器。前の梁：歯車の絵の吊り札と、吊るした歯車 2 つ。
    台の前の床：左に部品を盛った陳列箱、右に置物と箱。当たり判定は dress_solid の town/market_junk"""
    p = Part('market_junk')
    p.add('linen', boxb(-3.45, 3.45, 0.015, 0.03, -0.42, 0.43), boxb(-3.45, 3.45, -0.3, 0.03, 0.415, 0.43))
    goods_junk_crate(p, (-2.55, 0.0), 1.5, 0.66, 0.24, 0.03, seed=21, cloth=False)
    goods_junk_crate(p, (1.25, 0.02), 1.1, 0.6, 0.22, 0.03, seed=22, cloth=False)
    gear(p, (-0.95, 0.06, 0.05), 0.24, 0.06, 'y', 'graphite')
    gear(p, (-0.45, 0.05, -0.15), 0.15, 0.05, 'y', 'brass', hub='graphite')
    coil(p, (-0.5, 0.03, 0.18), 0.09, 0.16, 2.5, 'brass')
    figurine(p, (0.2, -0.05), 0.03, 0.7)
    p.add('ivory', flat_box((2.4, 0.14, -0.05), (0.32, 0.22, 0.24), 8))
    p.add('dark', flat_box((2.4, 0.17, 0.075), (0.2, 0.12, 0.01), 8))
    p.add('wood2', boxb(2.85, 3.3, 0.03, 0.2, -0.2, 0.2))
    p.add('brass', boxb(2.9, 3.25, 0.2, 0.23, -0.15, 0.15))
    # 前の梁
    hang_board(p, 0.0, 2.2, -0.05, 0.8, 0.4, 'gear', drop=0.28)
    for x in (-3.0, 3.0):
        p.add('rope', beam((x, 2.25, -0.05), (x, 1.75, -0.05), 0.02))
        gear(p, (x, 1.6, -0.05), 0.17, 0.05, 'z', 'graphite' if x < 0 else 'brass', hub='graphite' if x > 0 else 'brass')
    # 台の前の床
    goods_junk_crate(p, (-2.55, 0.72), 1.7, 0.56, 0.5, -1.1, seed=23)
    figurine(p, (2.0, 0.75), -1.1, 1.0)
    crate_open(p, (2.85, 0.75), 0.8, 0.6, 0.45, -1.1)
    heap(p, 2.5, 3.2, 0.5, 1.0, -1.04, 0.5, 24)
    return p


# ---------------------------------------------------------------- 一覧

PARTS = {
    'goods_basket': goods_basket, 'goods_basket_s': goods_basket_s, 'goods_sacks': goods_sacks, 'goods_jar': goods_jar,
    'goods_cloth': goods_cloth, 'goods_cloth_wall': goods_cloth_wall, 'goods_roll': goods_roll, 'goods_bins': goods_bins,
    'goods_scale': goods_scale, 'goods_hanging': goods_hanging, 'junk_goods': junk_goods,
    'sign_hang': sign_hang, 'sign_round': sign_round, 'sign_stand': sign_stand, 'sign_cloth': sign_cloth,
    'seat_small': seat_small, 'seat_mat': seat_mat, 'pot_succulent': pot_succulent, 'pot_shrub': pot_shrub, 'pot_vine': pot_vine,
    'diner_table': diner_table, 'diner_set_2': diner_set_2, 'diner_set_4': diner_set_4, 'toy_banki': toy_banki,
    'laundry_basket': laundry_basket, 'wind_flag': wind_flag, 'laundry_goods': laundry_goods, 'laundry_goods_8': lambda: laundry_goods(8.0),
    'market_general': market_general, 'market_junk': market_junk,
}
