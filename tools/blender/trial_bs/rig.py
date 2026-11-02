"""haru_bs の骨と重み（段 2）。スキル集の rigging（+ references/humanoid-rig.md）の手順：
  Skeleton Design → Bone Placement → Hierarchy → Constraints/IK → Weight Painting → Deformation Test → Export Prep

  .venv-blender/bin/python tools/blender/trial_bs/build_haru_bs.py --rig     （モデルから作り直して骨と重みまで）

骨の名前：スキル集の決まり（`L_arm_upper`・`spine_01` など）ではなく、ゲームが名前で探す 29 本（ゲームの約束が勝つ）。
骨格の物体の名前はスキル集の `ARM_[Asset]`（ゲームは Skeleton3D を型で探すので、物体の名前は問わない）。
骨の頭の位置は段 1 の関節 proportions.J（絵の画素から測った位置。体の形もこの関節で作ってある）。
重み：
  ・服・体（曲がる物）：Blender の自動の重み（熱の拡散）から始め、物ごとに使ってよい骨に絞り、左右の島で反対側の手足の骨を消し、
    つなぎ目をならして（隣の頂点との平均）、1 頂点 4 本まで・合計 1 に直す（rigging の Weight Painting 1〜5）
  ・硬い物：1 本の骨に 1.0（頭・ゴーグル・靴・ポーチ・板・籠手）
  ・髪の塊：根元は head、先へ向かってなめらかに hair.* へ（ゲームの揺れの骨。根元・生え際は揺れない）
光刃・スパークは骨の子（光刃は forearm.L、スパークは hand.R）。光刃の原点は籠手の射出口（ゲームが溜めの間 0.6 倍に縮める）。
"""
import math
import bmesh
import bpy
from mathutils import Vector, Matrix

from proportions import J

ARM_NAME = 'ARM_HaruBS'

# ---------------------------------------------------------------- 骨（名前・頭・尾・親・つなぐか）
# 髪・ポーチの骨は物体の形から決める（hair_bones()・pouch_bones()）
BODY_BONES = [
    ('root', Vector((0, 0, 0)), Vector((0, 0.20, 0)), None, False),
    ('hips', J['hips'], J['spine'], 'root', False),
    ('spine', J['spine'], J['chest'], 'hips', True),
    ('chest', J['chest'], J['neck'], 'spine', True),
    ('neck', J['neck'], J['head'], 'chest', True),
    ('head', J['head'], J['head_top'], 'neck', True),
]
for _s in ('L', 'R'):
    BODY_BONES += [
        ('shoulder.' + _s, J['shoulder.' + _s], J['upper_arm.' + _s], 'chest', False),
        ('upper_arm.' + _s, J['upper_arm.' + _s], J['forearm.' + _s], 'shoulder.' + _s, True),
        ('forearm.' + _s, J['forearm.' + _s], J['hand.' + _s], 'upper_arm.' + _s, True),
        ('hand.' + _s, J['hand.' + _s], J['hand_end.' + _s], 'forearm.' + _s, True),
        ('thigh.' + _s, J['thigh.' + _s], J['shin.' + _s], 'hips', False),
        ('shin.' + _s, J['shin.' + _s], J['foot.' + _s], 'thigh.' + _s, True),
        ('foot.' + _s, J['foot.' + _s], J['toe.' + _s], 'shin.' + _s, True),
    ]

HAIR_REGIONS = {
    'hair.front': 'SM_Hair_HaruBS_Front', 'hair.top': 'SM_Hair_HaruBS_Top',
    'hair.back.L': 'SM_Hair_HaruBS_Back_L', 'hair.back.R': 'SM_Hair_HaruBS_Back_R',
    'hair.nape': 'SM_Hair_HaruBS_Nape', 'hair.side.L': 'SM_Hair_HaruBS_Side_L', 'hair.side.R': 'SM_Hair_HaruBS_Side_R',
}
CONTRACT_BONES = ['root', 'hips', 'spine', 'chest', 'neck', 'head', 'hair.front', 'hair.top', 'hair.back.L', 'hair.back.R',
                  'hair.nape', 'hair.side.L', 'hair.side.R', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L', 'shoulder.R',
                  'upper_arm.R', 'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R',
                  'pouch.L', 'pouch.R']

