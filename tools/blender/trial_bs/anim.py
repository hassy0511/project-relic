"""haru_bs の 14 の動作（段 2）。スキル集の animation（+ walk-cycle、combat-animation）の手順：
  Reference → Blocking（段の補間）→ Breakdown → Splining（Bezier・自動の取っ手）→ Polish → 輪の確かめ → NLA の帯 → 書き出し

・60 こま/秒（スキル集の既定は 30。「プロジェクトの決まりを確かめる」：ゲームは 60 刻み、haru_r の長さも 60 こまの刻み）。
・その場（in place）。根（root）は動かさない（腰 hips だけが上下・前後に動く）。ゲームは根の動きを使わない。
・攻撃：PlayerView は攻撃の動作を攻撃時間の長さに合わせて流し、当たりは攻撃時間の 25%〜70%。振り抜き（action）を 25% に置く。
  combat-animation の段：予備動作 → 振り抜き（いちばん短い）→ 振り切り → 戻り。
・骨の大きさのキーは打たない（rigging・animation の MUST NOT）。
・姿勢の書き方（スキル集には無い。ここで決めた）：
    (rx, ry, rz)        骨格の軸（X = 本人の左、Y = 後ろ、Z = 上）まわりの回転（度）。親に運ばれた軸で、基準の姿勢から回す
    D(x, y, z)          骨の向き（胴の座標：胸の今の向きに乗った X 左・Y 後ろ・Z 上）。手・腕・刃の向きを決めやすい
    足：('foot', x, y, z, pitch, yaw)   足首の目標（骨格の座標、m）と足の向き（pitch + でつま先が下、yaw + で左へ）。脚は IK（膝の極つき）で解いて焼く
"""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion, Euler

from proportions import J

FPS = 60
FK = ['hips', 'spine', 'chest', 'neck', 'head', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L',
      'shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R']
LEGS = {'L': ('thigh.L', 'shin.L', 'foot.L'), 'R': ('thigh.R', 'shin.R', 'foot.R')}


class D:
    """骨の向き（胴の座標）。up があれば、ref（基準の姿勢での向き）を up に近づけるよう骨の軸のまわりにひねる"""
    def __init__(self, x, y, z, ref=None, up=None):
        self.d = Vector((x, y, z)).normalized()
        self.ref = Vector(ref) if ref else None
        self.up = Vector(up).normalized() if up else None


GUN_UP = (0, -1, 0)    # 基準の姿勢でのスパークの上（銃の +Z。parts_body.gun_frame の式から：A ポーズでは前を向く）


def GUN(x, y, z):
    """右手：銃身をこの向きに、銃の上を上（+Z）へ"""
    return D(x, y, z, ref=GUN_UP, up=(0, 0, 1))


def F(x, y, z, pitch=0.0, yaw=0.0):
    return ('foot', x, y, z, pitch, yaw)


FL0 = Vector(J['foot.L'])
FR0 = Vector(J['foot.R'])

# ---------------------------------------------------------------- 基準になる姿勢
BASE = {
    'hips_loc': (0, 0, -0.012), 'hips': (0, 0, 0), 'spine': (0, 0, 0), 'chest': (0, 0, 0), 'neck': (0, 0, 0), 'head': (0, 0, 0),
    'shoulder.L': (0, 0, 0), 'shoulder.R': (0, 0, 0),
    'upper_arm.L': D(0.30, 0.03, -1), 'forearm.L': D(0.22, -0.30, -1), 'hand.L': (0, 0, 0),
    'upper_arm.R': D(-0.28, 0.05, -1), 'forearm.R': D(-0.12, -0.70, -1), 'hand.R': GUN(-0.05, -0.9, -0.75),
    'foot.L': F(FL0.x, FL0.y, FL0.z, 0, 6), 'foot.R': F(FR0.x, FR0.y, FR0.z, 0, -6),
}

# 構え（攻撃の始まりと終わり）：左足が前、膝を曲げ、胴は少し右へ（光刃の左腕が前）
GUARD = dict(BASE, **{
    'hips_loc': (0, 0.0, -0.06), 'hips': (0, 0, -12), 'spine': (6, 0, 0), 'chest': (4, 0, -6), 'head': (-6, 0, 14),
    'upper_arm.L': D(0.40, -0.45, -0.80), 'forearm.L': D(0.15, -1.0, -0.15),
    'upper_arm.R': D(-0.30, 0.20, -0.95), 'forearm.R': D(-0.20, -0.85, -0.45), 'hand.R': GUN(-0.1, -1.0, -0.35),
    'foot.L': F(0.17, -0.13, 0.105, 0, 12), 'foot.R': F(-0.17, 0.13, 0.105, 0, -28),
})


def P(base, **kw):
    """base に上書きした姿勢。キーの名前の . は _ で書く（upper_arm_L）"""
    out = dict(base)
    for k, v in kw.items():
        k2 = k.replace('_L', '.L').replace('_R', '.R') if (k.endswith('_L') or k.endswith('_R')) else k
        out[k2] = v
    return out


def mirror_pose(p):
    """左右を入れ替えた姿勢（走るの後半の歩）"""
    out = {}
    for k, v in p.items():
        k2 = k[:-2] + ('.R' if k.endswith('.L') else '.L') if (k.endswith('.L') or k.endswith('.R')) else k
        if isinstance(v, D):
            nv = D(-v.d.x, v.d.y, v.d.z)
            if v.ref is not None:
                nv.ref, nv.up = Vector((-v.ref.x, v.ref.y, v.ref.z)), v.up
            v = nv
        elif isinstance(v, tuple) and v and v[0] == 'foot':
            v = F(-v[1], v[2], v[3], v[4], -v[5])
        elif k == 'hips_loc':
            v = (-v[0], v[1], v[2])
        elif isinstance(v, tuple) and len(v) == 3:
            v = (v[0], -v[1], -v[2])
        out[k2] = v
    return out


