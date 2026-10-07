"""町の組み合わせの部品：キットの部品（town_parts.py）を、町の場所の寸法に合わせて 1 つの GLB にまとめた物。

1 つにまとめるのは軽さのため（RoomKit は部品ごと・材質ごとに 1 回で描く。同じ部品が並ぶと MultiMesh になる）。
どれも当たり判定は無い（部屋の geometry の箱がそのまま当たり判定。ここの寸法はその箱に合わせてある）。
絵：town_mood_day.png（中段の広場）・town_facilities.png（工房・雑貨屋の正面）・town_kit_buildings.png。

原点と向き（ゲーム：+Z が正面）
  stall_*            露店の屋根の中心の真下の床。正面（+Z）が客の側
  goods_*            台・棚の上の面の中心（goods_shelf は棚の背の板の中心の床）
  parapet_rail_8/4   胸壁（1 m 厚）の上の面の中心。正面（+Z）が広場の側
  terrace_8a/b/c/4   段の壁の面の下の中心（壁の面が z=0、正面へ最大 1.6 m 出る）。高さ 16 m の壁を町の正面にする
  workshop_front     ヤーナの工房の正面（左右の棟の面 z=0、入口の奥まりは z=-2）の下の中心
  diner_front        食堂の正面の下の中心
  monument           広場の中央の台（3.2 m 角）の下の中心
  stage_8x3          広場の奥の壇（8×0.8×3）の下の中心
  stair_rail_12      階段の横の壁に付く手すり。原点 = 下の段の床・壁の面。+Z へ 12 m で 5 m 上がる
  lower_block_*      下の段の家並み（遠くから見る）。床の中心
"""
from __future__ import annotations

import math

import numpy as np

import town_parts as P
from town_geo import Part, beam, box, boxb, cyl, lathe, prism, sag, sheet, tube


# ---------------------------------------------------------------- 露店

def stall(w=8.0, d=5.2, h=3.45, ridge=0.55, name='stall') -> Part:
    """露店の枠と赤い帆布の屋根（town_mood_day の手前の露店）。柱は四隅、前の梁に吊り灯 2 つ"""
    p = Part(name)
    hx, hz = w / 2 - 0.2, d / 2 - 0.15
    for x in (-hx, hx):
        for z in (-hz, hz):
            P.post(p, x, z, 0, h + 0.15, 0.16)
    # 梁：前後は真鍮、左右は黒鉛
    for z in (-hz, hz):
        p.add('brass', beam((-hx, h - 0.1, z), (hx, h - 0.1, z), 0.09))
    for x in (-hx, hx):
        p.add('graphite', beam((x, h - 0.1, -hz), (x, h - 0.1, hz), 0.09))
    p.add('graphite', beam((0, h - 0.1, -hz), (0, h + ridge - 0.05, 0), 0.07), beam((0, h - 0.1, hz), (0, h + ridge - 0.05, 0), 0.07),
          beam((0, h + ridge - 0.05, 0), (0, h - 0.1, 0), 0.07))
    # 帆布：奥行きの真ん中が棟。柱の間でたるむ
    def roof(u, v):
        x = -w / 2 + w * u
        z = -d / 2 - 0.1 + (d + 0.2) * v
        y = h + ridge * math.sin(math.pi * v) - 0.12 * abs(math.sin(math.pi * 2 * u)) * math.sin(math.pi * v) * 0.8
        return (x, y, z)
    p.add('cloth', sheet(roof, 12, 8, 0.03))
    # 前と横の垂れ（波形）
    def valance(u, v, z0=d / 2 + 0.1):
        x = -w / 2 + w * u
        return (x, h + 0.02 - 0.42 * v * (0.72 + 0.28 * math.cos(u * math.pi * 2 * w)), z0)
    p.add('cloth', sheet(valance, int(w * 4), 1, 0.02))
    p.add('cloth2', sheet(lambda u, v: (-w / 2 + w * u, h + 0.02 - 0.3 * v, -d / 2 - 0.1), 8, 1, 0.02))
    for x in (-w / 2, w / 2):
        p.add('cloth', sheet(lambda u, v, x=x: (x, h + ridge * math.sin(math.pi * u) * 0.0 + 0.02 - 0.35 * v, -d / 2 + d * u), 6, 1, 0.02))
    # 綱（棟から柱へ）と吊り灯
    for x in (-w / 4, w / 4):
        P.lantern(p, x, h - 0.65, hz, 1.2)
        p.add('brass', cyl((x, h - 0.33, hz), (x, h - 0.1, hz), 0.012, 5))
    for x in (-hx, hx):
        p.add('rope', tube(sag((x, h + 0.1, hz), (x + (0.6 if x < 0 else -0.6), 0.0, hz + 0.9), 4, 0.1), 0.012, 4))
        p.add('graphite', boxb(x + (0.45 if x < 0 else -0.75), x + (0.75 if x < 0 else -0.45), 0, 0.06, hz + 0.75, hz + 1.05))
    return p


