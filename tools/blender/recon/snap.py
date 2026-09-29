"""メッシュの面をなめらかにしながら、外形の縁（輪郭線）だけを絵の外形に合わせる（外形に留めた平滑化）。

場から作った面（fair.py）は、なめらかだが外形とは数 mm ずれる。以前は外形に合わせるために視体積のボクセルを
戻していたので、外形の段が面に横筋・ひれとして出た。ここでは面そのものに対して、次の 2 つを繰り返す。
  1. Taubin の平滑化（縮まない平滑化）を smooth 回 … 波・段・筋・溝を消す
  2. 視点ごとの輪郭線（視線に対して表の三角形と裏の三角形の境の辺）のうち、画像の上でその外向きのすぐ隣が
     面に覆われていない「外の縁」の頂点について、画像の面の中の外向き（法線を画像の面へ写した向き）に沿って
     目標の外形の縁を探し、そこまでの動き（1 回に max_px 画素まで）を求める。その動きを面の上で隣の平均に
     spread 回広げ（縁のまわり約 1〜2cm がそろって動く）、0.8 倍だけ動かす。
     頭（首より上）は動かさない（hair.py の形の部品のまま。fair_mesh の freeze_z）。
     右真横の視点では、左の腕（体の向こう側で、絵では隠れている）の輪郭は内へだけ動かす（外形の外の背中の
     こぶを切る）。右前斜めの視点では、右の前腕は動かさない（丸い断面のまま）。右前斜めの視点では、
     左の前腕（籠手）は縁ごとに動かさず、高さ 1cm ごとの縁の動きの平均で前腕ごと前後に動かす（絵の腕が丸い
     腕より太く、縁だけを寄せると断面がくさび形になる。前後の位置のずれだけを直す：正面の外形は変わらない）。
釣り合った形は、なめらかな面で、縁だけが外形に沿う。最後に、広げ方を小さくした留めを 3 回。
右の前腕と手の前後の位置（align_right_arm）：右真横の絵では前腕と手が胴の手前に重なって描かれ、外形の縁に
ならないので、縁の留めでは前後の位置が決まらない（以前は前腕が絵より約 5cm 前にあり、真横の色で胴の色が
腕に、腕の色が胴に付いた）。W1-00b の腕の無い右真横の絵との色の差から絵の腕（肘〜手）の範囲を切り出し、
高さ 1cm ごとに前後の中点をそろえるように、右の前腕と手を前後（y）だけに動かす（肘の上でなめらかに 0 へ）。
右前 45 度の絵とは約 3cm 食い違うので、絵の中点へ 6 割だけ（ARM_ALIGN_GAIN）。
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
              views=REAL, outward_only: np.ndarray | None = None, skip: dict | None = None,
              shift: dict | None = None, inward_only: dict | None = None) -> tuple[np.ndarray, dict]:
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
        if inward_only is not None and name in inward_only:
            # 内へだけ動かす頂点（その視点では隠れている部位：外形より外へはみ出さないように切るだけ）
            mv = np.where(inward_only[name][idx], np.minimum(mv, 0.0), mv)
        dw = (mv / cam.ppm)[:, None] * (nu[:, None] * r[None] + nv[:, None] * np.array([0, 0, -1.0])[None])
        if shift is not None and name in shift:
            # まとめて動かす部位（前腕）：縁の動きを高さ 1cm ごとに平均し、部位の頂点すべてを同じだけ動かす
            # （断面の形は変えず、位置だけを外形に合わせる。縁だけを動かすと断面がくさび形になる）
            grp, w_grp = shift[name]
            g = grp[idx]
            _shift_groups(X, grp, w_grp, idx[g > 0], dw[g > 0], num, den, r)
            idx, dw = idx[g == 0], dw[g == 0]
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


def _shift_groups(X: np.ndarray, grp: np.ndarray, w_grp: np.ndarray, ridx: np.ndarray, rdw: np.ndarray,
                  num: np.ndarray, den: np.ndarray, r: np.ndarray, bin_m: float = 0.01) -> None:
    """部位（grp の番号ごと）の縁の頂点 ridx の動き rdw を高さ bin_m ごとに平均し（上下に 2 つの幅でならす）、
    部位のすべての頂点に、重み w_grp をかけて足す（num, den に書く）。

    動きは前後（y）だけにする：その視点の画像の横の動き（rdw・r）を、y だけの動きに直す（y = (rdw・r) / r_y）。
    左右（x）に動かすと正面の外形がずれる。
    """
    rdw = np.stack([np.zeros(len(rdw)), (rdw @ r) / r[1], np.zeros(len(rdw))], 1)
    for gid in np.unique(grp[grp > 0]):
        sel = grp[ridx] == gid
        allv = np.nonzero(grp == gid)[0]
        if not sel.any() or len(allv) == 0:
            continue
        z0 = X[allv, 2].min()
        nb = int((X[allv, 2].max() - z0) / bin_m) + 1
        b = np.clip(((X[ridx[sel], 2] - z0) / bin_m).astype(int), 0, nb - 1)
        cnt = np.bincount(b, minlength=nb).astype(float)
        mean = np.stack([np.bincount(b, rdw[sel, k], minlength=nb) for k in range(3)], 1)
        ok = cnt > 0
        mean[ok] /= cnt[ok, None]
        cz = np.arange(nb)
        for k in range(3):
            mean[:, k] = np.interp(cz, cz[ok], mean[ok, k])
        mean = ndi.gaussian_filter1d(mean, 2.0, axis=0, mode='nearest')
        zb = (X[allv, 2] - z0) / bin_m
        T = np.stack([np.interp(zb, cz, mean[:, k]) for k in range(3)], 1) * w_grp[allv, None]
        num[allv] += T
        den[allv] += w_grp[allv]


def targets(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], sigma_v: float = 6.0) -> dict[str, np.ndarray]:
    """目標の外形（本文の最後）"""
    from recon import fair
    return {n: fair.target_sdf(masks[n], cams[n], (sigma_v, 2.0), 2.0) for n in REAL}


ARM_Z = (0.56, 0.95)        # 絵の腕の前後の中点を使う高さ（肘の下〜指先の上）
ARM_BLEND_Z = (0.90, 0.99)  # この間で動きを 1 → 0（上腕・肩は動かさない）
# 動かす割合：右前 45 度の絵は、右真横の絵より前腕を約 3cm 前に描いている（絵どうしの食い違い）。
# 真横に全部合わせると 45 度の絵と外れるので、6 割だけ動かす（残りは texture.py の視点ごとの合わせ込みで吸収）
ARM_ALIGN_GAIN = 0.6


def side_arm_mask(cams: dict[str, V.Cam]) -> np.ndarray | None:
    """右真横の絵の中の右の前腕と手（腕の無い右真横の絵との色・外形の差の、いちばん大きい塊）"""
    if 'side_right_noarms' not in cams or not os.path.exists(os.path.join(V.SRC, V.VIEWS['side_right_noarms']['file'])):
        return None
    a = V.load_rgba('side_right').astype(np.float32)
    b = V.load_rgba('side_right_noarms').astype(np.float32)
    sh = int(round(cams['side_right_noarms'].u0 - cams['side_right'].u0))
    b = np.roll(b, -sh, axis=1)
    ma, mb = a[..., 3] > 128, b[..., 3] > 128
    arm = ma & (~mb | (np.abs(a[..., :3] - b[..., :3]).max(-1) > 40))
    arm = ndi.binary_opening(arm, iterations=2)
    lab, n = ndi.label(arm)
    if n == 0:
        return None
    sizes = ndi.sum(arm, lab, range(1, n + 1))
    return ndi.binary_closing(lab == (int(np.argmax(sizes)) + 1), iterations=4)


def _arm_centres(X: np.ndarray, arm: np.ndarray, zb: np.ndarray, bin_m: float) -> np.ndarray:
    """高さ zb ごとの、右の前腕と手の頂点の前後（y）の中点（無い高さは nan）"""
    out = np.full(len(zb), np.nan)
    for i, z in enumerate(zb):
        sel = arm & (np.abs(X[:, 2] - z) < bin_m / 2)
        if sel.sum() >= 10:
            out[i] = 0.5 * (X[sel, 1].min() + X[sel, 1].max())
    return out


def right_arm_target(X: np.ndarray, cams: dict[str, V.Cam], arm_mask: np.ndarray | None,
                     bin_m: float = 0.01) -> dict | None:
    """右の前腕と手の前後の中点の目標（高さごと）：最初の位置から、右真横の絵の腕の中点へ ARM_ALIGN_GAIN の割合"""
    if arm_mask is None:
        return None
    from recon import uvparts
    s = cams['side_right']
    reg = uvparts.region_of_point(X, V.HEIGHT - V.HEIGHT / 4.4)
    arm = np.isin(reg, (2, 4)) & (X[:, 2] > ARM_Z[0] - 0.05) & (X[:, 2] < ARM_BLEND_Z[1])
    zb = np.arange(ARM_Z[0], ARM_Z[1] + 1e-9, bin_m)
    y0 = _arm_centres(X, arm, zb, bin_m)
    ya = np.full(len(zb), np.nan)
    for i, z in enumerate(zb):
        cols = np.nonzero(arm_mask[int(s.v_of(z))])[0]
        if len(cols) >= 20:
            ya[i] = -((cols.min() + cols.max() + 1) / 2 - s.u0) / s.ppm
    ok = np.isfinite(y0) & np.isfinite(ya)
    if ok.sum() < 5:
        return None
    return {'arm': arm, 'zb': zb, 'bin_m': bin_m,
            'y': np.interp(zb, zb[ok], y0[ok] + ARM_ALIGN_GAIN * (ya[ok] - y0[ok]))}


def align_right_arm(X: np.ndarray, tgt: dict | None, log=print) -> np.ndarray:
    """右の前腕と手を前後（y）だけに動かして、高さごとの中点を目標（right_arm_target）にそろえる（本文の最後）"""
    if tgt is None:
        return X
    zb, arm = tgt['zb'], tgt['arm']
    cur = _arm_centres(X, arm, zb, tgt['bin_m'])
    ok = np.isfinite(cur)
    if ok.sum() < 5:
        return X
    dz = np.interp(zb, zb[ok], (tgt['y'] - cur)[ok])
    dz = ndi.gaussian_filter1d(dz, 3.0, mode='nearest')
    t = ((ARM_BLEND_Z[1] - X[:, 2]) / (ARM_BLEND_Z[1] - ARM_BLEND_Z[0])).clip(0, 1)
    w = (t * t * (3 - 2 * t)) * arm
    X = X.copy()
    X[:, 1] += w * np.interp(X[:, 2], zb, dz)
    log(f'  右の前腕と手を前後に動かす：{dz.min() * 100:+.1f}〜{dz.max() * 100:+.1f}cm（{int((w > 0).sum())} 頂点）')
    return X


def fair_mesh(X: np.ndarray, faces: np.ndarray, cams: dict[str, V.Cam], masks: dict[str, np.ndarray],
              rounds: int = 40, smooth: int = 8, final_snaps: int = 3, log=print, spread: int = 40,
              max_px: float = 4.0, freeze_z: tuple[float, float] = (1.195, 1.225)) -> np.ndarray:
    """本文の 1 と 2 を rounds 回。最後は留めるだけを数回（縁を外形にぴったり）。masks は元の絵の外形。

    頭（freeze_z より上）は動かさない：頭・髪の房は hair.py の形の部品そのもので、外形への引き寄せや
    強い平滑化をかけると、房の先が丸まり、房のひれ・段が戻る。freeze_z の間で動きをなめらかに 0 にする。
    """
    sds = targets(cams, masks)
    move = 1.0 - ((X[:, 2] - freeze_z[0]) / (freeze_z[1] - freeze_z[0])).clip(0, 1)
    move = (move * move * (3 - 2 * move))[:, None]
    # 右真横の絵では、左の腕（体の向こう側）は体と右の腕に隠れて見えない。その輪郭を右真横の外形（右の腕の
    # カフ・手袋の段）へ寄せると、籠手の前後に段がつくので寄せない
    # ただし外形の外へはみ出す所（背中の後ろのこぶ）は内へだけ寄せる（inward_only）
    left_arm = (X[:, 0] > 0.18) & (X[:, 2] > 0.45) & (X[:, 2] < 1.05)
    # 右の前腕（肘〜手首）は右前斜めの外形へ縁ごとに寄せない：絵の腕は丸い腕より太く描かれていて、縁だけを
    # 寄せると断面がくさび形・段になる。正面と右真横の外形だけで、ふくらみの丸い断面のまま
    r_fore = (X[:, 0] < -0.20) & (X[:, 2] > 0.70) & (X[:, 2] < 1.0)
    # 左の手（手首より先）は、右真横（体の向こうで隠れている）でも右前斜め（指が重なって細く描かれる）でも
    # 縁を寄せない：寄せると指が内へ削られて、先のとがった爪のような指になった。正面の外形のふくらみのまま
    l_hand = (X[:, 0] > 0.30) & (X[:, 2] < 0.80)
    skip = {'three_quarter': r_fore | l_hand, 'side_right': l_hand}
    inward = {'side_right': left_arm}
    # 左の前腕（肘〜手首、籠手）は、右前斜めの外形へは縁ごとではなく、前腕ごと前後に動かす（_shift_groups）。
    # 右前斜めの絵は前腕を丸い腕より太く描いていて、縁だけを寄せると断面が三角（くさび形）になる。
    # 左の前腕は右真横の絵では隠れているので、前後の位置は右前斜めの絵からしか決まらない。
    # 右の前腕は右真横の絵に写っていて前後の位置が決まるので、前腕ごと動かすと真横の外形とけんかする
    # （試した：真横の IoU が 0.970 → 0.961）。右の前腕はこれまでどおり縁ごとに寄せる
    fz = X[:, 2]
    fore = (X[:, 0] > 0.20) & (fz > 0.72) & (fz < 1.0)
    grp = np.where(fore, 2, 0)
    w_grp = (((fz - 0.72) / 0.05).clip(0, 1) * ((1.0 - fz) / 0.05).clip(0, 1)).astype(float)
    shift = {'three_quarter': (grp, w_grp)}
    W = laplacian(len(X), faces)
    E = edges_of(faces)
    arm_tgt = right_arm_target(X, cams, side_arm_mask(cams))
    X = align_right_arm(X, arm_tgt, log=log)
    for it in range(rounds):
        if it == rounds // 2:
            X = align_right_arm(X, arm_tgt, log=log)
        X = X + move * (taubin(X, W, smooth) - X)
        D, st = snap_step(X, faces, cams, sds, W, E, max_px=max_px, spread=spread, skip=skip, shift=shift,
                          inward_only=inward)
        X = X + 0.8 * move * D
        if it % 5 == 0 or it == rounds - 1:
            log(f'  面の平滑化と縁の留め {it + 1}/{rounds}', st)
    for _ in range(final_snaps):
        D, st = snap_step(X, faces, cams, sds, W, E, max_px=2.0, spread=8, skip=skip, shift=shift,
                          inward_only=inward)
        X = X + move * D
        X = X + move * (taubin(X, W, 1) - X)
    X = align_right_arm(X, arm_tgt, log=log)
    log('  最後の留め', st)
    return X
