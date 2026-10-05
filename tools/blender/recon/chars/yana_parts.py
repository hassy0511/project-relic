"""ヤーナ（yana）の服の部品と塗りの決まり（costume.py が読み込む。書式は chars/burton_parts.py と同じ）。

部品の表：docs/art_orders/W2_人物の部品表.md の 2 章。寸法は calib.json のカメラで絵に 1cm の格子を重ねて読んだ
（再構築の座標：身長 1.55m。本来の 1.72m へは骨付けの段で 1.110 倍）。本人の左 = +X、正面 = −Y。
  右の義手（機械：肩の板・肩の下の関節の輪と琥珀・上腕の板・肘の関節と琥珀・前腕の板・手首の輪。板は 8 角の面の殻、
  関節は暗い輪。手は hand.build_open の義手の形＝白い節と黒い関節）、左のまくり袖の口・指抜き手袋のカフ、
  エプロン（前：胸当て・腰から下の垂れ布、後ろ：背当て・垂れ布。背面の絵のとおり後ろにも布がある）、肩ひも ×2・
  肩ひもの金具 ×2・首の後ろの帯、ベルト・バックル・後ろの板、左腰のタオル・小瓶（革の受け）・腰の袋 ×2、
  ズボンの脇のポケット ×2・右の太ももの当て布・裾の帯 ×2、靴 ×2（底・かかと・爪先・胴・ひも）、ハンマー（腰の後ろの輪に下げる）。
決まりの塗り（body_rules）：胴・腕の上は生成りのシャツ、左腕は袖口より先が肌、右腕は義手の部品の下で暗い色、
ベルトより下はズボン、頭と首は形の場（バートンと同じ）。
寸法の一部（腕の軸・胴の前後の面）は、形の段のメッシュ（build/yana/yana_mesh.npz）を高さで切って測る（絵の関節の表
J は腕の中心から外れていた。肘で前後に 5cm）。
"""
from __future__ import annotations

import math
import os

import numpy as np

# 色は絵（yana_3d_front・yana_shoes・yana_grip・yana_hip_left）の平らに照らされた所の中央値で測った（2026-10-05）。
# 義手の板・タオル・シャツは生成り、関節・ベルト・靴底は石墨、琥珀は塗りの 1 色（発光しない。spec_yana_3d_add.md）
PALETTE = {
    'brick': '#B0623F',      # エプロン
    'ivory': '#F3E2C8',      # シャツ・タオル・義手の板
    'graphite': '#46423D',   # 義手の関節・ベルト・靴底
    'brass': '#8B6F4E',      # バックル・ズボンの裾の帯・靴の爪先
    'umber': '#5E4537',      # 靴の胴・肩ひも・手袋・腰の袋
    'amber': '#FFBC52',      # 義手の円（塗りの 1 色）
    'skin': '#E7B58D',
    'olive': '#746543',      # ズボン
    'hair': '#6E4838',       # 髪
    'patch': '#8E714A',      # 右の太ももの当て布
    'pocket': '#655838',     # ズボンの脇のポケット（ズボンより少し暗い）
    'wood': '#8A6345',       # ハンマーの柄
    'bottle': '#4A3428',     # 小瓶
    'iron': '#55524D',       # ハンマーの頭
}
NAMES = list(PALETTE)
CELLS = 16

# A ポーズの関節（chars/yana.json の joints.ART_XZ と骨付けの段の表。y は形の段のメッシュ）
J = {
    'upper_arm': (0.177, 0.0462, 1.13), 'forearm': (0.287, 0.0532, 0.935), 'hand': (0.338, 0.0482, 0.77),
    'hand_end': (0.395, 0.0471, 0.63), 'thigh': (0.10, -0.064, 0.66), 'shin': (0.12, 0.0234, 0.36),
    'foot': (0.125, 0.0123, 0.10),
}
# 体の重みを写す部品（胸から腰へ曲がる胸当て・背当て、肩の上の板・ひも）
FOLLOW_BODY = ('bib', 'bib_back', 'strap.L', 'strap.R', 'neck_band', 'pros_shoulder')
FOLLOW_TORSO_ONLY = ('bib', 'bib_back', 'strap.L', 'strap.R', 'neck_band')
BOX_RULES: list = []

BELT_Z = ((0.885, 0.875), (0.937, 0.930))     # ベルトの下・上（前, 後ろ）
BIB = dict(top=1.112, x_top=(-0.122, 0.114), x_bot=(-0.128, 0.122))
BIB_BACK = dict(top=1.104, x_top=(-0.118, 0.104), x_bot=(-0.122, 0.112))
SKIRT_HEM = 0.512
SLEEVE_T = (0.098, 0.150)       # 左のまくり袖の口：上腕の軸に沿った肩からの長さ
NECK_TOP = 1.235                # シャツの首の上の端（あごの下）
HAIRLINE_PAINT = ([0.0, 0.06, 0.075, 0.085, 0.095, 0.11], [1.44, 1.425, 1.40, 1.375, 1.335, 1.318])
HAIR_LOW = ([50, 60, 72, 95, 110, 135, 180], [1.40, 1.36, 1.30, 1.31, 1.305, 1.285, 1.265])
BOOT_CUT = 0.222        # この高さより下の脚の体は消して、靴の部品に置き換える（裾の帯の中で切る）
BOOT_RAMP = (0.07, 0.15)
BOOT_CUT_X = (0.03, 0.40)
RIGHT_HAND_PART = True

