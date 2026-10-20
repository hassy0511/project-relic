"""町の部品（キット）を数値から組む道具。bpy を使うのは書き出し（write_glb）だけ。

遺構のキット（geo.py）と同じ約束で書き出す：材質は名前（ivory・graphite・brass・amber・cloth…）で、Godot の RoomKit が
content/kits/town.json の "materials" の同じ名前の共有の材質に置き換える。UV は面の向きの平面投影でメートルのまま。
違うのは書き方だけ：座標はゲームと同じ向き（X 右、Y 上、Z 手前 = 部品の正面。yaw=0 で +Z を向く）、単位は m、
原点は部品の底の中心（壁は厚みの中心）。Blender へは (x, -z, y) で渡し、glTF に書き出すとゲームの座標に戻る。
風で揺れる布（旗・洗濯物・垂れ幕・日よけの垂れ・小旗の綱）は、形に揺れの重み（sway・hang・sagging）を付ける。
重みは頂点の色のアルファ（1 - 重み）に入り、キットの材質の "sway" がそれで頂点を動かす（docs/design/42_コンテンツの書き方.md 14.2.2）。
"""
from __future__ import annotations

import math
from typing import Callable, Iterable, Sequence

import numpy as np

V = np.array

# spec_town_3d.md の色見本（sRGB）。陰は焼かない。Godot のキットに同じ名前が無いときだけ、この色がそのまま使われる
MATERIALS: dict[str, dict] = {
    'ivory':    dict(color='#E9DFC9', rough=0.8),      # 壁・床の白磁（#F3E9D2 を日なたで飛ばないよう少し落とす。閂と同じ）
    'ivory2':   dict(color='#D3C6AC', rough=0.85),     # 白磁の 2 段目（段・台の縁など、同じ白が続くと形が読めない所）
    'graphite': dict(color='#444641', rough=0.6, metal=0.3),
    'brass':    dict(color='#A98749', rough=0.42, metal=0.65),
    'cloth':    dict(color='#B75B43', rough=0.95),     # 赤錆色の帆布
    'cloth2':   dict(color='#93432F', rough=0.95),     # 帆布の濃い色（同じ赤が並ばないように）
    'wood':     dict(color='#594333', rough=0.85),
    'wood2':    dict(color='#7A5C43', rough=0.85),     # 明るい板（木箱・踏み台・天板）
    'amber':    dict(color='#FFBC52', emit=3.0),       # 灯具の芯（ゲーム内で発光）
    'dark':     dict(color='#2B2824', rough=0.4),      # 窓の奥・暗い開口
    'green':    dict(color='#6E7A3C', rough=0.9),      # 鉢植え
    'rope':     dict(color='#A08A62', rough=0.95),
    'linen':    dict(color='#E2D5BA', rough=0.95),     # 洗濯物・麻の布
    'desert':   dict(color='#BC5636', rough=1.0),      # 遠景の砂（空の絵の下の砂の色）
    'hull':     dict(color='#E2D6BE', rough=0.85),     # オルドの外殻（遠景。キットで大きな板の絵を貼る）
    'shell':    dict(color='#E9DFC9', rough=0.8),      # 家・擁壁の大きな面（キットで部屋の壁と同じ白磁の絵を貼る。town_terrace）
    'grime_decal': dict(color='#8A7058', rough=1.0),   # 汚れの斑の板（town_rooms.grime_patch。キットの "blend": "decal" の材質で床の上に重ねる）
    'oil_decal': dict(color='#4E4640', rough=1.0),     # 油じみの斑の板（town_rooms.oil_patch）
    'skyglass': dict(color='#F2E6CF', emit=1.2),       # 屋内の明るい窓（外の昼の光。town_rooms.deco の lit）
    # W2-05b 市場のにぎわい（spec_town_goods.md の色見本。town_goods.py）
    'burlap':   dict(color='#E6C398', rough=0.95),     # 麻袋・ござ（生成りの粗布）
    'crop_red': dict(color='#BF4737', rough=0.9),      # 作物の赤（実）
    'crop_green': dict(color='#728052', rough=0.9),    # 作物の緑（葉・乾燥草）
    'crop_yellow': dict(color='#D69E57', rough=0.9),   # 作物の黄（根菜・豆・乾燥果実）
    'wicker':   dict(color='#B08656', rough=0.95),     # かごの編み（spec に色が無いので絵のかごの色。編み目は形にしない）
    'slate':    dict(color='#555A5F', rough=0.9),      # 灰色の布・灰色の袋とかめ・干し魚（絵の灰色。金属でない黒鉛色）
}


