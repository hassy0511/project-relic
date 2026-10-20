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


def ell_plate(c, ax, th0, th1, ph0, ph1, thick=1.2, grow=0.0, dth=10.0, dph=12.0, pfn=None):
    """楕円体の上の板（厚み thick）。ph0・ph1 は数（度）か、th（度）の関数。角は度。
    pfn(th, ph, grow)（ラジアン）を渡すと、楕円体の代わりにその面の上の板（浮遊型の葉の花びら形など）"""
    P = pfn or (lambda t_, p_, g_: ell_point(c, ax, t_, p_, g_))
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
                verts.append(P(math.radians(t), math.radians(p), g))
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
        ivory.append(ell_plate(C, AX, 24.0, min(vbot, 132.0), f0, f1, dth=15, dph=19))
    # 横の真鍮の板（3e：縦に 4 つの塊に分ける。絵の段の真鍮）と、その後ろの白磁の板
    for sg in (1, -1):
        a, b = (61.0, 79.0) if sg > 0 else (-79.0, -61.0)
        for t0, t1 in ((38.0, 58.0), (60.0, 82.0), (84.0, 106.0), (108.0, 128.0)):
            brass.append(ell_plate(C, AX, t0, t1, a, b, thick=1.8, grow=0.6, dth=11, dph=9))
        a, b = (82.0, 158.0) if sg > 0 else (-158.0, -82.0)
        ivory.append(ell_plate(C, AX, 24.0, 138.0, a, b, dth=16, dph=19))
        # 後ろの核の窓の縁（真鍮）
        a, b = (158.5, 163.0) if sg > 0 else (-163.0, -158.5)
        brass.append(ell_plate(C, AX, 40.0, 122.0, a, b, thick=1.4, grow=0.4, dth=8, dph=4))
    # 上のかぶと（1 枚）と下の腹（黒鉛の芯が見える）
    ivory.append(ell_plate(C, AX, 0.0, 21.5, -180.0, 180.0, dth=11, dph=45))
    # 砲口（V の奥、前へ突き出す）
    dark.append(cyl((0, -12.0, 67.0), (0, -17.5, 67.0), 2.6, 12))
    dark.append(cyl((0, -17.5, 67.0), (0, -18.2, 67.0), 1.5, 12))
    # 腰の黒鉛の塊（股の関節の間）
    dark.append(ell_solid((0, 0.5, 52.5), (6.0, 6.0, 4.0, 4.0), 12, 6))
    # 核の窓の縦の仕切り（黒鉛。絵の背面の窓は中央で 2 つに分かれる）
    dark.append(ell_plate(C, AX, 46.0, 116.0, 178.6, 181.4, thick=1.2, grow=0.2, dth=12, dph=3))
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
        # 3e：腿・脛は角ばった板（前に稜。腿は中ほどがふくらみ、脛は下へ細る）。股・膝の黒鉛の円盤は大きめ
        thigh = prism(hip + d * 4.2, knee - d * 3.6, [(0, 4.6, 4.4, 4.0), (0.35, 5.8, 6.0, 5.0), (1, 4.6, 4.8, 4.0)], fwd=(0, -1, 0))
        rig.add(f'thigh_{side}', 'body', hip, ax, [('ivory', thigh), ('dark', disc(hip + V3([sg * 1.0, 0, 0]), 4.9, 4.6))])   # 股の円盤は細く外へ（腰と分かれて丸い関節に見える）
        d2 = (ankle - knee) / np.linalg.norm(ankle - knee)
        shin = prism(knee + d2 * 3.8, ankle - d2 * 3.0, [(0, 4.4, 4.6, 3.6), (0.3, 4.6, 4.8, 3.6), (1, 3.2, 3.4, 2.8)], fwd=(0, -1, 0))
        knee_d = disc(knee, 4.8, 6.8)
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


def loft_rings(rings):
    """同じ点数の輪 [(x, y, z), ...] の列をつなぐ（両端に蓋。閉じた形）"""
    n = len(rings[0])
    v = V3([p for r in rings for p in r], float)
    f = []
    for i in range(len(rings) - 1):
        for k in range(n):
            f.append([i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k])
    f.append(list(range(n))[::-1])
    f.append([(len(rings) - 1) * n + k for k in range(n)])
    return v, orient(v, f)


# 突撃型の車体の外形（y, 半幅 w, 下の z0, 上の z1, 上の半幅 wt）。鼻・胴・後ろを 1 つの式でつなぐ（板はこの面に沿わせる）
# 3e：断面を丸い兜形に（上の半幅を狭く・面取りを大きく）、後ろは斜めに落とす（絵の真横の後ろの端は下ほど前へ入る）
CH_SECS = [(-88, 15, 10, 31, 9), (-60, 23, 11, 47, 14), (-30, 27, 13, 65, 16), (-6, 29, 17, 81, 17),
           (6, 30, 18, 84, 17), (40, 31, 22, 93, 17), (72, 29, 28, 95, 15), (92, 22, 36, 90, 11), (101, 13, 46, 82, 7)]
CH_CHAM = 0.55
POCKET_Y = (-7.0, 19.0)      # 核の窓（本人の右 = -X）の前後の幅
POCKET_Z = (44.0, 69.0)
POCKET_D = 8.0


def ch_sec(y):
    a = np.array(CH_SECS, float)
    return tuple(float(np.interp(y, a[:, 0], a[:, k])) for k in range(1, 5))   # w, z0, z1, wt


def ch_c(w, z0, z1, wt):
    return CH_CHAM * min(w, wt, (z1 - z0) / 2)


