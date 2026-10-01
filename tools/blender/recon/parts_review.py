"""ハル（haru_r）の部品の前後の比べ（Cycles）：服の硬い部品の近写と、銃の握りの近写。

  .venv-blender/bin/python tools/blender/recon/parts_review.py --glb <GLB> --out <dir> [--only parts,grip]
  .venv-blender/bin/python tools/blender/recon/parts_review.py --compose <前の dir> <後の dir> --dest docs/art_orders/haru_r_trial

  parts：全身 6 方向（基準の姿勢、ゲームと同じく拳を握って銃を持つ）＋近写（右肩・膝・前腕・帯とポーチ・手袋）
  grip ：右手と銃の近写。idle・run・撃つ（右腕を正面へ水平に伸ばす：haru_pose.gd の照準と同じ）・jump を 2 方向から
  --compose：前と後を 1 行ずつ並べた parts_before_after.jpg・gun_grip.jpg を作る
  hand ：（6 回目）右手の部品の近写。動作 6 つ × 手から見た 3 方向（手から 16cm より遠い体は透明）＋体の向きの 2 方向
  bleed：（6 回目）汚れ探しの近写 18 枚（首の後ろ・右肩・膝・ポーチ・胸・脚・靴・手袋・右の手首）
  --compose-hand 前 後 画面の前 画面の後：hand_grip.jpg、--compose-bleed 前 後：bleed_fix.jpg
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
# 6 回目の汚れ探し：（名前, 骨, ずらし, 方位角, 上から, 幅）
BLEED = [
    ('neck back', 'neck', (0, 0.0, -0.02), 180, 10, 0.14),
    ('neck back low', 'neck', (0, 0.0, -0.02), 180, -20, 0.14),
    ('neck back L', 'neck', (0.03, 0.0, -0.02), -135, 10, 0.14),
    ('R shoulder top', 'upper_arm.R', (0, 0, 0.03), 90, 70, 0.20),
    ('R shoulder front', 'upper_arm.R', (0, 0, -0.02), 20, 10, 0.20),
    ('R shoulder back', 'upper_arm.R', (0, 0, -0.02), 160, 10, 0.20),
    ('R shoulder side', 'upper_arm.R', (0, 0, -0.02), 90, 10, 0.20),
    ('R knee out', 'shin.R', (0, 0, 0), 80, 0, 0.16),
    ('L knee out', 'shin.L', (0, 0, 0), -80, 0, 0.16),
    ('R knee front', 'shin.R', (0, 0, 0), 20, 0, 0.16),
    ('R pouch/forearm', 'hips', (-0.12, 0, 0.0), 80, 0, 0.18),
    ('L pouch', 'hips', (0.12, 0, 0.0), -80, 0, 0.18),
    ('L shoulder', 'upper_arm.L', (0, 0, -0.03), -60, 15, 0.26),
    ('chest front', 'chest', (0, 0, 0.0), 0, 10, 0.32),
    ('legs back', 'shin.L', (-0.143, 0, 0.05), 180, 5, 0.42),
    ('boots front', 'foot.L', (-0.15, 0, 0.0), 20, 20, 0.36),
    ('L glove', 'hand.L', (0, 0, -0.04), -60, 10, 0.22),
    ('R wrist', 'hand.R', (0, 0, 0.0), 120, 10, 0.24),
]
# (名前, 動作, フレーム)
GRIP_POSES = [('idle', 'idle', 1), ('run', 'run', 6), ('shoot (aim fwd)', 'aim', 1), ('jump', 'jump', 5),
              ('dash', 'dash', 4)]
GRIP_AZ = [(90, 10), (25, 15)]
# 6 回目の右手の部品：動作 × 手から見た 3 方向（手の甲の側・親指の側・前の下＝指が握りの前を回る所）
HAND_POSES = [('idle', 'idle', 1), ('run', 'run', 6), ('shoot (aim)', 'aim', 1), ('jump', 'jump', 5),
              ('dash', 'dash', 4), ('combo', 'combo1', 4)]
HAND_VIEWS = [('back of hand', (0.25, -1.0, 0.35)), ('thumb side', (0.15, 1.0, 0.45)), ('front', (1.0, 0.6, -0.45))]
HAND_WRIST_IN_GUN = (-0.062, -0.040, -0.010)   # ai_character.py と同じ（銃の座標の手首）


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


def gun_axes(S):
    """今の姿勢の銃の座標の軸（世界）と、握りの中ほどの点。ai_character.hand_frame と同じ決め方を姿勢で回す"""
    from mathutils import Vector
    arm = S.arm
    b = arm.data.bones['hand.R']
    pb = arm.pose.bones['hand.R']
    gx = (b.tail_local - b.head_local).normalized()
    gy = (Vector((1.0, 0.0, 0.0)) - gx * gx.x).normalized()
    gz = gx.cross(gy)
    R = (arm.matrix_world @ pb.matrix @ b.matrix_local.inverted()).to_3x3()
    ax = [(R @ v).normalized() for v in (gx, gy, gz)]
    wrist = arm.matrix_world @ pb.head
    o = wrist - sum((a * c for a, c in zip(ax, HAND_WRIST_IN_GUN)), Vector())
    return ax, o


def isolate(S, center, radius: float):
    """中心から radius より遠い体の面を透明にする（手の近写で、手の向こう・手前の体が隠さないように）。
    戻すための元の材質の番号を返す（restore に渡す）"""
    import bpy
    body = S.body
    me = body.data
    if not any(sl.material and sl.material.name == 'review_cut' for sl in body.material_slots):
        m = bpy.data.materials.new('review_cut')
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        o = nt.nodes.new('ShaderNodeOutputMaterial')
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        nt.links.new(tr.outputs[0], o.inputs['Surface'])
        me.materials.append(m)
    cut = next(i for i, sl in enumerate(body.material_slots) if sl.material and sl.material.name == 'review_cut')
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    em = ev.to_mesh()
    mw = np.array(body.matrix_world)
    co = np.empty(len(em.vertices) * 3)
    em.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    far_v = np.linalg.norm(co - np.array(center), axis=1) > radius
    ev.to_mesh_clear()
    old = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('material_index', old)
    lt = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_total', lt)
    ls = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', ls)
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    far_f = np.array([far_v[lv[a:a + n]].all() for a, n in zip(ls, lt)])
    new = np.where(far_f, cut, old).astype(np.int32)
    me.polygons.foreach_set('material_index', new)
    me.update()
    return old


def restore(S, old) -> None:
    S.body.data.polygons.foreach_set('material_index', old)
    S.body.data.update()


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
    if 'bleed' in only:
        S.rest()
        for i, (name, bone, off, az, el, w) in enumerate(BLEED):
            c = S.bone_head(bone) + Vector(off)
            d, r = RV.az_dirs(az, el)
            S.render(tuple(c), d, r, w, size, os.path.join(out, f'bleed_{i}.png'))
    if 'hand' in only:
        for i, (name, act, fr) in enumerate(HAND_POSES):
            if act == 'aim':
                aim(S)
            else:
                S.pose(act, fr)
            ax, o = gun_axes(S)
            c = o + ax[0] * (-0.01) + ax[2] * (-0.025)
            old = isolate(S, c, 0.16)     # 手から 16cm より遠い体は描かない（手と銃だけの近写）
            for j, (_, v) in enumerate(HAND_VIEWS):
                d = -(ax[0] * v[0] + ax[1] * v[1] + ax[2] * v[2]).normalized()
                r = d.cross(ax[2]).normalized() if abs(d.dot(ax[2])) < 0.95 else ax[0]
                S.render(tuple(c), d, r, 0.22, size, os.path.join(out, f'hand_{i}_{j}.png'))
            restore(S, old)
            # 体の向きの 2 方向（右・右前）
            for j, (az, el) in enumerate(GRIP_AZ):
                d, r = RV.az_dirs(az, el)
                S.render(tuple(c), d, r, 0.30, size, os.path.join(out, f'handaz_{i}_{j}.png'))
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


def compose_hand(before: str, after: str, mv_before: str, mv_after: str, dest: str) -> None:
    """6 回目：hand_grip.jpg（Blender の近写の前後と、model-viewer の画面の前後）"""
    from recon import review as RV
    s = 240

    def load(p: str) -> np.ndarray:
        if not os.path.exists(p):
            return np.full((s, s, 3), 40, np.uint8)
        im = Image.open(p).convert('RGBA')
        w, h = im.size
        if w != h:   # model-viewer の画面は縦長：中央の正方形
            k = min(w, h)
            im = im.crop(((w - k) // 2, (h - k) // 2, (w - k) // 2 + k, (h - k) // 2 + k))
        a = np.asarray(im.resize((s, s))).astype(np.float32)
        al = a[..., 3:4] / 255
        return (a[..., :3] * al + 50 * (1 - al)).astype(np.uint8)
    rows = []
    for i, (name, _, _) in enumerate(HAND_POSES):
        row = [RV.label(load(os.path.join(before, f'handaz_{i}_{j}.png')), f'before {name} az {az}')
               for j, (az, _) in enumerate(GRIP_AZ)]
        row += [RV.label(load(os.path.join(after, f'handaz_{i}_{j}.png')), f'AFTER {name} az {az}')
                for j, (az, _) in enumerate(GRIP_AZ)]
        row += [RV.label(load(os.path.join(after, f'hand_{i}_{j}.png')), f'AFTER {name} {v[0]}')
                for j, v in enumerate(HAND_VIEWS)]
        rows.append(row)
    mv_poses = ['idle', 'run', 'jump', 'dash', 'combo1', 'charge']
    blank = np.full((s, s, 3), 30, np.uint8)
    for tag, d, view in (('viewer before', mv_before, 'right'), ('viewer AFTER', mv_after, 'front-right'),
                         ('viewer AFTER', mv_after, 'right'), ('viewer AFTER', mv_after, 'back-right')):
        row = [RV.label(load(os.path.join(d, f'{p}_{view}.png')), f'{tag} {p} {view}') for p in mv_poses]
        rows.append(row + [blank])
    Image.fromarray(RV.grid(rows)).convert('RGB').save(os.path.join(dest, 'hand_grip.jpg'), quality=85)


def compose_bleed(before: str, after: str, dest: str) -> None:
    """6 回目：bleed_fix.jpg（近写の前後を並べる。前・後の 2 枚 1 組で 1 行に 4 組）"""
    from recon import review as RV
    s = 260

    def load(p: str) -> np.ndarray:
        if not os.path.exists(p):
            return np.full((s, s, 3), 40, np.uint8)
        im = Image.open(p).convert('RGBA').resize((s, s))
        a = np.asarray(im).astype(np.float32)
        al = a[..., 3:4] / 255
        return (a[..., :3] * al + 50 * (1 - al)).astype(np.uint8)
    rows, row = [], []
    for i, (name, *_rest) in enumerate(BLEED):
        row += [RV.label(load(os.path.join(before, f'bleed_{i}.png')), f'before {name}'),
                RV.label(load(os.path.join(after, f'bleed_{i}.png')), f'AFTER {name}')]
        if len(row) == 8:
            rows.append(row)
            row = []
    if row:
        rows.append(row + [np.full((s, s, 3), 30, np.uint8)] * (8 - len(row)))
    Image.fromarray(RV.grid(rows)).convert('RGB').save(os.path.join(dest, 'bleed_fix.jpg'), quality=85)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb')
    ap.add_argument('--out')
    ap.add_argument('--only', default='parts,grip')
    ap.add_argument('--size', type=int, default=360)
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--compose', nargs=2)
    ap.add_argument('--compose-hand', nargs=4, help='前の dir・後の dir・model-viewer の前・後の画面の dir')
    ap.add_argument('--compose-bleed', nargs=2)
    ap.add_argument('--dest', default='docs/art_orders/haru_r_trial')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    if args.compose:
        compose(args.compose[0], args.compose[1], args.dest)
        return
    if args.compose_hand:
        compose_hand(*args.compose_hand, args.dest)
        return
    if args.compose_bleed:
        compose_bleed(*args.compose_bleed, args.dest)
        return
    render_all(args.glb, args.out, set(args.only.split(',')), args.size, args.samples)


if __name__ == '__main__':
    main()