# ---------------------------------------------------------------- 14 の動作（こまは 60 こま/秒）
def clips():
    C = {}
    # 待機（120 こま、輪）：息（胸の上下）と体重の移し（腰の横）。控えめに（animation：Over-animate idle しない）
    i0 = P(BASE, chest=(2, 0, 0))
    i1 = P(BASE, chest=(-1.5, 0, 0), shoulder_L=(0, -2.5, 0), shoulder_R=(0, 2.5, 0), head=(-1, 0, 0),
           upper_arm_L=D(0.31, 0.02, -1), upper_arm_R=D(-0.29, 0.04, -1))
    i2 = P(BASE, hips_loc=(0.012, 0, -0.02), hips=(0, -2.5, 0), spine=(0, 2.0, 0), chest=(1.5, 1.0, 0), head=(0, -1.5, 2))
    i3 = P(i1, hips_loc=(0.006, 0, -0.016), hips=(0, -1.2, 0), spine=(0, 1.0, 0))
    C['idle'] = dict(length=120, loop=True, keys=[(0, i0), (30, i1), (60, i2), (90, i3), (120, i0)])

    # 走る（40 こま = 2 歩、輪）：walk-cycle の contact → down → passing → up を走りに（flight を入れる）。
    # 左足の接地が 0、右足が 20。腕は脚と逆。体は前へ 12 度
    run_base = P(BASE, hips=(14, 0, 0), spine=(8, 0, 0), chest=(4, 0, 0), neck=(-8, 0, 0), head=(-12, 0, 0))
    # 足：接地は 0〜5 こま（0.083 秒）で 0.58 m 後ろへ。ゲームは走りの速さ / 7 m/s で流すので、地面の速さ 7 m/s と足の速さが合う
    # （その場の走りで足が地面の上を滑らない。0.58 m ÷ 5/60 秒 ≈ 7 m/s）
    lf = {0: (-0.30, 0.115, -15), 2.5: (-0.01, 0.105, 0), 5: (0.28, 0.13, 30), 12: (0.38, 0.38, 55),
          20: (0.06, 0.40, 30), 28: (-0.38, 0.28, -5), 35: (-0.34, 0.16, -15)}
    hz = {0: -0.075, 2.5: -0.090, 5: -0.060, 12: -0.020, 20: -0.075}

    def hz_at(ph):
        ks = sorted(hz)
        for a_, b_ in zip(ks, ks[1:]):
            if a_ <= ph <= b_:
                return hz[a_] + (hz[b_] - hz[a_]) * (ph - a_) / (b_ - a_)
        return hz[0]
    arm_fw = (D(0.15, -0.40, -0.90), D(0.12, -0.85, 0.45))     # 腕が前（上腕・前腕。肘は約 90 度）
    arm_bk = (D(0.15, 0.60, -0.80), D(0.10, -0.45, -0.90))      # 腕が後ろ
    gun_fw, gun_bk = D(-0.10, -0.85, -0.45), D(-0.10, -0.30, -0.95)   # 銃口は前下（走りながら狙わない）
    keys = []

    def foot_at(tbl, f):
        ks = sorted(tbl)
        f %= 40
        for a, b in zip(ks, ks[1:] + [40]):
            if a <= f <= b:
                va, vb = tbl[a], tbl[b if b < 40 else 0]
                t = (f - a) / (b - a)
                return tuple(x + (y - x) * t for x, y in zip(va, vb))

    def lerp_d(a, b, t):
        v = a.d.lerp(b.d, t)
        return D(v.x, v.y, v.z)

    run_keys = sorted({t % 40 for t in lf} | {(t + 20) % 40 for t in lf}) + [40]
    for f in run_keys:
        ph = f % 20
        zz = hz_at(ph)
        yl, zl, pl = foot_at(lf, f)
        yr, zr, pr = foot_at(lf, f + 20)
        # 右腕が前に出ている量（0 で左足の接地＝右腕が前、20 で後ろ）。骨盤のひねりは脚、胸は逆へ
        a = (math.cos(math.pi * f / 20.0) + 1.0) / 2.0
        twist = -10.0 * math.cos(math.pi * f / 20.0)
        uR = lerp_d(arm_bk[0], arm_fw[0], a)
        fR = lerp_d(arm_bk[1], arm_fw[1], a)
        uL = lerp_d(arm_bk[0], arm_fw[0], 1.0 - a)
        fL = lerp_d(arm_bk[1], arm_fw[1], 1.0 - a)
        uR, fR = D(-uR.d.x, uR.d.y, uR.d.z), D(-fR.d.x, fR.d.y, fR.d.z)
        pose = P(run_base, hips_loc=(0, 0, zz), hips=(14, 0, twist * 0.8), chest=(4, 0, -twist * 1.2), head=(-12, 0, twist * 0.4),
                 upper_arm_L=uL, forearm_L=fL, upper_arm_R=uR, forearm_R=fR,
                 hand_R=GUN(*lerp_d(gun_bk, gun_fw, a).d),
                 foot_L=F(0.135, yl, zl, pl, 4), foot_R=F(-0.135, yr, zr, pr, -4))
        keys.append((f, pose))
    C['run'] = dict(length=40, loop=True, keys=keys)

    # 落ちる（40、輪）：腕を外へ上げ、脚は下がって片膝が曲がる。ゆるい揺れ
    fa = P(BASE, hips_loc=(0, 0, 0.0), chest=(-4, 0, 0), head=(-4, 0, 0),
           upper_arm_L=D(0.90, 0.05, 0.02), forearm_L=D(0.75, -0.40, 0.30),
           upper_arm_R=D(-0.90, 0.05, -0.02), forearm_R=D(-0.60, -0.70, 0.15), hand_R=GUN(-0.4, -0.9, 0.1),
           foot_L=F(0.14, -0.06, 0.20, 30, 4), foot_R=F(-0.15, 0.08, 0.14, 40, -4))
    fb = P(fa, chest=(-2, 0, 0), upper_arm_L=D(0.90, 0.0, 0.12), upper_arm_R=D(-0.90, 0.0, 0.08),
           foot_L=F(0.14, -0.02, 0.15, 38, 4), foot_R=F(-0.15, 0.04, 0.21, 30, -4))
    C['fall'] = dict(length=40, loop=True, keys=[(0, fa), (20, fb), (40, fa)])

    # ドリル（8、輪）：右腕を前へまっすぐ（スパークの先にドリル）、左手で前腕を支える。小さく震える
    dr = P(BASE, hips_loc=(0, 0.01, -0.07), hips=(6, 0, -8), spine=(5, 0, 0), chest=(4, 0, -4), head=(-8, 0, 10),
           upper_arm_R=D(-0.08, -1.0, -0.05), forearm_R=D(-0.02, -1.0, 0.0), hand_R=GUN(0, -1, 0),
           upper_arm_L=D(-0.15, -0.75, -0.55), forearm_L=D(-0.80, -0.55, 0.15),
           foot_L=F(0.18, -0.16, 0.105, 0, 10), foot_R=F(-0.17, 0.14, 0.105, 0, -22))
    dr1 = P(dr, hips_loc=(0.004, 0.014, -0.074), chest=(5, 0.6, -4), upper_arm_R=D(-0.07, -1.0, -0.03))
    dr2 = P(dr, hips_loc=(-0.004, 0.006, -0.068), chest=(3.5, -0.6, -4), upper_arm_R=D(-0.09, -1.0, -0.07))
    C['drill'] = dict(length=8, loop=True, keys=[(0, dr), (2, dr1), (4, dr), (6, dr2), (8, dr)])

    # 跳ぶ（16、1 回。最後の姿勢のまま上がる）：踏み切りで伸びきり → 前の膝を上げる → 上がる姿勢
    j0 = P(BASE, hips_loc=(0, 0, 0.0), chest=(-4, 0, 0), head=(-4, 0, 0),
           upper_arm_L=D(0.35, -0.55, 0.45), forearm_L=D(0.30, -0.55, 0.70),
           upper_arm_R=D(-0.50, -0.30, -0.25), forearm_R=D(-0.30, -0.80, 0.30), hand_R=GUN(-0.25, -0.85, 0.2),
           foot_L=F(0.13, 0.02, 0.13, 50, 4), foot_R=F(-0.13, 0.06, 0.15, 55, -4))
    j1 = P(j0, foot_L=F(0.13, -0.18, 0.38, 20, 4), foot_R=F(-0.14, 0.12, 0.17, 45, -4),
           upper_arm_L=D(0.60, -0.35, 0.05), forearm_L=D(0.45, -0.70, 0.35), upper_arm_R=D(-0.60, -0.25, -0.15))
    j2 = P(j1, chest=(-2, 0, 0), foot_L=F(0.13, -0.15, 0.40, 15, 4), foot_R=F(-0.14, 0.09, 0.22, 40, -4),
           upper_arm_L=D(0.75, -0.15, 0.05), forearm_L=D(0.60, -0.55, 0.40),
           upper_arm_R=D(-0.70, -0.10, -0.10), forearm_R=D(-0.50, -0.70, 0.25), hand_R=GUN(-0.4, -0.85, 0.1))
    C['jump'] = dict(length=16, loop=False, keys=[(0, j0), (8, j1), (16, j2)])

    # 空中斬り（18、振り抜き 4.5）：左上から右下への袈裟。脚は抱える
    air_leg = dict(foot_L=F(0.15, -0.18, 0.42, 25, 4), foot_R=F(-0.15, 0.16, 0.32, 45, -4))
    a0 = P(BASE, hips_loc=(0, 0, 0.0), chest=(-10, 0, 22), head=(-6, 0, -12), spine=(-4, 0, 6),
           upper_arm_L=D(0.40, 0.15, 0.90), forearm_L=D(0.10, 0.45, 0.90),
           upper_arm_R=D(-0.45, 0.25, -0.85), forearm_R=D(-0.30, -0.60, -0.70), hand_R=GUN(-0.2, -0.8, -0.6), **air_leg)
    a1 = P(a0, chest=(10, 0, -10), spine=(5, 0, -4), head=(-8, 0, 6),
           upper_arm_L=D(0.10, -0.95, 0.15), forearm_L=D(-0.35, -0.80, -0.45))
    a2 = P(a1, chest=(14, 0, -24), spine=(6, 0, -8), head=(-10, 0, 14), upper_arm_L=D(-0.40, -0.55, -0.65), forearm_L=D(-0.70, -0.15, -0.70))
    a3 = P(a2, chest=(8, 0, -16))
    a4 = P(BASE, hips_loc=(0, 0, 0.0), chest=(2, 0, 0), upper_arm_L=D(0.55, -0.10, -0.6), forearm_L=D(0.45, -0.60, -0.4),
           upper_arm_R=D(-0.50, 0.10, -0.6), forearm_R=D(-0.4, -0.6, -0.4), hand_R=GUN(-0.3, -0.8, -0.3),
           foot_L=F(0.14, -0.10, 0.30, 30, 4), foot_R=F(-0.15, 0.10, 0.22, 40, -4))
    C['air'] = dict(length=18, loop=False, keys=[(0, a0), (2, P(a0, chest=(-14, 0, 28))), (4.5, a1), (8, a2), (12, a3), (18, a4)])

    # 3 段斬り 1（17、振り抜き 4.25）：右肩に構えた刃を左へ横に払う（裏の払い）。左足で踏み込む
    step_l = dict(hips_loc=(0, -0.02, -0.075), foot_L=F(0.17, -0.22, 0.105, 0, 14), foot_R=F(-0.16, 0.16, 0.12, 15, -30))
    c1a = P(GUARD, hips=(0, 0, -18), chest=(4, 0, -32), head=(-6, 0, 30),
            upper_arm_L=D(-0.45, -0.75, -0.10), forearm_L=D(-0.90, -0.05, 0.35))
    c1b = P(c1a, chest=(4, 0, -40), upper_arm_L=D(-0.50, -0.70, 0.0))
    c1c = P(GUARD, hips=(0, 0, -4), chest=(6, 0, -4), head=(-6, 0, 6), **step_l,
            upper_arm_L=D(0.10, -1.0, 0.0), forearm_L=D(0.50, -0.85, 0.0))
    c1d = P(c1c, hips=(0, 0, 8), chest=(6, 0, 24), head=(-6, 0, -16),
            upper_arm_L=D(0.80, -0.50, 0.0), forearm_L=D(1.0, 0.15, 0.0))
    c1e = P(c1d, chest=(5, 0, 20), upper_arm_L=D(0.78, -0.40, -0.25), forearm_L=D(0.85, -0.10, -0.25))
    C['combo1'] = dict(length=17, loop=False, keys=[(0, c1a), (2.5, c1b), (4.25, c1c), (6.5, c1d), (10, c1e), (17, P(GUARD, **step_l))])

    # 3 段斬り 2（18、振り抜き 4.5）：左から右への返し。右足で踏み込む
    step_r = dict(hips_loc=(0, -0.02, -0.075), foot_R=F(-0.16, -0.20, 0.105, 0, -10), foot_L=F(0.17, 0.14, 0.12, 15, 25))
    c2a = P(GUARD, **step_l, hips=(0, 0, 10), chest=(4, 0, 30), head=(-6, 0, -22),
            upper_arm_L=D(0.85, 0.05, 0.10), forearm_L=D(0.75, 0.55, 0.20))
    c2b = P(c2a, chest=(4, 0, 36), upper_arm_L=D(0.85, 0.15, 0.12))
    c2c = P(GUARD, **step_r, hips=(0, 0, 0), chest=(6, 0, 2), head=(-6, 0, 0),
            upper_arm_L=D(0.10, -1.0, 0.05), forearm_L=D(-0.30, -0.95, 0.05))
    c2d = P(c2c, hips=(0, 0, -10), chest=(6, 0, -30), head=(-6, 0, 22),
            upper_arm_L=D(-0.60, -0.70, 0.0), forearm_L=D(-1.0, 0.10, -0.05))
    c2e = P(c2d, chest=(5, 0, -24), upper_arm_L=D(-0.50, -0.70, -0.20), forearm_L=D(-0.85, -0.20, -0.25))
    C['combo2'] = dict(length=18, loop=False, keys=[(0, c2a), (2.5, c2b), (4.5, c2c), (7, c2d), (11, c2e), (18, P(GUARD, **step_r))])

    # 3 段斬り 3（27、振り抜き 6.75）：しゃがんでから下から上へ斬り上げる（敵を浮かせる）
    c3a = P(GUARD, hips_loc=(0, 0, -0.14), hips=(10, 0, 10), spine=(8, 0, 6), chest=(12, 0, 22), head=(-14, 0, -18),
            upper_arm_L=D(0.50, 0.50, -0.70), forearm_L=D(0.40, 0.35, -0.85),
            foot_L=F(0.20, -0.16, 0.105, 0, 14), foot_R=F(-0.18, 0.18, 0.105, 0, -30))
    c3b = P(c3a, hips_loc=(0, 0, -0.16), chest=(14, 0, 26), upper_arm_L=D(0.50, 0.60, -0.65))
    c3c = P(c3a, hips_loc=(0, -0.01, -0.03), hips=(-4, 0, -6), spine=(-6, 0, -4), chest=(-14, 0, -10), head=(-4, 0, 10),
            upper_arm_L=D(0.15, -0.80, 0.60), forearm_L=D(0.0, -0.40, 0.90),
            foot_L=F(0.19, -0.18, 0.15, 30, 14), foot_R=F(-0.17, 0.15, 0.16, 35, -30))
    c3d = P(c3c, chest=(-16, 0, -14), upper_arm_L=D(0.10, -0.20, 1.0), forearm_L=D(-0.05, 0.30, 0.95))
    C['combo3'] = dict(length=27, loop=False, keys=[(0, c3a), (4, c3b), (6.75, c3c), (12, c3d), (18, P(c3d, chest=(-10, 0, -10))), (27, GUARD)])

    # 突進突き（20、振り抜き 5）：左腕を引いてから前へまっすぐ突く。深い踏み込み
    l0 = P(GUARD, hips_loc=(0, 0.02, -0.08), hips=(0, 0, 14), chest=(4, 0, 26), head=(-6, 0, -24),
           upper_arm_L=D(0.25, 0.75, -0.60), forearm_L=D(0.05, -1.0, 0.05))
    l1 = P(GUARD, hips_loc=(0, -0.04, -0.15), hips=(8, 0, -16), spine=(4, 0, -6), chest=(10, 0, -28), head=(-14, 0, 30),
           upper_arm_L=D(0.0, -1.0, 0.04), forearm_L=D(-0.05, -1.0, 0.05),
           upper_arm_R=D(-0.35, 0.55, -0.75), forearm_R=D(-0.30, 0.10, -0.95),
           foot_L=F(0.18, -0.42, 0.105, 0, 6), foot_R=F(-0.17, 0.34, 0.15, 35, -20))
    C['lunge'] = dict(length=20, loop=False, keys=[(0, l0), (2.5, P(l0, chest=(4, 0, 32))), (5, l1), (10, P(l1, chest=(9, 0, -24))), (20, P(GUARD, foot_L=F(0.18, -0.30, 0.105, 0, 8), foot_R=F(-0.17, 0.22, 0.11, 10, -24), hips_loc=(0, -0.02, -0.09)))])

    # 溜め斬り（30、振り抜き 7.5）：右へ大きく溜めて、160 度の大振り（衝撃波）
    wide = dict(foot_L=F(0.24, -0.18, 0.105, 0, 18), foot_R=F(-0.22, 0.20, 0.105, 0, -32))
    ch0 = P(GUARD, **wide, hips_loc=(0, 0, -0.11), hips=(0, 0, -22), chest=(6, 0, -44), head=(-8, 0, 40),
            upper_arm_L=D(-0.60, -0.40, 0.30), forearm_L=D(-0.85, 0.35, 0.40),
            upper_arm_R=D(-0.45, 0.45, -0.75), forearm_R=D(-0.35, -0.20, -0.90))
    ch1 = P(ch0, chest=(8, 0, -54), hips=(0, 0, -26), upper_arm_L=D(-0.65, -0.20, 0.35))
    ch2 = P(ch0, hips_loc=(0, -0.02, -0.13), hips=(0, 0, 0), chest=(8, 0, 0), head=(-8, 0, 10),
            upper_arm_L=D(0.15, -1.0, 0.05), forearm_L=D(0.40, -0.90, 0.0))
    ch3 = P(ch2, hips=(0, 0, 16), chest=(6, 0, 44), head=(-8, 0, -20),
            upper_arm_L=D(0.90, -0.20, 0.10), forearm_L=D(0.85, 0.50, 0.10))
    ch4 = P(ch3, chest=(4, 0, 40), upper_arm_L=D(0.90, 0.10, -0.20), forearm_L=D(0.75, 0.55, -0.30))
    C['charge'] = dict(length=30, loop=False, keys=[(0, ch0), (4, ch1), (7.5, ch2), (11, ch3), (17, ch4), (30, P(GUARD, **wide))])

    # ダッシュ（14）：低く前へ倒れて滑る。腕は後ろへ流れ、左腕が外から前へ払う（ダッシュ斬りでも同じ動作を 0.35 秒で流す）
    da0 = P(BASE, hips_loc=(0, 0.02, -0.10), hips=(20, 0, 0), spine=(8, 0, 0), chest=(6, 0, 0), neck=(-10, 0, 0), head=(-18, 0, 0),
            upper_arm_L=D(0.30, 0.75, -0.55), forearm_L=D(0.25, 0.90, -0.25),
            upper_arm_R=D(-0.30, 0.55, -0.75), forearm_R=D(-0.20, 0.45, -0.85), hand_R=GUN(-0.2, 0.3, -0.9),
            foot_L=F(0.15, -0.26, 0.105, 0, 6), foot_R=F(-0.15, 0.36, 0.20, 40, -10))
    da1 = P(da0, chest=(6, 0, 20), upper_arm_L=D(0.90, 0.30, -0.10), forearm_L=D(0.80, 0.55, 0.0))
    da2 = P(da0, chest=(6, 0, -6), upper_arm_L=D(0.05, -1.0, 0.0), forearm_L=D(-0.40, -0.90, 0.0))
    da3 = P(da0, chest=(6, 0, -24), upper_arm_L=D(-0.80, -0.40, -0.20), forearm_L=D(-1.0, 0.20, -0.20))
    C['dash'] = dict(length=14, loop=False, keys=[(0, da0), (3.5, da1), (6, da2), (9, da3), (14, P(da3, hips=(14, 0, 0)))])

    # 被弾（16）：2〜4 こまで打たれた形（combat-animation の Hit Reaction）→ よろけ → 構え直し（重い被弾は最後のまま 1 秒）
    h1 = P(BASE, hips_loc=(0, 0.03, -0.03), hips=(-6, 0, 0), spine=(-8, 0, 0), chest=(-14, 0, 6), neck=(-6, 0, 0), head=(-16, 0, -6),
           upper_arm_L=D(0.65, -0.35, -0.55), forearm_L=D(0.55, -0.60, -0.15),
           upper_arm_R=D(-0.60, -0.30, -0.65), forearm_R=D(-0.45, -0.70, -0.25), hand_R=GUN(-0.3, -0.9, 0.0),
           foot_L=F(0.16, -0.04, 0.12, 15, 6), foot_R=F(-0.16, 0.10, 0.105, 0, -10))
    h2 = P(h1, hips_loc=(0, 0.02, -0.08), hips=(6, 0, 0), spine=(8, 0, 0), chest=(12, 0, -4), head=(10, 0, 4),
           upper_arm_L=D(0.40, -0.55, -0.70), forearm_L=D(0.10, -0.80, 0.40),
           foot_L=F(0.16, -0.04, 0.105, 0, 6), foot_R=F(-0.17, 0.16, 0.105, 0, -16))
    h3 = P(h2, chest=(9, 0, -3), head=(6, 0, 3))
    C['hurt'] = dict(length=16, loop=False, keys=[(0, P(BASE, chest=(-4, 0, 0))), (3, h1), (9, h2), (16, h3)])

    # 倒れる（36）：打たれ → 膝が崩れる → 後ろへ尻もち → あお向け（最後のまま）
    dd1 = P(h1)
    dd2 = P(BASE, hips_loc=(0, 0.02, -0.26), hips=(10, 0, 0), spine=(10, 0, 0), chest=(18, 0, 0), head=(16, 0, 0),
            upper_arm_L=D(0.45, -0.30, -0.80), forearm_L=D(0.40, -0.55, -0.70),
            upper_arm_R=D(-0.45, -0.30, -0.80), forearm_R=D(-0.35, -0.60, -0.70), hand_R=GUN(-0.3, -0.8, -0.5),
            foot_L=F(0.17, -0.12, 0.105, 0, 15), foot_R=F(-0.17, -0.06, 0.105, 0, -15))
    dd3 = P(dd2, hips_loc=(0, 0.10, -0.52), hips=(-42, 0, 0), spine=(-6, 0, 0), chest=(-8, 0, 0), head=(-10, 0, 0),
            upper_arm_L=D(0.75, 0.30, -0.55), forearm_L=D(0.70, -0.10, -0.70),
            upper_arm_R=D(-0.75, 0.30, -0.55), forearm_R=D(-0.70, -0.10, -0.70),
            foot_L=F(0.19, -0.32, 0.10, -20, 15), foot_R=F(-0.19, -0.26, 0.10, -20, -15))
    dd4 = P(dd3, hips_loc=(0, 0.16, -0.66), hips=(-84, 0, 0), spine=(-4, 0, 0), chest=(-4, 0, 0), neck=(-4, 0, 0), head=(-6, 0, 18),
            upper_arm_L=D(0.90, 0.30, 0.25), forearm_L=D(0.80, 0.40, 0.45),
            upper_arm_R=D(-0.90, 0.30, 0.15), forearm_R=D(-0.85, 0.40, 0.30), hand_R=GUN(-0.9, 0.4, -0.2),
            foot_L=F(0.22, -0.52, 0.09, -60, 25), foot_R=F(-0.16, -0.56, 0.09, -60, -20))
    dd5 = P(dd4, hips_loc=(0, 0.16, -0.64), chest=(-6, 0, 0), head=(-8, 0, 20))
    C['dead'] = dict(length=36, loop=False, keys=[(0, P(BASE)), (4, dd1), (12, dd2), (20, dd3), (28, dd4), (32, dd5), (36, dd4)])
    return C


