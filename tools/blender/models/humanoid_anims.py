"""人型の共通アニメーション（30fps）。

骨の回転の向き（確認済み）：
- 腕・脚（下向きの骨）：X がマイナスで前へ振る、プラスで後ろへ振る
- すね：X プラスで膝が曲がる。前腕：X マイナスで肘が曲がる
- 上腕を横に上げる：右は Z プラス、左は Z マイナス
- 背骨・胸・首・頭：X プラスで前に倒れる。Y プラスでキャラクターの左へひねる
主人公は右手に銃、左腕のガントレットから光刃を出す。
"""
from __future__ import annotations

import math

from lib.humanoid import Clip, Pose, mirror

# 右手は銃を少し前に構えている
GUN_HOLD: Pose = {'upper_arm.R': (-10, 0, 8), 'forearm.R': (-35, 0, 0)}


def merge(*poses: Pose) -> Pose:
    out: Pose = {}
    for p in poses:
        out.update(p)
    return out


def idle() -> Clip:
    base = merge({'upper_arm.L': (0, 0, -8), 'forearm.L': (-12, 0, 0), 'spine': (2, 0, 0)}, GUN_HOLD)
    breathe = merge(base, {'chest': (-2, 0, 0), 'upper_arm.L': (0, 0, -10)})
    return Clip('idle', 60, [(1, base), (31, breathe), (61, base)])


# 走りで右の上腕をひねる角度（Y）：肘を曲げた前腕と銃が体の前を横切って内（左）を向かないように、外へ向ける
RUN_GUN_TWIST = 15


def run() -> Clip:
    contact: Pose = {
        'spine': (12, 0, 0), 'chest': (0, -8, 0), 'head': (-8, 6, 0),
        'thigh.L': (-45, 0, 0), 'shin.L': (15, 0, 0),
        'thigh.R': (35, 0, 0), 'shin.R': (55, 0, 0),
        'upper_arm.L': (35, 0, -10), 'forearm.L': (-50, 0, 0),
        'upper_arm.R': (-30, RUN_GUN_TWIST, 10), 'forearm.R': (-70, 0, 0),
    }
    passing: Pose = {
        'spine': (12, 0, 0), 'chest': (0, 0, 0), 'head': (-8, 0, 0),
        'thigh.L': (0, 0, 0), 'shin.L': (25, 0, 0),
        'thigh.R': (-35, 0, 0), 'shin.R': (95, 0, 0),
        'upper_arm.L': (5, 0, -10), 'forearm.L': (-50, 0, 0),
        'upper_arm.R': (0, RUN_GUN_TWIST, 10), 'forearm.R': (-70, 0, 0),
    }
    c2 = mirror(contact)
    p2 = mirror(passing)
    # 右手は銃を持っているので、反対の足のときも振りを小さくする
    for p in (c2, p2):
        p['upper_arm.R'] = (p['upper_arm.R'][0] * 0.6, RUN_GUN_TWIST, 10)
        p['forearm.R'] = (-70, 0, 0)
    return Clip('run', 20, [(1, contact), (6, passing), (11, c2), (16, p2), (21, contact)],
                bob=[(1, 0.0), (6, 0.05), (11, 0.0), (16, 0.05), (21, 0.0)])


def jump() -> Clip:
    p = merge({
        'spine': (5, 0, 0), 'thigh.L': (-65, 0, 0), 'shin.L': (85, 0, 0), 'thigh.R': (-10, 0, 0), 'shin.R': (35, 0, 0),
        'upper_arm.L': (-50, 0, -25), 'forearm.L': (-30, 0, 0),
    }, GUN_HOLD)
    return Clip('jump', 8, [(1, p), (9, p)], loop=False)


