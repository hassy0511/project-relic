"""部位ごとの UV 展開：体を平面で部位に切り分け、各部位を前後（手は内外）の 2 枚にして展開し、詰める。

Smart UV Project は、髪の房・指・服の段のある面を 1000 近い小さな島に分けてしまう（島の境で色がにじみ、
UV の空きも多い）。ここでは切れ目（シーム）を体の自然な境に、平面で切った真っすぐな線として置く。

  部位と切る面（Blender の座標。本人の左 +X、前 -Y、上 +Z）
    頭      首の高さ（あご）の水平面より上。前後に切り、後ろの半分はさらに左右に切る
            （前の半分は顔を 1 枚で含む。顔の絵を貼りやすい）
    胴      ベルトの高さの水平面で上下に。前後に切る
    腕      肩の切れ目（わきの下から肩の上へ傾いた面）から先、手首の面まで。ひじの高さで上下に、前後に
    手      手首の面（|x| = 0.31）より先。手の板の向き（腕の傾き約 35 度）で体の側と外側に切る
    脚      股の高さの水平面より下、左右に。膝の高さで上下に、前後に
  切る面は bmesh の bisect_plane で、その部位の面だけを切る（ほかの部位には線を入れない）。
  切れ目が三角形の辺の上を真っすぐ通るので、島の縁がぎざぎざにならない。
展開は伸びの少ない方法（MINIMUM_STRETCH）。島は 3 次元の面積に比例した大きさになるので、頭の島を
head_scale 倍（既定 2 倍、面積 4 倍）、手の島を 1〜1.5 倍（指と手袋は細かいので、大きくしても損はない）に
してから、凹んだ形も考えて詰める（CONCAVE）。Blender の詰め方は島の大きさの組み合わせで結果が変わるので、
手の倍率と島のすき間（2048 角で約 4・3.5・3 画素）を試し、UV の 75% 以上が使われる組のうち、すき間の
最も大きいものを選ぶ。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi
from scipy import sparse

ARM_DEG = 35.0      # A ポーズの腕の開き（手の板の向きに使う）
HAND_X = 0.31       # 手首の面 |x|
CUT_Z = {'legs': 0.60, 'torso': 0.86, 'arm': 0.92, 'leg': 0.31}   # 股・ベルト・ひじ・膝の高さ


def _arm_gap_x(z: np.ndarray) -> np.ndarray:
    """腕と胴を分ける |x|（高さ z ごと）。わきの下より上は肩へ傾いた面、下は腕と胴の間のすき間の中ほど"""
    zz = np.array([0.50, 0.70, 0.80, 0.90, 0.97, 1.15, 1.30])
    xx = np.array([0.27, 0.25, 0.22, 0.16, 0.138, 0.169, 0.195])
    return np.interp(z, zz, xx)


def region_of_point(c: np.ndarray, head_z: float) -> np.ndarray:
    """点 (n, 3) → 大きな部位：0 頭、1 胴、2 右腕、3 左腕、4 右手、5 左手、6 右脚、7 左脚"""
    x, z = c[:, 0], c[:, 2]
    ax = np.abs(x)
    reg = np.full(len(c), 1, np.int32)
    reg[z >= head_z] = 0
    arm = (z < head_z) & (z > 0.45) & (ax > _arm_gap_x(z))
    hand = arm & (ax > HAND_X) & (z < 0.85)
    reg[arm & (x < 0)] = 2
    reg[arm & (x > 0)] = 3
    reg[hand & (x < 0)] = 4
    reg[hand & (x > 0)] = 5
    leg = (reg == 1) & (z < CUT_Z['legs'])
    reg[leg & (x < 0)] = 6
    reg[leg & (x > 0)] = 7
    return reg


def _face_arrays(bm):
    C = np.array([f.calc_center_median()[:] for f in bm.faces])
    A = np.array([f.calc_area() for f in bm.faces])
    return C, A


def _bisect(bm, faces, co, no) -> None:
    import bmesh
    if not faces:
        return
    edges = list({e for f in faces for e in f.edges})
    verts = list({v for f in faces for v in f.verts})
    bmesh.ops.bisect_plane(bm, geom=faces + edges + verts, plane_co=tuple(co), plane_no=tuple(no), dist=1e-6)


def cut_parts(bm, head_z: float) -> tuple[np.ndarray, list[str]]:
    """bm（三角形のメッシュ）を部位の平面で切り、面ごとの部位の番号と名前の一覧を返す"""
    import bmesh
    names: list[str] = []

    def faces_where(pred):
        bm.faces.ensure_lookup_table()
        C, _ = _face_arrays(bm)
        m = pred(C)
        return [bm.faces[i] for i in np.nonzero(m)[0]]

    # 1. 大きな部位の境
    # 頭と胴：首の水平面（首のまわりだけ）
    _bisect(bm, faces_where(lambda C: (np.abs(C[:, 2] - head_z) < 0.05) & (np.abs(C[:, 0]) < 0.2)),
            (0, 0, head_z), (0, 0, 1))
    # 腕と胴：わきの下より上の傾いた面（左右）
    for s in (-1, 1):
        p0 = np.array([s * 0.138, 0, 0.97])
        p1 = np.array([s * 0.169, 0, 1.15])
        d = p1 - p0
        no = np.cross(d, [0, 1, 0])
        no /= np.linalg.norm(no)
        _bisect(bm, faces_where(lambda C: (C[:, 2] > 0.93) & (C[:, 2] < head_z) & (C[:, 0] * s > 0.08)), p0, no)
    # 手首：|x| = HAND_X の面（腕の低い所だけ）
    for s in (-1, 1):
        _bisect(bm, faces_where(lambda C: (C[:, 2] < 0.85) & (C[:, 2] > 0.45) & (C[:, 0] * s > 0.25)),
                (s * HAND_X, 0, 0), (1, 0, 0))
    # 股：水平面（胴の中だけ）と、脚の左右を分ける x = 0 の面
    _bisect(bm, faces_where(lambda C: (np.abs(C[:, 2] - CUT_Z['legs']) < 0.05) & (np.abs(C[:, 0]) < 0.25)),
            (0, 0, CUT_Z['legs']), (0, 0, 1))
    _bisect(bm, faces_where(lambda C: (C[:, 2] < CUT_Z['legs'] + 0.01) & (np.abs(C[:, 0]) < 0.06)),
            (0, 0, 0), (1, 0, 0))

    # 2. 部位ごとに前後（手は内外）と上下に切る
    bm.faces.ensure_lookup_table()
    C, A = _face_arrays(bm)
    reg = region_of_point(C, head_z)
    t = math.radians(ARM_DEG)
    plan = []   # (部位の番号, 名前, 切る面の法線, 上下に切る高さ)
    plan.append((0, 'head', np.array([0, 1.0, 0]), None))
    plan.append((1, 'torso', np.array([0, 1.0, 0]), CUT_Z['torso']))
    plan.append((2, 'arm_r', np.array([0, 1.0, 0]), CUT_Z['arm']))
    plan.append((3, 'arm_l', np.array([0, 1.0, 0]), CUT_Z['arm']))
    plan.append((4, 'hand_r', np.array([-math.cos(t), 0, math.sin(t)]), None))
    plan.append((5, 'hand_l', np.array([math.cos(t), 0, math.sin(t)]), None))
    plan.append((6, 'leg_r', np.array([0, 1.0, 0]), CUT_Z['leg']))
    plan.append((7, 'leg_l', np.array([0, 1.0, 0]), CUT_Z['leg']))
    cens = {}
    for r, name, no, zc in plan:
        m = reg == r
        if not m.any():
            continue
        cen = (C[m] * A[m, None]).sum(0) / A[m].sum()
        _bisect(bm, faces_where(lambda C2, r=r: region_of_point(C2, head_z) == r), cen, no)
        if zc is not None:
            _bisect(bm, faces_where(lambda C2, r=r: region_of_point(C2, head_z) == r), (0, 0, zc), (0, 0, 1))
        if r == 0:
            # 頭の後ろの半分を左右に
            _bisect(bm, faces_where(lambda C2: (region_of_point(C2, head_z) == 0) & (C2[:, 1] > cen[1])),
                    (0, 0, 0), (1, 0, 0))
        cens[r] = cen

    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.faces.ensure_lookup_table()
    C, A = _face_arrays(bm)
    reg = region_of_point(C, head_z)
    lab = np.zeros(len(C), np.int32)
    for r, name, no, zc in plan:
        m = reg == r
        cen = cens.get(r)
        if cen is None or not m.any():
            continue
        side = ((C[m] - cen) @ no) >= 0
        first, second = ('in', 'out') if name.startswith('hand') else ('front', 'back')
        # 前（-Y）・体の側（手）を first にする
        a_is_first = ~side
        parts = []
        for sd, nm in ((a_is_first, first), (~a_is_first, second)):
            if zc is not None:
                parts.append((sd & (C[m, 2] >= zc), f'{name}_{nm}'))
                parts.append((sd & (C[m, 2] < zc), f'{name}_{nm}_lower'))
            elif r == 0 and nm == 'back':
                parts.append((sd & (C[m, 0] <= 0), 'head_back_right'))
                parts.append((sd & (C[m, 0] > 0), 'head_back_left'))
            else:
                parts.append((sd, f'{name}_{nm}'))
        idx = np.nonzero(m)[0]
        for sel, nm in parts:
            if nm not in names:
                names.append(nm)
            lab[idx[sel]] = names.index(nm)
    return lab, names


def face_adjacency(faces: np.ndarray) -> sparse.csr_matrix:
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    fid = np.tile(np.arange(len(faces)), 3)
    key = np.sort(e, 1)
    order = np.lexsort((key[:, 1], key[:, 0]))
    key, fid = key[order], fid[order]
    same = np.all(key[1:] == key[:-1], 1)
    i = np.nonzero(same)[0]
    a, b = fid[i], fid[i + 1]
    n = len(faces)
    return sparse.coo_matrix((np.ones(2 * len(a)), (np.concatenate([a, b]), np.concatenate([b, a]))),
                             shape=(n, n)).tocsr()


def merge_fragments(lab: np.ndarray, A: sparse.csr_matrix, min_faces: int = 150, iters: int = 6) -> np.ndarray:
    """同じ部位の中で離れた小さな切れ端（min_faces 未満）を、まわりで最も多い部位に移す（島を 1 部位 1 つに）"""
    lab = lab.copy()
    for _ in range(iters):
        changed = 0
        for p in np.unique(lab):
            m = lab == p
            sub = A[m][:, m]
            ncomp, cl = sparse.csgraph.connected_components(sub, directed=False)
            if ncomp <= 1:
                continue
            sizes = np.bincount(cl)
            idx = np.nonzero(m)[0]
            keep = int(np.argmax(sizes))
            for c in range(ncomp):
                if c == keep or sizes[c] >= min_faces:
                    continue
                f = idx[cl == c]
                nb_lab = lab[A[f].indices]
                nb_lab = nb_lab[nb_lab != p]
                if len(nb_lab) == 0:
                    continue
                lab[f] = np.bincount(nb_lab).argmax()
                changed += 1
        if changed == 0:
            break
    return lab


def _island_masks(tris: np.ndarray, scale_px: float, angles, pad: int) -> list[tuple]:
    """1 つの島（UV の三角形 (n, 3, 2)、島の中心が原点）を、向きごとに画素へ塗ったマスク。

    戻り値は向きごとの (角度, マスク, 島の座標 → マスクの画素へのずらし)。マスクは pad 画素太らせてある
    （塗りの誤差とすき間の分）。
    """
    from PIL import Image, ImageDraw
    out = []
    for a in angles:
        c, s_ = math.cos(a), math.sin(a)
        R = np.array([[c, -s_], [s_, c]])
        t = (tris.reshape(-1, 2) @ R.T) * scale_px
        lo = t.min(0) - pad - 1
        t = t - lo
        w, h = (np.ceil(t.max(0)) + pad + 2).astype(int)
        im = Image.new('L', (int(w), int(h)), 0)
        dr = ImageDraw.Draw(im)
        for tri in t.reshape(-1, 3, 2):
            dr.polygon([tuple(p) for p in tri], fill=255)
        m = np.asarray(im) > 0
        if pad > 0:
            m = ndi.binary_dilation(m, iterations=pad)
        out.append((a, m, -lo))
    return out


def raster_pack(islands: list[np.ndarray], res: int = 1024, gap_px: int = 2, n_angles: int = 8, steps: int = 6,
                grow_max: float = 1.15, grow_first: list[int] | None = None) -> tuple[float, list[tuple]]:
    """島（それぞれ中心が原点の UV の三角形 (n, 3, 2)、大きさの比は保つ）を 1 × 1 の中へ詰める。

    画素（res 角）の上で、大きい島から順に、向き（n_angles 通り）ごとに「重ならずに置ける位置」を
    FFT の畳み込みで求め、上端が最も低い（同じなら左）位置に置く。全体の倍率は二分探索で、全部が入る
    最大にする。置いた島を gap_px 画素太らせて占有に書くので、島の間は gap_px 画素以上あく（島のマスクは
    塗りの誤差の分 1 画素太らせる）。
    最後に、島ごとに、まわりのすき間に収まる限り大きくする（最大 grow_max 倍。grow_first の島から先に）。
    その島の細かさは少し上がる（下がることはない）。
    戻り値は (倍率, 島ごとの (角度, 倍率の係数, 中心の UV))。UV = 回転(角度) · 島 × 倍率 × 係数 + 中心。
    """
    from scipy.signal import fftconvolve
    areas = [float(np.abs(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])).sum() / 2) for t in islands]
    area = sum(areas)
    order = np.argsort(-np.array(areas))
    angles = [2 * math.pi * k / n_angles for k in range(n_angles)]
    grow = ndi.generate_binary_structure(2, 1)

    def stamp(occ, m, y, x, sign=1.0):
        mg = np.pad(m, gap_px)
        if gap_px > 0:
            mg = ndi.binary_dilation(mg, grow, iterations=gap_px)
        y0, x0 = y - gap_px, x - gap_px
        ys = slice(max(0, y0), min(res, y0 + mg.shape[0]))
        xs = slice(max(0, x0), min(res, x0 + mg.shape[1]))
        occ[ys, xs] += sign * mg[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0]

    def attempt(scale):
        occ = np.zeros((res, res), np.float32)
        place = [None] * len(islands)
        for i in order:
            best = None
            for a, m, off in _island_masks(islands[i], scale * res, angles, 1):
                h, w = m.shape
                if h > res or w > res:
                    continue
                ov = fftconvolve(occ, m[::-1, ::-1].astype(np.float32), mode='valid')
                free = np.argwhere(ov < 0.5)
                if len(free) == 0:
                    continue
                key = (free[:, 0] + h) * res + free[:, 1]   # 上端が最も低く、同じなら左
                j = int(np.argmin(key))
                if best is None or key[j] < best[0]:
                    best = (key[j], a, m, int(free[j][0]), int(free[j][1]), off)
            if best is None:
                return None, None
            _, a, m, y, x, off = best
            stamp(occ, m, y, x)
            place[i] = [a, 1.0, (x + off[0], y + off[1]), m, y, x]
        return place, occ

    lo_s, hi_s = math.sqrt(0.5 / area), math.sqrt(0.95 / area)
    best = (lo_s, *attempt(lo_s))
    if best[1] is None:
        raise RuntimeError('UV の島が詰められない')
    for _ in range(steps):
        mid = (lo_s + hi_s) / 2
        pl, occ = attempt(mid)
        if pl is None:
            hi_s = mid
        else:
            lo_s = mid
            best = (mid, pl, occ)
    scale, place, occ = best
    # すき間に収まる限り島を大きくする
    first = list(grow_first or [])
    for i in first + [int(j) for j in order if int(j) not in first]:
        a, _, (cx, cy), m, y, x = place[i]
        stamp(occ, m, y, x, -1.0)
        for f in np.arange(grow_max, 1.0, -0.025):
            (_, m2, off2), = _island_masks(islands[i], scale * f * res, [a], 1)
            x2, y2 = int(round(cx - off2[0])), int(round(cy - off2[1]))
            h2, w2 = m2.shape
            if x2 < 0 or y2 < 0 or x2 + w2 > res or y2 + h2 > res:
                continue
            if (occ[y2:y2 + h2, x2:x2 + w2] * m2).sum() < 0.5:
                place[i] = [a, float(f), (x2 + off2[0], y2 + off2[1]), m2, y2, x2]
                m, y, x = m2, y2, x2
                break
        stamp(occ, m, y, x)
    return scale, [(p[0], p[1], (p[2][0] / res, p[2][1] / res)) for p in place]


def unwrap(obj, head_z: float, head_scale: float = 2.0, hand_scales=(1.0, 1.2, 1.35, 1.5),
           margins=(0.002, 0.0017, 0.0015), method: str = 'MINIMUM_STRETCH', target: float = 0.75
           ) -> tuple[dict, np.ndarray]:
    """obj（三角形のメッシュ）を部位の平面で切ってシームを入れ、展開し、頭の島を head_scale 倍にして詰める。

    margins は島の間のすき間（UV の幅の割合。2048 角で 0.002 = 約 4 画素）の候補。使われる面積が target 以上に
    なる組のうち、すき間の最も大きいものを選ぶ（どれも届かなければ、使われる面積の最も大きいもの）。
    """
    import bpy
    import bmesh
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    lab, names = cut_parts(bm, head_z)
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    tri = np.array([[v.index for v in f.verts] for f in bm.faces])
    lab = merge_fragments(lab, face_adjacency(tri))
    n_seam = 0
    for e in bm.edges:
        lf = e.link_faces
        s = len(lf) == 2 and lab[lf[0].index] != lab[lf[1].index]
        e.seam = s
        n_seam += s
    bm.to_mesh(me)
    bm.free()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method=method, fill_holes=True, correct_aspect=True, margin=0.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    # 島の大きさを決めて詰める。Blender の詰め方は島の大きさの組み合わせで結果が変わるので、手の倍率と
    # すき間をいくつか試し、UV の使われる面積が最も大きいものを選ぶ
    nl = len(me.loops)
    base = np.empty(nl * 2, np.float32)
    me.uv_layers.active.data.foreach_get('uv', base)
    base = base.reshape(-1, 2)
    loop_face = np.repeat(np.arange(len(me.polygons)), 3)
    loop_part = lab[loop_face]
    best = None
    tried = []
    for hs in hand_scales:
        for margin in margins:
            uvs = base.copy()
            for p, nm in enumerate(names):
                li = loop_part == p
                if not li.any():
                    continue
                sc = head_scale if nm.startswith('head') else hs if nm.startswith('hand') else 1.0
                c = uvs[li].mean(0)
                uvs[li] = (uvs[li] - c) * sc + c
            me.uv_layers.active.data.foreach_set('uv', uvs.ravel())
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', margin_method='FRACTION', margin=margin,
                                    shape_method='CONCAVE')
            bpy.ops.object.mode_set(mode='OBJECT')
            out = np.empty(nl * 2, np.float32)
            me.uv_layers.active.data.foreach_get('uv', out)
            t = out.reshape(-1, 3, 2)
            used = float(np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
                                - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1])).sum() / 2)
            tried.append((round(hs, 2), margin, round(used, 4)))
            key = (used >= target, margin if used >= target else 0.0, used)
            if best is None or key > best[4]:
                best = (used, out.copy(), hs, margin, key)
    me.uv_layers.active.data.foreach_set('uv', best[1])
    me.update()
    counts = {nm: int((lab == p).sum()) for p, nm in enumerate(names)}
    return {'method': f'plane cuts by body part (front/back halves), {method} unwrap, CONCAVE pack',
            'parts': counts, 'seam_edges': int(n_seam), 'head_scale': head_scale, 'hand_scale': best[2],
            'margin': best[3], 'pack_tries': tried}, lab
