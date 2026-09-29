"""Original, deterministic W2-03 boss art, rendered with Blender 4.5.

Run: blender -b --factory-startup --python generate_kannuki.py
All final PNGs and the editable .blend remain in this directory. Temporary
panel renders are created outside the repository and removed on completion.
"""

import json
import math
import os
import tempfile
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector


OUT = Path(__file__).resolve().parent
PALETTE = {
    "ivory": "F3E9D2", "ivory_dim": "DDD1B8", "brass": "A98749",
    "brass_light": "C7AB70", "graphite": "444641", "black": "282D2D",
    "amber": "FFBC52", "alert": "E26A4A", "dull": "777C78",
    "redcloth": "B75B43", "brown": "594333", "skin": "E7B58D",
    "gray": "E6E6E6", "paper": "E6E6E6", "ink": "343A39",
    "arena_floor": "5B5B52", "arena_wall": "777363",
}
MATS = {}
IMAGE_BOUNDS = {}


def lin(hexcode):
    vals = [int(hexcode[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + .055) / 1.055) ** 2.4 for v in vals)


def mat(key, emission=False):
    cache_key = (key, emission)
    if cache_key in MATS:
        return MATS[cache_key]
    m = bpy.data.materials.new(key + ("_em" if emission else ""))
    m.diffuse_color = (*lin(PALETTE[key]), 1)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if emission:
        node = nt.nodes.new("ShaderNodeEmission")
        node.inputs["Color"].default_value = (*lin(PALETTE[key]), 1)
        node.inputs["Strength"].default_value = 1
        nt.links.new(node.outputs[0], out.inputs["Surface"])
    else:
        node = nt.nodes.new("ShaderNodeBsdfPrincipled")
        node.inputs["Base Color"].default_value = (*lin(PALETTE[key]), 1)
        node.inputs["Metallic"].default_value = .16 if key in {"brass", "brass_light"} else .02
        node.inputs["Roughness"].default_value = .82
        nt.links.new(node.outputs[0], out.inputs["Surface"])
    MATS[cache_key] = m
    return m


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def finish_mesh(obj, name, material, group="misc", bevel=0):
    obj.name = name
    obj["part_group"] = group
    obj.data.materials.append(mat(material))
    if bevel:
        bevel_mod = obj.modifiers.new("broad_chamfer", "BEVEL")
        bevel_mod.width = bevel
        bevel_mod.segments = 1
        bevel_mod.affect = "EDGES"
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=bevel_mod.name)
    for face in obj.data.polygons:
        face.use_smooth = False
    return obj


