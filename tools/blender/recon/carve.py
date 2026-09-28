"""視体積（visual hull）で、多視点の絵からハルの形を起こす（再構築）。

■ 使い方（.venv-blender の python で動かす。bpy をモジュールとして使うので Blender の画面は要らない）
  python tools/blender/recon/views.py                 元の絵の取り出し・マスク・最初の較正
  python tools/blender/recon/carve.py                 以下の 1〜4 をすべて（2mm のボクセルで約 7 分、最大 6GB）
  python tools/blender/recon/carve.py --stage calib   1 だけ（calib.json を書き直す）
  python tools/blender/recon/carve.py --stage hull    2 だけ（較正は calib.json を使う）
  python tools/blender/recon/carve.py --stage mesh    3 と 4（2 の結果 hull.npz を使う）
  比べるための別の結果（本番の成果物は上書きしない。build/recon/variants/<名前>/ に出る）：
    --no-mirror --variant no_mirror              左右反転の仮想の視点なし
    --no-mirror --no-prior --variant raw_hull3   素の 3 視点の視体積（事前の形なし）
  その他：--vox 0.002（ボクセルの大きさ m）、--target-tris 40000、--taubin 20

■ 流れ
 1. calib … 較正の追い込み（views.py の最初の較正から）
    - 右前斜めの絵の方位角：A ポーズでは左右の脚・腕は同じ前後位置にあるので、
      「斜めの絵での左右の間隔 / 正面の絵での左右の間隔 = cos(方位角)」を行ごとに求め、中央値をとる。
      外形の一致（IoU）は方位角 25〜45 度でほとんど変わらず、方位角の手がかりにならない（視体積が手足を
      斜めの平行四辺形にして辻褄を合わせてしまう）。発注は 45 度だが、実際の絵は約 31 度で描かれている。
    - 上下（足の裏の行・身長の画素数）は 4 枚とも直接測れてそろっているので動かさない。右前斜めの横位置と
      縮尺、右真横の縮尺を、3 視点の視体積を各視点へ投影し直した IoU の平均が最大になるよう探す。
      正面は基準（x=0 は両脚の中点、身長 1.55m の定義）。
 2. hull … 形（ボクセル。並びは (z, x, y)。z の輪切りが絵の行に当たる）
    H0 = 3 つの実の視点（正面・右真横・右前斜め）の外形（1 画素太らせる）すべての内側にあるボクセル。
    H  = H0 を、右前斜めを左右反転した「左前斜めの仮想の視点」でも削ったもの。ただし
         ・左右非対称の部品（右肩の板・右太ももの板・左の籠手）は削らない。正面の絵の色（白磁・真鍮・琥珀）の
           左右差から自動で見つける。右側の板は右真横の絵の白磁の範囲にも入るボクセルだけに絞る。
         ・実の視点の拒否権：仮想の視点で削ったせいで実の外形が欠けたところは H0 から戻す。
           仮想の視点は、実の視点に見えない向き（断面の角）を丸めるだけに使う。
         ・どの実の視点でも他の塊の陰になる輪切りの塊（視体積の「おばけ」。脚の間の棒など）は消す。
    P  = 事前の形。H の輪切りの塊を上下につないだ「筋」ごとに、外形が決める向き（最大 8 方向）の張り出しへ
         楕円に近い支持関数（2 次のフーリエ級数）を当てはめ、筋に沿ってならす。輪切りごとに、上下に続く
         張り出しは凸包でなめらかに、髪の房のような細かい張り出しは縁に付く小さな「こぶ」で、外形の縁に
         ちょうど届く断面にする。手足が胴に合流するところでは手足の断面を合流の先へ延ばし、なめらかな和で
         つなぐ。断面は半平面からの距離の連続の場で持つので、面にしても輪切りの段がでない。
         （視体積だけだと断面は六角形になり、腕は真横の絵で胴に重なるので前後が 2 倍近く厚くなる）
    F  = P に、実の 3 視点の外形が欠けた投影の升目の分だけ H0 からボクセルを戻したもの（P に最も近く、
         視線に沿って平均の位置の前後 3 ボクセルだけ）。外形は H0 と同じに保ち、見えない向きだけ事前の形にする。
 3. mesh … F の距離の場をマーチングキューブで面にする → Taubin で段差を消す → 靴底を z=0 の平面に →
    Blender で小島の除去・穴埋め・部位ごとの間引き（頭 33%、手 14%、体 53% の三角形）・なめらかな陰影・
    Smart UV Project（頭の島は 2 倍）→ haru_mesh.glb / .blend
 4. check … check.py：calib.json のカメラで Cycles の灰色の画像を描き、元の絵と並べる（geo_check_*.png）。
    メッシュを各視点へ投影した外形と元の絵の外形の IoU を測る。

■ 出力（build/recon/）
  calib.json, mask_<視点>.png, mask_asymmetric_parts.png, hull.npz（F・H0・P・距離の場）, haru_mesh.glb,
  haru_mesh.blend, haru_mesh.npz（間引き後の頂点・三角形。check.py が使う）, geo_check_*.png, recon_report.json
"""
from __future__ import annotations

import argparse
import json
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
OUT = V.WORK   # 形・メッシュ・確認画像の出力先（--variant で build/recon/variants/<名前>/ に変わる）


def log(*a) -> None:
    import resource
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    print(f'[{time.time() - T0:7.1f}s {mem:4.1f}GB]', *a, flush=True)


# ---------------------------------------------------------------- ボクセルの格子

class Grid:
    """ボクセルの格子。配列の並びは (z, x, y)。z の輪切りが画像の行に対応するので、この並びにする"""

    def __init__(self, lo: np.ndarray, hi: np.ndarray, vox: float):
        self.vox = vox
        self.lo = lo
        n = np.ceil((hi - lo) / vox).astype(int)
        self.xs = lo[0] + (np.arange(n[0]) + 0.5) * vox
        self.ys = lo[1] + (np.arange(n[1]) + 0.5) * vox
        self.zs = lo[2] + (np.arange(n[2]) + 0.5) * vox
        self.X, self.Y = np.meshgrid(self.xs, self.ys, indexing='ij')
        self.shape = (len(self.zs), len(self.xs), len(self.ys))

    @staticmethod
    def around(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], vox: float) -> 'Grid':
        """正面の外形で x、真横の外形で y の範囲を決める（余白 2cm）"""
        f, s = cams['front'], cams['side_right']
        cf = np.nonzero(masks['front'].any(0))[0]
        cs = np.nonzero(masks['side_right'].any(0))[0]
        x0, x1 = (cf[0] - f.u0) / f.ppm, (cf[-1] + 1 - f.u0) / f.ppm
        # 真横の画像の右は -Y
        y0, y1 = -(cs[-1] + 1 - s.u0) / s.ppm, -(cs[0] - s.u0) / s.ppm
        m = 0.02
        return Grid(np.array([x0 - m, y0 - m, -m / 2]), np.array([x1 + m, y1 + m, V.HEIGHT + m]), vox)

    def lookup(self, cam: V.Cam, mask: np.ndarray) -> np.ndarray:
        """各ボクセルの中心が、その視点の外形の内側に写るか (z, x, y)"""
        u = np.floor(cam.u_of(self.X, self.Y)).astype(int)
        v = np.floor(cam.v_of(self.zs)).astype(int)
        h, w = mask.shape
        okv = (v >= 0) & (v < h)
        rows = np.zeros((len(self.zs), w + 1), bool)
        rows[okv, :-1] = mask[v[okv]]
        u = np.where((u >= 0) & (u < w), u, w)
        return rows[:, u]

    def reproject(self, occ: np.ndarray, cam: V.Cam, size: int = V.IMG) -> np.ndarray:
        """ボクセルの集まりをその視点の画像へ投影した外形（画素ごとの真偽）。

        各ボクセルを投影の幅（格子の間隔の半分）で塗る。軸に沿った視点ではこれで偏りがない。
        """
        iz, ix, iy = np.nonzero(occ)
        uc = cam.u_of(self.xs[ix], self.ys[iy])
        r = cam.r
        hw = 0.5 * self.vox * cam.ppm * max(abs(r[0]), abs(r[1]))
        c0 = np.clip(np.ceil(uc - hw - 0.5).astype(int), 0, size)
        c1 = np.clip(np.floor(uc + hw - 0.5).astype(int) + 1, 0, size)
        n = len(self.zs)
        w1 = size + 1
        diff = (np.bincount(iz * w1 + c0, minlength=n * w1) - np.bincount(iz * w1 + c1, minlength=n * w1))
        cov = np.cumsum(diff.reshape(n, w1), axis=1)[:, :size] > 0
        yc = np.arange(size) + 0.5
        k = np.floor(((cam.v0 - yc) / cam.ppm - self.lo[2]) / self.vox).astype(int)
        ok = (k >= 0) & (k < n)
        img = np.zeros((size, size), bool)
        img[ok] = cov[k[ok]]
        return img

    def edt(self, b: np.ndarray) -> np.ndarray:
        """真の部分の各ボクセルから、偽の部分までの距離（m）"""
        return (ndi.distance_transform_edt(b) * self.vox).astype(np.float32)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    return float((a & b).sum() / max(1, (a | b).sum()))


