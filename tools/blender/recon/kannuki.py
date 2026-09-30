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


def helix(p0, p1, r0, r1, turns, width, height, n=14):
    """円錐（p0 の半径 r0 → p1 の半径 r1）の上を巻く帯（削岩錐の真鍮の螺旋）"""
    p0, p1 = V3(p0, float), V3(p1, float)
    L = np.linalg.norm(p1 - p0)
    a, s, u = frame(p1 - p0)
    rings = []
    m = int(turns * n)
    slope = (r1 - r0) / L
    for i in range(m + 1):
        t = i / m
        ph = 2 * math.pi * turns * t
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


def build_body():
    zc = AXIS_Z
    y_rf, y_rr = -2.6, 3.0                     # 結束環の中心
    # 胴の殻（白磁）
    # 殻は錠前核の所（y = -0.55 ～ 0.85）で 2 つに分かれ、間は黒鉛の芯が見える（蓋・板を開くと核が見える）
    ang = [math.radians(a) for a in range(0, 360, 18)]
    low = [(R_SHELL * math.cos(a), zc + R_SHELL * math.sin(a)) for a in ang]
    low = [(x, z - zc) for x, z in low]
    sill = [(x, min(z, 0.9)) for x, z in low]
    sill = [q for i, q in enumerate(sill) if i == 0 or q != sill[i - 1]]
    sill = [(x, z + zc) for x, z in sill]
    sill = [(x, z - 0.0) for x, z in sill]
    shell = merge(extrude(sill, (0, -0.56, 0), (0, 0.86, 0), up=(0, 0, 1)), lathe((0, -2.35, zc), (0, -0.55, zc), [(0, 1.3), (0.03, 1.47), (0.07, R_SHELL), (0.97, R_SHELL), (1, 1.3)], 20),
                  lathe((0, 0.85, zc), (0, 2.75, zc), [(0, 1.3), (0.03, R_SHELL), (0.93, R_SHELL), (0.97, 1.47), (1, 1.3)], 20))
    # 真鍮：結束環 2 本・側帯・レールの走り
    ring = lambda y: lathe((0, y - 0.25, zc), (0, y + 0.25, zc), [(0, 1.5), (0.06, 1.75), (0.94, 1.75), (1, 1.5)], 24)
    brass = [ring(y_rf), ring(y_rr)]
    for sx in (-1, 1):
        brass.append(box((sx * 1.5, 0.2, zc), (0.16, 5.1, 0.28)))
        brass.append(box((sx * 0.98, 0.15, zc + 1.14), (0.22, 4.3, 0.1)))          # 蓋の走り
    # 黒鉛：芯（環・腕の付け根の隙間から見える）・腹板・肩の軸受け
    dark = [cyl((0, -3.75, zc), (0, 3.95, zc), 1.34, 20),
            box((0, 0.1, zc - 1.46), (2.2, 4.9, 0.32)),
            cyl((0, -3.8, zc), (0, -3.6, zc), 1.42, 20), cyl((0, 3.3, zc), (0, 3.5, zc), 1.42, 20)]
    sh = shoulder_points()
    for s in sh.values():
        dark.append(cyl((s[0] - 0.6 * np.sign(s[0]), s[1], s[2]), (s[0], s[1], s[2]), 0.5, 12))
    add('body', None, (0, 0.2, zc), (1, 0, 0), [('ivory', shell), ('brass', merge(*brass)), ('dark', merge(*dark))])


def build_ends():
    zc = AXIS_Z
    cone = lathe((0, -5.0, zc), (0, -3.7, zc), [(0, 0.3), (0.3, 0.75), (1, 1.42)], 20)
    tip = lathe((0, -5.08, zc), (0, -4.7, zc), [(0, 0.0), (0.4, 0.22), (1, 0.32)], 12)
    band = lathe((0, -3.8, zc), (0, -3.68, zc), [(0, 1.44), (1, 1.44)], 20)
    add('nose', 'body', (0, -4.4, zc), (1, 0, 0), [('ivory', cone), ('brass', merge(tip, band))])
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
    hexr = lathe((0, yc, zc + 1.25), (0, yc, zc + 1.62), [(0, 0.5), (1, 0.5)], 6, up=(1, 0, 0))
    rollers = [cyl((-0.45, yc + d, zc + 1.5), (0.45, yc + d, zc + 1.5), 0.15, 10) for d in (-0.39, 0.39)]
    add('core', 'body', (0, yc, zc + 1.3), (1, 0, 0), [('core', merge(hexr, *rollers))])
    # 蓋（滑る）
    def lid(y0, y1):
        w0, w1, z0, z1 = 1.1, 0.78, zc + 0.8, zc + 1.88
        poly = [(-w0, z0), (-w0, zc + 1.2), (-w1, z1), (w1, z1), (w0, zc + 1.2), (w0, z0)]
        return extrude(poly, (0, y0, 0), (0, y1, 0), up=(0, 0, 1))
    lf, lr = lid(-1.33, -0.38), lid(0.68, 1.68)
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
    # 上腕（肩の横軸）
    upper = extrude(cham_rect(0.36, 0.26, 0.11), S + u * 0.3, E - u * 0.25, up=np.cross(ea, u))
    hub = cyl(S - pa * 0.42, S + pa * 0.42, 0.42, 14)
    ehub = cyl(E - ea * 0.45, E + ea * 0.45, 0.3, 12)
    rod = cyl(S + u * 0.35 - np.cross(ea, u) * 0.24 + ea * 0.28, E - u * 0.3 - np.cross(ea, u) * 0.24 + ea * 0.28, 0.06, 8)
    add('arm_fl_pitch', 'arm_fl_yaw', S, pa, [('ivory', upper), ('brass', merge(hub, ehub)), ('dark', rod)])
    # 前腕（肘）
    fore = extrude(cham_rect(0.33, 0.24, 0.1), E + f * 0.25, D0 - f * 0.3, up=np.cross(ea, f))
    collar = lathe(D0 - f * 0.42, D0 + f * 0.02, [(0, 0.44), (1, 0.5)], 16)
    ebolt = cyl(E - ea * 0.5, E + ea * 0.5, 0.2, 10)
    band = lathe(D0 - f * 0.03, D0 + f * 0.08, [(0, 0.52), (1, 0.52)], 16)
    add('arm_fl_elbow', 'arm_fl_pitch', E, ea, [('ivory', merge(fore, collar)), ('dark', ebolt), ('brass', band)])
    # 削岩錐（自転）
    cone = lathe(D0 + f * 0.08, T, [(0, 0.47), (1, 0.0)], 16)
    hx = helix(D0 + f * 0.1, T - f * 0.12, 0.47 * 0.96, 0.02, 2.5, 0.16, 0.06)
    tipc = lathe(T - f * 0.26, T + f * 0.02, [(0, 0.09), (1, 0.0)], 10)
    add('arm_fl_drill', 'arm_fl_elbow', D0, f, [('dark', cone), ('brass', merge(hx, tipc))])


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
