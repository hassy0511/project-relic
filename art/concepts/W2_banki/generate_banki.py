"""Deterministic W2-02 Banki model and orthographic sheet renderer (Blender 4.x).

The five models are original, simple low-poly constructions based on the
approved design language in W0 A and the W2-02 order. Run headlessly:

    blender -b --factory-startup --python generate_banki.py

Use ``-- --quick`` for a small visual check, ``-- --design`` for design
sheets, or ``-- --only=charger --only-3d`` to refresh one model's 3D views.
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


OUT = Path(__file__).resolve().parent
QUICK = "--quick" in sys.argv
DESIGN_ONLY = "--design" in sys.argv
ONLY_3D = "--only-3d" in sys.argv
TURNAROUND_ONLY = "--turnaround" in sys.argv
ONLY_ID = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--only=")), None)
PALETTE = {
    "ivory": "F3E9D2",
    "ivory_shadow": "DDD1B8",
    "brass": "A98749",
    "graphite": "444641",
    "graphite_dark": "303330",
    "amber": "FFBC52",
    "alert": "E26A4A",
    "broken": "6F7370",
    "gray": "E6E6E6",
    "orange": "B75B43",
    "brown": "594333",
    "hair": "493A31",
    "skin": "E9B68E",
}
HEIGHT = {"mini": .30, "sentry": 1.10, "charger": 1.20,
          "shield": 1.80, "floater": .80}
VIEW_SCALE = {"mini": .45, "sentry": 1.32, "charger": 2.40,
              "shield": 2.16, "floater": .98}
CENTRE_Z = {"mini": .15, "sentry": .55, "charger": .60,
            "shield": .90, "floater": 0.0}
MAT = {}


def rgba(code):
    return tuple(int(code[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (1.0,)


def linear_rgba(code):
    def convert(c):
        return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
    return tuple(convert(c) for c in rgba(code)[:3]) + (1.0,)


def mat(name):
    if name in MAT:
        return MAT[name]
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba(PALETTE[name])
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = linear_rgba(PALETTE[name])
    bsdf.inputs["Metallic"].default_value = .10 if name == "brass" else 0.0
    bsdf.inputs["Roughness"].default_value = .85
    MAT[name] = m
    return m


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


class Model:
    def __init__(self, name):
        self.name = name
        self.groups = {}
        self.objects = []

    def add(self, obj, group, material):
        obj.name = self.name + "." + group + "." + obj.name
        obj.data.materials.append(mat(material))
        for face in obj.data.polygons:
            face.use_smooth = False
        self.groups.setdefault(group, []).append(obj)
        self.objects.append(obj)
        return obj

    def box(self, name, loc, dims, material="ivory", group="shell", bevel=0.014, rot=0):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = dims
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.rotation_euler[2] = rot
        if bevel:
            mod = obj.modifiers.new("single_chamfer", "BEVEL")
            mod.width = bevel
            mod.segments = 1
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=mod.name)
        return self.add(obj, group, material)

    def cyl(self, name, loc, radius, depth, axis=(0, 0, 1), material="brass", group="joint", verts=12):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
        return self.add(obj, group, material)

    def ico(self, name, loc, scale, material="ivory", group="shell", sub=1):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return self.add(obj, group, material)

    def move(self, delta):
        d = Vector(delta)
        for obj in self.objects:
            obj.location += d

    def scale(self, s):
        for obj in self.objects:
            obj.location *= s
            obj.scale *= s

    def rotate_z(self, angle):
        from mathutils import Matrix
        r = Matrix.Rotation(angle, 4, "Z")
        for obj in self.objects:
            obj.location = r @ obj.location
            if obj.rotation_mode == "QUATERNION":
                obj.rotation_quaternion = r.to_quaternion() @ obj.rotation_quaternion
            else:
                obj.rotation_euler.rotate_axis("Z", angle)

    def rotate_x(self, angle):
        from mathutils import Matrix
        r = Matrix.Rotation(angle, 4, "X")
        for obj in self.objects:
            obj.location = r @ obj.location
            if obj.rotation_mode == "QUATERNION":
                obj.rotation_quaternion = r.to_quaternion() @ obj.rotation_quaternion
            else:
                obj.rotation_euler.rotate_axis("X", angle)


def line(name, a, b, radius=.006, material="brass"):
    a, b = Vector(a), Vector(b)
    v = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=radius, depth=v.length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(v.normalized())
    obj.data.materials.append(mat(material))
    return obj


def build_mini(state):
    m = Model("mini")
    crouch = -.035 if state == "telegraph" else 0.0
    leap = .07 if state == "attack" else 0.0
    zz = crouch + leap
    m.box("lower_frame", (0, 0, .18 + zz), (.29, .23, .09), "graphite", "chassis")
    m.box("pentagonal_wedge", (0, 0, .24 + zz), (.34, .27, .12), "ivory", "shell", .035)
    m.box("ridge", (0, 0, .31 + zz), (.026, .235, .018), "brass", "shell", .007)
    m.box("sensor_recess", (0, -.137, .239 + zz), (.23, .014, .04), "graphite_dark", "sensor_cover", .007)
    m.box("sensor_bar", (0, -.147, .24 + zz), (.18, .006, .016),
          "alert" if state in {"telegraph", "attack"} else "amber" if state != "broken" else "graphite",
          "sensor_cover", .003)
    m.box("blunt_nose", (0, -.140, .183 + zz), (.09, .036, .045), "graphite", "ram", .008)
    if state != "broken":
        for x, side in [(-.125, "left_leg"), (.125, "right_leg")]:
            m.cyl("hip", (x, 0, .14 + zz), .035, .065, (1, 0, 0), "brass", side)
            m.box("spring_shin", (x, 0, .087 + zz), (.073, .075, .10), "ivory", side, .015)
            m.box("foot", (x, -.023, .025 + leap), (.097, .115, .047), "ivory", side, .012)
    else:
        m.box("broken_foot", (.25, -.02, .04), (.10, .11, .05), "ivory_shadow", "detached")
    m.box("back_socket", (0, .131, .20 + zz), (.10, .029, .06), "graphite", "back_panel", .006)
    return m


def build_sentry(state):
    m = Model("sentry")
    head_shift = .035 if state == "telegraph" else -.025 if state == "attack" else 0.0
    m.box("post_body", (0, 0, .82 + head_shift), (.30, .26, .54), "ivory", "shell", .034)
    m.box("vertical_brass_seam", (0, -.137, .936 + head_shift), (.025, .01, .27), "brass", "shell", .005)
    m.box("lower_dark_spine", (0, -.137, .66 + head_shift), (.036, .01, .17), "graphite", "shell", .005)
    m.box("sensor_recess", (0, -.139, .929 + head_shift), (.21, .012, .047), "graphite_dark", "sensor_cover", .006)
    m.box("line_sensor", (0, -.150, .93 + head_shift), (.17, .007, .016),
          "alert" if state in {"telegraph", "attack"} else "amber" if state != "broken" else "graphite",
          "sensor_cover", .003)
    muzzle_y = -.173 if state == "attack" else -.147
    m.box("three_round_muzzle_case", (0, muzzle_y, .80 + head_shift), (.085, .045, .11), "graphite", "muzzle", .008)
    for i in (-1, 0, 1):
        m.cyl("muzzle_hole", (0, muzzle_y - .025, .80 + head_shift + i * .025),
              .008, .003, (0, 1, 0), "graphite_dark", "muzzle", 8)
    m.box("rear_core_frame", (0, .145, .77), (.15, .035, .22), "brass", "core_lid", .013)
    m.box("rear_core", (0, .168, .77), (.095, .009, .14), "amber" if state != "broken" else "graphite", "core_lid", .008)
    if state != "broken":
        for x, side in [(-.13, "left_leg"), (.13, "right_leg")]:
            m.cyl("hip", (x, 0, .58), .059, .095, (1, 0, 0), "brass", side)
            m.box("thigh", (x, 0, .44), (.105, .13, .26), "ivory", side, .017)
            m.cyl("knee", (x, 0, .30), .052, .105, (1, 0, 0), "brass", side)
            m.box("shin", (x, 0, .17), (.10, .12, .23), "ivory", side, .018)
            m.box("broad_foot", (x, -.045, .038), (.16, .22, .075), "ivory", side, .014)
    else:
        for x in (-.13, .13):
            m.box("damaged_upper_leg", (x, 0, .40), (.10, .12, .25), "graphite", "chassis")
        m.box("fallen_shin", (.38, -.03, .05), (.10, .23, .09), "ivory_shadow", "detached")
    return m


def build_charger(state):
    m = Model("charger")
    rush = -.12 if state == "attack" else 0.0
    telegraph = -.07 if state == "telegraph" else 0.0
    m.box("inner_vehicle", (0, rush, .70), (.79, 1.73, .42), "graphite", "chassis", .04)
    if state != "broken":
        m.box("roof_arch", (0, .05 + rush, .99), (.77, 1.58, .32), "ivory", "shell", .095)
        m.box("long_brass_spine", (0, .08 + rush, 1.16), (.032, 1.50, .019), "brass", "shell", .007)
        for x, side in [(-.37, "left_flank"), (.37, "right_flank")]:
            m.box("shoulder_fairing", (x, .08 + rush, .83), (.18, 1.55, .37), "ivory", side, .05)
    else:
        m.box("cracked_roof", (-.14, .17, .91), (.40, 1.10, .19), "ivory_shadow", "shell", .06)
        m.box("torn_panel", (.55, .02, .33), (.23, .55, .13), "ivory", "detached", .03)
    for x, side in [(-.50, "left_wheels"), (.50, "right_wheels")]:
        for y in (-.52, .52):
            m.cyl("wheel_rubber", (x, y + rush, .28), .263, .15, (1, 0, 0), "graphite_dark", side, 16)
            m.cyl("wheel_ivory_ring", (x + (.079 if x > 0 else -.079), y + rush, .28),
                  .20, .015, (1, 0, 0), "ivory", side, 16)
            m.cyl("wheel_hub", (x + (.09 if x > 0 else -.09), y + rush, .28),
                  .092, .026, (1, 0, 0), "brass", side, 12)
    m.box("front_ram", (0, -.95 + rush + telegraph, .52), (.72, .36 if state != "attack" else .43, .23),
          "ivory", "ram", .055)
    m.box("ram_face", (0, -1.13 + rush + telegraph, .53), (.49, .030, .15), "ivory_shadow", "ram", .017)
    # The sensor sits on the chassis face above the moving ram, never floating
    # with the ram's telescoping segment.
    m.box("sensor_recess", (0, -.88 + rush, .80), (.35, .018, .049), "graphite_dark", "sensor_cover", .007)
    m.box("line_sensor", (0, -.89 + rush, .80), (.29, .007, .016),
          "alert" if state in {"telegraph", "attack"} else "amber" if state != "broken" else "graphite",
          "sensor_cover", .003)
    m.box("rear_exhaust", (0, .889 + rush, .65), (.22, .05, .18), "graphite_dark", "rear", .01)
    # The weak core is on the machine's right (+X); left side is solid.
    m.cyl("right_core_socket", (.465, .08 + rush, .79), .14, .045, (1, 0, 0), "graphite_dark", "core_lid")
    m.cyl("right_core", (.492, .08 + rush, .79), .095, .013, (1, 0, 0),
          "amber" if state != "broken" else "graphite", "core_lid")
    hatch_z = .97 if state in {"recovery", "broken"} else .84
    m.box("right_hinged_hatch", (.524, .08 + rush, hatch_z), (.035, .23, .075),
          "ivory", "core_lid", .01)
    return m


def build_shield(state):
    m = Model("shield")
    m.box("torso", (0, 0, 1.30), (.68, .37, .48), "ivory", "shell", .045)
    m.box("chest_seam", (0, -.193, 1.32), (.025, .012, .34), "brass", "shell", .005)
    m.box("hip", (0, 0, .96), (.48, .33, .24), "graphite", "chassis", .032)
    m.box("head", (0, -.01, 1.66), (.37, .31, .28), "ivory", "head", .045)
    m.box("sensor_recess", (0, -.173, 1.68), (.27, .014, .052), "graphite_dark", "sensor_cover", .007)
    m.box("line_sensor", (0, -.185, 1.68), (.21, .007, .018),
          "alert" if state in {"telegraph", "attack"} else "amber" if state != "broken" else "graphite",
          "sensor_cover", .003)
    m.cyl("core_back_socket", (0, .208, 1.34), .15, .050, (0, 1, 0), "brass", "core_lid")
    m.cyl("core_back_lantern", (0, .243, 1.34), .095, .018, (0, 1, 0),
          "amber" if state != "broken" else "graphite", "core_lid")
    for x, side in [(-.22, "right_leg"), (.22, "left_leg")]:
        m.cyl("hip_pivot", (x, 0, .85), .09, .12, (1, 0, 0), "brass", side)
        m.box("thigh", (x, 0, .67), (.21, .25, .32), "ivory", side, .034)
        m.cyl("knee_pivot", (x, 0, .48), .095, .12, (1, 0, 0), "brass", side)
        m.box("heavy_shin", (x, -.006, .27), (.24, .29, .37), "ivory", side, .04)
        m.box("broad_foot", (x, -.075, .065), (.29, .43, .13), "ivory", side, .027)
    m.cyl("right_shoulder", (-.47, 0, 1.41), .13, .16, (1, 0, 0), "brass", "right_arm")
    m.box("right_upper_arm", (-.52, 0, 1.22), (.24, .27, .32), "ivory", "right_arm", .035)
    fist_y = -.17 if state == "attack" else -.045
    m.box("right_forearm", (-.54, fist_y, .91), (.25, .28, .30), "ivory", "right_arm", .032)
    m.box("right_fist", (-.54, fist_y - .07, .70), (.22, .26, .16), "graphite", "right_arm", .035)
    m.cyl("left_shoulder", (.47, 0, 1.41), .13, .16, (1, 0, 0), "brass", "left_arm")
    m.box("left_arm_bracket", (.55, -.035, 1.18), (.20, .25, .48), "graphite", "left_arm", .025)
    sh_z = 1.15 if state == "telegraph" else .96 if state == "recovery" else 1.05
    sh_y = -.36 if state in {"telegraph", "attack"} else -.28
    if state != "broken":
        m.box("left_wall_shield", (.78, sh_y, sh_z), (.45, .15, 1.05), "ivory", "shield", .07)
        m.box("shield_brass_spine", (.78, sh_y - .084, sh_z), (.030, .013, .88), "brass", "shield", .004)
        m.box("shield_lower_lip", (.78, sh_y - .092, sh_z - .34), (.28, .014, .09), "graphite", "shield", .01)
    else:
        m.box("broken_shield", (1.03, -.36, .64), (.30, .12, .47), "ivory_shadow", "detached", .035)
        m.box("broken_shield_fragment", (.73, -.40, .27), (.19, .12, .19), "ivory", "detached", .02)
    return m


def build_floater(state):
    m = Model("floater")
    tilt = math.radians(12) if state in {"telegraph", "attack"} else 0
    m.cyl("dark_central_hull", (0, 0, 0), .29, .17, material="graphite", group="chassis", verts=12)
    for i, a in enumerate((0, 120, 240)):
        angle = math.radians(a)
        x, y = .18 * math.sin(angle), -.18 * math.cos(angle)
        if state == "broken" and i == 2:
            m.box("fallen_lobe", (.49, .30, -.20), (.23, .32, .10), "ivory_shadow", "detached", .045)
            continue
        m.box("three_lobed_carapace", (x, y, .035), (.40, .36, .15), "ivory", "lobe_%d" % i, .065, -angle)
        m.box("radial_brass_seam", (x, y, .118), (.024, .26, .009), "brass", "lobe_%d" % i, .003, -angle)
    m.cyl("top_lantern_frame", (0, 0, .128), .115, .045, material="brass", group="core_lid", verts=12)
    m.cyl("top_lantern_core", (0, 0, .159), .074, .018,
          material="amber" if state != "broken" else "graphite", group="core_lid", verts=12)
    m.box("front_sensor_recess", (0, -.392, .014), (.23, .015, .043), "graphite_dark", "sensor_cover", .008)
    m.box("front_line_sensor", (0, -.404, .014), (.19, .006, .016),
          "alert" if state in {"telegraph", "attack"} else "amber" if state != "broken" else "graphite",
          "sensor_cover", .003)
    m.box("lower_gun_case", (0, -.24, -.13), (.115, .14, .092), "graphite_dark", "muzzle", .018)
    m.cyl("lower_muzzle", (0, -.31, -.13), .029, .017, (0, 1, 0), "graphite", "muzzle", 12)
    for i, a in enumerate((0, 120, 240)):
        angle = math.radians(a)
        x, y = .20 * math.sin(angle), -.20 * math.cos(angle)
        m.box("underside_vent", (x, y, -.093), (.12, .18, .014), "graphite_dark", "vents", .008, -angle)
    if tilt:
        from mathutils import Matrix
        r = Matrix.Rotation(tilt, 4, "X")
        for obj in m.objects:
            obj.location = r @ obj.location
            obj.rotation_euler.rotate_axis("X", tilt)
    return m


BUILDERS = {"mini": build_mini, "sentry": build_sentry, "charger": build_charger,
            "shield": build_shield, "floater": build_floater}


def build_haru():
    """Simple scale mannequin in Haru's W0-A color and 155 cm proportions."""
    m = Model("haru_scale")
    m.box("jacket", (0, 0, 1.00), (.33, .20, .35), "orange", "torso", .055)
    m.box("undershirt", (0, -.107, 1.02), (.13, .014, .28), "ivory", "torso", .005)
    m.box("belt", (0, 0, .81), (.36, .22, .045), "graphite", "torso", .01)
    m.box("shorts", (0, 0, .70), (.36, .24, .22), "orange", "torso", .025)
    for x in (-.13, .13):
        m.box("thigh", (x, 0, .55), (.16, .20, .19), "orange", "leg", .024)
        m.cyl("knee", (x, -.01, .43), .07, .16, (1, 0, 0), "brass", "leg")
        m.box("shin", (x, 0, .26), (.13, .16, .30), "ivory", "leg", .018)
        m.box("boot", (x, -.05, .075), (.18, .28, .15), "brown", "leg", .022)
        m.box("boot_toe", (x, -.167, .055), (.17, .09, .085), "ivory", "leg", .019)
    for x in (-.25, .25):
        m.box("shoulder", (x, 0, 1.14), (.14, .21, .16),
              "ivory" if x < 0 else "orange", "arm", .026)
        m.box("orange_sleeve", (x * 1.11, 0, 1.06), (.14, .17, .14), "orange", "arm", .02)
        m.box("forearm", (x * 1.20, 0, .91), (.115, .14, .20),
              "skin" if x < 0 else "ivory", "arm", .02)
        m.box("glove", (x * 1.29, -.005, .76), (.11, .14, .13), "graphite", "arm", .02)
    m.box("neck", (0, 0, 1.24), (.11, .11, .09), "skin", "head", .018)
    m.ico("face", (0, -.005, 1.37), (.16, .13, .17), "skin", "head", 2)
    m.ico("large_hair", (0, .018, 1.47), (.175, .15, .086), "hair", "head", 1)
    for x in (-.10, .00, .10):
        m.ico("hair_tuft", (x, -.065, 1.50), (.07, .08, .048), "hair", "head")
    m.box("goggle_band", (0, -.138, 1.51), (.29, .019, .047), "graphite", "head", .009)
    for x in (-.075, .075):
        m.box("goggle_lens", (x, -.150, 1.515), (.105, .007, .029), "amber", "head", .004)
        m.ico("eye_white", (x, -.134, 1.385), (.043, .012, .046), "ivory", "head", 1)
        m.ico("brown_iris", (x, -.145, 1.385), (.025, .009, .032), "brown", "head", 1)
        m.box("brow", (x, -.139, 1.438), (.070, .008, .010), "hair", "head", .002)
    m.box("small_smile", (0, -.139, 1.313), (.055, .006, .007), "brown", "head", .002)
    return m