# ---------------------------------------------------------------- 重みの決まり（物ごと）
LIMB = ('shoulder', 'upper_arm', 'forearm', 'hand', 'thigh', 'shin', 'foot', 'pouch')
AUTO = {
    'SM_Char_HaruBS_Body': ['chest', 'neck', 'head', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L',
                            'shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R'],
    'SM_Cloth_HaruBS_Gloves': ['forearm.L', 'hand.L', 'forearm.R', 'hand.R'],
    'SM_Cloth_HaruBS_Shirt': ['hips', 'spine', 'chest', 'neck'],
    'SM_Cloth_HaruBS_Jacket': ['hips', 'spine', 'chest', 'shoulder.L', 'shoulder.R', 'upper_arm.L', 'upper_arm.R'],
    'SM_Cloth_HaruBS_Collar': ['chest', 'neck'],
    'SM_Cloth_HaruBS_Sleeves': ['chest', 'shoulder.L', 'upper_arm.L', 'shoulder.R', 'upper_arm.R'],
    'SM_Cloth_HaruBS_Trousers': ['hips', 'thigh.L', 'shin.L', 'thigh.R', 'shin.R'],
    'SM_Cloth_HaruBS_Leggings': ['thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R'],
    'SM_Cloth_HaruBS_AnkleCuffs': ['shin.L', 'foot.L', 'shin.R', 'foot.R'],
    'SM_Frame_HaruBS_ShoulderStraps': ['spine', 'chest', 'shoulder.L', 'shoulder.R'],
}
# 硬い物：骨の名前（'*' は左右の島で .L/.R）。組 (骨, 重み) の並びは混ぜる
RIGID = {
    'SM_Char_HaruBS_Head': 'head', 'SM_Acc_HaruBS_Goggles': 'head', 'SM_Acc_HaruBS_GoggleStrap': 'head',
    'SM_Hair_HaruBS_Cap': 'head',
    'SM_Cloth_HaruBS_Belt': 'hips', 'SM_Cloth_HaruBS_Buckle': 'hips',
    'SM_Cloth_HaruBS_Pouch_L': 'pouch.L', 'SM_Cloth_HaruBS_Pouch_R': 'pouch.R',
    'SM_Cloth_HaruBS_Boots': 'foot.*', 'SM_Cloth_HaruBS_Soles': 'foot.*',
    'SM_Frame_HaruBS_BackPanel': 'chest', 'SM_Frame_HaruBS_ShoulderPlate_R': 'upper_arm.R',
    'SM_Frame_HaruBS_Gauntlet_L': 'forearm.L',
    'SM_Frame_HaruBS_KneePads': 'shin.*', 'SM_Frame_HaruBS_ShinPlates': 'shin.*',
    'SM_Frame_HaruBS_ThighPlate_R': [('thigh.R', 0.7), ('hips', 0.3)],
}
BONE_PARENTED = {'LightBlade': 'forearm.L', 'SM_Weapon_HaruBS_SparkGun': 'hand.R'}


def _sel_only(objs, active):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


# ---------------------------------------------------------------- 骨の位置（髪・ポーチ）
def hair_bones():
    """髪の地域ごとの骨：頭 = 塊の上の端（根元）、尾 = 根元から最も遠い先の平均。親は head"""
    out = []
    for bone, obn in HAIR_REGIONS.items():
        ob = bpy.data.objects[obn]
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
        zs = sorted(v.z for v in vs)
        ztop = zs[int(len(zs) * 0.90)]
        top = [v for v in vs if v.z >= ztop]
        h = sum(top, Vector()) / len(top)
        far = sorted(vs, key=lambda v: (v - h).length)
        tip = far[int(len(far) * 0.75):]
        t = sum(tip, Vector()) / len(tip)
        if (t - h).length < 0.04:
            t = h + (t - h).normalized() * 0.04
        out.append((bone, h, t, 'head', False))
    return out


def pouch_bones():
    out = []
    for s in ('L', 'R'):
        ob = bpy.data.objects['SM_Cloth_HaruBS_Pouch_' + s]
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
        c = sum(vs, Vector()) / len(vs)
        top = max(v.z for v in vs)
        bot = min(v.z for v in vs)
        out.append(('pouch.' + s, Vector((c.x, c.y + 0.010, top)), Vector((c.x, c.y, bot)), 'hips', False))
    return out


