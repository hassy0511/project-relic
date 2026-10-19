"""杖をついた老人の住人（町長トルーデ）の動作（60fps）。ai_character.py --clips elder で、humanoid_anims の 14 動作の代わりに焼く。

ゲームが使うもの（godot/scripts/view/props_view.gd）：
  idle    待機（3 秒の輪）。右手で杖の T 字の握りを上から握って少し寄りかかり、息で胸が動き、頭はゆっくり左右を見る。
          左腕は力を抜いて下ろす
右手の杖は手の部品と一緒に hand.R に付いている（chars/trude_parts.py の grip_prop、ai_character.py の _build_grip_hand）。
杖の先が床に着き、軸がまっすぐ立つ右腕の姿勢（上腕・前腕・手首の回転）は、こまごとに骨と杖の目印から解く（solve_arm）。
骨の回転の向きは humanoid_anims.py の頭の説明と同じ。作り方は SKILL 7b。
"""
from __future__ import annotations

import math

from lib.humanoid import Clip, Pose, bone_names

FPS = 60
EASE = {'interp': 'SINE', 'ease': 'EASE_IN_OUT'}
# 杖の先の置き場所（骨の物体の座標＝再構築の座標、身長 1.55m）：本人の右前、スカートの裾の外
TIP = (-0.300, -0.215, 0.0)


def merge(*poses: Pose) -> Pose:
    out: Pose = {}
    for p in poses:
        out.update(p)
    return out


# 立った基準の姿勢：背中を少し丸め、頭は少し上げて相手を見る。左腕は体の横に力を抜いて
STAND: Pose = {
    'spine': (5, 0, 0), 'chest': (3, 0, 0), 'neck': (-2, 0, 0), 'head': (-6, 0, 0),
    'upper_arm.L': (4, 0, -2), 'forearm.L': (-14, 0, 0), 'hand.L': (0, 0, 4),
}
ARM_R = ('upper_arm.R', 'forearm.R', 'hand.R')


def solve_arm(arm, body: Pose, pts: dict, guess=None) -> tuple[Pose, dict]:
    """体の姿勢 body のとき、杖の軸がまっすぐ下を向き、先が TIP に着き、横棒が水平で左右に向き、指が前を向く右腕の回転を解く。
    pts：杖の目印（基準の姿勢の骨の物体の座標。bar_c 横棒の中心、tip 先、bar_axis_end 横棒の軸の上の点）"""
    import bpy
    import numpy as np
    from mathutils import Vector
    from scipy.optimize import minimize
    pbs = arm.pose.bones
    for pb in pbs:
        pb.rotation_mode = 'XYZ'
    names = bone_names()
    hb = arm.data.bones['hand.R']
    rest_inv = hb.matrix_local.inverted()
    rest_dir = (hb.tail_local - hb.head_local).normalized()
    c0, t0, a0 = (Vector(pts[k]) for k in ('bar_c', 'tip', 'bar_axis_end'))
    tip = Vector(TIP)

    def pose_of(v) -> Pose:
        p = dict(body)
        p['upper_arm.R'] = (v[0], v[1], v[2])
        p['forearm.R'] = (v[3], v[4], 0.0)
        p['hand.R'] = (v[5], v[6], v[7])
        return p

    def apply(p: Pose) -> None:
        for bn in names:
            x, y, z = p.get(bn, (0.0, 0.0, 0.0))
            pbs[bn].rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
        bpy.context.view_layer.update()

    def measure(v):
        apply(pose_of(v))
        M = pbs['hand.R'].matrix @ rest_inv
        c, t, a = M @ c0, M @ t0, M @ a0
        sd = (t - c).normalized()
        bd = (a - c).normalized()
        fd = (M.to_3x3() @ rest_dir).normalized()
        elbow = pbs['forearm.R'].head
        return c, t, sd, bd, fd, elbow

    def cost(v):
        c, t, sd, bd, fd, elbow = measure(v)
        e = 40.0 * (sd - Vector((0.0, 0.0, -1.0))).length_squared
        e += 400.0 * (t.z - tip.z) ** 2 + 120.0 * ((t.x - tip.x) ** 2 + (t.y - tip.y) ** 2)
        e += 6.0 * bd.z ** 2 + 3.0 * bd.y ** 2
        e += 4.0 * max(0.0, fd.y + 0.6) ** 2              # 指は前（−Y）へ
        e += 30.0 * max(0.0, elbow.x + 0.17) ** 2          # 肘は体の横（胴にめり込まない）
        e += 2e-6 * float(np.sum(np.asarray(v) ** 2))     # 小さい回転を好む
        e += 1e-3 * max(0.0, v[3]) ** 2                    # 肘は前へだけ曲がる（X が負）
        return e

    starts = [guess] if guess is not None else []
    for tw in (-90.0, -45.0, 0.0, 45.0, 90.0):
        starts.append([-20.0, 0.0, 6.0, -45.0, tw, -10.0, 0.0, 0.0])
    best = None
    for s in starts:
        r = minimize(cost, np.asarray(s, float), method='Powell', options={'maxfev': 4000, 'xtol': 1e-3, 'ftol': 1e-9})
        r = minimize(cost, r.x, method='Nelder-Mead', options={'maxfev': 3000, 'xatol': 1e-3, 'fatol': 1e-10})
        if best is None or r.fun < best.fun:
            best = r
    v = [round(float(x), 2) for x in best.x]
    c, t, sd, bd, fd, elbow = measure(v)
    rep = {'cost': round(float(best.fun), 6), 'tip': [round(x, 4) for x in t], 'bar_c': [round(x, 4) for x in c],
           'shaft_dir': [round(x, 3) for x in sd], 'bar_dir': [round(x, 3) for x in bd],
           'finger_dir': [round(x, 3) for x in fd], 'angles': v}
    for pb in pbs:
        pb.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    p = pose_of(v)
    return {k: p[k] for k in ARM_R}, rep


SOLVED: list = []      # 解いた姿勢の記録（ai_character.py の stats には入らない。確かめ用に print する）


def idle(arm, pts: dict) -> Clip:
    a = STAND
    b = merge(STAND, {'chest': (2, -2, 1), 'neck': (-2, -2, 0), 'head': (-5, -6, 2), 'upper_arm.L': (6, 0, -3),
                      'forearm.L': (-18, 0, 0)})
    c = merge(STAND, {'spine': (5, 0, 0), 'chest': (1, 0, 0), 'head': (-8, 0, 0)})
    d = merge(STAND, {'chest': (2, 2, -1), 'neck': (-2, 2, 0), 'head': (-5, 7, -2), 'upper_arm.L': (2, 0, -1),
                      'forearm.L': (-12, 0, 0)})
    keys = []
    guess = None
    for f, p in ((1, a), (46, b), (91, c), (136, d)):
        r, rep = solve_arm(arm, p, pts, guess)
        guess = list(r['upper_arm.R']) + list(r['forearm.R'][:2]) + list(r['hand.R'])
        SOLVED.append((f, rep))
        print('elder idle', f, rep, flush=True)
        keys.append((f, merge(p, r), EASE))
    keys.append((181, keys[0][1], EASE))
    return Clip('idle', 180, keys, fps=FPS, ground=True)


def all_clips(arm, hand_report: dict) -> list[Clip]:
    pts = hand_report.get('prop_points_rest')
    if not pts:
        raise SystemExit('elder の動作には右手の杖（HAND["GRIP"]）の目印が要る')
    return [idle(arm, pts)]