def camera_at(direction, target, ortho):
    target = Vector(target)
    d = 5.0
    dirs = {
        "front": Vector((0, -d, 0)), "back": Vector((0, d, 0)),
        "side_right": Vector((d, 0, 0)), "side_left": Vector((-d, 0, 0)),
        "front_right45": Vector((d / math.sqrt(2), -d / math.sqrt(2), 0)),
        "top": Vector((0, 0, d)), "bottom": Vector((0, 0, -d)),
    }
    bpy.ops.object.camera_add(location=target + dirs[direction])
    cam = bpy.context.object
    cam.name = "RenderCamera"
    v = target - cam.location
    cam.rotation_euler = v.to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    # Blender ortho_scale spans the horizontal field at landscape aspect;
    # convert the requested vertical world span to a matching wide field.
    cam.data.ortho_scale = ortho * max(bpy.context.scene.render.resolution_x / bpy.context.scene.render.resolution_y, 1.0)
    bpy.context.scene.camera = cam
    return cam


def lighting(camera):
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("NeutralWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (.8, .8, .8, 1)
    bg.inputs["Strength"].default_value = .55
    for offset, energy, size in [((0, 0, 0), 115, 4.0), ((1.5, 1.0, 2.0), 45, 3.0)]:
        bpy.ops.object.light_add(type="AREA", location=camera.location + Vector(offset))
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()


def render(path, width, height, direction, target, ortho, transparent=True):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.film_transparent = transparent
    scene.render.filepath = str(OUT / path)
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.eevee.taa_render_samples = 16
    camera = camera_at(direction, target, ortho)
    lighting(camera)
    if not transparent:
        # A neutral background is specified for design sheets; no floor plane.
        scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value = linear_rgba("E6E6E6")
        scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 1
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path, width, height)


