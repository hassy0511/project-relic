"""中段の広場の北の段々（高さ 16 m の段の壁、手前の面 z=16）を、奥行きのある家の塊にする。

前は「壁の面に家の正面を貼っただけ」で、階段の口・壁の両端・階段の上から見ると、正面の奥が何も無い板（ハリボテ）だった。
ここでは段ごとに家を本当の箱（側面・屋根・奥行き）で積み、段を奥へ下げていく（絵：town_mood_day の左の段々の町）。

  段 0（床〜5 m）  擁壁。広場に面した扉・配管・はしご（前の terrace_* の下の段と同じ）。上の面が 5 m の通路
  段 1（5〜約 9.4 m）  通路の奥（z≈18.5）に家の正面。屋根が 9.4 m の通路（前の縁に手すり）
  段 2（約 9.4〜14 m）  z≈22 に家の正面。屋根に給水塔・日よけ
  段 3（約 14〜17.5 m）  z≈27 に家の正面。町の空の線（給水塔・柱）
  北の階段の両側（|x| 4〜8）は高さ 9 m の角の棟。階段は棟の間の路地になり、路地の奥（z=34）に上の段への門の棟
  広場の東西の端（|x| 46.5〜48）は段ごとに奥へ下げた妻の面（窓・配管）。下は広場の床の下（-7 m）まで擁壁

座標は部屋のまま（原点 = 部屋の原点。飾りは pos [0,0,0]・yaw 0 で置く）。+Z が丘の奥、広場は z < 16。
当たり判定は部屋の geometry のまま（段の壁の箱・階段の横の壁・門の壁は "hide" で描かない）。見えている面は当たり判定の面と同じ所に置く
（擁壁の面 z=16、路地の面 |x|=4、門の面 z=34）。当たり判定より高い所（路地の 9 m より上、門の 12 m より上）は、
カメラが入り込まないよう路地の面から下げる（段 2・段 3 は |x| ≥ 8）。

大きな面（家の壁・擁壁）は材質 shell（キットの壁と同じ白磁の絵）、細部は平らな色（flat）・金属（metal）・灯（amber）。
"""
from __future__ import annotations

import math

import numpy as np

import town_parts as P
from town_geo import Part, Piece, beam, boxb, cyl, lathe, sag, sheet, tube
from town_sets import _door, _retaining, _window

WALL_Z = 16.0        # 段の壁の手前の面（擁壁の面）
BACK = 40.0          # 家の塊の奥（どこからも見えない）
ALLEY = 4.0          # 北の階段の両側の壁の面 |x|
TOWER = 8.0          # 角の棟の外の面 |x|
TOWER_TOP = 9.0      # 角の棟の屋根（= 階段の横の壁の当たり判定の上）
END = 48.0           # 広場の東西の端（擁壁の前の部分の端）
END1 = 46.5          # 段 0 の奥・段 1 の妻の面
GATE_Z = 34.0        # 門の棟の面（門の壁の当たり判定の面）
GATE_TOP = 12.0      # 門の棟の屋根（= 門の壁の当たり判定の上）


# ---------------------------------------------------------------- 面の飾り（面の座標：面は z=0、+Z が外、x は面の中心から）

def _rail(p: Part, a, b, y, h=0.95, lamps=4.0, step=2.0):
    """手すり（a → b の (x, z)、床の高さ y）：真鍮の柱と上の棒、黒鉛の中の棒。lamps m ごとに柱の上の小さな灯"""
    a, b = np.array([a[0], y, a[1]], float), np.array([b[0], y, b[1]], float)
    L = float(np.linalg.norm(b - a))
    if L < 0.3:
        return
    d = (b - a) / L
    n = max(1, int(round(L / step)))
    for k in range(n + 1):
        c = a + d * (L * k / n)
        p.add('brass', boxb(c[0] - 0.035, c[0] + 0.035, y, y + h, c[2] - 0.035, c[2] + 0.035))
        if lamps and k % max(1, int(round(lamps / step))) == 1:
            p.add('amber', boxb(c[0] - 0.05, c[0] + 0.05, y + h + 0.02, y + h + 0.15, c[2] - 0.05, c[2] + 0.05))
            p.add('brass', boxb(c[0] - 0.07, c[0] + 0.07, y + h + 0.15, y + h + 0.19, c[2] - 0.07, c[2] + 0.07))
    p.add('brass', cyl(a + [0, h, 0], b + [0, h, 0], 0.04, 5, cap=False))
    p.add('graphite', beam(a + [0, h * 0.55, 0], b + [0, h * 0.55, 0], 0.04))


def _balcony(p: Part, x0, x1, y, out=0.9):
    """小さなバルコニー（面に付く床と手すり）"""
    p.add('wood', boxb(x0, x1, y - 0.12, y, 0, out))
    p.add('graphite', boxb(x0, x1, y - 0.22, y - 0.12, 0, out - 0.05))
    for x in (x0 + 0.1, x1 - 0.1):
        p.add('graphite', beam((x, y - 0.9, 0.02), (x, y - 0.18, out - 0.15), 0.06))
    _rail(p, (x0 + 0.05, out - 0.06), (x1 - 0.05, out - 0.06), y, h=0.85, lamps=0, step=0.6)
    for x in (x0 + 0.05, x1 - 0.05):
        _rail(p, (x, 0.05), (x, out - 0.06), y, h=0.85, lamps=0, step=0.5)


def _window_simple(p: Part, x, y, z):
    """遠くから見る窓（_window の軽い版：枠は 1 枚の箱、暗い奥、上へ開いた雨戸。三角形 36）"""
    p.add('graphite', boxb(x - 0.46, x + 0.46, y - 0.08, y + 0.78, z, z + 0.08))
    p.add('dark', boxb(x - 0.36, x + 0.36, y, y + 0.7, z + 0.08, z + 0.095))
    hinge = np.array([x, y + 0.78, z + 0.08])
    d = np.array([0, -math.cos(math.radians(55)), math.sin(math.radians(55))])
    p.add('wood', beam(hinge, hinge + d * 0.62, 0.86, 0.04, up=(0, 0, 1)))


def _window_far(p: Part, x, y, z, shutter=True):
    """もっと遠くから見る窓（下の段の家並み）：裏の面の無い黒鉛の枠、暗い奥は 1 枚の面、雨戸は半分だけ（三角形 12〜24）"""
    fr = boxb(x - 0.42, x + 0.42, y - 0.08, y + 0.74, z, z + 0.07)
    fr.f = [f for f in fr.f if not all(abs(fr.v[k][2] - z) < 1e-6 for k in f)]
    p.add('graphite', fr)
    zz = z + 0.072
    p.add('dark', Piece(np.array([[x - 0.33, y, zz], [x + 0.33, y, zz], [x + 0.33, y + 0.66, zz], [x - 0.33, y + 0.66, zz]]), [[0, 1, 2, 3]]))
    if shutter:
        hinge = np.array([x, y + 0.74, z + 0.07])
        d = np.array([0, -math.cos(math.radians(55)), math.sin(math.radians(55))])
        p.add('wood', beam(hinge, hinge + d * 0.58, 0.78, 0.04, up=(0, 0, 1)))