def fall() -> Clip:
    a = merge({
        'spine': (-4, 0, 0), 'thigh.L': (-25, 0, 0), 'shin.L': (45, 0, 0), 'thigh.R': (10, 0, 0), 'shin.R': (30, 0, 0),
        'upper_arm.L': (-10, 0, -50), 'forearm.L': (-20, 0, 0), 'upper_arm.R': (-15, 0, 45), 'forearm.R': (-30, 0, 0),
    })
    b = merge(a, {'upper_arm.L': (-10, 0, -58), 'upper_arm.R': (-15, 0, 52)})
    return Clip('fall', 20, [(1, a), (11, b), (21, a)])


def dash() -> Clip:
    p = {
        'spine': (30, 0, 0), 'head': (-20, 0, 0), 'thigh.L': (-50, 0, 0), 'shin.L': (60, 0, 0),
        'thigh.R': (40, 0, 0), 'shin.R': (50, 0, 0),
        'upper_arm.L': (55, 0, -15), 'forearm.L': (-20, 0, 0), 'upper_arm.R': (50, 0, 15), 'forearm.R': (-30, 0, 0),
    }
    return Clip('dash', 7, [(1, p), (8, p)], loop=False)


def hurt() -> Clip:
    p = {
        'spine': (-20, 0, 0), 'head': (-20, 0, 0), 'upper_arm.L': (-20, 0, -40), 'upper_arm.R': (-20, 0, 40),
        'thigh.L': (-15, 0, 0), 'shin.L': (25, 0, 0),
    }
    return Clip('hurt', 8, [(1, p), (9, p)], loop=False)


def dead() -> Clip:
    a = {'spine': (-20, 0, 0), 'upper_arm.L': (-20, 0, -40), 'upper_arm.R': (-20, 0, 40)}
    b = {
        'spine': (45, 0, 0), 'head': (30, 0, 0), 'thigh.L': (-80, 0, 0), 'shin.L': (120, 0, 0),
        'thigh.R': (-70, 0, 0), 'shin.R': (125, 0, 0), 'upper_arm.L': (-30, 0, -20), 'upper_arm.R': (-30, 0, 20),
    }
    return Clip('dead', 18, [(1, a), (19, b)], loop=False, bob=[(1, 0.0), (19, -0.55)])


def drill() -> Clip:
    a = merge({
        'spine': (10, 12, 0), 'upper_arm.L': (-85, 0, -5), 'forearm.L': (-5, 0, 0),
        'thigh.L': (-25, 0, 0), 'shin.L': (20, 0, 0), 'thigh.R': (20, 0, 0), 'shin.R': (15, 0, 0),
    }, GUN_HOLD)
    b = merge(a, {'upper_arm.L': (-83, 0, -7), 'spine': (11, 12, 0)})
    return Clip('drill', 4, [(1, a), (3, b), (5, a)])


def stance(extra: Pose) -> Pose:
    """斬りの足構え（溜め斬り・突きなど、古い作りの動作が使う）"""
    return merge({'thigh.L': (-30, 0, 0), 'shin.L': (25, 0, 0), 'thigh.R': (25, 0, 0), 'shin.R': (20, 0, 0)}, GUN_HOLD,
                 extra)


# ---------------------------------------------------------------- 光刃の 3 段斬り（60fps、接地つき）
#
# 作り：予備動作（振りかぶり。ゆっくり始めて加速）→ 振り抜き（3 こま＝0.05 秒。QUAD の EASE_IN で最後が一番速い）
#       → 行き過ぎ（2 こま。勢いで少し先まで行く）→ 戻り（ゆっくり止まる。次の段の構えで終わる）。
# 全身で振る：腰・背骨・胸のひねりで刃を運び、頭は逆にひねって顔を相手に向けたまま、右腕（銃）は反対へ振って釣り合う。
# 脚は踏み込み（前の膝を曲げると、接地の計算で腰が沈む）。各段の終わりの姿勢 = 次の段の始めの姿勢（つながる）。
# 長さはゲームの中身の攻撃時間（tuning.yaml の comboTimes：0.28・0.30・0.45 秒）と同じ。当たり判定は攻撃時間の
# 25〜70% なので、振り抜きを 25% の所に置く（combo1 は 4〜7 こま目 = 0.05〜0.10 秒）。
# 腕の回転：X が負で前へ上げる。上げた腕の Y は縦の軸まわりの回転（正で本人の右へ＝左腕なら体の前を横切る）。
# Z は前後の軸まわり（下げた左腕は負で外へ。頭の上まで上げた腕は逆に正で外へ）。
# 背骨・胸の前傾は、腕を世界では同じ角度だけ後ろへ回す（剛体の回転）。前傾 40 度で刃を前下 65 度に向けるなら上腕 X は -105。

