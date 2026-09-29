"""ハルの顔：画家（Codex）の顔の絵から、表情の切り替え用アトラスを起こす。

形（メッシュ）とは独立の工程。やることは 3 つ。

1. 顔の絵（haru_face_front.png、頭だけの高解像度）を、全身の正面の絵（haru_3d_front.png）の
   頭に重ねる。まず相似変換（倍率・わずかな回転・平行移動）を正規化相互相関で求め（粗い総当たり →
   Nelder-Mead）、残った数 px のずれ（絵を描き直した差。あごが少し長いなど）を、TV-L1 の光学的流れを
   重み付きでなめらかにした「ずれの場」で追い込む。
   → build/recon/face_align.json（と face_fields.npz）、確認画像 face_align_check.png
2. 4 表情の絵（haru_face_expressions.png、2×2）の各頭を、顔の絵に重ねる。
   表情で変わる眉・目・口は照合から外し、髪・ゴーグル・耳・輪郭で合わせる（相似変換）。
   顔の絵との残りのずれは「通常」の頭で 1 つの場を求めて全表情に使い、さらに同じ絵の中の「通常」と
   各表情の頭のわずかな差（あごの線など）を、表情で変わる所を除いた小さな場で追い込む。
   → face_align.json の "expressions"、確認画像 face_expr_align_check.png
3. 表情アトラス（2048×2048、1024 四方の 4 区画。左上 通常、右上 笑顔、左下 驚き、右下 痛み）を作る。
   どの区画も「正面の絵の同じ範囲」を「同じ位置・同じ倍率」で写す。4 区画に共通の土台は
     ・窓の内側：高解像度の顔の絵（通常。色は全身の正面の絵に合わせる）
     ・窓の縁の近く・窓の外・顔の絵が全身の絵と違う所（首の横の髪など）：全身の正面の絵そのもの
   で、表情で変わる部分（眉＋目、口のまわり＝表情の領域）だけを各表情の絵に差し替える。
   だから表情の領域の外（顔の窓の縁を含む）は 4 区画で画素まで同じ、窓の縁は全身の絵と同じになり、
   表情の切り替えでも、体のテクスチャとの境でも継ぎ目が出ない。
   → face_atlas.png、face_atlas.json、確認画像 face_atlas_check.png、face_atlas_seam_check.png

■ 画素の座標（calib.json と同じ約束）
  画像の左上の角を 0 とする連続座標。x は右、y は下。画素 i は [i, i+1) を占め、中心は i + 0.5。

■ 顔の窓とアトラス（テクスチャ貼りの工程が使う）
  顔の窓 W = [WX0, WX1] × [WY0, WY1]（正面の絵の画素）は、区画 0 の [QX0, QX1] × [QY0, QY1]
  （アトラスの画素）に倍率 K で写る：
      ax = QX0 + (fx - WX0) * K,   ay = QY0 + (fy - WY0) * K
  Blender の UV：u = ax / 2048、v = 1 - ay / 2048（区画 0 は u∈[0, 0.5], v∈[0.5, 1]）
  世界の点 (x, y, z) → 正面の絵の画素：fx = u0 + ppm * x、fy = v0 - ppm * z（calib.json の front）
  区画 0 の全体（窓の外の余白も）に、正面の絵の対応する範囲の中身が入っている。窓の少し外に
  はみ出した頂点も正しい色を拾う。ゲームは材質の uv1_offset を ((i % 2) * 0.5, floor(i / 2) * 0.5)
  にして表情 i の区画へずらす。

■ 使い方（.venv-blender の python で動かす。bpy は使わない）
  python tools/blender/recon/face.py            照合からすべて（約 3 分）
  python tools/blender/recon/face.py --reuse    照合は face_align.json と face_fields.npz を使い回す（約 25 秒）
  テクスチャ貼りの工程からは front_px_to_face_uv() / world_to_face_uv() を import して使える。
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy import optimize
from skimage.feature import match_template
from skimage.morphology import convex_hull_object, disk
from skimage.registration import optical_flow_tvl1, phase_cross_correlation
from skimage.transform import rescale

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from recon import char as CH  # noqa: E402

REPO = CH.REPO
WORK = CH.WORK
SRC = os.path.join(WORK, 'src')
ART_REF = CH.CFG['art']['ref']
ART_DIR = CH.CFG['art']['dir']

FRONT_FILE = CH.CFG['views']['front']['file']
FACE_FILE = CH.get('face.file')
EXPR_FILE = CH.get('face.expressions_file')
EXPRESSIONS = list(CH.get('face.expressions'))   # 左上・右上・左下・右下（ゲームの表情番号の順）

# 顔の絵（<id>_face_front.png、2048 四方）の上の範囲 (x0, y0, x1, y1)。値はハルのもの（ほかは chars/<id>.json の params）
FACE_FEATURES_RECT = CH.p('face.FACE_FEATURES_RECT', (480, 360, 1580, 1650))   # ゴーグル〜あご。全身の正面の絵との粗い照合の型
FACE_HEAD_RECT = CH.p('face.FACE_HEAD_RECT', (200, 140, 1850, 1760))       # 頭全体。細かい照合に使う範囲
FACE_EXPR_RECT = CH.p('face.FACE_EXPR_RECT', (600, 820, 1460, 1600))       # 眉・目・口。表情で変わるので表情どうしの照合から外す
FACE_NECK_Y = CH.p('face.FACE_NECK_Y', 1650)                            # これより下（首の切り口）は絵ごとに違うので、ずれの場に使わない
FACE_WINDOW = CH.p('face.FACE_WINDOW', (615, 840, 1445, 1660))          # 顔の窓：頬〜頬（耳の手前）、ゴーグルの下〜あごの少し下
# 粗い照合の倍率の範囲（顔の絵 → 全身の正面の絵、顔の絵 → 表情の絵の区画）
FRONT_SCALE = CH.p('face.FRONT_SCALE', (0.18, 0.40))
EXPR_SCALE = CH.p('face.EXPR_SCALE', (0.40, 0.60))
# 表情で差し替える所を、顔の絵のこの範囲 (x0, y0, x1, y1) の中だけにする（None は限らない）。ヤーナの表情の絵は
# 表情ごとに前髪の房の描き方が違い、髪の違いが窓の縁まで「変わった所」になったので、眉・目・口の範囲に限る
ZONE_RECT = CH.p('face.ZONE_RECT', None)

# 照合の確かめに使う目印（顔の絵の画素、中心）
FRONT_LANDMARKS = CH.p('face.FRONT_LANDMARKS', {
    'eye_img_left': (810, 1160), 'eye_img_right': (1220, 1160), 'nose': (1020, 1330),
    'mouth': (1020, 1420), 'chin': (1020, 1610), 'ear_img_left': (530, 1260), 'ear_img_right': (1520, 1260),
})
EXPR_LANDMARKS = CH.p('face.EXPR_LANDMARKS', {
    'hair_top': (1080, 260), 'ear_img_left': (530, 1260), 'ear_img_right': (1520, 1260),
    'cheek_left': (660, 1400), 'cheek_right': (1380, 1400), 'chin': (1020, 1610),
})
STRUCT_MIN = 2e-4       # 残りのずれを測る小窓に要る「2 方向の模様」の強さ（構造テンソルの小さい方の固有値）

ATLAS = 2048
QUAD = 1024
ATLAS_SCALE = 4.0       # アトラスの画素 / 正面の絵の画素（顔の窓 約 230px → 約 920px）
MIN_MARGIN = 24         # 顔の窓とアトラスの区画の縁の最小の余白（アトラスの画素）

# ずれの場のなめらかさ（ガウスの σ）
FIELD_SIGMA_FRONT = 6.0     # 正面の絵の画素で
FIELD_SIGMA_EXPR = 10.0     # 表情の絵の画素で
FIELD_STEP_EXPR = 2.0       # 表情のずれの場の格子（顔の絵の画素。表情の絵のほぼ 1 画素）

# 表情の領域を決めるしきい値など（アトラスの画素で）
ZONE_DIFF = 0.08        # 通常と表情の色の差（0〜1）がこれより大きい所を「変わった所」とする
ZONE_OPEN = 2           # 細かい点を消す半径
ZONE_MIN_AREA = 120     # これより小さい塊は捨てる
ZONE_CLOSE = 20         # 眉と目を 1 つの塊にまとめる半径
ZONE_MIN_HULL = 4000    # まとめた塊（凸包）がこれより小さければ差し替えない
ZONE_GROW = 12          # まとめた塊（凸包）を広げる半径
ZONE_FEATHER = 5.0      # 境目のぼかし（ガウスの σ）
ZONE_SAFE = 16          # 表情で変わる所と顔の窓の縁の間に要る最小の距離
ZONE_EDGE = 4           # 窓の縁からこの距離までは差し替えない（4 区画で必ず同じ画素）

# 土台（顔の絵と全身の正面の絵の混ぜ方）。アトラスの画素で
BASE_EDGE = (2, 26)     # 窓の縁からの距離がこの間で、全身の絵 → 顔の絵へなめらかに移る
SHARPEN_MAX = 0.3            # 表情の絵の鮮明さをそろえる強さの上限
BASE_SIGMA = 2.0        # 顔の絵と全身の絵を比べる時のぼかし（正面の絵の画素で）
BASE_DIFF = 0.07        # そのぼかしでの色の差がこれより大きい所（外枠につながる塊）は全身の絵を使う


# ---------------------------------------------------------------- 画像

def extract_sources() -> None:
    """絵のブランチから build/recon/src へ取り出す（取り出し済みなら何もしない）"""
    os.makedirs(SRC, exist_ok=True)
    for f in (FRONT_FILE, FACE_FILE, EXPR_FILE):
        dst = os.path.join(SRC, f)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            continue
        data = subprocess.run(['git', '-C', REPO, 'show', f'{ART_REF}:{ART_DIR}/{f}'], check=True,
                              capture_output=True).stdout
        with open(dst, 'wb') as fp:
            fp.write(data)


def load_rgba(name: str) -> np.ndarray:
    """絵を (H, W, 4) の float32（0〜1、乗算していないアルファ）で読む。
    透明な画素の色は一番近い不透明な画素の色で埋める（補間で縁に黒などがにじまないように）"""
    a = np.asarray(Image.open(os.path.join(SRC, name)).convert('RGBA')).astype(np.float32) / 255.0
    valid = a[..., 3] >= 0.5
    idx = ndi.distance_transform_edt(~valid, return_distances=False, return_indices=True)
    a[..., :3] = a[..., :3][idx[0], idx[1]]
    return a


def on_gray(rgba: np.ndarray, sigma: float = 0.0) -> np.ndarray:
    """照合用：灰色（0.5）の背景に重ねた RGB。sigma > 0 ならぼかす"""
    rgb = rgba[..., :3] * rgba[..., 3:] + 0.5 * (1.0 - rgba[..., 3:])
    if sigma > 0:
        rgb = blur3(rgb, sigma)
    return rgb


def blur3(rgb: np.ndarray, sigma: float) -> np.ndarray:
    return np.stack([ndi.gaussian_filter(rgb[..., c], sigma) for c in range(rgb.shape[-1])], -1)


def gray(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)


def sample(img: np.ndarray, x, y, order: int = 1) -> np.ndarray:
    """画像を連続座標 (x, y) で読む（画素の中心は +0.5）。範囲の外は端の値"""
    coords = [np.asarray(y) - 0.5, np.asarray(x) - 0.5]
    if img.ndim == 2:
        return ndi.map_coordinates(img, coords, order=order, mode='nearest')
    return np.stack([ndi.map_coordinates(img[..., c], coords, order=order, mode='nearest')
                     for c in range(img.shape[-1])], -1)


def save_rgb(path: str, rgb: np.ndarray) -> None:
    Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


# ---------------------------------------------------------------- 相似変換とずれの場

@dataclass
class Similarity:
    """相似変換 dst = scale * R(angle) * src + (tx, ty)。画像の座標（y 下向き）で、angle > 0 は x→y の向き"""
    scale: float
    angle: float
    tx: float
    ty: float

    def matrix(self) -> np.ndarray:
        c, s = math.cos(self.angle) * self.scale, math.sin(self.angle) * self.scale
        return np.array([[c, -s, self.tx], [s, c, self.ty]])

    def apply(self, x, y):
        m = self.matrix()
        return m[0, 0] * x + m[0, 1] * y + m[0, 2], m[1, 0] * x + m[1, 1] * y + m[1, 2]

    def inverse(self) -> 'Similarity':
        k = 1.0 / self.scale
        c, s = math.cos(-self.angle) * k, math.sin(-self.angle) * k
        return Similarity(k, -self.angle, -(c * self.tx - s * self.ty), -(s * self.tx + c * self.ty))

    def to_json(self) -> dict:
        return {'scale': self.scale, 'angle_deg': math.degrees(self.angle), 'tx': self.tx, 'ty': self.ty,
                'matrix': self.matrix().tolist()}

    @staticmethod
    def from_json(d: dict) -> 'Similarity':
        return Similarity(d['scale'], math.radians(d['angle_deg']), d['tx'], d['ty'])


@dataclass
class Field:
    """なめらかな残りのずれ (dx, dy)。格子点 (x0 + step * (i + 0.5), y0 + step * (j + 0.5)) で持ち、間は線形補間。
    格子の外は端の値"""
    x0: float
    y0: float
    step: float
    dx: np.ndarray
    dy: np.ndarray

    def at(self, x, y):
        gx = (np.asarray(x) - self.x0) / self.step - 0.5
        gy = (np.asarray(y) - self.y0) / self.step - 0.5
        return (ndi.map_coordinates(self.dx, [gy, gx], order=1, mode='nearest'),
                ndi.map_coordinates(self.dy, [gy, gx], order=1, mode='nearest'))

    def grid(self):
        h, w = self.dx.shape
        gy, gx = np.mgrid[0:h, 0:w].astype(np.float64) + 0.5
        return self.x0 + gx * self.step, self.y0 + gy * self.step

    def stats(self) -> dict:
        m = np.hypot(self.dx, self.dy)
        return {'rms': round(float(np.sqrt((m ** 2).mean())), 3), 'max': round(float(m.max()), 3)}


def smooth_flow(reference: np.ndarray, moving: np.ndarray, weight: np.ndarray, sigma: float):
    """TV-L1 の光学的流れ（moving(p + flow) ≈ reference(p)）を求め、確からしさ weight で重み付けして
    なめらかにする（重み付きのガウスぼかし。重みの薄い所は 4 倍広いぼかしの値に寄せる）。
    返り値 (dx, dy) は格子の単位"""
    v, u = optical_flow_tvl1(reference.astype(np.float32), moving.astype(np.float32), attachment=15)
    w = weight.astype(np.float64)
    wide = 4 * sigma
    wl = ndi.gaussian_filter(w, wide) + 1e-9
    ul, vl = ndi.gaussian_filter(u * w, wide) / wl, ndi.gaussian_filter(v * w, wide) / wl
    lam = 0.05 * w[w > 0].mean()
    ws = ndi.gaussian_filter(w, sigma) + lam
    us = (ndi.gaussian_filter(u * w, sigma) + lam * ul) / ws
    vs = (ndi.gaussian_filter(v * w, sigma) + lam * vl) / ws
    return us, vs


def edge_weight(img: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """流れの確からしさ：模様（明るさの勾配）のある所ほど大きい（0〜1）"""
    gy, gx = np.gradient(ndi.gaussian_filter(img, 0.7))
    e = ndi.gaussian_filter(gx * gx + gy * gy, sigma)
    return np.sqrt(e / (np.quantile(e, 0.99) + 1e-12)).clip(0, 1)


# ---------------------------------------------------------------- 照合

def coarse_match(src: np.ndarray, src_rect, dst: np.ndarray, dst_rect, s_lo: float, s_hi: float,
                 template_px: int = 240) -> tuple[Similarity, float]:
    """粗い照合：src（灰色）の src_rect を倍率 s で縮めた型を、dst の dst_rect の中で探す。
    型がおよそ template_px になるまで両方を縮めて、倍率を s_lo〜s_hi で総当たりする（正規化相互相関）。
    返り値は src→dst の相似変換（回転 0）と相関値"""
    sx0, sy0, sx1, sy1 = src_rect
    dx0, dy0, dx1, dy1 = dst_rect
    size = max(sx1 - sx0, sy1 - sy0) * 0.5 * (s_lo + s_hi)
    work = min(1.0, template_px / size)
    area = dst[dy0:dy1, dx0:dx1]
    if work < 1.0:
        area = rescale(area, work, anti_aliasing=True)
    tpl_src = src[sy0:sy1, sx0:sx1]
    # 型の大きさが 1 段で約 1px 変わる刻み
    n = max(8, int(math.ceil((s_hi - s_lo) / (0.5 * (s_lo + s_hi)) * template_px)))
    best = (-2.0, s_lo, 0, 0)
    for s in np.linspace(s_lo, s_hi, n):
        tpl = rescale(tpl_src, s * work, anti_aliasing=True)
        if tpl.shape[0] >= area.shape[0] or tpl.shape[1] >= area.shape[1]:
            continue
        r = match_template(area, tpl)
        iy, ix = np.unravel_index(np.argmax(r), r.shape)
        if r[iy, ix] > best[0]:
            best = (float(r[iy, ix]), float(s), ix, iy)
    score, s, ix, iy = best
    # 型の左上の角 (sx0, sy0) が dst の (dx0 + ix / work, dy0 + iy / work) に来る
    return Similarity(s, 0.0, dx0 + ix / work - s * sx0, dy0 + iy / work - s * sy0), score


def weighted_ncc(a: np.ndarray, b: np.ndarray, w: np.ndarray) -> float:
    """重み付きの正規化相互相関"""
    n = w.sum()
    a = a - (a * w).sum() / n
    b = b - (b * w).sum() / n
    return float((a * b * w).sum() / math.sqrt((a * a * w).sum() * (b * b * w).sum() + 1e-12))


def refine(face: np.ndarray, other: np.ndarray, t0: Similarity, rect, exclude=None,
           passes=((2.0, 2, 3.0), (0.6, 1, 1.0))) -> tuple[Similarity, float]:
    """細かい照合：顔の絵の格子点で、t（顔→other）で写した other の明るさと顔の明るさの重み付き相関が
    最大になるよう、倍率・回転・平行移動を Nelder-Mead で追い込む。
    face, other：(H, W, 4)。rect：顔の絵の上の照合範囲。exclude：照合から外す範囲。
    passes：(ぼかし σ（other の画素で）, 格子の粗さ（other の画素で）, 初期の単体の大きさ)。粗い→細かいの順"""
    s0 = t0.scale                                   # other の画素 / 顔の画素
    x0, y0, x1, y1 = rect
    t = t0
    score = 0.0
    for sigma, coarse, size in passes:
        step = max(1, int(round(coarse * 0.9 / s0)))
        ys, xs = np.mgrid[y0:y1:step, x0:x1:step].astype(np.float64) + 0.5
        w = np.ones_like(xs)
        if exclude is not None:
            ex0, ey0, ex1, ey1 = exclude
            w[(xs > ex0) & (xs < ex1) & (ys > ey0) & (ys < ey1)] = 0.0
        # 顔の絵は other の解像度に合わせてからぼかす（other の 1 画素 = 顔の 1/s0 画素）
        face_b = gray(on_gray(face, math.hypot(0.5, sigma) / s0))
        other_b = gray(on_gray(other, sigma))
        target = sample(face_b, xs, ys)

        def cost(p, _t=t):
            tt = Similarity(_t.scale * math.exp(p[0]), _t.angle + p[1], _t.tx + p[2], _t.ty + p[3])
            u, v = tt.apply(xs, ys)
            return -weighted_ncc(sample(other_b, u, v), target, w)

        simplex = [[0, 0, 0, 0], [0.006 * size, 0, 0, 0], [0, 0.006 * size, 0, 0],
                   [0, 0, 1.5 * size, 0], [0, 0, 0, 1.5 * size]]
        r = optimize.minimize(cost, np.zeros(4), method='Nelder-Mead',
                              options=dict(initial_simplex=simplex, xatol=1e-5, fatol=1e-7, maxiter=600))
        p = r.x
        t = Similarity(t.scale * math.exp(p[0]), t.angle + p[1], t.tx + p[2], t.ty + p[3])
        score = -float(r.fun)
    return t, score


def patch_shift(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """同じ格子で読んだ 2 枚の小窓の、b の中身が a からどれだけずれているか（格子の単位、位相相関）"""
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    a = (a - a.mean()) * win
    b = (b - b.mean()) * win
    shift, _, _ = phase_cross_correlation(a, b, upsample_factor=20, normalization=None)
    return -float(shift[1]), -float(shift[0])


# ---------------------------------------------------------------- 顔の絵 ↔ 全身の正面の絵

@dataclass
class FrontAlign:
    """顔の絵 → 全身の正面の絵。正面の画素 p の中身は、顔の絵の T⁻¹(p + field(p)) にある"""
    t: Similarity
    field: Field | None

    def front_to_face(self, fx, fy):
        if self.field is not None:
            dx, dy = self.field.at(fx, fy)
            fx, fy = fx + dx, fy + dy
        return self.t.inverse().apply(fx, fy)


def residual_stats(a: np.ndarray, b: np.ndarray, valid: np.ndarray, patch: int = 32, stride: int = 16) -> dict:
    """同じ格子で読んだ 2 枚（a が基準、b が写した物）を小窓に分け、残りのずれ（位相相関、格子の単位）を測る。
    2 方向の模様が足りない小窓（平らな所・まっすぐな縁だけの所）はずれが決まらないので使わない"""
    shifts = []
    h, w = a.shape
    for y in range(0, h - patch + 1, stride):
        for x in range(0, w - patch + 1, stride):
            if not valid[y:y + patch, x:x + patch].all():
                continue
            pa, pb = a[y:y + patch, x:x + patch], b[y:y + patch, x:x + patch]
            gy, gx = np.gradient(pa)
            jxx, jyy, jxy = (gx * gx).mean(), (gy * gy).mean(), (gx * gy).mean()
            if 0.5 * (jxx + jyy - math.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)) < STRUCT_MIN:
                continue
            shifts.append(patch_shift(pa, pb))
    if not shifts:
        return {'patches': 0}
    m = np.hypot(*np.array(shifts).T)
    return {'patches': len(shifts), 'median': round(float(np.median(m)), 3),
            'p90': round(float(np.quantile(m, 0.9)), 3), 'max': round(float(m.max()), 3)}


def landmark_shifts(a: np.ndarray, b: np.ndarray, points: dict, half: int) -> dict:
    """目印（格子の添字）のまわり ±half の小窓ごとの残りのずれ（格子の単位）"""
    res = {}
    for name, (cx, cy) in points.items():
        cx, cy = int(round(cx)), int(round(cy))
        dx, dy = patch_shift(a[cy - half:cy + half, cx - half:cx + half], b[cy - half:cy + half, cx - half:cx + half])
        res[name] = [round(dx, 2), round(dy, 2)]
    return res


def front_residuals(front, face, fa: FrontAlign) -> dict:
    """顔の絵を写した物と正面の絵の残りのずれ（正面の絵の画素）。顔の窓の中の小窓の統計と、目印ごと"""
    x0, y0, x1, y1 = FACE_WINDOW
    (fx0, fx1), (fy0, fy1) = fa.t.apply(np.array([x0, x1]), np.array([y0, y1]))
    gx0, gy0 = math.floor(fx0) - 8, math.floor(fy0) - 8
    h, w = int(math.ceil(fy1)) + 8 - gy0, int(math.ceil(fx1)) + 8 - gx0
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64) + 0.5
    px, py = gx0 + gx, gy0 + gy
    a = gray(on_gray(sample(front, px, py)))
    b_rgba = sample(np.concatenate([on_gray(face, 0.5 / fa.t.scale), face[..., 3:]], -1), *fa.front_to_face(px, py))
    valid = (sample(front[..., 3], px, py) > 0.5) & (b_rgba[..., 3] > 0.5)
    pts = {}
    for name, (x, y) in FRONT_LANDMARKS.items():
        ox, oy = fa.t.apply(x, y)
        pts[name] = (ox - gx0 - 0.5, oy - gy0 - 0.5)                  # 格子の添字
    return {'window_patches': residual_stats(a, gray(b_rgba), valid, patch=24, stride=12),
            'landmarks': landmark_shifts(a, gray(b_rgba), pts, 14)}


def align_face_to_front(front: np.ndarray, face: np.ndarray) -> tuple[FrontAlign, dict]:
    """顔の絵 → 全身の正面の絵：相似変換と、なめらかなずれの場"""
    # 全身の正面の絵で頭のあたり：外形の一番上から下へ 520px、左右は頭の上の方の中心 ±300px
    alpha = front[..., 3] > 0.5
    top = int(np.nonzero(alpha.any(1))[0][0])
    cols = np.nonzero(alpha[top:top + 300].any(0))[0]
    cx = int((cols[0] + cols[-1]) / 2)
    dst_rect = (cx - 300, max(0, top - 40), cx + 300, top + 520)
    t0, c0 = coarse_match(gray(on_gray(face)), FACE_FEATURES_RECT, gray(on_gray(front)), dst_rect, *FRONT_SCALE)
    print(f'  粗い照合：倍率 {t0.scale:.4f} 相関 {c0:.4f}')
    t, c = refine(face, front, t0, FACE_HEAD_RECT)
    print(f'  相似変換：倍率 {t.scale:.5f} 回転 {math.degrees(t.angle):.3f}° '
          f'移動 ({t.tx:.2f}, {t.ty:.2f}) 相関 {c:.4f}')
    res_sim = front_residuals(front, face, FrontAlign(t, None))

    # ずれの場：頭全体（FACE_HEAD_RECT を正面の絵へ写した範囲）を、正面の絵の 1px の格子で
    x0, y0, x1, y1 = FACE_HEAD_RECT
    (ax0, ax1), (ay0, ay1) = t.apply(np.array([x0, x1]), np.array([y0, y1]))
    gx0, gy0 = math.floor(ax0), math.floor(ay0)
    w_, h_ = int(math.ceil(ax1)) - gx0, int(math.ceil(ay1)) - gy0
    gy, gx = np.mgrid[0:h_, 0:w_].astype(np.float64) + 0.5
    px, py = gx0 + gx, gy0 + gy
    ref = gray(on_gray(sample(front, px, py)))
    ux, uy = t.inverse().apply(px, py)
    mov_rgba = sample(np.concatenate([on_gray(face, 0.5 / t.scale), face[..., 3:]], -1), ux, uy)
    mov = gray(mov_rgba)
    weight = edge_weight(ref) * (sample(front[..., 3], px, py) > 0.5) * (mov_rgba[..., 3] > 0.5)
    weight *= uy < FACE_NECK_Y
    dx, dy = smooth_flow(ref, mov, weight, FIELD_SIGMA_FRONT)
    field = Field(gx0, gy0, 1.0, dx, dy)
    fa = FrontAlign(t, field)
    res = front_residuals(front, face, fa)
    print(f'  ずれの場：{field.stats()}（正面の画素）')
    print(f'  残りのずれ（窓の中の小窓、正面の画素）：相似変換だけ {res_sim["window_patches"]} → '
          f'場も使う {res["window_patches"]}')
    info = {'ncc': c, 'coarse_ncc': c0, 'residuals_similarity_only': res_sim, 'residuals_with_field': res}
    return fa, info


# ---------------------------------------------------------------- 4 表情 ↔ 顔の絵

@dataclass
class ExprAlign:
    """顔の絵 → 表情の絵。顔の絵の点 X の中身は、表情 i の絵の T_i(Y + field(Y))（Y = X + extra_i(X)）にある。
    field は「通常」の頭と顔の絵の間の共通のずれ、extra_i は同じ絵の中の「通常」の頭と表情 i の頭の間の
    小さなずれ（表情で変わる所を除いて求める。通常は None）"""
    t: list[Similarity]
    field: Field | None
    extra: list[Field | None] | None = None

    def face_to_expr(self, i: int, x, y):
        if self.extra is not None and self.extra[i] is not None:
            dx, dy = self.extra[i].at(x, y)
            x, y = x + dx, y + dy
        if self.field is not None:
            dx, dy = self.field.at(x, y)
            x, y = x + dx, y + dy
        return self.t[i].apply(x, y)


def expr_residuals(face, expr, ea: ExprAlign, i: int) -> dict:
    """顔の絵と表情 i の頭の残りのずれ（表情の絵の画素）。頭の小窓の統計（表情 1〜3 は眉・目・口の範囲を除く）と、
    目印ごと"""
    s = ea.t[i].scale
    step = 1.0 / s
    x0, y0, x1, y1 = FACE_HEAD_RECT
    h, w = int((FACE_NECK_Y - y0) / step), int((x1 - x0) / step)
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64) + 0.5
    X, Y = x0 + gx * step, y0 + gy * step
    a_rgba = sample(np.concatenate([on_gray(face, 0.5 / s), face[..., 3:]], -1), X, Y)
    b_rgba = sample(np.concatenate([on_gray(expr), expr[..., 3:]], -1), *ea.face_to_expr(i, X, Y))
    valid = (a_rgba[..., 3] > 0.5) | (b_rgba[..., 3] > 0.5)                 # 外形の縁も使う
    if i > 0:
        ex0, ey0, ex1, ey1 = FACE_EXPR_RECT
        valid &= ~((X > ex0) & (X < ex1) & (Y > ey0) & (Y < ey1))
    pts = {n: ((x - x0) / step - 0.5, (y - y0) / step - 0.5) for n, (x, y) in EXPR_LANDMARKS.items()}
    return {'head_patches': residual_stats(gray(a_rgba), gray(b_rgba), valid, patch=32, stride=16),
            'landmarks': landmark_shifts(gray(a_rgba), gray(b_rgba), pts, 20)}


def align_expressions_to_face(expr: np.ndarray, face: np.ndarray) -> tuple[ExprAlign, list[dict]]:
    """4 表情の各頭：顔の絵 → 表情の絵（2048 四方の全体の座標）の相似変換と、共通のずれの場"""
    face_g = gray(on_gray(face))
    expr_g = gray(on_gray(expr))
    ts, infos = [], []
    for i, name in enumerate(EXPRESSIONS):
        qx, qy = (i % 2) * QUAD, (i // 2) * QUAD
        t0, c0 = coarse_match(face_g, FACE_HEAD_RECT, expr_g, (qx, qy, qx + QUAD, qy + QUAD), *EXPR_SCALE)
        t, c = refine(face, expr, t0, FACE_HEAD_RECT, exclude=FACE_EXPR_RECT)
        print(f'  {name}: 倍率 {t.scale:.5f} 回転 {math.degrees(t.angle):.3f}° '
              f'移動 ({t.tx:.2f}, {t.ty:.2f}) 相関 {c:.4f}（粗い {c0:.4f}）')
        ts.append(t)
        infos.append({'name': name, 'quadrant_image_px': [qx, qy, qx + QUAD, qy + QUAD], 'ncc': c,
                      'coarse_ncc': c0})
    res_sim = [expr_residuals(face, expr, ExprAlign(ts, None), i) for i in range(4)]

    # ずれの場：「通常」の頭と顔の絵（同じ表情）の間の流れを、表情の絵のほぼ 1 画素の格子で
    st = FIELD_STEP_EXPR
    x0, y0, x1, y1 = FACE_HEAD_RECT
    h_, w_ = int((y1 - y0) / st), int((x1 - x0) / st)
    gy, gx = np.mgrid[0:h_, 0:w_].astype(np.float64) + 0.5
    X, Y = x0 + gx * st, y0 + gy * st
    ref_rgba = sample(np.concatenate([on_gray(face, 0.5 / ts[0].scale), face[..., 3:]], -1), X, Y)
    mov_rgba = sample(np.concatenate([on_gray(expr), expr[..., 3:]], -1), *ts[0].apply(X, Y))
    ref, mov = gray(ref_rgba), gray(mov_rgba)
    weight = edge_weight(ref) * (ref_rgba[..., 3] > 0.5) * (mov_rgba[..., 3] > 0.5) * (Y < FACE_NECK_Y)
    dx, dy = smooth_flow(ref, mov, weight, FIELD_SIGMA_EXPR / (ts[0].scale * st))
    field = Field(x0, y0, st, dx * st, dy * st)          # 顔の絵の画素で持つ
    ea = ExprAlign(ts, field, [None] * 4)
    print(f'  ずれの場：{field.stats()}（顔の絵の画素）')

    # 表情ごとの小さなずれ：同じ絵の中の「通常」の頭と表情 i の頭（輪郭やあごの線のわずかな差）。
    # 表情で変わる所（大きな塊）は流れが当てにならないので重みから外し、まわりからなめらかに埋める
    expr_rgba = np.concatenate([on_gray(expr), expr[..., 3:]], -1)
    ref_rgba = sample(expr_rgba, *ea.face_to_expr(0, X, Y))
    ref = gray(ref_rgba)
    for i in range(1, 4):
        mov_rgba = sample(expr_rgba, *ea.face_to_expr(i, X, Y))
        mov = gray(mov_rgba)
        diff = np.abs(ndi.gaussian_filter(ref, 1.0) - ndi.gaussian_filter(mov, 1.0)) > 0.08
        feat = ndi.binary_opening(diff, structure=disk(3))
        feat = ndi.binary_dilation(feat, structure=disk(8))
        weight = edge_weight(ref) * (ref_rgba[..., 3] > 0.5) * (mov_rgba[..., 3] > 0.5) * (Y < FACE_NECK_Y) * ~feat
        dx, dy = smooth_flow(ref, mov, weight, FIELD_SIGMA_EXPR / (ts[i].scale * st))
        ea.extra[i] = Field(x0, y0, st, dx * st, dy * st)
        print(f'  {EXPRESSIONS[i]} の小さなずれ：{ea.extra[i].stats()}（顔の絵の画素）')
    for i, info in enumerate(infos):
        info['residuals_similarity_only'] = res_sim[i]
        info['residuals_with_field'] = expr_residuals(face, expr, ea, i)
        print(f'  {EXPRESSIONS[i]} の残りのずれ（頭の小窓、表情の画素）：相似変換だけ '
              f'{res_sim[i]["head_patches"]} → 場も使う {info["residuals_with_field"]["head_patches"]}')
    return ea, infos


# ---------------------------------------------------------------- アトラス

def atlas_layout(fa: FrontAlign) -> dict:
    """顔の窓（正面の絵の画素、整数）と、区画 0 での置き場所を決める"""
    x0, y0, x1, y1 = FACE_WINDOW
    fx, fy = fa.t.apply(np.array([x0, x1, x0, x1]), np.array([y0, y0, y1, y1]))
    wx0, wy0, wx1, wy1 = (int(round(fx.min())), int(round(fy.min())), int(round(fx.max())), int(round(fy.max())))
    k = ATLAS_SCALE
    w, h = (wx1 - wx0) * k, (wy1 - wy0) * k
    if max(w, h) > QUAD - 2 * MIN_MARGIN:
        raise ValueError(f'顔の窓がアトラスの区画に入らない：{w}×{h}')
    qx0, qy0 = int(round((QUAD - w) / 2)), int(round((QUAD - h) / 2))
    return {'k': k, 'window_front': [wx0, wy0, wx1, wy1],
            'window_atlas': [qx0, qy0, int(qx0 + w), int(qy0 + h)]}


def quadrant_grid(layout: dict) -> tuple[np.ndarray, np.ndarray]:
    """区画 0 の各画素の中心 → 正面の絵の画素 (fx, fy)"""
    k = layout['k']
    wx0, wy0 = layout['window_front'][:2]
    qx0, qy0 = layout['window_atlas'][:2]
    ay, ax = np.mgrid[0:QUAD, 0:QUAD].astype(np.float64) + 0.5
    return wx0 + (ax - qx0) / k, wy0 + (ay - qy0) / k


def fit_gain_offset(src: np.ndarray, dst: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """色ごとに dst ≈ gain * src + offset を当てはめる（外れの大きい 1 割を捨てて 2 回）"""
    gain, offset = np.ones(3), np.zeros(3)
    for c in range(3):
        x, y = src[..., c][mask], dst[..., c][mask]
        keep = np.ones_like(x, bool)
        for _ in range(2):
            a, b = np.polyfit(x[keep], y[keep], 1)
            r = np.abs(a * x + b - y)
            keep = r <= np.quantile(r, 0.9)
        gain[c], offset[c] = np.clip(a, 0.75, 1.25), b
    return gain, offset


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def build_atlas(front, face, expr, fa: FrontAlign, ea: ExprAlign) -> dict:
    """表情アトラスを作る。返り値に画像・範囲・確認用の値。

    区画の中身（4 区画に共通の土台）：
      顔の絵（高解像度、色は全身の正面の絵に合わせる）… 窓の内側で、正面の絵と中身が合っている所
      全身の正面の絵（引き伸ばし）…………………………… 窓の縁の近く・窓の外・顔の絵と中身が違う所
    （顔の絵は首の下の髪が長いなど、窓の下の角で全身の絵と違う。そこは全身の絵を使う。
      窓の縁に向けて全身の絵へなめらかに移るので、窓の外の体のテクスチャと継ぎ目が出ない）
    その上で、表情の領域だけ各表情の絵に差し替える"""
    layout = atlas_layout(fa)
    k = layout['k']
    fx, fy = quadrant_grid(layout)
    ux, uy = fa.front_to_face(fx, fy)                                # 区画の画素 → 顔の絵の画素

    face_rgba = np.clip(sample(face, ux, uy, order=3), 0, 1)
    face_rgb, face_a = face_rgba[..., :3], face_rgba[..., 3]
    front_rgba = np.clip(sample(front, fx, fy, order=3), 0, 1)       # 全身の正面の絵をアトラスの細かさで
    front_rgb, front_a = front_rgba[..., :3], front_rgba[..., 3]

    # 各表情の絵を区画へ写す（アトラス 1 画素 ≈ 表情の絵 1/up 画素）
    exprs = [np.clip(sample(expr, *ea.face_to_expr(i, ux, uy), order=3), 0, 1) for i in range(4)]
    up = k * fa.t.scale / ea.t[0].scale

    qx0, qy0, qx1, qy1 = layout['window_atlas']
    ay, ax = np.mgrid[0:QUAD, 0:QUAD]
    window = (ax >= qx0) & (ax < qx1) & (ay >= qy0) & (ay < qy1)
    # 窓の縁からの距離（窓の外は負）
    border_dist = np.minimum(np.minimum(ax + 0.5 - qx0, qx1 - ax - 0.5), np.minimum(ay + 0.5 - qy0, qy1 - ay - 0.5))

    # 1) 表情の領域：表情の絵の「通常」と各表情の違う所（同じ絵の中の比較なので、描き方の差が出ない）を集め、
    #    眉＋目・口ごとの塊の凸包を少し広げてぼかす
    e0_cmp = blur3(exprs[0][..., :3], 0.5 * up)
    changed = np.zeros((QUAD, QUAD), bool)
    for e in exprs[1:]:
        d = np.abs(blur3(e[..., :3], 0.5 * up) - e0_cmp).max(-1)
        m = (d > ZONE_DIFF) & window & (face_a > 0.5) & (e[..., 3] > 0.5)
        if ZONE_RECT:
            m &= (ux >= ZONE_RECT[0]) & (ux < ZONE_RECT[2]) & (uy >= ZONE_RECT[1]) & (uy < ZONE_RECT[3])
        m = ndi.binary_opening(m, structure=disk(ZONE_OPEN))
        lab, n = ndi.label(m)
        if n:
            sizes = ndi.sum(m, lab, range(1, n + 1))
            m = np.isin(lab, 1 + np.nonzero(sizes >= ZONE_MIN_AREA)[0])
        changed |= m
    changed_gap = float(border_dist[changed].min())
    if changed_gap < ZONE_SAFE:
        raise ValueError(f'表情で変わる所が顔の窓の縁に近すぎる（{changed_gap:.0f}px）。FACE_WINDOW を広げる')
    zone = ndi.binary_closing(changed, structure=disk(ZONE_CLOSE))
    zone = ndi.binary_fill_holes(zone | changed)
    zone = convex_hull_object(zone)
    # 小さな塊（前髪の先・あごの線などの描き方のわずかな差）は差し替えない。髪や輪郭は表情で変えない方が形と合う
    lab, n = ndi.label(zone)
    sizes = ndi.sum(zone, lab, range(1, n + 1))
    zone = np.isin(lab, 1 + np.nonzero(sizes >= ZONE_MIN_HULL)[0])
    zone = ndi.binary_dilation(zone, structure=disk(ZONE_GROW))
    alpha = ndi.gaussian_filter(zone.astype(np.float32), ZONE_FEATHER)
    # 窓の縁の近く（ZONE_EDGE 以内）では必ず 0 に落とす（縁は 4 区画で同じ画素になる）
    alpha *= smoothstep((border_dist - ZONE_EDGE) / (ZONE_SAFE - ZONE_EDGE))
    alpha[alpha < 1e-3] = 0.0
    border_gap = float(border_dist[alpha > 0].min())

    # 2) 顔の絵の色を全身の正面の絵に合わせる（同じ細かさにぼかして、模様の少ない所で当てはめる）
    face_lo = blur3(face_rgb, 0.5 * k)
    front_lo = blur3(front_rgb, 0.25 * k)
    grad = np.hypot(*np.gradient(gray(face_lo)))
    ok = (front_a > 0.99) & (face_a > 0.99) & (grad < 0.01) & (~zone) & window
    gain, offset = fit_gain_offset(face_lo, front_lo, ok)
    face_cc = np.clip(face_rgb * gain + offset, 0, 1)

    # 3) 顔の絵と全身の絵の中身が違う所（首の下の髪の長さ・外形の違いなど）。粗くぼかして比べ、
    #    区画の外枠につながる塊だけを使う（顔の中の目や口は、解像度の差で色の差が出ても全身の絵にしない）
    sc = BASE_SIGMA * k
    d = np.abs(blur3(face_cc, sc) - blur3(front_rgb, sc)).max(-1)
    alpha_differ = ndi.gaussian_filter(((face_a > 0.5) != (front_a > 0.5)).astype(np.float32), sc) > 0.2
    pad = 10                                                        # 外枠に触れる塊が閉じる処理で削れないように
    differ = np.pad((d > BASE_DIFF) | alpha_differ, pad, mode='edge')
    differ = ndi.binary_closing(differ, structure=disk(8))[pad:-pad, pad:-pad]
    lab, n = ndi.label(differ)
    frame = np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    differ = np.isin(lab, np.unique(frame[frame > 0]))
    differ = ndi.binary_fill_holes(differ) & ~zone
    use_face = 1.0 - ndi.gaussian_filter(differ.astype(np.float32), 5.0)
    use_face *= smoothstep((border_dist - BASE_EDGE[0]) / (BASE_EDGE[1] - BASE_EDGE[0]))
    use_face = np.maximum(use_face, alpha)                          # 表情の領域はいつも顔の絵（と表情の絵）
    base = face_cc * use_face[..., None] + front_rgb * (1 - use_face[..., None])

    # 4) 表情の絵の鮮明さを顔の絵に近づける（通常の表情の絵で、顔の絵との差が最小になる強さを求める）
    e0 = exprs[0][..., :3]
    detail = e0 - blur3(e0, 0.6 * up)
    zmask = zone & (face_a > 0.5)
    r = (face_rgb - e0)[zmask]
    h = detail[zmask]
    # 当てはめた強さ（約 0.49）は暗い縁に淡い輪を残したので、SHARPEN_MAX までに抑える
    sharpen = float(np.clip((r * h).sum() / max((h * h).sum(), 1e-9), 0.0, SHARPEN_MAX))

    # 5) 表情ごとに：鮮明さをそろえ、領域のまわりの帯で色を土台に合わせ、ぼかした領域だけ差し替える
    base_cmp = blur3(base, 0.5 * up)
    ring = ndi.binary_dilation(zone, structure=disk(24)) & ~zone & window & (face_a > 0.5)
    feather = (alpha > 0.02) & (alpha < 0.98)
    quads = [base]
    expr_color, feather_err = [], []
    for e in exprs[1:]:
        rgb = e[..., :3]
        rgb = np.clip(rgb + sharpen * (rgb - blur3(rgb, 0.6 * up)), 0, 1)
        g, o = fit_gain_offset(blur3(rgb, 0.5 * up), base_cmp, ring & (e[..., 3] > 0.5))
        rgb = np.clip(rgb * g + o, 0, 1)
        expr_color.append({'gain': g.round(4).tolist(), 'offset': o.round(4).tolist()})
        feather_err.append(round(float(np.abs(blur3(rgb, 0.5 * up) - base_cmp)[feather].mean() * 255), 3))
        quads.append(base * (1 - alpha[..., None]) + rgb * alpha[..., None])

    # 透明な所：土台は透明な画素の色を一番近い不透明な画素の色で埋めた絵から作っているので、透明な画素はない
    n_transparent = int(((face_a < 0.5) & (front_a < 0.5)).sum())

    atlas = np.zeros((ATLAS, ATLAS, 3), np.float32)
    for i, q in enumerate(quads):
        atlas[(i // 2) * QUAD:(i // 2 + 1) * QUAD, (i % 2) * QUAD:(i % 2 + 1) * QUAD] = q

    # 確かめ：窓の縁（±3px の帯）で 4 区画が同じか、全身の正面の絵との差
    band = np.abs(border_dist) <= 3
    q8 = [np.round(np.clip(q, 0, 1) * 255) for q in quads]
    border_diff = max(float(np.abs(q8[i][band] - q8[0][band]).max()) for i in range(1, 4))
    outside_diff = max(float(np.abs(q8[i][~(alpha > 0)] - q8[0][~(alpha > 0)]).max()) for i in range(1, 4))
    seam_front = float(np.abs(quads[0][band] - front_rgb[band]).mean() * 255)
    # 窓の内側の顔の絵の部分が、全身の絵とどれだけ合っているか（全身の絵の細かさで比べる）
    inner = (use_face > 0.99) & (alpha == 0) & (front_a > 0.99)
    inner_err = float(np.abs(blur3(face_cc, 0.5 * k) - front_lo)[inner].mean() * 255)
    inner_err_raw = float(np.abs(blur3(face_rgb, 0.5 * k) - front_lo)[inner].mean() * 255)

    zy, zx = np.nonzero(alpha > 0)
    zone_atlas = [int(zx.min()), int(zy.min()), int(zx.max()) + 1, int(zy.max()) + 1]
    dy_, dx_ = np.nonzero(differ & window)
    return {
        'atlas': atlas, 'layout': layout, 'alpha': alpha, 'use_face': use_face, 'zone_atlas': zone_atlas,
        'zone_front': [float(fx[0, zone_atlas[0]]), float(fy[zone_atlas[1], 0]),
                       float(fx[0, zone_atlas[2] - 1]), float(fy[zone_atlas[3] - 1, 0])],
        'border_gap': border_gap, 'changed_gap': changed_gap, 'border_diff': border_diff,
        'outside_diff': outside_diff, 'sharpen': sharpen, 'expr_color': expr_color, 'feather_err': feather_err,
        'gain': gain, 'offset': offset, 'seam_front': seam_front, 'inner_err': inner_err,
        'inner_err_raw': inner_err_raw, 'n_transparent': n_transparent,
        'differ_fraction_in_window': round(float((differ & window).sum() / window.sum()), 4),
        'coverage_front': [float(fx[0, 0] - 0.5 / k), float(fy[0, 0] - 0.5 / k),
                           float(fx[0, -1] + 0.5 / k), float(fy[-1, 0] + 0.5 / k)],
    }


# ---------------------------------------------------------------- テクスチャ貼りの工程から使う

def load_atlas_meta(path: str | None = None) -> dict:
    with open(path or os.path.join(WORK, 'face_atlas.json')) as fp:
        return json.load(fp)


def front_px_to_face_uv(fx, fy, meta: dict | None = None):
    """正面の絵の画素 (fx, fy) → 顔の材質の Blender UV（区画 0 = 通常）。numpy の配列でもよい"""
    meta = meta or load_atlas_meta()
    lu, lv = meta['blender_uv_linear']['u'], meta['blender_uv_linear']['v']
    return lu['a'] * np.asarray(fx) + lu['b'], lv['a'] * np.asarray(fy) + lv['b']


def world_to_face_uv(x, z, calib: dict | None = None, meta: dict | None = None):
    """世界の点（Blender、x と z）→ 顔の材質の Blender UV。calib は calib.json（front の視点を使う）"""
    if calib is None:
        with open(os.path.join(WORK, 'calib.json')) as fp:
            calib = json.load(fp)
    v = calib['views']['front']
    fx = v['u0'] + v['pixels_per_meter'] * np.asarray(x) * v['image_right'][0]
    fy = v['v0'] - v['pixels_per_meter'] * np.asarray(z)
    return front_px_to_face_uv(fx, fy, meta)


# ---------------------------------------------------------------- 確認画像

def checker(a: np.ndarray, b: np.ndarray, cell: int) -> np.ndarray:
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    m = ((yy // cell + xx // cell) % 2 == 0)[..., None]
    return np.where(m, a, b)


def anaglyph(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a を赤、b を青緑に。ずれている所だけ色がにじむ"""
    ga, gb = gray(a), gray(b)
    return np.stack([ga, gb, gb], -1)