def _door_far(p: Part, x, y0, z):
    """もっと遠くから見る扉：裏の面の無い黒鉛の枠の板に木の扉の面と真鍮の取っ手（三角形 24。_door は 96）"""
    fr = boxb(x - 0.55, x + 0.55, y0, y0 + 1.95, z, z + 0.08)
    fr.f = [f for f in fr.f if not all(abs(fr.v[k][2] - z) < 1e-6 for k in f)]
    p.add('graphite', fr)
    zz = z + 0.082
    p.add('wood', Piece(np.array([[x - 0.45, y0, zz], [x + 0.45, y0, zz], [x + 0.45, y0 + 1.82, zz], [x - 0.45, y0 + 1.82, zz]]), [[0, 1, 2, 3]]))
    p.add('brass', boxb(x + 0.25, x + 0.31, y0 + 0.85, y0 + 1.1, zz, zz + 0.05))


def _lamp_simple(p: Part, x, y, z):
    """遠くから見る吊り灯（琥珀の箱と真鍮の笠）"""
    p.add('amber', boxb(x - 0.07, x + 0.07, y - 0.13, y + 0.12, z - 0.07, z + 0.07))
    p.add('brass', boxb(x - 0.11, x + 0.11, y + 0.12, y + 0.2, z - 0.11, z + 0.11), boxb(x - 0.08, x + 0.08, y - 0.18, y - 0.13, z - 0.08, z + 0.08))


def _awning_simple(p: Part, x0, x1, y, kind, out=1.2, drop=0.45):
    """遠くから見るひさし（P.awning の軽い版）：壁の受け、前の棒、帆布の面（たるみ 1 段）、前の垂れ"""
    w = x1 - x0
    p.add('graphite', boxb(x0, x1, y - 0.08, y + 0.06, 0, 0.1))
    p.add('brass', beam((x0 + 0.06, y - drop, out), (x1 - 0.06, y - drop, out), 0.06))
    for x in (x0 + 0.08, x1 - 0.08):
        p.add('brass' if kind == 'hard' else 'graphite', beam((x, y, 0.05), (x, y - drop, out), 0.05))
    p.add('cloth', sheet(lambda u, v: (x0 + 0.05 + (w - 0.1) * u, y - drop * v - 0.06 * math.sin(math.pi * u) * math.sin(math.pi * v) + 0.02,
                                       0.06 + (out - 0.06) * v), 3, 2, 0.025))
    p.add('cloth', boxb(x0 + 0.05, x1 - 0.05, y - drop - 0.2, y - drop + 0.02, out - 0.01, out + 0.02))


def pot(p: Part, x, y, z, s=1.0):
    """通路・屋上の小さな鉢植え（P.planter の軽い版）"""
    p.add('ivory', boxb(x - 0.3 * s, x + 0.3 * s, y, y + 0.45 * s, z - 0.3 * s, z + 0.3 * s))
    p.add('graphite', boxb(x - 0.32 * s, x + 0.32 * s, y + 0.4 * s, y + 0.47 * s, z - 0.32 * s, z + 0.32 * s))
    p.add('green', P._blob((x, y + 0.75 * s, z), 0.36 * s), P._blob((x + 0.12 * s, y + 0.98 * s, z - 0.05 * s), 0.24 * s))


def _retaining_light(p: Part, w, h):
    """妻の面の擁壁（遠く・外から見る）：2 m ごとの黒鉛の柱と 2 m の帯だけ（_retaining の軽い版）"""
    n = int(round(w / 2))
    for k in range(n + 1):
        x = min(max(-w / 2 + k * 2, -w / 2 + 0.1), w / 2 - 0.1)
        p.add('graphite', boxb(x - 0.1, x + 0.1, 0, h, 0, 0.1))
    for y in range(2, int(h), 2):
        p.add('graphite', boxb(-w / 2, w / 2, y - 0.05, y + 0.05, 0, 0.08))
    for y in (h - 4.9, h - 2.9):
        for k in range(n):
            xx = -w / 2 + k * 2 + 1.0
            p.add('brass', boxb(xx - 0.05, xx + 0.05, y - 0.09, y + 0.09, 0, 0.035))


def _face(spec: dict, w: float, h: float) -> Part:
    """面の飾り。spec：
      windows [(x, y)]、door x、door2 x（両開きの大きな扉）、awnings [(x0, x1, y, 'hard'|'soft'[, 奥行き])]、lanterns [(x, y)]、
      balconies [(x0, x1, y)]、pipes [x]、posts [x]（黒鉛の付け柱）、bands [y]（黒鉛の帯）、ladder (x, h)、vents [(x, y)]"""
    p = Part('face')
    for x in spec.get('posts', ()):
        P.post(p, x, 0.06, 0, h, 0.18, 0.14)
    for y in spec.get('bands', ()):
        p.add('graphite', boxb(-w / 2, w / 2, y - 0.06, y + 0.06, 0, 0.07))
    simple = spec.get('simple', False)     # 遠くから見る面：窓と灯を軽い版にする
    for k, (x, y) in enumerate(spec.get('windows', ())):
        if spec.get('far'):                # もっと遠く（下の段の家並み）：さらに軽い窓、雨戸は 1 つおき
            _window_far(p, x, y, 0.01, shutter=k % 2 == 0)
        else:
            (_window_simple if simple else _window)(p, x, y, 0.01)
    if spec.get('door') is not None:
        (_door_far if spec.get('far') else _door)(p, spec['door'], 0, 0.01)
    if spec.get('door2') is not None:
        x = spec['door2']
        for sx in (-1, 1):
            p.add('wood', boxb(x + sx * 0.03, x + sx * 1.25, 0, 3.2, 0.0, 0.08))
            for k in range(1, 4):
                xx = x + sx * (0.03 + k * 0.3)
                p.add('dark', boxb(xx - 0.012, xx + 0.012, 0.1, 3.1, 0.08, 0.09))
            p.add('brass', boxb(x + sx * 0.15 - 0.04, x + sx * 0.15 + 0.04, 1.3, 1.8, 0.08, 0.13),
                  boxb(x + sx * 1.25 - 0.3, x + sx * 1.25 - 0.05, 0.5, 0.58, 0.08, 0.11),
                  boxb(x + sx * 1.25 - 0.3, x + sx * 1.25 - 0.05, 2.6, 2.68, 0.08, 0.11))
        p.add('graphite', boxb(x - 1.45, x - 1.25, 0, 3.5, 0, 0.22), boxb(x + 1.25, x + 1.45, 0, 3.5, 0, 0.22),
              boxb(x - 1.55, x + 1.55, 3.2, 3.55, 0, 0.26))
        p.add('brass', boxb(x - 1.5, x - 1.2, 0, 0.25, 0, 0.26), boxb(x + 1.2, x + 1.5, 0, 0.25, 0, 0.26),
              boxb(x - 0.35, x + 0.35, 3.25, 3.5, 0.2, 0.3))
    for x0, x1, y, kind, *dep in spec.get('awnings', ()):
        out = dep[0] if dep else (1.2 if kind == 'hard' else 1.4)     # 5 つ目は奥行き（路地では短く）
        if simple:
            _awning_simple(p, x0, x1, y, kind, out)
        else:
            aw = P.awning(kind, x1 - x0, out, 0.45)
            p.place(aw, ((x0 + x1) / 2, y, 0.01))
    for x, y in spec.get('lanterns', ()):
        (_lamp_simple(p, x, y, 0.42) if simple else P.lantern(p, x, y, 0.42, 1.0))
        p.add('graphite', beam((x, y + 0.42, 0.0), (x, y + 0.42, 0.42), 0.05))
        p.add('brass', cyl((x, y + 0.42 - 0.04, 0.42), (x, y + 0.26, 0.42), 0.012, 5))
    for x0, x1, y in spec.get('balconies', ()):
        _balcony(p, x0, x1, y)
    for x in spec.get('pipes', ()):
        P.pipe_run(p, (x, 0.1, 0.18), (x, h - 0.2, 0.18), 0.09, 1.2)
        for y in np.arange(0.8, h - 0.4, 1.6):
            p.add('graphite', boxb(x - 0.04, x + 0.04, y - 0.05, y + 0.05, 0, 0.18))
    if spec.get('ladder'):
        x, lh = spec['ladder']
        p.place(P.ladder(lh), (x, 0, 0.12))
    for x, y in spec.get('vents', ()):
        p.add('graphite', boxb(x - 0.32, x + 0.32, y - 0.22, y + 0.22, 0, 0.06))
        for k in range(4):
            yy = y - 0.15 + k * 0.1
            p.add('dark', boxb(x - 0.26, x + 0.26, yy - 0.025, yy + 0.025, 0.06, 0.07))
    return p


