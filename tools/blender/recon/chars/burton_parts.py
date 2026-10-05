"""バートン（burton）の服の部品と塗りの決まり（costume.py が読み込む。書式は chars/haru_parts.py と同じ）。

部品の表：docs/art_orders/W2_人物の部品表.md の 1 章。寸法は calib.json のカメラで絵に 1cm の格子を重ねて読んだ
（再構築の座標：身長 1.55m。本来の 1.90m へは骨付けの段で 1.226 倍）。本人の左 = +X、正面 = −Y。
  立ち襟（生成り、前は V に開く）・前立て（生成りの帯 ×2）・前の留め具 ×2（真鍮）・上着の裾（赤錆、前の割れ目）・
  脇のポケットの蓋 ×2（石墨）と留め具・カフ ×2（生成り）とカフの黒線 ×2・ズボンの裾の帯 ×2・靴（底・かかと・爪先・胴・
  足首の帯）・側頭の白髪の帯 ×2（灰）。手は hand.py の開いた手（手袋なし、肌）。
塗りの決まり（body_rules）：上着（胴・腕）は赤錆、前の開き（V）と襟の中は内着の石墨、裾より下はズボンの茶。
色の約束：PALETTE の 'umber' はズボン・革の #594333。髪の色（#453630、絵から測った）は体の塗りの段の色
（params の flat.PALETTE の umber）で、部品の色見本とは別。
"""
from __future__ import annotations

import math

import numpy as np

# 色は絵（burton_3d_front・burton_shoes）の平らに照らされた所の中央値で測った（2026-10-02。spec の hex より絵に合わせる）：
# 上着 #AA472C（胸・腕・裾）、カフ・襟 #FBE1BF、留め具 #C98C3D、ズボン #5A3C30、靴の胴・筒の帯 #413834（暗い茶）、
# 靴の底・かかと・爪先 #6E4E3C（茶）、白髪 #9A928C（burton_head_side_right の灰の陰の側。明るい側 #D2C7BD は確認ページで白に見えた）
PALETTE = {
    'brick': '#AA472C', 'ivory': '#FBE1BF', 'graphite': '#444641', 'brass': '#C98C3D',
    'umber': '#5A3C30', 'skin': '#E7B58D', 'grey': '#9A928C', 'leather': '#6E4E3C', 'hair': '#453630',
    'boot': '#413834',
}
NAMES = list(PALETTE)
CELLS = 16

# A ポーズの関節（chars/burton.json の joints.ART_XZ と同じ x・z。y は真横の絵）
J = {
    'upper_arm': (0.215, 0.02, 1.19), 'forearm': (0.33, 0.03, 0.975), 'hand': (0.40, 0.02, 0.765),
    'hand_end': (0.42, 0.0, 0.635), 'thigh': (0.11, 0.0, 0.73), 'shin': (0.16, 0.01, 0.40),
    'foot': (0.18, 0.03, 0.10),
}
# 襟・裾は近くの体の重みを写す（首・胴・腰の複数の骨で曲がる所）
FOLLOW_BODY = ('collar', 'hem')
FOLLOW_TORSO_ONLY = ('collar', 'hem')
BOX_RULES: list = []

