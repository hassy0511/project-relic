"""子どもの住人（ニコ）の動作（60fps）。ai_character.py --clips child で、humanoid_anims の 14 動作の代わりに焼く。

ゲームが使うもの（godot/scripts/view/props_view.gd）：
  idle    待機（3 秒の輪）。重心を左右へ移し、息で胸が動き、頭は少し傾く。腕は力を抜いて下ろし、体に遅れて揺れる
  walk    歩き（1 歩 0.5 秒）。腰の上下、胸と腰の逆のひねり、腕は脚と逆に振る
  run     走り（1 歩 0.27 秒）。前傾、肘を曲げて大きく振る、跳ねる
  cower   怖がってしゃがむ（遺構 B1 の救出の場面 ch1.r01）。膝を曲げて体を丸め、両手を顔の前に上げ、小さく震える
骨の回転の向きは humanoid_anims.py の頭の説明と同じ（腕・脚は X が負で前へ、すねは X が正で膝が曲がる、前腕は X が負で肘が
曲がる、上腕を横へ上げるのは右が Z 正・左が Z 負、背骨・胸・首・頭は X が正で前へ倒れ、Y が正で本人の左へひねる）。
作り方は SKILL 7b：姿勢を少し置いて等速でつながず、緩急（つなぎの interp・ease）と全身の追いかけ（腰 → 胸 → 腕の順に遅れる）で動かす。
足の裏は ground=True で床に着ける（接地点は ai_character.py --foot-contacts の値）。
"""
from __future__ import annotations

from lib.humanoid import Clip, Pose, mirror

FPS = 60
EASE = {'interp': 'SINE', 'ease': 'EASE_IN_OUT'}


def merge(*poses: Pose) -> Pose:
    out: Pose = {}
    for p in poses:
        out.update(p)
    return out


# 立った基準の姿勢：腕は体の横に力を抜いて（肘を少し曲げる）、背中は少し前へ
STAND: Pose = {
    'spine': (2, 0, 0), 'chest': (-1, 0, 0), 'head': (-2, 0, 0),
    'upper_arm.L': (2, 0, -3), 'forearm.L': (-16, 0, 0), 'hand.L': (0, 0, 4),
    'upper_arm.R': (2, 0, 3), 'forearm.R': (-16, 0, 0), 'hand.R': (0, 0, -4),
}


def idle() -> Clip:
    a = STAND
    # 重心を左へ（腰のひねりは小さく、胸と頭が遅れてついてくる）。息を吸って胸を起こす
    b = merge(STAND, {'spine': (2, 3, -1.5), 'chest': (-3, 2, -1), 'head': (-3, -4, 4),
                      'upper_arm.L': (-2, 0, -5), 'upper_arm.R': (4, 0, 4), 'forearm.L': (-20, 0, 0)})
    c = merge(STAND, {'chest': (0, 0, 0), 'head': (0, 1, 0)})
    d = merge(STAND, {'spine': (2, -3, 1.5), 'chest': (-3, -2, 1), 'head': (-1, 4, -3),
                      'upper_arm.L': (4, 0, -4), 'upper_arm.R': (-2, 0, 5), 'forearm.R': (-20, 0, 0)})
    keys = [(1, a, EASE), (46, b, EASE), (91, c, EASE), (136, d, EASE), (181, a, EASE)]
    return Clip('idle', 180, keys, fps=FPS, ground=True)


def walk() -> Clip:
    # 左足が前に着いた所（かかとから）→ 通り過ぎ（右足を振り出す）→ 右足が前 → 通り過ぎ
    contact: Pose = {
        'spine': (4, -4, 0), 'chest': (-1, 7, 0), 'head': (-2, -3, 0),
        'thigh.L': (-24, 0, 0), 'shin.L': (6, 0, 0), 'foot.L': (-6, 0, 0),
        'thigh.R': (16, 0, 0), 'shin.R': (14, 0, 0), 'foot.R': (8, 0, 0),
        'upper_arm.L': (18, 0, -4), 'forearm.L': (-14, 0, 0),
        'upper_arm.R': (-20, 0, 4), 'forearm.R': (-28, 0, 0),
    }
    passing: Pose = {
        'spine': (4, 0, 0), 'chest': (-1, 0, 0), 'head': (-2, 0, 0),
        'thigh.L': (-2, 0, 0), 'shin.L': (6, 0, 0), 'foot.L': (0, 0, 0),
        'thigh.R': (-14, 0, 0), 'shin.R': (42, 0, 0), 'foot.R': (-4, 0, 0),
        'upper_arm.L': (2, 0, -4), 'forearm.L': (-18, 0, 0),
        'upper_arm.R': (-2, 0, 4), 'forearm.R': (-20, 0, 0),
    }
    c2, p2 = mirror(contact), mirror(passing)
    keys = [(1, contact, EASE), (16, passing, EASE), (31, c2, EASE), (46, p2, EASE), (61, contact, EASE)]
    return Clip('walk', 60, keys, fps=FPS, ground=True, bob=[(1, 0.0), (16, 0.014), (31, 0.0), (46, 0.014), (61, 0.0)])


