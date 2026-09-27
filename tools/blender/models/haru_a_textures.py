"""ハル（A案の試作）のテクスチャを描く。

- 色見本（palette）：spec_a.md の hex をマス目に並べた 256×256。全身の色はここを UV で指す
- 発光（emissive）：同じ並びで、琥珀の光る部分だけ色を置く
- 顔（face）：1024×1024 を 2×2 に分け、表情 4 種（通常／笑顔／驚き／痛み）。
  ゲームではテクスチャのずらし量で表情を切り替える

顔の座標は、頭の正面に投影したメートル単位（x：-0.14〜0.14、z：1.16〜1.44）で描く。
haru_a.py の顔の UV の投影と同じ範囲。
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFilter

# (名前, #hex, 発光の強さ)。spec_a.md の色見本を優先し、足りない色（肌、目など）は試作での仮の色
PALETTE = [
    ('brick', '#B75B43', 0),       # 作業着（spec）
    ('shell', '#F3E9D2', 0),       # 外装（spec）
    ('frame', '#444641', 0),       # フレーム・靴底（spec）
    ('brass', '#A98749', 0),       # 継ぎ目（spec）
    ('hair', '#594333', 0),        # 髪・革帯（spec）
    ('amber', '#FFBC52', 1.0),     # 遺物の光（spec）
    ('skin', '#EDB892', 0),        # 肌（仮）
    ('shirt', '#EBDDBF', 0),       # 中のシャツ（仮：外装より少し暗く）
    ('glove', '#4A3A30', 0),       # 手袋（仮）
    ('boot', '#7E4632', 0),        # 靴の甲（仮：作業着を暗く）
    ('brick_dark', '#94472F', 0),  # 作業着の影の面・折り返し（仮）
    ('leg', '#5A4436', 0),         # すねの布（仮）
    ('amber_dim', '#C98A2E', 0.35),  # ゴーグルのレンズ（弱く光る）
    ('lens_rim', '#2F302C', 0),    # レンズの縁（仮）
]
CELLS = 8
FACE_SKIN = '#EDB892'


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


def write_palette(out_dir: str) -> tuple[str, str]:
    size = 256
    cell = size // CELLS
    base = Image.new('RGB', (size, size), (128, 128, 128))
    emit = Image.new('RGB', (size, size), (0, 0, 0))
    db, de = ImageDraw.Draw(base), ImageDraw.Draw(emit)
    for i, (_, hx, strength) in enumerate(PALETTE):
        c, r = i % CELLS, i // CELLS
        box = (c * cell, r * cell, (c + 1) * cell - 1, (r + 1) * cell - 1)
        rgb = hex_rgb(hx)
        db.rectangle(box, fill=rgb)
        if strength > 0:
            de.rectangle(box, fill=tuple(int(v * strength) for v in rgb))
    os.makedirs(out_dir, exist_ok=True)
    pb, pe = os.path.join(out_dir, 'haru_a_palette.png'), os.path.join(out_dir, 'haru_a_emissive.png')
    base.save(pb)
    emit.save(pe)
    return pb, pe


# ---------------------------------------------------------------- 顔

S = 4          # 描くときの拡大率（最後に縮めて輪郭をなめらかにする）
FACE = 512     # 1 表情の大きさ（px）
X0, X1, Z0, Z1 = -0.14, 0.14, 1.16, 1.44
# 顔のパーツは「基準の頭」（中心 z=1.375、幅 0.128）の座標で描き、試作の頭の大きさへ拡大して置く
HEAD_K = 1.12
HEAD_Z = 1.36

LASH = (46, 32, 25)
BROW = (74, 53, 38)
IRIS_TOP = (64, 36, 22)
IRIS_BOT = (160, 102, 52)
PUPIL = (36, 22, 14)
MOUTH = (122, 58, 44)
MOUTH_IN = (132, 52, 44)
TONGUE = (214, 110, 94)
LOWER_LID = (150, 92, 70)
NOSE = (210, 140, 112)
BLUSH = (242, 150, 128)


def P(x: float, z: float) -> tuple[float, float]:
    """顔の座標（m）→ 1 表情の画像の中の px（拡大後）"""
    xn, zn = x * HEAD_K, HEAD_Z + (z - 1.375) * HEAD_K
    return ((xn - X0) / (X1 - X0) * FACE * S, (Z1 - zn) / (Z1 - Z0) * FACE * S)


def L(v: float) -> float:
    return v * HEAD_K / (X1 - X0) * FACE * S


def ellipse(d: ImageDraw.ImageDraw, x: float, z: float, rx: float, rz: float, fill) -> None:
    cx, cy = P(x, z)
    d.ellipse((cx - L(rx), cy - L(rz), cx + L(rx), cy + L(rz)), fill=fill)


def stroke(d: ImageDraw.ImageDraw, pts: list[tuple[float, float]], w0: float, w1: float | None = None, fill=LASH) -> None:
    """太さが変わる線（始点 w0 → 終点 w1）。丸い点を並べて描く"""
    w1 = w0 if w1 is None else w1
    n = 40
    segs = len(pts) - 1
    for i in range(n * segs + 1):
        f = i / (n * segs)
        k = min(segs - 1, int(f * segs))
        t = f * segs - k
        (xa, za), (xb, zb) = pts[k], pts[k + 1]
        x, z = xa + (xb - xa) * t, za + (zb - za) * t
        r = L((w0 + (w1 - w0) * f) / 2)
        cx, cy = P(x, z)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)


def curve(a, b, c, n=12) -> list[tuple[float, float]]:
    """2 次ベジエの点列"""
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(tuple((1 - t) ** 2 * a[k] + 2 * (1 - t) * t * b[k] + t ** 2 * c[k] for k in range(2)))
    return out  # type: ignore


EYE_X, EYE_Z = 0.047, 1.312


def draw_open_eye(img: Image.Image, side: int, scale: float = 1.0, iris_scale: float = 1.0, lid_drop: float = 0.0) -> None:
    """side=+1 は本人の左目（画像の右）。外側は side の向き"""
    d = ImageDraw.Draw(img)
    cx, cz = side * EYE_X, EYE_Z
    rx, rz = 0.0185 * scale, 0.0235 * scale
    ellipse(d, cx, cz, rx, rz, (252, 248, 240))
    # 虹彩：上が暗く下が明るい
    irx, irz = 0.0150 * iris_scale * scale, 0.0212 * iris_scale * scale
    icx, icz = cx - side * 0.0008, cz - 0.0015
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).ellipse(
        (P(icx, icz)[0] - L(irx), P(icx, icz)[1] - L(irz), P(icx, icz)[0] + L(irx), P(icx, icz)[1] + L(irz)), fill=255)
    # 白目の外にはみ出さない
    eye_mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(eye_mask).ellipse((P(cx, cz)[0] - L(rx), P(cx, cz)[1] - L(rz), P(cx, cz)[0] + L(rx), P(cx, cz)[1] + L(rz)), fill=255)
    from PIL import ImageChops
    mask = ImageChops.multiply(mask, eye_mask)
    grad = Image.new('RGB', img.size)
    gd = ImageDraw.Draw(grad)
    top, bot = P(0, icz + irz)[1], P(0, icz - irz)[1]
    for y in range(int(top), int(bot) + 1):
        f = min(1.0, max(0.0, (y - top) / max(1, bot - top)))
        gd.line((0, y, img.size[0], y), fill=tuple(int(IRIS_TOP[k] + (IRIS_BOT[k] - IRIS_TOP[k]) * f ** 1.3) for k in range(3)))
    img.paste(grad, (0, 0), mask)
    ellipse(d, icx, icz + 0.001, 0.0058 * iris_scale * scale, 0.0085 * iris_scale * scale, PUPIL)
    # まぶた（上）：内側から外側へ、外側で少し跳ねる
    top_z = cz + rz * 0.98 - lid_drop
    inner = (cx - side * rx * 1.05, cz + rz * 0.35 - lid_drop * 0.5)
    peak = (cx + side * rx * 0.1, top_z + 0.004)
    outer = (cx + side * rx * 1.15, cz + rz * 0.55 - lid_drop * 0.5)
    # まぶたより上の白目を肌で消す
    skin = hex_rgb(FACE_SKIN)
    cover = curve((inner[0] - side * 0.004, inner[1]), peak, (outer[0] + side * 0.004, outer[1]))
    poly = [P(*p) for p in cover] + [P(outer[0] + side * 0.006, cz + rz + 0.01), P(inner[0] - side * 0.006, cz + rz + 0.01)]
    d.polygon(poly, fill=skin)
    stroke(d, curve(inner, peak, outer), 0.0026, 0.0052)
    stroke(d, [outer, (outer[0] + side * 0.0045, outer[1] - 0.004)], 0.0045, 0.0015)
    # まぶた（下）：外側だけ短く
    lo_a = (cx + side * rx * 0.2, cz - rz * 0.98)
    lo_b = (cx + side * rx * 0.95, cz - rz * 0.55)
    stroke(d, [lo_a, lo_b], 0.0010, 0.0018, fill=LOWER_LID)
    # 光
    ellipse(d, icx + side * 0.0042, icz + 0.0085 - lid_drop * 0.3, 0.0042 * scale, 0.0055 * scale, (255, 255, 255))
    ellipse(d, icx - side * 0.0048, icz - 0.0090, 0.0018 * scale, 0.0018 * scale, (255, 250, 236))


def draw_brow(d: ImageDraw.ImageDraw, side: int, dz: float = 0.0, tilt: float = 0.0) -> None:
    """tilt が正で内側が下がる（怒り・痛み）、負で内側が上がる（驚き・困り）"""
    cx = side * EYE_X
    inner = (cx - side * 0.0145, 1.353 + dz - tilt)
    mid = (cx + side * 0.001, 1.360 + dz)
    outer = (cx + side * 0.0175, 1.356 + dz + tilt * 0.3)
    stroke(d, curve(inner, mid, outer), 0.0062, 0.0036, fill=BROW)


def draw_blush(img: Image.Image) -> Image.Image:
    layer = Image.new('RGBA', img.size, (*BLUSH, 0))
    ld = ImageDraw.Draw(layer)
    for side in (-1, 1):
        cx, cy = P(side * 0.061, 1.284)
        ld.ellipse((cx - L(0.012), cy - L(0.0055), cx + L(0.012), cy + L(0.0055)), fill=(*BLUSH, 90))
    layer = layer.filter(ImageFilter.GaussianBlur(L(0.004)))
    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')


def draw_nose(d: ImageDraw.ImageDraw) -> None:
    stroke(d, [(0.0035, 1.281), (0.0005, 1.2745)], 0.0022, 0.0016, fill=NOSE)


def face(expr: str) -> Image.Image:
    img = Image.new('RGB', (FACE * S, FACE * S), hex_rgb(FACE_SKIN))
    img = draw_blush(img)
    d = ImageDraw.Draw(img)
    if expr == 'normal':
        for s in (-1, 1):
            draw_open_eye(img, s)
            draw_brow(d, s)
        stroke(d, curve((-0.0125, 1.2485), (0.0, 1.2415), (0.0125, 1.2485)), 0.0021, 0.0021, fill=MOUTH)
    elif expr == 'smile':
        for s in (-1, 1):
            cx = s * EYE_X
            stroke(d, curve((cx - 0.017, 1.305), (cx, 1.326), (cx + 0.017, 1.305)), 0.0045, 0.0045)
            draw_brow(d, s, dz=0.004, tilt=-0.002)
        mouth = curve((-0.017, 1.252), (0.0, 1.226), (0.017, 1.252), n=16)
        d.polygon([P(*p) for p in mouth], fill=MOUTH_IN)
        tongue = curve((-0.009, 1.2385), (0.0, 1.2305), (0.009, 1.2385), n=10)
        d.polygon([P(*p) for p in tongue], fill=TONGUE)
        stroke(d, mouth + [mouth[0]], 0.0016, 0.0016, fill=MOUTH)
    elif expr == 'surprise':
        for s in (-1, 1):
            draw_open_eye(img, s, scale=1.08, iris_scale=0.72)
            draw_brow(d, s, dz=0.009, tilt=-0.003)
        ellipse(d, 0.0, 1.244, 0.0062, 0.0078, MOUTH)
        ellipse(d, 0.0, 1.2435, 0.0042, 0.0058, MOUTH_IN)
    elif expr == 'pain':
        for s in (-1, 1):
            cx = s * EYE_X
            # 「＞」「＜」の形に目をつぶる
            a = (cx + s * 0.016, 1.322)
            b = (cx - s * 0.012, 1.311)
            c = (cx + s * 0.016, 1.300)
            stroke(d, [a, b, c], 0.0045, 0.0045)
            draw_brow(d, s, dz=-0.002, tilt=0.006)
        d.rounded_rectangle((*P(-0.016, 1.254), *P(0.016, 1.236)), radius=L(0.005), fill=(250, 246, 238))
        stroke(d, [(-0.016, 1.245), (0.016, 1.245)], 0.0012, 0.0012, fill=(200, 170, 160))
        stroke(d, [(-0.016, 1.254), (0.016, 1.254), (0.016, 1.236), (-0.016, 1.236), (-0.016, 1.254)], 0.0017, 0.0017,
               fill=MOUTH)
    draw_nose(d)
    return img.resize((FACE, FACE), Image.LANCZOS)


FACE_ORDER = ['normal', 'smile', 'surprise', 'pain']  # 左上、右上、左下、右下


def write_face(out_dir: str) -> str:
    sheet = Image.new('RGB', (FACE * 2, FACE * 2))
    for i, e in enumerate(FACE_ORDER):
        sheet.paste(face(e), ((i % 2) * FACE, (i // 2) * FACE))
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, 'haru_a_face.png')
    sheet.save(p)
    return p


if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    print(write_palette(out), write_face(out))