SWORD_FPS = 60

# 脚の長さ（haru_r の関節表：股関節 0.715、膝 0.395、足首 0.090 m）と、足首からつま先までの前後の長さ
HIP_Z, THIGH_LEN, SHIN_LEN, TOE_REACH = 0.715, 0.32, 0.305, 0.22
LEG_REST = 4.0   # 基準の姿勢の脚の傾き（度）。実測（leg_table）に合わせた：前に振った脚は見積もりより低く、後ろは高くなる


def feet_for(legs, heel=(0, 0), lift=(False, False)) -> tuple[float, float]:
    """脚の角度から足首 X を決める：足の裏を床に平らにし（すねの傾きを打ち消す）、足首が高いほうの足は
    つま先が床に触れるまでかかとを上げる。heel はさらに足すかかとの上げ（度。正でつま先が下がる）。
    lift が True の足は上げた足（膝を上げた踏み込みなど）：床に合わせず、すねに対して平らのまま。
    足首の骨の X は正でつま先が下がる。すねの前への傾き = -(太もも X + すね X)"""
    def ankle_z(th, sh):
        return HIP_Z - THIGH_LEN * math.cos(math.radians(th + LEG_REST)) - SHIN_LEN * math.cos(math.radians(th + sh + LEG_REST))

    out = []
    zs = (ankle_z(legs[0], legs[1]), ankle_z(legs[2], legs[3]))
    low = min(zs)
    for i, (th, sh) in enumerate(((legs[0], legs[1]), (legs[2], legs[3]))):
        flat = -(th + sh)
        lift_deg = 0.0 if lift[i] else math.degrees(math.asin(min(1.0, (zs[i] - low) / TOE_REACH)))
        out.append(flat + lift_deg + heel[i])
    return (out[0], out[1])


def sp(*, hips=(0, 0), spine=(0, 0), chest=(0, 0), neck: float = 0, head=(0, 0), sh_l=(0, 0), sh_r=(0, 0),
       arm_l=(0, 0, 0), fore_l: float = 0, arm_r=(-10, 0, 8), fore_r: float = -35,
       legs=(-30, 25, 25, 20), heel=(0, 0), lift=(False, False)) -> Pose:
    """斬りの全身の姿勢（度）。hips：腰の (前傾 X, ひねり Y)。spine・chest：(前傾 X, ひねり Y)。neck：ひねり Y。head：(前傾 X, ひねり Y)。
    sh_l・sh_r：肩の (すくめ X, 前出し Z。左は負で前、右は正で前)。arm_l・arm_r：上腕 (X, Y, Z)。fore_l・fore_r：肘の曲げ X。
    legs：(左太もも X, 左すね X, 右太もも X, 右すね X)。世界での角度（腰の前傾は太ももから引く）。足首は feet_for で床に合わせ、
    heel：(左, 右) でさらにかかとを上げる。lift：(左, 右) True の足は上げた足（床に合わせない）"""
    feet = feet_for(legs, heel, lift)
    # 腰の前傾（hips X）は脚ごと回すので、太ももから引いて legs を世界での角度のままにする（足の位置・足の裏の向きが変わらない）
    th_l, th_r = legs[0] - hips[0], legs[2] - hips[0]
    return {
        'hips': (hips[0], hips[1], 0), 'spine': (spine[0], spine[1], 0), 'chest': (chest[0], chest[1], 0),
        'neck': (0, neck, 0), 'head': (head[0], head[1], 0),
        'shoulder.L': (sh_l[0], 0, sh_l[1]), 'shoulder.R': (sh_r[0], 0, sh_r[1]),
        'upper_arm.L': tuple(arm_l), 'forearm.L': (fore_l, 0, 0),
        'upper_arm.R': tuple(arm_r), 'forearm.R': (fore_r, 0, 0),
        'thigh.L': (th_l, 0, 0), 'shin.L': (legs[1], 0, 0), 'thigh.R': (th_r, 0, 0), 'shin.R': (legs[3], 0, 0),
        'foot.L': (feet[0], 0, 0), 'foot.R': (feet[1], 0, 0),
    }


