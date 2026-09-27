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


def joint(name: str, height: float, side: int = 1) -> tuple[float, float, float]:
    x, y, z = JOINTS_155[name]
    return (x * side * height, y * height, z * height)


def bone_names() -> list[str]:
    names = []
    for b in BONE_TAILS:
        if b in SIDED:
            names += [f'{b}.L', f'{b}.R']
        else:
            names.append(b)
    return names


def build_armature(height: float, name: str = 'Rig') -> bpy.types.Object:
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    created: dict[str, bpy.types.EditBone] = {}

    def make(bone: str, side: int, suffix: str) -> None:
        b = eb.new(bone + suffix)
        head = joint(bone, height, side)
        tail = joint(BONE_TAILS[bone], height, side)
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


@dataclass
class Clip:
    name: str
    length: int  # フレーム数（30fps）
    keys: list[tuple[int, Pose]] = field(default_factory=list)
    loop: bool = True
    # root の位置の上下（フレーム, 高さ m）
    bob: list[tuple[int, float]] = field(default_factory=list)


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


def bake_clips(arm: bpy.types.Object, clips: list[Clip]) -> None:
    """各クリップを別々のアクションとして作り、NLA に積む（glTF で個別のアニメーションになる）"""
    arm.animation_data_create()
    names = bone_names()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    for clip in clips:
        action = bpy.data.actions.new(clip.name)
        action.use_fake_user = True
        arm.animation_data.action = action
        for frame, pose in clip.keys:
            for bn in names:
                pb = arm.pose.bones[bn]
                x, y, z = pose.get(bn, (0.0, 0.0, 0.0))
                pb.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
                pb.keyframe_insert('rotation_euler', frame=frame)
        root = arm.pose.bones['root']
        bob = clip.bob or [(clip.keys[0][0], 0.0)]
        for frame, h in bob:
            # root は後ろ向き（+Y）の骨なので、ローカル Z がワールドの上方向に対応しないことがある。
            # ここでは location の Y 成分をワールドの上下として扱う（root のローカル Y = ワールド +Y ではなく、
            # 骨の軸はワールド Y 方向。上下はローカル Z）
            root.location = (0.0, 0.0, h)
            root.keyframe_insert('location', frame=frame)
        track = arm.animation_data.nla_tracks.new()
        track.name = clip.name
        strip = track.strips.new(clip.name, 1, action)
        strip.name = clip.name
        track.mute = True
        arm.animation_data.action = None