# 書き出しでまとめる材質：平らな色だけの材質は頂点の色にして 1 つの材質（flat）に、金属（黒鉛・真鍮）は metal にまとめる。
# 部品ごとの描画は多くて flat・metal・amber の 3 回になる（スマホのブラウザ版の描画の回数を減らす）。
# Godot のキット（town.json）の flat・metal は tint_mix=1 で頂点の色を使う。hull・desert（遠景）はそのまま
GROUP = {'ivory': 'flat', 'ivory2': 'flat', 'cloth': 'flat', 'cloth2': 'flat', 'wood': 'flat', 'wood2': 'flat', 'dark': 'flat',
         'green': 'flat', 'rope': 'flat', 'linen': 'flat', 'graphite': 'metal', 'brass': 'metal',
         'burlap': 'flat', 'crop_red': 'flat', 'crop_green': 'flat', 'crop_yellow': 'flat', 'wicker': 'flat', 'slate': 'flat'}


def hex_lin(h: str) -> tuple[float, float, float]:
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)  # type: ignore


def rot_y(deg: float) -> np.ndarray:
    """ゲームの yaw：+Z を向いた物を yaw 度回すと +X 寄りへ向く"""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return V([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def frame(a, up=(0, 1, 0)):
    a = unit(a)
    up = unit(up)
    if abs(float(a @ up)) > 0.98:
        up = V([1.0, 0, 0]) if abs(a[0]) < 0.9 else V([0, 0, 1.0])
    s = unit(np.cross(a, up))
    return a, s, np.cross(s, a)


# ---------------------------------------------------------------- 形

class Piece:
    """頂点 v (N,3)、面 f、面ごとの滑らかさ sm。w は頂点ごとの揺れの重み（0〜1、None = 揺れない）：書き出しで頂点の色の
    アルファ（1 - w）になり、キットの材質の "sway"（風で揺れる布・垂れたケーブル。42 章 14.2.2）が、重み 0 の留まった端から
    重み 1 の自由な端へ大きく揺らす。組の部品（place）に入れても重みは付いたまま"""

    def __init__(self, v, f, smooth=False, sm=None, w=None):
        self.v = np.asarray(v, float)
        self.f = [list(x) for x in f]
        self.sm = list(sm) if sm is not None else [bool(smooth)] * len(self.f)
        self.w = None if w is None else np.asarray(w, float)

    def moved(self, off=(0, 0, 0), yaw=0.0, scale=(1, 1, 1)) -> 'Piece':
        v = self.v * np.asarray(scale, float)
        if yaw:
            v = v @ rot_y(yaw).T
        f = self.f
        if np.prod(np.sign(scale)) < 0:
            f = [x[::-1] for x in f]
        return Piece(v + np.asarray(off, float), f, sm=self.sm, w=self.w)


def sway(piece: Piece, fn) -> Piece:
    """揺れの重みを付ける：fn(頂点 (N,3)) → 重み (N,)（0〜1 に切る）。重みは位置だけで決める（同じ所の頂点は同じ重み：
    布の表と裏・柄の板が一緒に動き、面が裂けない）。座標はその形を作ったときのもの"""
    piece.w = np.clip(np.asarray(fn(piece.v), float).reshape(-1), 0.0, 1.0)
    return piece


def hang(top_y, length, k=1.0, x=None):
    """吊った布の重み：上の端（y = top_y）で 0、length 下で k。x = (x0, x1) なら、その外は 0（柱・壁の受けを揺らさない）"""
    def fn(v):
        w = k * (top_y - v[:, 1]) / max(length, 1e-6)
        if x is not None:
            w = np.where((v[:, 0] >= x[0] - 1e-6) & (v[:, 0] <= x[1] + 1e-6), w, 0.0)
        return w
    return fn


def sagging(x0, x1, y, dip, length, k=1.0, line=0.25):
    """両端（x0・x1、高さ y）で留まり、真ん中が dip 下がる綱と、そこから吊った布の重み：綱は真ん中ほど揺れ（line × k まで）、
    布は綱からの深さ length で残りの (1 - line) × k を足す"""
    def fn(v):
        s = np.clip((v[:, 0] - x0) / max(x1 - x0, 1e-6), 0.0, 1.0)
        bow = 4.0 * s * (1.0 - s)
        rope_y = y - dip * bow
        drop = np.clip((rope_y - v[:, 1]) / max(length, 1e-6), 0.0, 1.0)
        return k * (line * bow + (1.0 - line) * drop)
    return fn


def _orient(p: Piece) -> Piece:
    """閉じた形の符号つきの体積が負なら裏返す（面を外向きに）"""
    c = p.v.mean(0)
    vol = 0.0
    for f in p.f:
        for k in range(1, len(f) - 1):
            vol += float(np.dot(p.v[f[0]] - c, np.cross(p.v[f[k]] - c, p.v[f[k + 1]] - c)))
    if vol < 0:
        p.f = [f[::-1] for f in p.f]
    return p


def _orient_dir(p: Piece, d) -> Piece:
    f = p.f[0]
    n = np.cross(p.v[f[1]] - p.v[f[0]], p.v[f[2]] - p.v[f[0]])
    if n @ np.asarray(d, float) < 0:
        p.f = [x[::-1] for x in p.f]
    return p


def box(c, size, yaw=0.0) -> Piece:
    """中心 c・全幅 size の箱"""
    h = np.asarray(size, float) / 2
    v = V([[sx * h[0], sy * h[1], sz * h[2]] for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)])
    f = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return _orient(Piece(v, f)).moved(c, yaw)


def boxb(x0, x1, y0, y1, z0, z1) -> Piece:
    """範囲で書く箱"""
    return box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))