# ---------------------------------------------------------------- 姿勢 → 骨の回転（自前の FK：キーを打つこまの姿勢を数で出す）
def _rest(arm):
    return {b.name: b.matrix_local.copy() for b in arm.data.bones}


def _q_from_euler(M3, e):
    R = Euler([math.radians(a) for a in e], 'XYZ').to_matrix()
    return (M3.inverted() @ R @ M3).to_quaternion()


def solve_pose(arm, pose):
    """姿勢の辞書 → {骨: (location, quaternion)}（FK の骨だけ。脚は IK）"""
    rest = _rest(arm)
    G = {'root': rest['root'].copy()}
    out = {}
    order = ['hips', 'spine', 'chest', 'neck', 'head', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L',
             'shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R']
    torso = Matrix.Identity(3)
    for b in order:
        bone = arm.data.bones[b]
        par = bone.parent.name
        M = rest[b]
        Gz = G[par] @ rest[par].inverted() @ M
        spec = pose.get(b, (0, 0, 0))
        loc = Vector((0, 0, 0))
        if b == 'hips':
            d = Vector(pose.get('hips_loc', (0, 0, 0)))
            loc = M.to_3x3().inverted() @ d
        if isinstance(spec, D):
            Gz3 = Gz.to_3x3()
            c = (Gz3 @ Vector((0, 1, 0))).normalized()
            want = (torso @ spec.d).normalized()
            A = c.rotation_difference(want).to_matrix()
            if spec.ref is not None:
                r = (A @ Gz3 @ M.to_3x3().inverted() @ spec.ref)
                r = (r - want * r.dot(want))
                u = (torso @ spec.up)
                u = (u - want * u.dot(want))
                if r.length > 1e-6 and u.length > 1e-6:
                    ang = r.normalized().angle(u.normalized())
                    if r.normalized().cross(u.normalized()).dot(want) < 0:
                        ang = -ang
                    A = Quaternion(want, ang).to_matrix() @ A
            q = (Gz3.inverted() @ A @ Gz3).to_quaternion()
        else:
            q = _q_from_euler(M.to_3x3(), spec)
        Gb = Gz @ Matrix.Translation(loc) @ q.to_matrix().to_4x4()
        G[b] = Gb
        out[b] = (loc, q)
        if b == 'chest':
            torso = Gb.to_3x3() @ M.to_3x3().inverted()
    return out