def goods_general(w=7.0) -> Part:
    """雑貨屋の台の上：壺・瓶・布の巻き・小箱（台の上の面の中心が原点）"""
    p = Part('goods_general')
    rng = np.random.default_rng(3)
    x = -w / 2 + 0.25
    k = 0
    while x < w / 2 - 0.3:
        kind = k % 5
        z = rng.uniform(-0.18, 0.18)
        if kind == 0:
            r = rng.uniform(0.12, 0.18)
            p.add('ivory' if k % 2 else 'brass', lathe((x, 0, z), (x, 0.42, z), [(0, r * 0.7), (0.45, r), (0.85, r * 0.55), (1, r * 0.4)], 8))
            x += r * 2 + 0.12
        elif kind == 1:
            p.add('wood2', box((x + 0.2, 0.13, z), (0.42, 0.26, 0.32), rng.uniform(-15, 15)))
            p.add('brass', box((x + 0.2, 0.27, z), (0.3, 0.03, 0.08)))
            x += 0.55
        elif kind == 2:
            p.add('cloth' if k % 3 else 'linen', cyl((x, 0.11, z - 0.2), (x, 0.11, z + 0.2), 0.11, 8))
            p.add('cloth2', cyl((x + 0.24, 0.11, z - 0.2), (x + 0.24, 0.11, z + 0.2), 0.1, 8))
            x += 0.55
        elif kind == 3:
            for j in range(3):
                p.add('dark' if j == 1 else 'green', cyl((x + j * 0.11, 0, z), (x + j * 0.11, 0.24, z), 0.045, 6))
            x += 0.45
        else:
            p.add('graphite', cyl((x + 0.15, 0, z), (x + 0.15, 0.3, z), 0.16, 10))
            p.add('brass', cyl((x + 0.15, 0.3, z), (x + 0.15, 0.34, z), 0.17, 10))
            x += 0.45
        k += 1
    p.add('linen', sheet(lambda u, v: (-w / 2 + 0.05 + (w - 0.1) * u, 0.005 if v < 0.75 else 0.005 - (v - 0.75) * 4 * 0.45,
                                       -0.42 + 0.84 * min(v, 0.75) / 0.75 + 0.03), 4, 4, 0.01))
    return p


def goods_junk(w=7.0) -> Part:
    """ジャンク屋の台の上：歯車・管の切れ端・ねじの箱・計器"""
    p = Part('goods_junk')
    x = -w / 2 + 0.3
    k = 0
    while x < w / 2 - 0.3:
        kind = k % 4
        if kind == 0:
            p.add('brass', cyl((x, 0.04, -0.05), (x, 0.1, -0.05), 0.22, 12))
            p.add('graphite', cyl((x, 0.1, -0.05), (x, 0.12, -0.05), 0.08, 8))
            x += 0.55
        elif kind == 1:
            p.add('graphite', cyl((x - 0.1, 0.08, 0.15), (x + 0.45, 0.08, -0.12), 0.07, 8))
            p.add('brass', cyl((x + 0.2, 0.08, 0.03), (x + 0.26, 0.08, 0.0), 0.09, 8))
            x += 0.6
        elif kind == 2:
            p.add('wood2', boxb(x, x + 0.45, 0, 0.18, -0.2, 0.2))
            p.add('brass', boxb(x + 0.05, x + 0.4, 0.18, 0.21, -0.15, 0.15))
            x += 0.6
        else:
            p.add('ivory', box((x + 0.15, 0.17, 0), (0.3, 0.34, 0.2), 10))
            p.add('dark', box((x + 0.15, 0.2, 0.1), (0.2, 0.16, 0.02), 10))
            p.add('amber', cyl((x + 0.15, 0.36, 0), (x + 0.15, 0.4, 0), 0.03, 6))
            x += 0.5
        k += 1
    p.add('linen', boxb(-w / 2 + 0.05, w / 2 - 0.05, -0.01, 0.005, -0.4, 0.4))
    return p


def goods_shelf(w=7.0, h=2.4, kind='general') -> Part:
    """露店の奥の箱の正面の棚（3 段）。原点 = 箱の正面の下の中心、棚は +Z へ 0.35 m"""
    p = Part(f'goods_shelf_{kind}')
    for y in (0.75, 1.35, 1.95):
        p.add('wood', boxb(-w / 2 + 0.1, w / 2 - 0.1, y - 0.05, y, 0, 0.35))
        p.add('brass', boxb(-w / 2 + 0.1, w / 2 - 0.1, y - 0.07, y - 0.05, 0.3, 0.36))
    for x in np.linspace(-w / 2 + 0.15, w / 2 - 0.15, 5):
        p.add('graphite', boxb(x - 0.04, x + 0.04, 0, h - 0.1, 0, 0.36))
    goods = goods_general(w - 0.4) if kind == 'general' else goods_junk(w - 0.4)
    for y in (0.75, 1.35, 1.95):
        p.place(goods, (0, y, 0.17), 0, (1, 0.8, 0.4))
    # 吊った布・道具
    for x in np.linspace(-w / 2 + 0.6, w / 2 - 0.6, 4):
        if kind == 'general':
            p.add('cloth2', sheet(lambda u, v, x=x: (x - 0.25 + 0.5 * u, h - 0.12 - 0.5 * v, 0.38), 2, 2, 0.01))
        else:
            p.add('graphite', boxb(x - 0.03, x + 0.03, h - 0.6, h - 0.1, 0.36, 0.42))
            p.add('brass', boxb(x - 0.09, x + 0.09, h - 0.7, h - 0.6, 0.35, 0.43))
    return p


# ---------------------------------------------------------------- 胸壁の手すり

def parapet_rail(w=8.0) -> Part:
    """胸壁（1 m 厚、高さ 1.2 m の箱）の上に立つ真鍮の手すりと、広場の側の面の黒鉛の付け柱（2 m ごと）"""
    p = Part(f'parapet_rail_{int(w)}')
    n = int(round(w / 2))
    for k in range(n + 1):
        x = -w / 2 + k * 2.0
        if abs(x) > w / 2 - 0.01:
            x = math.copysign(w / 2 - 0.1, x)
        # 付け柱（広場の側 z=+0.5 の面、床から上まで）
        p.add('graphite', boxb(x - 0.1, x + 0.1, -1.2, 0.04, 0.5, 0.56))
        p.add('brass', boxb(x - 0.13, x + 0.13, -1.2, -1.0, 0.48, 0.6), boxb(x - 0.13, x + 0.13, -0.22, -0.02, 0.48, 0.6))
        # 手すりの柱
        p.add('brass', boxb(x - 0.09, x + 0.09, 0, 0.08, -0.09, 0.09))
        p.add('brass', cyl((x, 0.08, 0), (x, 0.62, 0), 0.04, 8))
        p.add('brass', cyl((x, 0.6, 0), (x, 0.68, 0), 0.055, 8))
    p.add('brass', cyl((-w / 2 + 0.05, 0.62, 0), (w / 2 - 0.05, 0.62, 0), 0.045, 8, cap=False))
    p.add('graphite', cyl((-w / 2 + 0.05, 0.34, 0), (w / 2 - 0.05, 0.34, 0), 0.028, 6, cap=False))
    # 笠木（胸壁の上の縁、黒鉛）
    p.add('graphite', boxb(-w / 2, w / 2, -0.02, 0.0, -0.52, 0.52))
    return p