# ---------------------------------------------------------------- 体の前の出っ張りを押し戻す（骨付けの段の前）

# 形の段の体は、右真横の絵で体の前に下がる左手（y −0.15〜−0.25）を外形に含み、腰の前（z 0.62〜0.85、|x| < 0.16）が
# 28cm も前へ板のように出ていた（前の結果の文書の「エプロンの下半分が平たいひらひら」）。エプロンの下の脚の前の面を、
# 右真横の絵で測ったエプロンの前の縁の 1〜2cm 奥まで押し戻す（ai_character.add_costume が部品を作る前に体へ、
# 部品の寸法の測り _mesh() にも同じものを掛ける）
CLAMP_Z = ([0.575, 0.62, 0.75, 0.88, 0.955], [-0.150, -0.126, -0.116, -0.110, -0.130])


def BODY_CLAMP(co: np.ndarray) -> np.ndarray:
    co = co.copy()
    z = co[:, 2]
    m = (z > CLAMP_Z[0][0]) & (z < CLAMP_Z[0][-1]) & (np.abs(co[:, 0]) < 0.20) & (co[:, 1] < 0.0)
    ymin = np.interp(z[m], *CLAMP_Z)
    co[m, 1] = np.maximum(co[m, 1], ymin)
    return co


# ---------------------------------------------------------------- 形の段のメッシュの測り

_MESH = None


def _mesh() -> np.ndarray:
    global _MESH
    if _MESH is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'build', 'yana',
                         'yana_mesh.npz')
        _MESH = BODY_CLAMP(np.load(p)['verts'])
    return _MESH


def _band(z, dz=0.007):
    v = _mesh()
    return v[np.abs(v[:, 2] - z) < dz]


def body_front_y(z: float, x0: float, x1: float) -> float:
    p = _band(z)
    p = p[(p[:, 0] > x0) & (p[:, 0] < x1)]
    return float(p[:, 1].min())


def body_back_y(z: float, x0: float, x1: float) -> float:
    p = _band(z)
    p = p[(p[:, 0] > x0) & (p[:, 0] < x1)]
    return float(p[:, 1].max())


def body_r(ang_deg: float, z0: float, z1: float, win: float = 10.0, axis=(0.0, 0.0)) -> float:
    """縦の軸のまわりの角度（0 = 正面、+ = 本人の左）の向きの体の半径の最大（z0〜z1、角度の窓 ±win）"""
    v = _mesh()
    p = v[(v[:, 2] > z0) & (v[:, 2] < z1) & (np.abs(v[:, 0]) < 0.2)]
    x, y = p[:, 0] - axis[0], p[:, 1] - axis[1]
    a = np.degrees(np.arctan2(x, -y))
    m = np.abs((a - ang_deg + 180) % 360 - 180) < win
    return float(np.hypot(x[m], y[m]).max())


def arm_center(z: float, side: float) -> np.ndarray:
    p = _band(z, 0.006)
    p = p[(side * p[:, 0] > 0.19) & (side * p[:, 0] < 0.45)]
    return np.array([(p[:, 0].min() + p[:, 0].max()) / 2, (p[:, 1].min() + p[:, 1].max()) / 2, z])


def rect_sec(c, u, half_u, half_v, ch=0.002):
    """中心 c (x, y)、横の向き u（単位、xy）の、角を ch 切った長方形（反時計回り）"""
    u = np.asarray(u, float) / np.linalg.norm(u)
    n = np.array([-u[1], u[0]])
    pts = []
    for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        for k in (0, 1):
            # 角ごとに 2 点（切った角）
            if (su * sv > 0) == (k == 0):
                pu, pv = su * half_u, sv * (half_v - ch)
            else:
                pu, pv = su * (half_u - ch), sv * half_v
            pts.append(tuple(np.asarray(c) + u * pu + n * pv))
    return pts


def oct_sec(c, r, n=8, rot=math.pi / 8):
    return [(c[0] + r * math.cos(rot + 2 * math.pi * k / n), c[1] + r * math.sin(rot + 2 * math.pi * k / n))
            for k in range(n)]


# ---------------------------------------------------------------- 部品