def box(name, loc, dims, material, group="misc", bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish_mesh(obj, name, material, group, bevel)


def cyl(name, loc, radius, depth, material, axis=(0, 0, 1), group="misc", verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return finish_mesh(obj, name, material, group)


def cone(name, loc, r1, r2, depth, material, axis=(0, 0, 1), group="misc", verts=10):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc)
    obj = bpy.context.object
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    return finish_mesh(obj, name, material, group)


def line3(name, a, b, radius=.018, material="brass"):
    a, b = Vector(a), Vector(b)
    delta = b - a
    return cyl(name, (a+b)*.5, radius, delta.length, material, axis=delta,
               group="construction", verts=8)


def move_objects(objects, delta):
    delta = Vector(delta)
    for obj in objects:
        obj.location += delta


def rotate_objects(objects, pivot, axis, angle):
    pivot = Vector(pivot)
    rot = Matrix.Rotation(angle, 4, axis)
    for obj in objects:
        obj.location = pivot + rot @ (obj.location-pivot)
        q = rot.to_quaternion()
        if obj.rotation_mode == "QUATERNION":
            obj.rotation_quaternion = q @ obj.rotation_quaternion
        else:
            obj.rotation_euler = (q @ obj.rotation_euler.to_quaternion()).to_euler()


def arm(side=1, high=1, standalone=False, overheat=False):
    """Four-meter rigid cartridge, anchored at its body-side pivot."""
    before = set(bpy.context.scene.objects)
    pivot = Vector((0, 0, 0) if standalone else (side*1.68, 1.6, high*.78))
    s = 1 if standalone else side
    hot = "alert" if overheat else "brass"
    x = pivot.x + s*.58
    z = pivot.z
    cyl("arm_yaw_bearing", (pivot.x, pivot.y, z-.11), .43, .20,
        "graphite", axis=(0, 0, 1), group="joint", verts=12)
    cyl("arm_hinge_disc", (pivot.x+s*.13, pivot.y, z), .39, .32,
        "graphite", axis=(1, 0, 0), group="joint", verts=12)
    cyl("arm_hinge_pin", (pivot.x+s*.35, pivot.y, z), .18, .11,
        hot, axis=(1, 0, 0), group="joint", verts=12)
    box("arm_bridge", (pivot.x+s*.37, pivot.y-.21, z), (.78, .50, .36),
        "graphite", group="joint", bevel=.045)
    box("arm_inner_slide", (x, pivot.y-1.20, z), (.43, 2.15, .45),
        "black", group="arm", bevel=.05)
    box("arm_armor_rail", (x+s*.12, pivot.y-1.08, z+.27), (.32, 1.94, .13),
        "ivory", group="arm", bevel=.035)
    for offset in (.22, 1.67):
        box("arm_brass_collar", (x, pivot.y-offset, z), (.53, .14, .57),
            hot, group="arm", bevel=.035)
    box("arm_drill_sleeve", (x, pivot.y-2.38, z), (.58, 1.08, .60),
        "ivory_dim", group="arm", bevel=.075)
    cyl("arm_drill_hub", (x, pivot.y-2.94, z), .34, .22,
        "graphite", axis=(0, 1, 0), group="arm", verts=12)
    # The drill is a five-face stepped pick, never a tentacle or claw.
    drill_depths = (.26, .24, .24, .22)
    for i, (r0, r1, depth) in enumerate(((.36, .28, .26), (.29, .18, .24),
                                          (.20, .08, .24), (.10, .0, .22))):
        y = pivot.y - 3.04 - sum(drill_depths[:i]) - depth*.5
        cone("arm_drill_tooth", (x, y, z), r1, r0, depth,
             "graphite" if i % 2 else hot, axis=(0, 1, 0), group="arm", verts=8)
    return [o for o in bpy.context.scene.objects if o not in before], pivot


def boss(state="rest"):
    """Long axis Y, front -Y, upper back core +Z/+Y."""
    start = set(bpy.context.scene.objects)
    overheat = state == "phase3"
    core_open = state in {"open", "stun", "thrust_recover", "phase3_open"}
    released = state in {"phase2", "slam_wind", "slam", "slam_recover"}
    hot = "alert" if overheat or state in {"windup", "thrust", "sweep_wind", "sweep"} else "amber"
    cyl("ten_metre_inner_bolt", (0, 0, 0), 1.54, 10.0, "graphite",
        axis=(0, 1, 0), group="body", verts=18)
    for name, yy, depth in (("forward_shell", -4.18, 1.55),
                            ("mid_shell", 0, 6.66), ("aft_shell", 4.19, 1.55)):
        cyl(name, (0, yy, 0), 1.75, depth, "ivory",
            axis=(0, 1, 0), group="shell", verts=18)
    for yy in (-3.36, 0, 3.36):
        cyl("transverse_binding", (0, yy, 0), 1.81, .22,
            "brass" if yy else "graphite", axis=(0, 1, 0), group="binding", verts=18)
    for xx in (-1.06, 1.06):
        box("longitudinal_seam", (xx, 0, 1.40), (.13, 6.45, .15),
            "graphite", group="shell_trim", bevel=.025)
    for yy in (-2.05, .08, 2.05):
        box("shell_gap", (0, yy, 1.76), (1.22, .11, .065),
            "alert" if overheat else "graphite", group="shell_trim", bevel=.015)
    # Front reads as a door bolt's square latch inside a circle, not an eye.
    cyl("front_socket", (0, -5.03, 0), 1.35, .12, "black",
        axis=(0, 1, 0), group="front", verts=18)
    box("front_latch_block", (0, -5.15, 0), (1.90, .22, .72),
        "brass", group="front", bevel=.08)
    box("sensor_recess", (0, -5.28, .07), (1.48, .04, .16),
        "black", group="front", bevel=.025)
    box("horizontal_sensor", (0, -5.31, .07), (1.18, .025, .075),
        hot, group="front", bevel=.012)
    for xx in (-.91, .91):
        box("front_lock_stop", (xx, -5.33, 0), (.16, .14, 1.07),
            "graphite", group="front", bevel=.02)
    cyl("aft_end", (0, 5.02, 0), 1.30, .12, "black",
        axis=(0, 1, 0), group="aft", verts=18)
    box("aft_square_latch", (0, 5.14, 0), (1.64, .22, .66),
        "brass", group="aft", bevel=.06)
    # Dorsal/rear keyhole-like lock core. The back cover is two solid lids.
    box("core_brass_frame", (0, 2.12, 1.785), (1.88, 2.36, .21),
        "brass", group="core", bevel=.13)
    box("core_black_well", (0, 2.12, 1.92), (1.52, 1.94, .075),
        "black", group="core", bevel=.085)
    box("core_latch_bar", (0, 1.82, 1.974), (.97, .22, .07),
        "amber", group="core", bevel=.03)
    box("core_key_stem", (0, 2.28, 1.974), (.19, .88, .07),
        "amber", group="core", bevel=.03)
    for side in (-1, 1):
        x = side*(1.04 if core_open else .42)
        lid = box("left_core_lid" if side < 0 else "right_core_lid",
                  (x, 2.12, 2.08), (.82, 2.13, .23),
                  "ivory", group="lid", bevel=.11)
        if core_open:
            lid.rotation_euler[1] = side*.24
        box("lid_back_hinge", (side*.94, 2.12, 1.90), (.15, 2.05, .20),
            "graphite", group="joint", bevel=.025)
    # Perimeter rail carriage: two dark U shoes and eight brass rollers.
    if not released:
        for yy in (-3.15, 3.15):
            box("rail_carriage_neck", (0, yy, -1.92), (.92, .86, .70),
                "graphite", group="rail", bevel=.075)
            box("rail_crossbar", (0, yy, -2.31), (2.14, 1.14, .22),
                "brass", group="rail", bevel=.045)
            for xx in (-.88, .88):
                box("rail_guide_shoe", (xx, yy, -2.53), (.29, 1.14, .42),
                    "black", group="rail", bevel=.055)
                for dy in (-.36, .36):
                    cyl("rail_roller", (xx, yy+dy, -2.38), .16, .33,
                        "brass_light", axis=(1, 0, 0), group="rail", verts=10)
    elif state != "slam":
        for yy in (-3.15, 3.15):
            box("retracted_rail_mount", (0, yy, -1.76), (1.35, .74, .38),
                "graphite", group="rail", bevel=.06)
    arms = []
    for side in (-1, 1):
        for high in (-1, 1):
            if state == "broken" and side == 1 and high == 1:
                p = (side*1.68, 1.6, high*.78)
                cyl("broken_hinge", (p[0]+side*.1, p[1], p[2]), .42, .38,
                    "graphite", axis=(1, 0, 0), group="broken", verts=10)
                box("fractured_stump", (p[0]+side*.45, p[1]-.23, p[2]),
                    (.55, .53, .48), "dull", group="broken", bevel=.08)
                continue
            objs, pivot = arm(side, high, overheat=overheat)
            if state in {"sweep_wind", "sweep", "sweep_recover", "phase2"}:
                amount = {"sweep_wind": .30, "sweep": .78,
                          "sweep_recover": .20, "phase2": .25}[state]
                rotate_objects(objs, pivot, "Z", side*amount)
            if state in {"slam_wind", "slam", "slam_recover"}:
                rotate_objects(objs, pivot, "Z", side*.25)
            if state in {"stun", "thrust_recover"}:
                rotate_objects(objs, pivot, "X", high*.12)
            arms += objs
    created = [o for o in bpy.context.scene.objects if o not in start]
    if state == "slam_wind":
        rotate_objects(created, (0, 0, 0), "X", -.18)
        move_objects(created, (0, 0, 1.2))
    elif state == "slam":
        rotate_objects(created, (0, 0, 0), "X", .26)
        move_objects(created, (0, 0, -.65))
    elif state == "slam_recover":
        move_objects(created, (0, 0, -.35))
    elif state == "thrust":
        move_objects(created, (0, -1.3, 0))
    elif state == "windup":
        move_objects(created, (0, .6, 0))
    return created


def camera_at(name, location, target=(0, 0, 0), up=(0, 0, 1), scale=14):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.name = name
    forward = (Vector(target)-cam.location).normalized()
    right = forward.cross(Vector(up)).normalized()
    real_up = right.cross(forward).normalized()
    cam.rotation_euler = Matrix((right, real_up, -forward)).transposed().to_quaternion().to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    bpy.context.scene.camera = cam
    return cam


def setup_render(width, height, transparent=True, mood=False):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.eevee.taa_render_samples = 32 if mood else 24
    sc.eevee.use_shadows = bool(mood)
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.film_transparent = transparent
    sc.render.image_settings.color_depth = "8"
    sc.render.image_settings.compression = 25
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "Medium High Contrast" if mood else "Medium High Contrast"
    sc.view_settings.exposure = -.35 if mood else 0
    sc.view_settings.gamma = 1
    sc.world.color = (.65, .65, .65)
    return sc


def area(name, loc, power, color, size, target=(0, 0, 0)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = power
    obj.data.color = color
    obj.data.shape = "DISK"
    obj.data.size = size
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    area("broad_frontal", (5, -7, 10), 4500, (1, 1, 1), 13)
    area("soft_side", (-8, 3, 6), 2300, (1, 1, 1), 11)
    area("low_fill", (3, 8, -2), 1200, (1, 1, 1), 10)


VIEWS = {
    "front": ((0, -25, 0), (0, 0, 1)),
    "back": ((0, 25, 0), (0, 0, 1)),
    "side_right": ((25, 0, 0), (0, 0, 1)),
    "top": ((0, 0, 25), (0, 1, 0)),
    "bottom": ((0, 0, -25), (0, 1, 0)),
    "front_right45": ((19, -19, 11), (0, 0, 1)),
}


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("RENDER", path.name, path.stat().st_size)


def boss_view(path, view, state="rest", resolution=2048, save_blend=False):
    clear()
    setup_render(resolution, resolution, transparent=True)
    objs = boss(state)
    loc, up = VIEWS[view]
    camera_at("orthographic_"+view, loc, up=up, scale=14)
    studio()
    if save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "kannuki_source.blend"))
    render(path)
    return objs


