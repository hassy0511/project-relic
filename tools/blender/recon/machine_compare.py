"""機械（番機 5 種・閂）の「絵 | 前 | 後」を 4 方向で並べた比較の画像を作る（W2_番機3D化の結果.md の 3e）。

  .venv-blender/bin/python tools/blender/recon/machine_compare.py --type shield \
      --before build/before/banki_shield.glb --out docs/art_orders/banki_trial/r3_shield.jpg
  --type kannuki で閂（絵は origin/art/w2-kannuki）。--after を省くと godot/assets/models/ の今の GLB。

GLB を Blender に読み込み、絵と同じ正投影（banki.py の render_review・kannuki.py の render_review と同じカメラ）で Cycles で描く。
各方向で 3 枚（絵・前・後）の外形の和の箱で同じように切り抜くので、3 枚の大きさはそのまま比べられる。
"""
from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import banki as B   # noqa: E402

FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
RES = 640
VIEW_JA = {'front': '正面', 'back': '背面', 'top': '真上', 'front_right45': '斜め 45°', 'side': '真横', 'bottom': '真下'}


def banki_views(t, pick=('front', 'side', 'back', 'front_right45')):
    """(名前, 絵のファイル, カメラの向き, 上, 左右反転, 中心の高さ m)。番機は絵の中央の画素に写る点が中心"""
    cfg = B.TYPES[t]
    s = B.scale_of(cfg)
    zc = (cfg['rows'][1] - B.IMG / 2) / s / 100.0
    out = []
    for name, art, d, up, flip in B.review_views(t):
        nm = name if name != cfg['side'][0] else 'side'
        if nm in pick:
            out.append((nm, os.path.join(B.SRC, f'{t}_3d_{art}_r2.png'), d, up, flip, zc))
    return sorted(out, key=lambda v: list(pick).index(v[0])), B.IMG / s / 100.0


def kannuki_views():
    import kannuki as K
    src = K.SRC
    v = [('front', 'kannuki_3d_front_r2.png', (0, -1, 0), (0, 0, 1)), ('side', 'kannuki_3d_side_right_r2.png', (1, 0, 0), (0, 0, 1)),
         ('top', 'kannuki_3d_top_r2.png', (0, 0, 1), (-1, 0, 0)), ('front_right45', 'kannuki_3d_front_right45_r2.png', (0.7071, -0.7071, 0), (0, 0, 1))]
    return [(n, os.path.join(src, a), d, up, False, None) for n, a, d, up in v], 2048 / K.PX_PER_M


def setup_scene():
    import bpy
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = int(os.environ.get('CMP_SAMPLES', 24))
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.82, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    sc.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 2.0
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.type = 'ORTHO'
    cam.data.clip_end = 80
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam, sun


def render_glb(glb, views, ortho, out_prefix, kannuki=False):
    import bpy
    from mathutils import Matrix, Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    sc, cam, sun = setup_scene()
    cam.data.ortho_scale = ortho
    pts = np.array([ob.matrix_world @ v.co for ob in bpy.data.objects if ob.type == 'MESH' for v in ob.data.vertices])
    paths = []
    for name, art, d, up, flip, zc in views:
        d = Vector(d).normalized()
        z = d
        x = Vector(up).cross(z).normalized()
        y = z.cross(x)
        rot = Matrix((x, y, z)).transposed()
        if kannuki:
            # 閂の絵は外形の箱の中央に描かれている（kannuki.render_review と同じ）
            rr = np.array(rot)
            ctr = (pts.max(0) + pts.min(0)) / 2
            pr = (pts - ctr) @ rr[:, :2]
            cx, cy = (pr.max(0) + pr.min(0)) / 2
            center = Vector(ctr) + x * cx + y * cy
        else:
            center = Vector((0, 0, 0)) if name == 'top' else Vector((0, 0, zc))
        cam.matrix_world = Matrix.Translation(center + d * 30.0) @ rot.to_4x4()
        sun.matrix_world = (rot @ Matrix.Rotation(math.radians(-25), 3, 'X') @ Matrix.Rotation(math.radians(-20), 3, 'Y')).to_4x4()
        p = f'{out_prefix}_{name}.png'
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    return paths