def prosthetic() -> list[dict]:
    """右の義手（機械の作り）：腕の軸（メッシュの断面の中心）のまわりの 8 角の殻の板と、暗い関節の輪。
    絵 yana_3d_front・yana_arm・yana_grip：肩の大きな白い板 → 暗い輪（外の前に琥珀の円）→ 上腕の板 → 肘の暗い関節
    （外に琥珀の円）→ 前腕の板（手首へ細る）→ 手首の暗い輪。板と輪の間の体は暗い色（形の継ぎ目）"""
    P = []
    side = -1.0
    S = np.array([-0.205, 0.0, 1.13])
    E = arm_center(0.935, side)
    W = arm_center(0.79, side)
    W[2] = 0.775
    Lu = float(np.linalg.norm(E - S))
    Lf = float(np.linalg.norm(W - E))
    outv = np.array([-1.0, -0.15, 0.0])
    fu = frame(S, E, outv)
    fu['RN'] = 0.05
    ff = frame(E, W, outv)
    ff['RN'] = 0.045
    # 肩の板（球の座標、外上の向きが極）：肩の上から上腕の外・前・後ろを 1 枚で覆う
    d = unit(E - S)
    fsp = {'kind': 'sphere', 'a': S + 0.035 * d + np.array([0.012, 0.0, 0.0]),
           'e0': unit(np.array([-0.80, -0.05, 0.60])), 'e2': np.array([0.0, 1.0, 0.0]), 'RN': 0.06}
    fsp['e1'] = np.cross(fsp['e2'], fsp['e0'])
    fsp['d'] = fsp['e2']
    P.append(dict(name='pros_shoulder', bone='upper_arm.R', color='ivory', frame=fsp,
                  outline=octagon(-0.068, 0.062, -0.066, 0.066, 0.026), off=0.010, thick=0.010, bevel=0.004,
                  under='graphite', rmax=0.13, rmin=0.03, h=0.006))
    # 1 周目は暗い輪が太く高く、白い板と同じ高さで縞の筒に見えた → 暗い輪は細く、板より奥（板の縁の下へ少し入る）
    rings = [  # (名前, 色, 軸, t0, t1, 浮き, 厚み, 面の数)
        ('pros_ring_u', 'graphite', fu, 0.034, 0.066, 0.000, 0.007, 16),
        ('pros_upper', 'ivory', fu, 0.064, Lu - 0.020, 0.004, 0.012, 8),
        ('pros_elbow', 'graphite', ff, -0.024, 0.024, 0.000, 0.008, 16),
        ('pros_fore', 'ivory', ff, 0.022, Lf - 0.026, 0.004, 0.012, 8),
        ('pros_wrist', 'graphite', ff, Lf - 0.028, Lf + 0.008, 0.000, 0.007, 16),
    ]
    for nm, col, fr, t0, t1, off, th, n in rings:
        P.append(dict(name=nm, bone='upper_arm.R' if fr is fu else 'forearm.R', color=col, frame=fr, ring=True,
                      t0=t0, t1=t1, off=off, thick=th, bevel=0.003, under='graphite', rmax=0.10, n_ring=n,
                      sink=0.006))
    # 琥珀の円（関節の外の前）：肩の下の輪・肘
    for nm, fr, tc, rr, ang in (('pros_amber_u', fu, 0.050, 0.012, -25.0), ('pros_amber_e', ff, 0.0, 0.013, -10.0)):
        sc = math.radians(ang) * fr['RN']
        P.append(dict(name=nm, bone='upper_arm.R' if fr is fu else 'forearm.R', color='amber', frame=fr,
                      outline=octagon(sc - rr, sc + rr, tc - rr, tc + rr, rr * 0.3), off=0.008, thick=0.004,
                      bevel=0.002, rmax=0.10, h=0.004))
    return P