# ---------------------------------------------------------------- 段の正面（高さ 16 m の壁を町にする）

def _house_face(p: Part, x0, x1, y0, h, door_at=None, windows=(), awning=None, rng=None, depth=0.3, roof='flat'):
    """壁の面（z=0）から depth だけ出た家の正面。x0〜x1、床 y0、高さ h。窓は x の中心のリスト、扉は x"""
    w = x1 - x0
    p.add('ivory', boxb(x0 + 0.1, x1 - 0.1, y0 + 0.4, y0 + h - 0.1, 0, depth))
    p.add('wood', boxb(x0 + 0.1, x1 - 0.1, y0, y0 + 0.4, 0, depth + 0.02))
    for x in (x0 + 0.1, x1 - 0.1):
        p.add('graphite', boxb(x - 0.1, x + 0.1, y0, y0 + h, 0, depth + 0.05))
        p.add('brass', boxb(x - 0.13, x + 0.13, y0 + 0.05, y0 + 0.25, 0, depth + 0.08),
              boxb(x - 0.13, x + 0.13, y0 + h - 0.3, y0 + h - 0.1, 0, depth + 0.08))
    p.add('graphite', boxb(x0, x1, y0 + h - 0.1, y0 + h + 0.05, 0, depth + 0.12))
    if roof == 'parapet':
        p.add('ivory', boxb(x0, x1, y0 + h + 0.05, y0 + h + 0.5, depth - 0.15, depth + 0.05))
        p.add('graphite', boxb(x0, x1, y0 + h + 0.5, y0 + h + 0.56, depth - 0.18, depth + 0.08))
    for wx in windows:
        _window(p, wx, y0 + 1.0, depth)
    if door_at is not None:
        _door(p, door_at, y0, depth)
    if awning:
        ax0, ax1, ay, kind = awning
        aw = P.awning(kind, ax1 - ax0, 1.3 if kind == 'hard' else 1.5, 0.5)
        p.place(aw, ((ax0 + ax1) / 2, y0 + ay, depth))


def _window(p: Part, x, y, z):
    p.add('dark', boxb(x - 0.38, x + 0.38, y, y + 0.7, z, z + 0.01))
    p.add('graphite', boxb(x - 0.46, x + 0.46, y - 0.08, y, z, z + 0.14), boxb(x - 0.46, x + 0.46, y + 0.7, y + 0.78, z, z + 0.1),
          boxb(x - 0.46, x - 0.38, y, y + 0.7, z, z + 0.1), boxb(x + 0.38, x + 0.46, y, y + 0.7, z, z + 0.1),
          boxb(x - 0.02, x + 0.02, y, y + 0.7, z, z + 0.05))
    hinge = np.array([x, y + 0.78, z + 0.1])
    d = np.array([0, -math.cos(math.radians(55)), math.sin(math.radians(55))])
    p.add('wood', beam(hinge, hinge + d * 0.62, 0.86, 0.04, up=(0, 0, 1)))


def _door(p: Part, x, y0, z):
    p.add('wood', boxb(x - 0.45, x + 0.45, y0, y0 + 1.8, z, z + 0.04))
    p.add('graphite', boxb(x - 0.55, x - 0.45, y0, y0 + 1.9, z, z + 0.12), boxb(x + 0.45, x + 0.55, y0, y0 + 1.9, z, z + 0.12),
          boxb(x - 0.55, x + 0.55, y0 + 1.8, y0 + 1.9, z, z + 0.12))
    for k in range(1, 4):
        p.add('dark', boxb(x - 0.45 + k * 0.225 - 0.01, x - 0.45 + k * 0.225 + 0.01, y0 + 0.05, y0 + 1.75, z + 0.04, z + 0.05))
    p.add('brass', boxb(x + 0.25, x + 0.31, y0 + 0.85, y0 + 1.1, z + 0.04, z + 0.09))


def _retaining(p: Part, w, h, door_at=None, pipes=False, ladder_at=None, x_off=0.0):
    """下の段（床〜h）：2 m ごとの白磁の板・黒鉛の柱・2 m の帯。正面は z=0 の壁の面から 0.06 出る"""
    x0, x1 = -w / 2 + x_off, w / 2 + x_off
    n = int(round(w / 2))
    for k in range(n + 1):
        x = x0 + k * 2
        x = min(max(x, x0 + 0.1), x1 - 0.1)
        p.add('graphite', boxb(x - 0.1, x + 0.1, 0, h, 0, 0.1))
        for y in (0.08, 1.9, 3.9):
            if y < h - 0.2:
                p.add('brass', boxb(x - 0.13, x + 0.13, y, y + 0.2, 0, 0.13))
    for y in range(2, int(h), 2):
        p.add('graphite', boxb(x0, x1, y - 0.05, y + 0.05, 0, 0.08))
    p.add('wood', boxb(x0, x1, 0, 0.4, 0, 0.06))
    for k in range(n):
        for y in range(0, int(h) - 1, 2):
            for xx, yy in ((x0 + k * 2 + 0.45, y + 0.8), (x0 + k * 2 + 1.55, y + 1.55)):
                p.add('brass', boxb(xx - 0.05, xx + 0.05, yy - 0.09, yy + 0.09, 0, 0.035))
    if door_at is not None:
        _door(p, door_at + x_off, 0, 0.0)
    if pipes:
        for y in (2.75, 3.15):
            P.pipe_run(p, (x0, y, 0.32), (x1, y, 0.32), 0.13, 1.0)
        for x in np.arange(x0 + 1.0, x1, 2.0):
            p.add('graphite', boxb(x - 0.05, x + 0.05, 2.5, 3.4, 0, 0.3))
    if ladder_at is not None:
        p.place(P.ladder(h - 0.1), (ladder_at + x_off, 0, 0.3))


