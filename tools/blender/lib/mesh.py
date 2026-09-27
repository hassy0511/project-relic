"""本番キャラクター用の形づくりの道具。

- loft：輪切りの断面を道筋に沿って並べ、筒や塊を作る（手足、胴、髪の房、帯）
- 色は「色見本テクスチャ」のマス目を UV で指す（1 枚のテクスチャで全身の色を持つ）
- 骨の重みは、骨の線分までの距離から自動で付ける（関節の近くは 2 本の骨が混ざる）
"""
from __future__ import annotations

import math
from typing import Callable, Iterable, Sequence

import bmesh
import bpy
from mathutils import Vector

Vec = Sequence[float]


# ---------------------------------------------------------------- 形

def _frame(t: Vector, ref: Vector) -> tuple[Vector, Vector]:
    """道筋の向き t に直交する (横, 前) の 2 軸"""
    u = ref - t * ref.dot(t)
    if u.length < 1e-4:
        alt = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = alt - t * alt.dot(t)
    u.normalize()
    s = t.cross(u).normalized()
    return s, u


def loft(name: str, path: Sequence[Vec], radii: Sequence[float | tuple[float, float]], sides: int = 8,
         cap_start: bool = True, cap_end: bool = True, ref: Vec = (0, -1, 0), loop: bool = False,
         angle0: float | None = None, offsets: Sequence[Vec] | None = None) -> bpy.types.Object:
    """道筋 path の各点に楕円の断面（横 rx, 前 ry）を置いてつなぐ。

    半径が 0 の断面は 1 点に縮める（髪の房の先など）。loop=True で道筋を輪にする（ゴーグルの帯など）。
    offsets は各断面の中心をずらす量（前へのふくらみ等）。
    """
    pts = [Vector(p) for p in path]
    refv = Vector(ref).normalized()
    n = len(pts)
    a0 = math.pi / sides if angle0 is None else angle0
    bm = bmesh.new()
    rings: list[list[bmesh.types.BMVert]] = []
    for i, c in enumerate(pts):
        if loop:
            t = (pts[(i + 1) % n] - pts[(i - 1) % n])
        elif i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        t.normalize()
        s, u = _frame(t, refv)
        r = radii[i]
        rx, ry = (r, r) if isinstance(r, (int, float)) else r
        if offsets:
            c = c + Vector(offsets[i])
        if rx <= 1e-6 and ry <= 1e-6:
            rings.append([bm.verts.new(c)])
            continue
        ring = []
        for k in range(sides):
            th = a0 + 2 * math.pi * k / sides
            ring.append(bm.verts.new(c + s * (rx * math.cos(th)) + u * (ry * math.sin(th))))
        rings.append(ring)
    pairs = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if loop else [])
    for i, j in pairs:
        a, b = rings[i], rings[j]
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1 or len(b) == 1:
            tip, ring = (a[0], b) if len(a) == 1 else (b[0], a)
            for k in range(sides):
                bm.faces.new((ring[k], ring[(k + 1) % sides], tip))
            continue
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    if not loop:
        if cap_start and len(rings[0]) > 2:
            bm.faces.new(rings[0])
        if cap_end and len(rings[-1]) > 2:
            bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _to_object(name, bm)


def lock(name: str, base: Vec, ctrl: Vec, tip: Vec, width: float, depth: float, sides: int = 4,
         segments: int = 3, ref: Vec = (0, -1, 0), fat: float = 1.0) -> bpy.types.Object:
    """髪の房：base から ctrl を通って tip へ曲がりながら細くなる塊"""
    b, c, t = Vector(base), Vector(ctrl), Vector(tip)
    path, radii = [], []
    for i in range(segments + 1):
        f = i / segments
        p = (1 - f) ** 2 * b + 2 * (1 - f) * f * c + f ** 2 * t
        path.append(p)
        k = (1 - f) ** 0.8 * (1 + 0.25 * fat * math.sin(math.pi * f))
        radii.append((width * k, depth * k) if i < segments else 0.0)
    return loft(name, path, radii, sides=sides, cap_start=True, ref=ref)


def head_shape(name: str, center: Vec, rx: float, ry: float, rz_top: float, rz_bot: float, segments: int = 20,
               rings: int = 12, jaw: float = 0.55, chin_fwd: float = 0.02, face_flat: float = 0.9) -> bpy.types.Object:
    """頭：上は丸く、下はあごへ細くなる。顔の面は少し平らにする"""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    cx, cy, cz = center
    for v in bm.verts:
        x, y, z = v.co
        if z >= 0:
            X, Y, Z = x * rx, y * ry, z * rz_top
        else:
            t = -z
            w = 1 - jaw * t ** 1.6
            X = x * rx * w
            Y = y * ry * (1 - 0.3 * t ** 1.4) - chin_fwd * t ** 2
            Z = z * rz_bot
        if Y < 0:
            Y *= face_flat
        v.co = Vector((cx + X, cy + Y, cz + Z))
    return _to_object(name, bm)