def apron() -> list[dict]:
    """エプロン（前・後ろ）。胸当て・背当ては胴の面の殻、腰から下の垂れ布は高さの断面を積んだ板
    （上はベルトの下で体に沿い、下へ行くほど体から離す。脚の前を通る：胴の前の面は太ももを含む |x| < 0.15 の最小）"""
    P = []
    front = np.array([0.0, -1.0, 0.0])
    back = np.array([0.0, 1.0, 0.0])
    # RN は胴の半径（s ≈ x）。1 周目の 0.13 では s が x より小さく、背当てが肩ひもの外まで横へ回り込んだ
    fw = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), front)
    fw['RN'] = 0.155
    fb = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), back)
    fb['RN'] = 0.155
    b = BIB
    # 胸当て（前、s ≈ x）
    P.append(dict(name='bib', bone='chest', color='brick', frame=fw,
                  outline=[(b['x_bot'][0], BELT_Z[0][0] - 0.004), (b['x_bot'][1], BELT_Z[0][0] - 0.004),
                           (b['x_top'][1], b['top']), (b['x_top'][0], b['top'])],
                  off=0.004, thick=0.006, bevel=0.002, under='brick', rmax=0.25, h=0.008, env_rings=2,
                  smooth_iters=6))
    # 背当て（後ろ。軸の向きが逆なので s ≈ −x）
    bb = BIB_BACK
    P.append(dict(name='bib_back', bone='chest', color='brick', frame=fb,
                  outline=[(-bb['x_bot'][1], BELT_Z[0][1] - 0.004), (-bb['x_bot'][0], BELT_Z[0][1] - 0.004),
                           (-bb['x_top'][0], bb['top']), (-bb['x_top'][1], bb['top'])],
                  off=0.004, thick=0.006, bevel=0.002, under='brick', rmax=0.25, h=0.008, env_rings=2,
                  smooth_iters=6))
    # 垂れ布（前・後ろ）
    for nm, sg, z_top, xr_top, xr_bot, gap_bot in (
            ('skirt', -1.0, BELT_Z[0][0] + 0.012, (-0.108, 0.098), (-0.146, 0.122), 0.022),
            ('skirt_back', 1.0, BELT_Z[0][1] + 0.012, (-0.124, 0.100), (-0.150, 0.122), 0.020)):
        zs = np.linspace(z_top, SKIRT_HEM, 9)
        secs = []
        for i, z in enumerate(zs):
            f = (z_top - z) / (z_top - SKIRT_HEM)
            x0 = xr_top[0] + (xr_bot[0] - xr_top[0]) * f
            x1 = xr_top[1] + (xr_bot[1] - xr_top[1]) * f
            # 体の面（この高さ以上、腰の上まで。下の脚の間で前が引っ込んでも板はまっすぐ）
            zz = np.linspace(z, z_top, 6)
            if sg < 0:
                yb = min(body_front_y(q, x0, x1) for q in zz)
            else:
                yb = max(body_back_y(q, x0, x1) for q in zz)
            gap = 0.003 + (gap_bot - 0.003) * f ** 1.3
            y_in = yb + sg * gap
            y_out = y_in + sg * 0.006
            c = ((x0 + x1) / 2, (y_in + y_out) / 2)
            secs.append((float(z), rect_sec(c, (1.0, 0.0), (x1 - x0) / 2, 0.003, 0.0015)))
        secs = secs[::-1]
        P.append(dict(name=nm, bone='hips', color='brick', loft=secs))
    # 肩ひも ×2（左右の軸のまわり：胸当ての上の角 → 肩の上 → 背当ての上の角）。t = |x|
    up = np.array([0.0, 0.0, 1.0])
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        ax_y, ax_z = 0.01, 1.07
        fst = frame((0.0, ax_y, ax_z), (side, ax_y, ax_z), up)
        fst['RN'] = 0.1
        (tf0, tf1), (tb0, tb1) = ((0.064, 0.110), (0.052, 0.104)) if side > 0 else ((0.070, 0.116), (0.062, 0.114))
        xs = sorted((side * tf0, side * tf1))
        # 前の端は胸当ての上の縁の 1.2cm 下、後ろの端は背当ての上の縁の 1.2cm 下（体の面の y から角度を出す）
        zf, zb = BIB['top'] - 0.012, BIB_BACK['top'] - 0.012
        af = math.atan2(ax_y - body_front_y(zf, *xs), zf - ax_z)
        ab = math.atan2(body_back_y(zb, *xs) - ax_y, zb - ax_z)
        sf, sb = af * 0.1, -ab * 0.1           # 左：+ が前（e1 = −y）。右は軸が −x なので符号が逆
        if side < 0:
            sf, sb = -sf, -sb
        out = [(sb, tb0), (sf, tf0), (sf, tf1), (sb, tb1)]
        if side < 0:
            out = out[::-1]
        # 2 周目：肩の上の体の凸凹でひもの縁が波打った → 近所の最大 1 輪、よくならす
        P.append(dict(name='strap' + sx, bone='chest', color='umber', frame=fst, outline=out, off=0.008,
                      thick=0.005, bevel=0.0015, under='umber', rmax=0.25, env_rings=1, h=0.0045, smooth_iters=40,
                      raw_tol=0.0))
        # 金具（胸当ての上、ひもの上の輪）
        xa, xb = (0.062, 0.110) if side > 0 else (-0.116, -0.068)
        P.append(dict(name='strap_clip' + sx, bone='chest', color='graphite', frame=fw,
                      outline=octagon(xa - 0.003, xb + 0.003, 1.122, 1.164, 0.004), off=0.010, thick=0.006,
                      bevel=0.002, rmax=0.25, h=0.004))
    # 首の後ろの帯（肩ひもを結ぶ。背面の絵 z 1.19〜1.22）
    P.append(dict(name='neck_band', bone='chest', color='umber', frame=fb,
                  outline=[(-0.105, 1.186), (0.118, 1.186), (0.118, 1.216), (-0.105, 1.216)], off=0.005,
                  thick=0.005, bevel=0.0015, under='umber', rmax=0.25, h=0.005, smooth_iters=10))
    return P


