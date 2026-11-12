"""haru_f：重みの決まり（位置から骨の重みを決める関数）。自動の重みは使わない。"""
from __future__ import annotations

import numpy as np

from .geo import norm, smoothstep
from .spec import J, jp


def _clean(w):
    w = {k: v for k, v in w.items() if v > 0.004}
    t = sum(w.values())
    return {k: v / t for k, v in w.items()}


def torso_w(p):
    z = p[2]
    a = smoothstep(0.875, 0.945, z)      # hips → spine（ベルトの上）
    b = smoothstep(0.955, 1.035, z)      # spine → chest
    c = smoothstep(1.125, 1.165, z)      # chest → neck
    d = smoothstep(1.19, 1.225, z)       # neck → head
    return _clean({'hips': 1 - a, 'spine': a * (1 - b), 'chest': b * (1 - c), 'neck': c * (1 - d), 'head': d})


def arm_w(p, side, shoulder_mix=0.5, soft=1.0):
    sfx = '.L' if side > 0 else '.R'
    S, E, W, T = jp('upper_arm', side), jp('forearm', side), jp('hand', side), jp('hand_end', side)
    a1, a2, a3 = norm(E - S), norm(W - E), norm(T - W)
    s = float(np.dot(p - S, a1))
    w_up = smoothstep(-0.05 * soft, 0.04 * soft, s)
    w_fore = smoothstep(-0.032 * soft, 0.032 * soft, float(np.dot(p - E, norm(a1 + a2))))
    w_hand = smoothstep(-0.014, 0.014, float(np.dot(p - W, norm(a2 + a3))))
    rest = (1 - w_up) * (1 - w_fore) * (1 - w_hand)
    return _clean({'hand' + sfx: w_hand, 'forearm' + sfx: (1 - w_hand) * w_fore,
                   'upper_arm' + sfx: (1 - w_hand) * (1 - w_fore) * w_up,
                   'shoulder' + sfx: rest * shoulder_mix, 'chest': rest * (1 - shoulder_mix)})


def leg_w(p, side, hip_lo=0.63, hip_hi=0.745, knee=0.035, ankle=0.02):
    sfx = '.L' if side > 0 else '.R'
    H, K, A, T = jp('thigh', side), jp('shin', side), jp('foot', side), jp('foot_end', side)
    a1, a2 = norm(K - H), norm(A - K)
    w_th = 1.0 - smoothstep(hip_lo, hip_hi, p[2])
    w_sh = smoothstep(-knee, knee, float(np.dot(p - K, norm(a1 + a2))))
    w_ft = smoothstep(-ankle, ankle, float(np.dot(p - A, a2)))
    return _clean({'foot' + sfx: w_ft, 'shin' + sfx: (1 - w_ft) * w_sh, 'thigh' + sfx: (1 - w_ft) * (1 - w_sh) * w_th,
                   'hips': (1 - w_ft) * (1 - w_sh) * (1 - w_th)})


def side_of(p):
    return 1 if p[0] >= 0 else -1