def arm_view(path, view):
    clear()
    setup_render(2048, 2048, transparent=True)
    arm(standalone=True)
    target = (.33, -2.0, 0)
    if view == "side":
        loc, up = (18, -2, 0), (0, 0, 1)
    elif view == "top":
        loc, up = (0, -2, 18), (0, 1, 0)
    else:
        loc, up = (.33, -20, 0), (0, 0, 1)
    camera_at("arm_"+view, loc, target=target, up=up, scale=5.4)
    studio()
    render(path)


def parts_view(path):
    clear()
    setup_render(2048, 2048, transparent=True)
    objs = boss("rest")
    for obj in objs:
        g = obj.get("part_group", "")
        if g in {"shell", "shell_trim", "binding"}:
            obj.location.z += .65
        elif g == "lid":
            obj.location.z += 1.60
        elif g == "core":
            obj.location.z += 1.02
        elif g == "rail":
            obj.location.z -= .80
        elif g in {"arm", "joint"} and obj.name.startswith("arm_"):
            obj.location.x += 1.25 if obj.location.x > 0 else -1.25
    # Thin physical connection axes, including the four arm pivot directions.
    for side in (-1, 1):
        for high in (-1, 1):
            p = (side*1.68, 1.6, high*.78)
            line3("arm_rotation_axis", p, (p[0]+side*1.55, p[1], p[2]), .012)
    for yy in (-3.15, 3.15):
        line3("rail_attachment_axis", (0, yy, -1.72), (0, yy, -3.15), .012)
    line3("lid_hinge_axis", (-.94, 2.12, 1.9), (-.94, 2.12, 3.3), .012)
    line3("lid_hinge_axis", (.94, 2.12, 1.9), (.94, 2.12, 3.3), .012)
    camera_at("exploded_view", (19, -18, 15), target=(0, 0, .2), scale=17)
    studio()
    render(path)


