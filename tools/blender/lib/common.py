"""Blender スクリプト共通の道具。

座標の約束：Blender は Z が上。キャラクターの正面は Blender の -Y 方向
（glTF に書き出すと +Z 方向になり、ゲームの yaw=0 の向きと一致する）。
"""
from __future__ import annotations

import math
import os
from typing import Iterable

import bpy
import mathutils

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.frame_start = 1


def material(name: str, color: tuple[float, float, float], emission: float = 0.0, roughness: float = 0.7,
             metallic: float = 0.0) -> bpy.types.Material:
    """単色の材質。emission > 0 で発光（遺物の光など）"""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if emission > 0:
        bsdf.inputs['Emission Color'].default_value = (*color, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emission
    return mat


def hex_color(h: str) -> tuple[float, float, float]:
    """#rrggbb（sRGB）を Blender の線形色に変換する"""
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)  # type: ignore


def box(name: str, center: Iterable[float], size: Iterable[float], mat: bpy.types.Material | None = None,
        rot_z: float = 0.0, bevel: float = 0.0) -> bpy.types.Object:
    """中心と大きさ（全幅）で箱を作る"""
    sx, sy, sz = size
    bpy.ops.mesh.primitive_cube_add(size=1, location=tuple(center))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    obj.rotation_euler = (0, 0, rot_z)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel > 0:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if mat:
        obj.data.materials.append(mat)
    return obj


def cylinder(name: str, center: Iterable[float], radius: float, depth: float, mat: bpy.types.Material | None = None,
             axis: str = 'Z', vertices: int = 10) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=tuple(center))
    obj = bpy.context.active_object
    obj.name = name
    if axis == 'X':
        obj.rotation_euler = (0, math.pi / 2, 0)
    elif axis == 'Y':
        obj.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if mat:
        obj.data.materials.append(mat)
    return obj


def sphere(name: str, center: Iterable[float], radius: float, mat: bpy.types.Material | None = None,
           segments: int = 10, scale: Iterable[float] = (1, 1, 1)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(4, segments // 2), radius=radius,
                                         location=tuple(center))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = tuple(scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    return obj


def empty(name: str, location: Iterable[float], yaw_deg: float = 0.0) -> bpy.types.Object:
    """ゲームの目印。yaw_deg はゲームの向き（0 で +Z＝Blender の -Y）"""
    obj = bpy.data.objects.new(name, None)
    obj.location = tuple(location)
    obj.rotation_euler = (0, 0, math.radians(yaw_deg))
    bpy.context.scene.collection.objects.link(obj)
    return obj


def join(objs: list[bpy.types.Object], name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name
    return obj


def export_glb(path: str, animations: bool = True) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kwargs = dict(
        filepath=path,
        export_format='GLB',
        export_apply=True,
        export_animations=animations,
        export_yup=True,
        export_extras=True,
    )
    if animations:
        kwargs['export_animation_mode'] = 'ACTIONS'
        kwargs['export_force_sampling'] = True
    bpy.ops.export_scene.gltf(**kwargs)


def render_views(path_prefix: str, target: tuple[float, float, float], height: float,
                 views: dict[str, float] | None = None, size: int = 512) -> list[str]:
    """確認用の画像を Cycles で描く。views は {名前: カメラの方位角（度）}。正投影"""
    views = views or {'front': 0, 'side': 90, 'back': 180, 'three_quarter': 35}
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.cycles.device = 'CPU'
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.film_transparent = False
    world = bpy.data.worlds.new('preview_world') if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0

    cam_data = bpy.data.cameras.new('preview_cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = height * 1.25
    cam = bpy.data.objects.new('preview_cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new('preview_sun', 'SUN')
    sun_data.energy = 3.0
    sun = bpy.data.objects.new('preview_sun', sun_data)
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    scene.collection.objects.link(sun)

    out = []
    tx, ty, tz = target
    for name, az in views.items():
        a = math.radians(az)
        # 正面（az=0）は -Y 側から見る
        cam.location = (tx + math.sin(a) * 10, ty - math.cos(a) * 10, tz)
        direction = mathutils.Vector((tx, ty, tz)) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = f'{path_prefix}_{name}.png'
        bpy.ops.render.render(write_still=True)
        out.append(scene.render.filepath)
    bpy.data.objects.remove(cam)
    bpy.data.objects.remove(sun)
    return out