def key_pose(arm, pose, f, prev, interp):
    """FK の骨と足の目標に、こま f のキーを打つ（_feet_only の姿勢は足の目標だけ）"""
    sol = {} if pose.get('_feet_only') else solve_pose(arm, pose)
    for b, (loc, q) in sol.items():
        pb = arm.pose.bones[b]
        if b in prev and prev[b].dot(q) < 0:
            q = -q
        prev[b] = q
        pb.rotation_quaternion = q
        pb.keyframe_insert('rotation_quaternion', frame=f, group=b)
        if b == 'hips':
            pb.location = loc
            pb.keyframe_insert('location', frame=f, group=b)
    for s in ('L', 'R'):
        _, x, y, z, pitch, yaw = pose['foot.' + s]
        tg = bpy.data.objects['IK_foot.' + s]
        tg.location = (x, y, z)
        tg.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
        tg.keyframe_insert('location', frame=f)
        tg.keyframe_insert('rotation_euler', frame=f)


def _set_interp(action, interp, loop):
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        if loop and not fc.modifiers:
            fc.modifiers.new('CYCLES')     # 輪：自動の取っ手が継ぎ目でもなめらか（cycle-aware）
        fc.update()


def bake_legs(arm, length, iks):
    """脚の IK をこまごとに解いて、thigh・shin・foot の回転のキーに焼く（export-pipeline：Bake constraints before export）"""
    sc = bpy.context.scene
    rest = _rest(arm)
    store = []
    for f in range(0, length + 1):
        sc.frame_set(f)
        hips = arm.pose.bones['hips'].matrix
        fwd_h = (hips.to_3x3() @ rest['hips'].to_3x3().inverted() @ Vector((0, -1, 0))).normalized()
        rec = {}
        for s, (tg, pl, ik) in iks.items():
            th = arm.pose.bones['thigh.' + s]
            yaw = tg.rotation_euler.z
            fwd_f = Quaternion((0, 0, 1), yaw) @ Vector((0, -1, 0))
            kd = (fwd_h + fwd_f).normalized()
            mid = (th.head + tg.location) * 0.5
            pl.location = mid + kd * 0.6
        bpy.context.view_layer.update()
        for s, (tg, pl, ik) in iks.items():
            th = arm.pose.bones['thigh.' + s]
            sh = arm.pose.bones['shin.' + s]
            # 足の向き：yaw → pitch の順（Rz・Rx）を基準の足に
            R = Matrix.Rotation(tg.rotation_euler.z, 3, 'Z') @ Matrix.Rotation(tg.rotation_euler.x, 3, 'X')
            fm = (R @ rest['foot.' + s].to_3x3()).to_4x4()
            fm.translation = sh.tail.copy()
            rec[s] = (th.matrix.copy(), sh.matrix.copy(), fm, (sh.tail - tg.location).length)
        store.append(rec)
    for s, (tg, pl, ik) in iks.items():
        ik.mute = True
    prev = {}
    miss = 0.0
    for f, rec in enumerate(store):
        sc.frame_set(f)
        for s in ('L', 'R'):
            tm, sm, fm, err = rec[s]
            miss = max(miss, err)
            for b, m in zip(LEGS[s], (tm, sm, fm)):
                pb = arm.pose.bones[b]
                pb.matrix = m
                bpy.context.view_layer.update()
                q = pb.rotation_quaternion.copy()
                if b in prev and prev[b].dot(q) < 0:
                    q = -q
                prev[b] = q
                pb.rotation_quaternion = q
                pb.location = (0, 0, 0)
                pb.keyframe_insert('rotation_quaternion', frame=f, group=b)
    for s, (tg, pl, ik) in iks.items():
        ik.mute = False
    return miss


