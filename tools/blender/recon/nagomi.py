"""ナゴミ（相棒の AI ドローン、直径 25cm）を、絵の寸法から部品ごとの形（数式の曲面）で組み立てる。

  npm run nagomi:build
  （= .venv-blender/bin/python tools/blender/recon/nagomi.py --review。--review なしなら GLB だけ、数秒）
  絵は build/nagomi/src/ に置く。なければ絵のブランチ（ART_REF）から git show で取り出す。

できるもの
  godot/assets/models/nagomi.glb     モデル（テクスチャなし、部品ごとの平らな材質 4 つ）
  build/nagomi/review/               --review のとき：絵と Cycles の画像の比較（閉・全開）と外形の重なりの数値

■ やり方（人型でないものの 1 体目。視体積や絵の投影は使わない）
  ナゴミは「球を十字に 4 つに割った殻」と「中の骨組み」だけでできているので、絵から外形を削り出すより、
  絵で測った寸法（球の半径・継ぎ目の幅・殻の後ろの端・背面の支持輪の断面）から直接つくるほうが単純できれい。
  1. 殻 4 枚：球殻（外の半径 R、厚み SHELL_T）のうち「継ぎ目の面 x=±GAP、z=±GAP の外」「前の円筒（種子光の
     まわり）の外」「後ろの端 y=SHELL_BACK_Y より前」の範囲を、(前後の角度, 周りの角度) の格子で張る。
     外・内の面と、縁の側面を別につくる（縁は角を立てる）。
  2. 骨組み（黒鉛色）：背面の支持輪（断面の表 CAP_PROFILE を Y 軸のまわりに回す）、継ぎ目の下に通る 4 本の梁
     （殻の隙間から見える暗い十字）、前の襟（種子光のまわりの輪）、核を支える軸、底面の六角ドック。
  3. 真鍮：継ぎ目の留め具（CLIPS の角度）と、殻 4 枚の蝶番のピン。
  4. 核（種子光）：小さな球。材質 nagomi_core は発光（Godot で感情ごとに色と明るさを変える）。
  色は spec.md の基準 hex をそのまま使う（絵を投影しない。遠くでは平らな色のほうが絵に近く、継ぎ目は形で出る）。

■ 部品の階層（Godot で殻を開くため）
  nagomi（空の親）
    frame      骨組み・留め具・蝶番（動かない。材質 nagomi_frame・nagomi_brass）
    core       種子光（材質 nagomi_core）
    shell_ul / shell_ur / shell_ll / shell_lr   殻（本人から見て左上・右上・左下・右下ではなく、
               「正面の絵の」左上・右上・左下・右下）。原点は後ろの蝶番、ローカルの +X が回転軸で、
               +X まわりに正の角度だけ回すと前の端が外へ開く（閉 0 度・半開 11 度・全開 22 度、OPEN_DEG）。
  Godot では各殻の元の姿勢に Basis(Vector3.RIGHT, 角度) を右から掛ける（nagomi_view.gd）。

■ 座標（Blender）
  原点 = 球の中心。正面（種子光）は -Y、上は +Z、正面の絵の右（本人の左）は +X。
  glTF（Godot）では正面 +Z、上 +Y（Blender の -Y が glTF の +Z）。
  絵の縮尺：閉殻の絵は 2048px の中央に置かれ、約 61.5px/cm（spec_nagomi_3d.md）。
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT_GLB = os.path.join(REPO, 'godot', 'assets', 'models', 'nagomi.glb')
WORK = os.path.join(REPO, 'build', 'nagomi')
ART_REF = 'origin/art/w1-nagomi:art/concepts/W1_nagomi'   # 絵のブランチとフォルダ

# ---------------------------------------------------------------- 寸法（m、絵で測った値）
R = 0.1245            # 殻の外の半径（正面の絵の幅 1529px / 61.5 / 2）
SHELL_T = 0.008       # 殻の厚み
GAP = 0.0075          # 継ぎ目の半分の幅（正面の絵の暗い帯 約 1.4cm。ゲームの距離で読めるよう少し太く 1.5cm）
FRONT_HOLE = 0.021    # 種子光のまわりの丸い穴の半径（正面の絵の暗い円 約 4cm）
SHELL_BACK_Y = 0.059  # 殻の後ろの端（真横の絵で白い部分が終わる所、中心から 6cm 後ろ）
N_POLAR, N_AROUND = 20, 8   # 殻 1 枚の格子（前後・周り）

# 背面の支持輪（Y 軸のまわりの断面 (半径, y)）。真横の絵：y=6.1cm で直径 19.7cm、後ろの端 y=11.9cm で直径約 10cm
CAP_PROFILE = [(0.0, 0.035), (0.100, 0.035), (0.106, 0.050), (0.102, 0.062), (0.093, 0.076),
               (0.081, 0.090), (0.068, 0.102), (0.060, 0.109), (0.060, 0.112), (0.052, 0.113),
               (0.052, 0.119), (0.0, 0.119)]

BEAM_R = (0.104, 0.1225)   # 継ぎ目の下の梁の内・外の半径
BEAM_W = 0.0175            # 梁の幅（隙間 2*GAP より少し広く、殻の下にもぐる）
BEAM_POLAR = (6.0, 132.0)  # 梁が通る前後の角度の範囲（度、正面が 0）

# 真鍮の留め具：腕（up・down・left・right）ごとの前後の角度（度）。正面の絵で上下の腕は約 36 度、左右は約 60 度。
# 下の腕の 90 度（真下）はドックがあるので置かない
CLIPS = {'up': [36.0, 90.0], 'down': [36.0], 'left': [60.0, 90.0], 'right': [60.0, 90.0]}
CLIP_SIZE = (0.017, 0.019, 0.0085)   # 継ぎ目に沿う長さ・横の幅・高さ（梁の上に載る）

# 殻の回転軸の位置（Y 軸からの距離、前後の位置）：spec のとおり後ろの支持輪の縁。
# spec の角度（半開 25 度・全開 50 度）でここを回すと、殻が大きく振れて全開の正面の絵（殻は正面を向いたまま
# 斜めへ約 3cm ずれ、幅は閉殻の約 1.1 倍）と合わない。全開の正面の絵に見た目を合わせて、角度を半分より
# 小さく決めた（OPEN_DEG。全開の真横の絵とは合わない：絵どうしが食い違っている）
HINGE_R, HINGE_Y = 0.08, 0.06
OPEN_DEG = {'closed': 0.0, 'half': 11.0, 'open': 22.0}   # Godot の NagomiView.STATES と同じ値
PIN_R, PIN_Y = 0.101, 0.066
SEED_R, SEED_Y = 0.0125, -0.110      # 種子光（見える直径 2.5cm）
COLLAR = (0.0125, 0.0225, -0.1225, -0.104)   # 前の襟（内・外の半径、前・後ろの y）
DOCK_R, DOCK_H = 0.036, 0.003        # 底面のドック（丸い台の半径、殻の外へ出る高さ）。六角の凹部は対辺約 5.5cm

# 殻 4 枚：名前と、正面の絵での向き（x, z の符号）
SHELLS = {'shell_ul': (-1, 1), 'shell_ur': (1, 1), 'shell_ll': (-1, -1), 'shell_lr': (1, -1)}

# 色（spec.md の基準 hex、sRGB）
COLORS = {'nagomi_shell': '#F3E9D2', 'nagomi_frame': '#444641', 'nagomi_brass': '#A98749', 'nagomi_core': '#FFBC52'}


def srgb_to_linear(hexstr: str) -> tuple[float, float, float]:
    c = [int(hexstr[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ---------------------------------------------------------------- 形（numpy の頂点と面の表）

class MeshData:
    """頂点と面（多角形）と面ごとの材質の番号・なめらかさを貯める。"""

    def __init__(self):
        self.v: list[tuple] = []
        self.f: list[tuple] = []
        self.mat: list[int] = []
        self.smooth: list[bool] = []

    def add_v(self, p) -> int:
        self.v.append(tuple(float(x) for x in p))
        return len(self.v) - 1

    def add_f(self, idx, mat=0, smooth=True):
        self.f.append(tuple(idx))
        self.mat.append(mat)
        self.smooth.append(smooth)

    def grid(self, pts: np.ndarray, mat=0, smooth=True, flip=False) -> np.ndarray:
        """pts[i, j] の格子を四角形で張る。flip で面の向きを逆にする。"""
        ids = np.array([[self.add_v(p) for p in row] for row in pts])
        for i in range(pts.shape[0] - 1):
            for j in range(pts.shape[1] - 1):
                q = [ids[i, j], ids[i + 1, j], ids[i + 1, j + 1], ids[i, j + 1]]
                self.add_f(q[::-1] if flip else q, mat, smooth)
        return ids

    def strip(self, a: list[int], b: list[int], mat=0, smooth=False):
        """2 本の頂点の列 a・b の間を四角形でつなぐ（縁の側面）。"""
        for k in range(len(a) - 1):
            self.add_f([a[k], a[k + 1], b[k + 1], b[k]], mat, smooth)

    def box(self, center, ax, ay, az, size, mat=0):
        """中心と 3 つの向き（単位ベクトル）と大きさで箱を足す。"""
        c = np.asarray(center, float)
        hx, hy, hz = (np.asarray(a, float) * s / 2 for a, s in zip((ax, ay, az), size))
        ids = [self.add_v(c + sx * hx + sy * hy + sz * hz)
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        # 並び：0(---) 1(--+) 2(-+-) 3(-++) 4(+--) 5(+-+) 6(++-) 7(+++)
        for q in ([0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]):
            self.add_f([ids[i] for i in q], mat, False)

    def lathe(self, profile, axis_y=True, segs=32, mat=0, center=(0, 0, 0), smooth=True):
        """断面 (半径, 高さ) を Y 軸（axis_y）か Z 軸のまわりに回した面。半径 0 の点は 1 点にまとめる。"""
        c = np.asarray(center, float)
        rings = []
        for r, h in profile:
            if r <= 1e-9:
                p = (0, h, 0) if axis_y else (0, 0, h)
                rings.append([self.add_v(c + np.array(p))])
                continue
            ring = []
            for k in range(segs):
                a = 2 * math.pi * k / segs
                p = (r * math.cos(a), h, r * math.sin(a)) if axis_y else (r * math.cos(a), r * math.sin(a), h)
                ring.append(self.add_v(c + np.array(p)))
            rings.append(ring)
        for ra, rb in zip(rings, rings[1:]):
            if len(ra) == 1 and len(rb) == 1:
                continue
            for k in range(segs):
                k2 = (k + 1) % segs
                if len(ra) == 1:
                    q = [ra[0], rb[k2], rb[k]]
                elif len(rb) == 1:
                    q = [ra[k], ra[k2], rb[0]]
                else:
                    q = [ra[k], ra[k2], rb[k2], rb[k]]
                self.add_f(q if axis_y else q[::-1], mat, smooth)


def shell_points(radius: float, sx: int, sz: int) -> np.ndarray:
    """殻 1 枚の面の格子の点（N_POLAR+1 × N_AROUND+1）。

    前後は「前の穴の縁（Y 軸からの距離 FRONT_HOLE）」から「後ろの端 y=SHELL_BACK_Y」まで、角度で等分。
    周りは、その高さの断面の円のうち |x|≥GAP・|z|≥GAP の弧を角度で等分（縁の点は継ぎ目の面の上に載る）。
    """
    phi0 = math.asin(FRONT_HOLE / radius)
    phi1 = math.acos(-SHELL_BACK_Y / radius)
    pts = np.zeros((N_POLAR + 1, N_AROUND + 1, 3))
    for i in range(N_POLAR + 1):
        phi = phi0 + (phi1 - phi0) * i / N_POLAR
        rho = radius * math.sin(phi)
        y = -radius * math.cos(phi)
        t0 = math.asin(min(1.0, GAP / rho))
        for j in range(N_AROUND + 1):
            t = t0 + (math.pi / 2 - 2 * t0) * j / N_AROUND   # 0 = z 軸寄り、π/2 = x 軸寄り
            pts[i, j] = (sx * rho * math.sin(t), y, sz * rho * math.cos(t))
    return pts


def build_shell(sx: int, sz: int) -> MeshData:
    """殻 1 枚（世界の座標）。外・内の面と、縁の 4 辺の側面。"""
    m = MeshData()
    outer = shell_points(R, sx, sz)
    inner = shell_points(R - SHELL_T, sx, sz)
    flip = (sx * sz) < 0   # 左右を鏡に写した殻は面の向きが逆になる
    io = m.grid(outer, flip=flip)
    ii = m.grid(inner, flip=not flip)
    # 縁：前（穴の縁）・後ろ・両横。外の辺と内の辺をつなぐ（向きは外の格子と逆回り）
    edges = [(io[0, :], ii[0, :]), (io[:, -1], ii[:, -1]), (io[-1, ::-1], ii[-1, ::-1]), (io[::-1, 0], ii[::-1, 0])]
    for a, b in edges:
        if flip:
            m.strip(list(b), list(a))
        else:
            m.strip(list(a), list(b))
    return m


def arm_frame(arm: str, polar_deg: float):
    """腕（継ぎ目）の上の、前から polar_deg 度の点の向き（外向き n・継ぎ目に沿う t・横 b）。"""
    ph = math.radians(polar_deg)
    d = {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)}[arm]
    n = np.array([d[0] * math.sin(ph), -math.cos(ph), d[1] * math.sin(ph)])
    t = np.array([d[0] * math.cos(ph), math.sin(ph), d[1] * math.cos(ph)])
    b = np.cross(n, t)
    return n, t, b


def build_frame() -> MeshData:
    """骨組み（材質 0 = 黒鉛色）と真鍮（材質 1）。"""
    m = MeshData()
    # 背面の支持輪（前の面は平ら：開いたときに見える暗い円盤）
    m.lathe(CAP_PROFILE, segs=40, mat=0, smooth=False)
    # 背面の同心円の段（背面の絵の内側の円）
    m.lathe([(0.0, 0.1195), (0.036, 0.1195), (0.036, 0.117)], segs=32, mat=0, smooth=False)
    # 継ぎ目の下の梁（4 本の弧、断面は四角）
    for arm in ('up', 'down', 'left', 'right'):
        n_seg = 22
        rows = []
        for k in range(n_seg + 1):
            pd = BEAM_POLAR[0] + (BEAM_POLAR[1] - BEAM_POLAR[0]) * k / n_seg
            n, t, b = arm_frame(arm, pd)
            rows.append([n * BEAM_R[0] - b * BEAM_W / 2, n * BEAM_R[1] - b * BEAM_W / 2,
                         n * BEAM_R[1] + b * BEAM_W / 2, n * BEAM_R[0] + b * BEAM_W / 2])
        pts = np.array(rows)
        ring = np.concatenate([pts, pts[:, :1]], axis=1)   # 断面を閉じる
        ids = m.grid(ring, mat=0, smooth=False, flip=True)
        m.add_f(list(ids[0, :4])[::-1], 0, False)
        m.add_f(list(ids[-1, :4]), 0, False)
        for pd in CLIPS[arm]:
            n, t, b = arm_frame(arm, pd)
            h = CLIP_SIZE[2]
            m.box(n * (BEAM_R[1] + h / 2 - 0.002), t, b, n, CLIP_SIZE, mat=1)
    # 前の襟（種子光のまわりの輪）と、核を支える軸
    ri, ro, yf, yb = COLLAR
    m.lathe([(ri, yb), (ri, yf), (ro, yf + 0.0015), (ro, yb)], segs=24, mat=0, smooth=False)
    m.lathe([(0.0, yb - 0.002), (0.018, yb), (0.011, 0.0), (0.011, 0.04), (0.0, 0.04)], segs=16, mat=0, smooth=False)
    # 底面のドック（殻の下に少し出た丸い台と、六角の凹部。凹部の天井は殻の外に置く：殻に穴を開けないため）
    zb = -R - DOCK_H
    rin = 0.0275 / math.cos(math.pi / 6)    # 凹部の対辺 5.5cm
    m.lathe([(0.0, -R - 0.0008), (rin, -R - 0.0008), (rin, zb)], axis_y=False, segs=6, mat=0, smooth=False)
    z_edge = -math.sqrt(R * R - DOCK_R * DOCK_R) - 0.0012   # 台の縁は殻の面のすぐ外（横から見て薄い円盤）
    m.lathe([(rin, zb), (DOCK_R * 0.8, zb + 0.001), (DOCK_R, z_edge), (DOCK_R - 0.002, z_edge + 0.004), (0.0, z_edge + 0.004)],
            axis_y=False, segs=24, mat=0, smooth=False)
    # 蝶番のピン（殻ごとに、支持輪の接線の向きの真鍮の円柱。見た目だけ）
    for sx, sz in SHELLS.values():
        d = np.array([sx, 0.0, sz]) / math.sqrt(2)
        _cylinder(m, d * PIN_R + np.array([0, PIN_Y, 0]), np.cross(d, [0, 1, 0]), 0.0065, 0.026, mat=1)
    return m


def _cylinder(m: MeshData, center, axis, radius, length, mat=0, segs=10):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    u = np.cross(axis, [0, 1, 0] if abs(axis[1]) < 0.9 else [1, 0, 0])
    u /= np.linalg.norm(u)
    w = np.cross(axis, u)
    c = np.asarray(center, float)
    ends = []
    for s in (-1, 1):
        ends.append([m.add_v(c + s * axis * length / 2 + radius * (math.cos(a) * u + math.sin(a) * w))
                     for a in np.linspace(0, 2 * math.pi, segs, endpoint=False)])
    for k in range(segs):
        k2 = (k + 1) % segs
        m.add_f([ends[0][k], ends[0][k2], ends[1][k2], ends[1][k]], mat, True)
    m.add_f(ends[0][::-1], mat, False)
    m.add_f(ends[1], mat, False)


def hinge(sx: int, sz: int):
    """殻の蝶番の位置と回転軸（世界の座標）。軸まわりに正に回すと、殻の前の端が外（斜めの向き d）へ開く。"""
    d = np.array([sx, 0.0, sz]) / math.sqrt(2)
    p = d * HINGE_R + np.array([0, HINGE_Y, 0])
    axis = np.cross(d, [0, 1, 0])
    return p, axis / np.linalg.norm(axis)


def hinge_matrix(sx: int, sz: int) -> np.ndarray:
    """蝶番の位置を原点、回転軸をローカルの +X とする 4×4 行列（殻の物体の元の姿勢）。"""
    p, ax = hinge(sx, sz)
    ay = np.array([0.0, 1.0, 0.0])
    az = np.cross(ax, ay)
    mat = np.eye(4)
    mat[:3, 0], mat[:3, 1], mat[:3, 2], mat[:3, 3] = ax, ay, az, p
    return mat


def build_core() -> MeshData:
    m = MeshData()
    prof = [(SEED_R * math.sin(a), SEED_Y - SEED_R * math.cos(a)) for a in np.linspace(0, math.pi, 9)]
    prof[0] = (0.0, prof[0][1])
    prof[-1] = (0.0, prof[-1][1])
    m.lathe(prof, segs=16, mat=0, smooth=True)
    return m


# ---------------------------------------------------------------- Blender に置く・書き出す

def make_materials():
    import bpy
    mats = {}
    for name, hexc in COLORS.items():
        mt = bpy.data.materials.new(name)
        mt.use_nodes = True
        bsdf = mt.node_tree.nodes['Principled BSDF']
        col = srgb_to_linear(hexc)
        bsdf.inputs['Base Color'].default_value = (*col, 1.0)
        bsdf.inputs['Roughness'].default_value = {'nagomi_shell': 0.6, 'nagomi_frame': 0.8,
                                                   'nagomi_brass': 0.45, 'nagomi_core': 0.4}[name]
        bsdf.inputs['Metallic'].default_value = 0.6 if name == 'nagomi_brass' else 0.0
        if name == 'nagomi_core':
            bsdf.inputs['Emission Color'].default_value = (*col, 1.0)
            bsdf.inputs['Emission Strength'].default_value = 1.2
        mats[name] = mt
    return mats


def to_object(name: str, md: MeshData, mats: list, local: np.ndarray | None = None):
    """MeshData を物体にする。local（4×4）を渡すと、その座標系で頂点を持ち、物体の姿勢を local にする。"""
    import bpy
    from mathutils import Matrix
    v = np.array(md.v)
    if local is not None:
        inv = np.linalg.inv(local)
        v = (inv[:3, :3] @ v.T).T + inv[:3, 3]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v.tolist(), [], [list(f) for f in md.f])
    for mt in mats:
        me.materials.append(mt)
    me.polygons.foreach_set('material_index', md.mat)
    me.polygons.foreach_set('use_smooth', md.smooth)
    me.validate()
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)   # 面の向きを外向きにそろえる（閉じた部品ごと）
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if local is not None:
        ob.matrix_world = Matrix(local.tolist())
    return ob


def build_scene():
    """空の場面にナゴミを組む。戻り値：{名前: 物体}"""
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = make_materials()
    root = bpy.data.objects.new('nagomi', None)
    bpy.context.scene.collection.objects.link(root)
    objs = {'nagomi': root}
    objs['frame'] = to_object('frame', build_frame(), [mats['nagomi_frame'], mats['nagomi_brass']])
    objs['core'] = to_object('core', build_core(), [mats['nagomi_core']])
    for name, (sx, sz) in SHELLS.items():
        objs[name] = to_object(name, build_shell(sx, sz), [mats['nagomi_shell']], hinge_matrix(sx, sz))
    for name, ob in objs.items():
        if name != 'nagomi':
            mw = ob.matrix_world.copy()
            ob.parent = root
            ob.matrix_world = mw
    return objs


def set_open(objs, angles_deg: dict):
    """殻を開く（名前 → 角度）。確認の画像用（ゲームでは nagomi_view.gd が同じことをする）。"""
    from mathutils import Matrix
    for name, (sx, sz) in SHELLS.items():
        rest = Matrix(hinge_matrix(sx, sz).tolist())
        objs[name].matrix_world = rest @ Matrix.Rotation(math.radians(angles_deg.get(name, 0.0)), 4, 'X')


def export_glb(objs, path: str):
    import bpy
    set_open(objs, {})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs.values():
        ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, export_apply=False,
                              export_animations=False, use_selection=True)


def triangle_count(objs) -> int:
    n = 0
    for ob in objs.values():
        if ob.type == 'MESH':
            n += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return n


# ---------------------------------------------------------------- 確認（絵と Cycles の画像を並べる）

ORTHO = 2048 / 61.5 / 100      # 絵の 2048px の幅（m）
TILE = 400
# 視点：名前 → (絵のファイル, カメラの向き（物体から見たカメラの方向）, 上の向き, 殻の角度)
VIEWS = {
    'front': ('nagomi_3d_front.png', (0, -1, 0), (0, 0, 1), 0),
    'side_right': ('nagomi_3d_side_right.png', (1, 0, 0), (0, 0, 1), 0),
    'top': ('nagomi_3d_top.png', (0, 0, 1), (0, 1, 0), 0),
    'bottom': ('nagomi_3d_bottom.png', (0, 0, -1), (0, -1, 0), 0),
    'back': ('nagomi_3d_back.png', (0, 1, 0), (0, 0, 1), 0),
    'front_right45': ('nagomi_3d_front_right45.png', (0.7071, -0.7071, 0), (0, 0, 1), 0),
    'open_front': ('nagomi_3d_open_front.png', (0, -1, 0), (0, 0, 1), OPEN_DEG['open']),
    'open_side_right': ('nagomi_3d_open_side_right.png', (1, 0, 0), (0, 0, 1), OPEN_DEG['open']),
}


def render_views(objs, out_dir: str, samples: int = 24) -> dict:
    """VIEWS の各視点を正投影（絵と同じ縮尺）で描く。戻り値：名前 → PNG のパス"""
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
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
    sc.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 2.2
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ORTHO
    sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for name, (_, d, up, ang) in VIEWS.items():
        set_open(objs, {k: ang for k in SHELLS})
        d = Vector(d).normalized()
        cam.location = d * 1.0
        # カメラの -Z を物体へ、+Y を上へ
        z = d
        x = Vector(up).cross(z).normalized()
        y = z.cross(x)
        rot = Matrix((x, y, z)).transposed()
        cam.matrix_world = Matrix.Translation(cam.location) @ rot.to_4x4()
        # 光はカメラの左上から
        sun.matrix_world = (rot @ Matrix.Rotation(math.radians(-25), 3, 'X')
                            @ Matrix.Rotation(math.radians(-20), 3, 'Y')).to_4x4()
        p = os.path.join(out_dir, f'render_{name}.png')
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        out[name] = p
    set_open(objs, {})
    return out


def fetch_art(src: str):
    """比べる絵が src になければ、絵のブランチから取り出す。"""
    import subprocess
    os.makedirs(src, exist_ok=True)
    for art_file, *_ in VIEWS.values():
        p = os.path.join(src, art_file)
        if not os.path.exists(p):
            data = subprocess.run(['git', 'show', f'{ART_REF}/{art_file}'], cwd=REPO, check=True,
                                  capture_output=True).stdout
            with open(p, 'wb') as f:
                f.write(data)


def review(objs, src: str, out_dir: str) -> dict:
    """絵と描いた画像を並べた一覧（閉・全開）と、外形の重なり（IoU）を作る。"""
    from PIL import Image, ImageDraw
    fetch_art(src)
    renders = render_views(objs, os.path.join(out_dir, 'renders'))
    bg = (150, 150, 155)
    scores = {}
    tiles = []
    for name, (art_file, *_rest) in VIEWS.items():
        art = Image.open(os.path.join(src, art_file)).convert('RGBA').resize((TILE, TILE), Image.LANCZOS)
        ren = Image.open(renders[name]).convert('RGBA')
        a1 = np.asarray(art)[..., 3] > 64
        a2 = np.asarray(ren)[..., 3] > 64
        scores[name] = round(float((a1 & a2).sum() / max(1, (a1 | a2).sum())), 3)
        diff = np.zeros((TILE, TILE, 3), np.uint8) + np.array(bg, np.uint8)
        diff[a1 & ~a2] = (220, 60, 60)    # 絵にだけある
        diff[a2 & ~a1] = (60, 110, 230)   # モデルにだけある
        diff[a1 & a2] = (235, 235, 235)
        row = []
        for im in (art, ren):
            t = Image.new('RGB', (TILE, TILE), bg)
            t.paste(im, (0, 0), im)
            row.append(t)
        row.append(Image.fromarray(diff))
        tiles.append((name, row))
    cols = 2   # 1 行に 2 視点（絵・描いた画像・外形の差）
    W = Image.new('RGB', (cols * 3 * TILE, ((len(tiles) + 1) // cols) * (TILE + 24)), (40, 40, 44))
    dr = ImageDraw.Draw(W)
    for k, (name, row) in enumerate(tiles):
        x0 = (k % cols) * 3 * TILE
        y0 = (k // cols) * (TILE + 24)
        dr.text((x0 + 6, y0 + 4), f'{name}  art | render | silhouette (red=art only, blue=model only)  IoU {scores[name]}',
                fill=(230, 230, 230))
        for j, im in enumerate(row):
            W.paste(im, (x0 + j * TILE, y0 + 24))
    sheet = os.path.join(out_dir, 'nagomi_compare.png')
    W.save(sheet)
    small = W.copy()
    small.thumbnail((1600, 1600))
    small.convert('RGB').save(os.path.join(out_dir, 'nagomi_compare_small.jpg'), quality=88)
    return scores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=OUT_GLB)
    ap.add_argument('--src', default=os.path.join(WORK, 'src'), help='絵のフォルダ（--review で使う）')
    ap.add_argument('--review', action='store_true', help='絵との比較の画像を build/nagomi/review/ に作る')
    args = ap.parse_args()
    objs = build_scene()
    export_glb(objs, args.out)
    report = {'out': os.path.relpath(args.out, REPO), 'triangles': triangle_count(objs)}
    if args.review:
        report['iou'] = review(objs, args.src, os.path.join(WORK, 'review'))
        os.makedirs(os.path.join(WORK, 'review'), exist_ok=True)
        with open(os.path.join(WORK, 'review', 'report.json'), 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