# 面の向き → (yaw, 面に沿った x の向き)。'-z' は広場に向いた正面
YAW = {'-z': 180.0, '+z': 0.0, '+x': 90.0, '-x': -90.0}


def face(p: Part, normal: str, at, spec: dict, w: float, h: float):
    """面の飾りを、面の中心の下の点 at（ワールド）に、normal の向きで付ける"""
    if spec:
        p.place(_face(spec, w, h), at, YAW[normal])


# ---------------------------------------------------------------- 家（ワールドの座標の箱）

def house(p: Part, x0, x1, y0, top, zf, zb=BACK, base=None, front=None, left=None, right=None, roof='parapet',
          left_open=True, right_open=True):
    """家の箱：x0〜x1、y0〜top、正面 zf（広場の側、-Z 向き）〜奥 zb。base は見える床の高さ（下の家の屋根・通路）。
    front / left（x0 の面）/ right（x1 の面）は面の飾り（_face の spec）。roof：'parapet'（白磁の低い壁と笠木）・
    'rail'（前の縁に手すり。屋根が通路）・None。left_open / right_open：その側面が見えるか（付け柱・帯を付ける）"""
    base = y0 if base is None else base
    w, h = x1 - x0, top - base
    cx = (x0 + x1) / 2
    p.add('shell', boxb(x0, x1, y0, top, zf, zb))
    # 木の帯（足元）・黒鉛の角の柱・上の帯（正面と見える側面）
    p.add('wood', boxb(x0 - 0.03, x1 + 0.03, base, base + 0.4, zf - 0.03, zb))
    for x in (x0, x1):
        p.add('graphite', boxb(x - 0.08, x + 0.08, base, top, zf - 0.07, zf + 0.09))
        p.add('brass', boxb(x - 0.11, x + 0.11, base + 0.06, base + 0.28, zf - 0.1, zf + 0.12),
              boxb(x - 0.11, x + 0.11, top - 0.42, top - 0.2, zf - 0.1, zf + 0.12))
    p.add('graphite', boxb(x0 - 0.05, x1 + 0.05, top - 0.14, top, zf - 0.09, zf + 0.2))
    for x, op in ((x0, left_open), (x1, right_open)):
        if op:
            p.add('graphite', boxb(x - 0.05, x + 0.05, top - 0.14, top, zf, zb))
    if roof == 'parapet':
        p.add('ivory2', boxb(x0, x1, top, top + 0.45, zf, zf + 0.16))
        p.add('graphite', boxb(x0 - 0.03, x1 + 0.03, top + 0.45, top + 0.51, zf - 0.03, zf + 0.19))
        for x, s in ((x0, 1), (x1, -1)):
            p.add('ivory2', boxb(min(x, x + s * 0.16), max(x, x + s * 0.16), top, top + 0.45, zf + 0.16, zb))
            p.add('graphite', boxb(min(x, x + s * 0.16) - 0.03, max(x, x + s * 0.16) + 0.03, top + 0.45, top + 0.51, zf + 0.16, zb))
    elif roof == 'rail':
        _rail(p, (x0 + 0.12, zf + 0.18), (x1 - 0.12, zf + 0.18), top)
    if front:
        face(p, '-z', (cx, base, zf), front, w, h)
    if left:
        face(p, '-x', (x0, base, (zf + min(zb, zf + 14)) / 2), left, min(zb - zf, 14), h)
    if right:
        face(p, '+x', (x1, base, (zf + min(zb, zf + 14)) / 2), right, min(zb - zf, 14), h)


# ---------------------------------------------------------------- 正面の飾りを選ぶ

def front_spec(rng, w, h, tier):
    """家の正面の飾りを決める（扉・窓・日よけ・灯・バルコニー・配管）"""
    s: dict = {'windows': [], 'awnings': [], 'lanterns': [], 'balconies': [], 'pipes': [], 'simple': True}
    hw = w / 2
    door = None
    if tier < 3 and rng.random() < (0.75 if tier == 1 else 0.6):
        door = float(rng.uniform(-hw + 0.9, hw - 0.9)) if w > 2.4 else 0.0
        s['door'] = door
        if rng.random() < 0.6:
            s['lanterns'].append((door + (0.85 if rng.random() < 0.5 else -0.85), 1.9))
    # 下の列の窓（扉を避ける）
    xs = np.arange(-hw + 0.85, hw - 0.6, 1.55)
    xs = xs + (hw - 0.85 - xs[-1]) / 2 if len(xs) else xs
    lower = [float(x) for x in xs if door is None or abs(x - door) > 1.2]
    if tier == 3:
        lower = lower[::2] or lower
    for x in lower:
        s['windows'].append((x, 1.05))
    # 上の列の窓（背の高い家）
    if h >= 4.0 and rng.random() < 0.55:
        up = [float(x) for x in xs][1::2] or [0.0]
        for x in up:
            s['windows'].append((x, 2.75))
        if rng.random() < 0.35 and w > 3.0:
            x = up[0]
            s['balconies'].append((x - 0.75, x + 0.75, 2.6))
    # 日よけ：扉の上（固い）か窓の上（柔らかい）
    if door is not None and rng.random() < 0.6:
        s['awnings'].append((door - 0.9, door + 0.9, 2.35, 'hard'))
    elif lower and rng.random() < 0.55:
        a, b = min(lower), max(lower)
        if b - a < 0.5:
            a, b = a - 0.6, b + 0.6
        s['awnings'].append((a - 0.5, b + 0.5, 2.05, 'soft'))
    if w > 3.5 and rng.random() < 0.3:
        s['pipes'].append(float(hw - 0.35) * (1 if rng.random() < 0.5 else -1))
    return s


def side_spec(rng, length, h, ys=(1.05,), every=3.2, door_at=None, posts=True):
    """側面（妻・路地の面）の飾り：付け柱、窓の列、扉"""
    s: dict = {'windows': [], 'posts': [], 'pipes': [], 'simple': True}
    hl = length / 2
    if posts:
        n = max(1, int(round(length / 4.0)))
        s['posts'] = [float(-hl + 0.15 + k * (length - 0.3) / n) for k in range(n + 1)]
    for y in ys:
        for x in np.arange(-hl + 1.6, hl - 1.0, every):
            if door_at is None or abs(x - door_at) > 1.2:
                s['windows'].append((float(x), y))
    if door_at is not None:
        s['door'] = door_at
    if length > 6 and rng.random() < 0.5:
        s['pipes'].append(float(rng.uniform(-hl + 1.0, hl - 1.0)))
    return s


# ---------------------------------------------------------------- 屋根の上の物