def compose(rows, out, title, tile=360, top_flip=False):
    """rows = [(方向, 絵, 前, 後, 反転)]。各方向で 3 枚の外形の和の箱で切り抜き、2 方向ずつ横に並べる"""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(FONT, 20)
    small = ImageFont.truetype(FONT, 16)
    bg = (150, 150, 155)
    groups = []
    for name, art, before, after, flip in rows:
        ims = []
        for k, p in enumerate((art, before, after)):
            im = Image.open(p).convert('RGBA').resize((RES, RES), Image.LANCZOS)
            if flip and k > 0:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            if name == 'top' and k == 0 and top_flip:
                im = im.transpose(Image.FLIP_TOP_BOTTOM)
            ims.append(im)
        if name == 'top':
            # 真上の絵は縮尺が違うので、絵の外形の箱を「後」の外形の箱に合わせる（banki.py の _fit_bbox と同じ）
            ims[0] = _fit(ims[0], ims[2])
        a = np.zeros((RES, RES), bool)
        for im in ims:
            a |= np.asarray(im)[..., 3] > 40
        r, c = np.nonzero(a.any(1))[0], np.nonzero(a.any(0))[0]
        if len(r) == 0:
            r, c = np.array([0, RES - 1]), np.array([0, RES - 1])
        cy, cx = (r[0] + r[-1]) / 2, (c[0] + c[-1]) / 2
        half = max(r[-1] - r[0], c[-1] - c[0]) / 2 * 1.06 + 4
        box = (int(cx - half), int(cy - half), int(cx + half), int(cy + half))
        tiles = []
        for im in ims:
            t = Image.new('RGBA', (box[2] - box[0], box[3] - box[1]), bg + (255,))
            t.alpha_composite(im.crop(box) if box[0] >= 0 and box[1] >= 0 and box[2] <= RES and box[3] <= RES else
                              _pad_crop(im, box))
            tiles.append(t.convert('RGB').resize((tile, tile), Image.LANCZOS))
        groups.append((name, tiles))
    cols = 2
    head = 34
    lab = 24
    W = Image.new('RGB', (cols * 3 * tile + (cols - 1) * 8, head + ((len(groups) + 1) // 2) * (tile + lab)), (36, 36, 40))
    d = ImageDraw.Draw(W)
    d.text((8, 6), title, font=font, fill=(240, 236, 220))
    for k, (name, tiles) in enumerate(groups):
        x0 = (k % cols) * (3 * tile + 8)
        y0 = head + (k // cols) * (tile + lab)
        for j, (t, cap) in enumerate(zip(tiles, ('絵（r2）', '前', '後'))):
            W.paste(t, (x0 + j * tile, y0 + lab))
            d.text((x0 + j * tile + 6, y0 + 3), f'{VIEW_JA.get(name, name)}：{cap}', font=small, fill=(230, 230, 230))
    W.save(out, quality=84, optimize=True)
    return W.size


def _fit(art, ren):
    from PIL import Image
    a = np.asarray(art)[..., 3] > 64
    b = np.asarray(ren)[..., 3] > 64
    if not a.any() or not b.any():
        return art
    ra, ca = np.nonzero(a.any(1))[0], np.nonzero(a.any(0))[0]
    rb, cb = np.nonzero(b.any(1))[0], np.nonzero(b.any(0))[0]
    crop = art.crop((ca[0], ra[0], ca[-1] + 1, ra[-1] + 1)).resize((cb[-1] + 1 - cb[0], rb[-1] + 1 - rb[0]), Image.LANCZOS)
    out = Image.new('RGBA', art.size, (0, 0, 0, 0))
    out.paste(crop, (cb[0], rb[0]))
    return out


def _pad_crop(im, box):
    from PIL import Image
    out = Image.new('RGBA', (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    out.paste(im, (-box[0], -box[1]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--type', required=True)
    ap.add_argument('--before', required=True)
    ap.add_argument('--after')
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='')
    ap.add_argument('--views', default='front,side,back,front_right45', help='番機の方向（front・side・back・top・front_right45）')
    args = ap.parse_args()
    t = args.type
    kann = t == 'kannuki'
    if kann:
        import kannuki as K
        K.fetch_art()
        views, ortho = kannuki_views()
        after = args.after or os.path.join(B.MODELS, 'kannuki.glb')
    else:
        B.fetch_art()
        views, ortho = banki_views(t, tuple(args.views.split(',')))
        after = args.after or os.path.join(B.MODELS, f'banki_{t}.glb')
    work = os.path.join(B.REPO, 'build', 'compare', t)
    os.makedirs(work, exist_ok=True)
    pb = render_glb(args.before, views, ortho, os.path.join(work, 'before'), kann)
    pa = render_glb(after, views, ortho, os.path.join(work, 'after'), kann)
    rows = [(v[0], v[1], b, a, v[4]) for v, b, a in zip(views, pb, pa)]
    size = compose(rows, args.out, args.title or f'{t}：絵 | 前 | 後', top_flip=(not kann) and bool(B.TYPES[t].get('top_flip')))
    print(f'[compare] {args.out} {size} {os.path.getsize(args.out) // 1024} KB', flush=True)


if __name__ == '__main__':
    main()