def dilate2(m: np.ndarray, r: int) -> np.ndarray:
    if r <= 0:
        return m
    return ndi.binary_dilation(m, ndi.generate_binary_structure(2, 1), iterations=r)


def largest(occ: np.ndarray) -> np.ndarray:
    lab, n = ndi.label(occ)
    if n <= 1:
        return occ
    sizes = ndi.sum(occ, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


# ---------------------------------------------------------------- 1. 較正の追い込み

def estimate_three_quarter_azimuth(cams: dict[str, V.Cam], masks: dict[str, np.ndarray]) -> tuple[float, list]:
    """右前斜めの方位角を、左右の脚（膝下）と腕（肘〜手首）の間隔の比から求める"""
    f, t = cams['front'], cams['three_quarter']
    rows = []

    def big(rs, w=30):
        return [r for r in rs if r[1] - r[0] > w]

    for z in np.arange(0.16, 0.36, 0.005):   # すね（左右の脚が離れ、形が単純な高さ）
        rf = big(V.runs(masks['front'][int(f.v_of(z))]))
        rt = big(V.runs(masks['three_quarter'][int(t.v_of(z))]))
        if len(rf) == 2 and len(rt) == 2:
            cf = [(a + b) / 2 for a, b in rf]
            ct = [(a + b) / 2 for a, b in rt]
            rows.append(('leg', float(z), (ct[1] - ct[0]) / (cf[1] - cf[0])))
    for z in np.arange(0.68, 0.93, 0.005):   # 前腕〜肘（腕が胴から離れている高さ）
        rf = big(V.runs(masks['front'][int(f.v_of(z))]))
        rt = big(V.runs(masks['three_quarter'][int(t.v_of(z))]))
        if len(rf) == 3 and len(rt) == 3:
            cf = [(a + b) / 2 for a, b in rf]
            ct = [(a + b) / 2 for a, b in rt]
            rows.append(('arm', float(z), (ct[2] - ct[0]) / (cf[2] - cf[0])))
    ang = [math.degrees(math.acos(min(1.0, r[2]))) for r in rows]
    return float(np.median(ang)), [(k, round(z, 3), round(a, 2)) for (k, z, _), a in zip(rows, ang)]


def hull_ious(grid: Grid, cams: dict[str, V.Cam], masks: dict[str, np.ndarray], dmasks: dict[str, np.ndarray],
              views=REAL) -> dict[str, float]:
    occ = np.ones(grid.shape, bool)
    for v in views:
        occ &= grid.lookup(cams[v], dmasks[v])
    return {v: iou(grid.reproject(occ, cams[v]), masks[v]) for v in views}


def refine_calibration(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], vox: float = 0.003) -> dict:
    """右前斜めと右真横のずれ・縮尺を、視体積の投影の IoU の平均が最大になるよう追い込む"""
    az, rows = estimate_three_quarter_azimuth(cams, masks)
    log(f'右前斜めの方位角（手足の間隔の比から）: {az:.2f} 度（{len(rows)} 行）')
    tq = cams['three_quarter']
    tq.azimuth = round(az, 2)
    # 左右位置の最初の値：すねの高さで、左右の脚の中点が真横の絵の脚の前後位置に写るように
    s = cams['side_right']
    ys, us = [], []
    for z in np.arange(0.18, 0.34, 0.01):
        rsd = V.runs(masks['side_right'][int(s.v_of(z))])
        rt = [r for r in V.runs(masks['three_quarter'][int(tq.v_of(z))]) if r[1] - r[0] > 30]
        if len(rsd) == 1 and len(rt) == 2:
            ys.append(-((rsd[0][0] + rsd[0][1]) / 2 - s.u0) / s.ppm)
            us.append((rt[0][0] + rt[1][1]) / 2)
    y_leg = float(np.median(ys))
    # 左右の脚の中点は x=0、y=y_leg。u = u0 + ppm * (x*r0 + y*r1)
    tq.u0 = float(np.median(us)) - tq.ppm * y_leg * tq.r[1]
    log(f'右前斜めの u0 の最初の値: {tq.u0:.1f}')

    dmasks = {v: dilate2(masks[v], 1) for v in REAL}
    grid = Grid.around(cams, masks, vox)
    base = {k: (c.u0, c.v0, c.ppm) for k, c in cams.items()}
    # 上下（足の裏の行と身長の画素数）は 4 枚とも直接測れていてそろっているので動かさない。
    # 動かすのは横の位置と、足の裏を中心にした縮尺（±2%）だけ
    params = {'tq_du': 0.0, 'tq_s': 1.0, 'sd_s': 1.0}

    def apply(p):
        u0, v0, ppm = base['three_quarter']
        # 縮尺は足の裏（v0）と原点の横位置（u0）を中心に変える
        cams['three_quarter'].u0 = u0 + p['tq_du']
        cams['three_quarter'].ppm = ppm * p['tq_s']
        u0, v0, ppm = base['side_right']
        cams['side_right'].ppm = ppm * p['sd_s']

    def score(p):
        apply(p)
        r = hull_ious(grid, cams, masks, dmasks)
        return float(np.mean(list(r.values()))), r

    best, best_r = score(params)
    log('較正の追い込み 開始', round(best, 5), best_r)
    steps = {'tq_du': [8, 4, 2, 1, 0.5], 'tq_s': [0.004, 0.002, 0.001], 'sd_s': [0.004, 0.002, 0.001]}
    limits = {'tq_du': (-80, 80), 'tq_s': (0.98, 1.02), 'sd_s': (0.98, 1.02)}
    for level in range(5):
        improved = True
        while improved:
            improved = False
            for k, st in steps.items():
                if level >= len(st):
                    continue
                for sgn in (+1, -1):
                    q = dict(params)
                    q[k] = min(max(q[k] + sgn * st[level], limits[k][0]), limits[k][1])
                    sc, r = score(q)
                    if sc > best + 1e-6:
                        best, best_r, params = sc, r, q
                        improved = True
                        break
        log(f'  段階 {level}: {round(best, 5)} {params}')
    apply(params)
    log('較正の追い込み 終わり', round(best, 5), best_r)
    return {'three_quarter_azimuth_from_limb_pairs': {'median_deg': az, 'rows': rows},
            'refined_params': params, 'hull_reprojection_iou_at_refine': best_r, 'refine_voxel_m': vox}


# ---------------------------------------------------------------- 2. 形

def _near_color(rgba: np.ndarray, mask: np.ndarray, hexc: str, tol: float) -> np.ndarray:
    """基準の色（sRGB の hex）に近い画素（外形の内側だけ）"""
    c = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)], float)
    return (np.linalg.norm(rgba[..., :3].astype(float) - c, axis=-1) < tol) & mask