def canopy(p: Part, x0, x1, z0, z1, y, hgt=2.2, mat='cloth'):
    """4 本の柱と帆布の日よけ"""
    for x in (x0, x1):
        for z in (z0, z1):
            p.add('graphite', boxb(x - 0.06, x + 0.06, y, y + hgt, z - 0.06, z + 0.06))
            p.add('brass', boxb(x - 0.09, x + 0.09, y, y + 0.12, z - 0.09, z + 0.09))
    p.add(mat, sheet(lambda u, v: (x0 - 0.15 + (x1 - x0 + 0.3) * u, y + hgt - 0.25 * math.sin(math.pi * u) * math.sin(math.pi * v),
                                   z0 - 0.15 + (z1 - z0 + 0.3) * v), 4, 4, 0.03))


def roof_items(p: Part, rng, x0, x1, y, z0, z1, tier):
    """屋根の上：給水塔・日よけ・煙突・鉢植え・木箱・電線柱（段ごとに選ぶ）。z0〜z1 は見える屋根の奥行き"""
    w = x1 - x0
    if z1 - z0 < 1.2 or w < 1.6:
        return
    r = rng.random()
    if tier >= 2 and r < 0.3 and w > 2.6:
        p.place(P.water_tower(), (float(rng.uniform(x0 + 1.2, x1 - 1.2)), y, min(z1 - 1.2, z0 + 2.6)), 0, 1.25 if tier == 3 else 1.1)
    elif tier >= 2 and r < 0.55 and w > 3.0:
        a = float(rng.uniform(x0 + 0.4, x1 - 3.0))
        canopy(p, a, a + 2.6, z0 + 0.6, min(z1 - 0.4, z0 + 3.0), y, 2.1, 'cloth' if rng.random() < 0.6 else 'cloth2')
    elif r < 0.75:
        for k in range(int(rng.integers(1, 3))):
            x = float(rng.uniform(x0 + 0.5, x1 - 0.5))
            hh = float(rng.uniform(1.2, 2.6)) * (1.5 if tier == 3 else 1.0)
            zc = z0 + float(rng.uniform(0.8, min(2.4, z1 - z0 - 0.4)))
            P.pipe_run(p, (x, y, zc), (x, y + hh, zc), 0.16, 1.0)
            p.add('brass', lathe((x, y + hh, zc), (x, y + hh + 0.35, zc), [(0, 0.2), (1, 0.07)], 8))
    if tier < 3 and rng.random() < 0.6:
        pot(p, float(rng.uniform(x0 + 0.5, x1 - 0.5)), y, z0 + 0.55)
    if rng.random() < 0.35:
        p.place(P.crate(), (float(rng.uniform(x0 + 0.6, x1 - 0.6)), y, z0 + 0.9), float(rng.uniform(-20, 20)), 0.75)
    if tier == 3 and rng.random() < 0.3:
        p.place(P.power_pole(3.6), (float(rng.uniform(x0 + 0.5, x1 - 0.5)), y, z0 + 1.0))


# ---------------------------------------------------------------- 並び（段ごとの家の幅・高さ・正面）

def row(rng, a, b, widths, tops, fronts):
    """|x| a〜b を家で埋める。幅は widths から、隣どうしの屋根と正面は少し変える（同じ高さ・同じ面がちらつかないように）"""
    out = []
    x = a
    prev_top, prev_front = None, None
    while x < b - 0.01:
        wdt = float(rng.choice(widths))
        if b - (x + wdt) < 2.4:
            wdt = b - x
        top = float(rng.choice(tops))
        while prev_top is not None and abs(top - prev_top) < 0.18:
            top = float(rng.choice(tops))
        fr = float(rng.choice(fronts))
        while prev_front is not None and abs(fr - prev_front) < 0.2:
            fr = float(rng.choice(fronts))
        out.append([x, x + wdt, top, fr])
        prev_top, prev_front = top, fr
        x += wdt
    return out


def _ax(s, a, b):
    """|x| の範囲 a〜b を、その側（s = -1 西 / +1 東）のワールドの x0 < x1 にする"""
    return (min(s * a, s * b), max(s * a, s * b))