def k(frame: int, pose: Pose, interp: str | None = None, ease: str | None = None, lifted: tuple = ()):
    """こま。interp・ease は次のこままでのつなぎ（lib.humanoid.Key）。lifted：このこまで床に合わせない足（'foot.L' など）"""
    spec = {}
    if interp:
        spec['interp'] = interp
    if ease:
        spec['ease'] = ease
    if lifted:
        spec['lifted'] = tuple(lifted)
    return (frame, pose, spec)


# 体の部位ごとの「遅れ」。腰が先に回り、背骨→胸→肩→腕の順に追いかける（腰の入った振り）
GROUPS = {
    'hips': ('hips',), 'spine': ('spine',), 'chest': ('chest',), 'head': ('neck', 'head'),
    'sh': ('shoulder.L', 'shoulder.R'), 'arm_l': ('upper_arm.L', 'forearm.L', 'hand.L'),
    'arm_r': ('upper_arm.R', 'forearm.R', 'hand.R'),
    'legs': ('thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R'),
}


def between(a: Pose, b: Pose, w: dict[str, float]) -> Pose:
    """a から b へ、部位ごとに違う割合だけ進んだ姿勢（w：部位名 → 0〜1。無い部位は 1）"""
    out: Pose = {}
    for grp, bones in GROUPS.items():
        t = w.get(grp, 1.0)
        for bn in bones:
            pa, pb = a.get(bn, (0, 0, 0)), b.get(bn, (0, 0, 0))
            out[bn] = tuple(pa[i] + (pb[i] - pa[i]) * t for i in range(3))
    return out


# 腰が先、腕が最後：振り抜きの途中 2 こまの割合
LEAD_1 = {'hips': 0.75, 'spine': 0.55, 'chest': 0.35, 'head': 0.45, 'sh': 0.4, 'arm_l': 0.18, 'arm_r': 0.3, 'legs': 0.55}
LEAD_2 = {'hips': 1.0, 'spine': 0.95, 'chest': 0.85, 'head': 0.85, 'sh': 0.9, 'arm_l': 0.62, 'arm_r': 0.75, 'legs': 0.95}

# 1 段目の終わり（= 2 段目の始め）：刃を左前へ振り切って、少し戻した構え
READY_L = sp(hips=(2, 5), spine=(8, 6), chest=(2, 12), neck=-5, head=(0, -10), sh_l=(0, -5), sh_r=(0, -3),
             arm_l=(-70, -40, -6), fore_l=-22, arm_r=(0, 0, 22), fore_r=-36, legs=(-32, 26, 24, 10), heel=(0, 4))
# 2 段目の終わり（= 3 段目の始め）：刃を右前（体の前を横切った先）へ振り切って、少し戻した構え
READY_R = sp(hips=(2, -5), spine=(8, -6), chest=(2, -12), neck=5, head=(0, 10), sh_l=(0, -6), sh_r=(0, -3),
             arm_l=(-68, 24, 6), fore_l=-24, arm_r=(6, 0, 24), fore_r=-36, legs=(-30, 24, 24, 10), heel=(0, 4))

