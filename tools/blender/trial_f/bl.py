"""haru_f：geo.Mesh の集まりを Blender の物体（材質・UV・重み・骨）にして、GLB に書き出す。"""
from __future__ import annotations

import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import spec

PAL_NAMES = list(spec.PALETTE.keys())
PAL_COLS = 4
PAL_CELL = 16
# 顔の地図（2×2 の表情）の、肌だけの点（区画の左上の隅。どの区画でも肌の色）
SKIN_UV = (0.012, 0.988)


def pal_uv(name):
    i = PAL_NAMES.index(name)
    cx, cy = i % PAL_COLS, i // PAL_COLS
    rows = math.ceil(len(PAL_NAMES) / PAL_COLS)
    return ((cx + 0.5) / PAL_COLS, 1.0 - (cy + 0.5) / rows)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    return sc


def image(path, name):
    img = bpy.data.images.load(os.path.abspath(path))
    img.name = name
    img.pack()
    return img


def mat_tex(name, base_img, emit_img=None, emit_strength=1.0, rough=0.85, double=True, base_color=None, emit_color=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.25
    if base_img is not None:
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = base_img
        t.interpolation = 'Closest' if base_img.size[0] <= 128 else 'Linear'
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    elif base_color is not None:
        bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
    if emit_img is not None:
        t2 = nt.nodes.new('ShaderNodeTexImage')
        t2.image = emit_img
        t2.interpolation = 'Closest'
        nt.links.new(t2.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = emit_strength
    elif emit_color is not None:
        bsdf.inputs['Emission Color'].default_value = (*emit_color, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emit_strength
    m.use_backface_culling = not double
    return m


def make_armature(name='HaruRig'):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for (nm, parent, head, tail) in spec.bones():
        b = arm.edit_bones.new(nm)
        b.head = Vector(head)
        b.tail = Vector(tail)
        if parent:
            b.parent = eb[parent]
            b.use_connect = False
        d = (b.tail - b.head).normalized()
        # 骨の Z を正面（-Y）へ。骨が前後を向くときは上へ
        ref = Vector((0, -1, 0)) if abs(d.y) < 0.9 else Vector((0, 0, 1))
        b.align_roll(ref)
        eb[nm] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def make_object(mesh, arm, mats, gun_names=()):
    """geo.Mesh → 物体。mats = {'body':…, 'face':…, 'gun':…}。色の名前 skin/face は顔の材質、gun_names の部品は銃の材質"""
    me = bpy.data.meshes.new(mesh.name)
    verts = [tuple(p) for p in mesh.v]
    me.from_pydata(verts, [], mesh.f)
    me.update()
    ob = bpy.data.objects.new(mesh.name, me)
    bpy.context.scene.collection.objects.link(ob)
    slots = {}
    for key in ('body', 'face', 'gun'):
        used = False
        for i, c in enumerate(mesh.col):
            k = 'face' if c in ('skin', 'face') else ('gun' if mesh.piece[i] in gun_names else 'body')
            if k == key:
                used = True
                break
        if used:
            slots[key] = len(me.materials)
            me.materials.append(mats[key])
    uvl = me.uv_layers.new(name='UVMap')
    for pi, poly in enumerate(me.polygons):
        c = mesh.col[pi]
        key = 'face' if c in ('skin', 'face') else ('gun' if mesh.piece[pi] in gun_names else 'body')
        poly.material_index = slots[key]
        poly.use_smooth = bool(mesh.smooth[pi])
        for ci, li in enumerate(poly.loop_indices):
            vi = me.loops[li].vertex_index
            if key == 'face':
                if c == 'face' and mesh.fuv[pi] is not None:
                    uv = mesh.fuv[pi][ci]
                else:
                    uv = mesh.uv[vi] if (c == 'face' and mesh.uv[vi] is not None) else SKIN_UV
            else:
                uv = pal_uv(c)
            uvl.data[li].uv = uv
    # 重み
    groups = {}
    for vi, w in enumerate(mesh.w):
        tot = sum(w.values())
        items = sorted(w.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(v for _, v in items)
        for b, val in items:
            if val <= 0:
                continue
            if b not in groups:
                groups[b] = ob.vertex_groups.new(name=b)
            groups[b].add([vi], val / tot, 'REPLACE')
    if arm is not None:
        ob.parent = arm
        md = ob.modifiers.new('Armature', 'ARMATURE')
        md.object = arm
    return ob


def bone_child(ob, arm, bone, world):
    """物体を骨の子にして、世界での置き場所を world（4×4）にする"""
    ob.parent = arm
    ob.parent_type = 'BONE'
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = Matrix(world)
    bpy.context.view_layer.update()


def export_glb(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.abspath(path), export_format='GLB', use_selection=False,
        export_animations=False, export_skins=True, export_yup=True, export_apply=False,
        export_normals=True, export_tangents=False, export_materials='EXPORT', export_image_format='AUTO',
        export_cameras=False, export_lights=False, export_extras=False, export_def_bones=False,
        export_all_influences=False)