def terrace_side(s: int) -> Part:
    """北の段々の片側（s = -1 西 / +1 東）"""
    name = 'terrace_west' if s < 0 else 'terrace_east'
    p = Part(name)
    rng = np.random.default_rng(71 if s < 0 else 73)
    inner = '+x' if s < 0 else '-x'     # 路地へ向く面
    outer = '-x' if s < 0 else '+x'     # 広場の端（外）へ向く面

    # --- 段 0：擁壁の塊。前の部分（z 16〜17.5）は端 48 まで、奥は 46.5 まで。端は広場の床の下 -7 m まで
    x0, x1 = _ax(s, TOWER, END)
    p.add('shell', boxb(x0, x1, -7.0, 5.0, WALL_Z, 17.5))
    x0, x1 = _ax(s, TOWER, END1)
    p.add('shell', boxb(x0, x1, -7.0, 5.0, 17.5, BACK))
    # 擁壁の正面の飾り（前の terrace_a〜d の下の段と同じ組み合わせ）。8 m ごと、|x| 8〜48
    kinds = ['a', 'd', 'c', 'b', 'a'] if s < 0 else ['b', 'c', 'a', 'd', 'b']
    for k, ax in enumerate((12, 20, 28, 36, 44)):
        v = kinds[k]
        bay = Part('bay')
        _retaining(bay, 8.0, 5.0, door_at={'a': -1.0, 'b': None, 'c': 2.0, 'd': None}[v],
                   pipes=v in ('b', 'd'), ladder_at={'a': None, 'b': 2.5, 'c': None, 'd': None}[v])
        if v == 'a':
            bay.place(P.awning('soft', 2.2, 1.4, 0.4), (-1.0, 2.6, 0.06))
            P.lantern(bay, 0.4, 2.3, 0.32, 1.0)
            bay.add('graphite', beam((0.4, 2.62, 0.0), (0.4, 2.62, 0.32), 0.05))
        if v == 'c':
            bay.place(P.canvas_roll(), (-1.5, 3.4, 0.06))
        p.place(bay, (s * ax, 0, WALL_Z), 180)
    # 5 m の通路の縁：黒鉛の梁・白磁の笠木・手すりと灯
    x0, x1 = _ax(s, TOWER, END)
    p.add('graphite', boxb(x0, x1, 4.6, 5.0, WALL_Z - 0.4, WALL_Z))
    p.add('ivory2', boxb(x0, x1, 5.0, 5.05, WALL_Z - 0.38, WALL_Z + 0.3))
    for x in np.arange(x0 + 1.0, x1, 2.0):
        p.add('graphite', boxb(x - 0.08, x + 0.08, 4.35, 4.6, WALL_Z - 0.3, WALL_Z))
    _rail(p, (x0 + 0.1, WALL_Z + 0.12), (x1 - 0.1, WALL_Z + 0.12), 5.05)
    # 端の前の部分（z 16〜17.5）の外の縁にも手すり
    ex = s * END
    _rail(p, (ex - s * 0.12, WALL_Z + 0.12), (ex - s * 0.12, 17.38), 5.05, lamps=0)
    _rail(p, (ex - s * 0.12, 17.38), (s * (END1 + 0.1), 17.38), 5.05, lamps=0)
    # 妻（端）の面：擁壁の板（-7〜5 m）
    bay = Part('end')
    _retaining_light(bay, BACK - 17.5, 12.0)
    P.pipe_run(bay, (-(BACK - 17.5) / 2, 9.75, 0.3), ((BACK - 17.5) / 2 - 9.0, 9.75, 0.3), 0.13, 2.0)
    p.place(bay, (s * END1, -7.0, (17.5 + BACK) / 2), YAW[outer])
    bay = Part('end2')
    _retaining_light(bay, 1.5, 12.0)
    p.place(bay, (s * END, -7.0, WALL_Z + 0.75), YAW[outer])

    # --- 角の棟（階段の口の両側、|x| 4〜8、高さ 9 m、z 16〜奥）
    x0, x1 = _ax(s, ALLEY, TOWER)
    p.add('shell', boxb(x0, x1, 0.0, TOWER_TOP, WALL_Z, BACK))
    p.add('wood', boxb(x0, x1, 0.0, 0.4, WALL_Z - 0.03, WALL_Z + 0.1))
    for x in (x0, x1):
        p.add('graphite', boxb(x - 0.09, x + 0.09, 0, TOWER_TOP, WALL_Z - 0.08, WALL_Z + 0.1))
    p.add('graphite', boxb(x0 - 0.04, x1 + 0.04, TOWER_TOP - 0.16, TOWER_TOP, WALL_Z - 0.1, WALL_Z + 0.05))
    # 広場に向いた正面：下に扉、上に 2 列の窓・小さな日よけ
    face(p, '-z', ((x0 + x1) / 2, 0, WALL_Z), {
        'door': 0.6 * s, 'windows': [(-0.9 * s, 1.3), (-1.0, 5.9), (1.0, 5.9), (0.0, 7.6)],
        'awnings': [(0.6 * s - 0.8, 0.6 * s + 0.8, 2.3, 'hard')], 'lanterns': [(-0.5 * s, 1.95)],
        'bands': [5.0]}, 4.0, TOWER_TOP)
    # 外（通路の側）の面：通路から上（z 16〜18.5 が見える）
    face(p, outer, (s * TOWER, 5.0, 17.2), {'windows': [(0.0, 1.2)]}, 2.4, 4.0)
    # 路地の面（|x| = 4）：階段に沿って窓、踊り場（z 28〜34、5 m）に扉と日よけ、付け柱
    alley = {'posts': [], 'windows': [], 'pipes': [], 'lanterns': [], 'awnings': [], 'bands': [5.0]}
    # 面の座標の x：西の面（+x 向き、yaw 90）は面の x が -z へ向くので zc - z、東の面（-x 向き）は z - zc
    zc = (WALL_Z + GATE_Z) / 2
    loc = (lambda z: zc - z) if s < 0 else (lambda z: z - zc)
    for z in np.arange(WALL_Z + 0.15, GATE_Z, 4.4):
        alley['posts'].append(loc(float(z)))
    alley['posts'].append(loc(GATE_Z - 0.15))
    for z in (19.4, 24.8):
        floor = 5.0 * (z - WALL_Z) / 12.0
        alley['windows'].append((loc(z), floor + 1.7))
    door_z = 31.6 if s < 0 else 30.4
    for z in (21.8, 27.2, 29.4 if s < 0 else 33.0):
        alley['windows'].append((loc(z), 6.9))
    alley['door'] = loc(door_z)
    alley['awnings'].append((loc(door_z) - 0.9, loc(door_z) + 0.9, 7.35, 'hard', 0.8))   # 踊り場の上でカメラに近いので浅く
    alley['lanterns'].append((loc(door_z - 1.1 * (1 if s < 0 else -1)), 6.95))
    alley['pipes'].append(loc(17.0))
    face(p, inner, (s * ALLEY, 0, zc), alley, GATE_Z - WALL_Z, TOWER_TOP)
    # 角の棟の屋根：路地の側の縁と正面の縁に手すり、外の端に鉢植えと木箱（路地の上は空けておく。カメラが通る）
    _rail(p, (s * (ALLEY + 0.15), WALL_Z + 0.15), (s * (ALLEY + 0.15), GATE_Z - 0.2), TOWER_TOP, lamps=4.0)
    _rail(p, (s * (ALLEY + 0.15), WALL_Z + 0.15), (s * (TOWER - 0.1), WALL_Z + 0.15), TOWER_TOP, lamps=0)
    pot(p, s * (TOWER - 0.6), TOWER_TOP, WALL_Z + 0.7)
    p.place(P.crate(), (s * (TOWER - 0.7), TOWER_TOP, WALL_Z + 2.0), 15, 0.75)

    # --- 段 1：5 m の通路の奥の家（|x| 8〜46.5）。屋根は通路（前の縁に手すり）
    r1 = row(rng, TOWER, END1, [4.0, 4.5, 5.0, 5.5, 6.0], [9.25, 9.45, 9.65], [18.3, 18.6, 18.9])
    r1[0][2] = 8.85                              # 角の棟の隣は棟より低く（棟の横の面が浮かないように）
    for i, (a, b, top, fr) in enumerate(r1):
        x0, x1 = _ax(s, a, b)
        sp = front_spec(rng, b - a, top - 5.0, 1)
        last = i == len(r1) - 1
        ends = {}
        if last:
            ends = {('left' if s < 0 else 'right'): side_spec(rng, min(BACK - fr, 14), top - 5.0, ys=(1.05, 2.8), every=3.0)}
        house(p, x0, x1, 5.0, top, fr, base=5.0, front=sp, roof='rail', **ends)
    # 段 1 の前の通路の上の物
    for a, b, top, fr in r1:
        x0, x1 = _ax(s, a, b)
        if rng.random() < 0.45:
            pot(p, (x0 + x1) / 2 + float(rng.uniform(-1, 1)), 5.05, WALL_Z + 0.75)
        elif rng.random() < 0.35:
            p.place(P.barrel(), ((x0 + x1) / 2 + float(rng.uniform(-1.2, 1.2)), 5.05, fr - 0.6), 0, 0.8)
    # 段 1 の屋根の通路へのはしご（いくつか）
    for i in (2, 5):
        if i < len(r1):
            a, b, top, fr = r1[i]
            x = s * (b - 0.45)
            p.place(P.ladder(top - 5.0), (x, 5.05, fr - 0.12), 180)

    # --- 段 2：z≈22（|x| 8〜45.5）。床は段 1 の屋根（下に沈めて隙間を作らない）
    r2 = row(rng, TOWER, END1 - 1.0, [5.0, 5.5, 6.0, 6.5, 7.0], [13.5, 13.8, 14.1, 14.4], [21.8, 22.1, 22.4, 22.7])
    tops1 = lambda a, b: max(t for (aa, bb, t, f) in r1 if bb > a + 0.01 and aa < b - 0.01)  # noqa: E731
    for i, (a, b, top, fr) in enumerate(r2):
        x0, x1 = _ax(s, a, b)
        base = tops1(a, b)
        sp = front_spec(rng, b - a, top - base, 2)
        sides = {}
        if i == 0:     # 路地の側（|x| = 8）：段 1 の角の棟の屋根より上が見える
            sides[('right' if s < 0 else 'left')] = side_spec(rng, min(BACK - fr, 14), top - TOWER_TOP, ys=(1.4,), every=3.4)
        if i == len(r2) - 1:
            sides[('left' if s < 0 else 'right')] = side_spec(rng, min(BACK - fr, 14), top - base, ys=(1.05,), every=3.2)
        house(p, x0, x1, 8.5, top, fr, base=base, front=sp, roof='parapet', **sides)
        roof_items(p, rng, x0 + 0.3, x1 - 0.3, top, fr + 0.3, fr + 4.0, 2)

    # --- 段 3：z≈27（|x| 8.6〜44.5）。町の空の線
    r3 = row(rng, TOWER + 0.6, END1 - 2.0, [5.5, 6.5, 7.5, 8.0], [16.9, 17.3, 17.7, 18.1], [26.6, 27.0, 27.4])
    tops2 = lambda a, b: min(t for (aa, bb, t, f) in r2 if bb > a + 0.01 and aa < b - 0.01)  # noqa: E731
    for i, (a, b, top, fr) in enumerate(r3):
        x0, x1 = _ax(s, a, b)
        base = tops2(a, b)
        sp = front_spec(rng, b - a, top - base, 3)
        sides = {}
        if i == 0:
            sides[('right' if s < 0 else 'left')] = side_spec(rng, min(BACK - fr, 12), top - base, ys=(1.05,), every=3.6)
        if i == len(r3) - 1:
            sides[('left' if s < 0 else 'right')] = side_spec(rng, min(BACK - fr, 12), top - base, ys=(1.05,), every=3.6)
        house(p, x0, x1, 13.0, top, fr, base=base, front=sp, roof='parapet', **sides)
        roof_items(p, rng, x0 + 0.3, x1 - 0.3, top, fr + 0.3, fr + 5.0, 3)
    return p


