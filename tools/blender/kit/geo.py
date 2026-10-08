"""部屋のキットの部品を組む道具（寸法は m、Blender の座標：X 幅・Y 奥行き・Z 高さ）。

部品の正面（通路側）は Blender の -Y。glTF（Godot）では +Z になる（RoomKit の yaw = 0 で +Z を向く）。
形は単純な立体（箱・面取りの箱・回転体・管の曲げ）だけで組み、部品ごとに材質の名前（ivory・graphite・brass・amber・red・…）を付ける。
材質の名前は Godot 側のキット（content/kits/<id>.json の "materials"）で同じ名前の共有の材質に置き換わる。
UV は面の向きに合わせた平面の投影で、メートルのまま（Godot のシェーダーが uv_m で割る）。
"""
from __future__ import annotations

import math

import numpy as np

V3 = np.array

# W2-06 spec の色（sRGB）。Godot のキットに同じ名前が無いときだけ、この色がそのまま使われる
PALETTE = {
    'ivory': ('#F3E9D2', 0.72, 0.0, 0.0),
    'graphite': ('#444641', 0.55, 0.35, 0.0),
    'brass': ('#A98749', 0.45, 0.7, 0.0),
    'amber': ('#FFBC52', 0.4, 0.0, 4.0),
    'red': ('#D4433D', 0.4, 0.0, 4.0),
    'sand': ('#C9A27E', 0.95, 0.0, 0.0),
    'cloth': ('#B75B43', 0.95, 0.0, 0.0),
    'grate': ('#594333', 0.7, 0.2, 0.0),
    'dark': ('#2A2A28', 0.8, 0.0, 0.0),
    'sky': ('#FFE2B8', 0.9, 0.0, 2.5),
    'shaft': ('#FFD9A0', 0.9, 0.0, 1.0),
}


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(a, up=(0, 0, 1)):
    a = unit(a)
    up = unit(up)
    if abs(a @ up) > 0.98:
        up = np.array([0, 1.0, 0]) if abs(a[1]) < 0.9 else np.array([1.0, 0, 0])
    side = unit(np.cross(a, up))
    return a, side, np.cross(side, a)


def orient(v, faces):
    """閉じた立体の面を外向きにそろえる（符号つきの体積が負なら裏返す）"""
    c = v.mean(axis=0)
    vol = 0.0
    for f in faces:
        for k in range(1, len(f) - 1):
            vol += np.dot(v[f[0]] - c, np.cross(v[f[k]] - c, v[f[k + 1]] - c))
    return [f[::-1] for f in faces] if vol < 0 else faces