def label(img: Image.Image, xy, text: str) -> None:
    d = ImageDraw.Draw(img)
    x, y = xy
    d.rectangle((x, y, x + 7 * len(text) + 12, y + 22), fill=(0, 0, 0))
    d.text((x + 6, y + 5), text, fill=(255, 255, 255))


def write_align_check(front, face, fa: FrontAlign, layout: dict, path: str) -> None:
    """正面の絵の頭（2 倍）。左上 元の絵（窓を黄色で）、右上 顔の絵を写した物との市松、
    左下 赤＝正面・青緑＝顔の絵（相似変換だけ）、右下 同じ（ずれの場も使う）"""
    wx0, wy0, wx1, wy1 = layout['window_front']
    cx = (wx0 + wx1) / 2
    x0, y0, x1, y1 = cx - 190, wy0 - 215, cx + 190, wy1 + 25
    up = 2
    gy, gx = np.mgrid[0:int((y1 - y0) * up), 0:int((x1 - x0) * up)].astype(np.float64) + 0.5
    px, py = x0 + gx / up, y0 + gy / up
    fr = on_gray(sample(front, px, py, order=1))
    fc_sim = on_gray(sample(face, *fa.t.inverse().apply(px, py), order=3))
    fc = on_gray(sample(face, *fa.front_to_face(px, py), order=3))
    grid = np.concatenate([np.concatenate([fr, checker(fr, fc, 16 * up)], 1),
                           np.concatenate([anaglyph(fr, fc_sim), anaglyph(fr, fc)], 1)], 0)
    img = Image.fromarray((np.clip(grid, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    h, w = fr.shape[:2]
    for oy in (0, h):
        for ox in (0, w):
            d.rectangle((ox + (wx0 - x0) * up, oy + (wy0 - y0) * up, ox + (wx1 - x0) * up, oy + (wy1 - y0) * up),
                        outline=(255, 230, 0), width=2)
    label(img, (6, 6), 'front + face window')
    label(img, (w + 6, 6), 'checker front / face (final)')
    label(img, (6, h + 6), 'red=front cyan=face (similarity only)')
    label(img, (w + 6, h + 6), 'red=front cyan=face (similarity + field)')
    img.save(path)


def write_expr_check(face, expr, ea: ExprAlign, path: str) -> None:
    """4 表情：顔の絵の座標で、左 市松（顔の絵／表情）、右 赤＝顔の絵・青緑＝表情（ずれの場も使う）"""
    x0, y0, x1, y1 = FACE_HEAD_RECT
    step = 4
    gy, gx = np.mgrid[y0:y1:step, x0:x1:step].astype(np.float64) + 0.5
    fc = on_gray(sample(face, gx, gy))
    rows = []
    for i in range(4):
        e = on_gray(sample(expr, *ea.face_to_expr(i, gx, gy)))
        rows.append(np.concatenate([checker(fc, e, 12), anaglyph(fc, e)], 1))
    grid = np.concatenate([np.concatenate(rows[:2], 1), np.concatenate(rows[2:], 1)], 0)
    img = Image.fromarray((np.clip(grid, 0, 1) * 255).astype(np.uint8))
    h, w = rows[0].shape[:2]
    for i, name in enumerate(EXPRESSIONS):
        label(img, ((i % 2) * w + 6, (i // 2) * h + 6), f'{name}: checker face/expr | red=face cyan=expr')
    img.save(path)


def write_atlas_check(res: dict, path: str) -> None:
    """アトラス：窓（水色）、表情の領域（桃色の線）、顔の絵と全身の正面の絵の境（黄色の点線。外側が全身の絵）"""
    arr = (np.clip(res['atlas'], 0, 1) * 255).astype(np.uint8)
    edge = res['alpha'] > 0.5
    edge = edge & ~ndi.binary_erosion(edge, iterations=3)
    ey, ex = np.nonzero(edge)
    src = res['use_face'] > 0.5                                     # 顔の絵を使う所と全身の絵を使う所の境
    src_edge = src & ~ndi.binary_erosion(src, iterations=2)
    sy, sx = np.nonzero(src_edge & (((np.arange(QUAD)[:, None] + np.arange(QUAD)[None, :]) // 8) % 2 == 0))
    for i in range(4):
        ox, oy = (i % 2) * QUAD, (i // 2) * QUAD
        arr[ey + oy, ex + ox] = (255, 60, 200)
        arr[sy + oy, sx + ox] = (255, 220, 0)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    qx0, qy0, qx1, qy1 = res['layout']['window_atlas']
    for i, name in enumerate(EXPRESSIONS):
        ox, oy = (i % 2) * QUAD, (i // 2) * QUAD
        d.rectangle((ox + qx0, oy + qy0, ox + qx1 - 1, oy + qy1 - 1), outline=(0, 230, 255), width=4)
        d.rectangle((ox, oy, ox + QUAD - 1, oy + QUAD - 1), outline=(255, 255, 255), width=2)
        label(img, (ox + 10, oy + 10), f'{i} {name}')
    img.save(path)


def write_seam_check(front, res: dict, path: str) -> None:
    """正面の絵の頭（アトラスと同じ細かさに引き伸ばし）の窓の中を、各表情の区画で置き換えた物。
    窓の縁に継ぎ目が見えないことを確かめる（線は描かない）。全身の絵の外形の外は灰色"""
    lay = res['layout']
    k = lay['k']
    wx0, wy0, wx1, wy1 = lay['window_front']
    qx0, qy0, qx1, qy1 = lay['window_atlas']
    m = 40                                        # 窓のまわりに見せる幅（正面の絵の画素）
    x0, y0 = wx0 - m, wy0 - m
    w, h = int((wx1 - wx0 + 2 * m) * k), int((wy1 - wy0 + 2 * m) * k)
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float64) + 0.5
    fr_rgba = sample(front, x0 + gx / k, y0 + gy / k, order=3)
    tiles = []
    iy, ix = int(m * k), int(m * k)
    for i in range(4):
        ox, oy = (i % 2) * QUAD, (i // 2) * QUAD
        t = fr_rgba.copy()
        t[iy:iy + (qy1 - qy0), ix:ix + (qx1 - qx0), :3] = res['atlas'][oy + qy0:oy + qy1, ox + qx0:ox + qx1]
        tiles.append(on_gray(np.clip(t, 0, 1)))       # 外形の外（体が無い所）は灰色で見せる
    grid = np.concatenate([np.concatenate(tiles[:2], 1), np.concatenate(tiles[2:], 1)], 0)
    img = Image.fromarray((np.clip(grid, 0, 1) * 255).astype(np.uint8))
    img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
    for i, name in enumerate(EXPRESSIONS):
        label(img, ((i % 2) * (w // 2) + 6, (i // 2) * (h // 2) + 6), name)
    img.save(path)


# ---------------------------------------------------------------- 本体

def field_to_json(f: Field, key: str, unit: str) -> dict:
    return {'npz': 'face_fields.npz', 'keys': [f'{key}_dx', f'{key}_dy'], 'x0': f.x0, 'y0': f.y0,
            'step': f.step, 'shape': list(f.dx.shape), 'unit': unit, **f.stats()}


def save_alignment(fa: FrontAlign, fa_info: dict, ea: ExprAlign, ea_info: list[dict]) -> None:
    arrays = {'front_dx': fa.field.dx, 'front_dy': fa.field.dy, 'expr_dx': ea.field.dx, 'expr_dy': ea.field.dy}
    for i in range(1, 4):
        arrays[f'extra{i}_dx'], arrays[f'extra{i}_dy'] = ea.extra[i].dx, ea.extra[i].dy
    np.savez_compressed(os.path.join(WORK, 'face_fields.npz'), **{k: v.astype(np.float32) for k, v in arrays.items()})
    align = {
        'note': '相似変換 dst = scale * R(angle) * src + (tx, ty)。matrix は [[a, -b, tx], [b, a, ty]] で '
                'dst = matrix @ [x, y, 1]。座標は画像の左上の角を 0 とする連続座標（画素 i は [i, i+1)、'
                'calib.json と同じ）。field は相似変換の後に残る、描き直しによる数 px のなめらかなずれ：'
                '正面の画素 p の中身は顔の絵の T⁻¹(p + field_front(p)) にあり、顔の絵の点 X の中身は表情 i の絵の '
                'T_i(X + field_expr(X)) にある（face_fields.npz、格子点 (x0 + step*(i+0.5), y0 + step*(j+0.5))）。'
                'residuals は目印ごとの残りのずれ（dst の画素）。',
        'face_to_front': {'src': FACE_FILE, 'dst': FRONT_FILE, **fa.t.to_json(),
                          'front_to_face': fa.t.inverse().to_json(),
                          'ncc': round(fa_info['ncc'], 5), 'coarse_ncc': round(fa_info['coarse_ncc'], 5),
                          'field_front': field_to_json(fa.field, 'front', 'front px'),
                          'residuals_similarity_only_front_px': fa_info['residuals_similarity_only'],
                          'residuals_with_field_front_px': fa_info['residuals_with_field']},
        'expressions': [{'name': e['name'], 'src': FACE_FILE, 'dst': EXPR_FILE,
                         'quadrant_image_px': e['quadrant_image_px'], **ea.t[i].to_json(),
                         'ncc_hair_goggles_outline': round(e['ncc'], 5),
                         'field_extra': (field_to_json(ea.extra[i], f'extra{i}', 'face px')
                                         if ea.extra[i] is not None else None),
                         'residuals_similarity_only_expr_px': e['residuals_similarity_only'],
                         'residuals_with_field_expr_px': e['residuals_with_field']}
                        for i, e in enumerate(ea_info)],
        'field_expr': {**field_to_json(ea.field, 'expr', 'face px'),
                       'note': '「通常」の頭と顔の絵の間で求め、4 表情に共通で使う。表情 i（1〜3）はさらに '
                               'expressions[i].field_extra（同じ絵の中の通常の頭とのずれ）を先に足す：'
                               'Y = X + extra_i(X)、表情の絵の点 = T_i(Y + field_expr(Y))'},
    }
    with open(os.path.join(WORK, 'face_align.json'), 'w') as fp:
        json.dump(align, fp, ensure_ascii=False, indent=2)


def load_alignment() -> tuple[FrontAlign, ExprAlign]:
    with open(os.path.join(WORK, 'face_align.json')) as fp:
        d = json.load(fp)
    z = np.load(os.path.join(WORK, 'face_fields.npz'))
    ff, fe = d['face_to_front']['field_front'], d['field_expr']
    fa = FrontAlign(Similarity.from_json(d['face_to_front']),
                    Field(ff['x0'], ff['y0'], ff['step'], z['front_dx'], z['front_dy']))
    extra = [None] + [Field(fe['x0'], fe['y0'], fe['step'], z[f'extra{i}_dx'], z[f'extra{i}_dy'])
                      for i in range(1, 4)]
    ea = ExprAlign([Similarity.from_json(e) for e in d['expressions']],
                   Field(fe['x0'], fe['y0'], fe['step'], z['expr_dx'], z['expr_dy']), extra)
    return fa, ea


def write_atlas_meta(res: dict) -> None:
    lay = res['layout']
    k = lay['k']
    wx0, wy0, wx1, wy1 = lay['window_front']
    qx0, qy0, qx1, qy1 = lay['window_atlas']
    uv_u = {'a': k / ATLAS, 'b': (qx0 - wx0 * k) / ATLAS}
    uv_v = {'a': -k / ATLAS, 'b': 1.0 - (qy0 - wy0 * k) / ATLAS}
    meta = {
        'note': '顔の材質（名前に face を含める）の UV。顔の窓（正面の絵の画素）を区画 0（通常）へ倍率 K で'
                '写す。表情の領域（眉・目・口のまわり）の外は 4 区画で画素まで同じ。区画 0 の全体に、正面の絵の'
                '対応する範囲（quadrant0_front_px）の中身が入っている：窓の内側は高解像度の顔の絵（色は全身の絵に'
                '合わせた）、窓の縁の近く（内側 2〜26px で移り変わる）と窓の外は全身の正面の絵そのもの。だから窓の縁で'
                '体のテクスチャ（全身の正面の絵）と継ぎ目が出ず、窓から少しはみ出した頂点も正しい色を拾う。'
                '顔の材質は少なくとも expression_zone_front_px を覆うこと（そうでないと眉などの一部が表情で変わらない）。'
                'おすすめ：頭の頂点のうち、正面へ投影して window_front_px に入り、法線が前（-Y）を向く所。',
        'atlas_file': 'face_atlas.png',
        'atlas_size': [ATLAS, ATLAS],
        'pixel_convention': 'continuous pixel coords, origin = top-left corner of the image, x right, y down; '
                            'pixel i covers [i, i+1) (same as calib.json)',
        'expressions': EXPRESSIONS,
        'quadrants_atlas_px': {n: [(i % 2) * QUAD, (i // 2) * QUAD, (i % 2 + 1) * QUAD, (i // 2 + 1) * QUAD]
                               for i, n in enumerate(EXPRESSIONS)},
        'godot_uv1_offset': 'expression i -> ((i % 2) * 0.5, floor(i / 2) * 0.5, 0); '
                            'order [normal, smile, surprise, pain] = [top-left, top-right, bottom-left, bottom-right]',
        'window_front_px': [wx0, wy0, wx1, wy1],
        'window_atlas_px': [qx0, qy0, qx1, qy1],
        'atlas_px_per_front_px': k,
        'quadrant0_front_px': [round(v, 4) for v in res['coverage_front']],
        'formula': {
            'front_px_to_atlas_px': 'ax = QX0 + (fx - WX0) * K ; ay = QY0 + (fy - WY0) * K '
                                    '(WX0, WY0 = window_front_px[0:2], QX0, QY0 = window_atlas_px[0:2], '
                                    'K = atlas_px_per_front_px)',
            'atlas_px_to_blender_uv': 'u = ax / 2048 ; v = 1 - ay / 2048 (quadrant 0 = u in [0, 0.5], v in [0.5, 1])',
            'world_to_front_px': 'fx = u0 + ppm * x ; fy = v0 - ppm * z (calib.json views.front: image_right = +X)',
            'front_px_to_blender_uv_linear': 'u = u.a * fx + u.b ; v = v.a * fy + v.b (see blender_uv_linear)',
            'world_to_blender_uv_linear': 'u = u.a_x * x + u.b ; v = v.a_z * z + v.b '
                                          '(see world_to_blender_uv_at_build; x, z = Blender world coords in m)',
            'godot_note': 'glTF/Godot UV = (u, 1 - v) of the Blender UV; the exporter flips it automatically',
        },
        'blender_uv_linear': {'u': uv_u, 'v': uv_v},
        'expression_zone_atlas_px': res['zone_atlas'],
        'expression_zone_front_px': [round(v, 2) for v in res['zone_front']],
        'checks': {
            'zone_min_distance_to_window_border_atlas_px': round(res['border_gap'], 2),
            'changed_pixels_min_distance_to_window_border_atlas_px': round(res['changed_gap'], 2),
            'max_diff_between_quadrants_on_window_border_8bit': res['border_diff'],
            'max_diff_between_quadrants_outside_zone_8bit': res['outside_diff'],
            'mean_abs_diff_atlas_vs_front_on_window_border_8bit': round(res['seam_front'], 3),
            'mean_abs_diff_face_vs_front_inside_window_8bit': {'before_color_match': round(res['inner_err_raw'], 3),
                                                                'after_color_match': round(res['inner_err'], 3)},
            'fraction_of_window_taken_from_front_because_face_art_differs': res['differ_fraction_in_window'],
            'mean_abs_diff_expr_vs_base_in_feather_band_8bit': dict(zip(EXPRESSIONS[1:], res['feather_err'])),
            'background_pixels_filled_with_nearest_colour_per_quadrant': res['n_transparent'],
        },
        'color_match_to_front': {'gain': res['gain'].round(4).tolist(), 'offset': res['offset'].round(4).tolist(),
                                 'note': 'atlas = gain * rgb + offset（sRGB 0〜1、顔の絵を全身の正面の絵の色へ）'},
        'expression_processing': {'sharpen_amount': round(res['sharpen'], 4),
                                  'color_match_to_base': dict(zip(EXPRESSIONS[1:], res['expr_color']))},
        'sources': {'face': FACE_FILE, 'expressions': EXPR_FILE, 'front': FRONT_FILE,
                    'alignment': 'face_align.json'},
    }
    calib_path = os.path.join(WORK, 'calib.json')
    if os.path.exists(calib_path):
        with open(calib_path) as fp:
            cv = json.load(fp)['views']['front']
        ppm, u0, v0 = cv['pixels_per_meter'], cv['u0'], cv['v0']
        meta['world_to_blender_uv_at_build'] = {
            'note': 'calib.json（作った時点）から出した値。calib.json が変わったら world_to_face_uv() で計算し直す',
            'calib_front': {'u0': u0, 'v0': v0, 'pixels_per_meter': ppm},
            'u': {'a_x': uv_u['a'] * ppm, 'b': uv_u['a'] * u0 + uv_u['b']},
            'v': {'a_z': -uv_v['a'] * ppm, 'b': uv_v['a'] * v0 + uv_v['b']},
            'window_world_x': [(wx0 - u0) / ppm, (wx1 - u0) / ppm],
            'window_world_z': [(v0 - wy1) / ppm, (v0 - wy0) / ppm],
        }
    with open(os.path.join(WORK, 'face_atlas.json'), 'w') as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)


def main() -> None:
    t_start = time.time()
    extract_sources()
    os.makedirs(WORK, exist_ok=True)
    front = load_rgba(FRONT_FILE)
    face = load_rgba(FACE_FILE)
    expr = load_rgba(EXPR_FILE)

    if '--reuse' in sys.argv and os.path.exists(os.path.join(WORK, 'face_fields.npz')):
        print('1-2. 照合は使い回す')
        fa, ea = load_alignment()
    else:
        print('1. 顔の絵 → 全身の正面の絵')
        fa, fa_info = align_face_to_front(front, face)
        print('2. 4 表情の頭 → 顔の絵')
        ea, ea_info = align_expressions_to_face(expr, face)
        save_alignment(fa, fa_info, ea, ea_info)

    print('3. 表情アトラス')
    res = build_atlas(front, face, expr, fa, ea)
    save_rgb(os.path.join(WORK, 'face_atlas.png'), res['atlas'])
    write_atlas_meta(res)

    print('4. 確認画像')
    lay = res['layout']
    write_align_check(front, face, fa, lay, os.path.join(WORK, 'face_align_check.png'))
    write_expr_check(face, expr, ea, os.path.join(WORK, 'face_expr_align_check.png'))
    write_atlas_check(res, os.path.join(WORK, 'face_atlas_check.png'))
    write_seam_check(front, res, os.path.join(WORK, 'face_atlas_seam_check.png'))
    print(f'  窓（正面の絵）{lay["window_front"]} → 区画 0 {lay["window_atlas"]}、倍率 {lay["k"]}')
    print(f'  表情の領域と窓の縁の間 {res["border_gap"]:.1f}px、縁での区画の差 {res["border_diff"]}、'
          f'縁での全身の絵との差 {res["seam_front"]:.2f}、窓の内側の顔の絵と全身の絵の差 '
          f'{res["inner_err_raw"]:.2f} → {res["inner_err"]:.2f}（8bit）、'
          f'差し替えの境目の色の差 {res["feather_err"]}、全身の絵を使った割合 {res["differ_fraction_in_window"]}')
    print(f'完了（{time.time() - t_start:.0f} 秒）')


if __name__ == '__main__':
    main()