def _ledge(p: Part, x0, x1, y, out=0.7):
    """段の縁：黒鉛の梁と真鍮の手すり（上の段の床の縁）"""
    p.add('graphite', boxb(x0, x1, y - 0.35, y, 0, out))
    p.add('ivory2', boxb(x0, x1, y - 0.02, y + 0.03, 0, out - 0.05))
    for x in np.arange(x0 + 0.5, x1, 2.0):
        p.add('brass', cyl((x, y, out - 0.18), (x, y + 0.95, out - 0.18), 0.035, 6))
        p.add('graphite', boxb(x - 0.08, x + 0.08, y - 0.6, y - 0.35, 0, 0.3))
    p.add('brass', cyl((x0 + 0.05, y + 0.95, out - 0.18), (x1 - 0.05, y + 0.95, out - 0.18), 0.04, 6, cap=False))
    # 手すりの柱の小さな灯（夜の町並みの点々の明かり。town_mood_night / emergency）
    for x in np.arange(x0 + 2.5, x1, 4.0):
        p.add('amber', boxb(x - 0.05, x + 0.05, y + 0.97, y + 1.1, out - 0.23, out - 0.13))
        p.add('brass', boxb(x - 0.07, x + 0.07, y + 1.1, y + 1.14, out - 0.25, out - 0.11))
    p.add('graphite', cyl((x0 + 0.05, y + 0.55, out - 0.18), (x1 - 0.05, y + 0.55, out - 0.18), 0.025, 5, cap=False))


def terrace(variant='a', w=8.0) -> Part:
    """段の壁（高さ 16 m）を町の正面にする：下の段（擁壁、0〜5 m）、5 m の縁と手すり、中の段の家（5〜9.5 m）、
    9.5 m の縁、上の段の家（9.5〜14 m）、屋上（給水塔・柱・日よけ）。絵：town_mood_day の左の段々の町"""
    p = Part(f'terrace_{variant}')
    hw = w / 2
    rng = np.random.default_rng(ord(variant))
    # 下の段
    _retaining(p, w, 5.0, door_at={'a': -1.0, 'b': None, 'c': 2.0, 'd': None}[variant],
               pipes=variant in ('b', 'd'), ladder_at={'a': None, 'b': 2.5, 'c': None, 'd': None}[variant])
    if variant == 'a':
        p.place(P.awning('soft', 2.2, 1.4, 0.4), (-1.0, 2.6, 0.06))
        P.lantern(p, 0.4, 2.3, 0.32, 1.0)
        p.add('graphite', beam((0.4, 2.62, 0.0), (0.4, 2.62, 0.32), 0.05))
    if variant == 'c':
        p.place(P.canvas_roll(), (-1.5, 3.4, 0.06))
    # 5 m の縁
    _ledge(p, -hw, hw, 5.0, 0.75)
    # 中の段：2 軒
    if variant == 'a':
        _house_face(p, -hw, 0.2, 5.0, 4.2, door_at=-2.2, windows=(-0.6,), awning=(-3.4, -1.0, 2.6, 'hard'), depth=0.35)
        _house_face(p, 0.2, hw, 5.0, 3.6, windows=(1.4, 3.0), awning=(0.6, 3.8, 2.3, 'soft'), depth=0.25, roof='parapet')
    elif variant == 'b':
        _house_face(p, -hw, -0.6, 5.0, 3.8, windows=(-3.0, -1.6), awning=(-3.8, -0.8, 2.4, 'soft'), depth=0.3, roof='parapet')
        _house_face(p, -0.6, hw, 5.0, 4.4, door_at=1.0, windows=(2.8,), awning=(0.0, 2.0, 2.6, 'hard'), depth=0.4)
    elif variant == 'c':
        _house_face(p, -hw, -1.5, 5.0, 4.0, door_at=-3.0, windows=(-2.0,), depth=0.35)
        _house_face(p, -1.5, hw, 5.0, 3.6, windows=(0.2, 2.2), awning=(-1.2, 3.6, 2.3, 'hard'), depth=0.25, roof='parapet')
    else:
        _house_face(p, -hw, hw, 5.0, 4.0, door_at=0.0, windows=(-1.3, 1.3), awning=(-2.0, 2.0, 2.6, 'soft'), depth=0.3)
    # 鉢植え（縁の上）
    for x in rng.choice(np.arange(-hw + 0.8, hw - 0.6, 1.6), 2, replace=False):
        p.place(P.planter(0.6, 0.45), (float(x), 5.03, 0.35))
    # 9.5 m の縁
    _ledge(p, -hw, hw, 9.5, 0.55)
    # 上の段
    if variant in ('a', 'c'):
        _house_face(p, -hw + 0.5, 1.0, 9.5, 3.8, windows=(-2.6, -0.6), awning=(-3.2, 0.6, 2.3, 'hard') if variant == 'a' else None, depth=0.3, roof='parapet')
        _house_face(p, 1.0, hw, 9.5, 4.6, door_at=2.6, depth=0.4)
    else:
        _house_face(p, -hw, -1.0, 9.5, 4.4, windows=(-2.5,), awning=(-3.6, -1.4, 2.4, 'soft'), depth=0.35)
        _house_face(p, -1.0, hw - 0.5, 9.5, 3.6, windows=(0.4, 2.2), depth=0.25, roof='parapet')
    # 14 m〜：上の縁と屋上
    p.add('ivory', boxb(-hw, hw, 14.0, 15.9, 0, 0.12))
    p.add('graphite', boxb(-hw, hw, 15.9, 16.05, 0, 0.3))
    for x in np.arange(-hw + 0.1, hw, 2.0):
        p.add('graphite', boxb(x - 0.1, x + 0.1, 13.9, 16.0, 0, 0.16))
    if variant == 'a':
        p.place(P.water_tower(), (2.0, 16.0, -1.2), 0, 1.6)
        p.place(P.power_pole(4.0), (-3.0, 16.0, -0.5))
    elif variant == 'b':
        # 屋上の日よけ（4 本の柱と帆布）
        for x in (-3.4, -0.6):
            for z in (-2.6, -0.2):
                p.add('graphite', boxb(x - 0.06, x + 0.06, 16, 18.2, z - 0.06, z + 0.06))
        p.add('cloth', sheet(lambda u, v: (-3.6 + 3.2 * u, 18.2 - 0.25 * math.sin(math.pi * u) * math.sin(math.pi * v), -2.8 + 2.8 * v), 4, 4, 0.03))
        P.pipe_run(p, (2.5, 13.0, 0.4), (2.5, 18.5, 0.4), 0.14, 1.2)
        p.add('graphite', lathe((2.5, 18.5, 0.4), (2.5, 19.0, 0.4), [(0, 0.2), (1, 0.28)], 8))
    elif variant == 'c':
        for x, hh in ((-2.5, 3.0), (-1.8, 2.2)):
            P.pipe_run(p, (x, 15.0, -0.6), (x, 16 + hh, -0.6), 0.16, 1.0)
            p.add('brass', lathe((x, 16 + hh, -0.6), (x, 16 + hh + 0.5, -0.6), [(0, 0.2), (1, 0.06)], 8))
        p.add('cloth', sheet(lambda u, v: (0.5 + 3.2 * u, 16.9 - 0.9 * v - 0.15 * math.sin(math.pi * u), 0.15 + 0.6 * v), 4, 2, 0.02))
        for x in (0.5, 3.7):
            p.add('graphite', boxb(x - 0.05, x + 0.05, 16, 17.0, 0.0, 0.3))
    else:
        p.place(P.water_tower(), (-2.0, 16.0, -1.4), 0, 1.4)
    # 縁の間に洗濯綱
    if variant in ('b', 'c'):
        pts = sag((-hw + 0.4, 8.6, 0.55), (hw - 0.4, 8.2, 0.55), 10, 0.35)
        p.add('rope', tube(pts, 0.015, 4))
        for k, t in enumerate((0.2, 0.45, 0.7)):
            i = int(t * 10)
            a = pts[i]
            p.add('cloth' if k % 2 == 0 else 'linen', sheet(lambda u, v, a=a: (a[0] - 0.3 + 0.6 * u, a[1] - 0.02 - 0.6 * v, a[2]), 2, 2, 0.01))
    return p


