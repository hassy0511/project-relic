"""町の部品の確認の画像：部品を 1 つずつ斜め上から Cycles で描き、名前を付けて並べる（build/kit_town/review.jpg）。

絵の town_kit_buildings.png / town_props.png と同じ向き（左前の斜め上から）で見比べられるようにする。
"""
from __future__ import annotations

import math
import os

import numpy as np

TILE = 300


def render(cat: dict, names: list[str], work: str) -> str:
    import bpy
    from mathutils import Matrix, Vector
    from PIL import Image, ImageDraw

    import town_geo as geo
    os.makedirs(os.path.join(work, 'tiles'), exist_ok=True)
    tiles = []
    for n in names:
        part = cat[n]()
        part.name = n
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        ob = geo.to_object(part)
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 12
        sc.cycles.use_denoising = False
        sc.render.resolution_x = sc.render.resolution_y = TILE
        sc.render.film_transparent = False
        sc.view_settings.view_transform = 'Standard'
        if sc.world is None:
            sc.world = bpy.data.worlds.new('w')
        sc.world.use_nodes = True
        sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.42, 0.42, 0.44, 1)
        sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
        sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
        sc.collection.objects.link(sun)
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
        cam.data.type = 'ORTHO'
        sc.collection.objects.link(cam)
        sc.camera = cam
        lo, hi = part.bounds()
        # ゲーム座標 → Blender（x, -z, y）
        blo = Vector((lo[0], -hi[2], lo[1]))
        bhi = Vector((hi[0], -lo[2], hi[1]))
        ctr = (blo + bhi) / 2
        ext = (bhi - blo).length
        cam.data.ortho_scale = ext * 1.05
        d = Vector((-0.55, -1.0, 0.62)).normalized()        # 左前の斜め上（絵の向き）
        z = d
        x = Vector((0, 0, 1)).cross(z).normalized()
        y = z.cross(x)
        cam.matrix_world = Matrix.Translation(ctr + d * (ext * 3)) @ Matrix((x, y, z)).transposed().to_4x4()
        cam.data.clip_end = ext * 10
        p = os.path.join(work, 'tiles', f'{n}.png')
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        im = Image.open(p).convert('RGB')
        dr = ImageDraw.Draw(im)
        dr.text((6, 4), f'{n}  {part.tris()} tri', fill=(255, 255, 160))
        tiles.append(im)
    cols = 6
    rows = (len(tiles) + cols - 1) // cols
    W = Image.new('RGB', (cols * TILE, rows * TILE), (30, 30, 30))
    for k, im in enumerate(tiles):
        W.paste(im, ((k % cols) * TILE, (k // cols) * TILE))
    out = os.path.join(work, 'review.jpg')
    W.save(out, quality=85)
    print('[town] 確認の画像', out)
    return out