def ch_hw(y, z):
    """車体の外の面の半幅（+X 側）。面取りも含む"""
    w, z0, z1, wt = ch_sec(y)
    c = ch_c(w, z0, z1, wt)
    zz = min(max(z, z0), z1)
    if zz < z0 + c:
        return w - c + (zz - z0)
    if zz > z1 - c:
        return wt - (zz - (z1 - c))
    return w + (wt - w) * (zz - (z0 + c)) / ((z1 - c) - (z0 + c))


def ch_ring(y, inset=0.0, pocket=False):
    w, z0, z1, wt = ch_sec(y)
    c = ch_c(w, z0, z1, wt)
    w, wt, z0, z1 = w - inset, wt - inset, z0 + inset * 0.5, z1 - inset * 0.5
    poly = [(-w + c, z0), (w - c, z0), (w, z0 + c), (wt, z1 - c), (wt - c, z1), (-wt + c, z1), (-wt, z1 - c)]
    if pocket:   # -X の横に、核の窓のへこみ（前後は鼻と後ろの板の面が壁になる）
        z_hi, z_lo = POCKET_Z[1], POCKET_Z[0]
        poly += [(-ch_hw(y, z_hi), z_hi), (-(ch_hw(y, z_hi) - POCKET_D), z_hi),
                 (-(ch_hw(y, z_lo) - POCKET_D), z_lo), (-ch_hw(y, z_lo), z_lo)]
    poly += [(-w, z0 + c)]
    return [(x, y, z) for x, z in poly]


def ch_zt(y):
    return ch_sec(y)[2]


def shell_grid(vo, vi):
    """外の面の格子 vo[i][j]・内の面の格子 vi[i][j] から、厚みのある板（閉じた形）を作る"""
    nv, nu = len(vo), len(vo[0])
    verts = [p for g in (vo, vi) for row in g for p in row]
    W = nu
    n1 = nv * W
    idx = lambda s, i, j: s * n1 + i * W + j
    faces = []
    for i in range(nv - 1):
        for j in range(nu - 1):
            faces.append([idx(0, i, j), idx(0, i, j + 1), idx(0, i + 1, j + 1), idx(0, i + 1, j)])
            faces.append([idx(1, i, j), idx(1, i + 1, j), idx(1, i + 1, j + 1), idx(1, i, j + 1)])
    for i in range(nv - 1):
        for j in (0, nu - 1):
            faces.append([idx(0, i, j), idx(0, i + 1, j), idx(1, i + 1, j), idx(1, i, j)])
    for j in range(nu - 1):
        for i in (0, nv - 1):
            faces.append([idx(0, i, j), idx(1, i, j), idx(1, i, j + 1), idx(0, i, j + 1)])
    return _clean(V3(verts, float), faces)


def surf_plate(ys, zlo, zhi, lift=0.6, thick=3.0, nz=5):
    """車体の +X 側の面に沿う板。y の列 ys・下の縁 zlo(y)・上の縁 zhi(y)。面から lift 出て、面の下へ thick まで埋まる"""
    vo, vi = [], []
    for y in ys:
        a, b = zlo(y), zhi(y)
        ro, ri = [], []
        for k in range(nz):
            z = a + (b - a) * k / (nz - 1)
            h = ch_hw(y, z)
            ro.append((h + lift, y, z))
            ri.append((h + lift - thick, y, z))
        vo.append(ro)
        vi.append(ri)
    return shell_grid(vo, vi)


def top_plate(ys, x0, x1, lift, depth=3.0, bev=1.2):
    """背の上の面に沿う板（x0 → x1）。lift(y) だけ面から出て、面の下 depth まで埋まる"""
    rings = []
    for y in ys:
        zt = ch_zt(y)
        zb, zu = zt - depth, zt + lift(y)
        rings.append([(x0, y, zb), (x1, y, zb), (x1 - bev, y, zu), (x0 + bev, y, zu)])
    return loft_rings(rings)