class Part:
    """部品 1 つ：材質ごとの形の集まり。add_* はどれも (頂点, 面) を足す"""

    def __init__(self, name: str, note: str = ''):
        self.name = name
        self.note = note
        self.pieces: list[tuple[str, np.ndarray, list, bool]] = []   # (材質, 頂点, 面, なめらか)

    def add(self, mat, v, f, smooth=False):
        v = np.asarray(v, float)
        self.pieces.append((mat, v, orient(v, f), smooth))
        return self

    # ---- 形
    def box(self, mat, lo, hi):
        """軸にそろった箱（lo・hi は角の座標）"""
        lo, hi = V3(lo, float), V3(hi, float)
        v = [[(hi if i & 1 else lo)[0], (hi if i & 2 else lo)[1], (hi if i & 4 else lo)[2]] for i in range(8)]
        f = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
        return self.add(mat, v, f)

    def boxc(self, mat, c, s):
        c, s = V3(c, float), V3(s, float) / 2
        return self.box(mat, c - s, c + s)

    def prism(self, mat, poly, z0, z1, axis='z', at=(0, 0)):
        """凸の多角形 poly（2D）を軸の向きに z0〜z1 押し出す。axis：z（poly は x,y）・y（x,z）・x（y,z）"""
        n = len(poly)
        v = []
        for z in (z0, z1):
            for (a, b) in poly:
                a, b = a + at[0], b + at[1]
                v.append({'z': (a, b, z), 'y': (a, z, b), 'x': (z, a, b)}[axis])
        f = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)]
        f += [list(range(n))[::-1], list(range(n, 2 * n))]
        return self.add(mat, v, f)

    def cbox(self, mat, c, s, ch, axis='z'):
        """面取りの箱（軸に直角な断面の 4 隅を ch 落とす）"""
        c, s = V3(c, float), V3(s, float) / 2
        idx = {'z': (0, 1, 2), 'y': (0, 2, 1), 'x': (1, 2, 0)}[axis]
        w, h, d = s[idx[0]], s[idx[1]], s[idx[2]]
        poly = [(-w, -h + ch), (-w + ch, -h), (w - ch, -h), (w, -h + ch), (w, h - ch), (w - ch, h), (-w + ch, h), (-w, h - ch)]
        return self.prism(mat, poly, c[idx[2]] - d, c[idx[2]] + d, axis, (c[idx[0]], c[idx[1]]))

    def lathe(self, mat, p0, p1, prof, segs=16, smooth=True):
        """p0 → p1 の軸のまわりに、輪郭 prof = [(軸に沿った割合 0..1, 半径)] を回す"""
        p0, p1 = V3(p0, float), V3(p1, float)
        L = np.linalg.norm(p1 - p0)
        a, s, u = frame(p1 - p0)
        verts, rings = [], []
        for t, r in prof:
            c = p0 + a * (t * L)
            if r < 1e-6:
                verts.append(c)
                rings.append([len(verts) - 1] * segs)
                continue
            ids = []
            for k in range(segs):
                ph = 2 * math.pi * (k + 0.5) / segs
                verts.append(c + r * (math.cos(ph) * s + math.sin(ph) * u))
                ids.append(len(verts) - 1)
            rings.append(ids)
        faces = []
        for i in range(len(prof) - 1):
            for k in range(segs):
                q = [rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]]
                d = [x for j, x in enumerate(q) if x != q[j - 1]]
                if len(d) >= 3:
                    faces.append(d)
        # ふた：始めの輪は向きを逆に（前は両方を同じ向きで足したので、始めのふたが内向きになり、外から見ると消えて筒の中が透けた）
        for ring in (rings[0][::-1], rings[-1]):
            if len(set(ring)) > 1:
                faces.append(list(ring))
        return self.add(mat, verts, faces, smooth)

    def cyl(self, mat, p0, p1, r, segs=16, smooth=True):
        return self.lathe(mat, p0, p1, [(0, r), (1, r)], segs, smooth)

    def sweep(self, mat, path, r, segs=16, smooth=True):
        """折れ線 path に沿った太さ r の管（曲がり管）"""
        path = [V3(p, float) for p in path]
        verts, rings = [], []
        up0 = None
        for i, p in enumerate(path):
            t = unit(path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)])
            if up0 is None:
                _, s0, up0 = frame(t)
            s = unit(np.cross(t, up0))
            u = np.cross(s, t)
            ids = []
            for k in range(segs):
                ph = 2 * math.pi * (k + 0.5) / segs
                verts.append(p + r * (math.cos(ph) * s + math.sin(ph) * u))
                ids.append(len(verts) - 1)
            rings.append(ids)
        faces = []
        for i in range(len(path) - 1):
            for k in range(segs):
                faces.append([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]])
        faces += [rings[0][::-1], rings[-1]]
        v = np.asarray(verts)
        # 管は閉じているが曲がっているので、面の向きは輪の順で決める（orient は凸でない形でも体積の符号で正しく働く）
        return self.add(mat, v, faces, smooth)

    def tube(self, mat, rings):
        """輪の列（どれも同じ点の数）をつないだ、ふたの無い筒（光の筋など）"""
        verts, faces = [], []
        n = len(rings[0])
        for r in rings:
            verts.extend(r)
        for i in range(len(rings) - 1):
            for k in range(n):
                faces.append([i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k])
        self.pieces.append((mat, np.asarray(verts, float), faces, True))
        return self

    def mound(self, mat, c, rx, ry, h, segs=14, rings=5):
        """砂の吹きだまり：つぶれた半球（底は平ら）"""
        c = V3(c, float)
        verts = []
        rows = []
        for i in range(rings + 1):
            t = i / rings
            z = h * math.sin(t * math.pi / 2)
            k = math.cos(t * math.pi / 2)
            row = []
            for j in range(segs):
                ph = 2 * math.pi * j / segs
                wob = 1.0 + 0.08 * math.sin(3 * ph + 1.3) + 0.05 * math.cos(5 * ph)
                verts.append(c + V3([rx * k * wob * math.cos(ph), ry * k * wob * math.sin(ph), z]))
                row.append(len(verts) - 1)
            rows.append(row)
        faces = []
        for i in range(rings):
            for j in range(segs):
                faces.append([rows[i][j], rows[i][(j + 1) % segs], rows[i + 1][(j + 1) % segs], rows[i + 1][j]])
        faces.append(rows[0][::-1])
        faces = [f for f in faces if len(set(f)) >= 3]
        top = rows[-1]
        faces = [list(dict.fromkeys(f)) for f in faces]
        return self.add(mat, verts, faces, True)

    def transformed(self, fn_v, start=0):
        """start 番目以降の形の頂点に fn_v（N×3 → N×3）を掛ける（回転・移動）"""
        for i in range(start, len(self.pieces)):
            m, v, f, sm = self.pieces[i]
            self.pieces[i] = (m, fn_v(v), f, sm)
        return self

    def mirror_x(self, start=0):
        """start 番目以降の形を X で反転して足す（左右対称を 1 つの定義から作る）"""
        n = len(self.pieces)
        for i in range(start, n):
            m, v, f, sm = self.pieces[i]
            w = v.copy()
            w[:, 0] *= -1
            self.add(m, w, f, sm)
        return self


