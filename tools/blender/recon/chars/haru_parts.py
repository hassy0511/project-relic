"""ハル（haru）の服の部品と塗りの決まり（costume.py が読み込む。キャラクターごとの部品の設定）。

costume.py の道具（frame・octagon・circle・rrect・unit・jp・param_of）は、読み込みのときにこのモジュールへ渡される
（import しないで使える）。ここに書くもの：
  PALETTE            部品の色見本（名前 → spec の hex）。CELLS（色見本の区画の数、既定 8）
  J                  A ポーズの関節（joints.py の表、本人の左 = +X）
  pieces()           部品の一覧（costume.py の本文の書式）
  boot_pieces()      靴の部品（pieces() が呼ぶ）、BOOT_CUT・BOOT_RAMP（体の足を消す高さ・靴の重みの移し方）
  FOLLOW_BODY・FOLLOW_TORSO_ONLY・BOX_RULES・GOGGLE_STRAP（ai_character.py・cover_body が読む）
  body_rules()       決まりの塗り（cover_body の最後：脚・胴・首の色を決まりで決める）
  FRAME_GROUPS・FRAME_PAINT・frame_paint_rule()  外装フレームの段（群ごとに別の物体にする部品と、その下の塗り。ai_character.py）
  HAND               手の部品の寸法（hand.py）
値は 2026-10 まで costume.py・hand.py にあったハルの値のまま（移しただけ）。
"""
from __future__ import annotations

import math

import numpy as np

PALETTE = {
    'brick': '#B75B43', 'ivory': '#F3E9D2', 'graphite': '#444641', 'brass': '#A98749',
    'umber': '#594333', 'amber': '#FFBC52', 'skin': '#E7B58D',
}
NAMES = list(PALETTE)

# A ポーズの関節（joints.py の表、本人の左 = +X。右は x を反転）
J = {
    'upper_arm': (0.137, 0.0314, 1.105), 'forearm': (0.245, 0.0551, 0.912), 'hand': (0.335, 0.0302, 0.755),
    'hand_end': (0.4, 0.0045, 0.642), 'thigh': (0.095, 0.0038, 0.715), 'shin': (0.143, 0.0247, 0.395),
    'foot': (0.15, 0.0463, 0.09),
}
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
NECK_SIDE_LINE = (1.165, 1.2, -0.04, 1.225)   # 首の横のえりの縁：z = a + b·(y − c)、上限 d（前 1.165 → 後ろ 1.225）
LEG_TOP = 0.835          # 脚の決まりの上の端（帯の下に隠れる高さ。帯の下の縁は前 0.812・後ろ 0.822）
LEG_BANDS = (-0.050, 0.040)   # 膝の帯（暗い灰）の上・下の端（すねの軸に沿った膝からの長さ、m）
HOOD_FRONT_S = 0.135     # フードのえりの前の端（首の軸のまわりの角度 × 0.06。後ろから約 130 度）
KNEE_FRONT_S = 0.085     # 膝当ての下でれんがにする前の範囲（膝当ての枠の s ±0.066 より少し広く）
RIGHT_HAND_PART = True   # 右手を部品にする（6 回目、ai_character.py --hand-part）：右の手袋のカフは形を作らず、手首の前を肌に塗る


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
        P.append(dict(name='strap' + sx, bone='chest', color='graphite', frame=fst, outline=out, off=0.005,
                      thick=0.005, bevel=0.0015, under='graphite', clear=['graphite'], margin=0.02, rmax=0.2,
                      env_rings=0, h=0.0045, smooth_iters=16, raw_tol=0.0))
        # 8 回目：点の間隔 11mm と体の面の凸凹で、前の縁・下の端が段になった → 間隔 4.5mm、面をよくならす   # 細い帯：近所の最大を取ると、首の横のフードのふくらみから肩の上へ橋のように浮いた
    # 首の後ろのフードのえり（7 回目、絵 haru_neck.png の背面：れんがのえりが髪の先まで立つ）：首の軸のまわりの後ろ半分、
    # z 1.12〜1.215。首の後ろの塗りのまだら（UV の重なり、z 約 1.20）を形で覆う
    fh = frame((0.0, 0.02, 1.10), (0.0, 0.04, 1.30), (0.0, 1.0, 0.0))
    fh['RN'] = 0.06
    # 8 回目：前の横まで延ばす（首の横の肌とれんがの境が塗りの段になっていた。絵の正面のえりは V の横まで回る）。
    # 前の端は低く（V の縁へ下がる）。部品の下はれんが、その上の首の横は肌（cover_body の首の横の決まり）
    P.append(dict(name='hood_collar', bone='neck', color='brick', frame=fh,
                  outline=[(-0.090, 0.022), (0.090, 0.022), (HOOD_FRONT_S, 0.030), (HOOD_FRONT_S, 0.068),
                           (0.095, 0.130), (0.083, 0.137), (-0.083, 0.137), (-0.095, 0.130), (-HOOD_FRONT_S, 0.068),
                           (-HOOD_FRONT_S, 0.030)],
                  off=0.003, thick=0.007, bevel=0.003, under='brick', rmax=0.10))
    # ゴーグルのヒモ（8 回目）：前は髪の形（hair.strap_field）の帯を塗っていたので、房に割られた波打つ帯に見えた。
    # 今は髪の上を一周する一定の幅・厚みの帯の部品（build_goggle_strap）。中心の高さは絵（右真横・背面）のとおり、
    # こめかみ（ゴーグルの枠の横、y −0.035・z 1.418）から後ろ（y 0.145・z 1.35）へ下がり、後ろは水平
    P.append(dict(name='goggle_strap', bone='head', color='graphite', goggle_strap=True, **GOGGLE_STRAP))
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



