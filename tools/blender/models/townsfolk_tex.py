"""町の住人のキット（townsfolk.py）のテクスチャ：色見本と、決まりで描く顔。

1 人のテクスチャは 512×256 の 1 枚（材質も 1 つ）：
  左の 256×256 ＝ その人の顔（目・眉・口・鼻。頭の正面に平らに投影する）
  右の 256×256 ＝ キットの色見本（16×16 のマス目、1 マス 16px。全員で同じ並び）
色見本のマス目は、面の 3 つの頂点が同じ UV（マスの中心）を指すので、遠くでもミップマップで隣の色が混ざらない。

顔の座標は「頭の単位」：あごの先 v=0、頭頂 v=1、左右 u（本人の左が +）。顔の窓は u −0.45〜0.45、v −0.05〜0.85。
townsfolk.py の顔の UV の投影も同じ窓を使う（FACE_U・FACE_V）。

  python tools/blender/models/townsfolk_tex.py <出力フォルダ>   見本の顔を全部描く（確認用）
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter

# ---------------------------------------------------------------- 色見本
# (名前, #hex)。町の色（spec.md の色見本）＋ 汎用の 5 案の色 ＋ 髪・肌・細部。並びを変えると全員の GLB が変わる（足すのは末尾へ）
PALETTE = [
    ('skin', '#E9AA80'), ('skin_dark', '#D4956C'), ('skin_old', '#E6AA86'), ('lip', '#B9655A'),
    ('rust', '#A3513B'), ('rust_dark', '#7F3D2C'), ('rust_faded', '#B07A62'), ('rust_faded_dark', '#8F6150'),
    ('cream', '#EEDCC0'), ('cream_dark', '#D6C0A0'), ('sand', '#C9A06E'), ('sand_dark', '#A8814F'),
    ('brown', '#5E4334'), ('brown_dark', '#45302A'), ('graphite', '#46433F'), ('graphite_dark', '#33302D'),
    ('olive', '#7A7557'), ('olive_dark', '#5E5A42'), ('brass', '#A98749'), ('leather', '#6A4530'),
    ('boot', '#6B4634'), ('boot_toe', '#C49A6A'), ('sole', '#3A2E29'), ('lens', '#D89538'),
    ('hair_brown', '#6A4532'), ('hair_dark', '#3F2C24'), ('hair_ginger', '#B4602F'), ('hair_grey', '#C4BDB6'),
    ('hair_white', '#E7E2DA'), ('hair_brown_dark', '#4E3428'), ('hair_ginger_dark', '#8F4824'), ('hair_grey_dark', '#9F978F'),
    ('patch', '#B08A60'), ('patch_dark', '#8A6A4C'), ('stitch', '#E6D4B4'), ('ochre', '#B98F50'),
    ('ochre_dark', '#93703A'), ('sock', '#D9C4A2'), ('inner', '#3B2C25'), ('glove', '#5A4031'),
    ('knit', '#4A403A'), ('knit_dark', '#37302C'), ('beard_brown', '#5A3C2C'), ('beard_white', '#E4DED6'),
    ('hat_olive', '#8C7F5A'), ('hat_olive_dark', '#6E6345'), ('scarf_olive', '#6F6E4C'), ('scarf_brown', '#5C3F2F'),
]
CELLS = 16
INDEX = {n: i for i, (n, _) in enumerate(PALETTE)}

# 汎用の色の 5 案（spec.md）：a＝広い面の色、b＝差し色。設定の色の "$a"・"$b" がこれになる
SCHEMES = {
    'sand_rust': {'a': 'sand', 'a_dark': 'sand_dark', 'b': 'rust', 'b_dark': 'rust_dark'},            # 砂＋赤錆
    'cream_brown': {'a': 'cream', 'a_dark': 'cream_dark', 'b': 'brown', 'b_dark': 'brown_dark'},      # 生成り＋焦げ茶
    'graphite_sand': {'a': 'graphite', 'a_dark': 'graphite_dark', 'b': 'sand', 'b_dark': 'sand_dark'},  # 石墨＋砂
    'faded_rust_cream': {'a': 'rust_faded', 'a_dark': 'rust_faded_dark', 'b': 'cream', 'b_dark': 'cream_dark'},  # 褪せた赤錆＋生成り
    'olive_sand': {'a': 'olive', 'a_dark': 'olive_dark', 'b': 'sand', 'b_dark': 'sand_dark'},          # 灰オリーブ＋砂
}

TEX_W, TEX_H = 512, 256
FACE_PX = 256
PAL_X0 = 256          # 色見本の左の端（px）
CELL_PX = 16


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


def color_hex(name: str) -> str:
    return PALETTE[INDEX[name]][1]


def palette_uv(name: str) -> tuple[float, float]:
    """色の名前 → UV（マスの中心。Blender の UV は左下が原点）"""
    i = INDEX[name]
    col, row = i % CELLS, i // CELLS
    u = (PAL_X0 + (col + 0.5) * CELL_PX) / TEX_W
    v = 1 - ((row + 0.5) * CELL_PX) / TEX_H
    return u, v


def draw_palette(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    for i, (_, hx) in enumerate(PALETTE):
        c, r = i % CELLS, i // CELLS
        x0, y0 = PAL_X0 + c * CELL_PX, r * CELL_PX
        d.rectangle((x0, y0, x0 + CELL_PX - 1, y0 + CELL_PX - 1), fill=hex_rgb(hx))


# ---------------------------------------------------------------- 顔
# 顔の窓（頭の単位）。townsfolk.py の投影と同じ
FACE_U = (-0.45, 0.45)
FACE_V = (-0.05, 0.85)
SS = 4   # 描くときの拡大率（最後に縮めて縁をなめらかに）

LASH = (52, 36, 30)
WHITE = (250, 246, 238)
MOUTH = (128, 62, 50)
NOSE = (205, 132, 104)
BLUSH = (238, 140, 118)
WRINKLE = (196, 128, 100)


class Canvas:
    def __init__(self, skin: str):
        self.n = FACE_PX * SS
        self.img = Image.new('RGB', (self.n, self.n), hex_rgb(skin))
        self.d = ImageDraw.Draw(self.img)

    def P(self, u: float, v: float) -> tuple[float, float]:
        x = (u - FACE_U[0]) / (FACE_U[1] - FACE_U[0]) * self.n
        y = (FACE_V[1] - v) / (FACE_V[1] - FACE_V[0]) * self.n
        return x, y

    def L(self, a: float) -> float:
        return a / (FACE_U[1] - FACE_U[0]) * self.n

    def ellipse(self, u, v, ru, rv, fill) -> None:
        x, y = self.P(u, v)
        self.d.ellipse((x - self.L(ru), y - self.L(rv), x + self.L(ru), y + self.L(rv)), fill=fill)

    def stroke(self, pts, w0, w1=None, fill=LASH) -> None:
        w1 = w0 if w1 is None else w1
        n = 30
        segs = len(pts) - 1
        for i in range(n * segs + 1):
            f = i / (n * segs)
            k = min(segs - 1, int(f * segs))
            t = f * segs - k
            (ua, va), (ub, vb) = pts[k], pts[k + 1]
            u, v = ua + (ub - ua) * t, va + (vb - va) * t
            r = self.L((w0 + (w1 - w0) * f) / 2)
            x, y = self.P(u, v)
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def polygon(self, pts, fill) -> None:
        self.d.polygon([self.P(u, v) for u, v in pts], fill=fill)


def curve(a, b, c, n=12):
    return [tuple((1 - t) ** 2 * a[k] + 2 * (1 - t) * t * b[k] + t ** 2 * c[k] for k in range(2))
            for t in (i / n for i in range(n + 1))]


def draw_eye(cv: Canvas, side: int, f: dict) -> None:
    """side=+1 は本人の左目（画像の右）"""
    ex, ev = side * f['eye_u'], f['eye_v']
    s = f['eye_size']
    rx, rv = 0.060 * s, 0.072 * s * f.get('eye_tall', 1.0)
    iris = hex_rgb(f.get('iris', '#5A3A28'))
    iris_lo = tuple(min(255, int(c * 1.55 + 18)) for c in iris)
    old = f.get('old', False)
    # 白目
    cv.ellipse(ex, ev, rx, rv, WHITE)
    # 虹彩（上が暗い）：白目の内側に、少し内へ寄せる
    icx = ex - side * rx * 0.08
    irx, irv = rx * 0.78, rv * 0.86
    cv.ellipse(icx, ev - rv * 0.06, irx, irv, iris)
    cv.ellipse(icx, ev - rv * 0.30, irx * 0.80, irv * 0.55, iris_lo)
    cv.ellipse(icx, ev - rv * 0.02, irx * 0.42, irv * 0.48, (34, 22, 16))
    # 上まぶた：白目の上を肌で消してから太い線
    lid = f.get('lid', 0.0)   # 正で上まぶたが下がる（眠そう・年寄り）
    top = ev + rv * (0.95 - lid)
    inner = (ex - side * rx * 1.10, ev + rv * (0.30 - lid * 0.5))
    peak = (ex + side * rx * 0.05, top + rv * 0.12)
    outer = (ex + side * rx * 1.18, ev + rv * (0.50 - lid * 0.6))
    skin = hex_rgb(f['skin'])
    cover = curve((inner[0] - side * 0.01, inner[1]), peak, (outer[0] + side * 0.01, outer[1]))
    cv.polygon(cover + [(outer[0] + side * 0.02, ev + rv + 0.06), (inner[0] - side * 0.02, ev + rv + 0.06)], skin)
    # 下の縁も肌で整える（白目の下が丸く見えすぎないように、少しだけ）
    lw = f.get('lid_w', 0.022)
    cv.stroke(curve(inner, peak, outer), lw * 0.75, lw * 1.25)
    if f.get('lash', False):
        cv.stroke([outer, (outer[0] + side * 0.030, outer[1] + 0.018)], lw * 1.0, lw * 0.4)
    else:
        cv.stroke([outer, (outer[0] + side * 0.016, outer[1] - 0.012)], lw * 0.8, lw * 0.3)
    # 下まぶた（外側だけ短く）
    cv.stroke([(ex + side * rx * 0.15, ev - rv * 0.98), (ex + side * rx * 0.90, ev - rv * 0.62)], 0.006, 0.009,
              fill=(150, 92, 72))
    # 光
    cv.ellipse(icx + side * irx * 0.35, ev + rv * 0.32, rx * 0.22, rv * 0.20, (255, 255, 255))
    if old:
        # 目尻のしわ
        for k in (0, 1):
            a = (ex + side * rx * 1.35, ev + rv * (0.15 - 0.45 * k))
            b = (ex + side * rx * 1.75, ev + rv * (0.30 - 0.75 * k))
            cv.stroke([a, b], 0.006, 0.004, fill=WRINKLE)


def draw_brow(cv: Canvas, side: int, f: dict) -> None:
    ex = side * f['eye_u']
    bz = f['eye_v'] + f.get('brow_dv', 0.115)
    tilt = f.get('brow_tilt', 0.0)    # 正で内側が下がる（きりっと・不機嫌）
    w = f.get('brow_w', 0.026)
    col = hex_rgb(f.get('brow', '#4A3428'))
    inner = (ex - side * 0.050, bz - tilt)
    mid = (ex + side * 0.005, bz + 0.012)
    outer = (ex + side * 0.070, bz - 0.006 + tilt * 0.3)
    cv.stroke(curve(inner, mid, outer), w, w * 0.55, fill=col)


def draw_mouth(cv: Canvas, f: dict) -> None:
    mv = f.get('mouth_v', 0.16)
    kind = f.get('mouth', 'smile')
    w = f.get('mouth_w', 0.040)
    if kind == 'smile':
        cv.stroke(curve((-w, mv + 0.008), (0.0, mv - 0.016), (w, mv + 0.008)), 0.011, 0.011, fill=MOUTH)
    elif kind == 'flat':
        cv.stroke(curve((-w, mv), (0.0, mv - 0.006), (w, mv)), 0.011, 0.011, fill=MOUTH)
    elif kind == 'open':
        pts = curve((-w, mv + 0.010), (0.0, mv - 0.040), (w, mv + 0.010), n=16)
        cv.polygon(pts, (130, 54, 48))
        cv.polygon(curve((-w * 0.5, mv - 0.012), (0.0, mv - 0.030), (w * 0.5, mv - 0.012), n=8), (214, 110, 94))
        cv.stroke(pts + [pts[0]], 0.008, 0.008, fill=MOUTH)


def draw_nose(cv: Canvas, f: dict) -> None:
    nv = f.get('nose_v', 0.26)
    cv.stroke([(0.010, nv + 0.012), (0.002, nv)], 0.010, 0.007, fill=NOSE)


def draw_blush(cv: Canvas, f: dict) -> None:
    layer = Image.new('RGBA', cv.img.size, (*BLUSH, 0))
    ld = ImageDraw.Draw(layer)
    for side in (-1, 1):
        x, y = cv.P(side * (f['eye_u'] + 0.020), f['eye_v'] - 0.105)
        r, rv = cv.L(0.055), cv.L(0.024)
        ld.ellipse((x - r, y - rv, x + r, y + rv), fill=(*BLUSH, int(110 * f.get('blush', 1.0))))
    layer = layer.filter(ImageFilter.GaussianBlur(cv.L(0.016)))
    cv.img = Image.alpha_composite(cv.img.convert('RGBA'), layer).convert('RGB')
    cv.d = ImageDraw.Draw(cv.img)


def draw_wrinkles(cv: Canvas, f: dict) -> None:
    """年寄りの線：ほうれい線と額の線（薄く）"""
    for side in (-1, 1):
        cv.stroke(curve((side * 0.095, 0.245), (side * 0.112, 0.205), (side * 0.100, 0.175)), 0.006, 0.003, fill=WRINKLE)
    if f.get('forehead', True):
        for k in range(2):
            v = f['eye_v'] + 0.20 + k * 0.035
            cv.stroke(curve((-0.07, v), (0.0, v + 0.008), (0.07, v)), 0.005, 0.005, fill=WRINKLE)


def face_image(f: dict) -> Image.Image:
    """f：顔の設定（skin・eye_u・eye_v・eye_size・iris・brow・mouth…）。FACE_PX 角の画像"""
    cv = Canvas(f['skin'])
    if f.get('blush', 0):
        draw_blush(cv, f)
    for s in (-1, 1):
        draw_eye(cv, s, f)
        draw_brow(cv, s, f)
    draw_nose(cv, f)
    if f.get('wrinkles'):
        draw_wrinkles(cv, f)
    draw_mouth(cv, f)
    return cv.img.resize((FACE_PX, FACE_PX), Image.LANCZOS)


def write_texture(path: str, face: dict) -> str:
    img = Image.new('RGB', (TEX_W, TEX_H), hex_rgb(face['skin']))
    img.paste(face_image(face), (0, 0))
    draw_palette(img)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return path


if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    demo = {'skin': '#EDB48C', 'eye_u': 0.15, 'eye_v': 0.36, 'eye_size': 1.0, 'blush': 1.0, 'lash': True}
    print(write_texture(os.path.join(out, 'tf_demo.png'), demo))