def asymmetric_region(cams: dict[str, V.Cam], masks: dict[str, np.ndarray]) -> np.ndarray:
    """正面の絵で、色（白磁・真鍮・琥珀）が左右で対にならない部分＝左右非対称の部品の範囲（画素の真偽）。

    右肩の板・右太ももの板・左の籠手（と真鍮のレール）が見つかる。凸包で埋め、2cm ほど広げる。
    """
    from skimage.morphology import convex_hull_image
    f = cams['front']
    rgba = V.load_rgba('front')
    m = masks['front']
    a = (_near_color(rgba, m, '#F3E9D2', 40) | _near_color(rgba, m, '#A98749', 28)
         | _near_color(rgba, m, '#FFBC52', 35))
    cols = np.arange(V.IMG) + 0.5
    src = np.clip(np.floor(2 * f.u0 - cols).astype(int), 0, V.IMG - 1)
    a = a & ~dilate2(a[:, src], 6)
    a = ndi.binary_opening(a, iterations=3)
    lab, n = ndi.label(a)
    sizes = ndi.sum(a, lab, range(1, n + 1))
    reg = np.zeros_like(a)
    for i in np.nonzero(sizes > 3000)[0]:
        reg |= convex_hull_image(lab == i + 1)
    return dilate2(reg, 25) & dilate2(m, 3)


THETA = np.radians(np.arange(0.0, 360.0, 3.0))
NTH = np.stack([np.cos(THETA), np.sin(THETA)], 1)


def constraint_dirs(cams: dict[str, V.Cam], mirror: bool) -> list[tuple[np.ndarray, V.Cam, str, int]]:
    """外形が張り出しを決める水平の向き：(単位ベクトル n, カメラ, マスクの名前, 符号)。

    n 方向の張り出しの端は、そのカメラの画像で u が符号の向きに最大の点。
    """
    out = []
    for name in REAL:
        c = cams[name]
        r = c.r[:2]
        out += [(r, c, name, +1), (-r, c, name, -1)]
    if mirror:
        m = cams['three_quarter'].mirrored()
        a = math.radians(m.azimuth)
        rw = np.array([-math.cos(a), -math.sin(a)])   # 反転した視点の「画像の右」の世界での向き
        out += [(rw, m, 'three_quarter', +1), (-rw, m, 'three_quarter', -1)]
    return out


def _fourier(th: np.ndarray, order: int) -> np.ndarray:
    cols = [np.ones_like(th)]
    for k in range(1, order + 1):
        cols += [np.cos(k * th), np.sin(k * th)]
    return np.stack(cols, 1)


