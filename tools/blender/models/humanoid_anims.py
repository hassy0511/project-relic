"""人型の共通アニメーション（30fps）。

骨の回転の向き（確認済み）：
- 腕・脚（下向きの骨）：X がマイナスで前へ振る、プラスで後ろへ振る
- すね：X プラスで膝が曲がる。前腕：X マイナスで肘が曲がる
- 上腕を横に上げる：右は Z プラス、左は Z マイナス
- 背骨・胸・首・頭：X プラスで前に倒れる。Y プラスでキャラクターの左へひねる
主人公は右手に銃、左腕のガントレットから光刃を出す。
"""
from __future__ import annotations

from lib.humanoid import Clip, Pose, mirror

# 右手は銃を少し前に構えている
GUN_HOLD: Pose = {'upper_arm.R': (-10, 0, 8), 'forearm.R': (-35, 0, 0)}


def merge(*poses: Pose) -> Pose:
    out: Pose = {}
    for p in poses:
        out.update(p)
    return out


def idle() -> Clip:
    base = merge({'upper_arm.L': (0, 0, -8), 'forearm.L': (-12, 0, 0), 'spine': (2, 0, 0)}, GUN_HOLD)
    breathe = merge(base, {'chest': (-2, 0, 0), 'upper_arm.L': (0, 0, -10)})
    return Clip('idle', 60, [(1, base), (31, breathe), (61, base)])


def run() -> Clip:
    contact: Pose = {
        'spine': (12, 0, 0), 'chest': (0, -8, 0), 'head': (-8, 6, 0),
        'thigh.L': (-45, 0, 0), 'shin.L': (15, 0, 0),
        'thigh.R': (35, 0, 0), 'shin.R': (55, 0, 0),
        'upper_arm.L': (35, 0, -10), 'forearm.L': (-50, 0, 0),
        'upper_arm.R': (-30, 0, 10), 'forearm.R': (-70, 0, 0),
    }
    passing: Pose = {
        'spine': (12, 0, 0), 'chest': (0, 0, 0), 'head': (-8, 0, 0),
        'thigh.L': (0, 0, 0), 'shin.L': (25, 0, 0),
        'thigh.R': (-35, 0, 0), 'shin.R': (95, 0, 0),
        'upper_arm.L': (5, 0, -10), 'forearm.L': (-50, 0, 0),
        'upper_arm.R': (0, 0, 10), 'forearm.R': (-70, 0, 0),
    }
    c2 = mirror(contact)
    p2 = mirror(passing)
    # 右手は銃を持っているので、反対の足のときも振りを小さくする
    for p in (c2, p2):
        p['upper_arm.R'] = (p['upper_arm.R'][0] * 0.6, 0, 10)
        p['forearm.R'] = (-70, 0, 0)
    return Clip('run', 20, [(1, contact), (6, passing), (11, c2), (16, p2), (21, contact)],
                bob=[(1, 0.0), (6, 0.05), (11, 0.0), (16, 0.05), (21, 0.0)])


def jump() -> Clip:
    p = merge({
        'spine': (5, 0, 0), 'thigh.L': (-65, 0, 0), 'shin.L': (85, 0, 0), 'thigh.R': (-10, 0, 0), 'shin.R': (35, 0, 0),
        'upper_arm.L': (-50, 0, -25), 'forearm.L': (-30, 0, 0),
    }, GUN_HOLD)
    return Clip('jump', 8, [(1, p), (9, p)], loop=False)


def fall() -> Clip:
    a = merge({
        'spine': (-4, 0, 0), 'thigh.L': (-25, 0, 0), 'shin.L': (45, 0, 0), 'thigh.R': (10, 0, 0), 'shin.R': (30, 0, 0),
        'upper_arm.L': (-10, 0, -50), 'forearm.L': (-20, 0, 0), 'upper_arm.R': (-15, 0, 45), 'forearm.R': (-30, 0, 0),
    })
    b = merge(a, {'upper_arm.L': (-10, 0, -58), 'upper_arm.R': (-15, 0, 52)})
    return Clip('fall', 20, [(1, a), (11, b), (21, a)])


def dash() -> Clip:
    p = {
        'spine': (30, 0, 0), 'head': (-20, 0, 0), 'thigh.L': (-50, 0, 0), 'shin.L': (60, 0, 0),
        'thigh.R': (40, 0, 0), 'shin.R': (50, 0, 0),
        'upper_arm.L': (55, 0, -15), 'forearm.L': (-20, 0, 0), 'upper_arm.R': (50, 0, 15), 'forearm.R': (-30, 0, 0),
    }
    return Clip('dash', 7, [(1, p), (8, p)], loop=False)


def hurt() -> Clip:
    p = {
        'spine': (-20, 0, 0), 'head': (-20, 0, 0), 'upper_arm.L': (-20, 0, -40), 'upper_arm.R': (-20, 0, 40),
        'thigh.L': (-15, 0, 0), 'shin.L': (25, 0, 0),
    }
    return Clip('hurt', 8, [(1, p), (9, p)], loop=False)


def dead() -> Clip:
    a = {'spine': (-20, 0, 0), 'upper_arm.L': (-20, 0, -40), 'upper_arm.R': (-20, 0, 40)}
    b = {
        'spine': (45, 0, 0), 'head': (30, 0, 0), 'thigh.L': (-80, 0, 0), 'shin.L': (120, 0, 0),
        'thigh.R': (-70, 0, 0), 'shin.R': (125, 0, 0), 'upper_arm.L': (-30, 0, -20), 'upper_arm.R': (-30, 0, 20),
    }
    return Clip('dead', 18, [(1, a), (19, b)], loop=False, bob=[(1, 0.0), (19, -0.55)])