# ---------------------------------------------------------------- 工房・食堂の正面

def workshop_front() -> Part:
    """ヤーナの工房の正面（town_facilities 左上）：太い配管が正面を横切り、屋根の上へ立ち上がる。入口の上に赤い日よけ。
    原点 = 左右の棟の正面（z=0）の下の中心。入口の奥まり（幅 3.2）の奥は z=-2、まぐさは y 3.8〜7"""
    p = Part('workshop_front')
    # 左右の棟の正面の飾り（白磁の板の上に柱と帯）
    for sx in (-1, 1):
        cx = sx * 4.3
        for x in (cx - 2.6, cx + 2.6, cx):
            p.add('graphite', boxb(x - 0.1, x + 0.1, 0, 7.0, 0, 0.12))
            for y in (0.08, 3.4, 6.6):
                p.add('brass', boxb(x - 0.13, x + 0.13, y, y + 0.22, 0, 0.15))
        p.add('graphite', boxb(cx - 2.7, cx + 2.7, 3.45, 3.55, 0, 0.1))
        p.add('wood', boxb(cx - 2.7, cx + 2.7, 0, 0.45, 0, 0.06))
        _window(p, cx - 1.2 * sx, 1.1, 0.05)
        _window(p, cx + 1.3 * sx, 4.5, 0.05)
        p.place(P.tool_rack(), (cx + 1.25 * sx, 0, 0.12))
    # 入口：奥の両開きの扉（z=-2）、まぐさの正面
    for sx in (-1, 1):
        p.add('wood', boxb(sx * 0.02, sx * 1.2, 0, 3.0, -2.0, -1.95))
        p.add('brass', boxb(sx * 0.2 - 0.04, sx * 0.2 + 0.04, 1.2, 1.6, -1.95, -1.9))
    p.add('graphite', boxb(-1.4, 1.4, 3.0, 3.8, -2.0, -1.9), boxb(-1.6, -1.3, 0, 3.8, -2.0, 0.0), boxb(1.3, 1.6, 0, 3.8, -2.0, 0.0))
    p.add('ivory2', boxb(-1.6, 1.6, 3.8, 7.0, 0, 0.08))
    # 赤い日よけ（入口の上）
    p.place(P.awning('hard', 4.2, 1.8, 0.7), (0, 3.75, 0.08))
    P.lantern(p, -2.0, 2.9, 0.4, 1.3)
    P.lantern(p, 2.0, 2.9, 0.4, 1.3)
    for x in (-2.0, 2.0):
        p.add('graphite', beam((x, 3.3, 0.0), (x, 3.3, 0.4), 0.06))
    # 太い配管：正面を横切る 2 本と、立ち上がる煙突
    # （看板の板の下の端 y≈5.95 より下を通す）
    for y, r in ((4.85, 0.28), (5.55, 0.22)):
        P.pipe_run(p, (-7.3, y, 0.4), (7.3, y, 0.4), r, 1.4)
    for x in np.arange(-6.5, 7.0, 2.2):
        p.add('graphite', boxb(x - 0.07, x + 0.07, 4.5, 5.85, 0, 0.4))
    for x, top in ((-5.6, 11.5), (-4.6, 10.0), (5.2, 12.0)):
        P.pipe_run(p, (x, 5.55, 0.45), (x, top, 0.45), 0.3, 1.3)
        p.add('brass', lathe((x, top, 0.45), (x, top + 0.6, 0.45), [(0, 0.34), (0.5, 0.4), (1, 0.18)], 10))
    # 足元：樽・タンク・木箱
    p.place(P.barrel(), (-6.3, 0, 0.7))
    p.place(P.tank(), (6.0, 0, 0.7), 90)
    p.place(P.crate(), (-3.1, 0, 0.75), 12, 0.8)
    p.place(P.crate(), (3.3, 0, 0.7), -8, 0.75)
    return p