# 振り幅（刃の先の向き）：右 70 度 → 左 85 度（振り抜き）→ 左 95 度（行き過ぎ）→ 左前 55 度。ゲームのカメラは後ろにあるので、
# 刃を体の前〜横に置いたままにする（左後ろまで回すと、カメラからは腕に隠れて見えない）。
# 大きさは体のひねり（腰 ±14〜16、背骨 ±16、胸 ±28〜32）で出す。反対の腕（銃）は振り抜きで反動のように大きく開く。


def combo1() -> Clip:
    """右から左への横薙ぎ（左腕の光刃）。17 こま = 0.283 秒"""
    # 予備動作：体を右へ深くひねり、刃を胸の前に引きつけて（肘を曲げて）右後ろ上へ。銃の腕は内に抱える。重心は後ろ（右）の足
    coil = sp(hips=(0, -16), spine=(0, -16), chest=(-6, -30), neck=14, head=(-2, 32), sh_l=(2, 12), sh_r=(0, 6),
              arm_l=(-92, 50, 0), fore_l=-48, arm_r=(-24, 0, 4), fore_r=-65, legs=(-20, 14, 26, 8), heel=(0, 10))
    # 振り抜き：腰→背骨→胸のひねりで左へ、腕は伸び切る。前の足を大きく踏み込んで腰が沈む。右腕は反動で後ろ外へ開く
    strike = sp(hips=(8, 14), spine=(16, 16), chest=(6, 28), neck=-12, head=(6, -26), sh_l=(-2, -16), sh_r=(0, -10),
                arm_l=(-88, -34, -6), fore_l=-4, arm_r=(18, 0, 48), fore_r=-28, legs=(-46, 34, 30, 6), heel=(0, 10))
    keys = [
        k(1, sp(hips=(0, -8), spine=(3, -10), chest=(-2, -20), neck=10, head=(0, 22), sh_l=(0, 6), sh_r=(0, 4),
                arm_l=(-78, 36, 6), fore_l=-40, arm_r=(-16, 0, 6), fore_r=-55, legs=(-22, 16, 24, 6), heel=(0, 8)),
          'QUAD', 'EASE_IN'),
        k(4, coil, 'LINEAR'),
        k(5, between(coil, strike, LEAD_1), 'LINEAR'),
        k(6, between(coil, strike, LEAD_2), 'LINEAR'),
        k(7, strike, 'SINE', 'EASE_OUT'),
        # 行き過ぎ：腕と胸はさらに先へ、腰は少し戻り始める
        k(9, sp(hips=(10, 12), spine=(18, 19), chest=(7, 32), neck=-14, head=(8, -32), sh_l=(-2, -18), sh_r=(0, -12),
                arm_l=(-84, -38, -8), fore_l=0, arm_r=(24, 0, 56), fore_r=-24, legs=(-48, 36, 30, 8), heel=(0, 10)),
          'CUBIC', 'EASE_OUT'),
        # 戻り：ゆっくり構えへ
        k(14, sp(hips=(4, 7), spine=(10, 9), chest=(3, 16), neck=-7, head=(3, -14), sh_l=(0, -8), sh_r=(0, -6),
                 arm_l=(-74, -42, -6), fore_l=-16, arm_r=(6, 0, 30), fore_r=-34, legs=(-36, 28, 26, 10), heel=(0, 6)),
          'SINE', 'EASE_IN_OUT'),
        k(18, READY_L),
    ]
    return Clip('combo1', 17, keys, loop=False, fps=SWORD_FPS, ground=True)


