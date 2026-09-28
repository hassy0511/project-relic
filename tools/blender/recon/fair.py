"""形の場をなめらかにする（fairing）：輪切りの段・横筋・細い棘を消し、実の 3 視点の外形はそのまま保つ。

carve.py の P（輪切りの事前の形）と F（外形を戻した形）は、輪切りごとに決めるので、隣の輪切りと食い違って
横筋・段・薄いひれが出る。ここでは 3 次元の場として、次の 3 つを繰り返して形を決め直す。

  1. ならす   φ ← G_σ * φ     ガウスのぼかし（上下 σz を大きく、水平 σxy は小さく。部位で強さを変える）
  2. 持ち上げる  実の視点で外形の内側なのに、その視線上のどこも形の中にない（φ < 0）画素（視線）ごとに、
               視線上で形に最も近い点（φ が最大の点）p* に小さな球を足す（φ ← max(φ, ρ - |q - c|)）。
               球は形の面に接し、p* を覆う最小の大きさ（半径は ρmax まで。足りない分は次の回に伸びる）。
               なので、髪の房や指は、外形の縁から p* の位置に丸い断面で伸びる（奥行きの向きに薄い板にならない）。
  3. 削る     φ ← min(φ, D)   D は実の 3 視点の外形（1 画素太らせる）の符号つき距離を視線に沿って延ばした
               ものの最小（＝視体積の場）。はみ出しと、外形に見える隙間（指の間・腕と胴の間）を保つ。

横筋は上下のぼかしで消え、外形の縁（それぞれの視点で面が視線と平行になる線）だけが外形に留められ、
その間の面はなめらかにつながる。持ち上げは視線ごとだが、隣の視線の p* と深さの不足は外形の縁に沿って
なめらかに変わるので、横筋にならない。

  python tools/blender/recon/fair.py --name test   （実験用。carve.py の hull.npz を使い build/recon/fair/ に出す）
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

from recon import views as V  # noqa: E402

REAL = ('front', 'side_right', 'three_quarter')
T0 = time.time()


def log(*a) -> None:
    import resource
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    print(f'[fair {time.time() - T0:7.1f}s {mem:4.1f}GB]', *a, flush=True)


def mask_sdf(mask: np.ndarray, sigma: float = 0.8) -> np.ndarray:
    """外形のマスクの符号つき距離（画素、内側が正、境目は画素の中心の中間）。画素の刻みを消すため少しぼかす"""
    d = np.where(mask, ndi.distance_transform_edt(mask) - 0.5, -(ndi.distance_transform_edt(~mask) - 0.5))
    return ndi.gaussian_filter(d.astype(np.float32), sigma)


class Rays:
    """1 つの視点の視線の束。視線は（輪切り k, 画像の横の位置 a）で、横の間隔はボクセルの幅。

    正面（視線が +Y）と真横（視線が +X）は格子の軸に沿うので、その軸の最大をとるだけ。
    斜めの視点は、輪切りごとに視線に沿った点を双線形で読み出す（sample）。
    """

    def __init__(self, lo: np.ndarray, vox: float, shape: tuple[int, int, int], cam: V.Cam, sd: np.ndarray):
        self.cam, self.vox, self.lo, self.shape = cam, vox, lo, shape
        nz, nx, ny = shape
        self.xs = lo[0] + (np.arange(nx) + 0.5) * vox
        self.ys = lo[1] + (np.arange(ny) + 0.5) * vox
        self.zs = lo[2] + (np.arange(nz) + 0.5) * vox
        a = cam.azimuth % 360
        self.axis = 2 if abs(a) < 1e-6 else (1 if abs(a - 90) < 1e-6 else None)
        vv = cam.v_of(self.zs) - 0.5   # 画素の中心が i + 0.5 なので、配列の添字では -0.5
        if self.axis == 2:
            uu = cam.u_of(self.xs, 0 * self.xs) - 0.5
        elif self.axis == 1:
            uu = cam.u_of(0 * self.ys, self.ys) - 0.5
        else:
            # 斜め：視線の横の位置 t（画像の右 r の向き）と奥行き s（視線 d の向き）を格子の四隅から決める
            r, d = cam.r[:2], cam.d[:2]
            cx = np.array([self.xs[0], self.xs[-1], self.xs[0], self.xs[-1]])
            cy = np.array([self.ys[0], self.ys[0], self.ys[-1], self.ys[-1]])
            t = cx * r[0] + cy * r[1]
            s = cx * d[0] + cy * d[1]
            self.t = np.arange(t.min(), t.max() + vox, vox)
            self.s = np.arange(s.min(), s.max() + vox, vox)
            T, S = np.meshgrid(self.t, self.s, indexing='ij')
            X = T * r[0] + S * d[0]
            Y = T * r[1] + S * d[1]
            self.fi = (X - self.xs[0]) / vox   # 格子の添字（連続）
            self.fj = (Y - self.ys[0]) / vox
            self.inside = (self.fi >= 0) & (self.fi <= nx - 1) & (self.fj >= 0) & (self.fj <= ny - 1)
            uu = cam.u0 + cam.ppm * self.t - 0.5
        V_, U_ = np.meshgrid(vv, uu, indexing='ij')
        # 視線の中心での、外形の符号つき距離（画素）
        self.sd = ndi.map_coordinates(sd, [V_, U_], order=1, mode='nearest').astype(np.float32)

    def sample(self, field: np.ndarray, k0: int, k1: int) -> np.ndarray:
        """斜めの視点：輪切り k0..k1 の視線に沿った値 (k, a, b)。格子の外は -1"""
        n = k1 - k0
        A, B = self.fi.shape
        out = np.empty((n, A, B), np.float32)
        for q in range(n):
            out[q] = ndi.map_coordinates(field[k0 + q], [self.fi, self.fj], order=1, mode='constant', cval=-1.0)
        return out

    def ray_max(self, field: np.ndarray, chunk: int = 32) -> tuple[np.ndarray, np.ndarray]:
        """視線ごとの最大と、その位置（格子の添字の連続値 (k, i, j) の配列 (…, 3)）"""
        nz = self.shape[0]
        if self.axis is not None:
            m = field.max(axis=self.axis)
            b = field.argmax(axis=self.axis)
            K, A = np.meshgrid(np.arange(nz), np.arange(m.shape[1]), indexing='ij')
            if self.axis == 2:
                pos = np.stack([K, A, b], -1).astype(np.float32)
            else:
                pos = np.stack([K, b, A], -1).astype(np.float32)
            return m, pos
        A, B = self.fi.shape
        m = np.empty((nz, A), np.float32)
        pos = np.empty((nz, A, 3), np.float32)
        for k0 in range(0, nz, chunk):
            k1 = min(nz, k0 + chunk)
            smp = self.sample(field, k0, k1)
            bi = smp.argmax(axis=2)
            m[k0:k1] = np.take_along_axis(smp, bi[..., None], 2)[..., 0]
            aa = np.arange(A)[None, :].repeat(k1 - k0, 0)
            pos[k0:k1, :, 0] = np.arange(k0, k1)[:, None]
            pos[k0:k1, :, 1] = self.fi[aa, bi]
            pos[k0:k1, :, 2] = self.fj[aa, bi]
        return m, pos


def hull_field(lo, vox, shape, cams: dict[str, V.Cam], sds: dict[str, np.ndarray], dilate_px: float = 1.0,
               chunk: int = 64) -> np.ndarray:
    """実の 3 視点の外形の符号つき距離（画素）を視線に沿って延ばし、最小をとった場（m、内側が正）"""
    nz, nx, ny = shape
    xs = lo[0] + (np.arange(nx) + 0.5) * vox
    ys = lo[1] + (np.arange(ny) + 0.5) * vox
    zs = lo[2] + (np.arange(nz) + 0.5) * vox
    D = np.empty(shape, np.float32)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    for k0 in range(0, nz, chunk):
        k1 = min(nz, k0 + chunk)
        blk = np.full((k1 - k0, nx, ny), np.inf, np.float32)
        for name in REAL:
            c = cams[name]
            vv = c.v_of(zs[k0:k1]) - 0.5
            uu = c.u_of(X, Y) - 0.5
            Vb = np.broadcast_to(vv[:, None, None], blk.shape)
            Ub = np.broadcast_to(uu[None], blk.shape)
            val = ndi.map_coordinates(sds[name], [Vb.ravel(), Ub.ravel()], order=1, mode='nearest')
            np.minimum(blk, ((val.reshape(blk.shape) + dilate_px) / c.ppm).astype(np.float32), out=blk)
        D[k0:k1] = blk
    return D


def add_balls(phi: np.ndarray, centers: np.ndarray, radii: np.ndarray, vox: float) -> None:
    """φ ← max(φ, ρ - |q - c|)（球の和）。centers は格子の添字（連続）、radii はボクセル単位"""
    if len(centers) == 0:
        return
    R = int(math.ceil(radii.max())) + 1
    base = np.floor(centers).astype(np.int64)
    frac = centers - base
    shp = np.array(phi.shape)
    flat = phi.reshape(-1)
    rng = np.arange(-R + 1, R + 1)
    for oz in rng:
        for ox in rng:
            for oy in rng:
                q = base + np.array([oz, ox, oy])
                dist = np.sqrt(((np.array([oz, ox, oy])[None] - frac) ** 2).sum(1))
                val = radii - dist
                ok = (val > -1.0) & np.all((q >= 0) & (q < shp), 1)
                if not ok.any():
                    continue
                idx = np.ravel_multi_index(q[ok].T, phi.shape)
                np.maximum.at(flat, idx, (val[ok] * vox).astype(np.float32))


def grad_at(phi: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """φ の勾配の向き（単位ベクトル、添字の空間）を点で求める（中心差分・双線形）"""
    g = np.zeros_like(pts)
    for ax in range(3):
        e = np.zeros(3)
        e[ax] = 1.0
        a = ndi.map_coordinates(phi, (pts + e).T, order=1, mode='nearest')
        b = ndi.map_coordinates(phi, (pts - e).T, order=1, mode='nearest')
        g[:, ax] = a - b
    n = np.linalg.norm(g, axis=1, keepdims=True)
    return g / np.maximum(n, 1e-9)


def lift(phi: np.ndarray, rays: dict[str, Rays], reach: dict[str, np.ndarray], vox: float,
         eps: float, rho_min: float, rho_max, need_px: float = 0.5, big: float = 2.0,
         sigma_l: float = 2.5, gain: float = 1.3) -> dict:
    """外形の内側なのに形に届いていない視線を、形に届かせる（本文の 2）。

    不足が小さい（big ボクセル以下）視線：p* に不足の量を置き、幅 sigma_l のガウスで広げて φ に足す
      （縁のまわりをなだらかに押し出す。多めに押し出し、はみ出しは次の「削る」で視体積の面に平らに当たる）。
    不足が大きい視線（髪の房・指の先など、形が外形の縁まで伸びていない所）：形に接して p* へ向かう球を足す
      （半径は rho_min〜rho_max。届かない分は次の回にさらに伸びる）。
    rho_max は数（ボクセル）か、（k, i, j）の配列 → 最大の半径（部位で変える）を返す関数。
    """
    stats = {}
    allc, allr, sp, sd_ = [], [], [], []
    for name, ry in rays.items():
        m, pos = ry.ray_max(phi)
        miss = (ry.sd >= need_px) & reach[name] & (m < eps * vox)
        stats[name] = int(miss.sum())
        if not miss.any():
            continue
        p = pos[miss].astype(np.float64)
        dm = (eps * vox - m[miss]) / vox   # 不足（ボクセル単位）。φ が距離なら、面は p* から約 -m の所
        small = dm <= big
        sp.append(p[small])
        sd_.append(dm[small])
        p, dm = p[~small], dm[~small]
        if len(p) == 0:
            continue
        g = grad_at(phi, p)
        rmax = rho_max(p) if callable(rho_max) else np.full(len(p), float(rho_max))
        rho = np.clip((dm + eps) / 2 + 0.25, rho_min, rmax)
        # 球の中心：p* から面の向きへ s だけ進めた所（面に接し、届くなら p* を覆う）
        s = np.maximum(0.0, dm - rho + 0.5)
        allc.append(p + g * s[:, None])
        allr.append(rho)
    if sp:
        p = np.concatenate(sp)
        dm = np.concatenate(sd_)
        if len(p):
            raise_ = smooth_raise(phi.shape, p, dm, sigma_l)
            phi += (gain * vox) * raise_
            del raise_
    if allc:
        add_balls(phi, np.concatenate(allc), np.concatenate(allr), vox)
    return stats


def smooth_raise(shape, pts: np.ndarray, amount: np.ndarray, sigma: float, c: float = 0.005) -> np.ndarray:
    """点ごとの量を幅 sigma（ボクセル）のガウスで広げた、なだらかな持ち上げの場（ボクセル単位）。

    量の重み付き平均 × 点の密度の飽和（縁に沿って点が並ぶ所で約 1、離れると 0 へ）。
    """
    idx = np.clip(np.rint(pts).astype(np.int64), 0, np.array(shape) - 1)
    k0, k1 = int(idx[:, 0].min()), int(idx[:, 0].max()) + 1
    pad = int(math.ceil(3 * sigma)) + 1
    a0, a1 = max(0, k0 - pad), min(shape[0], k1 + pad)
    sub = (a1 - a0,) + tuple(shape[1:])
    num = np.zeros(sub, np.float32)
    den = np.zeros(sub, np.float32)
    flat = np.ravel_multi_index((idx[:, 0] - a0, idx[:, 1], idx[:, 2]), sub)
    np.add.at(num.reshape(-1), flat, amount.astype(np.float32))
    np.add.at(den.reshape(-1), flat, 1.0)
    num = ndi.gaussian_filter(num, sigma)
    den = ndi.gaussian_filter(den, sigma)
    out = np.zeros(shape, np.float32)
    out[a0:a1] = num / (den + c)
    return out


def fair(phi: np.ndarray, lo: np.ndarray, vox: float, cams: dict[str, V.Cam], masks: dict[str, np.ndarray],
         iters: int = 10, sigma_z: float = 3.0, sigma_xy: float = 1.0, eps: float = 0.4,
         rho_min: float = 2.0, rho_max=3.0, weight=None, final_lift: bool = True) -> tuple[np.ndarray, dict]:
    """本文の 1〜3 を iters 回。weight は (z, x, y) の 0..1 の場（1 で強くならす）か None"""
    shape = phi.shape
    sds = {n: mask_sdf(masks[n]) for n in REAL}
    D = hull_field(lo, vox, shape, cams, sds)
    log('視体積の場', D.shape)
    rays = {n: Rays(lo, vox, shape, cams[n], sds[n]) for n in REAL}
    reach = {}
    for n, ry in rays.items():
        m, _ = ry.ray_max(D)
        reach[n] = m > 0.5 * vox
    phi = np.minimum(phi.astype(np.float32), D)
    band = 10 * vox
    hist = []
    for it in range(iters):
        np.clip(phi, -band, band, out=phi)
        sm = ndi.gaussian_filter(phi, (sigma_z, sigma_xy, sigma_xy))
        if weight is not None:
            weak = ndi.gaussian_filter(phi, (0.7, 0.7, 0.7))
            sm = weak + weight * (sm - weak)
        phi = sm
        del sm
        st = lift(phi, rays, reach, vox, eps, rho_min, rho_max)
        np.minimum(phi, D, out=phi)
        hist.append(st)
        log(f'  {it + 1}/{iters} 持ち上げた視線', st)
    if final_lift:
        st = lift(phi, rays, reach, vox, eps, rho_min, rho_max)
        np.minimum(phi, D, out=phi)
        hist.append(st)
    return phi, {'lift_history': hist}


def open_field(phi: np.ndarray, vox: float, radius_z: np.ndarray) -> np.ndarray:
    """3 次元の球による「開き」（半径 radius_z[k] m の球が入りきる所だけを残す）の場（m、内側が正）。

    削り込み E = {内側の距離 ≥ r}、開いた形 = E から距離 r 以内。薄い棚・房の張り出し・細い棘が消え、
    芯の形だけが残る（外形の切り欠きで視体積に刻まれた横溝も、溝の底の深さのなめらかな面になる）。
    """
    S = phi > 0
    din = ndi.distance_transform_edt(S).astype(np.float32) * vox
    r = radius_z.astype(np.float32)[:, None, None]
    E = din >= r
    del din
    dist = ndi.distance_transform_edt(~E).astype(np.float32) * vox
    del E
    out = r - dist
    return np.minimum(out, phi)


def ramp(zs: np.ndarray, z0: float, z1: float, a: float, b: float) -> np.ndarray:
    """z0 以下で a、z1 以上で b、間はなめらかに（smoothstep）"""
    t = np.clip((zs - z0) / (z1 - z0), 0, 1)
    return a + (b - a) * t * t * (3 - 2 * t)


# ---------------------------------------------------------------- 実験用

def mesh_of(phi: np.ndarray, lo: np.ndarray, vox: float, sigma: float = 0.6, taubin: int = 10):
    from skimage import measure
    from recon import carve as K
    occ = phi > 0
    lab, n = ndi.label(occ)
    if n > 1:
        sizes = ndi.sum(occ, lab, range(1, n + 1))
        keep = lab == (int(np.argmax(sizes)) + 1)
        phi = np.where(ndi.binary_dilation(keep, iterations=2), phi, np.minimum(phi, -vox))
    idx = np.nonzero(phi > 0)
    a0 = [max(0, int(i.min()) - 3) for i in idx]
    a1 = [int(i.max()) + 4 for i in idx]
    sub = np.pad(phi[a0[0]:a1[0], a0[1]:a1[1], a0[2]:a1[2]], 2, constant_values=-3 * vox)
    if sigma > 0:
        sub = ndi.gaussian_filter(sub, sigma)
    verts, faces, _, _ = measure.marching_cubes(sub, 0.0)
    zi, xi, yi = verts[:, 0] - 2 + a0[0], verts[:, 1] - 2 + a0[1], verts[:, 2] - 2 + a0[2]
    P = np.stack([lo[0] + (xi + 0.5) * vox, lo[1] + (yi + 0.5) * vox, lo[2] + (zi + 0.5) * vox], 1)
    faces = faces.astype(np.int64)
    if taubin:
        P = K.taubin(P, faces, iters=taubin)
    return P, faces


def voxel_iou(phi, lo, vox, cams, masks) -> dict:
    from recon import carve as K
    g = K.Grid(lo, lo + np.array(phi.shape)[[1, 2, 0]] * vox, vox)
    occ = phi > 0
    return {n: round(K.iou(g.reproject(occ, cams[n]), masks[n]), 4) for n in REAL}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='test')
    ap.add_argument('--src', default='phi_prior', choices=['phi', 'phi_prior'])
    ap.add_argument('--iters', type=int, default=10)
    ap.add_argument('--sz', type=float, default=3.0)
    ap.add_argument('--sxy', type=float, default=1.0)
    ap.add_argument('--rho-max', type=float, default=3.0)
    ap.add_argument('--pre', type=float, default=0.0, help='最初に一度だけ強くぼかす σ（ボクセル）')
    ap.add_argument('--open-head', type=float, default=0.0, help='頭の開きの半径 m（0 で開かない）')
    ap.add_argument('--open-body', type=float, default=0.01)
    ap.add_argument('--rho-head', type=float, default=0.0)
    ap.add_argument('--render', default='body,head')
    args = ap.parse_args()
    out = os.path.join(V.WORK, 'fair')
    os.makedirs(out, exist_ok=True)
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    lo, vox = d['lo'], float(d['vox'])
    phi = d[args.src].astype(np.float32)
    cams = V.load_calib()
    masks = {n: V.load_mask(n) for n in V.VIEWS}
    log('読んだ', phi.shape, voxel_iou(phi, lo, vox, cams, masks))
    zs = lo[2] + (np.arange(phi.shape[0]) + 0.5) * vox
    if args.pre > 0:
        phi = ndi.gaussian_filter(np.clip(phi, -0.03, 0.03), (args.pre, args.pre / 3, args.pre / 3))
    if args.open_head > 0:
        phi = open_field(phi, vox, ramp(zs, 1.19, 1.24, args.open_body, args.open_head))
        log('開いた', voxel_iou(phi, lo, vox, cams, masks))
    rho = args.rho_max
    if args.rho_head > 0:
        rz = ramp(zs, 1.19, 1.24, args.rho_max, args.rho_head)
        rho = lambda p: rz[np.clip(p[:, 0].astype(int), 0, len(rz) - 1)]  # noqa: E731
    phi, info = fair(phi, lo, vox, cams, masks, iters=args.iters, sigma_z=args.sz, sigma_xy=args.sxy,
                     rho_max=rho)
    log('IoU（ボクセル）', voxel_iou(phi, lo, vox, cams, masks))
    np.save(os.path.join(out, f'{args.name}_phi.npy'), phi.astype(np.float16))
    P, faces = mesh_of(phi, lo, vox)
    np.savez_compressed(os.path.join(out, f'{args.name}.npz'), verts=P.astype(np.float32), tris=faces)
    log('メッシュ', len(P), len(faces))
    if args.render:
        from recon import surfcheck
        for p in surfcheck.run(P, faces, os.path.join(out, args.name), which=tuple(args.render.split(','))):
            log(p)


if __name__ == '__main__':
    main()
