"""haru_f：重みの確かめ用の試しの姿勢（Blender の骨を、モデルの軸での回転で動かして描く）。
  build.py --pose arms_up,crouch,run,twist,slash"""
from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

# 姿勢：骨 → [(軸, 度), …]（モデルの軸。x = 左、y = 後ろ、z = 上。順に掛ける）
POSES = {
    'arms_up': {'upper_arm.L': [(Y, -150)], 'upper_arm.R': [(Y, 150)], 'forearm.L': [(Y, -10)], 'forearm.R': [(Y, 10)]},
    'arms_fwd': {'upper_arm.L': [(X, -85), (Y, 25)], 'upper_arm.R': [(X, -85), (Y, -25)], 'forearm.L': [(X, -40)], 'forearm.R': [(X, -40)]},
    'crouch': {'hips': [(X, -18)], 'spine': [(X, -10)], 'thigh.L': [(X, -95)], 'thigh.R': [(X, -95)], 'shin.L': [(X, 120)], 'shin.R': [(X, 120)],
               'foot.L': [(X, -25)], 'foot.R': [(X, -25)]},
    'run': {'hips': [(X, -10)], 'chest': [(Z, 14)], 'thigh.L': [(X, -62)], 'shin.L': [(X, 70)], 'thigh.R': [(X, 28)], 'shin.R': [(X, 85)],
            'upper_arm.L': [(X, 50), (Y, -8)], 'forearm.L': [(X, -75)], 'upper_arm.R': [(X, -55), (Y, 8)], 'forearm.R': [(X, -85)], 'head': [(X, 8)]},
    'twist': {'spine': [(Z, 18)], 'chest': [(Z, 30)], 'head': [(Z, -40), (X, 12)], 'neck': [(Z, -8)]},
    'slash': {'hips': [(Z, -14)], 'spine': [(Z, -16), (X, -8)], 'chest': [(Z, -28)], 'head': [(Z, 40)], 'shoulder.L': [(Z, -10)],
              'upper_arm.L': [(Y, -62), (Z, -70)], 'forearm.L': [(Z, -20)], 'upper_arm.R': [(Y, 40), (X, 30)], 'forearm.R': [(X, -40)],
              'thigh.L': [(X, -42)], 'shin.L': [(X, 48)], 'thigh.R': [(X, 22)], 'shin.R': [(X, 20)]},
}


def apply(arm, name):
    pose = POSES[name]
    rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    order = [b.name for b in arm.data.bones]        # 親が先
    M = {}
    for nm in order:
        b = arm.data.bones[nm]
        D = Matrix.Identity(4)
        for (ax, deg) in pose.get(nm, []):
            D = Matrix.Rotation(math.radians(deg), 4, ax) @ D
        head = rest[nm].to_translation()
        T, Ti = Matrix.Translation(head), Matrix.Translation(-head)
        local = T @ D @ Ti @ rest[nm]
        if b.parent:
            p = b.parent.name
            M[nm] = M[p] @ rest[p].inverted() @ local
        else:
            M[nm] = local
    for nm in order:
        arm.pose.bones[nm].matrix = M[nm]
        bpy.context.view_layer.update()


def clear(arm):
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