def _slice_records(grid: Grid, H: np.ndarray, cams: dict[str, V.Cam], dmasks: dict[str, np.ndarray],
                   mirror: bool, min_px: int) -> tuple[list[dict], list[np.ndarray], np.ndarray]:
    """輪切りの塊ごとに、画素・視体積の張り出し hC・外形が決める向きの張り出し（tight）を集める。

    tight は constraint_dirs の向きごとの張り出し（m）。その向きの端が
      (a) 外形の縁に接している（1.5 ボクセル先が外形の外）、または
      (b) 1.5 ボクセル先の画素は外形の内側だが、同じ輪切りの他の塊がそこを覆っていない
          （この塊がその画素を受け持つしかない。絵どうしの食い違いで視体積が外形に届かないところ）
    なら、その張り出しを守る。どちらでもない（他の塊の陰）向きは NaN。
    """
    dirs = constraint_dirs(cams, mirror)
    vox = grid.vox
    recs: list[dict] = []
    labels: list[np.ndarray] = []
    for k, z in enumerate(grid.zs):
        lab, n = ndi.label(H[k])
        labels.append(lab)
        if n == 0:
            continue
        objs = ndi.find_objects(lab)
        v_of = {id(c): int(c.v_of(z)) for _, c, _, _ in dirs}
        sizes = np.bincount(lab.ravel())
        biggest = int(sizes[1:].max())
        comps = []
        for ci in range(1, n + 1):
            sl = objs[ci - 1]
            ii, jj = np.nonzero(lab[sl] == ci)
            comps.append((ci, sl, ii + sl[0].start, jj + sl[1].start))
        # 各塊の、視点ごとの横の範囲（画素）
        ranges = []
        for _, _, ii, jj in comps:
            rr = []
            for _, cam, _, _ in dirs[::2]:
                u = cam.u_of(grid.xs[ii], grid.ys[jj])
                rr.append((float(u.min()), float(u.max())))
            ranges.append(rr)
        for idx, (ci, sl, ii, jj) in enumerate(comps):
            rec = {'k': k, 'label': ci, 'ii': ii, 'jj': jj}
            recs.append(rec)
            if len(ii) < min_px:
                continue
            # 薄い切れ端（厚さ 8mm 未満）で、その輪切りの最大の塊でないもの：髪の房の先などを、奥行きの
            # 決まらない板として残さない。外形に要る分は後の「戻す」で体に近いところだけが戻る
            if n > 1 and len(ii) < biggest:
                if ndi.distance_transform_edt(np.pad(lab[sl] == ci, 1)).max() < 2.0:
                    rec['thin'] = True
                    continue
            pts = np.stack([grid.xs[ii], grid.ys[jj]], 1)
            rec['hC'] = (pts @ NTH.T).max(0)
            tight = np.full(len(dirs), np.nan)
            for di, (nvec, cam, mname, sgn) in enumerate(dirs):
                e = float((pts @ nvec).max())
                u_in = cam.u0 + cam.ppm * sgn * e
                u_out = u_in + sgn * 1.5 * vox * cam.ppm
                v = v_of[id(cam)]
                mk = dmasks[mname]
                if not (0 <= v < mk.shape[0]):
                    continue
                iu_out = int(math.floor(u_out))
                outside = not (0 <= iu_out < mk.shape[1]) or not mk[v, iu_out]
                if not outside:
                    # 他の塊がその画素を覆っていなければ、この塊が受け持つ
                    covered = any(lo_ - 1.0 <= u_out <= hi_ + 1.0
                                  for j2, rr in enumerate(ranges) if j2 != idx
                                  for lo_, hi_ in [rr[di // 2]])
                    if covered:
                        continue
                tight[di] = e
            rec['tight'] = tight
    return recs, labels, np.array([math.atan2(d[0][1], d[0][0]) for d in dirs])


def _tracks(recs: list[dict], labels: list[np.ndarray]) -> None:
    """隣の輪切りの塊を「筋」につなぐ（rec['track']）。

    前の輪切りの各塊は、いちばん多く重なる次の塊 1 つにだけ引き継ぐ（その重なりが次の塊の面積の
    3 割以上のとき）。髪の房の先のような小さな塊が分かれても、大きな塊の筋は切れない。
    筋の上端で、上の輪切りの別の塊に合流するもの（腕→肩など）に rec['merge_up']。
    """
    by_key = {(r['k'], r['label']): r for r in recs}
    has_up = set()
    tid = 0
    for r in recs:
        if r['k'] == 0:
            r['track'] = tid
            tid += 1
    for k in range(1, len(labels)):
        a, b = labels[k - 1], labels[k]
        m = (a > 0) & (b > 0)
        heir: dict[int, tuple[int, int]] = {}
        if m.any():
            pairs, cnt = np.unique(np.stack([a[m], b[m]], 1), axis=0, return_counts=True)
            best: dict[int, tuple[int, int]] = {}
            for (la, lb), c in zip(pairs.tolist(), cnt.tolist()):
                has_up.add((k - 1, la))
                if la not in best or c > best[la][1]:
                    best[la] = (lb, c)
            area = np.bincount(b.ravel())
            for la, (lb, c) in best.items():
                if c >= 0.3 * area[lb] and (lb not in heir or c > heir[lb][1]):
                    heir[lb] = (la, c)
        for lb in range(1, int(b.max()) + 1):
            r = by_key.get((k, lb))
            if r is None:
                continue
            if lb in heir and 'track' in by_key.get((k - 1, heir[lb][0]), {}):
                r['track'] = by_key[(k - 1, heir[lb][0])]['track']
            else:
                r['track'] = tid
                tid += 1
    # 同じ輪切りで同じ筋を 2 つが引き継いだら、小さいほうを新しい筋にする
    seen: set[tuple[int, int]] = set()
    for r in sorted(recs, key=lambda r: -len(r['ii'])):
        key = (r['k'], r['track'])
        if key in seen:
            r['track'] = tid
            tid += 1
        else:
            seen.add(key)
    for r in recs:
        key = (r['k'], r['label'])
        r['merge_up'] = key in has_up and (r['k'] + 1, r['track']) not in seen


def _fit_support(ths: np.ndarray, hs: np.ndarray, ridge: float) -> np.ndarray | None:
    """接している向きの張り出しへ、2 次までのフーリエ級数を当てはめる（2 次の項は ridge で小さく）。

    係数は (a0, a1, b1, a2, b2)。a0 は平均の半径、(a1, b1) は中心、(a2, b2) は楕円のつぶれ。
    接している向きが 3 つ未満なら当てはめない。
    """
    if len(ths) < 3:
        return None
    A = _fourier(ths, 2)
    scale = max(float(np.mean(np.abs(hs))), 1e-3)
    reg = np.diag([0.0, 0.0, 0.0, ridge, ridge]) * len(ths)
    coef = np.linalg.solve(A.T @ A + reg + 1e-9 * np.eye(5), A.T @ hs)
    # 2 次の項が大きすぎる（半径より大きい）と断面が凹むので抑える
    c2 = math.hypot(coef[3], coef[4])
    if c2 > 0.6 * max(coef[0], scale * 0.3):
        coef[3:] *= 0.6 * max(coef[0], scale * 0.3) / c2
    return coef


def _nan_smooth(a: np.ndarray, sigma: float) -> np.ndarray:
    """NaN を飛ばして列ごとに 1 次元のガウスでぼかす（重みの足りないところは NaN のまま）"""
    ok = ~np.isnan(a)
    num = ndi.gaussian_filter1d(np.where(ok, a, 0.0), sigma, axis=0, mode='nearest')
    den = ndi.gaussian_filter1d(ok.astype(float), sigma, axis=0, mode='nearest')
    out = num / np.maximum(den, 1e-9)
    out[den < 0.2] = np.nan
    return out


def _nan_median(a: np.ndarray, w: int) -> np.ndarray:
    """NaN を飛ばした列ごとの移動中央値（幅 w、奇数）。段差は残し、幅 w/2 より短い出っ張りは消す"""
    import warnings
    from numpy.lib.stride_tricks import sliding_window_view
    h = w // 2
    pad = np.pad(a, ((h, h), (0, 0)), constant_values=np.nan)
    win = sliding_window_view(pad, w, axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        return np.nanmedian(win, axis=-1)


def _margin_block(grid: Grid, field: np.ndarray, k: int, h: np.ndarray, box: tuple[int, int, int, int],
                  normals: np.ndarray | None = None, lobes: list | None = None) -> None:
    """支持関数 h（normals の向きごと。省略時は THETA）の内側までの余裕 min(h - p・n)（と、こぶの円の
    内側までの余裕）を、箱の範囲で field に max で書く"""
    normals = NTH if normals is None else normals
    i0, i1, j0, j1 = box
    i0, j0 = max(0, i0), max(0, j0)
    i1, j1 = min(field.shape[1], i1), min(field.shape[2], j1)
    if i0 >= i1 or j0 >= j1:
        return
    gx, gy = np.meshgrid(grid.xs[i0:i1], grid.ys[j0:j1], indexing='ij')
    margin = (h[None, :] - np.stack([gx.ravel(), gy.ravel()], 1) @ normals.T).min(1).reshape(gx.shape)
    for cx, cy, rl in lobes or []:
        margin = np.maximum(margin, rl - np.hypot(gx - cx, gy - cy))   # こぶ（円）は凸包にせず和をとる
    blk = field[k, i0:i1, j0:j1]
    np.maximum(blk, margin.astype(np.float32), out=blk)


def _section_support(c: np.ndarray, raw: np.ndarray, smooth: np.ndarray, dir_th: np.ndarray, hC: np.ndarray,
                     disc: float) -> tuple[np.ndarray, np.ndarray, list]:
    """1 つの断面の形：凸な部分の支持関数（向き THETA と外形の縁の向き）と、縁に付く小さな円（こぶ）。

    土台は上下にならした楕円（フーリエ係数 c）。外形の縁の張り出し raw（NaN は縁に接していない）について
      1. 楕円が縁より外の向きは、その前後 ±30 度をなめらかに縮める（平らに切ると角ばった溝になるため。
         広げすぎると溝が太くなる）。
      2. 縁に届かない向きは、まず「上下になめらかな成分」smooth（筋に沿って移動中央値でならした張り出し）
         までを、半径 disc×(平均半径) の円との凸包でなめらかに張り出す（顔の正面・胴の前など、上下に続く形）。
      3. それでも届かない残り（髪の房の先など、上下に細かく変わる成分）は、縁の線に接する小さな円
         （半径は残りの 0.8 倍 + 2mm）を
         凸包にせず「こぶ」として付ける。凸包にすると小さな出っ張りが幅の広い棚になるため（半径 R の丸に
         高さ r の出っ張りの凸包は幅がおよそ 2√(2Rr)。頭で 1cm の房なら 9cm の棚になる）。
      4. 縁の向きでは縁の線そのものも半平面として加える（凸な部分は外形の縁を超えない）。
    戻り値：凸な部分の支持関数 h と向き n、こぶの一覧 [(中心 x, 中心 y, 半径)]。
    """
    ok = ~np.isnan(raw)
    th_k, t_k = dir_th[ok], raw[ok]
    s_k = np.where(np.isnan(smooth[ok]), -np.inf, smooth[ok])
    n_k = np.stack([np.cos(th_k), np.sin(th_k)], 1)
    th_all = np.concatenate([THETA, th_k])
    n_all = np.concatenate([NTH, n_k], 0)
    h = _fourier(th_all, 2) @ c
    nT = len(THETA)
    # 縮める量は向きごとの窓の「最大」（足し合わせると窓の重なりで縮みすぎて形が消える）
    shrink = np.zeros_like(h)
    for i, (thk, tk) in enumerate(zip(th_k, t_k)):
        over = h[nT + i] - tk
        if over > 0:
            dth = np.abs(np.angle(np.exp(1j * (th_all - thk))))
            w = np.where(dth < math.radians(30), np.cos(dth / math.radians(30) * math.pi / 2) ** 2, 0.0)
            shrink = np.maximum(shrink, over * w)
    h = h - shrink
    center = c[1:3]
    a0 = max(c[0], 0.002)
    rho = max(disc * a0, 0.002)
    lobes = []
    base = h[nT:].copy()
    for i, (nk, tk, sk) in enumerate(zip(n_k, t_k, s_k)):
        if base[i] < tk:
            t_convex = max(base[i], min(tk, sk))
            if t_convex > base[i]:
                cd = center + (t_convex - rho - nk @ center) * nk
                h = np.maximum(h, n_all @ cd + rho)
            rest = tk - t_convex
            if rest > 0.5 * VOX_HINT:
                r_l = 0.8 * rest + 0.002
                # 楕円の中心から縁の向きへ進んだところに置く（縁の線に接する円）。
                # 視体積の端の点（断面の角）へ寄せると棘になるので寄せない
                cl = center + (tk - r_l - nk @ center) * nk
                lobes.append((cl[0], cl[1], r_l))
    h[nT:] = np.minimum(h[nT:], t_k)
    h[:nT] = np.minimum(h[:nT], hC)
    return h, n_all, lobes


VOX_HINT = 0.002   # こぶを付ける最小の残り（おおよそボクセル 1 つ）


def slice_prior(grid: Grid, H: np.ndarray, cams: dict[str, V.Cam], dmasks: dict[str, np.ndarray], mirror: bool,
                min_px: int = 12, ridge: float = 0.15, disc: float = 0.35,
                extend: float = 2.5) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """輪切りの塊ごとに、なめらかな断面の事前の形を当てはめる（本文の説明の P）。

    1. 塊ごとに、外形が決める向き（最大 8 つ）の張り出しを集める（_slice_records）。
    2. 上下の輪切りの塊を「筋」につなぐ（_tracks）。筋に沿って、向きごとの張り出しを移動中央値＋ガウスで
       ならした「なめらかな成分」を作る（窓は塊の半径の 0.4 倍、大きな塊は 0.8 倍。裾・ベルトの段は残り、
       髪の房のギザギザは消える）。
    3. なめらかな成分へ支持関数（2 次のフーリエ級数＝楕円に近い形）を当てはめ、係数も筋に沿ってぼかす。
    4. 輪切りごとに、楕円を土台にして外形の縁の張り出しにちょうど届く断面を作る（_section_support：
       なめらかな成分までは凸包の張り出し、細かい成分は縁に付く小さな「こぶ」）。
    5. 筋が上で大きな塊に合流する（腕→肩、脚→腰、指→手のひら）ときは、筋の断面を軸の傾きに沿って
       半径の extend 倍だけ先細りに延ばし、別の場に書く（合流の先でも腕や脚が丸いまま続く）。
    戻り値：本体の場、延長の場（どちらも内側が正の距離 m）、当てはめなかった小さな塊、統計。
    """
    recs, labels, dir_th = _slice_records(grid, H, cams, dmasks, mirror, min_px)
    _tracks(recs, labels)
    vox = grid.vox
    nz = H.shape[0]
    pad = 8
    phi = np.full(H.shape, -pad * vox, np.float32)
    ext = np.full(H.shape, -pad * vox, np.float32)
    kept = np.zeros_like(H)
    stats = {'fitted': 0, 'kept_as_hull': 0, 'tracks': 0, 'extended_slices': 0}
    tracks: dict[int, list[dict]] = {}
    for r in recs:
        tracks.setdefault(r['track'], []).append(r)
    stats['tracks'] = len(tracks)
    full = _fourier(THETA, 2)
    for tr in tracks.values():
        tr.sort(key=lambda r: r['k'])
        for r in tr:
            if r.get('thin'):
                stats['thin_dropped'] = stats.get('thin_dropped', 0) + 1
            elif 'tight' not in r:
                kept[r['k'], r['ii'], r['jj']] = True
                stats['kept_as_hull'] += 1
        tr = [r for r in tr if 'tight' in r]
        if not tr:
            continue
        T = np.array([r['tight'] for r in tr])
        radius = float(np.median([math.sqrt(len(r['ii']) / math.pi) for r in tr])) * vox
        # 移動中央値の窓：塊の半径の 0.4 倍（頭・胴・腰のような大きな塊は 0.8 倍、最大 7cm）。
        # 中央値は窓の半分より長い段（裾・ベルト）は残し、短い出っ張り（髪の房のギザギザ）は消す
        w = int(np.clip(round((0.8 if radius > 0.06 else 0.4) * radius / vox), 1, 17)) * 2 + 1
        Ts = _nan_smooth(_nan_median(T, w), max(1.0, w / 6)) if len(tr) >= 3 else T.copy()
        Cf = np.full((len(tr), 5), np.nan)
        for i in range(len(tr)):
            ok = ~np.isnan(Ts[i])
            c = _fit_support(dir_th[ok], Ts[i][ok], ridge)
            if c is not None:
                Cf[i] = c
        okc = ~np.isnan(Cf[:, 0])
        if not okc.any():
            for r in tr:
                kept[r['k'], r['ii'], r['jj']] = True
                stats['kept_as_hull'] += 1
            continue
        idx = np.arange(len(tr))
        for j in range(5):
            Cf[:, j] = np.interp(idx, idx[okc], Cf[okc, j])
        if len(tr) >= 3:
            Cf = ndi.gaussian_filter1d(Cf, max(1.5, w / 4), axis=0, mode='nearest')

        # 縁の張り出しそのものも上下に少しならす（5mm。画素の刻みのばらつきと、帯・縁取りの細かい段で
        # 横筋が立たないように。ならして外形に届かなくなった分は、最後の「戻す」が小さな塊で補う）
        Tr = np.where(np.isnan(T), np.nan, _nan_smooth(T, 2.5)) if len(tr) >= 3 else T
        for i, r in enumerate(tr):
            h_all, n_all, lobes = _section_support(Cf[i], Tr[i], Ts[i], dir_th, r['hC'], disc)
            ii, jj = r['ii'], r['jj']
            _margin_block(grid, phi, r['k'], h_all,
                          (ii.min() - pad, ii.max() + pad + 1, jj.min() - pad, jj.max() + pad + 1), n_all, lobes)
            stats['fitted'] += 1

        # 上で大きな塊に合流する筋（腕→肩、脚→腰、指→手のひら）は、合流の先へ延ばす。
        # 手足のように細長い筋（長さが半径の 3 倍以上）だけ。首や髪の房の根元は延ばさない
        top = tr[-1]
        if top.get('merge_up') and len(tr) >= 8 and len(tr) * vox >= 3 * radius:
            n = min(len(tr), 15)
            seg = Cf[-n:]
            ks = np.array([q['k'] for q in tr[-n:]], float)
            c0 = seg[-1].copy()
            c0[[0, 3, 4]] = seg[-5:].mean(0)[[0, 3, 4]]
            slope = np.polyfit(ks, seg[:, 1:3], 1)[0] if n >= 5 else np.zeros(2)   # 軸の傾き（中心の動き）
            L = int(min(80, math.ceil(extend * max(c0[0], vox) / vox)))
            for t in range(1, L + 1):
                k = top['k'] + t
                if k >= nz:
                    break
                c = c0.copy()
                c[1:3] += slope * t
                # 先へ行くほど細く（端で半径の半分）。合流先の形からはみ出して箱形にならないように
                c[0] -= 0.5 * c0[0] * t / L
                h = full @ c
                cx, cy = c[1], c[2]
                rad = c[0] + math.hypot(c[3], c[4])
                ic = int((cx - grid.xs[0]) / vox)
                jc = int((cy - grid.ys[0]) / vox)
                rv = int(rad / vox) + pad
                _margin_block(grid, ext, k, h, (ic - rv, ic + rv + 1, jc - rv, jc + rv + 1))
                stats['extended_slices'] += 1
    return phi, ext, kept, stats


def smooth_union(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """2 つの距離の場（内側が正）のなめらかな和。境目に半径 k ほどのすみ肉（丸いつなぎ）ができる"""
    h = np.clip(0.5 + 0.5 * (a - b) / k, 0, 1)
    return (b + (a - b) * h + k * h * (1 - h)).astype(np.float32)


def restore(grid: Grid, H0: np.ndarray, F: np.ndarray, cams: dict[str, V.Cam], tol: float = 1.0,
            iters: int = 3, window: float | None = None) -> tuple[np.ndarray, int]:
    """実の視点で H0 には写るのに F には写らない「投影の升目」ごとに、H0 のボクセルを戻す。

    升目は（輪切り, 画像の横位置をボクセルの幅で区切ったもの）。戻すのは、その升目の視線上にある H0 の
    ボクセルのうち F に最も近いもの（最短距離 + tol ボクセル以内）。戻したボクセルは 1 つ太らせる
    （面にするときのぼかしで消えないように）。
    """
    F = F.copy()
    total = 0
    iz = np.arange(grid.shape[0])[:, None, None]
    for it in range(iters):
        added = np.zeros_like(F)
        dist = None
        for name in REAL:
            cam = cams[name]
            b = np.floor(cam.u_of(grid.X, grid.Y) / (grid.vox * cam.ppm)).astype(np.int32)
            b -= b.min()
            nb = int(b.max()) + 1
            key = (iz * nb).astype(np.int32) + b[None]
            nkey = grid.shape[0] * nb
            covH = np.bincount(key[H0], minlength=nkey) > 0
            covF = np.bincount(key[F | added], minlength=nkey) > 0
            # 隣の升目（横に 1 つ）が覆われていれば、1 ボクセル分の不足は許す
            c2 = covF.reshape(grid.shape[0], nb)
            near = c2.copy()
            near[:, 1:] |= c2[:, :-1]
            near[:, :-1] |= c2[:, 1:]
            lost = covH & ~near.ravel()
            if not lost.any():
                continue
            cand = H0 & ~F & lost[key]
            if dist is None:
                # F までの距離（ボクセル単位の近似。どの点が最も近いかを選ぶだけなので十分）
                dist = ndi.distance_transform_cdt(~F, metric='chessboard').astype(np.float32) * grid.vox
            kk = key[cand]
            dd = dist[cand]
            mind = np.full(nkey, np.inf, np.float32)
            np.minimum.at(mind, kk, dd)
            ok = dd <= mind[kk] + tol * grid.vox
            idx = np.nonzero(cand)
            if window is not None:
                # 同じ近さの候補が視線に沿って広く並ぶとき（例：頭の後ろに離れて描かれた髪の先。横位置は
                # どの絵からも決まらず、視体積では頭の幅いっぱいの薄い板になる）、平均の位置の前後
                # window ボクセルだけを戻して、小さな塊にする
                sd = cam.d[0] * grid.xs[idx[1]] + cam.d[1] * grid.ys[idx[2]]
                cnt = np.bincount(kk[ok], minlength=nkey)
                mean = np.bincount(kk[ok], weights=sd[ok], minlength=nkey) / np.maximum(cnt, 1)
                ok &= np.abs(sd - mean[kk]) <= window * grid.vox
            added[tuple(i[ok] for i in idx)] = True
            del key, cand, kk, dd, idx
        n = int(added.sum())
        if n == 0:
            break
        added = ndi.binary_dilation(added) & H0
        F |= added
        total += n
        log(f'  戻したボクセル（{it + 1} 回目）: {n}')
    return F, total


def remove_ghosts(grid: Grid, H: np.ndarray, cams: dict[str, V.Cam], min_bins: int = 2) -> tuple[np.ndarray, int]:
    """輪切りごとに、どの実の視点でも他の塊の陰に隠れてしまう塊（視体積の「おばけ」）を消す。

    視体積は、外形どうしの交わりの影に、実際にはない塊を作ることがある（例：左右の脚の間の後ろ側に
    できる細い棒）。ある塊を消しても 3 つの実の視点のどの外形も変わらないなら、その塊は外形からは
    必要とされていない。投影の升目（ボクセルの幅）で、その塊だけが覆う升目が min_bins 未満なら消す。
    """
    bins = {}
    for name in REAL:
        cam = cams[name]
        b = np.floor(cam.u_of(grid.X, grid.Y) / (grid.vox * cam.ppm)).astype(np.int64)
        bins[name] = b - b.min()
    out = H.copy()
    removed = 0
    for k in range(H.shape[0]):
        lab, n = ndi.label(H[k])
        if n < 2:
            continue
        m = lab > 0
        comp = lab[m]
        essential = np.zeros(n + 1, bool)
        for name in REAL:
            bb = bins[name][m]
            pairs = np.unique(np.stack([comp, bb], 1), axis=0)
            cnt = np.bincount(pairs[:, 1])
            only = pairs[cnt[pairs[:, 1]] == 1]
            per = np.bincount(only[:, 0], minlength=n + 1)
            essential |= per >= min_bins
        ghost = np.nonzero(~essential[1:])[0] + 1
        if len(ghost):
            out[k][np.isin(lab, ghost)] = False
            removed += len(ghost)
    return out, removed


def signed_distance(grid: Grid, occ: np.ndarray) -> np.ndarray:
    """ボクセルの集まりの符号つき距離（m、内側が正）。境目は内と外のボクセルの中心の中間"""
    return (grid.edt(occ) - grid.edt(~occ) - np.where(occ, 0.5, -0.5) * grid.vox).astype(np.float32)


def build_hull(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], vox: float, mirror: bool = True,
               prior: bool = True) -> dict:
    grid = Grid.around(cams, masks, vox)
    log(f'格子 {grid.shape}（{vox * 1000:.1f}mm）')
    dmasks = {v: dilate2(masks[v], 1) for v in REAL}
    report: dict = {'voxel_m': vox, 'grid_shape': list(grid.shape), 'mirror': mirror, 'prior': prior}

    H0 = np.ones(grid.shape, bool)
    for v in REAL:
        H0 &= grid.lookup(cams[v], dmasks[v])
    H0 = largest(H0)
    r0 = {v: round(iou(grid.reproject(H0, cams[v]), masks[v]), 4) for v in REAL}
    back = V.Cam('back', 180.0, cams['back'].ppm, cams['back'].u0, cams['back'].v0)
    r0['back(check)'] = round(iou(grid.reproject(H0, back), masks['back']), 4)
    log('H0（実の 3 視点の視体積）IoU', r0)
    report['iou_H0'] = r0

    H = H0.copy()
    if mirror:
        asym = asymmetric_region(cams, masks)
        V.save_mask('asymmetric_parts', asym)
        exempt = grid.lookup(cams['front'], asym)
        # 本人の右側の板（右肩・右太もも）は右真横の絵に全体が見えている。その白磁の範囲（少し広げる）に
        # 写るボクセルだけを除外に残す。板の後ろの脚や腕まで除外すると、板が前後に長い棒になるため。
        # 左の籠手（x > 0）は右真横からは隠れているので、正面の範囲だけで除外する
        side_ivory = dilate2(_near_color(V.load_rgba('side_right'), masks['side_right'], '#F3E9D2', 40), 12)
        right = (grid.X < 0)[None, :, :]
        exempt &= ~right | grid.lookup(cams['side_right'], side_ivory)
        H &= grid.lookup(cams['three_quarter'].mirrored(), dmasks['three_quarter']) | exempt
        H = largest(H)
        rH = {v: round(iou(grid.reproject(H, cams[v]), masks[v]), 4) for v in REAL}
        log('H（左右反転の仮想の視点でも削る）IoU', rH)
        report['iou_H_mirror_carved_before_veto'] = rH
        # 実の視点の拒否権：仮想の視点が削ったせいで実の外形が欠けたところは H0 から戻す。
        # 仮想の視点は、実の視点に見えない向き（断面の角）を削るだけにする（例：斜めの絵では左足の底が
        # 右足より少し高く描かれていて、反転すると右足の底 1.4cm を削ってしまう）
        H, n_veto = restore(grid, H0, H, cams)
        H = largest(H)
        rH = {v: round(iou(grid.reproject(H, cams[v]), masks[v]), 4) for v in REAL}
        log('H（実の視点の拒否権の後）IoU', rH, '戻した', n_veto)
        report['iou_H_mirror_carved'] = rH
        report['mirror_veto_restored_voxels'] = n_veto
        report['mirror_removed_fraction'] = round(1 - H.sum() / H0.sum(), 4)

    if not prior:
        # 比べるための素の視体積（事前の形なし）
        sd = signed_distance(grid, H)
        np.savez_compressed(os.path.join(OUT, 'hull.npz'), F=H, H0=H0, P=H, phi=sd.astype(np.float16),
                            phi_prior=sd.astype(np.float16), lo=grid.lo, vox=vox, shape=np.array(grid.shape))
        report['iou_F_final_voxels'] = {v: round(iou(grid.reproject(H, cams[v]), masks[v]), 4) for v in REAL}
        return report
    H, n_ghost = remove_ghosts(grid, H, cams)
    H = largest(H)
    log(f'おばけの塊を消した: {n_ghost}')
    report['ghost_components_removed'] = n_ghost
    phi, ext, kept, stats = slice_prior(grid, H, cams, dmasks, mirror)
    del H
    log('輪切りの事前の形', stats)
    report['slice_prior_stats'] = stats
    # 上下方向に軽くぼかして（輪切りごとに残る小さな段差をならす）、合流の先へ延ばした形となめらかにつなぐ
    k_floor = int(np.ceil((0.01 - grid.lo[2]) / grid.vox))
    phi_s = ndi.gaussian_filter1d(phi, 2.0, axis=0)
    phi_s[:k_floor] = np.maximum(phi_s[:k_floor], phi[:k_floor])   # 靴の底が上下のぼかしで縮まないように
    phi = smooth_union(phi_s, ndi.gaussian_filter1d(ext, 2.0, axis=0), 0.012)
    del ext, phi_s
    # 視体積の符号つき距離（内側が正。境目はボクセルの中心の中間）
    sd_h0 = signed_distance(grid, H0)
    # 当てはめなかった小さな塊は視体積の形のまま。全体を視体積の中に収める
    phi = np.maximum(phi, np.where(ndi.binary_dilation(kept, iterations=2), sd_h0, -np.inf).astype(np.float32))
    np.minimum(phi, sd_h0, out=phi)
    del sd_h0, kept
    P = largest(phi > 0)
    phi_prior = phi.copy()
    rP = {v: round(iou(grid.reproject(P, cams[v]), masks[v]), 4) for v in REAL}
    log('P（事前の形）IoU', rP)
    report['iou_P_prior'] = rP

    F, n_add = restore(grid, H0, P, cams, window=3.0)
    F = largest(F)
    # 最終の場：事前の形の場と、戻したボクセルの符号つき距離の大きいほう
    # 戻したボクセルは薄い板になりやすいので、視体積の中で 1 ボクセル太らせる
    R = ndi.binary_dilation(F & ~P, iterations=1) & H0
    if R.any():
        phi = np.maximum(phi, ndi.gaussian_filter(signed_distance(grid, R), 1.0))
    phi[~ndi.binary_dilation(F, iterations=2)] = -3 * grid.vox
    rF = {v: round(iou(grid.reproject(F, cams[v]), masks[v]), 4) for v in REAL}
    rF['back(check)'] = round(iou(grid.reproject(F, back), masks['back']), 4)
    log('F（外形を戻した最終の形）IoU', rF)
    report['iou_F_final_voxels'] = rF
    report['restored_voxels'] = n_add
    report['volume_m3'] = {'H0': float(H0.sum() * vox ** 3), 'P': float(P.sum() * vox ** 3),
                           'F': float(F.sum() * vox ** 3)}
    np.savez_compressed(os.path.join(OUT, 'hull.npz'), F=F, H0=H0, P=P, phi=phi.astype(np.float16),
                        phi_prior=phi_prior.astype(np.float16),
                        lo=grid.lo, vox=vox, shape=np.array(grid.shape))
    return report


# ---------------------------------------------------------------- 3. 面

def extract_surface(sigma_vox: float = 0.7) -> tuple[np.ndarray, np.ndarray]:
    """最終の場（hull.npz の phi、内側が正の距離）を少しぼかしてマーチングキューブで面にする"""
    from skimage import measure
    d = np.load(os.path.join(OUT, 'hull.npz'))
    F, lo, vox = d['F'], d['lo'], float(d['vox'])
    phi = d['phi'].astype(np.float32)
    # 形のある範囲だけを切り出し、周りに 4 ボクセルの余白を足す（面が閉じるように）
    idx = np.nonzero(F)
    a0 = [int(i.min()) for i in idx]
    a1 = [int(i.max()) + 1 for i in idx]
    pad = 4
    sub = np.pad(phi[a0[0]:a1[0], a0[1]:a1[1], a0[2]:a1[2]], pad, constant_values=-3 * vox)
    field = ndi.gaussian_filter(sub, sigma_vox)
    verts, faces, _, _ = measure.marching_cubes(field, 0.0)
    # 配列の並び (z, x, y) → 世界 (x, y, z)
    zi, xi, yi = (verts[:, 0] - pad + a0[0], verts[:, 1] - pad + a0[1], verts[:, 2] - pad + a0[2])
    P = np.stack([lo[0] + (xi + 0.5) * vox, lo[1] + (yi + 0.5) * vox, lo[2] + (zi + 0.5) * vox], 1)
    # (z,x,y)→(x,y,z) は巡回の入れ替えなので、三角形の向き（表裏）は変わらない
    return P, faces.astype(np.int64)


def taubin(P: np.ndarray, faces: np.ndarray, iters: int = 20, lam: float = 0.5, mu: float = -0.53) -> np.ndarray:
    """Taubin の平滑化（縮まない平滑化）。一様な重みのラプラシアン"""
    n = len(P)
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    W = sparse.diags(1.0 / np.maximum(deg, 1)) @ A
    X = P.copy()
    for _ in range(iters):
        X = X + lam * (W @ X - X)
        X = X + mu * (W @ X - X)
    return X


# ---------------------------------------------------------------- 3b. Blender（掃除・間引き・UV・書き出し）

def region_of(co: np.ndarray, head_z: float) -> np.ndarray:
    """頂点の部位：0 = 体、1 = 頭（首より上）、2 = 手（手首から先）"""
    reg = np.zeros(len(co), np.int8)
    reg[co[:, 2] > head_z] = 1
    reg[(np.abs(co[:, 0]) > 0.31) & (co[:, 2] < 0.85)] = 2
    return reg


# 三角形の予算の割合（全体に対して）。頭は顔と髪の房、手は指があるので面積の割に多く配る
REGION_SHARE = {1: 0.33, 2: 0.14, 0: 0.53}


def decimate_by_region(obj, target: int, head_z: float, report: dict) -> None:
    import bpy
    me = obj.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    reg_v = region_of(co.reshape(-1, 3), head_z)
    counts = {}
    for r, share in REGION_SHARE.items():
        # 面の部位は頂点の多数決（3 頂点の最頻）
        tri = np.empty(len(me.polygons) * 3, np.int32)
        me.polygons.foreach_get('vertices', tri)
        fr = reg_v[tri.reshape(-1, 3)]
        face_reg = np.where((fr == r).sum(1) >= 2, r, -1)
        sel = face_reg == r
        n = int(sel.sum())
        if n == 0:
            continue
        ratio = min(1.0, share * target / n)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        me.polygons.foreach_set('select', sel)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.decimate(ratio=ratio)
        bpy.ops.object.mode_set(mode='OBJECT')
        counts[{0: 'body', 1: 'head', 2: 'hands'}[r]] = {'before': n, 'ratio': round(ratio, 4)}
        me = obj.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        reg_v = region_of(co.reshape(-1, 3), head_z)
    # 間引きの後で残った四角形などを三角形にそろえる
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode='OBJECT')
    me = obj.data
    tri = np.empty(len(me.polygons) * 3, np.int32)
    me.polygons.foreach_get('vertices', tri)
    fr = reg_v[tri.reshape(-1, 3)]
    for r, name in ((0, 'body'), (1, 'head'), (2, 'hands')):
        counts.setdefault(name, {})['after'] = int(((fr == r).sum(1) >= 2).sum())
    report['decimate_regions'] = counts


def blender_mesh(P: np.ndarray, faces: np.ndarray, target_tris: int, head_z: float, report: dict) -> None:
    import bpy  # noqa: F401  （bmesh は bpy の後でないと読めない）
    import bmesh
    from lib import common as C

    C.reset_scene()
    me = bpy.data.meshes.new('haru')
    me.vertices.add(len(P))
    me.vertices.foreach_set('co', P.astype(np.float32).ravel())
    me.loops.add(len(faces) * 3)
    me.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set('loop_start', (np.arange(len(faces)) * 3).astype(np.int32))
    me.update(calc_edges=True)
    me.validate()
    obj = bpy.data.objects.new('haru', me)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # 掃除：重なった頂点をつなぐ・小島を消す・穴を埋める・表裏をそろえる
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.faces.ensure_lookup_table()
    seen = set()
    islands = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]
        comp = []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        islands.append(comp)
    islands.sort(key=len, reverse=True)
    removed = 0
    for comp in islands[1:]:
        if len(comp) < 0.01 * len(islands[0]):
            bmesh.ops.delete(bm, geom=comp, context='FACES')
            removed += 1
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(me)
    bm.free()
    report['cleanup'] = {'islands': len(islands), 'removed_small_islands': removed,
                         'boundary_edges_filled': len(boundary), 'non_manifold_edges': nonman}
    log('掃除', report['cleanup'], '三角形', len(me.polygons))

    # 間引き：部位ごとに三角形の数の予算を決め、選んだ面だけを間引く（頭と手は面積のわりに細かく残す）
    decimate_by_region(obj, target_tris, head_z, report)
    me = obj.data
    log('間引き後の三角形', len(me.polygons))
    bpy.ops.object.shade_smooth()

    # 表裏の確認（外向き）と、間引きで生じた非多様体の辺の数
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    report['decimated'] = {'tris': len(bm.faces), 'verts': len(bm.verts),
                           'non_manifold_edges': sum(1 for e in bm.edges if not e.is_manifold),
                           'boundary_edges': sum(1 for e in bm.edges if e.is_boundary)}
    bm.to_mesh(me)
    bm.free()

    # UV：Smart UV Project → 頭の島だけ 2 倍に拡大 → 詰め直す（頭の解像度が約 4 倍の面積になる）
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    scale_uv_islands(obj, lambda c: c[2] > head_z, 2.0)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.002)
    bpy.ops.object.mode_set(mode='OBJECT')
    report['uv'] = uv_stats(obj, head_z)
    log('UV', report['uv'])

    mat = C.material('haru_body', (0.6, 0.6, 0.6), roughness=0.8)
    obj.data.materials.append(mat)
    obj.vertex_groups.clear()

    # 書き出し：頂点と面（check.py 用）、GLB、blend
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    tri = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get('vertices', tri)
    np.savez_compressed(os.path.join(OUT, 'haru_mesh.npz'), verts=co.reshape(-1, 3), tris=tri.reshape(-1, 3))
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    C.export_glb(os.path.join(OUT, 'haru_mesh.glb'), animations=False)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'haru_mesh.blend'))
    log('書き出し', os.path.join(OUT, 'haru_mesh.glb'))