def _roll_axis(name, head, tail):
    """骨の Z 軸を向ける先：曲がる骨は前（-Y）。前後を向く骨（足・根）は上"""
    d = (tail - head).normalized()
    if abs(d.y) > 0.7:
        return Vector((0, 0, 1))
    return Vector((0, -1, 0))


def make_armature(coll):
    arm = bpy.data.armatures.new(ARM_NAME)
    ob = bpy.data.objects.new(ARM_NAME, arm)
    coll.objects.link(ob)
    arm.display_type = 'OCTAHEDRAL'
    bones = BODY_BONES + hair_bones() + pouch_bones()
    _sel_only([ob], ob)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for name, h, t, parent, conn in bones:
        b = eb.new(name)
        b.head = h
        b.tail = t
        b.align_roll(_roll_axis(name, h, t))
        b.use_deform = True
    for name, h, t, parent, conn in bones:
        if parent:
            eb[name].parent = eb[parent]
            eb[name].use_connect = conn
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return ob


# ---------------------------------------------------------------- 重み
def _islands(me):
    """つながった頂点の島（頂点の番号の並びのリスト）"""
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    seen = [False] * len(me.vertices)
    out = []
    for i in range(len(me.vertices)):
        if seen[i]:
            continue
        st = [i]
        seen[i] = True
        isl = []
        while st:
            k = st.pop()
            isl.append(k)
            for n in adj[k]:
                if not seen[n]:
                    seen[n] = True
                    st.append(n)
        out.append(isl)
    return out, adj


def _get_w(ob):
    """頂点ごとの {骨: 重み}"""
    names = {g.index: g.name for g in ob.vertex_groups}
    return [{names[g.group]: g.weight for g in v.groups if g.weight > 0.0} for v in ob.data.vertices]


def _set_w(ob, W):
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {}
    for i, w in enumerate(W):
        for b, x in w.items():
            if x <= 0.0:
                continue
            g = groups.get(b) or ob.vertex_groups.new(name=b)
            groups[b] = g
            g.add([i], x, 'REPLACE')


def _clean(w, k=4):
    """1 頂点 k 本まで、合計 1"""
    items = sorted(w.items(), key=lambda t: -t[1])[:k]
    items = [(b, x) for b, x in items if x > 0.01]
    s = sum(x for _, x in items)
    if s <= 0:
        return {}
    return {b: x / s for b, x in items}


def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (p - (a + ab * t)).length


def _side_of(x):
    return 'L' if x > 0.03 else ('R' if x < -0.03 else None)


def auto_weights(arm, ob, allowed):
    """自動の重み（熱の拡散）→ 使ってよい骨に絞る → 左右の島 → ならす → 4 本・合計 1"""
    _sel_only([ob, arm], arm)
    ok = True
    par, mw = ob.parent, ob.matrix_world.copy()
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except RuntimeError as e:
        ok = False
        print('AUTO WEIGHTS FAILED', ob.name, e)
    if par is not None:
        # parent_set は親を骨格にする。フレームの部品は群（Frame_*）の子に戻す
        ob.parent = par
        ob.matrix_world = mw
    W = _get_w(ob)
    me = ob.data
    isl, adj = _islands(me)
    side = [None] * len(me.vertices)
    for il in isl:
        cx = sum(me.vertices[i].co.x for i in il) / len(il)
        s = _side_of(cx)
        for i in il:
            side[i] = s
    bones = arm.data.bones
    empty = 0
    for i, v in enumerate(me.vertices):
        w = {b: x for b, x in W[i].items() if b in allowed}
        if side[i]:
            w = {b: x for b, x in w.items() if not (b.split('.')[0] in LIMB and b.endswith('.' + ('R' if side[i] == 'L' else 'L')))}
        if sum(w.values()) < 1e-4:
            # 熱が届かなかった頂点：いちばん近い骨（使ってよい骨・同じ側）
            empty += 1
            p = ob.matrix_world @ v.co
            cand = [b for b in allowed if not (side[i] and b.split('.')[0] in LIMB and b.endswith('.' + ('R' if side[i] == 'L' else 'L')))]
            best = min(cand, key=lambda b: _seg_dist(p, bones[b].head_local, bones[b].tail_local))
            w = {best: 1.0}
        W[i] = w
    # ならす（つなぎ目の勾配。rigging：曲がる所の真ん中で 1.0/0.0 にしない）
    for _ in range(2):
        W2 = []
        for i in range(len(W)):
            acc = dict((b, x * 2.0) for b, x in W[i].items())
            n = 2.0
            for k in adj[i]:
                for b, x in W[k].items():
                    acc[b] = acc.get(b, 0.0) + x
                n += 1.0
            W2.append({b: x / n for b, x in acc.items()})
        W = W2
    W = [_clean(w) for w in W]
    _set_w(ob, W)
    return ok, empty


