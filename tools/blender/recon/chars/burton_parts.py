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

PALETTE = {
    'brick': '#B75B43', 'ivory': '#F3E9D2', 'graphite': '#444641', 'brass': '#A98749',
    'umber': '#594333', 'skin': '#E7B58D', 'grey': '#A39C97', 'leather': '#6D4E3C',
}
NAMES = list(PALETTE)
CELLS = 8

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
SLIT_X = 0.006                  # 裾の前の割れ目の半幅（V の下から裾まで）
JACKET_Z = 0.80                 # これより上の胴・腕は上着の赤錆（裾の部品の下で切り替わる）
NECK_TOP = 1.345                # 内着の首（石墨）の上の端（あごの下）
CUFF_T = (0.112, 0.207)         # カフ：前腕の軸に沿った肘からの長さ（生成りの上の端・黒線の上）。黒線は手首 +4mm まで
# 側頭の白髪（灰）：頭の縦の軸のまわりの (s, z) の多角形（s = 角度 × 0.10、横（±X）が 0、+ は後ろ）。髪の色の所だけ灰に塗る
# （部品の殻にすると、とがった房の上に浮いた鉢巻きに見えた）。絵：こめかみ（y −0.02、z 1.44〜1.47）→ 耳の上の後ろ（y 0.10、z 1.415〜1.44）
GREY_STREAK = [(-0.030, 1.437), (0.040, 1.425), (0.095, 1.413), (0.095, 1.437), (0.040, 1.452), (-0.030, 1.470)]
BOOT_CUT = 0.165        # この高さより下の脚の体は消して、靴の部品に置き換える（足首の帯の中で切る）
BOOT_RAMP = (0.07, 0.14)
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
                  outline=[(-sb, COLLAR_Z[0]), (sb, COLLAR_Z[0]), (st_, COLLAR_Z[1]), (0.0, COLLAR_Z[1] + 0.010),
                           (-st_, COLLAR_Z[1])],
                  off=0.003, thick=0.009, bevel=0.003, under='graphite', rmax=0.2, h=0.006))
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
    sh = 0.17 * (math.pi - 0.05)
    P.append(dict(name='hem', bone='hips', color='brick', frame=fh,
                  outline=[(-sh, HEM_Z[0]), (sh, HEM_Z[0]), (sh, HEM_Z[1]), (-sh, HEM_Z[1])],
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
        P.append(dict(name='boot_cuff' + sx, bone='shin' + sx, color='graphite', frame=fb, ring=True,
                      t0=(k[2] - 0.226) / dz, t1=(k[2] - 0.150) / dz, off=0.004, thick=0.012, bevel=0.004,
                      under='umber', rmax=0.14, n_ring=48, sink=0.02))
        P += boot_pieces(side, sx)
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
    for name, color, secs in (('sole', 'leather', sole), ('heel', 'leather', heel), ('sole_plate', 'graphite', plate),
                              ('toe_cap', 'leather', toe), ('upper', 'graphite', upper)):
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
    # 裾の前の割れ目（V の下から裾まで、細い暗い線）
    slit = free & (y < -0.02) & (z > JACKET_Z) & (z < V_BOT[0] - 0.01) & (np.abs(x) < SLIT_X) & (np.abs(x) < 0.05)
    under[slit] = NAMES.index('graphite')
    # ズボン：裾より下
    legs = free & (z < JACKET_Z)
    under[legs] = NAMES.index('umber')
    # 首のまわりに残る真鍮・琥珀の色（あごの下の絵の陰）：首より上・胴の上は真鍮が来ない → 内着の石墨
    stray = (z > 1.20) & np.isin(lab, [NAMES.index('brass')]) & (under < 0)
    under[stray] = NAMES.index('graphite')
    # 側頭の白髪：髪の色（暗い所）だけ灰に
    lum = col.mean(1)
    hairish = (z > 1.39) & (lum < 0.33) & (under < 0)
    for side in (1.0, -1.0):
        th = np.arctan2(y * side, x * side)        # 横（±X）が 0、+ は後ろ
        st = np.stack([th * 0.10, z], 1)
        poly = np.array(GREY_STREAK, float)
        cand = np.nonzero(hairish & (x * side > 0.03))[0]
        if len(cand):
            ins_ = inside_poly(st[cand], poly)
            under[cand[ins_]] = NAMES.index('grey')
            stats['grey_streak' + ('.L' if side > 0 else '.R')] = int(ins_.sum())
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
