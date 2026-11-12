"""絵に cm の格子を重ねた画像を作る（寸法を読むため）。
  python3 tools/blender/trial_f/measure.py <絵の名前> <出力> [x0 x1 z0 z1] [--head]
全身の絵：頭頂 125 行・足裏 1922 行 = 155 cm、中心 1024 列。"""
import sys
from PIL import Image, ImageDraw, ImageFont

ART = 'build/art_f/'
TOP, SOLE, CX = 125, 1922, 1024
PX_PER_CM = (SOLE - TOP) / 155.0


def grid(name, out, x0=-60, x1=60, z0=0, z1=160, zoom=1.0, ppc=PX_PER_CM, sole=SOLE, cx=CX, bg=(128, 128, 136)):
    im = Image.open(ART + name + '.png').convert('RGBA')
    b = Image.new('RGBA', im.size, bg + (255,))
    b.alpha_composite(im)
    im = b.convert('RGB')
    box = (int(cx + x0 * ppc), int(sole - z1 * ppc), int(cx + x1 * ppc), int(sole - z0 * ppc))
    im = im.crop(box)
    s = zoom
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    d = ImageDraw.Draw(im, 'RGBA')
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except Exception:
        f = ImageFont.load_default()
    for x in range(int(x0), int(x1) + 1):
        px = (x - x0) * ppc * s
        if x % 5 == 0:
            d.line([(px, 0), (px, im.height)], fill=(0, 255, 255, 150 if x % 10 == 0 else 70), width=1)
            if x % 10 == 0:
                d.text((px + 2, 2), str(x), fill=(255, 255, 0, 255), font=f)
        else:
            d.line([(px, 0), (px, im.height)], fill=(0, 0, 0, 28), width=1)
    for z in range(int(z0), int(z1) + 1):
        py = (z1 - z) * ppc * s
        if z % 5 == 0:
            d.line([(0, py), (im.width, py)], fill=(0, 255, 255, 150 if z % 10 == 0 else 70), width=1)
            d.text((2, py + 1), str(z), fill=(255, 255, 0, 255), font=f)
        else:
            d.line([(0, py), (im.width, py)], fill=(0, 0, 0, 28), width=1)
    im.save(out, quality=88)
    print(out, im.size)


if __name__ == '__main__':
    a = sys.argv[1:]
    nums = [float(v) for v in a[2:6]] if len(a) >= 6 else [-60, 60, 0, 160]
    zoom = float(a[6]) if len(a) > 6 else 1.0
    grid(a[0], a[1], *nums, zoom=zoom)