def _uv_islands(bm, uv) -> list[list]:
    """UV の島（UV がつながった面の集まり）"""
    seen = set()
    out = []

    def key(loop):
        return (round(loop[uv].uv.x, 6), round(loop[uv].uv.y, 6))

    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]
        seen.add(f.index)
        comp = []
        while stack:
            g = stack.pop()
            comp.append(g)
            for lp in g.loops:
                e = lp.edge
                a, b = key(lp), key(lp.link_loop_next)
                for lp2 in e.link_loops:
                    h = lp2.face
                    if h is g or h.index in seen:
                        continue
                    # 相手の面でこの辺の両端の UV が同じならつながっている
                    c, d = key(lp2), key(lp2.link_loop_next)
                    if {a, b} == {c, d}:
                        seen.add(h.index)
                        stack.append(h)
        out.append(comp)
    return out


def scale_uv_islands(obj, pred, factor: float) -> None:
    """面の中心が pred を満たす面が過半の UV の島を、島の中心のまわりに factor 倍する"""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    n = 0
    for comp in _uv_islands(bm, uv):
        votes = sum(1 for f in comp if pred(f.calc_center_median()))
        if votes * 2 <= len(comp):
            continue
        loops = [lp for f in comp for lp in f.loops]
        c = sum((lp[uv].uv for lp in loops), loops[0][uv].uv * 0) / len(loops)
        for lp in loops:
            lp[uv].uv = c + (lp[uv].uv - c) * factor
        n += 1
    bm.to_mesh(obj.data)
    bm.free()


