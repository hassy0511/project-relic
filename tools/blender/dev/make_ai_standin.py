"""AI 変換の取り込みを試すための「代役」を作る（開発用）。

本物の AI の出力（TRELLIS.2 の GLB）が届く前に、取り込みの仕組みを試すため、
A案の試作のハルを「A ポーズ・骨なし・1 つの塊・銃なし」にして書き出す。
  python tools/blender/dev/make_ai_standin.py <出力.glb> [--fused] [--turn 度]
--fused：ボクセルで作り直して継ぎ目のない塊にする（AI の出力に近い。色は消える）
--turn：正面の向きを変える（取り込み側の向きの補正を試す）
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402
from mathutils import Matrix  # noqa: E402

from lib import common as C  # noqa: E402
from models import haru_a  # noqa: E402

APOSE_DEG = 35.0  # 腕を体から開く角度（発注書 W1-00 の A ポーズ）


def main() -> None:
    out = sys.argv[1]
    fused = '--fused' in sys.argv
    turn = float(sys.argv[sys.argv.index('--turn') + 1]) if '--turn' in sys.argv else 0.0
    haru_a.build_gun = lambda b, fist: None  # 銃は別の絵・別の部品にするので、代役には付けない
    haru_a.build()
    arm = bpy.data.objects['HaruRig']
    body = bpy.data.objects['Haru']
    # 腕を A ポーズへ（肩を中心に、体の外へ開く）
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    # 動作を焼き付けたあとは最後の動作の姿勢が残っているので、基準の姿勢に戻す
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    for side, sx in ((1, '.L'), (-1, '.R')):
        pb = arm.pose.bones['upper_arm' + sx]
        cur = (pb.tail - pb.head).normalized()
        now = math.degrees(math.atan2(abs(cur.x), -cur.z))
        # Y 軸まわりの回転で、+X 側（左腕）は下から外へ開く向きが負になる
        rot = Matrix.Rotation(-math.radians(APOSE_DEG - now) * side, 4, 'Y')
        head = pb.head.copy()
        pb.matrix = Matrix.Translation(head) @ rot @ Matrix.Translation(-head) @ pb.matrix
        bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier='Armature')
    # 骨、光刃、目印を消して、形だけにする
    for o in list(bpy.data.objects):
        if o is not body:
            bpy.data.objects.remove(o, do_unlink=True)
    body.parent = None
    body.vertex_groups.clear()
    if fused:
        m = body.modifiers.new('remesh', 'REMESH')
        m.mode = 'VOXEL'
        m.voxel_size = 0.006
        bpy.ops.object.modifier_apply(modifier='remesh')
    if turn:
        body.rotation_euler = (0, 0, math.radians(turn))
        bpy.ops.object.transform_apply(rotation=True)
    # AI の出力のように、大きさと位置をずらしておく（取り込み側で直せるか試す）
    body.scale = (0.62, 0.62, 0.62)
    body.location = (0.3, -0.2, 0.4)
    bpy.ops.object.transform_apply(location=True, scale=True)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    C.export_glb(out, animations=False)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print('wrote', out, 'tris', tris, 'fused', fused)


if __name__ == '__main__':
    main()
