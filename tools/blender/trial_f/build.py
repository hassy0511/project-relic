"""haru_f を作る：形 → Blender の物体 → GLB（動作は anim_bake.py で差し込む）。

  .venv-blender/bin/python -m tools.blender.trial_f.build [--render front,right_noarms,…] [--out build/f/haru_f_mesh.glb]
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='build/f/haru_f_mesh.glb')
    ap.add_argument('--render', default='')
    ap.add_argument('--size', type=int, default=1024)
    ap.add_argument('--sheet', default='build/f/compare.jpg')
    ap.add_argument('--crop', default='')
    ap.add_argument('--hide', default='')
    ap.add_argument('--head', action='store_true')
    ap.add_argument('--pose', default='')
    args = ap.parse_args()
    t0 = time.time()
    from . import bl, geo, spec, textures, parts_body
    import bpy
    groups = {k: geo.Mesh(k) for k in ('Haru', 'Frame_core', 'Frame_arm', 'Frame_legs')}
    parts_body.build_body(groups['Haru'])
    extra = {}
    for modname in ('parts_head', 'parts_gear'):
        try:
            mod = __import__('tools.blender.trial_f.' + modname, fromlist=['build'])
        except ModuleNotFoundError:
            continue
        extra.update(mod.build(groups) or {})
    bl.reset()
    tex = 'build/f/tex'
    pb, pe = textures.make_palette(tex)
    face_path = os.path.join(tex, 'haru_f_face.png')
    if not os.path.exists(face_path):
        textures.make_face_placeholder(tex)
    ip, ie, iface = bl.image(pb, 'haru_f_palette'), bl.image(pe, 'haru_f_emit'), bl.image(face_path, 'haru_f_face')
    mats = {'body': bl.mat_tex('haru_f_body', ip, ie, 1.0),
            'face': bl.mat_tex('haru_f_face', iface, None, rough=1.0),
            'gun': bl.mat_tex('spark_gun_f', ip, ie, 1.0)}
    arm = bl.make_armature('HaruRig')
    gun_names = extra.get('gun_pieces', ())
    hide = set(args.hide.split(',')) if args.hide else set()
    for k, g in groups.items():
        if not g.f:
            continue
        ob = bl.make_object(g, arm, mats, gun_names)
        if k in hide:
            ob.hide_render = True
        print('%-11s tris %6d  verts %6d' % (k, g.tri_count(), len(g.v)))
    if 'blade' in extra:
        b = extra['blade']
        bm = geo.Mesh('LightBlade')
        bm.add(b['verts'], b['faces'], 'amber', {}, smooth=False)
        mats_b = {'body': bl.mat_tex('haru_f_blade', None, None, emit_strength=1.6, base_color=(1.0, 0.50, 0.08), emit_color=(1.0, 0.50, 0.08)),
                  'face': mats['face'], 'gun': mats['gun']}
        ob = bl.make_object(bm, None, mats_b)
        bl.bone_child(ob, arm, 'forearm.L', b['world'])
        if 'blade' in hide or True:
            ob.hide_render = 'blade' not in (args.hide and [] or [])
    if 'muzzle' in extra:
        e = bpy.data.objects.new('muzzle', None)
        bpy.context.scene.collection.objects.link(e)
        bl.bone_child(e, arm, 'hand.R', extra['muzzle'])
    print('total tris', sum(g.tri_count() for g in groups.values()))
    bl.export_glb(args.out)
    print('exported', args.out, os.path.getsize(args.out), 'bytes  %.1fs' % (time.time() - t0))
    # 絵との比べでは発光を切る（絵は発光なし）
    for mt in bpy.data.materials:
        if mt.use_nodes and 'Principled BSDF' in mt.node_tree.nodes:
            mt.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.0
    if args.head:
        from . import render
        cam, sun = render.setup(640)
        render.render_head(cam, sun, 'build/f/render', 'build/f/head.jpg')
    if args.pose:
        from . import render, posetest
        from PIL import Image
        if 'Cam' not in bpy.data.objects:
            render.setup(600)
        cam, sun = bpy.data.objects['Cam'], bpy.data.objects['Sun']
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 600
        tiles = []
        for pn in args.pose.split(','):
            posetest.apply(arm, pn)
            row = []
            for az in (-35, 90, 180, -120):
                render.aim(cam, sun, az, (0, 0, 0.82), 1.9)
                fp = os.path.abspath('build/f/render/pose_%s_%d.png' % (pn, az))
                bpy.context.scene.render.filepath = fp
                bpy.ops.render.render(write_still=True)
                row.append(render.over(Image.open(fp).convert('RGBA')))
            tiles.append(row)
            posetest.clear(arm)
        sheet = Image.new('RGB', (600 * 4, 600 * len(tiles)), (128, 128, 136))
        for i, row in enumerate(tiles):
            for j, t in enumerate(row):
                sheet.paste(t, (j * 600, i * 600))
        sheet.save('build/f/poses.jpg', quality=86)
        print('pose sheet build/f/poses.jpg', sheet.size)
    if args.render:
        from . import render
        names = args.render.split(',')
        cam, sun = (bpy.data.objects['Cam'], bpy.data.objects['Sun']) if args.head else render.setup(args.size)
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = args.size
        os.makedirs('build/f/render', exist_ok=True)
        for n in names:
            render.render_view(cam, sun, n, 'build/f/render/%s.png' % n, args.size)
        crop = [float(v) for v in args.crop.split(',')] if args.crop else None
        render.compare_sheet(names, 'build/f/render', args.sheet, args.size, crop)
        print('rendered %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
