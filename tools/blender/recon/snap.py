"""メッシュの面をなめらかにしながら、外形の縁（輪郭線）だけを絵の外形に合わせる（外形に留めた平滑化）。

場から作った面（fair.py）は、なめらかだが外形とは数 mm ずれる。以前は外形に合わせるために視体積のボクセルを
戻していたので、外形の段が面に横筋・ひれとして出た。ここでは面そのものに対して、次の 2 つを繰り返す。
  1. Taubin の平滑化（縮まない平滑化）を smooth 回 … 波・段・筋・溝を消す
  2. 視点ごとの輪郭線（視線に対して表の三角形と裏の三角形の境の辺）のうち、画像の上でその外向きのすぐ隣が
     面に覆われていない「外の縁」の頂点について、画像の面の中の外向き（法線を画像の面へ写した向き）に沿って
     目標の外形の縁を探し、そこまでの動き（1 回に max_px 画素まで）を求める。その動きを面の上で隣の平均に
     spread 回広げ（縁のまわり約 1〜2cm がそろって動く）、0.8 倍だけ動かす。
     頭（head_z より上）は外へだけ動かす：房の先は外形まで伸ばすが、房の間の切り欠きで面を削らない。
     右真横の視点では、左の腕（体の向こう側で、絵では隠れている）の輪郭は動かさない。
釣り合った形は、なめらかな面で、縁だけが外形に沿う。最後に、広げ方を小さくした留めを 3 回。
目標の外形（target）は元の絵の外形の符号つき距離を、上下に 6 画素・左右に 2 画素ならしたもの（頭は 2 画素）。
上下に強くならすのは、縫い目・帯の端の細かな段で輪郭線が上下に波打たないように（横筋にしない）。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy import sparse  # noqa: E402

from recon import views as V  # noqa: E402

REAL = ('front', 'side_right', 'three_quarter')


def laplacian(n: int, faces: np.ndarray) -> sparse.csr_matrix:
    """一様な重みの平均の行列 W（W @ x は隣の頂点の平均）"""
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    return (sparse.diags(1.0 / np.maximum(deg, 1)) @ A).tocsr()


def taubin(X: np.ndarray, W: sparse.csr_matrix, iters: int, lam: float = 0.5, mu: float = -0.53) -> np.ndarray:
    """Taubin の平滑化（縮まない平滑化）。W は laplacian の隣の平均の行列"""
    for _ in range(iters):
        X = X + lam * (W @ X - X)
        X = X + mu * (W @ X - X)
    return X


def vertex_normals(X: np.ndarray, faces: np.ndarray) -> np.ndarray:
    fn = np.cross(X[faces[:, 1]] - X[faces[:, 0]], X[faces[:, 2]] - X[faces[:, 0]])
    vn = np.zeros_like(X)
    for i in range(3):
        np.add.at(vn, faces[:, i], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


def coverage(X: np.ndarray, faces: np.ndarray, cam: V.Cam, size: int = V.IMG, scale: int = 2) -> np.ndarray:
    """メッシュが覆う画素（画像を 1/scale に縮めた大きさ）。頂点と三角形の重心を打ち、小さく閉じる"""
    n = size // scale
    pts = np.concatenate([X, X[faces].mean(1)])
    u, v = cam.project(pts)
    iu = np.floor(u / scale).astype(np.int64)
    iv = np.floor(v / scale).astype(np.int64)
    ok = (iu >= 0) & (iu < n) & (iv >= 0) & (iv < n)
    img = np.zeros((n, n), bool)
    img[iv[ok], iu[ok]] = True
    return ndi.binary_closing(img, iterations=1) | img


def _bilinear(img: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    return ndi.map_coordinates(img, [v - 0.5, u - 0.5], order=1, mode='nearest')


def edges_of(faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """辺（頂点の組）と、その辺を持つ 2 つの三角形（閉じた多様体を前提）"""
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    fid = np.tile(np.arange(len(faces)), 3)
    key = np.sort(e, 1)
    order = np.lexsort((key[:, 1], key[:, 0]))
    key, fid = key[order], fid[order]
    same = np.all(key[1:] == key[:-1], 1)
    i = np.nonzero(same)[0]
    return key[i], np.stack([fid[i], fid[i + 1]], 1)


def snap_step(X: np.ndarray, faces: np.ndarray, cams: dict[str, V.Cam], sds: dict[str, np.ndarray],
              W: sparse.csr_matrix, E: tuple, max_px: float = 3.0, search_px: int = 40, spread: int = 20,
              views=REAL, outward_only: np.ndarray | None = None, skip: dict | None = None
              ) -> tuple[np.ndarray, dict]:
    """外形の縁（輪郭線）の頂点を目標の外形へ動かす量を求め、面の上でなめらかに広げた動き（頂点ごと）。

    輪郭線は、視線に対して表と裏の三角形の境の辺。そのうち、画像の上で外向きのすぐ隣がメッシュに
    覆われていないもの（外の縁）の頂点を、画像の面の中の外向きに沿って目標の外形の縁まで動かす。
    その動きを spread 回、隣の平均で広げ、重みで割る（縁のまわり約 1cm がそろって動く）。
    """
    edges, ef = E
    fn = np.cross(X[faces[:, 1]] - X[faces[:, 0]], X[faces[:, 2]] - X[faces[:, 0]])
    N = vertex_normals(X, faces)
    num = np.zeros_like(X)
    den = np.zeros(len(X))
    st = {}
    for name in views:
        cam = cams[name]
        d, r = cam.d, cam.r
        facing = fn @ d
        cont = np.sign(facing[ef[:, 0]]) != np.sign(facing[ef[:, 1]])
        idx = np.unique(edges[cont].ravel())
        if skip is not None and name in skip:
            idx = idx[~skip[name][idx]]
        if len(idx) == 0:
            continue
        nu = N[idx] @ r
        nv = -N[idx, 2]
        nl = np.hypot(nu, nv)
        ok = nl > 0.3
        idx, nu, nv = idx[ok], nu[ok] / nl[ok], nv[ok] / nl[ok]
        u, v = cam.project(X[idx])
        cov = coverage(X, faces, cam)
        sc = 2
        tu, tv = (u + 3.0 * nu) / sc, (v + 3.0 * nv) / sc
        iu = np.clip(np.floor(tu).astype(int), 0, cov.shape[1] - 1)
        iv = np.clip(np.floor(tv).astype(int), 0, cov.shape[0] - 1)
        outer = ~cov[iv, iu]
        idx, nu, nv, u, v = idx[outer], nu[outer], nv[outer], u[outer], v[outer]
        sd = sds[name]
        s0 = _bilinear(sd, u, v)
        steps = np.arange(-search_px, search_px + 1, 1.0)
        su = u[:, None] + steps[None] * nu[:, None]
        sv = v[:, None] + steps[None] * nv[:, None]
        vals = _bilinear(sd, su.ravel(), sv.ravel()).reshape(su.shape)
        sign = vals > 0
        cross = sign[:, :-1] & ~sign[:, 1:]
        a, b_ = vals[:, :-1], vals[:, 1:]
        pos = steps[None, :-1] + a / np.maximum(a - b_, 1e-9)
        dist = np.where(cross, np.abs(pos), np.inf)
        j = np.argmin(dist, 1)
        rows = np.arange(len(idx))
        found = np.isfinite(dist[rows, j])
        best = np.where(found, pos[rows, j], s0)
        mv = np.clip(best, -max_px, max_px)
        if outward_only is not None:
            # 外へだけ動かす頂点（頭：房の先は外形まで伸ばすが、房の間の切り欠きで面を削らない）
            mv = np.where(outward_only[idx], np.maximum(mv, 0.0), mv)
        dw = (mv / cam.ppm)[:, None] * (nu[:, None] * r[None] + nv[:, None] * np.array([0, 0, -1.0])[None])
        np.add.at(num, idx, dw)
        np.add.at(den, idx, 1.0)
        st[name] = {'rim': int(len(idx)), 'mean_abs_px': round(float(np.abs(best).mean()), 3),
                    'far': int((np.abs(best) > max_px).sum())}
    # 面の上でなめらかに広げる（重みつきの平均。縁から離れると 0 へ）
    has = den > 0
    num[has] /= den[has, None]
    w = has.astype(float)
    num *= w[:, None]
    for _ in range(spread):
        num = W @ num
        w = W @ w
    D = num / np.maximum(w, 1e-9)[:, None] * np.minimum(1.0, w / 0.15)[:, None]
    return D, st


def targets(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], sigma_v: float = 6.0) -> dict[str, np.ndarray]:
    """目標の外形（本文の最後）"""
    from recon import fair
    return {n: fair.target_sdf(masks[n], cams[n], (sigma_v, 2.0), 2.0) for n in REAL}


def fair_mesh(X: np.ndarray, faces: np.ndarray, cams: dict[str, V.Cam], masks: dict[str, np.ndarray],
              rounds: int = 40, smooth: int = 8, final_snaps: int = 3, log=print, spread: int = 40,
              max_px: float = 4.0, head_z: float = 1.21) -> np.ndarray:
    """本文の 1 と 2 を rounds 回。最後は留めるだけを数回（縁を外形にぴったり）。masks は元の絵の外形"""
    sds = targets(cams, masks)
    outward_only = X[:, 2] > head_z
    # 右真横の絵では、左の腕（体の向こう側）は体と右の腕に隠れて見えない。その輪郭を右真横の外形（右の腕の
    # カフ・手袋の段）へ寄せると、籠手の前後に段がつくので寄せない
    skip = {'side_right': (X[:, 0] > 0.18) & (X[:, 2] > 0.45) & (X[:, 2] < 1.05)}
    W = laplacian(len(X), faces)
    E = edges_of(faces)
    for it in range(rounds):
        X = taubin(X, W, smooth)
        D, st = snap_step(X, faces, cams, sds, W, E, max_px=max_px, spread=spread, outward_only=outward_only,
                          skip=skip)
        X = X + 0.8 * D
        if it % 5 == 0 or it == rounds - 1:
            log(f'  面の平滑化と縁の留め {it + 1}/{rounds}', st)
    for _ in range(final_snaps):
        D, st = snap_step(X, faces, cams, sds, W, E, max_px=2.0, spread=8, outward_only=outward_only, skip=skip)
        X = X + D
        X = taubin(X, W, 1)
    log('  最後の留め', st)
    return X
