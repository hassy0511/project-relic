"""平らに塗る：絵は「どこが何色か」を決めるのにだけ使い、部位ごとに spec の 1 色で塗る（texture.py から呼ぶ）。

前のやり方（texture.py の 'proj'）は、各方向の絵の色をそのまま面に貼っていた。絵どうしが数 cm 食い違い、
絵の陰影と筆のむらもそのまま写るので、しみ・むら（特に顔の縁・耳・もみあげ・ほお）が出た。
ナゴミ・閂のように「部位ごとに平らな色」にすると絵の画風（W0 A 案：平らな色、線なし）に合う。

■ 体（paint_body）
  1. 焼いた色（視点の多数決の色、texel ごと）を spec の色の表（PALETTE）のどれかに分ける。表の色を出発点に、
     実際の絵の色の中央値へ少し寄せながら 3 回分け直す（絵の陰影で暗い所も同じ色に入るように）。
  2. 面の上で掃除する：texel を 3D の小さな箱（CELL、部位と法線の向きも鍵）にまとめ、箱のつながり
     （3D の近さ・法線の近さ。UV の継ぎ目をまたぐ）の上で、多数決のぼかし → 小さな島（3D の面積が
     MIN_AREA より小さい）を周りの色へ併合する。バックル・膝の琥珀・指先などの小さな本物の模様は、
     色・部位ごとに小さい閾値にして残す。
  3. 各 texel の色は、近くの箱の色の重み付きの多数決で決め、境目だけ 2 色を細く混ぜる（なめらかな境目・
     アンチエイリアス）。陰影は焼かない（光はゲームが付ける）。
■ 顔（paint_face_atlas）
  顔の絵の 4 表情の 2×2 の画像：肌の色の画素 → 体と同じ平らな肌色（継ぎ目が出ない）。目・眉・まつ毛・口
  （肌に囲まれた小さな塊）は絵の色のまま。髪・ゴーグルなど大きな塊・縁に届く塊は色の表で平らに塗る。
  鼻・ほおの陰影・赤みは肌として消える。
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy import sparse  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from recon import char as CH  # noqa: E402

# spec_haru_3d.md の基準 hex（絵の色をスポイトしない。W0 の基準色）
PALETTE = CH.p('flat.PALETTE', {
    'brick': '#B75B43',      # 上着・ズボン・足首のカフ
    'ivory': '#F3E9D2',      # シャツ・肩板・太もも板・膝・すね側板・爪先・背中パネル
    'graphite': '#444641',   # 帯・手袋・暗い支持部・ゴーグル枠・靴底
    'brass': '#A98749',      # バックル・レール
    'umber': '#594333',      # 髪・襟・靴・すねの中央
    'amber': '#FFBC52',      # レンズ・膝の継ぎ目（ゲームで発光）
    'skin': '#E7B58D',       # 顔・指先・首
})
# 部位ごとに使わない色（uvparts.region_of_point：0 頭、1 胴、2/3 腕、4/5 手、6/7 脚）
FORBID = CH.p('flat.FORBID', {'0': ['ivory'], '4': ['brick', 'umber', 'amber'], '5': ['brick', 'umber', 'amber']})
# 髪・襟・靴・すねの中央の茶（umber）は、胴・腕では襟の高さより上、脚では膝より下だけ（絵の陰で暗くなった
# 上着の赤が茶に分けられて、帯の縁・脇にしみが出るのを防ぐ）
# （ハルの絵の襟の内側は上着の赤の陰なので、胴・腕には茶を使わない）
UMBER_Z = CH.p('flat.UMBER_Z', {'torso_min': 9.0, 'leg_max': 0.43})
# 首まわりのフードの襟（胴のうち、この高さより上で左右の中心に近い所）は暗い色（帯・茶）にしない（絵の陰のしみ）
NECK_NO_DARK = CH.p('flat.NECK_NO_DARK', {'z_min': 1.13, 'x': 0.075})
BOOST = CH.p('flat.BOOST', {'brass': 1.0, 'amber': 1.5})   # 多数決で細い模様（バックルの枠・琥珀の点）が消えないように
BRASS_TORSO_X = CH.p('flat.BRASS_TORSO_X', 0.03)
# 頭の琥珀（ゴーグルのレンズ）は、ぼかすと角が丸くなるので、箱の素の多数決のまま（レンズの角ばった形を残す）
SHARP_HEAD = CH.p('flat.SHARP_HEAD', ['amber'])
L_WEIGHT = 0.5          # 分けるときの明るさの差の重み（絵の陰影は主に明るさを変えるので軽く）
CENTER_PULL = 0.5       # 表の色から、分けた色の中央値へ寄せる割合
CELL = 0.003            # 掃除の箱の大きさ（m）
SMOOTH_ITERS = 4        # 多数決のぼかしの回数
SMOOTH_SIGMA = 1.0      # そのぼかしの幅（箱の何倍）
MIN_AREA = 3.5e-4       # これより小さい島（m²）は周りへ併合
MIN_AREA_LABEL = CH.p('flat.MIN_AREA_LABEL', {'brass': 0.4e-4, 'amber': 0.25e-4})
MIN_AREA_HAND = 0.3e-4  # 手（部位 4・5）の島の閾値（指先の肌・指の間）
MIN_AREA_HEAD = CH.p('flat.MIN_AREA_HEAD', {'default': 5e-4, 'amber': 1e-4})   # 頭（髪の先の肌色・ほおの髪の色のしみ）
EDGE_SIGMA = 1.0        # texel の色を決める近くの箱の重みの幅（箱の何倍）
EDGE_SHARP = 0.10       # 境目の混ぜる幅（2 色の重みの比 0.5 ± これ）


def log(msg: str) -> None:
    print(f'[flat {time.strftime("%H:%M:%S")}] {msg}', flush=True)


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB 0..1 → CIE Lab（D65）"""
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32)
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883], np.float32)
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def classify(col: np.ndarray, names: list[str], forbid: np.ndarray | None = None, iters: int = 3):
    """色 (n,3) → 色の表の番号。forbid (n, len(names)) の真の所は選ばない"""
    lb = lab(col.astype(np.float32))
    ref = lab(np.stack([hex_rgb(PALETTE[k]) for k in names]))
    cen = ref.copy()
    for _ in range(iters):
        d = lb[:, None, :] - cen[None]
        d[..., 0] *= L_WEIGHT
        d = (d ** 2).sum(-1)
        if forbid is not None:
            d[forbid] = 1e9
        lbl = np.argmin(d, 1)
        for i in range(len(names)):
            m = lbl == i
            if m.sum() > 100:
                cen[i] = ref[i] + CENTER_PULL * (np.median(lb[m], 0) - ref[i])
    return lbl, cen


