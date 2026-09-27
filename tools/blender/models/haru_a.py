"""ハル：W0 A案の 3D 試作（ハル 1 体だけの検証用）。

基準：art/concepts/W0_art_bible/artbible_a_lineup_r3.png（origin/art/w0）と spec_a.md。
仮に決めたこと（P-1〜P-11）は docs/art_orders/W0_受領と検証計画.md。

- 4.5 頭身（身長 1.55m）。頭を大きく、手足を短く
- 左右は本人基準。右手に別体の小型銃、左前腕に琥珀の光刃の籠手
- 輪郭線なし。面の向きで明暗を作る（服と髪は角を立て、顔と肌はなめらか）
- 色は色見本テクスチャ 1 枚、顔は表情 4 種のテクスチャ（切り替え可能）
- 関節の近くは 2 本の骨が混ざる重みで、なめらかに曲がる

  python tools/blender/models/haru_a.py [--render]
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

from lib import common as C  # noqa: E402
from lib import humanoid as H  # noqa: E402
from lib import mesh as M  # noqa: E402
from models import haru_a_textures as T  # noqa: E402
from models import humanoid_anims as A  # noqa: E402

HEIGHT = 1.55

# 4.5 頭身の関節（身長 1.0 に正規化）。骨の名前と構成は標準の人型と同じ
JOINTS_HARU = {
    'root': (0, 0, 0),
    'hips': (0, 0, 0.470),
    'spine': (0, 0, 0.545),
    'chest': (0, 0, 0.620),
    'neck': (0, 0, 0.728),
    'head': (0, 0.003, 0.758),
    'head_end': (0, 0, 1.0),
    'shoulder': (0.030, 0, 0.715),
    'upper_arm': (0.105, 0, 0.715),
    'forearm': (0.122, 0.006, 0.575),
    'hand': (0.138, 0, 0.455),
    'hand_end': (0.142, -0.004, 0.405),
    'thigh': (0.057, 0, 0.455),
    'shin': (0.062, 0, 0.255),
    'foot': (0.062, 0.012, 0.058),
    'toe': (0.062, -0.070, 0.012),
}

PAL = M.Palette(T.PALETTE, T.CELLS)
BELT_Z = 0.862  # ベルトの高さ（絵では身長の約 55%）

# 顔のテクスチャに投影する範囲（haru_a_textures と同じ）
FACE_X0, FACE_X1, FACE_Z0, FACE_Z1 = T.X0, T.X1, T.Z0, T.Z1
# 頭は「基準の頭」（中心 z=1.375、幅 0.128）で形を決め、HEAD_K 倍して置く（顔のテクスチャと同じ変換）
HEAD_K = T.HEAD_K
HEAD_C = (0.0, 0.005, T.HEAD_Z)


def HS(p) -> Vector:
    """基準の頭の座標 → 試作の頭の座標"""
    return Vector((p[0] * HEAD_K, HEAD_C[1] + (p[1] - 0.005) * HEAD_K, HEAD_C[2] + (p[2] - 1.375) * HEAD_K))


def J(name: str, side: int = 1) -> Vector:
    return Vector(H.joint(name, HEIGHT, side, JOINTS_HARU))


def lerp(a: Vector, b: Vector, t: float) -> Vector:
    return a + (b - a) * t


class Builder:
    def __init__(self, arm: bpy.types.Object, body_mat, face_mat):
        self.arm = arm
        self.body_mat = body_mat
        self.face_mat = face_mat
        self.parts: list[bpy.types.Object] = []
        self.stats: dict[str, int] = {}

    def add(self, obj, group: str, color, weights, shade: float | None = 30.0):
        """color：色の名前か関数。weights：骨の名前（剛体）か候補の骨のリスト（距離で自動）"""
        obj.data.materials.append(self.body_mat)
        M.paint(obj, PAL, color)
        if isinstance(weights, str):
            M.weight_rigid(obj, weights)
        else:
            M.weight_auto(obj, self.arm, weights)
        M.smooth(obj, shade)
        self.stats[group] = self.stats.get(group, 0) + M.tri_count(obj)
        self.parts.append(obj)
        return obj


def make_materials(tex_dir: str):
    pal_path, emit_path = T.write_palette(tex_dir)
    face_path = T.write_face(tex_dir)

    def textured(name: str, base: str, emit: str | None):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes['Principled BSDF']
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Metallic'].default_value = 0.0
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(base)
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if emit:
            et = nt.nodes.new('ShaderNodeTexImage')
            et.image = bpy.data.images.load(emit)
            nt.links.new(et.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = 2.0
        return mat

    body = textured('haru_body', pal_path, emit_path)
    face = textured('haru_face', face_path, None)
    blade = bpy.data.materials.new('haru_blade')
    blade.use_nodes = True
    b = blade.node_tree.nodes['Principled BSDF']
    amber = C.hex_color('#FFBC52')
    b.inputs['Base Color'].default_value = (*amber, 1)
    b.inputs['Emission Color'].default_value = (*amber, 1)
    b.inputs['Emission Strength'].default_value = 3.0
    b.inputs['Alpha'].default_value = 0.85
    blade.surface_render_method = 'BLENDED'
    return body, face, blade


# ---------------------------------------------------------------- 部品

TORSO = ['hips', 'spine', 'chest', 'neck']


def build_head(b: Builder) -> None:
    k = HEAD_K
    head = M.head_shape('head', HEAD_C, rx=0.128 * k, ry=0.128 * k, rz_top=0.14 * k, rz_bot=0.155 * k, segments=20,
                        rings=12, jaw=0.48, chin_fwd=0.012 * k, face_flat=0.9)
    b.add(head, 'head', 'skin', 'head', shade=None)
    # 顔の面：顔用の材質にして、正面から平らに投影する
    head.data.materials.append(b.face_mat)
    me = head.data
    uvl = me.uv_layers[0].data
    for p in me.polygons:
        c, n = p.center, p.normal
        if c.y < -0.05 and FACE_Z0 + 0.005 < c.z < FACE_Z1 - 0.005 and abs(c.x) < 0.118 and n.y < -0.25:
            p.material_index = 1
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                u = (co.x - FACE_X0) / (FACE_X1 - FACE_X0) * 0.5
                v = 0.5 + (co.z - FACE_Z0) / (FACE_Z1 - FACE_Z0) * 0.5
                uvl[li].uv = (min(0.5, max(0.0, u)), min(1.0, max(0.5, v)))
    # 首
    neck = M.loft('neck', [(0, 0.004, 1.100), (0, 0.008, 1.150), (0, 0.012, 1.215)], [0.048, 0.045, 0.043], sides=10)
    b.add(neck, 'head', 'skin', ['chest', 'neck', 'head'], shade=None)


def build_hair(b: Builder) -> None:
    import bmesh
    k = HEAD_K
    cap = M.head_shape('hair_cap', HS((0, 0.012, 1.39)), rx=0.141 * k, ry=0.144 * k, rz_top=0.142 * k,
                       rz_bot=0.142 * k, segments=16, rings=10, jaw=0.0, chin_fwd=0.0, face_flat=1.0)
    bm = bmesh.new()
    bm.from_mesh(cap.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        o = Vector((c.x / k, (c.y - HEAD_C[1]) / k + 0.005, (c.z - HEAD_C[2]) / k + 1.375))  # 基準の頭の座標
        if o.z < 1.235 or (o.y < -0.05 and o.z < 1.455 and abs(o.x) < 0.108) or (o.y < -0.02 and o.z < 1.30):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(cap.data)
    bm.free()
    b.add(cap, 'hair', 'hair', 'head', shade=0)

    # (根元, 曲がりの制御点, 先端, 幅, 厚み)。房は大きく、数は少なく
    locks = [
        # 前髪：中央で分けて、額に下ろす
        ((0.020, -0.118, 1.485), (0.034, -0.150, 1.435), (0.046, -0.146, 1.362), 0.030, 0.016),
        ((-0.024, -0.118, 1.485), (-0.036, -0.150, 1.432), (-0.018, -0.146, 1.358), 0.030, 0.016),
        ((0.072, -0.108, 1.470), (0.094, -0.132, 1.420), (0.104, -0.118, 1.345), 0.030, 0.016),
        ((-0.076, -0.108, 1.470), (-0.098, -0.132, 1.418), (-0.106, -0.114, 1.338), 0.030, 0.016),
        # 横：耳を隠す
        ((0.122, -0.040, 1.405), (0.148, -0.052, 1.330), (0.132, -0.060, 1.262), 0.030, 0.020),
        ((-0.122, -0.040, 1.405), (-0.148, -0.052, 1.330), (-0.132, -0.060, 1.262), 0.030, 0.020),
        ((0.126, 0.030, 1.400), (0.152, 0.040, 1.320), (0.140, 0.050, 1.250), 0.032, 0.022),
        ((-0.126, 0.030, 1.400), (-0.152, 0.040, 1.320), (-0.140, 0.050, 1.250), 0.032, 0.022),
        # もみあげ
        ((0.116, -0.072, 1.405), (0.126, -0.086, 1.340), (0.118, -0.090, 1.282), 0.022, 0.012),
        ((-0.116, -0.072, 1.405), (-0.126, -0.086, 1.340), (-0.118, -0.090, 1.282), 0.022, 0.012),
        # 上：はねる房
        ((0.000, -0.030, 1.515), (0.000, -0.015, 1.550), (0.012, 0.030, 1.565), 0.042, 0.034),
        ((0.060, -0.020, 1.505), (0.100, -0.010, 1.535), (0.152, 0.000, 1.520), 0.038, 0.028),
        ((-0.060, -0.020, 1.505), (-0.100, -0.010, 1.535), (-0.156, 0.000, 1.512), 0.038, 0.028),
        ((0.090, 0.020, 1.470), (0.140, 0.030, 1.475), (0.182, 0.030, 1.432), 0.034, 0.026),
        ((-0.090, 0.020, 1.470), (-0.140, 0.030, 1.475), (-0.186, 0.030, 1.422), 0.034, 0.026),
        ((0.000, 0.070, 1.490), (0.000, 0.120, 1.505), (0.000, 0.172, 1.470), 0.042, 0.030),
        ((0.030, -0.080, 1.505), (0.050, -0.125, 1.532), (0.070, -0.155, 1.520), 0.032, 0.026),
        # 後ろ：襟足へ
        ((0.060, 0.110, 1.380), (0.082, 0.150, 1.320), (0.062, 0.142, 1.250), 0.036, 0.024),
        ((-0.060, 0.110, 1.380), (-0.082, 0.150, 1.320), (-0.062, 0.142, 1.250), 0.036, 0.024),
        ((0.000, 0.130, 1.380), (0.000, 0.162, 1.310), (0.000, 0.132, 1.238), 0.040, 0.024),
    ]
    for i, (base, ctrl, tip, w, d) in enumerate(locks):
        # 房の平たい面を頭の表面に沿わせる：厚みの向きを頭の中心から外へ
        out = (Vector(base) - Vector((0, 0.005, 1.375))).normalized()
        o = M.lock(f'lock{i}', HS(base), HS(ctrl), HS(tip), w * k, d * k, sides=4, segments=3, ref=tuple(out))
        b.add(o, 'hair', 'hair', 'head', shade=0)


def build_goggles(b: Builder) -> None:
    """額に上げたゴーグル（P-8）。帯は髪の表面に沿って後頭部へ回る"""
    k = HEAD_K
    cc = HS((0, 0.012, 1.39))
    rx, ry, rz = 0.141 * k, 0.144 * k, 0.142 * k

    def surface(ph: float, z: float, gap: float) -> tuple[float, float, float]:
        f = math.sqrt(max(0.0, 1 - ((z - cc.z) / rz) ** 2))
        return (math.sin(ph) * (rx * f + gap), cc.y - math.cos(ph) * (ry * f + gap), z)

    path = []
    for i in range(16):
        ph = 2 * math.pi * i / 16
        z = 1.458 - 0.075 * (1 - math.cos(ph)) / 2
        path.append(surface(ph, z, 0.0))
    strap = M.loft('goggle_strap', path, [(0.006, 0.014)] * 16, sides=4, loop=True, ref=(0, 0, 1),
                   angle0=math.pi / 4)
    b.add(strap, 'goggles', 'frame', 'head', shade=0)
    for s in (1, -1):
        ph = s * 0.40
        c = Vector(surface(ph, 1.462, 0.024))
        rot = (-24, 0, math.degrees(ph))
        e = Euler(tuple(math.radians(a) for a in rot), 'XYZ')
        fwd = Vector((0, -1, 0))
        fwd.rotate(e)
        b.add(M.rbox('goggle_frame', c, (0.082, 0.040, 0.058), bevel=0.011, rot=rot), 'goggles', 'frame', 'head',
              shade=0)
        b.add(M.rbox('goggle_lens', c + fwd * 0.018, (0.066, 0.008, 0.044), bevel=0.006, rot=rot), 'goggles',
              'amber_dim', 'head', shade=0)
    b.add(M.rbox('goggle_bridge', surface(0, 1.462, 0.020), (0.036, 0.022, 0.018), bevel=0.004, rot=(-24, 0, 0)),
          'goggles', 'frame', 'head', shade=0)


def build_torso(b: Builder) -> None:
    rings = [  # (z, 横, 前後, 前へのずれ)。ベルトから下はズボン（腰の高いズボン）
        (0.655, 0.105, 0.078, 0.0),
        (0.710, 0.130, 0.089, 0.0),
        (0.790, 0.130, 0.090, 0.0),
        (0.860, 0.122, 0.085, 0.0),
        (0.905, 0.122, 0.082, -0.002),
        (0.950, 0.131, 0.085, -0.006),
        (1.030, 0.139, 0.086, -0.004),
        (1.090, 0.133, 0.080, 0.0),
        (1.125, 0.098, 0.066, 0.004),
        (1.150, 0.052, 0.046, 0.006),
    ]
    torso = M.loft('torso', [(0, y, z) for z, _, _, y in rings], [(rx, ry) for _, rx, ry, _ in rings], sides=12,
                   ref=(0, -1, 0))

    def color(c: Vector, n: Vector) -> str:
        if c.z < BELT_Z:
            return 'brick'
        if abs(c.x) < 0.052 and n.y < -0.5 and c.z < 1.11:
            return 'shirt'
        return 'brick'
    b.add(torso, 'torso', color, TORSO, shade=30)

    # 上着の前の縁（開いた上着の厚み）
    for s in (1, -1):
        lap = M.loft('lapel', [(s * 0.057, -0.084, BELT_Z + 0.02), (s * 0.057, -0.090, 0.95), (s * 0.066, -0.084, 1.07),
                               (s * 0.078, -0.060, 1.125)], [(0.013, 0.007)] * 4, sides=4, ref=(0, -1, 0))
        b.add(lap, 'torso', 'brick', TORSO, shade=0)
    # 襟（フードを畳んだような太い襟。前は開く）
    path = []
    for k in range(10):
        ph = math.radians(42 + (360 - 84) * k / 9)
        path.append((math.sin(ph) * 0.080, -math.cos(ph) * 0.064 + 0.008, 1.135 + 0.022 * (1 - math.cos(ph)) / 2))
    collar = M.loft('collar', path, [(0.026, 0.020)] * 10, sides=6, ref=(0, 0, 1))
    b.add(collar, 'torso', 'brick', TORSO, shade=35)
    # 帯：肩から背中で X 字に交差する（P-6）
    for s in (1, -1):
        pts = [(s * 0.074, -0.089, BELT_Z + 0.02), (s * 0.077, -0.093, 0.950), (s * 0.080, -0.085, 1.060),
               (s * 0.086, -0.036, 1.137), (s * 0.082, 0.044, 1.118), (s * 0.052, 0.090, 1.020),
               (s * 0.000, 0.093, 0.935), (-s * 0.064, 0.090, BELT_Z + 0.02)]
        strap = M.loft('strap', pts, [(0.016, 0.006)] * len(pts), sides=4, ref=(0, -1, 0))
        # 帯の平たい面を体の表面へ向ける：前後の向きを外向きに
        b.add(strap, 'straps', 'frame', TORSO, shade=0)
    # ベルト、バックル、ポーチ
    belt = M.loft('belt', [(0, 0, BELT_Z - 0.019), (0, 0, BELT_Z + 0.019)], [(0.128, 0.090), (0.126, 0.088)], sides=12,
                  cap_start=False, cap_end=False)
    b.add(belt, 'belt', 'hair', TORSO, shade=30)
    b.add(M.rbox('buckle', (0, -0.092, BELT_Z), (0.056, 0.012, 0.040), bevel=0.004), 'belt', 'brass', 'spine', shade=0)
    b.add(M.rbox('buckle_in', (0, -0.098, BELT_Z), (0.032, 0.004, 0.020)), 'belt', 'frame', 'spine', shade=0)
    b.add(M.rbox('pouch', (0.126, -0.028, BELT_Z - 0.050), (0.040, 0.076, 0.086), bevel=0.010), 'belt', 'hair', 'hips',
          shade=0)


def build_arm(b: Builder, s: int) -> None:
    sx = '.L' if s == 1 else '.R'
    ua, fa, hd, he = J('upper_arm', s), J('forearm', s), J('hand', s), J('hand_end', s)
    bones = ['chest', 'shoulder' + sx, 'upper_arm' + sx, 'forearm' + sx, 'hand' + sx]
    inner = ua + Vector((-s * 0.018, 0, 0.012))
    skin = M.loft('arm', [inner, lerp(ua, fa, 0.5), fa, lerp(fa, hd, 0.5), hd],
                  [0.047, 0.044, 0.040, 0.040, 0.034], sides=8)
    b.add(skin, 'arms', 'skin', bones, shade=None)
    # 半袖（肩を包む）。袖口の面は暗い色
    top = ua + Vector((-s * 0.024, 0, 0.036))
    sleeve = M.loft('sleeve', [top, ua + Vector((0, 0, 0.004)), lerp(ua, fa, 0.46)],
                    [(0.054, 0.058), (0.070, 0.073), (0.064, 0.067)], sides=8)
    down = (fa - ua).normalized()
    b.add(sleeve, 'arms', lambda c, n: 'brick_dark' if n.dot(down) > 0.8 else 'brick', bones[:3], shade=30)
    band = M.loft('arm_band', [lerp(ua, fa, 0.55), lerp(ua, fa, 0.68)], [0.047, 0.045], sides=8)
    b.add(band, 'arms', 'frame', bones[1:4], shade=30)
    # 手：手袋（指なし）の甲と、指をまとめた塊、親指
    mid = lerp(hd, he, 0.45)
    b.add(M.rbox('hand', mid + Vector((0, 0, 0.004)), (0.046, 0.080, 0.074), bevel=0.013), 'hands', 'glove',
          'hand' + sx, shade=30)
    b.add(M.rbox('fingers', he + Vector((-s * 0.008, -0.002, -0.010)), (0.048, 0.078, 0.050), bevel=0.014,
                 rot=(0, 0, 0)), 'hands', 'skin', 'hand' + sx, shade=40)
    b.add(M.rbox('thumb', mid + Vector((-s * 0.024, -0.042, -0.012)), (0.026, 0.028, 0.050), bevel=0.008,
                 rot=(12, 0, 0)), 'hands', 'skin', 'hand' + sx, shade=40)
    if s == -1:
        # 右：手首の帯と、別体の小型銃（P-5）
        b.add(M.loft('wrist_band', [lerp(fa, hd, 0.80), lerp(fa, hd, 1.0)], [0.040, 0.039], sides=8), 'hands', 'glove',
              ['forearm.R', 'hand.R'], shade=30)
        build_gun(b, lerp(hd, he, 0.55))
    else:
        build_gauntlet(b, fa, hd)
        # 右肩にだけ板がある（P-2）ので、左肩は何もなし


def build_gun(b: Builder, fist: Vector) -> None:
    """右手の銃。腕を下ろした姿勢で、銃口は下、銃の上面は前を向く（腕を前に伸ばすと上面が上になる）"""
    x = fist.x
    y0 = -0.064  # 銃身の線（拳の前）
    parts = [
        ('gun_slide', (x, y0, 0.575), (0.046, 0.062, 0.250), 0.008, 'frame'),
        ('gun_muzzle', (x, y0, 0.444), (0.038, 0.052, 0.022), 0.005, 'brass'),
        ('gun_grip', (x, -0.018, 0.664), (0.036, 0.090, 0.042), 0.008, 'frame'),
        ('gun_cell', (x, y0 - 0.0315, 0.600), (0.020, 0.005, 0.080), 0.0, 'amber'),
        ('gun_cell_side', (x - 0.0235, y0, 0.585), (0.005, 0.030, 0.080), 0.0, 'amber'),
        ('gun_rear', (x, y0, 0.703), (0.042, 0.054, 0.018), 0.005, 'brass'),
    ]
    for name, c, size, bev, col in parts:
        b.add(M.rbox(name, c, size, bevel=bev), 'gun', col, 'hand.R', shade=0)
    muzzle = C.empty('muzzle', (x, y0, 0.430))
    M.parent_to_bone(muzzle, b.arm, 'hand.R')


def build_gauntlet(b: Builder, fa: Vector, hd: Vector) -> None:
    """左前腕の籠手と光刃（P-4）。刃は手首の外側から前腕に沿って、拳の先へ約 45cm 伸びる"""
    bones = ['upper_arm.L', 'forearm.L', 'hand.L']
    g = M.loft('gauntlet', [lerp(fa, hd, 0.2), lerp(fa, hd, 0.55), lerp(fa, hd, 0.93)],
               [(0.054, 0.055), (0.055, 0.056), (0.050, 0.052)], sides=8)
    b.add(g, 'gauntlet', 'shell', 'forearm.L', shade=0)
    b.add(M.loft('elbow_cap', [lerp(fa, hd, -0.07), lerp(fa, hd, 0.19)], [0.048, 0.049], sides=8), 'gauntlet', 'frame',
          bones[:2], shade=30)
    b.add(M.loft('wrist_cuff', [lerp(fa, hd, 0.92), lerp(fa, hd, 1.02)], [0.044, 0.042], sides=8), 'gauntlet', 'frame',
          'forearm.L', shade=30)
    axis = (hd - fa).normalized()
    emit_c = lerp(fa, hd, 0.78) + Vector((0.055, 0, 0))
    b.add(M.rbox('emitter', emit_c, (0.020, 0.032, 0.080), bevel=0.005), 'gauntlet', 'frame', 'forearm.L', shade=0)
    b.add(M.rbox('emitter_slit', emit_c + Vector((0.0105, 0, -0.008)), (0.003, 0.012, 0.050)), 'gauntlet', 'amber',
          'forearm.L', shade=0)
    base = hd + Vector((0.060, 0, 0.02))
    sock = C.empty('blade_socket', base)
    # 目印の +Y を刃の向き（前腕の向き）に合わせる
    sock.rotation_mode = 'QUATERNION'
    sock.rotation_quaternion = Vector((0, 1, 0)).rotation_difference(axis)
    M.parent_to_bone(sock, b.arm, 'forearm.L')
    # 刃：ひし形の断面で先がとがる。ゲームでは斬るときだけ表示する
    # 原点を刃の根元に置く（ゲームで溜め中に縮めるとき、根元を中心に縮むように）
    blade = M.loft('LightBlade', [Vector((0, 0, 0)), axis * 0.08, axis * 0.36, axis * 0.45],
                   [(0.010, 0.018), (0.012, 0.026), (0.010, 0.022), 0.0], sides=4, angle0=0.0, ref=(0, -1, 0))
    blade.location = base
    blade.data.materials.append(b.blade_mat)  # type: ignore[attr-defined]
    M.smooth(blade, 0)
    b.stats['blade'] = M.tri_count(blade)
    M.parent_to_bone(blade, b.arm, 'forearm.L')


def build_shoulder_plate(b: Builder) -> None:
    """右肩の板（P-2）。肩の骨に付け、腕を上げても肩の上に残る"""
    ua = J('upper_arm', -1)
    b.add(M.rbox('shoulder_plate', ua + Vector((-0.022, 0.0, 0.046)), (0.130, 0.158, 0.060), bevel=0.022,
                 rot=(0, -22, 0), taper=(0.8, 0.85)), 'plates', 'shell', 'shoulder.R', shade=0)
    b.add(M.rbox('shoulder_plate_under', ua + Vector((-0.020, 0.0, 0.020)), (0.124, 0.150, 0.020), bevel=0.006,
                 rot=(0, -22, 0)), 'plates', 'frame', 'shoulder.R', shade=0)


def build_leg(b: Builder, s: int) -> None:
    sx = '.L' if s == 1 else '.R'
    th, sh, ft = J('thigh', s), J('shin', s), J('foot', s)
    leg_bones = ['hips', 'thigh' + sx, 'shin' + sx]
    rings = [  # (z, 中心の x, 半径)
        (0.765, 0.072, (0.080, 0.084)),
        (0.665, 0.090, (0.095, 0.097)),
        (0.555, 0.095, (0.097, 0.099)),
        (0.465, 0.096, (0.090, 0.092)),
        (0.415, 0.096, (0.074, 0.077)),
        (0.385, 0.096, (0.056, 0.059)),
    ]
    pants = M.loft('pants', [(s * x, 0, z) for z, x, _ in rings], [r for _, _, r in rings], sides=10)
    b.add(pants, 'legs', 'brick', leg_bones, shade=30)
    X = s * 0.096
    lower = M.loft('shin_cloth', [(X, 0.004, 0.405), (X, 0.006, 0.32), (X, 0.008, 0.17), (X, 0.012, 0.11)],
                   [0.050, 0.052, 0.046, 0.044], sides=8)
    b.add(lower, 'legs', 'leg', ['thigh' + sx, 'shin' + sx, 'foot' + sx], shade=30)
    # 膝当てと、両側の琥珀のレンズ（P-3）
    b.add(M.rbox('knee_pad', (X, -0.050, 0.392), (0.100, 0.058, 0.120), bevel=0.019, rot=(-6, 0, 0)), 'plates',
          'shell', 'shin' + sx, shade=0)
    for side in (1, -1):
        c = Vector((X + side * 0.054, -0.014, 0.398))
        b.add(M.cyl('knee_joint', c, 0.027, 0.020, axis=(1, 0, 0), sides=8), 'plates', 'frame', 'shin' + sx, shade=30)
        b.add(M.cyl('knee_lens', c + Vector((side * 0.011, 0, 0)), 0.017, 0.006, axis=(1, 0, 0), sides=8), 'plates',
              'amber', 'shin' + sx, shade=0)
    # すねの部分フレーム：外側の支柱と、ふくらはぎの板
    b.add(M.rbox('shin_strut', (X + s * 0.050, 0.004, 0.255), (0.018, 0.038, 0.200), bevel=0.005), 'plates', 'frame',
          'shin' + sx, shade=0)
    b.add(M.rbox('calf_plate', (X, 0.046, 0.250), (0.078, 0.030, 0.150), bevel=0.011), 'plates', 'shell',
          'shin' + sx, shade=0)
    # 右の太ももの板（P-2）：ベルトから下がる大きな板
    if s == -1:
        b.add(M.rbox('thigh_plate', (-0.110, -0.092, 0.700), (0.100, 0.032, 0.210), bevel=0.015, rot=(6, 0, 8)),
              'plates', 'shell', 'thigh.R', shade=0)
    # 靴：底、甲、つま先の覆い、足首の折り返し（大きく厚い靴）
    fx = X
    b.add(M.rbox('sole', (fx, -0.034, 0.020), (0.124, 0.250, 0.040), bevel=0.010), 'boots', 'frame', 'foot' + sx,
          shade=0)
    b.add(M.rbox('boot', (fx, 0.004, 0.084), (0.118, 0.168, 0.104), bevel=0.018, taper=(0.9, 0.85)), 'boots', 'boot',
          'foot' + sx, shade=30)
    b.add(M.rbox('toe_cap', (fx, -0.100, 0.064), (0.120, 0.100, 0.070), bevel=0.021, taper=(0.9, 0.75)), 'boots',
          'shell', 'foot' + sx, shade=30)
    cuff = M.loft('boot_cuff', [(fx, 0.008, 0.112), (fx, 0.010, 0.162)], [(0.064, 0.068), (0.062, 0.066)], sides=8)
    b.add(cuff, 'boots', 'brick', ['shin' + sx, 'foot' + sx], shade=30)


def build() -> dict:
    C.reset_scene()
    arm = H.build_armature(HEIGHT, 'HaruRig', JOINTS_HARU)
    tex_dir = tempfile.mkdtemp(prefix='haru_a_tex_')
    body_mat, face_mat, blade_mat = make_materials(tex_dir)
    b = Builder(arm, body_mat, face_mat)
    b.blade_mat = blade_mat  # type: ignore[attr-defined]

    build_head(b)
    build_hair(b)
    build_goggles(b)
    build_torso(b)
    for s in (1, -1):
        build_arm(b, s)
        build_leg(b, s)
    build_shoulder_plate(b)

    body = C.join(b.parts, 'Haru')
    H.finalize_skin(body, arm)
    H.bake_clips(arm, A.all_clips())
    stats = dict(sorted(b.stats.items()))
    stats['total_body'] = M.tri_count(body)
    stats['total_with_blade'] = stats['total_body'] + stats.get('blade', 0)
    stats['vertices_body'] = len(body.data.vertices)
    stats['materials'] = [m.name for m in body.data.materials] + ['haru_blade']
    return stats


def render_checks(out_prefix: str) -> None:
    C.render_views(out_prefix, (0, 0, HEIGHT / 2), HEIGHT,
                   views={'front': 0, 'side': 90, 'back': 180, 'three_quarter': 35}, size=640)
    C.render_views(out_prefix + '_upper', (0, 0, 0.98), 0.62,
                   views={'front': 0, 'side': 90, 'back': 180, 'three_quarter': 35}, size=480)
    C.render_views(out_prefix + '_head', (0, 0, 1.37), 0.36,
                   views={'front': 0, 'side': 90, 'back': 180, 'three_quarter': 30}, size=480)


if __name__ == '__main__':
    stats = build()
    out = os.path.join(C.REPO, 'public', 'assets', 'models', 'haru_a.glb')
    C.export_glb(out)
    with open(os.path.join(C.REPO, 'public', 'assets', 'models', 'haru_a.stats.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    if '--render' in sys.argv:
        prefix = os.environ.get('RENDER_PREFIX', os.path.join(C.REPO, 'art', 'renders', 'haru_a'))
        render_checks(prefix)
    print(json.dumps(stats, ensure_ascii=False))
    print('wrote', out)