def rot_z(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return lambda v: v @ R.T


def to_blender(part: Part):
    """部品を 1 つの Blender の物体にする（材質ごとの面、平面投影の UV（m）、管・球だけなめらか）"""
    import bpy
    names = []
    for m, *_ in part.pieces:
        if m not in names:
            names.append(m)
    verts, faces, mat_idx, smooth = [], [], [], []
    off = 0
    for m, v, f, sm in part.pieces:
        verts.extend(v.tolist())
        for fc in f:
            faces.append([i + off for i in fc])
            mat_idx.append(names.index(m))
            smooth.append(sm)
        off += len(v)
    me = bpy.data.meshes.new(part.name)
    me.from_pydata(verts, [], faces)
    me.validate()
    for m in names:
        me.materials.append(material(m))
    uv = me.uv_layers.new(name='UVMap')
    V = np.asarray(verts)
    for pi, pl in enumerate(me.polygons):
        pl.material_index = mat_idx[pi]
        pl.use_smooth = smooth[pi]
        n = np.abs(np.asarray(pl.normal))
        ax = int(np.argmax(n))
        for li in pl.loop_indices:
            p = V[me.loops[li].vertex_index]
            uv.data[li].uv = {0: (p[1], p[2]), 1: (p[0], p[2]), 2: (p[0], p[1])}[ax]
    ob = bpy.data.objects.new(part.name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def srgb_to_linear(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def material(name):
    import bpy
    m = bpy.data.materials.get(name)
    if m:
        return m
    hexc, rough, metal, emit = PALETTE.get(name, ('#9A948C', 0.7, 0.0, 0.0))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    col = (*srgb_to_linear(hexc), 1.0)
    b.inputs['Base Color'].default_value = col
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit > 0:
        b.inputs['Emission Color'].default_value = col
        b.inputs['Emission Strength'].default_value = emit
    m.diffuse_color = col
    return m


def tri_count(part: Part) -> int:
    return sum(len(fc) - 2 for _, _, f, _ in part.pieces for fc in f)