def combo2() -> Clip:
    """左から右への切り返し。18 こま = 0.30 秒"""
    # 予備動作：体を左へ深くひねり、刃を左上へ引く。銃の腕は内に抱える。重心は前（左）の足
    coil = sp(hips=(0, 16), spine=(-2, 16), chest=(-8, 30), neck=-14, head=(-4, -30), sh_l=(4, 10), sh_r=(0, -4),
              arm_l=(-96, -46, -12), fore_l=-40, arm_r=(-18, 0, 10), fore_r=-60, legs=(-26, 20, 22, 6), heel=(0, 8))
    # 振り抜き：腰→背骨→胸で右へ、腕は伸び切って体の前を横切る。右腕は反動で後ろ外へ大きく開く（刃の通り道からも逃げる）
    strike = sp(hips=(8, -14), spine=(16, -16), chest=(6, -28), neck=12, head=(6, 26), sh_l=(-2, -18), sh_r=(0, -12),
                arm_l=(-88, 30, 6), fore_l=-4, arm_r=(36, 0, 46), fore_r=-26, legs=(-34, 30, 32, 2), heel=(0, 10))
    keys = [
        k(1, READY_L, 'QUAD', 'EASE_IN'),
        k(5, coil, 'LINEAR'),
        k(6, between(coil, strike, LEAD_1), 'LINEAR'),
        k(7, between(coil, strike, LEAD_2), 'LINEAR'),
        k(8, strike, 'SINE', 'EASE_OUT'),
        k(10, sp(hips=(10, -12), spine=(18, -18), chest=(7, -32), neck=14, head=(8, 30), sh_l=(-2, -20), sh_r=(0, -12),
                 arm_l=(-84, 34, 8), fore_l=0, arm_r=(42, 0, 52), fore_r=-22, legs=(-38, 34, 32, 4), heel=(0, 10)),
          'CUBIC', 'EASE_OUT'),
        k(15, sp(hips=(4, -7), spine=(10, -9), chest=(3, -16), neck=7, head=(3, 14), sh_l=(0, -8), sh_r=(0, -6),
                 arm_l=(-72, 26, 6), fore_l=-18, arm_r=(12, 0, 30), fore_r=-34, legs=(-32, 26, 26, 10), heel=(0, 6)),
          'SINE', 'EASE_IN_OUT'),
        k(19, READY_R),
    ]
    return Clip('combo2', 18, keys, loop=False, fps=SWORD_FPS, ground=True)


def combo3() -> Clip:
    """振り下ろし（とどめ）。27 こま = 0.45 秒。膝を上げて大きく振りかぶり、踏み込みながら叩きつけ、沈んだ姿勢を少し保つ"""
    # 振りかぶり：上腕を頭の上の左へ（Z 正で外へ開いて髪に入らない）。背を反らして体を左へひねり、前（左）の膝を上げ、
    # 後ろの足はつま先立ち。銃の腕は胸の前に抱える
    peak = sp(hips=(-4, 12), spine=(-18, 10), chest=(-12, 16), neck=-8, head=(-8, -16), sh_l=(14, 8), sh_r=(0, -4),
              arm_l=(-160, -12, 30), fore_l=-45, arm_r=(-20, 0, 18), fore_r=-70, legs=(-34, 58, 18, 4), heel=(0, 14),
              lift=(True, False))
    # 叩きつけ：前の足を踏み下ろして深く沈み、腰→背骨→胸が折れて腕が最後に振り下りる。前傾 48 度なので上腕は -112（世界で前下 64 度）。
    # 右腕は反動で後ろ上へ大きく開く
    impact = sp(hips=(10, -8), spine=(36, -10), chest=(12, -14), neck=6, head=(18, 8), sh_l=(-6, -16), sh_r=(0, -8),
                arm_l=(-112, 0, -6), fore_l=-6, arm_r=(46, 0, 44), fore_r=-20, legs=(-56, 38, 36, 4), heel=(0, 10))
    keys = [
        k(1, READY_R, 'CUBIC', 'EASE_IN'),
        k(7, peak, 'LINEAR', lifted=('foot.L',)),
        k(8, peak, 'LINEAR', lifted=('foot.L',)),
        k(9, between(peak, impact, {'hips': 0.7, 'spine': 0.6, 'chest': 0.4, 'head': 0.4, 'sh': 0.4, 'arm_l': 0.15, 'arm_r': 0.3, 'legs': 0.6}),
          'LINEAR', lifted=('foot.L',)),
        k(10, between(peak, impact, {'hips': 1.0, 'spine': 0.95, 'chest': 0.85, 'head': 0.8, 'sh': 0.9, 'arm_l': 0.6, 'arm_r': 0.75, 'legs': 0.95}),
          'LINEAR'),
        k(11, impact, 'SINE', 'EASE_OUT'),
        # 行き過ぎ：さらに沈む
        k(13, sp(hips=(12, -9), spine=(42, -12), chest=(14, -16), neck=6, head=(22, 9), sh_l=(-8, -18), sh_r=(0, -8),
                 arm_l=(-110, 0, -4), fore_l=0, arm_r=(52, 0, 48), fore_r=-16, legs=(-58, 40, 36, 6), heel=(0, 10)),
          'SINE', 'EASE_OUT'),
        # 叩きつけた姿勢を保つ（わずかに戻る）
        k(19, sp(hips=(10, -8), spine=(38, -10), chest=(12, -14), neck=6, head=(18, 8), sh_l=(-6, -16), sh_r=(0, -8),
                 arm_l=(-104, 0, -6), fore_l=-4, arm_r=(46, 0, 42), fore_r=-22, legs=(-56, 38, 34, 4), heel=(0, 10)),
          'CUBIC', 'EASE_OUT'),
        # 立ち直り（idle へつながる）
        k(28, sp(spine=(6, 0), arm_l=(-26, 0, -10), fore_l=-22, arm_r=(-10, 0, 8), fore_r=-35, legs=(-30, 25, 25, 20))),
    ]
    return Clip('combo3', 27, keys, loop=False, fps=SWORD_FPS, ground=True)