# ---------------------------------------------------------------- 路地の奥の門の棟と、その上の橋の棟

def stair_gate() -> Part:
    """北の階段の奥（z=34）の門の棟：踊り場（5 m）に両開きの大きな扉、上に窓。下は |x| 4 の間、9 m より上は |x| 8 まで広がる。
    その上（12 m〜、z 37〜）に段 3 の高さの橋の棟（路地の上をまたぐ）"""
    p = Part('stair_gate')
    p.add('shell', boxb(-ALLEY, ALLEY, 0.0, TOWER_TOP, GATE_Z, BACK), boxb(-TOWER, TOWER, TOWER_TOP, GATE_TOP, GATE_Z, BACK))
    face(p, '-z', (0, 5.0, GATE_Z), {
        'door2': 0.0, 'lanterns': [(-1.9, 2.3), (1.9, 2.3)], 'posts': [-3.85, 3.85],
        'windows': [(-3.0, 2.6), (3.0, 2.6)]}, 8.0, TOWER_TOP - 5.0)
    # 扉の上の飾り板（真鍮の縁・赤い面）
    p.add('graphite', boxb(-1.3, 1.3, 8.75, 9.55, GATE_Z - 0.12, GATE_Z))
    p.add('cloth', boxb(-1.15, 1.15, 8.85, 9.45, GATE_Z - 0.15, GATE_Z - 0.1))
    p.add('brass', boxb(-1.35, 1.35, 9.55, 9.65, GATE_Z - 0.16, GATE_Z), boxb(-1.35, 1.35, 8.65, 8.75, GATE_Z - 0.16, GATE_Z))
    # 9〜12 m：|x| 8 まで広い階。正面に窓の列と帯、上に笠木
    face(p, '-z', (0, TOWER_TOP, GATE_Z), {
        'simple': True, 'windows': [(-6.2, 0.95), (-3.2, 0.95), (3.2, 0.95), (6.2, 0.95)], 'posts': [-7.85, -1.6, 1.6, 7.85],
        'bands': [0.0]}, 16.0, GATE_TOP - TOWER_TOP)
    p.add('graphite', boxb(-TOWER - 0.05, TOWER + 0.05, GATE_TOP - 0.14, GATE_TOP, GATE_Z - 0.1, GATE_Z + 0.1))
    p.add('ivory2', boxb(-TOWER, TOWER, GATE_TOP, GATE_TOP + 0.45, GATE_Z, GATE_Z + 0.16))
    p.add('graphite', boxb(-TOWER - 0.03, TOWER + 0.03, GATE_TOP + 0.45, GATE_TOP + 0.51, GATE_Z - 0.03, GATE_Z + 0.19))
    # 橋の棟（12 m〜16.4 m、z 37〜）
    rng = np.random.default_rng(5)
    house(p, -TOWER - 0.6, TOWER + 0.6, GATE_TOP, 16.4, 37.0, base=GATE_TOP, roof='parapet', left_open=False, right_open=False,
          front={'simple': True, 'windows': [(-6.5, 1.05), (-4.0, 1.05), (-1.3, 1.05), (1.3, 1.05), (4.0, 1.05), (6.5, 1.05)],
                 'awnings': [(-2.2, 2.2, 2.25, 'soft')], 'balconies': [(-5.3, -2.7, 2.6)], 'posts': [-2.9, 2.9]})
    p.place(P.water_tower(), (-3.0, 16.4, 39.0), 0, 1.3)
    canopy(p, 1.5, 5.0, 37.6, 39.6, 16.4, 2.2, 'cloth2')
    roof_items(p, rng, -8.0, -5.2, GATE_TOP, GATE_Z + 0.4, 36.6, 2)
    return p


PARTS = {'terrace_west': lambda: terrace_side(-1), 'terrace_east': lambda: terrace_side(1), 'stair_gate': stair_gate}


# ---------------------------------------------------------------- 箱の建物（どの向きの面にも飾りを付けられる）

def ring(p: Part, x0, x1, z0, z1, y, sides='nsew', h=0.45, t=0.16):
    """屋上の縁の白磁の低い壁と黒鉛の笠木。sides：'s'（-z の辺）'n'（+z）'w'（-x）'e'（+x）。角で重ならないように切る"""
    if 's' in sides:
        p.add('ivory2', boxb(x0, x1, y, y + h, z0, z0 + t))
        p.add('graphite', boxb(x0 - 0.03, x1 + 0.03, y + h, y + h + 0.06, z0 - 0.03, z0 + t + 0.03))
    if 'n' in sides:
        p.add('ivory2', boxb(x0, x1, y, y + h, z1 - t, z1))
        p.add('graphite', boxb(x0 - 0.03, x1 + 0.03, y + h, y + h + 0.06, z1 - t - 0.03, z1 + 0.03))
    za = z0 + (t + 0.03 if 's' in sides else 0.0)
    zb = z1 - (t + 0.03 if 'n' in sides else 0.0)
    if 'w' in sides:
        p.add('ivory2', boxb(x0, x0 + t, y, y + h, za, zb))
        p.add('graphite', boxb(x0 - 0.03, x0 + t + 0.03, y + h, y + h + 0.06, za, zb))
    if 'e' in sides:
        p.add('ivory2', boxb(x1 - t, x1, y, y + h, za, zb))
        p.add('graphite', boxb(x1 - t - 0.03, x1 + 0.03, y + h, y + h + 0.06, za, zb))


def block(p: Part, x0, x1, y0, top, z0, z1, faces: dict, base=None, roof='nsew'):
    """箱の建物（ワールドの座標）。faces：見える面の向き（'-z' '+z' '-x' '+x'）→ 面の飾り（_face の spec）。
    見える面には足元の木の帯と上の黒鉛の帯を付ける。roof：屋上の縁の壁の辺（ring の sides）"""
    base0 = y0 if base is None else base
    p.add('shell', boxb(x0, x1, y0, top, z0, z1))
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    for n, spec in faces.items():
        spec = dict(spec)
        base = spec.pop('_base', base0)       # その面の見える床（手前の低い棟の屋根など）
        h = top - base
        if n in ('-z', '+z'):
            z = z0 if n == '-z' else z1
            o = -1 if n == '-z' else 1
            p.add('wood', boxb(x0, x1, base, base + 0.4, min(z, z + o * 0.03), max(z, z + o * 0.03)))
            p.add('graphite', boxb(x0, x1, top - 0.14, top, min(z, z + o * 0.1), max(z, z + o * 0.1)))
            face(p, n, (cx, base, z), spec, x1 - x0, h)
        else:
            x = x0 if n == '-x' else x1
            o = -1 if n == '-x' else 1
            p.add('wood', boxb(min(x, x + o * 0.03), max(x, x + o * 0.03), base, base + 0.4, z0, z1))
            p.add('graphite', boxb(min(x, x + o * 0.1), max(x, x + o * 0.1), top - 0.14, top, z0, z1))
            face(p, n, (x, base, cz), spec, z1 - z0, h)
    if roof:
        ring(p, x0, x1, z0, z1, top, roof)