def diner_front() -> Part:
    """食堂の正面（10 m 幅・高さ 5.5 m の棟、前に配膳台）：大きな配膳の窓、赤い日よけ、吊り灯、献立の板"""
    p = Part('diner_front')
    for x in (-4.9, -1.75, 1.75, 4.9):
        p.add('graphite', boxb(x - 0.1, x + 0.1, 0, 5.5, 0, 0.12))
        for y in (0.08, 2.6, 5.1):
            p.add('brass', boxb(x - 0.13, x + 0.13, y, y + 0.22, 0, 0.15))
    p.add('wood', boxb(-5, 5, 0, 0.4, 0, 0.06))
    p.add('graphite', boxb(-5, 5, 5.35, 5.5, 0, 0.2))
    # 配膳の窓（暗い奥・木の枠・明かり）
    p.add('dark', boxb(-1.65, 1.65, 1.1, 2.6, 0, 0.02))
    p.add('wood', boxb(-1.75, 1.75, 1.0, 1.1, 0, 0.25), boxb(-1.75, 1.75, 2.6, 2.75, 0, 0.12),
          boxb(-1.75, -1.6, 1.1, 2.6, 0, 0.12), boxb(1.6, 1.75, 1.1, 2.6, 0, 0.12))
    for x in (-3.3, 3.3):
        _window(p, x, 1.4, 0.05)
    # 日よけ
    p.place(P.awning('hard', 6.6, 2.4, 0.8), (0, 3.4, 0.1))
    P.lantern(p, -1.2, 2.55, 1.5, 1.2)
    P.lantern(p, 1.2, 2.55, 1.5, 1.2)
    for x in (-1.2, 1.2):
        p.add('brass', cyl((x, 2.86, 1.5), (x, 3.0, 1.5), 0.012, 5))
    # 献立の板（白磁の縁、黒鉛の面）
    p.add('graphite', boxb(2.3, 3.9, 3.7, 4.7, 0, 0.08))
    p.add('ivory', boxb(2.4, 3.8, 3.8, 4.6, 0.08, 0.1))
    for k in range(3):
        p.add('wood', boxb(2.55, 3.65, 4.4 - k * 0.22, 4.46 - k * 0.22, 0.1, 0.11))
    # 屋根の上の煙突と給水
    P.pipe_run(p, (-3.8, 6.0, -1.0), (-3.8, 8.4, -1.0), 0.22, 1.0)
    p.add('brass', lathe((-3.8, 8.4, -1.0), (-3.8, 8.8, -1.0), [(0, 0.26), (1, 0.1)], 8))
    p.place(P.water_tower(), (3.0, 6.0, -4.0), 0, 1.2)
    return p


# ---------------------------------------------------------------- 広場

def monument() -> Part:
    """広場の中央：白磁の台（3.2 m 角・高さ 1 m）に、真鍮と黒鉛の機械の柱。頂に灯（town_mood_day の中央）"""
    p = Part('monument')
    # 台の縁取り（台の箱そのものは部屋の形。ここは角の柱と真鍮の帯）
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('graphite', boxb(sx * 1.6 - 0.12, sx * 1.6 + 0.12, 0, 1.06, sz * 1.6 - 0.12, sz * 1.6 + 0.12))
            p.add('brass', boxb(sx * 1.6 - 0.15, sx * 1.6 + 0.15, 0.85, 1.1, sz * 1.6 - 0.15, sz * 1.6 + 0.15))
    p.add('brass', boxb(-1.62, 1.62, 1.0, 1.06, -1.62, 1.62))
    # 機械の柱（真ん中の 1 m 角の箱を包む）
    p.add('ivory2', boxb(-0.62, 0.62, 1.06, 1.5, -0.62, 0.62))
    p.add('brass', lathe((0, 1.5, 0), (0, 3.7, 0), [(0, 0.62), (0.08, 0.56), (0.5, 0.52), (0.92, 0.56), (1, 0.66)], 12))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        x, z = 0.66 * math.cos(a), 0.66 * math.sin(a)
        p.add('graphite', cyl((x, 1.06, z), (x, 4.2, z), 0.11, 8))
        p.add('brass', cyl((x, 2.2, z), (x, 2.35, z), 0.15, 8), cyl((x, 3.3, z), (x, 3.45, z), 0.15, 8))
    for y in (2.0, 3.0):
        p.add('graphite', cyl((0, y, 0), (0, y + 0.12, 0), 0.6, 12))
    p.add('graphite', lathe((0, 3.7, 0), (0, 4.4, 0), [(0, 0.7), (1, 0.45)], 12))
    p.add('brass', cyl((0, 4.4, 0), (0, 4.55, 0), 0.5, 12))
    # 頂の灯（部屋の明かり (0, 5.6, 2) の位置）
    for k in range(4):
        a = k * math.pi / 2
        p.add('brass', beam((0.38 * math.cos(a), 4.55, 0.38 * math.sin(a)), (0.3 * math.cos(a), 5.75, 0.3 * math.sin(a)), 0.05))
    p.add('amber', cyl((0, 4.6, 0), (0, 5.7, 0), 0.24, 10))
    p.add('brass', lathe((0, 5.7, 0), (0, 6.2, 0), [(0, 0.42), (0.6, 0.3), (1, 0.06)], 12))
    # 4 本の腕と吊り灯
    for k in range(4):
        a = k * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        p.add('graphite', beam((0.6 * c, 3.9, 0.6 * s), (1.45 * c, 3.9, 1.45 * s), 0.08))
        P.lantern(p, 1.45 * c, 3.45, 1.45 * s, 1.0)
    # 床の円（真鍮の輪）は plaza_ring
    return p


