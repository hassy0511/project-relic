"""大番機「閂」（W2-03 ボス）を、Codex の手描きの絵（r2）を見ながら部品ごとの 3D にする。

  npm run banki:build      （番機 5 種のあとにこれも走る）
  .venv-blender/bin/python tools/blender/recon/kannuki.py [--review]

できるもの
  godot/assets/models/kannuki.glb   モデル（部品の階層・材質は 4 つ：白磁・黒鉛・真鍮・琥珀の発光 banki_core）
  build/kannuki/review/             --review のとき：絵と Cycles の画像の比較（正面・真横・背面・真上・真下・斜め）
  build/kannuki/pose.json           肘を伸ばす角など、Godot の見本が使う数値

■ 番機（banki.py）と違う所
  番機は小さな卵・楔で、絵の外形を掛け合わせる視体積がよく合った。閂は 10 m の長い筒に 4 本の腕・爪・蓋がついた機械で、
  外形を掛け合わせると腕と胴が溶けてしまうので、絵の見た目（正面・背面・真横・真上・真下・腕の 3 枚・分解図・核を開いた図）を見ながら
  spec（spec_kannuki_3d_r2.md の寸法：全長 10.0 m・殻の直径 3.5 m・腕 4.0 m・蓋の滑り 0.6 m）どおりの数値で組む（spec が絵の縮尺に勝つ）。
  番機と同じなのは：部品の階層、原点 = 回転軸、ローカル +X = 回転軸の向き（Godot で「元の姿勢 * Basis(RIGHT, 角度)」）、
  色は最初から「清書の色」（白磁・黒鉛・真鍮の平らな塗り。部品ごと）、琥珀色の発光は別の材質 banki_core。

■ 座標（Blender、m）
  原点 = 地面の中心。長い軸は Y：錐の前端が -Y、角い受け口の後端が +Y（glTF では +Z が前）。上は +Z。+X は前から見て絵の右（本人の左）。
  胴の軸の高さは AXIS_Z = 2.6 m（腹の爪が地面のレールを挟む）。

■ 部品（親 → 子）と動き
  body                                       胴（白磁の殻）＋ 結束環・側帯（真鍮）＋ 芯・腹板・軸受け（黒鉛）
   ├ nose / tail                              前の鈍い錐 / 後ろの角い受け口（固定）
   ├ lid_f / lid_r                            背中の 2 枚の蓋。ローカル +X の向きへ最大 0.6 m 滑って離れる（回転ではなく平行移動）
   ├ keyplate                                 錠前の真鍮の板。後ろの縁が軸（ローカル +X）で、上へ約 100 度開く（蓋が開くとき一緒に）
   ├ clamp_f / clamp_r                        腹のレール把持部（黒鉛）── claw_*_l/r：真鍮の爪。ローカル +X（胴の前後の向き）で開閉
   └ arm_{fl,fr,rl,rr}_yaw                    肩の縦軸（Z）：外側へ約 45 度（前の腕は +角度が外向き）
        └ …_pitch                             肩の横軸：上下約 25 度
             └ …_elbow                         肘：0 ～ 90 度（畳んだ姿勢が元の姿勢。pose.json の elbow_straight が「伸ばした」角）
                  └ …_drill                    削岩錐：長手の軸（ローカル +X）で連続 360 度の自転
  核：琥珀の六角の回転子 core（body の子・上向き）と両脇のローラー。蓋（lid_*）と板（keyplate）が閉じていると隠れる。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import banki as B   # noqa: E402  make_materials・new_object・axis_matrix・smooth_by_angle を使い回す

REPO = B.REPO
WORK = os.path.join(REPO, 'build', 'kannuki')
SRC = os.path.join(WORK, 'r2')
ART_REF = 'origin/art/w2-kannuki:art/concepts/W2_kannuki'
OUT = os.path.join(B.MODELS, 'kannuki.glb')
AXIS_Z = 2.6
R_SHELL = 1.5
CORE_AMBER = '#F59A2A'
V3 = np.array


def log(msg):
    print(f'[kannuki] {msg}', flush=True)


# ---------------------------------------------------------------- 形の道具（m）

def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def orient(v, faces):
    """符号つきの体積が負なら面を全部裏返す（外向きにそろえる）"""
    vol = 0.0
    for f in faces:
        for k in range(1, len(f) - 1):
            vol += np.dot(v[f[0]], np.cross(v[f[k]], v[f[k + 1]]))
    return [f[::-1] for f in faces] if vol < 0 else faces


def frame(a, up=(0, 0, 1)):
    a = unit(a)
    up = unit(up)
    if abs(a @ up) > 0.98:
        up = np.array([0, 1.0, 0]) if abs(a[1]) < 0.9 else np.array([1.0, 0, 0])
    side = unit(np.cross(a, up))
    return a, side, np.cross(side, a)


def extrude(poly, p0, p1, up=(0, 0, 1)):
    """凸の断面 poly（(側, 上) の m）を p0 → p1 へ押し出す"""
    p0, p1 = V3(p0, float), V3(p1, float)
    a, s, u = frame(p1 - p0, up)
    n = len(poly)
    v = [p + q[0] * s + q[1] * u for p in (p0, p1) for q in poly]
    f = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    f += [list(range(n))[::-1], list(range(n, 2 * n))]
    v = V3(v)
    return v, orient(v, f)


def cham_rect(w, h, c):
    """面取りした長方形（半幅 w・半高 h・面取り c）"""
    return [(-w, -h + c), (-w + c, -h), (w - c, -h), (w, -h + c), (w, h - c), (w - c, h), (-w + c, h), (-w, h - c)]


def box(c, size, up=(0, 0, 1)):
    c = V3(c, float)
    h = V3(size, float) / 2
    return extrude([(-h[0], -h[2]), (h[0], -h[2]), (h[0], h[2]), (-h[0], h[2])],
                   c - (0, h[1], 0), c + (0, h[1], 0), up=(0, 0, 1))


def lathe(p0, p1, prof, segs=16, up=(0, 0, 1), cap=True):
    """p0 → p1 の軸のまわりに、輪郭 prof = [(軸に沿った割合 0..1, 半径)] を回す"""
    p0, p1 = V3(p0, float), V3(p1, float)
    L = np.linalg.norm(p1 - p0)
    a, s, u = frame(p1 - p0, up)
    verts, rings = [], []
    for t, r in prof:
        c = p0 + a * (t * L)
        if r < 1e-6:
            verts.append(c)
            rings.append([len(verts) - 1] * segs)
        else:
            ids = []
            for k in range(segs):
                ph = 2 * math.pi * k / segs
                verts.append(c + r * (math.cos(ph) * s + math.sin(ph) * u))
                ids.append(len(verts) - 1)
            rings.append(ids)
    faces = []
    for i in range(len(prof) - 1):
        for k in range(segs):
            q = [rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]]
            d = [x for j, x in enumerate(q) if x != q[j - 1]]
            if len(d) >= 3:
                faces.append(d)
    if cap:
        for ring in (rings[0], rings[-1]):
            if len(set(ring)) > 1:
                faces.append(list(ring))
    v = V3(verts)
    return v, orient(v, faces)


def cyl(p0, p1, r, segs=12):
    return lathe(p0, p1, [(0, r), (1, r)], segs)


def helix(p0, p1, r0, r1, turns, width, height, n=14, phase=0.0):
    """円錐（p0 の半径 r0 → p1 の半径 r1）の上を巻く帯（削岩錐の真鍮の螺旋）。phase：巻き始めの角（ラジアン）"""
    p0, p1 = V3(p0, float), V3(p1, float)
    L = np.linalg.norm(p1 - p0)
    a, s, u = frame(p1 - p0)
    rings = []
    m = int(turns * n)
    slope = (r1 - r0) / L
    for i in range(m + 1):
        t = i / m
        ph = 2 * math.pi * turns * t + phase
        rad = math.cos(ph) * s + math.sin(ph) * u
        c = p0 + a * (t * L)
        r = r0 + (r1 - r0) * t
        pts = []
        for da, dr in ((-width / 2, -0.03), (-width * 0.3, height), (width * 0.3, height), (width / 2, -0.03)):
            pts.append(c + a * da + rad * max(r + dr + slope * da, 0.0))
        rings.append(pts)
    verts = [p for r in rings for p in r]
    faces = []
    for i in range(m):
        for k in range(4):
            faces.append([4 * i + k, 4 * i + (k + 1) % 4, 4 * (i + 1) + (k + 1) % 4, 4 * (i + 1) + k])
    faces.append([0, 1, 2, 3][::-1])
    faces.append([4 * m + k for k in range(4)])
    v = V3(verts)
    return v, orient(v, faces)


def merge(*pieces):
    vs, fs, off = [], [], 0
    for v, f in pieces:
        vs.append(v)
        fs += [[i + off for i in fc] for fc in f]
        off += len(v)
    return np.concatenate(vs), fs


# ---------------------------------------------------------------- 部品の組み立て

PARTS: list[dict] = []


def add(name, parent, pivot, axis, pieces):
    """pieces = [(材質, (頂点 m, 面))]。先頭の材質が部品本体、残りは同じ原点・向きの子（例：name + '_brass'）"""
    PARTS.append(dict(name=name, parent=parent, pivot=V3(pivot, float), axis=unit(axis), pieces=pieces))


def mirrored(part, name, parent, sx, sy, y0):
    """x（sx = -1 で左右）・y（sy = -1 で y0 を中心に前後）に鏡映した部品。回転軸は擬ベクトルなので符号を sx*sy で直す"""
    def T(p):
        p = V3(p, float).copy()
        p[..., 0] *= sx
        if sy < 0:
            p[..., 1] = 2 * y0 - p[..., 1]
        return p
    ax = V3([sx * part['axis'][0], sy * part['axis'][1], part['axis'][2]]) * (sx * sy)
    pcs = [(m, (T(v), orient(T(v), f))) for m, (v, f) in part['pieces']]
    return dict(name=name, parent=parent, pivot=T(part['pivot']), axis=unit(ax), pieces=pcs)


R_PLATE = 1.42     # 3e：胴の板の外の半径（前は殻 1.5）。結束環 1.75 は同じ = 外形の大きさは同じで、環の間の胴を細く見せる
R_CORE = 1.30      # 黒鉛の芯


def sector_prism(y0, y1, a0, a1, r_out, thick, n, bev=0.05, zc=None):
    """胴の軸（Y、高さ zc）のまわりの板：角 a0 → a1（度。0 = +X、90 = 上）を n 面の平らな殻にし、y0 → y1 へ押し出す。
    両端は bev だけ面取り（外の半径を縮める）"""
    zc = AXIS_Z if zc is None else zc
    angs = np.radians(np.linspace(a0, a1, n + 1))
    def ring(y, ro):
        ri = ro - thick
        out = [(ro * math.cos(a), y, zc + ro * math.sin(a)) for a in angs]
        inn = [(ri * math.cos(a), y, zc + ri * math.sin(a)) for a in angs[::-1]]
        return out + inn
    rings = [ring(y0, r_out - bev), ring(y0 + bev, r_out), ring(y1 - bev, r_out), ring(y1, r_out - bev)]
    m = len(rings[0])
    v = V3([p for r in rings for p in r], float)
    f = []
    for i in range(len(rings) - 1):
        for k in range(m):
            f.append([i * m + k, i * m + (k + 1) % m, (i + 1) * m + (k + 1) % m, (i + 1) * m + k])
    f.append(list(range(m))[::-1])
    f.append([(len(rings) - 1) * m + k for k in range(m)])
    return v, orient(v, f)


def strip(pts, normal_fn, w=0.018, lift=0.006):
    """面の上の細い線（ひび）：点の列 pts に沿った幅 w の帯を、面の外向き normal_fn(p) へ lift だけ浮かせた片面の板"""
    pts = [V3(p, float) for p in pts]
    verts, faces = [], []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        n = unit(normal_fn(p))
        sd = unit(np.cross(n, t))
        q = p + n * lift
        verts += [q - sd * w * 0.5, q + sd * w * 0.5]
    for i in range(len(pts) - 1):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
        f = [a, b, c, d]
        nrm = np.cross(V3(verts[b]) - V3(verts[a]), V3(verts[d]) - V3(verts[a]))
        if nrm @ unit(normal_fn(pts[i])) < 0:
            f = f[::-1]
        faces.append(f)
    return V3(verts), faces


def build_body():
    """3e：胴は滑らかな筒をやめ、黒鉛の芯の上に長い白磁の板（上の横・下の横・背の前後）を継ぎ目を空けて貼る（絵の真横の長い板と暗い継ぎ目）。
    結束環（真鍮）には暗い切り欠き、板の角に真鍮の留め具、横に配管（黒鉛）、板にひび（黒鉛の細い線）"""
    zc = AXIS_Z
    y_rf, y_rr = -2.6, 3.0                     # 結束環の中心
    ya, yb = y_rf + 0.27, y_rr - 0.27          # 環の間
    ivory, brass, dark = [], [], []
    for sx in (1, -1):
        mx = (lambda p: p) if sx > 0 else (lambda p, sx=sx: (p[0] * V3([-1, 1, 1]), orient(p[0] * V3([-1, 1, 1]), p[1])))
        ivory.append(mx(sector_prism(ya, yb, 9.0, 61.0, R_PLATE, 0.14, 3)))              # 上の横の長い板
        ivory.append(mx(sector_prism(ya + 0.1, yb - 0.1, -56.0, 4.0, R_PLATE - 0.03, 0.14, 3)))   # 下の横の長い板
        for y0, y1 in ((ya, -1.45), (1.80, yb)):
            ivory.append(mx(sector_prism(y0, y1, 65.0, 90.0, R_PLATE, 0.14, 1)))        # 背の板（蓋の前後）
    # 真鍮：結束環 2 本・側帯（上下の板の継ぎ目）・蓋の走り・留め具
    ring = lambda y: lathe((0, y - 0.25, zc), (0, y + 0.25, zc), [(0, 1.5), (0.06, 1.75), (0.94, 1.75), (1, 1.5)], 20)
    brass += [ring(y_rf), ring(y_rr)]
    for sx in (-1, 1):
        brass.append(box((sx * 1.44, 0.2, zc + 0.04), (0.1, yb - ya - 0.2, 0.12)))
        brass.append(box((sx * 0.98, 0.15, zc + 1.05), (0.22, 4.3, 0.1)))          # 蓋の走り（楔の蓋の低い端から出ない高さ）
        for y in (ya + 0.25, -1.0, 1.3, yb - 0.25):
            for a in (16.0, 54.0):
                ar = math.radians(a)
                c = V3([sx * R_PLATE * math.cos(ar), y, zc + R_PLATE * math.sin(ar)])
                nrm = V3([sx * math.cos(ar), 0, math.sin(ar)])
                brass.append(cyl(c - nrm * 0.02, c + nrm * 0.045, 0.06, 6))
    # 黒鉛：芯・腹板・肩の軸受け・環の切り欠き・配管・ひび
    dark += [cyl((0, -3.75, zc), (0, 3.95, zc), R_CORE, 16),
             box((0, 0.1, zc - 1.42), (2.0, 4.9, 0.3)),
             cyl((0, -3.8, zc), (0, -3.6, zc), 1.42, 20), cyl((0, 3.3, zc), (0, 3.5, zc), 1.42, 20)]
    for yr in (y_rf, y_rr):
        for a in (25.0, 155.0, -25.0, -155.0):
            ar = math.radians(a)
            c = V3([1.76 * math.cos(ar), yr, zc + 1.76 * math.sin(ar)])
            dark.append(extrude([(-0.025, -0.09), (0.025, -0.09), (0.025, 0.09), (-0.025, 0.09)], c - (0, 0.03, 0), c + (0, 0.03, 0),
                                up=(-math.sin(ar), 0, math.cos(ar))))
    sh = shoulder_points()
    for s_ in sh.values():
        sx = np.sign(s_[0])
        dark.append(cyl((s_[0] - 0.6 * sx, s_[1], s_[2]), (s_[0], s_[1], s_[2]), 0.5, 12))
        # 肩から胴へ入る配管 2 本
        toward = y_rf if s_[1] < 0 else y_rr
        for dz, dy in ((-0.25, 0.0), (-0.55, 0.15)):
            p0 = V3([s_[0] - 0.1 * sx, s_[1], s_[2] + dz])
            p1 = V3([sx * 1.25, toward + (0.3 if s_[1] < 0 else -0.3), zc + 0.35 + dz])
            dark.append(cyl(p0, p1, 0.065, 6))
    for sx in (-1, 1):
        a = math.radians(-60.0)
        dark.append(cyl((sx * 1.43 * math.cos(a), ya, zc + 1.43 * math.sin(a)), (sx * 1.43 * math.cos(a), yb, zc + 1.43 * math.sin(a)), 0.07, 6))
        # ひび（板の上の細い線）
        nrm = lambda p: V3([p[0], 0, p[2] - zc])
        on = lambda a, y, r=R_PLATE + 0.003: (sx * r * math.cos(math.radians(a)), y, zc + r * math.sin(math.radians(a)))
        for pts in ([on(52, -1.9), on(44, -1.6), on(47, -1.25), on(38, -0.95)],
                    [on(20, 1.1), on(28, 1.45), on(24, 1.7), on(33, 2.05)],
                    [on(-14, -1.4), on(-22, -1.05), on(-17, -0.7)],
                    [on(-30, 2.1), on(-38, 2.3), on(-33, 2.55)]):
            dark.append(strip(pts, nrm))
    add('body', None, (0, 0.2, zc), (1, 0, 0), [('ivory', merge(*ivory)), ('brass', merge(*brass)), ('dark', merge(*dark))])


def build_ends():
    zc = AXIS_Z
    # 3e：前の錐は 8 面の角ばった錐（絵の正面の多面の丸屋根）。上下の稜に真鍮の筋
    cone = lathe((0, -5.0, zc), (0, -3.7, zc), [(0, 0.3), (0.3, 0.74), (0.7, 1.12), (1, 1.30)], 8)   # 3e：根元を 1.42 → 1.30（環との間に暗い帯）
    tip = lathe((0, -5.08, zc), (0, -4.7, zc), [(0, 0.0), (0.4, 0.22), (1, 0.32)], 8)
    band = lathe((0, -3.8, zc), (0, -3.68, zc), [(0, 1.33), (1, 1.33)], 16)
    ridges = []
    for sz in (1, -1):
        prof = [(-4.98, 0.33), (-4.61, 0.75), (-4.09, 1.13), (-3.72, 1.31)]
        pts = [V3([0.0, y, zc + sz * (r * math.cos(math.pi / 8) + 0.012)]) for y, r in prof]
        rings = []
        for i, q in enumerate(pts):
            t = pts[min(i + 1, 3)] - pts[max(i - 1, 0)]
            up = unit(np.cross(t, (1, 0, 0))) * (-sz)
            rings.append([q - (0.11, 0, 0), q + (0.11, 0, 0), q + (0.07, 0, 0) + up * 0.05, q - (0.07, 0, 0) + up * 0.05])
        v = V3([x for r in rings for x in r])
        f = [[4 * i + k, 4 * i + (k + 1) % 4, 4 * (i + 1) + (k + 1) % 4, 4 * (i + 1) + k] for i in range(3) for k in range(4)]
        f += [[3, 2, 1, 0], [12, 13, 14, 15]]
        ridges.append((v, orient(v, f)))
    add('nose', 'body', (0, -4.4, zc), (1, 0, 0), [('ivory', cone), ('brass', merge(tip, band, *ridges))])
    o, i = 0.9, 0.52
    slabs = [box((0, 4.47, zc + (o + i) / 2), (2 * o, 1.05, o - i)), box((0, 4.47, zc - (o + i) / 2), (2 * o, 1.05, o - i)),
             box(((o + i) / 2, 4.47, zc), (o - i, 1.05, 2 * i)), box((-(o + i) / 2, 4.47, zc), (o - i, 1.05, 2 * i))]
    collar = lathe((0, 3.9, zc), (0, 4.05, zc), [(0, 1.2), (1, 1.2)], 16)
    back = box((0, 4.3, zc), (2 * i + 0.02, 0.7, 2 * i + 0.02))
    add('tail', 'body', (0, 4.45, zc), (1, 0, 0), [('ivory', merge(*slabs)), ('brass', collar), ('dark', back)])


def build_core():
    zc = AXIS_Z
    yc = 0.15
    # 錠前核：六角の回転子（琥珀）と両脇のローラー
    # 3e：六角の宝石（上の面が面取りで尖る）と、両脇の歯のついたローラー（歯は胴の黒鉛の輪）
    hexr = lathe((0, yc, zc + 1.22), (0, yc, zc + 1.70), [(0, 0.42), (0.45, 0.52), (0.72, 0.5), (1, 0.3)], 6, up=(1, 0, 0))
    rollers = [cyl((-0.45, yc + d, zc + 1.5), (0.45, yc + d, zc + 1.5), 0.15, 12) for d in (-0.39, 0.39)]
    add('core', 'body', (0, yc, zc + 1.3), (1, 0, 0), [('core', merge(hexr, *rollers))])
    # 蓋（滑る）
    def lid(y_core, y_out):
        # 3e：箱をやめて楔に（核の側が高く、環の側へ下がって細る。絵の真横の台形）
        import banki_parts as BP
        def ring(y, w1, z1, zm):
            return [(-1.1, y, zc + 0.8), (-1.1, y, zm), (-w1, y, z1), (w1, y, z1), (1.1, y, zm), (1.1, y, zc + 0.8)]
        mid = y_core + (y_out - y_core) * 0.35
        return BP.loft_rings([ring(y_core, 0.78, zc + 1.88, zc + 1.2), ring(mid, 0.74, zc + 1.8, zc + 1.2),
                              ring(y_out, 0.56, zc + 1.42, zc + 1.12)])
    lf, lr = lid(-0.38, -1.33), lid(0.68, 1.68)
    trim_f = box((0, -0.41, zc + 1.6), (1.3, 0.06, 0.3))
    trim_r = box((0, 0.71, zc + 1.6), (1.3, 0.06, 0.3))
    add('lid_f', 'body', (0, -0.855, zc + 1.4), (0, -1, 0), [('ivory', lf), ('brass', trim_f)])
    add('lid_r', 'body', (0, 1.18, zc + 1.4), (0, 1, 0), [('ivory', lr), ('brass', trim_r)])
    # 錠前の板（真鍮）：前の縁を軸に上へ開く
    plate = box((0, yc, zc + 1.62), (1.0, 0.52, 0.16))
    slot = merge(cyl((0, yc, zc + 1.69), (0, yc, zc + 1.72), 0.1, 10), box((0, yc, zc + 1.7), (0.09, 0.0 + 0.3, 0.03), up=(0, 0, 1)))
    add('keyplate', 'body', (0, yc - 0.26, zc + 1.58), (1, 0, 0), [('brass', plate), ('dark', slot)])


def build_clamps():
    zc = AXIS_Z
    for nm, y in (('f', -1.7), ('r', 1.5)):
        head = merge(box((0, y, 0.98), (1.4, 0.85, 0.36)), cyl((-0.42, y, 1.3), (-0.42, y, 0.85), 0.11, 8),
                     cyl((0.42, y, 1.3), (0.42, y, 0.85), 0.11, 8))
        add(f'clamp_{nm}', 'body', (0, y, 1.0), (1, 0, 0), [('dark', head)])
        for sx, tag in ((1, 'l'), (-1, 'r')):
            # 爪：付け根（x = ±0.62, z = 0.9）から外へ張り出して下がり、先が内向きに曲がる鉤
            path = [(0.0, 0.0), (0.22, -0.08), (0.36, -0.28), (0.36, -0.5), (0.24, -0.72), (0.05, -0.8)]
            vs, fs = [], []
            pts = [V3([sx * (0.62 + a), y, 0.85 + b]) for a, b in path]
            n = len(pts)
            ring = []
            for i, p in enumerate(pts):
                d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
                d /= np.linalg.norm(d)
                nx = V3([d[2], 0, -d[0]]) if True else None
                nx /= np.linalg.norm(nx)
                ring.append([p + nx * 0.09 + V3([0, 0.32, 0]), p + nx * 0.09 - V3([0, 0.32, 0]),
                             p - nx * 0.09 - V3([0, 0.32, 0]), p - nx * 0.09 + V3([0, 0.32, 0])])
            verts = [q for r in ring for q in r]
            faces = []
            for i in range(n - 1):
                for k in range(4):
                    faces.append([4 * i + k, 4 * i + (k + 1) % 4, 4 * (i + 1) + (k + 1) % 4, 4 * (i + 1) + k])
            faces.append([3, 2, 1, 0])
            faces.append([4 * (n - 1) + k for k in (0, 1, 2, 3)])
            v = V3(verts)
            claw = (v, orient(v, faces))
            pin = cyl((sx * 0.62, y - 0.36, 0.85), (sx * 0.62, y + 0.36, 0.85), 0.13, 8)
            add(f'claw_{nm}_{tag}', f'clamp_{nm}', (sx * 0.62, y, 0.85), (0, 1, 0) if sx > 0 else (0, -1, 0),
                [('brass', claw), ('dark', pin)])


def shoulder_points():
    """肩の位置（m、世界）"""
    out = {}
    for arm, (sx, sy) in {'fl': (1, 1), 'fr': (-1, 1), 'rl': (1, -1), 'rr': (-1, -1)}.items():
        p = V3([1.55, -3.2, AXIS_Z + 0.5])
        p[0] *= sx
        if sy < 0:
            p[1] = 2 * ARM_Y0 - p[1]
        out[arm] = p
    return out


ARM_Y0 = 0.175   # 前の腕の肩 y = -3.2、後ろ = +3.55 の中間


def arm_geometry():
    S = V3([1.55, -3.2, AXIS_Z + 0.5])
    u = unit((0.25, -0.6, 0.4))
    f = unit((0.12, -0.45, -0.88))
    E = S + u * 1.3
    D0 = E + f * 1.1
    T = D0 + f * 1.6
    ea = unit(np.cross(u, f))
    uh = V3([u[0], u[1], 0])
    pa = unit(np.cross((0, 0, 1), uh))
    return S, E, D0, T, u, f, ea, pa


def build_arm_fl():
    S, E, D0, T, u, f, ea, pa = arm_geometry()
    # 肩の縦軸（回る台座）
    turret = cyl(S - (0, 0, 0.55), S + (0, 0, 0.55), 0.36, 12)
    ringz = cyl(S + (0, 0, 0.5), S + (0, 0, 0.62), 0.5, 14)
    add('arm_fl_yaw', 'body', S, (0, 0, 1), [('dark', turret), ('brass', ringz)])
    # 上腕（肩の横軸）。3e：角ばった板 2 枚（上腕の板に肩当てを重ねる）、油圧の棒、真鍮の軸の蓋
    import banki_parts as BP
    up_u = np.cross(ea, u)
    upper = BP.prism(S + u * 0.3, E - u * 0.25, [(0, 0.30, 0.27, 0.22), (0.3, 0.37, 0.33, 0.25), (1, 0.33, 0.29, 0.23)], fwd=up_u)
    guard = BP.prism(S + u * 0.12, S + u * 0.62, [(0, 0.36, 0.33, 0.2), (0.6, 0.43, 0.40, 0.27), (1, 0.40, 0.37, 0.25)], fwd=up_u)
    hub = cyl(S - pa * 0.42, S + pa * 0.42, 0.42, 12)
    ehub = cyl(E - ea * 0.45, E + ea * 0.45, 0.3, 10)
    caps = merge(cyl(S + pa * 0.42, S + pa * 0.47, 0.22, 6), cyl(S - pa * 0.47, S - pa * 0.42, 0.22, 6))
    rod = cyl(S + u * 0.35 - up_u * 0.24 + ea * 0.28, E - u * 0.3 - up_u * 0.24 + ea * 0.28, 0.06, 6)
    sleeve = cyl(S + u * 0.35 - up_u * 0.24 + ea * 0.28, S + u * 0.75 - up_u * 0.24 + ea * 0.28, 0.1, 6)
    add('arm_fl_pitch', 'arm_fl_yaw', S, pa, [('ivory', merge(upper, guard)), ('brass', merge(hub, ehub, caps)), ('dark', merge(rod, sleeve))])
    # 前腕（肘）。角ばった板と白磁の襟、真鍮の帯
    up_f = np.cross(ea, f)
    fore = BP.prism(E + f * 0.22, D0 - f * 0.34, [(0, 0.29, 0.26, 0.22), (0.35, 0.35, 0.31, 0.25), (1, 0.32, 0.29, 0.23)], fwd=up_f)
    collar = lathe(D0 - f * 0.42, D0 + f * 0.02, [(0, 0.44), (1, 0.5)], 12)
    ebolt = cyl(E - ea * 0.5, E + ea * 0.5, 0.2, 8)
    band = lathe(D0 - f * 0.03, D0 + f * 0.08, [(0, 0.52), (1, 0.52)], 12)
    add('arm_fl_elbow', 'arm_fl_pitch', E, ea, [('ivory', merge(fore, collar)), ('dark', ebolt), ('brass', band)])
    # 削岩錐（自転）。3e：鋼の円すいに螺旋の溝（黒鉛の稜）と真鍮の螺旋・真鍮の帯 3 本・真鍮の先
    L = np.linalg.norm(T - D0)
    cone = lathe(D0 + f * 0.08, T, [(0, 0.47), (1, 0.0)], 12)
    r_at = lambda d: 0.47 * (1 - (d - 0.08) / (L - 0.08))
    flute = helix(D0 + f * 0.1, T - f * 0.2, r_at(0.1) * 0.97, r_at(L - 0.2), 2.25, 0.12, 0.05, n=9, phase=math.pi)
    hx = helix(D0 + f * 0.1, T - f * 0.12, 0.47 * 0.96, 0.02, 2.25, 0.15, 0.06, n=9)
    bands = [lathe(D0 + f * (d - 0.03), D0 + f * (d + 0.035), [(0, r_at(d) + 0.035), (1, r_at(d + 0.035) + 0.035)], 12)
             for d in (0.24, 0.62, 1.0)]
    tipc = lathe(T - f * 0.26, T + f * 0.02, [(0, 0.09), (1, 0.0)], 8)
    add('arm_fl_drill', 'arm_fl_elbow', D0, f, [('dark', merge(cone, flute)), ('brass', merge(hx, tipc, *bands))])


def build_arms():
    build_arm_fl()
    base = {p['name']: p for p in PARTS if p['name'].startswith('arm_fl_')}
    for arm, (sx, sy) in {'fr': (-1, 1), 'rl': (1, -1), 'rr': (-1, -1)}.items():
        for k in ('yaw', 'pitch', 'elbow', 'drill'):
            src = base[f'arm_fl_{k}']
            par = 'body' if k == 'yaw' else f'arm_{arm}_' + ('yaw', 'pitch', 'elbow')[('pitch', 'elbow', 'drill').index(k)]
            PARTS.append(mirrored(src, f'arm_{arm}_{k}', par, sx, sy, ARM_Y0))


# ---------------------------------------------------------------- Blender

def build() -> dict:
    import bpy
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PARTS.clear()
    build_body()
    build_ends()
    build_core()
    build_clamps()
    build_arms()
    mats = B.make_materials('kannuki', None)
    ivory = mats['shell_flat'].copy()      # 白磁（spec #F3E9D2 × 0.95）。番機の清書の色より少しだけ明るい
    ivory.name = 'banki_ivory'
    ivory.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*B.srgb_to_linear('#E9DFC9'), 1)
    # 3e：琥珀を濃く（絵の核は深い橙。前の #FFBC52・発光 1.5 は淡く見えた）。ゲームでは enemy_view.gd が色を決める
    cb = mats['core'].node_tree.nodes['Principled BSDF']
    cb.inputs['Base Color'].default_value = (*B.srgb_to_linear(CORE_AMBER), 1)
    cb.inputs['Emission Color'].default_value = (*B.srgb_to_linear(CORE_AMBER), 1)
    cb.inputs['Emission Strength'].default_value = 1.0
    matmap = {'ivory': ivory, 'dark': mats['dark'], 'brass': mats['brass'], 'core': mats['core']}
    objs = {}
    meshes = []
    for p in PARTS:
        rot = B.axis_matrix(p['axis'])
        piv = p['pivot'] * 100.0
        first = None
        for i, (mk, (v, f)) in enumerate(p['pieces']):
            nm = p['name'] if i == 0 else f"{p['name']}_{mk}"
            ob = B.new_object(nm, v * 100.0, f, matmap[mk], piv, rot)
            meshes.append(ob)
            if first is None:
                first = ob
                objs[p['name']] = ob
            else:
                mw = ob.matrix_world.copy()
                ob.parent = first
                ob.matrix_world = mw
    root = bpy.data.objects.new('kannuki', None)
    bpy.context.scene.collection.objects.link(root)
    for p in PARTS:
        ob = objs[p['name']]
        mw = ob.matrix_world.copy()
        ob.parent = objs[p['parent']] if p['parent'] else root
        ob.matrix_world = mw
    B.smooth_by_angle(meshes, 38.0)
    tri = sum(sum(len(pl.vertices) - 2 for pl in ob.data.polygons) for ob in meshes)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, export_apply=False,
                              export_animations=False, use_selection=True)
    # 見本のための数値
    S, E, D0, T, u, f, ea, pa = arm_geometry()
    phi = math.atan2(np.dot(np.cross(f, u), ea), np.dot(f, u))
    pose = {'elbow_straight_deg': round(math.degrees(phi), 2), 'arm_len_m': round(float(np.linalg.norm(E - S) + np.linalg.norm(T - E)), 2),
            'tip_fl_m': [round(float(x), 2) for x in T]}
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, 'pose.json'), 'w') as fh:
        json.dump(pose, fh, indent=1)
    info = {'triangles': tri, 'parts': len(PARTS), 'objects': len(meshes), 'seconds': round(time.time() - t0, 1), 'pose': pose}
    log(json.dumps(info, ensure_ascii=False))
    return info


# ---------------------------------------------------------------- 確認（絵と Cycles の画像を並べる）

TILE = 400
PX_PER_M = 166.0      # 側面・真上・真下の絵：全長 10 m = 1660 px（spec）


def fetch_art():
    import subprocess
    os.makedirs(SRC, exist_ok=True)
    for n in ('3d_front', '3d_back', '3d_side_right', '3d_top', '3d_bottom', '3d_front_right45', 'arm_side', 'arm_top', 'arm_front'):
        p = os.path.join(SRC, f'kannuki_{n}_r2.png')
        if not os.path.exists(p):
            r = subprocess.run(['git', 'show', f'{ART_REF}/kannuki_{n}_r2.png'], cwd=REPO, capture_output=True)
            if r.returncode == 0:
                with open(p, 'wb') as fh:
                    fh.write(r.stdout)


def render_review(out_dir):
    import bpy
    from mathutils import Matrix, Vector
    from PIL import Image, ImageDraw
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 16
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = TILE
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.82, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    sc.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 2.0
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2048 / PX_PER_M
    cam.data.clip_end = 60
    sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    pts = np.array([ob.matrix_world @ v.co for ob in bpy.data.objects if ob.type == 'MESH' and 'core' not in ob.name for v in ob.data.vertices])
    views = [('front', (0, -1, 0), (0, 0, 1)), ('side', (1, 0, 0), (0, 0, 1)), ('back', (0, 1, 0), (0, 0, 1)),
             ('top', (0, 0, 1), (-1, 0, 0)), ('bottom', (0, 0, -1), (1, 0, 0)), ('front_right45', (0.7071, -0.7071, 0), (0, 0, 1))]
    art_name = {'side': '3d_side_right', 'front': '3d_front', 'back': '3d_back', 'top': '3d_top', 'bottom': '3d_bottom',
                'front_right45': '3d_front_right45'}
    tiles, scores = [], {}
    bg = (150, 150, 155)
    for name, d, up in views:
        d = Vector(d).normalized()
        z = d
        x = Vector(up).cross(z).normalized()
        y = z.cross(x)
        rot = Matrix((x, y, z)).transposed()
        rr = np.array(rot)
        ctr = pts.mean(0) * 0 + (pts.max(0) + pts.min(0)) / 2      # 外形の箱の中心が絵の中央（納品時に中央合わせ）
        pr = (pts - ctr) @ rr[:, :2]
        cx, cy = (pr.max(0) + pr.min(0)) / 2
        ctr = Vector(ctr) + x * cx + y * cy
        cam.matrix_world = Matrix.Translation(ctr + d * 30.0) @ rot.to_4x4()
        sun.matrix_world = (rot @ Matrix.Rotation(math.radians(-25), 3, 'X') @ Matrix.Rotation(math.radians(-20), 3, 'Y')).to_4x4()
        rp = os.path.join(out_dir, f'render_kannuki_{name}.png')
        sc.render.filepath = rp
        bpy.ops.render.render(write_still=True)
        ren = Image.open(rp).convert('RGBA')
        artim = Image.open(os.path.join(SRC, f'kannuki_{art_name[name]}_r2.png')).convert('RGBA').resize((TILE, TILE), Image.LANCZOS)
        a1 = np.asarray(artim)[..., 3] > 64
        a2 = np.asarray(ren)[..., 3] > 64
        scores[name] = round(float((a1 & a2).sum() / max(1, (a1 | a2).sum())), 3)
        diff = np.zeros((TILE, TILE, 3), np.uint8) + np.array(bg, np.uint8)
        diff[a1 & ~a2] = (220, 60, 60)
        diff[a2 & ~a1] = (60, 110, 230)
        diff[a1 & a2] = (235, 235, 235)
        row = []
        for im in (artim, ren):
            tt = Image.new('RGB', (TILE, TILE), bg)
            tt.paste(im, (0, 0), im)
            row.append(tt)
        row.append(Image.fromarray(diff))
        tiles.append((name, row))
    cols = 2
    W = Image.new('RGB', (cols * 3 * TILE, ((len(tiles) + 1) // cols) * (TILE + 24)), (40, 40, 44))
    dr = ImageDraw.Draw(W)
    for k, (name, row) in enumerate(tiles):
        x0, y0 = (k % cols) * 3 * TILE, (k // cols) * (TILE + 24)
        dr.text((x0 + 6, y0 + 4), f'kannuki {name}  art | render | silhouette (red=art only, blue=model only)  IoU {scores[name]}', fill=(230, 230, 230))
        for j, im in enumerate(row):
            W.paste(im, (x0 + j * TILE, y0 + 24))
    W.save(os.path.join(out_dir, 'kannuki_compare.png'))
    small = W.copy()
    small.thumbnail((1600, 1600))
    small.convert('RGB').save(os.path.join(out_dir, 'kannuki_compare_small.jpg'), quality=88)
    return scores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--review', action='store_true')
    args = ap.parse_args()
    fetch_art()
    info = build()
    if args.review:
        info['iou'] = render_review(os.path.join(WORK, 'review'))
        log(f'IoU {info["iou"]}')


if __name__ == '__main__':
    main()