def mark_axes(id_, center_x=0):
    axes = {
        "mini": [(-.13, 0, .14), (.13, 0, .14)],
        "sentry": [(-.13, 0, .58), (.13, 0, .58), (-.13, 0, .30), (.13, 0, .30)],
        "charger": [(.50, -.52, .28), (.50, .52, .28), (.47, .08, .79)],
        "shield": [(-.47, 0, 1.41), (.47, 0, 1.41), (.78, -.28, 1.05), (0, .20, 1.34)],
        "floater": [(0, 0, .13), (0, -.24, -.13)],
    }
    for x, y, z in axes[id_]:
        x += center_x
        line("joint_axis", (x - .09, y - .06, z), (x + .09, y - .06, z), .007, "alert")
        line("joint_axis_end", (x - .09, y - .06, z - .025), (x - .09, y - .06, z + .025), .006, "alert")
        line("joint_axis_end", (x + .09, y - .06, z - .025), (x + .09, y - .06, z + .025), .006, "alert")


def explode(m, id_):
    offsets = {
        "mini": {"left_leg": (-.17, 0, -.10), "right_leg": (.17, 0, -.10), "sensor_cover": (0, -.11, 0), "back_panel": (0, .13, 0)},
        "sentry": {"left_leg": (-.24, 0, -.10), "right_leg": (.24, 0, -.10), "muzzle": (0, -.16, 0), "sensor_cover": (0, -.16, .12), "core_lid": (0, .18, 0)},
        "charger": {"left_wheels": (-.26, 0, -.10), "right_wheels": (.26, 0, -.10), "ram": (0, -.20, 0), "core_lid": (.21, 0, .15), "sensor_cover": (0, -.20, .12)},
        "shield": {"right_arm": (-.22, 0, 0), "left_arm": (.17, 0, 0), "shield": (.38, -.15, 0), "core_lid": (0, .20, 0), "sensor_cover": (0, -.16, .08)},
        "floater": {"lobe_0": (0, -.19, .05), "lobe_1": (.18, .10, .05), "lobe_2": (-.18, .10, .05), "muzzle": (0, -.11, -.12), "core_lid": (0, 0, .16)},
    }
    for group, delta in offsets[id_].items():
        for obj in m.groups.get(group, []):
            obj.location += Vector(delta)
    # Sparse straight connection guides, not arrows or dimension lines.
    for group, delta in offsets[id_].items():
        objs = m.groups.get(group, [])
        if not objs:
            continue
        c = sum((obj.location for obj in objs), Vector((0, 0, 0))) / len(objs)
        line("assembly_connector", c - Vector(delta), c, .0025, "brass")


