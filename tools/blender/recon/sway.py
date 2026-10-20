"""揺れの骨（2 次の動き）：髪の房のまとまりと、帯から下がるポーチに骨を足し、重みを付ける（ai_character.py --sway-bones）。

ゲームは骨を SpringBoneSimulator3D で揺らす（godot/scripts/view/haru_sway.gd。走り出し・止まる・着地・ダッシュ・振り向きで
遅れて追いつく）。骨の形・重みだけをここで決め、揺れ方（固さ・減衰・当たり）はゲームの側で決める。
設定はキャラクターの部品の表（chars/<id>_parts.py）の SWAY。無いキャラクター・--sway-bones の無い作り直しは今までどおり（骨 20 本）。

■ 髪（SWAY['hair']）
  髪の頂点：体の材質（<id>_body）の面の、髪の色（テクスチャ。costume.strap_push と同じ決まり）で、頭の中心から 0.3 m 以内・
  高さ hair_z_min より上の頂点。
  1. 髪の土台の面（帽子）の半径 r_cap：頭の中心から見た向きの近く（cap_cone 度の円すい）の髪の頂点の半径の cap_pct 分位を、
     さらに近く（cap_smooth 度）でならしたもの。房の先ほど r − r_cap が大きい。
  2. 外へ出た長さの重み w_out = smoothstep(excess[0], excess[1], r − r_cap)：土台は頭に付いたまま、房の先ほど揺れる。
  3. 髪でない面（顔・耳・ゴーグル・ヒモ・えり）からの距離の重み w_clr = smoothstep(clear[0], clear[1], 距離)：
     ゴーグル・ヒモの下・生え際・耳のまわりの髪は動かさない（揺れても顔・ゴーグル・ヒモを突き抜けない）。
  4. まとまり k（名前・向き a_k・広がり σ_k 度・重みの上限 m_k）への分け方：exp(−(角度(頂点の向き, a_k)/σ_k)²) を
     上位 2 つで割り合い。揺れの骨の重み = m_k × w_out × w_clr × 割合。もとの頭・首の重みは残りの割合に縮める。
  骨：根 = 頭の中心 + a_k × (まとまりの r_cap の中央値 − pivot_in)、先 = まとまりの房の先の重心（重み² の平均）。親は head。
  根は髪の外の面より pivot_in（4 cm）内＝地肌のあたり：房の先までの腕の長さが約 8 cm になり、同じ角度でも先がよく動く
  （1 回目の 1.5 cm 内の根では、ゲームのカメラの距離でほとんど見えなかった）。
■ ポーチ（SWAY['pouches']：部品の名前 → 骨の名前）
  部品の頂点を、その骨（親は hips）に重み 1 で付ける（ai_character.add_costume）。骨は箱の上の面の中心から下の面の中心へ。
座標は再構築の座標（Blender。本人の左 +X、後ろ +Y、上 +Z、靴底 z = 0）。髪・ポーチは腕を下ろしても動かないので、A ポーズと同じ。
"""
from __future__ import annotations

import math

import numpy as np

# 既定（部品の表の SWAY で上書き）
DEFAULTS = {
    'center': (0.0, 0.03, 1.37),
    'hair_z_min': 1.20,
    'radius_max': 0.30,
    'cap_cone': 20.0,
    'cap_pct': 20.0,
    'cap_smooth': 10.0,
    'excess': (-0.010, 0.025),
    'clear': (0.004, 0.022),
    'pivot_in': 0.040,
    'tail_min': 0.05,
    'hair': [],
    'pouches': {},
    'pouch_pivot_down': 0.01,
}


def spec_of(CO) -> dict | None:
    """部品の表（costume モジュール CO）の SWAY を既定とまぜる。無ければ None"""
    s = getattr(CO, 'SWAY', None)
    if not s:
        return None
    out = dict(DEFAULTS)
    out.update(s)
    return out


def hair_color(vc: np.ndarray) -> np.ndarray:
    """髪の色（下地の色。costume.strap_push・ai_character.add_costume と同じ決まり：赤みが青より 0.06 以上、暗い）"""
    return (vc[:, 0] - vc[:, 2] > 0.06) & (vc[:, 0] < 0.55)