def air() -> Clip:
    start = {'chest': (0, -35, 0), 'upper_arm.L': (-70, 0, 45), 'forearm.L': (-40, 0, 0),
             'thigh.L': (-60, 0, 0), 'shin.L': (80, 0, 0), 'thigh.R': (-20, 0, 0), 'shin.R': (60, 0, 0)}
    end = dict(start, **{'chest': (5, 35, 0), 'upper_arm.L': (-70, 0, -55), 'forearm.L': (-10, 0, 0)})
    return Clip('air', 9, [(1, start), (5, end), (10, end)], loop=False)


def lunge() -> Clip:
    start = stance({'spine': (20, 0, 0), 'upper_arm.L': (30, 0, -10), 'forearm.L': (-60, 0, 0),
                    'thigh.L': (-50, 0, 0), 'shin.L': (40, 0, 0), 'thigh.R': (45, 0, 0), 'shin.R': (30, 0, 0)})
    end = stance({'spine': (25, 20, 0), 'upper_arm.L': (-95, 0, 0), 'forearm.L': (0, 0, 0),
                  'thigh.L': (-55, 0, 0), 'shin.L': (40, 0, 0), 'thigh.R': (40, 0, 0), 'shin.R': (10, 0, 0)})
    return Clip('lunge', 10, [(1, start), (5, end), (11, end)], loop=False)


def charge() -> Clip:
    """溜め斬り：大きく回転して薙ぎ払う"""
    start = stance({'spine': (5, -60, 0), 'chest': (0, -30, 0), 'upper_arm.L': (-60, 0, 70), 'forearm.L': (-50, 0, 0)})
    mid = stance({'spine': (10, 0, 0), 'chest': (0, 0, 0), 'upper_arm.L': (-80, 0, -20), 'forearm.L': (0, 0, 0)})
    end = stance({'spine': (10, 60, 0), 'chest': (0, 30, 0), 'upper_arm.L': (-70, 0, -80), 'forearm.L': (0, 0, 0)})
    return Clip('charge', 15, [(1, start), (5, start), (9, mid), (12, end), (16, end)], loop=False)


def all_clips() -> list[Clip]:
    return [idle(), run(), jump(), fall(), dash(), hurt(), dead(), drill(), combo1(), combo2(), combo3(), air(),
            lunge(), charge()]