COLLAR_Z = (1.262, 1.335)       # 立ち襟の下・上（前の端）。後ろの上は 1.345
HEM_Z = (0.792, 0.872)          # 上着の裾の部品の下・上（裾の下の縁は正面で 0.79〜0.80）
V_TOP = (1.262, 0.036)          # 前の開き（内着の石墨）：上の高さと半幅
V_BOT = (0.985, 0.008)          # 下の高さと半幅（前立ての帯がこの外を覆う）
SLIT_X = (0.006, 0.022)         # 裾の前の割れ目の半幅（V の下 → 裾の下の縁。絵は下へ逆 V に開く）
JACKET_Z = 0.80                 # これより上の胴・腕は上着の赤錆（裾の部品の下で切り替わる）
# 髪の下の縁：正面からの角度（度）→ 高さ。絵の右真横・背面：もみあげは耳の中ほど（1.372）まで、耳の後ろは耳の下の端、
# 後ろの真ん中は襟の中まで（えり足の V）
HAIR_LOW = ([50, 60, 72, 95, 100, 180], [1.44, 1.41, 1.378, 1.375, 1.25, 1.25])
NECK_TOP = 1.345                # 内着の首（石墨）の上の端（あごの下）
CUFF_T = (0.112, 0.207)         # カフ：前腕の軸に沿った肘からの長さ（生成りの上の端・黒線の上）。黒線は手首 +4mm まで
# 側頭の白髪（灰）は房の形の部品（pieces() の grey_*、costume.build_tube）。塗りで描くと平らなシール・ぎざぎざの縁に見えた
BOOT_CUT = 0.165        # この高さより下の脚の体は消して、靴の部品に置き換える（足首の帯の中で切る）
BOOT_RAMP = (0.07, 0.14)
BOOT_CUT_X = (0.03, 0.40)   # 靴底が |x| 0.334 まで広い（0.32 では体の爪先の端が残った）
RIGHT_HAND_PART = True