def render_3d(id_):
    views = ["front", "back", "side_right", "top", "bottom", "front_right45"]
    if id_ in {"charger", "shield"}:
        views.append("side_left")
    clear()
    build = BUILDERS[id_]("idle")
    for view in views:
        render(f"{id_}_3d_{view}.png", 2048, 2048, view,
               (0, 0, CENTRE_Z[id_]), VIEW_SCALE[id_], True)
        for obj in list(bpy.context.scene.objects):
            if obj.type in {"CAMERA", "LIGHT"}:
                bpy.data.objects.remove(obj, do_unlink=True)
    clear()
    m = BUILDERS[id_]("idle")
    explode(m, id_)
    render(f"{id_}_3d_parts.png", 2048, 2048, "front_right45",
           (0, 0, CENTRE_Z[id_]), VIEW_SCALE[id_] * 1.35, True)
    clear()
    BUILDERS[id_]("broken")
    render(f"{id_}_3d_broken.png", 2048, 2048, "front",
           (0, 0, CENTRE_Z[id_]), VIEW_SCALE[id_], True)


def render_scale(id_):
    clear()
    haru = build_haru()
    haru.move((-.82, 0, 0))
    m = BUILDERS[id_]("idle")
    if id_ == "charger":
        m.rotate_z(math.pi / 2)
    if id_ == "floater":
        m.move((.68, 0, .94))
    else:
        m.move((.75, 0, 0))
    render(f"{id_}_scale.png", 4096, 2048, "front",
           (0, 0, .80), 2.08, False)


