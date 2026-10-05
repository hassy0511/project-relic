"""AI が作った 3D（TRELLIS.2 などの GLB）を、ゲームで動かせるキャラクターにする。

入力：A ポーズで立つ人物の GLB（骨なし・1 つの塊。発注書 W1-00 の条件で描いた絵から作ったもの）
出力：標準の人型の骨・重み・14 動作・銃・光刃・目印つきの GLB

  python tools/blender/models/ai_character.py --input <入力.glb> --out <出力.glb>
      [--turn 度]          正面が -Y（glTF では +Z）を向くように回す角度（向きが違うとき）
      [--keep-frame]       入力がすでに約束の座標（身長 1.55m、正面 -Y、靴底 z=0、胴の中心 x=y=0）のとき、
                           向き・大きさ・位置を一切動かさない（絵から起こしたハル。確認のカメラと画素を合わせるため）
      [--target-tris 数]   面を減らす目標。0 で減らさない。
                           省略時：テクスチャの付いた入力は減らさない（UV・顔の区画を崩さないため）、それ以外は 16000
      [--joints <json>]    関節の位置を手で直す（自動の推定を上書き。単位は m）
      [--gun <glb>]        銃を絵から起こした GLB（tools/blender/recon/gun.py の spark_gun.glb）にする。
                           省略時は箱の組み合わせの仮の銃
      [--blade-anchor auto|x,y,z]
                           光刃の根元（A ポーズの座標、m）。auto は左前腕の外側（小指側）のレールの手首側の端を
                           形から探す。省略時は従来どおり手首の外側
      [--grip-fist x,y,z]  （--gun のとき）右手を拳にして銃の握りを握らせる。値は A ポーズの掌の向き（ハルは
                           0,1,0 = 後ろ）。手を手の骨の軸まわりにねじって掌を体の内側へ向け、指の付け根から先を
                           握りのまわりに曲げる（指の骨が無いので、基準の姿勢のメッシュそのものを拳の形にする）
      [--fist-shapekey]    （--grip-fist のとき）拳を基準の姿勢に焼き込まず、シェイプキー 'fist' にする。基準の
                           姿勢は絵のとおりの開いた手。Godot の player_view.gd は読み込むと fist = 1 にする
      [--rest-arm-deg 度]  基準の姿勢の腕の開き（正面から見た真下からの角度）。前後の軸まわりだけで腕を下ろす
                           （腕の前後の傾き・肘の曲がりを保つ）。省略時は従来どおり標準の向きへ最短の回転で
      [--fill-unweighted 割合]
                           自動の重み（熱）が付かない頂点がこの割合（0〜1）までなら、全体を距離の重みに替えず、
                           一番近い重みのある頂点の重みを写す（別の殻の髪の房・板など）。省略時は従来どおり
      [--rigid-parts]      膝当て（膝の前）と右肩の板（下地の色で探す）を 1 本の骨（すね・右の上腕）にだけ付け、曲げても形を保つ
      [--no-weapon]        銃・光刃・目印を付けない（ヤーナなどの NPC。--gun・--blade-anchor・--grip-fist は無視）
      [--final-height m]   最後に骨の物体を一様に拡大して、この身長にする（再構築は身長 1.55m の座標で行い、ヤーナは 1.72m）。
                           骨の物体の拡大なので、動作（骨の回転・移動）はそのまま同じ割合で大きくなる
      [--name 名前]        骨の物体・体の物体の名前（既定 HaruRig・Haru）
      [--stats <json>]     数値の記録の書き出し先（省略時は <出力>.stats.json）
      [--render <接頭辞>]  確認用の画像（関節の目印つき）

手順：
 1. 向き・大きさ（身長 1.55m）・足の位置をそろえる
 2. 形から関節の位置を推定する（腕は A ポーズの腕の軸を直線で当てはめる）
 3. 面を減らす
 4. 骨の重みを付ける（Blender の自動の重み。失敗したら骨までの距離の重み）
 5. 腕を下ろして、その姿勢を新しい基準の姿勢にする（標準の動作が使えるように）
 6. 標準の骨を入れ直し、動作・銃・光刃・目印を付けて書き出す

材質：入力の材質の名前・テクスチャ・UV はそのまま残す（'haru_body'、'haru_face' など）。
  下地の色が画像で、発光がまだ無い材質にだけ、琥珀色の所から発光のテクスチャを作って足す。
  名前に face を含む材質（表情の区画を UV でずらす顔）には一切手を付けない。
  銃は 'spark_gun'（--gun のとき、GLB の材質のまま）、光刃は 'haru_blade'。
目印：'muzzle'（銃口の先、hand.R の子）、'blade_socket'（光刃の根元、+Y が刃の向き、forearm.L の子）、
  'LightBlade'（光刃のメッシュ、forearm.L の子。ゲームが攻撃中だけ表示する）。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

from lib import common as C  # noqa: E402
from lib import humanoid as H  # noqa: E402
from lib import mesh as M  # noqa: E402
from models import haru_a as HA  # noqa: E402
from models import humanoid_anims as A  # noqa: E402

HEIGHT = 1.55
# 標準の体型の比率（4.3 頭身。haru_a の関節表）。高さの推定に使う
P = HA.JOINTS_HARU
# 基準の姿勢での上腕の向き（ほぼ真下、少しだけ外へ）
REST_ARM_DIR = Vector((P['forearm'][0] - P['upper_arm'][0], P['forearm'][1] - P['upper_arm'][1],
                       P['forearm'][2] - P['upper_arm'][2])).normalized()


# ---------------------------------------------------------------- 1. そろえる

def import_and_normalize(path: str, turn: float, keep_frame: bool = False) -> bpy.types.Object:
    """keep_frame=True：入力がすでに約束の座標なので、つなぐ・掃除するだけで、向き・大きさ・位置は動かさない"""
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in list(bpy.context.scene.objects):
        if o.type not in ('MESH',):
            # 空の親などは、子の位置を保ったまま外す
            for ch in o.children:
                mw = ch.matrix_world.copy()
                ch.parent = None
                ch.matrix_world = mw
    body = C.join(meshes, 'Body') if len(meshes) > 1 else meshes[0]
    body.name = 'Body'
    for o in list(bpy.context.scene.objects):
        if o is not body:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    body.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # glTF の読み込みでは、面の角ごとに頂点が分かれていることがある。重なった頂点をつなぎ、浮いた頂点を消す
    # （UV は面の角ごとに持つので、つないでも色の貼り方は崩れない）
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5 * max(body.dimensions))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    if keep_frame:
        return body
    pts = verts(body)
    # A ポーズでは、腕を広げた左右の幅が前後の奥行きより大きい。奥行きのほうが大きければ 90 度回す
    ext = pts.max(0) - pts.min(0)
    auto = 90.0 if ext[1] > ext[0] * 1.05 else 0.0
    rot = math.radians(turn + auto)
    if rot:
        body.data.transform(Matrix.Rotation(rot, 4, 'Z'))
    pts = verts(body)
    # 前後：靴のつま先は足首より前に出る。つま先が +Y 側にあれば後ろ向きなので 180 度回す
    if not turn:
        h = pts[:, 2].max() - pts[:, 2].min()
        z0 = pts[:, 2].min()
        foot = pts[pts[:, 2] < z0 + 0.03 * h]
        shin = pts[np.abs(pts[:, 2] - (z0 + 0.2 * h)) < 0.01 * h]
        if len(foot) and len(shin) and np.median(foot[:, 1]) > np.median(shin[:, 1]):
            body.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
            pts = verts(body)
    lo, hi = pts.min(0), pts.max(0)
    s = HEIGHT / (hi[2] - lo[2])
    body.data.transform(Matrix.Scale(s, 4))
    pts = verts(body)
    lo, hi = pts.min(0), pts.max(0)
    # 左右は外形の中央、前後は胴の高さの断面の重心、上下は足の裏を 0 に
    torso = pts[np.abs(pts[:, 2] - 0.6 * HEIGHT) < 0.02]
    body.data.transform(Matrix.Translation((-(lo[0] + hi[0]) / 2, -float(np.median(torso[:, 1])), -lo[2])))
    return body


def verts(obj: bpy.types.Object) -> np.ndarray:
    n = len(obj.data.vertices)
    a = np.empty(n * 3, dtype=np.float64)
    obj.data.vertices.foreach_get('co', a)
    return a.reshape(n, 3)


# ---------------------------------------------------------------- 2. 関節の推定

def intervals(vals: np.ndarray, gap: float) -> list[tuple[float, float]]:
    """数の並びを、gap より大きい隙間で区切った区間の一覧"""
    if len(vals) == 0:
        return []
    v = np.sort(vals)
    cuts = np.where(np.diff(v) > gap)[0]
    out, start = [], 0
    for c in cuts:
        out.append((v[start], v[c]))
        start = c + 1
    out.append((v[start], v[-1]))
    return out


def estimate_joints(pts: np.ndarray) -> dict[str, list[float]]:
    """関節の位置（本人の左 = +X 側。右は左右反転で使う）。単位は m"""
    Hh = HEIGHT

    def zslice(z: float, dz: float = 0.012, xmax: float = 1.0) -> np.ndarray:
        m = (np.abs(pts[:, 2] - z) < dz) & (np.abs(pts[:, 0]) < xmax)
        return pts[m]

    def cy(z: float, xmax: float = 1.0) -> float:
        s = zslice(z, xmax=xmax)
        return float(np.median(s[:, 1])) if len(s) else 0.0

    J: dict[str, list[float]] = {}
    # 胴と頭の高さ：標準の比率。前後は断面の中央
    for name in ('hips', 'spine', 'chest', 'neck', 'head'):
        z = P[name][2] * Hh
        J[name] = [0.0, cy(z, xmax=0.10), z]
    J['root'] = [0.0, 0.0, 0.0]
    J['head_end'] = [0.0, J['head'][1], float(pts[:, 2].max())]

    # 胴の半分の幅（胸の高さの断面で、中央を含む区間）
    zc = P['chest'][2] * Hh
    s = zslice(zc)
    left = s[s[:, 0] > 0][:, 0]
    iv = intervals(left, 0.012)
    torso_half = iv[0][1] if iv else 0.13

    # 腕：水平の輪切りごとに、体の芯（中央を含む塊）から離れた外側の塊を腕とみなし、直線を当てはめる
    zs = P['upper_arm'][2] * Hh
    arm_parts = []
    for z in np.arange(0.25 * Hh, zs, 0.006 * Hh):
        sl = zslice(z, dz=0.003 * Hh)
        sl = sl[sl[:, 0] > 0]
        if len(sl) < 3:
            continue
        iv = intervals(sl[:, 0], 0.015)
        if len(iv) < 2:
            continue
        core_max = iv[0][1]
        arm_parts.append(sl[sl[:, 0] > core_max + 1e-6])
    arm = np.concatenate(arm_parts) if arm_parts else np.zeros((0, 3))
    # 腕の塊は肩から手先へ一続きのはずなので、脚の外側などに残った小さな塊を除く：肩に近い側から順に外へ伸びるもの
    if len(arm):
        arm = arm[arm[:, 0] > torso_half]
    if len(arm) < 50:
        raise SystemExit('腕の点が見つからない（A ポーズでない、または向きが違う可能性）')
    c = arm.mean(0)
    _, _, vt = np.linalg.svd(arm - c, full_matrices=False)
    d = vt[0]
    if d[2] > 0:
        d = -d  # 肩から手先へ向ける
    # 肩の関節：軸の上で、肩の高さの点
    t_sh = (zs - c[2]) / d[2]
    shoulder = c + d * t_sh
    proj = (arm - shoulder) @ d
    L = float(proj.max())  # 肩から指先まで
    # 上腕 0.44、前腕 0.37、手首から手の先 0.15（haru_a の比率）
    J['upper_arm'] = shoulder.tolist()
    J['forearm'] = (shoulder + d * L * 0.44).tolist()
    J['hand'] = (shoulder + d * L * 0.81).tolist()
    J['hand_end'] = (shoulder + d * L * 0.96).tolist()
    J['shoulder'] = [0.3 * shoulder[0], 0.0, zs]

    # 脚：膝の高さの断面の、左側の重心
    def leg_x(z: float) -> tuple[float, float]:
        sl = zslice(z, xmax=0.25)
        sl = sl[sl[:, 0] > 0.01]
        return (float(np.median(sl[:, 0])), float(np.median(sl[:, 1]))) if len(sl) else (0.06 * Hh, 0.0)

    kx, ky = leg_x(P['shin'][2] * Hh)
    tx, _ = leg_x(0.38 * Hh)
    ax, ay = leg_x(0.10 * Hh)
    J['thigh'] = [tx * 0.95, cy(P['thigh'][2] * Hh, xmax=0.2), P['thigh'][2] * Hh]
    J['shin'] = [kx, ky, P['shin'][2] * Hh]
    J['foot'] = [ax, ay, P['foot'][2] * Hh]
    feet = pts[(pts[:, 2] < 0.035 * Hh) & (pts[:, 0] > 0)]
    toe_y = float(feet[:, 1].min()) if len(feet) else -0.1
    J['toe'] = [ax, ay + (toe_y - ay) * 0.7, 0.012]
    J['_arm_dir'] = d.tolist()
    J['_torso_half'] = [torso_half]
    return J


def load_overrides(J: dict, path: str | None) -> dict:
    if path and os.path.exists(path):
        with open(path) as f:
            J.update(json.load(f))
    return J


# ---------------------------------------------------------------- 3〜5. 面を減らす、重み、基準の姿勢

def decimate(obj: bpy.types.Object, target: int) -> None:
    tris = M.tri_count(obj)
    if tris <= target:
        return
    m = obj.modifiers.new('decimate', 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.ratio = target / tris
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)


def joints_table(J: dict) -> dict:
    """推定した関節（m、左側）を、humanoid.build_armature 用の比率の表にする"""
    return {k: (v[0] / HEIGHT, v[1] / HEIGHT, v[2] / HEIGHT) for k, v in J.items() if not k.startswith('_')}


def fill_from_nearest(body: bpy.types.Object, todo: list[int]) -> int:
    """重みの無い頂点に、一番近い「重みのある頂点」の重みを写す。写した数を返す"""
    from mathutils.kdtree import KDTree
    me = body.data
    todo_set = set(todo)
    src = [v for v in me.vertices if v.index not in todo_set]
    if not src:
        return 0
    kd = KDTree(len(src))
    for v in src:
        kd.insert(v.co, v.index)
    kd.balance()
    names = {g.index: g.name for g in body.vertex_groups}
    for vi in todo:
        _, j, _ = kd.find(me.vertices[vi].co)
        for g in me.vertices[j].groups:
            if g.weight > 0.001:
                body.vertex_groups[names[g.group]].add([vi], g.weight, 'REPLACE')
    return len(todo)


def skin(body: bpy.types.Object, arm: bpy.types.Object, fill_limit: float = 0.0) -> str:
    """自動の重み（骨の熱の広がり）。うまくいかない頂点が多ければ、骨までの距離の重みにする。

    fill_limit > 0：重みの無い頂点が全体のその割合までなら、距離の重みに替えず、一番近い重みのある頂点の
    重みを写す（髪の房・板など、別の殻で骨が見通せず熱が届かない所だけを埋める）。
    """
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    method = 'heat'
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except RuntimeError:
        method = 'distance'
    todo = [v.index for v in body.data.vertices if not any(g.weight > 0.001 for g in v.groups)]
    unweighted = len(todo)
    if method == 'heat' and unweighted > len(body.data.vertices) * 0.005:
        if unweighted <= len(body.data.vertices) * fill_limit:
            fill_from_nearest(body, todo)
            method = 'heat+nearest'
        else:
            method = 'distance'
    if method == 'distance':
        body.vertex_groups.clear()
        bones = [b.name for b in arm.data.bones if b.name != 'root']
        M.weight_auto(body, arm, bones, power=6.0, max_influences=4)
        if not body.parent:
            H.finalize_skin(body, arm)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_limit_total(limit=4)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return f'{method}（重みの無い頂点 {unweighted}）'


def vertex_colors_from_texture(body: bpy.types.Object) -> np.ndarray | None:
    """頂点ごとの下地の色（sRGB 0..1、体の材質のテクスチャを頂点の UV で引く）。テクスチャが無ければ None"""
    mat = next((m for m in body.data.materials if m and m.use_nodes and 'face' not in m.name.lower()), None)
    if mat is None:
        return None
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None or not bsdf.inputs['Base Color'].links:
        return None
    node = bsdf.inputs['Base Color'].links[0].from_node
    if node.type != 'TEX_IMAGE' or node.image is None:
        return None
    img = node.image
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    me = body.data
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    lv = np.zeros(len(me.loops), dtype=np.int64)
    me.loops.foreach_get('vertex_index', lv)
    vuv = np.zeros((len(me.vertices), 2))
    vuv[lv] = uv                                        # 継ぎ目の頂点は、どれか 1 つの UV（色はほぼ同じ）
    iy = np.clip((vuv[:, 1] * h).astype(int), 0, h - 1)  # Blender の画像は下の行が 0
    ix = np.clip((vuv[:, 0] * w).astype(int), 0, w - 1)
    return px[iy, ix, :3]


def rigid_parts(body: bpy.types.Object, J: dict) -> dict:
    """硬い部品（膝当て・右肩の板）を、1 本の骨にだけ付ける（自動の重みのあと、A ポーズで）。

    熱の重みは膝の上下（太もも・すね）や肩（肩・胸・上腕）を混ぜるので、曲げると膝当てと琥珀の継ぎ目や
    肩の板がぐにゃりと曲がる。
      膝当て：膝の関節の前と横（関節から KNEE_R1 以内）は、すね（shin.L/R）の重みを 1 に。KNEE_R2 までと、
        前後の向き（関節より後ろ）へは、なめらかに元の重みへ戻す（膝の裏は熱の重みのまま、なめらかに曲がる）。
        形で決める（色で選ぶと、部品の中の暗い線が選ばれずに残り、曲げたときにぎざぎざに裂ける）
      右肩の板：右の上腕の付け根から SHOULDER_R 以内のアイボリー（下地の色）を選び、辺で RING 輪ふくらませて
        から縮める（板の中の暗い線を埋める）。そこを右の上腕（upper_arm.R）の重み 1 にし、縁から RING 輪は
        元の重みと半々に混ぜる
    返り値：部品ごとの、重みを変えた頂点の数
    """
    KNEE_R1, KNEE_R2, KNEE_BACK = 0.112, 0.150, 0.03   # 膝当ての暗い縁・琥珀の継ぎ目まで硬く（8 回目：膝当ての上の角（関節から約 10cm）まで。半分の重みだと深く曲げたとき膝当ての上の縁の下で体が沈み、すき間ができた）
    KNEE_SMOOTH = (0.16, 0.045, 0.04)   # 膝の重みをなめらかにする範囲（関節からの距離）・移す高さの幅の半分・外の縁の戻しの幅
    SHOULDER_R, RING = 0.10, 2
    me = body.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    groups = list(body.vertex_groups)
    gidx = {vg.name: i for i, vg in enumerate(groups)}
    W = np.zeros((n, len(groups)))
    for v in me.vertices:
        for ge in v.groups:
            W[v.index, ge.group] = ge.weight
    ev = np.zeros(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)

    def grow(sel: np.ndarray) -> np.ndarray:
        out = sel.copy()
        out[ev[sel[ev[:, 0]], 1]] = True
        out[ev[sel[ev[:, 1]], 0]] = True
        return out

    def onehot(bone: str) -> np.ndarray:
        o = np.zeros(len(groups))
        o[gidx[bone]] = 1.0
        return o

    f_all = np.zeros(n)
    target = np.zeros((n, len(groups)))
    counts = {}
    # 膝のまわりの重み（8 回目）：熱の重みは膝の裏で頂点ごとにばらつき、深く曲げる（倒れ 125 度）と膝の裏の暗い帯と
    # ズボンがぎざぎざの暗い形に折れ込んだ。膝の関節から KNEE_SMOOTH 以内の脚の頂点は、脚の軸に沿った高さだけの
    # なめらかな関数で太もも → すねへ移す（同じ高さの輪は同じ重み＝折れ目がまっすぐ）
    knee_set = np.zeros(n, bool)
    for sx, side in (('.L', 1.0), ('.R', -1.0)):
        tb_, sb_ = 'thigh' + sx, 'shin' + sx
        if tb_ not in gidx or sb_ not in gidx:
            continue
        kj = np.array(J['shin']) * np.array([side, 1.0, 1.0])
        hj = np.array(J['thigh']) * np.array([side, 1.0, 1.0])
        fj = np.array(J['foot']) * np.array([side, 1.0, 1.0])
        up = (hj - kj) / np.linalg.norm(hj - kj)
        dn = (fj - kj) / np.linalg.norm(fj - kj)
        legw = W[:, gidx[tb_]] + W[:, gidx[sb_]]
        d = np.linalg.norm(co - kj, axis=1)
        m = (d < KNEE_SMOOTH[0]) & (legw > 0.6 * np.maximum(W.sum(1), 1e-9))
        # 高さ：関節より上は太ももの軸、下はすねの軸に沿った長さ（+ = 上）
        rel = co[m] - kj
        h = np.where(rel @ up > 0, rel @ up, -(rel @ dn))
        g = np.clip((KNEE_SMOOTH[1] - h) / (2 * KNEE_SMOOTH[1]), 0.0, 1.0)
        g = g * g * (3 - 2 * g)            # すねの重み
        # 外側の輪（d が KNEE_SMOOTH[0] に近い）は元の重みへなめらかに戻す
        e = np.clip((KNEE_SMOOTH[0] - d[m]) / KNEE_SMOOTH[2], 0.0, 1.0)
        idx = np.nonzero(m)[0]
        tot = W[idx].sum(1)
        new = np.zeros((len(idx), len(groups)))
        new[:, gidx[sb_]] = g * tot
        new[:, gidx[tb_]] = (1 - g) * tot
        W[idx] = e[:, None] * new + (1 - e[:, None]) * W[idx]
        knee_set[idx] = True
        counts['knee_smooth' + sx] = int(len(idx))
    # 膝当て（形で決める）
    for sx, side in (('.L', 1.0), ('.R', -1.0)):
        bone = 'shin' + sx
        if bone not in gidx:
            continue
        kj = np.array(J['shin']) * np.array([side, 1.0, 1.0])
        d = np.linalg.norm(co - kj, axis=1)
        fd = np.clip((KNEE_R2 - d) / (KNEE_R2 - KNEE_R1), 0.0, 1.0)
        fy = np.clip((kj[1] + KNEE_BACK - co[:, 1]) / KNEE_BACK, 0.0, 1.0)   # 関節より後ろへ行くほど 0
        f = fd * fy
        f = f * f * (3 - 2 * f)
        m = f > f_all
        f_all[m] = f[m]
        target[m] = onehot(bone)
        counts[bone] = int((f > 0.01).sum())
    # 右肩の板（色で選び、穴を埋める）
    col = vertex_colors_from_texture(body)
    if col is not None and 'upper_arm.R' in gidx:
        r, g, b = col[:, 0], col[:, 1], col[:, 2]
        ivory = (r > 0.72) & (g > 0.6) & (b > 0.55) & (r - b < 0.3)
        sj = np.array(J['upper_arm']) * np.array([-1.0, 1.0, 1.0])
        near = (np.linalg.norm(co - sj, axis=1) < SHOULDER_R) & (co[:, 0] < -0.11) & (co[:, 2] > sj[2] - 0.08)
        sel = near & ivory
        for _ in range(RING):
            sel = grow(sel) & near
        for _ in range(RING):
            sel = ~grow(~sel)
        band = sel.copy()
        for _ in range(RING):
            band = grow(band)
        band &= ~sel
        f = np.where(sel, 1.0, np.where(band, 0.5, 0.0))
        m = f > f_all
        f_all[m] = f[m]
        target[m] = onehot('upper_arm.R')
        counts['upper_arm.R'] = int(sel.sum())
    changed = f_all > 1e-3
    W[changed] = (1 - f_all[changed, None]) * W[changed] + f_all[changed, None] * target[changed]
    changed |= knee_set
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    for vi in np.nonzero(changed)[0]:
        for gi, vg in enumerate(groups):
            if W[vi, gi] > 1e-4:
                vg.add([int(vi)], float(W[vi, gi]), 'REPLACE')
            else:
                vg.remove([int(vi)])
    return counts


def add_costume(body: bpy.types.Object, tex_dir: str, skip: tuple = ()) -> tuple[bpy.types.Object, dict]:
    """服の硬い部品（recon/costume.py）を体の形から作り、1 本の骨に重み 1 で付ける（A ポーズ、自動の重みのあと）。

    材質 haru_parts：色見本の画像（8 区画）を UV で指す。部品の面は角度 35 度より鋭い所で折る（板の縁はくっきり、
    板の面はなめらか）。返り値：(部品の物体, 数値の記録)
    """
    sys.path.insert(0, os.path.join(C.REPO, 'tools', 'blender', 'recon'))
    import costume as CO
    me = body.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    tris = []
    for p in me.polygons:
        vs = p.vertices[:]
        for k in range(1, len(vs) - 1):
            tris.append((vs[0], vs[k], vs[k + 1]))
    # 体の出っ張りを押し戻す（キャラクターの部品の表の BODY_CLAMP。ヤーナの腰の前。無ければ何もしない）
    clamp = getattr(CO, 'BODY_CLAMP', None)
    if clamp is not None:
        co = clamp(co)
        me.vertices.foreach_set('co', co.ravel())
        me.update()
    P = CO.build_all(co, np.array(tris), skip=skip)
    removed_feet = 0
    # ゴーグルのヒモの下の髪を押し込む（8 回目、costume.strap_push）
    if hasattr(CO, 'strap_push'):
        vc = vertex_colors_from_texture(body)
        hair = None if vc is None else ((vc[:, 0] - vc[:, 2] > 0.06) & (vc[:, 0] < 0.55)).astype(float)
        co2, pushed = CO.strap_push(co, hair)
        if pushed:
            me.vertices.foreach_set('co', co2.ravel())
            me.update()
        CO.FIT['goggle_strap_pushed_verts'] = pushed
    pm = bpy.data.meshes.new('costume')
    pm.from_pydata(P['V'].tolist(), [], P['F'].tolist())
    pm.update()
    obj = bpy.data.objects.new('costume', pm)
    bpy.context.scene.collection.objects.link(obj)
    mat = bpy.data.materials.new(CO.PARTS_MAT)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Metallic'].default_value = 0.0
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(CO.palette_image(os.path.join(tex_dir, f'{CO.PARTS_MAT}_base.png')))
    tex.image.name = f'{CO.PARTS_MAT}_base'
    tex.interpolation = 'Closest'
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    pm.materials.append(mat)
    uvname = me.uv_layers.active.name if me.uv_layers.active else 'UVMap'
    uv = pm.uv_layers.new(name=uvname)
    uv.data.foreach_set('uv', np.repeat(CO.palette_uv(P['color']), 3, 0).ravel())
    # 体の重みを写す部品（右肩の板と下の帯）：載る骨 1 本の剛体だと、腕を下ろした基準の姿勢（と動作）で肩の上の体
    # （胸・肩の骨の重みが混ざる）が板の内の縁から突き抜け、板が 2 つに割れて見えた（6 回目）。近くの体の頂点の重みを
    # なめらかにして写し、板と下の体が同じに動くようにする
    follow = np.zeros(len(P['V']), bool)
    names = [str(n) for n in P['names']]
    for pi, nm in enumerate(names):
        if nm in CO.FOLLOW_BODY:
            follow[np.unique(P['F'][P['piece'] == pi])] = True
    for bi, bone in enumerate(P['bones']):
        vg = obj.vertex_groups.new(name=str(bone))
        vg.add(np.nonzero((P['vbone'] == bi) & ~follow)[0].tolist(), 1.0, 'REPLACE')
    # 靴：高さで foot から shin へなめらかに移す（カフの中の胴の上は shin に 1 = カフ・脚と一緒に動く）
    sw = P['shin_w']
    for vi in np.nonzero(sw >= 0)[0]:
        foot = str(P['bones'][P['vbone'][vi]])
        shin = foot.replace('foot', 'shin')
        w = float(sw[vi])
        if w > 1e-4:
            obj.vertex_groups[shin].add([int(vi)], w, 'REPLACE')
        if w < 1 - 1e-4:
            obj.vertex_groups[foot].add([int(vi)], 1.0 - w, 'REPLACE')
        else:
            obj.vertex_groups[foot].remove([int(vi)])
    if follow.any():
        from scipy.spatial import cKDTree
        groups = list(body.vertex_groups)
        Wb = np.zeros((len(me.vertices), len(groups)))
        for v in me.vertices:
            for ge in v.groups:
                Wb[v.index, ge.group] = ge.weight
        Wb /= np.maximum(Wb.sum(1, keepdims=True), 1e-9)
        fi = np.nonzero(follow)[0]
        d, nn = cKDTree(co).query(P['V'][fi], k=8)
        wk = 1.0 / np.maximum(d, 1e-4)
        Wf = (Wb[nn] * wk[..., None]).sum(1) / wk.sum(1, keepdims=True)
        # 肩ひもなど（CO.FOLLOW_TORSO_ONLY）は腕の骨の重みを除く（残りが無ければ chest）
        torso_only = np.zeros(len(P['V']), bool)
        for pi, nm in enumerate(names):
            if nm in getattr(CO, 'FOLLOW_TORSO_ONLY', ()):
                torso_only[np.unique(P['F'][P['piece'] == pi])] = True
        to = torso_only[fi]
        if to.any():
            armg = [gi for gi, g in enumerate(groups) if g.name.split('.')[0] in ('upper_arm', 'forearm', 'hand')]
            Wf[np.ix_(to, armg)] = 0.0
            empty = to & (Wf.sum(1) < 1e-6)
            chest = [gi for gi, g in enumerate(groups) if g.name == 'chest']
            if empty.any() and chest:
                Wf[empty, chest[0]] = 1.0
        Wf[Wf < 0.02] = 0.0
        Wf /= np.maximum(Wf.sum(1, keepdims=True), 1e-9)
        for gi, g in enumerate(groups):
            m = Wf[:, gi] > 0
            if m.any():
                vg = obj.vertex_groups.get(g.name) or obj.vertex_groups.new(name=g.name)
                for vi, w in zip(fi[m], Wf[m, gi]):
                    vg.add([int(vi)], float(w), 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    # 靴は部品（重みを写したあとに消す：上の写しは消す前の頂点の番号）（7 回目）：体の足・靴（脚の BOOT_CUT より下。カフの中で切る）を消す
    if any(str(n).startswith('boot_upper') for n in P['names']):
        gone = CO.boot_cut_mask(co)
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        kill = [f for f in bm.faces if any(gone[v.index] for v in f.verts)]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(me)
        bm.free()
        me.update()
        removed_feet = int(gone.sum())
    return obj, {'tris': int(len(P['F'])), 'pieces': [str(n) for n in P['names']], 'body_feet_removed': removed_feet,
                 'fit': dict(getattr(CO, 'FIT', {}))}


def lower_arms(body: bpy.types.Object, arm: bpy.types.Object,
               frontal_deg: float | None = None) -> tuple[dict, Quaternion]:
    """腕を下ろした姿勢を、メッシュの新しい基準の形にする。下ろしたあとの関節の位置と、左腕の回転を返す。

    frontal_deg が無ければ、上腕を標準の向き（REST_ARM_DIR）へ最短の回転で向ける（従来どおり）。
    frontal_deg（度）を渡すと、前後の軸（Y）まわりだけで回し、正面から見た上腕の傾き（真下から外へ）を
    その角度にする。腕の前後の傾き・肘の曲がりはそのまま（最短の回転だと、前へ出た上腕を下ろすときに
    腕全体が後ろへ振れる）。
    """
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    q_left = Quaternion()
    for side, sx in ((1, '.L'), (-1, '.R')):
        pb = arm.pose.bones['upper_arm' + sx]
        cur = (pb.tail - pb.head).normalized()
        if frontal_deg is None:
            want = Vector((REST_ARM_DIR.x * side, REST_ARM_DIR.y, REST_ARM_DIR.z))
            q = cur.rotation_difference(want)
        else:
            a_cur = math.atan2(cur.x * side, -cur.z)
            q = Quaternion(Vector((0.0, 1.0, 0.0)), (a_cur - math.radians(frontal_deg)) * side)
        if side == 1:
            q_left = q.copy()
        head = pb.head.copy()
        pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix
        bpy.context.view_layer.update()
    # 下ろしたあとの関節の位置（左側の骨から読む）
    new = {}
    for name in ('upper_arm', 'forearm', 'hand'):
        new[name] = list(arm.pose.bones[name + '.L'].head)
    new['hand_end'] = list(arm.pose.bones['hand.L'].tail)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    for m in body.modifiers:
        if m.type == 'ARMATURE':
            bpy.ops.object.modifier_apply(modifier=m.name)
    return new, q_left


# ---------------------------------------------------------------- 6. 材質、銃、光刃

def has_textures(body: bpy.types.Object) -> bool:
    """材質のどれかが画像のテクスチャを使っているか（UV で色を持つ入力か）"""
    for mat in body.data.materials:
        if mat and mat.use_nodes and any(n.type == 'TEX_IMAGE' and n.image for n in mat.node_tree.nodes):
            return True
    return False


def fix_materials(body: bpy.types.Object, tex_dir: str) -> None:
    """AI の材質は金属っぽさが混ざりがちなので、ゲームの塗りに合わせる。琥珀色の部分を光らせる。

    材質を置き換えはしない（名前・下地の色のテクスチャ・UV はそのまま）。
    顔の材質（名前に face）には触らない。すでに発光がつながっている材質には発光を足さない。
    """
    for mat in body.data.materials:
        if not mat or not mat.use_nodes or 'face' in mat.name.lower():
            continue
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not bsdf:
            continue
        # 金属・粗さのテクスチャはつながりを外して、一定の値にする
        for inp in ('Metallic', 'Roughness'):
            for link in list(bsdf.inputs[inp].links):
                nt.links.remove(link)
        bsdf.inputs['Metallic'].default_value = 0.0
        bsdf.inputs['Roughness'].default_value = 0.85
        if bsdf.inputs['Emission Color'].links:
            continue  # 発光のテクスチャはすでにある（絵から起こしたハルは焼き込み済み）
        base = bsdf.inputs['Base Color'].links[0].from_node if bsdf.inputs['Base Color'].links else None
        if base is None or base.type != 'TEX_IMAGE' or base.image is None:
            continue
        img = base.image
        w, h = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
        # sRGB の値で琥珀色（#FFBC52 付近：赤が強く、青が弱く、明るい）を探す
        r, g, b_ = px[..., 0], px[..., 1], px[..., 2]
        mask = (r > 0.85) & (g > 0.55) & (g < 0.9) & (b_ < 0.5) & (r - b_ > 0.45)
        if mask.mean() < 0.0005:
            continue
        emit = np.zeros_like(px)
        emit[..., :3] = px[..., :3] * mask[..., None]
        emit[..., 3] = 1.0
        ei = bpy.data.images.new(f'{img.name}_emissive', w, h)
        ei.pixels = emit.ravel().tolist()
        p = os.path.join(tex_dir, f'{mat.name}_emissive.png')
        ei.filepath_raw = p
        ei.file_format = 'PNG'
        ei.save()
        node = nt.nodes.new('ShaderNodeTexImage')
        node.image = ei
        nt.links.new(node.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 1.5


def name_images(body: bpy.types.Object) -> None:
    """テクスチャの画像の名前を「材質_用途」にそろえる（haru_body_base、haru_body_emit、haru_face_base など）。

    Godot は GLB の中の画像を「<GLB の名前>_<画像の名前>.png」として取り出すので、名前が入力の作り方で
    変わると、古い画像のファイルが残ってしまう。名前をそろえておけば、作り直しても同じファイルが上書きされる。
    """
    for mat in body.data.materials:
        if not mat or not mat.use_nodes:
            continue
        for link in mat.node_tree.links:
            n = link.from_node
            if n.type != 'TEX_IMAGE' or n.image is None:
                continue
            kind = {'Base Color': 'base', 'Emission Color': 'emit', 'Normal': 'normal'}.get(link.to_socket.name)
            if kind is None:
                continue
            want = f'{mat.name}_{kind}'
            if n.image.name != want and want not in bpy.data.images:
                n.image.name = want


def add_gun_and_blade(arm: bpy.types.Object, gun_mat, blade_mat, blade: dict | None = None) -> list[bpy.types.Object]:
    """銃（右手）と光刃（左前腕）。銃は絵が届くまで箱の組み合わせの仮の形"""
    parts = []
    hr = arm.data.bones['hand.R']
    fist = hr.head_local.lerp(hr.tail_local, 0.55)
    x, fy, fz = fist.x, fist.y, fist.z
    y0 = fy - 0.061
    spec = [  # (名前, 中心, 大きさ, 面取り, 色)
        ('gun_slide', (x, y0, fz - 0.080), (0.046, 0.062, 0.250), 0.008, 'frame'),
        ('gun_muzzle', (x, y0, fz - 0.211), (0.038, 0.052, 0.022), 0.005, 'brass'),
        ('gun_grip', (x, fy - 0.015, fz + 0.009), (0.036, 0.090, 0.042), 0.008, 'frame'),
        ('gun_cell', (x, y0 - 0.0315, fz - 0.055), (0.020, 0.005, 0.080), 0.0, 'amber'),
        ('gun_cell_side', (x - 0.0235, y0, fz - 0.070), (0.005, 0.030, 0.080), 0.0, 'amber'),
        ('gun_rear', (x, y0, fz + 0.048), (0.042, 0.054, 0.018), 0.005, 'brass'),
    ]
    for name, c, size, bev, col in spec:
        o = M.rbox(name, c, size, bevel=bev)
        o.data.materials.append(gun_mat)
        M.paint(o, HA.PAL, col)
        M.weight_rigid(o, 'hand.R')
        M.smooth(o, 0)
        parts.append(o)
    muzzle = C.empty('muzzle', (x, y0, fz - 0.225))
    M.parent_to_bone(muzzle, arm, 'hand.R')
    add_blade(arm, blade_mat, blade)
    return parts


# 絵から起こした銃の握り方（--gun）。拳の中心は手の骨の根元から先へ GRIP_ALONG の所、
# そこから掌の側（体の内側）へ GRIP_IN、正面へ GRIP_FRONT ずらした所を銃の原点（握りの中心）にする
GRIP_ALONG = 0.45
GRIP_IN = 0.012
GRIP_FRONT = 0.0


# 拳の形（--grip-fist）：指の付け根は手首から指先までの GRIP_KNUCKLE の所。指は半径 GRIP_RADIUS の
# 円柱（銃の握り）に沿って掌の側へ曲げる
GRIP_KNUCKLE = 0.5
GRIP_RADIUS = 0.026   # （前のやり方の円柱の半径。今は使わない）
# 銃の握りの断面（spark_gun.glb を高さごとに切って測った。銃の座標：銃身 +X、上 +Z、原点は握りの中ほど）：
# 前の縁 x ≈ +0.03、前後の半径 約 2.4cm（前の縁から）、左右の半径 1.75cm（全幅 3.5cm）。
# 用心金の下の縁は z ≈ -0.025、握りの下端 -0.08、上は枠の下 z ≈ +0.012
GRIP_X_FRONT = 0.030
GRIP_A = 0.024
GRIP_B = 0.0175
GRIP_GAP = 0.0015     # 握りの面と指の面の間（めり込まない）
GRIP_K_BACK = 0.012   # 指の付け根は、断面の前の縁からこれだけ後ろ
GRIP_Z_TOP, GRIP_Z_BOT = 0.010, -0.074
GRIP_THUMB_W = 0.04   # 指の付け根から親指の側へこれより外で、付け根の近くは親指（曲げない）
GRIP_THUMB_SIDE = -0.0235   # 親指の内側の面を置く所（銃の左右の座標。受け筒の横の面 -0.022 のすぐ外）
HAND_END_FRAC = 0.8   # 手の骨の先（hand_end）は、手首から指先までのこの割合の所（joints.py、estimate_joints と同じ）


def grip_right_hand(body: bpy.types.Object, arm: bpy.types.Object, palm: Vector, shape_key: bool = False) -> dict:
    """右手を、銃の握りを握った拳の形にする（基準の姿勢のメッシュを直接変える）。握りの置き場所を返す。

    絵の手は A ポーズで指を開き、掌は palm の向き（ハルは後ろ）。銃を立てて構えるには掌が体の内側を
    向いている必要があるので、
      1. ねじる：手（hand.R の重みの分だけ）を手の骨の軸まわりに回し、掌を体の内側（+X）へ向ける
         （手首の混ざる所は重みの割合だけ回るので、手袋の袖口がなめらかにねじれる）
      2. 曲げる：指の付け根（手首から指先までの GRIP_KNUCKLE）より先を、掌の側の半径 GRIP_RADIUS の
         円柱のまわりに曲げる（指の長さに比例した角度。約 5.5cm の指で 120 度ほど）
    shape_key=True なら基準の姿勢のメッシュは開いた手のまま残し、拳の形をシェイプキー 'fist' に入れる
    （ゲームでは銃を持つとき fist = 1。絵の A ポーズの開いた手と比べられる）。
    返り値：{'origin': 握りの中心, 'x': 銃身の向き, 'z': 銃の上（親指の側 = 正面）}
    """
    hr = arm.data.bones['hand.R']
    W = hr.head_local.copy()
    h = (hr.tail_local - W).normalized()
    reach = (hr.tail_local - W).length / HAND_END_FRAC
    gi = body.vertex_groups['hand.R'].index
    me = body.data
    n = len(me.vertices)
    w = np.zeros(n)
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi:
                w[v.index] = g.weight
    co = np.empty(n * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    hv = np.array(h)
    Wv = np.array(W)

    # 1. ねじる（掌 palm → 体の内側 +X）
    p0 = Vector(palm) - h * Vector(palm).dot(h)
    p1 = Vector((1.0, 0.0, 0.0)) - h * h.x
    p0.normalize()
    p1.normalize()
    ang = math.atan2(h.dot(p0.cross(p1)), p0.dot(p1))
    idx = np.nonzero(w > 1e-4)[0]
    for i in idx:
        q = Quaternion(h, ang * w[i])
        co[i] = Wv + np.array(q @ Vector(co[i] - Wv))

    # 2. 曲げる：指（付け根 K より先）を、銃の握りの断面（楕円：前後の半径 GRIP_A、左右の半径 GRIP_B）の
    #    まわりに巻く。指の掌の側の面（qv = q_palm）が断面の縁に沿い、指の長さ（K からの距離）だけ前の縁を回って
    #    向こうの側面へ届く。K は断面の前の縁から GRIP_K_BACK 後ろの、掌の側の面の上。
    pv = np.array(p1)                       # 掌の向き（体の内側）＝銃の左右（gy）
    tv = np.array(h.cross(p1))              # 親指の側（正面）＝銃の上（gz）
    K = Wv + hv * reach * GRIP_KNUCKLE
    rel = co - K
    sv = rel @ hv
    qv = rel @ pv
    wv = rel @ tv
    rad = np.linalg.norm(rel - np.outer(sv, hv), axis=1)
    fing = (w > 0.3) & (sv > 0) & (rad < 0.08)
    # 絵の開いた手の指は少し掌の側へ曲がっている。指の中心線の傾き（qv を sv の 1 次式で）を引いて、
    # 中心線からの厚みの向きの位置 q_rel と、中心線に沿った長さで巻く。親指（帯の外、付け根の近く）は曲げない
    thumb = fing & (wv > GRIP_THUMB_W) & (sv < 0.03)
    fing &= ~thumb
    slope, c0 = np.polyfit(sv[fing], qv[fing], 1) if fing.sum() > 10 else (0.0, 0.0)
    q_rel = qv - (c0 + slope * sv)
    s_len = sv * math.sqrt(1 + slope * slope)
    q_palm = float(np.percentile(q_rel[fing], 92)) if fing.any() else 0.0
    A, B = GRIP_A + GRIP_GAP, GRIP_B + GRIP_GAP
    x0 = A - GRIP_K_BACK
    phi0 = -math.acos(max(-1.0, min(1.0, x0 / A)))
    y0 = B * math.sin(phi0)
    centre = K + pv * (c0 + q_palm) - (hv * x0 + pv * y0)
    phis = np.linspace(phi0, phi0 + 2 * math.pi, 2001)
    ex, ey = A * np.cos(phis), B * np.sin(phis)
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(ex), np.diff(ey)))])
    ph = np.interp(s_len[fing], arc, phis)
    nx, ny = np.cos(ph) / A, np.sin(ph) / B
    nl = np.hypot(nx, ny)
    nx, ny = nx / nl, ny / nl
    out = q_palm - q_rel[fing]
    # 指の帯（人さし指〜小指）が握りの使える高さより長ければ、帯の中ほどへ寄せて縮める（小指が握りの下端を
    # 回り込んだり、人さし指が用心金に入ったりしないように）
    wf0 = wv[fing & (sv > 0.02)]
    lo, hi = (np.percentile(wf0, 3), np.percentile(wf0, 97)) if len(wf0) else (0.0, 0.0)
    w_mid = float((lo + hi) / 2)
    squeeze = min(1.0, (GRIP_Z_TOP - GRIP_Z_BOT) / max(hi - lo, 1e-6))
    wv_new = w_mid + (wv[fing] - w_mid) * squeeze
    co[fing] = (centre + np.outer(A * np.cos(ph) + out * nx, hv) + np.outer(B * np.sin(ph) + out * ny, pv)
                + np.outer(wv_new, tv))
    # 銃の置き場所：握りの断面の中心（銃の座標 (GRIP_X_FRONT - GRIP_A, 0, z)）を、指の帯の中ほどの所へ。
    # 指の帯の高さ（wv の範囲）の中ほどを、握りの使える高さ（GRIP_Z_TOP〜GRIP_Z_BOT）の中ほどに合わせる
    wf = wf0
    z_mid = (GRIP_Z_TOP + GRIP_Z_BOT) / 2
    origin = centre + tv * w_mid - hv * (GRIP_X_FRONT - GRIP_A) - tv * z_mid
    C = origin
    # 親指を銃の横（掌の側の面、受け筒の高さ）へ寄せて触れさせる（寄せる量は親指の内側の面と銃の横の面の間）
    thumb_zone = (w > 0.3) & (wv > GRIP_THUMB_W - 0.01) & (sv > -0.04) & ~fing
    if thumb.any():
        y_in = float(np.percentile((co[thumb] - np.array(origin)) @ pv, 95))
        shift = max(0.0, GRIP_THUMB_SIDE - y_in)
        f = np.clip((wv - (GRIP_THUMB_W - 0.01)) / 0.015, 0, 1) * np.clip((sv + 0.04) / 0.02, 0, 1)
        co[thumb_zone] += np.outer(f[thumb_zone] * shift, pv)
    if os.environ.get('GRIP_DEBUG'):
        for nm, m in (('thumb', thumb), ('fingers', fing)):
            if m.any():
                L = co[m] - np.array(origin)
                print('GRIPDBG', nm, int(m.sum()), 'x', np.percentile(L @ hv, [5, 50, 95]).round(3),
                      'y', np.percentile(L @ pv, [5, 50, 95]).round(3), 'z', np.percentile(L @ tv, [5, 50, 95]).round(3))
    if shape_key:
        if body.data.shape_keys is None:
            body.shape_key_add(name='Basis', from_mix=False)
        sk = body.shape_key_add(name='fist', from_mix=False)
        sk.data.foreach_set('co', co.ravel())
        sk.value = 0.0
    else:
        me.vertices.foreach_set('co', co.ravel())
    me.update()
    return {'origin': Vector(C), 'x': h, 'z': Vector(tv), 'fingers': int(fing.sum()), 'twist_deg': math.degrees(ang),
            'q_palm': round(q_palm, 4), 'band_squeeze': round(squeeze, 3), 'finger_band': [round(float(np.percentile(wf, 3)), 4),
                                                       round(float(np.percentile(wf, 97)), 4)] if fing.any() else None}


def add_recon_gun(arm: bpy.types.Object, path: str, grip: dict | None = None,
                  place_override: Matrix | None = None) -> bpy.types.Object:
    """絵から起こした銃（spark_gun.glb）を右手に持たせる。

    GLB の銃：原点 = 握りの中心、銃身 +X（銃口が +X）、上 +Z、空の目印 'muzzle' が銃口の先。
    持たせ方：銃身を手の骨の向き（手首 → 指先）へ、銃の上をキャラクターの正面（-Y）へ向ける
    （腕を下ろした基準の姿勢で、銃口は下、握りは後ろへ出る。腕を前へ上げると銃口が前を向く）。
    銃は hand.R に丸ごと付け（剛体）、目印 'muzzle' を銃口の先に置き直す（hand.R の子）。
    """
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    gun_objs = [o for o in new if o.type == 'MESH']
    tip = next((o for o in new if o.name.startswith('muzzle')), None)
    bpy.context.view_layer.update()
    tip_world = tip.matrix_world.translation.copy() if tip else None
    for o in gun_objs:
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    gun = C.join(gun_objs, 'spark_gun') if len(gun_objs) > 1 else gun_objs[0]
    gun.name = 'spark_gun'
    for o in new:
        if o is not gun and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    if tip_world is None:  # 目印が無ければ、銃口側（+X）の端の中央
        pts = np.array([v.co[:] for v in gun.data.vertices])
        tip_world = Vector((pts[:, 0].max(), 0.0, float(np.median(pts[pts[:, 0] > pts[:, 0].max() - 0.01, 2]))))

    hr = arm.data.bones['hand.R']
    gx = (hr.tail_local - hr.head_local).normalized()          # 銃身 = 手の向き
    front = Vector((0.0, -1.0, 0.0))
    if grip:                                                   # 拳の形にしたとき：握りの中心と親指の側
        front = grip['z']
    gz = (front - gx * front.dot(gx)).normalized()             # 銃の上 = 正面
    gy = gz.cross(gx)
    rot = Matrix((gx, gy, gz)).transposed().to_4x4()           # 列が銃の X, Y, Z
    inward = Vector((1.0, 0.0, 0.0))                           # 右手の掌の側（体の内側）
    if grip:
        origin = grip['origin']
    else:
        origin = hr.head_local.lerp(hr.tail_local, GRIP_ALONG) + inward * GRIP_IN + front * GRIP_FRONT
    place = Matrix.Translation(origin) @ rot
    if place_override is not None:
        place = place_override
    gun.data.transform(place)
    gun.data.update()
    M.weight_rigid(gun, 'hand.R')
    muzzle = C.empty('muzzle', place @ tip_world)
    M.parent_to_bone(muzzle, arm, 'hand.R')
    return gun


# 右手の部品（--hand-part、recon/hand.py）：手首（hand.R の元）を銃の座標のこの位置に置く。
# 銃の向きは前と同じ（銃身 = 手の骨の向き、銃の上 = 親指の側 = 腕を下ろした姿勢の正面、+Y = 掌 = 体の内側）
HAND_WRIST_IN_GUN = (-0.062, -0.040, -0.010)
HAND_CUT = -0.006       # 体の右手を消す所（手首から手の向きへの距離。これより先の面を消す。カフの下）
HAND_RAMP = (-0.042, -0.014)   # 手首の体とカフの重みを、前腕の重みから hand.R の 1 へなめらかに移す範囲


def hand_frame(arm: bpy.types.Object) -> tuple[Matrix, Vector, Vector]:
    """銃の座標 → 骨の物体の座標の行列（右手の部品と銃の置き場所）。返り値：(行列, 手首, 手の向き)"""
    hr = arm.data.bones['hand.R']
    W = hr.head_local.copy()
    gx = (hr.tail_local - W).normalized()
    gy = (Vector((1.0, 0.0, 0.0)) - gx * gx.x).normalized()     # 掌 = 体の内側
    gz = gx.cross(gy)                                            # 親指の側 = 正面
    rot = Matrix((gx, gy, gz)).transposed()
    origin = W - rot @ Vector(HAND_WRIST_IN_GUN)
    return Matrix.Translation(origin) @ rot.to_4x4(), W, gx


def sample_surface(obj: bpy.types.Object, step_area: float = 4e-7) -> np.ndarray:
    """物体の面の上の点（物体の座標）"""
    me = obj.data
    V = np.array([v.co[:] for v in me.vertices])
    out = []
    rng = np.random.default_rng(0)
    for p in me.polygons:
        vs = p.vertices[:]
        for k in range(1, len(vs) - 1):
            a, b, c = V[vs[0]], V[vs[k]], V[vs[k + 1]]
            ar = np.linalg.norm(np.cross(b - a, c - a)) / 2
            n = max(1, int(ar / step_area))
            u = rng.random((n, 2))
            m = u.sum(1) > 1
            u[m] = 1 - u[m]
            out.append(a + np.outer(u[:, 0], b - a) + np.outer(u[:, 1], c - a))
    return np.concatenate(out + [V])


def add_hand_part(body: bpy.types.Object, arm: bpy.types.Object, gun: bpy.types.Object, place: Matrix) -> dict:
    """体の右手（手首から先）を消し、銃を握った手の部品（recon/hand.py）に置き換える。

    掌・指は hand.R に 1（剛体）。カフと、残した手首の体は、HAND_RAMP の範囲で前腕の重みから hand.R へ
    なめらかに移す（同じ位置の体とカフは同じ重み＝曲げてもカフが手首から離れない）。返り値：数値の記録
    """
    sys.path.insert(0, os.path.join(C.REPO, 'tools', 'blender', 'recon'))
    import costume as CO
    import hand as HD
    inv = place.inverted()
    gun_pts = sample_surface(gun)
    Rinv = np.array(inv.to_3x3())
    tinv = np.array(inv.translation)
    gun_pts = gun_pts @ Rinv.T + tinv
    hr = arm.data.bones['hand.R']
    W = np.array(hr.head_local)
    h = np.array((hr.tail_local - hr.head_local).normalized())

    me = body.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    groups = list(body.vertex_groups)
    gidx = {vg.name: i for i, vg in enumerate(groups)}
    Wt = np.zeros((n, len(groups)))
    for v in me.vertices:
        for ge in v.groups:
            Wt[v.index, ge.group] = ge.weight
    Wt /= np.maximum(Wt.sum(1, keepdims=True), 1e-9)
    arm_w = sum(Wt[:, gidx[b]] for b in ('forearm.R', 'hand.R') if b in gidx)
    s = (co - W) @ h
    near = (np.linalg.norm(co - W, axis=1) < 0.25) & (arm_w > 0.5)
    # 前腕の手首の断面（カフの大きさ）：銃の座標の (y, z) − 手首
    band = near & (s > -0.034) & (s < -0.008)
    sec = (co[band] @ Rinv.T + tinv)[:, 1:]          # 銃の座標の (y, z)
    if os.environ.get('HAND_DEBUG'):
        for s0 in np.arange(-0.08, 0.02, 0.01):
            b2 = near & (s > s0) & (s < s0 + 0.01)
            q = (co[b2] @ Rinv.T + tinv)[:, 1:]
            if len(q) > 5:
                print('HANDDBG s', round(s0, 3), len(q), 'y', np.percentile(q[:, 0], [2, 98]).round(3), 'z', np.percentile(q[:, 1], [2, 98]).round(3))
        rr = np.linalg.norm(sec, axis=1)
        print('HANDDBG section', len(sec), np.percentile(rr, [5, 50, 90, 100]).round(4), sec.mean(0).round(4), np.percentile(sec[:, 0], [0, 50, 100]).round(4), np.percentile(sec[:, 1], [0, 50, 100]).round(4))
    H = HD.build(gun_pts, np.array(HAND_WRIST_IN_GUN), sec)

    # 体の右手を消す
    gone = near & (s > HAND_CUT)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if any(gone[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    n2 = len(me.vertices)
    co = np.empty(n2 * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    from scipy.spatial import cKDTree
    s2 = (co - W) @ h
    Wt2 = np.zeros((n2, len(groups)))
    for v in me.vertices:
        for ge in v.groups:
            Wt2[v.index, ge.group] = ge.weight
    Wt2 /= np.maximum(Wt2.sum(1, keepdims=True), 1e-9)
    armw2 = sum(Wt2[:, gidx[b]] for b in ('forearm.R', 'hand.R') if b in gidx)
    near2 = (np.linalg.norm(co - W, axis=1) < 0.25) & (armw2 > 0.5)

    def ramp(sv: np.ndarray) -> np.ndarray:
        f = np.clip((sv - HAND_RAMP[0]) / (HAND_RAMP[1] - HAND_RAMP[0]), 0, 1)
        return f * f * (3 - 2 * f)
    hot = np.zeros(len(groups))
    hot[gidx['hand.R']] = 1.0
    rv = np.nonzero(near2 & (s2 > HAND_RAMP[0]))[0]
    f = ramp(s2[rv])
    Wt2[rv] = (1 - f[:, None]) * Wt2[rv] + f[:, None] * hot
    for vi in rv:
        for gi, vg in enumerate(groups):
            if Wt2[vi, gi] > 1e-4:
                vg.add([int(vi)], float(Wt2[vi, gi]), 'REPLACE')
            else:
                vg.remove([int(vi)])

    # 部品の物体（骨の物体の座標へ）
    R = np.array(place.to_3x3())
    t = np.array(place.translation)
    V = H['V'] @ R.T + t
    F = H['F']
    pm = bpy.data.meshes.new('hand_R')
    pm.from_pydata(V.tolist(), [], F.tolist())
    pm.update()
    obj = bpy.data.objects.new('hand_R', pm)
    bpy.context.scene.collection.objects.link(obj)
    mat = bpy.data.materials.get(CO.PARTS_MAT)
    if mat is None:
        raise SystemExit(f'--hand-part は --costume（材質 {CO.PARTS_MAT}）と一緒に使う')
    pm.materials.append(mat)
    uvname = me.uv_layers.active.name if me.uv_layers.active else 'UVMap'
    uv = pm.uv_layers.new(name=uvname)
    cidx = np.array([CO.NAMES.index(c) for c in H['color']])
    uv.data.foreach_set('uv', np.repeat(CO.palette_uv(cidx), 3, 0).ravel())
    # 重み：掌・指は hand.R に 1。カフ（手首の前後）は、近い体の頂点の重みに同じなめらかな移し方
    sh = (V - W) @ h
    vg_h = obj.vertex_groups.new(name='hand.R')
    cuff = sh < HAND_RAMP[1] + 0.002
    vg_h.add(np.nonzero(~cuff)[0].tolist(), 1.0, 'REPLACE')
    if cuff.any():
        tree = cKDTree(co[near2])
        _, nn = tree.query(V[cuff])
        src = np.nonzero(near2)[0][nn]
        wc = Wt2[src].copy()
        fc = ramp(sh[cuff])
        wc = (1 - fc[:, None]) * wc + fc[:, None] * hot
        cidx_v = np.nonzero(cuff)[0]
        for gi, g in enumerate(groups):
            m = wc[:, gi] > 1e-4
            if m.any():
                vg = obj.vertex_groups.get(g.name) or obj.vertex_groups.new(name=g.name)
                for vi, w in zip(cidx_v[m], wc[m, gi]):
                    vg.add([int(vi)], float(w), 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    # めり込みの確かめ：手の面の点のうち銃の中に入っている数（最近点の法線の向きで判定）
    from mathutils.bvhtree import BVHTree
    gm = gun.data
    gv = [tuple((inv @ v.co)) for v in gm.vertices]
    gbvh = BVHTree.FromPolygons(gv, [tuple(p.vertices) for p in gm.polygons])
    depth = []
    for p in H['V']:
        loc, nrm, _, dist = gbvh.find_nearest(Vector(p))
        if loc is not None:
            depth.append(float((Vector(p) - loc).dot(nrm)))
    depth = np.array(depth)
    rep_pen = {'inside_verts': int((depth < -0.0005).sum()), 'deepest_mm': round(float(-depth.min()) * 1000, 2),
               'touch_verts_2mm': int((np.abs(depth) < 0.002).sum())}
    rep = dict(H['report'])
    rep['penetration'] = rep_pen
    rep.update({'tris': int(len(F)), 'body_verts_removed': int(gone.sum()), 'ramp_verts': int(len(rv)),
                'wrist_in_gun': list(HAND_WRIST_IN_GUN)})
    return {'obj': obj, 'report': rep}


LEFT_HAND_CUT = 0.006          # 体の左手を消す所（手首から手の向きへの距離。手袋のカフの部品 glove_cuff.L の中）
LEFT_HAND_RAMP = (-0.006, 0.014)   # 掌の手首の側と残した手首の体の重みを、前腕から hand.L へなめらかに移す範囲


def add_left_hand_part(body: bpy.types.Object, arm: bpy.types.Object, sx: str = '.L') -> dict:
    """体の左手（手首から先、絵から起こした開いた手）を消し、開いた手の部品（recon/hand.build_open）に置き換える（8 回目）。

    手の座標：+X = hand.L の骨の向き、+Y = 掌（体の内側 = −X の世界）、+Z = 親指の側（正面 = −Y の世界）。
    手袋のカフ（costume の glove_cuff.L、前腕に 1）は残し、その中で体を切る（切り口はカフの中）。重みは掌・指が hand.L に 1、
    手首の側（LEFT_HAND_RAMP）は前腕からなめらかに移す。"""
    sys.path.insert(0, os.path.join(C.REPO, 'tools', 'blender', 'recon'))
    import costume as CO
    import hand as HD
    from scipy.spatial import cKDTree
    # sx：'.L'（ハルの左手）か '.R'（NPC の右手：左右を反転。掌 = 体の内側 = +X の世界）
    sgn = 1.0 if sx == '.L' else -1.0
    cut = CO.HAND.get('LEFT_HAND_CUT', LEFT_HAND_CUT)
    hramp = CO.HAND.get('LEFT_HAND_RAMP', LEFT_HAND_RAMP)
    hb = arm.data.bones['hand' + sx]
    W = np.array(hb.head_local)
    ex = np.array((hb.tail_local - hb.head_local).normalized())
    ey = np.array([-sgn, 0.0, 0.0]) - ex * (-sgn * ex[0])
    ey /= np.linalg.norm(ey)
    ez = np.cross(ex, ey)
    if ez[1] > 0:          # 親指は正面（−Y）へ
        ez = -ez
    Rm = np.stack([ex, ey, ez], 1)        # 手の座標 → 世界
    me = body.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    groups = list(body.vertex_groups)
    gidx = {vg.name: i for i, vg in enumerate(groups)}
    Wt = np.zeros((n, len(groups)))
    for v in me.vertices:
        for ge in v.groups:
            Wt[v.index, ge.group] = ge.weight
    Wt /= np.maximum(Wt.sum(1, keepdims=True), 1e-9)
    arm_w = sum(Wt[:, gidx[b]] for b in ('forearm' + sx, 'hand' + sx) if b in gidx)
    # 部品（材質 haru_parts）の頂点は除く（手袋のカフ・籠手）
    parts_mi = [i for i, m in enumerate(me.materials) if m and m.name.startswith(CO.PARTS_MAT)]
    is_part = np.zeros(n, bool)
    for p in me.polygons:
        if p.material_index in parts_mi:
            is_part[list(p.vertices)] = True
    loc = (co - W) @ Rm                  # 手の座標
    near = (np.linalg.norm(co - W, axis=1) < 0.25) & (arm_w > 0.5) & ~is_part
    band = near & (loc[:, 0] > -0.002) & (loc[:, 0] < 0.012)
    sec = loc[band][:, 1:]
    # 義手（ヤーナの右手、HAND['MECH']）。ほかのキャラクターは MECH が無いので今までどおり
    mech = CO.HAND.get('MECH') if sx == '.R' else None
    H = HD.build_open(sec, mech=mech) if mech else HD.build_open(sec)
    gone = near & (loc[:, 0] > cut)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if any(gone[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    n2 = len(me.vertices)
    co = np.empty(n2 * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    Wt2 = np.zeros((n2, len(groups)))
    for v in me.vertices:
        for ge in v.groups:
            Wt2[v.index, ge.group] = ge.weight
    Wt2 /= np.maximum(Wt2.sum(1, keepdims=True), 1e-9)
    armw2 = sum(Wt2[:, gidx[b]] for b in ('forearm' + sx, 'hand' + sx) if b in gidx)
    x2 = (co - W) @ ex
    near2 = (np.linalg.norm(co - W, axis=1) < 0.25) & (armw2 > 0.5)

    def ramp(sv):
        f = np.clip((sv - hramp[0]) / (hramp[1] - hramp[0]), 0, 1)
        return f * f * (3 - 2 * f)
    hot = np.zeros(len(groups))
    hot[gidx['hand' + sx]] = 1.0
    # 残した手首の体（カフの中）：前腕から hand.L へ
    is_part2 = np.zeros(n2, bool)
    for p in me.polygons:
        if p.material_index in parts_mi:
            is_part2[list(p.vertices)] = True
    rv = np.nonzero(near2 & ~is_part2 & (x2 > hramp[0]))[0]
    f = ramp(x2[rv])
    Wt2[rv] = (1 - f[:, None]) * Wt2[rv] + f[:, None] * hot
    for vi in rv:
        for gi, vg in enumerate(groups):
            if Wt2[vi, gi] > 1e-4:
                vg.add([int(vi)], float(Wt2[vi, gi]), 'REPLACE')
            else:
                vg.remove([int(vi)])
    V = H['V'] @ Rm.T + W
    F = H['F']
    if np.linalg.det(Rm) < 0:            # 左手系なら面を裏返す（外向きのまま）
        F = F[:, ::-1]
    pm = bpy.data.meshes.new('hand' + sx.replace('.', '_'))
    pm.from_pydata(V.tolist(), [], F.tolist())
    pm.update()
    obj = bpy.data.objects.new('hand' + sx.replace('.', '_'), pm)
    bpy.context.scene.collection.objects.link(obj)
    pm.materials.append(bpy.data.materials.get(CO.PARTS_MAT))
    uvname = me.uv_layers.active.name if me.uv_layers.active else 'UVMap'
    uv = pm.uv_layers.new(name=uvname)
    cidx = np.array([CO.NAMES.index(c) for c in H['color']])
    uv.data.foreach_set('uv', np.repeat(CO.palette_uv(cidx), 3, 0).ravel())
    hx = H['V'][:, 0]
    vg_h = obj.vertex_groups.new(name='hand' + sx)
    wr = hx < hramp[1]
    vg_h.add(np.nonzero(~wr)[0].tolist(), 1.0, 'REPLACE')
    if wr.any():
        src_ok = np.nonzero(near2)[0]
        _, nn = cKDTree(co[src_ok]).query(V[wr])
        wc = Wt2[src_ok[nn]].copy()
        fc = ramp(hx[wr])
        wc = (1 - fc[:, None]) * wc + fc[:, None] * hot
        wi = np.nonzero(wr)[0]
        for gi, g in enumerate(groups):
            m = wc[:, gi] > 1e-4
            if m.any():
                vg = obj.vertex_groups.get(g.name) or obj.vertex_groups.new(name=g.name)
                for vi, w in zip(wi[m], wc[m, gi]):
                    vg.add([int(vi)], float(w), 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    rep = dict(H['report'])
    rep.update({'tris': int(len(F)), 'body_verts_removed': int(gone.sum()), 'ramp_verts': int(len(rv)),
                'wrist_section_pts': int(len(sec))})
    return {'obj': obj, 'report': rep}


def find_rail_anchor(pts: np.ndarray, J: dict) -> tuple[list[float], list[float]]:
    """左前腕の外側（体から離れる側）のレールの、手首側の端を形から探す（A ポーズの座標）。

    前腕の軸に直交し、前額面の中で体から離れる向きを「外」とし、前腕の手首寄りの部分で一番外へ出ている所を
    レールの面とみなす。その高さを保って、手首の側へ一番遠くまで続く所を根元にする。
    返り値：(根元の点, 外の向き)
    """
    e, w = np.array(J['forearm']), np.array(J['hand'])
    d = w - e
    L = float(np.linalg.norm(d))
    d /= L
    n = np.array([-d[2], 0.0, d[0]])
    n /= np.linalg.norm(n)
    if n[0] < 0:
        n = -n
    rel = pts - e
    t = rel @ d / L
    radial = rel - np.outer(rel @ d, d)
    r = np.linalg.norm(radial, axis=1)
    m = (t > 0.45) & (t < 1.25) & (r < 0.09)
    if m.sum() < 10:
        return (w + n * 0.04).tolist(), n.tolist()
    lat = radial[m] @ n
    top = lat >= lat.max() - 0.008
    k = np.argmax(np.where(top, t[m], -1))
    p = pts[m][k]
    return p.tolist(), n.tolist()


def add_blade(arm: bpy.types.Object, blade_mat, blade: dict | None = None) -> bpy.types.Object:
    """光刃：左前腕から、前腕と平行に（籠手のレールからは幅の広い平たい帯の刃 58cm、それ以外は 45cm）。

    blade が無ければ従来どおり手首の外側から。blade = {'base': 根元（基準の姿勢の座標）, 'side': 外の向き} なら、
    レールの端から刃を出す（刃の平らな面が外を向く：薄い向き = side、幅の向き = 前腕と side に直交）。
    """
    fl, hl = arm.data.bones['forearm.L'], arm.data.bones['hand.L']
    axis = (fl.tail_local - fl.head_local).normalized()
    if blade:
        side = Vector(blade['side'])
        side = (side - axis * side.dot(axis)).normalized()
        base = Vector(blade['base']) + side * 0.004
        # 平たい帯の刃（light_blade_gauntlet.png：幅 4〜5cm、前腕＋手の約 1.3 倍の長さ、先は斜めに切った形）。
        # 断面は 4 角を 45 度から置いた長方形（半幅 = rx·0.71、半厚 = ry·0.71）：幅 約 4.8cm、厚み 約 6mm。
        # 長さ 0.58m、80% まで同じ幅で、最後の 10cm で片側（幅の向き）へ寄せて細め、斜めの切っ先にする
        width_dir = axis.cross(side).normalized()
        sock = C.empty('blade_socket', base)
        sock.rotation_mode = 'QUATERNION'
        sock.rotation_quaternion = Vector((0, 1, 0)).rotation_difference(axis)
        M.parent_to_bone(sock, arm, 'forearm.L')
        path = [Vector((0, 0, 0)), axis * 0.03, axis * 0.47, axis * 0.58]
        radii = [(0.026, 0.0035), (0.034, 0.0042), (0.034, 0.0042), (0.005, 0.0012)]
        offsets = [Vector((0, 0, 0))] * 3 + [width_dir * 0.021]
        obj = M.loft('LightBlade', path, radii, sides=4, angle0=math.pi / 4, ref=tuple(side), offsets=offsets)
        obj.location = base
        obj.data.materials.append(blade_mat)
        M.smooth(obj, 0)
        M.parent_to_bone(obj, arm, 'forearm.L')
        return obj
    else:
        base = hl.head_local + Vector((0.06, 0, 0.02))
        ref = (0, -1, 0)
        radii = [(0.010, 0.018), (0.012, 0.026), (0.010, 0.022), 0.0]
    sock = C.empty('blade_socket', base)
    sock.rotation_mode = 'QUATERNION'
    sock.rotation_quaternion = Vector((0, 1, 0)).rotation_difference(axis)
    M.parent_to_bone(sock, arm, 'forearm.L')
    obj = M.loft('LightBlade', [Vector((0, 0, 0)), axis * 0.08, axis * 0.36, axis * 0.45],
                 radii, sides=4, angle0=0.0, ref=ref)
    obj.location = base
    obj.data.materials.append(blade_mat)
    M.smooth(obj, 0)
    M.parent_to_bone(obj, arm, 'forearm.L')
    return obj


def blade_material() -> bpy.types.Material:
    """光刃の材質（haru_a と同じ琥珀の発光、少し透ける）。

    発光の強さは 1.0：以前の 3.0 では緑が飽和して、琥珀ではなく白っぽいレモン色に見えた
    （ゲームの player_view.gd も発光の倍率を下げた）"""
    blade = bpy.data.materials.new('haru_blade')
    blade.use_nodes = True
    b = blade.node_tree.nodes['Principled BSDF']
    amber = C.hex_color('#FFBC52')
    b.inputs['Base Color'].default_value = (*amber, 1)
    b.inputs['Emission Color'].default_value = (*amber, 1)
    b.inputs['Emission Strength'].default_value = 1.0
    b.inputs['Alpha'].default_value = 0.85
    blade.surface_render_method = 'BLENDED'
    return blade


def render_check(prefix: str, J: dict) -> None:
    """関節の位置に赤い球を置いて、正面と横を描く"""
    red = C.material('joint_marker', (1, 0.05, 0.05), emission=2.0)
    markers = []
    for k, v in J.items():
        if k.startswith('_'):
            continue
        for side in ((1, -1) if abs(v[0]) > 1e-4 else (1,)):
            markers.append(C.sphere(f'm_{k}', (v[0] * side, v[1], v[2]), 0.018, red, segments=8))
    C.render_views(prefix, (0, 0, HEIGHT / 2), HEIGHT, views={'front': 0, 'side': 90, 'three_quarter': 35}, size=640)
    for m in markers:
        bpy.data.objects.remove(m, do_unlink=True)


# ---------------------------------------------------------------- 全体

def parse_anchor(text: str | None) -> str | list[float] | None:
    if not text or text == 'auto':
        return text
    return [float(c) for c in text.split(',')]


def lowered_point(p: list[float], J: dict, q: Quaternion) -> Vector:
    """A ポーズの左腕の上の点を、腕を下ろした基準の姿勢へ移す（lower_arms と同じ肩まわりの回転 q）"""
    sh = Vector(J['upper_arm'])
    return sh + q @ (Vector(p) - sh)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--turn', type=float, default=0.0)
    ap.add_argument('--keep-frame', action='store_true')
    ap.add_argument('--target-tris', type=int, default=None)
    ap.add_argument('--joints')
    ap.add_argument('--gun')
    ap.add_argument('--blade-anchor')
    ap.add_argument('--grip-fist', help='右手を拳にして銃を握らせる。値は A ポーズの掌の向き x,y,z（ハルは 0,1,0）')
    ap.add_argument('--fist-shapekey', action='store_true',
                    help='拳を基準の姿勢に焼き込まず、シェイプキー fist にする（開いた手が基準。ゲームで fist = 1）')
    ap.add_argument('--rest-arm-deg', type=float, default=None,
                    help='基準の姿勢の腕の開き（正面から見た真下からの角度、度）。前後の軸まわりだけで下ろす')
    ap.add_argument('--fill-unweighted', type=float, default=0.0,
                    help='自動の重みが付かない頂点がこの割合までなら、近い頂点の重みで埋める（既定 0 = 従来どおり）')
    ap.add_argument('--rigid-parts', action='store_true',
                    help='膝当て・右肩の板（下地の色で探す）を 1 本の骨にだけ付ける（テクスチャのある入力）')
    ap.add_argument('--costume', action='store_true',
                    help='服の硬い部品（recon/costume.py）を別の形にして、載る骨 1 本に付ける（ハル）')
    ap.add_argument('--hand-part', action='store_true',
                    help='体の右手を消し、銃を握った手の部品（recon/hand.py）にする。基準の姿勢で握っている（ハル 6 回目）')
    ap.add_argument('--no-weapon', action='store_true', help='銃・光刃・目印を付けない（NPC）')
    ap.add_argument('--final-height', type=float, default=None, help='最後に一様に拡大する身長（m）')
    ap.add_argument('--name', default='Haru', help='物体の名前（骨は <名前>Rig）')
    ap.add_argument('--stats', help='数値の記録の JSON（既定は <出力>.stats.json）')
    ap.add_argument('--render')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])

    body = import_and_normalize(args.input, args.turn, args.keep_frame)
    src_tris = M.tri_count(body)
    textured = has_textures(body)
    pts_apose = verts(body)
    J = load_overrides(estimate_joints(pts_apose), args.joints)
    if args.render:
        render_check(args.render + '_joints', J)
    # テクスチャの付いた入力は、面を減らすと UV の継ぎ目や顔の区画が崩れるので、既定では減らさない
    target = args.target_tris if args.target_tris is not None else (0 if textured else 16000)
    if target > 0:
        decimate(body, target)

    # 光刃の根元（A ポーズで決めて、腕を下ろしたあとの位置へ移す）
    anchor = None if args.no_weapon else parse_anchor(args.blade_anchor)
    blade_apose = None
    if anchor == 'auto':
        if '_blade_anchor' in J:
            base = J['_blade_anchor']
            _, side = find_rail_anchor(pts_apose, J)
        else:
            base, side = find_rail_anchor(pts_apose, J)
        blade_apose = {'base': base, 'side': side}
    elif anchor:
        _, side = find_rail_anchor(pts_apose, J)
        blade_apose = {'base': anchor, 'side': side}

    # 仮の骨（A ポーズ）で重みを付け、腕を下ろして基準の形にする
    tmp = H.build_armature(HEIGHT, 'TmpRig', joints_table(J))
    method = skin(body, tmp, args.fill_unweighted)
    rigid = rigid_parts(body, J) if args.rigid_parts else None
    costume = None
    if args.costume:
        cobj, costume = add_costume(body, tempfile.mkdtemp(prefix='ai_costume_'),
                                    skip=('glove_cuff.R',) if args.hand_part else ())
        body = C.join([body, cobj], 'Body')
    lowered, q_left = lower_arms(body, tmp, args.rest_arm_deg)
    bpy.data.objects.remove(tmp, do_unlink=True)
    body.parent = None
    J2 = dict(J)
    J2.update(lowered)
    blade = None
    if blade_apose:
        blade = {'base': list(lowered_point(blade_apose['base'], J, q_left)),
                 'side': list(q_left @ Vector(blade_apose['side']))}

    # 標準の骨を入れ直す（重みは骨の名前で残っている）
    arm = H.build_armature(HEIGHT, f'{args.name}Rig', joints_table(J2))
    H.finalize_skin(body, arm)
    tex_dir = tempfile.mkdtemp(prefix='ai_char_')
    fix_materials(body, tex_dir)
    grip_info = None
    hand_info = None
    if args.no_weapon:
        parts = []
        if args.hand_part:
            # NPC（バートン）：両手とも力を抜いて開いた手の部品（recon/hand.build_open。右は左右を反転）
            hand_info = {}
            for sx in ('.L', '.R'):
                lp = add_left_hand_part(body, arm, sx)
                body = C.join([body, lp['obj']], body.name)
                hand_info['hand' + sx] = lp['report']
    elif args.gun:
        # 絵から起こした銃。材質は入力（'haru_body'、'haru_face'）と銃（'spark_gun'）のまま
        blade_mat = blade_material()
        grip = None
        hand_info = None
        if args.hand_part:
            place, _, _ = hand_frame(arm)
            gun_obj = add_recon_gun(arm, args.gun, None, place_override=place)
            hp = add_hand_part(body, arm, gun_obj, place)
            body = C.join([body, hp['obj']], body.name)
            hand_info = hp['report']
            # 左手も部品（8 回目：絵から起こした開いた手の手袋の縁がぎざぎざだった）
            lp = add_left_hand_part(body, arm)
            body = C.join([body, lp['obj']], body.name)
            hand_info['left_hand'] = lp['report']
            parts = [gun_obj]
        elif args.grip_fist:
            grip = grip_right_hand(body, arm, Vector([float(c) for c in args.grip_fist.split(',')]),
                                   shape_key=args.fist_shapekey)
        if not args.hand_part:
            parts = [add_recon_gun(arm, args.gun, grip)]
        if grip:
            grip_info = {'fingers_bent': grip['fingers'], 'twist_deg': round(grip['twist_deg'], 1),
                         'grip_origin': [round(c, 4) for c in grip['origin']],
                         'q_palm': grip.get('q_palm'), 'finger_band': grip.get('finger_band'),
                         'band_squeeze': grip.get('band_squeeze')}
        add_blade(arm, blade_mat, blade)
    else:
        parts_mat, face_mat, blade_mat = HA.make_materials(tex_dir)
        parts_mat.name = 'ai_parts'  # 銃など、色見本で塗る部品
        bpy.data.materials.remove(face_mat)
        parts = add_gun_and_blade(arm, parts_mat, blade_mat, blade)
    body = C.join([body] + parts, args.name) if parts else body
    body.name = args.name
    name_images(body)
    H.bake_clips(arm, A.all_clips())
    final_scale = 1.0
    if args.final_height:
        # 骨の物体を一様に拡大（子の体・目印も一緒に。動作の移動の値も骨の物体の中の値なので同じ割合で大きくなる）
        final_scale = args.final_height / HEIGHT
        arm.scale = (final_scale,) * 3
        bpy.context.view_layer.update()

    C.export_glb(args.out)
    stats = {
        'source_tris': src_tris,
        'total_body': M.tri_count(body),
        'vertices_body': len(body.data.vertices),
        'skinning': method,
        'textured_input': textured,
        'decimate_target': target,
        'materials': [m.name for m in body.data.materials if m] + ([] if args.no_weapon else ['haru_blade']),
        'final_scale': round(final_scale, 5),
        'joints': {k: [round(x, 4) for x in v] for k, v in J2.items()},
        # A ポーズ（入力の姿勢）の関節。確認の画像で腕を A ポーズへ戻すのに使う
        'joints_apose': {k: [round(x, 4) for x in v] for k, v in J.items()},
        'blade': {k: [round(x, 4) for x in v] for k, v in blade.items()} if blade else None,
        'grip': grip_info,
        'hand_part': hand_info if (args.gun or args.no_weapon) else None,
        'rigid_parts': rigid,
        'costume': costume,
    }
    with open(args.stats or (os.path.splitext(args.out)[0] + '.stats.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    if args.render:
        C.render_views(args.render, (0, 0, HEIGHT / 2), HEIGHT,
                       views={'front': 0, 'side': 90, 'back': 180, 'three_quarter': 35}, size=640)
    print(json.dumps({k: v for k, v in stats.items() if k not in ('joints', 'joints_apose')}, ensure_ascii=False))
    print('wrote', args.out)


if __name__ == '__main__':
    main()