def belt_items() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    back = np.array([0.0, 1.0, 0.0])
    fw = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), front)
    fw['RN'] = 0.15
    fb = frame((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), back)
    fb['RN'] = 0.15
    # ベルト（エプロンの上。垂れ布の上の端・胸当ての下の端を覆う）
    P.append(dict(name='belt', bone='hips', color='graphite', frame=fw, ring=True,
                  t0=BELT_Z[0], t1=BELT_Z[1], off=0.012, thick=0.007, bevel=0.002, under='brick',
                  rmax=0.25, n_ring=120, sink=0.014))
    P.append(dict(name='buckle', bone='hips', color='brass', frame=fw,
                  outline=octagon(-0.046, 0.030, 0.889, 0.940, 0.004), off=0.020, thick=0.006, bevel=0.002,
                  rmax=0.25, h=0.005))
    P.append(dict(name='belt_plate_back', bone='hips', color='brass', frame=fb,
                  outline=octagon(-0.030, 0.050, 0.878, 0.928, 0.004), off=0.020, thick=0.005, bevel=0.002,
                  rmax=0.25, h=0.005))
    # 腰の袋 ×2（箱。絵の正面・真横・背面：両脇のベルトの下）
    for name, ang, zc, size in (('pouch.R', -97.0, 0.812, (0.064, 0.036, 0.130)),
                                ('pouch.L', 104.0, 0.832, (0.058, 0.034, 0.105))):
        P.append(dict(name=name, bone='hips', color='umber', box=True, frame=fw, ang=ang, zc=zc, size=size,
                      rmax=0.3))
    # タオル（左腰、前寄りの横。ベルトに上の端を挟んで垂れる 2 枚：外の短い布と、下へ長い布）
    for nm, ang, z_top, z_bot, hw, lift in (('towel', 58.0, 0.905, 0.640, 0.046, 0.026),
                                           ('towel_lo', 64.0, 0.880, 0.592, 0.036, 0.020)):
        a = math.radians(ang)
        rad = np.array([math.sin(a), -math.cos(a)])
        tan = np.array([math.cos(a), math.sin(a)])
        secs = []
        for z in np.linspace(z_bot, z_top, 7):
            r = body_r(ang, z - 0.01, min(z + 0.06, z_top + 0.01), 14.0)
            f = (z_top - z) / (z_top - z_bot)
            rc = r + lift * (0.4 + 0.6 * f) + 0.004
            secs.append((float(z), rect_sec(rad * rc, tan, hw * (1 + 0.08 * f), 0.004, 0.0015)))
        P.append(dict(name=nm, bone='hips', color='ivory', loft=secs))
    # 小瓶（左腰、ベルトの革の受けに縦に）：受け（暗い茶の筒）＋瓶（暗い茶）＋口・栓
    a = math.radians(82.0)
    rad = np.array([math.sin(a), -math.cos(a)])
    rb = body_r(82.0, 0.84, 0.95, 10.0)
    c = rad * (rb + 0.030)
    secs_h = [(0.838, oct_sec(c, 0.018)), (0.842, oct_sec(c, 0.0205)), (0.905, oct_sec(c, 0.0205)),
              (0.909, oct_sec(c, 0.018))]
    secs_b = [(0.900, oct_sec(c, 0.0165)), (0.928, oct_sec(c, 0.0165)), (0.934, oct_sec(c, 0.010)),
              (0.946, oct_sec(c, 0.009))]
    secs_c = [(0.944, oct_sec(c, 0.0105)), (0.958, oct_sec(c, 0.0105)), (0.961, oct_sec(c, 0.008))]
    P.append(dict(name='bottle_holder', bone='hips', color='umber', loft=secs_h))
    P.append(dict(name='bottle', bone='hips', color='bottle', loft=secs_b))
    P.append(dict(name='bottle_cork', bone='hips', color='wood', loft=secs_c))
    P += hammer()
    return P


def hammer() -> list[dict]:
    """ハンマー（腰の後ろの右、ベルトの革の輪に頭を上にして下げる。絵 hammer_side/front・yana_grip：頭 12×7×6cm、
    首の金具（頭の上下）、8 角の柄 44cm・径 3.5cm、握りの巻き革 11cm、石突き）。再構築の座標では 0.901 倍。
    会話の待機では両手とも開いた手（全身の 7 枚の絵のとおり）。握る姿勢の絵 yana_grip は、仕事の動作を作るときに使う"""
    P = []
    ang = -148.0
    a = math.radians(ang)
    rad = np.array([math.sin(a), -math.cos(a)])
    tan = np.array([math.cos(a), math.sin(a)])
    k = 0.901
    z_head0 = 0.946
    hr = 0.0158                                       # 柄の半径（8 角の外接）
    rb = max(body_r(ang, z, z + 0.03, 12.0) for z in np.arange(0.50, 0.93, 0.03))
    c = rad * (rb + hr + 0.012)
    hw, hd, hh = 0.120 * k / 2, 0.070 * k / 2, 0.060 * k
    zt = z_head0 + hh
    head = [(z_head0, rect_sec(c, tan, hw - 0.004, hd - 0.004, 0.006)),
            (z_head0 + 0.005, rect_sec(c, tan, hw, hd, 0.008)),
            (zt - 0.005, rect_sec(c, tan, hw, hd, 0.008)),
            (zt, rect_sec(c, tan, hw - 0.004, hd - 0.004, 0.006))]
    P.append(dict(name='hammer_head', bone='hips', color='iron', loft=head))
    for nm, z0, z1 in (('hammer_collar_lo', z_head0 - 0.022, z_head0 + 0.002), ('hammer_collar_hi', zt - 0.002, zt + 0.014)):
        P.append(dict(name=nm, bone='hips', color='brass',
                      loft=[(z0, rect_sec(c, tan, 0.019, 0.017, 0.004)), (z1, rect_sec(c, tan, 0.019, 0.017, 0.004))]))
    L = 0.44 * k
    z_bot = z_head0 + hh - L
    P.append(dict(name='hammer_handle', bone='hips', color='wood',
                  loft=[(z_bot + 0.030, oct_sec(c, hr)), (z_head0 - 0.020, oct_sec(c, hr))]))
    P.append(dict(name='hammer_grip', bone='hips', color='umber',
                  loft=[(z_bot + 0.034, oct_sec(c, hr + 0.0022)), (z_bot + 0.034 + 0.11 * k, oct_sec(c, hr + 0.0022))]))
    P.append(dict(name='hammer_pommel', bone='hips', color='wood',
                  loft=[(z_bot, oct_sec(c, hr + 0.002)), (z_bot + 0.004, oct_sec(c, hr + 0.005)),
                        (z_bot + 0.030, oct_sec(c, hr + 0.005)), (z_bot + 0.034, oct_sec(c, hr + 0.002))]))
    # ベルトの革の輪（柄を通す）：柄のまわりの角の筒
    P.append(dict(name='hammer_loop', bone='hips', color='umber',
                  loft=[(0.872, rect_sec(c - rad * 0.004, tan, 0.024, 0.024, 0.006)),
                        (0.900, rect_sec(c - rad * 0.004, tan, 0.024, 0.024, 0.006))]))
    return P