def ends(w, more=()):
    """面の両端の付け柱（面の座標）"""
    return [-w / 2 + 0.12, w / 2 - 0.12, *more]


# ---------------------------------------------------------------- 南の階段（下の段へ）の両側の棟と奥の棟

# 南の階段のまわりの棟の屋根。どれも当たり判定が無い（部屋の geometry を足さない）ので、プレイヤーが届く縁
# （胸壁の上 1.2 m・階段の横の壁の上 3.0 m・奥の壁の上 4.0 m）より 2.5 m 以上低くして、縁の向こうの下の町に見せる。
# 前は手前の棟の屋根（1.0 m）が胸壁のすぐ横、奥の棟の屋根（3.0 m）が横の壁の上と同じ高さで、歩いて乗ると落ちた
SW_FRONT_TOP = -2.0     # 手前の平屋（胸壁の上から 3.2 m 下。屋上の小さな庭）
SW_BACK_TOP = 0.5       # 奥の 2 階建て（横の壁の上から 2.5 m 下。跳んでも戻れない深さ）
SW_REAR_TOP = 1.5       # 奥の壁の向こうの棟（奥の壁の上から 2.5 m 下）
SW_WALL_TOP = 3.0       # 階段の横の壁（geometry、|x| 4〜4.5、z -32〜-14）の上
SW_END_TOP = 4.0        # 階段の奥の壁（geometry、z -33〜-32）の上


def stair_well_s() -> Part:
    """南の階段（x -4〜4、z -14〜-32 を 5 m 下る）の両側の棟と奥の棟。前は下の段の床から 8 m の薄い壁が 2 枚立っているだけだった。
    階段の横の壁・奥の壁（geometry）はそのまま見せ、その外側に家を付ける。家の屋根は届く縁より 2.5 m 以上低い（SW_* の説明）。
    家より上に出る横の壁の外の面には付け柱・帯・配管を付け、上に笠木を載せて、厚みのある本当の壁に見せる"""
    p = Part('stair_well_s')
    rng = np.random.default_rng(11)
    for s in (-1, 1):
        out = '+x' if s > 0 else '-x'
        xi, xo = 4.5, 9.5
        x0, x1 = min(s * xi, s * xo), max(s * xi, s * xo)
        # 手前の平屋（下の段の床 -5 m 〜 -2.0 m）：外の面に扉・窓・日よけ・灯
        block(p, x0, x1, -5.3, SW_FRONT_TOP, -21.0, -15.0, {
            out: {'simple': True, 'posts': ends(6.0), 'door': 1.2 * s, 'windows': [(-1.4 * s, 1.05)],
                  'awnings': [(1.2 * s - 0.9, 1.2 * s + 0.9, 2.35, 'hard')], 'lanterns': [(0.25 * s, 1.95)]}},
              base=-5.0, roof=('e' if s > 0 else 'w'))
        # 屋上の小さな庭（鉢植え・木箱）。胸壁の手すりの向こう、3 m 下に見える
        pot(p, s * 8.6, SW_FRONT_TOP, -16.0)
        pot(p, s * 8.6, SW_FRONT_TOP, -19.6)
        p.place(P.crate(), (s * 6.4, SW_FRONT_TOP, -20.2), 10 * s, 0.7)
        # 奥の 2 階建て（-5 〜 0.5 m）：外の面に 2 列の窓、北の面（手前の平屋の屋上から上）に屋上へ出る扉
        block(p, x0, x1, -5.3, SW_BACK_TOP, -33.0, -21.0, {
            out: {'simple': True, 'posts': ends(12.0, [0.0]), 'door': -3.0 * s, 'windows': [(-4.6, 1.05), (-1.4 * s, 1.05), (2.2, 1.05), (4.4, 1.05),
                                                                         (-4.4, 3.65), (-1.8, 3.65), (1.8, 3.65), (4.4, 3.65)],
                  'awnings': [(-3.0 * s - 0.9, -3.0 * s + 0.9, 2.35, 'hard'), (1.4, 5.0, 2.05, 'soft')],
                  'balconies': [(-2.6, -1.0, 3.45)], 'lanterns': [(-3.0 * s + 0.9 * s, 1.95)], 'bands': [2.85], 'pipes': [5.6 * s]},
            '+z': {'_base': SW_FRONT_TOP, 'door': 0.6 * s, 'windows': [(-1.3 * s, 0.75)], 'lanterns': [(-0.3 * s, 1.45)]}},
              base=-5.0, roof=('n' + ('e' if s > 0 else 'w')))
        roof_items(p, rng, min(s * 6.4, s * 9.2), max(s * 6.4, s * 9.2), SW_BACK_TOP, -32.4, -24.0, 2)
        # 家より上に出る横の壁の外の面（x = ±4.5）：付け柱・帯・配管。手前（z -21〜-15）は -2.0 から、奥は 0.5 から
        for z0, z1, base in ((-21.0, -15.0, SW_FRONT_TOP), (-32.0, -21.0, SW_BACK_TOP)):
            L, h = z1 - z0, SW_WALL_TOP - base
            sp = {'posts': ends(L, [0.0] if L > 8 else []), 'bands': [h - 0.9]}
            if L < 8:
                sp['pipes'] = [-1.2 * s]
            face(p, out, (s * xi, base, (z0 + z1) / 2), sp, L, h)
    # 奥の棟（階段の奥の壁の向こう、-5 〜 1.5 m）
    block(p, -9.5, 9.5, -5.3, SW_REAR_TOP, -40.0, -33.0, {
        '+x': {'simple': True, 'posts': ends(7.0), 'windows': [(-1.6, 1.05), (1.6, 1.05), (-1.6, 3.9), (1.6, 3.9)], 'bands': [3.3]},
        '-x': {'simple': True, 'posts': ends(7.0), 'windows': [(-1.6, 1.05), (1.6, 1.05), (-1.6, 3.9), (1.6, 3.9)], 'bands': [3.3]},
        '+z': {'_base': SW_BACK_TOP}}, base=-5.0)
    p.place(P.water_tower(), (-6.5, SW_REAR_TOP, -37.5), 0, 1.2)
    canopy(p, 2.0, 5.6, -38.6, -35.0, SW_REAR_TOP, 2.2, 'cloth')
    # 奥の壁の、奥の棟の屋根より上に出る面（z = -33、南向き）：付け柱と帯
    face(p, '-z', (0.0, SW_REAR_TOP, -33.0), {'posts': ends(9.0, [0.0]), 'bands': [SW_END_TOP - SW_REAR_TOP - 0.8]}, 9.0, SW_END_TOP - SW_REAR_TOP)
    # 階段の横の壁・奥の壁の上の笠木（geometry の壁の上の面）
    for s in (-1, 1):
        p.add('graphite', boxb(min(s * 3.94, s * 4.56), max(s * 3.94, s * 4.56), SW_WALL_TOP, SW_WALL_TOP + 0.1, -32.0, -14.0))
        p.add('brass', boxb(min(s * 3.92, s * 4.58), max(s * 3.92, s * 4.58), SW_WALL_TOP - 0.1, SW_WALL_TOP, -14.06, -13.94))
    p.add('graphite', boxb(-4.56, 4.56, SW_END_TOP, SW_END_TOP + 0.1, -33.06, -31.94))
    return p


