"""仮のハル（MVP 用）。

Codex の設定画が届くまでの代役。単純な形を骨に丸ごと割り当てた「剛体スキニング」で作る。
寸法と骨の構成は本番と同じ（身長 1.55m、標準の人型の骨）なので、アニメーションはそのまま本番に移せる。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib import common as C  # noqa: E402
from lib import humanoid as H  # noqa: E402
from models import humanoid_anims as A  # noqa: E402

HEIGHT = 1.55


def build() -> None:
    C.reset_scene()
    arm = H.build_armature(HEIGHT, 'HaruRig')
    j = lambda name, side=1: H.joint(name, HEIGHT, side)  # noqa: E731

    skin = C.material('skin', C.hex_color('#e8b48a'))
    jacket = C.material('jacket', C.hex_color('#c9a46a'))
    scarf = C.material('scarf', C.hex_color('#b5452f'))
    pants = C.material('pants', C.hex_color('#4a4238'))
    boots = C.material('boots', C.hex_color('#3a2e24'))
    hair = C.material('hair', C.hex_color('#3b2a20'))
    frame = C.material('frame', C.hex_color('#ece6da'), roughness=0.35)
    glow = C.material('relic_glow', C.hex_color('#ffb23e'), emission=4.0)
    metal = C.material('metal', C.hex_color('#6b6760'), metallic=0.6, roughness=0.4)

    parts = []

    def add(obj, bone):
        H.bind_part(obj, bone, arm)
        parts.append(obj)

    def mid(a, b):
        return tuple((x + y) / 2 for x, y in zip(a, b))

    def length(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    # 胴体
    add(C.box('pelvis', mid(j('hips'), j('spine')), (0.30, 0.18, 0.18), pants, bevel=0.02), 'hips')
    add(C.box('belly', mid(j('spine'), j('chest')), (0.28, 0.17, 0.18), jacket, bevel=0.02), 'spine')
    add(C.box('torso', mid(j('chest'), j('neck')), (0.34, 0.20, 0.20), jacket, bevel=0.03), 'chest')
    add(C.box('chest_plate', (0, -0.105, j('chest')[2] + 0.09), (0.22, 0.04, 0.14), frame, bevel=0.01), 'chest')
    add(C.box('chest_glow', (0, -0.128, j('chest')[2] + 0.09), (0.10, 0.01, 0.03), glow), 'chest')
    add(C.box('back_unit', (0, 0.12, j('chest')[2] + 0.07), (0.18, 0.06, 0.20), frame, bevel=0.015), 'chest')
    add(C.box('belt', (0, 0, j('hips')[2] + 0.02), (0.31, 0.19, 0.04), boots), 'hips')
    add(C.cylinder('scarf', (0, 0, j('neck')[2] + 0.01), 0.085, 0.07, scarf, vertices=10), 'neck')

    # 頭
    hz = j('head')[2]
    add(C.sphere('head', (0, -0.005, hz + 0.105), 0.115, skin, segments=12, scale=(0.95, 1.0, 1.05)), 'head')
    add(C.sphere('hair', (0, 0.015, hz + 0.14), 0.122, hair, segments=10, scale=(1.0, 1.0, 0.85)), 'head')
    add(C.box('goggle_band', (0, 0, hz + 0.19), (0.25, 0.25, 0.03), boots), 'head')
    add(C.box('goggle', (0, -0.115, hz + 0.19), (0.16, 0.04, 0.05), metal), 'head')
    add(C.box('visor_emitter', (0.115, -0.02, hz + 0.1), (0.03, 0.06, 0.05), frame), 'head')
    # 目（向きが分かるように）
    add(C.box('eye.L', (0.04, -0.108, hz + 0.105), (0.025, 0.01, 0.035), boots), 'head')
    add(C.box('eye.R', (-0.04, -0.108, hz + 0.105), (0.025, 0.01, 0.035), boots), 'head')

    for side, s in ((1, '.L'), (-1, '.R')):
        ua, fa, hd, he = j('upper_arm', side), j('forearm', side), j('hand', side), j('hand_end', side)
        add(C.box('upper_arm' + s, mid(ua, fa), (0.085, 0.09, length(ua, fa) + 0.02), jacket, bevel=0.01), 'upper_arm' + s)
        add(C.box('forearm' + s, mid(fa, hd), (0.075, 0.08, length(fa, hd)), skin if side == -1 else frame, bevel=0.01), 'forearm' + s)
        add(C.box('hand' + s, mid(hd, he), (0.06, 0.07, 0.09), skin), 'hand' + s)
        th, sh, ft, to = j('thigh', side), j('shin', side), j('foot', side), j('toe', side)
        add(C.box('thigh' + s, mid(th, sh), (0.12, 0.13, length(th, sh)), pants, bevel=0.01), 'thigh' + s)
        add(C.box('shin' + s, mid(sh, ft), (0.10, 0.11, length(sh, ft)), pants, bevel=0.01), 'shin' + s)
        add(C.box('shin_guard' + s, (sh[0], -0.06, (sh[2] + ft[2]) / 2 + 0.03), (0.09, 0.03, 0.2), frame), 'shin' + s)
        add(C.box('boot' + s, (ft[0], -0.035, 0.045), (0.11, 0.21, 0.09), boots, bevel=0.01), 'foot' + s)
        add(C.box('heel_thruster' + s, (ft[0], 0.075, 0.07), (0.07, 0.04, 0.05), glow), 'foot' + s)

    # 左腕のガントレット（光刃の射出口）
    fl, hl = j('forearm', 1), j('hand', 1)
    add(C.box('gauntlet', mid(fl, hl), (0.10, 0.11, 0.16), frame, bevel=0.015), 'forearm.L')
    add(C.box('blade_emitter', (hl[0] + 0.01, -0.05, hl[2] + 0.04), (0.03, 0.03, 0.06), glow), 'forearm.L')
    # 右手の銃「スパーク」（手に持つ。腕と一体化させない）
    hr = j('hand', -1)
    add(C.box('spark_body', (hr[0], -0.08, hr[2] - 0.03), (0.05, 0.22, 0.07), metal, bevel=0.01), 'hand.R')
    add(C.box('spark_cell', (hr[0], -0.04, hr[2] + 0.01), (0.03, 0.06, 0.03), glow), 'hand.R')

    body = C.join(parts, 'Haru')
    H.finalize_skin(body, arm)
    H.bake_clips(arm, A.all_clips())


if __name__ == '__main__':
    build()
    out = os.path.join(C.REPO, 'public', 'assets', 'models', 'haru_proxy.glb')
    C.export_glb(out)
    if '--render' in sys.argv:
        C.render_views(os.path.join(C.REPO, 'art', 'renders', 'haru_proxy'), (0, 0, HEIGHT / 2), HEIGHT)
    print('wrote', out)