def drill() -> Clip:
    a = merge({
        'spine': (10, 12, 0), 'upper_arm.L': (-85, 0, -5), 'forearm.L': (-5, 0, 0),
        'thigh.L': (-25, 0, 0), 'shin.L': (20, 0, 0), 'thigh.R': (20, 0, 0), 'shin.R': (15, 0, 0),
    }, GUN_HOLD)
    b = merge(a, {'upper_arm.L': (-83, 0, -7), 'spine': (11, 12, 0)})
    return Clip('drill', 4, [(1, a), (3, b), (5, a)])


def stance(extra: Pose) -> Pose:
    """斬りの足構え"""
    return merge({'thigh.L': (-30, 0, 0), 'shin.L': (25, 0, 0), 'thigh.R': (25, 0, 0), 'shin.R': (20, 0, 0)}, GUN_HOLD,
                 extra)


def combo1() -> Clip:
    """右から左への横薙ぎ（左腕の光刃）"""
    start = stance({'chest': (5, -40, 0), 'upper_arm.L': (-70, 0, 45), 'forearm.L': (-40, 0, 0)})
    mid = stance({'chest': (8, 0, 0), 'upper_arm.L': (-85, 0, 0), 'forearm.L': (-5, 0, 0)})
    end = stance({'chest': (8, 35, 0), 'upper_arm.L': (-70, 0, -55), 'forearm.L': (-10, 0, 0)})
    return Clip('combo1', 9, [(1, start), (4, mid), (7, end), (10, end)], loop=False)


def combo2() -> Clip:
    """左から右への切り返し"""
    start = stance({'chest': (5, 35, 0), 'upper_arm.L': (-70, 0, -55), 'forearm.L': (-10, 0, 0)})
    mid = stance({'chest': (8, 0, 0), 'upper_arm.L': (-90, 0, 0), 'forearm.L': (-20, 0, 0)})
    end = stance({'chest': (8, -40, 0), 'upper_arm.L': (-75, 0, 50), 'forearm.L': (-50, 0, 0)})
    return Clip('combo2', 9, [(1, start), (4, mid), (7, end), (10, end)], loop=False)


def combo3() -> Clip:
    """振り下ろし（とどめ）"""
    start = stance({'spine': (-12, 0, 0), 'chest': (-5, 10, 0), 'upper_arm.L': (-150, 0, -32), 'forearm.L': (-15, 0, 0)})
    mid = stance({'spine': (10, 0, 0), 'upper_arm.L': (-100, 0, 0), 'forearm.L': (0, 0, 0)})
    end = stance({'spine': (28, 0, 0), 'head': (-15, 0, 0), 'upper_arm.L': (-35, 0, 0), 'forearm.L': (-5, 0, 0)})
    return Clip('combo3', 14, [(1, start), (5, start), (8, mid), (10, end), (15, end)], loop=False)


def air() -> Clip:
    start = {'chest': (0, -35, 0), 'upper_arm.L': (-70, 0, 45), 'forearm.L': (-40, 0, 0),
             'thigh.L': (-60, 0, 0), 'shin.L': (80, 0, 0), 'thigh.R': (-20, 0, 0), 'shin.R': (60, 0, 0)}
    end = dict(start, **{'chest': (5, 35, 0), 'upper_arm.L': (-70, 0, -55), 'forearm.L': (-10, 0, 0)})
    return Clip('air', 9, [(1, start), (5, end), (10, end)], loop=False)


def lunge() -> Clip:
    start = stance({'spine': (20, 0, 0), 'upper_arm.L': (30, 0, -10), 'forearm.L': (-60, 0, 0),
                    'thigh.L': (-50, 0, 0), 'shin.L': (40, 0, 0), 'thigh.R': (45, 0, 0), 'shin.R': (30, 0, 0)})
    end = stance({'spine': (25, 20, 0), 'upper_arm.L': (-95, 0, 0), 'forearm.L': (0, 0, 0),
                  'thigh.L': (-55, 0, 0), 'shin.L': (40, 0, 0), 'thigh.R': (40, 0, 0), 'shin.R': (10, 0, 0)})
    return Clip('lunge', 10, [(1, start), (5, end), (11, end)], loop=False)


def charge() -> Clip:
    """溜め斬り：大きく回転して薙ぎ払う"""
    start = stance({'spine': (5, -60, 0), 'chest': (0, -30, 0), 'upper_arm.L': (-60, 0, 70), 'forearm.L': (-50, 0, 0)})
    mid = stance({'spine': (10, 0, 0), 'chest': (0, 0, 0), 'upper_arm.L': (-80, 0, -20), 'forearm.L': (0, 0, 0)})
    end = stance({'spine': (10, 60, 0), 'chest': (0, 30, 0), 'upper_arm.L': (-70, 0, -80), 'forearm.L': (0, 0, 0)})
    return Clip('charge', 15, [(1, start), (5, start), (9, mid), (12, end), (16, end)], loop=False)


def all_clips() -> list[Clip]:
    return [idle(), run(), jump(), fall(), dash(), hurt(), dead(), drill(), combo1(), combo2(), combo3(), air(),
            lunge(), charge()]
