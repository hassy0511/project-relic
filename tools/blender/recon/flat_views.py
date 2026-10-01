"""体（頭より下）を、視点の多数決でなく「1 つの絵のきれいな形」で塗る（flat.paint_body から呼ぶ。4 回目の直し）。

前のやり方（flat.paint_body の多数決）は、texel ごとに数 cm 食い違う何枚もの絵の色を混ぜて決めていたので、
袖口・白い板・肩ひも・帯・ポケットの蓋・膝当て・靴のカフ・手袋の縁の境目がどれもゆらぎ、にじみ・まだらが出た。
顔がきれいなのは、1 枚のきれいな絵の線をそのまま使っているから。体も同じにする：

  1. 絵ごとの色の地図（view_map）：正面・背面・右の真横（腕の無い絵）・左の真横・右の真横（腕だけ）の絵を、
     spec の 7 色に 2D で分け、2D で掃除し（多数決のぼかし・小さな島の併合）、色の塊ごとの輪郭を
     ベクトルの多角形にする（輪郭を少しなめらかにしてから Douglas-Peucker で間引く：直線は直線、角は角のまま）。
     多角形を 4 倍の細かさで塗り（大きい塊から先、小さい塊を上に）、画素ごとの色の割合（アンチエイリアス）にする。
  2. texel ごとに、どの 1 枚の絵から色をもらうかを決める（choose_view）：なめらかにした法線（NRM_SIGMA の近所の平均。
     面の凸凹で選ぶ絵がちらつかないように）がいちばん向いている絵で、その絵から見えていて（奥行きの比べ）、
     絵の外形の中に落ちる所。絵どうしは混ぜない（境目は 1 枚の絵の線だけ）。
  3. 部位の決まり（rules）：胴・脚に肌なし、胴・腕に茶なし、脚の茶は膝より下、真鍮は籠手とバックルだけ、
     袖口より先の腕は赤なし（背面の絵の陰の肌が赤に分けられる）。禁じた色は 2 番目の色へ。
頭（部位 0）はこれまでのまま（形の部品で塗る。承認済み）。前のやり方は flat.BODY_PAINT="vote" か環境変数 FLAT_BODY=vote。
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from recon import char as CH  # noqa: E402

# 視点：その絵が使える部位（'body' 腕・手のほか、'all' すべて、'right_arm' 右腕・右手だけ）
VIEWS = CH.p('flat_views.VIEWS', {'front': 'all', 'back': 'all', 'side_right_noarms': 'body', 'side_left': 'all',
                                  'side_right': 'right_arm'})
# 正面・背面の絵を優先する（横の絵は、横を向いた面だけ：約 60 度より横。肩ひも・肩板の絵どうしの食い違いの継ぎ目を減らす）
PREFER = CH.p('flat_views.PREFER', {'front': 0.2, 'back': 0.2})
NRM_SIGMA = 0.035     # 絵を選ぶ法線のなめらかさ（m）
OCC_TOL = 0.012       # 見えるかの奥行きの許し（m）
SEAM = 0.05          # 絵の切り替わりで 2 枚を混ぜる幅（向きの差）
FACE_MIN = 0.3       # 絵がこれより斜めに見ている面（約 72 度より斜め）は、その絵から色を引かない
WIDE_PX = 8.0        # 禁じた色の代わりの色を探す近所の広さ（絵の画素）
AA_PX = 1.1          # 色の地図の境目のなめらかさ（絵の画素。アンチエイリアス）
SS = 4                # 多角形を塗る細かさ（絵の画素の何分の 1）
MODE_SIGMA = 1.5      # 2D の多数決のぼかし（画素）
PRE_SIGMA = 1.0       # 輪郭を取る前のなめらかさ（画素）
POLY_TOL = 1.2        # 輪郭の間引きの許し（画素。これより小さいゆらぎは直線に）
MIN_PX = CH.p('flat_views.MIN_PX', {'default': 200, 'brass': 12, 'amber': 12})   # これより小さな塊（画素）は周りへ
L_WEIGHT = 0.3
# 部位の決まり
SKIN_NECK = CH.p('flat_views.SKIN_NECK', {'z_min': 1.10, 'x': 0.07})      # 胴の肌は首の前・後ろのここだけ
LEG_UMBER_Z = CH.p('flat_views.LEG_UMBER_Z', 0.43)                         # 脚の茶は膝より下
# 腕の軸（A ポーズ。左腕、右は x を反転）：肩の関節 → ひじ。袖口（赤の終わり）は肩から SLEEVE_S（m）
ARM_AXIS = CH.p('flat_views.ARM_AXIS', {'shoulder': (0.137, 0.031, 1.105), 'elbow': (0.245, 0.055, 0.912)})
SLEEVE_S = CH.p('flat_views.SLEEVE_S', 0.205)
BRASS_TORSO_X = CH.p('flat_views.BRASS_TORSO_X', 0.035)
# 輪の決まり（絵で測った高さ・長さ。境目は面を切る平面なので、ぐるりと真っすぐ・同じ太さ）
#   帯：前 z 0.812〜0.856、後ろ 0.822〜0.872（前後の向きの角度で間を取る）。帯の中はグラファイト（バックルの真鍮は絵のまま）、
#       帯の下 margin の中の中心の幅（|x| < pouch_x。横はポーチが下がる）はグラファイトなし
#   脚：ズボンの裾 hem より下に赤なし、上に茶・琥珀なし。靴のカフ cuff は赤の輪。靴底（前 sole_front・後ろ sole_back より下）は
#       グラファイトの輪、靴の甲（靴底とカフの間）にグラファイトなし
#   袖：肩から腕の軸に沿って cuff の間はグラファイトの輪（袖口）、手前に肌なし、先に赤なし
#       袖口の先 forearm_skin は肌の輪。右腕は手袋の手前 forearm_skin_right まで肌（グラファイト・アイボリーなし）
#   手：手首の関節から手の向きに fingers より先は肌（指。指の出る手袋）、palm より手前（手首から）は肌なし
RINGS = CH.p('flat_views.RINGS', {
    'belt_front': (0.812, 0.856), 'belt_back': (0.822, 0.872), 'belt_margin': 0.02, 'pouch_x': 0.10,
    'hem': 0.474, 'boot_cuff': (0.155, 0.205), 'sole_front': 0.032, 'sole_back': 0.054,
    'sleeve_cuff': (0.177, 0.205), 'forearm_skin': (0.205, 0.24), 'forearm_skin_right': 0.37,
    'wrist': (0.335, 0.0302, 0.755), 'hand_end': (0.4, 0.0045, 0.642), 'fingers': 0.14, 'palm': (-0.02, 0.12),
    'aa': 0.003})


DEBUG: dict = {}   # 調べ物用（どの texel がどの絵から色をもらったか）


def log(msg: str) -> None:
    print(f'[flat_views {time.strftime("%H:%M:%S")}] {msg}', flush=True)


# ---------------------------------------------------------------- 1. 絵ごとの色の地図

def _merge_small(lab2: np.ndarray, oh: np.ndarray, names: list[str]) -> int:
    merged = 0
    for _ in range(3):
        changed = False
        for i in range(len(names)):
            m = lab2 == i
            if not m.any():
                continue
            cc, n = ndi.label(m)
            if not n:
                continue
            sizes = ndi.sum(m, cc, range(1, n + 1))
            lim = MIN_PX.get(names[i], MIN_PX['default'])
            small = np.isin(cc, np.nonzero(sizes < lim)[0] + 1)
            if small.any():
                oh2 = oh.copy()
                oh2[i] = -1
                lab2[small] = np.argmax(oh2, 0)[small]
                merged += int((sizes < lim).sum())
                changed = True
        if not changed:
            break
    return merged


def view_map(view: str, names: list[str], classify) -> tuple[np.ndarray, tuple[int, int], dict]:
    """絵 → 色ごとの割合の地図 (L, h, w) uint8（0..SS²）と、その左上 (y0, x0)"""
    from skimage import measure
    t0 = time.time()
    path = os.path.join(CH.REPO, CH.CFG['work'], 'src', CH.CFG['views'][view]['file'])
    rgba = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32) / 255.0
    opaque = rgba[..., 3] > 0.5
    ys, xs = np.nonzero(opaque)
    y0, y1, x0, x1 = max(ys.min() - 4, 0), min(ys.max() + 5, rgba.shape[0]), max(xs.min() - 4, 0), min(xs.max() + 5, rgba.shape[1])
    sub, op = rgba[y0:y1, x0:x1], opaque[y0:y1, x0:x1]
    L = len(names)
    li, _ = classify(sub[..., :3][op], names, l_weight=L_WEIGHT)
    lab2 = np.full(op.shape, -1, int)
    lab2[op] = li
    oh = np.stack([ndi.gaussian_filter((lab2 == i).astype(np.float32), MODE_SIGMA) for i in range(L)], 0)
    lab2 = np.where(op, np.argmax(oh, 0), -1)
    merged = _merge_small(lab2, oh, names)
    # 塊ごとの輪郭 → 多角形（大きい順に塗る）
    polys = []
    for i in range(L):
        cc, n = ndi.label(lab2 == i)
        objs = ndi.find_objects(cc)
        for k, sl in enumerate(objs):
            if sl is None:
                continue
            m = np.pad((cc[sl] == k + 1).astype(np.float32), 2)
            area = float(m.sum())
            cs = measure.find_contours(ndi.gaussian_filter(m, PRE_SIGMA), 0.5)
            if not cs:
                continue
            c = max(cs, key=lambda c: abs(np.sum(c[:-1, 0] * c[1:, 1] - c[1:, 0] * c[:-1, 1])))
            c = measure.approximate_polygon(c, POLY_TOL)
            if len(c) < 3:
                continue
            # (行, 列)（画素 i の中心 = i）→ 連続座標（中心 = i+0.5）の SS 倍
            yy = (c[:, 0] - 2 + sl[0].start + 0.5) * SS
            xx = (c[:, 1] - 2 + sl[1].start + 0.5) * SS
            polys.append((area, i, list(zip(xx.tolist(), yy.tolist()))))
    polys.sort(key=lambda p: -p[0])
    h, w = op.shape
    im = Image.new('L', (w * SS, h * SS), 255)
    dr = ImageDraw.Draw(im)
    for _, i, pts in polys:
        dr.polygon(pts, fill=i)
    big = np.asarray(im).copy()
    # 多角形どうしのすき間（どれも塗らなかった所）は一番近い塗った色
    hole = big == 255
    if hole.any():
        idx = ndi.distance_transform_edt(hole, return_distances=False, return_indices=True)
        big = big[idx[0], idx[1]]
    # 外形は絵の不透明の所（SS 倍に拡大）
    opb = np.repeat(np.repeat(op, SS, 0), SS, 1)
    big = np.where(opb, big, 255)
    cov = np.stack([(big == i).reshape(h, SS, w, SS).sum((1, 3)).astype(np.uint8) for i in range(L)], 0)
    log(f'{view}：{len(polys)} 多角形、小さな島 {merged}（{time.time() - t0:.0f}s）')
    return cov, (int(y0), int(x0)), {'polygons': len(polys), 'merged_2d': merged, 'labels': lab2}


# ---------------------------------------------------------------- 2. texel ごとに 1 枚の絵を選ぶ

def smooth_normals(pos: np.ndarray, nrm: np.ndarray, sigma: float) -> np.ndarray:
    step = max(1, len(pos) // 40_000)   # 近所を広く取るため間引く（約 7mm おき）
    sub = np.arange(0, len(pos), step)
    tree = cKDTree(pos[sub])
    d, nb = tree.query(pos, k=24, distance_upper_bound=2.5 * sigma, workers=-1)
    ok = nb < len(sub)
    nb = np.where(ok, nb, 0)
    nn = nrm[sub][nb]
    w = np.where(ok, np.exp(-0.5 * (d / sigma) ** 2), 0.0) * (np.einsum('nkc,nc->nk', nn, nrm) > 0.0)
    ns = (w[..., None] * nn).sum(1) + 1e-3 * nrm
    return ns / np.maximum(np.linalg.norm(ns, axis=1, keepdims=True), 1e-12)


def arm_s(pos: np.ndarray) -> np.ndarray:
    """腕の軸に沿った、肩の関節からの距離（m）。左右は |x| で"""
    a = np.array(ARM_AXIS['shoulder'], float)
    b = np.array(ARM_AXIS['elbow'], float)
    d = (b - a) / np.linalg.norm(b - a)
    p = pos.copy()
    p[:, 0] = np.abs(p[:, 0])
    return (p - a) @ d


ISLAND = CH.p('flat_views.ISLAND', {'cell': 0.003, 'default': 1.5e-4, 'brass': 0.1e-4, 'amber': 0.1e-4})


def island_merge(p, ns, rg, res, mesh, sel, cov, names) -> int:
    """面の上の小さな色の島（絵の継ぎ目・斜めの所の切れ端）を周りの色へ。3mm の箱のつながりの上で数え、
    島の色の texel だけを周りの色に塗り替える（ほかの境目の線は動かさない）"""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    verts, tris = mesh['verts'], mesh['tris']
    ta = 0.5 * np.linalg.norm(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]]), axis=1)
    cnt = np.bincount(res['tri'], minlength=len(tris))
    area = (ta / np.maximum(cnt, 1))[res['tri'][sel]]
    L = len(names)
    lab = np.argmax(cov, 1)
    cs = ISLAND['cell']
    q = np.floor(p / cs).astype(np.int64) + 2048
    ax = np.argmax(np.abs(ns), 1)
    sg = (ns[np.arange(len(ns)), ax] > 0).astype(np.int64)
    key = ((q[:, 0] * 4096 + q[:, 1]) * 4096 + q[:, 2]) * 64 + rg.astype(np.int64) * 8 + ax * 2 + sg
    ukey, cell = np.unique(key, return_inverse=True)
    nc = len(ukey)
    carea = np.bincount(cell, area, nc)
    cpos = np.stack([np.bincount(cell, p[:, i] * area, nc) for i in range(3)], 1) / carea[:, None]
    cn = np.stack([np.bincount(cell, ns[:, i] * area, nc) for i in range(3)], 1)
    cn /= np.maximum(np.linalg.norm(cn, axis=1, keepdims=True), 1e-12)
    hist = np.zeros((nc, L))
    np.add.at(hist, (cell, lab), area)
    clab = np.argmax(hist, 1)
    old = clab.copy()
    tree = cKDTree(cpos)
    K = 16
    d, nb = tree.query(cpos, k=K, distance_upper_bound=cs * 2.6, workers=-1)
    ok = (nb < nc)
    nb = np.where(ok, nb, 0)
    ok &= np.einsum('nkc,nc->nk', cn[nb], cn) > 0.2
    rows = np.repeat(np.arange(nc), K)[ok.ravel()]
    cols = nb.ravel()[ok.ravel()]
    thr = np.array([ISLAND.get(k, ISLAND['default']) for k in names])
    merged = 0
    for _ in range(6):
        same = clab[rows] == clab[cols]
        g = sparse.coo_matrix((np.ones(same.sum()), (rows[same], cols[same])), shape=(nc, nc))
        ncomp, comp = connected_components(g, directed=False)
        comp_area = np.bincount(comp, carea, ncomp)
        comp_lab = np.zeros(ncomp, int)
        comp_lab[comp] = clab
        small = comp_area < thr[comp_lab]
        diff = ~same & small[comp[rows]]
        votes = np.zeros((ncomp, L))
        np.add.at(votes, (comp[rows[diff]], clab[cols[diff]]), carea[cols[diff]])
        change = small & (votes.sum(1) > 0)
        if not change.any():
            break
        clab = np.where(change[comp], np.argmax(votes, 1)[comp], clab)
        merged += int(change.sum())
    moved = (clab[cell] != old[cell]) & (lab == old[cell])
    one = np.zeros((int(moved.sum()), L), np.float32)
    one[np.arange(len(one)), clab[cell[moved]]] = 1.0
    cov[moved] = one
    log(f'面の上の小さな島 {merged}（texel {int(moved.sum()):,}）')
    return merged


def paint(res: dict, mesh: dict, cams: dict, names: list[str], pal: np.ndarray, classify,
          regions=(1, 2, 3, 4, 5, 6, 7)) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """体の texel の色。返り値 (texel の番号, 色 (n,3), 色の番号 (n,), 記録)"""
    from recon import texture as T
    t0 = time.time()
    pos, nrm, reg = res['pos'], res['nrm'], res['reg']
    verts, tris = mesh['verts'], mesh['tris']
    sel = np.nonzero(np.isin(reg, regions))[0]
    p, rg = pos[sel], reg[sel]
    ns = smooth_normals(p, nrm[sel], NRM_SIGMA)
    log(f'法線のなめらか {len(sel):,} texel（{time.time() - t0:.0f}s）')
    treg = T.tri_regions(verts, tris)
    L = len(names)
    best = np.full(len(sel), -np.inf)
    cov = np.zeros((len(sel), L), np.float32)
    covw = np.zeros((len(sel), L), np.float32)
    best2 = np.full(len(sel), -np.inf)
    cov2 = np.zeros((len(sel), L), np.float32)
    covw2 = np.zeros((len(sel), L), np.float32)
    who = np.full(len(sel), -1, np.int8)
    stats = {}
    vlist = [v for v in VIEWS if v in cams and v in CH.CFG['views']]
    for vi, view in enumerate(vlist):
        use = VIEWS[view]
        cam = cams[view]
        allow = np.ones(len(sel), bool)
        tmask = np.ones(len(tris), bool)
        if use == 'body':
            allow = ~np.isin(rg, (2, 3, 4, 5))
            tmask = ~np.isin(treg, (2, 3, 4, 5))
        elif use == 'right_arm':
            allow = np.isin(rg, (2, 4))
        cmap, (y0, x0), st = view_map(view, names, classify)
        stats[view] = {k: v for k, v in st.items() if k != 'labels'}
        zb = T.zbuffer(verts, tris[tmask], cam)
        u, v = cam.project(p)
        t = p @ cam.d
        zr = T.nearest(zb, u, v, fill=np.inf)
        zmin = T.nearest(ndi.grey_erosion(np.where(np.isfinite(zb), zb, 1e9), size=3), u, v, fill=1e9)
        zr = np.where(np.isfinite(zr), zr, zmin)
        vis = t <= zr + OCC_TOL
        # 境目を texel 1〜2 個の幅でなめらかに（アンチエイリアス。絵の画素 0.86mm、体の texel 約 1.1mm）
        cmf = np.stack([ndi.gaussian_filter(m.astype(np.float32) / (SS * SS), AA_PX) for m in cmap], -1)
        c = T.bilinear(cmf, u - x0, v - y0)
        cmf = np.stack([ndi.gaussian_filter(m.astype(np.float32) / (SS * SS), WIDE_PX) for m in cmap], -1)
        cw = T.bilinear(cmf, u - x0, v - y0)
        del cmf
        inside = (c.sum(1) > 0.5) & (u - x0 > 0) & (v - y0 > 0) & (u - x0 < cmap.shape[2]) & (v - y0 < cmap.shape[1])
        face = -(ns @ cam.d) + PREFER.get(view, 0.0)
        ok = allow & vis & inside & (face - PREFER.get(view, 0.0) > FACE_MIN)
        take = ok & (face > best)
        sec = ok & ~take & (face > best2)
        # 1 番目を 2 番目へ送る
        best2[take], cov2[take], covw2[take] = best[take], cov[take], covw[take]
        best[take] = face[take]
        cov[take] = c[take]
        covw[take] = cw[take]
        who[take] = vi
        best2[sec], cov2[sec], covw2[sec] = face[sec], c[sec], cw[sec]
        stats[view]['texels'] = int(take.sum())
        log(f'{view}：見えて向いている {int(ok.sum()):,}（{time.time() - t0:.0f}s）')
    # 絵の切り替わりの所（2 枚の絵がほぼ同じだけ向いている）は、細い幅だけ 2 枚を混ぜる（切り替わりの線のアンチエイリアス）
    with np.errstate(invalid='ignore'):
        wsw = np.clip((best - best2) / SEAM + 0.5, 0, 1)[:, None]
    wsw[~np.isfinite(best2)] = 1.0
    cov = wsw * cov + (1 - wsw) * cov2
    covw = wsw * covw + (1 - wsw) * covw2
    del cov2, covw2
    # どの絵もよく見ていない texel（わきの下・股・肩の上・靴底など）は、絵を斜めに引かず、面の上で一番近い塗った texel の色
    none = who < 0
    DEBUG['who'], DEBUG['sel'] = who.copy(), sel
    stats['fallback_texels'] = int(none.sum())
    if none.any() and (~none).any():
        kn = np.nonzero(~none)[0]
        tree = cKDTree(p[kn])
        qi = np.nonzero(none)[0]
        d, nb = tree.query(p[qi], k=8, workers=-1)
        good = np.einsum('qkc,qc->qk', ns[kn[nb]], ns[qi]) > 0.2
        pick = np.where(good.any(1), np.argmax(good, 1), 0)
        src = kn[nb[np.arange(len(qi)), pick]]
        cov[qi] = cov[src]
        covw[qi] = covw[src]
    # 3. 部位の決まり
    z = p[:, 2]
    R = RINGS
    aa = R['aa']
    ix = {k: i for i, k in enumerate(names)}
    legs = np.isin(rg, (6, 7))
    arms = np.isin(rg, (2, 3))
    hands = np.isin(rg, (4, 5))
    sa = arm_s(p)
    wr = np.array(R['wrist'], float)
    hd = np.array(R['hand_end'], float) - wr
    hd /= np.linalg.norm(hd)
    ph = p.copy()
    ph[:, 0] = np.abs(ph[:, 0])
    uh = (ph - wr) @ hd
    # 帯・靴底の高さ（前後の向きの角度で前の値と後ろの値の間）
    cphi = -(p[:, 1] - 0.01) / np.maximum(np.hypot(p[:, 0], p[:, 1] - 0.01), 1e-6)
    tb = (1 - cphi) / 2
    blo = R['belt_front'][0] + tb * (R['belt_back'][0] - R['belt_front'][0])
    bhi = R['belt_front'][1] + tb * (R['belt_back'][1] - R['belt_front'][1])
    sole = R['sole_front'] + tb * (R['sole_back'] - R['sole_front'])
    belt_zone = np.isin(rg, (1, 6, 7))

    def below(x, t):   # x < t で 1（縁は aa の幅でなめらか）。禁じる所の境目もアンチエイリアス
        return np.clip((t - x) / aa + 0.5, 0, 1)

    # 禁じる度合い（0..1）
    forbid = np.zeros((len(sel), L), np.float32)

    def fb(k, w):
        forbid[:, ix[k]] = np.maximum(forbid[:, ix[k]], w.astype(np.float32))
    neck = (z > SKIN_NECK['z_min']) & (np.abs(p[:, 0]) < SKIN_NECK['x'])
    fb('skin', (rg == 1) & ~neck)
    fb('skin', legs)
    fb('umber', np.isin(rg, (1, 2, 3)))
    fb('brick', hands)
    fb('umber', hands)
    fb('brass', np.isin(rg, (1, 6, 7)) & ~((rg == 1) & (np.abs(p[:, 0]) < BRASS_TORSO_X)))
    fb('brick', arms * below(-sa, -SLEEVE_S))                     # 袖口より先の腕に赤なし（背面の絵の陰の肌）
    fb('skin', arms * below(sa, R['sleeve_cuff'][0] + aa / 2))     # 袖の中に肌なし
    right_forearm = arms * (p[:, 0] < 0) * below(-sa, -R['forearm_skin'][1]) * below(sa, R['forearm_skin_right'])
    for k in ('graphite', 'ivory', 'brass', 'amber'):
        fb(k, right_forearm)
    fb('brick', legs * below(z, R['hem']))                         # 裾より下に赤なし
    fb('umber', legs * below(-z, -R['hem']))                       # 裾より上に茶・琥珀なし
    fb('amber', legs * below(-z, -R['hem']))
    fb('skin', hands * below(-uh, -R['palm'][0]) * below(uh, R['palm'][1]))
    fb('graphite', belt_zone * below(z, blo + aa / 2) * (z > blo - R['belt_margin']) * (np.abs(p[:, 0]) < R['pouch_x']))
    fb('graphite', legs * below(-z, -(sole - aa / 2)) * below(z, R['boot_cuff'][0] + aa / 2))
    default = np.where(hands, ix['graphite'], np.where(arms & (sa > SLEEVE_S), ix['skin'], ix['brick']))
    default = np.where(legs & (z < R['hem']), ix['umber'], default)
    # 禁じた色の分は、絵の近所（covw：広くぼかした地図）のほかの色へ。近所にも無ければ部位の決まった色へ
    lost = (cov * forbid).sum(1, keepdims=True)
    cov = cov * (1 - forbid)
    rep = covw * (1 - forbid)
    rs = rep.sum(1, keepdims=True)
    dflt = np.zeros_like(cov)
    dflt[np.arange(len(cov)), default] = 1.0
    rep = np.where(rs > 1e-3, rep / np.maximum(rs, 1e-9), dflt)
    cov = cov + lost * rep
    cov /= np.maximum(cov.sum(1, keepdims=True), 1e-9)
    stats['forbidden_moved'] = int((lost[:, 0] > 0.5).sum())

    def band(x, lo, hi):   # lo〜hi の中で 1（縁は aa の幅でなめらか）
        a = np.clip((x - lo) / aa + 0.5, 0, 1) * np.clip((hi - x) / aa + 0.5, 0, 1)
        return (a * a * (3 - 2 * a))[:, None]

    def force(mask, a, k, keep=None):
        a = a * mask[:, None]
        one = np.zeros((1, L), np.float32)
        one[0, k] = 1.0
        tgt = np.repeat(one, len(cov), 0)
        if keep is not None:   # その色は絵のまま（帯のバックル）
            kk = cov[:, keep:keep + 1]
            tgt = tgt * (1 - kk)
            tgt[:, keep] += kk[:, 0]
        cov[:] = a * tgt + (1 - a) * cov
        return int((a[:, 0] > 0.5).sum())
    stats['rings'] = {
        'belt': force(belt_zone, band(z, blo, bhi), ix['graphite'], keep=ix['brass']),
        'boot_cuff': force(legs, band(z, *R['boot_cuff']), ix['brick']),
        'sleeve_cuff': force(arms, band(sa, *R['sleeve_cuff']), ix['graphite']),
        'forearm_skin': force(arms, band(sa, *R['forearm_skin']), ix['skin']),
        'fingers': force(hands, band(uh, R['fingers'], 9.0), ix['skin']),
        'sole': force(legs, band(z, -1.0, sole), ix['graphite']),
    }
    stats['islands_3d'] = island_merge(p, ns, rg, res, mesh, sel, cov, names)
    col = cov @ pal
    lbl = np.argmax(cov, 1)
    stats['per_view_fraction'] = {v: round(float(np.mean(who == i)), 4) for i, v in enumerate(vlist)}
    log(f'体 {time.time() - t0:.0f}s：{stats["per_view_fraction"]}、どの絵にも無い {stats["fallback_texels"]:,}')
    return sel, col, lbl, stats
