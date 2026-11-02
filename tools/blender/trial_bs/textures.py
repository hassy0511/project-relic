"""UV の詰め込みと色の地図（テクスチャ）。

uv-workflow：ロフトの UV（継ぎ目は見えない側）を、材質ごとに島の大きさをそろえて（average_islands_scale ＝ texel 密度をそろえる）
1 枚の地図へ詰める（pack_islands、余白 0.004）。texture-workflow / stylized-style：色は面ごとの基準色で塗り、
陰の段は「描いた陰」として 2 段目の色で塗る（下を向く面、髪の房の内側）。AO は焼かない（stylized：painted, not baked）。
顔：頭の前の面を正面の投影で UV にし、2×2 の表情の絵（haru_face_expressions.png）の各区画から、目・眉・鼻・口だけを
肌の色の上へ写す（絵の陰は肌の平らな色に戻す）。区画 0（左上）が通常、ゲームは uv1_offset で区画を切り替える。
"""
import os
import math

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw

import proportions as P
from meshkit import PAINT_KEYS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ART = os.path.join(ROOT, 'build', 'art')

DARK = {'brick': 'brick_dk', 'ivory': 'ivory_dk', 'umber': 'umber_dk', 'skin': 'skin_dk', 'amber': 'amber_dk', 'graphite_lt': 'graphite'}
HEAD_C = Vector((0, -0.015, 1.34))

# 顔：頭の (x, z) → 表情の絵の区画の画素（区画は 1024 角、2048 の地図の左上）。目の中心・あごの下で合わせた
FACE_EYE_X = 587.0
FACE_EYE_Y = 655.0
FACE_EYE_Z = 1.322
FACE_PX_PER_M = 1871.0
# 2×2 の絵は区画ごとに頭の位置がずれている（肌の形の位相相関で測った、区画 0 に対する位置のずれ）
FACE_SHIFT = [(0, 0), (-149, -1), (0, -132), (-148, -130)]
FACE_BOXES = [  # 区画の画素：右目と眉、左目と眉、鼻、口
    (398, 538, 546, 712), (628, 538, 778, 712), (556, 722, 616, 768), (505, 760, 672, 848)]
FACE_BROW_Y = 598     # これより上（眉の帯）では、髪の色（前髪の先）を写さない


def face_uv(x, z):
    qx = FACE_EYE_X + x * FACE_PX_PER_M
    qy = FACE_EYE_Y + (FACE_EYE_Z - z) * FACE_PX_PER_M
    return qx / 2048.0, 1.0 - qy / 2048.0


def head_uv(ob):
    """頭の UV：前を向く面は正面の投影（表情の区画 0）、後ろを向く面は肌だけの隅へ"""
    me = ob.data
    uvl = me.uv_layers['UVMap']
    mw = ob.matrix_world
    for poly in me.polygons:
        n = (mw.to_3x3() @ poly.normal)
        for li in poly.loop_indices:
            v = mw @ me.vertices[me.loops[li].vertex_index].co
            if n.y < 0.15 and v.y < 0.03:
                uvl.data[li].uv = face_uv(v.x, v.z)
            else:
                uvl.data[li].uv = (40 / 2048.0 + (v.x + 0.15) * 0.05, 1 - (40 / 2048.0 + (1.5 - v.z) * 0.05))


def face_texture(path):
    art = Image.open(os.path.join(ART, 'haru_face_expressions.png')).convert('RGBA')
    A = np.array(art).astype(np.float32)
    skin = np.array(P.RGB['skin'], np.float32)
    ref_skin = np.array((248, 182, 134), np.float32)          # 絵の肌（明るい側）
    out = np.zeros((2048, 2048, 4), np.float32)
    out[..., :3] = skin
    out[..., 3] = 255
    for qi in range(4):
        ox, oy = (qi % 2) * 1024, (qi // 2) * 1024
        sx, sy = FACE_SHIFT[qi]
        for x0, y0, x1, y1 in FACE_BOXES:
            src = A[oy + sy + y0:oy + sy + y1, ox + sx + x0:ox + sx + x1]
            rgb = src[..., :3]
            d = np.sqrt(((rgb - ref_skin) ** 2).sum(-1))
            # 肌に近い色（絵の陰・赤み）は平らな肌に戻す。遠い色（目・眉・口）だけ写す
            m = np.clip((d - 38.0) / 40.0, 0, 1) * (src[..., 3] / 255.0)
            lum = 0.3 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]
            hairlike = (lum > 52) & (lum < 105) & (rgb[..., 0] - rgb[..., 2] > 25) & (rgb[..., 0] < 135)
            rows = np.arange(y0, y1)[:, None] + np.zeros((1, x1 - x0))
            m[hairlike & (rows < FACE_BROW_Y)] = 0.0
            dst = out[oy + y0:oy + y1, ox + x0:ox + x1]
            dst[..., :3] = dst[..., :3] * (1 - m[..., None]) + rgb * m[..., None]
    Image.fromarray(out.astype(np.uint8), 'RGBA').convert('RGB').save(path)