# axis：頭の縦の軸 (x, y)。y/z：中心の高さの決まり（y0 → y1 で z0 → z1、その外は一定）。half：幅の半分、thick：厚み、
# off：髪の外の面からのすき間。ends：両端の y（ゴーグルの枠の横に差し込む）。smooth_deg：外の面の当てはめのなめらかさ
GOGGLE_STRAP = dict(axis=(0.0, 0.03), y=(-0.035, 0.145), z=(1.418, 1.35), half=0.0125, thick=0.0045, off=0.0015,
                    ends_y=-0.065, end_x=(0.1095, 0.1185), end_deg=30.0, smooth_deg=14.0, n=160, rmax=0.25, bevel=0.0012, win_deg=25.0, pct=40.0,
                    push_fall=0.008, push_gap=0.001, push_y_min=-0.085)


# ---------------------------------------------------------------- 決まりの塗り（cover_body から）

def body_rules(pos: np.ndarray, col: np.ndarray, lab: np.ndarray, under: np.ndarray, ins: dict, stats: dict) -> None:
    """部品の下の塗り（cover_body）のあとで、脚・胴・首の色を決まりで決める（under に色の番号を書く）。
    ins：部品の名前 → 部品の真下の texel の印"""
    collar_ins = ins.get('hood_collar', np.zeros(len(pos), bool))
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
        # 8 回目：膝当ての下の太ももの側（関節より上の前）はズボンのれんが。膝を深く曲げる（倒れ 125 度）と、すねに付いた
        # 膝当ての上の半分が太ももから離れ、その下の暗い帯がぎざぎざの暗い形で見えた（暗い帯は横・後ろだけ）
        kspec = next(q for q in pieces() if q['name'] == 'knee_frame' + ('.L' if side > 0 else '.R'))
        ks, kt, kr = param_of(kspec, pos[m])
        under_pad = (np.abs(ks) < KNEE_FRONT_S) & (kt < 0.0) & (kr < 0.13)
        lab_leg = np.where(under_pad & (t < LEG_BANDS[1]), NAMES.index('brick'), lab_leg)
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
    # 首の横（8 回目）：上の決まりは z 1.20 の水平の線で切っていたので、あごの下の寝た面で肌とれんがの境が段になった。
    # 絵 haru_neck.png のとおり、フードのえりの縁は後ろ（フードのえりの部品の上の端）から前の V へ斜めに下がる線にし、
    # その上は肌（髪の茶・暗い色はそのまま）
    y = pos[:, 1]
    sn = (z > 1.13) & (z < 1.26) & (np.abs(x) > 0.028) & (np.abs(x) < 0.10) & (y > -0.13) & (y < 0.035)
    zline = np.clip(NECK_SIDE_LINE[0] + NECK_SIDE_LINE[1] * (y - NECK_SIDE_LINE[2]), 1.14, NECK_SIDE_LINE[3])
    skin_ok = np.isin(lab, [NAMES.index('skin'), NAMES.index('brick'), NAMES.index('ivory')]) | (under >= 0)
    # 首の横・前：フードのえりの部品の下はれんが（部品の under）、シャツの上の縁（z 1.123）より上で部品の外は肌（絵の正面：
    # えりの前の端の間は肌）。境は部品の縁の下に隠れる
    up = sn & (z > NECK_V_Z[0] + 0.010) & ~collar_ins & skin_ok & ~(nk & (under == NAMES.index('ivory')))
    lo_ = sn & (z < zline) & (z <= NECK_V_Z[0] + 0.010) & (y > -0.07) & ~(nk & in_v) & ~collar_ins
    under[up] = NAMES.index('skin')
    under[lo_] = NAMES.index('brick')
    stats['neck_side_texels'] = int((up | lo_).sum())
    tb = tb | up | lo_
    stats['torso_rule_texels'] = int(tb.sum())