def render_mechanics(id_):
    clear()
    m = BUILDERS[id_]("idle")
    m.move((-.90, 0, 0))
    mark_axes(id_, -.90)
    ex = BUILDERS[id_]("idle")
    explode(ex, id_)
    ex.move((.90, 0, 0))
    sc = {"mini": 1.35, "sentry": 1.62, "charger": 2.55,
          "shield": 2.45, "floater": 1.42}[id_]
    render(f"{id_}_mechanics.png", 4096, 2048, "front_right45",
           (0, 0, CENTRE_Z[id_]), sc, False)


def render_attack(id_):
    clear()
    x_positions = (-1.80, -.60, .60, 1.80)
    states = ("idle", "telegraph", "attack", "recovery")
    factor = {"mini": 2.15, "sentry": .75, "charger": .64,
              "shield": .58, "floater": 1.25}[id_]
    for x, state in zip(x_positions, states):
        m = BUILDERS[id_](state)
        if id_ == "charger":
            m.rotate_z(math.radians(35))
        m.scale(factor)
        m.move((x, 0, 0))
        if state == "telegraph":
            line("telegraph_flash", (x - .20, -.45, .20), (x + .20, -.45, .20), .025, "alert")
    render(f"{id_}_attack.png", 4096, 2048, "front",
           (0, 0, .55), 2.70, False)