def pack(objs):
    """objs の UV の島を、大きさをそろえて 1 枚へ詰める（複数の物体を一緒に編集）"""
    bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')


def raster(objs, size, path):
    img = Image.new('RGB', (size, size), (128, 128, 128))
    dr = ImageDraw.Draw(img)
    for ob in objs:
        me = ob.data
        uvl = me.uv_layers['UVMap']
        pa = me.attributes['paint']
        mw = ob.matrix_world
        rot = mw.to_3x3()
        hair = ob.name.startswith('SM_Hair_')
        for poly in me.polygons:
            key = PAINT_KEYS[pa.data[poly.index].value]
            n = (rot @ poly.normal).normalized()
            c = mw @ poly.center
            dark = n.z < -0.55
            if hair:
                dark = n.dot((c - HEAD_C).normalized()) < 0.2
            if dark and key in DARK:
                key = DARK[key]
            col = P.RGB[key]
            pts = [(uvl.data[li].uv.x * size, (1 - uvl.data[li].uv.y) * size) for li in poly.loop_indices]
            dr.polygon(pts, fill=col, outline=col)
            dr.line(pts + [pts[0]], fill=col, width=3)
    img.save(path)


def image_node(mat, path, name):
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    for n in list(nt.nodes):
        if n.type == 'VERTEX_COLOR':
            nt.nodes.remove(n)
    img = bpy.data.images.load(path)
    img.name = name
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Linear'
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    return tex


def make_all(objs, M, out):
    tex = os.path.join(out, 'tex')
    os.makedirs(tex, exist_ok=True)
    groups = {}
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.data.materials:
            groups.setdefault(ob.data.materials[0].name, []).append(ob)
    # 顔
    head = bpy.data.objects['SM_Char_HaruBS_Head']
    head_uv(head)
    p = os.path.join(tex, 'haru_bs_T_HaruBS_Face_BC.png')
    face_texture(p)
    image_node(M['face'], p, 'T_HaruBS_Face_BC')
    # 体・服・髪の地図、フレーム、銃
    for key, mname, size, tname in (('cloth', 'MAT_Cloth_HaruBS', 2048, 'T_HaruBS_Body_BC'),
                                    ('frame', 'MAT_Ceramic_FrameBS', 1024, 'T_HaruBS_Frame_BC'),
                                    ('gun', 'spark_gun_HaruBS', 512, 'T_HaruBS_SparkGun_BC')):
        obs = groups.get(mname, [])
        if not obs:
            continue
        pack(obs)
        p = os.path.join(tex, f'haru_bs_{tname}.png')
        raster(obs, size, p)
        image_node(M[key], p, tname)
    # 光刃：平らな琥珀（発光はゲームで別に付ける。透明は使わない）
    mb = M['blade']
    nt = mb.node_tree
    for n in list(nt.nodes):
        if n.type == 'VERTEX_COLOR':
            nt.nodes.remove(n)
    bsdf = nt.nodes['Principled BSDF']
    r, g, b = (c / 255.0 for c in P.RGB['amber'])
    bsdf.inputs['Base Color'].default_value = (r ** 2.2, g ** 2.2, b ** 2.2, 1)
    bsdf.inputs['Emission Color'].default_value = (r ** 2.2, g ** 2.2, b ** 2.2, 1)
    bsdf.inputs['Emission Strength'].default_value = 2.0