def charger_half(sg=1):
    """+X 側の板と縁の帯（本人の左）。-X 側は mirror_x で作る = 左右は 1 つの定義から"""
    iv, br, dk = [], [], []
    ivl = lambda pts: (lambda y: float(np.interp(y, [p[0] for p in pts], [p[1] for p in pts])))
    # 上の重ね板（背の中央の両側）
    tl = ivl([(-4, 1.0), (2, 2.6), (56, 3.4), (62, 1.0)])
    iv.append(top_plate(np.linspace(-4, 62, 12), 3.2, 12.5, tl))
    # 横の板：鼻の側（核の窓の前）と後ろの側（窓の後ろ）。窓の所は空ける
    fore = (np.linspace(-32, -11, 6), ivl([(-32, 36), (-11, 40)]), ivl([(-32, 54), (-11, 60)]))
    aft = (np.linspace(23, 84, 12), ivl([(23, 42), (60, 46), (84, 60)]), ivl([(23, 72), (62, 72), (84, 60)]))
    for ys, lo, hi in (fore, aft):
        iv.append(surf_plate(ys, lo, hi, 0.9, 3.0, 6))
        # 板の上の縁の真鍮の帯
        br.append(surf_plate(ys, (lambda y, hi=hi: hi(y) - 2.4), hi, 1.5, 2.6, 2))
    # 鼻の斜めの真鍮の帯（ラムから胴の継ぎ目の高さまで）
    fr = ivl([(-86, 0.34), (-10, 0.60)])
    lo = lambda y: ch_sec(y)[1] + fr(y) * (ch_sec(y)[2] - ch_sec(y)[1])
    br.append(surf_plate(np.linspace(-86, -10, 14), lo, lambda y: lo(y) + 2.8, 0.7, 2.4, 2))
    # 肩の大きな曲面の板（車輪の上へ張り出す）と、その下の厚み（体との隙間をふさぐ）
    # 3e：肩の大きな曲面の板を、背から車輪の上まで覆う甲虫の羽のような 2 枚（核の窓の前と後ろ。間は核と蓋のために空ける）。
    # 下の縁は真鍮。板と胴の間は黒鉛の層（絵の正面で板と胴の間が暗い）
    # 後ろの羽（背の高い所から後ろの車輪の上まで）と、前の泥よけ（前の車輪の上）
    for WC, WA, th0, th1, a0, a1 in (((0.0, 56.0, 38.0), (46.0, 58.0, 63.0, 63.0), 20.0, 78.0, 48.0, 145.0),
                                     ((0.0, -30.0, 30.0), (50.0, 40.0, 42.0, 42.0), 36.0, 82.0, 20.0, 95.0)):
        if WC[1] > 0:
            # 後ろの羽は重ね板に（絵の真横の後ろへ流れる板）：上の板が下の板に少し重なり、下の板は前後 2 枚に分かれる
            iv.append(ell_plate(WC, WA, th0, 51.0, a0, a1, thick=2.4, grow=1.8, dth=9.5, dph=12))
            for b0, b1 in ((a0 + 3.0, 95.0), (98.0, a1 - 4.0)):
                iv.append(ell_plate(WC, WA, 47.0, th1, b0, b1, thick=2.4, dth=9.5, dph=12))
        else:
            iv.append(ell_plate(WC, WA, th0, th1, a0, a1, thick=2.4, dth=9.5, dph=12))
        br.append(ell_plate(WC, WA, th1, th1 + 3.0, a0 + 1.5, a1 - 1.5, thick=1.6, grow=-0.3, dth=3, dph=12))
        dk.append(ell_plate(WC, WA, th0 + 4.0, th1 + 2.0, a0 + 3.0, a1 - 3.0, thick=9.0, grow=-2.6, dth=15, dph=18))
    return iv, br, dk


def charger(rig: Rig):
    """突撃型（全高 120 cm・全長 200 cm）。楔の車体（前が低い）・前の真鍮の衝角・後ろの真鍮のひれ・4 輪（懸架は黒鉛）。
    左右は 1 つの定義（charger_half）から鏡写しに作る。左右で違うのは、本人の右（-X）の横の核の窓と、その蓋だけ"""
    cfg = B.TYPES['charger']
    nose_y, rear_y = [-88, -60, -30, POCKET_Y[0]], [POCKET_Y[1], 40, 75, 98]
    mid_y = [POCKET_Y[0], 6, POCKET_Y[1]]
    # 車体の殻：鼻・胴（-X の横だけ窓のへこみ）・後ろ
    nose = loft_rings([ch_ring(y) for y in nose_y])
    mid = loft_rings([ch_ring(y, pocket=True) for y in mid_y])
    rear = loft_rings([ch_ring(y) for y in rear_y])
    # 中の黒鉛の芯（殻の下。胴だけは窓のへこみの底より内へ）
    core_body = merge(loft_rings([ch_ring(y, 2.0) for y in [-86] + nose_y[1:]]),
                      loft_rings([ch_ring(y, 12.0) for y in mid_y]),
                      loft_rings([ch_ring(y, 2.0) for y in rear_y[:-1] + [95]]))
    iv, br, dk = charger_half()
    ivm = [mirror_x(p) for p in iv]
    brm = [mirror_x(p) for p in br]
    dkm = [mirror_x(p) for p in dk]
    # 背の中央の真鍮の筋（ひれの前）
    spine = top_plate(np.linspace(-36, 60, 12), -1.9, 1.9, lambda y: 1.5, depth=2.0, bev=0.5)
    rig.add('body', None, cfg['body_pivot'], (1, 0, 0),
            [('ivory', merge(nose, mid, rear, *iv, *ivm)), ('dark', merge(core_body, *dk, *dkm)), ('brass', merge(spine, *br, *brm))])
    # センサー（鼻の上の横長の窓）
    rig.add('sensor', 'body', (0, -47, 56), (1, 0, 0), [('sensor', box((0, -46.5, 55.5), (22, 5, 2.4)))])   # 3e：細くした背の上の面に収まる幅
    # 核（本人の右 = -X の横の窓の奥の円柱）と、その蓋（窓をふさぐ面に沿う板。上の縁が蝶番）
    zc = 0.5 * (POCKET_Z[0] + POCKET_Z[1])
    core = cyl((-18.2, 6, zc), (-12.0, 6, zc), 11.8, 16)   # 3e：胴を兜形にした分だけ内へ（斜めの蓋の下に収まる）
    rig.add('core', 'body', (-26, 6, 64), (1, 0, 0), [('core', core)])
    cy = np.linspace(POCKET_Y[0] - 2.0, POCKET_Y[1] + 2.0, 8)
    cover = mirror_x(surf_plate(cy, lambda y: POCKET_Z[0] - 2.0, lambda y: 78.0, 0.9, 2.6, 8))
    trim = mirror_x(surf_plate(cy, lambda y: 75.6, lambda y: 78.4, 1.6, 2.6, 2))
    rig.add('core_cover', 'body', (-14.5, 6, 78.5), (0, -1, 0), [('ivory', cover), ('brass', trim)])   # 3e：蝶番を兜形の胴の面（蓋の上の縁）へ
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
        # 3e：細い腕をやめ、車輪と胴の間を埋める黒鉛の塊と短い軸（絵の正面の車輪の内側の暗い機構。細い腕は台車のように見えた）
        susp = merge(box((sgx * 34.5, c[1], 27.5), (11, 20, 15)), cyl((sgx * 39.5, c[1], c[2]), (c[0], c[1], c[2]), 4.2, 8))
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
    # 3e：肩の板は平らな楔をやめ、外へ斜めに張り出す 2 段の角ばった板（中央に折れ目の稜。上の段は角の付け根）。付け根は黒鉛の玉
    for sg in (1, -1):
        a, b = (78.0, 160.0) if sg > 0 else (-160.0, -78.0)
        ivory.append(ell_plate(C, AX, 16.0, 116.0, a, b, thick=0.5, dth=8, dph=10))
        lo_p = prism((sg * 9.6, 1.6, 21.0), (sg * 14.8, 1.6, 12.0), [(0, 3.8, 1.3, 0.8), (0.45, 5.0, 1.7, 0.9), (1, 3.0, 1.0, 0.6)],
                     fwd=(sg * 0.87, 0, 0.5), keel=0.7)
        up_p = prism((sg * 5.8, 1.8, 24.6), (sg * 11.4, 1.8, 19.4), [(0, 3.2, 1.2, 0.7), (0.5, 4.2, 1.5, 0.8), (1, 3.4, 1.1, 0.6)],
                     fwd=(sg * 0.68, 0, 0.74), keel=0.7)
        ivory += [lo_p, up_p]
        dark.append(ell_solid((sg * 9.4, 1.6, 17.4), (2.6, 3.6, 3.6, 3.6), 10, 5))
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
        horn = extrude_taper([(-1.8, -3.4), (1.8, -3.4), (1.8, 3.4), (-1.8, 3.4)], base, tip, 0.12, (0, -1, 0))
        edge = extrude_taper([(-0.4, -3.1), (0.4, -3.1), (0.4, 3.1), (-0.4, 3.1)], base - V3([sg * 2.0, 0, 0]), tip - V3([sg * 0.45, 0, 0]), 0.12, (0, -1, 0))
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


