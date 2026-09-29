"""多視点の絵からハルの形を起こす（再構築）：較正 → なめらかな形の場 → 外形に留めた面 → 部位ごとの UV。

■ 使い方（.venv-blender の python で動かす。bpy をモジュールとして使うので Blender の画面は要らない）
  python tools/blender/recon/views.py                 元の絵の取り出し・マスク・最初の較正
  python tools/blender/recon/carve.py --stage surface 面の工程をすべて（2 → 3 → 4。較正 calib.json は変えない。
                                                      約 13 分、最大 2.5GB）。ふつうはこれ 1 つ
      = 2. hull（fair.py の体のレンズ ＋ hair.py の頭と髪の房、約 2.5 分）
        → 3. mesh（マーチングキューブ → snap.py の外形への留め → Blender の掃除・間引き・自己交差の直し →
                   uvparts.py の UV → 書き出し、約 5 分）
        → 4. check（check.py・surfcheck.py・uvcheck.py の確認画像、約 5 分）
  python tools/blender/recon/carve.py                 1〜4 をすべて（1 の較正の追い込みも。calib.json を書き直す）
  python tools/blender/recon/carve.py --stage calib   1 だけ（calib.json を書き直す）
  python tools/blender/recon/carve.py --stage hull    2 だけ（較正は calib.json を使う）
  python tools/blender/recon/carve.py --stage mesh    3 と 4（2 の結果 hull.npz を使う）
  python tools/blender/recon/carve.py --stage blender 3 の Blender の段（間引き・UV・書き出し）と 4 だけ
                                                      （3 で書いた、面を整えたあとの面 surface.npz を使う。約 7 分）
  その他：--vox 0.002（ボクセルの大きさ m）、--target-tris 37000（間引きの目標。長い辺の割りと UV の切れ目で増え、最終は約 4.5 万）、
          --variant 名前（本番の成果物を上書きせず build/recon/variants/<名前>/ に出す）
  build/recon の外の成果物は作らない。ゲームの GLB までは build_haru_r.py（npm run haru:recon）。

■ 流れ
 1. calib … 較正の追い込み（views.py の最初の較正から）
    - 右前斜めの絵の方位角：A ポーズでは左右の脚・腕は同じ前後位置にあるので、
      「斜めの絵での左右の間隔 / 正面の絵での左右の間隔 = cos(方位角)」を行ごとに求め、中央値をとる。
      外形の一致（IoU）は方位角 25〜45 度でほとんど変わらず、方位角の手がかりにならない。
      発注は 45 度だが、実際の絵は約 31 度で描かれている。
    - W1-00b の追加の絵（calibrate_added_views）：右前・左前の斜めは同じ間隔の比から（約 ±46.5 度）、横位置は正面と
      右真横の視体積の投影の IoU から。左真横も横位置を同じく。腕の無い右真横は、脚と頭の外形を右真横に重ねる。
      形（視体積・レンズ・外形の留め）には使わず、色（texture.py）と髪の房の当てはめ（hair.py）に使う。
    - 上下（足の裏の行・身長の画素数）は 4 枚とも直接測れてそろっているので動かさない。右前斜めの横位置と
      縮尺、右真横の縮尺を、3 視点の視体積を各視点へ投影し直した IoU の平均が最大になるよう探す。
 2. hull … なめらかな形の場（fair.py と hair.py。並びは (z, x, y)、2mm のボクセル）
    以前の方法（輪切りごとに断面を当てはめる、視体積で切る）は、隣の輪切りと判断が食い違って横筋・段・ひれが
    出て、頭は角ばった箱・くさび形の顔になった。いまは、
    - 体（首より下、fair.py）：正面の絵の外形の「ふくらみ」（∇²f = -1 の解から h = √(2f)）を、右真横の絵の
      前後の中心から前後に延ばしたレンズ。腕・脚・指は丸い断面、胴は（右真横の絵の厚みに合わせて）角の丸い
      箱形。えり・フードの上の縁（1.203m）で切り、視体積の場（外形の符号つき距離を視線に沿って延ばした最小。
      外形は 2 画素太らせる）で切る。
    - 頭と髪（hair.py）：高さごとの超楕円の断面を積んだ頭（顔・あご）と髪の帽子、首の楕円柱、鼻、額のゴーグル
      の帯、つむじから流れる葉の形の房 38 本（3 視点の外形に向き・長さ・浮き・幅を当てはめる）と前髪 4 本。
      なめらかな和でつなぐ。視体積では切らない。
 3. mesh … 面
    - 場をマーチングキューブで面にし、Taubin でならす。
    - snap.py：面をなめらかにしながら（Taubin）、視点ごとの輪郭線の頂点だけを絵の外形まで動かし、その動きを
      面の上で広げる、を 40 回。実の 3 視点の外形に合い、面には段・筋が残らない。頭（首より上）は動かさない。
    - 靴底を z=0 の平面に。Blender で小島の除去・穴埋め・部位ごとの間引き（頭 38%、手 13%、体 49%。頭は髪の房の形を残す）・
      間引きでできた破片の除去・長い辺（4.5cm より長い）を割る・自己交差の直し（交差する三角形のまわりだけを
      ならす）・面積 0 の三角形の除去・なめらかな陰影。
    - UV（uvparts.py）：体を平面で部位（頭・胴・腕・手・脚、長い部位は上下にも）に切り、それぞれ前後（手は
      内外）の 2 枚にして伸びの少ない展開（27 の島）。頭の島は 2 倍、手は 1.35 倍にして、画素の上で詰める
      （FFT で置ける位置を探す。空いた所に収まる島は最大 1.25 倍に）。
    - haru_mesh.glb / .blend / .npz に書き出す。
 4. check … check.py：calib.json のカメラで Cycles の灰色の画像を描き、元の絵と並べる（geo_check_*.png）。
    メッシュを各視点へ投影した外形と元の絵の外形の IoU を測る。surfcheck.py：なめる光（斜め上の横から浅い
    角度の強い光）で面の段・筋・こぶを見る画像（surf_check_*.png）。uvcheck.py：UV の島の並びと、市松模様を
    UV で貼った画像（uv_check.png）、島の間のすき間の最小。

■ 出力（build/recon/）
  calib.json, mask_<視点>.png, hull.npz（形の場 phi・F・H0）, surface.npz（面を整えたあと、間引きの前の面）,
  haru_mesh.glb, haru_mesh.blend,
  haru_mesh.npz（間引き後の頂点・三角形。check.py が使う）, geo_check_*.png, surf_check_*.png, uv_check.png,
  recon_report.json
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

def estimate_three_quarter_azimuth(cams: dict[str, V.Cam], masks: dict[str, np.ndarray],
                                   name: str = 'three_quarter') -> tuple[float, list]:
    """斜めの絵（name）の方位角の大きさを、左右の脚（膝下）と腕（肘〜手首）の間隔の比から求める"""
    f, t = cams['front'], cams[name]
    rows = []

    def big(rs, w=30):
        return [r for r in rs if r[1] - r[0] > w]

    for z in np.arange(0.16, 0.36, 0.005):   # すね（左右の脚が離れ、形が単純な高さ）
        rf = big(V.runs(masks['front'][int(f.v_of(z))]))
        rt = big(V.runs(masks[name][int(t.v_of(z))]))
        if len(rf) == 2 and len(rt) == 2:
            cf = [(a + b) / 2 for a, b in rf]
            ct = [(a + b) / 2 for a, b in rt]
            rows.append(('leg', float(z), (ct[1] - ct[0]) / (cf[1] - cf[0])))
    for z in np.arange(0.68, 0.93, 0.005):   # 前腕〜肘（腕が胴から離れている高さ）
        rf = big(V.runs(masks['front'][int(f.v_of(z))]))
        rt = big(V.runs(masks[name][int(t.v_of(z))]))
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


ADDED_OBLIQUE = {'front_right45': +1, 'front_left45': -1}   # 追加の斜めの絵と方位角の符号（右前 +、左前 -）


def calibrate_added_views(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], vox: float = 0.003) -> dict:
    """W1-00b の追加の絵（左真横・左右の前斜め・腕の無い右真横）のカメラを追い込む。

    上下（足の裏の行・身長の画素数）は正面とそろっているので動かさない。
    - 斜め：方位角の大きさは右前斜めと同じく手足の間隔の比から（左前は符号を負に）。横位置の最初の値は
      すねの高さの左右の脚の中点、そこから正面と右真横の視体積（左右対称）を投影した外形の IoU が最大に
      なる横位置を探す（縮尺は正面のまま）。
    - 左真横：同じく視体積の投影の IoU で横位置。
    - 腕の無い右真横：右真横と同じ縮尺にし、腕の無い高さ（脚 z 0.03〜0.55、頭 z 1.25〜）で右真横の外形と
      いちばん重なる横位置。
    """
    out: dict = {}
    # 正面と右真横だけの視体積（左右対称。右前斜めで切ると、左前から見た外形が片寄る）
    grid = Grid.around(cams, masks, vox)
    occ = np.ones(grid.shape, bool)
    for v in ('front', 'side_right'):
        occ &= grid.lookup(cams[v], dilate2(masks[v], 1))
    occ = largest(occ)
    s = cams['side_right']
    for name, sgn in ADDED_OBLIQUE.items():
        if name not in cams:
            continue
        az, rows = estimate_three_quarter_azimuth(cams, masks, name)
        c = cams[name]
        c.azimuth = round(sgn * az, 2)
        ys, us = [], []
        for z in np.arange(0.18, 0.34, 0.01):
            rsd = V.runs(masks['side_right'][int(s.v_of(z))])
            rt = [r for r in V.runs(masks[name][int(c.v_of(z))]) if r[1] - r[0] > 30]
            if len(rsd) == 1 and len(rt) == 2:
                ys.append(-((rsd[0][0] + rsd[0][1]) / 2 - s.u0) / s.ppm)
                us.append((rt[0][0] + rt[1][1]) / 2)
        c.u0 = float(np.median(us)) - c.ppm * float(np.median(ys)) * c.r[1]
        out[name] = {'azimuth_from_limb_pairs_deg': round(sgn * az, 2), 'rows': len(rows),
                     'leg_ratio_median': round(math.cos(math.radians(az)), 4)}
        log(f'{name}: 方位角 {sgn * az:.2f} 度（{len(rows)} 行、間隔の比 {math.cos(math.radians(az)):.3f}）')
    for name in [n for n in ('front_right45', 'front_left45', 'side_left') if n in cams]:
        c = cams[name]
        u00, ppm0 = c.u0, c.ppm
        best = (-1.0, 0.0, 1.0)
        # 縮尺は動かさない（頭頂・足の裏の行は正面とそろっている。2 視点の視体積は斜めから見ると太いので、
        # 縮尺を動かすと小さい方へ片寄る）
        for sc in (1.0,):
            for du in np.arange(-40, 40.5, 2.0):
                c.u0, c.ppm = u00 + du, ppm0 * sc
                r = iou(grid.reproject(occ, c), masks[name])
                if r > best[0]:
                    best = (r, du, sc)
        du1, sc1 = best[1], best[2]
        for du in np.arange(du1 - 2, du1 + 2.01, 0.5):
            c.u0, c.ppm = u00 + du, ppm0 * sc1
            r = iou(grid.reproject(occ, c), masks[name])
            if r > best[0]:
                best = (r, du, sc1)
        c.u0, c.ppm = u00 + best[1], ppm0 * best[2]
        out.setdefault(name, {}).update({'du_px': float(best[1]), 'scale': best[2],
                                         'hull_reprojection_iou': round(best[0], 4)})
        log(f'{name}: 横 {best[1]:+.1f}px 縮尺 {best[2]} 視体積の投影 IoU {best[0]:.4f}')
    if 'side_right_noarms' in cams:
        c = cams['side_right_noarms']
        c.ppm, c.v0 = s.ppm, s.v0
        rows = np.r_[int(s.v_of(0.55)):int(s.v_of(0.03)), int(s.v_of(1.55)):int(s.v_of(1.25))]
        a = masks['side_right'][rows]
        best = (-1.0, 0)
        for sh in range(-40, 41):
            b = np.roll(masks['side_right_noarms'][rows], -sh, axis=1)
            r = (a & b).sum() / max((a | b).sum(), 1)
            if r > best[0]:
                best = (r, sh)
        c.u0 = s.u0 + best[1]
        out['side_right_noarms'] = {'shift_vs_side_right_px': best[1], 'iou_legs_head': round(float(best[0]), 4)}
        log(f'side_right_noarms: 右真横から {best[1]:+d}px（脚と頭の外形の IoU {best[0]:.4f}）')
    return out


# ---------------------------------------------------------------- 2. 形の場

def build_hull(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], vox: float) -> dict:
    """なめらかな形の場（fair.build_field）を作り、hull.npz に書く"""
    from recon import fair
    grid = Grid.around(cams, masks, vox)
    log(f'格子 {grid.shape}（{vox * 1000:.1f}mm）')
    report: dict = {'voxel_m': vox, 'grid_shape': list(grid.shape), 'method': 'lens body below the collar (fair.py) + superellipse head/cap, '
                    'goggles band and fitted hair locks (hair.py)'}
    # 比べるための素の視体積（実の 3 視点、外形を 1 画素太らせる）
    H0 = np.ones(grid.shape, bool)
    for v in REAL:
        H0 &= grid.lookup(cams[v], dilate2(masks[v], 1))
    H0 = largest(H0)
    back = V.Cam('back', 180.0, cams['back'].ppm, cams['back'].u0, cams['back'].v0)
    r0 = {v: round(iou(grid.reproject(H0, cams[v]), masks[v]), 4) for v in REAL}
    r0['back(check)'] = round(iou(grid.reproject(H0, back), masks['back']), 4)
    log('H0（実の 3 視点の視体積）IoU', r0)
    report['iou_H0'] = r0
    phi, info = fair.build_field(cams, masks, grid.lo, vox, grid.shape)
    report.update(info)
    F = largest(phi > 0)
    rF = {v: round(iou(grid.reproject(F, cams[v]), masks[v]), 4) for v in REAL}
    rF['back(check)'] = round(iou(grid.reproject(F, back), masks['back']), 4)
    log('形の場（面にする前。外形への合わせは 3 の面の段で行う）IoU', rF)
    report['iou_field_voxels'] = rF
    report['volume_m3'] = {'H0': float(H0.sum() * vox ** 3), 'F': float(F.sum() * vox ** 3)}
    np.savez_compressed(os.path.join(OUT, 'hull.npz'), F=F, H0=H0, phi=phi.astype(np.float16),
                        lo=grid.lo, vox=vox, shape=np.array(grid.shape))
    return report


# ---------------------------------------------------------------- 3. 面

def extract_surface(cams: dict[str, V.Cam], masks: dict[str, np.ndarray], report: dict) -> tuple[np.ndarray, np.ndarray]:
    """形の場を面にし（fair.mesh_of）、外形に留めてなめらかにし（snap.fair_mesh）、靴底を平らにする"""
    from recon import fair, snap
    d = np.load(os.path.join(OUT, 'hull.npz'))
    lo, vox = d['lo'], float(d['vox'])
    P, faces = fair.mesh_of(d['phi'].astype(np.float32), lo, vox)
    report['mc_verts'], report['mc_tris'] = int(len(P)), int(len(faces))
    report['iou_before_snap'] = fair.mesh_iou(P, faces, cams, masks)
    log('マーチングキューブ', len(P), '頂点', len(faces), '三角形', report['iou_before_snap'])
    P = snap.fair_mesh(P, faces, cams, masks, log=log)
    report['iou_after_snap'] = fair.mesh_iou(P, faces, cams, masks)
    log('面を整えた', report['iou_after_snap'])
    # 靴の底は平ら：ならしで丸まった底の数 mm を z=0 の面にそろえる
    # z < 2mm → 0、2〜4mm → 0〜4mm に引き伸ばす（4mm より上はそのまま。つながりは連続）
    low = P[:, 2] < 0.004
    P[low, 2] = np.maximum(0.0, (P[low, 2] - 0.002) * 2.0)
    return P, faces


# ---------------------------------------------------------------- 3b. Blender（掃除・間引き・UV・書き出し）

def region_of(co: np.ndarray, head_z: float) -> np.ndarray:
    """頂点の部位：0 = 体、1 = 頭（首より上）、2 = 手（手首から先）"""
    reg = np.zeros(len(co), np.int8)
    reg[co[:, 2] > head_z] = 1
    reg[(np.abs(co[:, 0]) > 0.31) & (co[:, 2] < 0.85)] = 2
    return reg


# 三角形の予算の割合（全体に対して）。頭は顔と髪の房、手は指があるので面積の割に多く配る
REGION_SHARE = {1: 0.38, 2: 0.13, 0: 0.49}
MAX_EDGE_M = 0.045        # 間引きのあと、これより長い辺は割る


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


def _components(bm) -> list[list]:
    """面のつながった塊（面の一覧の一覧）"""
    bm.faces.ensure_lookup_table()
    seen = set()
    out = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        out.append(comp)
    return out


def repair_self_intersections(obj, rounds: int = 16) -> dict:
    """間引きで細い所（指の間・カフの縁）に出た自己交差を、交差する三角形のまわりだけをならして直す。

    頂点を共有しない三角形の組の重なりを BVH で探し、その頂点と 2 つ隣までを Laplacian で 4 回ならす、を
    交差がなくなるまで（最大 rounds 回）。ならすと細い所が少し縮むので、2 つの面が離れる。
    """
    import bmesh
    from mathutils.bvhtree import BVHTree
    me = obj.data
    counts = []
    for _ in range(rounds + 1):
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bm)
        bad = set()
        for i, j in bvh.overlap(bvh):
            if i < j and not (set(bm.faces[i].verts) & set(bm.faces[j].verts)):
                bad.update((i, j))
        counts.append(len(bad))
        if not bad or len(counts) > rounds:
            bm.free()
            break
        vs = {v for i in bad for v in bm.faces[i].verts}
        for _ in range(2):            # 2 つ隣まで
            vs |= {w for v in list(vs) for e in v.link_edges for w in e.verts}
        for _ in range(4):
            bmesh.ops.smooth_vert(bm, verts=list(vs), factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.to_mesh(me)
        bm.free()
    return {'faces_in_intersections_per_round': counts}


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
    # 間引きで平らな所（靴の横・底）にできた長い辺を割る（曲げたときに形が崩れないように）
    bm = bmesh.new()
    bm.from_mesh(me)
    split = 0
    for _ in range(3):
        long_e = [e for e in bm.edges if e.calc_length() > MAX_EDGE_M]
        if not long_e:
            break
        split += len(long_e)
        res = bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=False)
        faces = list({f for g in res['geom'] if isinstance(g, bmesh.types.BMVert) for f in g.link_faces})
        bmesh.ops.triangulate(bm, faces=[f for f in faces if len(f.verts) > 3])
    # 間引きで小さな塊ができていれば消す（細い所が切れた破片）
    comps = _components(bm)
    comps.sort(key=len, reverse=True)
    small = [f for c in comps[1:] for f in c]
    if small:
        bmesh.ops.delete(bm, geom=small, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    report['removed_small_pieces_after_decimate'] = len(comps) - 1
    report['long_edges_split'] = {'max_edge_m': MAX_EDGE_M, 'split': split,
                                  'longest_after_m': round(max(e.calc_length() for e in bm.edges), 4)}
    bm.to_mesh(me)
    bm.free()
    log('長い辺を割った', report['long_edges_split'])
    report['self_intersections'] = repair_self_intersections(obj)
    log('自己交差の直し', report['self_intersections'])
    # 面積 0 の三角形・長さ 0 の辺を消す（残ると UV の展開（MINIMUM_STRETCH）がその島で失敗し、島が円になる）
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    report['degenerate_dissolved'] = int(len(me.polygons) - len(bm.faces))
    # 3 枚以上の面が付いた辺（まれに間引き・ならしでできる）：まわりの面を消して穴を埋め直す
    nm = [e for e in bm.edges if len(e.link_faces) > 2]
    if nm:
        bmesh.ops.delete(bm, geom=list({f for e in nm for f in e.link_faces}), context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    report['nonmanifold_edges_repaired'] = len(nm)
    bm.to_mesh(me)
    bm.free()
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

    # UV：部位ごとに平面で切ってシームを入れ、展開して詰める（uvparts.py）。切った所で三角形が少し増える
    from recon import uvparts
    info, _ = uvparts.unwrap(obj, head_z)
    report['uv'] = dict(info, **uv_stats(obj, head_z))
    me = obj.data
    log('UV', {k: v for k, v in report['uv'].items() if k != 'parts'})

    mat = C.material('haru_body', (0.6, 0.6, 0.6), roughness=0.8)
    obj.data.materials.append(mat)
    obj.vertex_groups.clear()

    # 書き出し：頂点と面（check.py 用）、GLB、blend
    me = obj.data
    me.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(me)
    report['final'] = {'tris': len(bm.faces), 'verts': len(bm.verts),
                       'non_manifold_edges': sum(1 for e in bm.edges if not e.is_manifold),
                       'boundary_edges': sum(1 for e in bm.edges if e.is_boundary)}
    bm.free()
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
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    isl = _uv_islands(bm, bm.loops.layers.uv.active)
    bm.free()
    sizes = sorted(len(c) for c in isl)
    out['islands'] = len(isl)
    out['smallest_island_tris'] = sizes[0] if sizes else 0
    for k, (a3, a2) in acc.items():
        out[f'{k}_px_per_cm_at_2048'] = round(math.sqrt(a2 / max(a3, 1e-9)) * 2048 / 100, 2)
    return out



# ---------------------------------------------------------------- まとめ

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='all', choices=['all', 'calib', 'hull', 'mesh', 'blender', 'surface'])
    ap.add_argument('--vox', type=float, default=0.002)
    ap.add_argument('--target-tris', type=int, default=37000,
                    help='間引きの目標（長い辺の割りと UV の切れ目で増え、最終は約 4.5 万）')
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
        cal['added_views'] = calibrate_added_views(cams, masks)
        V.save_calib(cams, {'stage': 'refined', 'refine': cal})
        report['calib'] = cal
    cams = V.load_calib()

    if args.stage in ('all', 'hull', 'surface'):
        report['hull'] = build_hull(cams, masks, args.vox)

    if args.stage in ('all', 'mesh', 'blender', 'surface'):
        # 頭の下端（首より上）：身長の 4.4 頭身から。頭は約 1.55/4.4 = 0.35m
        head_z = V.HEIGHT - V.HEIGHT / 4.4
        surf = os.path.join(OUT, 'surface.npz')
        if args.stage == 'blender':
            # 面を整えたあとの面（surface.npz）から、Blender の段だけをやり直す
            report.setdefault('mesh', {})['head_z'] = head_z
            d = np.load(surf)
            P, faces = d['verts'].astype(np.float64), d['tris'].astype(np.int64)
        else:
            report['mesh'] = {'head_z': head_z}
            P, faces = extract_surface(cams, masks, report['mesh'])
            np.savez_compressed(surf, verts=P.astype(np.float32), tris=faces.astype(np.int32))
        blender_mesh(P, faces, args.target_tris, head_z, report['mesh'])
        from recon import check, surfcheck
        report['check'] = check.run(OUT)
        d = np.load(os.path.join(OUT, 'haru_mesh.npz'))
        report['surf_check'] = [os.path.basename(p) for p in
                                surfcheck.run(d['verts'], d['tris'], os.path.join(OUT, 'surf_check'), samples=32)]
        from recon import uvcheck
        report['mesh']['uv'].update(uvcheck.run(OUT))
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
