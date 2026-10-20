"""ハルの 2 次の動き（髪・ポーチの揺れ、足の接地）の比べの画像を並べる（W1_ハル再構築の結果.md 8.6・8.8）。
撮るのは Godot の --haru_motion_shots（godot/scripts/debug/haru_motion_shots.gd）。ここではその PNG を切り抜いて、日本語の見出しを付けた
JPG（1 枚 400 KB まで）にする：
  .venv-blender/bin/python tools/blender/recon/secondary_sheets.py <撮った所> <出す所> [--pouch=<ポーチの撮った所>]
動き（strip_runstop・strip_landing・strip_dash、--pouch で strip_pouch）：行 = 前（切った）・後（入れた）・違い（前と後で色の違う
画素を赤に。同じ場面・同じカメラなので、揺れで動いた所だけが赤くなる）、列 = 0.0〜0.5 秒。
止まった絵（still_stairs・still_ramp）：前・後のそれぞれに全身と足もと。
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
TITLES = {
    'runstop': '走って止まる（スティックを離した刻みから 0.1 秒ごと）',
    'landing': '着地（着地した刻みから 0.1 秒ごと）',
    'dash': 'ダッシュ（押した刻みから 0.1 秒ごと）',
}
POUCH_TITLE = '帯のポーチ（右）：走って止まる（スティックを離した刻みから 0.1 秒ごと）'
ROWS = {'off': ('前', '（揺れなし）'), 'on': ('後', '（髪・ポーチが', '揺れる）'), 'diff': ('違い', '（赤：前と後で', '動いた所）')}
STILL_TITLES = {'stairs': '階段の段の縁に横向きに立つ（1 段 0.31 m）', 'ramp': '坂に横向きに立つ（23.8 度）'}
# 切り抜き（画面の割合）：動きは追うカメラの真ん中の上半身、ポーチは腰のまわり。止まった絵は全身と足もと
STRIP_BOX = (0.35, 0.04, 0.65, 0.62)
POUCH_BOX = (0.25, 0.0, 0.75, 1.0)
FULL_BOX = (0.30, 0.0, 0.70, 1.0)
FEET_BOX = (0.22, 0.0, 0.78, 1.0)


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def crop_box(im, box):
    w, h = im.size
    x0, y0, x1, y1 = box
    return im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))


def diff_cell(a, b, thresh=28):
    """違いの行のこま：後のこまを薄い灰にし、前と違う画素（揺れで動いた所）を赤で塗る"""
    A = np.asarray(a, np.int16)
    B = np.asarray(b, np.int16)
    mask = np.abs(A - B).max(axis=2) > thresh
    g = np.asarray(b.convert('L'), np.float32) * 0.45 + 120
    out = np.repeat(g[:, :, None], 3, axis=2)
    out[mask] = (226, 40, 64)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def strip(folder, name, box, cell_h, title):
    frames = {m: [Image.open(os.path.join(folder, f'haru_{name}_{m}_{k}.png')).convert('RGB') for k in range(6)]
              for m in ('off', 'on')}
    c0 = crop_box(frames['off'][0], box)
    cw = int(c0.width * cell_h / c0.height)
    label_w = 150
    head = 46
    sheet = Image.new('RGB', (label_w + cw * 6, head + 26 + cell_h * 3 + 12), (245, 243, 238))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), 'ハルの 2 次の動き：' + title, fill=(30, 30, 30), font=font(24))
    for k in range(6):
        d.text((label_w + k * cw + cw // 2 - 22, head + 2), f'{k * 0.1:.1f} 秒', fill=(60, 60, 60), font=font(18))
    cells = {}
    for r, m in enumerate(('off', 'on', 'diff')):
        y = head + 26 + r * (cell_h + 6)
        label = ROWS[m]
        d.text((10, y + cell_h // 2 - 30), label[0], fill=(20, 20, 20), font=font(26))
        for i, line in enumerate(label[1:]):
            d.text((10, y + cell_h // 2 + 4 + i * 19), line, fill=(80, 80, 80), font=font(15))
        for k in range(6):
            if m == 'diff':
                c = diff_cell(cells[('off', k)], cells[('on', k)])
            else:
                c = crop_box(frames[m][k], box).resize((cw, cell_h), Image.LANCZOS)
                cells[(m, k)] = c
            sheet.paste(c, (label_w + k * cw, y))
            d.rectangle((label_w + k * cw, y, label_w + (k + 1) * cw - 1, y + cell_h - 1), outline=(200, 196, 188))
    return sheet


def still(folder, name):
    ims = {m: Image.open(os.path.join(folder, f'haru_{name}_{m}.png')).convert('RGB') for m in ('off', 'on')}
    feet = {m: Image.open(os.path.join(folder, f'haru_{name}_{m}_feet.png')).convert('RGB') for m in ('off', 'on')}
    ch = 560
    tiles = []
    for m in ('off', 'on'):
        a = crop_box(ims[m], FULL_BOX)
        a = a.resize((int(a.width * ch / a.height), ch), Image.LANCZOS)
        b = crop_box(feet[m], FEET_BOX)
        b = b.resize((int(b.width * ch / b.height), ch), Image.LANCZOS)
        tiles.append((a, b))
    head = 46
    sheet = Image.new('RGB', (sum(a.width + b.width + 8 for a, b in tiles) + 10, head + 30 + ch + 8), (245, 243, 238))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), '足の接地：' + STILL_TITLES[name], fill=(30, 30, 30), font=font(24))
    x = 6
    for (a, b), m in zip(tiles, ('off', 'on')):
        d.text((x + 4, head + 2), '前（足の接地なし）' if m == 'off' else '後（足の接地あり：腰を下げ、各足を下の面に）',
               fill=(20, 20, 20), font=font(19))
        sheet.paste(a, (x, head + 30))
        sheet.paste(b, (x + a.width + 2, head + 30))
        x += a.width + b.width + 8
    return sheet


def save(img, path, limit=400_000):
    q = 88
    while True:
        img.save(path, quality=q, optimize=True)
        if os.path.getsize(path) <= limit or q <= 50:
            break
        q -= 6
    print(path, os.path.getsize(path) // 1000, 'KB', 'q', q, img.size)


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    src, out = pos[0], pos[1]
    pouch = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--pouch=')), None)
    os.makedirs(out, exist_ok=True)
    for nm in ('runstop', 'landing', 'dash'):
        if os.path.exists(os.path.join(src, f'haru_{nm}_on_0.png')):
            save(strip(src, nm, STRIP_BOX, 330, TITLES[nm]), os.path.join(out, f'strip_{nm}.jpg'))
    if pouch:
        save(strip(pouch, 'runstop', POUCH_BOX, 330, POUCH_TITLE), os.path.join(out, 'strip_pouch.jpg'))
    for nm in ('stairs', 'ramp'):
        if os.path.exists(os.path.join(src, f'haru_{nm}_off.png')):
            save(still(src, nm), os.path.join(out, f'still_{nm}.jpg'))


if __name__ == '__main__':
    main()