# ---------------------------------------------------------------- 体

def paint_body(res: dict, mesh: dict) -> dict:
    t0 = time.time()
    names = list(PALETTE)
    pal = np.stack([hex_rgb(PALETTE[k]) for k in names])
    L = len(names)
    pos, nrm, col, reg = res['pos'], res['nrm'], res['col'], res['reg']
    verts, tris = mesh['verts'], mesh['tris']
    # texel の 3D の面積（三角形の面積 ÷ その三角形の texel の数）
    ta = 0.5 * np.linalg.norm(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]]), axis=1)
    cnt = np.bincount(res['tri'], minlength=len(tris))
    area = (ta / np.maximum(cnt, 1))[res['tri']]
    forbid = np.zeros((len(col), L), bool)
    for r, bad in FORBID.items():
        for k in bad:
            forbid[reg == int(r), names.index(k)] = True
    iu = names.index('umber')
    z = pos[:, 2]
    forbid[np.isin(reg, (1, 2, 3)) & (z < UMBER_Z['torso_min']), iu] = True
    forbid[np.isin(reg, (6, 7)) & (z > UMBER_Z['leg_max']), iu] = True
    neck = (reg == 1) & (z > NECK_NO_DARK['z_min']) & (np.abs(pos[:, 0]) < NECK_NO_DARK['x'])
    forbid[neck, names.index('graphite')] = True
    forbid[neck, iu] = True
    forbid[neck, names.index('brass')] = True
    # 真鍮は籠手のレール（腕・手）とバックル（胴の中心）だけ。帯の下の縁の陰が真鍮に分けられないように
    forbid[~np.isin(reg, (0, 2, 3, 4, 5)) & ~((reg == 1) & (np.abs(pos[:, 0]) < BRASS_TORSO_X)), names.index('brass')] = True
    lbl, cen = classify(col, names, forbid)
    # 頭の真鍮に近い色は、ゴーグルのレンズの縁の暗い琥珀（絵の陰）→ 琥珀
    lbl[(reg == 0) & (lbl == names.index('brass'))] = names.index('amber')
    log(f'分け {time.time() - t0:.0f}s：' + ', '.join(f'{k} {np.mean(lbl == i):.1%}' for i, k in enumerate(names)))

    # 箱（3D の位置・部位・法線の主な向き）
    q = np.floor(pos / CELL).astype(np.int64) + 2048
    ax = np.argmax(np.abs(nrm), 1)
    sg = (nrm[np.arange(len(nrm)), ax] > 0).astype(np.int64)
    key = ((q[:, 0] * 4096 + q[:, 1]) * 4096 + q[:, 2]) * 64 + reg.astype(np.int64) * 8 + ax * 2 + sg
    ukey, cell = np.unique(key, return_inverse=True)
    nc = len(ukey)
    carea = np.bincount(cell, area, nc)
    cpos = np.stack([np.bincount(cell, pos[:, i] * area, nc) for i in range(3)], 1) / carea[:, None]
    cnrm = np.stack([np.bincount(cell, nrm[:, i] * area, nc) for i in range(3)], 1)
    cnrm /= np.maximum(np.linalg.norm(cnrm, axis=1, keepdims=True), 1e-12)
    creg = np.bincount(cell, reg.astype(np.float64) * area, nc) / carea   # 箱は部位を鍵に含むので一つの値
    creg = np.rint(creg).astype(int)
    hist = np.zeros((nc, L))
    np.add.at(hist, (cell, lbl), area)
    log(f'箱 {nc:,}（{time.time() - t0:.0f}s）')

    # 箱のつながり
    tree = cKDTree(cpos)
    K = 20
    dist, nb = tree.query(cpos, k=K, distance_upper_bound=CELL * 2.6, workers=-1)
    ok = np.isfinite(dist) & (nb < nc)
    nb = np.where(ok, nb, 0)
    cosn = np.einsum('nkc,nc->nk', cnrm[nb], cnrm)
    ok &= cosn > 0.2
    w = np.where(ok, np.exp(-0.5 * (dist / (CELL * SMOOTH_SIGMA)) ** 2), 0.0)
    # 多数決のぼかし（面積で重み）
    boost = np.array([BOOST.get(k, 1.0) for k in names])
    p = hist / np.maximum(hist.sum(1, keepdims=True), 1e-12) * boost
    for _ in range(SMOOTH_ITERS):
        p = (w[..., None] * p[nb] * carea[nb][..., None]).sum(1)
        p /= np.maximum(p.sum(1, keepdims=True), 1e-12)
    clab = np.argmax(p, 1)
    raw = np.argmax(hist, 1)
    for k in SHARP_HEAD:
        i = names.index(k)
        m = (creg == 0) & ((raw == i) | (clab == i))
        clab[m] = raw[m]
    # 小さな島を周りへ併合
    rows = np.repeat(np.arange(nc), K)[ok.ravel()]
    cols = nb.ravel()[ok.ravel()]
    thr = np.array([MIN_AREA_LABEL.get(k, MIN_AREA) for k in names])
    thr_head = np.array([MIN_AREA_HEAD.get(k, MIN_AREA_HEAD['default']) for k in names])
    merged = 0
    for it in range(6):
        same = clab[rows] == clab[cols]
        g = sparse.coo_matrix((np.ones(same.sum()), (rows[same], cols[same])), shape=(nc, nc))
        ncomp, comp = connected_components(g, directed=False)
        comp_area = np.bincount(comp, carea, ncomp)
        comp_lab = np.zeros(ncomp, int)
        comp_lab[comp] = clab
        comp_hand = np.zeros(ncomp, bool)
        comp_hand[comp[np.isin(creg, (4, 5))]] = True
        comp_head = np.zeros(ncomp, bool)
        comp_head[comp[creg == 0]] = True
        cthr = np.where(comp_hand, np.minimum(thr[comp_lab], MIN_AREA_HAND), thr[comp_lab])
        cthr = np.where(comp_head, np.maximum(cthr, thr_head[comp_lab]), cthr)
        small = comp_area < cthr
        if not small.any():
            break
        # 島の縁の隣の色（自分の色以外、面積で重み）
        diff = ~same & small[comp[rows]]
        votes = np.zeros((ncomp, L))
        np.add.at(votes, (comp[rows[diff]], clab[cols[diff]]), carea[cols[diff]])
        has = votes.sum(1) > 0
        # 一番小さい島から：同じ回では、隣が自分より大きい島だけ
        tgt = np.argmax(votes, 1)
        change = small & has
        if not change.any():
            break
        clab = np.where(change[comp], tgt[comp], clab)
        merged += int(change.sum())
    log(f'小さな島の併合 {merged}（{time.time() - t0:.0f}s）')

    # texel の色：近くの箱の色の重み付きの多数決、境目だけ 2 色を細く混ぜる
    KT = 16
    dist, nbt = tree.query(pos, k=KT, workers=-1)
    wt = np.exp(-0.5 * (dist / (CELL * EDGE_SIGMA)) ** 2) * (np.einsum('nkc,nc->nk', cnrm[nbt], nrm) > 0.2)
    wt += 1e-9 * (np.arange(KT) == 0)
    pv = np.zeros((len(pos), L), np.float32)
    for k in range(KT):
        np.add.at(pv, (np.arange(len(pos)), clab[nbt[:, k]]), wt[:, k])
    o = np.argsort(-pv, 1)
    i1, i2 = o[:, 0], o[:, 1]
    p1 = pv[np.arange(len(pv)), i1]
    p2 = pv[np.arange(len(pv)), i2]
    t = p1 / np.maximum(p1 + p2, 1e-12)
    a = np.clip((t - 0.5) / (2 * EDGE_SHARP) + 0.5, 0, 1)
    a = a * a * (3 - 2 * a)
    out = a[:, None] * pal[i1] + (1 - a[:, None]) * pal[i2]
    res['col'] = out.astype(np.float32)
    res['flat_label'] = i1
    frac = {k: round(float((area * (i1 == i)).sum() / area.sum()), 4) for i, k in enumerate(names)}
    log(f'平らな色 {time.time() - t0:.0f}s：{frac}')
    return {'cells': int(nc), 'merged_islands': merged, 'area_fraction': frac,
            'centres_lab': {k: [round(float(v), 1) for v in cen[i]] for i, k in enumerate(names)}}


