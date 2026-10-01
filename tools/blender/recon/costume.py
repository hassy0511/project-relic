"""服の硬い部品を、体の面に沿った別の形（殻）として作る（ハル：肩の板・膝当て・籠手・帯・ポーチ・手袋と靴のカフ・
太ももの板・背中の板・袖口）。

塗りでは直らない所（絵どうし・絵と形の食い違いで、板の縁がにじむ・別の絵の帯が板の上に載る）を、形で直す。
ゴーグル・ベルト・耳・番機・閂・ナゴミと同じく「別の形のものは、色を形から」：部品ごとに平らな 1 色なので、
縁は作りからくっきりする。

■ 形（build_all → ai_character.py の --costume）
  部品は「軸のまわりの円柱の座標」(s, t) の上の輪郭で決める：軸の点 a・向き d（t は a から d の向きへの長さ m）、
  基準の向き e0（s = 0、部品の中心の向き）、s は角度 × 名目の半径 RN（m）。輪郭は絵（正面・背面・真横）で測った
  多角形（凸）か、ぐるりと一周の帯（ring）。各点で軸から外へ光線を飛ばして体の面の半径 r を測り、なめらかにして、
  r + OFF（体から浮かす）＋ 厚み の所に上の面を置く。縁は BEVEL だけ下げ（面取り）、縁から体の中（r − SINK）まで壁を下ろす
  （底の面は作らない：体の中で見えない）。ポーチは箱。
  色は部品ごとに PALETTE の 1 色（材質 haru_parts の色見本の画像を UV で指す）。骨は部品が載る骨 1 本に重み 1（剛体）。
■ 下の体の塗り（cover_body → texture.py、flat.paint_body のあと）
  部品の真下（輪郭の中で、体の面が部品の内側の面の近く）は、下地の布の色（UNDER、無ければ周りの色）。
  輪郭のまわり MARGIN の帯では、部品の色（CLEAR：例 膝当ての白・暗い枠）だけを周りの色に替える（塗りの板が
  部品からはみ出して二重の縁にならない）。
座標は A ポーズの再構築の座標（texture.py のメッシュ・ai_character.py の --keep-frame の入力と同じ。本人の右は -X、正面は -Y）。
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

PALETTE = {
    'brick': '#B75B43', 'ivory': '#F3E9D2', 'graphite': '#444641', 'brass': '#A98749',
    'umber': '#594333', 'amber': '#FFBC52', 'skin': '#E7B58D',
}
NAMES = list(PALETTE)
CELLS = 8          # 色見本の画像：横に 8 区画（1 区画 32 画素）

# A ポーズの関節（joints.py の表、本人の左 = +X。右は x を反転）
J = {
    'upper_arm': (0.137, 0.0314, 1.105), 'forearm': (0.245, 0.0551, 0.912), 'hand': (0.335, 0.0302, 0.755),
    'hand_end': (0.4, 0.0045, 0.642), 'thigh': (0.095, 0.0038, 0.715), 'shin': (0.143, 0.0247, 0.395),
    'foot': (0.15, 0.0463, 0.09),
}
H = 0.011         # 殻の点の間隔（m）
# 体の重みを写す部品（ai_character.add_costume）：載る骨 1 本の剛体にすると、肩の上で体が突き抜ける
FOLLOW_BODY = ('shoulder_pad.R', 'shoulder_strap.R', 'strap.L', 'strap.R', 'hood_collar')
# 体の重みを写すとき腕の骨の重みを除く部品（肩ひも：わきの下の体の重みを写すと、腕を下ろしたとき胸の前の端が腕に
# 引かれて体から浮いた輪になった）
FOLLOW_TORSO_ONLY = ('strap.L', 'strap.R')
# 塗りだけの決まり（cover_body）：箱（x, y, z の範囲）の中の、clear の色を、同じ箱の中のほかの色で塗り直す
#   首の後ろ：絵では髪とえりで素肌は見えない。肌色の横の筋が残っていた（6 回目）
#   keep：この色（色見本からの距離 tol 以内）のほかは塗り直す（布と肌の混ざった色の筋も消える）。fill：決まった色で埋める
#   右肩のまわり：板の部品より外に残る絵の板の白（正面の絵の板は形の板より広い）を、れんが色に
BOX_RULES = [dict(name='neck_back_noskin', box=((-0.11, 0.11), (0.02, 0.2), (1.08, 1.188)),
                  keep=['brick', 'umber', 'graphite'], tol=0.03),
             dict(name='right_shoulder_noivory', box=((-0.34, -0.095), (-0.2, 0.2), (0.98, 1.25)), clear=['ivory'],
                  fill='brick'),
             # 右肩・背中の板のまわりに残る、白とれんがの混ざった色の細い縁（色見本では「れんが」になり上の決まりを
             # すり抜ける）：れんが・暗い灰・こげ茶のほかを近くのその色で塗り直す
             dict(name='right_shoulder_edges', box=((-0.34, -0.095), (-0.2, 0.2), (0.98, 1.25)),
                  keep=['brick', 'umber', 'graphite'], tol=0.03),
             dict(name='back_plate_edges', box=((-0.10, 0.10), (0.03, 0.25), (1.0, 1.15)),
                  keep=['brick', 'umber', 'graphite'], tol=0.03)]
TORSO_Z = (0.835, 1.10)   # 胴の決まりの高さ（帯の下に隠れる高さ〜えりの下）
SHIRT_X = (-0.040, 0.055)       # 正面のシャツの白を残す x の範囲（絵の正面で測った。上着の前の開き）
SHIRT_X_LOW = (-0.073, 0.089)   # 上着の裾より下（z < SHIRT_HEM_Z）のシャツの範囲
SHIRT_HEM_Z = 0.885
NECK_V_X = (-0.036, 0.052)      # 首の前の肌の V の範囲（シャツの上の縁の高さ。絵の正面）
NECK_V_SLOPE = 0.31             # V が上へ広がる割合（z 1.113 → 1.165 で x −0.052〜0.068）
NECK_V_TOP = 1.20               # 首の前の決まりの上の端（あごの下。顔は別の材質）
NECK_V_Z = (1.113, 1.165)       # シャツの上の縁・V の広がりの基準の高さ
LEG_TOP = 0.835          # 脚の決まりの上の端（帯の下に隠れる高さ。帯の下の縁は前 0.812・後ろ 0.822）
LEG_BANDS = (-0.050, 0.040)   # 膝の帯（暗い灰）の上・下の端（すねの軸に沿った膝からの長さ、m）
RIGHT_HAND_PART = True   # 右手を部品にする（6 回目、ai_character.py --hand-part）：右の手袋のカフは形を作らず、手首の前を肌に塗る


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def jp(name: str, side: float) -> np.ndarray:
    p = np.array(J[name], float)
    p[0] *= side
    return p


def unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(a, b, ref) -> dict:
    """軸 a → b、基準の向き ref（軸に直交させる）"""
    a = np.asarray(a, float)
    d = unit(np.asarray(b, float) - a)
    e0 = unit(np.asarray(ref, float) - d * np.dot(ref, d))
    e1 = np.cross(d, e0)
    return {'a': a, 'd': d, 'e0': e0, 'e1': e1}


def octagon(s0, s1, t0, t1, c) -> list:
    """角を c だけ切った長方形（凸の八角形、反時計回り）"""
    return [(s0 + c, t0), (s1 - c, t0), (s1, t0 + c), (s1, t1 - c), (s1 - c, t1), (s0 + c, t1), (s0, t1 - c),
            (s0, t0 + c)]


def circle(sc, tc, rad, n=12) -> list:
    return [(sc + rad * math.cos(2 * math.pi * k / n), tc + rad * math.sin(2 * math.pi * k / n)) for k in range(n)]


# ---------------------------------------------------------------- 部品の表

def pieces() -> list[dict]:
    """部品の一覧。数値は絵で測った（正面・背面・真横の絵の色の塊の範囲。本文の 5 回目を参照）"""
    P = []
    up = np.array([0.0, 0.0, 1.0])
    front = np.array([0.0, -1.0, 0.0])

    # 膝当て（両膝）：暗い枠＋白い板＋横の琥珀のボルト（暗い座金つき）。すねの軸、膝の関節から下へ t
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        k = jp('shin', side)
        fr = frame(k, jp('foot', side), front)
        fr['RN'] = 0.06
        P.append(dict(name='knee_frame' + sx, bone='shin' + sx, color='graphite', frame=fr,
                      outline=octagon(-0.066, 0.066, -0.082, 0.066, 0.026), off=0.004, thick=0.006, bevel=0.002,
                      under=None, clear=['ivory', 'graphite', 'amber'], margin=0.012, rmax=0.11))
        P.append(dict(name='knee_plate' + sx, bone='shin' + sx, color='ivory', frame=fr,
                      outline=octagon(-0.048, 0.048, -0.072, 0.056, 0.022), off=0.004, thick=0.013, bevel=0.003,
                      rmax=0.11))
        for sb in (-1.0, 1.0):
            P.append(dict(name=f'knee_washer{sx}{int(sb)}', bone='shin' + sx, color='graphite', frame=fr,
                          outline=circle(sb * 0.058, -0.004, 0.02), off=0.004, thick=0.008, bevel=0.002, rmax=0.11))
            P.append(dict(name=f'knee_bolt{sx}{int(sb)}', bone='shin' + sx, color='amber', frame=fr,
                          outline=circle(sb * 0.058, -0.004, 0.0125, 10), off=0.004, thick=0.016, bevel=0.003,
                          rmax=0.11))
        # 塗りに残る膝の横の琥珀の点（絵のボルト。部品のボルトと二重になる）を消す：琥珀だけ周りの色へ
        P.append(dict(name='knee_paint_bolts' + sx, bone='shin' + sx, color='amber', frame=fr, clear_only=True,
                      outline=octagon(0.02, 0.14, -0.05, 0.04, 0.01), clear=['amber', 'brass'], fill='graphite', margin=0.012,
                      rmax=0.11))
        P.append(dict(name='knee_paint_bolts2' + sx, bone='shin' + sx, color='amber', frame=fr, clear_only=True,
                      outline=octagon(-0.14, -0.02, -0.05, 0.04, 0.01), clear=['amber', 'brass'], fill='graphite', margin=0.012,
                      rmax=0.11))
        # 絵のボルトの円の縁（細い茶・黄土の輪）が膝の横（形のボルトより後ろ、真横の近く）に残る：膝の横は暗い裏地の色に
        # 決める（6 回目）
        P.append(dict(name='knee_hinge_dark' + sx, bone='shin' + sx, color='graphite', frame=fr, clear_only=True,
                      outline=octagon(0.03, 0.175, -0.05, 0.04, 0.012), under='graphite', rmax=0.11))
        P.append(dict(name='knee_hinge_dark2' + sx, bone='shin' + sx, color='graphite', frame=fr, clear_only=True,
                      outline=octagon(-0.175, -0.03, -0.05, 0.04, 0.012), under='graphite', rmax=0.11))
        # 靴のカフ（赤の厚い帯、z 0.152〜0.212。絵 haru_shoes.png の太い輪）。7 回目：靴は部品（下の boot_*）
        fb = frame(jp('shin', side), jp('foot', side), front)
        fb['RN'] = 0.05
        dz = -fb['d'][2]
        P.append(dict(name='boot_cuff' + sx, bone='shin' + sx, color='brick', frame=fb, ring=True,
                      t0=(k[2] - 0.212) / dz, t1=(k[2] - 0.150) / dz, off=0.002, thick=0.010, bevel=0.003,
                      rmax=0.09, n_ring=48, sink=0.015))   # 壁を深く：アキレス腱のくぼみで上の縁から脚との間のすき間が見えた
        # すねの白い側面の板（7 回目、絵：すねの中央は茶、白は内・外の細い側面の板。正面から約 70 度、上が尖る）。
        # 膝当ての下の縁（t 0.07）からカフの上（t 0.172）まで
        for sb in (-1.0, 1.0):
            sc = sb * 1.15 * fb['RN']
            t0, t1 = (k[2] - 0.322) / dz, (k[2] - 0.222) / dz
            P.append(dict(name=f'shin_plate{sx}{int(sb)}', bone='shin' + sx, color='ivory', frame=fb,
                          outline=[(sc - 0.011, t0), (sc + 0.011, t0), (sc + 0.029, t0 + 0.024), (sc + 0.024, t1 - 0.005),
                                   (sc + 0.019, t1), (sc - 0.019, t1), (sc - 0.024, t1 - 0.005), (sc - 0.029, t0 + 0.024)],
                          off=0.003, thick=0.007, bevel=0.0025, rmax=0.09))
        # 靴（7 回目：体の足を消して部品に。絵 haru_shoes.png と全身の絵）
        P += boot_pieces(side, sx)

    # 右肩の板（本人の右だけ）：上腕の軸（肩 → 肘）、外上の向きが中心。白い板＋下の縁の暗い帯
    sh, el = jp('upper_arm', -1.0), jp('forearm', -1.0)
    d = unit(el - sh)
    outv = unit(np.array([-1.0, 0.0, 0.25]))
    fr = frame(sh, el, outv)
    fr['RN'] = 0.055
    # 球の座標（肩の関節の少し下を中心に、外上の向きが極）：肩の上から上腕の外・前・後ろを 1 枚で覆う
    fsp = {'kind': 'sphere', 'a': sh + 0.03 * d, 'e0': unit(np.array([-0.86, 0.0, 0.51])),
           'e2': np.array([0.0, 1.0, 0.0]), 'RN': 0.06}
    fsp['e1'] = np.cross(fsp['e2'], fsp['e0'])
    fsp['d'] = fsp['e2']
    P.append(dict(name='shoulder_pad.R', bone='upper_arm.R', color='ivory', frame=fsp,
                  outline=octagon(-0.056, 0.058, -0.060, 0.060, 0.024), off=0.012, thick=0.008, bevel=0.004,
                  under='brick', clear=['ivory'], fill='brick', margin=0.04, rmax=0.12, rmin=0.03))
    P.append(dict(name='shoulder_strap.R', bone='upper_arm.R', color='graphite', frame=fr, ring=True,
                  t0=0.094, t1=0.116, off=0.003, thick=0.006, bevel=0.002, under='graphite', rmax=0.085))
    # 袖口の暗い帯（両腕、肩から腕の軸に沿って 17.7〜20.5cm）
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        fs = frame(jp('upper_arm', side), jp('forearm', side), front)
        fs['RN'] = 0.05
        P.append(dict(name='sleeve_cuff' + sx, bone='upper_arm' + sx, color='graphite', frame=fs, ring=True,
                      t0=0.176, t1=0.206, off=0.002, thick=0.005, bevel=0.0015, under='graphite', rmax=0.08))

    # 左の籠手：前腕の軸（肘 → 手首）。暗い帯（肘側・手首側）＋白い筒＋外側の真鍮のレールと琥珀の芯
    e, w = jp('forearm', 1.0), jp('hand', 1.0)
    Lf = float(np.linalg.norm(w - e))
    outl = unit(np.array([1.0, 0.0, 0.55]))
    fg = frame(e, w, outl)
    fg['RN'] = 0.04
    P.append(dict(name='gauntlet_top.L', bone='forearm.L', color='graphite', frame=fg, ring=True,
                  t0=0.012, t1=0.040, off=0.004, thick=0.007, bevel=0.002, under='skin', rmax=0.07))
    P.append(dict(name='gauntlet_body.L', bone='forearm.L', color='ivory', frame=fg, ring=True,
                  t0=0.036, t1=Lf - 0.030, off=0.004, thick=0.005, bevel=0.002, under='skin',
                  clear=['ivory', 'brass', 'amber'], margin=0.012, rmax=0.07))
    P.append(dict(name='gauntlet_bottom.L', bone='forearm.L', color='graphite', frame=fg, ring=True,
                  t0=Lf - 0.034, t1=Lf - 0.006, off=0.004, thick=0.008, bevel=0.002, under='skin', rmax=0.07))
    P.append(dict(name='gauntlet_rail.L', bone='forearm.L', color='brass', frame=fg,
                  outline=octagon(-0.016, 0.016, 0.022, Lf - 0.012, 0.006), off=0.009, thick=0.010, bevel=0.002,
                  rmax=0.07))
    P.append(dict(name='gauntlet_cell.L', bone='forearm.L', color='amber', frame=fg,
                  outline=octagon(-0.0075, 0.0075, 0.04, Lf - 0.03, 0.004), off=0.009, thick=0.016, bevel=0.002,
                  rmax=0.07))
    # 手袋のカフ（両手首）：暗い帯
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        e2, w2 = jp('forearm', side), jp('hand', side)
        L2 = float(np.linalg.norm(w2 - e2))
        fc = frame(e2, w2, front)
        fc['RN'] = 0.035
        if side < 0 and RIGHT_HAND_PART:
            # 右手は部品（recon/hand.py：手・指・カフ）。ここは塗りだけ：肘から手首までの前腕は肌（絵の右の前腕は
            # 手首のカフのほかは素肌。体の塗りに残る手袋の暗い色のぎざぎざの縁を消す。カフの部品の下も肌）
            P.append(dict(name='glove_cuff' + sx, bone='forearm' + sx, color='graphite', frame=fc, ring=True,
                          clear_only=True, t0=0.01, t1=L2 + 0.03, under='skin', rmax=0.07))
            continue
        t0 = L2 - 0.004 if side > 0 else L2 - 0.022
        P.append(dict(name='glove_cuff' + sx, bone='forearm' + sx, color='graphite', frame=fc, ring=True,
                      t0=t0, t1=L2 + 0.016, off=0.003, thick=0.006, bevel=0.002, under='graphite', rmax=0.06))

    # 帯：縦の軸のまわり。前 z 0.812〜0.856、後ろ 0.822〜0.872
    fw = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), front)
    fw['RN'] = 0.15
    P.append(dict(name='belt', bone='hips', color='graphite', frame=fw, ring=True,
                  t0=(0.812, 0.822), t1=(0.856, 0.872), off=0.003, thick=0.006, bevel=0.002, under=None,
                  clear=['graphite', 'brass'], margin=0.010, rmax=0.22, n_ring=120))
    # バックル：真鍮の枠（外 7.0 × 5.8cm）、中に帯の暗い色（板を上に重ねる）
    P.append(dict(name='buckle', bone='hips', color='brass', frame=fw,
                  outline=octagon(-0.035, 0.035, 0.806, 0.864, 0.006), off=0.010, thick=0.005, bevel=0.0015,
                  rmax=0.22))
    P.append(dict(name='buckle_in', bone='hips', color='graphite', frame=fw,
                  outline=octagon(-0.022, 0.022, 0.818, 0.852, 0.003), off=0.010, thick=0.0065, bevel=0.001,
                  rmax=0.22))
    P.append(dict(name='buckle_bar', bone='hips', color='brass', frame=fw,
                  outline=octagon(-0.004, 0.004, 0.818, 0.852, 0.001), off=0.010, thick=0.0085, bevel=0.001,
                  rmax=0.22))
    # 肩ひも（7 回目、両側）：背中（|x| 0.06〜0.105、z 0.965 から）→ 肩の上 → 胸の前（|x| 0.075〜0.12 → 下で 0.085〜0.115、z 約 1.0 まで）。
    # 左右の軸（x）のまわりの円柱の座標：s = 角度（上 = 0、前 = +）× RN、t = |x|。絵の正面・背面で測った
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        fst = frame((0.0, 0.015, 1.03), (side, 0.015, 1.03), up)
        fst['RN'] = 0.1
        if side < 0:      # 右：軸が −x 向きなので前後の角度の符号が逆になる
            sb, sf = 0.2085, -0.232
        else:
            sb, sf = -0.2085, 0.232
        sf = sf * 0.19 / 0.232      # 胸の前の端（わきの下に近づくと腕を下ろした姿勢で体から浮く）
        out = [(sb, 0.060), (sf, 0.085), (sf, 0.115), (sb, 0.105)]
        if side < 0:
            out = out[::-1]
        P.append(dict(name='strap' + sx, bone='chest', color='graphite', frame=fst, outline=out, off=0.002,
                      thick=0.005, bevel=0.0015, under='graphite', clear=['graphite'], margin=0.02, rmax=0.2,
                      env_rings=0))   # 細い帯：近所の最大を取ると、首の横のフードのふくらみから肩の上へ橋のように浮いた
    # 首の後ろのフードのえり（7 回目、絵 haru_neck.png の背面：れんがのえりが髪の先まで立つ）：首の軸のまわりの後ろ半分、
    # z 1.12〜1.215。首の後ろの塗りのまだら（UV の重なり、z 約 1.20）を形で覆う
    fh = frame((0.0, 0.02, 1.10), (0.0, 0.04, 1.30), (0.0, 1.0, 0.0))
    fh['RN'] = 0.06
    P.append(dict(name='hood_collar', bone='neck', color='brick', frame=fh,
                  outline=octagon(-0.095, 0.095, 0.022, 0.137, 0.012), off=0.003, thick=0.007, bevel=0.003,
                  rmax=0.10))
    # 背中の板（肩ひもの間、x ±0.057、z 1.037〜1.114）
    P.append(dict(name='back_plate', bone='chest', color='ivory',
                  frame=dict(frame((0.0, 0.02, 0.0), (0.0, 0.02, 1.0), (0.0, 1.0, 0.0)), RN=0.12),
                  outline=octagon(-0.056, 0.056, 1.037, 1.113, 0.008), off=0.004, thick=0.007, bevel=0.002,
                  under='brick', clear=['ivory'], fill='brick', margin=0.03, rmax=0.2))
    # 右の太ももの板：太ももの軸（股 → 膝）、前外の向き。z 0.755〜0.55（絵の正面・真横・背面）
    t, k = jp('thigh', -1.0), jp('shin', -1.0)
    ft = frame(t, k, unit(np.array([-0.8, -0.6, 0.0])))
    ft['RN'] = 0.085
    dz = -ft['d'][2]
    P.append(dict(name='thigh_panel.R', bone='thigh.R', color='ivory', frame=ft,
                  outline=octagon(-0.075, 0.070, (t[2] - 0.758) / dz, (t[2] - 0.548) / dz, 0.010), off=0.007,
                  thick=0.009, bevel=0.003, under='brick', clear=['ivory'], fill='brick', margin=0.02,
                  rmax=0.15))
    # ポーチ（帯の下、腰の横）：箱。縦の軸のまわりの角度（度、0 = 正面、+ = 本人の左）、高さ
    for name, ang, zc, size in (('pouch.R', -72.0, 0.79, (0.052, 0.030, 0.090)),
                                ('pouch.L', 88.0, 0.795, (0.055, 0.030, 0.085))):
        P.append(dict(name=name, bone='hips', color='graphite', box=True, frame=fw, ang=ang, zc=zc, size=size,
                      clear=['graphite'], margin=0.012, rmax=0.25))
    return P



# ---------------------------------------------------------------- 靴（7 回目）

BOOT_CUT = 0.176        # この高さより下の脚の体（足・靴）は消して、靴の部品に置き換える（カフの中で切る）
BOOT_RAMP = (0.095, 0.155)   # 靴の重み：この高さより下は foot に 1、上は shin に 1、間はなめらかに移す


def rrect(x0, x1, y0, y1, rf, rb, k=3) -> list:
    """角を丸めた長方形（上から見て反時計回り、x 右・y 後ろ）。rf：前（y0）の角、rb：後ろ（y1）の角の半径。
    角は k+1 点（k=3 → 30 度ずつの面：絵の面のある靴）"""
    pts = []
    for (cx, cy, r, a0) in ((x0 + rf, y0 + rf, rf, 180), (x1 - rf, y0 + rf, rf, 270),
                            (x1 - rb, y1 - rb, rb, 0), (x0 + rb, y1 - rb, rb, 90)):
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def boot_pieces(side: float, sx: str) -> list[dict]:
    """片足の靴（左の値で書き、右は x を反転）。部品は高さ z の断面（角の丸い長方形）を積んだ形（loft）。
    寸法：足の大きさ・軸は体の足の断面（全身の絵の外形から作った形）で測り、部品の割り付けは haru_shoes.png の真横・正面
    （靴底 前 3.3cm・後ろ 5.9cm、かかとと前の底の間に浅い切り欠き、白い爪先は甲の高さ 10.5cm まで、甲の暗い帯、茶の胴）"""
    X0, X1 = 0.088, 0.267          # 靴底の内・外（左足、m）
    YF, YB = -0.152, 0.131         # 爪先・かかと
    P = []

    def sec(z, x0, x1, y0, y1, rf, rb, k=3):
        return (z, rrect(x0, x1, y0, y1, rf, rb, k))

    # 靴底（暗い灰）：前の底・かかと（下に切り欠き）・全体の板・かかとの上がり
    sole = [sec(0.000, X0 + 0.004, X1 - 0.004, YF + 0.005, 0.004, 0.034, 0.004),
            sec(0.004, X0 + 0.001, X1 - 0.001, YF + 0.001, 0.010, 0.036, 0.004),
            sec(0.021, X0 + 0.001, X1 - 0.001, YF + 0.001, 0.046, 0.036, 0.004)]
    heel = [sec(0.000, X0 + 0.010, X1 - 0.010, 0.050, YB - 0.004, 0.004, 0.022),
            sec(0.004, X0 + 0.008, X1 - 0.008, 0.048, YB - 0.001, 0.004, 0.024),
            sec(0.021, X0 + 0.008, X1 - 0.008, 0.046, YB - 0.001, 0.004, 0.024)]
    plate = [sec(0.020, X0, X1, YF, YB, 0.037, 0.025),
             sec(0.030, X0, X1, YF, YB, 0.037, 0.025),
             sec(0.034, X0 + 0.003, X1 - 0.003, YF + 0.003, YB - 0.003, 0.034, 0.022)]
    riser = [sec(0.030, X0, X1, -0.030, YB, 0.006, 0.025),
             sec(0.055, X0, X1, 0.030, YB, 0.006, 0.025),
             sec(0.059, X0 + 0.003, X1 - 0.003, 0.036, YB - 0.003, 0.005, 0.022)]
    # 白い爪先：前は甲より低く、後ろの縁は斜め（下 y −0.018、上 y −0.048）
    toe = [sec(0.028, X0 + 0.004, X1 - 0.004, YF + 0.005, -0.018, 0.034, 0.004),
           sec(0.086, X0 + 0.004, X1 - 0.004, YF + 0.005, -0.036, 0.034, 0.004),
           sec(0.097, X0 + 0.009, X1 - 0.009, YF + 0.015, -0.042, 0.030, 0.004),
           sec(0.106, X0 + 0.016, X1 - 0.016, YF + 0.030, -0.048, 0.024, 0.003)]
    # 茶の胴：低い所は爪先の中に隠れ、甲で前へ傾き、カフの中で脚の太さになる
    upper = [sec(0.028, X0 + 0.007, X1 - 0.009, -0.100, 0.124, 0.02, 0.030, 4),
             sec(0.090, X0 + 0.008, X1 - 0.016, -0.064, 0.124, 0.02, 0.030, 4),
             sec(0.110, 0.100, 0.232, -0.050, 0.121, 0.022, 0.030, 4),
             sec(0.130, 0.103, 0.221, -0.036, 0.117, 0.026, 0.032, 4),
             sec(0.150, 0.106, 0.213, -0.024, 0.114, 0.034, 0.036, 4),
             sec(0.188, 0.107, 0.209, -0.020, 0.111, 0.036, 0.040, 4)]
    # 甲の暗い帯（絵：カフの下から爪先の上まで、正面の幅の約 55%）
    def yf_up(z):
        zs = [u[0] for u in upper]
        ys = [min(p[1] for p in u[1]) for u in upper]
        return float(np.interp(z, zs, ys))
    xc = 0.159
    strap = []
    for z in (0.100, 0.112, 0.130, 0.150, 0.166):
        y0 = yf_up(z)
        strap.append(sec(z, xc - 0.031, xc + 0.031, y0 - 0.0055, y0 + 0.016, 0.008, 0.002))
    for name, color, secs in (('sole', 'graphite', sole), ('heel', 'graphite', heel), ('sole_plate', 'graphite', plate),
                              ('sole_riser', 'graphite', riser), ('toe_cap', 'ivory', toe), ('upper', 'umber', upper),
                              ('tongue', 'graphite', strap)):
        if side < 0:   # 右足：x を反転（並びも逆にして反時計回りを保つ）
            secs = [(z, [(-x, y) for (x, y) in pts][::-1]) for z, pts in secs]
        P.append(dict(name=f'boot_{name}{sx}', bone='foot' + sx, color=color, loft=secs,
                      ramp=('shin' + sx, 'foot' + sx)))
    return P


def build_loft(spec: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """断面（高さ z ごとの凸の多角形、同じ点の数）を積んだ閉じた形。上下はふた。外向きにそろえる"""
    secs = spec['loft']
    n = len(secs[0][1])
    V = np.array([(x, y, z) for z, pts in secs for (x, y) in pts], float)
    F = []
    for j in range(len(secs) - 1):
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            c, d = (j + 1) * n + (i + 1) % n, (j + 1) * n + i
            F += [(a, b, c), (a, c, d)]
    # ふた：中心の点からの扇
    for j, flip in ((0, True), (len(secs) - 1, False)):
        ci = len(V)
        V = np.vstack([V, V[j * n:(j + 1) * n].mean(0)])
        for i in range(n):
            a, b = j * n + i, j * n + (i + 1) % n
            F.append((ci, b, a) if flip else (ci, a, b))
    F = np.array(F)
    p = V[F]
    vol = np.einsum('ij,ij->i', p[:, 0], np.cross(p[:, 1], p[:, 2])).sum() / 6
    if vol < 0:
        F = F[:, [0, 2, 1]]
    return V, F, {}


def boot_cut_mask(co: np.ndarray) -> np.ndarray:
    """消す体の頂点（脚の BOOT_CUT より下）"""
    return (co[:, 2] < BOOT_CUT) & (np.abs(co[:, 0]) > 0.03) & (np.abs(co[:, 0]) < 0.32)


def ramp_w(z: np.ndarray) -> np.ndarray:
    """靴の頂点の shin の重み（0 = foot）"""
    f = np.clip((z - BOOT_RAMP[0]) / (BOOT_RAMP[1] - BOOT_RAMP[0]), 0, 1)
    return f * f * (3 - 2 * f)


# ---------------------------------------------------------------- 幾何

def inside_poly(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    x, y = pts[:, 0], pts[:, 1]
    ins = np.zeros(len(pts), bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        c = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0)
        ins ^= c
    return ins


def poly_dist(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """輪郭までの距離（符号なし）"""
    best = np.full(len(pts), np.inf)
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ab = b - a
        tt = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        best = np.minimum(best, np.linalg.norm(pts - (a + np.outer(tt, ab)), axis=1))
    return best


def t_range(spec: dict, s: np.ndarray, which: str) -> np.ndarray:
    v = spec[which]
    if isinstance(v, tuple):   # 前・後ろの値を角度で混ぜる（帯の傾き）
        th = s / spec['frame']['RN']
        f = (1 - np.cos(th)) / 2
        return v[0] * (1 - f) + v[1] * f
    return np.full(len(s), float(v))


def param_of(spec: dict, pos: np.ndarray):
    fr = spec['frame']
    rel = pos - fr['a']
    if fr.get('kind') == 'sphere':
        r = np.linalg.norm(rel, axis=1)
        b = np.arcsin(np.clip((rel @ fr['e2']) / np.maximum(r, 1e-9), -1, 1))
        a = np.arctan2(rel @ fr['e1'], rel @ fr['e0'])
        return a * fr['RN'], b * fr['RN'], r
    t = rel @ fr['d']
    x, y = rel @ fr['e0'], rel @ fr['e1']
    th = np.arctan2(y, x)
    return th * fr['RN'], t, np.hypot(x, y)


def ray_dirs(fr: dict, s: np.ndarray, t: np.ndarray):
    if fr.get('kind') == 'sphere':   # 経度 a（e0 → e1）、緯度 b（e2 の向き）
        a, b = s / fr['RN'], t / fr['RN']
        dirs = (np.outer(np.cos(a) * np.cos(b), fr['e0']) + np.outer(np.sin(a) * np.cos(b), fr['e1'])
                + np.outer(np.sin(b), fr['e2']))
        return np.repeat(fr['a'][None], len(s), 0), dirs
    th = s / fr['RN']
    org = fr['a'] + np.outer(t, fr['d'])
    dirs = np.outer(np.cos(th), fr['e0']) + np.outer(np.sin(th), fr['e1'])
    return org, dirs


def cast(bvh, org: np.ndarray, dirs: np.ndarray, rmax: float) -> np.ndarray:
    from mathutils import Vector
    r = np.full(len(org), np.nan)
    for i in range(len(org)):
        hit = bvh.ray_cast(Vector(org[i]), Vector(dirs[i]), rmax)
        if hit[0] is not None:
            r[i] = hit[3]
    return r


def smooth_r(r: np.ndarray, edges: np.ndarray, iters: int = 4) -> np.ndarray:
    n = len(r)
    for _ in range(40):           # 当たらなかった点は隣の平均で埋める
        bad = np.isnan(r)
        if not bad.any():
            break
        acc = np.zeros(n)
        cnt = np.zeros(n)
        for a, b in ((edges[:, 0], edges[:, 1]), (edges[:, 1], edges[:, 0])):
            ok = ~np.isnan(r[b])
            np.add.at(acc, a[ok], r[b[ok]])
            np.add.at(cnt, a[ok], 1)
        fill = bad & (cnt > 0)
        r[fill] = acc[fill] / cnt[fill]
    r = np.nan_to_num(r, nan=float(np.nanmedian(r)) if np.isfinite(r).any() else 0.05)
    for _ in range(iters):
        acc = np.zeros(n)
        cnt = np.zeros(n)
        np.add.at(acc, edges[:, 0], r[edges[:, 1]])
        np.add.at(acc, edges[:, 1], r[edges[:, 0]])
        np.add.at(cnt, edges[:, 0], 1)
        np.add.at(cnt, edges[:, 1], 1)
        r = 0.5 * r + 0.5 * acc / np.maximum(cnt, 1)
    return r


def tri_edges(F: np.ndarray) -> np.ndarray:
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e.sort(1)
    return np.unique(e, axis=0)


def sample_patch(spec: dict):
    """凸の輪郭の中の (s, t) の点と三角形。最初の nb 個が輪郭の上（反時計回り）。
    点の間隔は H か、小さい部品（ボルト・レールの芯）では短い辺の 1/4"""
    from scipy.spatial import Delaunay
    poly = np.array(spec['outline'], float)
    H = min(globals()['H'], float((poly.max(0) - poly.min(0)).min()) / 4)
    bnd = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        m = max(1, int(math.ceil(np.linalg.norm(b - a) / H)))
        for k in range(m):
            bnd.append(a + (b - a) * k / m)
    bnd = np.array(bnd)
    lo, hi = poly.min(0), poly.max(0)
    gs, gt = np.meshgrid(np.arange(lo[0], hi[0] + H, H), np.arange(lo[1], hi[1] + H, H))
    g = np.stack([gs.ravel(), gt.ravel()], 1)
    g = g[inside_poly(g, poly) & (poly_dist(g, poly) > 0.45 * H)]
    pts = np.concatenate([bnd, g])
    tri = Delaunay(pts).simplices
    cen = pts[tri].mean(1)
    tri = tri[inside_poly(cen, poly) | (poly_dist(cen, poly) < 1e-6)]
    # 反時計回りにそろえる
    p = pts[tri]
    cr = (p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1]) - (p[:, 1, 1] - p[:, 0, 1]) * (p[:, 2, 0] - p[:, 0, 0])
    tri[cr < 0] = tri[cr < 0][:, [0, 2, 1]]
    loops = [np.arange(len(bnd))]
    return pts, tri, loops


def sample_ring(spec: dict):
    fr = spec['frame']
    n = spec.get('n_ring', 64)
    th = np.arange(n) * 2 * math.pi / n
    th = np.where(th > math.pi, th - 2 * math.pi, th)
    s = th * fr['RN']
    t0, t1 = t_range(spec, s, 't0'), t_range(spec, s, 't1')
    m = max(3, int(math.ceil(float(np.max(t1 - t0)) / H)) + 1)
    f = np.linspace(0, 1, m)
    S = np.repeat(s[None, :], m, 0)
    T = t0[None, :] + (t1 - t0)[None, :] * f[:, None]
    pts = np.stack([S.ravel(), T.ravel()], 1)
    idx = np.arange(m * n).reshape(m, n)
    tris = []
    for j in range(m - 1):
        for i in range(n):
            a, b, c, d = idx[j, i], idx[j, (i + 1) % n], idx[j + 1, (i + 1) % n], idx[j + 1, i]
            tris += [(a, b, c), (a, c, d)]
    loops = [idx[0], idx[-1][::-1]]
    return pts, np.array(tris), loops


def build_shell(spec: dict, bvh) -> tuple[np.ndarray, np.ndarray, dict]:
    fr = spec['frame']
    pts, tri, loops = sample_ring(spec) if spec.get('ring') else sample_patch(spec)
    org, dirs = ray_dirs(fr, pts[:, 0], pts[:, 1])
    r = cast(bvh, org, dirs, spec.get('rmax', 0.2))
    edges = tri_edges(tri)
    r = smooth_r(r, edges, 0)
    raw = np.clip(r, spec.get('rmin', 0.0), spec.get('rmax', 1.0))
    # 包む面：近所の最大（2 輪）→ なめらかに → 元の半径より内へは入れない（体の凸凹が板を突き抜けない）
    env = raw.copy()
    for _ in range(spec.get('env_rings', 2)):
        m = env.copy()
        np.maximum.at(m, edges[:, 0], env[edges[:, 1]])
        np.maximum.at(m, edges[:, 1], env[edges[:, 0]])
        env = m
    env = smooth_r(env, edges, 4)
    r = np.maximum(env, raw)
    n = len(pts)
    bmask = np.zeros(n, bool)
    for lp in loops:
        bmask[lp] = True
    top = r + spec['off'] + spec['thick'] - np.where(bmask, spec.get('bevel', 0.0), 0.0)
    V = [org + dirs * top[:, None]]
    F = [tri]
    sink = spec.get('sink', 0.004)
    for lp in loops:
        base = sum(len(v) for v in V)
        bot = org[lp] + dirs[lp] * (r[lp] - sink)[:, None]
        V.append(bot)
        k = len(lp)
        for i in range(k):
            j = (i + 1) % k
            ti, tj = lp[i], lp[j]
            bi, bj = base + i, base + j
            F.append(np.array([[ti, bi, bj], [ti, bj, tj]]))
    info = {'r': r, 'pts': pts}
    return np.concatenate(V), np.concatenate(F), info


def build_box(spec: dict, bvh) -> tuple[np.ndarray, np.ndarray, dict]:
    fr = spec['frame']
    ang = math.radians(spec['ang'])
    s = np.array([ang * fr['RN']])
    t = np.array([spec['zc']])
    org, dirs = ray_dirs(fr, s, t)
    r = cast(bvh, org, dirs, spec.get('rmax', 0.25))
    r0 = float(r[0]) if np.isfinite(r[0]) else 0.15
    w, dep, h = spec['size']
    rad = dirs[0]
    up = fr['d']
    tan = np.cross(up, rad)
    out = []
    faces = []
    # 本体と、上の蓋（少し大きく前へ出る）
    for (cw, cd, ch, zo) in ((w, dep, h, 0.0), (w + 0.006, dep + 0.006, h * 0.32, h * 0.36)):
        c = org[0] + rad * (r0 + cd / 2 - 0.006) + up * zo
        base = sum(len(o) for o in out)
        corners = []
        for sz in (-1, 1):
            for sy in (-1, 1):
                for sx in (-1, 1):
                    corners.append(c + tan * sx * cw / 2 + rad * sy * cd / 2 + up * sz * ch / 2)
        out.append(np.array(corners))
        q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for a, b, cc, d in q:
            faces.append((base + a, base + b, base + cc))
            faces.append((base + a, base + cc, base + d))
    V = np.concatenate(out)
    F = np.array(faces)
    # 外向きにそろえる（箱の中心から面の中心への向き）
    for k in range(0, len(F), 12):
        cen = V[F[k:k + 12]].reshape(-1, 3).mean(0)
        for i in range(k, k + 12):
            p = V[F[i]]
            nrm = np.cross(p[1] - p[0], p[2] - p[0])
            if nrm @ (p.mean(0) - cen) < 0:
                F[i] = F[i][[0, 2, 1]]
    return V, F, {'r': np.array([r0]), 'pts': np.stack([s, t], 1)}


def build_all(verts: np.ndarray, tris: np.ndarray, out_npz: str | None = None, skip: tuple = ()) -> dict:
    """部品の形をすべて作る（skip の名前の部品は作らない：右手を部品にしたときの右の手袋のカフ）。
    返り値：{V, F, color（面ごとの色の番号）, bone（頂点ごとの骨の名前の番号）, bones, names}"""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([tuple(v) for v in verts], [tuple(int(i) for i in t) for t in tris])
    Vs, Fs, cols, vb, pn, sw = [], [], [], [], [], []
    bones = []
    report = {}
    off = 0
    for spec in pieces():
        if spec.get('clear_only') or spec['name'] in skip:   # 塗りだけを直す範囲（形は作らない）
            continue
        if spec.get('loft'):
            V, F, _ = build_loft(spec)
        else:
            V, F, _ = build_box(spec, bvh) if spec.get('box') else build_shell(spec, bvh)
        if spec['bone'] not in bones:
            bones.append(spec['bone'])
        Vs.append(V)
        Fs.append(F + off)
        cols.append(np.full(len(F), NAMES.index(spec['color'])))
        vb.append(np.full(len(V), bones.index(spec['bone'])))
        if spec.get('ramp'):      # 靴：shin の重み（高さで foot からなめらかに）
            if spec['ramp'][0] not in bones:
                bones.append(spec['ramp'][0])
            sw.append(ramp_w(V[:, 2]))
        else:
            sw.append(np.full(len(V), -1.0))
        pn.append(np.full(len(F), len(report)))
        report[spec['name']] = len(F)
        off += len(V)
    res = {'V': np.concatenate(Vs), 'F': np.concatenate(Fs), 'color': np.concatenate(cols),
           'vbone': np.concatenate(vb), 'bones': np.array(bones), 'piece': np.concatenate(pn),
           'shin_w': np.concatenate(sw),
           'names': np.array(list(report))}
    if out_npz:
        np.savez(out_npz, **res)
        with open(os.path.splitext(out_npz)[0] + '.json', 'w') as fp:
            json.dump({'tris': int(len(res['F'])), 'pieces': report}, fp, indent=1)
    return res


# ---------------------------------------------------------------- 下の体の塗り

def cover_body(pos: np.ndarray, col: np.ndarray, verts: np.ndarray, tris: np.ndarray) -> dict:
    """部品の下・まわりの体の色を替える（texture.py の res['pos']・res['col']。col は sRGB 0..1、その場で書き換える）"""
    from mathutils.bvhtree import BVHTree
    from scipy.spatial import cKDTree
    bvh = BVHTree.FromPolygons([tuple(v) for v in verts], [tuple(int(i) for i in t) for t in tris])
    pal = np.stack([hex_rgb(PALETTE[n]) for n in NAMES])
    lab = np.argmin(((col[:, None, :] - pal[None]) ** 2).sum(-1), 1)
    under = np.full(len(pos), -1)        # 部品の真下：決まった色（-2 = 周りの色）
    clear = np.zeros(len(pos), bool)     # まわりの帯：部品の色だけ周りの色へ
    stats = {}
    for spec in pieces():
        if not spec.get('under') and not spec.get('clear'):
            continue
        s, t, r = param_of(spec, pos)
        fr = spec['frame']
        near = r < spec.get('rmax', 0.2) + 0.02
        if spec.get('box'):
            ang = math.radians(spec['ang'])
            w, dep, h = spec['size']
            ds = np.abs(s - ang * fr['RN'])
            dt = np.abs(t - spec['zc'])
            ins = near & (ds < w / 2) & (dt < h / 2)
            band = near & (ds < w / 2 + spec['margin']) & (dt < h / 2 + spec['margin'])
        else:
            if spec.get('ring'):
                t0, t1 = t_range(spec, s, 't0'), t_range(spec, s, 't1')
                ins0 = (t > t0) & (t < t1)
                dist = np.where(ins0, 0.0, np.minimum(np.abs(t - t0), np.abs(t - t1)))
            else:
                poly = np.array(spec['outline'], float)
                st = np.stack([s, t], 1)
                cand = near & (np.abs(s) < 4) & (t > poly[:, 1].min() - 0.06) & (t < poly[:, 1].max() + 0.06)
                ins0 = np.zeros(len(pos), bool)
                dist = np.full(len(pos), np.inf)
                ci = np.nonzero(cand)[0]
                ins0[ci] = inside_poly(st[ci], poly)
                dist[ci] = np.where(ins0[ci], 0.0, poly_dist(st[ci], poly))
            # 体の面が部品の内側の面の近くにある所だけ（同じ向きの奥の面・別の手足は除く）
            org, dirs = ray_dirs(fr, s, t)
            cand = np.nonzero(near & (dist < spec.get('margin', 0.0) + 1e-9))[0]
            ok = np.zeros(len(pos), bool)
            if len(cand):
                rr = cast(bvh, org[cand], dirs[cand], spec.get('rmax', 0.2) + 0.03)
                ok[cand] = np.isfinite(rr) & (np.abs(rr - r[cand]) < 0.006)
            ins = ok & ins0
            band = ok & (dist < spec.get('margin', 0.0))
        if spec.get('under'):
            under[ins] = NAMES.index(spec['under'])
        elif spec.get('clear') and not spec.get('clear_only'):
            under[ins & (under == -1)] = -2
        if spec.get('clear'):
            cl = np.isin(lab, [NAMES.index(c) for c in spec['clear']])
            if spec.get('fill'):      # 決まった色で埋める（近い色の写しだと放射状の筋になる所）
                fm = band & cl & (under < 0)
                under[fm] = NAMES.index(spec['fill'])
            else:
                clear |= band & cl
        stats[spec['name']] = int(ins.sum())
    for rule in BOX_RULES:
        (x0, x1), (y0, y1), (z0, z1) = rule['box']
        inb = ((pos[:, 0] > x0) & (pos[:, 0] < x1) & (pos[:, 1] > y0) & (pos[:, 1] < y1)
               & (pos[:, 2] > z0) & (pos[:, 2] < z1))
        if 'keep' in rule:
            kp = np.isin(lab, [NAMES.index(c) for c in rule['keep']])
            dpal = np.linalg.norm(col - pal[lab], axis=1)
            cl = inb & ~(kp & (dpal < rule['tol'])) & (under < 0)
        else:
            cl = inb & np.isin(lab, [NAMES.index(c) for c in rule['clear']]) & (under < 0)
        src = inb & ~cl
        if rule.get('fill'):
            under[cl] = NAMES.index(rule['fill'])
        elif cl.any() and src.any():
            tree = cKDTree(pos[src])
            _, nn = tree.query(pos[cl], k=1)
            col[cl] = col[np.nonzero(src)[0][nn]]
            lab[cl] = lab[np.nonzero(src)[0][nn]]
        stats[rule['name']] = int(cl.sum())
    # 脚の決まり（7 回目）：帯より下の脚は、絵の色を使わず高さの決まりだけで塗る（絵どうしの食い違いの白・赤・暗い色の
    # 切れ端が残らない）。すねの軸に沿った膝からの長さ t で：t < LEG_BANDS[0] はズボンのれんが、膝の帯は暗い灰、
    # その下（すね）は茶。太ももの板・膝当て・すねの板・カフ・靴は形の部品
    # 腕・手（A ポーズで x 0.237 より外、z 0.55 より上）を含めない
    leg = (pos[:, 2] < LEG_TOP) & (np.abs(pos[:, 0]) < np.where(pos[:, 2] > 0.54, 0.20, 0.30))
    for side in (1.0, -1.0):
        m = leg & (pos[:, 0] * side > 0)
        k, f = jp('shin', side), jp('foot', side)
        t = (pos[m] - k) @ unit(f - k)
        lab_leg = np.where(t < LEG_BANDS[0], NAMES.index('brick'),
                           np.where(t < LEG_BANDS[1], NAMES.index('graphite'), NAMES.index('umber')))
        under[np.nonzero(m)[0]] = lab_leg
    stats['leg_rule_texels'] = int(leg.sum())
    # 胴・上腕の決まり（7 回目）：上着の胴（帯の下に隠れる高さ〜えりの下）・肩のまわり・上腕（肩〜袖口）は、肩ひも・
    # 背中の板・肩の板・袖口・フードのえりを形の部品にしたので、絵の色を使わず決まりだけで塗る：正面のシャツの範囲
    # （絵の正面で測った SHIRT_X・裾より下は SHIRT_X_LOW、前の面）は白、ほかはれんが（横の絵の肩ひもの切れ端・
    # 板の白の縁・境目の混ぜ色の細い線が残らない）
    x, z = pos[:, 0], pos[:, 2]
    tor = (z > TORSO_Z[0]) & (z < TORSO_Z[1]) & (np.abs(x) < 0.15)
    tor |= (z > TORSO_Z[0]) & (z < 1.15) & (np.abs(x) < 0.15) & (pos[:, 1] > 0.03)      # 背中はえりの下まで
    tor |= (z > 0.95) & (z < 1.20) & (np.abs(x) > 0.075) & (np.abs(x) < 0.30)           # 肩のまわり（顔・髪より下）
    tor |= (z > 1.10) & (z < 1.20) & (np.abs(x) > 0.045) & (pos[:, 1] > -0.02)           # 首の横〜肩の上（フード）
    for side in (1.0, -1.0):
        a, b = jp('upper_arm', side), jp('forearm', side)
        d = unit(b - a)
        rel = pos - a
        t = rel @ d
        rad = np.linalg.norm(rel - np.outer(t, d), axis=1)
        tor |= (t > -0.02) & (t < 0.176) & (rad < 0.085) & (x * side > 0.10)
    shirt = (pos[:, 1] < -0.02) & (z < TORSO_Z[1]) & np.where(
        z > SHIRT_HEM_Z, (x > SHIRT_X[0]) & (x < SHIRT_X[1]), (x > SHIRT_X_LOW[0]) & (x < SHIRT_X_LOW[1]))
    tb = tor & (under < 0)
    under[tb] = np.where(shirt[tb], NAMES.index('ivory'), NAMES.index('brick'))
    # 首の前の開き（シャツの上の縁〜えりの下、前の面）：肌の V（絵の正面で測った NECK_V_X）、その下の縁までシャツ、横はれんが
    # V は上へ行くほど広がる（えりの縁が斜め）。あごの下（NECK_V_TOP）まで、V の中は肌・外はれんが
    nk = (z >= TORSO_Z[1]) & (z < NECK_V_TOP) & (pos[:, 1] < -0.02) & (np.abs(x) < 0.15) & (under < 0)
    dz = np.clip(z - NECK_V_Z[0], 0.0, None)
    in_v = (x > NECK_V_X[0] - NECK_V_SLOPE * dz) & (x < NECK_V_X[1] + NECK_V_SLOPE * dz)
    nk_col = np.where(in_v & (z > NECK_V_Z[0]), NAMES.index('skin'),
                      np.where((x > SHIRT_X[0]) & (x < SHIRT_X[1]), NAMES.index('ivory'), NAMES.index('brick')))
    under[nk] = nk_col[nk]
    tb = tb | nk
    stats['torso_rule_texels'] = int(tb.sum())
    fixed = under >= 0
    col[fixed] = pal[under[fixed]]
    lab[fixed] = under[fixed]
    todo = (under == -2) | (clear & ~fixed)
    src = ~todo & ~fixed
    if todo.any() and src.any():
        tree = cKDTree(pos[src])
        _, nn = tree.query(pos[todo], k=1)
        si = np.nonzero(src)[0][nn]
        col[todo] = col[si]
    stats['under_texels'] = int(fixed.sum())
    stats['cleared_texels'] = int(todo.sum())
    return stats


def palette_image(path: str) -> str:
    from PIL import Image
    img = np.zeros((32, 32 * CELLS, 3), np.uint8)
    for i, n in enumerate(NAMES):
        img[:, i * 32:(i + 1) * 32] = (hex_rgb(PALETTE[n]) * 255).round().astype(np.uint8)
    Image.fromarray(img).save(path)
    return path


def palette_uv(color_idx: np.ndarray) -> np.ndarray:
    """色の番号 → UV（Blender の UV、区画の中心）"""
    return np.stack([(color_idx + 0.5) / CELLS, np.full(len(color_idx), 0.5)], 1)
