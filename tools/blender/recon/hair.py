"""頭と髪：なめらかな頭（顔・あご）＋ なめらかな髪の帽子 ＋ 先の細る髪の房（ゲームの髪の作り方）。

以前の方法（外形の出っ張りを視線に沿って延ばした「ひれ」を頭の芯に足し、面を外形へ引き寄せる）では、
房が見た視点の面の中の薄いひれになり、ほかの向きからはとげ・いぼに見え、頭は視体積の面が残る角ばった箱に
なった。3 枚の外形から房の立体の形は決まらないので、ここでは「形の部品」を置き、外形はその部品の大きさ・
向きを決める手がかりにだけ使う（視体積で切らない）。carve.py の 2（hull）で fair.build_field から呼ばれる。

■ 1. 頭（skin_head）：顔・あご・頭の骨の形
  高さごとの断面を、前と後ろで別の半径・指数をもつ超楕円 |x/a|^n + |(y-cy)/b|^n = 1 にする。
    a（左右の半幅）：正面の絵の肌の幅（あご〜ほお。耳より下の高さ）から。それより上は頭の骨のふくらみ。
    前の端：右真横の絵の顔の輪郭を読んだ節（鼻と、額の前の前髪・ゴーグルを除く。鼻はあとで小さな楕円体で足す）。
    後ろの端：髪の中に隠れる頭の骨（あごの下では首へ）。
    前の半分の指数 n_f：右前斜めの絵の顔の右の縁（本人の左のほお）に届くように、高さごとに決める。
  断面を上下になめらかにつなぎ（節の値を PCHIP で補間）、ボクセルの占有から符号つき距離にしてぼかす。
  前の端の口・あごは右真横の絵の小さなあごに合わせ、前の半分の指数はほお骨の 2.6 からあごの先の 2.0 へ下げる
  （ほおの前を平らに、あごを細く。口の突き出た顔にしない）。
  鼻は小さな楕円体、首は縦の楕円柱（体の場の首とつなぐ）。
  耳（ears_field）：正面の絵（外の縁 |x| ≈ 0.133）と右真横の絵（y 0.005〜0.048、z 1.26〜1.33）の位置に、後ろへ
  開いた平たい楕円体 ＋ 付け根 ＋ 外の面の浅いくぼみ。帽子と房は耳から 5mm 離す（耳が髪にうまらず見え、
  絵の耳の肌色が耳の形の上に載る）。

■ 2. 髪の帽子（cap）：房の先を落とした髪の外形の内側の、なめらかな閉じた面
  髪と頭の外形を半径 3cm の円で開き（房の先を落とす）2cm で閉じた外形（正面・右真横・右前斜め）から、
  高さごとに超楕円の断面を当てはめる：左右の幅は正面、前後の端は右真横、前と後ろの半分の指数は
  右前斜めの右の縁（左前のふくらみ）と左の縁（右後ろのふくらみ）から（2 未満にしない：2 未満だと前後の
  中心線に折れ目ができる）。指数の下限でも右前斜めの縁を越える高さは断面を縮める。左右は対称。値は上下に
  1cm でならし、てっぺんとえり足の下端は楕円の弧で丸く閉じる。前髪の高さでは前の端を額の 1.5cm 前までに
  （真横の絵の前の端は前髪の先とゴーグルで、そのままだと額の上にひさしができる）。
  顔の範囲（生え際 hairline_z(|x|) より下で y < 0.02。正面の絵の肌の縁を読んだ節）では、帽子は頭の面より
  外へ出さない（なめらかな積）。顔・ほお・こめかみは頭の面がそのまま見え、髪はその外側と後ろ。
  額の前（生え際 HAIRLINE の真ん中はゴーグルの下の縁 1.392 まで上げた）は帽子で覆わず、前髪の殻（下）が覆う。
  ゴーグル（goggles_field）：正面の絵の枠とレンズの輪郭を読んだ多角形（GOGGLE_FRAME・GOGGLE_LENS、左右は反転）の
  柱を、帽子の面からの厚みで切った 2 つの六角の枠（1.3cm）＋ 4mm 奥のレンズ ＋ 細い橋。額の丸みに沿って
  回り込む（以前の、額の幅いっぱいの平らな板はひさしに見えた）。
  ベルト（strap_field）：房のすき間をうめてなめらかにした髪の包みの面の上の、右真横の絵のとおり後ろへ下がる
  幅 2.3cm の帯（包みの外 4mm〜内 2mm の殻）。塗りの段はこの形で色を決める（part_fields_at）。
  前髪（bangs_field）：正面の絵のゴーグルの下の前髪の範囲（髪の色、ゴーグルの下の帯につながる所）を、額の面から
  前へ押し出した殻。厚みは範囲の縁からの距離で決まる（真ん中で最大 1.1cm、縁・先は 2mm のくさび）。
  顔のアトラスに描かれた前髪の V が、どの向きからも V の形の上に載る（以前の、ゴーグルの下の楕円体の根元の
  こぶの列と細い牙のような房はやめた）。

■ 3. 髪の房（Lock）：帽子に根をもつ、先の細る平たい葉の形の房（約 35 本 ＋ 前髪 4 本）
  頭の中心 C から見た向きで表す。根の向き d0 と先の向き d1 の間を大きな円に沿って進み（slerp）、
  中心からの距離は「帽子（と頭）の面の距離 r(d) ＋ 浮き L・t²」。根元では面に半分うまり、
  先へ行くほど面から浮く（重なった房の段になる）。断面は楕円：幅 w（面に沿う向き。根元の 0.75 倍から
  30% の所で最も広く、先へ細る）と厚み h（面の法線の向き。w の 0.3 倍）。形の場は、房に沿って半径の
  0.4 倍の間隔で並べた楕円体の場の最大。
  最初の並び：頭のてっぺんの後ろのつむじ W から放射状に流れる 3 つの輪（36・66・96 度に 7・9・10 本の大きな房。つむじの
  すぐまわりの輪はてっぺんのこぶに見えたので置かない）と、ゴーグルの上（後ろ）から立ち上がる大きな房 6 本
  （根・先を絵から読んだ表。真ん中の高い房は前へかぶさる）。顔の範囲に根か先がある房は置かない（前へ流れる房は額の上で止める）。
  当てはめのあとも顔の範囲・ゴーグルの枠に入る房は、入らなくなるまで先を縮める（縮めきれない房は落とす）。
  当てはめ：7 視点の絵の外形（あごより上。正面・背面・右真横・左真横・右前 45 度・左前 45 度・右前斜め 31 度）と、
  帽子＋頭＋房の投影の IoU の重みつき平均（真横 1.5、右前斜め 31 度 0.5、ほかは 1）
  が大きくなるよう、
  房ごとに先の向き（振り）・長さ（角度）・浮き・幅を座標ごとの探索で動かす（半分の解像度の投影を房ごとに
  差し替えて数えるので 1 巡 1 秒ほど、6 巡）。顔の範囲・ゴーグルの枠に入る房の点、最初の流れから 20 度より
  外れた向きは罰。外形の小さな切り欠きは追わない（色の絵が細部を担う）。房は最後に顔の範囲とゴーグルの枠で切る。

■ 4. つなぎ
  頭・鼻・首・耳・帽子・ゴーグル・前髪・房・ベルトをなめらかな和（幅 3〜6mm。房の根元にすみ肉ができ、割れ目・食い込みが
  できない）で 1 つの場にし、fair.build_field で体の場（えりより下）となめらかな和でつなぐ。carve.py の 3 で
  マーチングキューブにして面にする（頭は snap.py の外形への引き寄せ・平滑化から外す）。
  計算は |x| < 0.3m の箱の中だけ（約 40 秒）。記録（断面の値の要約・房の向き・頭のまわりの外形の IoU）は
  recon_report.json の hull.head に入る。

  本番は carve.py --stage surface（体と頭の場 → 面 → UV → 確認画像）の中で呼ばれる。
  python tools/blender/recon/hair.py            （実験用：頭だけの場を作り、面にして、なめる光の画像と
                                                  外形の重なりの画像を build/recon/hair/ に描く。約 1 分）
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.interpolate import PchipInterpolator  # noqa: E402

from recon import char as CH  # noqa: E402
from recon import views as V  # noqa: E402

# 房の当てはめに使う外形の視点。W1-00b の追加の絵（左真横・左右の前 45 度）と背面も使う
# （3 視点だけだと、房の後ろ・上への張り出しが決まらず、横と斜めから丸いもじゃもじゃに見えた）
REAL = CH.p('hair.REAL', ('front', 'side_right', 'three_quarter', 'side_left', 'front_right45', 'front_left45', 'back'))
T0 = time.time()
OUT = os.path.join(V.WORK, 'hair')

HEAD_C = np.array(CH.p('hair.HEAD_C', [0.0, 0.03, 1.37]))   # 頭の中心（房の向きの原点）
Z_FIT = CH.p('hair.Z_FIT', 1.215)                         # 外形の当てはめに使う高さの下端（あごより上。えりを含めない）
# 生え際：額の中ほどはゴーグルの下の縁まで上げる（額の前の髪は帽子ではなく、正面の絵の前髪を写した殻 bangs_field）
HAIRLINE = CH.p('hair.HAIRLINE', {'y_face': 0.02, 'x': [0.0, 0.050, 0.070, 0.087, 0.094, 0.101, 0.20],
            'z': [1.392, 1.390, 1.368, 1.325, 1.28, 1.24, 1.24]})
# ゴーグル（額の上）：正面の絵の枠の範囲（x, z）、帽子の面からの厚みの上限、レンズの前の面（右真横の絵で y ≈ -0.146）
GOGGLES = {'x': (-0.111, 0.125), 'z': (1.392, 1.488), 'round': 0.022, 'thick': (0.012, 0.030), 'front_y': -0.146}
# ゴーグルの形（正面の絵の枠とレンズの輪郭を読んだ多角形。世界の (x, z)。本人の右のレンズ。左は x = MIRROR_X で
# 反転）：枠は帽子の面から FRAME_T 外へ出た縁、レンズは LENS_T（枠より 4mm 奥）、真ん中は細い橋
GOGGLE_FRAME = [(-0.1115, 1.410), (-0.110, 1.467), (-0.016, 1.487), (-0.006, 1.438), (-0.037, 1.391), (-0.104, 1.391)]
GOGGLE_LENS = [(-0.095, 1.412), (-0.097, 1.4616), (-0.024, 1.4723), (-0.0176, 1.4508), (-0.0305, 1.4142)]
GOGGLE_BRIDGE = ((-0.012, 0.021), (1.437, 1.474))
GOGGLE_MIRROR_X = 0.0045
FRAME_T, LENS_T, BRIDGE_T = 0.013, 0.009, 0.008
# ベルト：右真横の絵で、ゴーグルの横（y = -0.035, z = 1.418）から後ろ（y = 0.145, z = 1.35）へ下がり、後ろは水平。
# 幅 2.3cm（絵の帯の幅。左右の真横の絵は後ろで 1.335、背面の絵は 1.364 と食い違うので、その間）
STRAP = {'y': (-0.035, 0.145), 'z': (1.418, 1.35), 'half': 0.0115, 'off': 0.004, 'inner': 0.002}
# 頭の部品の有無（キャラクターごと。ハル：ゴーグル・ベルト・前髪の殻・耳。ヤーナ：ゴーグルとベルトは無い）
PARTS = CH.p('hair.PARTS', {'goggles': True, 'strap': True, 'bangs': True, 'ears': True})
# 耳：正面の絵（外の縁 |x| ≈ 0.133、z 1.26〜1.33）と右真横の絵（y 0.005〜0.048）から
EAR = CH.p('hair.EAR', {'c': (0.112, 0.027, 1.294), 'r': (0.0085, 0.021, 0.033), 'yaw_deg': 22.0,
       'root_c': (0.092, 0.020, 1.290), 'root_r': (0.013, 0.016, 0.022)})
# 房の当てはめの視点の重み：右真横は頭の外形が全身の外形に占める割合が大きく、横顔・ゴーグル・後ろの房の形が
# はっきり出るので重く
VIEW_WEIGHT = CH.p('hair.VIEW_WEIGHT', {'front': 1.0, 'side_right': 1.5, 'three_quarter': 0.5, 'side_left': 1.5, 'front_right45': 1.0,
               'front_left45': 1.0, 'back': 1.0})
# 房の浮き・幅の上限：絵（W1-00b の頭の横・後ろ・上）の房は幅 5〜9cm の大きな葉で、先は頭から 6〜9cm 浮いて
# 後ろ・上へ張り出す（以前の 7.5cm・9cm では、横から見た外形の後ろの房の先まで届かなかった）
LOCK_LIFT_MAX = CH.p('hair.LOCK_LIFT_MAX', 0.095)
LOCK_WIDTH_MAX = CH.p('hair.LOCK_WIDTH_MAX', 0.10)
PARAMS = {
    'cap_open_m': 0.03,        # 髪の帽子に使う外形を開く円の半径（房の先を落とす）
    'cap_close_m': 0.02,       # その後で閉じる円の半径
    'cap_inset_m': 0.004,      # 帽子を外形より内側へ
    'union_k': 0.006,          # 房・頭・帽子のなめらかな和の幅
    'lock_thick': 0.30,        # 房の厚み / 幅（紙のように薄くならないように。大きな平たい葉の房にするため 0.38 から下げた）
}
PARAMS.update(CH.p('hair.PARAMS', {}))
# 頭（顔・あご）の断面の節（skin_stack、世界の m）。ハルの値は絵を読んだもの。ほかのキャラクターは chars/<id>.json で
#   zs：断面を積む高さの範囲、ka_z・ka：あご〜ほおの上の頭の骨の左右の半幅の節（あご〜ほおは正面の絵の肌の幅）、
#   jaw_z：肌の幅を読む節、front_z・front_y：顔の前の端（真横の絵の肌の縁、鼻を除く）、back_z・back_y：後ろの端、
#   nf_z・nf：前の半分の指数、side_rows：真横の肌を読む高さ、cx_z：左右の中心を測る高さ、nose：鼻の楕円体（y, z, 半径）
SKIN = CH.p('hair.SKIN', {
    'zs': (1.180, 1.490),
    'jaw_z': (1.186, 1.196, 1.206, 1.216, 1.226, 1.236, 1.246),
    'ka_z': (1.258, 1.275, 1.30, 1.34, 1.38, 1.42, 1.45, 1.47, 1.482, 1.49),
    'ka': (0.083, 0.086, 0.088, 0.090, 0.091, 0.087, 0.078, 0.062, 0.040, 0.0),
    'front_z': (1.180, 1.190, 1.200, 1.215, 1.235, 1.250, 1.270, 1.300, 1.330, 1.360, 1.400, 1.430, 1.460, 1.475, 1.487),
    'front_y': (-0.045, -0.070, -0.089, -0.100, -0.106, -0.111, -0.115, -0.116, -0.114, -0.111, -0.104, -0.092,
                -0.070, -0.046, -0.010),
    'back_z': (1.180, 1.20, 1.22, 1.25, 1.28, 1.32, 1.38, 1.43, 1.46, 1.475, 1.487),
    'back_y': (-0.020, 0.000, 0.030, 0.075, 0.110, 0.125, 0.130, 0.120, 0.100, 0.075, 0.040),
    'nf_z': (1.18, 1.21, 1.24, 1.28), 'nf': (2.0, 2.1, 2.3, 2.6),
    'side_rows': (1.185, 1.37), 'cx_z': (1.2, 1.25),
    'nose': ((-0.114, 1.279), (0.0062, 0.012, 0.016)),
})
# 髪の帽子の断面（cap_stack）：高さの範囲、えり足の下端の丸め、前髪の高さの前の端の制限（ハルはゴーグルの高さで外す）
CAP = CH.p('hair.CAP', {'zs': (1.200, 1.560), 'nape': (1.212, 1.242), 'cx_z': (1.3, 1.48), 'n_zmin': 1.25,
                        'fringe_ramp': (1.375, 1.42), 'fringe_ztop': 1.45})
# 首（縦の楕円柱）：半径 (x, y)、前後の中心、高さの範囲
NECK = dict({'cx': 0.0}, **CH.p('hair.NECK', {'r': (0.040, 0.044), 'cy': 0.012, 'z': (1.06, 1.27)}))
# 前髪の殻（bangs_field）：正面の絵で前髪を探す範囲。z：上・下、x：左右の範囲、root_z：根（この高さより上につながる塊だけ）、
# thick_ramp：厚みを 0.6 → 1.0 倍にする高さ
BANGS = CH.p('hair.BANGS', {'z': (1.445, 1.295), 'x': (GOGGLE_MIRROR_X - 0.088, GOGGLE_MIRROR_X + 0.088),
                            'root_z': 1.392, 'thick_ramp': (1.29, 1.36)})
# 最初の房の並び：つむじの向き、つむじから放射状の輪 (角度, 本数, 流れの角度, 浮き, 幅, 位相)、
# 絵を読んだ房の表 (根, 先, 浮き, 幅)
LOCK_WHORL = CH.p('hair.LOCK_WHORL', (0.0, 0.42, 0.9))
LOCK_RINGS = CH.p('hair.LOCK_RINGS', ((36, 7, 48, 0.034, 0.088, 0.5), (66, 9, 44, 0.030, 0.088, 0.0),
                                      (96, 10, 36, 0.022, 0.080, 0.5)))
LOCK_TABLE = CH.p('hair.LOCK_TABLE', (
    ((0.030, 0.015, 1.505), (-0.045, -0.050, 1.580), 0.045, 0.070),
    ((-0.045, 0.020, 1.515), (-0.110, -0.050, 1.525), 0.030, 0.070),
    ((0.050, 0.020, 1.515), (0.095, -0.075, 1.530), 0.030, 0.070),
    ((-0.080, 0.030, 1.490), (-0.160, -0.030, 1.480), 0.025, 0.065),
    ((0.090, 0.030, 1.490), (0.170, -0.020, 1.450), 0.025, 0.065),
))


def log(*a) -> None:
    import resource
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    print(f'[hair {time.time() - T0:7.1f}s {mem:4.1f}GB]', *a, flush=True)


def ramp(t, t0: float, t1: float, a: float = 0.0, b: float = 1.0):
    s = np.clip((np.asarray(t, float) - t0) / (t1 - t0), 0, 1)
    return a + (b - a) * s * s * (3 - 2 * s)


def smooth_max(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """なめらかな和（内側が正の場）"""
    h = np.clip(0.5 + 0.5 * (a - b) / k, 0, 1)
    return (b + (a - b) * h + k * h * (1 - h)).astype(np.float32)


def smooth_min(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """なめらかな積（内側が正の場）"""
    return -smooth_max(-a, -b, k)


# ---------------------------------------------------------------- 絵の測り

def _rgba(view: str) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(os.path.join(V.SRC, V.VIEWS[view]['file'])).convert('RGBA')).astype(np.int32)


def skin_mask(view: str) -> np.ndarray:
    """肌の色の画素（顔・首・手）"""
    im = _rgba(view)
    r, g, b, a = im[..., 0], im[..., 1], im[..., 2], im[..., 3]
    m = (a > 128) & (r > 200) & (g > 140) & (g < 215) & (b > 100) & (b < 185) & (r - b > 50)
    return ndi.binary_opening(m, iterations=1)


def head_masks(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], open_m: float, close_m: float
               ) -> dict[str, np.ndarray]:
    """頭（Z_FIT より上）の外形を開いて閉じた外形（房の先を落とし、房の間を埋める）"""
    from skimage.morphology import disk
    out = {}
    for n in REAL:
        c, m = cams[n], masks[n].copy()
        v_cut = int(c.v_of(Z_FIT - 0.03))
        m[v_cut:] = False
        ro, rc = int(round(open_m * c.ppm)), int(round(close_m * c.ppm))
        # 頭のまわりだけ切り出して（大きな円の開き・閉じは遅い）
        ua, ub = int(c.u0 - 0.40 * c.ppm), int(c.u0 + 0.40 * c.ppm)
        sub = m[:v_cut, ua:ub]
        sub = ndi.binary_opening(sub, disk(ro))
        sub = ndi.binary_closing(np.pad(sub, rc), disk(rc))[rc:-rc, rc:-rc]
        mm = np.zeros_like(m)
        mm[:v_cut, ua:ub] = sub
        lab, nl = ndi.label(mm)
        if nl > 1:
            sizes = ndi.sum(mm, lab, range(1, nl + 1))
            mm = lab == (int(np.argmax(sizes)) + 1)
        out[n] = mm
    return out


def row_extent(mask: np.ndarray, cam: V.Cam, zs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """高さごとの外形の左右の端（画像の横の座標を世界の m にしたもの：(u - u0) / ppm）。無い行は nan"""
    lo = np.full(len(zs), np.nan)
    hi = np.full(len(zs), np.nan)
    for k, z in enumerate(zs):
        v = int(math.floor(cam.v_of(z)))
        if 0 <= v < mask.shape[0]:
            cols = np.nonzero(mask[v])[0]
            if len(cols):
                lo[k] = (cols[0] - cam.u0) / cam.ppm
                hi[k] = (cols[-1] + 1 - cam.u0) / cam.ppm
    return lo, hi


def _fill_smooth(a: np.ndarray, sigma: float) -> np.ndarray:
    ok = np.isfinite(a)
    b = np.interp(np.arange(len(a)), np.nonzero(ok)[0], a[ok])
    return ndi.gaussian_filter1d(b, sigma, mode='nearest')


def support(a: float, bf: float, bb: float, nf: float, nb: float, r: np.ndarray, front: bool) -> float:
    """断面（中心 0）の、向き r（水平の単位ベクトル）への張り出し。front=True は前の半分（y < 0）"""
    t = np.linspace(0, math.pi / 2, 200)
    n = nf if front else nb
    b = bf if front else bb
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2 / n)
    y = b * np.abs(s) ** (2 / n)
    best = -1e9
    for sx in (-1, 1):
        for sy in ((-1,) if front else (1,)):
            best = max(best, float(np.max(sx * x * r[0] + sy * y * r[1])))
    return best


def solve_exponent(a, bf, bb, n_other, r, target, front: bool, lo=1.7, hi=4.0) -> float:
    """張り出しが target になる指数（二分法。範囲の外は端）"""
    def f(n):
        return support(a, bf, bb, n if front else n_other, n_other if front else n, r, front) - target
    if f(lo) >= 0:
        return lo
    if f(hi) <= 0:
        return hi
    for _ in range(30):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------- 断面の積み重ね

@dataclass
class Stack:
    """高さごとの超楕円の断面。配列はすべて zs と同じ長さ"""
    zs: np.ndarray
    a: np.ndarray
    cx: np.ndarray
    cy: np.ndarray
    bf: np.ndarray
    bb: np.ndarray
    nf: np.ndarray
    nb: np.ndarray

    def at(self, z: np.ndarray) -> dict:
        return {k: np.interp(z, self.zs, getattr(self, k)) for k in ('a', 'cx', 'cy', 'bf', 'bb', 'nf', 'nb')}

    def rho(self, xs: np.ndarray, ys: np.ndarray, zs: np.ndarray) -> np.ndarray:
        """格子 (z, x, y) の各点の「断面の中の割合」ρ（1 が面、内側が 1 未満）"""
        p = self.at(zs)
        out = np.full((len(zs), len(xs), len(ys)), 9.0, np.float32)
        for k in range(len(zs)):
            a = p['a'][k]
            if a < 1e-3:
                continue
            dx = np.abs(xs - p['cx'][k])[:, None] / a
            dy = (ys - p['cy'][k])[None, :]
            front = dy < 0
            b = np.where(front, p['bf'][k], p['bb'][k])
            n = np.where(front, p['nf'][k], p['nb'][k])
            out[k] = ((dx ** n + (np.abs(dy) / np.maximum(b, 1e-3)) ** n) ** (1 / n)).astype(np.float32)
        return out


def occ_to_sdf(occ: np.ndarray, vox: float, sigma: float = 1.5) -> np.ndarray:
    """占有 → 符号つき距離（m、内側が正）。ボクセルの階段を消すため少しぼかす"""
    d = np.where(occ, ndi.distance_transform_edt(occ) - 0.5, -(ndi.distance_transform_edt(~occ) - 0.5))
    return ndi.gaussian_filter((d * vox).astype(np.float32), sigma)


def skin_stack(cams: dict[str, V.Cam], masks: dict[str, np.ndarray]) -> Stack:
    """頭（顔・あご・頭の骨）の断面（本文の 1）"""
    zs = np.arange(SKIN['zs'][0], SKIN['zs'][1], 0.002)
    f, s, t = cams['front'], cams['side_right'], cams['three_quarter']
    sk_f = skin_mask('front')
    lo_f, hi_f = row_extent(sk_f, f, zs)
    # 側面の顔の輪郭：肌の外形を 1.2cm の円で開いて鼻を落とす
    from skimage.morphology import disk
    sk_s = skin_mask('side_right')
    sk_s[:int(s.v_of(SKIN['side_rows'][1]))] = False
    sk_s[int(s.v_of(SKIN['side_rows'][0])):] = False
    sk_so = ndi.binary_opening(sk_s, disk(int(0.012 * s.ppm)))
    _, fr_s = row_extent(sk_so, s, zs)          # 真横の絵の右 = 前（-Y）。fr_s は前の端の -y
    lo_t, hi_t = row_extent(skin_mask('three_quarter'), t, zs)
    # 左右の半幅：あご〜ほお（耳より下 z < 1.262）は正面の肌の幅、上は頭の骨のふくらみ（節）
    half = (hi_f - lo_f) / 2
    kz = list(SKIN['jaw_z'])
    ka = [float(np.interp(z, zs, np.where(np.isfinite(half), half, np.nan))) for z in kz]
    kz_all = [SKIN['zs'][0]] + kz + list(SKIN['ka_z'])
    ka_all = [0.0] + ka + list(SKIN['ka'])
    nj = len(kz) + 2
    ka_all = np.maximum.accumulate(np.nan_to_num(np.array(ka_all), nan=0.0)[:nj]).tolist() + ka_all[nj:]
    a = PchipInterpolator(kz_all, ka_all)(zs)
    # 前の端（-y）：右真横の絵の顔の輪郭を読んだ節（鼻は除く。前髪の下の額・眉・目・口・あご）。
    # 真横の絵では前髪とゴーグルが額の前に出ていて、外形から直接は測れないので、肌の縁を読んだ値
    kz_f, ky_f = SKIN['front_z'], SKIN['front_y']
    yf = PchipInterpolator(kz_f, ky_f)(zs)
    # 後ろの端：あごの下は首の前、上へ行くほど頭の骨の後ろ（髪の中）
    kz_b, ky_b = SKIN['back_z'], SKIN['back_y']
    yb = PchipInterpolator(kz_b, ky_b)(zs)
    cy = (yf + yb) / 2
    bf = cy - yf
    bb = yb - cy
    cx = np.full(len(zs), float(np.nanmedian(((hi_f + lo_f) / 2)[(zs > SKIN['cx_z'][0]) & (zs < SKIN['cx_z'][1])])))
    # 前の半分の指数：右前斜めの絵の顔の右の縁（本人の左のほお）に届くように（あご〜ほお）
    nb = np.full(len(zs), 2.2)
    # 前の半分の指数：ほお骨（z 1.28）で 2.6 から、あごの先で 2.0 へ（ほおの前を平らに、あごを細く。
    # 右前斜めの外形に合わせて解くと、ほおが前へふくらんだ「口の突き出た」顔になった）
    nf = np.interp(zs, SKIN['nf_z'], SKIN['nf'])
    r = t.r[:2]
    return Stack(zs, a, cx, cy, bf, bb, nf, nb)


def cap_stack(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], p: dict, skin: Stack | None = None
              ) -> tuple[Stack, dict]:
    """髪の帽子の断面（本文の 2）"""
    hm = head_masks(cams, masks, p['cap_open_m'], p['cap_close_m'])
    zs = np.arange(CAP['zs'][0], CAP['zs'][1], 0.002)
    f, s, t = cams['front'], cams['side_right'], cams['three_quarter']
    lo_f, hi_f = row_extent(hm['front'], f, zs)
    lo_s, hi_s = row_extent(hm['side_right'], s, zs)      # 真横：右 = 前。y = -(u - u0)/ppm
    lo_t, hi_t = row_extent(hm['three_quarter'], t, zs)
    ins = p['cap_inset_m']
    sig = 0.01 / 0.002
    top = 0.5 * (zs[np.isfinite(lo_f)].max() + zs[np.isfinite(lo_s)].max()) - ins
    a = np.maximum(_fill_smooth((hi_f - lo_f) / 2 - ins, sig), 0)
    cx = np.full(len(zs), float(np.nanmedian(((hi_f + lo_f) / 2)[(zs > CAP['cx_z'][0]) & (zs < CAP['cx_z'][1])])))
    yf = _fill_smooth(-hi_s + ins, sig)
    yb = _fill_smooth(-lo_s - ins, sig)
    if skin is not None:
        # 前髪の高さでは帽子の前を額の 1.5cm 前までに（真横の絵の前の端は前髪の先とゴーグル。
        # そのままだと額の上に 3cm のひさしができる）。ゴーグルの高さ（z > 1.40）は前へ出てよい
        sy = np.interp(zs, skin.zs, skin.cy - skin.bf, right=np.nan)
        lim = sy - 0.015 - 0.032 * ramp(zs, *CAP['fringe_ramp'])
        yf = np.where(np.isfinite(lim) & (zs < CAP['fringe_ztop']), np.maximum(yf, lim), yf)
    # 上と下は楕円の弧で丸く閉じる（平らな台・とがりにしない）：てっぺんから 4cm、えり足の下端から 3cm
    z1, (zb0, zb1) = top - 0.04, CAP['nape']
    k1 = int(np.searchsorted(zs, z1))
    kb = int(np.searchsorted(zs, zb1))
    s_top = np.sqrt(np.clip(1 - ((zs - z1) / (top - z1)).clip(0, None) ** 2, 0, 1))
    s_bot = np.sqrt(np.clip(1 - ((zb1 - zs) / (zb1 - zb0)).clip(0, None) ** 2, 0, 1))
    for arr in (a, yf, yb):
        arr[k1:] = arr[k1]
        arr[:kb] = arr[kb]
    mid = (yf + yb) / 2
    sc = s_top * s_bot
    a = a * sc
    yf = mid + (yf - mid) * sc
    yb = mid + (yb - mid) * sc
    uc = CAP.get('undercut')
    if uc and skin is not None:
        # 刈り上げ（ヤーナ）：この高さより下の帽子は頭の面（skin）から margin までに締める（横と後ろの髪は短い。
        # 絵の外形の、下がった長い房で広がった帽子が耳を覆わないように）
        w = 1.0 - ramp(zs, uc['z'][0], uc['z'][1])
        m = uc['margin']
        sa = np.interp(zs, skin.zs, skin.a + m, left=np.nan, right=np.nan)
        syb = np.interp(zs, skin.zs, skin.cy + skin.bb + m, left=np.nan, right=np.nan)
        a = np.where(np.isfinite(sa), a - w * np.maximum(a - sa, 0), a)
        yb = np.where(np.isfinite(syb), yb - w * np.maximum(yb - syb, 0), yb)
    cy = (yf + yb) / 2
    bf, bb = cy - yf, yb - cy
    r = t.r[:2]
    nf = np.full(len(zs), np.nan)
    nb = np.full(len(zs), np.nan)
    for k, z in enumerate(zs):
        if not (CAP['n_zmin'] < z < top - 0.03) or not np.isfinite(hi_t[k]):
            continue
        c0 = cx[k] * r[0] + cy[k] * r[1]
        # 右の縁 = 本人の左前のふくらみ（前の半分）、左の縁 = 右後ろ（後ろの半分）
        nf[k] = solve_exponent(a[k], bf[k], bb[k], 2.2, r, hi_t[k] - ins - c0, True, 2.0, 3.2)
        nb[k] = solve_exponent(a[k], bf[k], bb[k], 2.2, -r, -(lo_t[k] + ins - c0), False, 2.0, 3.2)
    nf = _fill_smooth(nf, 8.0)
    nb = _fill_smooth(nb, 8.0)
    # 右前斜めの右の縁に、指数の下限でも届きすぎる高さは、断面を縮める（帽子を外形の内側に）
    shrink = np.ones(len(zs))
    for k, z in enumerate(zs):
        if a[k] > 1e-3 and np.isfinite(hi_t[k]) and z > CAP['n_zmin']:
            c0 = cx[k] * r[0] + cy[k] * r[1]
            sup = support(a[k], bf[k], bb[k], nf[k], nb[k], r, True)
            tgt = hi_t[k] - ins - c0
            shrink[k] = min(1.0, tgt / max(sup, 1e-6))
    shrink = ndi.gaussian_filter1d(shrink, 4.0)
    a = a * shrink
    bf = bf * shrink
    info = {'top_z': round(float(top), 4), 'nf_mean': round(float(np.mean(nf)), 3),
            'nb_mean': round(float(np.mean(nb)), 3)}
    return Stack(zs, a, cx, cy, bf, bb, nf, nb), info


# ---------------------------------------------------------------- 髪の房

@dataclass
class Lock:
    """1 本の房。向きは頭の中心 HEAD_C からの単位ベクトル"""
    root: tuple        # 根の向き
    tip: tuple         # 先の向き
    lift: float        # 先の、帽子の面からの浮き（m）
    width: float       # 根元の幅（m）
    name: str = ''


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def slerp(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    a, b = _unit(a), _unit(b)
    om = math.acos(float(np.clip(a @ b, -1, 1)))
    if om < 1e-6:
        return np.repeat(a[None], len(t), 0)
    so = math.sin(om)
    return (np.sin((1 - t) * om)[:, None] * a + np.sin(t * om)[:, None] * b) / so


class RadialTable:
    """帽子（と頭）の面までの、中心 HEAD_C からの距離 r(向き)。方位角・仰角の表から双線形で読む"""

    def __init__(self, field: np.ndarray, lo: np.ndarray, vox: float, step_deg: float = 2.0):
        self.step = step_deg
        th = np.radians(np.arange(-180, 180 + step_deg, step_deg))
        ph = np.radians(np.arange(-90, 90 + step_deg, step_deg))
        TH, PH = np.meshgrid(th, ph, indexing='ij')
        d = np.stack([np.cos(PH) * np.sin(TH), -np.cos(PH) * np.cos(TH), np.sin(PH)], -1)  # θ=0 は前（-Y）
        rs = np.arange(0.0, 0.40, 0.001)
        pts = HEAD_C[None, None, None] + rs[None, None, :, None] * d[:, :, None, :]
        # 格子 (z, x, y) の連続の添字
        idx = [(pts[..., 2] - lo[2]) / vox - 0.5, (pts[..., 0] - lo[0]) / vox - 0.5, (pts[..., 1] - lo[1]) / vox - 0.5]
        val = ndi.map_coordinates(field, [i.ravel() for i in idx], order=1, mode='constant', cval=-1.0)
        val = val.reshape(pts.shape[:3])
        inside = val > 0
        # 中心から外へ、最初に外へ出る所（外に出る直前の点から、場の値で線形に補間）
        out_first = np.argmax(~inside, axis=2)
        k = np.clip(out_first, 1, len(rs) - 1)
        v0 = np.take_along_axis(val, (k - 1)[..., None], 2)[..., 0]
        v1 = np.take_along_axis(val, k[..., None], 2)[..., 0]
        frac = np.clip(v0 / np.maximum(v0 - v1, 1e-9), 0, 1)
        self.r = (rs[k - 1] + frac * 0.001).astype(np.float32)

    def __call__(self, d: np.ndarray) -> np.ndarray:
        d = np.atleast_2d(d)
        th = np.degrees(np.arctan2(d[:, 0], -d[:, 1]))
        ph = np.degrees(np.arcsin(np.clip(d[:, 2], -1, 1)))
        return ndi.map_coordinates(self.r, [(th + 180) / self.step, (ph + 90) / self.step], order=1, mode='nearest')


def lock_samples(L: Lock, rtab: RadialTable, thick: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """房に沿った楕円体の並び：中心 (n,3)、軸の行列 (n,3,3)（列が T, B, N）、半径 (n,3)"""
    d0, d1 = _unit(L.root), _unit(L.tip)
    om = math.acos(float(np.clip(d0 @ d1, -1, 1)))
    r_mid = float(rtab(d0)[0])
    length = om * r_mid + L.lift
    w_tip = 0.0022

    def leaf(t):
        """葉の形の幅（根元の 0.75 から 30% の所で最も広く、先へ細る）"""
        return L.width * 0.5 * (1 - t) ** 0.8 * (0.75 + 0.8 * t) + w_tip

    # 並べる間隔は半径の 0.4 倍（先ほど細かく）
    ts = [0.0]
    while ts[-1] < 1.0:
        ts.append(min(1.0, ts[-1] + 0.4 * float(leaf(ts[-1])) / max(length, 1e-3)))
    t = np.array(ts)
    dirs = slerp(d0, d1, t)
    w = leaf(t)
    bangs = L.name.startswith('bangs')
    if bangs:
        thick = 0.40
    h = np.maximum(w * thick, 0.0018)
    R = rtab(dirs) + L.lift * t ** 2
    if bangs:
        # 前髪は額に半分うめず、額の上に載せる（内側の面が額の面のすぐ前）。右真横の絵では前髪が額の前へ
        # 約 2cm 出ている。先へ行くほど額に沿って薄くなる
        R = R + 0.8 * h
    P = HEAD_C[None] + R[:, None] * dirs
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = dirs - (dirs * T).sum(1, keepdims=True) * T
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    B = np.cross(T, N)
    radii = np.stack([np.maximum(w, h) * 1.0, w, h], 1)
    frames = np.stack([T, B, N], 2)
    return P, frames, radii


def lock_field(samples, lo: np.ndarray, vox: float, shape) -> tuple[tuple, np.ndarray] | None:
    """房の場（内側が正、およその距離 m）を、房のまわりの小さな箱で返す：(箱の始めの添字, 場)"""
    P, Fr, Rd = samples
    rmax = Rd.max(1)
    pmin = P - rmax[:, None] - 2 * vox
    pmax = P + rmax[:, None] + 2 * vox
    # 格子の添字 (z, x, y)
    i0 = np.floor((np.array([pmin[:, 2].min(), pmin[:, 0].min(), pmin[:, 1].min()]) - lo[[2, 0, 1]]) / vox).astype(int)
    i1 = np.ceil((np.array([pmax[:, 2].max(), pmax[:, 0].max(), pmax[:, 1].max()]) - lo[[2, 0, 1]]) / vox).astype(int)
    i0 = np.maximum(i0, 0)
    i1 = np.minimum(i1, np.array(shape))
    if np.any(i1 <= i0):
        return None
    zs = lo[2] + (np.arange(i0[0], i1[0]) + 0.5) * vox
    xs = lo[0] + (np.arange(i0[1], i1[1]) + 0.5) * vox
    ys = lo[1] + (np.arange(i0[2], i1[2]) + 0.5) * vox
    out = np.full((len(zs), len(xs), len(ys)), -0.02, np.float32)
    for c, M, r in zip(P, Fr, Rd):
        a0 = np.searchsorted(zs, c[2] - r.max() - vox)
        a1 = np.searchsorted(zs, c[2] + r.max() + vox)
        b0 = np.searchsorted(xs, c[0] - r.max() - vox)
        b1 = np.searchsorted(xs, c[0] + r.max() + vox)
        c0 = np.searchsorted(ys, c[1] - r.max() - vox)
        c1 = np.searchsorted(ys, c[1] + r.max() + vox)
        if a1 <= a0 or b1 <= b0 or c1 <= c0:
            continue
        Z, X, Y = np.meshgrid(zs[a0:a1] - c[2], xs[b0:b1] - c[0], ys[c0:c1] - c[1], indexing='ij')
        q = np.stack([X, Y, Z], -1) @ M          # 局所の座標 (T, B, N)
        e = np.sqrt(((q / r) ** 2).sum(-1))
        val = (1 - e) * r.min()
        np.maximum(out[a0:a1, b0:b1, c0:c1], val.astype(np.float32), out=out[a0:a1, b0:b1, c0:c1])
    return (tuple(i0), out)


# ---------------------------------------------------------------- 外形への当てはめ（2 次元の投影）

class Views2D:
    """当てはめ用：3 視点の、頭のまわりの切り抜き（半分の解像度）"""

    def __init__(self, cams: dict[str, V.Cam], masks: dict[str, np.ndarray], scale: float = 0.5):
        self.cams, self.scale = cams, scale
        self.crop = {}
        self.art = {}
        for n in REAL:
            c = cams[n]
            u_a, u_b = c.u0 - 0.30 * c.ppm, c.u0 + 0.30 * c.ppm
            v_a, v_b = c.v_of(1.60), c.v_of(Z_FIT)
            self.crop[n] = (u_a, v_a, int((u_b - u_a) * scale), int((v_b - v_a) * scale))
            ua, va, W, H = self.crop[n]
            yy, xx = np.mgrid[0:H, 0:W]
            src = ndi.map_coordinates(masks[n].astype(np.float32),
                                      [va + (yy + 0.5) / scale - 0.5, ua + (xx + 0.5) / scale - 0.5], order=1)
            self.art[n] = src > 0.5

    def to_px(self, n: str, P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        u, v = self.cams[n].project(P)
        ua, va, W, H = self.crop[n]
        return (u - ua) * self.scale, (v - va) * self.scale

    def splat_field(self, n: str, field: np.ndarray, lo, vox) -> np.ndarray:
        """場の内側（> 0）のボクセルを投影した外形"""
        ua, va, W, H = self.crop[n]
        iz, ix, iy = np.nonzero(field > 0)
        P = np.stack([lo[0] + (ix + 0.5) * vox, lo[1] + (iy + 0.5) * vox, lo[2] + (iz + 0.5) * vox], 1)
        u, v = self.to_px(n, P)
        img = np.zeros((H, W), bool)
        hw = 0.5 * vox * self.cams[n].ppm * self.scale * 0.999   # ボクセルの投影の半幅（中心と 8 つの縁を打つ）
        for du in (-hw, 0.0, hw):
            for dv in (-hw, 0.0, hw):
                iu, iv = np.floor(u + du).astype(int), np.floor(v + dv).astype(int)
                ok = (iu >= 0) & (iu < W) & (iv >= 0) & (iv < H)
                img[iv[ok], iu[ok]] = True
        return img

    def raster_lock(self, n: str, samples) -> tuple[tuple, np.ndarray] | None:
        """房の楕円体の並びを投影した外形（小さな箱：(v0, u0, 画像)）"""
        P, Fr, Rd = samples
        cam = self.cams[n]
        k = cam.ppm * self.scale
        A = np.stack([cam.r, np.array([0, 0, -1.0])], 0)          # 画像の (右, 下)
        u, v = self.to_px(n, P)
        # 2 次元の共分散：(A M diag(r²) Mᵀ Aᵀ) k²
        AM = np.einsum('ij,njk->nik', A, Fr)                      # (n,2,3)
        S = np.einsum('nik,nk,njk->nij', AM, Rd ** 2, AM) * k * k
        hu, hv = np.sqrt(S[:, 0, 0]), np.sqrt(S[:, 1, 1])
        ua, va, W, H = self.crop[n]
        u0, u1 = int(max(0, np.floor((u - hu).min()))), int(min(W, np.ceil((u + hu).max()) + 1))
        v0, v1 = int(max(0, np.floor((v - hv).min()))), int(min(H, np.ceil((v + hv).max()) + 1))
        if u1 <= u0 or v1 <= v0:
            return None
        yy, xx = np.mgrid[v0:v1, u0:u1]
        px, py = xx.ravel() + 0.5, yy.ravel() + 0.5
        det = S[:, 0, 0] * S[:, 1, 1] - S[:, 0, 1] ** 2
        inv = np.stack([S[:, 1, 1], -S[:, 0, 1], S[:, 0, 0]], 1) / np.maximum(det, 1e-12)[:, None]
        img = np.zeros(len(px), bool)
        for j in range(len(P)):
            du, dv = px - u[j], py - v[j]
            m = (np.abs(du) <= hu[j] + 1) & (np.abs(dv) <= hv[j] + 1)
            if not m.any():
                continue
            q = inv[j, 0] * du[m] ** 2 + 2 * inv[j, 1] * du[m] * dv[m] + inv[j, 2] * dv[m] ** 2
            img[np.nonzero(m)[0][q <= 1]] = True
        return (v0, u0), img.reshape(v1 - v0, u1 - u0)


def face_zone_penalty(P: np.ndarray, Rd: np.ndarray) -> float:
    """顔の前（生え際より下の顔の面の前）に入る房の点の数（罰）"""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    zh = hairline_z(np.abs(x))
    bad = (y - Rd[:, 2] < HAIRLINE['y_face'] + 0.01) & (z < zh + 0.005) & (np.abs(x) < 0.12)
    if not PARTS['goggles']:
        return float(bad.sum())
    g = GOGGLES
    gog = (y < -0.04) & (x > g['x'][0] - 0.01) & (x < g['x'][1] + 0.01) & (z > g['z'][0] - 0.01) & (z < g['z'][1] + 0.005)
    return float(bad.sum() + gog.sum())


def hairline_z(ax: np.ndarray) -> np.ndarray:
    """生え際の高さ（顔の前を切り取る範囲の上）。正面の絵の肌の縁を読んだ節：額の中ほどは眉の上（前髪の下）、
    目の外の端から外は、もみあげの下（あごの上）まで下がる"""
    return PchipInterpolator(HAIRLINE['x'], HAIRLINE['z'], extrapolate=True)(np.clip(ax, 0, HAIRLINE['x'][-1]))


def initial_locks() -> list[Lock]:
    """最初の房の並び：つむじ W から放射状に流れる 3 つの輪（顔の前は除く）"""
    W = _unit(list(LOCK_WHORL))
    # W に垂直な 2 つの向き
    e1 = _unit(np.cross(W, [1.0, 0, 0]))
    e2 = np.cross(W, e1)
    locks = []
    # (つむじからの角度, 本数, 流れの長さの角度, 浮き, 幅, 位相)。ハル：つむじのすぐまわりの 4 本の輪は、頭のてっぺんの
    # こぶ・まげに見えたので置かない。W1-00b の頭の横・後ろ・上の絵：房は幅 6〜9cm の大きな葉を重ねた形（以前の 9・12・12 本、
    # 幅 6〜7cm では小さな房が多すぎて、横から見ると丸いもじゃもじゃに見えた）。本数を減らし、幅と浮きを大きくした
    rings = LOCK_RINGS
    for ri, (al, n, beta, lift, w, ph) in enumerate(rings):
        for j in range(n):
            ang = 2 * math.pi * (j + ph) / n
            axis_dir = math.cos(ang) * e1 + math.sin(ang) * e2   # つむじから見た流れの向き
            a = math.radians(al)
            d0 = _unit(math.cos(a) * W + math.sin(a) * axis_dir)
            b = math.radians(al + beta)
            d1 = _unit(math.cos(b) * W + math.sin(b) * axis_dir)
            # 顔の前（前向きで生え際より下）に根か先がある房は置かない
            p0 = HEAD_C + 0.13 * d0
            p1 = HEAD_C + 0.15 * d1
            if any((p[1] < HAIRLINE['y_face'] - 0.02) and (p[2] < hairline_z(abs(p[0])) + 0.01) and abs(p[0]) < 0.11
                   for p in (p0, p1)):
                # 前へ流れる房は、額の上で止める（前髪の上の立ち上がり）
                if d0[1] < -0.2 and p0[2] > 1.40:
                    b = math.radians(al + beta * 0.45)
                    d1 = _unit(math.cos(b) * W + math.sin(b) * axis_dir)
                else:
                    continue
            locks.append(Lock(tuple(d0), tuple(d1), lift, w, f'r{ri}_{j}'))
    # ゴーグルの上（後ろ）から立ち上がる大きな房（正面・右前斜めの絵：ゴーグルの上に頭の高さの約 2 割の髪。
    # 真ん中の高い房は前へかぶさり、本人の右へ流れる）。根・先は絵を読んだ表（つむじからの放射ではない）
    top = LOCK_TABLE   # (根, 先, 浮き, 幅)
    for j, (r0, r1, lift, w) in enumerate(top):
        d0 = _unit(np.array(r0) - HEAD_C)
        d1 = _unit(np.array(r1) - HEAD_C)
        locks.append(Lock(tuple(d0), tuple(d1), lift, w, f'top_front_{j}'))
    return locks


def rotate_toward(d: np.ndarray, axis: np.ndarray, ang: float) -> np.ndarray:
    """向き d を、軸 axis のまわりに ang ラジアン回す（ロドリゲス）"""
    k = _unit(axis)
    return d * math.cos(ang) + np.cross(k, d) * math.sin(ang) + k * (k @ d) * (1 - math.cos(ang))


def perturb(L: Lock, what: str, step: float) -> Lock:
    d0, d1 = _unit(L.root), _unit(L.tip)
    if what == 'lift':
        return Lock(L.root, L.tip, float(np.clip(L.lift + step, 0.0, LOCK_LIFT_MAX)), L.width, L.name)
    if what == 'width':
        return Lock(L.root, L.tip, L.lift, float(np.clip(L.width + step, 0.03, LOCK_WIDTH_MAX)), L.name)
    flow = _unit(np.cross(d0, d1))          # 大きな円の軸
    if what == 'len':                        # 流れに沿って伸ばす・縮める
        d1n = rotate_toward(d1, flow, math.radians(step))
        om = math.degrees(math.acos(float(np.clip(d0 @ d1n, -1, 1))))
        if not (12 <= om <= 80):
            return L
        return Lock(L.root, tuple(d1n), L.lift, L.width, L.name)
    if what == 'swing':                      # 先を横へ振る（根のまわりに回す）
        d1n = rotate_toward(d1, d0, math.radians(step))
        return Lock(L.root, tuple(d1n), L.lift, L.width, L.name)
    raise ValueError(what)


class Fitter:
    """房の当てはめ（本文の 3 の最後）。投影の数え上げを房ごとに差し替えて、IoU を速く求める"""

    def __init__(self, v2: Views2D, base: dict[str, np.ndarray], rtab: RadialTable, thick: float,
                 locks: list[Lock], init: list[Lock]):
        self.v2, self.rtab, self.thick = v2, rtab, thick
        self.base = base
        self.cnt = {n: base[n].astype(np.int32) for n in REAL}
        self.locks = list(locks)
        self.init = list(init)
        self.rast = [self._raster(L) for L in self.locks]
        for i in range(len(self.locks)):
            self._apply(self.rast[i], +1)

    def _raster(self, L: Lock) -> dict:
        s = lock_samples(L, self.rtab, self.thick)
        return {'r': {n: self.v2.raster_lock(n, s) for n in REAL}, 'pen': face_zone_penalty(s[0], s[2])}

    def _apply(self, R: dict, sign: int) -> None:
        for n in REAL:
            x = R['r'][n]
            if x is None:
                continue
            (v0, u0), img = x
            self.cnt[n][v0:v0 + img.shape[0], u0:u0 + img.shape[1]] += sign * img

    def ious(self) -> dict[str, float]:
        out = {}
        for n in REAL:
            c = self.cnt[n] > 0
            a = self.v2.art[n]
            out[n] = float((c & a).sum() / max(1, (c | a).sum()))
        return out

    def plaus(self, i: int, L: Lock) -> float:
        """もっともらしさの罰：最初の流れからの外れ（先の向き）"""
        d1, e1 = _unit(L.tip), _unit(self.init[i].tip)
        dev = math.degrees(math.acos(float(np.clip(d1 @ e1, -1, 1))))
        return 0.0004 * max(0.0, dev - 20.0)

    def score(self, pen_total: float, plaus_total: float) -> float:
        io = self.ious()
        return float(sum(VIEW_WEIGHT[n] * io[n] for n in REAL) / sum(VIEW_WEIGHT.values())) \
            - 0.01 * pen_total - plaus_total

    def run(self, sweeps: int = 6, log=print) -> None:
        pen = [R['pen'] for R in self.rast]
        pl = [self.plaus(i, L) for i, L in enumerate(self.locks)]
        best = self.score(sum(pen), sum(pl))
        log('  房の当てはめ 開始', round(best, 4), {k: round(v, 4) for k, v in self.ious().items()})
        steps = {'lift': 0.008, 'width': 0.008, 'len': 8.0, 'swing': 10.0}
        for sw in range(sweeps):
            sc = 1.0 if sw < sweeps // 2 else 0.5
            nacc = 0
            for i in range(len(self.locks)):
                for what, st in steps.items():
                    for sgn in (+1, -1):
                        L2 = perturb(self.locks[i], what, sgn * st * sc)
                        if L2 is self.locks[i]:
                            continue
                        R2 = self._raster(L2)
                        self._apply(self.rast[i], -1)
                        self._apply(R2, +1)
                        p2 = self.plaus(i, L2)
                        s2 = self.score(sum(pen) - pen[i] + R2['pen'], sum(pl) - pl[i] + p2)
                        if s2 > best + 1e-5:
                            best, self.locks[i], self.rast[i], pen[i], pl[i] = s2, L2, R2, R2['pen'], p2
                            nacc += 1
                            break
                        self._apply(R2, -1)
                        self._apply(self.rast[i], +1)
            log(f'  房の当てはめ {sw + 1}/{sweeps}', round(best, 4), {k: round(v, 4) for k, v in self.ious().items()},
                '動かした', nacc)


# ---------------------------------------------------------------- まとめ：頭の場

def stack_field(st: Stack, lo, vox, shape, k0: int) -> np.ndarray:
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(k0, nz) + 0.5) * vox
    rho = st.rho(xs, ys, zs)
    inside = (rho < 1.0) & (zs >= st.zs[0])[:, None, None] & (zs <= st.zs[-1])[:, None, None]
    return occ_to_sdf(inside, vox)


def ellipsoid_field(c, radii, lo, vox, shape, k0) -> np.ndarray:
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(k0, nz) + 0.5) * vox
    Z, X, Y = np.meshgrid(zs - c[2], xs - c[0], ys - c[1], indexing='ij')
    e = np.sqrt((X / radii[0]) ** 2 + (Y / radii[1]) ** 2 + (Z / radii[2]) ** 2)
    return ((1 - e) * min(radii)).astype(np.float32)


def face_cut(lo, vox, shape, k0) -> np.ndarray:
    """顔の前を切り取る範囲の場（範囲の中が正）：y < y_face かつ z < 生え際"""
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(k0, nz) + 0.5) * vox
    zh = hairline_z(np.abs(xs))                       # (nx,)
    fy = np.broadcast_to((HAIRLINE['y_face'] - ys)[None, None, :], (len(zs), 1, ny))
    fz = zh[None, :, None] - zs[:, None, None]
    return smooth_min(np.broadcast_to(fy, (len(zs), nx, ny)), np.broadcast_to(fz, (len(zs), nx, ny)), 0.008)


def goggle_zone(lo, vox, shape, k0) -> np.ndarray:
    """ゴーグルの枠の範囲の場（中が正、m）：正面から見た角の丸い長方形（x, z）× 顔の側（y < -0.03）"""
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(k0, nz) + 0.5) * vox
    g = GOGGLES
    cx, hx = (g['x'][0] + g['x'][1]) / 2, (g['x'][1] - g['x'][0]) / 2 - g['round']
    cz, hz = (g['z'][0] + g['z'][1]) / 2, (g['z'][1] - g['z'][0]) / 2 - g['round']
    qx = np.abs(xs - cx) - hx                          # (nx,)
    qz = np.abs(zs - cz) - hz                          # (nz,)
    QX, QZ = np.meshgrid(qx, qz)                       # (nz, nx)
    d2 = np.hypot(np.maximum(QX, 0), np.maximum(QZ, 0)) + np.minimum(np.maximum(QX, QZ), 0) - g['round']
    win = (-d2).astype(np.float32)[:, :, None]
    front = (-0.03 - ys).astype(np.float32)[None, None, :]
    return smooth_min(np.broadcast_to(win, (len(zs), nx, ny)), np.broadcast_to(front, (len(zs), nx, ny)), 0.01)


def polygon_sdf2d(px: np.ndarray, pz: np.ndarray, poly) -> np.ndarray:
    """凸でなくてもよい多角形の、平面 (x, z) の符号つき距離（中が正、m）"""
    P = np.asarray(poly, float)
    d = np.full(px.shape, np.inf)
    inside = np.zeros(px.shape, bool)
    for i in range(len(P)):
        a, b = P[i], P[i - 1]
        e = b - a
        wx, wz = px - a[0], pz - a[1]
        t = np.clip((wx * e[0] + wz * e[1]) / (e @ e), 0, 1)
        d = np.minimum(d, np.hypot(wx - e[0] * t, wz - e[1] * t))
        c1 = pz >= a[1]
        c2 = pz < b[1]
        c3 = e[0] * wz > e[1] * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        inside ^= flip
    return np.where(inside, d, -d).astype(np.float32)


def _grid(lo, vox, shape, k0=0):
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(k0, nz) + 0.5) * vox
    return xs, ys, zs


def goggle_outline2d(xs: np.ndarray, zs: np.ndarray) -> dict[str, np.ndarray]:
    """ゴーグルの輪郭の平面の場 (nz, nx)：枠（2 つ）・レンズ（2 つ）・橋。中が正"""
    X, Z = np.meshgrid(xs, zs)
    out = {'frame': None, 'lens': None}
    for key, poly in (('frame', GOGGLE_FRAME), ('lens', GOGGLE_LENS)):
        right = polygon_sdf2d(X, Z, poly)
        left = polygon_sdf2d(X, Z, [(2 * GOGGLE_MIRROR_X - x, z) for x, z in poly])
        out[key] = np.maximum(right, left)
    (bx0, bx1), (bz0, bz1) = GOGGLE_BRIDGE
    out['bridge'] = np.minimum(np.minimum(X - bx0, bx1 - X), np.minimum(Z - bz0, bz1 - Z)).astype(np.float32)
    return out


def goggles_field(Cf: np.ndarray, lo, vox, shape) -> tuple[np.ndarray, np.ndarray]:
    """ゴーグル：2 つの角の丸い六角の枠（帽子の面から FRAME_T）＋ 4mm 奥のレンズ ＋ 細い橋。
    輪郭は正面の絵の枠・レンズ（正面の投影で切った柱を、帽子の面からの厚みで切る。額の丸みに沿って回り込む）。
    返り値：(ゴーグルの場, 房を切る範囲の場)。どちらも中が正"""
    xs, ys, zs = _grid(lo, vox, shape)
    o = goggle_outline2d(xs, zs)
    shp = Cf.shape
    front = np.broadcast_to((0.015 - ys).astype(np.float32)[None, None, :], shp)

    def prism(f2d):
        return np.broadcast_to(f2d[:, :, None], shp)
    ring = smooth_min(prism(o['frame']), -prism(o['lens']) + 0.0005, 0.0015)
    frame = smooth_min(smooth_min(ring, Cf + FRAME_T, 0.003), front, 0.004)
    lens = smooth_min(smooth_min(prism(o['lens']), Cf + LENS_T, 0.002), front, 0.004)
    bridge = smooth_min(smooth_min(prism(o['bridge']), Cf + BRIDGE_T, 0.003), front, 0.004)
    gog = np.maximum(np.maximum(frame, lens), bridge)
    zone = smooth_min(prism(np.maximum(o['frame'], o['bridge'])) + 0.004,
                      np.broadcast_to((-0.03 - ys).astype(np.float32)[None, None, :], shp), 0.01)
    return gog.astype(np.float32), zone.astype(np.float32)


def strap_field(env: np.ndarray, lo, vox, shape) -> np.ndarray:
    """ゴーグルのベルト：なめらかにした髪の包み（env、中が正）の面から STRAP['off'] 外の、傾いた帯"""
    xs, ys, zs = _grid(lo, vox, shape)
    (y0, y1), (z0, z1) = STRAP['y'], STRAP['z']
    zc = z0 + (z1 - z0) * np.clip((ys - y0) / (y1 - y0), 0, 1)          # (ny,)
    band = (STRAP['half'] - np.abs(zs[:, None, None] - zc[None, None, :])).astype(np.float32)
    band = np.broadcast_to(band, env.shape)
    back = np.broadcast_to((ys - (y0 - 0.01)).astype(np.float32)[None, None, :], env.shape)
    # 包みの面の外 4mm〜内側 2mm の殻だけ（房のすき間の上は橋のように渡る。中身の詰まったつばにしない）
    shell = smooth_min(env + STRAP['off'], -(env - STRAP['inner']), 0.0015)
    return smooth_min(smooth_min(band, shell, 0.002), back, 0.006)


def bangs_mask_front(cams: dict[str, V.Cam]) -> np.ndarray:
    """正面の絵の前髪（ゴーグルの下から額へ下がる髪の色の画素。ゴーグルの下の帯につながる所だけ）"""
    from skimage.morphology import disk
    im = _rgba('front')
    r, g, b, a = im[..., 0], im[..., 1], im[..., 2], im[..., 3]
    hair = (a > 128) & (r - b > 18) & (r < 175) & (g < 125) & (r > 45)
    c = cams['front']
    v_top, v_bot = int(c.v_of(BANGS['z'][0])), int(c.v_of(BANGS['z'][1]))
    u_a, u_b = int(c.u0 + BANGS['x'][0] * c.ppm), int(c.u0 + BANGS['x'][1] * c.ppm)
    m = np.zeros_like(hair)
    m[v_top:v_bot, u_a:u_b] = hair[v_top:v_bot, u_a:u_b]
    m = ndi.binary_opening(m, disk(4))            # 眉（細い）を落とす
    m = ndi.binary_closing(m, disk(2))
    lab, nl = ndi.label(m)
    v_root = int(c.v_of(BANGS['root_z']))
    keep = set(np.unique(lab[v_top:v_root + 3])) - {0}
    return np.isin(lab, list(keep))


def bangs_field(S: np.ndarray, cams: dict[str, V.Cam], lo, vox, shape) -> np.ndarray:
    """前髪：正面の絵の前髪の範囲を、額（頭の面 S）から前へ押し出した殻（中が正）。
    厚みは範囲の縁からの距離で決める（真ん中で最大 1.1cm、縁と先は 2mm：レンズ形の断面のくさび）。
    正面の絵（顔のアトラス）の前髪の V が、どの向きからも V の形の上に載る"""
    xs, ys, zs = _grid(lo, vox, shape)
    c = cams['front']
    m = bangs_mask_front(cams)
    d = np.where(m, ndi.distance_transform_edt(m) - 0.5, -(ndi.distance_transform_edt(~m) - 0.5)) / c.ppm
    d = ndi.gaussian_filter(d, 1.5).astype(np.float32)
    U, Vv = np.meshgrid(c.u0 + c.ppm * xs, c.v_of(zs))
    d2 = ndi.map_coordinates(d, [Vv - 0.5, U - 0.5], order=1, mode='constant', cval=-0.05).astype(np.float32)
    T = np.clip(0.002 + 0.9 * np.maximum(d2, 0), 0, 0.011) * ramp(zs, *BANGS['thick_ramp'], 0.6, 1.0)[:, None]
    shell = S + T[:, :, None].astype(np.float32)
    front = np.broadcast_to((-0.02 - ys).astype(np.float32)[None, None, :], S.shape)
    return smooth_min(smooth_min(np.broadcast_to(d2[:, :, None], S.shape), shell, 0.002), front, 0.006)


def ears_field(lo, vox, shape) -> np.ndarray:
    """耳：左右の、少し後ろへ開いた平たい楕円体 ＋ 付け根 ＋ 外の面の浅いくぼみ（中が正）"""
    xs, ys, zs = _grid(lo, vox, shape)
    Z, X, Y = np.meshgrid(zs, xs, ys, indexing='ij')
    out = np.full(Z.shape, -0.05, np.float32)
    for sx in (1.0, -1.0):
        cx, cy, cz = EAR['c']
        x0 = EAR.get('x0', 0.0)   # 耳の左右の中心（頭が体の中心から横へずれて描かれたキャラクター）
        yaw = math.radians(EAR['yaw_deg']) * sx
        dx, dy, dz = X - x0 - sx * cx, Y - cy, Z - cz
        # 耳の面は y-z 面を z 軸のまわりに回したもの（後ろの縁が外へ開く）
        lx = dx * math.cos(yaw) - dy * math.sin(yaw)
        ly = dx * math.sin(yaw) + dy * math.cos(yaw)
        rx, ry, rz = EAR['r']
        body = (1 - np.sqrt((lx / rx) ** 2 + (ly / ry) ** 2 + (dz / rz) ** 2)) * rx
        rc, rr = EAR['root_c'], EAR['root_r']
        root = (1 - np.sqrt(((X - x0 - sx * rc[0]) / rr[0]) ** 2 + ((Y - rc[1]) / rr[1]) ** 2
                            + ((Z - rc[2]) / rr[2]) ** 2)) * min(rr)
        ear = smooth_max(body.astype(np.float32), root.astype(np.float32), 0.006)
        dimple = (1 - np.sqrt(((lx - sx * 0.0075) / 0.006) ** 2 + ((ly + 0.002) / 0.012) ** 2
                              + ((dz + 0.002) / 0.019) ** 2)) * 0.006
        ear = smooth_min(ear, -dimple.astype(np.float32), 0.002)
        out = np.maximum(out, ear)
    return out


def build_head(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], lo: np.ndarray, vox: float, shape,
               z0: float = 1.10, params: dict | None = None, fit_sweeps: int = 6, log=log, x_half: float = 0.30
               ) -> tuple[int, np.ndarray, dict]:
    """頭の場（本文の 1〜4）。格子 (lo, vox, shape) の z0 より上の輪切りだけ：(始めの輪切り k0, 場, 記録)。
    計算は |x| < x_half の箱の中だけで行い、箱の外は外側（負）にする"""
    p = dict(PARAMS, **(params or {}))
    zs_all = lo[2] + (np.arange(shape[0]) + 0.5) * vox
    xs_all = lo[0] + (np.arange(shape[1]) + 0.5) * vox
    k0 = int(np.searchsorted(zs_all, z0))
    ix = np.nonzero(np.abs(xs_all) < x_half)[0]
    i0, i1 = int(ix[0]), int(ix[-1]) + 1
    lo_b = lo + np.array([i0 * vox, 0.0, k0 * vox])
    shp = (shape[0] - k0, i1 - i0, shape[2])
    info: dict = {'params': p, 'head_center': HEAD_C.tolist(), 'hairline': HAIRLINE}
    # 1. 頭（顔・あご）、鼻、首
    sk = skin_stack(cams, masks)
    S = stack_field(sk, lo_b, vox, shp, 0)
    nose = ellipsoid_field((float(sk.cx[0]),) + tuple(SKIN['nose'][0]), tuple(SKIN['nose'][1]), lo_b, vox, shp, 0)
    S = smooth_max(S, nose, 0.007)
    S = smooth_max(S, neck_field(lo_b, vox, shp, 0), 0.012)
    ears = ears_field(lo_b, vox, shp) if PARTS['ears'] else np.full(S.shape, -0.05, np.float32)
    if PARTS['ears']:
        S = smooth_max(S, ears, 0.006)
    log('頭（顔・あご・首・耳）')
    # 2. 髪の帽子（顔の前を切り取る）
    cs, ci = cap_stack(cams, masks, p, sk)
    info['cap'] = ci
    cut = face_cut(lo_b, vox, shp, 0)
    # 顔の範囲では、帽子は頭（顔）の面より外へ出ない（顔の面が見える。範囲の縁でなめらかに切り替える）
    allowed = smooth_max(S - 0.002, -cut, 0.012)
    Cf = smooth_min(stack_field(cs, lo_b, vox, shp, 0), allowed, 0.012)
    del allowed
    # 耳のまわりは帽子を 5mm 離す（耳が髪の中にうまらず見える）
    Cf = smooth_min(Cf, -(ears + 0.005), 0.004)
    log('髪の帽子', ci)
    base = smooth_max(S, Cf, p['union_k'])
    # ゴーグル：2 つの六角の枠 ＋ 奥のレンズ ＋ 橋（帽子の面に沿って回り込む。平らな板にしない）
    if PARTS['goggles']:
        gog, gz = goggles_field(Cf, lo_b, vox, shp)
        base = smooth_max(base, gog, 0.002)
    else:
        gz = np.full(base.shape, -0.05, np.float32)   # ゴーグルの無いキャラクター：房を切る範囲なし
    # 前髪：正面の絵の前髪の範囲を額から押し出した殻（房の楕円体の並びは使わない：根元がこぶの列になった）
    if PARTS['bangs']:
        bang = bangs_field(S, cams, lo_b, vox, shp)
        base = smooth_max(base, bang, 0.004)
    info['parts'] = PARTS
    info['goggles'] = None if not PARTS['goggles'] else {'frame': GOGGLE_FRAME, 'lens': GOGGLE_LENS, 'bridge': GOGGLE_BRIDGE,
                       'mirror_x': GOGGLE_MIRROR_X, 'thick': (FRAME_T, LENS_T, BRIDGE_T)}
    info['ears'] = EAR
    # 3. 房：最初の並び → 外形への当てはめ（房の道は、頭と帽子の和の面に沿う）
    rtab = RadialTable(base, lo_b, vox)
    v2 = Views2D(cams, masks)
    base2d = {n: v2.splat_field(n, base, lo_b, vox) for n in REAL}
    init = initial_locks()
    fit = Fitter(v2, base2d, rtab, p['lock_thick'], init, init)
    iou_base = {n: round(float((base2d[n] & v2.art[n]).sum() / (base2d[n] | v2.art[n]).sum()), 4) for n in REAL}
    info['iou_head_region'] = {'cap_and_head_only': iou_base,
                               'initial_locks': {k: round(v, 4) for k, v in fit.ious().items()}}
    if fit_sweeps:
        fit.run(fit_sweeps, log=log)
    # 顔の範囲・ゴーグルの枠にまだ入る房は、入らなくなるまで先を縮める（最後に切ると切り口の残る短い房になる）。
    # 縮めきれない房は落とす
    locks, dropped, shortened = [], 0, 0
    for L in fit.locks:
        for _ in range(12):
            s_ = lock_samples(L, rtab, p['lock_thick'])
            if face_zone_penalty(s_[0], s_[2]) == 0:
                break
            L2 = perturb(L, 'len', -5.0)
            L = Lock(L2.root, L2.tip, L2.lift * 0.85, L2.width, L2.name) if L2 is not L else None
            shortened += 1
            if L is None:
                break
        if L is None or face_zone_penalty(*[lock_samples(L, rtab, p['lock_thick'])[i] for i in (0, 2)]) > 0:
            dropped += 1
            continue
        locks.append(L)
    info['locks_shortened_steps'], info['locks_dropped'] = shortened, dropped
    fit2 = Fitter(v2, base2d, rtab, p['lock_thick'], locks, locks)
    fit = fit2
    info['iou_head_region']['fitted_locks'] = {k: round(v, 4) for k, v in fit.ious().items()}
    bangs = []
    info['locks'] = [dict(asdict(L), root=[round(v, 4) for v in L.root], tip=[round(v, 4) for v in L.tip])
                     for L in locks + bangs]
    info['n_locks'] = len(locks) + len(bangs)

    # 4. 房の場を足す（前髪は顔の前の切り取りの外）
    def add(lock_list):
        Lf = np.full(base.shape, -0.02, np.float32)
        for L in lock_list:
            res = lock_field(lock_samples(L, rtab, p['lock_thick']), lo_b, vox, base.shape)
            if res is None:
                continue
            (a, b, c), f = res
            sl = (slice(a, a + f.shape[0]), slice(b, b + f.shape[1]), slice(c, c + f.shape[2]))
            np.maximum(Lf[sl], f, out=Lf[sl])
        return Lf

    Lf = smooth_min(add(locks), -np.maximum(np.maximum(cut, gz), ears + 0.004) - 0.004, 0.004)
    phi_b = smooth_max(base, Lf, p['union_k'])
    # ベルト：髪の包み（房のすき間をうめてなめらかにした場）の面の上の帯
    env = ndi.gaussian_filter(phi_b, 5.0)
    if PARTS['strap']:
        phi_b = smooth_max(phi_b, smooth_min(strap_field(env, lo_b, vox, shp), -gz, 0.004), 0.002)
    del env
    phi = np.full((shp[0], shape[1], shape[2]), -0.05, np.float32)
    phi[:, i0:i1] = phi_b
    # 箱の縁で場が切れないように（念のため）
    phi[:, i0:i0 + 2] = np.minimum(phi[:, i0:i0 + 2], -vox)
    phi[:, i1 - 2:i1] = np.minimum(phi[:, i1 - 2:i1], -vox)
    info['iou_head_region']['final_field'] = {n: round(float((lambda c: (c & v2.art[n]).sum() / (c | v2.art[n]).sum())(
        v2.splat_field(n, phi_b, lo_b, vox))), 4) for n in REAL}
    log('房', info['n_locks'], '本', info['iou_head_region'])
    return k0, phi, info


def part_fields_at(P: np.ndarray, x_half: float = 0.26, z0: float = 1.12) -> dict[str, np.ndarray]:
    """面の点 P (n,3) での頭の部品の場（中が正、m）：'skin'（頭・鼻・首。耳は含めない）、'ear'、'strap'。
    塗りの段（flat.py）が「形の部品の色は形から」決めるのに使う。形の場は build_head と同じ作り方で、
    ベルトの基準の髪の包みは hull.npz の場（形の段の出力）をぼかしたもの"""
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    lo, vox, shape = d['lo'], float(d['vox']), tuple(int(s) for s in d['shape'])
    zs_all = lo[2] + (np.arange(shape[0]) + 0.5) * vox
    xs_all = lo[0] + (np.arange(shape[1]) + 0.5) * vox
    k0 = int(np.searchsorted(zs_all, z0))
    ix = np.nonzero(np.abs(xs_all) < x_half)[0]
    i0, i1 = int(ix[0]), int(ix[-1]) + 1
    lo_b = lo + np.array([i0 * vox, 0.0, k0 * vox])
    shp = (shape[0] - k0, i1 - i0, shape[2])
    cams = V.load_calib()
    masks = {n: V.load_mask(n) for n in V.VIEWS}
    sk = skin_stack(cams, masks)
    S = stack_field(sk, lo_b, vox, shp, 0)
    nose = ellipsoid_field((float(sk.cx[0]),) + tuple(SKIN['nose'][0]), tuple(SKIN['nose'][1]), lo_b, vox, shp, 0)
    S = smooth_max(S, nose, 0.007)
    S = smooth_max(S, neck_field(lo_b, vox, shp, 0), 0.012)
    out = {'skin': S}
    ears = ears_field(lo_b, vox, shp) if PARTS['ears'] else np.full(S.shape, -0.05, np.float32)
    out['ear'] = ears
    # 髪（帽子・前髪・房）：build_head と同じ作り方。房は形の段が当てはめた値（recon_report.json）をそのまま使う
    p = dict(PARAMS)
    Se = smooth_max(S, ears, 0.006) if PARTS['ears'] else S
    cs, _ = cap_stack(cams, masks, p, sk)
    cut = face_cut(lo_b, vox, shp, 0)
    Cf = smooth_min(stack_field(cs, lo_b, vox, shp, 0), smooth_max(Se - 0.002, -cut, 0.012), 0.012)
    Cf = smooth_min(Cf, -(ears + 0.005), 0.004)
    base = smooth_max(Se, Cf, p['union_k'])
    gz = np.full(S.shape, -0.05, np.float32)
    if PARTS['goggles']:
        gog, gz = goggles_field(Cf, lo_b, vox, shp)
        base = smooth_max(base, gog, 0.002)
    hair = Cf
    if PARTS['bangs']:
        bang = bangs_field(Se, cams, lo_b, vox, shp)
        base = smooth_max(base, bang, 0.004)
        hair = np.maximum(hair, bang)
    try:
        with open(os.path.join(V.WORK, 'recon_report.json')) as fp:
            locks = [Lock(tuple(L['root']), tuple(L['tip']), L['lift'], L['width'], L.get('name', ''))
                     for L in json.load(fp)['hull']['head']['locks']]
    except (OSError, KeyError):
        locks = []
    if locks:
        rtab = RadialTable(base, lo_b, vox)
        Lf = np.full(S.shape, -0.02, np.float32)
        for L in locks:
            r_ = lock_field(lock_samples(L, rtab, p['lock_thick']), lo_b, vox, S.shape)
            if r_ is None:
                continue
            (a, b, c), f = r_
            sl = (slice(a, a + f.shape[0]), slice(b, b + f.shape[1]), slice(c, c + f.shape[2]))
            np.maximum(Lf[sl], f, out=Lf[sl])
        Lf = smooth_min(Lf, -np.maximum(np.maximum(cut, gz), ears + 0.004) - 0.004, 0.004)
        hair = np.maximum(hair, Lf)
    out['hair'] = hair
    if PARTS['strap']:
        env = ndi.gaussian_filter(d['phi'][k0:, i0:i1].astype(np.float32), 5.0)
        out['strap'] = strap_field(env, lo_b, vox, shp)
    idx = ((P[:, [2, 0, 1]] - lo_b[[2, 0, 1]]) / vox - 0.5).T
    return {k: ndi.map_coordinates(f, idx, order=1, mode='constant', cval=-0.05) for k, f in out.items()}


def neck_field(lo, vox, shape, k0) -> np.ndarray:
    """首：縦の楕円柱（下は体の中、上は頭の中）"""
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(k0, nz) + 0.5) * vox
    (rx, ry), cy, (z0, z1) = NECK['r'], NECK['cy'], NECK['z']
    e = np.sqrt(((xs[:, None] - NECK['cx']) / rx) ** 2 + ((ys[None, :] - cy) / ry) ** 2)
    f = ((1 - e) * rx).astype(np.float32)
    top = (z1 - zs)[:, None, None]
    bot = (zs - z0)[:, None, None]
    return smooth_min(smooth_min(np.broadcast_to(f[None], (len(zs), nx, ny)), np.broadcast_to(top, (len(zs), nx, ny)),
                                 0.01), np.broadcast_to(bot, (len(zs), nx, ny)), 0.01)


# ---------------------------------------------------------------- 実験用

def overlay(v2: Views2D, phi: np.ndarray, lo_s, vox, path: str) -> dict:
    """外形の重なりの画像（緑 = 絵だけ、赤 = 形だけ、灰 = 両方）と IoU"""
    from PIL import Image
    tiles, out = [], {}
    for n in REAL:
        c = v2.splat_field(n, phi, lo_s, vox)
        a = v2.art[n]
        img = np.zeros(a.shape + (3,), np.uint8)
        img[a & c] = (150, 150, 150)
        img[a & ~c] = (40, 200, 60)
        img[c & ~a] = (220, 50, 50)
        tiles.append(img)
        out[n] = round(float((a & c).sum() / (a | c).sum()), 4)
    h = max(t.shape[0] for t in tiles)
    tiles = [np.pad(t, ((0, h - t.shape[0]), (0, 4), (0, 0))) for t in tiles]
    Image.fromarray(np.concatenate(tiles, 1)).resize((sum(t.shape[1] for t in tiles) * 2, h * 2),
                                                     Image.NEAREST).save(path)
    return out


def main() -> None:
    from recon import fair, surfcheck
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='test')
    ap.add_argument('--sweeps', type=int, default=6)
    ap.add_argument('--render', type=int, default=1)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    lo, vox, shape = d['lo'], float(d['vox']), tuple(int(s) for s in d['shape'])
    cams = V.load_calib()
    masks = {n: V.load_mask(n) for n in V.VIEWS}
    k0, phi, info = build_head(cams, masks, lo, vox, shape, fit_sweeps=args.sweeps)
    lo_s = lo + np.array([0, 0, k0 * vox])
    v2 = Views2D(cams, masks)
    info['overlay_iou'] = overlay(v2, phi, lo_s, vox, os.path.join(OUT, f'{args.name}_overlay.png'))
    log('外形の IoU（あごより上）', info['overlay_iou'])
    # 頭のまわりだけ面にする
    xs = lo[0] + (np.arange(shape[1]) + 0.5) * vox
    sel = np.nonzero(np.abs(xs) < 0.30)[0]
    sub = phi[:, sel[0]:sel[-1] + 1].copy()
    sub[:int(0.08 / vox)] = np.minimum(sub[:int(0.08 / vox)], -0.01)   # 下は切る
    P, faces = fair.mesh_of(sub, lo_s + np.array([sel[0] * vox, 0, 0]), vox)
    np.savez_compressed(os.path.join(OUT, f'{args.name}.npz'), verts=P.astype(np.float32), tris=faces)
    with open(os.path.join(OUT, f'{args.name}.json'), 'w') as fp:
        json.dump(info, fp, indent=1, ensure_ascii=False, default=float)
    log('面', len(P), len(faces))
    if args.render:
        for f in surfcheck.run(P, faces, os.path.join(OUT, args.name), which=('head', 'face'), samples=12):
            log(f)


if __name__ == '__main__':
    main()
