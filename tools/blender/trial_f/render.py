"""haru_f：絵と同じ枠の正投影で描く（Cycles）。絵と並べた比べの画像を作る。"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector
from PIL import Image

ART = 'build/art_f/'
PX_PER_M = (1922 - 125) / 1.55
# 視点：名前 → (方位角（正面 0、本人の左が正）, 絵のファイル)
VIEWS = {
    'front': (0, 'haru_3d_front'), 'back': (180, 'haru_3d_back'), 'right': (-90, 'haru_3d_side_right'),
    'right_noarms': (-90, 'haru_3d_side_right_noarms'), 'left': (90, 'haru_3d_side_left'),
    'fr45': (-45, 'haru_3d_front_right45'), 'fl45': (45, 'haru_3d_front_left45'),
}
DEPTH0 = 0.021      # 真横の絵の中心は、原点から 2.1 cm 後ろ


def setup(size=1024, samples=24):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.device = 'CPU'
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('W')
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.62
    sc.world = w
    cam = bpy.data.cameras.new('Cam')
    cam.type = 'ORTHO'
    ob = bpy.data.objects.new('Cam', cam)
    sc.collection.objects.link(ob)
    sc.camera = ob
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 2.0
    sun.angle = math.radians(20)
    so = bpy.data.objects.new('Sun', sun)
    sc.collection.objects.link(so)
    return ob, so


def aim(cam, sun, az_deg, center, scale, elev_deg=0.0, dist=6.0):
    a, e = math.radians(az_deg), math.radians(elev_deg)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))     # 正面の視点は -y の側
    c = Vector(center)
    cam.location = c + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = scale
    cam.data.clip_end = 30
    # 光：視点の少し上・少し左から
    ls = (d + Vector((0, 0, 0.55)) + Vector((-d.y, d.x, 0)) * 0.35).normalized()
    sun.rotation_euler = (-ls).to_track_quat('-Z', 'Y').to_euler()


def render_view(cam, sun, name, out, size=1024):
    az, _ = VIEWS[name]
    full = 2048 / PX_PER_M
    zc = (1922 - 1024) / PX_PER_M
    a = math.radians(az)
    # 絵の中心の列：正面は x=0、真横は前後の DEPTH0
    c = Vector((0, DEPTH0, zc)) if abs(az) == 90 else Vector((0, DEPTH0 * abs(math.sin(a)), zc))
    aim(cam, sun, az, c, full)
    bpy.context.scene.render.filepath = os.path.abspath(out)
    bpy.ops.render.render(write_still=True)


def art_img(name, size):
    im = Image.open(ART + name + '.png').convert('RGBA').resize((size, size), Image.LANCZOS)
    return im


def over(im, bg=(128, 128, 136)):
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    return b.convert('RGB')


def compare_sheet(names, render_dir, out, size=1024, crop=None):
    """絵 | モデル | 重ね（絵の外形を赤、モデルを青）を視点ごとに 1 行"""
    from PIL import ImageChops, ImageFilter
    rows = []
    for n in names:
        art = art_img(VIEWS[n][1], size)
        ren = Image.open(os.path.join(render_dir, n + '.png')).convert('RGBA')
        a1 = art.getchannel('A').point(lambda v: 255 if v > 128 else 0)
        a2 = ren.getchannel('A').point(lambda v: 255 if v > 128 else 0)
        e1 = ImageChops.difference(a1.filter(ImageFilter.MaxFilter(3)), a1)
        e2 = ImageChops.difference(a2.filter(ImageFilter.MaxFilter(3)), a2)
        ov = Image.merge('RGB', (e1, Image.new('L', a1.size, 0), e2))
        ov = Image.blend(over(art), over(ren), 0.5)
        # 外形の重なり（IoU）
        import numpy as np
        A, B = np.array(a1) > 0, np.array(a2) > 0
        iou = (A & B).sum() / max(1, (A | B).sum())
        row = Image.new('RGB', (size * 3, size), (128, 128, 136))
        row.paste(over(art), (0, 0))
        row.paste(over(ren), (size, 0))
        row.paste(ov, (size * 2, 0))
        if crop:
            x0, y0, x1, y1 = [int(v * size) for v in crop]
            row = Image.fromarray(np.concatenate([np.array(row)[y0:y1, k * size + x0:k * size + x1] for k in range(3)], axis=1))
        rows.append(row)
        print('  %-12s IoU %.3f' % (n, iou))
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows)
    sheet = Image.new('RGB', (W, H), (128, 128, 136))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(out, quality=88)
    print('sheet', out, sheet.size)


HEAD_VIEWS = [('front', 0, 0, 'haru_face_front'), ('right', -90, 0, 'haru_head_side_right'), ('back', 180, 0, 'haru_head_back'),
              ('top', 0, 90, 'haru_head_top'), ('fr45', -45, 0, 'haru_head_front_right45')]


def render_head(cam, sun, out_dir, out_sheet, size=640, zc=1.37, span=0.50):
    """頭の 5 方向を描いて、頭の拡大の絵と並べる（絵は 40.7 画素/cm、頭頂 146 行 = 155 cm）"""
    import numpy as np
    os.makedirs(out_dir, exist_ok=True)
    tiles_a, tiles_r = [], []
    ppc = 40.7
    for (name, az, el, art) in HEAD_VIEWS:
        if el == 90:
            cam.location = Vector((0, 0.01, 4.0))
            cam.rotation_euler = (0, 0, 0)
            cam.data.ortho_scale = span
            sun.rotation_euler = (math.radians(25), 0, 0)
        else:
            a = math.radians(az)
            c = Vector((0, DEPTH0 * abs(math.sin(a)), zc))
            aim(cam, sun, az, c, span)
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = size
        path = os.path.join(out_dir, 'head_%s.png' % name)
        bpy.context.scene.render.filepath = os.path.abspath(path)
        bpy.ops.render.render(write_still=True)
        tiles_r.append(over(Image.open(path).convert('RGBA')))
        im = Image.open(ART + art + '.png').convert('RGBA')
        if el == 90:
            box = (1024 - span * 50 * ppc, 1024 - span * 50 * ppc, 1024 + span * 50 * ppc, 1024 + span * 50 * ppc)
        else:
            top = 146 + (155 - (zc + span / 2) * 100) * ppc
            box = (1024 - span * 50 * ppc, top, 1024 + span * 50 * ppc, top + span * 100 * ppc)
        box = tuple(int(v) for v in box)
        canvas = Image.new('RGBA', (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
        canvas.paste(im, (-box[0], -box[1]))
        tiles_a.append(over(canvas.resize((size, size), Image.LANCZOS)))
    sheet = Image.new('RGB', (size * len(HEAD_VIEWS), size * 2), (128, 128, 136))
    for i, (ta, tr) in enumerate(zip(tiles_a, tiles_r)):
        sheet.paste(ta, (i * size, 0))
        sheet.paste(tr, (i * size, size))
    sheet.save(out_sheet, quality=88)
    print('head sheet', out_sheet, sheet.size)
