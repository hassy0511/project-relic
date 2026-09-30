"""番機を「閂のやり方」で組む：部品ごとに、きれいな形（楕円体の板・旋盤の形・面取りの箱・円柱）を絵の寸法に合わせて置き、
小さな形ごとに平らな材質 1 つ（白磁・真鍮・黒鉛・琥珀の発光）。テクスチャ・視体積・色の投票は使わない。

  banki.py から呼ばれる（既定）。BANKI_MODEL=hull で従来の視体積＋領域の色に戻す。
  .venv-blender/bin/python tools/blender/recon/banki.py --type sentry --review

■ 約束（banki.py・閂と同じ）
  座標は cm（書き出しは m）。原点 = 足もとの中心、正面 -Y、上 +Z、+X = 正面の絵の右（本人の左）。
  部品の原点 = 回転軸、ローカル +X = 回転軸の向き。部品の名前・親子は enemy_view.gd が使うものと同じ。
  板と板の継ぎ目は、黒鉛の芯の上に白磁の板を少し隙間を空けて貼る（隙間から黒鉛が見える = 絵の暗い継ぎ目）。
  真鍮の縁は、板の縁に沿った細い帯（別の形）。発光は 'sensor'・'core' という名前の物体（Godot で色を変える）。
■ 寸法は絵（r2、歩哨型は 16 px/cm）の上に 5 cm の格子を重ねて測った（build_views と同じ投影）。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import banki as B   # noqa: E402
import kannuki as K   # noqa: E402  lathe・cyl・box・extrude・merge・orient を使い回す（単位は何でもよい）

V3 = np.array
lathe, cyl, box, extrude, merge, orient = K.lathe, K.cyl, K.box, K.extrude, K.merge, K.orient
IVORY = '#E9DFC9'


def log(msg):
    print(f'[banki_parts] {msg}', flush=True)


# ---------------------------------------------------------------- 形の道具（cm）

def ell_point(c, ax, th, ph, grow=0.0):
    """楕円体（中心 c・半径 ax = (x, y, z上, z下)）の上の点。th = 上からの角、ph = 正面（-Y）から +X へ回る角。grow：外へ膨らませる cm"""
    st, ct = math.sin(th), math.cos(th)
    az = ax[2] if ct >= 0 else ax[3]
    return V3([c[0] + (ax[0] + grow) * st * math.sin(ph), c[1] - (ax[1] + grow) * st * math.cos(ph), c[2] + (az + grow) * ct])


def ell_plate(c, ax, th0, th1, ph0, ph1, thick=1.2, grow=0.0, dth=10.0, dph=12.0):
    """楕円体の上の板（厚み thick）。ph0・ph1 は数（度）か、th（度）の関数。角は度"""
    f0 = ph0 if callable(ph0) else (lambda t, v=ph0: v)
    f1 = ph1 if callable(ph1) else (lambda t, v=ph1: v)
    nv = max(2, int(math.ceil((th1 - th0) / dth)))
    span = max(abs(f1(t) - f0(t)) for t in np.linspace(th0, th1, nv + 1))
    nu = max(2, int(math.ceil(span / dph)))
    verts = []
    for g in (grow, grow - thick):
        for i in range(nv + 1):
            t = th0 + (th1 - th0) * i / nv
            a, b = f0(t), f1(t)
            for j in range(nu + 1):
                p = a + (b - a) * j / nu
                verts.append(ell_point(c, ax, math.radians(t), math.radians(p), g))
    W = nu + 1
    n1 = (nv + 1) * W
    idx = lambda s, i, j: s * n1 + i * W + j
    faces = []
    for i in range(nv):
        for j in range(nu):
            faces.append([idx(0, i, j), idx(0, i, j + 1), idx(0, i + 1, j + 1), idx(0, i + 1, j)])
            faces.append([idx(1, i, j), idx(1, i + 1, j), idx(1, i + 1, j + 1), idx(1, i, j + 1)])
    for i in range(nv):   # 左右の縁
        for j in (0, nu):
            faces.append([idx(0, i, j), idx(0, i + 1, j), idx(1, i + 1, j), idx(1, i, j)])
    for j in range(nu):   # 上下の縁
        for i in (0, nv):
            faces.append([idx(0, i, j), idx(1, i, j), idx(1, i, j + 1), idx(0, i, j + 1)])
    v = V3(verts)
    return _clean(v, faces)


def _clean(v, faces):
    """つぶれた面（同じ点が 2 回）を除き、外向きにそろえる"""
    out = []
    for f in faces:
        g = [f[0]] + [x for k, x in enumerate(f[1:], 1) if np.linalg.norm(v[x] - v[f[k - 1]]) > 1e-6]
        if len(g) > 2 and np.linalg.norm(v[g[-1]] - v[g[0]]) < 1e-6:
            g = g[:-1]
        if len(g) >= 3:
            out.append(g)
    return v, orient(v, out)


def ell_solid(c, ax, segs=16, rings=10):
    """閉じた楕円体（黒鉛の芯など）"""
    return ell_plate(c, ax, 0.0, 180.0, -180.0, 180.0, thick=0.0 + 0.5, dth=180.0 / rings, dph=360.0 / segs)


def limb(p0, p1, r0, r1, segs=8, cap=0.25):
    """面取りした太い棒（腿・脛）：p0 → p1、半径 r0 → r1、両端を細める"""
    return lathe(p0, p1, [(0, r0 * 0.7), (cap * 0.5, r0), (1 - cap * 0.5, r1), (1, r1 * 0.7)], segs)


def disc(c, r, w, segs=14, axis=(1, 0, 0)):
    c = V3(c, float)
    a = V3(axis, float) * (w / 2)
    return lathe(c - a, c + a, [(0, r * 0.9), (0.2, r), (0.8, r), (1, r * 0.9)], segs)


def wedge(base, tip, w, h, up=(0, 0, 1)):
    """足の爪：base（幅 w・高さ h の断面）から tip へ細る楔"""
    base, tip = V3(base, float), V3(tip, float)
    return extrude_taper([(-w, 0), (w, 0), (w * 0.8, h), (-w * 0.8, h)], base, tip, 0.25, up)


def extrude_taper(poly, p0, p1, k, up=(0, 0, 1)):
    """断面 poly を p0 → p1 へ押し出し、先で k 倍に細る"""
    a, s, u = K.frame(p1 - p0, up)
    n = len(poly)
    v = [p0 + q[0] * s + q[1] * u for q in poly] + [p1 + k * (q[0] * s + q[1] * u) for q in poly]
    f = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    f += [list(range(n))[::-1], list(range(n, 2 * n))]
    v = V3(v)
    return v, orient(v, f)


def mirror_x(piece):
    v, f = piece
    v = v * V3([-1, 1, 1])
    return v, orient(v, f)


# ---------------------------------------------------------------- 部品

class Rig:
    def __init__(self):
        self.parts = []

    def add(self, name, parent, pivot, axis, pieces):
        """pieces = [(材質, (頂点 cm, 面))]。先頭が部品本体、残りは name_<材質> の子"""
        pieces = [(m, p) for m, p in pieces if p is not None]
        self.parts.append(dict(name=name, parent=parent, pivot=V3(pivot, float), axis=V3(axis, float), pieces=pieces))


def sentry(rig: Rig):
    """歩哨型（全高 110 cm）。卵の胴（前に V の開口と砲口、横に真鍮の板、後ろに琥珀の核）と 2 本の逆関節ぎみの脚"""
    C = (0.0, 0.0, 73.5)
    AX = (17.0, 16.0, 22.0, 21.0)        # 卵：幅・奥行き・上・下の半径
    th_z = lambda z: math.degrees(math.acos(np.clip((z - C[2]) / (AX[2] if z >= C[2] else AX[3]), -1, 1)))
    apex, vbot = th_z(76.0), th_z(59.0)
    v_in = lambda t: 2.5 if t <= apex else 2.5 + (t - apex) / (vbot - apex) * 20.0   # V の開口の縁（度）
    ivory, brass, dark = [], [], []
    core_in = ell_solid(C, (AX[0] - 1.6, AX[1] - 1.6, AX[2] - 1.6, AX[3] - 1.6), 16, 10)
    dark.append(core_in)
    # 前の 2 枚（V の開口で分かれる。上は中央の細い継ぎ目）
    for sg in (1, -1):
        f0 = (lambda t: v_in(t)) if sg > 0 else (lambda t: -58.0)
        f1 = (lambda t: 58.0) if sg > 0 else (lambda t: -v_in(t))
        ivory.append(ell_plate(C, AX, 24.0, min(vbot, 132.0), f0, f1, dth=9, dph=10))
    # 横の真鍮の板（縦の帯）と、その後ろの白磁の板
    for sg in (1, -1):
        a, b = (61.0, 79.0) if sg > 0 else (-79.0, -61.0)
        brass.append(ell_plate(C, AX, 40.0, 128.0, a, b, thick=1.6, grow=0.5, dth=8, dph=6))
        a, b = (82.0, 158.0) if sg > 0 else (-158.0, -82.0)
        ivory.append(ell_plate(C, AX, 24.0, 138.0, a, b, dth=9, dph=12))
        # 後ろの核の窓の縁（真鍮）
        a, b = (158.5, 163.0) if sg > 0 else (-163.0, -158.5)
        brass.append(ell_plate(C, AX, 40.0, 122.0, a, b, thick=1.4, grow=0.4, dth=8, dph=4))
    # 上のかぶと（1 枚）と下の腹（黒鉛の芯が見える）
    ivory.append(ell_plate(C, AX, 0.0, 21.5, -180.0, 180.0, dth=7, dph=30))
    # 砲口（V の奥、前へ突き出す）
    dark.append(cyl((0, -12.0, 67.0), (0, -17.5, 67.0), 2.6, 12))
    dark.append(cyl((0, -17.5, 67.0), (0, -18.2, 67.0), 1.5, 12))
    # 腰の黒鉛の塊（股の関節の間）
    dark.append(ell_solid((0, 0.5, 51.0), (11.0, 8.0, 5.0, 5.0), 14, 6))
    rig.add('body', None, (0, 0, 47.0), (1, 0, 0), [('ivory', merge(*ivory)), ('brass', merge(*brass)), ('dark', merge(*dark))])
    # 棘（真鍮）と付け根の輪
    spike = lathe((0, 0, 94.0), (0, 0, 110.0), [(0, 5.0), (0.12, 5.0), (0.2, 3.6), (1, 0.0)], 8)
    collar = lathe((0, 0, 93.0), (0, 0, 95.5), [(0, 6.2), (1, 5.4)], 12)
    rig.add('spike', 'body', (0, 0, 94.0), (1, 0, 0), [('brass', spike), ('dark', collar)])
    # 砲口の蓋（前の下のあご。白磁）
    chin = ell_plate(C, AX, vbot + 1.5, 168.0, -34.0, 34.0, thick=1.4, grow=0.3, dth=8, dph=10)
    rig.add('muzzle_cover', 'body', (0, -4, 48.0), (1, 0, 0), [('ivory', chin)])
    # センサー（前の横長の窓）
    sensor = ell_plate(C, AX, th_z(82.2), th_z(79.8), -22.0, 22.0, thick=0.6, grow=0.25, dth=4, dph=8)
    rig.add('sensor', 'body', (0, -15.0, 81.0), (1, 0, 0), [('sensor', sensor)])
    # 核（後ろの縦長の窓、琥珀）
    core = ell_plate(C, AX, 44.0, 118.0, 162.0, 198.0, thick=0.8, grow=-0.6, dth=8, dph=6)
    rig.add('core', 'body', (0, 15.0, 76.0), (1, 0, 0), [('core', core)])
    # 脚（本人の左 = +X）
    for sg, side in ((1, 'l'), (-1, 'r')):
        hip, knee, ankle = V3([sg * 9.0, -1.0, 49.0]), V3([sg * 11.0, 9.5, 31.0]), V3([sg * 13.0, 2.0, 9.0])
        ax = (1, 0, 0)
        d = (knee - hip) / np.linalg.norm(knee - hip)
        thigh = limb(hip + d * 4.0, knee - d * 4.0, 5.6, 4.6, 8)
        rig.add(f'thigh_{side}', 'body', hip, ax, [('ivory', thigh), ('dark', disc(hip, 4.6, 6.0))])
        d2 = (ankle - knee) / np.linalg.norm(ankle - knee)
        shin = limb(knee + d2 * 3.8, ankle - d2 * 3.0, 4.4, 3.4, 8)
        knee_d = disc(knee, 4.4, 6.5)
        hub = disc(knee + V3([sg * 3.6, 0, 0]), 2.0, 1.2, 10)
        rig.add(f'shin_{side}', f'thigh_{side}', knee, ax, [('ivory', shin), ('dark', knee_d), ('brass', hub)])
        # 足：足首の黒鉛の塊と 3 本の爪（前 2・後ろ 1）。爪は白磁で先が真鍮
        ank = merge(disc(ankle, 3.4, 5.5), box((ankle[0], ankle[1], 5.0), (6.0, 7.0, 4.0)))
        toes_iv, toes_br = [], []
        for tip, w in (((ankle[0] + sg * 5.5, -15.0, 0.5), 2.6), ((ankle[0] - sg * 3.0, -14.0, 0.5), 2.6), ((ankle[0], 13.0, 0.5), 2.4)):
            tip = V3(tip)
            base = V3([ankle[0], ankle[1], 1.0]) + (tip - V3([ankle[0], ankle[1], 1.0])) * 0.2
            mid = base + (tip - base) * 0.62
            toes_iv.append(extrude_taper([(-w, 0), (w, 0), (w * 0.8, 4.2), (-w * 0.8, 4.2)], base, mid, 0.72))
            toes_br.append(extrude_taper([(-w * 0.72, 0), (w * 0.72, 0), (w * 0.58, 3.0), (-w * 0.58, 3.0)], mid, tip, 0.2))
        rig.add(f'foot_{side}', f'shin_{side}', ankle, ax, [('dark', ank), ('ivory', merge(*toes_iv)), ('brass', merge(*toes_br))])


def loft(sections, cham=0.25):
    """y に沿った断面の列 [(y, 半幅, 下の z, 上の z, 上の半幅)] を面取りの八角形でつなぐ（閉じた形）"""
    rings = []
    for y, w, z0, z1, wt in sections:
        h = z1 - z0
        c = cham * min(w, wt, h / 2)
        poly = [(-w + c, z0), (w - c, z0), (w, z0 + c), (wt, z1 - c), (wt - c, z1), (-wt + c, z1), (-wt, z1 - c), (-w, z0 + c)]
        rings.append([(x, y, z) for x, z in poly])
    n = 8
    v = V3([p for r in rings for p in r])
    f = []
    for i in range(len(rings) - 1):
        for k in range(n):
            f.append([i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k])
    f.append(list(range(n))[::-1])
    f.append([(len(rings) - 1) * n + k for k in range(n)])
    return v, orient(v, f)


def slab(pts_yz, x0, x1):
    """y-z の多角形（凸）を x0 → x1 に押し出した板（ひれ・横の板）"""
    n = len(pts_yz)
    v = V3([(x, y, z) for x in (x0, x1) for y, z in pts_yz])
    f = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    f += [list(range(n))[::-1], list(range(n, 2 * n))]
    return v, orient(v, f)


def charger(rig: Rig):
    """突撃型（全高 120 cm・全長 200 cm）。楔の車体（前が低い）・前の真鍮の衝角・後ろの真鍮のひれ・4 輪（懸架は黒鉛）"""
    cfg = B.TYPES['charger']
    # 車体：黒鉛の芯（全体）と、前・後ろの白磁の殻（間に黒鉛の帯と、本人の右に琥珀の核）
    core_body = loft([(-86, 13, 11, 29, 10), (-58, 22, 12, 45, 18), (-30, 27, 14, 62, 22), (0, 29, 19, 79, 23), (40, 31, 23, 92, 24), (95, 25, 38, 90, 18)], 0.4)
    nose = loft([(-88, 15, 10, 31, 11), (-60, 24, 11, 47, 20), (-30, 29, 13, 65, 24), (-6, 31, 17, 81, 25)], 0.4)
    rear = loft([(6, 32, 18, 83, 25), (40, 34, 22, 95, 26), (75, 33, 28, 95, 24), (98, 28, 38, 90, 19)], 0.4)
    # 上の重ね板（白磁、中央の背の両側）と横の肩の板
    tops, sides, br = [], [], []
    for sg in (1, -1):
        tops.append(slab([(-2, 84), (58, 101), (62, 97), (0, 80)], sg * 3, sg * 20))
        sides.append(slab([(-30, 38), (60, 46), (84, 60), (62, 72), (-30, 56)], sg * 32.5, sg * 36.0))
        # 真鍮の縁：鼻の横の斜めの帯・肩の板の上の縁
        br.append(slab([(-30, 55.5), (62, 71.5), (62, 74.0), (-30, 58.0)], sg * 34.0, sg * 37.0))
    # 肩の大きな曲面の板（車輪の上へ張り出す。正面から見て幅 ±48 cm）と下の縁の真鍮
    WC, WA = (0.0, 25.0, 50.0), (50.0, 75.0, 48.0, 48.0)
    for a0, a1 in ((58.0, 122.0), (-122.0, -58.0)):
        sides.append(ell_plate(WC, WA, 38.0, 74.0, a0, a1, thick=2.0, dth=6, dph=8))
        br.append(ell_plate(WC, WA, 74.5, 78.0, a0 + 2, a1 - 2, thick=1.6, grow=-0.2, dth=4, dph=8))
    # 鼻の横の真鍮の帯（斜め）
    for sg in (1, -1):
        v, f = loft([(-86, 1.2, 25, 28, 1.2), (-8, 1.2, 55, 58.5, 1.2)])
        v = v + V3([sg * 23.0, 0, 0])
        v[:, 0] += sg * (v[:, 1] + 86) / 78 * 7.0
        br.append((v, orient(v, f)))
    rig.add('body', None, cfg['body_pivot'], (1, 0, 0),
            [('ivory', merge(nose, rear, *tops, *sides)), ('dark', core_body), ('brass', merge(*br))])
    # センサー（鼻の上の横長の窓）
    rig.add('sensor', 'body', (0, -47, 56), (1, 0, 0), [('sensor', box((0, -46.5, 55.5), (30, 5, 2.4)))])
    # 核（本人の右 = -X の横、黒鉛の帯の所）と、その蓋
    core = cyl((-33.5, 6, 64), (-20, 6, 64), 12.5, 16)
    rig.add('core', 'body', (-26, 6, 64), (1, 0, 0), [('core', core)])
    cover = slab([(-16, 54), (-16, 84), (28, 88), (28, 56)], -34.5, -31.5)
    trim = slab([(-16, 84), (28, 88), (28, 90.5), (-16, 86.5)], -35, -31)
    rig.add('core_cover', 'body', (-22, 6, 86.0), (0, -1, 0), [('ivory', cover), ('brass', trim)])
    # 衝角（真鍮の角ばった箱）とレール
    ram = merge(extrude_taper([(-11, -11), (11, -11), (11, 11), (-11, 11)], V3([0, -86, 21]), V3([0, -102, 21]), 0.8, (0, 0, 1)))
    rail = box((0, -61, 24), (12, 42, 8))
    rig.add('ram', 'body', (0, -82, 25.0), (1, 0, 0), [('brass', ram)])
    rig.add('ram_rail', 'ram', (0, -61, 24), (1, 0, 0), [('dark', rail)])
    # ひれ（後ろの上、真鍮）
    fin = slab([(58, 92), (86, 121), (96, 121), (90, 95), (80, 84)], -3, 3)
    rig.add('fin', 'body', (0, 80, 92.0), (1, 0, 0), [('brass', fin)])
    # 懸架（黒鉛）と車輪（黒鉛のタイヤ・白磁の C の蓋・真鍮の軸）
    for n, par, c, rad, w in cfg['wheels']:
        c = V3(c, float)
        sgx = np.sign(c[0])
        susp = merge(box((sgx * 32, c[1], 30), (8, 16, 10)), cyl((sgx * 30, c[1], 30), (c[0], c[1], c[2]), 3.2, 8))
        rig.add(par, None, (sgx * 30, c[1], 30.0), (1, 0, 0), [('dark', susp)])
        tyre = B.cylinder(c, rad, w, 20)
        cov = B.c_disc(c, rad * 0.8, w, 20)
        hub = B.cylinder((c[0] + sgx * (w / 2 + 1.6), c[1], c[2]), rad * 0.22, 1.6, 10)
        rig.add(n, par, c, (1, 0, 0), [('dark', tyre), ('ivory', cov), ('brass', hub)])



def mini(rig: Rig):
    """子番機（全高 30 cm）。丸い兜の胴（前に横長のセンサー）・2 本の角（内側が真鍮）・横の肩の板・短い 2 本の脚"""
    C = (0.0, 0.0, 15.5)
    AX = (9.2, 11.0, 9.3, 5.2)
    th_z = lambda z: math.degrees(math.acos(np.clip((z - C[2]) / (AX[2] if z >= C[2] else AX[3]), -1, 1)))
    ivory, brass, dark = [], [], []
    dark.append(ell_solid(C, (AX[0] - 0.5, AX[1] - 0.5, AX[2] - 0.5, AX[3] - 0.5), 16, 10))
    ivory.append(ell_plate(C, AX, 16.0, 122.0, -74.0, 74.0, thick=0.5, dth=8, dph=10))
    for sg in (1, -1):
        a, b = (78.0, 160.0) if sg > 0 else (-160.0, -78.0)
        ivory.append(ell_plate(C, AX, 16.0, 116.0, a, b, thick=0.5, dth=8, dph=10))
        # 肩の板（横へ張り出す楔）
        ivory.append(extrude_taper([(-1.9, -5.4), (1.9, -5.4), (1.9, 5.4), (-1.9, 5.4)], V3([sg * 8.6, 0.5, 19.6]), V3([sg * 14.6, 0.5, 10.6]), 0.62, (0, 1, 0)))
    ivory.append(ell_plate(C, AX, 0.0, 13.0, -180.0, 180.0, thick=0.5, dth=6, dph=30))
    # 後ろの排気の輪（真鍮）と黒鉛の筒
    brass.append(lathe((0, 10.0, 16.0), (0, 11.6, 16.0), [(0, 3.9), (1, 3.9)], 16))
    dark.append(lathe((0, 9.0, 16.0), (0, 12.2, 16.0), [(0, 3.2), (0.8, 3.2), (1, 1.6)], 16))
    # 腰（黒鉛）とあごの板
    dark.append(ell_solid((0, 0, 10.2), (7.5, 5.5, 2.6, 2.6), 14, 6))
    ivory.append(slab([(-8.2, 8.5), (-6.8, 10.8), (-5.2, 10.8), (-6.0, 8.0)], -3.0, 3.0))
    dark.append(ell_plate(C, AX, th_z(16.4), th_z(14.2), -34.0, 34.0, thick=0.3, grow=0.06, dth=4, dph=10))   # センサーの窓の縁
    rig.add('sensor', 'body', (0, -9, 15.3), (1, 0, 0), [('sensor', ell_plate(C, AX, th_z(15.8), th_z(14.8), -29.0, 29.0, thick=0.3, grow=0.12, dth=4, dph=10))])
    rig.add('body', None, (0, 0, 12.0), (1, 0, 0), [('ivory', merge(*ivory)), ('brass', merge(*brass)), ('dark', merge(*dark))])
    rig.parts.insert(0, rig.parts.pop())
    rig.add('core', 'body', (0, 9, 11.0), (1, 0, 0), [('core', ell_plate(C, AX, th_z(12.4), th_z(10.8), 160.0, 200.0, thick=0.3, grow=0.1, dth=4, dph=10))])
    for sg, side in ((1, 'l'), (-1, 'r')):
        # 角：白磁の楔、内側の縁が真鍮
        base, tip = V3([sg * 6.2, 1.0, 21.5]), V3([sg * 5.0, 4.2, 30.0])
        horn = extrude_taper([(-1.5, -2.6), (1.5, -2.6), (1.5, 2.6), (-1.5, 2.6)], base, tip, 0.15, (0, -1, 0))
        edge = extrude_taper([(-0.35, -2.4), (0.35, -2.4), (0.35, 2.4), (-0.35, 2.4)], base - V3([sg * 1.7, 0, 0]), tip - V3([sg * 0.4, 0, 0]), 0.15, (0, -1, 0))
        rig.add(f'horn_{side}', 'body', (sg * 6.2, 1.0, 21.5), (1, 0, 0), [('ivory', horn), ('brass', edge)])
        hip, knee, ankle = V3([sg * 6.5, 0.0, 10.0]), V3([sg * 10.0, -3.5, 5.4]), V3([sg * 11.2, -3.2, 2.6])
        d = (knee - hip) / np.linalg.norm(knee - hip)
        thigh = limb(hip + d * 1.2, knee - d * 0.6, 2.5, 2.1, 8)
        rings = merge(disc(hip + d * 1.2, 2.7, 0.8, 12, d), disc(knee - d * 0.8, 2.4, 0.8, 12, d))
        rig.add(f'thigh_{side}', 'body', hip, (1, 0, 0), [('ivory', thigh), ('brass', rings), ('dark', disc(hip, 2.4, 3.0))])
        rig.add(f'shin_{side}', f'thigh_{side}', knee, (1, 0, 0), [('dark', limb(knee, ankle, 1.8, 1.6, 8))])
        toe_f = extrude_taper([(-1.6, 0), (1.6, 0), (1.3, 3.8), (-1.3, 3.8)], V3([ankle[0], ankle[1] - 1.0, 0.2]), V3([ankle[0] + sg * 0.6, -10.0, 0.2]), 0.35)
        toe_b = extrude_taper([(-1.5, 0), (1.5, 0), (1.2, 3.4), (-1.2, 3.4)], V3([ankle[0], ankle[1] + 0.8, 0.2]), V3([ankle[0] + sg * 1.2, 3.5, 0.2]), 0.4)
        rig.add(f'foot_{side}', f'shin_{side}', ankle, (1, 0, 0), [('dark', merge(disc(ankle, 1.9, 2.6), toe_b)), ('ivory', toe_f)])



def rot_z(piece, ang):
    v, f = piece
    c, s_ = math.cos(ang), math.sin(ang)
    v = v @ V3([[c, s_, 0], [-s_, c, 0], [0, 0, 1]])
    return v, f


def floater(rig: Rig):
    """浮遊型（全高 51 cm）。レンズ形のハブ（前にセンサー）・3 枚の葉（上下の白磁の板の間に真鍮の帯）・上の冠（琥珀の核）・下の黒鉛の砲口"""
    C = (0.0, 0.0, 24.0)
    AX = (19.0, 19.0, 8.5, 8.5)
    th_z = lambda z: math.degrees(math.acos(np.clip((z - C[2]) / 8.5, -1, 1)))
    ivory = [ell_plate(C, AX, 6.0, 83.0, -180.0, 180.0, thick=0.8, dth=11, dph=15),
             ell_plate(C, AX, 97.0, 140.0, -180.0, 180.0, thick=0.8, dth=11, dph=15)]
    brass = [ell_plate(C, AX, 85.0, 95.0, -180.0, 180.0, thick=1.0, grow=0.3, dth=10, dph=12)]
    dark = [ell_solid(C, (18.2, 18.2, 7.8, 7.8), 20, 8), ell_solid((0, 0, 17.0), (15.0, 15.0, 4.0, 4.0), 16, 6)]
    dark.append(ell_plate(C, AX, th_z(22.6), th_z(19.4), -38.0, 38.0, thick=0.4, grow=0.1, dth=5, dph=12))   # センサーの窓の縁
    rig.add('body', None, (0, 0, 25.0), (1, 0, 0), [('ivory', merge(*ivory)), ('brass', merge(*brass)), ('dark', merge(*dark))])
    rig.add('sensor', 'body', (0, -18, 21.0), (1, 0, 0), [('sensor', ell_plate(C, AX, th_z(22.0), th_z(20.0), -32.0, 32.0, thick=0.4, grow=0.3, dth=5, dph=12))])
    # 葉：+X へ伸ばして作り、角度へ回す
    LC, LA = (37.0, 0.0, 24.5), (19.0, 12.5, 7.0, 7.0)
    for k, ang in enumerate((90.0, 210.0, 330.0)):
        a = math.radians(ang)
        up = ell_plate(LC, LA, 0.0, 82.0, -180.0, 180.0, thick=0.8, dth=13, dph=20)
        lo = ell_plate(LC, LA, 98.0, 180.0, -180.0, 180.0, thick=0.8, dth=13, dph=20)
        band = ell_plate(LC, LA, 84.0, 96.0, -180.0, 180.0, thick=1.2, grow=0.2, dth=12, dph=15)
        root = box((20.5, 0, 24.5), (5.0, 9.0, 8.0))
        piv = (17.0 * math.cos(a), 17.0 * math.sin(a), 25.0)
        rig.add(f'lobe_{k}', 'body', piv, (1, 0, 0), [('ivory', rot_z(merge(up, lo), a)), ('brass', rot_z(band, a)), ('dark', rot_z(root, a))])
    # 冠（上の尖り、白磁。前に真鍮の筋）と琥珀の核
    crown = lathe((0, 2.0, 31.0), (0, 2.0, 50.5), [(0, 9.5), (0.35, 7.0), (1, 1.2)], 6)
    stripe = extrude_taper([(-1.0, -0.6), (1.0, -0.6), (1.0, 0.6), (-1.0, 0.6)], V3([0, -5.2, 33.0]), V3([0, 0.9, 50.0]), 0.5, (0, 1, 0))
    rig.add('crown', 'body', (0, 8, 37.5), (1, 0, 0), [('ivory', crown), ('brass', stripe)])
    core = ell_plate((0, -4.5, 33.5), (4.6, 4.6, 4.6, 4.6), 0.0, 90.0, -110.0, 110.0, thick=0.6, dth=15, dph=20)
    rig.add('core', 'crown', (0, -5, 35.0), (1, 0, 0), [('core', core)])
    # 砲口（下、黒鉛）
    muzzle = lathe((0, 0, 14.0), (0, 0, 1.5), [(0, 7.5), (0.55, 6.0), (0.6, 4.2), (1, 3.4)], 10)
    rig.add('muzzle', 'body', (0, 0, 12.5), (1, 0, 0), [('dark', muzzle)])



def bbox(c, size, cham=0.22, taper=1.0):
    """面取りした箱（中心 c・大きさ size）。taper：上の面の幅の倍率"""
    c = V3(c, float)
    hx, hy, hz = V3(size, float) / 2
    v, f = loft([(c[1] - hy, hx, c[2] - hz, c[2] + hz, hx * taper), (c[1] + hy, hx, c[2] - hz, c[2] + hz, hx * taper)], cham)
    return v + V3([c[0], 0, 0]), f


def facet(c, ax, th0=0.0, th1=180.0, ph0=-180.0, ph1=180.0, n=8, m=6, thick=None):
    """角ばった楕円体（低い多角形の鎧の板）：経度 n 分割・緯度 m 分割"""
    t = thick if thick is not None else min(ax[:3]) * 0.9
    return ell_plate(c, ax, th0, th1, ph0, ph1, thick=t, dth=(th1 - th0) / m + 1e-6, dph=(ph1 - ph0) / n + 1e-6)


def shield(rig: Rig):
    """盾型（全高 180 cm）。菱形の兜・胸の大きな板（中央で 2 枚）・丸い肩の板・本人の右の太い籠手・本人の左に真鍮の縁の大盾・太い脚。
    板は低い多角形の楕円体（facet）で、絵の角ばった鎧に合わせる"""
    ivory, brass, dark = [], [], []
    dark.append(facet((0, 2, 120), (23, 16, 30, 28), n=10, m=8))            # 胴の芯（板の隙間から見える）
    dark.append(facet((0, 1, 96), (17, 12, 7, 7), n=10, m=4))               # 腰
    C, AX = (0, 0, 122), (28, 19, 32, 27)
    for a0, a1 in ((3.0, 64.0), (-64.0, -3.0)):
        ivory.append(facet(C, AX, 28.0, 150.0, a0, a1, n=4, m=6, thick=2.0))   # 胸の板（中央に黒鉛の継ぎ目）
        ivory.append(facet(C, AX, 30.0, 140.0, a0 + np.sign(a0) * 72, a1 + np.sign(a0) * 72, n=3, m=5, thick=2.0))  # 背中の板
    for sg in (1, -1):
        ivory.append(facet((sg * 35, 0, 139), (18.0, 17.0, 14.0, 9.0), 0.0, 115.0, n=8, m=4, thick=2.0))   # 肩の板
        brass.append(facet((sg * 35, 0, 139), (18.0, 17.0, 14.0, 9.0), 115.0, 124.0, n=8, m=1, thick=1.2))
        dark.append(cyl((sg * 16, 0, 139), (sg * 30, 0, 139), 7.5, 10))   # 肩の関節
    dark.append(merge(cyl((34, 0, 128), (38, 0, 110), 5.5, 8), cyl((38, 0, 110), (46, -4, 123), 5.0, 8)))   # 本人の左の腕
    brass.append(bbox((0, 18.2, 122), (20, 1.4, 44)))   # 後ろの核の窓の縁
    rig.add('body', None, (0, 0, 95.0), (1, 0, 0), [('ivory', merge(*ivory)), ('dark', merge(*dark)), ('brass', merge(*brass))])
    rig.add('core', 'body', (0, 18, 122), (1, 0, 0), [('core', bbox((0, 18.6, 122), (13, 1.2, 36)))])
    # 兜（菱形、6 面）とセンサー
    helm = lathe((0, -3, 134), (0, -3, 180), [(0, 9.0), (0.3, 14.0), (1, 0.0)], 6)
    rig.add('head', 'body', (0, 0, 133.0), (1, 0, 0), [('ivory', helm), ('dark', cyl((0, -2, 128), (0, -2, 137), 7.5, 10))])
    rig.add('sensor', 'head', (0, -14, 148), (1, 0, 0), [('sensor', box((0, -15.6, 148.5), (13, 2.0, 2.2)))])
    # 本人の右の腕：上腕（黒鉛）・籠手（白磁の角ばった塊、真鍮の帯）・拳（黒鉛）
    rig.add('upperarm_r', 'body', (-42, 0, 130.0), (1, 0, 0), [('dark', cyl((-40, 0, 130), (-52, 0, 110), 6.0, 8))])
    fore = facet((-64, 0, 100), (17.0, 17.0, 25.0, 22.0), 0.0, 180.0, n=8, m=5, thick=3.0)
    ring = lathe((-64, 0, 82.0), (-64, 0, 86.0), [(0, 15.5), (1, 15.5)], 8)
    fist = facet((-61, -2, 70), (13.0, 13.0, 11.0, 11.0), n=8, m=4)
    rig.add('forearm_r', 'upperarm_r', (-52, 0, 104.0), (1, 0, 0), [('ivory', fore), ('dark', fist), ('brass', ring)])
    # 大盾：六角の板（白磁）、真鍮の縁、黒鉛の握りと中心の円盤
    def xz_slab(poly, y0, y1):
        v, f = slab(poly, y0, y1)
        v = v[:, [1, 0, 2]]
        return v, orient(v, f)
    face = xz_slab([(56, 184), (80, 150), (78, 40), (58, 14), (38, 40), (36, 150)], -13.0, -9.0)
    rim = xz_slab([(56, 189), (83, 151), (81, 38), (58, 9), (35, 38), (33, 151)], -10.0, -6.5)
    stripe = xz_slab([(66, 150), (70, 150), (68, 60), (64, 60)], -13.8, -12.6)
    boss = cyl((58, -12.0, 125), (58, -15.0, 125), 6.5, 12)
    grip = cyl((44, -2, 123), (54, -7, 124), 3.5, 8)
    def turn(piece, deg=40.0, c=(58.0, -10.0)):
        v, f = piece
        a = math.radians(deg)
        x, y = v[:, 0] - c[0], v[:, 1] - c[1]
        v = np.stack([c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a), v[:, 2]], 1)
        return v, f
    rig.add('shield', 'body', (30, 5, 127.0), (0, 0, 1), [('ivory', turn(face)), ('brass', turn(merge(rim, stripe))), ('dark', merge(turn(boss), grip))])
    # 脚：腿・脛は角ばった楕円体、膝・足首は黒鉛の円盤、足は面取りの箱に真鍮の底
    for sg, side in ((1, 'l'), (-1, 'r')):
        hip, knee, ankle = V3([sg * 20, 0, 92.0]), V3([sg * 23, 0, 52.0]), V3([sg * 25, 0, 16.0])
        thigh = facet((sg * 22, -2, 73), (16.0, 16.0, 22.0, 19.0), n=8, m=5, thick=3.0)
        rig.add(f'thigh_{side}', 'body', hip, (1, 0, 0), [('ivory', thigh), ('dark', cyl((sg * 12, 0, 91), (sg * 28, 0, 91), 7.5, 10))])
        shin = facet((sg * 25, -2, 34), (15.0, 16.0, 19.0, 17.0), n=8, m=5, thick=3.0)
        rig.add(f'shin_{side}', f'thigh_{side}', knee, (1, 0, 0), [('ivory', shin), ('dark', cyl((sg * 13, 0, 52), (sg * 35, 0, 52), 8, 10))])
        foot = bbox((sg * 27, -6, 7.5), (32, 44, 11), 0.4, 0.75)
        sole = bbox((sg * 27, -6, 1.2), (34, 46, 2.4), 0.3)
        rig.add(f'foot_{side}', f'shin_{side}', ankle, (1, 0, 0), [('ivory', foot), ('brass', sole), ('dark', cyl((sg * 17, 0, 16), (sg * 33, 0, 16), 6, 10))])


BUILDERS = {'sentry': sentry, 'charger': charger, 'mini': mini, 'floater': floater, 'shield': shield}


# ---------------------------------------------------------------- 組み立て・書き出し

def build(t: str, out_glb: str) -> dict:
    import bpy
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig = Rig()
    BUILDERS[t](rig)
    mats = B.make_materials(t, None)
    mats['shell'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*B.srgb_to_linear(IVORY), 1)
    matmap = {'ivory': mats['shell'], 'dark': mats['dark'], 'brass': mats['brass'], 'sensor': mats['sensor'], 'core': mats['core']}
    objs, meshes = {}, []
    for p in rig.parts:
        rot = B.axis_matrix(p['axis'])
        first = None
        for i, (mk, (v, f)) in enumerate(p['pieces']):
            nm = p['name'] if i == 0 else f"{p['name']}_{mk}"
            ob = B.new_object(nm, v, f, matmap[mk], p['pivot'], rot)
            meshes.append(ob)
            if first is None:
                first = ob
                objs[p['name']] = ob
            else:
                mw = ob.matrix_world.copy()
                ob.parent = first
                ob.matrix_world = mw
    root = bpy.data.objects.new(f'banki_{t}', None)
    bpy.context.scene.collection.objects.link(root)
    for p in rig.parts:
        ob = objs[p['name']]
        mw = ob.matrix_world.copy()
        ob.parent = objs[p['parent']] if p['parent'] else root
        ob.matrix_world = mw
    B.smooth_by_angle(meshes, 38.0)
    tri = sum(sum(len(pl.vertices) - 2 for pl in ob.data.polygons) for ob in meshes)
    os.makedirs(os.path.dirname(out_glb), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_yup=True, export_apply=False,
                              export_animations=False, use_selection=True)
    info = {'type': t, 'method': 'parts', 'triangles': tri, 'parts': sorted(objs.keys()), 'seconds': round(time.time() - t0, 1),
            'glb': os.path.relpath(out_glb, B.REPO)}
    log(str(info))
    return info