def prism(poly, y0, y1, yaw=0.0, off=(0, 0, 0)) -> Piece:
    """凸の多角形 poly（(x, z)）を y0〜y1 に押し出す"""
    n = len(poly)
    v = [(x, y, z) for y in (y0, y1) for x, z in poly]
    f = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)] + [list(range(n))[::-1], list(range(n, 2 * n))]
    return _orient(Piece(V(v, float), f)).moved(off, yaw)


def beam(p0, p1, w, h=None, up=(0, 1, 0)) -> Piece:
    """p0 → p1 の角材（断面 w × h）"""
    h = w if h is None else h
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    a, s, u = frame(p1 - p0, up)
    q = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    v = [p + x * s + y * u for p in (p0, p1) for x, y in q]
    f = [[k, (k + 1) % 4, 4 + (k + 1) % 4, 4 + k] for k in range(4)] + [[3, 2, 1, 0], [4, 5, 6, 7]]
    return _orient(Piece(V(v), f))


def lathe(p0, p1, prof: Sequence[tuple[float, float]], segs=12, cap=True) -> Piece:
    """p0 → p1 の軸のまわりに輪郭 [(割合 0..1, 半径)] を回す。側面は滑らか、蓋は平ら（別の頂点）"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    a, s, u = frame(p1 - p0)
    verts, rings = [], []
    for t, r in prof:
        c = p0 + a * (t * L)
        ids = []
        for k in range(segs):
            ph = 2 * math.pi * (k + 0.5) / segs
            verts.append(c + max(r, 1e-4) * (math.cos(ph) * s + math.sin(ph) * u))
            ids.append(len(verts) - 1)
        rings.append(ids)
    faces = []
    for i in range(len(prof) - 1):
        for k in range(segs):
            faces.append([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]])
    side = Piece(V(verts), faces, smooth=True)
    # 側面の向き：最初の四角形の法線が軸から外へ
    f0 = faces[0]
    n = np.cross(side.v[f0[1]] - side.v[f0[0]], side.v[f0[3]] - side.v[f0[0]])
    cen = side.v[f0].mean(0)
    axis_pt = p0 + a * float((cen - p0) @ a)
    if n @ (cen - axis_pt) < 0:
        side.f = [x[::-1] for x in side.f]
    if not cap:
        return side
    out = [side]
    for ring, t in ((rings[0], 0), (rings[-1], 1)):
        if prof[0 if t == 0 else -1][1] > 1e-3:
            cv = V([verts[i] for i in ring])
            out.append(_orient_dir(Piece(cv, [list(range(segs))]), -a if t == 0 else a))
    return merge(out)


def cyl(p0, p1, r, segs=12, cap=True) -> Piece:
    return lathe(p0, p1, [(0, r), (1, r)], segs, cap)


def tube(points, r, segs=6) -> Piece:
    """折れ線に沿った管（綱・手すり・曲がり管）。継ぎ目は各点で角を二等分する"""
    pts = [np.asarray(p, float) for p in points]
    rings, verts = [], []
    s_prev = None
    for i, p in enumerate(pts):
        if i == 0:
            d = pts[1] - p
        elif i == len(pts) - 1:
            d = p - pts[i - 1]
        else:
            d = unit(p - pts[i - 1]) + unit(pts[i + 1] - p)
        a, s, u = frame(d)
        if s_prev is not None:
            # ねじれないよう、前の輪の横の向きを今の断面へ写す
            s = unit(s_prev - a * float(s_prev @ a))
            u = np.cross(s, a)
        s_prev = s
        ids = []
        for k in range(segs):
            ph = 2 * math.pi * k / segs
            verts.append(p + r * (math.cos(ph) * s + math.sin(ph) * u))
            ids.append(len(verts) - 1)
        rings.append(ids)
    faces = []
    for i in range(len(pts) - 1):
        for k in range(segs):
            faces.append([rings[i][k], rings[i][(k + 1) % segs], rings[i + 1][(k + 1) % segs], rings[i + 1][k]])
    vv = V(verts)
    f0 = faces[0]
    n = np.cross(vv[f0[1]] - vv[f0[0]], vv[f0[3]] - vv[f0[0]])
    if n @ (vv[f0].mean(0) - pts[0]) < 0:
        faces = [f[::-1] for f in faces]
    side = Piece(vv, faces, smooth=True)
    caps = [_orient_dir(Piece(vv[rings[0]], [list(range(segs))]), pts[0] - pts[1]),
            _orient_dir(Piece(vv[rings[-1]], [list(range(segs))]), pts[-1] - pts[-2])]
    return merge([side] + caps)


def sag(p0, p1, n=8, depth=0.3) -> list[np.ndarray]:
    """p0 → p1 を n 分割し、真ん中が depth だけ下がる綱の点"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    return [p0 + (p1 - p0) * t - V([0, depth * 4 * t * (1 - t), 0]) for t in np.linspace(0, 1, n + 1)]


