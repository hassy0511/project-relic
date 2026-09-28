"""骨を入れたハル（haru_r.glb）の確認の画像を Cycles で描く（build/recon/review/）。

  .venv-blender/bin/python tools/blender/recon/review.py
      [--glb godot/assets/models/haru_r.glb]   骨・動作の入った GLB（ai_character.py の出力）
      [--stats build/recon/haru_r.stats.json]  ai_character.py の記録（A ポーズの関節。腕を A ポーズへ戻すのに使う）
      [--out build/recon/review]
      [--samples 64] [--size 1024]             Cycles の標本数と、大きい画像の一辺の画素数
      [--only compare,face,poses,joints]       一部だけ描く

できるもの
  compare_views.png  左から「元の絵」「Cycles の画像（calib.json の正投影カメラと画素が一致）」「重ね（絵 50%）」。
                     上から正面・右前斜め（calib.json の方位角 約 31 度）・右真横・背面。
                     骨の入った GLB は腕を下ろした基準の姿勢なので、上腕を A ポーズの向き（stats の joints_apose）へ
                     戻してから描く（光刃と銃は隠す。絵には無い）。
  face.png           上の段：顔の近写（正面）を 4 表情（通常・笑顔・驚き・痛み）で。顔の材質の UV を区画の分だけ
                     ずらす（ゲームの uv1_offset と同じ）。下の段：face_atlas.png のその区画。
  poses.png          右前斜め（少し上から）で、run・jump・combo1・combo3・charge・dash・hurt。
                     光刃は斬りの動作（combo1・combo3・charge）だけ表示。銃はいつも表示。
  joints.png         関節の近写：肩・肘・膝・股関節を、動作の中の曲げの大きい所で（銃は隠す）。
                     最後の列は右手の銃の握り（idle、外側と正面から）。

光：白い一様な空の光＋カメラの左上手前からの弱い太陽（絵の「均一な正面の光」に近づける）。色の変換は Standard。
全体で 7〜9 分（4 コアの CPU）。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from lib import common as C  # noqa: E402
from recon import views as V  # noqa: E402

REPO = C.REPO
RECON = os.path.join(REPO, 'build', 'recon')
BG = 50            # 背景の灰色（8 bit）
EXPRESSIONS = ['normal', 'smile', 'surprise', 'pain']

# 動作の確認：(動作, フレーム, 光刃を出すか)
POSES = [('run', 1, False), ('jump', 5, False), ('combo1', 5, True), ('combo3', 8, True),
         ('charge', 12, True), ('dash', 4, False), ('hurt', 5, False)]

# 関節の近写：(見出し, 動作, フレーム, 中心にする骨の根元（複数なら中点）, 方位角, 幅 m, 銃を出すか)
# 銃は関節を隠すので、握りの確認（最後の 2 枚）のときだけ出す
JOINT_SHOTS = [
    ('L shoulder: combo3 f1 (arm raised)', 'combo3', 1, ['upper_arm.L', 'forearm.L'], -150, 0.70, False),
    ('R shoulder: fall f11 (arm out)', 'fall', 11, ['upper_arm.R'], 0, 0.50, False),
    ('L elbow: combo1 f1', 'combo1', 1, ['forearm.L'], -45, 0.42, False),
    ('R elbow: run f6 (-70)', 'run', 6, ['forearm.R'], 90, 0.42, False),
    ('gun grip: idle f1', 'idle', 1, ['hand.R'], 90, 0.40, True),
    ('knees: dead f19 (125)', 'dead', 19, ['shin.L', 'shin.R'], 60, 0.60, False),
    ('L knee: jump f5 (85)', 'jump', 5, ['shin.L'], -90, 0.45, False),
    ('hips: dash f4 (split)', 'dash', 4, ['thigh.L', 'thigh.R'], 90, 0.60, False),
    ('hips: jump f5', 'jump', 5, ['thigh.L', 'thigh.R'], 35, 0.60, False),
    ('gun grip: idle f1', 'idle', 1, ['hand.R'], 0, 0.40, True),
]


# ---------------------------------------------------------------- 場面

class Scene:
    def __init__(self, glb: str, samples: int):
        C.reset_scene()
        bpy.ops.import_scene.gltf(filepath=glb)
        objs = list(bpy.context.scene.objects)
        self.arm = next(o for o in objs if o.type == 'ARMATURE')
        self.blade = next((o for o in objs if o.name.startswith('LightBlade')), None)
        # 骨の形の表示に読み込まれる球などは描かない
        for o in objs:
            if o.type == 'MESH' and o.parent is None:
                bpy.data.objects.remove(o, do_unlink=True)
        self.body = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o is not self.blade)
        ad = self.arm.animation_data
        if ad:
            for t in ad.nla_tracks:
                t.mute = True
            ad.action = None
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.device = 'CPU'
        sc.cycles.samples = samples
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.use_denoising = True
        # 銃を隠すときの透明な材質は面が何枚も重なるので、透明の跳ね返りの上限を上げる（足りないと黒く残る）
        sc.cycles.transparent_max_bounces = 128
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
        sc.render.film_transparent = True
        sc.view_settings.view_transform = 'Standard'
        world = bpy.data.worlds.new('review_world')
        sc.world = world
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
        world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.75
        cd = bpy.data.cameras.new('review_cam')
        cd.type = 'ORTHO'
        cd.clip_end = 30
        self.cam = bpy.data.objects.new('review_cam', cd)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        ld = bpy.data.lights.new('review_sun', 'SUN')
        ld.energy = 1.6
        ld.angle = math.radians(15)
        self.sun = bpy.data.objects.new('review_sun', ld)
        sc.collection.objects.link(self.sun)
        self.scene = sc
        self._hidden_mat = None

    # ---- 姿勢
    def rest(self) -> None:
        ad = self.arm.animation_data
        if ad:
            ad.action = None
        for pb in self.arm.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    def pose(self, action: str, frame: int) -> None:
        self.rest()
        act = bpy.data.actions.get(action) or next(a for a in bpy.data.actions if a.name.startswith(action))
        ad = self.arm.animation_data or self.arm.animation_data_create()
        ad.action = act
        if hasattr(ad, 'action_slot') and getattr(act, 'slots', None) and len(act.slots):
            ad.action_slot = act.slots[0]
        self.scene.frame_set(frame)
        bpy.context.view_layer.update()

    def apose(self, stats: dict | None) -> None:
        """上腕を A ポーズ（入力の姿勢）の向きへ戻す。腕を下ろしたときと同じく、肩の関節まわりに回す"""
        self.rest()
        if not stats or 'joints_apose' not in stats:
            return
        ja = stats['joints_apose']
        mw = self.arm.matrix_world
        for side, sx in ((1, '.L'), (-1, '.R')):
            pb = self.arm.pose.bones['upper_arm' + sx]
            head = mw @ pb.head
            cur = ((mw @ pb.tail) - head).normalized()
            a, b = Vector(ja['upper_arm']), Vector(ja['forearm'])
            want = (b - a).normalized()
            # ai_character.py の --rest-arm-deg と同じく、前後の軸（Y）まわりだけで回す（前後の傾きは保つ）
            ang = math.atan2(cur.x * side, -cur.z) - math.atan2(want.x, -want.z)
            q = Quaternion(Vector((0.0, 1.0, 0.0)), ang * side)
            # 世界の回転を、骨の姿勢の行列（アーマチュアの座標）に掛ける
            hl = pb.head.copy()
            rl = (mw.to_3x3().inverted() @ q.to_matrix() @ mw.to_3x3()).to_4x4()
            pb.matrix = Matrix.Translation(hl) @ rl @ Matrix.Translation(-hl) @ pb.matrix
            bpy.context.view_layer.update()

    def bone_head(self, name: str) -> Vector:
        return self.arm.matrix_world @ self.arm.pose.bones[name].head

    # ---- 見せ方
    def show_blade(self, on: bool) -> None:
        if self.blade:
            self.blade.hide_render = not on

    def show_gun(self, on: bool) -> None:
        """銃の材質の枠を、透明な材質と入れ替える（銃は体のメッシュに結合されている）"""
        slots = [s for s in self.body.material_slots if s.material and s.material.name.startswith('spark_gun')]
        if not on:
            if self._hidden_mat is None:
                m = bpy.data.materials.new('review_hidden')
                m.use_nodes = True
                nt = m.node_tree
                nt.nodes.clear()
                out = nt.nodes.new('ShaderNodeOutputMaterial')
                tr = nt.nodes.new('ShaderNodeBsdfTransparent')
                nt.links.new(tr.outputs[0], out.inputs['Surface'])
                self._hidden_mat = m
                self._gun_mat = slots[0].material if slots else None
            for s in self.body.material_slots:
                if s.material is self._gun_mat:
                    s.material = self._hidden_mat
        elif self._hidden_mat is not None:
            for s in self.body.material_slots:
                if s.material is self._hidden_mat:
                    s.material = self._gun_mat

    def face_offset(self, i: int) -> None:
        """顔の材質の UV を表情 i の区画へずらす（Godot の uv1_offset = ((i%2)*0.5, floor(i/2)*0.5) と同じ。
        glTF の v は下向きなので、Blender の v では -0.5）"""
        for m in bpy.data.materials:
            if 'face' not in m.name or not m.use_nodes:
                continue
            nt = m.node_tree
            mp = nt.nodes.get('review_mapping')
            if mp is None:
                tc = nt.nodes.new('ShaderNodeUVMap')
                mp = nt.nodes.new('ShaderNodeMapping')
                mp.name = 'review_mapping'
                nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
                for n in nt.nodes:
                    if n.type == 'TEX_IMAGE':
                        nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
            mp.inputs['Location'].default_value = ((i % 2) * 0.5, -(i // 2) * 0.5, 0.0)

    # ---- 描く
    def render(self, center, d, r, ortho: float, size: int, path: str, samples: int | None = None) -> np.ndarray:
        d = Vector(d).normalized()
        r = Vector(r).normalized()
        up = r.cross(d).normalized()
        rot = Matrix((r, up, -d)).transposed()
        self.cam.matrix_world = Matrix.Translation(Vector(center) - d * 10.0) @ rot.to_4x4()
        self.cam.data.ortho_scale = ortho
        ldir = (-d + (-r) * 0.5 + Vector((0, 0, 1)) * 0.8).normalized()
        self.sun.matrix_world = ldir.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        sc = self.scene
        sc.render.resolution_x = sc.render.resolution_y = size
        keep = sc.cycles.samples
        if samples:
            sc.cycles.samples = samples
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        sc.cycles.samples = keep
        img = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32)
        a = img[..., 3:4] / 255
        return (img[..., :3] * a + BG * (1 - a)).astype(np.uint8)


def az_dirs(az: float, elev: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """方位角 az（度、0 = 正面、90 = 本人の右）、上から elev 度。カメラの視線と画像の右"""
    a, e = math.radians(az), math.radians(elev)
    d = np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e)])
    r = np.array([math.cos(a), -math.sin(a), 0.0])
    return d, r


# ---------------------------------------------------------------- 画像の組み立て

def art_on_grey(view: str, size: int) -> np.ndarray:
    rgba = V.load_rgba(view).astype(np.float32)
    a = rgba[..., 3:4] / 255
    rgb = (rgba[..., :3] * a + BG * (1 - a)).astype(np.uint8)
    return np.asarray(Image.fromarray(rgb).resize((size, size), Image.LANCZOS))


def label(arr: np.ndarray, text: str) -> np.ndarray:
    im = Image.fromarray(arr)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 8 + 7 * len(text), 22], fill=(0, 0, 0))
    dr.text((5, 5), text, fill=(255, 230, 0))
    return np.asarray(im)


def grid(rows: list[list[np.ndarray]]) -> np.ndarray:
    w = max(sum(p.shape[1] for p in row) for row in rows)
    out = []
    for row in rows:
        r = np.concatenate(row, 1)
        out.append(np.pad(r, ((0, 0), (0, w - r.shape[1]), (0, 0)), constant_values=BG))
    return np.concatenate(out, 0)


# ---------------------------------------------------------------- 各画像

def compare_views(S: Scene, stats: dict | None, out: str, size: int) -> None:
    cams = V.load_calib()
    S.apose(stats)
    S.show_blade(False)
    S.show_gun(False)
    rows = []
    for name in ('front', 'three_quarter', 'side_right', 'back'):
        c = cams[name]
        b = c.blender_camera()
        ren = S.render(b['center'], b['direction'], b['right'], b['ortho_scale'], size,
                       os.path.join(out, 'tmp', f'cmp_{name}.png'))
        art = art_on_grey(name, size)
        mix = (art.astype(np.float32) * 0.5 + ren.astype(np.float32) * 0.5).astype(np.uint8)
        rows.append([label(art, f'art {name}'), label(ren, f'render {name} (az {c.azimuth:.1f}, calib camera)'),
                     label(mix, 'overlay 50/50')])
    S.show_gun(True)
    Image.fromarray(grid(rows)).save(os.path.join(out, 'compare_views.png'))


def face(S: Scene, out: str, size: int) -> None:
    S.rest()
    S.show_blade(False)
    head = S.bone_head('head')
    center = (0.0, head.y, 1.365)
    d, r = az_dirs(0)
    atlas = Image.open(os.path.join(RECON, 'face_atlas.png')).convert('RGB')
    aw, ah = atlas.size
    top, bottom = [], []
    for i, name in enumerate(EXPRESSIONS):
        S.face_offset(i)
        ren = S.render(center, d, r, 0.36, size, os.path.join(out, 'tmp', f'face_{name}.png'))
        top.append(label(ren, f'{name} (uv offset {(i % 2) * 0.5}, {(i // 2) * 0.5})'))
        qx, qy = (i % 2) * aw // 2, (i // 2) * ah // 2
        q = atlas.crop((qx, qy, qx + aw // 2, qy + ah // 2)).resize((size, size), Image.LANCZOS)
        bottom.append(label(np.asarray(q), f'face_atlas quadrant {i}: {name}'))
    S.face_offset(0)
    Image.fromarray(grid([top, bottom])).save(os.path.join(out, 'face.png'))


def poses(S: Scene, out: str, size: int) -> None:
    d, r = az_dirs(35, 8)
    panels = []
    for action, frame, blade in POSES:
        S.pose(action, frame)
        S.show_blade(blade)
        hips = S.bone_head('hips')
        center = (hips.x, hips.y, 0.78)
        ren = S.render(center, d, r, 1.95, size, os.path.join(out, 'tmp', f'pose_{action}.png'))
        panels.append(label(ren, f'{action} f{frame}' + (' (blade)' if blade else '')))
    S.show_blade(False)
    S.rest()
    rows = [panels[:4], panels[4:]]
    Image.fromarray(grid(rows)).save(os.path.join(out, 'poses.png'))


def joints(S: Scene, out: str, size: int, samples: int) -> None:
    S.show_blade(False)
    panels = []
    for title, action, frame, bones, az, width, gun in JOINT_SHOTS:
        S.pose(action, frame)
        S.show_gun(gun)
        c = sum((S.bone_head(b) for b in bones), Vector()) / len(bones)
        d, r = az_dirs(az)
        ren = S.render(tuple(c), d, r, width, size, os.path.join(out, 'tmp', f'joint_{len(panels)}.png'),
                       samples=samples)
        panels.append(label(ren, f'{title}  az {az}'))
    S.rest()
    S.show_gun(True)
    Image.fromarray(grid([panels[:5], panels[5:]])).save(os.path.join(out, 'joints.png'))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb', default=os.path.join(REPO, 'godot', 'assets', 'models', 'haru_r.glb'))
    ap.add_argument('--stats', default=None)
    ap.add_argument('--out', default=os.path.join(RECON, 'review'))
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--size', type=int, default=1024)
    ap.add_argument('--only', default='compare,face,poses,joints')
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    stats_path = args.stats
    if stats_path is None:
        for p in (os.path.join(RECON, 'haru_r.stats.json'), os.path.splitext(args.glb)[0] + '.stats.json'):
            if os.path.exists(p):
                stats_path = p
                break
    stats = None
    if stats_path and os.path.exists(stats_path):
        with open(stats_path) as f:
            stats = json.load(f)
    else:
        print('記録（stats）が無いので、比べる画像は腕を下ろしたまま描く')
    os.makedirs(os.path.join(args.out, 'tmp'), exist_ok=True)
    S = Scene(args.glb, args.samples)
    only = set(args.only.split(','))
    t0 = time.time()
    if 'compare' in only:
        compare_views(S, stats, args.out, args.size)
        print(f'compare_views.png {time.time() - t0:.0f} 秒', flush=True)
    if 'face' in only:
        face(S, args.out, args.size * 3 // 4)
        print(f'face.png {time.time() - t0:.0f} 秒', flush=True)
    if 'poses' in only:
        poses(S, args.out, args.size * 3 // 4)
        print(f'poses.png {time.time() - t0:.0f} 秒', flush=True)
    if 'joints' in only:
        joints(S, args.out, args.size // 2, max(16, args.samples // 2))
        print(f'joints.png {time.time() - t0:.0f} 秒', flush=True)
    print('wrote', args.out)


if __name__ == '__main__':
    main()
