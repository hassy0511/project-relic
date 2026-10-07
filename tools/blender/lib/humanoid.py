"""標準の人型の骨と、アニメーションの補助。

すべての人型キャラクターは同じ骨の名前と構成を使い、アニメーションを使い回す。
骨の名前（three.js 側もこの名前で参照する）：
  root, hips, spine, chest, neck, head,
  shoulder.L/R, upper_arm.L/R, forearm.L/R, hand.L/R,
  thigh.L/R, shin.L/R, foot.L/R
.L はキャラクターの左（Blender の +X）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import bpy
from mathutils import Vector

# 身長 1.0 に正規化した関節の位置（x, y, z）。正面は -Y
JOINTS_155 = {
    'root': (0, 0, 0),
    'hips': (0, 0, 0.500),
    'spine': (0, 0, 0.590),
    'chest': (0, 0, 0.700),
    'neck': (0, 0, 0.815),
    'head': (0, 0, 0.845),
    'head_end': (0, 0, 1.0),
    'shoulder': (0.035, 0, 0.800),
    'upper_arm': (0.120, 0, 0.800),
    'forearm': (0.150, 0, 0.640),
    'hand': (0.170, 0, 0.500),
    'hand_end': (0.175, 0, 0.445),
    'thigh': (0.060, 0, 0.500),
    'shin': (0.060, 0, 0.275),
    'foot': (0.060, 0, 0.055),
    'toe': (0.060, -0.080, 0.012),
}

BONE_PARENTS = {
    'hips': 'root', 'spine': 'hips', 'chest': 'spine', 'neck': 'chest', 'head': 'neck',
    'shoulder': 'chest', 'upper_arm': 'shoulder', 'forearm': 'upper_arm', 'hand': 'forearm',
    'thigh': 'hips', 'shin': 'thigh', 'foot': 'shin',
}

# 骨の先端の関節
BONE_TAILS = {
    'root': 'hips', 'hips': 'spine', 'spine': 'chest', 'chest': 'neck', 'neck': 'head', 'head': 'head_end',
    'shoulder': 'upper_arm', 'upper_arm': 'forearm', 'forearm': 'hand', 'hand': 'hand_end',
    'thigh': 'shin', 'shin': 'foot', 'foot': 'toe',
}

SIDED = {'shoulder', 'upper_arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'}


def joint(name: str, height: float, side: int = 1, joints: dict | None = None) -> tuple[float, float, float]:
    x, y, z = (joints or JOINTS_155)[name]
    return (x * side * height, y * height, z * height)


def bone_names() -> list[str]:
    names = []
    for b in BONE_TAILS:
        if b in SIDED:
            names += [f'{b}.L', f'{b}.R']
        else:
            names.append(b)
    return names


def build_armature(height: float, name: str = 'Rig', joints: dict | None = None) -> bpy.types.Object:
    """joints を渡すと、そのキャラクターの体型の関節位置で骨を作る（骨の名前と構成は共通）"""
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    created: dict[str, bpy.types.EditBone] = {}

    def make(bone: str, side: int, suffix: str) -> None:
        b = eb.new(bone + suffix)
        head = joint(bone, height, side, joints)
        tail = joint(BONE_TAILS[bone], height, side, joints)
        if bone == 'root':
            tail = (0, 0.15 * height, 0)  # root は後ろ向きの短い骨
        b.head = head
        b.tail = tail
        b.roll = 0
        created[bone + suffix] = b

    for bone in BONE_TAILS:
        if bone in SIDED:
            make(bone, 1, '.L')
            make(bone, -1, '.R')
        else:
            make(bone, 1, '')
    for bone, parent in BONE_PARENTS.items():
        for suffix in (['.L', '.R'] if bone in SIDED else ['']):
            psuffix = suffix if parent in SIDED else ''
            created[bone + suffix].parent = created[parent + psuffix]
            created[bone + suffix].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm


def bind_part(obj: bpy.types.Object, bone: str, arm: bpy.types.Object) -> None:
    """部品を 1 本の骨に丸ごと割り当てる（剛体のスキニング）"""
    vg = obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')


def finalize_skin(mesh: bpy.types.Object, arm: bpy.types.Object) -> None:
    mesh.parent = arm
    mod = mesh.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm


# ---------------------------------------------------------------- アニメーション

Pose = dict[str, tuple[float, float, float]]  # 骨の名前 → (x, y, z) 回転（度、骨のローカル軸）

# 書き出しの標本の間隔（1 秒あたりのこま数）。Godot は 60fps で描くので、速い動作（斬り）のこまを 1/60 秒で置ける。
# Clip.fps がこれより小さいクリップ（従来の 30fps）は、こまの番号を伸ばして同じ秒数にする（動きは変わらない）
SCENE_FPS = 60

# こまの指定：(こま, 姿勢) か (こま, 姿勢, つなぎ)。つなぎは次のこままでの補間：
#   {'interp': 'BEZIER'（既定。なめらか）| 'LINEAR'（等速）| 'SINE' | 'QUAD' | 'CUBIC' | 'EXPO' | 'BACK',
#    'ease': 'EASE_IN'（ゆっくり始めて速く）| 'EASE_OUT'（速く始めてゆっくり止まる）| 'EASE_IN_OUT'}
Key = tuple

# 足の裏の接地点（足首の骨の頭からの、基準の姿勢でのずれ。m）。つま先と、かかと
FOOT_CONTACTS = ((0.0, -0.22, -0.09), (0.0, 0.06, -0.09))
TOE_REACH = 0.22        # 足首からつま先までの前後の長さ（かかとを上げる角度の計算に使う）
FOOT_LIFT_MAX = 40.0    # これより足首を起こさないと床に届かない足は、浮いている足として残す（度）


@dataclass
class Clip:
    name: str
    length: int  # こま数（fps 単位。秒数は length / fps）
    keys: list[Key] = field(default_factory=list)
    loop: bool = True
    # root の位置の上下（こま, 高さ m）
    bob: list[tuple[int, float]] = field(default_factory=list)
    # keys・length・bob のこまの単位（1 秒あたりのこま数）
    fps: int = 30
    # True：各こまで、低いほうの足の裏が床（z=0）に着くように root を下げる（しゃがみ・踏み込みの上下は脚の曲げから決まる）。
    # bob があれば、それをさらに足す
    ground: bool = False


def mirror(pose: Pose) -> Pose:
    """左右を入れ替えたポーズ（歩きの反対の足など）"""
    out: Pose = {}
    for k, (x, y, z) in pose.items():
        if k.endswith('.L'):
            out[k[:-2] + '.R'] = (x, -y, -z)
        elif k.endswith('.R'):
            out[k[:-2] + '.L'] = (x, -y, -z)
        else:
            out[k] = (x, -y, -z)
    return out


def _foot_contacts_local(arm: bpy.types.Object) -> dict[str, list]:
    """足の裏の接地点を、足首の骨のローカル座標にしたもの（姿勢を付けたあと pb.matrix @ 点 で世界の位置になる）"""
    out = {}
    for bn in ('foot.L', 'foot.R'):
        b = arm.data.bones[bn]
        inv = b.matrix_local.to_3x3().inverted()
        out[bn] = [inv @ Vector(c) for c in FOOT_CONTACTS]
    return out


def ground_offset(arm: bpy.types.Object, contacts: dict[str, list]) -> float:
    """今の姿勢（評価済み）で、足の裏の一番低い点が床（z=0）に着く root の高さ。
    root が今どこにあっても（アクションの補間で動いていても）よいように、root からの相対で測る"""
    root_z = arm.pose.bones['root'].matrix.translation.z
    lowest = min((arm.pose.bones[bn].matrix @ c).z for bn, cs in contacts.items() for c in cs)
    return root_z - lowest


def bake_clips(arm: bpy.types.Object, clips: list[Clip]) -> None:
    """各クリップを別々のアクションとして作り、NLA に積む（glTF で個別のアニメーションになる）。
    標本は SCENE_FPS（60fps）。こまごとのつなぎ（Key の 3 つ目）と、足の接地（Clip.ground）もここで付ける"""
    scene = bpy.context.scene
    scene.render.fps = SCENE_FPS
    scene.render.fps_base = 1.0
    arm.animation_data_create()
    names = bone_names()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    contacts = _foot_contacts_local(arm)
    root = arm.pose.bones['root']
    for clip in clips:
        scale = SCENE_FPS / clip.fps

        def sf(frame: float) -> float:
            return 1 + (frame - 1) * scale

        action = bpy.data.actions.new(clip.name)
        action.use_fake_user = True
        arm.animation_data.action = action
        specs: dict[float, dict] = {}
        bob = dict(clip.bob)
        for key in clip.keys:
            frame, pose = key[0], key[1]
            if len(key) > 2 and key[2]:
                specs[round(sf(frame), 3)] = key[2]
            for bn in names:
                pb = arm.pose.bones[bn]
                x, y, z = pose.get(bn, (0.0, 0.0, 0.0))
                pb.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
                pb.keyframe_insert('rotation_euler', frame=sf(frame))
            if clip.ground:
                # このこまに置いた回転で姿勢を評価してから、足の裏の高さを測る
                scene.frame_set(int(round(sf(frame))))
                h = ground_offset(arm, contacts) + bob.get(frame, 0.0)
                root.location = (0.0, 0.0, h)
                root.keyframe_insert('location', frame=sf(frame))
                # 浮いているほうの足は、つま先が床に触れるまでかかとを上げる（足首 X を正へ。上げすぎる足は浮かせたまま）
                for bn in ('foot.L', 'foot.R'):
                    for _ in range(2):
                        scene.frame_set(int(round(sf(frame))))
                        low = min((arm.pose.bones[bn].matrix @ c).z for c in contacts[bn]) + h - root.matrix.translation.z
                        if low <= 0.004:
                            break
                        lift = math.degrees(math.asin(min(1.0, low / TOE_REACH)))
                        pb = arm.pose.bones[bn]
                        if pb.rotation_euler.x + math.radians(lift) > math.radians(FOOT_LIFT_MAX):
                            break
                        pb.rotation_euler.x += math.radians(lift)
                        pb.keyframe_insert('rotation_euler', frame=sf(frame))
        if not clip.ground:
            for frame, h in (clip.bob or [(clip.keys[0][0], 0.0)]):
                # root は後ろ向き（+Y）の骨で、ローカル Z がワールドの上。location の Z が上下になる
                root.location = (0.0, 0.0, h)
                root.keyframe_insert('location', frame=sf(frame))
        root.location = (0.0, 0.0, 0.0)
        # つなぎ：こまの指定が無ければ従来どおりなめらか（ベジエ）
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                spec = specs.get(round(kp.co.x, 3), {})
                kp.interpolation = spec.get('interp', 'BEZIER')
                if kp.interpolation == 'BEZIER':
                    kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
                else:
                    kp.easing = spec.get('ease', 'AUTO')
            fc.update()
        if clip.ground:
            # こまとこまの間（補間）でも足が床にめり込まないように、書き出しの標本ごとに root を測り直して置く
            bob_keys = sorted((sf(f), h) for f, h in clip.bob) or [(sf(clip.keys[0][0]), 0.0)]

            def bob_at(f: float) -> float:
                if f <= bob_keys[0][0]:
                    return bob_keys[0][1]
                for (f0, h0), (f1, h1) in zip(bob_keys, bob_keys[1:]):
                    if f0 <= f <= f1:
                        return h0 + (h1 - h0) * (f - f0) / max(1e-6, f1 - f0)
                return bob_keys[-1][1]

            first, last = int(round(sf(clip.keys[0][0]))), int(round(sf(clip.keys[-1][0])))
            for f in range(first, last + 1):
                scene.frame_set(f)
                root.location = (0.0, 0.0, ground_offset(arm, contacts) + bob_at(f))
                root.keyframe_insert('location', frame=f)
            root.location = (0.0, 0.0, 0.0)
        track = arm.animation_data.nla_tracks.new()
        track.name = clip.name
        strip = track.strips.new(clip.name, 1, action)
        strip.name = clip.name
        track.mute = True
        arm.animation_data.action = None