def with_step_lifts(keys, move=0.04, lift=0.05):
    """床に着いた足（足首が 0.13 m より低い）がキーの間で move より動くなら、間に足を lift だけ上げたキーを足す
    （combat-animation：その場の攻撃で足を滑らせない。踏み込みは足を上げて置き直す）。上げたキーは前の姿勢の半分のこま"""
    out = [keys[0]]
    for (f0, p0), (f1, p1) in zip(keys, keys[1:]):
        mid = None
        for s in ('L', 'R'):
            a, b = p0['foot.' + s], p1['foot.' + s]
            pa, pb = Vector(a[1:4]), Vector(b[1:4])
            if pa.z < 0.13 and pb.z < 0.13 and (pa - pb).length > move:
                if mid is None:
                    mid = dict(p0)
                m = pa.lerp(pb, 0.5)
                mid['foot.' + s] = F(m.x, m.y, max(pa.z, pb.z) + lift, (a[4] + b[4]) / 2 + 10, (a[5] + b[5]) / 2)
        if mid is not None:
            # 体は前のキーと次のキーの間（足だけ上げる。体は Bezier で間を通る）：体の骨のキーは打たないよう足だけの印
            mid['_feet_only'] = True
            out.append(((f0 + f1) / 2.0, mid))
        out.append((f1, p1))
    return out


