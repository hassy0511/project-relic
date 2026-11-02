"""haru_bs の比率・関節の位置・色（段 1 と段 2 の共通の基準）。

座標は Blender（Z が上、正面が -Y、本人の左が +X）、単位は m。原点は両足の間の床。
寸法は正面・真横の全身の絵（2048 角、髪先 123 px〜靴底 1925 px = 1.556 m）から測った
（docs/art_orders/W1_ハル_blender-skills試作.md の「絵の分析」）。
"""
from mathutils import Vector

HEIGHT = 1.556                 # 髪の先まで（haru_r と同じ高さ）
PX = HEIGHT / 1802.0           # 全身の絵の 1 画素（m）
FEET_PX = 1925                 # 全身の絵の靴底の行
FRONT_CX = 1024                # 正面の絵で x = 0 の列
SIDE_CX = 1000                 # 真横の絵で y = 0 の列


def mirror(v):
    return Vector((-v.x, v.y, v.z))


# ---------------------------------------------------------------- 関節（骨の頭の位置。段 2 の骨もこれを使う）
J = {}
J['root'] = Vector((0, 0, 0))
J['hips'] = Vector((0, -0.025, 0.80))
J['spine'] = Vector((0, -0.030, 0.90))
J['chest'] = Vector((0, -0.032, 1.00))
J['neck'] = Vector((0, -0.020, 1.150))
J['head'] = Vector((0, -0.015, 1.225))
J['head_top'] = Vector((0, -0.015, 1.48))
# 腕（A ポーズ、縦から約 30 度開く。手のひらは太ももへ向く）
J['shoulder.L'] = Vector((0.035, -0.025, 1.125))
J['upper_arm.L'] = Vector((0.135, -0.025, 1.105))
J['forearm.L'] = Vector((0.2595, -0.025, 0.9057))
J['hand.L'] = Vector((0.3761, -0.025, 0.7191))
J['hand_end.L'] = Vector((0.4757, -0.025, 0.6004))
# 脚
J['thigh.L'] = Vector((0.085, -0.025, 0.775))
J['shin.L'] = Vector((0.130, -0.018, 0.430))
J['foot.L'] = Vector((0.158, 0.005, 0.105))
J['toe.L'] = Vector((0.166, -0.150, 0.030))
for k in list(J):
    if k.endswith('.L'):
        J[k[:-2] + '.R'] = mirror(J[k])

# ---------------------------------------------------------------- 色（発注書の基準色。絵の画素の値と比べて採った）
def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


PAL = {
    'brick': '#B75B43',        # 上着・ズボン・足首のカフ
    'brick_dk': '#97462F',     # 上着の陰の側（塗りの 2 段目）
    'ivory': '#F3E9D2',        # シャツ・白磁の板
    'ivory_dk': '#DCCDB0',     # 白磁の陰の段
    'graphite': '#444641',     # 帯・手袋・底・枠・銃
    'graphite_lt': '#5A5C56',  # 銃・枠の明るい面
    'brass': '#A98749',        # バックル・レール・継ぎ目
    'umber': '#594333',        # 髪・襟・靴・すねの中央
    'umber_dk': '#46332A',     # 髪の内側・陰
    'amber': '#FFBC52',        # レンズ・膝の継ぎ目・銃の窓・光刃
    'amber_dk': '#E89A2E',     # レンズの奥の段
    'skin': '#E7B58D',
    'skin_dk': '#D69A72',      # 肌の陰（あごの下・耳の中）
    'iris': '#795334',
    'white': '#FFF8EA',
    'mouth': '#98684F',
}
RGB = {k: hexrgb(v) for k, v in PAL.items()}