def rigid_weights(ob, spec):
    me = ob.data
    isl, _ = _islands(me)
    W = [{} for _ in me.vertices]
    for il in isl:
        cx = sum((ob.matrix_world @ me.vertices[i].co).x for i in il) / len(il)
        if isinstance(spec, list):
            w = dict(spec)
        elif spec.endswith('.*'):
            w = {spec[:-1] + ('L' if cx > 0 else 'R'): 1.0}
        else:
            w = {spec: 1.0}
        for i in il:
            W[i] = dict(w)
    _set_w(ob, W)


def hair_weights(arm, ob, bone):
    """根元は head、先へ向かって hair.*（smoothstep。ゲームの揺れは先ほど大きく、生え際は動かない）"""
    b = arm.data.bones[bone]
    h, t = b.head_local, b.tail_local
    ax = t - h
    W = []
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        u = max(0.0, min(1.0, (p - h).dot(ax) / ax.length_squared))
        u = max(0.0, min(1.0, (u - 0.05) / 0.55))
        s = u * u * (3 - 2 * u)
        W.append(_clean({bone: s, 'head': 1.0 - s}))
    _set_w(ob, W)


def fist_to_hand(ob, side):
    """拳・開いた手の島（手首より先）は手の骨に 1.0（指の骨は約束に無い）"""
    s = '.' + side
    a, e = J['hand' + s], J['hand_end' + s]
    d = (e - a).normalized()
    me = ob.data
    isl, _ = _islands(me)
    W = _get_w(ob)
    for il in isl:
        c = sum((ob.matrix_world @ me.vertices[i].co for i in il), Vector()) / len(il)
        if (c - a).dot(d) > 0.0 and (c.x > 0) == (side == 'L'):
            for i in il:
                W[i] = {'hand' + s: 1.0}
    _set_w(ob, W)


def bind(arm, ob):
    """骨格の修飾子と親（すでに parent_set で付いていれば何もしない）"""
    if not any(m.type == 'ARMATURE' for m in ob.modifiers):
        m = ob.modifiers.new('Armature', 'ARMATURE')
        m.object = arm
    if ob.parent is None:
        # 外装フレームの部品は群（Frame_*、骨格の子）の子のまま（書き出しで群ごとに 1 つにまとめる）
        mw = ob.matrix_world.copy()
        ob.parent = arm
        ob.matrix_world = mw


def apply_modifiers(ob):
    """重みの前に、骨格以外の修飾子（Solidify）を適用する（書き出しでも同じ形になる）"""
    for m in list(ob.modifiers):
        if m.type == 'ARMATURE':
            continue
        _sel_only([ob], ob)
        bpy.ops.object.modifier_apply(modifier=m.name)


def bone_parent(arm, ob, bone, origin=None):
    """骨の子にする（ゲームでは BoneAttachment3D の下）。origin があれば物体の原点をそこへ（形は動かさない）"""
    if origin is not None:
        mw = ob.matrix_world.copy()
        local = mw.inverted() @ origin
        ob.data.transform(Matrix.Translation(-local))
        ob.matrix_world = mw @ Matrix.Translation(local)
    mw = ob.matrix_world.copy()
    ob.parent = arm
    ob.parent_type = 'BONE'
    ob.parent_bone = bone
    ob.matrix_world = mw