def sheet(corner: Callable[[float, float], Iterable[float]], nu=6, nv=6, thick=0.02) -> Piece:
    """(u, v) ∈ [0,1]² → 点 の布。表と裏を thick だけ離した薄い板（重なった 2 枚の面はちらつくので作らない）"""
    pts = V([[list(corner(u, v)) for u in np.linspace(0, 1, nu + 1)] for v in np.linspace(0, 1, nv + 1)], float)
    rows, cols = pts.shape[0], pts.shape[1]
    du = np.gradient(pts, axis=1)
    dv = np.gradient(pts, axis=0)
    nrm = np.cross(du, dv)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=2, keepdims=True), 1e-9)
    # 表は上（水平に近い布）か手前（立った布）
    mean = nrm.reshape(-1, 3).mean(0)
    if mean[1] < -0.2 or (abs(mean[1]) <= 0.2 and mean[2] < 0):
        nrm = -nrm
        flip = True
    else:
        flip = False
    idx = lambda r, c: r * cols + c  # noqa: E731
    top = (pts + nrm * thick / 2).reshape(-1, 3)
    bot = (pts - nrm * thick / 2).reshape(-1, 3)
    faces = [[idx(r, c), idx(r, c + 1), idx(r + 1, c + 1), idx(r + 1, c)] for r in range(rows - 1) for c in range(cols - 1)]
    if flip:
        faces = [f[::-1] for f in faces]
    m = len(top)
    back = [[i + m for i in f[::-1]] for f in faces]
    edges = [(idx(0, c), idx(0, c + 1)) for c in range(cols - 1)] + [(idx(r, cols - 1), idx(r + 1, cols - 1)) for r in range(rows - 1)] \
        + [(idx(rows - 1, c + 1), idx(rows - 1, c)) for c in range(cols - 1)] + [(idx(r + 1, 0), idx(r, 0)) for r in range(rows - 1)]
    rim = [[b, a, a + m, b + m] for a, b in edges]
    if flip:
        rim = [f[::-1] for f in rim]
    return Piece(np.concatenate([top, bot]), faces + back + rim, sm=[True] * (2 * len(faces)) + [False] * len(rim))


