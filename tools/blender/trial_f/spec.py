"""haru_f：寸法・関節・色見本（絵に cm の格子を重ねて読んだ値。measure.py）。

座標は Blender と同じ：x = 本人の左が正、y = 後ろが正（正面は -y）、z = 上。単位は m。
全身の絵：頭頂 125 行・足裏 1922 行 = 155 cm、中心 1024 列。真横の絵の前後は、絵の中心から 2.1 cm 後ろを 0 にした
（足の長さの真ん中が原点になる。ゲームの約束：原点は両足の間の床）。
"""
import numpy as np

HEIGHT = 1.55

# 色見本（発注書 spec_haru_3d.md の基準色と、絵から拾った陰の段）。名前 → hex
PALETTE = {
    'brick': '#B75B43', 'brick_dk': '#7E3F2E', 'ivory': '#F3E9D2', 'ivory_dk': '#D9CCB0',
    'graphite': '#444641', 'graphite_dk': '#33342F', 'brass': '#A98749', 'umber': '#594333',
    'hair': '#603C2E', 'hair_dk': '#3A2218', 'amber': '#F5AC40', 'skin': '#F0B58B',
    'boot': '#5B3B2D', 'white': '#FFF8EA', 'amber_dk': '#D9912E', 'gun': '#4A4C48',
    'hair_md': '#4E3024',
}
EMISSIVE = {'amber': '#5A3A0E', 'amber_dk': '#3C2609'}
SKIN_HEX = PALETTE['skin']

# 関節（左。右は x を反転）。骨は 親 → 子 の順
J = {
    'root': (0.0, 0.0, 0.0),
    'hips': (0.0, 0.0, 0.76),
    'spine': (0.0, 0.0, 0.87),
    'chest': (0.0, 0.005, 0.985),
    'neck': (0.0, 0.012, 1.135),
    'head': (0.0, 0.010, 1.205),
    'head_end': (0.0, 0.010, 1.50),
    'shoulder': (0.035, 0.025, 1.105),
    'upper_arm': (0.145, 0.040, 1.100),
    'forearm': (0.250, 0.056, 0.915),
    'hand': (0.358, 0.050, 0.748),
    'hand_end': (0.425, 0.046, 0.600),
    'thigh': (0.090, 0.004, 0.725),
    'shin': (0.150, 0.016, 0.410),
    'foot': (0.165, 0.040, 0.100),
    'foot_end': (0.182, -0.105, 0.020),
}


def jp(name, side=1):
    p = J[name]
    return np.array([p[0] * side, p[1], p[2]], dtype=float)


# 頭の中心（頭の部品の基準）と大きさ
HEAD_C = np.array([0.0, -0.008, 1.335])

# 骨の一覧：名前, 親, 根の位置, 先の位置（先は骨の向きだけを決める）
def bones():
    out = [('root', None, (0, 0, 0), (0, 0, 0.12)),
           ('hips', 'root', J['hips'], J['spine']),
           ('spine', 'hips', J['spine'], J['chest']),
           ('chest', 'spine', J['chest'], J['neck']),
           ('neck', 'chest', J['neck'], J['head']),
           ('head', 'neck', J['head'], J['head_end'])]
    hc = HEAD_C
    hair = {
        'hair.front': ((0.0, -0.105, 1.445), (0.0, -0.135, 1.36)),
        'hair.top': ((0.0, -0.02, 1.50), (0.02, -0.03, 1.565)),
        'hair.back.L': ((0.07, 0.10, 1.42), (0.10, 0.165, 1.35)),
        'hair.back.R': ((-0.07, 0.10, 1.42), (-0.10, 0.165, 1.35)),
        'hair.nape': ((0.0, 0.115, 1.30), (0.0, 0.125, 1.215)),
        'hair.side.L': ((0.125, 0.0, 1.40), (0.185, 0.02, 1.32)),
        'hair.side.R': ((-0.125, 0.0, 1.40), (-0.185, 0.02, 1.32)),
    }
    for k, (a, b) in hair.items():
        out.append((k, 'head', a, b))
    for s, sfx in ((1, '.L'), (-1, '.R')):
        m = lambda n: tuple(jp(n, s))
        out += [('shoulder' + sfx, 'chest', m('shoulder'), m('upper_arm')),
                ('upper_arm' + sfx, 'shoulder' + sfx, m('upper_arm'), m('forearm')),
                ('forearm' + sfx, 'upper_arm' + sfx, m('forearm'), m('hand')),
                ('hand' + sfx, 'forearm' + sfx, m('hand'), m('hand_end'))]
    for s, sfx in ((1, '.L'), (-1, '.R')):
        m = lambda n: tuple(jp(n, s))
        out += [('thigh' + sfx, 'hips', m('thigh'), m('shin')),
                ('shin' + sfx, 'thigh' + sfx, m('shin'), m('foot')),
                ('foot' + sfx, 'shin' + sfx, m('foot'), m('foot_end'))]
    out += [('pouch.L', 'hips', (0.135, -0.035, 0.845), (0.150, -0.035, 0.745)),
            ('pouch.R', 'hips', (-0.135, -0.005, 0.835), (-0.150, -0.005, 0.715))]
    return out


CLIPS = ['air', 'charge', 'combo1', 'combo2', 'combo3', 'dash', 'dead', 'drill', 'fall', 'hurt', 'idle', 'jump', 'lunge', 'run']