# ---------------------------------------------------------------- 顔

FACE_SKIN_D = (10.0, 18.0)   # 肌の度合い：肌の色からの差（明るさは L_WEIGHT_FACE 倍）がこの間で 1 → 0
L_WEIGHT_FACE = 0.6
FACE_FEATURE_MAX = 0.06      # 区画の面積のこれより小さく、区画の縁に届かない肌でない塊は、目・眉・口（絵の色のまま）
FACE_SPECK = 24              # これより小さな塊（画素）は肌へ
FACE_REGION = ['umber', 'skin']   # 顔の材質の所（顔の窓の中）にあるのは髪と肌だけ（ゴーグル・襟は窓の外）


def paint_face_atlas(atlas_p: str, meta: dict, out_p: str) -> str:
    t0 = time.time()
    rgb = np.asarray(Image.open(atlas_p).convert('RGB')).astype(np.float32) / 255.0
    H, W = rgb.shape[:2]
    lb = lab(rgb)
    skin_hex = hex_rgb(PALETTE['skin'])
    # 絵の肌の色（表の色の近くの画素の中央値）
    d0 = np.linalg.norm((lb - lab(skin_hex)) * [L_WEIGHT_FACE, 1, 1], axis=-1)
    ref = np.median(lb[d0 < 20], 0)
    d = np.linalg.norm((lb - ref) * [L_WEIGHT_FACE, 1, 1], axis=-1)
    s = 1.0 - np.clip((d - FACE_SKIN_D[0]) / (FACE_SKIN_D[1] - FACE_SKIN_D[0]), 0, 1)
    nonskin = s < 0.5
    feature = np.zeros((H, W), bool)
    region = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in meta['quadrants_atlas_px'].values():
        sub = nonskin[y0:y1, x0:x1]
        lab_, n = ndi.label(sub)
        if not n:
            continue
        sizes = ndi.sum(sub, lab_, range(1, n + 1))
        border = np.zeros(n + 1, bool)
        for edge in (lab_[0], lab_[-1], lab_[:, 0], lab_[:, -1]):
            border[edge] = True
        big = (sizes > FACE_FEATURE_MAX * sub.size) | border[1:]
        speck = sizes < FACE_SPECK
        # 目・眉・口は表情の範囲の中だけ（あごの下の陰などは肌）
        zx0, zy0, zx1, zy1 = meta['expression_zone_atlas_px']
        inzone = np.zeros(n + 1, bool)
        inzone[np.unique(lab_[zy0:zy1, zx0:zx1])] = True
        feat = ~big & ~speck & inzone[1:]
        feature[y0:y1, x0:x1] = np.isin(lab_, np.nonzero(feat)[0] + 1)
        region[y0:y1, x0:x1] = np.isin(lab_, np.nonzero(big)[0] + 1)
    # 大きな塊（髪・ゴーグルなど）は色の表で平らに（多数決で掃除し、境目は細く混ぜる）
    rl, _ = classify(rgb.reshape(-1, 3), FACE_REGION)
    rl = rl.reshape(H, W)
    rl[~region] = FACE_REGION.index('skin')
    pal = np.stack([hex_rgb(PALETTE[k]) for k in FACE_REGION])
    onehot = np.stack([ndi.gaussian_filter((rl == i).astype(np.float32), 3.0) for i in range(len(FACE_REGION))], -1)
    rl = np.argmax(onehot, -1)
    soft = np.stack([ndi.gaussian_filter((rl == i).astype(np.float32), 0.9) for i in range(len(FACE_REGION))], -1)
    flat = (soft[..., :, None] * pal[None, None]).sum(-2) / np.maximum(soft.sum(-1, keepdims=True), 1e-6)
    # 目・眉・口：絵の色のまま。縁の画素（肌との混ざり）だけ、肌の度合い s で平らな肌色と混ぜる
    near_f = ndi.binary_dilation(feature, iterations=2)
    sf = np.where(near_f, s, 1.0)[..., None]
    out = np.where(near_f[..., None], sf * skin_hex + (1 - sf) * rgb, flat)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out_p)
    log(f'顔の画像 {out_p}：目・眉・口 {feature.mean():.2%}、髪など {(rl != FACE_REGION.index("skin")).mean():.1%}'
        f'（{time.time() - t0:.0f}s）')
    return out_p


if __name__ == '__main__':   # 調べ物用：保存した焼いた色（TEX_DUMP）と顔の画像で試す
    import json
    work = os.path.join(CH.REPO, CH.CFG['work'])
    tex = os.path.join(work, 'tex')
    out_dir = sys.argv[1] if len(sys.argv) > 1 else tex
    meta = json.load(open(os.path.join(work, 'face_atlas.json')))
    paint_face_atlas(os.path.join(work, meta['atlas_file']), meta, os.path.join(out_dir, 'face_atlas_flat_test.png'))
    c = np.load(os.path.join(tex, 'res_cache.npz'))
    res = {k: c[k] for k in ('pix', 'tri', 'bar', 'pos', 'nrm', 'col', 'reg')}
    res['size'] = 2048
    mesh = {'verts': c['verts'], 'tris': c['tris']}
    print(paint_body(res, mesh))
    from recon import texture as T
    T.save_png(os.path.join(out_dir, 'flat_test.png'), T.to_image(res, res['col']))