def pieces() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    back = np.array([0.0, 1.0, 0.0])
    # 立ち襟：首の縦の軸のまわり、後ろが s = 0。前は V に開く（下 |x| 0.025、上 |x| 0.06）
    fc = frame((0.0, 0.012, 0.0), (0.0, 0.012, 1.0), back)
    fc['RN'] = 0.10
    sb, st_ = 0.10 * (math.pi - math.asin(0.25)), 0.10 * (math.pi - math.asin(0.55))
    P.append(dict(name='collar', bone='neck', color='ivory', frame=fc,
                  outline=[(-sb, COLLAR_Z[0]), (sb, COLLAR_Z[0]), (st_, COLLAR_Z[1]), (0.20, COLLAR_Z[1] + 0.020),
                           (0.0, COLLAR_Z[1] + 0.025), (-0.20, COLLAR_Z[1] + 0.020), (-st_, COLLAR_Z[1])],
                  off=0.003, thick=0.009, bevel=0.003, under='graphite', rmax=0.2, rmin=0.098, h=0.006))
    # 後ろ・横の上の縁は絵より 2〜2.5cm 高い：体の土台の上の端（fair.BODY_TOP）と頭の間の UV のつぶれた細い三角形が、
    # 首の後ろで隣の島の色を拾ってまだらになった（ハルのフードのえりと同じ。形で覆う）。rmin で首から離して立てる
    # 前立て（生成りの帯 ×2）：縦の軸、正面が s = 0（s ≈ x）。V の外の縁から 2.5〜3cm
    fw = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), front)
    fw['RN'] = 0.14
    for sg, sx in ((1.0, '.L'), (-1.0, '.R')):
        o = [(V_BOT[1], V_BOT[0] - 0.012), (V_BOT[1] + 0.024, V_BOT[0] - 0.012), (V_TOP[1] + 0.026, V_TOP[0] + 0.004),
             (V_TOP[1] - 0.002, V_TOP[0] + 0.004)]
        o = [(sg * s, t) for s, t in o]
        if sg < 0:
            o = o[::-1]
        P.append(dict(name='placket' + sx, bone='chest', color='ivory', frame=fw, outline=o, off=0.003, thick=0.006,
                      bevel=0.002, under='graphite', rmax=0.25, h=0.005))
    # 前の留め具 ×2（真鍮、3cm 角）：前の真ん中
    for k, zc in enumerate((1.098, 1.025)):
        P.append(dict(name=f'fastener{k}', bone='chest', color='brass', frame=fw,
                      outline=octagon(-0.016, 0.016, zc - 0.016, zc + 0.016, 0.003), off=0.003, thick=0.013,
                      bevel=0.0025, rmax=0.25, h=0.004))
    # 上着の裾：腰のまわり、後ろが s = 0、前の真ん中は割れ目（|x| < SLIT_X）
    fh = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), back)
    fh['RN'] = 0.17
    sh0, sh1 = 0.17 * math.pi - SLIT_X[1], 0.17 * math.pi - (SLIT_X[1] - 0.004)   # 前の割れ目（下ほど広い）
    P.append(dict(name='hem', bone='hips', color='brick', frame=fh,
                  outline=[(-sh0, HEM_Z[0]), (sh0, HEM_Z[0]), (sh1, HEM_Z[1]), (-sh1, HEM_Z[1])],
                  off=0.002, thick=0.007, bevel=0.002, under='brick', rmax=0.3, h=0.008, n_ring=96))
    # 脇のポケットの蓋（石墨）と留め具（真鍮）：正面から約 70 度、z 0.855〜0.905
    for sg, sx in ((1.0, '.L'), (-1.0, '.R')):
        sc = sg * math.radians(68) * 0.14
        P.append(dict(name='pocket' + sx, bone='hips', color='graphite', frame=fw,
                      outline=octagon(sc - 0.027, sc + 0.027, 0.853, 0.905, 0.004), off=0.004, thick=0.008, bevel=0.002,
                      under='brick', rmax=0.3, h=0.005))
        P.append(dict(name='pocket_button' + sx, bone='hips', color='brass', frame=fw,
                      outline=octagon(sc - 0.010, sc + 0.010, 0.869, 0.889, 0.002), off=0.004, thick=0.013,
                      bevel=0.002, rmax=0.3, h=0.003))
    # カフ（生成り）と黒線：前腕の軸（肘 → 手首）
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        e2, w2 = jp('forearm', side), jp('hand', side)
        L2 = float(np.linalg.norm(w2 - e2))
        fk = frame(e2, w2, front)
        fk['RN'] = 0.05
        P.append(dict(name='cuff' + sx, bone='forearm' + sx, color='ivory', frame=fk, ring=True,
                      t0=CUFF_T[0], t1=CUFF_T[1], off=0.003, thick=0.008, bevel=0.003, under='brick',
                      clear=['ivory'], fill='brick', margin=0.015, rmax=0.12, n_ring=48))
        P.append(dict(name='cuff_line' + sx, bone='forearm' + sx, color='graphite', frame=fk, ring=True,
                      t0=CUFF_T[1], t1=L2 + 0.004, off=0.003, thick=0.009, bevel=0.002, under='brick',
                      rmax=0.12, n_ring=48, sink=0.012))
        # ズボンの裾の帯（足首の上、靴の胴にかぶさる）：すねの軸
        k = jp('shin', side)
        fb = frame(k, jp('foot', side), front)
        fb['RN'] = 0.06
        dz = -fb['d'][2]
        P.append(dict(name='boot_cuff' + sx, bone='shin' + sx, color='boot', frame=fb, ring=True,
                      t0=(k[2] - 0.222) / dz, t1=(k[2] - 0.160) / dz, off=0.003, thick=0.008, bevel=0.003,
                      under='umber', rmax=0.14, n_ring=48, sink=0.02))
        # 靴の筒の上の帯の留め具（絵 burton_shoes.png：外側のやや後ろの小さな板）
        ft = frame((side * 0.175, 0.02, 0.0), (side * 0.175, 0.02, 1.0), front)
        ft['RN'] = 0.07
        st = side * math.radians(110) * 0.07
        P.append(dict(name='boot_tab' + sx, bone='shin' + sx, color='boot', frame=ft,
                      outline=octagon(st - 0.014, st + 0.014, 0.170, 0.214, 0.003), off=0.012, thick=0.007,
                      bevel=0.002, rmax=0.14, h=0.004))
        P += boot_pieces(side, sx)
        # 側頭の白髪：房の形の部品 2 本（上・下）。こめかみから耳の上を通って後ろへ流れ、先がとがる（絵 burton_head_side_right・
        # burton_face_front・burton_head_back。左右対称）。房全体が 1 色（灰）。耳（θ 96〜118 度、上の端 z 1.427）の上を通す
        # 頭に沿って寝かせる（先を浮かせると角のように飛び出した）。2 本は重なって 1 本の帯に見える幅
        for nm, path, wd in (('grey_hi', [(64, 1.458), (108, 1.451), (138, 1.433)], 0.036),
                             ('grey_lo', [(68, 1.441), (108, 1.437), (134, 1.420)], 0.032)):
            P.append(dict(name=nm + sx, bone='head', color='grey',
                          tube=dict(axis=(0.0, 0.01), side=side, path=path, width=wd, thick=0.34, lift=(0.0035, 0.004))))
    return P



