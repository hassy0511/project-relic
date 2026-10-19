"""町の住人のキット：体の土台 4 種 ＋ 部品 ＋ 髪 ＋ 決まりの顔 ＋ 色の案から、1 人を 1 つの設定で作る。

  .venv-blender/bin/python tools/blender/models/townsfolk.py --person tobi      1 人（設定 tools/blender/recon/chars/townsfolk/tobi.json）
  .venv-blender/bin/python tools/blender/models/townsfolk.py --all             全員
      [--out-dir godot/assets/models]  [--render build/townsfolk/render]（Cycles で 4 方向の確認の画像）

出力：godot/assets/models/tf_<id>.glb（骨・動作つき）と build/townsfolk/stats/tf_<id>.json（三角形・材質の数）。
作り方：絵（W2_townsfolk の townsfolk_bodies・townsfolk_parts・townsfolk_variations）から測った寸法で、部品を単純な形から直接組む
（SKILL の「機械は寸法から部品で組む」と同じ。遠くで見る住人なので、絵からの再構築はしない）。
- 体の土台（BODIES）：大人の男 170cm・大人の女 160cm・子ども 120cm・老人 145cm。骨は標準の 20 本（lib/humanoid.py）で全員同じ構成。
  身長は頭頂の高さ。設定の height で一様に伸び縮みする
- 部品（PARTS の関数）：帽子・首巻き・上着・前掛け・下衣・靴・手袋・髪・ひげ・つぎあて。どれも面ごとに平らな 1 色（色見本のマス目）
- 色：townsfolk_tex.PALETTE の名前か、色の案（SCHEMES）の "$a"・"$b"・"$a_dark"・"$b_dark"
- 顔：townsfolk_tex.face_image が決まりで描いた目・眉・口を、頭の正面に平らに投影する。テクスチャは顔＋色見本の 1 枚、材質も 1 つ
- 動作：子どもは child_anims（待機・歩き・走り・しゃがむ）、ほかは townsfolk_anims の待機（老人は背を丸める）
座標：Blender の Z が上、正面は −Y、本人の左が +X、靴底が z=0。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402,I001
import bmesh  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from lib import common as C  # noqa: E402
from lib import humanoid as H  # noqa: E402
from lib import mesh as M  # noqa: E402
from models import townsfolk_tex as T  # noqa: E402

CONF_DIR = os.path.join(C.REPO, 'tools', 'blender', 'recon', 'chars', 'townsfolk')
OUT_DIR = os.path.join(C.REPO, 'godot', 'assets', 'models')
BUILD_DIR = os.path.join(C.REPO, 'build', 'townsfolk')

# ---------------------------------------------------------------- 体の土台（寸法は m。絵の三面図を身長で割って読んだ）
# S：頭頂の高さ。chin：あごの先、neck：首の付け根（襟の高さ）、sh：肩の関節（x, z）、chest・belt・hip：胴の輪切り（z, 半幅, 半奥行き）、
# hem：上着（チュニック）の裾、crotch：股、hip_z：股関節、knee・ankle：（z, x）、arm_deg：腕の開き、elbow・wrist・hand_end：z、
# r_*：手足の半径、head：(半幅, 半奥行き)、foot：（つま先の前の長さ, かかとの後ろ, 半幅）
BODIES = {
    'man': dict(S=1.67, chin=1.44, neck=1.385, sh=(0.175, 1.30), sh_top=0.20,
                chest=(1.17, 0.165, 0.118), belt=(0.995, 0.150, 0.106), hip=(0.86, 0.160, 0.112), hem=(0.68, 0.215, 0.150),
                crotch=0.73, hip_z=0.80, knee=(0.44, 0.125), ankle=(0.10, 0.165), arm_deg=13.0, elbow=1.02, wrist=0.77,
                hand_end=0.665, r_upper=0.048, r_fore=0.041, r_wrist=0.032, r_thigh=0.078, r_calf=0.056, r_ankle=0.040,
                r_neck=0.052, head=(0.092, 0.104), foot=(0.175, 0.075, 0.062), hand=1.0, clips='adult'),
    'woman': dict(S=1.58, chin=1.32, neck=1.268, sh=(0.150, 1.19), sh_top=0.168,
                  chest=(1.07, 0.136, 0.104), belt=(0.965, 0.118, 0.090), hip=(0.84, 0.150, 0.108), hem=(0.59, 0.195, 0.140),
                  crotch=0.66, hip_z=0.74, knee=(0.42, 0.110), ankle=(0.10, 0.145), arm_deg=14.0, elbow=0.955, wrist=0.71,
                  hand_end=0.615, r_upper=0.038, r_fore=0.034, r_wrist=0.027, r_thigh=0.070, r_calf=0.050, r_ankle=0.035,
                  r_neck=0.042, head=(0.103, 0.114), foot=(0.150, 0.065, 0.052), hand=0.88, clips='adult'),
    'child': dict(S=1.15, chin=0.865, neck=0.828, sh=(0.122, 0.768), sh_top=0.140,
                  chest=(0.68, 0.115, 0.090), belt=(0.555, 0.108, 0.084), hip=(0.48, 0.114, 0.088), hem=(0.385, 0.145, 0.105),
                  crotch=0.39, hip_z=0.44, knee=(0.215, 0.085), ankle=(0.075, 0.108), arm_deg=16.0, elbow=0.585, wrist=0.448,
                  hand_end=0.372, r_upper=0.034, r_fore=0.030, r_wrist=0.025, r_thigh=0.056, r_calf=0.043, r_ankle=0.031,
                  r_neck=0.036, head=(0.121, 0.128), foot=(0.125, 0.055, 0.046), hand=0.78, clips='child'),
    'elder': dict(S=1.43, chin=1.12, neck=1.075, sh=(0.150, 0.98), sh_top=0.170,
                  chest=(0.90, 0.146, 0.116), belt=(0.83, 0.140, 0.110), hip=(0.71, 0.152, 0.114), hem=(0.545, 0.200, 0.140),
                  crotch=0.555, hip_z=0.62, knee=(0.33, 0.100), ankle=(0.09, 0.135), arm_deg=13.0, elbow=0.77, wrist=0.59,
                  hand_end=0.49, r_upper=0.043, r_fore=0.037, r_wrist=0.030, r_thigh=0.068, r_calf=0.051, r_ankle=0.037,
                  r_neck=0.045, head=(0.122, 0.133), foot=(0.150, 0.065, 0.055), hand=0.92, clips='elder'),
}

TORSO = ['hips', 'spine', 'chest', 'neck']


class Body:
    """体の土台の寸法（設定の height に合わせて一様に伸ばす）と関節"""

    def __init__(self, kind: str, height: float | None = None):
        d = BODIES[kind]
        self.kind = kind
        self.k = (height or d['S']) / d['S']
        k = self.k
        s = lambda v: v * k  # noqa: E731
        self.S = s(d['S'])
        self.chin, self.neck = s(d['chin']), s(d['neck'])
        self.sh_x, self.sh_z = s(d['sh'][0]), s(d['sh'][1])
        self.sh_top = s(d['sh_top'])
        self.chest = tuple(s(v) for v in d['chest'])
        self.belt = tuple(s(v) for v in d['belt'])
        self.hip = tuple(s(v) for v in d['hip'])
        self.hem = tuple(s(v) for v in d['hem'])
        self.crotch, self.hip_z = s(d['crotch']), s(d['hip_z'])
        self.knee = tuple(s(v) for v in d['knee'])
        self.ankle = tuple(s(v) for v in d['ankle'])
        self.arm_deg = d['arm_deg']
        self.elbow_z, self.wrist_z, self.hand_end_z = s(d['elbow']), s(d['wrist']), s(d['hand_end'])
        for key in ('r_upper', 'r_fore', 'r_wrist', 'r_thigh', 'r_calf', 'r_ankle', 'r_neck'):
            setattr(self, key, s(d[key]))
        self.head_h = self.S - self.chin
        self.head_rx, self.head_ry = s(d['head'][0]), s(d['head'][1])
        self.head_c = Vector((0.0, 0.004 * k, self.chin + 0.53 * self.head_h))
        self.head_rz_top = self.S - self.head_c.z
        self.head_rz_bot = self.head_c.z - self.chin
        self.foot = tuple(s(v) for v in d['foot'])
        self.hand_k = d['hand'] * k
        self.clips = d['clips']
        self.joints = self._joints()

    def arm_pt(self, z: float, side: int) -> Vector:
        """腕の軸の上の、高さ z の点（基準の姿勢は腕を arm_deg だけ外へ開いて下ろす）"""
        t = math.tan(math.radians(self.arm_deg))
        return Vector((side * (self.sh_x + (self.sh_z - z) * t), 0.0, z))

    def leg_pt(self, z: float, side: int) -> Vector:
        """脚の軸（股関節 → 膝 → 足首）の上の、高さ z の点"""
        hx, kz, kx, az, ax = self.leg_x0, self.knee[0], self.knee[1], self.ankle[0], self.ankle[1]
        if z >= kz:
            f = (self.hip_z - z) / (self.hip_z - kz)
            x = hx + (kx - hx) * f
        else:
            f = (kz - z) / (kz - az)
            x = kx + (ax - kx) * f
        return Vector((side * x, 0.0, z))

    def _joints(self) -> dict:
        self.leg_x0 = self.knee[1] * 0.78
        e, w, he = (self.arm_pt(z, 1) for z in (self.elbow_z, self.wrist_z, self.hand_end_z))
        neck_j = self.neck - 0.25 * (self.neck - self.chest[0])
        j = {
            'root': (0, 0, 0),
            'hips': (0, 0, self.hip_z),
            'spine': (0, 0, self.belt[0] - 0.02 * self.k),
            'chest': (0, 0, self.chest[0]),
            'neck': (0, 0, neck_j),
            'head': (0, 0.004 * self.k, self.chin + 0.06 * self.head_h),
            'head_end': (0, 0.004 * self.k, self.S),
            'shoulder': (self.sh_x * 0.25, 0, self.sh_z - 0.01 * self.k),
            'upper_arm': (self.sh_x, 0, self.sh_z),
            'forearm': (e.x, 0.006 * self.k, e.z),
            'hand': (w.x, 0.0, w.z),
            'hand_end': (he.x, -0.004 * self.k, he.z),
            'thigh': (self.leg_x0, 0, self.hip_z),
            'shin': (self.knee[1], -0.008 * self.k, self.knee[0]),
            'foot': (self.ankle[1], 0.006 * self.k, self.ankle[0]),
            'toe': (self.ankle[1], -self.foot[0], 0.012 * self.k),
        }
        return j

    def J(self, name: str, side: int = 1) -> Vector:
        return Vector(H.joint(name, 1.0, side, self.joints))

    def torso_at(self, z: float) -> tuple[float, float]:
        """胴（シャツの面）の半幅・半奥行き。輪切りの表をなめらかにつなぐ"""
        tab = [(self.hem[0], self.hip[1] * 0.98, self.hip[2] * 0.98), (self.hip[0], self.hip[1], self.hip[2]),
               (self.belt[0], self.belt[1], self.belt[2]), (self.chest[0], self.chest[1], self.chest[2]),
               (self.sh_z, self.sh_top * 0.92, self.chest[2] * 0.92), (self.neck, self.r_neck * 1.9, self.r_neck * 1.7)]
        if z <= tab[0][0]:
            return tab[0][1], tab[0][2]
        for (z0, a0, b0), (z1, a1, b1) in zip(tab, tab[1:]):
            if z0 <= z <= z1:
                f = (z - z0) / (z1 - z0)
                f = f * f * (3 - 2 * f)
                return a0 + (a1 - a0) * f, b0 + (b1 - b0) * f
        return tab[-1][1], tab[-1][2]


# ---------------------------------------------------------------- 形の道具

def shell(name: str, levels: list, sides: int = 12, a0: float = -math.pi, a1: float = math.pi, closed: bool = True,
          power: float = 2.4, cap_top: bool = False, cap_bottom: bool = False) -> bpy.types.Object:
    """縦の軸のまわりの殻。levels：[(z, 中心 x, 中心 y, 半幅, 半奥行き), …]（下から上）。
    角度 a は正面（−Y）が 0、本人の左（+X）が +90 度。closed=False なら a0〜a1 だけの板（前の開いた上着など）。
    断面は超楕円（power。2 で楕円、大きいほど角ばる）"""
    bm = bmesh.new()
    n = sides if closed else sides + 1
    rows = []
    for (z, cx, cy, rx, ry) in levels:
        row = []
        for i in range(n):
            a = (a0 + (a1 - a0) * i / sides) if not closed else (-math.pi + 2 * math.pi * (i + 0.5) / sides)
            sa, ca = math.sin(a), math.cos(a)
            ex = 2.0 / power
            x = cx + rx * math.copysign(abs(sa) ** ex, sa)
            y = cy - ry * math.copysign(abs(ca) ** ex, ca)
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        m = n if closed else n - 1
        for i in range(m):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if closed and cap_bottom:
        bm.faces.new(list(reversed(rows[0])))
    if closed and cap_top:
        bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return M._to_object(name, bm)


def solidify(obj: bpy.types.Object, t: float) -> None:
    """板に厚みを付ける（外へ t）"""
    mod = obj.modifiers.new('solid', 'SOLIDIFY')
    mod.thickness = t
    mod.offset = 1.0
    mod.use_even_offset = True
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def tube(name: str, pts: list, radii: list, sides: int = 8, caps: bool = True, ref=(0, -1, 0)) -> bpy.types.Object:
    return M.loft(name, [tuple(p) for p in pts], radii, sides=sides, cap_start=caps, cap_end=caps, ref=ref)


def lerp(a: Vector, b: Vector, t: float) -> Vector:
    return a + (b - a) * t


def flip_faces_outward(obj: bpy.types.Object, center_fn) -> None:
    """閉じていない殻の面の向きを、軸から外向きにそろえる（Godot は裏の面を描かない）"""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    flip = []
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(c - center_fn(c)) < 0:
            flip.append(f)
    bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(me)
    bm.free()


# ---------------------------------------------------------------- 1 人を組む

class Person:
    def __init__(self, conf: dict):
        self.conf = conf
        self.id = conf['id']
        self.body = Body(conf['body'], conf.get('height'))
        self.scheme = T.SCHEMES.get(conf.get('scheme', 'sand_rust'), {})
        self.skin = conf.get('skin', 'skin')
        self.parts: list[bpy.types.Object] = []
        self.stats: dict[str, int] = {}
        self.arm = H.build_armature(1.0, f'TF_{self.id}_Rig', self.body.joints)
        self.mat = None
        self.tex_path = os.path.join(BUILD_DIR, 'tex', f'tf_{self.id}.png')

    # 色の名前（"$a" などの案の色も）→ 色見本の名前
    def col(self, c: str | None, default: str = 'cream') -> str:
        c = c or default
        if c.startswith('$'):
            return self.scheme[c[1:]]
        return c

    def add(self, obj, group: str, color, weights, shade: float | None = 0.0):
        """color：色の名前か (面の中心, 法線) → 色の名前 の関数。weights：骨の名前（剛体）か候補の骨のリスト（距離で自動）"""
        me = obj.data
        if not me.uv_layers:
            me.uv_layers.new(name='UVMap')
        uvl = me.uv_layers[0].data
        for poly in me.polygons:
            name = self.col(color) if isinstance(color, str) else self.col(color(poly.center.copy(), poly.normal.copy()))
            u, v = T.palette_uv(name)
            for li in poly.loop_indices:
                uvl[li].uv = (u, v)
        if isinstance(weights, str):
            M.weight_rigid(obj, weights)
        else:
            M.weight_auto(obj, self.arm, weights)
        M.smooth(obj, shade)
        self.stats[group] = self.stats.get(group, 0) + M.tri_count(obj)
        self.parts.append(obj)
        return obj

    def arm_bones(self, s: int) -> list[str]:
        sx = '.L' if s == 1 else '.R'
        return ['chest', 'shoulder' + sx, 'upper_arm' + sx, 'forearm' + sx, 'hand' + sx]

    def leg_bones(self, s: int) -> list[str]:
        sx = '.L' if s == 1 else '.R'
        return ['hips', 'thigh' + sx, 'shin' + sx, 'foot' + sx]


# ---------------------------------------------------------------- 頭・顔・首・耳

def build_head(p: Person) -> None:
    b = p.body
    c = b.head_c
    head = M.head_shape('head', tuple(c), rx=b.head_rx, ry=b.head_ry, rz_top=b.head_rz_top, rz_bot=b.head_rz_bot,
                        segments=20, rings=14, jaw=0.50, chin_fwd=0.10 * b.head_h, face_flat=0.86)
    p.add(head, 'head', p.skin, 'head', shade=None)
    # 顔の面：正面から平らに投影して、テクスチャの左の顔の区画を指す
    me = head.data
    uvl = me.uv_layers[0].data
    hu = b.head_h
    for poly in me.polygons:
        cc, n = poly.center, poly.normal
        if cc.y < c.y - 0.2 * b.head_ry and n.y < -0.30 and cc.z > b.chin - 0.01 and cc.z < b.chin + 0.80 * hu:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                u = (co.x / hu - T.FACE_U[0]) / (T.FACE_U[1] - T.FACE_U[0])
                v = ((co.z - b.chin) / hu - T.FACE_V[0]) / (T.FACE_V[1] - T.FACE_V[0])
                uvl[li].uv = (min(1.0, max(0.0, u)) * T.FACE_PX / T.TEX_W, 1 - (1 - min(1.0, max(0.0, v))) * T.FACE_PX / T.TEX_H)
    # 耳
    for s in (1, -1):
        ear = M.head_shape('ear', (s * b.head_rx * 0.96, c.y + 0.10 * b.head_ry, c.z - 0.10 * hu), rx=0.022 * b.k * 1.0,
                           ry=0.030 * b.k, rz_top=0.036 * b.k, rz_bot=0.030 * b.k, segments=8, rings=6, jaw=0.2,
                           chin_fwd=0.0, face_flat=1.0)
        p.add(ear, 'head', p.skin, 'head', shade=None)
    # 首（襟の中から頭の中まで）
    neck = tube('neck', [(0, 0.004 * b.k, b.neck - 0.05 * b.k), (0, 0.006 * b.k, b.chin + 0.02 * b.k),
                         (0, 0.010 * b.k, b.head_c.z - 0.02 * b.k)], [b.r_neck, b.r_neck * 0.97, b.r_neck * 0.95], sides=10)
    p.add(neck, 'head', p.skin, ['chest', 'neck', 'head'], shade=None)


def face_params(p: Person) -> dict:
    """顔の設定（体の種類の既定 ＋ 設定の face で上書き）"""
    defaults = {
        'man': dict(eye_u=0.150, eye_v=0.37, eye_size=0.82, eye_tall=0.95, brow_w=0.034, brow_dv=0.105, brow_tilt=0.012,
                    mouth='flat', mouth_v=0.15, nose_v=0.25, lid_w=0.024),
        'woman': dict(eye_u=0.155, eye_v=0.36, eye_size=0.98, brow_w=0.022, brow_dv=0.120, mouth='smile', mouth_v=0.15,
                      nose_v=0.25, lash=True, blush=0.8),
        'child': dict(eye_u=0.160, eye_v=0.35, eye_size=1.06, eye_tall=1.05, brow_w=0.026, brow_dv=0.120, mouth='smile',
                      mouth_v=0.14, nose_v=0.24, blush=0.9),
        'elder': dict(eye_u=0.150, eye_v=0.37, eye_size=0.80, eye_tall=0.85, lid=0.18, brow_w=0.030, brow_dv=0.110,
                      mouth='smile', mouth_v=0.15, nose_v=0.25, old=True, wrinkles=True, blush=0.4),
    }[p.body.kind]
    f = dict(defaults)
    f.update(p.conf.get('face', {}))
    f['skin'] = T.color_hex(p.skin)
    if 'brow' in f and not f['brow'].startswith('#'):
        f['brow'] = T.color_hex(f['brow'])
    return f


# ---------------------------------------------------------------- 髪・ひげ

def head_pt(b: Body, lon: float, lat: float, gap: float = 0.0) -> Vector:
    """頭の楕円体の面の点。lon：正面 0・本人の左 +90 度、lat：中心の高さ 0・上 +90"""
    lo, la = math.radians(lon), math.radians(lat)
    rz = b.head_rz_top if la >= 0 else b.head_rz_bot
    x = (b.head_rx + gap) * math.cos(la) * math.sin(lo)
    y = -(b.head_ry + gap) * math.cos(la) * math.cos(lo)
    z = (rz + gap) * math.sin(la)
    return b.head_c + Vector((x, y, z))


def hair_cap(p: Person, color: str, front_lat: float, side_lat: float, back_lat: float, gap: float = 0.010,
             bulk: float = 1.0) -> None:
    """頭を覆う髪の土台。生え際（正面 front_lat・横 side_lat・後ろ back_lat、度）より下の面は消す"""
    b = p.body
    g = gap * b.k * bulk
    cap = M.head_shape('hair_cap', tuple(b.head_c + Vector((0, 0.006 * b.k, 0.004 * b.k))), rx=b.head_rx + g * 1.3,
                       ry=b.head_ry + g * 1.2, rz_top=b.head_rz_top + g * 1.5, rz_bot=b.head_rz_bot + g, segments=16, rings=12,
                       jaw=0.0, chin_fwd=0.0, face_flat=1.0)
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median() - b.head_c
        lon = math.degrees(math.atan2(c.x / b.head_rx, -c.y / b.head_ry))
        rz = b.head_rz_top if c.z >= 0 else b.head_rz_bot
        lat = math.degrees(math.asin(max(-1.0, min(1.0, c.z / (rz + g)))))
        a = abs(lon)
        if a < 60:
            lim = front_lat + (side_lat - front_lat) * max(0.0, (a - 35) / 25)
        elif a < 110:
            lim = side_lat
        else:
            lim = side_lat + (back_lat - side_lat) * min(1.0, (a - 110) / 40)
        if lat < lim:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(cap.data)
    bm.free()
    p.add(cap, 'hair', color, 'head', shade=0)


def lock_on(p: Person, color: str, base: tuple, tip: tuple, width: float, depth: float, bend: float = 0.012,
            gap: float = 0.006, fat: float = 1.0) -> None:
    """頭の面の (経度, 緯度) の根から、(経度, 緯度, 外への浮き) の先へ伸びる房"""
    b = p.body
    k = b.k
    root = head_pt(b, base[0], base[1], gap * k)
    tp = head_pt(b, tip[0], tip[1], tip[2] * k if len(tip) > 2 else gap * k)
    mid = lerp(root, tp, 0.5)
    out = (mid - b.head_c).normalized()
    ctrl = mid + out * bend * k
    o = M.lock('lock', tuple(root), tuple(ctrl), tuple(tp), width * k, depth * k, sides=4, segments=3, ref=tuple(out), fat=fat)
    p.add(o, 'hair', color, 'head', shade=0)


def build_hair(p: Person) -> None:
    h = p.conf.get('hair')
    if not h:
        return
    b = p.body
    k = b.k
    style = h['style']
    col = h.get('color', 'hair_brown')
    dark = h.get('dark', col)
    hat = p.conf.get('hat')
    if style == 'short':
        # 短い髪：土台 ＋ 上と横の小さな房、前髪 3 本
        hair_cap(p, col, 52, 2, -38, gap=0.012)
        if not hat:
            for lon, lat, tl, tt, w in ((0, 70, 25, 80, 0.045), (40, 62, 70, 52, 0.040), (-40, 62, -70, 52, 0.040),
                                        (120, 55, 150, 30, 0.042), (-120, 55, -150, 30, 0.042), (180, 60, 180, 20, 0.045),
                                        (80, 70, 110, 55, 0.040), (-80, 70, -110, 55, 0.040)):
                lock_on(p, col, (lon, lat), (tl, tt, 0.026), w, 0.022, bend=0.018)
        for lon, tl in ((-22, -30), (8, 18), (34, 44)):
            lock_on(p, col, (lon, 62), (tl, 30, 0.012), 0.040, 0.016, bend=0.012)
        for s in (1, -1):
            lock_on(p, col, (s * 70, 30), (s * 76, -8, 0.010), 0.034, 0.016, bend=0.008)
    elif style == 'spiky':
        # 子どもの立った髪：大きな房を多く
        hair_cap(p, col, 50, 0, -40, gap=0.016, bulk=1.3)
        if not hat:
            for lon, lat, tl, tt, w in ((0, 75, 20, 95, 0.060), (45, 60, 80, 55, 0.055), (-45, 60, -80, 55, 0.055),
                                        (130, 50, 160, 25, 0.055), (-130, 50, -160, 25, 0.055), (180, 55, 180, 10, 0.06),
                                        (90, 62, 125, 40, 0.05), (-90, 62, -125, 40, 0.05)):
                lock_on(p, col, (lon, lat), (tl, tt, 0.040), w, 0.030, bend=0.026)
        for lon, tl in ((-30, -40), (-8, -2), (14, 22), (36, 46)):
            lock_on(p, col, (lon, 64), (tl, 28, 0.016), 0.048, 0.020, bend=0.016)
        for s in (1, -1):
            lock_on(p, col, (s * 72, 35), (s * 80, -12, 0.016), 0.042, 0.020, bend=0.010)
            lock_on(p, col, (s * 120, 30), (s * 130, -25, 0.016), 0.050, 0.020, bend=0.010)
    elif style in ('bun', 'grey_bun'):
        # まとめ髪：土台（えり足まで）＋ 上のお団子 ＋ 顔の横の房 ＋ 前髪
        hair_cap(p, col, 56, 8, -30, gap=0.010)
        bun_c = head_pt(b, 180, 55 if style == 'bun' else 20, 0.040 * k)
        r = (0.058 if style == 'bun' else 0.050) * k
        bun = M.head_shape('bun', tuple(bun_c), rx=r, ry=r * 0.9, rz_top=r * 0.9, rz_bot=r * 0.85, segments=10, rings=7,
                           jaw=0.0, chin_fwd=0.0, face_flat=1.0)
        p.add(bun, 'hair', dark, 'head', shade=0)
        for lon, tl in ((-26, -36), (6, 14), (30, 44)):
            lock_on(p, col, (lon, 64), (tl, 34, 0.010), 0.046, 0.016, bend=0.012)
        for s in (1, -1):
            lock_on(p, col, (s * 58, 40), (s * 66, -40, 0.012), 0.030, 0.014, bend=0.010)
        if h.get('band'):
            ring = [head_pt(b, 360 * i / 14, 46 + 14 * math.cos(math.radians(360 * i / 14)), 0.018 * k) for i in range(14)]
            band = M.loft('band', [tuple(v) for v in ring], [(0.020 * k, 0.007 * k)] * 14, sides=4, loop=True,
                          ref=(0, 0, 1), angle0=math.pi / 4)
            p.add(band, 'hair', h['band'], 'head', shade=0)
    elif style == 'pigtails':
        hair_cap(p, col, 56, 4, -40, gap=0.012)
        for lon, tl in ((-30, -40), (-10, -6), (12, 18), (32, 44)):
            lock_on(p, col, (lon, 66), (tl, 30, 0.012), 0.046, 0.018, bend=0.014)
        for s in (1, -1):
            root = head_pt(b, s * 105, -5, 0.010 * k)
            pts = [root, root + Vector((s * 0.040, 0.010, -0.010)) * k, root + Vector((s * 0.070, 0.020, -0.060)) * k,
                   root + Vector((s * 0.075, 0.018, -0.110)) * k]
            tail = tube('tail', pts, [(0.030 * k, 0.030 * k), (0.042 * k, 0.040 * k), (0.038 * k, 0.036 * k), 0.0], sides=6)
            p.add(tail, 'hair', col, 'head', shade=0)
            tie = tube('tie', [root + Vector((s * 0.022, 0.004, -0.004)) * k, root + Vector((s * 0.040, 0.008, -0.010)) * k],
                       [0.026 * k, 0.026 * k], sides=6)
            p.add(tie, 'hair', h.get('tie', 'leather'), 'head', shade=0)
            lock_on(p, col, (s * 62, 40), (s * 70, -20, 0.012), 0.030, 0.014, bend=0.010)
    elif style == 'long':
        hair_cap(p, col, 58, 10, -35, gap=0.012)
        for lon, tl in ((-34, -50), (-12, -16), (10, 18), (30, 48)):
            lock_on(p, col, (lon, 66), (tl, 30, 0.012), 0.050, 0.018, bend=0.014)
        # 後ろと横の長い髪：頭の後ろから肩の上まで下がる板
        lev = []
        top = b.head_c.z + 0.1 * b.head_rz_top
        bot = b.neck - 0.06 * k
        for i in range(5):
            f = i / 4
            z = bot + (top - bot) * f
            rx = (b.head_rx + 0.020 * k) * (0.95 + 0.25 * (1 - f))
            ry = (b.head_ry + 0.016 * k) * (0.85 + 0.15 * (1 - f))
            lev.append((z, 0.0, b.head_c.y + 0.010 * k + 0.02 * k * (1 - f), rx, ry))
        back = shell('long_back', lev, sides=12, a0=math.radians(62), a1=math.radians(298), closed=False, power=2.2)
        solidify(back, 0.012 * k)
        p.add(back, 'hair', col, ['neck', 'head'], shade=0)
        for s in (1, -1):
            lock_on(p, col, (s * 60, 38), (s * 70, -60, 0.020), 0.046, 0.020, bend=0.012)
    elif style == 'grey_bob':
        # 老女の灰の髪：帽子の下から肩へ（耳の前と後ろの房）
        hair_cap(p, col, 50, -10, -40, gap=0.014, bulk=1.2)
        for s in (1, -1):
            lock_on(p, col, (s * 62, 35), (s * 70, -62, 0.020), 0.050, 0.022, bend=0.012)
            lock_on(p, col, (s * 100, 30), (s * 110, -70, 0.024), 0.060, 0.024, bend=0.014)
            lock_on(p, col, (s * 145, 30), (s * 150, -60, 0.020), 0.060, 0.022, bend=0.012)
        for lon, tl in ((-24, -36), (10, 24)):
            lock_on(p, col, (lon, 66), (tl, 36, 0.012), 0.060, 0.018, bend=0.014)
    elif style == 'grey_short':
        # 帽子の下の短い白髪（横と後ろ）
        hair_cap(p, col, 60, -18, -42, gap=0.012)
        for s in (1, -1):
            lock_on(p, col, (s * 78, 20), (s * 86, -22, 0.016), 0.040, 0.018, bend=0.010)
            lock_on(p, col, (s * 130, 15), (s * 140, -30, 0.016), 0.050, 0.018, bend=0.010)
    elif style == 'swept':
        # 後ろへなでつけた短い髪（白髪の青年）：前の房が立ち上がって後ろへ
        hair_cap(p, col, 55, 0, -38, gap=0.014, bulk=1.15)
        for lon, lat, tl, tt, w in ((-10, 66, -30, 92, 0.060), (20, 64, 30, 94, 0.055), (50, 55, 80, 70, 0.050),
                                    (-50, 55, -80, 70, 0.050), (140, 45, 165, 20, 0.055), (-140, 45, -165, 20, 0.055)):
            lock_on(p, col, (lon, lat), (tl, tt, 0.040), w, 0.026, bend=0.022)
        for s in (1, -1):
            lock_on(p, col, (s * 70, 34), (s * 76, -10, 0.012), 0.034, 0.016, bend=0.008)
        lock_on(p, col, (-18, 60), (-28, 28, 0.014), 0.040, 0.016, bend=0.012)


def build_beard(p: Person) -> None:
    bd = p.conf.get('beard')
    if not bd:
        return
    b = p.body
    k = b.k
    col = bd.get('color', 'beard_brown')
    full = bd.get('size', 'short') == 'full'
    # あごの殻：頭の楕円体の下の前の部分を外へ 7〜14mm
    g = (0.016 if full else 0.008) * k
    sh = M.head_shape('beard', tuple(b.head_c), rx=b.head_rx + g, ry=b.head_ry + g, rz_top=b.head_rz_top,
                      rz_bot=b.head_rz_bot + g * (2.6 if full else 1.4), segments=20, rings=14, jaw=0.48,
                      chin_fwd=0.10 * b.head_h, face_flat=0.88)
    bm = bmesh.new()
    bm.from_mesh(sh.data)
    kill = []
    mouth_z = b.chin + 0.15 * b.head_h
    for f in bm.faces:
        c = f.calc_center_median()
        lon = math.degrees(math.atan2((c.x - b.head_c.x) / b.head_rx, -(c.y - b.head_c.y) / b.head_ry))
        top = b.chin + (0.36 if full else 0.30) * b.head_h - 0.002 * abs(lon) * b.k
        ok = abs(lon) < 100 and c.z < top
        # 口のまわりは開ける（口の線が見えるように）。豊かなひげは口の下を残す
        if ok and abs(lon) < 22 and mouth_z - 0.035 * b.head_h < c.z < mouth_z + 0.03 * b.head_h and not full:
            ok = False
        if not ok:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(sh.data)
    bm.free()
    p.add(sh, 'beard', col, 'head', shade=0)
    # 口ひげ
    for s in (1, -1):
        a = head_pt(b, s * 4, -48, 0.010 * k)
        c2 = head_pt(b, s * 30, -62 if not full else -66, 0.008 * k)
        mus = M.lock('mustache', tuple(a), tuple(lerp(a, c2, 0.5) + Vector((0, -0.006 * k, 0.004 * k))), tuple(c2),
                     (0.016 if full else 0.010) * k, 0.008 * k, sides=4, segments=2, ref=(0, -1, 0))
        p.add(mus, 'beard', col, 'head', shade=0)


# ---------------------------------------------------------------- 上半身：シャツ（チュニック）・袖・腕・手

def torso_levels(p: Person, z0: float, z1: float, off: float, n: int = 8, flare: float = 0.0) -> list:
    """胴の面から off だけ外の輪切り（z0〜z1）。flare：裾（z0）の広がりの割合"""
    b = p.body
    out = []
    for i in range(n):
        z = z0 + (z1 - z0) * i / (n - 1)
        rx, ry = b.torso_at(z)
        f = max(0.0, (b.belt[0] - z) / max(1e-6, b.belt[0] - z0)) if z < b.belt[0] else 0.0
        out.append((z, 0.0, 0.004 * b.k, rx + off + flare * rx * f, ry + off + flare * ry * f * 0.8))
    return out


def build_top(p: Person) -> None:
    """シャツ・チュニック（胴の面そのもの）。length：'tunic'（裾は腰の下）か 'tucked'（ベルトの下でズボンへ）"""
    t = p.conf.get('top', {})
    b = p.body
    k = b.k
    col = t.get('color', 'cream')
    trim = t.get('trim', 'sand')
    z0 = b.hem[0] if t.get('length', 'tunic') == 'tunic' else b.belt[0] - 0.06 * k
    flare = 0.0
    if t.get('length', 'tunic') == 'tunic':
        flare = (b.hem[1] / b.torso_at(b.hem[0])[0]) - 1.0
    lev = torso_levels(p, z0, b.neck + 0.005 * k, 0.0, n=10, flare=flare)
    torso = shell('top', lev, sides=12, power=2.4, cap_top=True, cap_bottom=True)
    v_depth = t.get('v_neck', 0.07) * k

    def color(c, n):
        # 首の V の切れ込み（肌）とその縁
        if n.y < -0.4 and abs(c.x) < 0.024 * k and c.z > b.neck - v_depth:
            return p.skin
        if c.z > b.neck - 0.02 * k and n.z > 0.5:
            return trim
        return col
    p.add(torso, 'top', color, TORSO, shade=0)
    # 首まわりの縁（襟ぐり）
    ring = []
    for i in range(14):
        a = 2 * math.pi * i / 14
        ring.append((math.sin(a) * b.r_neck * 1.35, 0.004 * k - math.cos(a) * b.r_neck * 1.25, b.neck + 0.004 * k))
    p.add(M.loft('neckline', ring, [(0.010 * k, 0.010 * k)] * 14, sides=4, loop=True, ref=(0, 0, 1)), 'top', trim, TORSO, 0)
    if t.get('hem_band'):
        lev2 = [(z, cx, cy, rx + 0.004 * k, ry + 0.004 * k) for (z, cx, cy, rx, ry) in lev[:2]]
        band = shell('hem_band', [lev2[0], (lev2[0][0] + 0.03 * k,) + lev2[0][1:]], sides=12, power=2.4)
        p.add(band, 'top', t['hem_band'], TORSO, 0)
    for s in (1, -1):
        build_arm(p, s, t)


def build_arm(p: Person, s: int, t: dict) -> None:
    b = p.body
    k = b.k
    bones = p.arm_bones(s)
    sleeve = t.get('sleeve', 'short')        # short（肘の上）・elbow・wide（7 分の広い袖）・long
    col = t.get('color', 'cream')
    trim = t.get('trim', 'sand')
    sh = b.arm_pt(b.sh_z, s)
    top = sh + Vector((-s * 0.030 * k, 0, 0.030 * k))
    el = b.arm_pt(b.elbow_z, s)
    wr = b.arm_pt(b.wrist_z, s)
    # 肩から肘・手首までの肌（袖の中にも通す）
    skin = tube('arm', [top, lerp(sh, el, 0.5), el, lerp(el, wr, 0.5), wr],
                [b.r_upper * 0.95, b.r_upper * 0.92, b.r_fore * 1.0, b.r_fore * 0.92, b.r_wrist], sides=8)
    p.add(skin, 'arms', p.skin, bones, shade=None)
    end = {'short': 0.62, 'elbow': 0.95, 'wide': 1.25, 'long': 1.92}[sleeve]
    # 袖の先：上腕の長さを 1 とした位置（1 より先は前腕）
    if end <= 1.0:
        e = lerp(sh, el, end)
    else:
        e = lerp(el, wr, end - 1.0)
    r_end = {'short': 1.55, 'elbow': 1.45, 'wide': 2.1, 'long': 1.25}[sleeve] * (b.r_upper if end <= 1 else b.r_fore)
    pts = [top, sh + Vector((0, 0, 0.004 * k)), lerp(sh, e, 0.55), e]
    radii = [(b.r_upper * 1.35, b.r_upper * 1.45), (b.r_upper * 1.55, b.r_upper * 1.6), r_end * 0.98, r_end]
    slv = tube('sleeve', pts, radii, sides=8)
    p.add(slv, 'arms', col, bones[:4] if end > 1 else bones[:3], shade=0)
    # 袖口の帯
    d = (e - lerp(sh, e, 0.8)).normalized()
    band = tube('cuff', [e - d * 0.030 * k, e + d * 0.004 * k], [r_end * 1.06, r_end * 1.08], sides=8)
    p.add(band, 'arms', trim, bones[1:4] if end > 1 else bones[1:3], shade=0)
    if t.get('wrist_band') and sleeve != 'long':
        wb = tube('wrist_band', [lerp(el, wr, 0.55), lerp(el, wr, 0.95)], [b.r_fore * 1.1, b.r_wrist * 1.2], sides=8)
        p.add(wb, 'arms', t['wrist_band'], bones[2:5], shade=0)
    build_hand(p, s)


def build_hand(p: Person, s: int) -> None:
    b = p.body
    k = b.hand_k
    sx = '.L' if s == 1 else '.R'
    wr = b.arm_pt(b.wrist_z, s)
    he = b.arm_pt(b.hand_end_z, s)
    d = (he - wr).normalized()
    g = p.conf.get('gloves')
    palm_c = lerp(wr, he, 0.38)
    rot_y = -s * b.arm_deg
    glove = g.get('color', 'glove') if g else p.skin
    # 掌（手の甲が外を向く）・指（4 本をまとめた塊を少し曲げる）・親指（前）
    p.add(M.rbox('palm', palm_c, (0.030 * k, 0.074 * k, 0.078 * k), bevel=0.012 * k, rot=(0, rot_y, 0)), 'hands', glove,
          'hand' + sx, shade=30)
    fc = lerp(wr, he, 0.80) + Vector((-s * 0.004 * k, 0.002 * k, 0))
    p.add(M.rbox('fingers', fc, (0.026 * k, 0.070 * k, 0.062 * k), bevel=0.011 * k, rot=(0, rot_y + s * 8, 0),
                 taper=(0.8, 0.9)), 'hands', p.skin, 'hand' + sx, shade=40)
    tc = palm_c + Vector((-s * 0.016 * k, -0.034 * k, -0.010 * k))
    p.add(M.rbox('thumb', tc, (0.022 * k, 0.024 * k, 0.052 * k), bevel=0.008 * k, rot=(18, rot_y, -s * 12)), 'hands',
          p.skin if not g else glove, 'hand' + sx, shade=40)
    if g:
        cuff = tube('glove_cuff', [wr + d * 0.004 * k, wr - d * 0.030 * k], [0.034 * k, 0.036 * k], sides=8)
        p.add(cuff, 'hands', g.get('cuff', glove), ['forearm' + sx, 'hand' + sx], shade=0)


# ---------------------------------------------------------------- 帯（ベルト）・ポーチ・肩ひも

def build_belt(p: Person) -> None:
    bl = p.conf.get('belt')
    if not bl:
        return
    b = p.body
    k = b.k
    z = bl.get('z', b.belt[0])
    off = bl.get('off', 0.010) * k
    rx, ry = b.torso_at(z)
    lev = [(z - 0.022 * k, 0.0, 0.004 * k, rx + off, ry + off), (z + 0.022 * k, 0.0, 0.004 * k, rx + off, ry + off)]
    belt = shell('belt', lev, sides=12, power=2.4)
    p.add(belt, 'belt', bl.get('color', 'leather'), TORSO, shade=0)
    fy = 0.004 * k - (ry + off)
    if bl.get('buckle', 'brass'):
        p.add(M.rbox('buckle', (0, fy - 0.004 * k, z), (0.050 * k, 0.010 * k, 0.040 * k), bevel=0.003 * k), 'belt',
              bl.get('buckle', 'brass'), 'spine', shade=0)
    if bl.get('sash'):
        # 帯の結び目から垂れる布（体の土台の絵の茶の帯）
        p.add(M.rbox('sash_tail', (0.040 * k, fy - 0.006 * k, z - 0.10 * k), (0.045 * k, 0.010 * k, 0.17 * k),
                     bevel=0.002 * k, rot=(4, 0, 0)), 'belt', bl.get('color', 'leather'), 'hips', shade=0)
    for side in bl.get('pouch', []):
        s = 1 if side == 'L' else -1
        a = math.radians(s * 75)
        px = math.sin(a) * (rx + off + 0.018 * k)
        py = 0.004 * k - math.cos(a) * (ry + off + 0.018 * k)
        p.add(M.rbox('pouch', (px, py, z - 0.055 * k), (0.030 * k, 0.065 * k, 0.085 * k), bevel=0.008 * k,
                     rot=(0, 0, math.degrees(-a) + 90 * s - 90 * s)), 'belt', bl.get('pouch_color', 'leather'), 'hips',
              shade=0)
    if bl.get('strap'):
        # 肩から斜めに掛けた細いひも（本人の左の肩 → 右の腰）
        sc = bl['strap']
        pts = []
        for i in range(9):
            f = i / 8
            zz = b.sh_z + 0.02 * k + (z - (b.sh_z + 0.02 * k)) * f
            xx = 0.07 * k * (1 - f) - 0.12 * k * f
            rx2, ry2 = b.torso_at(zz)
            pts.append((xx, 0.004 * k - (ry2 + 0.012 * k) * math.sqrt(max(0.05, 1 - (xx / (rx2 + 0.02 * k)) ** 2)), zz))
        p.add(M.loft('strap', pts, [(0.016 * k, 0.004 * k)] * 9, sides=4, ref=(0, -1, 0)), 'belt', sc, TORSO, shade=0)


# ---------------------------------------------------------------- 上着（前の開いた殻・袖つき）・肩掛け

def build_jacket(p: Person) -> None:
    j = p.conf.get('jacket')
    if not j:
        return
    b = p.body
    k = b.k
    kind = j.get('kind', 'short')   # short（短い上着）・vest（袖なし）・long（膝までの上着）・long_vest・wrap（前を重ねる）
    col = j.get('color', '$b')
    trim = j.get('trim', col)
    inner = j.get('inner', 'inner')
    hem_z = {'short': b.belt[0] - 0.10 * k, 'vest': b.belt[0] - 0.08 * k, 'wrap': b.hem[0] + 0.03 * k,
             'long': b.knee[0] + 0.03 * k, 'long_vest': (b.hem[0] + b.knee[0]) / 2}[kind]
    hem_z = j.get('hem', hem_z / k) * k if 'hem' in j else hem_z
    off = j.get('off', 0.020) * k
    open_deg = j.get('open', 16 if kind != 'wrap' else 0)
    lev = []
    n = 10
    top_z = b.neck - 0.01 * k
    for i in range(n):
        z = hem_z + (top_z - hem_z) * i / (n - 1)
        rx, ry = b.torso_at(max(z, b.hem[0]))
        if z < b.hem[0]:
            # 上着が裾より長いとき：下へ広がる
            f = (b.hem[0] - z) / max(1e-6, b.hem[0] - hem_z)
            rx, ry = b.hem[1] * (1 + 0.20 * f), b.hem[2] * (1 + 0.15 * f)
        elif z < b.belt[0]:
            top_rx = b.torso_at(z)[0]
            f = (b.belt[0] - z) / max(1e-6, b.belt[0] - b.hem[0])
            rx, ry = max(top_rx, b.hem[1] * f + top_rx * (1 - f)), max(ry, b.hem[2] * f + ry * (1 - f))
        lev.append((z, 0.0, 0.004 * k, rx + off, ry + off * 0.9))
    a0 = math.radians(open_deg)
    sh_ = shell('jacket', lev, sides=14, a0=a0, a1=2 * math.pi - a0, closed=False, power=2.4)
    flip_faces_outward(sh_, lambda c: Vector((0, 0.004 * k, c.z)))
    solidify(sh_, 0.008 * k)

    def color(c, nrm):
        radial = Vector((c.x, c.y - 0.004 * k, 0))
        if radial.length > 1e-6 and nrm.dot(radial.normalized()) < -0.3:
            return inner
        # 前の縁（襟の折り返し）は trim
        a = math.degrees(math.atan2(c.x, -(c.y - 0.004 * k)))
        if abs(abs(a) - open_deg) < 13 and c.z > b.belt[0] - 0.02 * k and nrm.z < 0.6:
            return trim
        if c.z < hem_z + 0.012 * k:
            return j.get('hem_color', trim if kind in ('wrap',) else col)
        return col
    p.add(sh_, 'jacket', color, TORSO if kind not in ('long',) else ['hips', 'spine', 'chest', 'neck'], shade=0)
    # 襟（後ろで立つ）
    ring = []
    for i in range(9):
        a = math.radians(open_deg + 10 + (360 - 2 * open_deg - 20) * i / 8)
        ring.append((math.sin(a) * b.r_neck * 1.7, 0.004 * k - math.cos(a) * b.r_neck * 1.55 + 0.010 * k,
                     b.neck + 0.010 * k + 0.012 * k * (1 - math.cos(a)) / 2))
    if j.get('collar', True):
        p.add(M.loft('collar', ring, [(0.018 * k, 0.012 * k)] * 9, sides=5, ref=(0, 0, 1)), 'jacket', trim, TORSO, 0)
    # 前ポケット
    for pk in j.get('pockets', []):
        s = 1 if pk.get('side', 'L') == 'L' else -1
        zz = pk.get('z', 0.5) * (b.belt[0] - hem_z) + hem_z if pk.get('rel', True) else pk['z'] * k
        a = math.radians(s * pk.get('a', 38))
        rx, ry = lev[0][3], lev[0][4]
        for (zl, _, _, rxl, ryl) in lev:
            if zl <= zz:
                rx, ry = rxl, ryl
        pc = Vector((math.sin(a) * (rx + 0.012 * k), 0.004 * k - math.cos(a) * (ry + 0.012 * k), zz))
        w, hgt = pk.get('w', 0.075) * k, pk.get('h', 0.075) * k
        p.add(M.rbox('pocket', tuple(pc), (w, 0.012 * k, hgt), bevel=0.003 * k, rot=(0, 0, math.degrees(a))), 'jacket',
              pk.get('color', trim), TORSO, shade=0)
        if pk.get('flap'):
            p.add(M.rbox('flap', tuple(pc + Vector((0, -0.004 * k, hgt * 0.42))), (w * 1.05, 0.016 * k, hgt * 0.28),
                         bevel=0.003 * k, rot=(0, 0, math.degrees(a))), 'jacket', pk['flap'], TORSO, shade=0)
    if j.get('hood'):
        # 背中に下ろしたフード（頭の後ろの下）
        hc = Vector((0, 0.004 * k + b.chest[2] * 0.9, b.neck - 0.03 * k))
        hood = M.head_shape('hood', tuple(hc), rx=b.r_neck * 2.4, ry=0.050 * k, rz_top=0.050 * k, rz_bot=0.080 * k,
                            segments=10, rings=6, jaw=0.2, chin_fwd=0.0, face_flat=1.0)
        p.add(hood, 'jacket', col, TORSO, shade=0)
    # 袖
    sleeve = j.get('sleeve', 'none' if kind in ('vest', 'long_vest') else 'short')
    if sleeve != 'none':
        for s in (1, -1):
            jacket_sleeve(p, s, sleeve, col, j.get('cuff', trim))
    else:
        # 袖ぐりの縁（肩の上の太い縁）
        for s in (1, -1):
            sh = b.arm_pt(b.sh_z, s)
            ring = []
            for i in range(10):
                a = 2 * math.pi * i / 10
                ring.append(tuple(sh + Vector((-s * 0.030 * k + math.cos(a) * 0.0 * k, math.sin(a) * b.r_upper * 1.6,
                                               0.004 * k + math.cos(a) * b.r_upper * 1.5))))
            p.add(M.loft('armhole', ring, [(0.012 * k, 0.012 * k)] * 10, sides=4, loop=True, ref=(1, 0, 0)), 'jacket', trim,
                  p.arm_bones(s)[:2], shade=0)


def jacket_sleeve(p: Person, s: int, sleeve: str, col: str, cuff: str) -> None:
    b = p.body
    k = b.k
    bones = p.arm_bones(s)
    sh = b.arm_pt(b.sh_z, s)
    el = b.arm_pt(b.elbow_z, s)
    wr = b.arm_pt(b.wrist_z, s)
    top = sh + Vector((-s * 0.034 * k, 0, 0.036 * k))
    if sleeve == 'short':
        e, r_end = lerp(sh, el, 0.66), b.r_upper * 1.85
    elif sleeve == 'rolled':
        e, r_end = lerp(sh, el, 0.95), b.r_upper * 1.75
    elif sleeve == 'wide':
        e, r_end = lerp(el, wr, 0.30), b.r_fore * 2.4
    else:
        e, r_end = lerp(el, wr, 0.88), b.r_fore * 1.55
    pts = [top, sh + Vector((0, 0, 0.006 * k)), lerp(sh, e, 0.5), e]
    radii = [(b.r_upper * 1.55, b.r_upper * 1.65), (b.r_upper * 1.80, b.r_upper * 1.85), r_end * 0.97, r_end]
    p.add(tube('jsleeve', pts, radii, sides=8), 'jacket', col, bones[:4] if sleeve in ('wide', 'long') else bones[:3],
          shade=0)
    d = (e - lerp(sh, e, 0.8)).normalized()
    wide = 0.060 if sleeve in ('rolled', 'wide') else 0.034
    p.add(tube('jcuff', [e - d * wide * k, e + d * 0.006 * k], [r_end * 1.07, r_end * 1.10], sides=8), 'jacket', cuff,
          bones[1:4] if sleeve in ('wide', 'long') else bones[1:3], shade=0)


def build_poncho(p: Person) -> None:
    po = p.conf.get('poncho')
    if not po:
        return
    b = p.body
    k = b.k
    lev = []
    bot = po.get('hem', 0.0) * k or (b.belt[0] - 0.05 * k)
    top = b.neck + 0.005 * k
    for i in range(8):
        f = i / 7
        z = bot + (top - bot) * f
        # 肩から下へ広がる（腕の外まで）
        rxs = (b.sh_x + b.r_upper * 2.4) * (1 - f) ** 0.6 + b.r_neck * 1.6 * (1 - (1 - f) ** 0.6)
        rys = (b.chest[2] + 0.050 * k) * (1 - f) ** 0.6 + b.r_neck * 1.5 * (1 - (1 - f) ** 0.6)
        lev.append((z, 0.0, 0.004 * k, rxs, rys))
    pc = shell('poncho', lev, sides=16, power=2.2, closed=True)
    solidify(pc, 0.008 * k)
    col, col2 = po.get('color', '$b'), po.get('color2', 'cream')

    def color(c, nrm):
        radial = Vector((c.x, c.y, 0))
        if radial.length > 1e-6 and nrm.dot(radial.normalized()) < -0.3:
            return 'inner'
        # つぎはぎの 2 色：正面から本人の左は col、右は col2、裾の帯は col2
        if c.z < bot + 0.03 * k:
            return po.get('hem_color', col2)
        return col if c.x * (1 if po.get('split', 'L') == 'L' else -1) > 0.02 * k else col2
    bones = ['spine', 'chest', 'neck', 'shoulder.L', 'shoulder.R']
    p.add(pc, 'poncho', color, bones, shade=0)


# ---------------------------------------------------------------- 首巻き

def build_scarf(p: Person) -> None:
    sc = p.conf.get('scarf')
    if not sc:
        return
    b = p.body
    k = b.k
    kind = sc.get('kind', 'cowl')   # cowl（太い襟巻き）・snood（輪＋留め金）・bandana（三角の布）・long（垂れる長い布）
    col = sc.get('color', 'cream')
    thick = {'cowl': 0.032, 'snood': 0.036, 'bandana': 0.020, 'long': 0.026, 'big': 0.042}[kind] * k
    ring = []
    n = 14
    for i in range(n):
        a = 2 * math.pi * i / n
        zz = b.neck + 0.014 * k + 0.012 * k * math.cos(a)
        ring.append((math.sin(a) * (b.r_neck + thick * 0.75), 0.004 * k - math.cos(a) * (b.r_neck + thick * 0.70), zz))
    p.add(M.loft('scarf', ring, [(thick, thick * 0.85)] * n, sides=6, loop=True, ref=(0, 0, 1)), 'scarf', col,
          ['chest', 'neck'], shade=0)
    fy = 0.004 * k - (b.r_neck + thick * 1.4)
    if kind in ('cowl', 'big', 'bandana'):
        # 前に垂れる三角の布
        w = (0.11 if kind != 'bandana' else 0.09) * k * (1.3 if kind == 'big' else 1.0)
        hgt = (0.10 if kind != 'big' else 0.17) * k
        bm = bmesh.new()
        zt = b.neck + 0.005 * k
        rx0, ry0 = b.torso_at(zt - hgt)
        v = [bm.verts.new((-w, fy + 0.006 * k, zt)), bm.verts.new((w, fy + 0.006 * k, zt)),
             bm.verts.new((0.0, 0.004 * k - ry0 - 0.020 * k, zt - hgt))]
        bm.faces.new(v)
        drape = M._to_object('drape', bm)
        flip_faces_outward(drape, lambda c: Vector((0, 0.1, c.z)))
        solidify(drape, 0.010 * k)
        p.add(drape, 'scarf', col, ['chest', 'neck'], shade=0)
        if kind == 'big':
            # 長い垂れ（本人の右の胸へ）
            pts = [(-0.05 * k, fy, b.neck - 0.01 * k), (-0.075 * k, fy - 0.004 * k, b.chest[0]),
                   (-0.085 * k, 0.004 * k - b.chest[2] - 0.035 * k, b.belt[0] - 0.02 * k)]
            p.add(M.loft('tail', pts, [(0.040 * k, 0.010 * k)] * 3, sides=4, ref=(0, -1, 0)), 'scarf', col, TORSO, 0)
    if kind == 'snood':
        p.add(M.rbox('scarf_buckle', (0.035 * k, fy - 0.010 * k, b.neck + 0.005 * k), (0.030 * k, 0.010 * k, 0.034 * k),
                     bevel=0.003 * k), 'scarf', sc.get('buckle', 'brass'), 'neck', shade=0)
    if kind == 'long':
        # 首に巻いて、本人の左の胸から腰へ垂れる
        rxc, ryc = b.torso_at(b.chest[0])
        pts = [(0.05 * k, fy, b.neck - 0.005 * k), (0.07 * k, 0.004 * k - ryc - 0.030 * k, b.chest[0] + 0.03 * k),
               (0.08 * k, 0.004 * k - b.belt[2] - 0.050 * k, b.belt[0] - 0.02 * k),
               (0.085 * k, 0.004 * k - b.hip[2] - 0.060 * k, b.belt[0] - 0.14 * k)]
        p.add(M.loft('scarf_tail', pts, [(0.045 * k, 0.010 * k)] * 4, sides=4, ref=(0, -1, 0)), 'scarf', col,
              ['hips', 'spine', 'chest'], shade=0)
    if kind == 'bandana':
        p.add(M.rbox('knot', (0.0, 0.004 * k + b.r_neck + thick, b.neck + 0.02 * k), (0.035 * k, 0.025 * k, 0.025 * k),
                     bevel=0.006 * k), 'scarf', col, 'neck', shade=0)


# ---------------------------------------------------------------- 下衣・脚

def leg_axis(b: Body, s: int, z: float) -> Vector:
    return b.leg_pt(z, s)


def build_lower(p: Person) -> None:
    lo = p.conf.get('lower', {'kind': 'pants'})
    b = p.body
    k = b.k
    kind = lo.get('kind', 'pants')   # pants（ふくらんだズボン・足首で絞る）・trousers（まっすぐ）・knickers（膝の下で絞る）・shorts・skirt
    col = lo.get('color', '$a')
    cuff = lo.get('cuff', 'cream')
    # 腰（ベルトの下〜股）
    if kind != 'skirt':
        lev = []
        for i in range(5):
            z = b.crotch - 0.02 * k + (b.belt[0] + 0.01 * k - (b.crotch - 0.02 * k)) * i / 4
            rx, ry = b.torso_at(z)
            lev.append((z, 0.0, 0.004 * k, rx * 1.02, ry * 1.04))
        p.add(shell('seat', lev, sides=12, power=2.4, cap_bottom=True), 'lower', col, ['hips', 'spine'], shade=0)
    # 脚
    for s in (1, -1):
        bones = p.leg_bones(s)
        if kind == 'skirt':
            leg_inner(p, s, b.knee[0] + 0.06 * k, lo.get('leg', 'sock'))
            continue
        if kind == 'pants':
            prof = [(b.crotch + 0.03 * k, 1.00), (b.knee[0] + 0.12 * k, 1.12), (b.knee[0], 1.25), (b.ankle[0] + 0.20 * k, 1.32),
                    (b.ankle[0] + 0.12 * k, 1.05)]
            cuff_z = b.ankle[0] + 0.10 * k
        elif kind == 'trousers':
            prof = [(b.crotch + 0.03 * k, 1.00), (b.knee[0], 0.92), (b.ankle[0] + 0.12 * k, 0.95), (b.ankle[0] + 0.06 * k, 0.98)]
            cuff_z = b.ankle[0] + 0.06 * k
        elif kind == 'knickers':
            prof = [(b.crotch + 0.03 * k, 1.00), (b.knee[0] + 0.10 * k, 1.15), (b.knee[0] - 0.02 * k, 1.28),
                    (b.knee[0] - 0.10 * k, 1.10)]
            cuff_z = b.knee[0] - 0.12 * k
        else:  # shorts
            prof = [(b.crotch + 0.03 * k, 1.02), (b.knee[0] + 0.12 * k, 1.12), (b.knee[0] + 0.03 * k, 1.14)]
            cuff_z = b.knee[0] + 0.02 * k
        rt = b.r_thigh * lo.get('bag', 1.0) * (1.25 if kind in ('pants', 'knickers') else 1.12)
        pts = [leg_axis(b, s, z) + Vector((s * 0.0, 0, 0)) for z, _ in prof]
        pts[0] = pts[0] + Vector((-s * 0.010 * k, 0, 0))
        radii = [(rt * f, rt * f * 0.95) for _, f in prof]
        p.add(tube('leg', pts, radii, sides=10), 'lower', col, bones[:3], shade=0)
        # 裾の帯（ズボンの端）
        dz = 0.032 * k if kind != 'trousers' else 0.022 * k
        r_c = (b.r_calf * 1.05 if kind in ('pants', 'knickers') else rt * prof[-1][1] * 1.02)
        if kind == 'shorts':
            r_c = rt * prof[-1][1] * 1.04
        band = tube('cuff_band', [leg_axis(b, s, cuff_z - dz), leg_axis(b, s, cuff_z + dz)], [r_c, r_c * 1.02], sides=10)
        p.add(band, 'lower', cuff if kind != 'trousers' else lo.get('cuff', col), bones[1:3], shade=0)
        # 帯の下の脚（靴まで）：ズボンの中の靴下か肌
        if kind in ('knickers', 'shorts'):
            leg_inner(p, s, cuff_z, lo.get('leg', 'sock' if kind == 'knickers' else p.skin))
        else:
            leg_inner(p, s, cuff_z, lo.get('leg', 'sock'))
    if kind == 'skirt':
        build_skirt(p, lo)


def leg_inner(p: Person, s: int, z_top: float, color: str) -> None:
    """裾から靴の中までの脚（靴下・肌・タイツ）"""
    b = p.body
    k = b.k
    bones = p.leg_bones(s)
    pts = [leg_axis(b, s, z) for z in (z_top + 0.02 * k, (z_top + b.ankle[0]) / 2, b.ankle[0] + 0.02 * k)]
    r0 = b.r_calf if z_top < b.knee[0] + 0.05 * k else b.r_thigh * 0.85
    p.add(tube('shin', pts, [r0, b.r_calf * 0.92, b.r_ankle], sides=8), 'legs', color, bones[1:4], shade=None)


def build_skirt(p: Person, lo: dict) -> None:
    b = p.body
    k = b.k
    top = b.belt[0] + 0.01 * k
    hem = lo.get('hem', 0.0) * k or (b.ankle[0] + 0.06 * k)
    lev = []
    for i in range(7):
        f = i / 6
        z = hem + (top - hem) * f
        rx0, ry0 = b.torso_at(max(z, b.hip[0]))
        spread = (1 - f)
        rx = max(rx0, b.hip[1]) * (1.0 + 0.42 * lo.get('flare', 1.0) * spread ** 1.2) + 0.012 * k
        ry = max(ry0, b.hip[2]) * (1.0 + 0.50 * lo.get('flare', 1.0) * spread ** 1.2) + 0.012 * k
        if z > b.hip[0]:
            rx, ry = rx0 + 0.010 * k, ry0 + 0.010 * k
        lev.append((z, 0.0, 0.004 * k, rx, ry))
    sk = shell('skirt', lev, sides=16, power=2.2, closed=True)
    solidify(sk, 0.008 * k)
    col = lo.get('color', 'brown')
    wrap = lo.get('wrap')

    def color(c, nrm):
        radial = Vector((c.x, c.y - 0.004 * k, 0))
        if radial.length > 1e-6 and nrm.dot(radial.normalized()) < -0.3:
            return 'inner'
        if c.z < hem + 0.025 * k and lo.get('hem_band'):
            return lo['hem_band']
        if wrap:
            # 巻きスカートの上の布（正面から wrap.from〜wrap.to 度は wrap.color）
            a = math.degrees(math.atan2(c.x, -(c.y - 0.004 * k)))
            if wrap['from'] <= a <= wrap['to']:
                return wrap['color']
        return col
    p.add(sk, 'skirt', color, 'hips', shade=0)


# ---------------------------------------------------------------- 前掛け

def build_apron(p: Person) -> None:
    ap = p.conf.get('apron')
    if not ap:
        return
    b = p.body
    k = b.k
    col = ap.get('color', 'cream')
    kind = ap.get('kind', 'waist')       # waist（腰から膝）・bib（胸当てと肩ひもつき）
    top = b.belt[0] - 0.012 * k
    bot = ap.get('hem', 0.0) * k or (b.knee[0] - 0.02 * k)
    lo = p.conf.get('lower', {})
    skirt = lo.get('kind') == 'skirt'
    half = ap.get('half', 0.75)     # 体の前の幅の割合
    rows = []
    n = 7
    for i in range(n):
        f = i / (n - 1)
        z = bot + (top - bot) * f
        if skirt:
            # スカートの面から 1.2cm 外
            hem = lo.get('hem', 0.0) * k or (b.ankle[0] + 0.06 * k)
            ff = max(0.0, min(1.0, (z - hem) / (b.belt[0] + 0.01 * k - hem)))
            spread = 1 - ff
            rx0, ry0 = b.torso_at(max(z, b.hip[0]))
            ry = max(ry0, b.hip[2]) * (1.0 + 0.50 * lo.get('flare', 1.0) * spread ** 1.2) + 0.026 * k
            rx = max(rx0, b.hip[1]) * (1.0 + 0.42 * lo.get('flare', 1.0) * spread ** 1.2) + 0.026 * k
        else:
            rx0, ry0 = b.torso_at(max(z, b.hem[0]))
            if z < b.belt[0]:
                rx0, ry0 = max(rx0, b.hip[1] * 1.05), max(ry0, b.hip[2] * 1.25)
            if z < b.crotch:
                # 脚の前：脚の前の面より前
                rx0, ry0 = b.hip[1] * 1.15, (b.r_thigh * 1.35 + 0.02 * k)
            rx, ry = rx0 + 0.022 * k, ry0 + 0.024 * k
        rows.append((z, rx, ry))
    bm = bmesh.new()
    cols = 7
    grid = []
    for (z, rx, ry) in rows:
        row = []
        for j in range(cols):
            u = -half + 2 * half * j / (cols - 1)
            a = u * math.pi / 2
            row.append(bm.verts.new((rx * math.sin(a), 0.004 * k - ry * math.cos(a), z)))
        grid.append(row)
    for r0, r1 in zip(grid, grid[1:]):
        for j in range(cols - 1):
            bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
    apron = M._to_object('apron', bm)
    flip_faces_outward(apron, lambda c: Vector((0, 0.004 * k, c.z)))
    solidify(apron, 0.006 * k)
    p.add(apron, 'apron', col, 'hips', shade=0)
    for pk in ap.get('pockets', []):
        s = 1 if pk.get('side', 'L') == 'L' else -1
        zz = bot + (top - bot) * pk.get('z', 0.55)
        z_i = min(range(n), key=lambda i: abs(rows[i][0] - zz))
        _, rx, ry = rows[z_i]
        a = s * half * math.pi / 2 * pk.get('x', 0.5)
        pc = (rx * math.sin(a) + 0.0, 0.004 * k - (ry + 0.008 * k) * math.cos(a), zz)
        p.add(M.rbox('apocket', pc, (pk.get('w', 0.08) * k, 0.008 * k, pk.get('h', 0.08) * k), bevel=0.002 * k,
                     rot=(0, 0, math.degrees(a))), 'apron', pk.get('color', 'sand'), 'hips', shade=0)
    if kind == 'bib':
        rx, ry = b.torso_at(b.chest[0])
        bib = M.rbox('bib', (0, 0.004 * k - ry - 0.012 * k, (b.belt[0] + b.chest[0] + 0.05 * k) / 2),
                     (rx * 1.1, 0.010 * k, b.chest[0] + 0.05 * k - b.belt[0]), bevel=0.003 * k)
        p.add(bib, 'apron', col, ['spine', 'chest'], shade=0)
        for s in (1, -1):
            pts = []
            for i in range(7):
                f = i / 6
                ang = math.pi * f
                xx = s * (rx * 0.45 + 0.02 * k * f)
                zz = b.chest[0] + 0.05 * k + (b.sh_z + 0.02 * k - b.chest[0] - 0.05 * k) * math.sin(ang)
                rr = b.torso_at(min(zz, b.sh_z))[1] + 0.016 * k
                pts.append((xx, 0.004 * k - rr * math.cos(ang), zz))
            p.add(M.loft('bib_strap', pts, [(0.016 * k, 0.004 * k)] * 7, sides=4, ref=(0, 0, 1)), 'apron',
                  ap.get('strap', 'leather'), ['spine', 'chest', 'neck'], shade=0)
    # 腰のひも（横の結び目）
    if ap.get('ties', True):
        for s in (1, -1):
            rx, ry = b.torso_at(b.belt[0])
            p.add(M.rbox('tie', (s * (rx + 0.012 * k), 0.004 * k, b.belt[0] - 0.035 * k), (0.012 * k, 0.020 * k, 0.07 * k),
                         bevel=0.002 * k), 'apron', ap.get('tie', col), 'hips', shade=0)


# ---------------------------------------------------------------- 靴

def build_shoes(p: Person) -> None:
    sh = p.conf.get('shoes', {'kind': 'boots'})
    b = p.body
    k = b.k
    kind = sh.get('kind', 'boots')    # boots（足首の上まで、帯）・low（くるぶしの下まで）
    col = sh.get('color', 'boot')
    toe = sh.get('toe', 'boot_toe')
    sole = sh.get('sole', 'sole')
    fwd, back, hw = b.foot
    for s in (1, -1):
        sx = '.L' if s == 1 else '.R'
        a = b.leg_pt(b.ankle[0], s)
        fx = a.x
        cy = (-fwd + back) / 2
        L = fwd + back
        h_up = (0.125 if kind == 'boots' else 0.075) * k * (b.S / 1.55) ** 0.3
        p.add(M.rbox('sole', (fx, cy, 0.012 * k), (hw * 2.1, L * 1.02, 0.026 * k), bevel=0.006 * k), 'shoes', sole,
              'foot' + sx, shade=0)
        p.add(M.rbox('upper', (fx, cy + L * 0.10, 0.026 * k + h_up * 0.5), (hw * 1.9, L * 0.78, h_up), bevel=0.016 * k,
                     taper=(0.92, 0.80)), 'shoes', col, 'foot' + sx, shade=30)
        p.add(M.rbox('toe_cap', (fx, -fwd + L * 0.20, 0.026 * k + 0.030 * k), (hw * 1.95, L * 0.40, 0.062 * k),
                     bevel=0.020 * k, taper=(0.88, 0.70)), 'shoes', toe, 'foot' + sx, shade=30)
        if kind == 'boots':
            top_z = 0.026 * k + h_up
            cuffc = tube('boot_cuff', [(fx, 0.004 * k, top_z - 0.034 * k), (fx, 0.004 * k, top_z + 0.010 * k)],
                         [(hw * 1.02, hw * 1.08), (hw * 1.02, hw * 1.08)], sides=8)
            p.add(cuffc, 'shoes', sh.get('cuff', col), ['shin' + sx, 'foot' + sx], shade=0)
            if sh.get('strap'):
                p.add(M.rbox('strap', (fx, -L * 0.05, 0.026 * k + h_up * 0.45), (hw * 2.0, 0.030 * k, 0.026 * k),
                             bevel=0.004 * k), 'shoes', sh['strap'], 'foot' + sx, shade=0)


# ---------------------------------------------------------------- 帽子

def build_hat(p: Person) -> None:
    ht = p.conf.get('hat')
    if not ht:
        return
    b = p.body
    k = b.k
    kind = ht['kind']     # wide（つば広）・cap（つばと耳当て）・beret・knit・bonnet・hood
    col = ht.get('color', 'sand')
    band = ht.get('band', 'brown')
    c = b.head_c
    if kind == 'wide':
        base_z = c.z + b.head_rz_top * 0.42
        rx, ry = b.head_rx * 1.08, b.head_ry * 1.08
        crown = shell('crown', [(base_z, 0, c.y, rx, ry), (base_z + 0.06 * k, 0, c.y, rx * 0.98, ry * 0.98),
                                (base_z + 0.11 * k, 0, c.y, rx * 0.84, ry * 0.84)], sides=10, power=2.2, cap_top=True)
        p.add(crown, 'hat', col, 'head', shade=0)
        bandm = shell('hat_band', [(base_z + 0.005 * k, 0, c.y, rx + 0.004 * k, ry + 0.004 * k),
                                   (base_z + 0.040 * k, 0, c.y, rx * 0.99 + 0.004 * k, ry * 0.99 + 0.004 * k)], sides=10, power=2.2)
        p.add(bandm, 'hat', band, 'head', shade=0)
        brim_r = ht.get('brim', 0.15) * k
        lev = [(base_z - 0.030 * k, 0, c.y, rx + brim_r, ry + brim_r), (base_z, 0, c.y, rx + 0.004 * k, ry + 0.004 * k)]
        brim = shell('brim', lev, sides=14, power=2.0)
        flip_faces_outward(brim, lambda cc: Vector((0, c.y, cc.z - 1.0)))
        solidify(brim, 0.010 * k)
        p.add(brim, 'hat', col, 'head', shade=0)
        if ht.get('patch'):
            p.add(M.rbox('hat_patch', (rx * 0.5, c.y - ry * 0.85, base_z + 0.065 * k), (0.035 * k, 0.010 * k, 0.035 * k),
                         rot=(0, 0, -30)), 'hat', ht['patch'], 'head', shade=0)
    elif kind in ('cap', 'knit', 'bonnet', 'beret', 'hood'):
        g = {'cap': 0.022, 'knit': 0.020, 'bonnet': 0.024, 'beret': 0.020, 'hood': 0.030}[kind] * k
        low = {'cap': 30, 'knit': 22, 'bonnet': 25, 'beret': 42, 'hood': -60}[kind]
        dome = M.head_shape('hat', tuple(c + Vector((0, 0.004 * k, 0.010 * k))), rx=b.head_rx + g, ry=b.head_ry + g,
                            rz_top=b.head_rz_top + g * (1.6 if kind != 'beret' else 1.2), rz_bot=b.head_rz_bot + g,
                            segments=14, rings=10, jaw=0.0, chin_fwd=0.0, face_flat=1.0)
        bm = bmesh.new()
        bm.from_mesh(dome.data)
        kill = []
        for f in bm.faces:
            cc = f.calc_center_median() - c
            rz = b.head_rz_top if cc.z >= 0 else b.head_rz_bot
            lat = math.degrees(math.asin(max(-1.0, min(1.0, cc.z / (rz + g)))))
            lon = math.degrees(math.atan2(cc.x, -cc.y))
            lim = low
            if kind == 'hood' and abs(lon) < 55:
                lim = 62
            elif kind == 'cap' and abs(lon) < 50:
                lim = 40
            if lat < lim:
                kill.append(f)
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        if kind == 'beret':
            # 平たく大きく、少し後ろへ傾ける
            for v in bm.verts:
                d = v.co - c
                v.co = c + Vector((d.x * 1.18, d.y * 1.18 + 0.012 * k, d.z * 0.72 + 0.045 * k))
        bm.to_mesh(dome.data)
        bm.free()
        flip_faces_outward(dome, lambda cc: c)
        solidify(dome, 0.008 * k)
        p.add(dome, 'hat', col, 'head', shade=0)
        # 縁の帯
        if kind in ('knit', 'bonnet', 'beret', 'cap'):
            lat0 = math.radians(low + (8 if kind != 'beret' else 0))
            ring = []
            for i in range(14):
                lon = 2 * math.pi * i / 14
                lat = lat0 if kind != 'cap' else math.radians(low + 4 + (8 if abs(math.degrees(lon) % 360 - 0) < 50 or
                                                                          abs(math.degrees(lon) % 360 - 360) < 50 else 0))
                rz = b.head_rz_top + g
                pt = c + Vector(((b.head_rx + g + 0.006 * k) * math.cos(lat) * math.sin(lon),
                                 0.004 * k - (b.head_ry + g + 0.006 * k) * math.cos(lat) * math.cos(lon),
                                 0.010 * k + rz * math.sin(lat)))
                if kind == 'beret':
                    d = pt - c
                    pt = c + Vector((d.x * 1.0, d.y * 1.0, d.z * 0.72 + 0.045 * k))
                ring.append(tuple(pt))
            w = (0.024 if kind == 'knit' else 0.014) * k
            p.add(M.loft('hat_rim', ring, [(w, 0.010 * k)] * 14, sides=4, loop=True, ref=(0, 0, 1)), 'hat',
                  ht.get('band', col), 'head', shade=0)
        if kind == 'cap':
            # 前のつば・耳当て
            vis = head_pt(b, 0, 30, 0.026 * k)
            p.add(M.rbox('visor', tuple(vis + Vector((0, -0.035 * k, -0.004 * k))), (b.head_rx * 1.3, 0.075 * k, 0.012 * k),
                         bevel=0.004 * k, rot=(-12, 0, 0)), 'hat', ht.get('visor', col), 'head', shade=0)
            for s in (1, -1):
                ep = head_pt(b, s * 92, -8, 0.026 * k)
                p.add(M.rbox('flap', tuple(ep), (0.016 * k, 0.070 * k, 0.090 * k), bevel=0.008 * k), 'hat',
                      ht.get('flap', col), 'head', shade=0)
            if ht.get('goggles'):
                for s in (1, -1):
                    gp = head_pt(b, s * 22, 52, 0.032 * k)
                    out = (gp - c).normalized()
                    lens = M.loft('goggle', [tuple(gp - out * 0.012 * k), tuple(gp + out * 0.022 * k)],
                                  [0.034 * k, 0.032 * k], sides=10, ref=(0, 0, 1))
                    p.add(lens, 'hat', ht.get('goggle_frame', 'leather'), 'head', shade=0)
                    p.add(M.loft('glass', [tuple(gp + out * 0.020 * k), tuple(gp + out * 0.026 * k)], [0.026 * k, 0.026 * k],
                                 sides=10, ref=(0, 0, 1)), 'hat', 'lens', 'head', shade=0)
        if kind == 'beret' and ht.get('buckle'):
            bp = head_pt(b, 40, 48, 0.030 * k) + Vector((0, 0, 0.010 * k))
            p.add(M.rbox('beret_buckle', tuple(bp), (0.030 * k, 0.010 * k, 0.034 * k), bevel=0.003 * k, rot=(0, 0, 40)),
                  'hat', ht['buckle'], 'head', shade=0)
        if kind == 'knit' and ht.get('patch'):
            pp = head_pt(b, -30, 45, 0.032 * k)
            p.add(M.rbox('knit_patch', tuple(pp), (0.036 * k, 0.010 * k, 0.034 * k), rot=(0, 0, 30)), 'hat', ht['patch'],
                  'head', shade=0)


# ---------------------------------------------------------------- つぎあて（服の上に置く小さな板）

def build_patches(p: Person, bvh: BVHTree) -> None:
    b = p.body
    k = b.k
    for pt in p.conf.get('patches', []):
        where = pt.get('on', 'body')       # body（胴の軸）・leg_L・leg_R・arm_L・arm_R
        z = pt['z'] * k
        a = math.radians(pt.get('a', 0))
        if where.startswith('leg'):
            s = 1 if where.endswith('L') else -1
            ax = b.leg_pt(z, s)
            bones = p.leg_bones(s)[:3]
        elif where.startswith('arm'):
            s = 1 if where.endswith('L') else -1
            ax = b.arm_pt(z, s)
            bones = p.arm_bones(s)
        else:
            ax = Vector((0, 0.004 * k, z))
            bones = ['hips', 'spine', 'chest']
        d = Vector((math.sin(a), -math.cos(a), 0))
        hit = bvh.ray_cast(ax + d * 1.0, -d, 2.0)
        if hit[0] is None:
            continue
        loc, nrm = hit[0], hit[1]
        q = Vector((0, -1, 0)).rotation_difference(nrm)
        w, h = pt.get('w', 0.07) * k, pt.get('h', 0.07) * k
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * w, v.co.y * 0.004 * k, v.co.z * h))
        rot = pt.get('rot', 0)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(rot), 3, 'Y'))
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=q.to_matrix())
        bmesh.ops.translate(bm, verts=bm.verts, vec=loc + nrm * 0.002 * k)
        o = M._to_object('patch', bm)
        p.add(o, 'patches', pt.get('color', 'patch'), bones, shade=0)


# ---------------------------------------------------------------- 組み立て・材質・動作・書き出し

def make_material(p: Person, face: dict) -> bpy.types.Material:
    T.write_texture(p.tex_path, face)
    mat = bpy.data.materials.new(f'tf_{p.id}')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.88
    bsdf.inputs['Metallic'].default_value = 0.0
    tex = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(p.tex_path)
    img.name = f'tf_{p.id}'
    tex.image = img
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def build_person(conf: dict) -> tuple[Person, dict]:
    C.reset_scene()
    p = Person(conf)
    face = face_params(p)
    build_head(p)
    build_hair(p)
    build_beard(p)
    build_top(p)
    build_lower(p)
    build_shoes(p)
    build_belt(p)
    build_apron(p)
    build_jacket(p)
    build_poncho(p)
    build_scarf(p)
    build_hat(p)
    # つぎあては組んだ服の面に置く
    if p.conf.get('patches'):
        bm = bmesh.new()
        for o in p.parts:
            me = o.data
            bm2 = bmesh.new()
            bm2.from_mesh(me)
            bm2.transform(o.matrix_world)
            tmpme = bpy.data.meshes.new('tmp')
            bm2.to_mesh(tmpme)
            bm2.free()
            bm.from_mesh(tmpme)
            bpy.data.meshes.remove(tmpme)
        bvh = BVHTree.FromBMesh(bm)
        build_patches(p, bvh)
        bm.free()
    p.mat = make_material(p, face)
    for o in p.parts:
        o.data.materials.clear()
        o.data.materials.append(p.mat)
    body = C.join(p.parts, f'TF_{p.id}')
    # 同じ位置の点をつなぐ（部品ごとの継ぎ目は残す。三角形の数は変わらない）
    H.finalize_skin(body, p.arm)
    clips_kind = conf.get('clips', p.body.clips)
    fwd, back, _ = p.body.foot
    contacts = ((0.0, -(fwd - 0.01 * p.body.k), -p.body.ankle[0]), (0.0, back - 0.01 * p.body.k, -p.body.ankle[0]))
    if clips_kind == 'child':
        from models import child_anims
        H.bake_clips(p.arm, child_anims.all_clips(), contacts)
    else:
        from models import townsfolk_anims
        H.bake_clips(p.arm, townsfolk_anims.all_clips(clips_kind, conf.get('pose', {})), contacts)
    stats = dict(sorted(p.stats.items()))
    stats['total_tris'] = M.tri_count(body)
    stats['vertices'] = len(body.data.vertices)
    stats['materials'] = [m.name for m in body.data.materials if m]
    stats['body'] = p.body.kind
    stats['height_m'] = round(p.body.S, 3)
    stats['clips'] = [t.name for t in p.arm.animation_data.nla_tracks]
    return p, stats


def load_conf(pid: str) -> dict:
    with open(os.path.join(CONF_DIR, f'{pid}.json'), encoding='utf-8') as f:
        return json.load(f)


def render(prefix: str, p: Person) -> None:
    S = p.body.S
    C.render_views(prefix, (0, 0, S / 2 + 0.03), S * 1.05, views={'front': 0, 'side': 90, 'back': 180, 'three_quarter': 35},
                   size=520)


def main() -> None:
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--person', action='append', default=[])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--out-dir', default=OUT_DIR)
    ap.add_argument('--render', default=None, help='確認の画像の接頭辞のフォルダ（Cycles、4 方向）')
    args = ap.parse_args(argv)
    ids = args.person
    if args.all:
        ids = sorted(os.path.splitext(f)[0] for f in os.listdir(CONF_DIR) if f.endswith('.json'))
    os.makedirs(os.path.join(BUILD_DIR, 'stats'), exist_ok=True)
    for pid in ids:
        conf = load_conf(pid)
        p, stats = build_person(conf)
        out = os.path.join(args.out_dir, f'tf_{pid}.glb')
        C.export_glb(out)
        with open(os.path.join(BUILD_DIR, 'stats', f'tf_{pid}.json'), 'w') as f:
            json.dump(stats, f, indent=1, ensure_ascii=False)
        if args.render:
            os.makedirs(args.render, exist_ok=True)
            render(os.path.join(args.render, f'tf_{pid}'), p)
        print(json.dumps({'id': pid, **{k: v for k, v in stats.items() if k in ('total_tris', 'materials', 'clips', 'height_m')}},
                         ensure_ascii=False), flush=True)
        print('wrote', out, flush=True)


if __name__ == '__main__':
    main()
