"""ハル（haru_r）の部品の前後の比べ（Cycles）：服の硬い部品の近写と、銃の握りの近写。

  .venv-blender/bin/python tools/blender/recon/parts_review.py --glb <GLB> --out <dir> [--only parts,grip]
  .venv-blender/bin/python tools/blender/recon/parts_review.py --compose <前の dir> <後の dir> --dest docs/art_orders/haru_r_trial

  parts：全身 6 方向（基準の姿勢、ゲームと同じく拳を握って銃を持つ）＋近写（右肩・膝・前腕・帯とポーチ・手袋）
  grip ：右手と銃の近写。idle・run・撃つ（右腕を正面へ水平に伸ばす：haru_pose.gd の照準と同じ）・jump を 2 方向から
  --compose：前と後を 1 行ずつ並べた parts_before_after.jpg・gun_grip.jpg を作る
"""
from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

FULL = [0, 45, 90, 180, -90, -45]
# (名前, 骨（中心）, 中心のずらし, 方位角, 上から, 幅 m)
CLOSE = [
    ('R shoulder 45', 'upper_arm.R', (0, 0, -0.05), 45, 10, 0.34),
    ('R shoulder side', 'upper_arm.R', (0, 0, -0.05), 90, 0, 0.34),
    ('R shoulder back', 'upper_arm.R', (0, 0, -0.05), 150, 10, 0.34),
    ('knees front', 'shin.L', (-0.143, 0, 0), 0, 0, 0.42),
    ('R knee side', 'shin.R', (0, 0, 0), 90, 0, 0.30),
    ('L forearm out', 'forearm.L', (0, 0, -0.10), -70, 0, 0.34),
    ('L forearm front', 'forearm.L', (0, 0, -0.10), -10, 0, 0.34),
    ('belt front', 'hips', (0, 0, 0.08), 0, 5, 0.50),
    ('belt R side', 'hips', (0, 0, 0.0), 70, 5, 0.50),
    ('belt back', 'hips', (0, 0, 0.05), 180, 5, 0.50),
    ('L glove', 'hand.L', (0, 0, -0.04), -20, 0, 0.24),
    ('R glove/fist', 'hand.R', (0, 0, -0.04), 20, 0, 0.24),
]
# (名前, 動作, フレーム)
GRIP_POSES = [('idle', 'idle', 1), ('run', 'run', 6), ('shoot (aim fwd)', 'aim', 1), ('jump', 'jump', 5),
              ('dash', 'dash', 4)]
GRIP_AZ = [(90, 10), (25, 15)]


def aim(S) -> None:
    """撃つ姿勢：右の上腕を正面（-Y）へ水平に向け、肘を伸ばす（haru_pose.gd の照準の重み 1）"""
    import bpy
    from mathutils import Matrix, Vector
    S.rest()   # 動作を外した基準の姿勢から（動作が付いていると、骨の行列の書き換えが上書きされる）
    arm = S.arm
    mw = arm.matrix_world

    def rot_to(bone: str, child: str, want: Vector) -> None:
        pb = arm.pose.bones[bone]
        a = mw @ pb.head
        b = mw @ arm.pose.bones[child].head
        q = (b - a).normalized().rotation_difference(want.normalized())
        hl = pb.head.copy()
        rl = (mw.to_3x3().inverted() @ q.to_matrix() @ mw.to_3x3()).to_4x4()
        pb.matrix = Matrix.Translation(hl) @ rl @ Matrix.Translation(-hl) @ pb.matrix
        bpy.context.view_layer.update()

    rot_to('upper_arm.R', 'forearm.R', Vector((0, -1, 0)))
    ua = arm.pose.bones['upper_arm.R']
    rot_to('forearm.R', 'hand.R', (mw @ arm.pose.bones['forearm.R'].head) - (mw @ ua.head))


def render_all(glb: str, out: str, only: set[str], size: int, samples: int) -> None:
    import bpy  # noqa: F401
    from mathutils import Vector
    from recon import review as RV
    os.makedirs(out, exist_ok=True)
    S = RV.Scene(glb, samples)
    S.show_blade(False)
    S.show_gun(True)
    if 'parts' in only:
        S.rest()
        for az in FULL:
            d, r = RV.az_dirs(az, 5)
            S.render((0, 0, 0.78), d, r, 1.7, size, os.path.join(out, f'full_{az}.png'))
        for i, (name, bone, off, az, el, w) in enumerate(CLOSE):
            c = S.bone_head(bone) + Vector(off)
            d, r = RV.az_dirs(az, el)
            S.render(tuple(c), d, r, w, size, os.path.join(out, f'close_{i}.png'))
    if 'grip' in only:
        for i, (name, act, fr) in enumerate(GRIP_POSES):
            if act == 'aim':
                aim(S)
            else:
                S.pose(act, fr)
            hr = S.arm.pose.bones['hand.R']
            mw = S.arm.matrix_world
            c = (mw @ hr.head).lerp(mw @ hr.tail, 0.6)
            for j, (az, el) in enumerate(GRIP_AZ):
                d, r = RV.az_dirs(az, el)
                S.render(tuple(c), d, r, 0.30, size, os.path.join(out, f'grip_{i}_{j}.png'))


def compose(before: str, after: str, dest: str) -> None:
    from recon import review as RV

    def load(d: str, f: str, size: int) -> np.ndarray:
        p = os.path.join(d, f)
        if not os.path.exists(p):
            return np.full((size, size, 3), 40, np.uint8)
        im = Image.open(p).convert('RGBA').resize((size, size))
        a = np.asarray(im).astype(np.float32)
        al = a[..., 3:4] / 255
        return (a[..., :3] * al + 50 * (1 - al)).astype(np.uint8)

    # 部品：全身 6 方向（前・後の 2 行）＋近写 12 枚（前・後を 6 枚ずつ 4 行）
    s = 300
    rows = []
    for tag, d in (('before', before), ('after', after)):
        rows.append([RV.label(load(d, f'full_{az}.png', s), f'{tag} az {az}') for az in FULL])
    for k in (0, 6):
        for tag, d in (('before', before), ('after', after)):
            rows.append([RV.label(load(d, f'close_{i}.png', s), f'{tag} {CLOSE[i][0]}') for i in range(k, k + 6)])
    Image.fromarray(RV.grid(rows)).convert('RGB').save(os.path.join(dest, 'parts_before_after.jpg'), quality=85)
    # 握り：動作ごとに 1 行（前 2 方向・後 2 方向）
    rows = []
    for i, (name, _, _) in enumerate(GRIP_POSES):
        row = []
        for tag, d in (('before', before), ('after', after)):
            for j, (az, _) in enumerate(GRIP_AZ):
                row.append(RV.label(load(d, f'grip_{i}_{j}.png', s), f'{tag} {name} az {az}'))
        rows.append(row)
    Image.fromarray(RV.grid(rows)).convert('RGB').save(os.path.join(dest, 'gun_grip.jpg'), quality=85)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb')
    ap.add_argument('--out')
    ap.add_argument('--only', default='parts,grip')
    ap.add_argument('--size', type=int, default=360)
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--compose', nargs=2)
    ap.add_argument('--dest', default='docs/art_orders/haru_r_trial')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    if args.compose:
        compose(args.compose[0], args.compose[1], args.dest)
        return
    render_all(args.glb, args.out, set(args.only.split(',')), args.size, args.samples)


if __name__ == '__main__':
    main()