def boot_pieces(side: float, sx: str) -> list[dict]:
    """片足の靴（左の値で書き、右は x を反転）。絵 burton_shoes.png と全身の絵（正面・右真横）で測った：
    靴底 x 0.096〜0.334・y −0.19〜0.165、厚い茶の底（前 3.5cm・かかと 5cm、間に土踏まずの切り欠き）、
    茶の爪先の帯（甲の前、z 0.05〜0.10）、暗い胴（足首で脚の太さ）"""
    X0, X1 = 0.098, 0.330
    YF, YB = -0.188, 0.160
    P = []

    def sec(z, x0, x1, y0, y1, rf, rb, k=3):
        return (z, rrect(x0, x1, y0, y1, rf, rb, k))

    sole = [sec(0.000, X0 + 0.004, X1 - 0.004, YF + 0.006, 0.010, 0.045, 0.004),
            sec(0.004, X0 + 0.001, X1 - 0.001, YF + 0.001, 0.016, 0.048, 0.004),
            sec(0.036, X0 + 0.001, X1 - 0.001, YF + 0.001, 0.050, 0.048, 0.004)]
    heel = [sec(0.000, X0 + 0.012, X1 - 0.012, 0.065, YB - 0.004, 0.004, 0.026),
            sec(0.004, X0 + 0.010, X1 - 0.010, 0.063, YB - 0.001, 0.004, 0.028),
            sec(0.050, X0 + 0.010, X1 - 0.010, 0.060, YB - 0.001, 0.004, 0.028)]
    plate = [sec(0.034, X0, X1, YF, YB, 0.048, 0.03),
             sec(0.052, X0, X1, YF, YB, 0.048, 0.03),
             sec(0.058, X0 + 0.004, X1 - 0.004, YF + 0.004, YB - 0.004, 0.044, 0.026)]
    toe = [sec(0.050, X0 + 0.010, X1 - 0.010, YF + 0.008, -0.060, 0.042, 0.004),
           sec(0.085, X0 + 0.012, X1 - 0.014, YF + 0.014, -0.070, 0.040, 0.004),
           sec(0.100, X0 + 0.022, X1 - 0.026, YF + 0.034, -0.078, 0.032, 0.004)]
    upper = [sec(0.050, X0 + 0.014, X1 - 0.016, -0.150, 0.150, 0.03, 0.035, 4),
             sec(0.095, X0 + 0.016, X1 - 0.030, -0.120, 0.148, 0.03, 0.035, 4),
             sec(0.120, 0.112, 0.282, -0.080, 0.140, 0.03, 0.04, 4),
             sec(0.150, 0.108, 0.272, -0.060, 0.128, 0.04, 0.045, 4),
             sec(0.185, 0.106, 0.268, -0.055, 0.122, 0.045, 0.045, 4)]
    for name, color, secs in (('sole', 'leather', sole), ('heel', 'leather', heel), ('sole_plate', 'boot', plate),
                              ('toe_cap', 'leather', toe), ('upper', 'boot', upper)):
        if side < 0:
            secs = [(z, [(-x, y) for (x, y) in pts][::-1]) for z, pts in secs]
        P.append(dict(name=f'boot_{name}{sx}', bone='foot' + sx, color=color, loft=secs,
                      ramp=('shin' + sx, 'foot' + sx)))
    return P


