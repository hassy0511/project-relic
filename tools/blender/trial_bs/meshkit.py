"""メッシュを組む小さな道具（ロフト＝輪を並べて四角の面でつなぐ、板、キャップ）。

スキル集の character-artist（変形する所は四角の面、関節に輪を足す）と uv-workflow（継ぎ目は見えない側、
手で決めた継ぎ目で展開）に合わせて、ロフトは作るときに UV も決める：u は輪のまわり（継ぎ目は seam の角度）、
v は芯に沿った長さ（m）。あとで島の大きさをそろえて詰める（texel 密度をそろえる）。
面ごとに色の名前（proportions.PAL の鍵）を持たせ、テクスチャはこの色で塗る（textures.py）。
"""
import math
import bmesh
import bpy
from mathutils import Vector, Matrix

from proportions import PAL

PAINT_KEYS = list(PAL.keys())


class Part:
    def __init__(self):
        self.v = []
        self.f = []      # 頂点の番号の並び
        self.uv = []     # 面ごとの (u, v) の並び
        self.col = []    # 面ごとの色の名前

    def add_v(self, p):
        self.v.append(Vector(p))
        return len(self.v) - 1

    def add_f(self, idx, uvs, col):
        self.f.append(list(idx))
        self.uv.append([tuple(t) for t in uvs])
        self.col.append(col)

    def extend(self, other):
        o = len(self.v)
        self.v += [Vector(p) for p in other.v]
        for f, uv, c in zip(other.f, other.uv, other.col):
            self.add_f([i + o for i in f], uv, c)
        return self

    def transformed(self, m):
        p = Part()
        p.v = [m @ v for v in self.v]
        p.f = [list(f) for f in self.f]
        p.uv = [list(u) for u in self.uv]
        p.col = list(self.col)
        return p

    def recolor(self, fn):
        """fn(face_center, face_index, old) -> 新しい色"""
        for i, f in enumerate(self.f):
            c = sum((self.v[k] for k in f), Vector()) / len(f)
            self.col[i] = fn(c, i, self.col[i])
        return self

    def tris(self):
        return sum(len(f) - 2 for f in self.f)


# ---------------------------------------------------------------- 輪
def frame_from_dir(d, up=Vector((0, 0, 1))):
    """芯の向き d に垂直な 2 軸（x, y）。up に近い向きを y にする"""
    d = Vector(d).normalized()
    if abs(d.dot(up)) > 0.95:
        up = Vector((0, -1, 0))
    x = up.cross(d).normalized()
    y = d.cross(x).normalized()
    return x, y


def ring(center, xa, ya, rx, ry, n, start=0.0, sq=2.0, shape=None):
    """中心 center、軸 xa・ya、半径 rx・ry の輪（n 点）。sq > 2 で角ばった丸（超楕円）。
    shape(a) があれば、角度 a での半径の倍率"""
    pts = []
    for j in range(n):
        a = start + 2 * math.pi * j / n
        c, s = math.cos(a), math.sin(a)
        e = 2.0 / sq
        cx = math.copysign(abs(c) ** e, c)
        cy = math.copysign(abs(s) ** e, s)
        k = shape(a) if shape else 1.0
        pts.append(Vector(center) + xa * (cx * rx * k) + ya * (cy * ry * k))
    return pts


def poly_ring(center, xa, ya, pts2d):
    return [Vector(center) + xa * x + ya * y for x, y in pts2d]


def loft(rings, col='brick', cap0=True, cap1=True, closed=True, tip0=None, tip1=None):
    """rings：同じ点の数の輪の並び。四角の面でつなぐ。cap：端を n 角形で閉じる。
    tip：端を 1 点に絞る（三角の扇）。col は文字か、fn(i_ring, j) -> 色"""
    p = Part()
    n = len(rings[0])
    idx = [[p.add_v(q) for q in r] for r in rings]
    # u：輪のまわりの長さ（平均）、v：芯の長さ
    circ = sum(sum((r[(j + 1) % n] - r[j]).length for j in range(n if closed else n - 1)) for r in rings) / len(rings)
    cents = [sum(r, Vector()) / n for r in rings]
    vs = [0.0]
    for i in range(1, len(rings)):
        vs.append(vs[-1] + max((cents[i] - cents[i - 1]).length,
                               sum((rings[i][j] - rings[i - 1][j]).length for j in range(n)) / n))
    us = [circ * j / n for j in range(n + 1)] if closed else [circ * j / (n - 1) for j in range(n)]
    colf = col if callable(col) else (lambda i, j: col)
    m = n if closed else n - 1
    for i in range(len(rings) - 1):
        for j in range(m):
            j1 = (j + 1) % n
            p.add_f([idx[i][j], idx[i][j1], idx[i + 1][j1], idx[i + 1][j]],
                    [(us[j], vs[i]), (us[j + 1], vs[i]), (us[j + 1], vs[i + 1]), (us[j], vs[i + 1])],
                    colf(i, j))
    # 外向きにそろえる（最初の面の法線が芯から外を向くように）
    _orient(p, cents)
    if closed:
        for end, cap, tip in ((0, cap0, tip0), (len(rings) - 1, cap1, tip1)):
            r = rings[end]
            c = cents[end]
            ec = colf(end if end == 0 else end - 1, 0)
            if tip is not None:
                t = p.add_v(tip)
                for j in range(n):
                    j1 = (j + 1) % n
                    a, b = idx[end][j], idx[end][j1]
                    p.add_f([a, b, t], [(us[j], vs[end]), (us[j + 1], vs[end]), ((us[j] + us[j + 1]) / 2, vs[end] + (-1 if end == 0 else 1) * (Vector(tip) - c).length)], ec)
                    _fix_last(p, c, cents, end)
            elif cap:
                xa = (r[0] - c).normalized() if (r[0] - c).length > 1e-9 else Vector((1, 0, 0))
                nrm = (cents[1] - cents[0]) if end == 0 else (cents[-1] - cents[-2])
                ya = nrm.normalized().cross(xa).normalized()
                uv = [((q - c).dot(xa) + 10, (q - c).dot(ya) + 10) for q in r]
                p.add_f(list(idx[end]), uv, ec)
                _fix_last(p, c, cents, end)
    return p


