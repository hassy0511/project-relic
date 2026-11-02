"""比べの画像（docs/art_orders/haru_bs_trial/）を、render_compare.py の描いた絵から組む。

  .venv-blender/bin/python tools/blender/trial_bs/sheets.py <pass>

model_views.jpg（全身：絵｜haru_bs、1 行に 2 つの向き）、model_head.jpg（頭）、model_face.jpg（4 つの表情）。
JPG は 400 KB 以下、日本語のラベル（IPA ゴシック）。
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'build', 'trial_bs')
ART = os.path.join(ROOT, 'build', 'art')
DOC = os.path.join(ROOT, 'docs', 'art_orders', 'haru_bs_trial')
FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'

sys.path.insert(0, HERE)


def font(sz):
    return ImageFont.truetype(FONT, sz) if os.path.exists(FONT) else ImageFont.load_default()


def on_gray(im, size, crop=None):
    im = im.convert('RGBA')
    if crop:
        w, h = im.size
        im = im.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
    bg = Image.new('RGBA', im.size, (206, 206, 210, 255))
    bg.alpha_composite(im)
    return bg.convert('RGB').resize(size, Image.LANCZOS)


def pair_sheet(pairs, out, cell, crop, cols, title, max_kb=390):
    """pairs：[(ラベル, 絵の画像, モデルの画像)]。1 行に cols 組"""
    cw, ch = cell
    lab = 34
    rows = (len(pairs) + cols - 1) // cols
    W = cols * cw * 2 + (cols - 1) * 16
    H = 48 + rows * (ch + lab)
    sheet = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), title, fill=(20, 20, 20), font=font(26))
    for i, (label, a, b) in enumerate(pairs):
        r, c = divmod(i, cols)
        x = c * (cw * 2 + 16)
        y = 48 + r * (ch + lab)
        d.text((x + 6, y + 4), f'{label}：絵', fill=(40, 40, 40), font=font(22))
        d.text((x + cw + 6, y + 4), 'haru_bs', fill=(40, 40, 40), font=font(22))
        sheet.paste(on_gray(a, (cw, ch), crop), (x, y + lab))
        sheet.paste(on_gray(b, (cw, ch), crop), (x + cw, y + lab))
    os.makedirs(DOC, exist_ok=True)
    q = 88
    while True:
        sheet.save(out, quality=q, optimize=True)
        if os.path.getsize(out) <= max_kb * 1024 or q <= 50:
            break
        q -= 6
    print(out, os.path.getsize(out) // 1024, 'KB', 'q', q)


def main(tag):
    import render_compare as R
    cmp_dir = os.path.join(OUT, 'cmp', tag)

    def pr(view, label):
        a = Image.open(os.path.join(ART, R.VIEWS[view]['img']))
        b = Image.open(os.path.join(cmp_dir, f'{view}_render.png'))
        return (label, a, b)
    body = [('front', '正面'), ('back', '背面'), ('side_right', '右の真横'), ('side_left', '左の真横'),
            ('three_quarter', '右前 45 度'), ('front_left45', '左前 45 度')]
    pairs = [pr(v, l) for v, l in body if os.path.exists(os.path.join(cmp_dir, f'{v}_render.png'))]
    pair_sheet(pairs, os.path.join(DOC, 'model_views.jpg'), (270, 470), (0.2, 0.03, 0.8, 0.97), 2,
               '全身：Codex の絵｜haru_bs（同じ正投影のカメラ、陰は 3 段のトゥーン）')
    head = [('head_side_right', '頭・右の真横'), ('head_back', '頭・背面'), ('head_front_right45', '頭・右前 45 度'),
            ('head_top', '頭・真上'), ('face_front', '顔・正面'), ('gun_side', 'スパーク・真横')]
    pairs = [pr(v, l) for v, l in head if os.path.exists(os.path.join(cmp_dir, f'{v}_render.png'))]
    pair_sheet(pairs, os.path.join(DOC, 'model_head.jpg'), (330, 330), None, 2,
               '頭：Codex の絵｜haru_bs（絵の髪の外形の箱に合わせたカメラ）')
    face = [('expr0', '通常（0,0）'), ('expr1', '笑顔（0.5,0）'), ('expr2', '驚き（0,0.5）'), ('expr3', '痛み（0.5,0.5）')]
    pairs = [pr(v, l) for v, l in face if os.path.exists(os.path.join(cmp_dir, f'{v}_render.png'))]
    pair_sheet(pairs, os.path.join(DOC, 'model_face.jpg'), (330, 330), (0.1, 0.05, 0.9, 0.85), 2,
               '表情：2×2 の絵の区画｜haru_bs（顔の材質の uv1_offset をずらしたもの）')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'p1')
