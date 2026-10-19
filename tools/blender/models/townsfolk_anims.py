"""町の住人のキット（townsfolk.py）の待機の動作（60fps）。子どもは child_anims（待機・歩き・走り・しゃがむ）を使う。

  adult  大人の待機（3 秒の輪）：重心を左右へ移し、息で胸が動き、頭はゆっくり左右を見る。腕は力を抜いて下ろす
  elder  老人の待機（4 秒の輪）：背を丸めて（胸・首を前へ、頭は上げて相手を見る）、膝を少し曲げる。ゆっくりした息と小さな揺れ
骨の回転の向きは humanoid_anims.py の頭の説明と同じ（背骨・胸・首・頭は X が正で前へ倒れ、Y が正で本人の左へひねる。
上腕を横へ上げるのは右が Z 正・左が Z 負、前腕は X が負で肘が曲がる）。作り方は SKILL 7b（緩急と全身の追いかけ）。
設定の pose（{骨: [x, y, z]}）は基準の姿勢に足す（腕を少し開く・頭を傾けるなど、人ごとの癖）。
"""
from __future__ import annotations

from lib.humanoid import Clip, Pose

FPS = 60
EASE = {'interp': 'SINE', 'ease': 'EASE_IN_OUT'}


def merge(*poses: Pose) -> Pose:
    out: Pose = {}
    for p in poses:
        out.update(p)
    return out


def add(base: Pose, extra: dict) -> Pose:
    out = dict(base)
    for k, v in extra.items():
        x, y, z = out.get(k, (0.0, 0.0, 0.0))
        out[k] = (x + v[0], y + v[1], z + v[2])
    return out


ADULT: Pose = {
    'spine': (1, 0, 0), 'chest': (-1, 0, 0), 'head': (-2, 0, 0),
    'upper_arm.L': (2, 0, 3), 'forearm.L': (-12, 0, 0), 'hand.L': (0, 0, 3),
    'upper_arm.R': (2, 0, -3), 'forearm.R': (-12, 0, 0), 'hand.R': (0, 0, -3),
}

ELDER: Pose = {
    'spine': (6, 0, 0), 'chest': (12, 0, 0), 'neck': (8, 0, 0), 'head': (-18, 0, 0),
    'upper_arm.L': (-8, 0, 2), 'forearm.L': (-22, 0, 0), 'hand.L': (0, 0, 4),
    'upper_arm.R': (-8, 0, -2), 'forearm.R': (-22, 0, 0), 'hand.R': (0, 0, -4),
    'thigh.L': (-6, 0, 0), 'shin.L': (10, 0, 0), 'foot.L': (-4, 0, 0),
    'thigh.R': (-6, 0, 0), 'shin.R': (10, 0, 0), 'foot.R': (-4, 0, 0),
}


def idle_adult(extra: dict) -> Clip:
    a = add(ADULT, extra)
    b = add(merge(ADULT, {'spine': (1, 3, -1.5), 'chest': (-2, 2, -1), 'head': (-3, -5, 3),
                          'upper_arm.L': (0, 0, 4), 'upper_arm.R': (3, 0, -2), 'forearm.R': (-15, 0, 0)}), extra)
    c = add(merge(ADULT, {'chest': (0, 0, 0), 'head': (0, 1, 0)}), extra)
    d = add(merge(ADULT, {'spine': (1, -3, 1.5), 'chest': (-2, -2, 1), 'head': (-1, 5, -3),
                          'upper_arm.L': (3, 0, 2), 'upper_arm.R': (0, 0, -4), 'forearm.L': (-15, 0, 0)}), extra)
    keys = [(1, a, EASE), (46, b, EASE), (91, c, EASE), (136, d, EASE), (181, a, EASE)]
    return Clip('idle', 180, keys, fps=FPS, ground=True)


def idle_elder(extra: dict) -> Clip:
    a = add(ELDER, extra)
    b = add(merge(ELDER, {'chest': (10, 2, -1), 'neck': (8, 2, 0), 'head': (-16, -6, 2), 'upper_arm.L': (-6, 0, 3)}), extra)
    c = add(merge(ELDER, {'chest': (13, 0, 0), 'head': (-20, 0, 0)}), extra)
    d = add(merge(ELDER, {'chest': (10, -2, 1), 'neck': (8, -2, 0), 'head': (-16, 6, -2), 'upper_arm.R': (-6, 0, -3)}), extra)
    keys = [(1, a, EASE), (61, b, EASE), (121, c, EASE), (181, d, EASE), (241, a, EASE)]
    return Clip('idle', 240, keys, fps=FPS, ground=True)


def all_clips(kind: str, extra: dict | None = None) -> list[Clip]:
    extra = {k: tuple(v) for k, v in (extra or {}).items()}
    if kind == 'elder':
        return [idle_elder(extra)]
    return [idle_adult(extra)]