# ---------------------------------------------------------------- 決まりの塗り（cover_body から）

def body_rules(pos: np.ndarray, col: np.ndarray, lab: np.ndarray, under: np.ndarray, ins: dict, stats: dict) -> None:
    """胴・腕は上着の赤錆、前の開き（V）と襟の中・首は内着の石墨、裾より下の脚はズボンの茶（絵の色を使わない）。
    手（部品）・頭（顔の材質と髪）は触らない"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    free = under < 0
    # 頭（あごより上の頭の殻・耳・髪）は除く：首の軸から離れた所（あご・ほお）と NECK_TOP より上
    r_neck = np.hypot(x, y - 0.012)
    head = (z > NECK_TOP) | ((z > 1.30) & (r_neck > 0.075) & (y < 0.0))
    # 上着（胴と腕）：裾の高さより上
    jacket = free & ~head & (z >= JACKET_Z)
    under[jacket] = NAMES.index('brick')
    # 首と襟の中（内着）
    neck = free & ~head & (z > COLLAR_Z[0] - 0.004) & (r_neck < 0.10)
    under[neck] = NAMES.index('graphite')
    # 前の開き（V）：前の面で、高さで半幅が変わる
    f = np.clip((z - V_BOT[0]) / (V_TOP[0] - V_BOT[0]), 0, 1)
    hw = V_BOT[1] + (V_TOP[1] - V_BOT[1]) * f + 0.008
    vv = free & ~head & (y < -0.02) & (z > V_BOT[0] - 0.01) & (z <= COLLAR_Z[0]) & (np.abs(x) < hw)
    under[vv] = NAMES.index('graphite')
    # 襟の V の中（襟の下の縁〜あごの下、前）：内着
    vtop = (y < -0.04) & (z > COLLAR_Z[0] - 0.002) & (z < 1.318) & (np.abs(x) < 0.07) & free
    under[vtop] = NAMES.index('graphite')
    vv |= vtop
    # 裾の前の割れ目（V の下から裾まで、細い暗い線）
    fs = np.clip((V_BOT[0] - 0.01 - z) / (V_BOT[0] - 0.01 - HEM_Z[0]), 0, 1)
    slit = free & (y < -0.02) & (z > JACKET_Z) & (z < V_BOT[0] - 0.01) & (np.abs(x) < SLIT_X[0] + (SLIT_X[1] - SLIT_X[0]) * fs)
    under[slit] = NAMES.index('graphite')
    # ズボン：裾より下
    legs = free & (z < JACKET_Z)
    under[legs] = NAMES.index('umber')
    # 頭と首の帯（あごの下〜頭頂、首の軸の近く）：形の場（hair.part_fields_at）で決める。絵の多数決の色を使わない
    #   耳 → 肌、髪の場 → 髪、頭の面（あご・ほお・首の後ろ）→ 肌、立ち襟の上の縁より下 → 内着の石墨、ほかの首 → 肌。
    #   側頭・後ろ（耳の上の高さより上）は髪（刈り上げの面が肌に塗られてまだらになった）。白髪の多角形の中の髪は灰
    from recon import hair as HR
    hb = (z > 1.25) & (z < 1.57) & (np.hypot(x, y - 0.01) < np.where(z > 1.30, 0.17, 0.125))
    hi = np.nonzero(hb)[0]
    lab_h = np.full(len(hi), -1)
    if len(hi):
        f = HR.part_fields_at(pos[hi])
        xh, yh, zh = x[hi], y[hi], z[hi]
        ear = f['ear'] > -0.002
        # 髪は髪の形（帽子・房）の上だけ：面が髪の場から 4mm 以内（刈り上げの帽子は頭の面から 6mm 以内なので、
        # hair − skin の差では側頭が肌になった）。肌の面に髪の色を塗らない（生え際は形の縁）
        hair = (f['hair'] > -0.004) & ~ear
        ctop = np.interp(yh, [-0.10, 0.10], [COLLAR_Z[1], COLLAR_Z[1] + 0.010])
        lab_h[:] = NAMES.index('skin')
        lab_h[zh < ctop + 0.004] = NAMES.index('graphite')
        lab_h[(f['skin'] > -0.004) & (zh > 1.318)] = NAMES.index('skin')
        lab_h[(yh < -0.045) & (zh > 1.316)] = NAMES.index('skin')      # あごの下（顔の材質の下の縁から上）
        # 横・後ろ（|θ| > 55 度）は角度の表の高さより上を髪にする（刈り上げの帽子は頭の面とほぼ同じ所にあり、形の場では
        # 側頭が肌と髪のまだらになった）。耳より後ろ（|θ| > 95 度）は首の後ろを襟の中まで髪にし、襟の下の内着より優先する
        # （首の後ろの UV のつぶれた島が石墨・肌の斑点になった）
        th_f = np.degrees(np.arctan2(np.abs(xh), -(yh - 0.01)))      # 0 = 正面、90 = 横、180 = 後ろ
        zb = np.interp(th_f, HAIR_LOW[0], HAIR_LOW[1])
        low = (th_f > 50.0) & (zh > zb) & ~ear
        lab_h[hair | low] = NAMES.index('hair')
        lab_h[ear] = NAMES.index('skin')
        keep = under[hi] >= 0          # 部品の下（襟）はそのまま
        # ただし後ろ（耳より後ろ）の髪の下の縁より上は、襟の下の内着より髪を優先する（襟の上の縁から見える首の後ろが
        # 石墨と肌の斑点になった：UV のつぶれた三角形が隣の島の色を拾う。首の後ろの島ごと髪の色にする）
        keep &= ~(low & (th_f > 95.0))
        under[hi[~keep]] = lab_h[~keep]
    stats['head_band_texels'] = int(len(hi))
    stats['burton_rule_texels'] = int((jacket | neck | vv | slit | legs).sum())


# ---------------------------------------------------------------- 手の部品（hand.py）

# 両手とも力を抜いて開いた手（hand.build_open）。手袋なし（掌も指も肌）。絵 burton_hands.png：長さ 20cm（再構築の座標で
# 16cm）、太い指。ハルの開いた手の寸法を、長さ 1.1 倍・指の太さ 1.25 倍にした
_S, _R = 1.10, 1.25
HAND = dict(
    GLOVE=None,
    LID='graphite',
    OPEN_FINGERS=[(n, z * _S * 1.1, x * _S, r * _R, tuple(v * _S for v in L), fan) for n, z, x, r, L, fan in (
        ('index', 0.0255, 0.070, 0.0080, (0.036, 0.023, 0.019), 6.0),
        ('middle', 0.0085, 0.073, 0.0083, (0.038, 0.025, 0.020), 1.0),
        ('ring', -0.0085, 0.070, 0.0078, (0.035, 0.023, 0.019), -4.0),
        ('pinky', -0.0240, 0.063, 0.0068, (0.028, 0.019, 0.016), -9.0))],
    OPEN_CURL=(14.0, 20.0, 14.0),
    CUFF_LID=(-0.012, 0.006),
    OPEN_THUMB=dict(base=(0.026, 0.008, 0.024), r=0.0088 * _R, lens=(0.035, 0.030, 0.025), out_deg=22.0,
                    palm_deg=34.0, curl=(8.0, 12.0, 10.0)),
    PALM_HALF_T=0.0115 * _R,
    PALM_WRIST=(0.002, 0.0, 0.016, 0.030),
    PALM_X=(0.012, 0.046),
    THENAR=((0.029, 0.007, 0.023), 0.0145),
    HYPOTHENAR=((0.035, 0.005, -0.021), 0.013),
    LEFT_HAND_CUT=-0.004,
    LEFT_HAND_RAMP=(-0.014, 0.006),
)