def rbox(name: str, center: Vec, size: Vec, bevel: float = 0.0, rot: Vec = (0, 0, 0),
         taper: tuple[float, float] = (1.0, 1.0)) -> bpy.types.Object:
    """面取りした箱。rot は XYZ の回転（度）。taper は上面の (幅, 奥行き) の倍率"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = size
    for v in bm.verts:
        x, y, z = v.co
        if z > 0:
            x *= taper[0]
            y *= taper[1]
        v.co = Vector((x * sx, y * sy, z * sz))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', profile=0.5)
    from mathutils import Euler
    m = Euler(tuple(math.radians(a) for a in rot), 'XYZ').to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _to_object(name, bm)


def cyl(name: str, center: Vec, radius: float, depth: float, axis: Vec = (0, 0, 1), sides: int = 8) -> bpy.types.Object:
    c = Vector(center)
    a = Vector(axis).normalized()
    return loft(name, [c - a * depth / 2, c + a * depth / 2], [radius, radius], sides=sides,
                ref=(0, -1, 0) if abs(a.y) < 0.9 else (0, 0, 1))


def _to_object(name: str, bm: bmesh.types.BMesh) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.uv_layers.new(name='UVMap')
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def transform(obj: bpy.types.Object, fn: Callable[[Vector], Vector]) -> None:
    for v in obj.data.vertices:
        v.co = fn(v.co.copy())


def mirror_x(obj: bpy.types.Object, name: str) -> bpy.types.Object:
    """左右反転した複製（面の向きも直す）"""
    me = obj.data.copy()
    me.name = name
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 色（色見本テクスチャのマス目を指す）

class Palette:
    """色の名前 → 色見本テクスチャのマス目。cells×cells のマス目に左上から並べる"""

    def __init__(self, entries: list[tuple[str, str, float]], cells: int = 8):
        self.entries = entries  # (名前, #hex, 発光の強さ 0〜1)
        self.cells = cells
        self.index = {n: i for i, (n, _, _) in enumerate(entries)}

    def uv(self, name: str) -> tuple[float, float]:
        i = self.index[name]
        col, row = i % self.cells, i // self.cells
        # Blender の UV は左下が原点。画像の上の行が v の大きい側
        return ((col + 0.5) / self.cells, 1 - (row + 0.5) / self.cells)


def paint(obj: bpy.types.Object, pal: Palette, color: str | Callable[[Vector, Vector], str]) -> None:
    """面ごとに色を塗る。color は色の名前か、(面の中心, 法線) → 色の名前 の関数"""
    me = obj.data
    uvl = me.uv_layers[0].data
    for poly in me.polygons:
        name = color if isinstance(color, str) else color(poly.center.copy(), poly.normal.copy())
        u, v = pal.uv(name)
        for li in poly.loop_indices:
            uvl[li].uv = (u, v)


# ---------------------------------------------------------------- 骨の重み

def _seg_dist(p: Vector, a: Vector, b: Vector) -> float:
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def weight_auto(obj: bpy.types.Object, arm: bpy.types.Object, bones: Iterable[str], power: float = 6.0,
                max_influences: int = 3) -> None:
    """骨の線分までの距離で重みを付ける。関節の近くでは隣り合う骨が混ざり、なめらかに曲がる"""
    bones = list(bones)
    segs = [(b, arm.data.bones[b].head_local.copy(), arm.data.bones[b].tail_local.copy()) for b in bones]
    groups = {b: obj.vertex_groups.get(b) or obj.vertex_groups.new(name=b) for b in bones}
    for v in obj.data.vertices:
        ws = []
        for b, h, t in segs:
            d = _seg_dist(v.co, h, t)
            ws.append((1.0 / (d + 0.004) ** power, b))
        ws.sort(reverse=True)
        ws = ws[:max_influences]
        total = sum(w for w, _ in ws)
        for w, b in ws:
            w /= total
            if w > 0.01:
                groups[b].add([v.index], w, 'REPLACE')


def weight_rigid(obj: bpy.types.Object, bone: str) -> None:
    vg = obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')


def weight_fn(obj: bpy.types.Object, fn: Callable[[Vector], dict[str, float]]) -> None:
    """頂点の位置から重みを決める関数で付ける"""
    for v in obj.data.vertices:
        for b, w in fn(v.co.copy()).items():
            if w <= 0:
                continue
            vg = obj.vertex_groups.get(b) or obj.vertex_groups.new(name=b)
            vg.add([v.index], w, 'REPLACE')


# ---------------------------------------------------------------- 陰影のなめらかさ

def smooth(obj: bpy.types.Object, angle_deg: float | None) -> None:
    """angle_deg=None で全面なめらか、数値で「その角度より鋭い辺は角を立てる」、0 で全面カクカク"""
    me = obj.data
    if angle_deg is None:
        for p in me.polygons:
            p.use_smooth = True
        return
    if angle_deg <= 0:
        for p in me.polygons:
            p.use_smooth = False
        return
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg))


def tri_count(obj: bpy.types.Object) -> int:
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def parent_to_bone(obj: bpy.types.Object, arm: bpy.types.Object, bone: str) -> None:
    """物体を骨の子にする（glTF では骨のノードの子として書き出される）。今の位置は保つ"""
    bpy.context.view_layer.update()  # 作ったばかりの物体は matrix_world がまだ更新されていない
    mw = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = mw