def plaza_ring(r=6.0) -> Part:
    """広場の床の円の模様（白磁の 2 段目の帯と真鍮の輪）。床の上 1 cm"""
    p = Part('plaza_ring')
    seg = 48
    def ring(r0, r1, y, mat):
        v, f = [], []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            v += [(r0 * math.cos(a), y, r0 * math.sin(a)), (r1 * math.cos(a), y, r1 * math.sin(a))]
        for k in range(seg):
            i, j = 2 * k, 2 * ((k + 1) % seg)
            f.append([i, j, j + 1, i + 1])
        from town_geo import Piece
        pc = Piece(np.array(v, float), f)
        n = np.cross(pc.v[f[0][1]] - pc.v[f[0][0]], pc.v[f[0][3]] - pc.v[f[0][0]])
        if n[1] < 0:
            pc.f = [x[::-1] for x in pc.f]
        p.add(mat, pc)
    ring(r - 0.8, r, 0.012, 'ivory2')
    ring(r - 0.12, r + 0.08, 0.018, 'brass')
    ring(r - 0.95, r - 0.8, 0.018, 'brass')
    ring(2.6, 2.8, 0.018, 'brass')
    return p


def stage(w=8.0, d=3.0, h=0.8) -> Part:
    """広場の奥の壇（8×0.8×3）の縁：黒鉛の角、真鍮の帯、前の 2 段の踏み段、両脇の旗竿と旗"""
    p = Part('stage')
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('graphite', boxb(sx * w / 2 - 0.12, sx * w / 2 + 0.12, 0, h + 0.04, sz * d / 2 - 0.12, sz * d / 2 + 0.12))
    p.add('brass', boxb(-w / 2, w / 2, h - 0.06, h + 0.02, -d / 2 - 0.03, -d / 2 + 0.03),
          boxb(-w / 2, w / 2, h - 0.06, h + 0.02, d / 2 - 0.03, d / 2 + 0.03))
    p.add('wood', boxb(-w / 2 + 0.1, w / 2 - 0.1, h, h + 0.04, -d / 2 + 0.1, d / 2 - 0.1))
    for x in np.arange(-w / 2 + 2, w / 2, 2.0):
        p.add('graphite', boxb(x - 0.08, x + 0.08, 0, h, -d / 2 - 0.04, -d / 2))
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.35)
        p.add('graphite', cyl((x, h, d / 2 - 0.35), (x, h + 4.2, d / 2 - 0.35), 0.06, 8))
        p.add('brass', lathe((x, h + 4.2, d / 2 - 0.35), (x, h + 4.4, d / 2 - 0.35), [(0, 0.08), (1, 0.02)], 8))
        p.add('graphite', beam((x, h + 4.0, d / 2 - 0.35), (x - sx * 0.9, h + 4.0, d / 2 - 0.35), 0.05))
        p.add('cloth', sheet(lambda u, v, x=x, sx=sx: (x - sx * (0.1 + 0.75 * u), h + 3.95 - 1.6 * v, d / 2 - 0.35 + 0.05 * math.sin(v * 3)), 2, 4, 0.02))
        p.add('brass', sheet(lambda u, v, x=x, sx=sx: (x - sx * (0.32 + 0.3 * u), h + 3.4 - 0.3 * v, d / 2 - 0.35 + 0.05 * math.sin(v * 3) + 0.015), 1, 1, 0.01))
    return p


def stair_rail_r() -> Part:
    """stair_rail の左右反転（階段の右の壁に付く。-X が階段の側）"""
    src = stair_rail()
    p = Part('stair_rail_12_r')
    p.place(src, (0, 0, 0), 0, (-1, 1, 1))
    return p


def retaining(w=8.0, h=5.0, variant='a') -> Part:
    """段の擁壁（下の段から見た上の段の縁）：2 m ごとの白磁の板・黒鉛の柱・帯。b は配管つき"""
    p = Part(f'retaining_{variant}')
    _retaining(p, w, h, door_at=-1.0 if variant == 'c' else None, pipes=variant == 'b')
    return p


def stair_rail(L=12.0, rise=5.0) -> Part:
    """階段の横の壁に付く真鍮の手すり（壁の面 z… ではなく x=0 の面に付く。+X が階段の側）。下の段の床から +Z へ L m で rise 上がる"""
    p = Part('stair_rail_12')
    a = np.array([0.18, 1.0, 0.0])
    b = np.array([0.18, 1.0 + rise, L])
    p.add('brass', cyl(a + [0, 0, -0.6], a, 0.045, 8), cyl(a, b, 0.045, 8, cap=False), cyl(b, b + [0, 0, 0.6], 0.045, 8))
    p.name = 'stair_rail_12'
    for t in np.linspace(0.05, 0.95, 5):
        c = a + (b - a) * t
        p.add('graphite', beam((0, c[1] - 0.1, c[2]), (0.18, c[1] - 0.04, c[2]), 0.06))
        p.add('brass', boxb(0, 0.04, c[1] - 0.22, c[1] + 0.02, c[2] - 0.1, c[2] + 0.1))
    # 壁の灯（中ほど）
    m = a + (b - a) * 0.5
    p.add('graphite', beam((0, m[1] + 1.4, m[2] + 1.0), (0.4, m[1] + 1.4, m[2] + 1.0), 0.06))
    P.lantern(p, 0.42, m[1] + 1.05, m[2] + 1.0, 1.0)
    return p