def emission_image(path, im):
    m = bpy.data.materials.new("sheet_image_"+path.stem)
    m.use_nodes = True
    m.surface_render_method = "DITHERED"
    nt = m.node_tree
    nt.nodes.clear()
    output = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = im
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    glow = nt.nodes.new("ShaderNodeEmission")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], glow.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(glow.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], output.inputs["Surface"])
    return m


def panel_rect(cx, cy, w, h, material="paper", z=0):
    obj = box("sheet_rect", (cx, cy, z), (w, h, .002), material)
    obj.data.materials.clear()
    obj.data.materials.append(mat(material, emission=True))
    return obj


def put_image(path, cx, cy, w, h, z=.08, turn=False):
    im = bpy.data.images.load(str(path), check_existing=True)
    if str(path) not in IMAGE_BOUNDS:
        ww, hh = im.size
        pixels = np.empty(ww*hh*4, dtype=np.float32)
        im.pixels.foreach_get(pixels)
        yy, xx = np.where(pixels[3::4].reshape(hh, ww) > .02)
        pad = 8
        IMAGE_BOUNDS[str(path)] = (
            max(0, int(xx.min())-pad), max(0, int(yy.min())-pad),
            min(ww, int(xx.max())+pad+1), min(hh, int(yy.max())+pad+1))
    x0, y0, x1, y1 = IMAGE_BOUNDS[str(path)]
    iw, ih = im.size
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, z))
    obj = bpy.context.object
    obj.name = "source_render_" + path.stem
    obj.scale = (w*(x1-x0)/iw, h*(y1-y0)/ih, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for uv_data in obj.data.uv_layers.active.data:
        u, v = uv_data.uv
        uv_data.uv = (x0/iw + u*(x1-x0)/iw,
                      y0/ih + v*(y1-y0)/ih)
    if turn:
        obj.rotation_euler[2] = -math.pi/2
    obj.data.materials.append(emission_image(path, im))
    return obj


def font():
    for f in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        if Path(f).exists():
            return bpy.data.fonts.load(f)
    return None


FONT = None


def txt(body, x, y, size=.28, material="ink", align="LEFT", z=.11):
    global FONT
    if FONT is None:
        FONT = font()
    bpy.ops.object.text_add(location=(x, y, z))
    obj = bpy.context.object
    obj.name = "sheet_text"
    obj.data.body = body
    if FONT:
        obj.data.font = FONT
    obj.data.size = size
    obj.data.align_x = align
    obj.data.materials.append(mat(material, emission=True))
    return obj


def board(title, subtitle):
    clear()
    setup_render(4096, 2048, transparent=False)
    bpy.context.scene.view_settings.look = "None"
    # Blender's ortho_scale is the horizontal span for this 2:1 output.
    camera_at("sheet_camera", (0, 0, 22), up=(0, 1, 0), scale=20)
    panel_rect(0, 0, 20, 10, "gray", -.10)
    panel_rect(0, 4.48, 20, 1.04, "graphite", -.04)
    txt(title, -9.6, 4.37, .53, "ivory")
    txt(subtitle, 9.6, 4.45, .24, "brass_light", "RIGHT")


def card(cx, cy, w, h, label, source=None, image_scale=1, turn=False,
         image_dx=0):
    panel_rect(cx, cy, w, h, "paper", -.02)
    panel_rect(cx, cy+h*.5-.04, w, .08, "brass", .02)
    txt(label, cx-w*.5+.20, cy+h*.5-.46, .27)
    if source:
        extent = min(w-.22, h-.60)*image_scale
        put_image(source, cx+image_dx, cy-.23, extent, extent, turn=turn)


def arc2(cx, cy, radius, color="brass", z=.06, steps=96, width=.025):
    for j in range(steps):
        a = 2*math.pi*j/steps
        b = 2*math.pi*(j+1)/steps
        line3("diagram_ring", (cx+radius*math.cos(a), cy+radius*math.sin(a), z),
              (cx+radius*math.cos(b), cy+radius*math.sin(b), z), width, color)


def draw_arena_plan(cx, cy, radius):
    arc2(cx, cy, radius, "graphite", steps=96, width=.035)
    arc2(cx, cy, radius*.88, "brass", steps=96, width=.045)
    arc2(cx, cy, radius*.72, "dull", steps=96, width=.025)
    panel_rect(cx, cy, radius*.45, radius*.38, "graphite", .04)
    panel_rect(cx, cy-.02, radius*.27, radius*.23, "brass", .07)
    for a in (.25*math.pi, .75*math.pi, 1.25*math.pi, 1.75*math.pi):
        xx = cx+radius*.57*math.cos(a)
        yy = cy+radius*.57*math.sin(a)
        panel_rect(xx, yy, radius*.17, radius*.17, "graphite", .06)
    # Resting boss is a long radial-free bar on the rail, at the top.
    panel_rect(cx, cy+radius*.88, radius*.66, radius*.11, "ivory", .08)
    txt("32 m", cx, cy-radius-.43, .28, "ink", "CENTER")


def haru_scale():
    """Original simplified geometric Haru at 1.55 m, only for size comparison."""
    # Body feet at -1.75, exactly 1.55 m to top of hair.
    x, y, z0 = 0, -6.25, -1.75
    box("haru_boot_L", (x-.12, y, z0+.08), (.18, .33, .16), "brown", bevel=.04)
    box("haru_boot_R", (x+.12, y, z0+.08), (.18, .33, .16), "brown", bevel=.04)
    for sx in (-.12, .12):
        box("haru_pant", (x+sx, y, z0+.42), (.17, .24, .55), "redcloth", bevel=.05)
        box("haru_knee", (x+sx, y-.13, z0+.57), (.18, .09, .16), "ivory", bevel=.03)
    box("haru_jacket", (x, y, z0+.92), (.48, .25, .48), "redcloth", bevel=.09)
    box("haru_shirt", (x, y-.14, z0+.98), (.16, .045, .32), "ivory", bevel=.02)
    for sx in (-.32, .32):
        box("haru_arm", (x+sx, y, z0+.93), (.16, .19, .43), "redcloth", bevel=.04)
    box("haru_right_shoulder_plate", (x-.34, y, z0+1.11), (.20, .28, .14), "ivory", bevel=.04)
    cyl("haru_head", (x, y, z0+1.35), .19, .29, "skin", verts=10)
    box("haru_hair", (x, y+.035, z0+1.50), (.39, .35, .11), "brown", bevel=.035)
    box("haru_goggles", (x, y-.19, z0+1.46), (.31, .08, .08), "amber", bevel=.02)


def scale_view(path):
    clear()
    setup_render(2048, 2048, transparent=True)
    boss("rest")
    haru_scale()
    camera_at("shared_world_scale", (24, 0, 0), target=(0, 0, -.1),
              up=(0, 0, 1), scale=14)
    studio()
    render(path)


def compose_designs(tmp):
    # The design boards use original transparent Blender renders as their art.
    p = lambda n: tmp / n
    board("KANNUKI  /  FORM", "W2-03  •  ten-metre bolt / orthographic")
    # The common rule requires all turnaround directions in one horizontal row.
    for x, label, source in (
        (-7.44, "FRONT / 4 arms", OUT/"kannuki_3d_front.png"),
        (-2.48, "RIGHT SIDE / 10 m", OUT/"kannuki_3d_side_right.png"),
        (2.48, "BACK / latch", OUT/"kannuki_3d_back.png"),
        (7.44, "TOP / dorsal core", OUT/"kannuki_3d_top.png"),
    ):
        card(x, -.25, 4.78, 8.62, label, source, 1.32)
    render(OUT/"kannuki_turnaround.png")

    board("KANNUKI  /  SCALE", "Haru 1.55 m  •  chamber diameter 32 m x 16 m")
    card(-4.80, -.25, 9.80, 8.65, "BOLT AND HARU / shared physical scale", p("scale.png"), 1.00)
    card(5.08, -.25, 9.35, 8.65, "CIRCULAR CHAMBER / plan")
    draw_arena_plan(5.08, -.25, 2.90)
    render(OUT/"kannuki_scale.png")

    board("KANNUKI  /  MECHANICS", "pivots / rail shoes / protected lock core")
    card(-4.95, 1.86, 9.55, 4.48, "RIGID ARM / two-axis hinge + Y-axis drill", OUT/"kannuki_arm_side.png", 2.3)
    card(4.95, 1.86, 9.55, 4.48, "RAIL CARRIAGE / two clamp shoes", OUT/"kannuki_3d_bottom.png", 2.3, True)
    card(-4.95, -2.57, 9.55, 4.20, "DORSAL CORE / armoured", OUT/"kannuki_3d_top.png", 2.3, True)
    card(4.95, -2.57, 9.55, 4.20, "DORSAL CORE / exposed", OUT/"kannuki_core_open.png", 2.3, True)
    render(OUT/"kannuki_mechanics.png")

    board("KANNUKI  /  ATTACK BEATS", "telegraph / strike / recovery")
    rows = [
        ("DRILL THRUST", ("windup", "thrust", "thrust_recover")),
        ("ROTARY SWEEP", ("sweep_wind", "sweep", "sweep_recover")),
        ("BODY SLAM", ("slam_wind", "slam", "slam_recover")),
    ]
    for r, (label, states) in enumerate(rows):
        y = 2.48-r*2.85
        txt(label, -9.59, y+1.12, .24, "graphite")
        for c, state in enumerate(states):
            x = -6.30+c*6.28
            card(x, y-.24, 6.03, 2.52,
                 ("01  WIND-UP", "02  ATTACK", "03  RECOVERY")[c],
                 p(state+".png"), 1.50,
                 image_dx=(.62, -.72, -.72)[c] if r == 0 else 0)
            if r == 0:
                panel_rect(x-2.43, y-.37, .09, 1.26, "graphite", .04)
    render(OUT/"kannuki_attacks.png")

    board("KANNUKI  /  THREE PHASES", "independent breakable arms")
    card(-4.95, 1.86, 9.55, 4.48, "PHASE 1 / rail-mounted", OUT/"kannuki_3d_front_right45.png", 1.65)
    card(4.95, 1.86, 9.55, 4.48, "PHASE 2 / rail released", p("phase2.png"), 1.65)
    card(-4.95, -2.57, 9.55, 4.20, "PHASE 3 / red-hot cutters", p("phase3.png"), 1.65)
    card(4.95, -2.57, 9.55, 4.20, "ONE ARM BROKEN / exposed hinge", p("broken.png"), 1.65)
    render(OUT/"kannuki_phases.png")


def arena_scene(path):
    clear()
    preview = os.environ.get("KANNUKI_PREVIEW") == "1"
    setup_render(1024 if preview else 4096, 512 if preview else 2048,
                 transparent=False, mood=True)
    sc = bpy.context.scene
    if preview:
        sc.eevee.taa_render_samples = 8
    sc.world.color = (.06, .065, .067)
    # Thirty-two-metre diameter floor and continuous outer rail.
    cyl("chamber_floor", (0, 0, -.35), 16, .70, "arena_floor", verts=96)
    for radius, z, name, material, thickness in (
        (15.60, .10, "outer_rail", "brass", .18),
        (14.75, .10, "inner_rail", "graphite", .24),
        (15.72, 7.0, "wall_rail", "brass", .20),
        (14.85, 7.0, "boss_rail", "graphite", .30),
    ):
        for j in range(96):
            a, b = 2*math.pi*j/96, 2*math.pi*(j+1)/96
            line3(name, (radius*math.cos(a), radius*math.sin(a), z),
                  (radius*math.cos(b), radius*math.sin(b), z), thickness, material)
    # Radial paving, cut into broad geometry instead of fine photo detail.
    for j in range(32):
        a = j*2*math.pi/32
        line3("floor_joint", (4.5*math.cos(a), 4.5*math.sin(a), -.005),
              (15.7*math.cos(a), 15.7*math.sin(a), -.005), .027, "graphite")
    # The full-height chamber wall is expressed as broad repeated stone blocks.
    for j in range(32):
        a = j*2*math.pi/32
        x, y = 16.05*math.cos(a), 16.05*math.sin(a)
        wall = box("chamber_wall_segment", (x, y, 7.85), (1.05, 3.25, 15.7),
                   "arena_wall", bevel=.13)
        wall.rotation_euler[2] = a
        band = box("wall_vertical_brace", (15.58*math.cos(a), 15.58*math.sin(a), 8),
                   (.38, .55, 15.5), "graphite", bevel=.055)
        band.rotation_euler[2] = a
    # Four breakable square pillars exactly, around the furnace core.
    for a in (.25*math.pi, .75*math.pi, 1.25*math.pi, 1.75*math.pi):
        x, y = 9.35*math.cos(a), 9.35*math.sin(a)
        box("destructible_pillar", (x, y, 5.75), (1.30, 1.30, 11.5),
            "ivory_dim", bevel=.14)
        for z in (2.2, 5.8, 9.6):
            box("pillar_break_seam", (x, y, z), (1.42, 1.42, .13),
                "graphite", bevel=.02)
        box("pillar_base", (x, y, .28), (2.05, 2.05, .56),
            "brass", bevel=.10)
    # Sealed central furnace door in a heavy raised lock housing.
    cyl("furnace_plinth", (0, 0, .60), 4.4, 1.2, "graphite", verts=16)
    box("sealed_door_housing", (0, 0, 5.3), (6.35, 3.65, 9.0),
        "ivory_dim", bevel=.55)
    box("central_furnace_door", (0, -2.02, 4.65), (4.35, .34, 6.95),
        "graphite", bevel=.27)
    box("furnace_latch_vertical", (0, -2.25, 4.65), (.45, .19, 5.70),
        "brass", bevel=.07)
    box("furnace_latch_horizontal", (0, -2.26, 4.65), (3.5, .18, .42),
        "brass", bevel=.05)
    for xx in (-1.35, 1.35):
        box("furnace_amber_seam", (xx, -2.25, 4.65), (.07, .05, 4.65),
            "amber", bevel=.015)
    # Bolt on outer rail, oriented tangentially; no invented legs or eye.
    machine = boss("rest")
    rotate_objects(machine, (0, 0, 0), "Z", math.atan2(8, 12))
    move_objects(machine, (12, 8, 8.95))
    # Stylized Haru-sized scout near the door, solely for atmosphere/scale.
    haru_scale()
    # Haru was authored with feet at -1.75 and y=-6.25: lift to the floor.
    for obj in list(sc.objects):
        if obj.name.startswith("haru_"):
            obj.location.z += 1.75
            obj.location.y += 2.7
    area("warm_furnace", (0, -6, 13), 5500, (1.0, .58, .30), 11, target=(0, 0, 4))
    area("cool_chamber", (10, 5, 14), 4200, (.56, .66, .70), 15, target=(0, 0, 5))
    area("boss_rim", (9, 12, 15), 4500, (1, .69, .37), 9, target=(12, 8, 8))
    # Front-side interior angle sees the furnace door and the boss to its right.
    bpy.ops.object.camera_add(location=(-3, -14, 12))
    cam = bpy.context.object
    cam.name = "arena_mood_camera"
    cam.rotation_euler = (Vector((0, 1, 6))-cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "PERSP"
    cam.data.lens = 16
    sc.camera = cam
    render(path)


def geometry_metrics():
    clear()
    objs = boss("rest")
    verts = []
    tris = 0
    for obj in objs:
        if obj.type != "MESH":
            continue
        tris += sum(max(0, len(poly.vertices)-2) for poly in obj.data.polygons)
        verts.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
    mins = [round(min(v[i] for v in verts), 4) for i in range(3)]
    maxs = [round(max(v[i] for v in verts), 4) for i in range(3)]
    stats = {"vertices": len(verts), "triangles": tris, "bbox_min_xyz_m": mins,
             "bbox_max_xyz_m": maxs, "body_length_m": 10.0,
             "body_diameter_m": 3.5, "arm_length_m": 4.0}
    print("METRICS", json.dumps(stats, ensure_ascii=False))
    (OUT/"metrics.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("KANNUKI_MODE") == "arena":
        arena_scene((Path(tempfile.gettempdir())/"relic_kannuki_arena_preview.png")
                    if os.environ.get("KANNUKI_PREVIEW") == "1"
                    else OUT/"kannuki_arena.png")
        return
    if os.environ.get("KANNUKI_MODE") == "boards":
        with tempfile.TemporaryDirectory(prefix="relic_kannuki_boards_") as td:
            tmp = Path(td)
            scale_view(tmp/"scale.png")
            for state in ("windup", "thrust", "thrust_recover", "sweep_wind",
                          "sweep", "sweep_recover", "slam_wind", "slam",
                          "slam_recover", "phase2", "phase3", "broken"):
                boss_view(tmp/(state+".png"), "front_right45", state, resolution=1024)
            compose_designs(tmp)
        return
    geometry_metrics()
    with tempfile.TemporaryDirectory(prefix="relic_kannuki_") as td:
        tmp = Path(td)
        for view in VIEWS:
            boss_view(OUT/("kannuki_3d_"+view+".png"), view,
                      save_blend=(view == "front_right45"))
        boss_view(OUT/"kannuki_core_open.png", "top", "open")
        for view in ("side", "top", "front"):
            arm_view(OUT/("kannuki_arm_"+view+".png"), view)
        parts_view(OUT/"kannuki_3d_parts.png")
        scale_view(tmp/"scale.png")
        for state in ("windup", "thrust", "thrust_recover", "sweep_wind",
                      "sweep", "sweep_recover", "slam_wind", "slam",
                      "slam_recover", "phase2", "phase3", "broken"):
            boss_view(tmp/(state+".png"), "front_right45", state, resolution=1024)
        compose_designs(tmp)
    arena_scene(OUT/"kannuki_arena.png")


if __name__ == "__main__":
    main()