def build_rig(blade_origin=None):
    """モデルの入った今の場面に骨と重みを付ける。戻り値：骨格の物体と、重みの報告"""
    top = bpy.data.collections['COL_HaruBS']
    c_rig = bpy.data.collections.get('COL_Rig') or bpy.data.collections.new('COL_Rig')
    if c_rig.name not in top.children:
        top.children.link(c_rig)
    arm = make_armature(c_rig)
    rep = {}
    for ob in [o for o in bpy.data.objects if o.type == 'MESH']:
        if ob.name in BONE_PARENTED:
            continue
        apply_modifiers(ob)
    for obn, allowed in AUTO.items():
        ob = bpy.data.objects[obn]
        ok, empty = auto_weights(arm, ob, allowed)
        rep[obn] = ('auto' if ok else 'auto-failed→nearest', empty)
    fist_to_hand(bpy.data.objects['SM_Char_HaruBS_Body'], 'R')
    fist_to_hand(bpy.data.objects['SM_Char_HaruBS_Body'], 'L')
    fist_to_hand(bpy.data.objects['SM_Cloth_HaruBS_Gloves'], 'R')
    for obn, spec in RIGID.items():
        rigid_weights(bpy.data.objects[obn], spec)
        rep[obn] = ('rigid', str(spec))
    for bone, obn in HAIR_REGIONS.items():
        hair_weights(arm, bpy.data.objects[obn], bone)
        rep[obn] = ('hair', bone)
    for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o.name not in BONE_PARENTED]:
        bind(arm, ob)
    for e in ('Frame_core', 'Frame_arm', 'Frame_legs'):
        g = bpy.data.objects[e]
        mw = g.matrix_world.copy()
        g.parent = arm
        g.matrix_world = mw
    bone_parent(arm, bpy.data.objects['LightBlade'], 'forearm.L', origin=blade_origin)
    bone_parent(arm, bpy.data.objects['SM_Weapon_HaruBS_SparkGun'], 'hand.R')
    return arm, rep


def weight_report(arm):
    """重みの確かめ：影響の数の最大、合計が 1 でない頂点、重みの無い頂点"""
    out = {}
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.name in BONE_PARENTED:
            continue
        W = _get_w(ob)
        mx = max((len(w) for w in W), default=0)
        bad = sum(1 for w in W if abs(sum(w.values()) - 1.0) > 1e-3)
        none = sum(1 for w in W if not w)
        out[ob.name] = (mx, bad, none, sorted({b for w in W for b in w}))
    return out


# ---------------------------------------------------------------- 脚の IK（humanoid-rig：足の目標 ＋ 膝の極）
def add_leg_ik(arm):
    """脚ごとに足首の目標（空の物体 IK_foot.L/R）と膝の極（IK_knee.L/R）を作り、shin に IK（2 本）を付ける。
    極の角度（pole_angle）は、基準の姿勢のまま目標を足首に置いたときに脚が動かない角度を探して決める。
    書き出しの前に焼いて（anim.bake_legs）外す。戻り値：{side: (目標, 極, 制約)}"""
    sc = bpy.context.scene
    c = bpy.data.collections.get('COL_Rig')
    out = {}
    for s in ('L', 'R'):
        tg = bpy.data.objects.new('IK_foot.' + s, None)
        pl = bpy.data.objects.new('IK_knee.' + s, None)
        for e in (tg, pl):
            e.empty_display_size = 0.04
            c.objects.link(e)
        tg.location = J['foot.' + s]
        pl.location = J['shin.' + s] + Vector((0, -0.5, 0.0))
        pb = arm.pose.bones['shin.' + s]
        ik = pb.constraints.new('IK')
        ik.target = tg
        ik.pole_target = pl
        ik.chain_count = 2
        ik.use_tail = True
        ik.use_stretch = False
        out[s] = (tg, pl, ik)
    bpy.context.view_layer.update()

    def err(s):
        e = 0.0
        for b in ('thigh.' + s, 'shin.' + s):
            pb = arm.pose.bones[b]
            e += (pb.tail - arm.data.bones[b].tail_local).length
        return e

    for s, (tg, pl, ik) in out.items():
        best = None
        for k in range(-180, 181, 5):
            ik.pole_angle = math.radians(k)
            bpy.context.view_layer.update()
            e = err(s)
            if best is None or e < best[0]:
                best = (e, k)
        lo = best[1]
        for k10 in range(lo * 10 - 50, lo * 10 + 51, 2):
            ik.pole_angle = math.radians(k10 / 10.0)
            bpy.context.view_layer.update()
            e = err(s)
            if e < best[0]:
                best = (e, k10 / 10.0)
        ik.pole_angle = math.radians(best[1])
        bpy.context.view_layer.update()
        print('IK pole angle', s, best[1], 'rest error %.5f m' % err(s))
    return out