def merge(pieces: Iterable[Piece]) -> Piece:
    pieces = list(pieces)
    vs, fs, off = [], [], 0
    for p in pieces:
        vs.append(p.v)
        fs += [[i + off for i in f] for f in p.f]
        off += len(p.v)
    w = None
    if any(p.w is not None for p in pieces):
        w = np.concatenate([p.w if p.w is not None else np.zeros(len(p.v)) for p in pieces])
    return Piece(np.concatenate(vs) if vs else np.zeros((0, 3)), fs, sm=sum((p.sm for p in pieces), []), w=w)


# ---------------------------------------------------------------- 部品

class Part:
    """材質ごとに形をためる。add(材質, 形...)、place(別の部品, 位置, 向き, 大きさ) で入れ子"""

    def __init__(self, name: str):
        self.name = name
        self.by_mat: dict[str, list[Piece]] = {}

    def add(self, mat: str, *pieces: Piece) -> 'Part':
        assert mat in MATERIALS, mat
        self.by_mat.setdefault(mat, []).extend(pieces)
        return self

    def mark(self) -> dict:
        """今の形の数（材質ごと）。sway_since と組で、そのあとに足した形にだけ揺れの重みを付ける"""
        return {m: len(ps) for m, ps in self.by_mat.items()}

    def sway_since(self, mark: dict, fn) -> 'Part':
        """mark のあとに足した形（どの材質も）に揺れの重み fn（town_geo.sway）を付ける"""
        for m, ps in self.by_mat.items():
            for pc in ps[mark.get(m, 0):]:
                sway(pc, fn)
        return self

    def place(self, other: 'Part', off=(0, 0, 0), yaw=0.0, scale=(1, 1, 1)) -> 'Part':
        if np.isscalar(scale):
            scale = (scale, scale, scale)
        for m, ps in other.by_mat.items():
            self.by_mat.setdefault(m, []).extend(p.moved(off, yaw, scale) for p in ps)
        return self

    def tris(self) -> int:
        return sum(len(f) - 2 for ps in self.by_mat.values() for p in ps for f in p.f)

    def bounds(self):
        allv = np.concatenate([p.v for ps in self.by_mat.values() for p in ps])
        return allv.min(0), allv.max(0)


# ---------------------------------------------------------------- 書き出し（bpy）