# ---------------------------------------------------------------- 外装フレーム〈ヴェスティージ〉の段（2026-10-07）

# 第 1 章でフレームは段ごとに付く（胴 → 左腕 → 脚）。ここに書いた部品は ai_character.py が群ごとに別の物体
# （同じ骨・同じ重みの skinned mesh。名前は群の名前）にし、ゲーム（player_view.gd の set_frame_parts）が付いていない群を隠す。
# 名前の頭が一致する部品がその群（.L/.R・番号つきもまとめて）。ここに無い部品（上着の袖口・帯・ポーチ・手袋とカフ・
# フードのえり・ゴーグルとヒモ・右の太ももの板・靴とカフ・手・銃）は作業着として 'Haru' に残る
#   胴（Frame_core）：背中の板（動力部）・右肩の板と下の固定帯・胸の肩ひも（背中から肩を回る 2 本）
#   腕（Frame_arm）：左の籠手（光刃を出す）
#   脚（Frame_legs）：膝当て（枠・板・座金・琥珀の継ぎ目）・すねの側板
FRAME_GROUPS = {
    'Frame_core': ('back_plate', 'shoulder_pad.R', 'shoulder_strap.R', 'strap.L', 'strap.R'),
    'Frame_arm': ('gauntlet_',),
    'Frame_legs': ('knee_frame', 'knee_plate', 'knee_washer', 'knee_bolt', 'shin_plate'),
}
# 群の下の体の塗り：フレームを外した作業着に、板の下にしか意味のない色（肩ひもの下の暗い灰・膝の暗い固定帯・すねの中央の
# 暗い茶＝絵の「暗いフレーム」）が残らないようにする。ai_character.py は、範囲の体の面を元の塗りのまま群の物体に写し
# （体の面から少し浮かせた殻。群を見せると今までと同じ見た目）、体のテクスチャの範囲の画素を fill の色にする
#   reach：部品からこの距離（m）以内で、いちばん近い部品がこの群の部品の体（A ポーズ）。rule：frame_paint_rule の範囲
#   keep：範囲の中で残す色（色見本の名前。この色どうしの混ざった色も残す）。ほかの色（と混ざった縁の色）は fill に。
#         keep が空なら範囲の画素を全部 fill に
FRAME_PAINT = {
    'Frame_core': dict(reach=0.03, keep=['brick', 'ivory', 'skin', 'umber'], fill='brick'),
    'Frame_arm': dict(reach=0.015, keep=['skin', 'brick'], fill='skin'),
    'Frame_legs': dict(reach=0.0, rule=True, keep=[], fill='brick', grow=8, smooth=80, radial=('shin', 'foot'),
                       smooth_zmin=0.235),
}
# フレームを外した体の形（ai_character._smooth_bare）：脚の体は絵の膝当て・すね当ての外形から作ったので、ズボンだけにすると
# 膝のこぶ・すねの波が目立つ。殻の中（群を見せると殻に隠れる所）の体を内側へだけならす。
#   grow：殻を広げる輪の数（膝の上のこぶまで殻の中に入れる）。smooth：ならす回数。radial：軸の骨（左右）からの半径をならし、
#   それより外の点だけを内へ（筒に近づく）。smooth_zmin：この高さ（m、靴のカフの上の端 0.212 の少し上）より下は動かさない


