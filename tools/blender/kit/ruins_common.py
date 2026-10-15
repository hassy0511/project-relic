"""遺構の各階層（B1〜B4）で使う、汚れの置き場所の部品（汚れの「しみ」）。部屋の JSON を書く道具（tools/dress_ruins.py）が、
汚れているべき所（管・灯の下、扉のまわり、通り道、部屋の隅）に置く。キットの材質の汚れの層（detail）は面じゅうに同じ割合で散るので、
置き場所を決めたいしみは、この平らな部品で描く（42 の 14.2.1・43 の 2 章）。

どれも当たり判定なし（床・壁から 1〜2 cm の薄い板）。材質の名前（Godot のキットの "materials" で、階層ごとの色に置き換わる）：
  stain_floor … 床のしみ（さび水・油・踏まれた汚れ）。縁のはっきりした平らな斑（汚れの層と同じ画風）
  stain_rust  … 壁を垂れるさびの筋
  stain_soot  … すす・焦げ（B3・B4 の機械のまわり）
原点：床のしみは底の中央、壁の筋は壁の面の上の端の中央（垂れ始めの所。下へ垂れる）
"""
from __future__ import annotations

import math

from geo import Part


def _blob(n, rx, ry, seed, wob=0.22):
    """不規則な丸い輪郭（凸でない。中心から扇に張る）"""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = 1.0 + wob * math.sin(3 * a + seed) + 0.6 * wob * math.sin(5 * a + 2.1 * seed) + 0.4 * wob * math.cos(7 * a + seed * 0.7)
        pts.append((rx * r * math.cos(a), ry * r * math.sin(a)))
    return pts


def _fan(p: Part, mat, pts, z, cx=0.0, cy=0.0):
    """輪郭 pts（xy）を高さ z の平らな面（上向き）に。中心から扇に張る（凸でなくてよい）"""
    v = [(cx, cy, z)] + [(cx + x, cy + y, z) for x, y in pts]
    n = len(pts)
    f = [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]
    # 上向きにそろえる（orient は閉じた立体用なので、ここは向きを直に決める）
    import numpy as np
    vv = np.asarray(v, float)
    out = []
    for tri in f:
        a, b, c = vv[tri]
        nz = np.cross(b - a, c - a)[2]
        out.append(tri if nz > 0 else tri[::-1])
    p.pieces.append((mat, vv, out, False))


def stain_floor(name='stain_floor', mat='stain_floor', seed=1.0, rx=1.1, ry=0.7):
    p = Part(name, '床のしみ（平らな斑 約 2.2×1.4 m、床から 1 cm）。原点：底の中央。scale で大きさを変える。当たり判定なし')
    _fan(p, mat, _blob(18, rx, ry, seed), 0.012)
    # 外れの小さな斑 2 つ（縁を不規則に見せる）
    _fan(p, mat, _blob(9, rx * 0.22, ry * 0.25, seed + 2), 0.012, rx * 1.15, ry * 0.5)
    _fan(p, mat, _blob(9, rx * 0.16, ry * 0.2, seed + 4), 0.012, -rx * 1.05, -ry * 0.55)
    return p


def stain_path():
    p = Part('stain_path', '通り道の踏まれた汚れ（細長い斑 3×0.9 m、床から 1 cm）。原点：底の中央。長い向きは X。当たり判定なし')
    for k, (x, y, sx, sy, s) in enumerate(((-0.9, 0.05, 0.75, 0.42, 1.3), (0.15, -0.08, 0.85, 0.38, 2.6), (1.05, 0.06, 0.6, 0.34, 4.1))):
        _fan(p, 'stain_floor', _blob(14, sx, sy, s, 0.28), 0.011, x, y)
    return p


def stain_corner():
    p = Part('stain_corner', '部屋の隅の汚れ（隅を中心にした扇 1.6 m、床から 1 cm）。原点：隅（壁 2 面の交わる線の下）。yaw 0 で +X・+Z が部屋の内側'
             '（b1_corner と同じ向き）')
    pts = [(0.0, 0.0)]
    for k in range(13):
        a = math.radians(90 * k / 12)
        r = 1.6 * (1.0 + 0.18 * math.sin(5 * a + 1.0) + 0.1 * math.sin(11 * a))
        pts.append((r * math.cos(a), -r * math.sin(a)))
    # 扇の要は隅。Blender の -Y が Godot の +Z（部屋の内側）
    import numpy as np
    v = np.asarray([(x, y, 0.013) for x, y in pts], float)
    f = [[0, k + 1, k] for k in range(1, len(pts) - 1)]
    out = []
    for tri in f:
        a, b, c = v[tri]
        out.append(tri if np.cross(b - a, c - a)[2] > 0 else tri[::-1])
    p.pieces.append(('stain_floor', v, out, False))
    return p