# ---------------------------------------------------------------- 下の段の家並み（胸壁の向こうに見える）

def lower_block(variant='a') -> Part:
    """下の段の家並み（10×8 m ほど）：白磁の箱の家 3〜4 軒、平屋根・帆布の日よけ・給水槽。遠くから見る物なので細部は少ない"""
    p = Part(f'lower_block_{variant}')
    rng = np.random.default_rng(10 + ord(variant))
    houses = {'a': [(-3.5, -1.0, 3.0, 4.0, 3.2), (0.5, -0.5, 4.0, 5.0, 4.6), (3.8, 1.5, 2.6, 3.4, 2.8), (-1.5, 2.8, 3.4, 2.2, 2.6)],
              'b': [(-3.0, 0.0, 4.0, 5.0, 3.8), (1.5, -1.5, 3.2, 3.2, 3.0), (2.8, 2.0, 3.6, 3.0, 5.2)],
              'c': [(-3.8, 1.0, 2.6, 4.0, 2.9), (-0.6, 0.0, 3.4, 5.6, 4.2), (3.2, -1.2, 3.4, 3.6, 3.4), (2.0, 2.8, 4.0, 2.0, 2.4)]}[variant]
    for cx, cz, w, d, h in houses:
        p.add('ivory', boxb(cx - w / 2, cx + w / 2, 0, h, cz - d / 2, cz + d / 2))
        p.add('graphite', boxb(cx - w / 2 - 0.05, cx + w / 2 + 0.05, h, h + 0.15, cz - d / 2 - 0.05, cz + d / 2 + 0.05))
        for sx in (-1, 1):
            for sz in (-1, 1):
                p.add('graphite', boxb(cx + sx * w / 2 - 0.12, cx + sx * w / 2 + 0.12, 0, h + 0.15, cz + sz * d / 2 - 0.12, cz + sz * d / 2 + 0.12))
        p.add('wood', boxb(cx - w / 2 - 0.02, cx + w / 2 + 0.02, 0, 0.4, cz - d / 2 - 0.02, cz + d / 2 + 0.02))
        # 正面（+Z と -Z の両方）に窓
        for zf, s in ((cz + d / 2, 1), (cz - d / 2, -1)):
            for wx in np.arange(cx - w / 2 + 0.9, cx + w / 2 - 0.5, 1.4):
                p.add('dark', boxb(wx - 0.3, wx + 0.3, h * 0.45, h * 0.45 + 0.6, min(zf, zf + s * 0.02), max(zf, zf + s * 0.02)))
        # 屋根の上：日よけか給水槽
        if rng.random() < 0.55:
            y = h + 0.15
            p.add('cloth' if rng.random() < 0.6 else 'cloth2',
                  sheet(lambda u, v, cx=cx, cz=cz, w=w, d=d, y=y: (cx - w * 0.4 + w * 0.8 * u, y + 1.6 - 0.25 * math.sin(math.pi * u) * math.sin(math.pi * v),
                                                                  cz - d * 0.4 + d * 0.8 * v), 3, 3, 0.03))
            for sx in (-1, 1):
                for sz in (-1, 1):
                    p.add('graphite', boxb(cx + sx * w * 0.4 - 0.05, cx + sx * w * 0.4 + 0.05, y, y + 1.6, cz + sz * d * 0.4 - 0.05, cz + sz * d * 0.4 + 0.05))
        else:
            p.add('brass', cyl((cx + w * 0.2, h + 0.15, cz), (cx + w * 0.2, h + 1.3, cz), 0.5, 10))
        # 低い手すり（屋上）
        p.add('brass', cyl((cx - w / 2, h + 0.9, cz + d / 2), (cx + w / 2, h + 0.9, cz + d / 2), 0.03, 5, cap=False))
    return p


def deck_slab(w=96.0, d=40.0) -> Part:
    """下の段の床（遠くから見る）：白磁の床の板と、外の縁の黒鉛の帯。床の上の面 y=0"""
    p = Part('deck_slab')
    p.add('ivory2', boxb(-w / 2, w / 2, -0.6, 0, -d / 2, d / 2))
    p.add('graphite', boxb(-w / 2, w / 2, -1.2, -0.6, -d / 2, d / 2))
    for x in np.arange(-w / 2, w / 2 + 0.1, 8.0):
        p.add('graphite', boxb(x - 0.08, x + 0.08, -0.02, 0.01, -d / 2, d / 2))
    for z in np.arange(-d / 2, d / 2 + 0.1, 8.0):
        p.add('graphite', boxb(-w / 2, w / 2, -0.02, 0.01, z - 0.08, z + 0.08))
    return p


SETS = {
    'stall': stall, 'goods_general': goods_general, 'goods_junk': goods_junk,
    'goods_shelf_general': lambda: goods_shelf(7.0, 2.4, 'general'), 'goods_shelf_junk': lambda: goods_shelf(7.0, 2.4, 'junk'),
    'parapet_rail_8': lambda: parapet_rail(8.0), 'parapet_rail_4': lambda: parapet_rail(4.0),
    'terrace_a': lambda: terrace('a'), 'terrace_b': lambda: terrace('b'), 'terrace_c': lambda: terrace('c'), 'terrace_d': lambda: terrace('d'),
    'workshop_front': workshop_front, 'diner_front': diner_front, 'monument': monument, 'plaza_ring': plaza_ring, 'stage': stage,
    'stair_rail_12': stair_rail, 'stair_rail_12_r': stair_rail_r,
    'retaining_a': lambda: retaining(8, 5, 'a'), 'retaining_b': lambda: retaining(8, 5, 'b'), 'retaining_c': lambda: retaining(8, 5, 'c'),
    'terrace_4': lambda: terrace('d', 4.0), 'lower_block_a': lambda: lower_block('a'), 'lower_block_b': lambda: lower_block('b'),
    'lower_block_c': lambda: lower_block('c'), 'deck_slab': deck_slab,
}
