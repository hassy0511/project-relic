"""練習銃（回収屋ギルドの古い訓練用の銃、W2-07b）を、絵の寸法から部品で組む（SKILL 2.2 の機械のやり方）。

  .venv-blender/bin/python tools/blender/recon/practice_gun.py [--review] [--hand-check]
  （--review なしなら GLB だけ、数秒）。絵は build/practice_gun/src/ に置く。なければ絵のブランチ（ART_REF）から
  git show で取り出す。

できるもの
  godot/assets/models/practice_gun.glb   モデル（材質 1 つ 'practice_gun'、色はテクスチャ 1 枚の区画で塗り分け、
                                         空の目印 'muzzle' が銃口の先）
  build/practice_gun/review/             --review：絵と Cycles の画像の比較（真横・真上・正面・斜め）
  build/practice_gun/hand_check.json     --hand-check：haru_r の右手の部品の点が、練習銃・スパークの中に入る数

■ 座標（Blender、m）はスパーク（gun.py の spark_gun.glb）と同じ
  原点 = 握りの中心、銃身 +X（銃口が +X）、上 +Z、握りは -Z。真横の絵は -Y 側から見た面（銃の右側。貸出札がある）。
  glTF（Godot）では +X が銃口、+Y が上。ゲームでは PlayerView がこの原点を、スパークと同じ右手の置き場所
  （ai_character.hand_frame、HAND_WRIST_IN_GUN）に置く。

■ 握り・引き金・用心金の内側はスパークと同じ（右手の部品がそのまま握れるように。発注書 W2-07b の 2 章）
  haru_r.glb のスパーク（材質 spark_gun の面）を hand_frame で銃の座標へ戻し、真横の外形を測った（GRIP_POLY・
  TRIGGER_POLY・用心金の穴 GUARD_IN）。握りの厚みは ±1.75cm、用心金の下の棒は ±0.85cm（スパークと同じ）。
  受け筒（外装）の幅もスパークと同じ ±2.3cm（絵の真上は 5.7cm だが、親指が受け筒の横に沿うので広げない）。

■ ほかの寸法は真横の絵（spec：全長 25cm、46.96 px/cm）を、握りがスパークと重なる所（握りの外形の重なり 0.71）に
  置いて 1cm の格子で測った：絵の画素 (px, py) → x = (px − 657) / 4696、z = (1082 − py) / 4696（m）。
  幅は真上・正面の絵（同じ縮尺）。銃身は丸（真横 5.3cm・真上 4.4cm の間で 4.7cm）。

■ 色（spec_practice_gun.md の hex）：部品ごとに 1 色。塗装のはげは形にせず、テクスチャの「決まり」で塗る
  （SKILL 2.1 の最後・3 章）：砂色の大きな面はまばらなはげ（約 6%）、面取りの帯と短い辺の面（縁）は多いはげ（約 30%）。
  はげは擦れた鉄 #9B8B75、大きなはげの中はくすんだ鉄 #666660。木は #594333 に握りの向きの木目。
  テクスチャ 1 枚（1024 角）の区画：左上 = まばら、右上 = 縁、左下 = 木目、右下 = 平らな色の升目。
  面ごとに、その面を正面から見た投影（m）を区画の中の決まった所（面の中心から作る番号）へ置く。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT_GLB = os.path.join(REPO, 'godot', 'assets', 'models', 'practice_gun.glb')
HARU_GLB = os.path.join(REPO, 'godot', 'assets', 'models', 'haru_r.glb')
WORK = os.path.join(REPO, 'build', 'practice_gun')
ART_REF = 'origin/art/w2-props:art/concepts/W2_props'

# ---------------------------------------------------------------- 色（spec の hex）
PAINT = '#D4B58A'     # 外装・短筒の砂色の塗装
IRON = '#666660'      # 露出した筒・引き金（くすんだ鉄）
WOOD = '#594333'      # 握り（古い濃木）
TAPE = '#E6D8BC'      # 補修の布テープ
RUST = '#A75B45'      # 貸出札・銃口の小面（赤錆色の塗装鉄）
WORN = '#9B8B75'      # 擦れた縁（塗装がはげた鈍い鉄）
BORE = '#2E2A27'      # 銃口の暗い小穴（spec の「暗い小穴」）
WOOD_TOP = '#4A372A'  # 握りの上の板（絵の濃い茶の板。木の色を 2 割暗く）

# ---------------------------------------------------------------- 寸法（m、銃の座標 x-z の真横の外形）
# スパークの握り（haru_r.glb から測った外形。前の縁は x≈0.03 でほぼ垂直、後ろの縁は下ほど後ろへ 21 度）
GRIP_POLY = [(0.0142, -0.0811), (0.0271, -0.0718), (0.0314, -0.0615), (0.0294, -0.0532), (0.0335, -0.0171),
             (0.0345, 0.0300), (-0.0146, 0.0300), (-0.0461, -0.0530), (-0.0427, -0.0626), (-0.0302, -0.0686)]
GRIP_W, GRIP_C = 0.0175, 0.0030
GRIP_AXIS = (0.355, 0.935)    # 握りの軸（後ろの縁の向き、x-z）
# 握りの上の板（濃い茶。受け筒の下で握りを受ける。後ろはスパークの握りの上の張り出しの代わり）
TANG_POLY = [(-0.0150, 0.0280), (0.0345, 0.0280), (0.0360, 0.0565), (-0.0335, 0.0565), (-0.0335, 0.0520),
             (-0.0215, 0.0385)]
TANG_W, TANG_C = 0.0185, 0.0025
# 外装（受け筒）。後ろの面は少し傾き、角は面取り。前の下は用心金の上まで下がる
HOUSING_POLY = [(0.0990, 0.0330), (0.0990, 0.0905), (0.0945, 0.0960), (-0.0140, 0.0960), (-0.0290, 0.0860),
                (-0.0356, 0.0590), (-0.0330, 0.0540), (0.0360, 0.0540), (0.0400, 0.0330)]
HOUSING_W, HOUSING_C = 0.0230, 0.0040
# 上の段（外装の上に載る面取りした台）
RIB_POLY = [(-0.0075, 0.0950), (0.0710, 0.0950), (0.0600, 0.1086), (0.0010, 0.1086)]
RIB_W, RIB_C = 0.0135, 0.0030
# 用心金（外と内の多角形。上の端は外装の中）。内側の穴はスパークと同じ所（人さし指が沿う）
GUARD_OUT = [(0.0335, 0.0360), (0.0335, -0.0120), (0.0420, -0.0190), (0.1000, -0.0190), (0.1140, -0.0060),
             (0.1140, 0.0470)]
GUARD_IN = [(0.0440, 0.0360), (0.0440, 0.0020), (0.0520, -0.0080), (0.0960, -0.0080), (0.1040, 0.0000),
            (0.1040, 0.0470)]   # 前の柱の上は銃身の中まで（外装の前の面より前にあるので）
GUARD_W, GUARD_C = 0.0085, 0.0025
# 引き金（スパークと同じ外形と位置）
TRIGGER_POLY = [(0.0524, 0.0350), (0.0521, 0.0175), (0.0643, -0.0024), (0.0710, -0.0024), (0.0771, 0.0018),
                (0.0701, 0.0213), (0.0748, 0.0350)]
TRIGGER_W, TRIGGER_C = 0.0045, 0.0012
# 銃身（丸）・口輪・赤錆色の筒先（八角）と暗い小穴
AXIS_Z = 0.0655
BARREL = (0.0940, 0.1700, 0.0235)            # x0, x1, 半径
COLLAR = (0.1680, 0.1880, 0.0275, 0.0025)    # x0, x1, 半径, 面取り
CAP = (0.1880, 0.2035, 0.0180, 0.0045)       # x0, x1, 半径（八角の外接）, 前の面取り
BORE_R, BORE_DEPTH = 0.0075, 0.0110
MUZZLE_TIP = (CAP[1], 0.0, AXIS_Z)
# 引き金の軸のピン（両側）
PIN = (0.0530, 0.0390, 0.0042, 0.0012)       # x, z, 半径, 出っ張り
# 貸出札（右側 = -Y の面）：赤錆色の板・鉄の鋲 2 つ・暗い三角と点 3 つ
PLATE = (-0.0040, 0.0560, 0.0710, 0.0870, 0.0016)   # x0, x1, z0, z1, 厚み
RIVETS = [(0.0020, 0.0790), (0.0500, 0.0790)]
RIVET_R = 0.0026
MARK_TRI = [(0.0130, 0.0755), (0.0210, 0.0755), (0.0170, 0.0835)]
MARK_DOTS = [(0.0250, 0.0770), (0.0290, 0.0770), (0.0330, 0.0770)]
# 布テープ：握りの軸に直角な面で切った帯 2 巻き（下の巻きの上に、少しずらして上の巻き）。s = 握りの軸に沿った位置
TAPE_WRAPS = [(-0.0660, -0.0450, 0.0012, 2.0), (-0.0480, -0.0260, 0.0020, -2.5)]   # s0, s1, 浮き, 傾き（度）
TAPE_ORIGIN = (-0.0156, 0.0273)   # s = 0 の点（握りの後ろの縁の上）

# ---------------------------------------------------------------- テクスチャの区画
TEX = 1024
REGION_M = 0.16            # 区画（512px）の 1 辺が表す長さ（m）= 32 px/cm
MARGIN = 8 / TEX
CELLS = {'paint': 0, 'iron': 1, 'wood': 2, 'tape': 3, 'rust': 4, 'worn': 5, 'bore': 6, 'wood_top': 7}
CELL_HEX = {'paint': PAINT, 'iron': IRON, 'wood': WOOD, 'tape': TAPE, 'rust': RUST, 'worn': WORN, 'bore': BORE,
            'wood_top': WOOD_TOP}
EDGE_LEN = 0.007           # 外形の辺がこれより短い面（角の面取り）も縁として扱う


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


# ---------------------------------------------------------------- 形の道具
class Mesh:
    """面ごとに（頂点の番号、色の種類 kind、縁か edge）を持つ。kind は CELLS の名前"""

    def __init__(self):
        self.v: list = []
        self.f: list = []
        self.kind: list = []
        self.edge: list = []

    def add_v(self, p) -> int:
        self.v.append(np.asarray(p, float))
        return len(self.v) - 1

    def face(self, ids, kind, edge=False):
        ids = [i for k, i in enumerate(ids) if i != ids[k - 1]]
        if len(ids) >= 3:
            self.f.append(ids)
            self.kind.append(kind)
            self.edge.append(edge)


def signed_area(P) -> float:
    P = np.asarray(P, float)
    return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


def ccw(P):
    return list(P) if signed_area(P) > 0 else list(P)[::-1]


def inset(P, d):
    """反時計回りの多角形を d だけ内側へ（辺を平行に動かし、隣の辺との交点を新しい角にする）"""
    P = np.asarray(P, float)
    n = len(P)
    out = []
    for k in range(n):
        a, b, c = P[k - 1], P[k], P[(k + 1) % n]
        e1, e2 = b - a, c - b
        n1 = np.array([-e1[1], e1[0]]) / np.linalg.norm(e1)
        n2 = np.array([-e2[1], e2[0]]) / np.linalg.norm(e2)
        m = n1 + n2
        cosh = max(0.35, float(np.dot(m / np.linalg.norm(m), n1)))
        out.append(b + m / np.linalg.norm(m) * d / cosh)
    return np.array(out)


def prism(M: Mesh, P, y0, y1, c, kind, side_kind=None):
    """真横の外形 P（x-z）を y0 → y1 へ押し出し、両側の縁を c だけ面取りする。
    側面（y = 一定）は kind、外周の帯も kind（短い辺の帯と面取りは縁）"""
    P = ccw(P)
    n = len(P)
    lens = [float(np.linalg.norm(np.subtract(P[(k + 1) % n], P[k]))) for k in range(n)]
    layers = ([(inset(P, c), y0), (np.asarray(P), y0 + c), (np.asarray(P), y1 - c), (inset(P, c), y1)]
              if c > 0 else [(np.asarray(P), y0), (np.asarray(P), y1)])
    rings = [[M.add_v((q[0], y, q[1])) for q in L] for L, y in layers]
    M.face(rings[0][::-1], kind)
    M.face(rings[-1], kind)
    for li in range(len(rings) - 1):
        cham = c > 0 and li != 1
        for k in range(n):
            a, b = rings[li][k], rings[li][(k + 1) % n]
            a2, b2 = rings[li + 1][k], rings[li + 1][(k + 1) % n]
            M.face([a, b, b2, a2], side_kind or kind, edge=cham or lens[k] < EDGE_LEN)


def ring_prism(M: Mesh, O, I, y0, y1, c, kind):
    """穴のある外形（外 O と内 I、同じ点の数で対応）の押し出し（用心金）。外は外へ、内は内へ面取り"""
    O, I = np.asarray(O, float), np.asarray(I, float)
    if signed_area(O) < 0:
        O, I = O[::-1], I[::-1]
    n = len(O)
    Oi, Io = inset(O, c), inset(I, -c)
    layers = [((Oi, Io), y0), ((O, I), y0 + c), ((O, I), y1 - c), ((Oi, Io), y1)]
    rings = [([M.add_v((q[0], y, q[1])) for q in L[0]], [M.add_v((q[0], y, q[1])) for q in L[1]]) for L, y in layers]
    for li, (ro, ri) in ((0, rings[0]), (3, rings[3])):
        for k in range(n - 1):
            q = [ro[k], ro[k + 1], ri[k + 1], ri[k]]
            M.face(q[::-1] if li == 0 else q, kind)
    for li in range(3):
        cham = li != 1
        for k in range(n - 1):
            for ring, flip in ((0, False), (1, True)):
                a, b = rings[li][ring][k], rings[li][ring][k + 1]
                a2, b2 = rings[li + 1][ring][k], rings[li + 1][ring][k + 1]
                q = [a, b, b2, a2]
                L = float(np.linalg.norm((O if ring == 0 else I)[k + 1] - (O if ring == 0 else I)[k]))
                M.face(q[::-1] if flip else q, kind, edge=cham or L < EDGE_LEN)


def lathe(M: Mesh, x_axis_z, prof, segs, kinds, edges, phase=0.0):
    """銃の軸（x、高さ x_axis_z）のまわりに輪郭 prof = [(x, 半径)] を回す。kinds・edges は区間ごと"""
    rings = []
    for x, r in prof:
        if r < 1e-7:
            i = M.add_v((x, 0.0, x_axis_z))
            rings.append([i] * segs)
        else:
            rings.append([M.add_v((x, r * math.cos(2 * math.pi * k / segs + phase),
                                   x_axis_z + r * math.sin(2 * math.pi * k / segs + phase))) for k in range(segs)])
    for i in range(len(prof) - 1):
        for k in range(segs):
            M.face([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]],
                   kinds[i], edges[i])
    return rings


def side_disc(M: Mesh, x, z, y0, y1, r, kind, segs=10):
    """y の向きの短い円柱（ピン・鋲）"""
    a = [M.add_v((x + r * math.cos(2 * math.pi * k / segs), y0, z + r * math.sin(2 * math.pi * k / segs)))
         for k in range(segs)]
    b = [M.add_v((x + r * math.cos(2 * math.pi * k / segs), y1, z + r * math.sin(2 * math.pi * k / segs)))
         for k in range(segs)]
    M.face(a[::-1], kind)
    M.face(b, kind)
    for k in range(segs):
        M.face([a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]], kind)


def tape_band(M: Mesh, s0, s1, lift, tilt_deg):
    """握りの軸に直角な 2 つの面で握りを切った帯（外へ lift 浮かせ、上下の縁は握りの面まで下ろす）"""
    ax = np.array(GRIP_AXIS) / np.linalg.norm(GRIP_AXIS)
    o = np.array(TAPE_ORIGIN)
    P = np.array(ccw(GRIP_POLY))

    def section(s, tilt):
        c = o + ax * s
        nrm = np.array([ax[1], -ax[0]])                    # 切り口の線の向き（前・下へ）
        t = math.radians(tilt)
        nrm = np.array([nrm[0] * math.cos(t) - nrm[1] * math.sin(t), nrm[0] * math.sin(t) + nrm[1] * math.cos(t)])
        hits = []
        for k in range(len(P)):
            a, b = P[k], P[(k + 1) % len(P)]
            d = b - a
            A = np.array([[nrm[0], -d[0]], [nrm[1], -d[1]]])
            if abs(np.linalg.det(A)) < 1e-12:
                continue
            u, v = np.linalg.solve(A, a - c)
            if 0.0 <= v <= 1.0:
                hits.append(c + nrm * u)
        hits.sort(key=lambda h: float(np.dot(h - c, nrm)))
        back, front = hits[0], hits[-1]
        return back, front, nrm

    def ring_pts(s, tilt, grow):
        back, front, nrm = section(s, tilt)
        back = back - nrm * grow
        front = front + nrm * grow
        w = GRIP_W + grow
        cc = GRIP_C
        # 切り口の面の中の面取りした長方形（前後 = nrm の向き、左右 = y）
        L = float(np.linalg.norm(front - back))
        out = []
        for u, y in [(0.0, -w + cc), (cc, -w), (L - cc, -w), (L, -w + cc), (L, w - cc), (L - cc, w), (cc, w),
                     (0.0, w - cc)]:
            p = back + nrm * u
            out.append((p[0], y, p[1]))
        return out

    tilt = tilt_deg
    lo_in = [M.add_v(p) for p in ring_pts(s0, tilt, 0.0)]
    lo = [M.add_v(p) for p in ring_pts(s0 + 0.0008, tilt, lift)]
    hi = [M.add_v(p) for p in ring_pts(s1 - 0.0008, tilt, lift)]
    hi_in = [M.add_v(p) for p in ring_pts(s1, tilt, 0.0)]
    n = len(lo)
    for A, B, e in ((lo_in, lo, True), (lo, hi, False), (hi, hi_in, True)):
        for k in range(n):
            M.face([A[k], A[(k + 1) % n], B[(k + 1) % n], B[k]], 'tape', e)


def build() -> Mesh:
    M = Mesh()
    prism(M, GRIP_POLY, -GRIP_W, GRIP_W, GRIP_C, 'wood')
    prism(M, TANG_POLY, -TANG_W, TANG_W, TANG_C, 'wood_top')
    prism(M, HOUSING_POLY, -HOUSING_W, HOUSING_W, HOUSING_C, 'paint')
    prism(M, RIB_POLY, -RIB_W, RIB_W, RIB_C, 'paint')
    ring_prism(M, GUARD_OUT, GUARD_IN, -GUARD_W, GUARD_W, GUARD_C, 'paint')
    prism(M, TRIGGER_POLY, -TRIGGER_W, TRIGGER_W, TRIGGER_C, 'iron')
    # 銃身：外装の中から口輪まで
    x0, x1, r = BARREL
    lathe(M, AXIS_Z, [(x0, 0.0), (x0, r), (x1, r), (x1, 0.0)], 20, ['paint'] * 3, [False, False, False])
    # 口輪：面取りした輪（はげの多い縁）
    cx0, cx1, cr, cc = COLLAR
    lathe(M, AXIS_Z, [(cx0, 0.0), (cx0, cr - cc), (cx0 + cc, cr), (cx1 - cc, cr), (cx1, cr - cc), (cx1, 0.0)], 16,
          ['paint'] * 5, [True, True, False, True, True], phase=math.pi / 16)
    # 赤錆色の筒先（八角）。前の面は輪で、中は暗い小穴
    px0, px1, pr, pc = CAP
    lathe(M, AXIS_Z, [(px0, 0.0), (px0, pr), (px1 - pc, pr), (px1, pr - pc), (px1, BORE_R + 0.0012), (px1, BORE_R),
                      (px1 - BORE_DEPTH, BORE_R), (px1 - BORE_DEPTH, 0.0)], 8,
          ['rust', 'rust', 'rust', 'rust', 'iron', 'bore', 'bore'], [False] * 7, phase=math.pi / 8)
    # ピン（両側）・貸出札・鋲・印
    px, pz, prr, pout = PIN
    side_disc(M, px, pz, -HOUSING_W - pout, HOUSING_W + pout, prr, 'iron')
    x0, x1, z0, z1, t = PLATE
    y_face = -HOUSING_W
    prism_y(M, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y_face - t, y_face + 0.001, 0.0012, 'rust')
    for rx, rz in RIVETS:
        side_disc(M, rx, rz, y_face - t - 0.0010, y_face, RIVET_R, 'iron', segs=8)
    prism_y(M, MARK_TRI, y_face - t - 0.0003, y_face - t + 0.0005, 0.0, 'bore')
    for dx, dz in MARK_DOTS:
        side_disc(M, dx, dz, y_face - t - 0.0003, y_face - t + 0.0005, 0.0011, 'bore', segs=6)
    for s0, s1, lift, tilt in TAPE_WRAPS:
        tape_band(M, s0, s1, lift, tilt)
    return M


def prism_y(M: Mesh, P, y0, y1, c, kind):
    """板（y の向きに薄い）。面取りは外側（y0 の側）だけ"""
    P = ccw(P)
    n = len(P)
    outer = inset(P, c) if c > 0 else np.asarray(P, float)
    rings = [[M.add_v((q[0], y0, q[1])) for q in outer],
             [M.add_v((q[0], y0 + c, q[1])) for q in P],
             [M.add_v((q[0], y1, q[1])) for q in P]]
    M.face(rings[0][::-1], kind)
    M.face(rings[2], kind)
    for li in range(2):
        for k in range(n):
            M.face([rings[li][k], rings[li][(k + 1) % n], rings[li + 1][(k + 1) % n], rings[li + 1][k]], kind)


# ---------------------------------------------------------------- テクスチャ（はげ・木目・平らな色）
def periodic_noise(n: int, sigma: float, seed: int, aniso=(1.0, 1.0)) -> np.ndarray:
    """周期的（つなぎ目のない）なめらかな雑音。sigma は画素、aniso = (横, 縦) の伸び"""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    g = np.exp(-2 * (math.pi * sigma) ** 2 * ((fx * aniso[0]) ** 2 + (fy * aniso[1]) ** 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    return (out - out.mean()) / out.std()


def chips(n: int, coverage: float, seed: int) -> np.ndarray:
    """はげの形（真偽）：大きな「どこ」の雑音 × 細かい「形」の雑音を、面積の割合 coverage で切る"""
    big = periodic_noise(n, 22.0, seed)
    fine = periodic_noise(n, 3.0, seed + 1)
    f = big * 0.75 + fine * 0.45
    return f > np.quantile(f, 1.0 - coverage)


def paint_tile(n: int, coverage: float, seed: int) -> np.ndarray:
    from scipy import ndimage as ndi
    m = chips(n, coverage, seed)
    core = ndi.binary_erosion(m, iterations=3)
    img = np.empty((n, n, 3))
    img[:] = hex_rgb(PAINT)
    img[m] = hex_rgb(WORN)
    img[core] = hex_rgb(IRON)
    return img


def wood_tile(n: int) -> np.ndarray:
    """木目：縦（v）に長く伸びた雑音を 3 段の濃さに（大きな木目だけ）"""
    g = periodic_noise(n, 5.0, 7, aniso=(0.6, 8.0))
    base = hex_rgb(WOOD)
    img = np.empty((n, n, 3))
    img[:] = base
    img[g > 0.9] = base * 0.86
    img[g < -1.1] = base * 1.12
    return img


def make_texture(path: str):
    from PIL import Image
    h = TEX // 2
    img = np.zeros((TEX, TEX, 3))
    img[:h, :h] = paint_tile(h, 0.06, 11)
    img[:h, h:] = paint_tile(h, 0.30, 23)
    img[h:, :h] = wood_tile(h)
    cs = h // 4
    for name, k in CELLS.items():
        r, c = divmod(k, 4)
        img[h + r * cs:h + (r + 1) * cs, h + c * cs:h + (c + 1) * cs] = hex_rgb(CELL_HEX[name])
    # 布テープの升目：ごく薄い汚れ（約 2 割、5% 暗く）と小さな錆のしみ（約 1%）
    r, c = divmod(CELLS['tape'], 4)
    dirt = periodic_noise(cs, 4.0, 31) > 0.85
    rust = periodic_noise(cs, 1.6, 37) > 2.3
    cell = img[h + r * cs:h + (r + 1) * cs, h + c * cs:h + (c + 1) * cs]
    cell[dirt] = hex_rgb(TAPE) * 0.95
    cell[rust] = hex_rgb(TAPE) * 0.8 + hex_rgb(RUST) * 0.2
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path)


def region_of(kind: str, edge: bool):
    """区画の左下の UV と区画の大きさ（Blender の UV は下が 0）。None なら平らな色の升目の中心"""
    if kind == 'paint':
        return ((0.5, 0.5) if edge else (0.0, 0.5)), 0.5
    if kind == 'wood':
        return (0.0, 0.0), 0.5
    if kind == 'tape':                       # 布の升目（しみ入り）。升目 1 つ = 4cm
        r, c = divmod(CELLS['tape'], 4)
        cs = 0.5 / 4
        return (0.5 + c * cs, 0.5 - (r + 1) * cs), cs
    return None


def cell_uv(kind: str):
    k = CELLS[kind]
    r, c = divmod(k, 4)
    cs = 0.5 / 4
    return (0.5 + (c + 0.5) * cs, 0.5 - (r + 0.5) * cs)


def face_uvs(M: Mesh):
    """面ごとの UV（面の頂点の順）。砂色・木は面を正面から見た投影を区画の中へ、ほかは升目の中心"""
    V = np.array(M.v)
    uvs = []
    ax = np.array([GRIP_AXIS[0], 0.0, GRIP_AXIS[1]])
    ax /= np.linalg.norm(ax)
    for fi, f in enumerate(M.f):
        kind, edge = M.kind[fi], M.edge[fi]
        reg = region_of(kind, edge)
        if reg is None:
            u = cell_uv(kind)
            uvs.append([u] * len(f))
            continue
        reg, size = reg
        P = V[f]
        nrm = np.zeros(3)
        for k in range(1, len(f) - 1):
            nrm += np.cross(P[k] - P[0], P[k + 1] - P[0])
        nrm = nrm / (np.linalg.norm(nrm) + 1e-12)
        if kind == 'wood':
            e2 = ax - nrm * np.dot(ax, nrm)                 # 木目は握りの軸に沿う
            if np.linalg.norm(e2) < 0.3:
                e2 = np.array([1.0, 0, 0]) - nrm * nrm[0]
        else:
            k = int(np.argmax(np.abs(nrm)))
            e2 = np.array([0, 0, 1.0]) if k != 2 else np.array([1.0, 0, 0])
            e2 = e2 - nrm * np.dot(e2, nrm)
        e2 /= np.linalg.norm(e2)
        e1 = np.cross(e2, nrm)
        q = np.stack([P @ e1, P @ e2], 1)
        q -= q.min(0)
        scale = 0.5 / REGION_M
        q *= scale
        span = q.max(0)
        room = size - 2 * MARGIN - span
        if (room < 0).any():
            q *= float(np.min((size - 2 * MARGIN) / np.maximum(span, 1e-9)))
            room = np.maximum(size - 2 * MARGIN - q.max(0), 0.0)
        c = P.mean(0)
        hsh = (math.sin(c[0] * 1731.1 + c[1] * 917.3 + c[2] * 413.7 + fi * 0.37) + 1) / 2
        hsh2 = (math.sin(c[0] * 419.9 - c[1] * 1371.7 + c[2] * 1123.1 + fi * 0.71) + 1) / 2
        off = np.array([reg[0] + MARGIN + room[0] * hsh, reg[1] + MARGIN + room[1] * hsh2])
        uvs.append([tuple(x) for x in q + off])
    return uvs


# ---------------------------------------------------------------- Blender
def to_blender(M: Mesh, tex_path: str):
    import bpy
    import bmesh   # bpy の後でないと読み込めない
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new('practice_gun')
    me.from_pydata([tuple(p) for p in M.v], [], [list(map(int, f)) for f in M.f])
    uv = me.uv_layers.new(name='UVMap')
    flat = [c for fu in face_uvs(M) for uvp in fu for c in uvp]
    uv.data.foreach_set('uv', flat)
    mt = bpy.data.materials.new('practice_gun')
    mt.use_nodes = True
    b = mt.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.78
    b.inputs['Metallic'].default_value = 0.0
    img = bpy.data.images.load(tex_path)
    img.name = 'practice_gun'
    tn = mt.node_tree.nodes.new('ShaderNodeTexImage')
    tn.image = img
    tn.interpolation = 'Linear'
    mt.node_tree.links.new(tn.outputs['Color'], b.inputs['Base Color'])
    me.materials.append(mt)
    me.validate()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new('practice_gun', me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35.0))
    mz = bpy.data.objects.new('muzzle', None)
    mz.location = MUZZLE_TIP
    bpy.context.scene.collection.objects.link(mz)
    mz.parent = ob
    return ob, mz


def export(ob, mz, path: str):
    import bpy
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    mz.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, export_apply=False,
                              export_animations=False, use_selection=True, export_extras=False)


def triangles(ob) -> int:
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ---------------------------------------------------------------- 確認
TILE = 512
PX_PER_CM = 46.96
ORTHO = 2048 / PX_PER_CM / 100
CENTER = ((1024 - 657) / (PX_PER_CM * 100), 0.0, (1082 - 1024) / (PX_PER_CM * 100))   # 絵の中心（銃の座標）
# 視点：名前 → (絵, カメラの方向（物体から見た）, 上)
VIEWS = {
    'side': ('practice_gun_side.png', (0, -1, 0), (0, 0, 1)),
    'top': ('practice_gun_top.png', (0, 0, 1), (0, 1, 0)),
    'front': ('practice_gun_front.png', (1, 0, 0), (0, 0, 1)),
    '3q': ('practice_gun_3q.png', (0.66, -0.66, 0.36), (0, 0, 1)),
}


def fetch_art(src: str):
    os.makedirs(src, exist_ok=True)
    for art_file, *_ in VIEWS.values():
        p = os.path.join(src, art_file)
        if not os.path.exists(p):
            data = subprocess.run(['git', 'show', f'{ART_REF}/{art_file}'], cwd=REPO, check=True,
                                  capture_output=True).stdout
            with open(p, 'wb') as f:
                f.write(data)


def render_views(out_dir: str, samples: int = 24) -> dict:
    import bpy
    from mathutils import Matrix, Vector
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = TILE
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.82, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    sc.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 1.8
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ORTHO
    sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for name, (_, d, up) in VIEWS.items():
        d = Vector(d).normalized()
        z = d
        x = Vector(up).cross(z).normalized()
        y = z.cross(x)
        rot = Matrix((x, y, z)).transposed()
        c = Vector(CENTER)
        if name == 'top':
            c = Vector((CENTER[0], 0.0, 0.0))
        if name == 'front':
            c = Vector((0.0, 0.0, CENTER[2]))
        if name == '3q':
            c = Vector((0.075, 0.0, 0.015))
        cam.matrix_world = Matrix.Translation(c + d * 1.0) @ rot.to_4x4()
        sun.matrix_world = (rot @ Matrix.Rotation(math.radians(-25), 3, 'X')
                            @ Matrix.Rotation(math.radians(-20), 3, 'Y')).to_4x4()
        p = os.path.join(out_dir, f'render_{name}.png')
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        out[name] = p
    return out


def review(src: str, out_dir: str) -> dict:
    from PIL import Image, ImageDraw
    fetch_art(src)
    renders = render_views(os.path.join(out_dir, 'renders'))
    bg = (205, 205, 210)
    scores = {}
    tiles = []
    for name, (art_file, *_r) in VIEWS.items():
        art = Image.open(os.path.join(src, art_file)).convert('RGBA').resize((TILE, TILE), Image.LANCZOS)
        ren = Image.open(renders[name]).convert('RGBA')
        a1 = np.asarray(art)[..., 3] > 64
        a2 = np.asarray(ren)[..., 3] > 64
        scores[name] = round(float((a1 & a2).sum() / max(1, (a1 | a2).sum())), 3)
        row = []
        for im in (art, ren):
            t = Image.new('RGB', (TILE, TILE), bg)
            t.paste(im, (0, 0), im)
            row.append(t)
        tiles.append((name, row))
    W = Image.new('RGB', (2 * 2 * TILE, 2 * (TILE + 24)), (40, 40, 44))
    dr = ImageDraw.Draw(W)
    for k, (name, row) in enumerate(tiles):
        x0 = (k % 2) * 2 * TILE
        y0 = (k // 2) * (TILE + 24)
        dr.text((x0 + 6, y0 + 4), f'{name}: art | model (Cycles)  silhouette IoU {scores[name]}', fill=(230, 230, 230))
        for j, im in enumerate(row):
            W.paste(im, (x0 + j * TILE, y0 + 24))
    sheet = os.path.join(out_dir, 'practice_gun_compare.png')
    W.save(sheet)
    small = W.copy()
    small.thumbnail((1600, 1600))
    small.save(os.path.join(out_dir, 'practice_gun_compare_small.jpg'), quality=88)
    return scores


def hand_check(gun_ob) -> dict:
    """haru_r の右手の部品の点（hand.R に重み 1、スパーク以外）を銃の座標へ戻し、練習銃・スパークの中に入る数を数える"""
    import bpy
    from mathutils import Matrix, Vector
    from mathutils.bvhtree import BVHTree
    sys.path.insert(0, os.path.join(REPO, 'tools', 'blender', 'models'))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=HARU_GLB)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    body = next(o for o in new if o.type == 'MESH' and o.name == 'Haru')
    hr = arm.data.bones['hand.R']
    W = hr.head_local
    gx = hr.matrix_local.to_3x3().col[1].normalized()
    gy = (Vector((1.0, 0.0, 0.0)) - gx * gx.x).normalized()
    gz = gx.cross(gy)
    rot = Matrix((gx, gy, gz)).transposed()
    origin = W - rot @ Vector((-0.062, -0.040, -0.010))   # ai_character.HAND_WRIST_IN_GUN
    inv = (Matrix.Translation(origin) @ rot.to_4x4()).inverted()
    me = body.data
    gi = body.vertex_groups['hand.R'].index
    spark_mi = [i for i, m in enumerate(me.materials) if m and m.name.startswith('spark_gun')]
    spark_v = {v for p in me.polygons if p.material_index in spark_mi for v in p.vertices}
    hand = []
    for v in me.vertices:
        if v.index in spark_v:
            continue
        w = next((g.weight for g in v.groups if g.group == gi), 0.0)
        if w > 0.99:
            hand.append(inv @ v.co)
    sp_verts = [inv @ me.vertices[i].co for i in sorted(spark_v)]
    remap = {j: k for k, j in enumerate(sorted(spark_v))}
    sp_faces = [[remap[i] for i in p.vertices] for p in me.polygons if p.material_index in spark_mi]
    bvh_spark = BVHTree.FromPolygons(sp_verts, sp_faces)
    gv = [v.co.copy() for v in gun_ob.data.vertices]
    bvh_gun = BVHTree.FromPolygons(gv, [list(p.vertices) for p in gun_ob.data.polygons])

    def inside(bvh, p, depth=0.0015):
        loc, nrm, _, dist = bvh.find_nearest(p)
        return loc is not None and (p - loc).dot(nrm) < 0 and dist > depth

    def near(bvh, p, gap=0.004):
        loc, nrm, _, dist = bvh.find_nearest(p)
        return loc is not None and dist < gap

    rep = {'hand_points': len(hand)}
    for nm, bvh in (('spark', bvh_spark), ('practice', bvh_gun)):
        rep[f'inside_{nm}'] = sum(1 for p in hand if inside(bvh, p))
        rep[f'touching_{nm}'] = sum(1 for p in hand if near(bvh, p))
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=OUT_GLB)
    ap.add_argument('--src', default=os.path.join(WORK, 'src'))
    ap.add_argument('--review', action='store_true')
    ap.add_argument('--hand-check', action='store_true')
    args = ap.parse_args()
    tex = os.path.join(WORK, 'practice_gun.png')
    make_texture(tex)
    M = build()
    ob, mz = to_blender(M, tex)
    export(ob, mz, args.out)
    V = np.array(M.v)
    rep = {'out': os.path.relpath(args.out, REPO), 'triangles': triangles(ob),
           'length_cm': round(float(V[:, 0].max() - V[:, 0].min()) * 100, 2),
           'height_cm': round(float(V[:, 2].max() - V[:, 2].min()) * 100, 2),
           'width_cm': round(float(V[:, 1].max() - V[:, 1].min()) * 100, 2),
           'muzzle': list(MUZZLE_TIP)}
    if args.review:
        rep['silhouette_iou'] = review(args.src, os.path.join(WORK, 'review'))
    if args.hand_check:
        rep['hand'] = hand_check(ob)
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, 'report.json'), 'w') as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == '__main__':
    main()