def drips(name='stain_drip', mat='stain_rust', width=0.9, length=1.8, seed=0.0, n=5):
    """壁を垂れる筋（壁の面から 1.2 cm 前の薄い板。上の端の帯から、長さの違う筋が下へ）。原点：壁の面・上の端の中央"""
    p = Part(name, f'壁を垂れるさびの筋（幅 {width} m・長さ {length} m まで、壁から 1.2 cm）。原点：壁の面の、垂れ始めの線の中央。当たり判定なし')
    import numpy as np
    y = -0.012
    rng = [0.62, 1.0, 0.45, 0.82, 0.55, 0.9, 0.38, 0.7]
    xs = [(-width / 2 + width * (k + 0.5) / n) for k in range(n)]
    for k, x in enumerate(xs):
        L = length * rng[(k + int(seed)) % len(rng)]
        w = width / n * (0.55 + 0.3 * math.sin(k * 2.3 + seed))
        # 上は太く、下へ細くなる筋（4 段）。先は丸く
        prof = [(0.0, w * 0.5), (0.3, w * 0.42), (0.65, w * 0.3), (0.92, w * 0.18), (1.0, w * 0.05)]
        left = [(x - hw + 0.03 * math.sin(t * 6 + k), -L * t) for t, hw in prof]
        right = [(x + hw + 0.03 * math.sin(t * 6 + k), -L * t) for t, hw in prof]
        v = [(a, y, b) for a, b in left] + [(a, y, b) for a, b in right]
        m = len(prof)
        f = []
        for i in range(m - 1):
            f.append([i, i + 1, m + i + 1, m + i])
        # 前（-Y）を向かせる
        vv = np.asarray(v, float)
        out = []
        for q in f:
            a, b, c = vv[q[0]], vv[q[1]], vv[q[2]]
            out.append(q if np.cross(b - a, c - a)[1] < 0 else q[::-1])
        p.pieces.append((mat, vv, out, False))
    # 上の帯（垂れ始めのにじみ）
    band = [(-width / 2 - 0.05, 0.0), (width / 2 + 0.05, 0.0), (width / 2, -0.12), (-width / 2, -0.1)]
    v = np.asarray([(a, y, b) for a, b in band], float)
    q = [0, 1, 2, 3]
    a, b, c = v[0], v[1], v[2]
    p.pieces.append((mat, v, [q if np.cross(b - a, c - a)[1] < 0 else q[::-1]], False))
    return p


def soot():
    p = Part('stain_soot', '壁のすす（下から上へ広がる焦げの斑 1.6×2.2 m、壁から 1.2 cm）。原点：壁の面の下の端の中央。当たり判定なし')
    import numpy as np
    pts = []
    for k in range(17):
        t = k / 16
        a = math.pi * t
        r = 1.0 + 0.2 * math.sin(4 * a + 0.7) + 0.12 * math.sin(9 * a)
        pts.append((0.8 * r * math.cos(a), 2.2 * r * math.sin(a) * (0.7 + 0.3 * math.cos(2 * a))))
    v = np.asarray([(0.0, -0.012, 0.0)] + [(x, -0.012, z) for x, z in pts], float)
    f = [[0, k, k + 1] for k in range(1, len(pts))]
    out = []
    for tri in f:
        a, b, c = v[tri]
        out.append(tri if np.cross(b - a, c - a)[1] < 0 else tri[::-1])
    p.pieces.append(('stain_soot', v, out, False))
    return p


# ---------------------------------------------------------------- 砂の吹きだまり・崩れた物（W2-06b ruins_clutter の 01・02・09・10 の形）

def _heightfield(p: Part, mat, nx, ny, x0, x1, y0, y1, hfn):
    """高さの格子の面（上向き）と、縁の 0 の高さの裾。hfn(x, y) が高さ（縁は 0 にする）"""
    import numpy as np
    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(y0, y1, ny)
    v = []
    for j in range(ny):
        for i in range(nx):
            v.append((xs[i], ys[j], max(0.0, hfn(xs[i], ys[j]))))
    vv = np.asarray(v, float)
    f = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a, b, c, d = j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i
            if vv[[a, b, c, d], 2].max() <= 0.004:
                continue          # 平らな 0 の所は描かない（床に重ねない）
            for tri in ([a, b, c], [a, c, d]):
                pa, pb, pc = vv[tri]
                f.append(tri if np.cross(pb - pa, pc - pa)[2] > 0 else tri[::-1])
    p.pieces.append((mat, vv, f, True))


