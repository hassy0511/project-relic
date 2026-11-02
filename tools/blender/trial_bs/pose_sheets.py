"""段 2 の確かめの絵：骨と重みの試しの姿勢（rig_poses.jpg）と、14 の動作の要のこま（anim_clips_*.jpg）。

  .venv-blender/bin/python tools/blender/trial_bs/pose_sheets.py [poses] [clips] [--only idle,run]

スキル集の rigging（Deformation Test Poses）と animation（Blocking の姿勢・輪の確かめ・止めた絵で攻撃の向きが読めるか）の
確かめを、MCP の画面の代わりに Cycles の静止画で行う（render_compare.py と同じ発光のトゥーン、1 本のスレッド）。
入力：build/trial_bs/haru_bs_anim.blend（build_haru_bs.py --anim）。出力：docs/art_orders/haru_bs_trial/*.jpg
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'build', 'trial_bs')
DOC = os.path.join(ROOT, 'docs', 'art_orders', 'haru_bs_trial')

import bpy
from mathutils import Vector, Matrix, Euler
from PIL import Image, ImageDraw

import render_compare as RC
import anim as A

ATTACKS = ('combo1', 'combo2', 'combo3', 'air', 'lunge', 'charge', 'dash')
PHASE = {}


def setup(arm):
    RC.toon_materials(Vector((-0.45, -0.75, 0.55)).normalized())
    cam = bpy.data.objects.new('CAM_Sheet', bpy.data.cameras.new('CAM_Sheet'))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    bpy.context.scene.camera = cam
    return cam


def place_cam(cam, rz, center=Vector((0, 0, 0.82)), scale=2.0):
    m = Euler((math.radians(80), 0, math.radians(rz)), 'XYZ').to_matrix()
    back = m @ Vector((0, 0, 1))
    cam.matrix_world = Matrix.Translation(center + back * 6.0) @ m.to_4x4()
    cam.data.ortho_scale = scale
    cam.data.clip_end = 20


def show_blade(on):
    b = bpy.data.objects['LightBlade']
    b.hide_render = not on


def shot(path, res):
    RC.render(None, path, res=res)
    return Image.open(path).convert('RGBA')


def cell(img, label, sub, w, h, bg=(214, 214, 210)):
    c = Image.new('RGB', (w, h), bg)
    im = img.resize((w, w), Image.LANCZOS) if img.size[0] != w else img
    c.paste(im, (0, h - w), im)
    d = ImageDraw.Draw(c)
    d.text((6, 4), label, fill=(30, 30, 30), font=RC.font(18))
    if sub:
        d.text((6, 26), sub, fill=(90, 60, 30), font=RC.font(15))
    return c


def rig_poses(arm):
    cam = setup(arm)
    iks = {s: (bpy.data.objects['IK_foot.' + s], bpy.data.objects['IK_knee.' + s],
               arm.pose.bones['shin.' + s].constraints[0]) for s in ('L', 'R')}
    arm.animation_data.action = None
    for tr in arm.animation_data.nla_tracks:
        tr.mute = True
    for s in iks:
        iks[s][2].mute = False
    show_blade(False)
    tmp = os.path.join(OUT, 's2', 'poses')
    os.makedirs(tmp, exist_ok=True)
    cells = []
    W, H = 300, 340
    # 2 つ目の絵：曲がる所の寄り（rz、中心、写す幅 m、札）
    CLOSE = {
        'A ポーズ（基準）': (180, Vector((0, 0, 0.82)), 1.75, '後ろ'),
        '腕を上げきる': (-20, Vector((0, 0, 1.10)), 0.70, '肩の寄り'),
        '深くしゃがむ': (-90, Vector((0, -0.06, 0.50)), 1.15, '腰・膝の寄り（右の真横）'),
        '首：右へ・上': (-30, Vector((0, 0, 1.24)), 0.55, '首の寄り'),
        '首：左へ・下': (35, Vector((0, 0, 1.24)), 0.55, '首の寄り'),
        '走りの一歩': (-90, Vector((0, 0, 0.82)), 1.75, '右の真横'),
        '剣の振り（溜め斬り）': (40, Vector((0, 0, 0.90)), 1.75, '左前'),
        '剣の構え（3 段斬り 1）': (40, Vector((0, 0, 0.90)), 1.75, '左前'),
    }
    for i, (name, pose) in enumerate(A.test_poses().items()):
        if '剣' in name:
            show_blade(True)
        A.apply_static_pose(arm, pose, iks)
        row = []
        rz2, c2, s2, lab2 = CLOSE[name]
        for j, (rz, center, scale, lab) in enumerate(((-30, Vector((0, 0, 0.86)), 1.75, '右前'), (rz2, c2, s2, lab2))):
            place_cam(cam, rz, center=center, scale=scale)
            im = shot(os.path.join(tmp, '%02d_%d.png' % (i, j)), 512)
            row.append(cell(im, name if j == 0 else '', lab, W, H))
        show_blade(False)
        cells.append(row)
    # 首の極端は頭の寄り
    sheet = Image.new('RGB', (W * 4, H * 4 + 30), (214, 214, 210))
    for i, row in enumerate(cells):
        for j, c in enumerate(row):
            sheet.paste(c, ((i % 2) * 2 * W + j * W, (i // 2) * H))
    d = ImageDraw.Draw(sheet)
    d.text((8, H * 4 + 6), 'haru_bs 骨と重みの試しの姿勢（rigging の Deformation Test Poses ＋ 走りの一歩・剣の振り）。左：右前から、右：曲がる所の寄り',
           fill=(40, 40, 40), font=RC.font(16))
    os.makedirs(DOC, exist_ok=True)
    p = os.path.join(DOC, 'rig_poses.jpg')
    sheet.save(p, quality=84)
    print('WROTE', p, os.path.getsize(p))


def clip_frames(name, cl):
    ks = [f for f, _ in cl['keys']]
    if name == 'idle':
        return [0, 30, 60, 90, 120]
    if name == 'run':
        return [0, 2.5, 5, 12, 20, 28]
    if name == 'drill':
        return [0, 2, 4, 6]
    fr = [f for f in ks]
    if len(fr) > 6:
        fr = fr[:6]
    return fr


def phase_label(name, f, length):
    if name in ATTACKS:
        hit = length * 0.25
        if name == 'dash':
            hit = length * 0.25
        if f < hit - 0.01:
            return '予備動作'
        if abs(f - hit) < 0.6:
            return '振り抜き（25%）'
        if f <= length * 0.7:
            return '振り切り'
        return '戻り'
    return ''


def clips_sheets(arm, only=None):
    cam = setup(arm)
    for s in ('L', 'R'):
        for c in arm.pose.bones['shin.' + s].constraints:
            c.mute = True      # 脚は焼いたキーで動く
    tracks = {tr.name: tr for tr in arm.animation_data.nla_tracks}
    for tr in tracks.values():
        tr.mute = True
    C = A.clips()
    groups = [('anim_clips_move.jpg', ['idle', 'run', 'jump', 'fall', 'dash', 'drill', 'hurt', 'dead']),
              ('anim_clips_combat.jpg', ['combo1', 'combo2', 'combo3', 'air', 'lunge', 'charge'])]
    tmp = os.path.join(OUT, 's2', 'clips')
    os.makedirs(tmp, exist_ok=True)
    W, H = 220, 262
    sc = bpy.context.scene
    for fname, names in groups:
        if only and not any(n in only for n in names):
            continue
        rows = []
        for name in names:
            if only and name not in only:
                continue
            cl = C[name]
            act = tracks[name].strips[0].action
            arm.animation_data.action = act
            show_blade(name in ATTACKS and name != 'dash' or name == 'dash')
            row = []
            for f in clip_frames(name, cl):
                sc.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
                # 止めた絵で向きが読める角度（combat-animation：Freeze-frame test）。走る・突きは横、ほかは右前
                rz = {'run': -90, 'lunge': 70, 'drill': -65, 'dash': -70}.get(name, -35)
                center = Vector((0, -0.1 if name == 'dead' else 0, 0.82 if name != 'dead' else 0.55))
                place_cam(cam, rz, center=center, scale=2.1)
                im = shot(os.path.join(tmp, '%s_%05.2f.png' % (name, f)), 440)
                lab = ('%s  ' % name if not row else '') + 'こま %g' % f
                row.append(cell(im, lab, phase_label(name, f, cl['length']), W, H))
            rows.append(row)
        arm.animation_data.action = None
        if not rows:
            continue
        ncol = max(len(r) for r in rows)
        sheet = Image.new('RGB', (W * ncol, H * len(rows) + 30), (214, 214, 210))
        for i, row in enumerate(rows):
            for j, c in enumerate(row):
                sheet.paste(c, (j * W, i * H))
        d = ImageDraw.Draw(sheet)
        d.text((8, H * len(rows) + 6), 'haru_bs の動作の要のこま（60 こま/秒。攻撃は攻撃時間に合わせて流れ、振り抜き＝当たりの始まり 25%）',
               fill=(40, 40, 40), font=RC.font(15))
        p = os.path.join(DOC, fname)
        sheet.save(p, quality=82)
        print('WROTE', p, os.path.getsize(p))


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    only = None
    if '--only' in argv:
        only = argv[argv.index('--only') + 1].split(',')
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'haru_bs_anim.blend'))
    arm = bpy.data.objects['ARM_HaruBS']
    if 'poses' in argv or not any(a in argv for a in ('poses', 'clips')):
        rig_poses(arm)
        bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'haru_bs_anim.blend'))
        arm = bpy.data.objects['ARM_HaruBS']
    if 'clips' in argv or not any(a in argv for a in ('poses', 'clips')):
        clips_sheets(arm, only)
