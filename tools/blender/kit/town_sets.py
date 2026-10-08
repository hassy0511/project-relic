"""町の組み合わせの部品：キットの部品（town_parts.py）を、町の場所の寸法に合わせて 1 つの GLB にまとめた物。

1 つにまとめるのは軽さのため（RoomKit は部品ごと・材質ごとに 1 回で描く。同じ部品が並ぶと MultiMesh になる）。
どれも当たり判定は無い（部屋の geometry の箱がそのまま当たり判定。ここの寸法はその箱に合わせてある）。
絵：town_mood_day.png（中段の広場）・town_facilities.png（工房・雑貨屋の正面）・town_kit_buildings.png。

原点と向き（ゲーム：+Z が正面）
  stall_*            露店の屋根の中心の真下の床。正面（+Z）が客の側
  goods_*            台・棚の上の面の中心（goods_shelf は棚の背の板の中心の床）
  parapet_rail_8/4   胸壁（1 m 厚）の上の面の中心。正面（+Z）が広場の側
  （北の段の壁の家並み・南の階段の両側の棟は town_terrace.py。部屋の座標のまま置く）
  workshop_front     ヤーナの工房の正面（左右の棟の面 z=0、入口の奥まりは z=-2）の下の中心。裏（z=-9）の窓・配管も
  diner_front        食堂の正面の下の中心。両側（x=±5）と裏（z=-9）の窓・扉・配管も
  monument           広場の中央の台（3.2 m 角）の下の中心
  stage_8x3          広場の奥の壇（8×0.8×3）の下の中心
  stair_rail_12      階段の横の壁に付く手すり。原点 = 下の段の床・壁の面。+Z へ 12 m で 5 m 上がる
  stair_treads_16    階段（当たり判定の stairs 8×5×12・16 段）の踏み段の縁。原点 = stairs の pos（底の中心）。+Z が上り
  lower_block_*      下の段の家並み（town_terrace.py）。床の中心
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
    # 裏（奥の箱の裏の面 z=-2.8。前は木の板の箱の面だけだった）：黒鉛の枠、掛けた帆布、積んだ木箱と樽
    zb = -2.8
    for x in (-3.42, -1.15, 1.15, 3.42):
        p.add('graphite', boxb(x - 0.08, x + 0.08, 0, 2.4, zb - 0.08, zb))
    p.add('graphite', boxb(-3.5, 3.5, 2.3, 2.45, zb - 0.1, zb), boxb(-3.5, 3.5, 0, 0.12, zb - 0.06, zb))
    p.add('cloth2', sheet(lambda u, v: (-2.2 + 2.6 * u, 2.38 - 1.5 * v - 0.12 * math.sin(math.pi * u) * v, zb - 0.06 - 0.05 * v), 4, 3, 0.02))
    p.place(P.canvas_roll(), (1.9, 2.25, zb), 180, 0.7)
    p.place(P.crate(), (-2.6, 0, zb - 0.55), 8)
    p.place(P.crate(), (-2.5, 0.74, zb - 0.55), -6, 0.8)
    p.place(P.barrel(), (2.7, 0, zb - 0.5), 0, 0.85)
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
    # 台の上の布：台の上の面（y=0）より 2 cm 上、前後の面より 2 cm 外（台の箱の面と重ならない）
    p.add('linen', boxb(-w / 2 + 0.05, w / 2 - 0.05, -0.005, 0.02, -0.42, 0.42))
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
    # 笠木（胸壁の上の両側の縁、黒鉛の細い帯）。胸壁の箱の上の面（y=0）より 2 cm 上へ出す。前は上の面いっぱいの板で、
    # 箱の上の面と同じ高さにあって重なってちらついた（見る向きで白と黒鉛がまだらに入れ替わった）。真ん中は箱の上の面（白磁の床）が見える
    for z0, z1 in ((-0.52, -0.36), (0.36, 0.52)):
        p.add('graphite', boxb(-w / 2, w / 2, -0.04, 0.02, z0, z1))
    return p


# ---------------------------------------------------------------- 段の正面（高さ 16 m の壁を町にする）

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


# ---------------------------------------------------------------- 工房・食堂の正面

def workshop_front() -> Part:
    """ヤーナの工房の正面（town_facilities 左上）：太い配管が正面を横切り、屋根の上へ立ち上がる。入口の上に赤い日よけ。
    原点 = 左右の棟の正面（z=0）の下の中心。入口の奥まり（幅 3.2）の奥は z=-2、まぐさは y 3.8〜7"""
    p = Part('workshop_front')
    # 左右の棟の正面の飾り（白磁の板の上に柱と帯）
    for sx in (-1, 1):
        cx = sx * 4.3
        for x in (cx - 2.6, cx + 2.6, cx):
            # 外の端の柱は棟の横の面（x = ±7.0）より 2 cm 外へ（横の面と同じ所だと重なってちらついた）
            out = 0.02 if abs(x) > 6.5 else 0.0
            p.add('graphite', boxb(x - 0.1 - (out if x < 0 else 0), x + 0.1 + (out if x > 0 else 0), 0, 7.0, 0, 0.12))
            for y in (0.08, 3.4, 6.6):
                p.add('brass', boxb(x - 0.13, x + 0.13, y, y + 0.22, 0, 0.15))
        p.add('graphite', boxb(cx - 2.7 - (0.03 if sx < 0 else 0), cx + 2.7 + (0.03 if sx > 0 else 0), 3.45, 3.55, 0, 0.1))
        p.add('wood', boxb(cx - 2.7 - (0.03 if sx < 0 else 0), cx + 2.7 + (0.03 if sx > 0 else 0), 0, 0.45, 0, 0.06))
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
    # 裏（z=-9、北の段の壁との間の 3 m の路地に向く面）：窓・裏口・配管
    import town_terrace as T
    T.face(p, '-z', (0, 0, -9.0), {'simple': True, 'posts': [-6.88, -1.6, 1.6, 6.88], 'door': -4.4,
                                   'windows': [(-2.6, 1.1), (3.0, 1.1), (5.4, 1.1), (-5.4, 4.5), (-2.6, 4.5), (0.0, 4.5), (3.0, 4.5), (5.4, 4.5)],
                                   'lanterns': [(-3.45, 1.95)], 'pipes': [1.0], 'vents': [(-0.4, 2.0)], 'bands': [3.45]}, 14.0, 7.0)
    for y, r in ((6.2, 0.2),):
        P.pipe_run(p, (-7.2, y, -9.35), (7.2, y, -9.35), r, 1.4)
    return p


def diner_front() -> Part:
    """食堂の正面（10 m 幅・高さ 5.5 m の棟、前に配膳台）：大きな配膳の窓、赤い日よけ、吊り灯、献立の板"""
    p = Part('diner_front')
    for x in (-4.9, -1.75, 1.75, 4.9):
        # 両端の柱は棟の横の面（x = ±5）より 2 cm 外へ（横の面と同じ所だと重なってちらついた）
        out = 0.02 if abs(x) > 4.5 else 0.0
        p.add('graphite', boxb(x - 0.1 - (out if x < 0 else 0), x + 0.1 + (out if x > 0 else 0), 0, 5.5, 0, 0.12))
        for y in (0.08, 2.6, 5.1):
            p.add('brass', boxb(x - 0.13, x + 0.13, y, y + 0.22, 0, 0.15))
    p.add('wood', boxb(-5.03, 5.03, 0, 0.4, 0, 0.06))
    p.add('graphite', boxb(-5.03, 5.03, 5.35, 5.5, 0, 0.2))
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
    # 両側（x=±5）と裏（z=-9）：前は窓の側だけ作ってあり、横と裏は何も無い白い壁だった
    import town_terrace as T
    side = {'simple': True, 'posts': [-4.38, 0.0, 4.38], 'windows': [(-2.0, 1.3), (2.0, 1.3), (-2.0, 3.4), (2.0, 3.4)], 'bands': [2.6]}
    T.face(p, '+x', (5.0, 0, -4.5), dict(side, pipes=[3.3]), 9.0, 5.5)
    T.face(p, '-x', (-5.0, 0, -4.5), dict(side, vents=[(3.2, 4.3)]), 9.0, 5.5)
    T.face(p, '-z', (0, 0, -9.0), {'simple': True, 'posts': [-4.88, 0.0, 4.88], 'door': 2.4, 'windows': [(-3.3, 1.3), (-1.2, 1.3), (-3.3, 3.4), (3.3, 3.4)],
                                   'awnings': [(1.5, 3.3, 2.35, 'hard')], 'lanterns': [(3.35, 1.95)], 'vents': [(1.2, 3.7)],
                                   'pipes': [-4.4], 'bands': [2.6]}, 10.0, 5.5)
    for x0, x1 in ((-5.0, 5.0),):
        p.add('wood', boxb(x0 - 0.03, x1 + 0.03, 0, 0.4, -9.03, -8.97))
    p.place(P.barrel(), (0.9, 0, -9.55), 0, 0.85)
    p.place(P.crate(), (-0.6, 0, -9.6), 12, 0.8)
    p.place(P.crate(), (-0.6, 0.6, -9.6), -8, 0.7)
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
    # 正面と両横の足元の黒鉛の帯（幅木）と、板の間の真鍮の留め板。前は低いカメラから見ると、正面が模様の無い一枚の面だった
    # （広場の床の板 0.08 m に下が埋まるので、帯は 0.2 m まで）
    p.add('graphite', boxb(-w / 2 + 0.12, w / 2 - 0.12, 0, 0.2, -d / 2 - 0.025, -d / 2 + 0.1))
    for sx in (-1, 1):
        xa, xb = sorted((sx * (w / 2 + 0.025), sx * (w / 2 - 0.1)))
        p.add('graphite', boxb(xa, xb, 0, 0.2, -d / 2 + 0.12, d / 2 - 0.12))
    for x in np.arange(-w / 2 + 1, w / 2, 2.0):
        for y in (0.3, 0.56):
            p.add('brass', boxb(x - 0.05, x + 0.05, y - 0.06, y + 0.06, -d / 2 - 0.02, -d / 2 + 0.01))
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.35)
        p.add('graphite', cyl((x, h, d / 2 - 0.35), (x, h + 4.2, d / 2 - 0.35), 0.06, 8))
        p.add('brass', lathe((x, h + 4.2, d / 2 - 0.35), (x, h + 4.4, d / 2 - 0.35), [(0, 0.08), (1, 0.02)], 8))
        p.add('graphite', beam((x, h + 4.0, d / 2 - 0.35), (x - sx * 0.9, h + 4.0, d / 2 - 0.35), 0.05))
        p.add('cloth', sheet(lambda u, v, x=x, sx=sx: (x - sx * (0.1 + 0.75 * u), h + 3.95 - 1.6 * v, d / 2 - 0.35 + 0.05 * math.sin(v * 3)), 2, 4, 0.02))
        p.add('brass', sheet(lambda u, v, x=x, sx=sx: (x - sx * (0.32 + 0.3 * u), h + 3.4 - 0.3 * v, d / 2 - 0.35 + 0.05 * math.sin(v * 3) + 0.015), 1, 1, 0.01))
    return p


def stair_treads(w=8.0, rise=5.0, run=12.0, n=16) -> Part:
    """階段（当たり判定の "stairs"：幅 w・高さ rise・長さ run・n 段、+Z へ上る）の踏み段の縁：段ごとに黒鉛の段鼻と、両端の真鍮の留め金。
    前は蹴上げが模様の無い同じ色の面で、低いカメラ（階段の足元で見上げる）から踏み面が隠れると、16 段が 1 枚のくさびに見えた。
    段鼻は踏み面より 1.5 cm 上・蹴上げより 3 cm 前（当たり判定の面と重ならない）。原点 = stairs の pos（底の中心）"""
    p = Part(f'stair_treads_{n}')
    hw = w / 2 - 0.03                                  # 横の壁の面（|x| = w/2）から 3 cm 手前まで
    for i in range(n):
        y = rise * (i + 1) / n
        z = -run / 2 + run * i / n                     # 段 i の蹴上げの面
        p.add('graphite', boxb(-hw, hw, y - 0.075, y + 0.015, z - 0.03, z + 0.08))
        # 留め金は横の壁の付け柱（壁から 0.14 m）に当たらない所に
        for sx in (-1, 1):
            xa, xb = sorted((sx * (w / 2 - 0.3), sx * (w / 2 - 0.16)))
            p.add('brass', boxb(xa, xb, y - 0.06, y + 0.025, z - 0.045, z + 0.1))
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
    # 擁壁そのものの面（前は飾りだけで、外から見ると柱の間から向こうが透けた）。奥へ 1 m の箱
    p.add('shell', boxb(-w / 2, w / 2, 0, h, -1.0, 0))
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


# ---------------------------------------------------------------- 下の段の床（家並み lower_block_* は town_terrace.py）

def deck_slab(w=96.0, d=41.3) -> Part:
    """下の段の床（遠くから見る）：白磁の床の板と、外の縁の黒鉛の帯。床の上の面 y=0。
    北の縁は擁壁の面（z=-15）より 0.3 m 奥（擁壁の下）まで入れる（縁の面が南の階段の棟の面と同じ所で重ならない）"""
    p = Part('deck_slab')
    p.add('ivory2', boxb(-w / 2, w / 2, -0.6, 0, -d / 2, d / 2))
    p.add('graphite', boxb(-w / 2, w / 2, -1.2, -0.6, -d / 2, d / 2))
    for x in np.arange(-w / 2, w / 2 + 0.1, 8.0):
        p.add('graphite', boxb(x - 0.08, x + 0.08, -0.02, 0.01, -d / 2, d / 2))
    for z in np.arange(-d / 2, d / 2 + 0.1, 8.0):
        p.add('graphite', boxb(-w / 2, w / 2, -0.02, 0.01, z - 0.08, z + 0.08))
    return p


def window_frame() -> Part:
    """窓だけ（壁に貼る）：暗い奥・黒鉛の枠・上へ開いた木の雨戸。原点 = 窓の下の縁の中心・壁の面"""
    p = Part('window_frame')
    _window(p, 0, 0, 0.0)
    p.add('ivory2', boxb(-0.5, 0.5, -0.14, -0.06, 0, 0.2))
    return p


def tent(w=4.0, d=3.0, h=2.6) -> Part:
    """立った日よけ（広場の露店の天幕、town_mood_day の左の天幕）：4 本の真鍮の柱と赤い帆布、下に台と木箱"""
    p = Part('tent')
    hx, hz = w / 2 - 0.1, d / 2 - 0.1
    for x in (-hx, hx):
        for z in (-hz, hz):
            p.add('brass', cyl((x, 0, z), (x, h + 0.25, z), 0.05, 8))
            p.add('graphite', boxb(x - 0.12, x + 0.12, 0, 0.11, z - 0.12, z + 0.12))     # 広場の床の板（0.08）より高く
    p.add('cloth', sheet(lambda u, v: (-w / 2 - 0.1 + (w + 0.2) * u, h + 0.35 * math.sin(math.pi * v) - 0.12 * math.sin(math.pi * u) * math.sin(math.pi * v),
                                       -d / 2 - 0.1 + (d + 0.2) * v), 8, 6, 0.03))
    p.add('cloth', sheet(lambda u, v: (-w / 2 - 0.1 + (w + 0.2) * u, h + 0.02 - 0.32 * v * (0.72 + 0.28 * math.cos(u * math.pi * 2 * w)), d / 2 + 0.1), int(w * 4), 1, 0.02))
    p.place(P.stall_table(2.0), (0, 0, -0.3))
    p.place(goods_general(1.8), (0, 0.955, -0.45), 0, (1, 1, 0.6))
    p.place(P.crate(), (-1.4, 0, 0.6), 10, 0.7)
    p.place(P.barrel(), (1.4, 0, 0.5), 0, 0.8)
    P.lantern(p, 0, h - 0.35, 0, 1.0)
    p.add('brass', cyl((0, h - 0.05, 0), (0, h + 0.3, 0), 0.012, 5))
    return p


SETS = {
    'window_frame': window_frame, 'tent': tent, 'planter_big': lambda: P.planter(1.2, 0.95),
    'stall': stall, 'goods_general': goods_general, 'goods_junk': goods_junk,
    'goods_shelf_general': lambda: goods_shelf(7.0, 2.4, 'general'), 'goods_shelf_junk': lambda: goods_shelf(7.0, 2.4, 'junk'),
    'parapet_rail_8': lambda: parapet_rail(8.0), 'parapet_rail_4': lambda: parapet_rail(4.0),
    'workshop_front': workshop_front, 'diner_front': diner_front, 'monument': monument, 'plaza_ring': plaza_ring, 'stage': stage,
    'stair_rail_12': stair_rail, 'stair_rail_12_r': stair_rail_r, 'stair_treads_16': stair_treads,
    'retaining_a': lambda: retaining(8, 5, 'a'), 'retaining_b': lambda: retaining(8, 5, 'b'), 'retaining_c': lambda: retaining(8, 5, 'c'),
    'deck_slab': deck_slab,
}