def legs() -> list[dict]:
    P = []
    front = np.array([0.0, -1.0, 0.0])
    for side, sx in ((1.0, '.L'), (-1.0, '.R')):
        # ズボンの裾の帯（靴の上の折り返し、絵 z 0.205〜0.25）：すねの縦の軸
        cx = side * 0.172
        fb = frame((cx, 0.02, 0.0), (cx, 0.02, 1.0), front)
        fb['RN'] = 0.07
        P.append(dict(name='trouser_cuff' + sx, bone='shin' + sx, color='brass', frame=fb, ring=True,
                      t0=0.203, t1=0.252, off=0.004, thick=0.010, bevel=0.003, under='olive', rmax=0.16,
                      n_ring=48, sink=0.02))
        # 脇の大きなポケット（太ももの外、z 0.48〜0.63）
        ft = frame((side * 0.16, 0.0, 0.0), (side * 0.16, 0.0, 1.0), front)
        ft['RN'] = 0.10
        sc = side * math.radians(88) * 0.10
        P.append(dict(name='side_pocket' + sx, bone='thigh' + sx, color='pocket', frame=ft,
                      outline=octagon(sc - 0.050, sc + 0.050, 0.485, 0.625, 0.006), off=0.003, thick=0.007,
                      bevel=0.002, under='olive', rmax=0.25, h=0.006))
        P += boot_pieces(side, sx)
    # 右の太ももの当て布（前の右、z 0.33〜0.46、x −0.23〜−0.11、少し傾く）
    fr = frame((-0.165, 0.0, 0.0), (-0.165, 0.0, 1.0), front)
    fr['RN'] = 0.10
    P.append(dict(name='thigh_patch.R', bone='thigh.R', color='patch', frame=fr,
                  outline=[(-0.060, 0.333), (0.052, 0.340), (0.058, 0.455), (-0.054, 0.462)], off=0.003,
                  thick=0.005, bevel=0.0015, under='olive', rmax=0.25, h=0.006))
    return P


def pieces() -> list[dict]:
    P = []
    P += prosthetic()
    # 左のまくり袖の口（生成り）・指抜き手袋のカフ（暗い茶）
    e, w = jp('forearm', 1.0), jp('hand', 1.0)
    S = np.array([0.205, 0.012, 1.13])
    E = arm_center(0.935, 1.0)
    Wl = arm_center(0.79, 1.0)
    Wl[2] = 0.775
    fs = frame(S, E, np.array([0.0, -1.0, 0.0]))
    fs['RN'] = 0.05
    P.append(dict(name='sleeve_cuff.L', bone='upper_arm.L', color='ivory', frame=fs, ring=True,
                  t0=SLEEVE_T[0], t1=SLEEVE_T[1], off=0.004, thick=0.010, bevel=0.004, under='ivory', rmax=0.10,
                  n_ring=48, sink=0.01))
    fg = frame(E, Wl, np.array([0.0, -1.0, 0.0]))
    fg['RN'] = 0.04
    Lg = float(np.linalg.norm(Wl - E))
    P.append(dict(name='glove_cuff.L', bone='forearm.L', color='umber', frame=fg, ring=True,
                  t0=Lg - 0.034, t1=Lg + 0.010, off=0.003, thick=0.007, bevel=0.002, under='umber', rmax=0.08,
                  n_ring=32))
    P += apron()
    P += belt_items()
    P += legs()
    P += hair_locks()
    return P


def hair_locks() -> list[dict]:
    """髪の房と前髪を 1 本ずつの面の部品にする（hair.LOCKS_AS_PARTS、hair.lock_mesh）。色は髪の 1 色、骨は head。
    道は形の段の場（hull.npz：帽子＋頭。房は含まない）の面に沿う"""
    from recon import hair as HR
    from recon import views as V
    if not HR.LOCKS_AS_PARTS:
        return []
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    out = []
    for name, Vm, Fm in HR.lock_parts(d['phi'], d['lo'], float(d['vox'])):
        out.append(dict(name='hair_' + name, bone='head', color='hair', mesh=(Vm, Fm)))
    return out


