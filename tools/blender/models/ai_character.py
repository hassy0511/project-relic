"""AI が作った 3D（TRELLIS.2 などの GLB）を、ゲームで動かせるキャラクターにする。

入力：A ポーズで立つ人物の GLB（骨なし・1 つの塊。発注書 W1-00 の条件で描いた絵から作ったもの）
出力：標準の人型の骨・重み・14 動作・銃・光刃・目印つきの GLB

  python tools/blender/models/ai_character.py --input <入力.glb> --out <出力.glb>
      [--turn 度]          正面が -Y（glTF では +Z）を向くように回す角度（向きが違うとき）
      [--target-tris 数]   面を減らす目標（既定 16000）
      [--joints <json>]    関節の位置を手で直す（自動の推定を上書き。単位は m）
      [--render <接頭辞>]  確認用の画像（関節の目印つき）

手順：
 1. 向き・大きさ（身長 1.55m）・足の位置をそろえる
 2. 形から関節の位置を推定する（腕は A ポーズの腕の軸を直線で当てはめる）
 3. 面を減らす
 4. 骨の重みを付ける（Blender の自動の重み。失敗したら骨までの距離の重み）
 5. 腕を下ろして、その姿勢を新しい基準の姿勢にする（標準の動作が使えるように）
 6. 標準の骨を入れ直し、動作・銃・光刃・目印を付けて書き出す
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
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

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

def import_and_normalize(path: str, turn: float) -> bpy.types.Object:
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


def skin(body: bpy.types.Object, arm: bpy.types.Object) -> str:
    """自動の重み（骨の熱の広がり）。うまくいかない頂点が多ければ、骨までの距離の重みにする"""
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    method = 'heat'
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except RuntimeError:
        method = 'distance'
    unweighted = sum(1 for v in body.data.vertices if not any(g.weight > 0.001 for g in v.groups))
    if method == 'heat' and unweighted > len(body.data.vertices) * 0.005:
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


def lower_arms(body: bpy.types.Object, arm: bpy.types.Object) -> dict:
    """腕を下ろした姿勢を、メッシュの新しい基準の形にする。下ろしたあとの関節の位置を返す"""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    for side, sx in ((1, '.L'), (-1, '.R')):
        pb = arm.pose.bones['upper_arm' + sx]
        cur = (pb.tail - pb.head).normalized()
        want = Vector((REST_ARM_DIR.x * side, REST_ARM_DIR.y, REST_ARM_DIR.z))
        q = cur.rotation_difference(want)
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
    return new


# ---------------------------------------------------------------- 6. 材質、銃、光刃

def fix_materials(body: bpy.types.Object, tex_dir: str) -> None:
    """AI の材質は金属っぽさが混ざりがちなので、ゲームの塗りに合わせる。琥珀色の部分を光らせる"""
    for mat in body.data.materials:
        if not mat or not mat.use_nodes:
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


def add_gun_and_blade(arm: bpy.types.Object, gun_mat, blade_mat) -> list[bpy.types.Object]:
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
    # 光刃：手首の外側から、前腕の向きに 45cm
    fl, hl = arm.data.bones['forearm.L'], arm.data.bones['hand.L']
    axis = (fl.tail_local - fl.head_local).normalized()
    base = hl.head_local + Vector((0.06, 0, 0.02))
    sock = C.empty('blade_socket', base)
    sock.rotation_mode = 'QUATERNION'
    sock.rotation_quaternion = Vector((0, 1, 0)).rotation_difference(axis)
    M.parent_to_bone(sock, arm, 'forearm.L')
    blade = M.loft('LightBlade', [Vector((0, 0, 0)), axis * 0.08, axis * 0.36, axis * 0.45],
                   [(0.010, 0.018), (0.012, 0.026), (0.010, 0.022), 0.0], sides=4, angle0=0.0, ref=(0, -1, 0))
    blade.location = base
    blade.data.materials.append(blade_mat)
    M.smooth(blade, 0)
    M.parent_to_bone(blade, arm, 'forearm.L')
    return parts


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

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--turn', type=float, default=0.0)
    ap.add_argument('--target-tris', type=int, default=16000)
    ap.add_argument('--joints')
    ap.add_argument('--render')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])

    body = import_and_normalize(args.input, args.turn)
    src_tris = M.tri_count(body)
    J = load_overrides(estimate_joints(verts(body)), args.joints)
    if args.render:
        render_check(args.render + '_joints', J)
    decimate(body, args.target_tris)

    # 仮の骨（A ポーズ）で重みを付け、腕を下ろして基準の形にする
    tmp = H.build_armature(HEIGHT, 'TmpRig', joints_table(J))
    method = skin(body, tmp)
    lowered = lower_arms(body, tmp)
    bpy.data.objects.remove(tmp, do_unlink=True)
    body.parent = None
    J2 = dict(J)
    J2.update(lowered)

    # 標準の骨を入れ直す（重みは骨の名前で残っている）
    arm = H.build_armature(HEIGHT, 'HaruRig', joints_table(J2))
    H.finalize_skin(body, arm)
    tex_dir = tempfile.mkdtemp(prefix='ai_char_')
    fix_materials(body, tex_dir)
    parts_mat, face_mat, blade_mat = HA.make_materials(tex_dir)
    parts_mat.name = 'ai_parts'  # 銃など、色見本で塗る部品
    bpy.data.materials.remove(face_mat)
    parts = add_gun_and_blade(arm, parts_mat, blade_mat)
    body = C.join([body] + parts, 'Haru')
    H.bake_clips(arm, A.all_clips())

    C.export_glb(args.out)
    stats = {
        'source_tris': src_tris,
        'total_body': M.tri_count(body),
        'vertices_body': len(body.data.vertices),
        'skinning': method,
        'materials': [m.name for m in body.data.materials if m] + ['haru_blade'],
        'joints': {k: [round(x, 4) for x in v] for k, v in J2.items()},
    }
    with open(os.path.splitext(args.out)[0] + '.stats.json', 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    if args.render:
        C.render_views(args.render, (0, 0, HEIGHT / 2), HEIGHT,
                       views={'front': 0, 'side': 90, 'back': 180, 'three_quarter': 35}, size=640)
    print(json.dumps({k: v for k, v in stats.items() if k != 'joints'}, ensure_ascii=False))
    print('wrote', args.out)


if __name__ == '__main__':
    main()