def ridge(pts, ups, widths, h=1.6, sink=0.5):
    """面に沿う細い稜（真鍮の筋）：点の列 pts・外向き ups・半幅 widths の台形の断面をつなぐ"""
    pts, ups = [V3(p, float) for p in pts], [V3(u, float) / np.linalg.norm(u) for u in ups]
    rings = []
    for i, (p, u, w) in enumerate(zip(pts, ups, widths)):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        sd = np.cross(t, u)
        sd = sd / np.linalg.norm(sd)
        q = p - u * sink
        rings.append([q - sd * w, q + sd * w, q + sd * w * 0.45 + u * (h + sink), q - sd * w * 0.45 + u * (h + sink)])
    return loft_rings(rings)


def floater(rig: Rig):
    """浮遊型（直径 80 cm・全高 51 cm）。3e：黒鉛の丸い三角のハブ（前に白磁の前板とセンサー）・3 枚の花びら形の葉
    （上の板は中央の真鍮の稜で左右 2 枚、赤道に真鍮の帯、下の板）・頭の冠（尖った塔の前が真鍮、後ろを覆うかぶとの下に琥珀の丸い核）・黒鉛の砲口。
    寸法は正面の絵（21.8 px/cm）、葉の平面形と真鍮の稜は真上の絵（縮尺が 0.8 倍なので 1.25 倍して読む）。部品の名前・原点・軸は前と同じ"""
    ivory, brass, dark = [], [], []
    # ハブ（黒鉛のこま形。下は砲口へすぼまる）
    dark.append(lathe((0, 0, 11.5), (0, 0, 31.0), [(0, 8.0), (0.25, 13.0), (0.5, 17.0), (0.78, 17.0), (1, 12.0)], 24))   # 葉の間に見える黒鉛を減らす
    dark.append(lathe((0, 0, 30.0), (0, 0, 32.2), [(0, 12.0), (1, 10.2)], 16))      # 核のまわりの輪
    # 前板（白磁の枕）とセンサーの窓の縁
    FC, FA = (0.0, -15.0, 23.5), (14.0, 13.5, 8.5, 8.0)
    front_plate = ell_plate(FC, FA, 6.0, 174.0, -78.0, 78.0, thick=3.0, dth=14, dph=13)
    ivory.append(front_plate)
    # 後ろの左右の角（30・150 度）にも同じ枕の板（センサーなし、赤道に真鍮の帯。絵の真横の中央の枕）。葉の間の黒鉛を覆う
    side_band = ell_plate(FC, FA, 86.0, 94.0, -74.0, 74.0, thick=1.2, grow=0.25, dth=8, dph=13)
    for ang in (120.0, -120.0):
        ivory.append(rot_z(front_plate, math.radians(ang)))
        brass.append(rot_z(side_band, math.radians(ang)))
    th_f = lambda z: math.degrees(math.acos(np.clip((z - FC[2]) / (FA[2] if z >= FC[2] else FA[3]), -1, 1)))
    dark.append(ell_plate(FC, FA, th_f(23.2), th_f(19.2), -35.0, 35.0, thick=0.5, grow=0.12, dth=6, dph=10))
    rig.add('sensor', 'body', (0, -28, 21.0), (1, 0, 0), [('sensor', ell_plate(FC, FA, th_f(22.5), th_f(19.9), -30.0, 30.0, thick=0.5, grow=0.3,
                                                                                  dth=6, dph=10))])
    # 葉の付け根の真鍮の軸
    for ang in (90.0, 210.0, 330.0):
        a = math.radians(ang)
        brass.append(cyl((13.5 * math.cos(a), 13.5 * math.sin(a), 24.5), (18.0 * math.cos(a), 18.0 * math.sin(a), 24.5), 3.4, 10))
    rig.add('body', None, (0, 0, 25.0), (1, 0, 0), [('ivory', merge(*ivory)), ('brass', merge(*brass)), ('dark', merge(*dark))])
    rig.parts.insert(0, rig.parts.pop())
    # 葉：+X へ伸ばして作り、角度へ回す。花びら形（外ほど幅が広い）のレンズ
    CX, CZ, AL, AW, AT, AB, KW = 29.0, 24.0, 12.5, 16.0, 9.0, 8.0, 0.36
    def lobe_pt(th, ph, g):
        st, ct = math.sin(th), math.cos(th)
        sp, cp = math.sin(ph), math.cos(ph)
        az = (AT if ct >= 0 else AB) * (1.0 - 0.5 * max(0.0, st * sp))     # 先ほど薄いレンズ
        return V3([CX + (AL + g) * st * sp, -(AW + g) * st * cp * (1 + KW * st * sp), CZ + (az + g) * ct])
    up_a = ell_plate(None, None, 0.0, 83.0, -87.0, 87.0, thick=1.0, dth=12, dph=15, pfn=lobe_pt)
    up_b = ell_plate(None, None, 0.0, 83.0, 93.0, 267.0, thick=1.0, dth=12, dph=15, pfn=lobe_pt)
    lo = ell_plate(None, None, 97.0, 180.0, -180.0, 180.0, thick=1.0, dth=14, dph=20, pfn=lobe_pt)
    band = ell_plate(None, None, 84.0, 96.0, -180.0, 180.0, thick=1.4, grow=0.3, dth=12, dph=15, pfn=lobe_pt)
    psi = np.linspace(-78.0, 80.0, 12)
    rp = [lobe_pt(math.radians(abs(q)), math.radians(90.0 if q >= 0 else 270.0), 0.0) for q in psi]
    ru = [p - V3([CX, 0.0, CZ - 4.0]) for p in rp]
    rw = [float(np.interp(q, [-78, 0, 80], [4.2, 3.4, 1.4])) for q in psi]
    rid = ridge(rp, ru, rw, h=1.0, sink=0.6)
    core_l = ell_solid((CX - 2.0, 0.0, CZ), (AL - 3.0, AW - 2.5, AT - 2.0, AB - 2.0), 14, 6)
    root = box((18.5, 0, 24.5), (6.0, 10.0, 8.0))
    for k, ang in enumerate((90.0, 210.0, 330.0)):
        a = math.radians(ang)
        piv = (17.0 * math.cos(a), 17.0 * math.sin(a), 25.0)
        rig.add(f'lobe_{k}', 'body', piv, (1, 0, 0), [('ivory', rot_z(merge(up_a, up_b, lo), a)), ('brass', rot_z(merge(band, rid), a)),
                                                     ('dark', rot_z(merge(root, core_l), a))])
    # 冠：後ろと横を覆うかぶと（前が尖った弧に開く）＋ 尖った塔（前の稜が真鍮）
    hood = ell_plate((0, 1.0, 30.5), (10.0, 9.5, 11.0, 2.0), 0.0, 90.0, 48.0, 312.0, thick=1.8, dth=15, dph=22)
    tower = prism((0, 3.0, 38.0), (0, 3.0, 51.5), [(0, 5.5, 5.5, 5.0), (0.55, 4.0, 4.5, 3.5), (1, 0.4, 0.5, 0.4)])
    stripe = prism((0, -2.0, 38.5), (0, 2.6, 51.0), [(0, 2.4, 1.1, 0.5), (1, 0.6, 0.5, 0.3)])
    rig.add('crown', 'body', (0, 8, 37.5), (1, 0, 0), [('ivory', merge(hood, tower)), ('brass', stripe)])
    core = ell_plate((0, 0.0, 30.0), (7.0, 7.0, 8.0, 1.0), 0.0, 90.0, -180.0, 180.0, thick=2.0, dth=18, dph=24)
    rig.add('core', 'crown', (0, -5, 35.0), (1, 0, 0), [('core', core)])
    # 砲口（下、黒鉛）
    muzzle = lathe((0, 0, 14.0), (0, 0, 1.5), [(0, 9.0), (0.45, 6.6), (0.55, 5.2), (0.62, 5.6), (0.8, 5.0), (1, 3.8)], 10)
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