def build_clips(arm, blocking=False, only=None):
    """14 の動作を作り、NLA の帯（帯の名前 = ゲームの動作の名前）に積む。actions は AN_HaruBS_<Clip>"""
    import rig
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.render.fps_base = 1.0
    iks = rig.add_leg_ik(arm)
    if arm.animation_data is None:
        arm.animation_data_create()
    report = {}
    for name, cl in clips().items():
        if only and name not in only:
            continue
        act = bpy.data.actions.new('AN_HaruBS_' + name.title())
        act.use_fake_user = True
        arm.animation_data.action = act
        tacts = {}
        for s in ('L', 'R'):
            tg = iks[s][0]
            if tg.animation_data is None:
                tg.animation_data_create()
            tacts[s] = bpy.data.actions.new('IKtarget_%s_%s' % (name, s))
            tg.animation_data.action = tacts[s]
        prev = {}
        for f, pose in (cl['keys'] if cl['loop'] else with_step_lifts(cl['keys'])):
            key_pose(arm, pose, f, prev, 'BEZIER')
        interp = 'CONSTANT' if blocking else 'BEZIER'
        _set_interp(act, interp, cl['loop'])
        for a in tacts.values():
            _set_interp(a, interp, cl['loop'])
        miss = bake_legs(arm, cl['length'], iks)
        # 脚の焼いたキーも輪なら Cycles
        for fc in act.fcurves:
            if cl['loop'] and not fc.modifiers:
                fc.modifiers.new('CYCLES')
        act.use_frame_range = True
        act.frame_start = 0
        act.frame_end = cl['length']
        act.use_cyclic = cl['loop']
        tr = arm.animation_data.nla_tracks.new()
        tr.name = name
        st = tr.strips.new(name, 0, act)
        st.action_frame_start, st.action_frame_end = 0, cl['length']
        tr.mute = True
        arm.animation_data.action = None
        for s in ('L', 'R'):
            iks[s][0].animation_data.action = None
        report[name] = (cl['length'], cl['length'] / FPS, len(cl['keys']), miss)
        print('CLIP %-7s %3d f  %.4f s  keys %d  IK miss %.4f m' % (name, cl['length'], cl['length'] / FPS, len(cl['keys']), miss))
    return report


