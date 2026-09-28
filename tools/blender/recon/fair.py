"""なめらかな形の場：絵の外形をふくらませた「レンズ」（体、首より下）＋ 頭と髪（hair.py）。

carve.py の 2（hull）から呼ばれる。以前の方法（輪切りごとに断面を当てはめる）は、隣の輪切りと判断が
食い違って横筋・段・ひれが出た。ここでは、2 次元の絵から作った場を視線に沿って延ばして形を組み立てるので、
輪切りごとの判断がなく、上下にもなめらかになる。場はすべて符号つき距離（m、内側が正）。

■ 1. 目標の外形（target_sdf）と視体積の場（hull_field）
  外形のマスクの符号つき距離（画素）を少しぼかす（体 6 画素・頭 3 画素。手首より先の高さはぼかさない：指の
  間を埋めない。籠手やカフの高さはぼかす：段が面に刻まれないように）。頭（あごより上）は、房の間の切り欠きを半径 2cm の円で閉じた外形（closed_masks）を使う。
  視体積の場 D = 正面と右真横の外形の符号つき距離を視線に沿って延ばした最小（TRIM_VIEWS）。
  外形の距離は視線に垂直な面の中の距離なので、D の削り込み {D ≥ r} は視体積の正確な削り込み。
  右前斜めの視体積では切らない：切ると腕・脚・胴の断面に平らな面と折れ目（くさび形）が残る（審査の指摘）。
  右前斜めの外形には、面の段（snap.py）で輪郭線だけをなめらかに合わせる。

■ 2. 体：ふくらみのレンズ（Lens）
  外形の「ふくらみ」h（poisson_height）：∇²f = -1 を外形の中で解き h = √(2f)。幅 2a の帯なら
  h = √(a² - x²) で、腕・脚・指・袖は丸い断面になる（距離変換と違い中心線の折れ目がない）。
  正面のレンズ：点 (x, y, z) は、正面の絵の画素 (x, z) の h と、奥行きの中心 c(z)（右真横の絵のその高さの行の
  前後の中点）から、前は c - y ≤ h·Sf、後ろは y - c ≤ h·Sb なら内側。Sf, Sb は奥行きのならし：その高さで
  最も太い所（胴・腰）は、前後の厚みが右真横の絵の前・後ろの端にちょうど届く倍率（上下に 3cm でならす）、
  細い所（腕・指・胴の脇）は 1（丸いまま）。股より下（LEG_Z）は行のすべて（両脚）に同じ倍率をかけ、1.5 倍まで
  太らせてもよい（脚は正面の幅と真横の奥行きの楕円の断面）。胴は角の丸い箱形、腕・指は丸い断面、上着の裾・ベルト・
  カフの段は体を一周する帯になる。靴（くるぶしより下）はレンズを使わず視体積のまま（絵でも角ばっている）。
  頭の高さでは真横のレンズも、なめらかな最大（幅 8mm）で足す（首より上は 3 で置き換わる）。最後に D で切る。

■ 3. 首より上
  体のレンズの上を、えり・フードの上の縁の高さ BODY_TOP（1.203m）の面で切り、視体積 D で切る（体だけ）。
  首より上（頭・顔・首・髪の帽子・房）は hair.build_head の場で、体の場となめらかな和（幅 8mm）でつなぐ。
  頭は視体積で切らない（視体積の面が角ばった箱・くさび形の顔・ひれの房の元だった）。以前の「丸い芯＋房の
  レンズ」の頭は git の履歴（コミット e576142）にある。

■ 5. 面（mesh_of、carve.py の 3）
  場をマーチングキューブで面にし、Taubin で 10 回ならす。そのあと snap.fair_mesh で、面をなめらかにしながら
  外形の縁（輪郭線）だけを絵の外形に合わせる（実の 3 視点の外形の一致を保つ。頭は動かさない）。

  python tools/blender/recon/fair.py --name test   （実験用：場から面まで作り、なめる光の確認画像を
                                                    build/recon/fair/test_*.png に描く。成果物は上書きしない）
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy import sparse  # noqa: E402

from recon import views as V  # noqa: E402

REAL = ('front', 'side_right', 'three_quarter')
T0 = time.time()

# 部位の境（m）。頭はあご（身長 / 4.4 頭身）より少し上から、手は手首より先
HEAD_Z = (1.19, 1.24)          # 体のレンズに真横のレンズを足し始める高さ（首より上は hair.py の頭に置き換わる）
BODY_TOP = 1.203               # 体の場の上の端（えり・フードの上の縁）。これより上は hair.py の頭
TRIM_VIEWS = ('front', 'side_right')   # 体を切る視体積の視点
LEG_Z = (0.54, 0.59)          # これより下（股より下）は脚：行のすべてに同じ奥行きの倍率
LEG_DEPTH_MAX = 1.5            # 脚の奥行きの倍率の上限（丸い断面より太らせてよい）
HAND_ROWS = (0.60, 0.77)       # この高さの間の行（手首より先の手と指）は、目標の外形をならさない（指の間を埋めない）

# 既定の値（carve.py の報告にも書く）
PARAMS = {
    'target_sigma_px': 6.0,       # 目標の外形のならし（体）
    'head_close_m': 0.02,         # 頭の外形の切り欠きを閉じる円の半径
    'lens_union_m': 0.008,        # 正面と真横のレンズのなめらかな和の幅
    'depth_sigma_m': 0.03,        # 胴の奥行きの倍率を上下にならす幅
}


def log(*a) -> None:
    import resource
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    print(f'[fair {time.time() - T0:7.1f}s {mem:4.1f}GB]', *a, flush=True)


def ramp(t: np.ndarray, t0: float, t1: float, a: float = 0.0, b: float = 1.0) -> np.ndarray:
    """t0 以下で a、t1 以上で b、間はなめらかに（smoothstep）"""
    s = np.clip((np.asarray(t, float) - t0) / (t1 - t0), 0, 1)
    return a + (b - a) * s * s * (3 - 2 * s)


def smooth_max(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """2 つの場（内側が正）のなめらかな和。境目に半径 k ほどのすみ肉ができる"""
    h = np.clip(0.5 + 0.5 * (a - b) / k, 0, 1)
    return (b + (a - b) * h + k * h * (1 - h)).astype(np.float32)


# ---------------------------------------------------------------- 1. 外形

def mask_sdf(mask: np.ndarray, sigma: float = 0.8) -> np.ndarray:
    """外形のマスクの符号つき距離（画素、内側が正、境目は画素の中心の中間）。画素の刻みを消すため少しぼかす"""
    d = np.where(mask, ndi.distance_transform_edt(mask) - 0.5, -(ndi.distance_transform_edt(~mask) - 0.5))
    return ndi.gaussian_filter(d.astype(np.float32), sigma)


def target_sdf(mask: np.ndarray, cam: V.Cam, sigma=6.0, sigma_head=3.0) -> np.ndarray:
    """目標の外形（符号つき距離、画素）。小さな切り欠き・出っ張りをならす。

    sigma は体（数か (上下, 左右) の組）、sigma_head は頭（あごより上）。手首より先の高さの行はならさない。
    """
    sd = mask_sdf(mask, 0.8)
    z = (cam.v0 - (np.arange(mask.shape[0]) + 0.5)) / cam.ppm
    w_hand = ramp(z, HAND_ROWS[0] - 0.04, HAND_ROWS[0]) * (1.0 - ramp(z, HAND_ROWS[1], HAND_ROWS[1] + 0.02))
    w_head = ramp(z, *HEAD_Z)
    out = ndi.gaussian_filter(sd, sigma)
    out += w_head.astype(np.float32)[:, None] * (ndi.gaussian_filter(sd, sigma_head) - out)
    out += w_hand.astype(np.float32)[:, None] * (sd - out)
    return out


def _head_morph(masks: dict[str, np.ndarray], cams: dict[str, V.Cam], radius_m: float, z0: float,
                op: str) -> dict[str, np.ndarray]:
    """頭（z0 より上）の行だけ、外形を円で閉じる（op='close'）か開く（'open'）"""
    from skimage.morphology import disk
    out = {}
    for n in REAL:
        m, c = masks[n], cams[n]
        r = int(round(radius_m * c.ppm))
        if op == 'close':
            mm = ndi.binary_closing(np.pad(m, r), disk(r))[r:-r, r:-r] | m
        else:
            mm = ndi.binary_opening(m, disk(r))
        v0 = int(c.v_of(z0))
        res = m.copy()
        res[:v0] = mm[:v0]
        lab, nl = ndi.label(res)
        if nl > 1:   # 開きで離れた小さな塊は落とす
            sizes = ndi.sum(res, lab, range(1, nl + 1))
            res = lab == (int(np.argmax(sizes)) + 1)
        out[n] = res
    return out


def closed_masks(masks, cams, radius_m: float = 0.02, z0: float = 1.21) -> dict[str, np.ndarray]:
    """頭の外形の切り欠き（房の間・あごの下）を円で閉じた外形"""
    return _head_morph(masks, cams, radius_m, z0, 'close')


def hull_field(lo, vox, shape, cams: dict[str, V.Cam], sds: dict[str, np.ndarray], dilate_px: float = 1.0,
               chunk: int = 64, names=REAL) -> np.ndarray:
    """視点の外形の符号つき距離（画素）を視線に沿って延ばし、最小をとった場（m、内側が正）＝視体積の場"""
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(nz) + 0.5) * vox
    D = np.empty(shape, np.float32)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    for k0 in range(0, nz, chunk):
        k1 = min(nz, k0 + chunk)
        blk = np.full((k1 - k0, nx, ny), np.inf, np.float32)
        for name in names:
            c = cams[name]
            Vb = np.broadcast_to((c.v_of(zs[k0:k1]) - 0.5)[:, None, None], blk.shape)
            Ub = np.broadcast_to((c.u_of(X, Y) - 0.5)[None], blk.shape)
            val = ndi.map_coordinates(sds[name], [Vb.ravel(), Ub.ravel()], order=1, mode='nearest')
            np.minimum(blk, ((val.reshape(blk.shape) + dilate_px) / c.ppm).astype(np.float32), out=blk)
        D[k0:k1] = blk
    return D


# ---------------------------------------------------------------- 2. 体：ふくらみのレンズ

def poisson_height(mask: np.ndarray) -> np.ndarray:
    """外形の「ふくらみ」の高さ（画素）：∇²f = -1（外形の中）、f = 0（外）を解き、h = √(2f)"""
    from scipy.sparse.linalg import cg
    out = np.zeros(mask.shape, np.float32)
    ii, jj = np.nonzero(mask)
    n = len(ii)
    if n == 0:
        return out
    idx = -np.ones(mask.shape, np.int64)
    idx[ii, jj] = np.arange(n)
    rows, cols, vals = [np.arange(n)], [np.arange(n)], [np.full(n, 4.0)]
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = ii + di, jj + dj
        ok = (a >= 0) & (a < mask.shape[0]) & (b >= 0) & (b < mask.shape[1])
        k = np.full(n, -1)
        k[ok] = idx[a[ok], b[ok]]
        good = k >= 0
        rows.append(np.arange(n)[good])
        cols.append(k[good])
        vals.append(-np.ones(int(good.sum())))
    A = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    d = ndi.distance_transform_edt(mask)
    f, _ = cg(A, np.ones(n), x0=(d[ii, jj] ** 2) / 2, rtol=1e-7, maxiter=5000)
    out[ii, jj] = np.sqrt(2 * np.maximum(f, 0))
    return out


def _row_bounds(mask: np.ndarray, cam: V.Cam, zs: np.ndarray, sign: float) -> tuple[np.ndarray, np.ndarray]:
    """各高さ z で、外形の行の両端（世界の座標。sign は画像の右が世界の +/- どちらか）。小さい方, 大きい方"""
    a = np.full(len(zs), np.nan)
    b = np.full(len(zs), np.nan)
    for k, z in enumerate(zs):
        v = int(math.floor(cam.v_of(z)))
        if 0 <= v < mask.shape[0]:
            cols = np.nonzero(mask[v])[0]
            if len(cols):
                a[k], b[k] = sorted([sign * (cols[0] - cam.u0) / cam.ppm, sign * (cols[-1] + 1 - cam.u0) / cam.ppm])
    for arr in (a, b):
        ok = ~np.isnan(arr)
        arr[:] = np.interp(np.arange(len(zs)), np.nonzero(ok)[0], arr[ok])
    return a, b


class Lens:
    """体のふくらみのレンズ（本文の 2）。masks は、ふくらませる外形（前後の端・中心もこれで測る）"""

    def __init__(self, cams: dict[str, V.Cam], masks: dict[str, np.ndarray], k_union: float = 0.008,
                 depth_sigma: float = 0.03):
        self.cams, self.masks, self.k, self.depth_sigma = cams, masks, k_union, depth_sigma
        f, s = cams['front'], cams['side_right']
        # 外形の外は負（外形までの距離）。外で場がちょうど 0 にならないように
        self.hf = (poisson_height(masks['front']) - ndi.distance_transform_edt(~masks['front'])) / f.ppm
        self.hs = (poisson_height(masks['side_right']) - ndi.distance_transform_edt(~masks['side_right'])) / s.ppm

    def field(self, lo, vox, shape) -> np.ndarray:
        nz, nx, ny = shape
        xs = lo[0] + (np.arange(nx) + 0.5) * vox
        ys = lo[1] + (np.arange(ny) + 0.5) * vox
        zs = lo[2] + (np.arange(nz) + 0.5) * vox
        f, s = self.cams['front'], self.cams['side_right']
        Hf = ndi.map_coordinates(self.hf, np.meshgrid(f.v_of(zs) - 0.5, f.u_of(xs, 0 * xs) - 0.5, indexing='ij'),
                                 order=1, mode='nearest').astype(np.float32)
        Hs = ndi.map_coordinates(self.hs, np.meshgrid(s.v_of(zs) - 0.5, s.u_of(0 * ys, ys) - 0.5, indexing='ij'),
                                 order=1, mode='nearest').astype(np.float32)
        y_front, y_back = _row_bounds(self.masks['side_right'], s, zs, -1.0)   # 真横の絵の右は -Y
        x_lo, x_hi = _row_bounds(self.masks['front'], f, zs, 1.0)
        cf = ndi.gaussian_filter1d((y_front + y_back) / 2, 0.01 / vox)
        cs = ndi.gaussian_filter1d((x_lo + x_hi) / 2, 0.01 / vox)
        # 奥行きのならし：その高さで最も太い所の前後の厚みを真横の絵の端に合わせる倍率（上下にならす）を、
        # 太さの割合 0.6〜0.9 でかける（胴の芯だけ。袖・腕・脚は丸いまま）
        Hp = np.maximum(Hf, 0)
        Hn = np.minimum(Hf, 0)
        hmax = np.maximum(ndi.gaussian_filter1d(Hp.max(1), 0.004 / vox), 1e-4)
        # 脚の高さ（股より下）は、行のすべて（両脚）に同じ倍率をかけ、太らせてもよい（最大 LEG_DEPTH_MAX 倍）：
        # 脚の断面は正面の幅と真横の奥行きの楕円になる（丸いままだと、面の段で真横の外形へ引かれた前後の縁が
        # とがり、レモン形の断面になる）
        legs = (1.0 - ramp(zs, LEG_Z[0], LEG_Z[1])).astype(np.float32)
        cap = 1.0 + (LEG_DEPTH_MAX - 1.0) * legs
        sf = ndi.gaussian_filter1d(np.minimum(cap, (cf - y_front) / hmax), self.depth_sigma / vox)
        sb = ndi.gaussian_filter1d(np.minimum(cap, (y_back - cf) / hmax), self.depth_sigma / vox)
        w = ramp(Hp / hmax[:, None], 0.6, 0.9).astype(np.float32)
        w = np.maximum(w, legs[:, None])
        Sf = 1 + (sf[:, None] - 1) * w
        Sb = 1 + (sb[:, None] - 1) * w
        dy = (ys[None, None, :] - cf[:, None, None]).astype(np.float32)
        Lf = np.where(dy < 0, (Hp * Sf + Hn)[:, :, None] + dy, (Hp * Sb + Hn)[:, :, None] - dy).astype(np.float32)
        del dy
        # 靴：レンズを使わない（大きな値にして、あとで視体積で切る）
        Lf += (1 - ramp(zs, 0.12, 0.17)).astype(np.float32)[:, None, None] * 0.2
        # 真横のレンズ（頭の高さだけ）
        Ls = Hs[:, None, :] - np.abs(xs[None, :, None] - cs[:, None, None]).astype(np.float32)
        w_side = ramp(zs, HEAD_Z[0] - 0.02, HEAD_Z[1] - 0.02).astype(np.float32)[:, None, None]
        Ls = w_side * Ls + (1 - w_side) * (-0.1)
        return smooth_max(Lf, Ls, self.k)


# ---------------------------------------------------------------- まとめ

def build_field(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], lo: np.ndarray, vox: float, shape,
                params: dict | None = None) -> tuple[np.ndarray, dict]:
    """本文の 1〜4：形の場（m、内側が正）と記録"""
    p = dict(PARAMS, **(params or {}))
    zs = lo[2] + (np.arange(shape[0]) + 0.5) * vox
    # 1. 目標の外形（頭は切り欠きを閉じる）と視体積の場
    cm = closed_masks(masks, cams, p['head_close_m'])
    sdp = {n: target_sdf(cm[n], cams[n], p['target_sigma_px'], 3.0) for n in REAL}
    # 体を切る視体積は正面と右真横だけ（右前斜めで切ると、腕・脚・胴の断面に平らな面と折れ目
    # （くさび形）が残る。右前斜めの外形には、3 の面の段で縁だけをなめらかに合わせる）
    D = hull_field(lo, vox, shape, cams, sdp, names=TRIM_VIEWS)
    log('視体積の場')
    # 2. 体のレンズ
    lens = Lens(cams, {n: sdp[n] > 0 for n in REAL}, p['lens_union_m'], p['depth_sigma_m'])
    phi = lens.field(lo, vox, shape)
    del lens, sdp
    log('体のレンズ')
    # 3. 首より上は体のレンズを使わない：レンズの上を、えり・フードの上の縁の高さ（BODY_TOP）の面で切る
    kb = int(np.searchsorted(zs, BODY_TOP - 0.03))
    top = np.broadcast_to((BODY_TOP - zs[kb:]).astype(np.float32)[:, None, None], phi[kb:].shape)
    phi[kb:] = -smooth_max(-phi[kb:], -top, 0.005)
    del top
    # 視体積で切る（体だけ。外形を 2 画素太らせた視体積。外形への細かな合わせは面の段で面ごとなめらかに行う）
    np.minimum(phi, D + 2.0 / cams['front'].ppm, out=phi)
    del D
    log('体の場（首より下）')
    # 4. 頭と髪（hair.py）：頭（顔・あご）・首・髪の帽子・房。視体積では切らない
    from recon import hair
    k0, hphi, hinfo = hair.build_head(cams, masks, lo, vox, shape, log=log)
    phi[k0:] = smooth_max(phi[k0:], hphi, 0.008)
    del hphi
    return phi, {'params': p, 'body_top_z': BODY_TOP, 'head': hinfo}


def mesh_of(phi: np.ndarray, lo: np.ndarray, vox: float, sigma: float = 0.6, taubin_iters: int = 10
            ) -> tuple[np.ndarray, np.ndarray]:
    """場をマーチングキューブで面にする（最大の塊だけ、三角形は外向き）。少しぼかし、Taubin でならす"""
    from skimage import measure
    from recon import snap
    occ = phi > 0
    lab, n = ndi.label(occ)
    if n > 1:
        sizes = ndi.sum(occ, lab, range(1, n + 1))
        keep = lab == (int(np.argmax(sizes)) + 1)
        phi = np.where(ndi.binary_dilation(keep, iterations=2), phi, np.minimum(phi, -vox))
    idx = np.nonzero(phi > 0)
    a0 = [max(0, int(i.min()) - 3) for i in idx]
    a1 = [int(i.max()) + 4 for i in idx]
    sub = np.pad(phi[a0[0]:a1[0], a0[1]:a1[1], a0[2]:a1[2]].astype(np.float32), 2, constant_values=-3 * vox)
    if sigma > 0:
        sub = ndi.gaussian_filter(sub, sigma)
    verts, faces, _, _ = measure.marching_cubes(sub, 0.0)
    zi, xi, yi = verts[:, 0] - 2 + a0[0], verts[:, 1] - 2 + a0[1], verts[:, 2] - 2 + a0[2]
    P = np.stack([lo[0] + (xi + 0.5) * vox, lo[1] + (yi + 0.5) * vox, lo[2] + (zi + 0.5) * vox], 1)
    # 場は内側が正なので、マーチングキューブの三角形は内向き。外向きにそろえる
    faces = faces[:, [0, 2, 1]].astype(np.int64)
    if taubin_iters:
        P = snap.taubin(P, snap.laplacian(len(P), faces), taubin_iters)
    return P, faces


def mesh_iou(P: np.ndarray, faces: np.ndarray, cams: dict[str, V.Cam], masks: dict[str, np.ndarray]) -> dict:
    """面を各視点へ写した外形と元の絵の外形の IoU（頂点と三角形の重心を打つ速い近似）"""
    from recon import snap
    out = {}
    for n in REAL:
        c = snap.coverage(P, faces, cams[n], scale=1)
        out[n] = round(float((c & masks[n]).sum() / (c | masks[n]).sum()), 4)
    return out


def main() -> None:
    """実験用：hull.npz の格子で場を作り、面にして、なめる光の確認画像を描く"""
    from recon import snap, surfcheck
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='test')
    ap.add_argument('--set', default='', help='PARAMS の上書き（例 head_open3d_m=0.04,spike_min_depth=4）')
    ap.add_argument('--render', default='body,head,torso')
    args = ap.parse_args()
    out = os.path.join(V.WORK, 'fair')
    os.makedirs(out, exist_ok=True)
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    lo, vox, shape = d['lo'], float(d['vox']), tuple(int(s) for s in d['shape'])
    cams = V.load_calib()
    masks = {n: V.load_mask(n) for n in V.VIEWS}
    params = {kv.split('=')[0]: float(kv.split('=')[1]) for kv in args.set.split(',') if kv}
    phi, _ = build_field(cams, masks, lo, vox, shape, params)
    P, faces = mesh_of(phi, lo, vox)
    log('面', len(P), len(faces), mesh_iou(P, faces, cams, masks))
    P = snap.fair_mesh(P, faces, cams, masks, log=log)
    log('面を整えた', mesh_iou(P, faces, cams, masks))
    np.savez_compressed(os.path.join(out, f'{args.name}.npz'), verts=P.astype(np.float32), tris=faces)
    if args.render:
        for f in surfcheck.run(P, faces, os.path.join(out, args.name), which=tuple(args.render.split(','))):
            log(f)


if __name__ == '__main__':
    main()