def boot_pieces(side: float, sx: str) -> list[dict]:
    """片足の靴（左の値で書き、右は x を反転）。絵 yana_shoes.png と全身の絵（正面・右真横）：
    靴底 x 0.118〜0.298・y −0.185〜0.135、厚い暗い底（前とかかとのブロック、間に土踏まずの切り欠き）、
    黄土の爪先（甲の前、z 0.05〜0.11）、茶の胴（足首 z 0.20 まで）、胴を回る暗いひも（z 0.14）"""
    X0, X1 = 0.118, 0.298
    YF, YB = -0.185, 0.135
    P = []

    def sec(z, x0, x1, y0, y1, rf, rb, k=3):
        return (z, rrect(x0, x1, y0, y1, rf, rb, k))

    sole = [sec(0.000, X0 + 0.004, X1 - 0.004, YF + 0.008, -0.010, 0.045, 0.004),
            sec(0.004, X0 + 0.001, X1 - 0.001, YF + 0.002, -0.006, 0.048, 0.004),
            sec(0.040, X0 + 0.001, X1 - 0.001, YF + 0.001, 0.010, 0.048, 0.004)]
    heel = [sec(0.000, X0 + 0.010, X1 - 0.010, 0.040, YB - 0.004, 0.004, 0.024),
            sec(0.004, X0 + 0.008, X1 - 0.008, 0.038, YB - 0.001, 0.004, 0.026),
            sec(0.044, X0 + 0.008, X1 - 0.008, 0.032, YB - 0.001, 0.004, 0.026)]
    plate = [sec(0.036, X0, X1, YF, YB, 0.048, 0.03),
             sec(0.052, X0, X1, YF, YB, 0.048, 0.03),
             sec(0.058, X0 + 0.004, X1 - 0.004, YF + 0.004, YB - 0.004, 0.044, 0.026)]
    toe = [sec(0.050, X0 + 0.008, X1 - 0.008, YF + 0.008, -0.030, 0.042, 0.004),
           sec(0.085, X0 + 0.012, X1 - 0.014, YF + 0.016, -0.045, 0.038, 0.004),
           sec(0.108, X0 + 0.024, X1 - 0.028, YF + 0.040, -0.060, 0.030, 0.004)]
    upper = [sec(0.050, X0 + 0.012, X1 - 0.014, -0.150, 0.128, 0.03, 0.035, 4),
             sec(0.095, X0 + 0.014, X1 - 0.026, -0.120, 0.126, 0.03, 0.035, 4),
             sec(0.125, 0.112, 0.262, -0.075, 0.122, 0.03, 0.04, 4),
             sec(0.160, 0.110, 0.250, -0.062, 0.115, 0.04, 0.045, 4),
             sec(0.215, 0.110, 0.248, -0.060, 0.112, 0.045, 0.045, 4)]
    lace = [sec(0.134, 0.106, 0.258, -0.074, 0.122, 0.035, 0.045, 4),
            sec(0.144, 0.106, 0.256, -0.072, 0.121, 0.035, 0.045, 4)]
    for name, color, secs in (('sole', 'graphite', sole), ('heel', 'graphite', heel), ('sole_plate', 'graphite', plate),
                              ('toe_cap', 'brass', toe), ('upper', 'umber', upper), ('lace', 'graphite', lace)):
        if side < 0:
            secs = [(z, [(-x, y) for (x, y) in pts][::-1]) for z, pts in secs]
        P.append(dict(name=f'boot_{name}{sx}', bone='foot' + sx, color=color, loft=secs,
                      ramp=('shin' + sx, 'foot' + sx)))
    return P


# ---------------------------------------------------------------- 決まりの塗り（cover_body から）