def remove_ik(arm):
    for s in ('L', 'R'):
        pb = arm.pose.bones['shin.' + s]
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        for n in ('IK_foot.' + s, 'IK_knee.' + s):
            o = bpy.data.objects.get(n)
            if o:
                bpy.data.objects.remove(o)


def apply_static_pose(arm, pose, iks):
    """1 つの姿勢を骨に置く（確かめの絵用。キーは打たない）。脚は IK の目標を置いて解いたまま"""
    sol = solve_pose(arm, pose)
    for b, (loc, q) in sol.items():
        pb = arm.pose.bones[b]
        pb.rotation_quaternion = q
        pb.location = loc
    rest = _rest(arm)
    bpy.context.view_layer.update()
    hips = arm.pose.bones['hips'].matrix
    fwd_h = (hips.to_3x3() @ rest['hips'].to_3x3().inverted() @ Vector((0, -1, 0))).normalized()
    for s in ('L', 'R'):
        _, x, y, z, pitch, yaw = pose['foot.' + s]
        tg, pl, ik = iks[s]
        tg.location = (x, y, z)
        tg.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
        th = arm.pose.bones['thigh.' + s]
        fwd_f = Quaternion((0, 0, 1), math.radians(yaw)) @ Vector((0, -1, 0))
        pl.location = (th.head + tg.location) * 0.5 + (fwd_h + fwd_f).normalized() * 0.6
    bpy.context.view_layer.update()
    for s in ('L', 'R'):
        tg = iks[s][0]
        sh = arm.pose.bones['shin.' + s]
        R = Matrix.Rotation(tg.rotation_euler.z, 3, 'Z') @ Matrix.Rotation(tg.rotation_euler.x, 3, 'X')
        fm = (R @ rest['foot.' + s].to_3x3()).to_4x4()
        fm.translation = sh.tail.copy()
        arm.pose.bones['foot.' + s].matrix = fm
    bpy.context.view_layer.update()