def _face_normal(p, f):
    vs = [p.v[k] for k in f]
    n = Vector()
    for i in range(len(vs)):
        a, b = vs[i], vs[(i + 1) % len(vs)]
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    return n


def _orient(p, cents, m=None):
    """外向きにそろえる：輪の間の面ごとに、法線が芯（両側の輪の中心の中点）から外を向くかを数え、多い方へ"""
    if not p.f:
        return
    n_ring = len(cents)
    per = len(p.f) // max(1, n_ring - 1)
    vote = 0.0
    for k, f in enumerate(p.f):
        i = min(k // max(1, per), n_ring - 2) if n_ring > 1 else 0
        c = (cents[i] + cents[i + 1]) / 2 if n_ring > 1 else cents[0]
        fc = sum((p.v[q] for q in f), Vector()) / len(f)
        nn = _face_normal(p, f)
        if nn.length > 1e-12:
            vote += 1.0 if nn.dot(fc - c) > 0 else -1.0
    if vote < 0:
        for i in range(len(p.f)):
            p.f[i] = p.f[i][::-1]
            p.uv[i] = p.uv[i][::-1]


def _fix_last(p, c, cents, end):
    """端の面を外向きに（芯の外へ）"""
    f = p.f[-1]
    out = (cents[0] - cents[1]) if end == 0 else (cents[-1] - cents[-2])
    if _face_normal(p, f).dot(out) < 0:
        p.f[-1] = f[::-1]
        p.uv[-1] = p.uv[-1][::-1]


def tube(path, radii, n=8, col='brick', up=Vector((0, 0, 1)), sq=2.0, start=0.0, caps=(True, True), shape=None, tips=(None, None)):
    """芯の点の並び path に沿った管。radii：点ごとの (rx, ry) か数。start：継ぎ目の角度"""
    rings = []
    for i, c in enumerate(path):
        if i == 0:
            d = path[1] - path[0]
        elif i == len(path) - 1:
            d = path[-1] - path[-2]
        else:
            d = (path[i + 1] - path[i - 1])
        xa, ya = frame_from_dir(d, up)
        r = radii[i]
        rx, ry = (r, r) if isinstance(r, (int, float)) else r
        rings.append(ring(c, xa, ya, rx, ry, n, start, sq, shape))
    return loft(rings, col, caps[0], caps[1], tip0=tips[0], tip1=tips[1])


def slab(pts2d, center, xa, ya, thick, col='ivory', bevel=0.0, back_col=None):
    """板：2D の輪郭 pts2d を、xa・ya の面に置き、法線（xa × ya）の向きへ thick の厚み。bevel で表の縁を面取り"""
    nrm = xa.cross(ya).normalized()
    c = Vector(center)
    back = poly_ring(c - nrm * thick / 2, xa, ya, pts2d)
    rings = [back]
    if bevel > 0:
        mid = poly_ring(c + nrm * (thick / 2 - bevel), xa, ya, pts2d)
        cx = sum(x for x, _ in pts2d) / len(pts2d)
        cy = sum(y for _, y in pts2d) / len(pts2d)
        inset = []
        for x, y in pts2d:
            d = Vector((x - cx, y - cy))
            ln = d.length
            k = max(0.0, (ln - bevel) / ln) if ln > 1e-9 else 1.0
            inset.append((cx + d.x * k, cy + d.y * k))
        rings += [mid, poly_ring(c + nrm * thick / 2, xa, ya, inset)]
    else:
        rings.append(poly_ring(c + nrm * thick / 2, xa, ya, pts2d))
    p = loft(rings, col)
    if back_col:
        p.col[-2] = back_col
    return p


def rounded_rect(w, h, r, seg=2):
    """幅 w・高さ h・角の丸み r の四角の輪郭（反時計回り）"""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def chamfer_rect(w, h, c):
    """角を切った四角（8 角）。白磁の板・ゴーグルのレンズの角ばった形"""
    return [(w / 2, -h / 2 + c), (w / 2, h / 2 - c), (w / 2 - c, h / 2), (-w / 2 + c, h / 2),
            (-w / 2, h / 2 - c), (-w / 2, -h / 2 + c), (-w / 2 + c, -h / 2), (w / 2 - c, -h / 2)]


# ---------------------------------------------------------------- Blender の物体へ
def to_object(part, name, coll, mat=None, smooth=True, angle=40.0, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in part.v], [], part.f)
    me.validate(clean_customdata=False)
    uvl = me.uv_layers.new(name='UVMap')
    li = 0
    for poly, uvs in zip(me.polygons, part.uv):
        for k, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uvs[k]
    attr = me.attributes.new('paint', 'INT', 'FACE')
    for poly, c in zip(me.polygons, part.col):
        attr.data[poly.index].value = PAINT_KEYS.index(c)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if mat:
        me.materials.append(mat)
    # 重なった点をまとめ、法線をそろえる（blender-modeler の Cleanup Checklist）
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
        if angle is not None:
            me.set_sharp_from_angle(angle=math.radians(angle))
    if parent:
        ob.parent = parent
    return ob