def blender_material(name: str):
    import bpy
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    if name in ('flat', 'metal'):
        # 頂点の色（確認の画像の Cycles 用。ゲームではキットの材質に置き換わる）
        attr = m.node_tree.nodes.new('ShaderNodeVertexColor')
        attr.layer_name = 'Col'
        m.node_tree.links.new(attr.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.8 if name == 'flat' else 0.5
        b.inputs['Metallic'].default_value = 0.0 if name == 'flat' else 0.5
        return m
    d = MATERIALS[name]
    col = hex_lin(d['color'])
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = d.get('rough', 0.8)
    b.inputs['Metallic'].default_value = d.get('metal', 0.0)
    if d.get('emit'):
        b.inputs['Emission Color'].default_value = (*col, 1)
        b.inputs['Emission Strength'].default_value = d['emit']
    m.diffuse_color = (*col, 1)
    return m


def to_object(part: Part):
    """部品を Blender の物体 1 つにする。平らな色は頂点の色（GROUP）、UV は面の向きの平面投影（m）。
    先に、同じ平面で重なった同じ向きの面（材質の違うもの）をほどく（check_coplanar.separate：小さい方の面を 1.5 cm 外へ）"""
    import bpy

    import check_coplanar
    check_coplanar.separate_town(part)
    verts, faces, mats, smooth, cols, sway_w = [], [], [], [], [], []
    groups = sorted({GROUP.get(m, m) for m in part.by_mat})
    off = 0
    for m in sorted(part.by_mat):
        mi = groups.index(GROUP.get(m, m))
        col = hex_lin(MATERIALS[m]['color'])
        for p in part.by_mat[m]:
            verts.append(p.v)
            sway_w.append(p.w if p.w is not None else np.zeros(len(p.v)))
            for k, f in enumerate(p.f):
                faces.append([i + off for i in f])
                mats.append(mi)
                smooth.append(p.sm[k])
                cols.append(col)
            off += len(p.v)
    g = np.concatenate(verts)
    # 頂点の色のアルファ = 1 - 揺れの重み（揺れない頂点は 1。前と同じ色）
    alpha = 1.0 - np.concatenate(sway_w)
    b = np.stack([g[:, 0], -g[:, 2], g[:, 1]], 1)      # ゲーム (x, y, z) → Blender (x, -z, y)
    me = bpy.data.meshes.new(part.name)
    me.from_pydata(b.tolist(), [], faces)
    for m in groups:
        me.materials.append(blender_material(m))
    for pl, mi, sm in zip(me.polygons, mats, smooth):
        pl.material_index = mi
        pl.use_smooth = bool(sm)
    me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='CORNER')
    me.uv_layers.new(name='UVMap')
    # 層を足すと前に取った層の参照が古くなることがあるので、両方を作ってから名前で取り直す
    ca = me.color_attributes['Col']
    uv = me.uv_layers['UVMap']
    for pl in me.polygons:
        n = np.abs(np.array(pl.normal))
        ax = int(np.argmax(n))
        c = cols[pl.index]
        for li in pl.loop_indices:
            vi = me.loops[li].vertex_index
            co = b[vi]
            uv.data[li].uv = {0: (co[1], co[2]), 1: (co[0], co[2]), 2: (co[0], co[1])}[ax]
            ca.data[li].color = (*c, float(alpha[vi]))
    me.validate()
    ob = bpy.data.objects.new(part.name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def write_glb(part: Part, path: str) -> dict:
    import os

    import bpy
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    ob = to_object(part)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 揺れの重みのある部品は、頂点の色をアルファごと書き出す（名前で選ぶ。ACTIVE だと、頂点の色を絵に使う材質（flat・metal）
    # だけの部品では RGB だけになり、重みが消えた）。重みの無い部品は前と同じ書き出し（同じ GLB）
    swaying = any(pc.w is not None and bool((pc.w > 0).any()) for ps in part.by_mat.values() for pc in ps)
    vc = dict(export_vertex_color='NAME', export_vertex_color_name='Col') if swaying else dict(export_vertex_color='ACTIVE')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, export_apply=True,
                              export_animations=False, use_selection=True, export_extras=False,
                              export_active_vertex_color_when_no_material=True, **vc)
    lo, hi = part.bounds()
    return {'tris': part.tris(), 'mats': len({GROUP.get(m, m) for m in part.by_mat}), 'min': [round(float(x), 2) for x in lo],
            'max': [round(float(x), 2) for x in hi]}
