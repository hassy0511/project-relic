"""キットの部品の「重なった同じ向きの面」（ちらつき・z-fighting）を探す。bpy は使わない（形を数値で組んで調べるだけ）。

同じ部品の中で、別の形（箱・筒…）の面どうしが同じ平面（5 mm 以内）・同じ向き（表どうし）で 1 cm² 以上重なっていると、
描くたびにどちらが前か決まらず、まだら・縞になる（例：管の端の継ぎ輪のふたと管のふたが同じ面にあった）。
向かい合った面（箱どうしが接する面）は互いに隠れるので数えない。同じ材質・同じ色の重なりは見た目が変わらないので「注意」だけ。

  .venv-blender/bin/python tools/blender/kit/check_coplanar.py            町（town）と遺構（ruins_b1）の部品を全部
  .venv-blender/bin/python tools/blender/kit/check_coplanar.py --only pipes,workshop_front
  .venv-blender/bin/python tools/blender/kit/check_coplanar.py --raw        書き出しの前のほどきをせずに（作り方そのものの重なり）
  .venv-blender/bin/python tools/blender/kit/check_coplanar.py --room ch1_town.json:mid,ch1_ruins.json:r02,ch1_ruins.json:r03
                                                                            部屋に置いた形で、部品どうし・部品と地形の重なり
  終わりの値：材質の違う重なりが 1 つでもあれば 1

書き出し（town_geo.to_object・geo.to_blender）は、部品の中の重なりを separate でほどいてから書く：重なった 2 つの面の小さい方を、
その面の平面にある形の頂点ごと 1.5 cm 外へ出す（箱なら面が伸び、管なら端の輪とふたが一緒に動く）。部品どうし・地形との重なりはほどかない
（置き方の側 dress_town.py・dress_ruins.py で直す）。
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PLANE_TOL = 0.005     # 同じ平面とみなす距離（m。スマホ・ブラウザ版の 24 bit の深さでは、30 m 先の 2 mm は分けられない）
AREA_MIN = 1e-4       # 数える重なりの広さ（m²）
REACH_OUT = 2.0      # 部屋の立てる面の外へカメラが出る幅（m。壁の外へは出ないので小さめ）


def _faces_town(part):
    """town_geo.Part → [(形の番号, 材質, 頂点の列)]"""
    out, k = [], 0
    for mat, pieces in part.by_mat.items():
        for pc in pieces:
            for f in pc.f:
                out.append((k, mat, pc.v[f]))
            k += 1
    return out


def _faces_ruins(part):
    """geo.Part（Blender の座標：Z 上）→ ゲームの座標（Y 上）の面"""
    out = []
    for k, (mat, v, faces, _sm) in enumerate(part.pieces):
        v = np.asarray(v, float)
        g = np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)
        for f in faces:
            out.append((k, mat, g[f]))
    return out


def _clip(poly, a, b):
    """凸の多角形 poly（2D）を、直線 a→b の左側で切る（Sutherland–Hodgman）"""
    out = []
    n = len(poly)
    if n == 0:
        return out
    d = b - a
    side = lambda p: d[0] * (p[1] - a[1]) - d[1] * (p[0] - a[0])  # noqa: E731
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        sp, sq = side(p), side(q)
        if sp >= 0:
            out.append(p)
        if (sp >= 0) != (sq >= 0):
            t = sp / (sp - sq)
            out.append(p + (q - p) * t)
    return out


def _area(poly):
    if len(poly) < 3:
        return 0.0
    p = np.asarray(poly)
    return 0.5 * float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))


def _ccw(p):
    return p if _area(list(p)) >= 0 else p[::-1]


def _overlap(p2, q2):
    """凸の 2 つの多角形（2D、反時計回り）の重なり（広さ, 重なりの中心）"""
    poly = list(p2)
    n = len(q2)
    for i in range(n):
        poly = _clip(poly, q2[i], q2[(i + 1) % n])
        if not poly:
            return 0.0, None, []
    return abs(_area(poly)), np.mean(np.asarray(poly), 0), [np.asarray(q) for q in poly]


def _solids(faces):
    """閉じた形ごとの半空間の組（n, d）。凸の形なら「全部の面の内側」が形の中。
    閉じていない形（1 枚の板・ふたの無い筒）は数えない（面積の重みの法線の和が 0 にならない）"""
    acc: dict = {}
    for k, _mat, pts in faces:
        if len(pts) < 3:
            continue
        n = np.zeros(3)
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            n += [(p[1] - q[1]) * (p[2] + q[2]), (p[2] - q[2]) * (p[0] + q[0]), (p[0] - q[0]) * (p[1] + q[1])]
        a = np.linalg.norm(n)
        if a < 1e-12:
            continue
        e = acc.setdefault(k, [np.zeros(3), 0.0, []])
        e[0] += n
        e[1] += a
        e[2].append((n / a, float(n @ pts.mean(0)) / a))
    out = {}
    for k, (s, tot, hs) in acc.items():
        if len(hs) >= 4 and np.linalg.norm(s) < 1e-3 * tot:
            out[k] = (np.array([x[0] for x in hs]), np.array([x[1] for x in hs]))
    return out


class _Solids:
    """閉じた形の中にある点か（形の外接の箱で先にふるう）"""

    def __init__(self, faces):
        self.s = _solids(faces)
        self.keys = list(self.s)
        box: dict = {}
        for k, _m, pts in faces:
            if k in self.s:
                lo, hi = box.get(k, (pts.min(0), pts.max(0)))
                box[k] = (np.minimum(lo, pts.min(0)), np.maximum(hi, pts.max(0)))
        self.lo = np.array([box[k][0] for k in self.keys]).reshape(-1, 3)
        self.hi = np.array([box[k][1] for k in self.keys]).reshape(-1, 3)

    def inside(self, p, skip):
        if not self.keys:
            return False
        m = np.all(self.lo <= p, 1) & np.all(p <= self.hi, 1)
        for i in np.nonzero(m)[0]:
            k = self.keys[i]
            if k in skip:
                continue
            N, D = self.s[k]
            if np.all(N @ p - D < 1e-5):
                return True
        return False


def check(faces, colors=None, reach=None, base_skip=True, tol=PLANE_TOL):
    """重なった同じ向きの面の組 [(広さ, 材質 a, 材質 b, 中心, 法線, 形 a, 形 b, 面 a の広さ, 面 b の広さ, 平面の距離)]。
    重なりのすぐ外（法線の向きに 4 mm）が別の形の中なら、覆われて見えないので数えない。部品の底の面（下向き・いちばん低い所）も数えない"""
    solids = _Solids(faces)
    base = min(float(pts[:, 1].min()) for _k, _m, pts in faces) if faces and base_skip else -1e9
    recs = []
    for k, mat, pts in faces:
        if len(pts) < 3:
            continue
        # Newell の法線（多角形の面積の向き）
        n = np.zeros(3)
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            n += [(p[1] - q[1]) * (p[2] + q[2]), (p[2] - q[2]) * (p[0] + q[0]), (p[0] - q[0]) * (p[1] + q[1])]
        a = np.linalg.norm(n)
        if a < 2e-6:
            continue
        n /= a
        recs.append((k, mat, pts, n, float(n @ pts.mean(0)), a / 2))
    # 向きで束ねる（丸めた法線）、束の中で平面の距離で並べて近い組だけ調べる
    groups: dict = {}
    for r in recs:
        groups.setdefault(tuple(np.round(r[3], 2)), []).append(r)
    found = []
    for key, g in groups.items():
        g.sort(key=lambda r: r[4])
        ds = np.array([r[4] for r in g])
        n0 = np.array(key, float)
        n0 /= np.linalg.norm(n0)
        u = np.cross(n0, [0, 1, 0] if abs(n0[1]) < 0.9 else [1, 0, 0])
        u /= np.linalg.norm(u)
        w = np.cross(n0, u)
        p2s = [_ccw(np.stack([r[2] @ u, r[2] @ w], 1)) for r in g]
        lo = np.array([p.min(0) for p in p2s])
        hi = np.array([p.max(0) for p in p2s])
        j0 = 0
        for i in range(len(g)):
            while ds[i] - ds[j0] > tol:
                j0 += 1
            for j in range(j0, i):
                ri, rj = g[i], g[j]
                if ri[0] == rj[0] or float(ri[3] @ rj[3]) < 0.999:
                    continue
                if np.any(lo[i] > hi[j] - 1e-4) or np.any(lo[j] > hi[i] - 1e-4):
                    continue
                ar, c2, poly2 = _overlap(p2s[i], p2s[j])
                if ar <= AREA_MIN:
                    continue
                ni, di = ri[3], ri[4]

                def lift(q2, ni=ni, di=di):
                    """2D の点 → 面 i の平面の上の 3D の点（束ねた法線 n0 は丸めてあるので、面の本当の平面へ戻す）"""
                    b = u * q2[0] + w * q2[1]
                    return b + n0 * ((di - float(ni @ b)) / float(ni @ n0))
                c3 = lift(c2)
                if n0[1] < -0.99 and abs(c3[1] - base) < PLANE_TOL:
                    continue
                if reach is not None:
                    # 届く範囲（カメラの来られる箱）が面の表の側に無ければ、見えない
                    corners = np.array([[reach[i & 1][0], reach[(i >> 1) & 1][1], reach[(i >> 2) & 1][2]] for i in range(8)])
                    if float((corners @ ri[3]).max()) - ri[4] < 0.05:
                        continue
                # 重なりの中心と角の近く（中心へ 15 % 寄せた点）の全部が別の形の中なら、覆われている
                pts2 = [c2] + [c2 + (q - c2) * 0.85 for q in poly2]
                if all(solids.inside(lift(q) + ni * 0.004, (ri[0], rj[0])) for q in pts2):
                    continue
                found.append((ar, ri[1], rj[1], c3, n0, ri[0], rj[0], ri[5], rj[5], float(ds[i]), (ri[3], ri[4]), (rj[3], rj[4])))
    return found


GAP = 0.015          # 重なりをほどくときに、小さい方の面を外へ出す距離（m）


def separate(pieces, colors, passes=4) -> int:
    """重なった同じ向きの面（材質・色の違うもの）を、小さい方の面を外へ GAP 出してほどく。
    pieces：[(材質, 頂点 (N,3)・ゲームの座標（Y 上）・その場で書き換える, 面のリスト)]。その面の平面にある形の頂点を全部動かす
    （箱なら面が 1.5 cm 伸び、管なら端の輪とふたが一緒に動く）。返り値：動かした面の数"""
    moved = 0
    for _ in range(passes):
        faces = [(k, mat, V[f]) for k, (mat, V, F) in enumerate(pieces) for f in F]
        # 調べる幅は check の既定より広く（5 mm ちょうどの組が、向きを変えて置くと丸めの差で 5 mm より近くなる）
        diff = [f for f in check(faces, tol=PLANE_TOL * 1.6) if not _same_look(f[1], f[2], colors)]
        if not diff:
            break
        moves = {}
        for f in diff:
            (k, (n, d)), (_k2, (_n2, d2)) = sorted([(f[5], f[10]), (f[6], f[11])], key=lambda x: (f[7] if x[0] == f[5] else f[8], x[0]))
            key = (k, tuple(np.round(n, 3)), round(d, 3))
            moves[key] = (n, d, max(moves.get(key, (0, 0, 0))[2], max(0.0, d2 - d) + GAP))
        for (k, _n, _d), (n, d, dist) in moves.items():
            V = pieces[k][1]
            on = np.abs(V @ n - d) < PLANE_TOL * 0.5
            V[on] += n * dist
            moved += 1
    return moved


def separate_town(part) -> int:
    """town_geo.Part の重なりをほどく（書き出しの前に town_geo.to_object が呼ぶ）"""
    import town_geo
    cols = {k: v['color'] for k, v in town_geo.MATERIALS.items()}
    refs = [pc for ps in part.by_mat.values() for pc in ps]
    pieces = [(mat, pc.v.astype(float).copy(), pc.f) for mat, ps in part.by_mat.items() for pc in ps]
    n = separate(pieces, cols)
    if n:
        for pc, (_m, v, _f) in zip(refs, pieces):
            pc.v = v
    return n


def separate_ruins(part) -> int:
    """geo.Part（Blender の座標）の重なりをほどく（geo.to_blender が呼ぶ）"""
    import geo
    cols = {k: v[0] for k, v in geo.PALETTE.items()}
    pieces = []
    for mat, v, faces, _sm in part.pieces:
        v = np.asarray(v, float)
        pieces.append((mat, np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1), faces))
    n = separate(pieces, cols)
    if n:
        part.pieces = [(mat, np.stack([g[:, 0], -g[:, 2], g[:, 1]], 1), faces, sm)
                       for (mat, _v, faces, sm), (_m, g, _f) in zip(part.pieces, pieces)]
    return n


def _box_faces(c, size, yaw_deg=0.0):
    """RoomGeo.box と同じ箱（c は中心）の 6 面"""
    h = np.asarray(size, float) / 2
    a = np.radians(yaw_deg)
    R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    v = np.array([[h[0] if i & 1 else -h[0], h[1] if i & 2 else -h[1], h[2] if i & 4 else -h[2]] for i in range(8)]) @ R.T + c
    quads = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    out = [v[q] for q in quads]
    # 外向きにそろえる
    cen = v.mean(0)
    res = []
    for f in out:
        n = np.cross(f[1] - f[0], f[2] - f[0])
        res.append(f if n @ (f.mean(0) - cen) > 0 else f[::-1])
    return res


def _geo_boxes(g):
    """部屋の形（box・stairs・shell の床と天井）→ 箱の面の列のリスト（RoomGeo._shape と同じ寸法）"""
    pos, size, yaw = np.asarray(g.get('pos', [0, 0, 0]), float), np.asarray(g.get('size', [1, 1, 1]), float), float(g.get('yaw', 0))
    t = g.get('t', 'box')
    if t == 'box':
        return [_box_faces(pos + [0, size[1] / 2, 0], size, yaw)]
    if t == 'stairs':
        n = max(1, int(g.get('steps', 6)))
        a = np.radians(yaw)
        R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
        out = []
        for i in range(n):
            h = size[1] * (i + 1) / n
            z = -size[2] / 2 + size[2] * (i + 0.5) / n
            out.append(_box_faces(pos + R @ np.array([0, h / 2, z]), (size[0], h, size[2] / n), yaw))
        return out
    if t == 'shell':
        th = float(g.get('thick', 1))
        out = [_box_faces(pos + [0, -th / 2, 0], (size[0] + 2 * th, th, size[2] + 2 * th))]
        if g.get('ceiling'):
            out.append(_box_faces(pos + [0, size[1] + th / 2, 0], (size[0] + 2 * th, th, size[2] + 2 * th)))
        return out
    return []


def room_faces(area, room_id, kits):
    """部屋の飾り（dress）を置いた形の面と、描く地形の箱の面。返り値：(面のリスト, 届く範囲の箱, 部品の名前（形の番号 → 名前）)"""
    import json
    data = json.load(open(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'godot', 'content', 'areas', area), encoding='utf-8'))
    room = data['rooms'][room_id]
    faces, names, cache = [], {}, {}
    k = 0
    floors = []
    for g in room.get('geometry', []):
        for bx in _geo_boxes(g):
            for f in bx:
                n = np.cross(f[1] - f[0], f[2] - f[0])
                if n[1] > 0.5:
                    floors.append(f)
            if not g.get('hide'):
                for f in bx:
                    faces.append((k, 'geo', f))
                names[k] = 'geometry'
                k += 1
    for it in room.get('dress', []):
        kit, part = it['part'].split('/')
        if part not in cache:
            fn = kits.get(part)
            cache[part] = fn() if fn else None
            if cache[part] is not None:
                (separate_town if kit == 'town' else separate_ruins)(cache[part])
        p = cache[part]
        if p is None:
            continue
        a = np.radians(float(it.get('yaw', 0)))
        R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
        sc = it.get('scale', 1.0)
        S = np.asarray(sc if isinstance(sc, list) else [sc] * 3, float)
        flip = np.prod(np.sign(S)) < 0
        pos = np.asarray(it['pos'], float)
        src = _faces_town(p) if kit == 'town' else _faces_ruins(p)
        base_k = k
        for kk, mat, pts in src:
            w = (pts * S) @ R.T + pos
            faces.append((base_k + kk, mat, w[::-1] if flip else w))
            names[base_k + kk] = part
        k = base_k + 1 + max(kk for kk, _m, _p in src)
    fl = np.concatenate(floors)
    reach = (fl.min(0) - [REACH_OUT, -0.2, REACH_OUT], fl.max(0) + [REACH_OUT, 8.0, REACH_OUT])
    return faces, reach, names, floors


def _nothing_below(c, floors):
    """下向きの面の点 c の下に、カメラの入れる床（0.3 m 以上下の上の面）が無い（床の上・床の中の面の裏は見えない）"""
    for f in floors:
        if float(f[0][1]) < c[1] - 0.3 and f[:, 0].min() - 1e-3 <= c[0] <= f[:, 0].max() + 1e-3 \
                and f[:, 2].min() - 1e-3 <= c[2] <= f[:, 2].max() + 1e-3:
            return False
    return True


def _same_look(a, b, colors):
    if a == b:
        return True
    return colors is not None and colors.get(a) == colors.get(b)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', default='')
    ap.add_argument('--kit', default='town,ruins_b1')
    ap.add_argument('--show', type=int, default=4, help='部品ごとに書き出す重なりの数')
    ap.add_argument('--raw', action='store_true', help='書き出しの前のほどき（separate）をせずに調べる（作り方そのものの重なりを見る）')
    ap.add_argument('--room', default='', help='部屋に置いた形で調べる：ch1_town.json:mid・ch1_ruins.json:r02 など（届かない側を向いた面・他の部品に覆われた面は数えない）')
    a = ap.parse_args()
    if a.room:
        sys.exit(_room(a))
    only = {n for n in a.only.split(',') if n}
    bad = 0
    if 'town' in a.kit:
        import town
        import town_geo
        cols = {k: v['color'] for k, v in town_geo.MATERIALS.items()}
        for name, fn in town.catalog().items():
            if only and name not in only:
                continue
            p = fn()
            if not a.raw:
                separate_town(p)
            bad += _report(name, check(_faces_town(p)), cols, a.show)
    if 'ruins_b1' in a.kit:
        import geo
        import ruins_b1
        cols = {k: v[0] for k, v in geo.PALETTE.items()}
        for fn in ruins_b1.PARTS:
            p = fn()
            if only and p.name not in only:
                continue
            if not a.raw:
                separate_ruins(p)
            bad += _report(p.name, check(_faces_ruins(p)), cols, a.show)
    print(f'材質の違う重なり：{bad} 部品')
    sys.exit(1 if bad else 0)


def _room(a):
    import geo
    import ruins_b1
    import town
    import town_geo
    kits = dict(town.catalog())
    for fn in ruins_b1.PARTS:
        kits[fn().name] = fn
    cols = {k: v['color'] for k, v in town_geo.MATERIALS.items()}
    cols.update({k: v[0] for k, v in geo.PALETTE.items() if k not in cols})
    bad = 0
    for spec in a.room.split(','):
        area, rid = spec.split(':')
        faces, reach, names, floors = room_faces(area, rid, kits)
        found = [f for f in check(faces, reach=reach, base_skip=False) if not (f[4][1] < -0.99 and _nothing_below(f[3], floors))]
        # 形の番号から部品の名前を引けるよう、check の結果に中心から近い部品を書く
        diff = [f for f in found if not _same_look(f[1], f[2], cols)]
        print(f'{spec}: 材質の違う重なり {len(diff)} 組（同じ色 {len(found) - len(diff)}）')
        groups: dict = {}
        for f in diff:
            key = tuple(sorted([(names.get(f[5], '?'), f[1]), (names.get(f[6], '?'), f[2])]))
            groups.setdefault(key, []).append(f)
        for key, fs in sorted(groups.items(), key=lambda kv: -sum(f[0] for f in kv[1])):
            ar, ma, mb, c, n, *_ = max(fs, key=lambda f: f[0])
            print(f'  {key[0][0]}:{key[0][1]} / {key[1][0]}:{key[1][1]}  {len(fs)} 組  最大 {ar * 1e4:.0f} cm² at ({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f}) n ({n[0]:.0f}, {n[1]:.0f}, {n[2]:.0f})')
        bad += len(diff)
    return 1 if bad else 0


def _report(name, found, cols, show):
    diff = [f for f in found if not _same_look(f[1], f[2], cols)]
    same = len(found) - len(diff)
    if diff:
        print(f'[ちらつき] {name}: {len(diff)} 組（同じ色 {same}）')
        for ar, ma, mb, c, n, *_ in sorted(diff, key=lambda f: -f[0])[:show]:
            print(f'    {ma}/{mb} {ar * 1e4:.1f} cm² at ({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f}) n ({n[0]:.0f}, {n[1]:.0f}, {n[2]:.0f})')
        return 1
    if same:
        print(f'[注意] {name}: 同じ色の重なり {same} 組')
    return 0


if __name__ == '__main__':
    main()
