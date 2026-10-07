"""動作の数値の確認：光刃の先の軌跡、刃と頭・胴・脚の近さ、足の接地、腰の沈み（bpy。Blender の描画は使わない）。

  .venv-blender/bin/python tools/blender/recon/motion_check.py [--glb godot/assets/models/haru_r.glb]
      [--clips combo1,combo2,combo3] [--out build/motion]

各こま（GLB の標本、60fps）で次を出し、問題は「！」を付けて表に出す：
  - 刃の先の位置（本人の座標。+X 左、-Y 前、+Z 上）と、刃の線と頭の中心・胴（腰→首）・太ももの最短距離
  - 足の裏（つま先・かかと）の一番低い高さ。床は z=0。-0.01 より下はめり込み、両足とも 0.02 より上なら浮いている
  - root の高さ（腰の沈み）
<out>/<動作>_path.png：上・横・正面から見た刃の先の軌跡（番号はこま）と、要所の骨の線。
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from lib import common as C  # noqa: E402
from lib import humanoid as H  # noqa: E402

HEAD_R = 0.13     # 頭（髪を含む）の半径の目安
TORSO_R = 0.12    # 胴の半径の目安
LEG_R = 0.08


def seg_dist(a0: Vector, a1: Vector, b0: Vector, b1: Vector, n: int = 16) -> float:
    """線分 a と線分 b の最短距離（a を n 点で刻んで、点と線分の距離の最小）"""
    best = 1e9
    d = b1 - b0
    ll = d.length_squared
    for i in range(n + 1):
        p = a0.lerp(a1, i / n)
        t = 0.0 if ll < 1e-12 else max(0.0, min(1.0, (p - b0).dot(d) / ll))
        best = min(best, (p - (b0 + d * t)).length)
    return best


def bone_seg(arm, name: str) -> tuple[Vector, Vector]:
    pb = arm.pose.bones[name]
    return (arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail)


def check_clip(glb: str, clip: str, out_dir: str) -> list[str]:
    C.reset_scene()
    bpy.context.scene.render.fps = H.SCENE_FPS
    bpy.ops.import_scene.gltf(filepath=glb)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    act = bpy.data.actions.get(clip)
    if act is None:
        return [f'{clip}: 動作が無い']
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    if hasattr(ad, 'action_slot') and getattr(act, 'slots', None) and len(act.slots):
        ad.action_slot = act.slots[0]
    f0, f1 = int(math.floor(act.frame_range[0])), int(math.ceil(act.frame_range[1]))
    socket = bpy.data.objects['blade_socket']
    blade = bpy.data.objects['LightBlade']
    contacts = H._foot_contacts_local(arm)

    bpy.context.scene.frame_set(f0)
    bpy.context.view_layer.update()
    sm = socket.matrix_world
    axis = sm.to_3x3().col[1].normalized()
    blade_len = max((blade.matrix_world @ v.co - sm.translation).dot(axis) for v in blade.data.vertices)

    rows = []
    warns = []
    skel = []   # (こま, [(頭, 尾), ...]) 描画用
    tips = []
    print(f'== {clip}  こま {f0}〜{f1}（{(f1 - f0) / H.SCENE_FPS:.3f} 秒）、刃の長さ {blade_len:.2f} m')
    print(' こま   秒   root  刃の先 (x, y, z)         頭    胴    脚   左足   右足')
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        sm = socket.matrix_world
        s0 = sm.translation.copy()
        ax = sm.to_3x3().col[1].normalized()
        tip = s0 + ax * blade_len
        head0, head1 = bone_seg(arm, 'head')
        hc = (head0 + head1) / 2
        hd = seg_dist(s0, tip, hc, hc) - HEAD_R
        hips0, _ = bone_seg(arm, 'hips')
        neck0, _ = bone_seg(arm, 'neck')
        td = seg_dist(s0, tip, hips0, neck0) - TORSO_R
        ld = min(seg_dist(s0, tip, *bone_seg(arm, b)) for b in ('thigh.L', 'thigh.R', 'shin.L', 'shin.R')) - LEG_R
        fl = min((arm.pose.bones['foot.L'].matrix @ c).z for c in contacts['foot.L'])
        fr = min((arm.pose.bones['foot.R'].matrix @ c).z for c in contacts['foot.R'])
        rz = arm.pose.bones['root'].matrix.translation.z
        flag = ''
        if hd < 0:
            flag += '！頭'
        if td < 0:
            flag += '！胴'
        if ld < 0:
            flag += '！脚'
        if min(fl, fr) < -0.01:
            flag += '！めり込み'
        if min(fl, fr) > 0.02:
            flag += '！浮き'
        t = (f - f0) / H.SCENE_FPS
        print(f' {f:3d} {t:5.3f} {rz:+.3f} ({tip.x:+.2f},{tip.y:+.2f},{tip.z:+.2f})  {hd:+.2f} {td:+.2f} {ld:+.2f}  '
              f'{fl:+.3f} {fr:+.3f} {flag}')
        if flag:
            warns.append(f'{clip} こま {f}: {flag}')
        tips.append((f, tip))
        skel.append((f, [bone_seg(arm, b) for b in H.bone_names()], (s0, tip)))
    draw_paths(clip, tips, skel, os.path.join(out_dir, f'{clip}_path.png'))
    return warns


def draw_paths(clip: str, tips, skel, path: str) -> None:
    """上（x-y）・横（y-z）・正面（x-z）の 3 枚。1m = 180px"""
    S = 180
    W = 520
    views = [('top  (+X 左, -Y 前)', lambda p: (p.x, -p.y)), ('side  (-Y 前, +Z 上)', lambda p: (-p.y, p.z)),
             ('front  (+X 左, +Z 上)', lambda p: (p.x, p.z))]
    img = Image.new('RGB', (W * 3, W), (24, 24, 28))
    d = ImageDraw.Draw(img)
    n = len(skel)
    for vi, (title, proj) in enumerate(views):
        ox = vi * W + W // 2
        oy = W // 2 + (0 if vi == 0 else int(0.85 * S))

        def pt(p: Vector) -> tuple[float, float]:
            x, y = proj(p)
            return (ox + x * S, oy - y * S)

        d.text((vi * W + 8, 6), f'{clip}  {title}', fill=(230, 230, 230))
        # 床と中心線
        if vi > 0:
            d.line([(vi * W, oy), (vi * W + W, oy)], fill=(70, 70, 80))
        d.line([(ox, 0), (ox, W)], fill=(50, 50, 60))
        # 骨（3 こまごとに薄く）と刃（毎こま）
        for i, (f, bones, (s0, tip)) in enumerate(skel):
            c = int(90 + 165 * i / max(1, n - 1))
            if i % 3 == 0 or i == n - 1:
                for h, t in bones:
                    d.line([pt(h), pt(t)], fill=(c // 2, c // 2, c // 2), width=1)
            d.line([pt(s0), pt(tip)], fill=(c, int(c * 0.75), 40), width=1)
        # 先の軌跡
        for i in range(1, n):
            c = int(90 + 165 * i / max(1, n - 1))
            d.line([pt(tips[i - 1][1]), pt(tips[i][1])], fill=(255, c, 60), width=3)
        for i, (f, tip) in enumerate(tips):
            x, y = pt(tip)
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 240, 120))
            d.text((x + 4, y - 12), str(f), fill=(255, 240, 120))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print('軌跡：', path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb', default=os.path.join(C.REPO, 'godot/assets/models/haru_r.glb'))
    ap.add_argument('--clips', default='combo1,combo2,combo3')
    ap.add_argument('--out', default=os.path.join(C.REPO, 'build/motion'))
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    warns = []
    for clip in args.clips.split(','):
        warns += check_clip(os.path.abspath(args.glb), clip, args.out)
    print('\n問題：', len(warns))
    for w in warns:
        print(' ', w)


if __name__ == '__main__':
    main()
