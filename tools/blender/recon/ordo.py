"""巡礼機オルド（W2-04。町を背に載せて歩く全長 400 m の機械）を、spec の寸法から部品で組む（視体積・絵の色の投影は使わない）。

  npm run ordo:build
  .venv-blender/bin/python tools/blender/recon/ordo.py [--review]

できるもの
  godot/assets/models/ordo.glb   部品の階層。材質は 5 つ：ivory（白磁）・graphite（黒鉛）・brass（真鍮）・cloth（布）・amber（琥珀の発光）。
                                 名前は町のキット（content/kits/town.json の "materials"）と同じなので、あとで同じ名前の材質（汚れの層つき）に
                                 置き換えられる（ordo_view.gd の apply_kit）。UV は面の向きの平面投影（m、部品の原点から）
  build/ordo/rig.json            関節の位置（Godot の座標）・脚の長さ・背の面の範囲・三角形の数（結果の文書・確かめ用）
  build/ordo/review/             --review のとき：絵（4.5 px/m）と並べた正投影の画像

■ 寸法（spec_ordo_3d.md・spec.md が絵に勝つ。絵は形・部品の並び・前後の位置に使う）
  全長 400 m（側面・真上の絵の 1798 px ÷ 4.5 px/m と一致）。背の歩行面は地面から 120 m、肩の軸は 85 m、足の裏 38 × 24 m（前後 × 左右）。
  絵は名目の 4.5 px/m で測ると、背の面が約 70 m、足が約 64 m と spec と食い違う（高さは spec の 6 割、足は 1.7 倍）。
  そこで：前後・左右の位置（脚の取付 15/38/62/85 %、リフトの前後、船首の細り）は絵を 4.5 px/m で、高さは spec（絵の高さ × 約 1.72）、
  脚は spec の肩 85 m・足 38 × 24 m に合わせて、絵の脚の形（膝が後ろへ曲がる 2 節・板 2 枚と黒鉛の芯・真鍮の円板とピストン）で組む。
  船体の幅：町（約 90 m）と縁を載せる背の面は ±56 m、縁（舷）の外 ±60 m（旧遠景 ordo_far と同じ 120 m。町の部屋の外の縁が近く見える）。
  肩の円板の外の面が ±68.6 m（船体の最大の幅 137 m ≒ spec の約 135 m）。脚は船体の外（±64 m の面）に下がり、足は ±52〜76 m。
  前の 2 対（1・2）は膝が後ろ（船尾）へ、後ろの 2 対（3・4）は膝が前へ出る（側面の絵のとおり。前後は 1 つの定義を鏡写し）。

■ 座標（Blender、m）
  原点 = 背の歩行面（町を載せる平らな面）の真ん中（旧遠景 ordo_far と同じ）。上 +Z、船首 -Y。glTF / Godot では +Y が上、+Z が船首。
  +X はオルドの左（左舷）、-X が右（右舷。昇降リフトの側）。地面は z = -120（Godot の y = -120）。
  背の面：z = 0、|x| ≤ 56、y = -100 〜 +118（Godot の z = -118 〜 +100）で平ら。外は縁（高さ 2.5 m）、前後は船首（+44 m）・船尾（+33 m）へ持ち上がる。

■ 部品（親 → 子）と動き。原点 = 回転の軸、ローカル +X = 軸の向き（Godot で「元の姿勢 * Basis(RIGHT, 角度)」）
  body                         船体：黒鉛の芯＋すき間を空けた白磁の板（背・縁・舷の上下 2 段）・黒鉛の梁（トラス）・下に下がる突起・肩の受け・
                               船首のセンサースリット（琥珀）・船尾の禁足扉の外枠（船体側）・右舷のリフトの踊り場（布の日よけ）
   ├ door                      禁足扉（白磁の 2 枚扉＋真鍮の中の桟）。ローカル +X = 下：0〜30 m 下へ滑って開く（平行移動）
   ├ lift_guide                リフトのガイド（黒鉛の柱 4 本・真鍮の滑車）。ローカル +X = 下へ伸びる（平行移動）
   │  └ lift_cage              かご（10 × 8 × 12 m）。ローカル +X = 下（平行移動）。元の姿勢は踊り場の真下に収まった所
   └ leg_<l|r><1..4>_roll      肩の横振り（ローカル +X = 船首の向き、±5 度）。l = 左舷（+X）、r = 右舷（-X）、1〜4 は船首から
       └ leg_*_shoulder        肩のピッチ（ローカル +X = 左舷の向き、±22 度）：真鍮の円板・太もも（板 2 枚・黒鉛の芯・真鍮のピストン）
           └ leg_*_knee        膝（同じ軸）：膝の円板・すね
               └ leg_*_ankle   足首（同じ軸）：足首の円板・足（白磁の踏み板 2 枚・黒鉛の台・真鍮の縁金具）
  ピッチの軸は 8 本とも同じ +X（左右・前後に鏡写ししても符号を変えない）。歩き方は godot/scripts/view/ordo_view.gd（手続きで回す）。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import banki as B   # noqa: E402  new_object・axis_matrix・smooth_by_angle・srgb_to_linear を使い回す
import kannuki as K  # noqa: E402  orient・lathe・extrude・cham_rect・merge を使い回す

REPO = B.REPO
WORK = os.path.join(REPO, 'build', 'ordo')
SRC = os.path.join(WORK, 'art')
ART_REF = 'origin/art/w2-ordo:art/concepts/W2_ordo'
OUT = os.path.join(B.MODELS, 'ordo.glb')
V3 = np.array

# ---------------------------------------------------------------- 寸法（m）

GROUND = -120.0          # 地面（背の面から）
HULL_HW = 55.0           # 舷の外の面の半幅（町の所）。2026-10-16 に 60 → 55（町の東西の壁 |x| 49 から縁の内まで 2 m。--hull-hw で変えられる）
RIM_W, RIM_H = 4.0, 2.5  # 縁（舷）の幅・背の面からの高さ
BAND_H = 15.0            # 舷の白磁の帯の高さ（縁の上の端から。絵の側面図の細い白い帯）。その下は黒鉛の梁の外の面（中は閉じた芯）
PLATE_T = 1.2            # 舷の白磁の板の厚み（芯から浮かせた分。すき間から黒鉛の芯が見える）
GAP = 1.0                # 板のすき間（前後）
DECK_T = 1.0             # 背の板の厚み
SHOULDER_Z = GROUND + 85.0   # 肩の軸（地面から 85 m）
ANKLE_Z = GROUND + 14.0      # 足首の軸
XL = HULL_HW + 4.0       # 肩の軸の中心の x（左舷。右舷は -XL）。舷の外の面の 4 m 外
SPLAY_K, SPLAY_A = 8.0, 12.0   # 膝・足首を肩より外へ出す（m）。正面・真上の絵のとおり脚が外へ開き、足が舷の外に着く。
                               # ピッチの軸はどれも x に平行のままなので、横から見た 2 節の IK はそのまま
L_THIGH, L_SHIN = 48.0, 34.0
MOUNTS = {1: -140.0, 2: -48.0, 3: 48.0, 4: 140.0}   # 脚の取付（y。船首 -200 から 15・38・62・85 %）
FOOT_L, FOOT_W = 52.0, 34.0   # 足の裏（前後 × 左右）。spec 38 × 24 と絵 64 × 44 の間（絵の 8 割。隣の足とは最も近い時でも 10 m 離れる）
LIFT_Y = 12.0            # リフトの中心（Godot の z = -12。脚 2・3 の太ももの振れから 10 m 以上離れる所）
LIFT_SIDE = 1.0          # リフトの舷：+1 = 左舷（+X）。spec の文は右脇腹だが、町の下の段の部屋（ch1.lower）のリフトの端末が東（+X）の端にあるので合わせた
LANDING_TOP = 1.5        # 踊り場の上の面（背の面の 1.5 m 上 = 町の下の段の床の高さ。下の段の部屋から歩いて出られる）
DOOR_W, DOOR_H = 22.0, 30.0
# 船首の細り（平面）：絵 ordo_3d_top の外形を 4.5 px/m で測った、船首からの距離 d（m）と半幅の割合。先は 13 m の前の面を残す
BOW_TAPER = ((0.0, 0.12), (6.7, 0.32), (13.3, 0.46), (20.0, 0.57), (26.7, 0.66), (33.3, 0.77), (40.0, 0.86),
             (46.7, 0.93), (53.3, 0.975), (60.0, 1.0))
MAT_COLORS = {   # 名前は town.json の materials と同じ（あとでキットの材質に替えられる）
    'ivory': ('#E9DFC9', 0.8, 0.0),      # 白磁（spec #F3E9D2。閂・町のキットと同じ清書の色）
    'graphite': ('#444641', 0.6, 0.3),
    'brass': ('#A98749', 0.55, 0.4),     # つや消しの真鍮（spec）。つやを強くすると平らな円板が空を映して玉に見える
    'cloth': ('#B75B43', 0.95, 0.0),
    'amber': ('#FFBC52', 0.4, 0.0),
    'dark': ('#2B2824', 0.7, 0.0),       # 黒鉛の梁の奥の閉じた芯（梁の外の面と色を分けて、骨組みに見せる。キットの dark と同じ）
}


def log(msg):
    print(f'[ordo] {msg}', flush=True)


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def z_top(y):
    """背の面の高さ（船首 +30 m・船尾 +22 m へ持ち上がる。町の所は平ら）。絵の持ち上がり（4.5 px/m で +27・+20 m）とほぼ同じ"""
    if y < -100:
        z = 30.0 * smooth((-100.0 - y) / 62.0)
        if y < -194:
            z -= (-194.0 - y) * 1.0          # 船首の上の角の面取り
        return z
    if y > 118:
        return 22.0 * smooth((y - 118.0) / 34.0)
    return 0.0


def half_w(y):
    """舷の外の面の半幅（平面の形）。船首は絵の上面図のとおり先へ尖り（船首から 60 m で細る。先に 13 m の前の面）、
    船尾は最後の 34 m で 0.56 まで細る（禁足扉の外枠と両脇の翼が載る船尾の面）。町の所（y = -140〜166）は HULL_HW"""
    if y < -140:
        d = y + 200.0
        return HULL_HW * float(np.interp(d, [q[0] for q in BOW_TAPER], [q[1] for q in BOW_TAPER]))
    if y > 166:
        return HULL_HW * (1.0 - 0.44 * smooth((y - 166.0) / 27.0))
    return HULL_HW


def z_band(y):
    """舷の白磁の帯の下の縁（その下は黒鉛の梁の外の面と、奥の閉じた芯）。帯は縁の上の端から BAND_H（15 m、絵の側面図の細い帯）で、
    背の面の持ち上がりに沿う（三日月）。船首の頭は先の 50 m で 8 m、船尾の翼は最後の 40 m で 14 m 下まで白（絵の頭と尾の白い塊）"""
    zb = z_top(y) + RIM_H - BAND_H
    if y < -150:
        zb -= 8.0 * smooth((-150.0 - y) / 50.0)
    if y > 160:
        zb -= 14.0 * smooth((y - 160.0) / 40.0)
    return zb


def z_bot(y):
    """船底（梁の下の面・閉じた芯の底）。町の所は背の面から 52 m（体内の遺構 B1〜B4 の深さ 50〜60 m が入る。2026-10-16 の決定で薄くしない）。
    船首は前へ斜めに上がる（側面の絵：船首の下の面が前へ上がる）"""
    if y < -140:
        return -52.0 + 50.0 * smooth((-140.0 - y) / 60.0)
    if y > 160:
        return -52.0 + 8.0 * smooth((y - 160.0) / 40.0)
    return -52.0


def z_knee_line(y):
    """舷の上の段と下の段（少し内へ傾く面）の境"""
    return min(z_band(y) + 5.0, z_top(y) - 2.5)


# 形の関数の折れ目（ここには必ず断面を置く：背の面は y = -100〜118 で正確に平ら）
KNOTS = tuple(sorted({-194.0, -162.0, -150.0, -140.0, -110.0, -100.0, 118.0, 140.0, 150.0, 152.0, 160.0, 166.0, 193.0, 194.0,
                      *(-200.0 + q[0] for q in BOW_TAPER[1:-1])}))


def stations(y0, y1, step=4.0):
    """y0〜y1 の断面の位置。持ち上がる所・細る所（y < -100、y > 118）だけ細かく"""
    ys = {y0, y1}
    ys |= {k for k in KNOTS if y0 < k < y1}
    k = math.ceil(y0 / step) * step
    while k < y1:
        if k < -100 or k > 118:
            ys.add(float(k))
        k += step
    return sorted(ys)


# ---------------------------------------------------------------- 形の道具

def loft(sections, cap=True):
    """断面（同じ点の数の閉じた多角形、(n,3)）を順につないだ閉じた形"""
    n = len(sections[0])
    v = np.concatenate([np.asarray(s, float) for s in sections])
    f = []
    for i in range(len(sections) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            f.append([a, b, b + n, a + n])
    if cap:
        f.append(list(range(n))[::-1])
        f.append([(len(sections) - 1) * n + k for k in range(n)])
    return v, K.orient(v, f)


def offset_line(pts, d):
    """開いた折れ線（(x, z)）を右側（進む向きの右 = 船体の内側）へ d ずらす（頂点ごとの留め継ぎ）"""
    pts = [V3(p, float) for p in pts]
    out = []
    for i, p in enumerate(pts):
        ns = []
        for a, b in ((pts[i - 1], p) if i > 0 else (None, None), (p, pts[i + 1]) if i < len(pts) - 1 else (None, None)):
            if a is None:
                continue
            t = (b - a) / np.linalg.norm(b - a)
            ns.append(V3([t[1], -t[0]]))
        n = ns[0] if len(ns) == 1 else (ns[0] + ns[1])
        n = n / np.linalg.norm(n)
        if len(ns) == 2:
            n = n / max(float(n @ ns[0]), 0.3)
        out.append(p + n * d)
    return out


def plate(y0, y1, line_fn, thick, sx=1.0, step=4.0):
    """舷・背の板：断面の折れ線 line_fn(y) -> [(x, z)...]（x ≥ 0 の側、船体の内側が進む向きの右）を厚み thick で y0〜y1 へ"""
    secs = []
    for y in stations(y0, y1, step):
        o = line_fn(y)
        ring = list(o) + offset_line(o, thick)[::-1]
        secs.append([(sx * x, y, z) for x, z in ring])
    return loft(secs)


def ring_loft(y0, y1, poly_fn, sx=1.0, step=4.0):
    """断面の閉じた多角形 poly_fn(y) -> [(x, z)...] を y0〜y1 へ"""
    return loft([[(sx * x, y, z) for x, z in poly_fn(y)] for y in stations(y0, y1, step)])


def boxr(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    v = V3([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], float)
    f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return v, K.orient(v, f)


def bar(p0, p1, w, h, up=(0, 0, 1)):
    """p0 → p1 の角材（幅 w・高さ h。h は up の向き）"""
    return K.extrude([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], p0, p1, up=up)


def cylx(x0, x1, y, z, r, segs=16):
    return K.lathe((x0, y, z), (x1, y, z), [(0, r), (1, r)], segs)


def disc(x_in, x_out, y, z, r, segs=24):
    """真鍮の円板（x_in → x_out へ張り出す。絵の肩・膝・足首の円板）：面取りした外の縁の輪・一段へこんだ面・中の盛り上がり（ボス）。
    段の高さは 0.4〜0.9 m（遠くからでも輪と影が読める。平らな 1 枚だと、つやの映り込みで丸い玉に見えた）"""
    d = abs(x_out - x_in)
    s = 1.0 if x_out > x_in else -1.0
    rec, boss = min(0.6, 0.35 * d), 0.9
    L = d + boss - rec
    pts = [(0.0, r), (d - 0.3, r), (d, r - 0.3), (d, 0.8 * r), (d - rec, 0.78 * r), (d - rec, 0.42 * r),
           (d - rec + boss, 0.36 * r), (d - rec + boss, 0.0)]
    prof = [(t / L, rr) for t, rr in pts]
    return K.lathe((x_in, y, z), (x_in + s * L, y, z), prof, segs)


def slab(c, u, v, lu, lv, tw, ch, wdir=(1, 0, 0)):
    """面取りした板：中心 c、長さ lu（u の向き）・幅 lv（v の向き）・厚み tw（wdir の向き）。ch：角の面取り"""
    c, u, v, w = V3(c, float), V3(u, float), V3(v, float), V3(wdir, float)
    poly = K.cham_rect(lu / 2, lv / 2, ch)
    vs = []
    for s in (-0.5, 0.5):
        for a, b in poly:
            vs.append(c + u * a + v * b + w * (s * tw))
    n = len(poly)
    f = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
    f += [list(range(n))[::-1], list(range(n, 2 * n))]
    vs = V3(vs)
    return vs, K.orient(vs, f)


def mirror_x(piece):
    v, f = piece
    v = v * V3([-1.0, 1.0, 1.0])
    return v, K.orient(v, f)


def both(piece):
    """左舷（+X）の形と、その鏡写しの右舷"""
    return [piece, mirror_x(piece)]


M = K.merge


# ---------------------------------------------------------------- 船体

def core_poly(y):
    """閉じた芯の断面（背の板の下 → 舷の板の裏 → 帯の下で内へ → 船底）。帯の下は梁の外の面の 3〜7 m 奥（材質 dark：梁が骨組みに見える）"""
    hw, zt, zb, zbt, zk = half_w(y), z_top(y), z_band(y), z_bot(y), z_knee_line(y)
    lo = 0.25 * hw
    right = [(hw - 1.3, zt - 1.1), (hw - 1.3, zk), (max(hw - 4.2, lo), zb), (max(hw - 8.0, lo), zb - 1.0), (max(hw - 16.0, lo), zbt)]
    ring = [(0.0, zt - 1.1)] + right + [(0.0, zbt)] + [(-x, z) for x, z in right[::-1]]
    return ring


# 舷の板の前後の区切り（y）。肩の受けの所（下の段）は板を切って黒鉛の受けを見せる
FLANK_BREAKS = [-200, -186, -158, -128, -100, -74, -48, -22, 2, 22, 46, 70, 94, 118, 134, 150, 175, 200]
DECK_BREAKS = [-200, -186, -158, -130, -104, -78, -52, -26, 0, 26, 52, 78, 104, 128, 150, 175, 200]


def build_hull(pc):
    """黒鉛の芯・白磁の板（背・縁・舷の上下 2 段）・船首と船尾の面"""
    pc['dark'].append(ring_loft(-200.0, 200.0, core_poly))
    # 背の板：横に 3 列（真ん中・中・外）、前後に区切り。上の面が z_top（町の所は 0）
    for y0, y1 in zip(DECK_BREAKS[:-1], DECK_BREAKS[1:]):
        a, b = y0 + GAP / 2, y1 - GAP / 2
        for f0, f1 in ((0.0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.0)):
            def line(y, f0=f0, f1=f1):
                w = half_w(y) - RIM_W - 0.5
                return [(f0 * w + (0.5 if f0 > 0 else 0.0), z_top(y)), (f1 * w - 0.5, z_top(y))]
            if f0 == 0.0:
                # 真ん中の列は左右をつないだ 1 枚（中心線に継ぎ目を作らない）
                def line_c(y, f1=f1):
                    w = half_w(y) - RIM_W - 0.5
                    return [(-(f1 * w - 0.5), z_top(y)), (f1 * w - 0.5, z_top(y))]
                pc['ivory'].append(plate(a, b, line_c, DECK_T))
            else:
                pc['ivory'] += both(plate(a, b, line, DECK_T))
    # 縁（舷）の内側の白磁の角材：板と 0.4 m 離す（上から黒鉛の線が見える）
    for y0, y1 in zip(FLANK_BREAKS[:-1], FLANK_BREAKS[1:]):
        a, b = y0 + GAP / 2, y1 - GAP / 2
        def rim(y):
            hw, zt = half_w(y), z_top(y)
            return [(hw - RIM_W, zt - 1.0), (hw - 1.6, zt - 1.0), (hw - 1.6, zt + RIM_H - 0.15), (hw - RIM_W, zt + RIM_H - 0.15)]
        for sx in (1.0, -1.0):
            if (sx == LIFT_SIDE and lift_segment(a, b)) or RIM_W < 2.5:
                continue        # 細い縁（RIM_W < 2.5）は舷の板の上の端だけ（内の角材なし）
            pc['ivory'].append(ring_loft(a, b, rim, sx))
    # 舷の板：上の段（縁の上 → 境）と下の段（境 → 帯の下、内へ傾く）
    for y0, y1 in zip(FLANK_BREAKS[:-1], FLANK_BREAKS[1:]):
        a, b = y0 + GAP / 2, y1 - GAP / 2
        for sx in (1.0, -1.0):
            lift = sx == LIFT_SIDE and lift_segment(a, b)
            def upper(y, lift=lift):
                hw, zt, zk = half_w(y), z_top(y), z_knee_line(y)
                return [(hw, (zt + LANDING_TOP - 3.4) if lift else (zt + RIM_H)), (hw, zk)]
            pc['ivory'].append(plate(a, b, upper, PLATE_T, sx))
            if any(abs(0.5 * (a + b) - ym) < 14.0 for ym in MOUNTS.values()):
                continue    # 肩の受けの上は下の段の板を外す（絵：帯の下の縁が肩の円板の上で切れている）
            def lower(y):
                hw, zb, zk = half_w(y), z_band(y), z_knee_line(y)
                return [(hw, zk - 0.8), (hw - 2.5, zb)]
            pc['ivory'].append(plate(a, b, lower, PLATE_T, sx))
    build_bow(pc)
    build_stern(pc)


def lift_segment(a, b):
    return a < LIFT_Y < b


def section_outline(y, z_lo):
    """船首・船尾の面の外形（左右、縁の上 → z_lo まで）"""
    hw, zt = half_w(y), z_top(y)
    zk = z_knee_line(y)
    pts = [(hw, zt + RIM_H), (hw, zk), (hw - 5.0, z_band(y))]
    right = [p for p in pts if p[1] >= z_lo - 1e-6]
    return right


def face_panel(y_face, dy, x0, x1, z0, z1, zt_cut=None):
    """船首・船尾の平らな面の板（y_face から dy の厚み）"""
    return boxr(x0, x1, y_face, y_face + dy, z0, z1)


def build_bow(pc):
    """船首：尖った船首の先の前の面（13 m）に、真鍮の枠・黒鉛の溝・琥珀の帯のセンサースリット。帯は頭の両脇の斜めの面を船首から 40 m まで回る
    （正面から見ると V の琥珀の線）。白は帯の上だけで、下は黒鉛のあご（正面から一つの白い塊に見えないように）・頭の上の低い機械の箱"""
    y = -200.0
    hw, zt, zb = half_w(y), z_top(y), z_band(y)
    top = zt + RIM_H
    zs_lo, zs_hi = zb + 8.0, zb + 13.0          # スリットの帯（真鍮の枠）の上下
    pc['ivory'].append(boxr(-hw, hw, y - PLATE_T, y, zs_hi + 0.4, top))
    pc['ivory'].append(boxr(-hw, hw, y - PLATE_T, y, zb, zs_lo - 0.4))
    pc['graphite'].append(boxr(-hw + 0.3, hw - 0.3, y - 0.6, y + 0.5, zs_lo - 0.4, zs_hi + 0.4))
    pc['brass'].append(boxr(-hw + 0.8, hw - 0.8, y - PLATE_T - 0.7, y, zs_lo, zs_hi))
    pc['graphite'].append(boxr(-hw + 1.5, hw - 1.5, y - PLATE_T - 1.1, y, zs_lo + 1.0, zs_hi - 1.0))
    pc['amber'].append(boxr(-hw + 2.0, hw - 2.0, y - PLATE_T - 1.3, y, zs_lo + 1.8, zs_hi - 1.8))
    # 頭の両脇の斜めの面を回る帯：背の面に平行（船首の先の帯の高さから）
    dz = 0.5 * (zs_lo + zs_hi) - zt
    for sx in (1.0, -1.0):
        ys = np.linspace(-199.0, -160.0, 9)
        for ya, yb in zip(ys[:-1], ys[1:]):
            pa = V3([sx * (half_w(ya) + 0.3), ya, z_top(ya) + dz])
            pb = V3([sx * (half_w(yb) + 0.3), yb, z_top(yb) + dz])
            pc['brass'].append(bar(pa, pb, 1.4, 5.0, up=(0, 0, 1)))
            pc['graphite'].append(bar(pa + V3([sx * 0.5, 0, 0]), pb + V3([sx * 0.5, 0, 0]), 1.0, 3.4, up=(0, 0, 1)))
            pc['amber'].append(bar(pa + V3([sx * 0.8, 0, 0]), pb + V3([sx * 0.8, 0, 0]), 0.9, 1.4, up=(0, 0, 1)))
    # あご（帯の下で前へ出た黒鉛の塊と真鍮の縁）：正面の下は黒鉛
    pc['graphite'].append(slab((0, y + 2.0, zb - 3.0), (1, 0, 0), (0, 0, 1), max(2 * hw - 2.0, 6.0), 6.0, 9.0, 1.6, wdir=(0, 1, 0)))
    pc['brass'].append(boxr(-hw + 1.5, hw - 1.5, y - 2.6, y - 2.0, zb - 0.8, zb - 0.2))
    # 頭の上の機械の箱（黒鉛）と真鍮の丸屋根（低い：夜明けの甲羅の部屋 ch1.opening の台はこの上）
    zr = z_top(-178.0)
    pc['graphite'].append(boxr(-11, 11, -188, -170, zr - 1.0, zr + 4.5))
    pc['brass'].append(K.lathe((0, -179, zr + 4.5), (0, -179, zr + 7.0), [(0, 6.0), (0.4, 5.2), (1, 0.0)], 16))
    pc['amber'].append(boxr(-7, 7, -170.2, -169.6, zr + 2.0, zr + 2.8))


def build_stern(pc):
    """船尾の面：上は白磁の翼（左右、琥珀の細いスリット）、真ん中に禁足扉の黒鉛の外枠（四隅の真鍮・左右と上の琥珀の灯）と両脇の柱・横木、
    翼の下は黒鉛の面（真鍮の帯）。白い一つの塊に見えないように、扉の外枠の縦の黒い帯が上から下まで通る"""
    y = 200.0
    hw, zt, zb = half_w(y), z_top(y), z_band(y)
    top = zt + RIM_H
    zbt = z_bot(y)
    fx, fz = 17.0, 19.0               # 扉の外枠の半幅・半高（開口 22 × 30 の外）
    T = PLATE_T
    # 船尾の面の板（白磁の翼）：扉の外枠の左右（帯の下の縁 zb まで）・上
    for sx in (1.0, -1.0):
        pc['ivory'].append(boxr(sx * (fx + 6.5), sx * (0.5 * (fx + hw) + 3.0), y, y + T, zb, top))
        pc['ivory'].append(boxr(sx * (0.5 * (fx + hw) + 3.8), sx * hw, y, y + T, zb, top))
        pc['amber'].append(boxr(sx * (fx + 8.0), sx * (hw - 2.5), y + T, y + T + 0.4, top - 7.5, top - 6.6))
        pc['graphite'].append(boxr(sx * (fx + 7.5), sx * (hw - 2.0), y + T - 0.1, y + T + 0.25, top - 8.2, top - 5.9))
        # 翼の下の黒鉛の面と真鍮の帯
        pc['graphite'].append(boxr(sx * (fx + 0.5), sx * (hw - 1.0), y - 1.0, y + 0.6, zbt + 1.0, zb))
        pc['brass'].append(boxr(sx * (fx + 0.5), sx * (hw - 1.0), y + 0.6, y + 1.0, zb - 1.6, zb - 0.8))
    pc['ivory'].append(boxr(-fx - 6.0, fx + 6.0, y, y + T, fz + 2.8, top))
    pc['graphite'].append(boxr(-fx, fx, y - 1.0, y + 0.6, zbt + 1.0, -fz - 0.5))
    # 扉の外枠（船体側。黒鉛）・四隅の真鍮・琥珀の灯の帯（左右の縦と上）
    ox, oz = DOOR_W / 2, DOOR_H / 2
    for sx in (1.0, -1.0):
        pc['graphite'].append(boxr(sx * ox, sx * fx, y - 0.5, y + T + 1.6, -fz, fz))
        pc['amber'].append(boxr(sx * (ox + 1.6), sx * (ox + 2.4), y + T + 1.6, y + T + 1.9, -oz + 3.0, oz - 3.0))
        for sz in (1.0, -1.0):
            pc['brass'].append(boxr(sx * (fx - 5.0), sx * (fx + 0.6), y + T + 1.0, y + T + 2.6, sz * (fz - 5.0), sz * (fz + 0.6)))
    pc['graphite'].append(boxr(-ox, ox, y - 0.5, y + T + 1.6, oz, fz))
    pc['graphite'].append(boxr(-ox, ox, y - 0.5, y + T + 1.6, -fz, -oz))
    for sx in (1.0, -1.0):
        pc['amber'].append(boxr(sx * 2.0, sx * 8.0, y + T + 1.6, y + T + 1.9, oz + 1.6, oz + 2.4))
    pc['amber'].append(boxr(-3.0, 3.0, y + T + 1.6, y + T + 1.9, -oz - 2.4, -oz - 1.6))
    # 外枠の両脇の黒鉛の柱（絵：扉の左右の縦の帯。上の縁から船底の近くまで）と、上の真鍮の横木
    for sx in (1.0, -1.0):
        pc['graphite'].append(boxr(sx * (fx + 0.5), sx * (fx + 6.5), y - 0.3, y + T + 1.2, zbt + 2.0, top))
        pc['brass'].append(boxr(sx * (fx + 2.0), sx * (fx + 5.0), y + T + 1.2, y + T + 1.6, zbt + 4.0, top - 2.0))
        pc['brass'].append(boxr(sx * (fx + 0.2), sx * (fx + 6.8), y + T - 0.2, y + T + 1.5, fz + 1.0, fz + 2.6))
    pc['brass'].append(boxr(-fx - 2.0, fx + 2.0, y + T - 0.2, y + T + 2.2, fz + 0.6, fz + 2.2))
    # 開口の奥（黒鉛の芯の面より少し奥の暗い壁）
    pc['dark'].append(boxr(-ox, ox, y - 3.0, y - 2.0, -oz, oz))
    # 船尾の上：禁足扉の機械の箱、両脇の塔
    zr = z_top(186.0)
    pc['graphite'].append(boxr(-22, 22, 176, 192, zr - 1.0, zr + 9.0))
    pc['brass'].append(boxr(-23, 23, 175.5, 192.5, zr + 9.0, zr + 10.0))
    for x in (-12.0, 12.0):
        pc['amber'].append(boxr(x - 6, x + 6, 175.3, 175.9, zr + 3.0, zr + 3.8))
    for sx in (1.0, -1.0):
        x = sx * 30.0 * half_w(182.0) / HULL_HW
        pc['graphite'].append(boxr(x - 3.0, x + 3.0, 178, 186, zr - 1.0, zr + 16.0))
        pc['brass'].append(K.lathe((x, 182, zr + 16.0), (x, 182, zr + 21.0), [(0, 2.6), (1, 0.2)], 8))


def frame_x(y, z):
    """梁の外の面の x（帯の下 hw-2.5 → 船底 hw-9 の斜面。奥の閉じた芯は hw-4〜16 で、その 3〜7 m 手前）"""
    hw, zb, zbt = half_w(y), z_band(y), z_bot(y)
    t = (zb - z) / max(zb - zbt, 1e-3)
    return max(hw - 2.5 - 6.5 * t, 0.3 * hw + 2.0)


def core_x(y, z):
    """閉じた芯の帯の下の面の x（core_poly の (hw-8, zb-1) → (hw-16, zbt)）"""
    hw, zb, zbt = half_w(y), z_band(y), z_bot(y)
    t = min(max((zb - 1.0 - z) / max(zb - 1.0 - zbt, 1e-3), 0.0), 1.0)
    return max(hw - 8.0 - 8.0 * t, 0.25 * hw)


# 梁の区切り（脚の取付の前後 14 m は肩の受けのために切る）
FRAME_SPANS = [(-186.0, -154.0), (-126.0, -62.0), (-34.0, 34.0), (62.0, 126.0), (154.0, 188.0)]


def build_frame(pc):
    """舷の帯の下の黒鉛の梁（トラス）の外の面：上・中・下の弦材、12 m ごとの柱、上下 2 段の X の筋交い、柱から奥の芯へ戻る短い材、
    継ぎ目の真鍮の留め板、琥珀の灯。奥の閉じた芯（dark）が 3〜7 m 奥に見え、側面と正面・背面が骨組みに見える（絵の帯の下の黒い骨組み）。
    ほかに船底の突起、真ん中の竜骨と真鍮の管、肩の受け"""
    for sx in (1.0, -1.0):
        nrm = V3([sx * 1.0, 0.0, 0.0])
        for y0, y1 in FRAME_SPANS:
            zf_top = lambda y: z_band(y) - 1.4                      # noqa: E731
            zf_bot = lambda y: z_bot(y) + 1.8                       # noqa: E731
            zf_mid = lambda y: 0.5 * (zf_top(y) + zf_bot(y))        # noqa: E731
            for zf, hh in ((zf_top, 1.4), (zf_mid, 1.1), (zf_bot, 1.4)):
                secs = []
                for y in stations(y0, y1, 6.0):
                    zc = zf(y)
                    xc = frame_x(y, zc)
                    secs.append([(sx * (xc + dx), y, zc + dz) for dx, dz in ((-1.3, -hh), (0.3, -hh), (0.3, hh), (-1.3, hh))])
                pc['graphite'].append(loft(secs))
            # 柱（12 m ごと）・X の筋交い（上下 2 段）・奥の芯へ戻る材・留め板
            posts = list(np.arange(y0 + 4.0, y1 - 1.0, 12.0))
            pts = {}
            for y in posts:
                for key, zf in (('t', zf_top), ('m', zf_mid), ('b', zf_bot)):
                    zc = zf(y)
                    pts[(y, key)] = V3([sx * (frame_x(y, zc) - 0.4), y, zc])
                pc['graphite'].append(bar(pts[(y, 't')], pts[(y, 'b')], 1.7, 1.7, up=tuple(nrm)))
                for key in ('t', 'm', 'b'):
                    p = pts[(y, key)]
                    zc = float(p[2])
                    pin = V3([sx * (core_x(y, zc) + 0.3), y, zc])
                    pc['graphite'].append(bar(p, pin, 1.1, 1.1, up=(0, 0, 1)))
                pm = pts[(y, 'm')]
                pc['brass'].append(boxr(pm[0] - 0.4 * sx, pm[0] + 0.9 * sx, y - 1.1, y + 1.1, pm[2] - 1.1, pm[2] + 1.1))
            for i in range(len(posts) - 1):
                ya, yb = posts[i], posts[i + 1]
                for k0, k1 in (('t', 'm'), ('m', 'b')):
                    pc['graphite'].append(bar(pts[(ya, k0)], pts[(yb, k1)], 1.0, 1.0, up=tuple(nrm)))
                    pc['graphite'].append(bar(pts[(ya, k1)], pts[(yb, k0)], 1.0, 1.0, up=tuple(nrm)))
            # 琥珀の灯（上の弦材の外の面）
            for y in np.arange(y0 + 10.0, y1 - 4.0, 24.0):
                zc = zf_top(y)
                xc = frame_x(y, zc)
                pc['amber'].append(boxr(sx * (xc + 0.3), sx * (xc + 0.7), y - 1.6, y + 1.6, zc - 0.5, zc + 0.5))
        # 船底の突起（下へ尖る）
        for y in np.arange(-146.0, 190.0, 18.0):
            if any(abs(y - ym) < 12.0 for ym in MOUNTS.values()):
                continue
            zb_ = z_bot(y)
            x = sx * (half_w(y) - 18.0)
            pc['graphite'].append(K.lathe((x, y, zb_ + 0.5), (x, y, zb_ - 6.5), [(0, 2.2), (0.35, 2.2), (0.55, 1.5), (1, 0.35)], 6))
        # 肩の受け（芯から外へ出る黒鉛の筒）
        for ym in MOUNTS.values():
            x_in = core_x(ym, SHOULDER_Z) - 3.0
            pc['graphite'].append(K.lathe((sx * x_in, ym, SHOULDER_Z), (sx * (XL - 5.5), ym, SHOULDER_Z),
                                          [(0, 13.5), (0.85, 13.5), (0.92, 12.6), (1, 12.6)], 24))
            # 受けの上で帯の下の縁を支える腕（帯の下の板を外した所）
            zb_ = z_band(ym)
            for dy in (-12.5, 12.5):
                pa = V3([sx * (half_w(ym) - 2.0), ym + dy, z_knee_line(ym) - 0.5])
                pb = V3([sx * (frame_x(ym, zb_ - 8.0) - 0.5), ym + dy * 0.75, zb_ - 8.0])
                pc['graphite'].append(bar(pa, pb, 3.0, 3.0, up=(sx, 0, 0)))
    # 船首の下の斜めの面（あご）の黒鉛の板 3 列：前から見て、庇の下が穴に見えないように
    for y0, y1 in ((-197.0, -175.0), (-174.0, -152.0)):
        for f0, f1 in ((-1.0, -0.36), (-0.32, 0.32), (0.36, 1.0)):
            def chin(y, f0=f0, f1=f1):
                w = 0.62 * half_w(y)
                zb = z_bot(y) - 1.0
                return [(f1 * w, zb), (f0 * w, zb)]
            pc['graphite'].append(plate(y0, y1, chin, PLATE_T, step=3.0))
    # 真ん中の竜骨と真鍮の管
    secs = []
    for y in stations(-150.0, 172.0, 8.0):
        zb_ = z_bot(y)
        secs.append([(-8.0, y, zb_ - 4.5), (8.0, y, zb_ - 4.5), (9.0, y, zb_ + 0.5), (-9.0, y, zb_ + 0.5)])
    pc['graphite'].append(loft(secs))
    for sx in (1.0, -1.0):
        pc['brass'].append(K.lathe((sx * 11.0, -140.0, -54.0), (sx * 11.0, 165.0, -54.0), [(0, 1.3), (1, 1.3)], 10))


def landing_x():
    """踊り場の x の範囲（内 → 外。LIFT_SIDE の舷）。内の端は縁の内の 2.5 m 奥（町の下の段の東の壁の下まで。部屋から歩いて出る）"""
    hw = half_w(LIFT_Y)
    return hw - RIM_W - 2.5, hw + 16.0


def build_lift(pc):
    """リフトの踊り場（船体の部品。LIFT_SIDE の舷 = 左舷）：上の面が背の面の LANDING_TOP 上（下の段の床と同じ）の台・真鍮の手すり・
    布の日よけ・琥珀の灯。ガイドとかごは別の部品。下の段の部屋（ch1.lower）では、この台が歩ける展望の台（手すりの外に脚が見える）"""
    S = LIFT_SIDE
    hw = half_w(LIFT_Y)
    xi, xo = landing_x()
    L = LANDING_TOP
    y0, y1 = LIFT_Y - 9.0, LIFT_Y + 9.0
    X = lambda a, b: (S * a, S * b)                     # noqa: E731
    pc['graphite'].append(boxr(*X(xi, xo), y0, y1, L - 3.4, L - 0.6))
    pc['ivory'].append(boxr(*X(xi + 0.4, xo - 0.6), y0 + 0.6, y1 - 0.6, L - 0.6, L))
    # かごの通る口のふた（踊り場の外寄り）：真鍮の枠と黒鉛の格子（上の面から 3 cm。歩ける。前は黒鉛の板 1 枚で、大きな黒い敷物に見えた）
    xa, xb, ya, yb = hw + 6.2, hw + 14.2, LIFT_Y - 5.6, LIFT_Y + 5.6
    for x0, x1, y_0, y_1 in ((xa, xb, ya, ya + 0.5), (xa, xb, yb - 0.5, yb), (xa, xa + 0.5, ya, yb), (xb - 0.5, xb, ya, yb)):
        pc['brass'].append(boxr(*X(x0, x1), y_0, y_1, L - 0.2, L + 0.03))
    for x in np.arange(xa + 1.3, xb - 0.9, 1.2):
        pc['graphite'].append(boxr(*X(x - 0.2, x + 0.2), ya + 0.5, yb - 0.5, L - 0.2, L + 0.02))
    # 手すり（外の縁と前後の縁、高さ 1.45 m。前後の縁は内の端から：下の段の部屋では、この線に当たり判定の柵がある）
    for x in np.arange(xi + 0.6, xo - 0.8, 3.0):
        for y in (y0 + 0.5, y1 - 0.5):
            pc['brass'].append(boxr(*X(x - 0.15, x + 0.15), y - 0.15, y + 0.15, L, L + 1.3))
    for y in np.arange(y0 + 0.5, y1, 2.9):
        pc['brass'].append(boxr(*X(xo - 0.65, xo - 0.35), y - 0.15, y + 0.15, L, L + 1.3))
    pc['brass'].append(boxr(*X(xo - 0.7, xo - 0.3), y0 + 0.3, y1 - 0.3, L + 1.2, L + 1.45))
    for y in (y0 + 0.5, y1 - 0.5):
        pc['brass'].append(boxr(*X(xi + 0.4, xo - 0.3), y - 0.2, y + 0.2, L + 1.2, L + 1.45))
        pc['brass'].append(boxr(*X(xi + 0.4, xo - 0.3), y - 0.12, y + 0.12, L + 0.55, L + 0.7))
    # 布の日よけ（縁の側に柱 2 本、外へ下がる。柱は前後の手すりに付ける：柱と手すりの間に体が挟まらない）
    for y in (y0 + 0.9, y1 - 0.9):
        pc['graphite'].append(boxr(*X(hw - 2.0 - 0.3, hw - 2.0 + 0.3), y - 0.3, y + 0.3, L, L + 7.0))
        pc['graphite'].append(boxr(*X(hw + 7.5 - 0.3, hw + 7.5 + 0.3), y - 0.3, y + 0.3, L, L + 5.2))
    v = V3([(S * (hw - 2.6), y0 + 0.8, L + 7.2), (S * (hw + 8.4), y0 + 0.8, L + 5.0), (S * (hw + 8.4), y1 - 0.8, L + 5.0),
            (S * (hw - 2.6), y1 - 0.8, L + 7.2)])
    vv = np.concatenate([v, v + V3([0, 0, 0.35])])
    ff = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    pc['cloth'].append((vv, K.orient(vv, ff)))
    # 舷の上から下がる布の垂れ幕 2 枚（人が後から足した物）
    for yb in (LIFT_Y - 16.0, LIFT_Y + 16.0):
        pc['cloth'].append(boxr(*X(hw + 0.3, hw + 0.6), yb - 2.5, yb + 2.5, -12.0, 2.0))
        pc['brass'].append(boxr(*X(hw + 0.2, hw + 0.9), yb - 3.0, yb + 3.0, 1.6, 2.4))
    for y in (y0 + 0.4, y1 - 0.4):
        pc['amber'].append(boxr(*X(xo - 0.8, xo - 0.2), y - 0.4, y + 0.4, L - 2.6, L - 1.4))


# ---------------------------------------------------------------- 部品

PARTS: list[dict] = []


def add(name, parent, pivot, axis, pieces, kind='rot'):
    """pieces = {材質: [(頂点, 面)...]}。kind：rot（回転）か slide（ローカル +X へ平行移動）"""
    pcs = [(m, M(*lst)) for m, lst in pieces.items() if lst]
    PARTS.append(dict(name=name, parent=parent, pivot=V3(pivot, float), axis=K.unit(axis), pieces=pcs, kind=kind))


def pieces():
    return {k: [] for k in MAT_COLORS}


def build_body():
    pc = pieces()
    build_hull(pc)
    build_frame(pc)
    build_lift(pc)
    add('body', None, (0, 0, 0), (1, 0, 0), pc)


def build_door():
    """禁足扉：縦長の 2 枚の扉（白磁の板・黒鉛の縦の溝）と真ん中の真鍮の桟。外枠は船体側（build_stern）"""
    pc = pieces()
    y = 200.0
    ox, oz = DOOR_W / 2, DOOR_H / 2
    pc['graphite'].append(boxr(-ox, ox, y - 0.4, y + 0.4, -oz, oz))
    for sx in (1.0, -1.0):
        # 扉 1 枚 = 縦の板 2 枚（間に黒鉛の溝）
        for x0, x1 in ((0.9, ox / 2 - 0.3), (ox / 2 + 0.3, ox - 0.5)):
            pc['ivory'].append(boxr(sx * x0, sx * x1, y + 0.4, y + 1.6, -oz + 0.6, oz - 0.6))
        pc['brass'].append(boxr(sx * (ox / 2 - 0.9), sx * (ox / 2 + 0.9), y + 0.4, y + 1.9, -oz + 3.0, -oz + 4.6))   # 取っ手の受け
    pc['brass'].append(boxr(-0.9, 0.9, y + 0.4, y + 2.3, -oz, oz))
    for zz in (-oz + 0.3, oz - 0.3):
        pc['brass'].append(boxr(-ox + 0.3, ox - 0.3, y + 0.4, y + 2.0, zz - 0.5, zz + 0.5))
    add('door', 'body', (0, y + 1.0, 0), (0, 0, -1), pc, kind='slide')


def build_lift_parts():
    S = LIFT_SIDE
    hw = half_w(LIFT_Y)
    L = LANDING_TOP
    xc = S * (hw + 10.2)            # かごの中心の x（踊り場の口の真ん中）
    pc = pieces()
    for dx in (-4.6, 4.6):
        for dy in (-6.2, 6.2):
            pc['graphite'].append(boxr(xc + dx - 0.8, xc + dx + 0.8, LIFT_Y + dy - 0.8, LIFT_Y + dy + 0.8, -56.0, L - 3.4))
            pc['brass'].append(K.lathe((xc + dx - 1.1, LIFT_Y + dy, L - 5.0), (xc + dx + 1.1, LIFT_Y + dy, L - 5.0), [(0, 1.3), (1, 1.3)], 10))
    for dy in (-6.2, 6.2):
        pc['graphite'].append(boxr(xc - 5.4, xc + 5.4, LIFT_Y + dy - 0.7, LIFT_Y + dy + 0.7, -57.2, -55.4))
    for dx in (-4.6, 4.6):
        pc['graphite'].append(boxr(xc + dx - 0.7, xc + dx + 0.7, LIFT_Y - 7.0, LIFT_Y + 7.0, -57.2, -55.4))
    add('lift_guide', 'body', (xc, LIFT_Y, L - 3.4), (0, 0, -1), pc, kind='slide')
    pc = pieces()
    z0, z1 = L - 15.4, L - 3.6
    cx0, cx1, cy0, cy1 = xc - 4.0, xc + 4.0, LIFT_Y - 5.0, LIFT_Y + 5.0
    pc['graphite'].append(boxr(cx0, cx1, cy0, cy1, z0, z0 + 1.0))
    pc['graphite'].append(boxr(cx0, cx1, cy0, cy1, z1 - 1.0, z1))
    for x in (cx0 + 0.4, cx1 - 0.4):
        for yy in (cy0 + 0.4, cy1 - 0.4):
            pc['graphite'].append(boxr(x - 0.4, x + 0.4, yy - 0.4, yy + 0.4, z0 + 1.0, z1 - 1.0))
    xin = xc - S * 4.0               # 船体の側の面
    pc['ivory'].append(boxr(xin + S * 0.1, xin + S * 0.6, cy0 + 0.8, cy1 - 0.8, z0 + 1.0, z1 - 1.0))     # 船体の側の板
    pc['ivory'].append(boxr(cx0 + 0.8, cx1 - 0.8, cy1 - 0.6, cy1 - 0.1, z0 + 1.0, z0 + 5.5))     # 端の腰板
    xout = xc + S * 4.0
    for yy in np.linspace(cy0 + 1.6, cy1 - 1.6, 5):
        pc['graphite'].append(boxr(xout - S * 0.15, xout - S * 0.45, yy - 0.15, yy + 0.15, z0 + 1.0, z1 - 1.0))   # 外の面の格子
    pc['brass'].append(boxr(cx0 - 0.2, cx1 + 0.2, cy0 - 0.2, cy1 + 0.2, z0 + 0.8, z0 + 1.3))
    pc['amber'].append(boxr(xout + S * 0.25, xout - S * 0.1, LIFT_Y - 1.5, LIFT_Y + 1.5, z1 - 2.0, z1 - 1.4))
    add('lift_cage', 'lift_guide', (xc, LIFT_Y, z1), (0, 0, -1), pc, kind='slide')


def leg_frame(y_m, knee_dir):
    """脚の関節の位置（左舷）。knee_dir：+1 = 膝が船尾（+Y）へ、-1 = 船首へ。横から見た長さ（y・z）が太もも 48 m・すね 34 m"""
    S = V3([XL, y_m, SHOULDER_Z])
    A = V3([XL + SPLAY_A, y_m, ANKLE_Z])
    D = abs(A[2] - S[2])
    ca = (L_THIGH ** 2 + D ** 2 - L_SHIN ** 2) / (2 * L_THIGH * D)
    al = math.acos(ca)
    Kp = V3([XL + SPLAY_K, y_m + knee_dir * L_THIGH * math.sin(al), SHOULDER_Z - L_THIGH * math.cos(al)])
    return S, Kp, A


def seg_axes(p0, p1, toward):
    """節の向き u（p0 → p1、外へ開いた分の x も含む）、u に直角で YZ 面の中の v（toward の側）、横の向き w = u × v（外向き）"""
    u = (p1 - p0) / np.linalg.norm(p1 - p0)
    v = V3([0.0, -u[2], u[1]])
    v = v / np.linalg.norm(v)
    if v @ (toward - p0) < 0:
        v = -v
    w = np.cross(u, v)
    if w[0] < 0:
        w = -w
    return u, v, w


def build_leg(tag, y_m, knee_dir):
    """左舷の脚 1 本（tag = 'l1' など）。右舷・後ろの 2 対は鏡写し。
    太さは絵の脚（板 2 枚と黒鉛の芯、真鍮の円板・ピストン）を肩 85 m に合わせた：太ももの板 15.5 m、すねの板 13.5 m、肩の円板の半径 11 m"""
    S, Kp, A = leg_frame(y_m, knee_dir)
    xk, xa = Kp[0], A[0]
    # 肩の横振り（黒鉛の首輪）
    pc = pieces()
    pc['graphite'].append(K.lathe((XL - 7.0, y_m, SHOULDER_Z), (XL - 2.6, y_m, SHOULDER_Z), [(0, 12.4), (0.8, 13.0), (1, 12.4)], 24))
    pc['amber'].append(boxr(XL - 5.6, XL - 3.8, y_m - 1.4, y_m + 1.4, SHOULDER_Z + 12.6, SHOULDER_Z + 13.3))
    add(f'leg_{tag}_roll', 'body', S, (0, -1, 0), pc)
    # 肩のピッチ：真鍮の円板・太もも（芯・板 2 枚・ピストン）
    pc = pieces()
    pc['graphite'].append(K.lathe((XL - 3.2, y_m, SHOULDER_Z), (XL + 3.2, y_m, SHOULDER_Z), [(0, 11.6), (0.8, 12.2), (1, 11.6)], 24))
    pc['brass'].append(disc(XL + 3.0, XL + 4.8, y_m, SHOULDER_Z, 11.0))
    pc['brass'].append(disc(XL - 3.0, XL - 4.4, y_m, SHOULDER_Z, 8.8, segs=16))
    u, v, w = seg_axes(S, Kp, A)
    L1 = float(np.linalg.norm(Kp - S))
    pc['graphite'].append(slab(S + u * (L1 * 0.53), u, v, L1 - 7.0, 9.0, 7.0, 1.8, wdir=w))
    for sx in (1.0, -1.0):
        pc['ivory'].append(slab(S + u * 26.0 + w * (sx * 4.8), u, v, 27.0, 15.5, 2.6, 3.0, wdir=w))
    p0, p1 = S + u * 8.0 + v * 9.2, S + u * (L1 - 8.0) + v * 9.2
    pc['brass'].append(K.lathe(p0, p1, [(0, 1.7), (1, 1.7)], 12))
    pc['graphite'].append(K.lathe(p0 - u * 0.5, p0 + u * 15.0, [(0, 2.6), (0.92, 2.6), (1, 2.0)], 12))
    pc['graphite'].append(bar(S + u * 7.0 + v * 4.5, p0 - u * 0.2, 2.4, 2.4, up=tuple(w)))
    pc['graphite'].append(bar(Kp - u * 7.0 + v * 4.0, p1 + u * 0.2, 2.4, 2.4, up=tuple(w)))
    q = S + u * 11.0 + w * 6.1   # 太ももの板の上の小さな琥珀の灯
    pc['amber'].append(slab(q + w * 0.15 - v * 4.0, u, v, 1.2, 1.4, 0.3, 0.2, wdir=w))
    add(f'leg_{tag}_shoulder', f'leg_{tag}_roll', S, (1, 0, 0), pc)
    # 膝：円板（両側）・膝頭の真鍮の筒・すね
    pc = pieces()
    pc['graphite'].append(K.lathe((xk - 7.2, Kp[1], Kp[2]), (xk + 7.2, Kp[1], Kp[2]), [(0, 8.4), (0.1, 9.4), (0.9, 9.4), (1, 8.4)], 24))
    pc['brass'].append(disc(xk + 7.0, xk + 8.6, Kp[1], Kp[2], 7.4, segs=22))
    pc['brass'].append(disc(xk - 7.0, xk - 8.6, Kp[1], Kp[2], 7.4, segs=22))
    pt = Kp + V3([0, knee_dir, 0]) * 8.4
    pc['brass'].append(K.lathe((xk - 5.6, pt[1], pt[2] + 0.5), (xk + 5.6, pt[1], pt[2] + 0.5), [(0, 2.9), (0.12, 3.4), (0.88, 3.4), (1, 2.9)], 14))
    u, v, w = seg_axes(Kp, A, S)
    L2 = float(np.linalg.norm(A - Kp))
    pc['graphite'].append(slab(Kp + u * (L2 * 0.5), u, v, L2 - 5.0, 7.6, 6.4, 1.4, wdir=w))
    for sx in (1.0, -1.0):
        pc['ivory'].append(slab(Kp + u * 18.5 + w * (sx * 4.6), u, v, 17.0, 13.5, 2.4, 2.6, wdir=w))
    p0, p1 = Kp + u * 7.0 - v * 7.6, Kp + u * (L2 - 7.0) - v * 7.6
    pc['brass'].append(K.lathe(p0, p1, [(0, 1.4), (1, 1.4)], 10))
    pc['graphite'].append(K.lathe(p1 - u * 9.0, p1 + u * 0.4, [(0, 2.1), (1, 2.1)], 10))
    pc['graphite'].append(bar(Kp + u * 6.0 - v * 3.6, p0 - u * 0.2, 2.0, 2.0, up=tuple(w)))
    pc['amber'].append(boxr(xk + 7.3, xk + 7.6, Kp[1] - 0.8, Kp[1] + 0.8, Kp[2] - 8.4, Kp[2] - 7.4))
    add(f'leg_{tag}_knee', f'leg_{tag}_shoulder', Kp, (1, 0, 0), pc)
    # 足首と足（足の裏 38 × 24 m）
    pc = pieces()
    ya, za = A[1], A[2]
    g = GROUND
    pc['graphite'].append(K.lathe((xa - 6.2, ya, za), (xa + 6.2, ya, za), [(0, 5.4), (0.12, 6.2), (0.88, 6.2), (1, 5.4)], 20))
    pc['brass'].append(disc(xa + 6.0, xa + 7.3, ya, za, 4.8, segs=18))
    pc['brass'].append(disc(xa - 6.0, xa - 7.3, ya, za, 4.8, segs=18))
    hl, hw_ = FOOT_L / 2, FOOT_W / 2
    ky, kx = FOOT_L / 38.0, FOOT_W / 24.0          # 最初の 38 × 24 m の足からの倍率（中の台・踏み板の内の端・灯・支えの位置）
    pc['graphite'].append(boxr(xa - hw_ + 0.5, xa + hw_ - 0.5, ya - hl + 1.0, ya + hl - 1.0, g, g + 1.6))
    pc['graphite'].append(boxr(xa - 8.5 * kx, xa + 8.5 * kx, ya - 5.5 * ky, ya + 5.5 * ky, g + 1.6, za - 1.5))
    for sy in (1.0, -1.0):
        # 踏み板（白磁）：外の端の上を斜めに落とす
        yi, yo = ya + sy * 6.0 * ky, ya + sy * (hl - 2.4)
        prof = [(yi, g + 1.6), (yo, g + 1.6), (yo, g + 4.4), (yo - sy * 3.6 * ky, g + 7.6), (yi, g + 7.6)]
        vs = [(x, yy, zz) for x in (xa - hw_ + 1.0, xa + hw_ - 1.0) for yy, zz in prof]
        n = len(prof)
        ff = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)] + [list(range(n))[::-1], list(range(n, 2 * n))]
        vs = V3(vs, float)
        pc['ivory'].append((vs, K.orient(vs, ff)))
        # 真鍮の縁金具（端の帯と四隅）
        pc['brass'].append(boxr(xa - hw_ + 0.4, xa + hw_ - 0.4, ya + sy * (hl - 2.4), ya + sy * hl, g, g + 3.6))
        for sx in (1.0, -1.0):
            pc['brass'].append(boxr(xa + sx * (hw_ - 1.6), xa + sx * hw_, ya + sy * (hl - 4.0), ya + sy * (hl - 0.2), g, g + 6.2))
        pc['amber'].append(boxr(xa - 3.5 * kx, xa + 3.5 * kx, ya + sy * 5.5 * ky, ya + sy * 5.9 * ky, g + 4.2, g + 5.2))
        # 足首の台から踏み板へ下りる黒鉛の支え
        pc['graphite'].append(bar(V3([xa, ya + sy * 4.5 * ky, za - 2.0]), V3([xa, ya + sy * 8.0 * ky, g + 7.4]), 6.0 * kx, 2.4, up=(0, sy, 0)))
    add(f'leg_{tag}_ankle', f'leg_{tag}_knee', A, (1, 0, 0), pc)


def mirror_part(part, name, parent, sx, sy):
    """部品を x（sx = -1）・y（sy = -1。y = 0 で前後）に鏡写し。回転の軸は世界の向きのまま（ピッチは 8 本とも +X、横振りは船首）"""
    def T(p):
        p = V3(p, float).copy()
        p[..., 0] *= sx
        p[..., 1] *= sy
        return p
    pcs = [(m, (T(v), K.orient(T(v), f))) for m, (v, f) in part['pieces']]
    return dict(name=name, parent=parent, pivot=T(part['pivot']), axis=part['axis'].copy(), pieces=pcs, kind=part['kind'])


def build_legs():
    build_leg('l1', MOUNTS[1], +1.0)
    build_leg('l2', MOUNTS[2], +1.0)
    base = {p['name']: p for p in PARTS if p['name'].startswith('leg_')}
    names = ('roll', 'shoulder', 'knee', 'ankle')
    for src, dst, sx, sy in (('l1', 'l4', 1, -1), ('l2', 'l3', 1, -1), ('l1', 'r1', -1, 1), ('l2', 'r2', -1, 1),
                             ('l1', 'r4', -1, -1), ('l2', 'r3', -1, -1)):
        for i, k in enumerate(names):
            par = 'body' if i == 0 else f'leg_{dst}_{names[i - 1]}'
            PARTS.append(mirror_part(base[f'leg_{src}_{k}'], f'leg_{dst}_{k}', par, sx, sy))


# ---------------------------------------------------------------- Blender

def to_gd(p):
    """Blender (x, y, z) → glTF / Godot (x, z, -y)"""
    return [round(float(p[0]), 3), round(float(p[2]), 3), round(float(-p[1]), 3)]


def make_materials():
    import bpy
    mats = {}
    for key, (hexc, rough, metal) in MAT_COLORS.items():
        m = bpy.data.materials.new(key)
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        col = B.srgb_to_linear(hexc)
        b.inputs['Base Color'].default_value = (*col, 1)
        b.inputs['Roughness'].default_value = rough
        b.inputs['Metallic'].default_value = metal
        if key == 'amber':
            b.inputs['Emission Color'].default_value = (*col, 1)
            b.inputs['Emission Strength'].default_value = 3.0
        m.diffuse_color = (*col, 1)
        mats[key] = m
    return mats


def metre_uv(ob):
    """UV = 面の向きの平面投影（部品の原点から m）。町のキットと同じ（汚れの層の uv_m がそのまま使える）"""
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    co = np.array([v.co for v in me.vertices]).reshape(-1, 3)
    for pl in me.polygons:
        ax = int(np.argmax(np.abs(np.array(pl.normal))))
        for li in pl.loop_indices:
            c = co[me.loops[li].vertex_index]
            uv.data[li].uv = {0: (c[1], c[2]), 1: (c[0], c[2]), 2: (c[0], c[1])}[ax]


def build(export=True) -> dict:
    import bpy
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    PARTS.clear()
    build_body()
    build_door()
    build_lift_parts()
    build_legs()
    mats = make_materials()
    objs, meshes = {}, []
    tri_by_mat = {k: 0 for k in MAT_COLORS}
    tri_by_group = {}
    for p in PARTS:
        rot = B.axis_matrix(p['axis'])
        piv = p['pivot'] * 100.0
        first = None
        for i, (mk, (v, f)) in enumerate(p['pieces']):
            nm = p['name'] if i == 0 else f"{p['name']}_{mk}"
            ob = B.new_object(nm, v * 100.0, f, mats[mk], piv, rot)
            metre_uv(ob)
            nt = sum(len(pl.vertices) - 2 for pl in ob.data.polygons)
            tri_by_mat[mk] += nt
            grp = 'legs' if p['name'].startswith('leg_') else ('lift' if p['name'].startswith('lift') else p['name'])
            tri_by_group[grp] = tri_by_group.get(grp, 0) + nt
            meshes.append(ob)
            if first is None:
                first = ob
                objs[p['name']] = ob
            else:
                mw = ob.matrix_world.copy()
                ob.parent = first
                ob.matrix_world = mw
    root = bpy.data.objects.new('ordo', None)
    bpy.context.scene.collection.objects.link(root)
    for p in PARTS:
        ob = objs[p['name']]
        mw = ob.matrix_world.copy()
        ob.parent = objs[p['parent']] if p['parent'] else root
        ob.matrix_world = mw
    B.smooth_by_angle(meshes, 38.0)
    tri = sum(tri_by_mat.values())
    if not export:
        return {'triangles': tri}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, export_apply=False,
                              export_animations=False, use_selection=True)
    # 関節の位置（Godot の座標）
    deck_x = half_w(0.0) - RIM_W - 1.0      # 背の板の外の列の外の縁（その外は縁の白磁の角材）
    rig = {'ground_y': GROUND, 'deck': {'y': 0.0, 'x': [-deck_x, deck_x], 'z': [-118.0, 100.0]},
           'rim': {'x': [half_w(0.0) - RIM_W, half_w(0.0)], 'top_y': RIM_H}, 'hull_half_width': half_w(0.0),
           'lift_landing': {'x': [LIFT_SIDE * landing_x()[0], LIFT_SIDE * landing_x()[1]], 'z': [-(LIFT_Y + 9.0), -(LIFT_Y - 9.0)],
                            'top_y': LANDING_TOP},
           'legs': {}}
    for p in PARTS:
        if p['name'].endswith('_shoulder') or p['name'].endswith('_knee') or p['name'].endswith('_ankle'):
            rig['legs'][p['name']] = to_gd(p['pivot'])
    rig['thigh_m'], rig['shin_m'] = L_THIGH, L_SHIN
    rig['lift'] = {'landing_top_y': LANDING_TOP, 'center': to_gd((LIFT_SIDE * (half_w(LIFT_Y) + 10.2), LIFT_Y, LANDING_TOP - 9.5))}
    rig['door'] = {'center': to_gd((0, 201.0, 0)), 'opening_m': [DOOR_W, DOOR_H]}
    os.makedirs(WORK, exist_ok=True)
    info = {'triangles': tri, 'by_material': tri_by_mat, 'by_group': tri_by_group, 'parts': len(PARTS), 'objects': len(meshes),
            'seconds': round(time.time() - t0, 1)}
    rig['info'] = info
    with open(os.path.join(WORK, 'rig.json'), 'w') as fh:
        json.dump(rig, fh, indent=1, ensure_ascii=False)
    log(json.dumps(info, ensure_ascii=False))
    return info


# ---------------------------------------------------------------- 確認（絵と並べた正投影）

TILE_W = 1000
PX_PER_M = 4.5


def fetch_art():
    import subprocess
    os.makedirs(SRC, exist_ok=True)
    for n in ('3d_side_right', '3d_front', '3d_back', '3d_top'):
        p = os.path.join(SRC, f'ordo_{n}.png')
        if not os.path.exists(p):
            r = subprocess.run(['git', 'show', f'{ART_REF}/ordo_{n}.png'], cwd=REPO, capture_output=True)
            if r.returncode == 0:
                with open(p, 'wb') as fh:
                    fh.write(r.stdout)


def render_review(out_dir):
    """絵（名目の 4.5 px/m）と同じ縮尺の正投影を Workbench で撮り、絵と上下に並べる（高さは spec に合わせたので絵より高い）"""
    import bpy
    from mathutils import Matrix, Vector
    from PIL import Image, ImageDraw
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 8
    sc.cycles.use_denoising = False
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = sc.render.resolution_y = 2048
    sc.render.resolution_percentage = 50
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.82, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
    sc.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 2.5
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2048 / PX_PER_M
    cam.data.clip_end = 3000
    sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    # 絵の外接（足の裏の行 1450、中心の列 1024）に合わせる：地面が 1450 行、中心が 1024 列
    zc_img = GROUND + (1450 - 1024) / PX_PER_M
    views = [('side_right', (LIFT_SIDE, 0, 0), (0, 0, 1), V3([0, 0, zc_img])),   # リフトの舷（左舷 +X）から。船首が左（絵と同じ向き）
             ('front', (0, -1, 0), (0, 0, 1), V3([0, 0, zc_img])),
             ('back', (0, 1, 0), (0, 0, 1), V3([0, 0, zc_img])),
             ('top', (0, 0, 1), (0, -1, 0), V3([0, 0, 0]))]
    rows = []
    for name, d, up, ctr in views:
        d = Vector(d).normalized()
        z = d
        x = Vector(up).cross(z).normalized()
        y = z.cross(x)
        rot = Matrix((x, y, z)).transposed()
        if name == 'top':
            rot = Matrix(((0, -1, 0), (1, 0, 0), (0, 0, 1)))     # 真上から、船首が左（絵と同じ）
        cam.matrix_world = Matrix.Translation(Vector(ctr.tolist()) + d * 1200.0) @ rot.to_4x4()
        sun.matrix_world = (rot @ Matrix.Rotation(math.radians(-30), 3, 'X') @ Matrix.Rotation(math.radians(-25), 3, 'Y')).to_4x4()
        rp = os.path.join(out_dir, f'render_{name}.png')
        sc.render.filepath = rp
        bpy.ops.render.render(write_still=True)
        ren = Image.open(rp).convert('RGBA').resize((TILE_W, TILE_W))
        if name == 'side_right' and LIFT_SIDE < 0:
            # 右舷を外から見ると船首が右に来る。絵の側面図は船首が左でリフトが見えるので、並べるために反転
            ren = ren.transpose(Image.FLIP_LEFT_RIGHT)
        art = Image.open(os.path.join(SRC, f'ordo_3d_{name}.png')).convert('RGBA').resize((TILE_W, TILE_W))
        bg = (150, 155, 165, 255)
        row = Image.new('RGBA', (2 * TILE_W, TILE_W), bg)
        row.alpha_composite(art, (0, 0))
        row.alpha_composite(ren, (TILE_W, 0))
        dr = ImageDraw.Draw(row)
        dr.text((8, 8), f'art {name} (4.5 px/m)', fill=(20, 20, 20, 255))
        note = (' / port side (lift side), bow left like the art' if LIFT_SIDE > 0 else ' / starboard, flipped like the art') if name == 'side_right' else ''
        dr.text((TILE_W + 8, 8), f'model {name} (same 4.5 px/m; heights follow spec){note}', fill=(20, 20, 20, 255))
        rows.append(row)
    W = Image.new('RGBA', (2 * TILE_W, TILE_W * len(rows)), (40, 40, 44, 255))
    for k, r in enumerate(rows):
        W.alpha_composite(r, (0, k * TILE_W))
    W = W.convert('RGB')
    W.save(os.path.join(out_dir, 'ordo_compare.jpg'), quality=86)
    small = W.copy()
    small.thumbnail((1600, 1600))
    small.save(os.path.join(out_dir, 'ordo_compare_small.jpg'), quality=86)


def set_hull(hw, rim_w, rim_h):
    """船体の半幅と縁を変える（形の関数はこの値を読む）"""
    global HULL_HW, RIM_W, RIM_H, XL
    HULL_HW, RIM_W, RIM_H = hw, rim_w, rim_h
    XL = HULL_HW + 4.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--review', action='store_true')
    ap.add_argument('--hull-hw', type=float, default=None,
                    help='舷の外の面の半幅（既定 60 m）。試しの形を作るとき（--out と一緒に。結果の文書 3.3）')
    ap.add_argument('--rim', type=str, default=None, help='縁の幅,高さ（m。既定 4,2.5）')
    ap.add_argument('--out', type=str, default=None, help='GLB の書き出し先（既定 godot/assets/models/ordo.glb）')
    args = ap.parse_args()
    global OUT
    if args.out:
        OUT = os.path.abspath(args.out)
    if args.hull_hw is not None or args.rim:
        rw, rh = (float(v) for v in args.rim.split(',')) if args.rim else (RIM_W, RIM_H)
        set_hull(args.hull_hw if args.hull_hw is not None else HULL_HW, rw, rh)
    info = build()
    if args.review:
        fetch_art()
        render_review(os.path.join(WORK, 'review'))
    return info


if __name__ == '__main__':
    main()
