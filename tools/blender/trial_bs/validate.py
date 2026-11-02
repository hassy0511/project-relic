"""validation-checklist（スキル集の references/validation-checklist.md）の数で確かめられる項目を数える。

  .venv-blender/bin/python tools/blender/trial_bs/validate.py

MCP の get_scene_info・査察のスクリプトの代わり。build/trial_bs/haru_bs.blend を開いて、
大きさ・原点・向き・三角形の数・n 角形・開いた辺・ばらばらの点・UV の範囲・材質・名前を出す。
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'build', 'trial_bs')

import bpy
import bmesh
from mathutils import Vector

CONTRACT = {'Frame_core', 'Frame_arm', 'Frame_legs', 'LightBlade', 'muzzle'}


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'haru_bs.blend'))
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    tris = 0
    rows = []
    bad_names = []
    for ob in bpy.data.objects:
        if ob.type == 'EMPTY':
            if ob.name not in CONTRACT and not ob.name.startswith(('CAM_', 'LGT_')):
                bad_names.append(ob.name)
            continue
        if ob.type != 'MESH':
            continue
        if not ob.name.startswith('SM_') and ob.name not in CONTRACT:
            bad_names.append(ob.name)
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.transform(ob.matrix_world)
        for v in bm.verts:
            lo = Vector((min(lo[i], v.co[i]) for i in range(3)))
            hi = Vector((max(hi[i], v.co[i]) for i in range(3)))
        t = sum(len(f.verts) - 2 for f in bm.faces)
        tris += t
        ngon = sum(1 for f in bm.faces if len(f.verts) > 4)
        quads = sum(1 for f in bm.faces if len(f.verts) == 4)
        nonman = sum(1 for e in bm.edges if not e.is_manifold)
        loose = sum(1 for v in bm.verts if not v.link_edges)
        uvl = bm.loops.layers.uv.active
        uv_out = 0
        if uvl:
            for f in bm.faces:
                for l in f.loops:
                    u, v = l[uvl].uv
                    if u < -1e-4 or u > 1.0001 or v < -1e-4 or v > 1.0001:
                        uv_out += 1
        rows.append((ob.name, t, quads, len(bm.faces), ngon, nonman, loose, uv_out, ob.data.materials[0].name if ob.data.materials else '-',
                     tuple(round(x, 3) for x in ob.matrix_world.to_scale())))
        bm.free()
        ev.to_mesh_clear()
    print(f'BOUNDS min {tuple(round(x, 3) for x in lo)} max {tuple(round(x, 3) for x in hi)} height {hi.z - lo.z:.3f}')
    print(f'TRIS {tris}')
    print('| 物体 | 三角形 | 四角/面 | n 角形 | 開いた辺 | ばらばらの点 | UV の外 | 材質 | 拡大 |')
    print('|---|---|---|---|---|---|---|---|---|')
    for r in sorted(rows, key=lambda r: -r[1]):
        print(f'| {r[0]} | {r[1]} | {r[2]}/{r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} |')
    mats = sorted({m.name for m in bpy.data.materials if m.users and not m.name.startswith('TOON_')})
    print('MATERIALS', len(mats), mats)
    print('IMAGES', [(i.name, i.size[0], i.size[1]) for i in bpy.data.images if i.size[0]])
    print('NAMES not following SM_/contract:', bad_names)
    print('COLLECTIONS', [c.name for c in bpy.data.collections])


if __name__ == '__main__':
    main()