def run() -> Clip:
    contact: Pose = {
        'spine': (13, -6, 0), 'chest': (0, 10, 0), 'head': (-10, -5, 0),
        'thigh.L': (-46, 0, 0), 'shin.L': (18, 0, 0), 'foot.L': (-4, 0, 0),
        'thigh.R': (30, 0, 0), 'shin.R': (55, 0, 0), 'foot.R': (16, 0, 0),
        'upper_arm.L': (38, 0, -12), 'forearm.L': (-62, 0, 0),
        'upper_arm.R': (-42, 0, 12), 'forearm.R': (-74, 0, 0),
    }
    passing: Pose = {
        'spine': (13, 0, 0), 'chest': (0, 0, 0), 'head': (-10, 0, 0),
        'thigh.L': (0, 0, 0), 'shin.L': (28, 0, 0), 'foot.L': (6, 0, 0),
        'thigh.R': (-40, 0, 0), 'shin.R': (100, 0, 0), 'foot.R': (-6, 0, 0),
        'upper_arm.L': (6, 0, -12), 'forearm.L': (-66, 0, 0),
        'upper_arm.R': (-8, 0, 12), 'forearm.R': (-70, 0, 0),
    }
    c2, p2 = mirror(contact), mirror(passing)
    lift = {'lifted': ('foot.R',)}
    lift2 = {'lifted': ('foot.L',)}
    keys = [(1, contact), (9, passing, lift), (17, c2), (25, p2, lift2), (33, contact)]
    return Clip('run', 32, keys, fps=FPS, ground=True,
                bob=[(1, 0.0), (9, 0.045), (17, 0.0), (25, 0.045), (33, 0.0)])


def cower() -> Clip:
    """しゃがんで体を丸め、両手を顔の前へ。肩をすくめ、小さく震える（4 こまごとに左右へ 1〜2 度）"""
    base: Pose = {
        'spine': (22, 0, 0), 'chest': (14, 0, 0), 'neck': (-4, 0, 0), 'head': (-6, 0, 0),
        'shoulder.L': (0, 0, 8), 'shoulder.R': (0, 0, -8),
        'upper_arm.L': (-62, -18, 12), 'forearm.L': (-118, 0, 0), 'hand.L': (10, 0, 10),
        'upper_arm.R': (-62, 18, -12), 'forearm.R': (-118, 0, 0), 'hand.R': (10, 0, -10),
        'thigh.L': (-58, 0, -10), 'shin.L': (104, 0, 0), 'foot.L': (-32, 0, 0),
        'thigh.R': (-58, 0, 10), 'shin.R': (104, 0, 0), 'foot.R': (-32, 0, 0),
    }
    keys = []
    f = 1
    for i in range(18):
        s = 1 if i % 2 == 0 else -1
        p = dict(base)
        p['chest'] = (14 + (0.8 if i % 3 == 0 else 0.0), 1.5 * s, 0)
        p['head'] = (-6, -2.0 * s, 1.0 * s)
        p['upper_arm.L'] = (-62 + 1.5 * s, -18, 12)
        p['upper_arm.R'] = (-62 - 1.5 * s, 18, -12)
        keys.append((f, p, {'interp': 'SINE', 'ease': 'EASE_IN_OUT'}))
        f += 4
    keys.append((f, keys[0][1], {'interp': 'SINE', 'ease': 'EASE_IN_OUT'}))
    return Clip('cower', f - 1, keys, fps=FPS, ground=True)


def all_clips() -> list[Clip]:
    return [idle(), walk(), run(), cower()]