def _smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / max(1e-9, e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _chord(deg: float) -> float:
    return 2.0 * math.sin(math.radians(deg) * 0.5)


def hair_weights(co: np.ndarray, hair: np.ndarray, other: np.ndarray, spec: dict) -> dict:
    """髪の頂点の揺れの骨の重みと骨の位置。
    co：体の頂点 (n,3)、hair：髪の頂点の印 (n,)、other：髪でない面の点 (m,3)（頭のまわりだけでよい）。
    返り値：{'weights': {骨の名前: (頂点の番号, 重み)}, 'bones': [(名前, 根, 先)], 'report': {...}}"""
    from scipy.spatial import cKDTree
    hc = np.asarray(spec['center'], float)
    idx = np.nonzero(hair)[0]
    P = co[idx] - hc
    r = np.linalg.norm(P, axis=1)
    u = P / np.maximum(r[:, None], 1e-9)
    tree = cKDTree(u)
    # 1. 髪の土台の面の半径（向きの円すいの中の低い分位 → ならす）
    nb = tree.query_ball_point(u, _chord(spec['cap_cone']))
    rc = np.array([np.percentile(r[n], spec['cap_pct']) for n in nb])
    nb2 = tree.query_ball_point(u, _chord(spec['cap_smooth']))
    rc = np.array([rc[n].mean() for n in nb2])
    excess = r - rc
    w_out = _smoothstep(spec['excess'][0], spec['excess'][1], excess)
    # 2. 髪でない面からの距離
    if len(other):
        dist, _ = cKDTree(other).query(co[idx])
    else:
        dist = np.full(len(idx), 1.0)
    w_clr = _smoothstep(spec['clear'][0], spec['clear'][1], dist)
    w = w_out * w_clr
    # 3. まとまりへの分け方
    regions = spec['hair']
    A = np.array([np.asarray(g[1], float) / np.linalg.norm(g[1]) for g in regions])
    sig = np.radians(np.array([float(g[2]) for g in regions]))
    cap = np.array([float(g[3]) for g in regions])
    ang = np.arccos(np.clip(u @ A.T, -1.0, 1.0))                  # (n, k)
    S = np.exp(-(ang / sig[None, :]) ** 2)
    # 上位 2 つだけ（影響する骨は 頭・首 ＋ 2 本まで）
    order = np.argsort(-S, axis=1)
    keep = np.zeros_like(S, bool)
    rows = np.arange(len(S))
    keep[rows, order[:, 0]] = True
    keep[rows, order[:, 1]] = True
    S = np.where(keep, S, 0.0)
    share = S / np.maximum(S.sum(1, keepdims=True), 1e-9)
    Wk = share * cap[None, :] * w[:, None]
    out_w = {}
    bones = []
    rep = {'hair_verts': int(len(idx)), 'moving_verts': int((Wk.sum(1) > 0.05).sum()),
           'cap_radius_mm': [round(float(np.percentile(rc, p)) * 1000, 1) for p in (5, 50, 95)],
           'excess_mm_p95': round(float(np.percentile(excess, 95)) * 1000, 1), 'regions': {}}
    for k, g in enumerate(regions):
        name = g[0]
        m = Wk[:, k] > 1e-3
        out_w[name] = (idx[m], Wk[m, k])
        core = share[:, k] > 0.5
        if not core.any():
            core = share[:, k] >= share[:, k].max() * 0.8
        r_piv = float(np.median(rc[core])) - spec['pivot_in']
        root = hc + A[k] * r_piv
        wt = (Wk[:, k] ** 2)
        if wt.sum() > 1e-6:
            tip = (co[idx] * wt[:, None]).sum(0) / wt.sum()
        else:
            tip = hc + A[k] * (r_piv + spec['tail_min'])
        d = tip - root
        if np.linalg.norm(d) < spec['tail_min']:
            d = (d / max(np.linalg.norm(d), 1e-9) if np.linalg.norm(d) > 1e-4 else A[k]) * spec['tail_min']
        tail = root + d
        bones.append((name, root, tail))
        rep['regions'][name] = {'verts': int(m.sum()), 'weight_max': round(float(Wk[:, k].max()), 3),
                                'weight_sum': round(float(Wk[:, k].sum()), 1),
                                'root': [round(float(c), 4) for c in root], 'tail': [round(float(c), 4) for c in tail]}
    return {'weights': out_w, 'bones': bones, 'report': rep}


def pouch_bone(V: np.ndarray, down: float) -> tuple[np.ndarray, np.ndarray]:
    """ポーチの箱の頂点から骨（根 = 上の面の中心の少し下、先 = 下の面の中心）"""
    z0, z1 = V[:, 2].min(), V[:, 2].max()
    c = V[:, :2].mean(0)
    return np.array([c[0], c[1], z1 - down]), np.array([c[0], c[1], z0])


def add_bones(arm, bones: list[tuple[str, np.ndarray, np.ndarray, str]]) -> None:
    """骨の物体に骨を足す（名前・根・先・親）。骨の物体の座標（拡大の前）"""
    import bpy
    from mathutils import Vector
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    for name, head, tail, parent in bones:
        b = eb.new(name)
        b.head = Vector(tuple(float(c) for c in head))
        b.tail = Vector(tuple(float(c) for c in tail))
        b.roll = 0.0
        b.parent = eb[parent]
        b.use_connect = False
        b.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')


def apply_hair_weights(body, weights: dict) -> int:
    """髪の頂点の重み：揺れの骨の重みを足し、もとの重みを残りの割合に縮める。変わった頂点だけ、影響を 4 本まで・
    合計 1 にそろえる（ほかの頂点の重みは 1 つも変えない）。返り値：重みの変わった頂点の数"""
    me = body.data
    n = len(me.vertices)
    tot = np.zeros(n)
    for name, (vi, w) in weights.items():
        tot[vi] += w
    tot = np.clip(tot, 0.0, 1.0)
    changed = np.nonzero(tot > 1e-4)[0]
    for vi in changed:
        for g in me.vertices[int(vi)].groups:
            g.weight = g.weight * (1.0 - tot[vi])
    for name, (vi, w) in weights.items():
        vg = body.vertex_groups.get(name) or body.vertex_groups.new(name=name)
        for i, wi in zip(vi, w):
            vg.add([int(i)], float(wi), 'REPLACE')
    gname = {g.index: g.name for g in body.vertex_groups}
    for vi in changed:
        v = me.vertices[int(vi)]
        ws = sorted(((g.weight, g.group) for g in v.groups), reverse=True)
        for w, gi in ws[4:] + [e for e in ws[:4] if e[0] <= 1e-6]:
            body.vertex_groups[gname[gi]].remove([int(vi)])
        ws = [e for e in ws[:4] if e[0] > 1e-6]
        s = sum(w for w, _ in ws[:4])
        if s > 1e-9:
            for w, gi in ws[:4]:
                body.vertex_groups[gname[gi]].add([int(vi)], w / s, 'REPLACE')
    return int(len(changed))