def render_states(id_):
    clear()
    x_positions = (-1.65, 0, 1.65)
    factor = {"mini": 2.30, "sentry": .78, "charger": .69,
              "shield": .62, "floater": 1.32}[id_]
    for x, state in zip(x_positions, ("idle", "telegraph", "broken")):
        m = BUILDERS[id_](state)
        if id_ == "charger":
            m.rotate_z(math.radians(35))
        m.scale(factor)
        m.move((x, 0, 0))
    render(f"{id_}_states.png", 4096, 2048, "front",
           (0, 0, .55), 2.70, False)


def family_text(body, x, z, size):
    bpy.ops.object.text_add(location=(x, -.9, z), rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = "family_note"
    obj.data.body = body
    obj.data.size = size
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.materials.append(mat("graphite"))


def render_turnaround(id_):
    """The four exact model views used as the authoritative design sheet."""
    clear()
    config = {
        "mini": (4.2, 3.3, (-2.20, -.73, .73, 2.20)),
        "sentry": (1.3, 3.0, (-2.25, -.75, .75, 2.25)),
        "charger": (.95, 3.8, (-2.60, -.87, .87, 2.60)),
        "shield": (.75, 3.3, (-2.20, -.73, .73, 2.20)),
        "floater": (1.4, 3.0, (-2.25, -.75, .75, 2.25)),
    }
    factor, ortho, xs = config[id_]
    for x, direction in zip(xs, ("FRONT", "RIGHT SIDE", "BACK", "TOP")):
        m = BUILDERS[id_]("idle")
        m.scale(factor)
        if direction == "RIGHT SIDE":
            m.rotate_z(-math.pi / 2)
        elif direction == "BACK":
            m.rotate_z(math.pi)
        elif direction == "TOP":
            m.rotate_x(math.pi / 2)
        elevation = (.85 if id_ == "charger" else .50) if direction == "TOP" else (.50 if id_ == "floater" else 0)
        m.move((x, 0, elevation))
        family_text(direction, x, -.45, .13)
    render(f"{id_}_turnaround.png", 4096, 2048, "front",
           (0, 0, .42), ortho, False)


def render_family():
    clear()
    layout = [
        ("mini", -3.15, 2.40, "MINI\nALL"),
        ("sentry", -1.65, 1.0, "SENTRY\nBACK CORE"),
        ("charger", -.15, .70, "CHARGER\nRIGHT CORE"),
        ("shield", 1.65, .78, "SHIELD\nBACK CORE"),
        ("floater", 3.15, 1.22, "FLOATER\nTOP CORE"),
    ]
    for id_, x, factor, caption in layout:
        m = BUILDERS[id_]("idle")
        if id_ == "charger":
            m.rotate_z(math.radians(35))
        m.scale(factor)
        m.move((x, 0, .55 if id_ == "floater" else 0))
        family_text(caption, x, -.48, .18)
    family_text("COMMON  /  IVORY SHELL  /  BRASS SEAMS  /  LINE SENSOR", 0, 2.02, .20)
    family_text("NORMAL AMBER  -  ALERT CORAL  |  DISTINCT WEAK POINTS", 0, 1.78, .14)
    render("banki_family.png", 4096, 2048, "front", (0, 0, .75), 3.85, False)


def save_source():
    clear()
    for x, id_ in zip((-2.7, -1.35, 0, 1.50, 2.95), BUILDERS):
        m = BUILDERS[id_]("idle")
        bpy.context.view_layer.update()
        points = [obj.matrix_world @ Vector(corner) for obj in m.objects for corner in obj.bound_box]
        lows = [min(p[i] for p in points) for i in range(3)]
        highs = [max(p[i] for p in points) for i in range(3)]
        tris = sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons) for obj in m.objects)
        print("MODEL_METRIC", id_, "bbox_min", tuple(round(v, 4) for v in lows),
              "bbox_max", tuple(round(v, 4) for v in highs), "triangles", tris, flush=True)
        m.move((x, 0, 0))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "banki_models.blend"))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in PALETTE:
        mat(name)
    ids = [ONLY_ID] if ONLY_ID else list(BUILDERS)
    if any(id_ not in BUILDERS for id_ in ids):
        raise ValueError("Unknown --only ID")
    if TURNAROUND_ONLY:
        for id_ in ids:
            render_turnaround(id_)
        print("COMPLETE_TURNAROUNDS", flush=True)
        return
    if QUICK:
        render_scale("mini")
        return
    for id_ in ids:
        if not DESIGN_ONLY:
            render_3d(id_)
        if not ONLY_3D:
            for fn in (render_scale, render_mechanics, render_attack, render_states):
                fn(id_)
        print("DONE", id_, flush=True)
    if not ONLY_ID and not ONLY_3D:
        render_family()
    if not DESIGN_ONLY:
        save_source()
    print("COMPLETE", len(list(OUT.glob("*.png"))), flush=True)


if __name__ == "__main__":
    main()
