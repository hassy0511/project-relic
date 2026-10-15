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


PARTS = [
    lambda: stain_floor('stain_floor', 'stain_floor', 1.0),
    lambda: stain_floor('stain_floor_b', 'stain_floor', 2.7, 0.9, 0.8),
    stain_path, stain_corner,
    lambda: drips('stain_drip', 'stain_rust', 0.9, 1.8, 0.0, 5),
    lambda: drips('stain_drip_long', 'stain_rust', 0.6, 3.2, 3.0, 4),
    soot,
]