def frame_paint_rule(pos: np.ndarray) -> dict:
    """形の距離では決めない塗りの範囲（A ポーズの点 pos → 群の名前 → 印）。
    脚：膝の帯（暗い灰、LEG_BANDS）・膝当ての横の暗い裏地（knee_hinge_dark）・すねの中央の茶（絵のすね当ての「暗いフレーム」）は、
    フレームを外すとズボンのれんがにする（膝の帯の上の端の少し上〜靴のカフの中）。body_rules の脚の決まりと同じ範囲"""
    leg = (pos[:, 2] < LEG_TOP) & (np.abs(pos[:, 0]) < np.where(pos[:, 2] > 0.54, 0.20, 0.30))
    m = np.zeros(len(pos), bool)
    for side in (1.0, -1.0):
        s = leg & (pos[:, 0] * side > 0)
        k, f = jp('shin', side), jp('foot', side)
        t = (pos - k) @ unit(f - k)
        m |= s & (t > LEG_BANDS[0] - 0.015)
    return {'Frame_legs': m}


# ---------------------------------------------------------------- 手の部品（hand.py）

# 右手は銃を握る（hand.build）、左手は開いた手（hand.build_open）。手袋は暗い灰（掌・指の付け根の節・親指の付け根）
HAND = dict(
    GAP=0.0012,          # 握りの面と指・掌の面の間（めり込まない・浮かない）
    # 指：（名前, 高さ z, 半径, 節の長さ（基節・中節・末節））。中指・薬指・小指は握りに巻く。
    FINGERS=[
        ('index', -0.006, 0.0082, (0.036, 0.024, 0.020)),
        ('middle', -0.0315, 0.0085, (0.038, 0.025, 0.021)),
        ('ring', -0.0490, 0.0080, (0.035, 0.023, 0.019)),
        ('pinky', -0.0645, 0.0070, (0.028, 0.019, 0.017)),
    ],
    THUMB=dict(z=0.005, r=0.0090, lens=(0.042, 0.030, 0.027)),
    GLOVE_FRAC=0.80,     # 基節の手袋の筒は、付け根からこの割合まで（その先は肌）
    GLOVE_THICK=0.0009,  # 手袋の筒の厚み（肌の棒より太い分）
    GLOVE='graphite',    # 手袋の色（None：手袋なし、掌も肌）
    # 開いた手：名前, 付け根の z, 付け根の x, 半径, 節の長さ, 扇の角度（度、+ = 親指の側）
    OPEN_FINGERS=[
        ('index', 0.0255, 0.070, 0.0080, (0.036, 0.023, 0.019), 6.0),
        ('middle', 0.0085, 0.073, 0.0083, (0.038, 0.025, 0.020), 1.0),
        ('ring', -0.0085, 0.070, 0.0078, (0.035, 0.023, 0.019), -4.0),
        ('pinky', -0.0240, 0.063, 0.0068, (0.028, 0.019, 0.016), -9.0),
    ],
    OPEN_CURL=(12.0, 16.0, 12.0),    # 節ごとの掌への曲げ（度、付け根の節から）
    CUFF_LID=(-0.004, 0.016),        # カフのふたの x の範囲（手首からの距離。カフの部品の先の口 = 手首 +1.6cm）
    OPEN_THUMB=dict(base=(0.024, 0.007, 0.020), r=0.0088, lens=(0.032, 0.027, 0.023), out_deg=22.0, palm_deg=34.0,
                    curl=(8.0, 12.0, 10.0)),
    PALM_HALF_T=0.0115,              # 掌の厚みの半分（指の付け根）
    PALM_WRIST=(0.002, 0.0, 0.0125, 0.024),   # 掌の手首の側の楕円 (y, z, 半径 y, 半径 z)
    THENAR=((0.026, 0.006, 0.020), 0.012),     # 母指球（中心, 半径）
    HYPOTHENAR=((0.032, 0.004, -0.018), 0.011),  # 小指球
)