def uv_stats(obj, head_z: float) -> dict:
    """UV の面積の使い方と、頭と体のテクセル密度（2048 角のとき 1cm あたりの画素）"""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    acc = {'head': [0.0, 0.0], 'body': [0.0, 0.0]}
    total_uv = 0.0
    for f in bm.faces:
        a3 = f.calc_area()
        p = [lp[uv].uv for lp in f.loops]
        a2 = 0.0
        for i in range(1, len(p) - 1):
            a2 += abs((p[i].x - p[0].x) * (p[i + 1].y - p[0].y) - (p[i + 1].x - p[0].x) * (p[i].y - p[0].y)) / 2
        k = 'head' if f.calc_center_median().z > head_z else 'body'
        acc[k][0] += a3
        acc[k][1] += a2
        total_uv += a2
    bm.free()
    out = {'uv_area_used': round(total_uv, 3)}
    for k, (a3, a2) in acc.items():
        out[f'{k}_px_per_cm_at_2048'] = round(math.sqrt(a2 / max(a3, 1e-9)) * 2048 / 100, 2)
    return out


# ---------------------------------------------------------------- まとめ

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='all', choices=['all', 'calib', 'hull', 'mesh'])
    ap.add_argument('--vox', type=float, default=0.002)
    ap.add_argument('--no-mirror', action='store_true')
    ap.add_argument('--no-prior', action='store_true', help='事前の形を使わない素の視体積（比べるため）')
    ap.add_argument('--target-tris', type=int, default=40000)
    ap.add_argument('--taubin', type=int, default=20)
    ap.add_argument('--variant', default='', help='比べるための別の出力先の名前（本番の成果物を上書きしない）')
    args = ap.parse_args()
    global OUT
    if args.variant:
        OUT = os.path.join(V.WORK, 'variants', args.variant)
        os.makedirs(OUT, exist_ok=True)

    V.extract_sources()
    masks = {v: V.load_mask(v) for v in V.VIEWS} if os.path.exists(V.mask_path('front')) else None
    if masks is None:
        V.main()
        masks = {v: V.load_mask(v) for v in V.VIEWS}
    rep_path = os.path.join(OUT, 'recon_report.json')
    report = json.load(open(rep_path)) if os.path.exists(rep_path) else {}

    if args.stage in ('all', 'calib'):
        cams = V.initial_calib(masks)
        cal = refine_calibration(cams, masks)
        V.save_calib(cams, {'stage': 'refined', 'refine': cal})
        report['calib'] = cal
    cams = V.load_calib()

    if args.stage in ('all', 'hull'):
        report['hull'] = build_hull(cams, masks, args.vox, mirror=not args.no_mirror, prior=not args.no_prior)

    if args.stage in ('all', 'mesh'):
        P, faces = extract_surface()
        log('マーチングキューブ', len(P), '頂点', len(faces), '三角形')
        P = taubin(P, faces, iters=args.taubin)
        # 靴の底は平ら：ぼかしと平滑化で丸まった底の数 mm を z=0 の面にそろえる
        # z < 2mm → 0、2〜4mm → 0〜4mm に引き伸ばす（4mm より上はそのまま。つながりは連続）
        low = P[:, 2] < 0.004
        P[low, 2] = np.maximum(0.0, (P[low, 2] - 0.002) * 2.0)
        log('Taubin 済み', '最も低い z', round(float(P[:, 2].min()), 4))
        # 頭の下端（首より上）：身長の 4.4 頭身から。頭は約 1.55/4.4 = 0.35m
        head_z = V.HEIGHT - V.HEIGHT / 4.4
        report['mesh'] = {'mc_verts': len(P), 'mc_tris': len(faces), 'taubin_iters': args.taubin,
                          'head_z': head_z}
        blender_mesh(P, faces, args.target_tris, head_z, report['mesh'])
        from recon import check
        report['check'] = check.run(OUT)
        if not args.variant:
            # 較正のファイルにも、最終のメッシュの外形の一致を書いておく（後の工程が確かめられるように）
            with open(V.CALIB_PATH) as fp:
                cal = json.load(fp)
            cal['silhouette_iou_final_mesh'] = {k: v['iou'] for k, v in report['check']['silhouette'].items()}
            with open(V.CALIB_PATH, 'w') as fp:
                json.dump(cal, fp, indent=2, ensure_ascii=False)

    with open(rep_path, 'w') as fp:
        json.dump(report, fp, indent=2, ensure_ascii=False)
    log('報告', rep_path)


if __name__ == '__main__':
    main()