def body_rules(pos: np.ndarray, col: np.ndarray, lab: np.ndarray, under: np.ndarray, ins: dict, stats: dict) -> None:
    """胴・腕の上はシャツの生成り、左腕の袖口より先は肌、右腕（義手の下）は石墨、ベルトより下はズボン。
    首は肌（シャツの首の縁より上）。頭と首の帯は形の場（hair.part_fields_at）で髪・肌・耳を決める（バートンと同じ）"""
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    free = under < 0
    r_neck = np.hypot(x + 0.012, y - 0.01)
    head = (z > NECK_TOP + 0.01) | ((z > 1.20) & (r_neck > 0.075) & (y < 0.0))
    belt = 0.905
    shirt = free & ~head & (z >= belt)
    under[shirt] = NAMES.index('ivory')
    # 左腕：袖口より先は肌（上腕の軸の長さで切る）
    S = np.array([0.205, 0.012, 1.13])
    E = arm_center(0.935, 1.0)
    d = (E - S) / np.linalg.norm(E - S)
    t = (pos - S) @ d
    rr = np.linalg.norm((pos - S) - np.outer(t, d), axis=1)
    larm = free & (x > 0.17) & (rr < 0.09) & (t > (SLEEVE_T[0] + SLEEVE_T[1]) / 2)
    under[larm] = NAMES.index('skin')
    # 右腕（義手）：部品の下・すき間は石墨
    Sr = np.array([-0.205, 0.0, 1.13])
    Er = arm_center(0.935, -1.0)
    dr = (Er - Sr) / np.linalg.norm(Er - Sr)
    tr = (pos - Sr) @ dr
    rrr = np.linalg.norm((pos - Sr) - np.outer(tr, dr), axis=1)
    # 1 周目は肩の板の外の胸・わきまで暗くなった → 肩の板の下の縁（z 1.08）より下の腕だけ
    rarm = free & (x < -0.19) & (z < 1.08) & ((rrr < 0.07) | (z < 0.96)) & (z > 0.70)
    under[rarm] = NAMES.index('graphite')
    # 首（シャツの首の縁より上）：肌
    neck = free & ~head & (z > 1.205) & (r_neck < 0.09)
    under[neck] = NAMES.index('skin')
    legs = free & (z < belt)
    under[legs] = NAMES.index('olive')
    # 頭と首の帯：形の場で（バートンと同じ作り）
    from recon import hair as HR
    hb = (z > 1.18) & (z < 1.62) & (np.hypot(x + 0.012, y - 0.01) < np.where(z > 1.22, 0.19, 0.125))
    hi = np.nonzero(hb)[0]
    if len(hi):
        f = HR.part_fields_at(pos[hi])
        xh, yh, zh = x[hi], y[hi], z[hi]
        ear = f['ear'] > -0.002
        hair = (f['hair'] > -0.004) & ~ear
        lab_h = np.full(len(hi), NAMES.index('skin'))
        lab_h[zh < 1.205] = NAMES.index('ivory')
        th_f = np.degrees(np.arctan2(np.abs(xh + 0.012), -(yh - 0.01)))
        zb = np.interp(th_f, HAIR_LOW[0], HAIR_LOW[1])
        # 角度の表の髪は耳より後ろ（えり足）だけ。1 周目は 50 度から使い、ほおの横が髪の色になった
        low = (th_f > 105.0) & (zh > zb) & ~ear
        # 頭の面に沿った帽子（刈り上げ・もみあげの下）は、線より下なら肌：前（正面から 75 度まで）は生え際の線（目の横は
        # 絵のとおり耳寄り）、耳の前は耳の中ほど、耳より後ろはえり足。頭から浮いた房（前髪・長い房）は線より下でも髪。
        # 2 周目：あごの横・目の横に、頭の面に貼り付いた帽子の髪の色が平らな茶の板として残った
        # 横（75 度より後ろ）は刈り上げの帽子が頭から 8mm（hair.CAP.undercut）なので、その厚みまで「貼り付いた帽子」に数える
        # （3 周目：あごの横・耳の下に茶の横縞が残った）
        flush = (f['hair'] - f['skin']) < np.where(th_f < 75.0, 0.009, 0.011)   # 4 周目：前は 4mm だと境が判定で揺れ、こめかみにのこぎりの歯
        line = np.where(th_f < 75.0, np.interp(np.abs(xh + 0.012), HAIRLINE_PAINT[0], HAIRLINE_PAINT[1]),
                        np.where(th_f < 100.0, 1.318, 1.25))
        hair &= ~(flush & (zh < line))
        lab_h[hair | low] = NAMES.index('hair')
        lab_h[ear] = NAMES.index('skin')
        keep = under[hi] >= 0
        under[hi[~keep]] = lab_h[~keep]
    stats['yana_rule_texels'] = int((shirt | larm | rarm | neck | legs).sum())


# ---------------------------------------------------------------- 手の部品（hand.py）

# 左：指抜き手袋（掌と基節が手袋の暗い茶、中節・末節は肌）。右：義手（白い節と黒い関節、甲は白い板、掌は黒）。
# 絵 yana_hands.png：左手 18cm（再構築の座標で 16.2cm）、細めの指
_S, _R = 1.02, 1.0
HAND = dict(
    GLOVE='umber',
    LID='umber',
    GLOVE_FRAC=0.82,
    GLOVE_THICK=0.0012,
    OPEN_FINGERS=[(n, z * _S, x * _S, r * _R, tuple(v * _S for v in L), fan) for n, z, x, r, L, fan in (
        ('index', 0.0255, 0.070, 0.0078, (0.036, 0.023, 0.019), 6.0),
        ('middle', 0.0085, 0.073, 0.0081, (0.038, 0.025, 0.020), 1.0),
        ('ring', -0.0085, 0.070, 0.0076, (0.035, 0.023, 0.019), -4.0),
        ('pinky', -0.0240, 0.063, 0.0066, (0.028, 0.019, 0.016), -9.0))],
    OPEN_CURL=(14.0, 18.0, 14.0),
    CUFF_LID=(-0.012, 0.006),
    OPEN_THUMB=dict(base=(0.026, 0.008, 0.024), r=0.0086, lens=(0.033, 0.028, 0.024), out_deg=22.0,
                    palm_deg=34.0, curl=(8.0, 12.0, 10.0)),
    PALM_HALF_T=0.0115,
    PALM_WRIST=(0.002, 0.0, 0.015, 0.028),
    PALM_X=(0.012, 0.044),
    THENAR=((0.028, 0.007, 0.022), 0.014),
    HYPOTHENAR=((0.034, 0.005, -0.020), 0.0125),
    LEFT_HAND_CUT=-0.004,
    LEFT_HAND_RAMP=(-0.014, 0.006),
    # 右の義手（hand.build_open の mech）：節は 8 角の筒（白）、関節は暗い玉、掌は暗い、甲に白い板
    MECH=dict(seg='ivory', joint='graphite', palm='graphite', plate='ivory', seg_r=1.12, joint_r=1.05, gap=0.0035,
              seg_n=8),
)