def sand_wall():
    p = Part('sand_wall', '壁ぎわの砂の吹きだまり（W2-06b の 01）2×1.3 m、壁で高さ 0.5、床の真ん中の側で 0（床から 0.5 cm 浮かせる）。'
             '原点：壁の面の下の端の中央。正面（+Z）が部屋の内側。当たり判定なし（壁の帯の前は 0.3 m 以下）')
    def h(x, y):
        d = -y                                   # 壁からの距離（Blender の -Y が部屋の内側）
        w = 1.0 - (abs(x) / 1.0) ** 3            # 両端で細る
        ripple = 0.025 * math.sin(6.0 * d + 1.3 * x) * (1 - d / 1.3)
        return (0.5 * max(0.0, 1 - d / 1.3) ** 1.6 + ripple) * max(0.0, w) + 0.005
    _heightfield(p, 'sand', 13, 8, -1.0, 1.0, -1.3, 0.0, h)
    return p


def sand_corner():
    p = Part('sand_corner', '部屋の隅の砂の吹きだまり（W2-06b の 02）隅から 1.8 m、隅で高さ 0.7。原点：隅（壁 2 面の交わる線の下）。'
             'yaw 0 で +X・+Z が部屋の内側（b1_corner と同じ向き）。当たり判定なし')
    def h(x, y):
        dx, dy = x, -y
        r = math.hypot(dx, dy)
        ang = math.atan2(dy, dx)
        reach = 1.8 * (1 + 0.12 * math.sin(3 * ang + 0.7))
        return 0.7 * max(0.0, 1 - r / reach) ** 1.7 + 0.005 if r < reach else 0.0
    _heightfield(p, 'sand', 11, 11, 0.0, 1.9, -1.9, 0.0, h)
    return p


def pipe_broken():
    p = Part('pipe_broken', '崩れて床に落ちた太い管（W2-06b の 09。黒鉛の管 1.6 m・半径 0.3、片方は割れた口、真鍮の継ぎ輪、まわりのかけら）。'
             '床に横たえる。原点：底の中央。管は X に沿う。当たり判定は dress_ruins_deep の表（1.75×0.65×0.62）')
    r = 0.3
    p.cyl('pipe', (-0.8, 0, r), (0.62, 0, r), r, 14)
    p.cyl('brass', (-0.8, 0, r), (-0.66, 0, r), r + 0.05, 14)
    # 割れた口：ぎざぎざの縁（薄い黒鉛の板を輪に）と、暗い中
    for k in range(10):
        a = 2 * math.pi * k / 10
        L = 0.08 + 0.1 * ((k * 7) % 3) / 2
        p.box('graphite', (0.62, -0.04, -0.04), (0.62 + L, 0.04, 0.04))
        p.transformed(lambda v, a=a: v + np.array([0, (r - 0.03) * math.cos(a), r + (r - 0.03) * math.sin(a)]), len(p.pieces) - 1)
    p.cyl('dark', (0.6, 0, r), (0.64, 0, r), r - 0.03, 12)
    for c, s in (((0.95, 0.25, 0.06), (0.24, 0.18, 0.12)), ((0.85, -0.3, 0.05), (0.18, 0.2, 0.1)), ((-0.95, 0.2, 0.05), (0.16, 0.14, 0.1))):
        p.cbox('ivory', c, s, 0.03)
    return p


def panel_fallen():
    p = Part('panel_fallen', '外れて倒れた白磁の外装の板（W2-06b の 10。2×1×0.16 の板が壁にもたれて傾き、足元にかけら）。'
             '原点：板の下の端の中央（床）。板は X に沿い、背面（壁の側、-Z）へ 0.88 m もたれる（上の端は高さ 0.47）。当たり判定は表')
    n0 = len(p.pieces)
    p.cbox('ivory', (0, 0.08, 0.5), (2.0, 0.16, 1.0), 0.04, 'y')
    p.box('graphite', (-1.0, 0.0, 0.0), (1.0, 0.18, 0.08))
    p.box('graphite', (-1.0, 0.0, 0.92), (1.0, 0.18, 1.0))
    p.transformed(apply_rx(-62), n0)
    for c, s in (((-0.6, -0.75, 0.07), (0.3, 0.24, 0.14)), ((0.3, -0.85, 0.06), (0.22, 0.2, 0.12)), ((0.8, -0.6, 0.05), (0.18, 0.16, 0.1))):
        p.cbox('ivory', c, s, 0.03)
    return p


def apply_rx(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    M = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return lambda v: v @ M.T


import numpy as np  # noqa: E402


PARTS = [
    sand_wall, sand_corner, pipe_broken, panel_fallen,
    lambda: stain_floor('stain_floor', 'stain_floor', 1.0),
    lambda: stain_floor('stain_floor_b', 'stain_floor', 2.7, 0.9, 0.8),
    stain_path, stain_corner,
    lambda: drips('stain_drip', 'stain_rust', 0.9, 1.8, 0.0, 5),
    lambda: drips('stain_drip_long', 'stain_rust', 0.6, 3.2, 3.0, 4),
    soot,
]