# ---------------------------------------------------------------- 角ばった鎧の板（3e：盾型・子番機・突撃型の直し）

def armor_ring(w, f, b, keel=0.78, side=0.2):
    """鎧の断面（9 角形。(横, 前) の座標）：前は稜（f）、横は w、後ろは平ら（b）。keel：前の稜の肩の位置"""
    return [(0.0, f), (w * 0.62, f * keel), (w, f * side), (w, -b * 0.35), (w * 0.62, -b),
            (-w * 0.62, -b), (-w, -b * 0.35), (-w, f * side), (-w * 0.62, f * keel)]


def prism(p0, p1, secs, fwd=(0, -1, 0), keel=0.78, side=0.2, tilt=None):
    """角ばった鎧の塊：p0 → p1 の軸に沿って、断面 secs = [(t 0..1, 半幅 w, 前 f, 後ろ b)] をつなぐ（閉じた形）。
    断面は armor_ring（前に稜、後ろが平ら）。fwd は「前」の向き（軸に直角に直す）。s（横）= fwd × 軸。
    tilt = [(ts, tv), ...]（断面ごと）：断面の点を軸の向きへ ts × 横 + tv × 前 だけずらす = 板の縁を斜めに切る（絵の斜めの継ぎ目）"""
    p0, p1 = V3(p0, float), V3(p1, float)
    a = p1 - p0
    L = np.linalg.norm(a)
    a = a / L
    v = V3(fwd, float) - a * (V3(fwd, float) @ a)
    v = v / np.linalg.norm(v)
    s = np.cross(v, a)
    rings = []
    for i, (t, w, f, b) in enumerate(secs):
        c = p0 + a * (t * L)
        ts, tv = tilt[i] if tilt else (0.0, 0.0)
        rings.append([c + q[0] * s + q[1] * v + a * (ts * q[0] + tv * q[1]) for q in armor_ring(w, f, b, keel, side)])
    return loft_rings(rings)