# 骨と重みの確かめの姿勢（rigging の Deformation Test Poses ＋ 走りの一歩 ＋ 剣の振り）
def test_poses():
    T = {}
    T['A ポーズ（基準）'] = P(BASE, **{k: (0, 0, 0) for k in FK}, hips_loc=(0, 0, 0),
                          foot_L=F(FL0.x, FL0.y, FL0.z, 0, 0), foot_R=F(FR0.x, FR0.y, FR0.z, 0, 0))
    T['腕を上げきる'] = P(BASE, upper_arm_L=D(0.25, 0.0, 1.0), forearm_L=D(0.15, 0.0, 1.0), hand_L=(0, 0, 0),
                     upper_arm_R=D(-0.25, 0.0, 1.0), forearm_R=D(-0.15, 0.0, 1.0), hand_R=GUN(-0.1, 0, 1),
                     shoulder_L=(0, -18, 0), shoulder_R=(0, 18, 0))
    T['深くしゃがむ'] = P(BASE, hips_loc=(0, 0.06, -0.42), hips=(28, 0, 0), spine=(14, 0, 0), chest=(8, 0, 0), head=(-26, 0, 0),
                     upper_arm_L=D(0.35, -0.70, -0.60), forearm_L=D(0.10, -0.95, 0.10),
                     upper_arm_R=D(-0.35, -0.70, -0.60), forearm_R=D(-0.10, -0.95, 0.10), hand_R=GUN(0, -1, 0.1),
                     foot_L=F(0.17, -0.05, 0.105, 0, 14), foot_R=F(-0.17, -0.05, 0.105, 0, -14))
    T['首：右へ・上'] = P(BASE, neck=(-14, 0, -30), head=(-22, 0, -40))
    T['首：左へ・下'] = P(BASE, neck=(16, 8, 30), head=(24, 10, 40))
    c = clips()
    T['走りの一歩'] = c['run']['keys'][2][1]
    T['剣の振り（溜め斬り）'] = c['charge']['keys'][3][1]
    T['剣の構え（3 段斬り 1）'] = c['combo1']['keys'][1][1]
    return T
