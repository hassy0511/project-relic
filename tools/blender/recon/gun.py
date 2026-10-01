"""スパーク（ハルの銃）を、画家の 2 枚の絵（真横・斜め 45 度）から起こす（再構築する）。

  .venv-blender/bin/python tools/blender/recon/gun.py

できるもの（build/recon/ の下）
  spark_gun.glb           銃のメッシュ（テクスチャ入り、発光する琥珀の窓、銃口の目印 'muzzle'）
  gun_check_side.png      左から「元の絵」「Cycles の画像（同じ真横の正投影）」「外形の差」
  gun_check_45.png        同じく斜めの絵と、絵に合わせたカメラの画像
  gun/                    途中の画像（部品の分け方、テクスチャ）と gun_report.json

■ やり方
1. 部品に分ける：真横の絵の外形の中を、部品ごとに置いた目印の線から「溝」（部品の境目に描かれた暗い細線）
   を壁にして広げる（分水嶺）。溝は黒トップハット（細い暗い線だけを拾う）で求める。
   溝のない所だけ FORCE で手直しし、最後に多数決で境目のぎざぎざをならす。
2. 部品ごとに外形を多角形にし、部品の厚み（全幅）で左右へ押し出す。縁は面取りする。
   面取りの幅は、絵に描かれた面取りの帯（明るい帯）に合わせて、辺の向き（上・下・前・後ろ）ごとに決める。
   隣の部品より細い部品は、隣の中へ少し食い込ませて隙間をなくす（食い込んだ辺は面取りしない）。
   同じ幅の部品どうしの境目は細い V 字の溝、細い隣との段差の面取りは段差の高さまで。
   細い所・尖った所で面取りの内側の縁が交差したら、その近くの辺だけ面取りを細める。
   厚み（全幅）は絵に数値がないので、指示の「遊底 約 4cm、握りは少し細い」と斜めの絵の見え方で決めた
   （PARTS の表）。
3. 窓（琥珀）はくぼみ、銃口は八角の筒と穴を別に作る。
4. 色：真横の絵をそのまま下地の色（テクスチャ）にして、左右の平らな面と面取りへ真横から投影する
   （反対側は同じ UV なので鏡写しになる）。上下・前後の面は、その辺から少し内側（面取りの帯の先）の色。
   琥珀の窓だけを切り出した発光のテクスチャを別に持つ（材質の Emission）。
5. 確認：真横は正投影、斜めは絵に合わせたカメラ（外形の一致が最大になるよう合わせる）で Cycles で描き、
   元の絵と並べる。

■ 座標（GLB の中、Blender の座標で）
  原点 = 握りの中心（拳で握る位置）。銃身は +X（銃口が +X）、上が +Z、握りは -Z 側。長さ約 30cm。
  真横の絵は -Y 側から見た面（銃の右側）。+Y 側は鏡写し。
  空の目印 'muzzle' を銃口の先（穴の中心）に置く（銃の子）。
  glTF（Godot）では +X が銃口、+Y が上になる（Blender の -Y は glTF の +Z）。
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy import optimize  # noqa: E402
from skimage import color, filters, measure, morphology, segmentation  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
RECON = os.path.join(REPO, 'build', 'recon')
SRC = os.path.join(RECON, 'src')
WORK = os.path.join(RECON, 'gun')
OUT_GLB = os.path.join(RECON, 'spark_gun.glb')
ART_BRANCH = 'origin/art/w1-haru3d'
ART_DIR = 'art/concepts/W1_haru_3d'
SIDE = 'spark_gun_side.png'
Q45 = 'spark_gun_3d.png'
IMG = 2048                # 絵の大きさ（正方形）

GUN_LENGTH = 0.30         # 全長（m）。spec_haru_3d.md の「約 30cm」
FIST_DROP = 0.040         # 握りの上端から拳の中心までの高さ（m）
SIMPLIFY_PX = 2.5         # 外形の多角形の許容誤差（画素）
CHAMFER_SLOPE = 0.7       # 面取りの深さ ÷ 面取りの幅（1 で 45 度）
GROOVE_PX = 5             # 同じ幅の部品どうしの溝の幅（画素）
WINDOW_DEPTH = 0.0025     # 窓のくぼみの深さ（m）
WINDOW_BEZEL_PX = 22      # 窓の枠（くぼみの口）の幅（画素）
BORE_WIDTH = 0.036        # 銃口の八角の筒の全幅（m）
BORE_RADIUS = 0.0110      # 銃口の穴の半径（m）
EMISSION_STRENGTH = 1.0   # 琥珀の窓の発光の強さ
DARK_SWATCH = (16, 48)    # テクスチャの左上の暗い色見本（銃口の穴の中）の範囲（画素）


# ---------------------------------------------------------------- 部品の表

@dataclass
class Part:
    """真横の絵の中の部品 1 つ。marks は目印の線（絵の画素座標）、width は全幅（m）、
    chamfer は面取りの幅（画素）を辺の向きごとに (上, 下, 前=銃口側, 後ろ) で。
    step_chamfer は、細い隣との段差の辺だけ面取りの幅を変えるとき {隣の名前: 画素}"""
    name: str
    marks: list[list[tuple[int, int]]]
    width: float
    chamfer: tuple[float, float, float, float]
    step_chamfer: dict[str, float] | None = None


PARTS = [
    # 上の遊底（前半）。上の縁に大きい面取り（絵の明るい帯が約 85 画素）
    Part('slide', [[(1000, 650), (1600, 650)]], 0.040, (80, 12, 12, 12)),
    # 銃口の塊。遊底より一回り大きい八角
    Part('muzzle', [[(1760, 560), (1760, 880)]], 0.046, (55, 30, 40, 12)),
    # 窓のある後ろの箱
    Part('receiver', [[(560, 560), (800, 560), (800, 700), (620, 830), (420, 800), (560, 560)]],
         0.044, (60, 20, 32, 25)),
    # 後ろの上の板（照門）
    Part('top_plate', [[(420, 468), (760, 472)]], 0.029, (18, 10, 42, 14)),
    # 後端の上の塊
    Part('rear_cap', [[(270, 560), (360, 560)]], 0.038, (48, 14, 14, 24), {'top_plate': 10}),
    # 後端の白磁の塊
    Part('ivory', [[(250, 690), (300, 690)]], 0.040, (12, 12, 12, 16)),
    # 下の枠：後ろ（白磁の下の塊と窓の箱の下の帯）・引き金の上・レールの下。一続きの 1 部品
    Part('frame', [[(180, 800), (260, 800)], [(300, 835), (560, 860)], [(700, 905), (980, 905)],
                   [(1100, 955), (1750, 955)]], 0.038, (14, 24, 20, 26)),
    # 真鍮のレール（少し張り出す）
    Part('rail', [[(1150, 855), (1650, 855)]], 0.042, (8, 8, 8, 8)),
    # 用心金（引き金の囲い）
    Part('guard', [[(590, 960), (590, 1150), (800, 1200), (1050, 1150), (1050, 980)]], 0.017, (20, 22, 22, 22)),
    # 引き金
    Part('trigger', [[(760, 960), (790, 1060)]], 0.009, (6, 6, 6, 6)),
    # 握り。後ろ・下・前に大きい面取り
    Part('grip', [[(450, 960), (350, 1100), (300, 1450)]], 0.035, (20, 72, 58, 78)),
    # 銃口の先の八角の筒（形は別に作る。ここでは領域だけ）
    Part('bore', [[(1888, 650), (1888, 760)]], BORE_WIDTH, (8, 8, 8, 8)),
]
PART_INDEX = {p.name: i + 1 for i, p in enumerate(PARTS)}   # ラベルの番号（0 は背景）

# 溝で分けられない所の手直し：(元の部品, 新しい部品, 多角形)。多角形の中で元の部品だった画素を新しい部品へ。
# 用心金の後ろの上の塊（引き金の穴の上の角）は、絵では枠と同じ太さでつながっているので枠にする
FORCE = [
    ('guard', 'frame', [(500, 800), (760, 800), (760, 930), (500, 930)]),
    # 握りの前上の角（斜めの面取り）と用心金の間の枠の細いくさびは、握りの面取りの続きとして握りへ
    ('frame', 'grip', [(536, 913), (584, 913), (584, 975), (536, 975)]),
]


# ---------------------------------------------------------------- 絵の読み込み

def extract_sources() -> None:
    """元の絵を美術のブランチから取り出す（取り出し済みなら何もしない）"""
    os.makedirs(SRC, exist_ok=True)
    for name in (SIDE, Q45):
        path = os.path.join(SRC, name)
        if os.path.exists(path):
            continue
        data = subprocess.run(['git', '-C', REPO, 'show', f'{ART_BRANCH}:{ART_DIR}/{name}'],
                              check=True, capture_output=True).stdout
        with open(path, 'wb') as f:
            f.write(data)


def load_rgba(name: str) -> np.ndarray:
    return np.asarray(Image.open(os.path.join(SRC, name)).convert('RGBA'))


# ---------------------------------------------------------------- 1. 部品に分ける

def groove_map(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """部品の境目の溝（暗い細線）の強さ。黒トップハット＝閉じた画像との差で、細い暗い線だけが残る"""
    lum = color.rgb2gray(rgb)
    th = morphology.black_tophat(lum, morphology.disk(5))
    th[~mask] = 0
    return filters.gaussian(th, 1.0)


def segment(rgba: np.ndarray) -> np.ndarray:
    """真横の絵を部品のラベル（0 = 背景、PART_INDEX の番号）に分ける"""
    mask = rgba[..., 3] > 127
    elev = groove_map(rgba[..., :3], mask)
    img = Image.new('I', (IMG, IMG), 0)
    dr = ImageDraw.Draw(img)
    for p in PARTS:
        for line in p.marks:
            dr.line(line, fill=PART_INDEX[p.name], width=5)
    markers = np.asarray(img).astype(np.int32)
    markers[~mask] = 0
    lab = segmentation.watershed(elev, markers, mask=mask)
    # 溝のない所の手直し
    for src, dst, poly in FORCE:
        img = Image.new('L', (IMG, IMG), 0)
        ImageDraw.Draw(img).polygon(poly, fill=1)
        sel = (np.asarray(img) > 0) & (lab == PART_INDEX[src])
        lab[sel] = PART_INDEX[dst]
    # 境目のぎざぎざをならす（多数決）。外形の際で背景に負けた画素は元のまま
    smooth = filters.rank.majority(lab.astype(np.uint8), morphology.disk(9)).astype(np.int32)
    keep = mask & (smooth == 0)
    smooth[keep] = lab[keep]
    smooth[~mask] = 0
    # 各部品は目印の線に触れている塊だけ残し、はぐれた画素は近い部品へ
    for i in PART_INDEX.values():
        cc, n = ndi.label(smooth == i)
        if n > 1:
            good = np.unique(cc[(markers == i) & (cc > 0)])
            smooth[(cc > 0) & ~np.isin(cc, good)] = 0
    hole = mask & (smooth == 0)
    if hole.any():
        _, idx = ndi.distance_transform_edt(smooth == 0, return_indices=True)
        smooth[hole] = smooth[idx[0][hole], idx[1][hole]]
    return smooth


def save_segmentation(rgba: np.ndarray, lab: np.ndarray, path: str) -> None:
    rng = np.random.default_rng(3)
    pal = rng.integers(60, 255, (len(PARTS) + 1, 3))
    pal[0] = 0
    ov = (0.5 * rgba[..., :3] + 0.5 * pal[lab]).astype(np.uint8)
    ov[segmentation.find_boundaries(lab)] = (255, 0, 0)
    im = Image.fromarray(ov)
    dr = ImageDraw.Draw(im)
    for p in PARTS:
        ys, xs = np.nonzero(lab == PART_INDEX[p.name])
        if len(xs):
            dr.text((int(xs.mean()) - 20, int(ys.mean())), p.name, fill=(255, 255, 255))
    im.crop((100, 400, 1950, 1650)).save(path)


def part_mask(lab: np.ndarray, part: Part) -> np.ndarray:
    """部品の領域。隣より細い部品は隣の中へ 6 画素、同じ幅の隣へは 2 画素食い込ませる（隙間を作らない）。
    ただし外形の際（背景から 8 画素以内）には食い込ませない。太い隣はそこで面取りして低くなっているので、
    食い込んだ端が面取りから顔を出してしまう"""
    i = PART_INDEX[part.name]
    own = lab == i
    inner = ndi.distance_transform_edt(lab > 0) > 8
    wider = inner & np.isin(lab, [PART_INDEX[q.name] for q in PARTS if q.width > part.width + 1e-4])
    equal = np.isin(lab, [PART_INDEX[q.name] for q in PARTS if q is not part and abs(q.width - part.width) <= 1e-4])
    grow = (ndi.binary_dilation(own, morphology.disk(6)) & wider) | (ndi.binary_dilation(own, morphology.disk(2)) & equal)
    return own | grow


# ---------------------------------------------------------------- 画素と世界の座標

@dataclass
class Frame:
    """絵の画素（連続座標。画素 i の中心が i + 0.5）と銃の座標（m）の対応"""
    ox: float      # 原点（拳の中心）の画素 x
    oy: float      # 原点の画素 y
    s: float       # 1 画素あたりの m

    def to_world(self, px: np.ndarray) -> np.ndarray:
        """(N,2) の画素 (x, y) → (N,2) の (X, Z)"""
        px = np.asarray(px, np.float64)
        return np.stack([(px[:, 0] - self.ox) * self.s, (self.oy - px[:, 1]) * self.s], 1)

    def to_px(self, xz: np.ndarray) -> np.ndarray:
        xz = np.asarray(xz, np.float64)
        return np.stack([xz[:, 0] / self.s + self.ox, self.oy - xz[:, 1] / self.s], 1)

    def uv(self, xz: np.ndarray) -> np.ndarray:
        """銃の (X, Z) → 真横の絵の UV（Blender の UV は下が 0）"""
        p = self.to_px(xz)
        return np.stack([p[:, 0] / IMG, 1.0 - p[:, 1] / IMG], 1)


def make_frame(rgba: np.ndarray, lab: np.ndarray) -> tuple[Frame, dict]:
    mask = rgba[..., 3] > 127
    xs = np.nonzero(mask.any(0))[0]
    s = GUN_LENGTH / (xs.max() - xs.min() + 1)
    grip = lab == PART_INDEX['grip']
    rows = np.nonzero(grip.any(1))[0]
    y_top = rows.min()
    row = int(round(y_top + FIST_DROP / s))
    cols = np.nonzero(grip[row])[0]
    ox, oy = (cols.min() + cols.max() + 1) / 2, row + 0.5
    # 握りの傾き（真下からの角度。下へ行くほど後ろ＝-X へ傾くと正）
    ys, xs2 = np.nonzero(grip)
    sel = ys > y_top + 40
    a, _ = np.polyfit(ys[sel], xs2[sel], 1)
    slant = math.degrees(math.atan(-a))
    info = {'px_per_m': 1 / s, 'm_per_px': s, 'origin_px': [ox, oy], 'grip_top_px': int(y_top),
            'grip_slant_deg': round(slant, 1), 'art_x_range_px': [int(xs.min()), int(xs.max())]}
    return Frame(ox, oy, s), info


# ---------------------------------------------------------------- 2. 外形の多角形と面取り

def trace(mask: np.ndarray, frame: Frame) -> list[np.ndarray]:
    """領域の外形 → 多角形（銃の (X, Z)）。外周は反時計回り、穴は時計回り。最初が外周"""
    soft = filters.gaussian(np.pad(mask.astype(np.float64), 2), 1.0)
    rings = []
    for c in measure.find_contours(soft, 0.5):
        c = measure.approximate_polygon(c, SIMPLIFY_PX)
        if len(c) < 4:
            continue
        px = np.stack([c[:, 1] - 2 + 0.5, c[:, 0] - 2 + 0.5], 1)[:-1]   # 閉じた点の重複を除く
        xz = frame.to_world(px)
        area = signed_area(xz)
        if abs(area) < (20 * frame.s) ** 2:
            continue
        rings.append(xz)
    rings.sort(key=lambda r: -abs(signed_area(r)))
    out = []
    for k, r in enumerate(rings):
        want_ccw = k == 0
        if (signed_area(r) > 0) != want_ccw:
            r = r[::-1].copy()
        out.append(r)
    return out


def signed_area(p: np.ndarray) -> float:
    x, z = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(z, -1) - np.roll(x, -1) * z))


def edge_frames(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """各辺 i（p[i] → p[i+1]）の向き t と外向きの法線 n（反時計回りの外周なら外、時計回りの穴なら穴の中）"""
    d = np.roll(p, -1, 0) - p
    t = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    return t, n


def classify_edges(ring: np.ndarray, part: Part, lab: np.ndarray, frame: Frame) -> list[int]:
    """各辺の外側に何があるか：0 = 背景、それ以外は隣の部品の番号（辺の上の 3 点 × 2 距離の多数決）"""
    _, n = edge_frames(ring)
    nxt = np.roll(ring, -1, 0)
    out = []
    for i in range(len(ring)):
        votes = []
        for f in (0.25, 0.5, 0.75):
            q = ring[i] * (1 - f) + nxt[i] * f
            for dpx in (3.0, 5.0):
                px = frame.to_px((q + n[i] * dpx * frame.s)[None])[0]
                x, y = int(px[0]), int(px[1])
                votes.append(int(lab[y, x]) if 0 <= x < IMG and 0 <= y < IMG else 0)
        vals, cnt = np.unique(votes, return_counts=True)
        out.append(int(vals[np.argmax(cnt)]))
    return out


def edge_chamfer(ring: np.ndarray, part: Part, neighbours: list[int], frame: Frame,
                 mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """各辺の面取りの幅（m）と深さの上限（m）。
    外形や自分より細い隣に面する辺は向きで決め、同じ幅の隣は溝、太い隣の中へ入る辺は 0。
    細い隣との段差の辺は、面取りの深さを段差の高さまでにする（深く削ると隣の部品の端が面取りから顔を出す）"""
    _, n = edge_frames(ring)
    up, down, front, back = part.chamfer
    c = np.zeros(len(ring))
    kcap = np.full(len(ring), 0.45 * part.width / 2)
    # 向きは、辺の前後 25 画素の弧でならした法線で決める（短いぎざぎざの辺で面取りの幅が暴れないように）
    seg = np.linalg.norm(np.roll(ring, -1, 0) - ring, axis=1)
    mid_arc = np.cumsum(seg) - seg / 2
    total = seg.sum()
    n_smooth = np.zeros_like(n)
    for i in range(len(ring)):
        d = np.abs(mid_arc - mid_arc[i])
        d = np.minimum(d, total - d)
        w = seg * (d <= 25 * frame.s + seg / 2)
        v = (n * w[:, None]).sum(0)
        n_smooth[i] = v / max(np.linalg.norm(v), 1e-12)
    widths = {PART_INDEX[q.name]: q.width for q in PARTS}
    for i, nb in enumerate(neighbours):
        if nb == PART_INDEX[part.name]:
            nb = 0
        if nb and widths[nb] > part.width + 1e-4:
            c[i] = 0.0
        elif nb and abs(widths[nb] - part.width) <= 1e-4:
            c[i] = GROOVE_PX
        else:
            nx, nz = n_smooth[i]
            c[i] = (up * max(nz, 0) ** 2 + down * max(-nz, 0) ** 2
                    + front * max(nx, 0) ** 2 + back * max(-nx, 0) ** 2)
            if nb:
                kcap[i] = min(kcap[i], (part.width - widths[nb]) / 2 - 0.0002)
                name = PARTS[nb - 1].name
                if part.step_chamfer and name in part.step_chamfer:
                    c[i] = part.step_chamfer[name]
    if mask is not None:
        # 部品の厚み（辺から内側へ、部品の外へ出るまでの長さ）の 45% までに抑える。細い所で面取りが向こう側へ抜けない
        nxt = np.roll(ring, -1, 0)
        for i in range(len(ring)):
            if c[i] <= 0:
                continue
            mid = frame.to_px(((ring[i] + nxt[i]) / 2)[None])[0]
            d = np.array([-n[i][0], n[i][1]])          # 内向き（画素の座標。y は下向き）
            length = 0.0
            for t in np.arange(2.0, 3.0 * c[i] + 4.0, 1.0):
                x, y = (mid + d * t).astype(int)
                if not (0 <= x < IMG and 0 <= y < IMG and mask[y, x]):
                    break
                length = t
            c[i] = min(c[i], 0.45 * length)
    return c * frame.s, kcap


class Collapse(Exception):
    pass


def inset_ring(p: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """多角形の各辺を内側へ c[i] だけずらした多角形（面取りの内側の縁）。
    辺が縮んで裏返ったら、その辺を消して両隣の線の交点へまとめる（簡単な straight skeleton）。
    返り値：内側の点 (M,2) と、外側の各点 i が対応する内側の点の番号 (N,)"""
    n_pts = len(p)
    t, n = edge_frames(p)
    nin = -n
    active = list(range(n_pts))

    def meet(a: int, b: int) -> np.ndarray:
        # 2 本のずらした線の交点。ほぼ平行で交点が遠くへ飛ぶときは、端の中点を平均の向きへずらす
        ref = 0.5 * (p[(a + 1) % n_pts] + p[b])
        fallback = ref + 0.5 * (nin[a] * c[a] + nin[b] * c[b])
        A = np.array([nin[a], nin[b]])
        rhs = np.array([c[a] + p[a] @ nin[a], c[b] + p[b] @ nin[b]])
        det = np.linalg.det(A)
        if abs(det) < 0.05:
            return fallback
        x = np.linalg.solve(A, rhs)
        if np.linalg.norm(x - ref) > 3.0 * max(c[a], c[b]) + 1e-6:
            return fallback
        return x

    while True:
        m = len(active)
        if m < 3:
            raise Collapse('面取りで潰れた')
        q = np.array([meet(active[j - 1], active[j]) for j in range(m)])
        # 裏返った（向きが逆になった）内側の辺のうち、いちばんひどいものを消す
        worst, wj = -1e-9, -1
        for j in range(m):
            d = float((q[(j + 1) % m] - q[j]) @ t[active[j]])
            if d < worst:
                worst, wj = d, j
        if wj < 0:
            break
        active.pop(wj)
    # 外側の点 i → 辺 i 以降で最初に残っている辺の始点
    pos = {e: j for j, e in enumerate(active)}
    idx = np.zeros(n_pts, np.int64)
    for i in range(n_pts):
        k = i
        while k % n_pts not in pos:
            k += 1
        idx[i] = pos[k % n_pts]
    return q, idx


def segments_cross(a, b, c, d) -> bool:
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 * o2 < 0) and (o3 * o4 < 0)


def first_crossing(q: np.ndarray) -> tuple[int, int] | None:
    """自己交差している 2 本の辺 (i, j) を 1 組返す（なければ None）"""
    m = len(q)
    for i in range(m):
        for j in range(i + 2, m):
            if i == 0 and j == m - 1:
                continue
            if segments_cross(q[i], q[(i + 1) % m], q[j], q[(j + 1) % m]):
                return i, j
    return None


def ring_is_simple(q: np.ndarray) -> bool:
    return first_crossing(q) is None


def point_in_ring(pt: np.ndarray, ring: np.ndarray) -> bool:
    x, z = pt
    inside = False
    for i in range(len(ring)):
        x1, z1 = ring[i]
        x2, z2 = ring[(i + 1) % len(ring)]
        if (z1 > z) != (z2 > z):
            xi = x1 + (z - z1) * (x2 - x1) / (z2 - z1)
            if xi > x:
                inside = not inside
    return inside


def dist_to_ring(pt: np.ndarray, ring: np.ndarray) -> float:
    a, b = ring, np.roll(ring, -1, 0)
    ab = b - a
    tt = np.clip(np.sum((pt - a) * ab, 1) / np.maximum(np.sum(ab * ab, 1), 1e-18), 0, 1)
    return float(np.min(np.linalg.norm(a + ab * tt[:, None] - pt, axis=1)))


def safe_inset(ring: np.ndarray, c: np.ndarray, outer: bool, name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """inset_ring を、内側の多角形が自己交差しなくなるまで面取りを細めながら試す。
    まず交差している所の近くの辺だけを細め、だめなら部品全体を細める"""
    cc = c.copy()
    n = len(ring)
    for _ in range(40):
        try:
            q, idx = inset_ring(ring, cc)
        except Collapse:
            break
        if (signed_area(q) > 0) != outer:
            break
        cross = first_crossing(q)
        if cross is None:
            # 面取りの内側の縁が、元の辺より外へ出ていないか（出ていると面取りの面が裏返る）
            _, nn = edge_frames(ring)
            bad = [e for e in range(n) for v in (q[idx[e]], q[idx[(e + 1) % n]])
                   if float((v - ring[e]) @ -nn[e]) < -1e-7]
            if bad:
                for e in set(bad):
                    for k in (e - 1, e, e + 1):
                        cc[k % n] *= 0.8
                continue
            if outer and not all(point_in_ring(v, ring) or dist_to_ring(v, ring) < 1e-6 for v in q):
                break
            if np.any(cc < c - 1e-9):
                print(f'  {name}: 面取りを {int(np.sum(cc < c - 1e-9))} 辺で細めた', flush=True)
            return q, idx, cc
        # 交差する 2 本の内側の辺の間（短い方の弧）に対応する外側の辺を細める
        i, j = cross
        m = len(q)
        arc1 = set(range(i, j + 2))
        arc2 = set(k % m for k in range(j, i + m + 2))
        arc = arc1 if len(arc1) <= len(arc2) else arc2
        hit = [e for e in range(n) if idx[e] in arc or idx[(e + 1) % n] in arc]
        cc[hit] *= 0.8
    scale = 0.8
    for _ in range(10):
        try:
            q, idx = inset_ring(ring, c * scale)
            ok = len(q) >= 3 and ring_is_simple(q) and (signed_area(q) > 0) == outer
            if ok and outer:
                ok = all(point_in_ring(v, ring) or dist_to_ring(v, ring) < 1e-6 for v in q)
            if ok:
                print(f'  {name}: 面取りを {scale:.2f} 倍に細めた', flush=True)
                return q, idx, c * scale
        except Collapse:
            pass
        scale *= 0.8
    raise RuntimeError(f'{name}: 面取りが作れない')


# ---------------------------------------------------------------- メッシュを組む

class Builder:
    """面ごとに頂点と UV を持つ（面取りの角を立てるので頂点は共有しない）"""

    def __init__(self):
        self.verts: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []
        self.uvs: list[list[tuple[float, float]]] = []
        self.parts: list[str] = []

    def face(self, pts: list[np.ndarray], uvs: list[np.ndarray], part: str, want: np.ndarray | None = None) -> None:
        """want（外向きにしたい向き）が与えられたら、法線がそちらを向くように並びを直す"""
        pts = [np.asarray(v, np.float64) for v in pts]
        keep = [i for i in range(len(pts)) if np.linalg.norm(pts[i] - pts[i - 1]) > 1e-9]
        pts, uvs = [pts[i] for i in keep], [uvs[i] for i in keep]
        if len(pts) < 3:
            return
        nrm = np.zeros(3)
        for i in range(len(pts)):   # Newell の方法
            a, b = pts[i], pts[(i + 1) % len(pts)]
            nrm += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]),
                             (a[0] - b[0]) * (a[1] + b[1])])
        if np.linalg.norm(nrm) < 1e-10:
            return   # 面積のない面は作らない
        if want is not None and nrm @ want < 0:
            pts, uvs = pts[::-1], uvs[::-1]
        base = len(self.verts)
        self.verts.extend(tuple(v) for v in pts)
        self.faces.append(tuple(range(base, base + len(pts))))
        self.uvs.append([tuple(map(float, u)) for u in uvs])
        self.parts.append(part)

    def triangles(self) -> tuple[np.ndarray, np.ndarray]:
        tris = []
        for f in self.faces:
            for k in range(1, len(f) - 1):
                tris.append((f[0], f[k], f[k + 1]))
        return np.asarray(self.verts, np.float64), np.asarray(tris, np.int64)


def v3(xz: np.ndarray, y: float) -> np.ndarray:
    return np.array([xz[0], y, xz[1]])


def build_extrusion(b: Builder, part: Part, rings: list[np.ndarray], lab: np.ndarray, frame: Frame,
                    mask: np.ndarray, cap_holes: list[np.ndarray] | None = None) -> dict:
    """外形の多角形を全幅 part.width で押し出し、縁を面取りする。cap_holes は左右の平らな面に開ける穴（窓）"""
    import bpy  # noqa: F401  （mathutils は bpy と一緒に読み込む）
    from mathutils.geometry import tessellate_polygon
    half = part.width / 2
    kmax = 0.45 * half
    inner_rings, idx_maps, halfw, cham = [], [], [], []
    for k, ring in enumerate(rings):
        nb = classify_edges(ring, part, lab, frame)
        c, kcap = edge_chamfer(ring, part, nb, frame, mask)
        q, idx, c = safe_inset(ring, c, outer=(k == 0), name=part.name)
        # 面取りの深さ：辺ごとに幅 × 傾き（上限つき）。点ごとには両隣の辺（面取りのある辺）の平均で、
        # 段差の辺に接する点はその上限を超えない
        ke = np.minimum(np.minimum(CHAMFER_SLOPE * c, kmax), kcap)
        kv = np.zeros(len(ring))
        for i in range(len(ring)):
            vals = [ke[j] for j in (i - 1, i) if c[j] > 0]
            kv[i] = float(np.mean(vals)) if vals else 0.0
            kv[i] = min([kv[i]] + [kcap[j] for j in (i - 1, i)])
        inner_rings.append(q)
        idx_maps.append(idx)
        halfw.append(half - kv)
        cham.append(c)

    # 左右の平らな面（内側の多角形。穴があれば穴も）
    polys = [[(v[0], v[1], 0.0) for v in q] for q in inner_rings]
    for h in cap_holes or []:
        polys.append([(v[0], v[1], 0.0) for v in h])
    flat = np.concatenate([np.asarray(q) for q in inner_rings] + [np.asarray(h) for h in (cap_holes or [])])
    tris = tessellate_polygon(polys)
    for side in (-1.0, 1.0):
        want = np.array([0.0, side, 0.0])
        for tri in tris:
            pts = [v3(flat[i], side * half) for i in tri]
            b.face(pts, list(frame.uv(flat[list(tri)])), part.name, want)

    # 面取りと、上下・前後の面（壁）
    for ring, q, idx, hw, c in zip(rings, inner_rings, idx_maps, halfw, cham):
        _, n = edge_frames(ring)
        m = len(ring)
        for i in range(m):
            j = (i + 1) % m
            o0, o1 = ring[i], ring[j]
            q0, q1 = q[idx[i]], q[idx[j]]
            for side in (-1.0, 1.0):
                want = np.array([n[i][0], side, n[i][1]])
                if idx[i] == idx[j]:
                    pts2 = [o0, o1, q0]
                    ys = [hw[i], hw[j], half]
                else:
                    pts2 = [o0, o1, q1, q0]
                    ys = [hw[i], hw[j], half, half]
                pts = [v3(p, side * y) for p, y in zip(pts2, ys)]
                b.face(pts, list(frame.uv(np.asarray(pts2))), part.name, want)
            # 壁：色は辺から面取りの帯の少し先（内側）を取る
            delta = max(c[i] / frame.s + 16.0, 12.0) * frame.s
            s0, s1 = o0 - n[i] * delta, o1 - n[i] * delta
            want = np.array([n[i][0], 0.0, n[i][1]])
            pts = [v3(o0, -hw[i]), v3(o1, -hw[j]), v3(o1, hw[j]), v3(o0, hw[i])]
            b.face(pts, list(frame.uv(np.array([s0, s1, s1, s0]))), part.name, want)
    return {'rings': [len(r) for r in rings], 'inner': [len(q) for q in inner_rings]}


def chamfered_rect(x0: float, z0: float, x1: float, z1: float, cut: float) -> np.ndarray:
    """角を切った長方形（反時計回り、8 点）"""
    return np.array([(x0 + cut, z0), (x1 - cut, z0), (x1, z0 + cut), (x1, z1 - cut),
                     (x1 - cut, z1), (x0 + cut, z1), (x0, z1 - cut), (x0, z0 + cut)])


def window_rings(amber: np.ndarray, frame: Frame) -> tuple[np.ndarray, np.ndarray]:
    """琥珀の窓：くぼみの口（枠の外周）と底（琥珀の板）の 2 つの 8 角形（反時計回り）"""
    ys, xs = np.nonzero(amber)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    pane = frame.to_world(np.array([[x0, y1], [x1, y0]], np.float64))
    mb = WINDOW_BEZEL_PX
    bez = frame.to_world(np.array([[x0 - mb, y1 + mb], [x1 + mb, y0 - mb]], np.float64))
    s = frame.s
    return (chamfered_rect(bez[0, 0], bez[0, 1], bez[1, 0], bez[1, 1], 16 * s),
            chamfered_rect(pane[0, 0], pane[0, 1], pane[1, 0], pane[1, 1], 8 * s))


def build_window(b: Builder, part: Part, mouth: np.ndarray, pane: np.ndarray, frame: Frame) -> None:
    """窓のくぼみ：口から底へ斜めの壁、底は平ら（色はどちらも真横の絵をそのまま投影）"""
    half = part.width / 2
    floor = half - WINDOW_DEPTH
    for side in (-1.0, 1.0):
        for i in range(len(mouth)):
            j = (i + 1) % len(mouth)
            pts2 = [mouth[i], mouth[j], pane[j], pane[i]]
            ys = [half, half, floor, floor]
            # 口の辺の内向き（くぼみの中心へ）と、外（side）の間を向く
            mid = 0.5 * (mouth[i] + mouth[j]) - 0.5 * (pane[i] + pane[j])
            want = np.array([-mid[0], side * 2.0 * np.linalg.norm(mid), -mid[1]])
            pts = [v3(p, side * y) for p, y in zip(pts2, ys)]
            b.face(pts, list(frame.uv(np.asarray(pts2))), 'window', want)
        want = np.array([0.0, side, 0.0])
        pts = [v3(p, side * floor) for p in pane]
        b.face(pts, list(frame.uv(pane)), 'window', want)


def build_bore(b: Builder, lab: np.ndarray, frame: Frame) -> dict:
    """銃口の八角の筒と穴。真横の絵の 'bore' の領域から、高さと前端を取る"""
    ys, xs = np.nonzero(lab == PART_INDEX['bore'])
    x_front = xs.max() + 1.0
    # 筒の根元（銃口の塊の前面）は筒の領域の左端
    x_root = xs.min()
    y0, y1 = ys.min(), ys.max() + 1.0
    s = frame.s
    (xf, zc_top), = frame.to_world(np.array([[x_front, y0]]))
    (xr, zc_bot), = frame.to_world(np.array([[x_root, y1]]))
    zc = 0.5 * (zc_top + zc_bot)
    hb = 0.5 * (zc_top - zc_bot)            # 半分の高さ
    hw = BORE_WIDTH / 2                      # 半分の幅
    bevel = 0.0022                           # 前の縁の面取り
    x_back = xr - 0.004                      # 塊の中へ少し差し込む

    def octagon(a: float, h: float, angles: np.ndarray) -> np.ndarray:
        """(y, z) の八角形を、中心から angles の向きの線と交わる点で表す（穴の円と同じ向きの点にする）"""
        cc = 0.35 * min(a, h)
        corners = np.array([(-a + cc, -h), (a - cc, -h), (a, -h + cc), (a, h - cc),
                            (a - cc, h), (-a + cc, h), (-a, h - cc), (-a, -h + cc)])
        pts = []
        for th in angles:
            d = np.array([math.cos(th), math.sin(th)])
            best = None
            for i in range(8):
                p, q = corners[i], corners[(i + 1) % 8]
                e = q - p
                den = d[0] * e[1] - d[1] * e[0]
                if abs(den) < 1e-12:
                    continue
                t = (p[0] * e[1] - p[1] * e[0]) / den       # 中心からの距離
                u = (p[0] * d[1] - p[1] * d[0]) / den       # 辺の上の位置
                if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
                    best = t
            pts.append(d * best)
        return np.array(pts)

    # 向き：一様な 16 方向と、八角の角の向き（角を残すため）
    cc = 0.35 * min(hw, hb)
    corner_ang = [math.atan2(z, y) for y, z in [(-hw + cc, -hb), (hw - cc, -hb), (hw, -hb + cc), (hw, hb - cc),
                                                 (hw - cc, hb), (-hw + cc, hb), (-hw, hb - cc), (-hw, -hb + cc)]]
    ang = np.sort(np.mod(np.concatenate([np.linspace(0, 2 * math.pi, 16, endpoint=False), corner_ang]),
                         2 * math.pi))
    outer = octagon(hw, hb, ang)
    front = octagon(hw - bevel, hb - bevel, ang)
    hole = np.stack([BORE_RADIUS * np.cos(ang), BORE_RADIUS * np.sin(ang)], 1)
    depth = max(xf - xr - 0.0008, 0.002)

    # 色：外側は真横の絵の筒の中から（上下は少し内側）、前面は筒の中央、穴の中は暗い色見本
    def uv_side(x: float, z: float) -> np.ndarray:
        """筒の外側：銃口の塊の前寄りの面の色を、高さだけ合わせて使う"""
        zz = np.clip(z, zc - hb + 8 * s, zc + hb - 8 * s)
        return frame.uv(np.array([[xr - 40 * s, zz]]))[0]

    # 前面は銃口の塊の横の面の色（筒の横は絵では光が当たって明るく描かれているので使わない）
    uv_front = frame.uv(np.array([[xr - 60 * s, zc]]))[0]
    uv_dark = np.array([np.mean(DARK_SWATCH) / IMG, 1 - np.mean(DARK_SWATCH) / IMG])

    def P(x: float, yz: np.ndarray) -> np.ndarray:
        return np.array([x, yz[0], zc + yz[1]])

    m = len(outer)
    for i in range(m):
        j = (i + 1) % m
        mid = 0.5 * (outer[i] + outer[j])
        want = np.array([0.0, mid[0], mid[1]])
        # 側面（後ろ → 前の面取りの手前）
        pts = [P(x_back, outer[i]), P(x_back, outer[j]), P(xf - bevel, outer[j]), P(xf - bevel, outer[i])]
        b.face(pts, [uv_side(p[0], p[2]) for p in pts], 'bore', want)
        # 前の縁の面取り
        pts = [P(xf - bevel, outer[i]), P(xf - bevel, outer[j]), P(xf, front[j]), P(xf, front[i])]
        b.face(pts, [uv_side(p[0], p[2]) for p in pts], 'bore', want + np.array([1.0, 0, 0]))
        # 前面（八角から穴の縁まで）
        pts = [P(xf, front[i]), P(xf, front[j]), P(xf, hole[j]), P(xf, hole[i])]
        b.face(pts, [uv_front] * 4, 'bore', np.array([1.0, 0, 0]))
        # 穴の内側
        pts = [P(xf, hole[i]), P(xf, hole[j]), P(xf - depth, hole[j]), P(xf - depth, hole[i])]
        mh = 0.5 * (hole[i] + hole[j])
        b.face(pts, [uv_dark] * 4, 'bore_hole', np.array([0.0, -mh[0], -mh[1]]))
    # 穴の底と、筒の後ろのふた
    b.face([P(xf - depth, h) for h in hole], [uv_dark] * m, 'bore_hole', np.array([1.0, 0, 0]))
    b.face([P(x_back, o) for o in outer], [uv_front] * m, 'bore', np.array([-1.0, 0, 0]))
    return {'muzzle': [float(xf), 0.0, float(zc)], 'bore_half_height': float(hb), 'bore_protrusion_m': float(xf - xr)}


# ---------------------------------------------------------------- 4. テクスチャ

def amber_mask(rgba: np.ndarray) -> np.ndarray:
    """琥珀の窓の画素（橙で明るく鮮やか）。真鍮（暗い）と白磁（淡い）は入らない"""
    hsv = color.rgb2hsv(rgba[..., :3])
    m = ((hsv[..., 0] > 0.06) & (hsv[..., 0] < 0.15) & (hsv[..., 1] > 0.45) & (hsv[..., 2] > 0.80)
         & (rgba[..., 3] > 200))
    m = ndi.binary_opening(m, morphology.disk(2))
    cc, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(np.ones_like(cc), cc, range(1, n + 1))
        m = cc == 1 + int(np.argmax(sizes))
    return ndi.binary_fill_holes(m)


# 部品ごとの平らな色（W0 の基準色。体の部品 costume.py と同じ表）。書かない部品は絵の部品の中央値の色
FLAT_COLOURS = {
    'ivory': (243, 233, 210), 'rail': (169, 135, 73), 'bore': (60, 61, 58),
}


def make_textures(rgba: np.ndarray, amber: np.ndarray, lab: np.ndarray | None = None) -> tuple[str, str]:
    """下地の色：部品ごとに平らな 1 色（lab：部品のラベル。FLAT_COLOURS か、絵のその部品の色の中央値）。
    lab が無ければ前のやり方（真横の絵の色そのまま）。部品の外（透明な所）は一番近い部品の色。
    発光：琥珀の窓だけ（縁は 1 画素ぼかす）"""
    a = rgba[..., 3]
    opaque = a >= 0.95 * a.max()
    if lab is not None:
        flat = np.zeros(rgba.shape[:2] + (3,), np.uint8)
        has = lab > 0
        for part in PARTS:
            m = lab == PART_INDEX[part.name]
            if not m.any():
                continue
            col = FLAT_COLOURS.get(part.name)
            if col is None:
                col = np.median(rgba[..., :3][m & ~amber & opaque], 0) if (m & ~amber & opaque).any() else (68, 70, 65)
            flat[m] = np.asarray(col, np.uint8)
        _, idx = ndi.distance_transform_edt(~has, return_indices=True)
        albedo = flat[idx[0], idx[1]].copy()
        amb = np.median(rgba[..., :3][amber], 0) if amber.any() else (255, 188, 82)
        albedo[amber] = np.asarray(amb, np.uint8)
    else:
        _, idx = ndi.distance_transform_edt(~opaque, return_indices=True)
        albedo = rgba[..., :3][idx[0], idx[1]].copy()
    d0, d1 = DARK_SWATCH
    albedo[d0:d1, d0:d1] = (14, 14, 15)
    emit_w = filters.gaussian(amber.astype(np.float64), 1.0)[..., None]
    # 窓の底（くぼみの底）の縁まで確実に光らせるため、少し広げてから色を掛ける
    emit_w = np.maximum(emit_w, ndi.binary_dilation(amber, iterations=2)[..., None] * 0.9)
    emissive = (albedo.astype(np.float64) * emit_w).astype(np.uint8)
    # 窓の下地は暗くする（明るさは発光で出す。下地も明るいと光が足されて黄色く飛ぶ）
    albedo = (albedo.astype(np.float64) * (1.0 - 0.75 * emit_w)).astype(np.uint8)
    p_alb = os.path.join(WORK, 'spark_gun_albedo.png')
    p_emi = os.path.join(WORK, 'spark_gun_emissive.png')
    Image.fromarray(albedo).save(p_alb, optimize=True)
    Image.fromarray(emissive).save(p_emi, optimize=True)
    return p_alb, p_emi


# ---------------------------------------------------------------- Blender

def blender_object(b: Builder, p_alb: str, p_emi: str, muzzle: list[float]):
    import bpy
    from lib import common as C
    C.reset_scene()
    me = bpy.data.meshes.new('spark_gun')
    me.from_pydata(b.verts, [], b.faces)
    uvl = me.uv_layers.new(name='UVMap')
    flat_uv = [u for f in b.uvs for u in f]
    uvl.data.foreach_set('uv', np.asarray(flat_uv, np.float32).ravel())
    me.polygons.foreach_set('use_smooth', np.zeros(len(me.polygons), bool))
    me.validate()
    me.update()
    obj = bpy.data.objects.new('spark_gun', me)
    bpy.context.scene.collection.objects.link(obj)

    mat = bpy.data.materials.new('spark_gun')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    t_alb = nt.nodes.new('ShaderNodeTexImage')
    t_alb.image = bpy.data.images.load(p_alb)
    t_alb.location = (-500, 250)
    t_emi = nt.nodes.new('ShaderNodeTexImage')
    t_emi.image = bpy.data.images.load(p_emi)
    t_emi.location = (-500, -150)
    nt.links.new(t_alb.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(t_emi.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = EMISSION_STRENGTH
    bsdf.inputs['Roughness'].default_value = 0.55
    bsdf.inputs['Metallic'].default_value = 0.0
    mat.use_backface_culling = True   # 閉じた形なので裏面は描かない（glTF の doubleSided = false）
    obj.data.materials.append(mat)

    mz = bpy.data.objects.new('muzzle', None)
    mz.empty_display_type = 'SINGLE_ARROW'
    mz.empty_display_size = 0.03
    mz.location = tuple(muzzle)   # 向きは銃と同じ（銃口の向きは +X）
    bpy.context.scene.collection.objects.link(mz)
    mz.parent = obj
    return obj, mz


def export(path: str) -> None:
    import bpy
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, export_apply=True,
                              export_animations=False, export_image_format='AUTO', export_extras=True)


# ---------------------------------------------------------------- 5. 確認

def rasterize(verts: np.ndarray, tris: np.ndarray, uv: np.ndarray, size: int) -> np.ndarray:
    img = Image.new('L', (size, size), 0)
    dr = ImageDraw.Draw(img)
    pu, pv = uv[tris, 0], uv[tris, 1]
    for i in range(len(tris)):
        dr.polygon([(pu[i, 0], pv[i, 0]), (pu[i, 1], pv[i, 1]), (pu[i, 2], pv[i, 2])], fill=255)
    return np.asarray(img) > 127


def side_project(verts: np.ndarray, frame: Frame, size: int) -> np.ndarray:
    px = frame.to_px(verts[:, [0, 2]])
    return px * (size / IMG)


@dataclass
class PerspCam:
    """斜めの絵のカメラ。az：-Y（真横）から +X（銃口）へ回る角度、el：上からの角度、dist：注視点までの距離、
    f：焦点距離（mm、センサー幅 36mm）、tx, tz：注視点、roll：視線回りの回転"""
    az: float
    el: float
    dist: float
    f: float
    tx: float
    tz: float
    roll: float

    def basis(self):
        a, e, r = math.radians(self.az), math.radians(self.el), math.radians(self.roll)
        back = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])   # 注視点 → カメラ
        d = -back
        right = np.cross(d, [0, 0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, d)
        right, up = right * math.cos(r) + up * math.sin(r), -right * math.sin(r) + up * math.cos(r)
        pos = np.array([self.tx, 0.0, self.tz]) + back * self.dist
        return pos, d, right, up

    def project(self, verts: np.ndarray, size: int) -> np.ndarray:
        pos, d, right, up = self.basis()
        q = verts - pos
        zc = q @ d
        k = self.f / 36.0 * size
        return np.stack([size / 2 + k * (q @ right) / zc, size / 2 - k * (q @ up) / zc], 1)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    return float((a & b).sum() / max((a | b).sum(), 1))


def fit_q45_camera(verts: np.ndarray, tris: np.ndarray, mask: np.ndarray,
                   az_fixed: float | None = None) -> tuple[PerspCam, float]:
    """斜めの絵の外形に、メッシュの外形がいちばん重なるカメラを探す（Nelder-Mead、512 画素で）。
    az_fixed を与えると方位角はその値に固定する（絵の「斜め 45 度」を信じる場合）"""
    size = 512
    target = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).resize((size, size), Image.BILINEAR)) > 127
    ys, xs = np.nonzero(target)
    tb = np.array([xs.min(), xs.max(), ys.min(), ys.max()], np.float64)
    c0 = verts.mean(0)
    cam = PerspCam(az_fixed or 45.0, 12.0, 0.6, 50.0, float(c0[0]), float(c0[2]), 0.0)
    # 最初の大きさと位置を外接矩形で合わせる
    for _ in range(3):
        uv = cam.project(verts, size)
        w = uv[:, 0].max() - uv[:, 0].min()
        cam.f *= (tb[1] - tb[0]) / w
        uv = cam.project(verts, size)
        pos, d, right, up = cam.basis()
        k = cam.f / 36.0 * size / cam.dist
        du = ((tb[0] + tb[1]) / 2 - (uv[:, 0].min() + uv[:, 0].max()) / 2) / k
        dv = ((tb[2] + tb[3]) / 2 - (uv[:, 1].min() + uv[:, 1].max()) / 2) / k
        shift = -right * du + up * dv
        cam.tx += shift[0]
        cam.tz += shift[2]

    def full(x):
        return x if az_fixed is None else np.concatenate([[az_fixed], x])

    def loss(x):
        x = full(x)
        c = PerspCam(x[0], x[1], math.exp(x[2]), x[3], x[4], x[5], x[6])
        if c.dist < 0.15 or c.f < 5:
            return 1.0
        uv = c.project(verts, size)
        return 1.0 - iou(rasterize(verts, tris, uv, size), target)

    x0 = np.array([cam.az, cam.el, math.log(cam.dist), cam.f, cam.tx, cam.tz, cam.roll])
    step = np.array([6.0, 4.0, 0.3, 8.0, 0.01, 0.01, 2.0])
    if az_fixed is not None:
        x0, step = x0[1:], step[1:]
    best = x0
    for _ in range(2):
        simplex = np.vstack([best] + [best + np.eye(len(best))[i] * step[i] for i in range(len(best))])
        res = optimize.minimize(loss, best, method='Nelder-Mead',
                                options={'initial_simplex': simplex, 'maxfev': 700, 'xatol': 1e-3, 'fatol': 1e-5})
        best = res.x
        step = step * 0.4
    loss_best = loss(best)
    x = full(best)
    cam = PerspCam(float(x[0]), float(x[1]), float(math.exp(x[2])), float(x[3]), float(x[4]), float(x[5]),
                   float(x[6]))
    return cam, 1.0 - float(loss_best)


def setup_render(size: int):
    import bpy
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = False
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('check_world')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
    cam = bpy.data.objects.new('check_cam', bpy.data.cameras.new('check_cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new('check_sun', 'SUN')
    sun_data.energy = 1.4
    sun_data.angle = math.radians(20)
    sun = bpy.data.objects.new('check_sun', sun_data)
    scene.collection.objects.link(sun)
    return scene, cam, sun


def render_view(scene, cam, sun, pos, d, right, up, path: str, ortho_scale: float | None = None,
                lens: float | None = None) -> np.ndarray:
    import bpy
    from mathutils import Matrix, Vector
    rot = Matrix((Vector(right), Vector(up), Vector(-np.asarray(d)))).transposed()
    cam.matrix_world = Matrix.Translation(Vector(pos)) @ rot.to_4x4()
    if ortho_scale:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho_scale
    else:
        cam.data.type = 'PERSP'
        cam.data.lens = lens
        cam.data.sensor_width = 36.0
        cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.clip_start = 0.01
    cam.data.clip_end = 20
    # 光はカメラの左上・手前から（絵の光に近い、正面寄りの柔らかい光）
    ldir = (-Vector(d) - Vector(right) * 0.5 + Vector(up) * 0.9).normalized()
    sun.matrix_world = ldir.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return np.asarray(Image.open(path).convert('RGBA'))


BG = np.array([200, 200, 208], np.float64)


def on_bg(rgba: np.ndarray, size: int) -> np.ndarray:
    im = Image.fromarray(rgba).resize((size, size), Image.LANCZOS) if rgba.shape[0] != size else Image.fromarray(rgba)
    a = np.asarray(im).astype(np.float64)
    al = a[..., 3:4] / 255
    return (a[..., :3] * al + BG * (1 - al)).astype(np.uint8)


def diff_image(art: np.ndarray, mesh: np.ndarray) -> np.ndarray:
    out = np.zeros(art.shape + (3,), np.uint8) + 40
    out[art & mesh] = (235, 235, 235)
    out[art & ~mesh] = (230, 40, 40)
    out[mesh & ~art] = (40, 110, 240)
    return out


def label(arr: np.ndarray, text: str) -> np.ndarray:
    im = Image.fromarray(arr)
    dr = ImageDraw.Draw(im)
    dr.rectangle((6, 6, 16 + 6 * len(text), 26), fill=(20, 20, 20))
    dr.text((11, 11), text, fill=(255, 230, 120))
    return np.asarray(im)


def checks(b: Builder, frame: Frame, side_rgba: np.ndarray, q_rgba: np.ndarray) -> dict:
    size = 1024
    verts, tris = b.triangles()
    # 真横：外形の一致（元の大きさで）
    side_mask = side_rgba[..., 3] > 127
    sil_side = rasterize(verts, tris, side_project(verts, frame, IMG), IMG)
    iou_side = iou(sil_side, side_mask)
    # 斜め：カメラを合わせる。絵の言う「45 度」に固定したものと、方位角も自由にしたもの
    q_mask = q_rgba[..., 3] > 127
    qcam, _ = fit_q45_camera(verts, tris, q_mask, az_fixed=45.0)
    fcam, _ = fit_q45_camera(verts, tris, q_mask)
    sil_q = rasterize(verts, tris, qcam.project(verts, IMG), IMG)
    iou_q = iou(sil_q, q_mask)
    iou_f = iou(rasterize(verts, tris, fcam.project(verts, IMG), IMG), q_mask)
    print(f'外形の IoU：真横 {iou_side:.4f}、斜め（45 度固定）{iou_q:.4f}、斜め（自由 {fcam.az:.1f} 度）{iou_f:.4f}',
          flush=True)
    print('斜めのカメラ', qcam, fcam, flush=True)

    scene, cam, sun = setup_render(size)
    # 真横：-Y から +Y を見る正投影。絵の中心を画面の中心に
    center = frame.to_world(np.array([[IMG / 2, IMG / 2]]))[0]
    ren_side = render_view(scene, cam, sun, (center[0], -2.0, center[1]), (0, 1, 0), (1, 0, 0), (0, 0, 1),
                           os.path.join(WORK, 'render_side.png'), ortho_scale=IMG * frame.s)
    pos, d, right, up = qcam.basis()
    ren_q = render_view(scene, cam, sun, pos, d, right, up, os.path.join(WORK, 'render_45.png'), lens=qcam.f)
    pos, d, right, up = fcam.basis()
    ren_f = render_view(scene, cam, sun, pos, d, right, up, os.path.join(WORK, 'render_45_free.png'), lens=fcam.f)

    def small(m):
        return np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((size, size), Image.BILINEAR)) > 127
    row = np.concatenate([
        label(on_bg(side_rgba, size), 'art: spark_gun_side.png'),
        label(on_bg(ren_side, size), 'mesh (Cycles, ortho, same frame)'),
        label(diff_image(small(side_mask), small(sil_side)), f'silhouette IoU {iou_side:.4f}  red=art only blue=mesh only'),
    ], 1)
    Image.fromarray(row).save(os.path.join(RECON, 'gun_check_side.png'))
    row = np.concatenate([
        label(on_bg(q_rgba, size), 'art: spark_gun_3d.png'),
        label(on_bg(ren_q, size), f'mesh (Cycles, az 45 fixed, el {qcam.el:.0f}, fitted)'),
        label(on_bg(ren_f, size), f'mesh (Cycles, az also fitted: {fcam.az:.0f}, IoU {iou_f:.3f})'),
        label(diff_image(small(q_mask), small(sil_q)), f'silhouette az 45: IoU {iou_q:.4f}'),
    ], 1)
    Image.fromarray(row).save(os.path.join(RECON, 'gun_check_45.png'))
    # 絵のない向き（反対側・上・後ろ）も 1 枚に
    extra = []
    for name, az, el in (('left side (mirror)', 180.0 + 0.0, 8.0), ('top-front', 60.0, 55.0),
                         ('rear-left', 215.0, 15.0), ('front', 90.0, 5.0)):
        c = PerspCam(az, el, qcam.dist, qcam.f, qcam.tx, qcam.tz, 0.0)
        p, dd, rr, uu = c.basis()
        img = render_view(scene, cam, sun, p, dd, rr, uu, os.path.join(WORK, f'render_{az:.0f}_{el:.0f}.png'),
                          lens=qcam.f * 0.85)
        extra.append(label(on_bg(img, size // 2), name))
    Image.fromarray(np.concatenate(extra, 1)).save(os.path.join(WORK, 'gun_check_other_views.png'))
    return {'iou_side': round(iou_side, 4), 'iou_45_az45': round(iou_q, 4), 'iou_45_free': round(iou_f, 4),
            'q45_camera_az45': {k: round(v, 4) for k, v in qcam.__dict__.items()},
            'q45_camera_free': {k: round(v, 4) for k, v in fcam.__dict__.items()}}


# ---------------------------------------------------------------- まとめ

def main() -> dict:
    os.makedirs(WORK, exist_ok=True)
    extract_sources()
    side = load_rgba(SIDE)
    q45 = load_rgba(Q45)
    lab = segment(side)
    save_segmentation(side, lab, os.path.join(WORK, 'parts.png'))
    frame, finfo = make_frame(side, lab)
    amber = amber_mask(side)
    b = Builder()
    stats = {}
    mouth, pane = window_rings(amber, frame)
    for part in PARTS:
        if part.name == 'bore':
            continue
        mask = part_mask(lab, part)
        rings = trace(mask, frame)
        holes = [mouth[::-1]] if part.name == 'receiver' else None
        stats[part.name] = build_extrusion(b, part, rings, lab, frame, mask, cap_holes=holes)
        if part.name == 'receiver':
            build_window(b, part, mouth, pane, frame)
    bore = build_bore(b, lab, frame)
    p_alb, p_emi = make_textures(side, amber, lab)
    verts, tris = b.triangles()
    obj, mz = blender_object(b, p_alb, p_emi, bore['muzzle'])
    export(OUT_GLB)
    bb_min, bb_max = verts.min(0), verts.max(0)
    report = {
        'glb': os.path.relpath(OUT_GLB, REPO), 'triangles': int(len(tris)), 'faces': len(b.faces),
        'bbox_min_m': [round(float(v), 4) for v in bb_min], 'bbox_max_m': [round(float(v), 4) for v in bb_max],
        'muzzle_m': [round(v, 4) for v in bore['muzzle']], 'frame': finfo, 'parts': stats,
        'triangles_by_part': {k: int(sum(len(f) - 2 for f, p in zip(b.faces, b.parts) if p == k))
                              for k in dict.fromkeys(b.parts)},
    }
    print(json.dumps(report, indent=1, ensure_ascii=False), flush=True)
    report['check'] = checks(b, frame, side, q45)
    with open(os.path.join(WORK, 'gun_report.json'), 'w') as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    return report


if __name__ == '__main__':
    main()