def zloft(secs, poly):
    """高さ z ごとの断面の列 secs = [(z, *引数)] を、poly(*引数) → [(x, y)] の多角形（点の数は同じ）でつなぐ（閉じた形）"""
    return loft_rings([[(x, y, z) for x, y in poly(*arg)] for z, *arg in secs])


def shield(rig: Rig):
    """盾型（全高 180 cm）。3e：角ばった鎧の板を重ねる（黒鉛の芯の上に、隙間を空けた白磁の板。隙間が絵の黒い継ぎ目）。
    凧形の兜・中央に稜のある胸の 2 枚・前垂れ・背中の 2 枚（間が核の窓）・2 段の肩当て・本人の右の 3 段の籠手（真鍮の帯・黒鉛の拳）・
    脚は腿 2 段・膝当て・脛 2 段・長い靴（真鍮の底）。部品の名前・原点と、大盾の板の形（fx.gd の盾の面の点が使う）は前と同じ。
    寸法は絵（9.78 px/cm）に 5 cm の格子を重ねて測った（絵は体の中心が x = -7 cm にずれているので +7 して読む）"""
    ivory, brass, dark = [], [], []
    # 胴の芯（黒鉛）：胸は前へ張り出す（絵の真横で前の端 y = -35、背中 +18）。腰
    dark.append(prism((0, -3, 95), (0, -3, 147), [(0, 17, 18, 15), (0.4, 22, 22, 17), (1, 19, 20, 17)]))
    dark.append(prism((0, -2, 76), (0, -2, 100), [(0, 13, 12, 11), (1, 16, 15, 13)]))
    # 胸の板（左右 2 枚を中央で合わせる。中央に前の稜、下は V の先）
    def chest_poly(w, f, g=0.0, y0=-3.0):
        return [(g, y0 - f), (w * 0.55, y0 - f * 0.86), (w, y0 - f * 0.4), (w, y0 + 2.0), (g, y0 + 2.0)]
    chest = zloft([(96.5, 3.0, 22.0), (104, 12.0, 26.0), (113, 21.0, 28.5), (127, 24.5, 29.0), (137, 22.0, 25.0), (141, 16.0, 19.0)], chest_poly)
    # 背中の板（左右 2 枚。間 x ±8 が核の窓 = 黒鉛の芯が見える）
    def back_poly(w, b, g=8.0, y0=-1.0):
        return [(g, y0), (w, y0), (w, y0 + b * 0.55), (w * 0.8, y0 + b), (g, y0 + b)]
    backp = zloft([(105, 15.0, 15.0), (117, 22.0, 20.0), (140, 23.0, 20.0), (153, 17.0, 16.0)], back_poly)
    for p in (chest, backp):
        ivory += [p, mirror_x(p)]
    # 前垂れ・後ろの垂れ（中央、下が尖る）
    def flap(w, f, y0):
        return [(-w, y0), (w, y0), (w * 0.95, y0 + f * 0.75), (0.0, y0 + f), (-w * 0.95, y0 + f * 0.75)]
    ivory.append(zloft([(101, 9.5, -21.0, -2.0), (89, 7.5, -23.0, -2.0), (76, 1.2, -16.0, -2.0)], flap))
    ivory.append(zloft([(101, 9.0, 17.0, 0.0), (89, 7.0, 18.0, 0.0), (79, 1.2, 12.0, 0.0)], flap))
    # 肩当て（2 段：上の丸い板と、少し外へ開いた下の垂れ）と黒鉛の肩の関節
    for sg in (1, -1):
        c = (sg * 36.0, -2.0, 141.0)
        ivory.append(facet(c, (18.5, 19.0, 19.0, 12.0), 0.0, 92.0, n=8, m=3, thick=3.0))
        ivory.append(facet((c[0], c[1], c[2] - 1.5), (20.0, 20.5, 15.0, 21.0), 101.0, 134.0, n=8, m=2, thick=2.5))
        dark.append(cyl((sg * 15, -2, 140), (sg * 31, -2, 140), 8.0, 10))
    # 本人の左の腕（盾を持つ。黒鉛）
    dark.append(merge(cyl((34, 0, 128), (38, 0, 110), 6.0, 8), cyl((38, 0, 110), (46, -4, 123), 5.5, 8)))
    rig.add('body', None, (0, 0, 95.0), (1, 0, 0), [('ivory', merge(*ivory)), ('dark', merge(*dark))])
    # 核（背中の窓の奥の縦長の琥珀）
    rig.add('core', 'body', (0, 18, 122), (1, 0, 0), [('core', bbox((0, 15.0, 132), (9.5, 2.6, 30)))])
    # 兜：凧形（前に稜、上と下が尖る）。首は黒鉛
    def helm_poly(w, f, b, y0):
        return [(0.0, y0 - f), (w * 0.72, y0 - f * 0.55), (w, y0), (w * 0.6, y0 + b), (-w * 0.6, y0 + b), (-w, y0), (-w * 0.72, y0 - f * 0.55)]
    helm = zloft([(126.5, 2.0, 5.0, 2.0, -18.0), (136, 13.5, 15.0, 8.0, -15.0), (149, 18.0, 18.5, 11.0, -12.0),
                  (162, 13.0, 14.0, 9.0, -11.0), (178.5, 0.6, 1.0, 0.6, -13.0)], helm_poly)
    rig.add('head', 'body', (0, 0, 133.0), (1, 0, 0), [('ivory', helm), ('dark', cyl((0, -4, 125), (0, -4, 137), 8.0, 10))])
    # センサー：兜の前の稜をまたいで曲がる細い窓
    def surf_y(x, z=146.5):
        w, f, y0 = 17.4, 18.2, -12.4
        return y0 - f + (f * 0.45) * abs(x) / (w * 0.72)
    seg = lambda xa, xb: extrude([(-0.45, -1.3), (0.45, -1.3), (0.45, 1.3), (-0.45, 1.3)],
                                 (xa, surf_y(xa) - 0.55, 146.5), (xb, surf_y(xb) - 0.55, 146.5), up=(0, 0, 1))
    rig.add('sensor', 'head', (0, -30.5, 146.5), (1, 0, 0), [('sensor', merge(seg(-10.0, 0.0), seg(0.0, 10.0)))])
    # 本人の右の腕：上腕（黒鉛）・籠手（3 段の白磁の板と真鍮の帯）・拳（黒鉛、指の段）
    rig.add('upperarm_r', 'body', (-42, 0, 130.0), (1, 0, 0), [('dark', merge(cyl((-40, 0, 131), (-54, -3, 110), 7.0, 8),
                                                                                   disc((-53, -3, 111), 8.0, 9.0, 10)))])
    gx, gy = -58.0, -6.0
    tl = lambda n, k=-0.22: [(k, 0.0)] * n          # 板の縁を斜めに（体の側が高い）
    g_core = prism((gx, gy, 118), (gx, gy, 72), [(0, 14, 14, 13.5), (1, 13, 13, 12.5)])
    g_top = prism((gx, gy, 123.5), (gx, gy, 105), [(0, 8, 8, 8), (0.3, 15.5, 15.5, 15), (0.8, 17.2, 17.6, 16.2), (1, 16.4, 16.8, 15.4)], tilt=tl(4))
    g_mid = prism((gx, gy, 102), (gx, gy, 90), [(0, 16.8, 17.2, 15.8), (0.25, 18.0, 18.4, 17.0), (1, 18.4, 18.8, 17.4)], tilt=tl(3))
    g_low = prism((gx + 0.5, gy, 85.0), (gx + 1.0, gy - 1, 72.5), [(0, 17.6, 18.0, 16.6), (0.6, 17.0, 17.4, 16.0), (1, 14.6, 15.0, 13.6)], tilt=tl(3))
    g_band = prism((gx, gy, 89.6), (gx + 0.5, gy, 85.6), [(0, 19.0, 19.4, 18.0), (1, 18.8, 19.2, 17.8)], tilt=tl(2))
    fist = prism((-55, -9, 77), (-55, -9, 57), [(0, 10.5, 10, 9), (0.55, 12, 11.5, 10), (1, 9.5, 9, 8)])
    fingers = [prism((-61, -20.0, 73.5 - k * 4.3), (-49, -20.0, 73.5 - k * 4.3), [(0, 1.8, 2.2, 1.6), (1, 1.8, 2.2, 1.6)], fwd=(0, -1, 0))
               for k in range(4)]
    rig.add('forearm_r', 'upperarm_r', (-52, 0, 104.0), (1, 0, 0), [('ivory', merge(g_top, g_mid, g_low)), ('dark', merge(g_core, fist, *fingers)),
                                                                     ('brass', g_band)])
    # 大盾：六角の板（白磁）、真鍮の縁と稲妻の筋、黒鉛の握りと中心の円盤（真鍮の輪）。板と縁は前と同じ（fx.gd が使う）
    def xz_slab(poly, y0, y1):
        v, f = slab(poly, y0, y1)
        v = v[:, [1, 0, 2]]
        return v, orient(v, f)
    face = xz_slab([(56, 184), (80, 150), (78, 40), (58, 14), (38, 40), (36, 150)], -13.0, -9.0)
    rim = xz_slab([(56, 189), (83, 151), (81, 38), (58, 9), (35, 38), (33, 151)], -10.0, -6.5)
    back = xz_slab([(56, 184), (80, 150), (78, 40), (58, 14), (38, 40), (36, 150)], -6.6, -5.6)   # 3e：盾の裏も白磁（真鍮は縁だけ）
    bolt = [(57, 172), (49, 146), (47, 104), (63, 92), (56, 70), (54, 36)]
    stripes = []
    for (x0, z0), (x1, z1) in zip(bolt[:-1], bolt[1:]):
        d = np.array([x1 - x0, z1 - z0], float)
        n = np.array([-d[1], d[0]]) / np.linalg.norm(d) * 1.6
        e = d / np.linalg.norm(d) * 1.2
        quad = [(x0 - e[0] + n[0], z0 - e[1] + n[1]), (x1 + e[0] + n[0], z1 + e[1] + n[1]),
                (x1 + e[0] - n[0], z1 + e[1] - n[1]), (x0 - e[0] - n[0], z0 - e[1] - n[1])]
        stripes.append(xz_slab(quad, -13.8, -12.6))
    boss = cyl((58, -12.0, 125), (58, -15.5, 125), 6.5, 12)
    boss_ring = lathe((58, -12.2, 125), (58, -14.4, 125), [(0, 9.0), (1, 9.0)], 12)
    grip = cyl((44, -2, 123), (54, -7, 124), 3.5, 8)
    def turn(piece, deg=40.0, c=(58.0, -10.0)):
        v, f = piece
        a = math.radians(deg)
        x, y = v[:, 0] - c[0], v[:, 1] - c[1]
        v = np.stack([c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a), v[:, 2]], 1)
        return v, f
    rig.add('shield', 'body', (30, 5, 127.0), (0, 0, 1), [('ivory', turn(merge(face, back))), ('brass', turn(merge(rim, boss_ring, *stripes))),
                                                         ('dark', merge(turn(boss), grip))])
    # 脚（本人の左 = +X で作り、右は鏡写し）：腿 2 段・膝当て・脛 2 段の板を黒鉛の芯の上に。靴は長い楔、底は真鍮
    tk = lambda n, k=-0.3: [(k, 0.0)] * n           # 板の縁を斜めに（内側が低い。絵の膝・足首の斜めの継ぎ目）
    th_iv = merge(prism((27, -2, 104), (27, -2, 80), [(0, 12.5, 12.5, 11.5), (0.2, 15.5, 16.5, 13.5), (0.85, 16, 17, 13.5), (1, 14.5, 15.5, 12.5)], tilt=tk(4)),
                  prism((27.5, -3, 74.0), (27.5, -3.5, 63.5), [(0, 14.5, 15.5, 12), (0.3, 15.5, 17.5, 12.5), (1, 14, 16, 11)], tilt=tk(3)))
    th_dk = merge(prism((26, -1, 100), (26.5, -1, 60), [(0, 12, 12, 11), (1, 11, 11, 10)]), cyl((12, 0, 91), (30, 0, 91), 7.5, 10))
    sh_iv = merge(prism((26, -9.5, 64), (26, -12, 44), [(0, 7.5, 5, 3), (0.5, 10, 8, 3), (1, 7, 5, 3)]),   # 膝当て
                  prism((27, -1.5, 48.5), (27.5, -1.5, 38.5), [(0, 12.5, 12.5, 12.5), (0.3, 14.5, 14.5, 13.5), (1, 15, 15, 14)], tilt=tk(3, -0.25)),
                  prism((27.5, -2, 33.5), (28, -3, 21), [(0, 15, 15, 14), (0.6, 17, 18, 15.5), (1, 17.5, 19, 16)], tilt=tk(3, -0.25)))
    sh_dk = merge(prism((26, 0, 52), (27, 0, 18), [(0, 10.5, 10.5, 10.5), (1, 10, 10, 10)]), cyl((13, 0, 52), (35, 0, 52), 8, 10))
    def boot(secs, x0):
        v, f = loft(secs, 0.35)
        return v + V3([x0, 0, 0]), f
    ft_iv = merge(boot([(-38, 12.5, 1.5, 6.0, 9.5), (-27, 15.5, 1.5, 14.0, 11.5), (-9, 17.0, 1.5, 21.0, 12.5),
                        (11, 16.5, 1.5, 21.0, 12.5), (23, 14.0, 1.5, 12.0, 10.0)], 29.0),
                  boot([(-24, 12.5, 12.0, 19.0, 9.0), (2, 13.5, 17.0, 26.0, 10.0)], 29.0))
    ft_br = boot([(-40.5, 13.5, 0.0, 3.2, 13.5), (-27, 16.5, 0.0, 3.2, 16.5), (11, 17.5, 0.0, 3.2, 17.5), (25.5, 15.0, 0.0, 3.2, 15.0)], 29.0)
    ft_dk = cyl((17, 0, 16), (33, 0, 16), 6.5, 10)
    for sg, side in ((1, 'l'), (-1, 'r')):
        m = (lambda p: p) if sg > 0 else mirror_x
        hip, knee, ankle = V3([sg * 20, 0, 92.0]), V3([sg * 23, 0, 52.0]), V3([sg * 25, 0, 16.0])
        rig.add(f'thigh_{side}', 'body', hip, (1, 0, 0), [('ivory', m(th_iv)), ('dark', m(th_dk))])
        rig.add(f'shin_{side}', f'thigh_{side}', knee, (1, 0, 0), [('ivory', m(sh_iv)), ('dark', m(sh_dk))])
        rig.add(f'foot_{side}', f'shin_{side}', ankle, (1, 0, 0), [('ivory', m(ft_iv)), ('brass', m(ft_br)), ('dark', m(ft_dk))])


# 陰をなめらかにつなぐ面の角（度）。歩哨型は絵のように面の折れを見せる（3e）
SMOOTH_DEG = {'sentry': 17.0}

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
    B.smooth_by_angle(meshes, SMOOTH_DEG.get(t, 38.0))
    tri = sum(sum(len(pl.vertices) - 2 for pl in ob.data.polygons) for ob in meshes)
    os.makedirs(os.path.dirname(out_glb), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_yup=True, export_apply=False,
                              export_animations=False, use_selection=True)
    info = {'type': t, 'method': 'parts', 'triangles': tri, 'parts': sorted(objs.keys()), 'seconds': round(time.time() - t0, 1),
            'glb': os.path.relpath(out_glb, B.REPO)}
    log(str(info))
    return info