# ---------------------------------------------------------------- 下の段の家並み（胸壁の向こう 4〜40 m に見える）

# 家の (中心 x, 中心 z, 幅, 奥行き, 高さ)（部品の座標。原点 = 下の段の床の中心）
LOWER_HOUSES = {
    'a': [(-3.5, -1.0, 3.0, 4.0, 3.2), (0.5, -0.5, 4.0, 5.0, 4.6), (3.8, 1.5, 2.6, 3.4, 2.8), (-1.5, 2.8, 3.4, 2.2, 2.6)],
    'b': [(-3.0, 0.0, 4.0, 5.0, 3.8), (1.5, -1.5, 3.2, 3.2, 3.0), (2.8, 2.0, 3.6, 3.0, 5.2)],
    'c': [(-3.8, 1.0, 2.6, 4.0, 2.9), (-0.6, 0.0, 3.4, 5.6, 4.2), (3.2, -1.2, 3.4, 3.6, 3.4), (2.0, 2.8, 4.0, 2.0, 2.4)],
}


def lower_block(variant='a') -> Part:
    """下の段の家並み（10×8 m ほど）：白磁の絵（shell）の箱の家 3〜4 軒。どの向きの面にも窓（他の家に隠れる所は付けない）、
    1 軒に 1 つの扉と固いひさし（吊り灯は付けない：灯の材質 1 つで描画が 1 回増えるため）、足元の木の帯と上の黒鉛の帯、屋上の縁の低い壁と笠木（前の宙に浮いた手すりの代わり）、
    屋上の日よけ・水槽・煙突。前は平らな灰色の箱に小さな暗い四角だけで、胸壁から 4 m の所では舞台の書き割りに見えた"""
    p = Part(f'lower_block_{variant}')
    rng = np.random.default_rng(10 + ord(variant))
    hs = LOWER_HOUSES[variant]
    boxes = [(cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2, h) for cx, cz, w, d, h in hs]

    def hidden(i, x, y, z):
        """(x, y, z) が i 以外の家の中か"""
        return any(k != i and a - 0.02 < x < b + 0.02 and c - 0.02 < z < e + 0.02 and y < hh
                   for k, (a, b, c, e, hh) in enumerate(boxes))

    for i, (cx, cz, w, d, h) in enumerate(hs):
        x0, x1, z0, z1, _ = boxes[i]
        centre = {'+z': (cx, z1), '-z': (cx, z0), '+x': (x1, cz), '-x': (x0, cz)}
        length = {'+z': w, '-z': w, '+x': d, '-x': d}

        def at(n, u, y, out=0.12):
            """面 n の面の座標 u（face の x の向き）・高さ y の、面のすぐ外のワールドの点"""
            fx, fz = centre[n]
            q = {'+z': (fx + u, fz + out), '-z': (fx - u, fz - out), '+x': (fx + out, fz - u), '-x': (fx - out, fz + u)}[n]
            return q[0], y, q[1]

        def free(n, u, y, half=0.5):
            return not any(hidden(i, *at(n, uu, y)) for uu in (u - half, u, u + half))

        # 見えている長さが一番長い面に扉
        seen = {n: sum(free(n, float(u), 1.0, 0.0) for u in np.arange(-length[n] / 2 + 0.25, length[n] / 2 - 0.2, 0.5)) for n in centre}
        door_n = max(seen, key=lambda n: (seen[n], n == '+z', n == '-z'))
        faces = {}
        for n in ('+z', '-z', '+x', '-x'):
            if not seen[n]:
                continue
            L = length[n]
            sp: dict = {'simple': True, 'far': True, 'windows': [], 'awnings': [], 'lanterns': []}
            door = None
            if n == door_n:
                cand = [float(u) for u in np.arange(-L / 2 + 0.8, L / 2 - 0.75, 0.3) if free(n, float(u), 1.0, 0.65)]
                if cand:
                    door = cand[int(rng.integers(len(cand)))]
                    sp['door'] = door
                    if h >= 2.6:
                        sp['awnings'].append((door - 0.75, door + 0.75, 2.2, 'hard', 0.8))
            rows = [0.95] + ([2.75] if h >= 4.2 else [])
            us = np.arange(-L / 2 + 0.85, L / 2 - 0.6, 1.7)
            us = us + (L / 2 - 0.85 - us[-1]) / 2 if len(us) else us
            for y in rows:
                for u in us:
                    u = float(u)
                    if (door is None or abs(u - door) > 1.15 or y > 2.5) and free(n, u, y + 0.4):
                        sp['windows'].append((u, y))
            faces[n] = sp
        block(p, x0, x1, 0.0, h, z0, z1, faces, base=0.0, roof='nsew')
        # 屋上：日よけ・水槽・煙突のどれか
        r = rng.random()
        if r < 0.45 and w > 2.8 and d > 2.6:
            canopy(p, cx - w * 0.32, cx + w * 0.32, cz - d * 0.3, cz + d * 0.3, h, 1.9, 'cloth' if rng.random() < 0.6 else 'cloth2')
        elif r < 0.8:
            tx, tz = cx + w * 0.18, cz - d * 0.15
            p.add('ivory2', boxb(tx - 0.6, tx + 0.6, h, h + 0.3, tz - 0.6, tz + 0.6))
            p.add('brass', cyl((tx, h + 0.3, tz), (tx, h + 1.4, tz), 0.5, 10))
            p.add('graphite', cyl((tx, h + 1.4, tz), (tx, h + 1.48, tz), 0.53, 10))
        else:
            x = cx - w * 0.25
            P.pipe_run(p, (x, h, cz), (x, h + 1.6, cz), 0.14, 0.8)
            p.add('brass', lathe((x, h + 1.6, cz), (x, h + 1.9, cz), [(0, 0.18), (1, 0.06)], 8))
    return p


PARTS.update({f'lower_block_{v}': (lambda v=v: lower_block(v)) for v in LOWER_HOUSES})


def parapet_corner() -> Part:
    """広場の角の柱（1.3 m 角、上の面 = 低い壁の上 1.2 m、下は -7 m）。南の角（胸壁と東西の低い壁の角）では geometry の壁どうしの
    間の 1 m 角の切れ目と、外の擁壁どうしの角の隙間をふさぐ。北の端（東西の低い壁が段の家の塊に当たる z=16）では壁の端の面をふさぐ。
    原点 = 角の柱の中心の上の面（y 1.2）"""
    p = Part('parapet_corner')
    p.add('shell', boxb(-0.65, 0.65, -8.2, 0.0, -0.65, 0.65))
    p.add('graphite', boxb(-0.7, 0.7, -0.04, 0.04, -0.7, 0.7))
    for y in (-8.0, -5.0, -2.2):
        p.add('brass', boxb(-0.69, 0.69, y, y + 0.22, -0.69, 0.69))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('graphite', boxb(sx * 0.65 - 0.1 * (sx > 0) - 0.06 * (sx < 0), sx * 0.65 + 0.06 * (sx > 0) + 0.1 * (sx < 0),
                                   -8.2, -0.04, sz * 0.65 - 0.1 * (sz > 0) - 0.06 * (sz < 0), sz * 0.65 + 0.06 * (sz > 0) + 0.1 * (sz < 0)))
    return p


PARTS.update({'stair_well_s': stair_well_s, 'parapet_corner': parapet_corner})
