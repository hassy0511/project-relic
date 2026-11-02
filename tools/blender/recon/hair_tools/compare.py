"""Sheet: per view, the drawing warped to the render frame | render with the drawing's outline (red).
usage: compare.py render_dir out.jpg [views] [tile]"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align import ART, CEN, T, W  # noqa: E402
rdir, out = sys.argv[1], sys.argv[2]
views = sys.argv[3].split(',') if len(sys.argv) > 3 else ['side_right', 'back', 'front_right45', 'top', 'front']
tile = int(sys.argv[4]) if len(sys.argv) > 4 else 420
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
cols = []
for vn in views:
    rr = Image.open(os.path.join(rdir, vn + '.png')).convert('RGBA')
    N = rr.size[0]
    pr = N / W
    fn, ppm, ho, zo = T[vn]
    ch, cv = CEN[vn]
    dr = Image.open(os.path.join(ART, fn)).convert('RGBA')
    a = ppm / pr
    bx = (ch - N / 2 / pr - ho) * ppm
    by = (zo - cv - N / 2 / pr) * ppm
    warped = dr.transform((N, N), Image.AFFINE, (a, 0, bx, 0, a, by), resample=Image.BILINEAR)
    bg = Image.new('RGBA', (N, N), (205, 205, 205, 255))
    w2 = bg.copy(); w2.alpha_composite(warped)
    r2 = bg.copy(); r2.alpha_composite(rr)
    wa = np.asarray(warped)[..., 3] > 128
    if vn == 'front':
        # only the head of the full-body art: cut below the chin line
        yy = np.arange(N)[:, None]
        wa = wa & (yy < N / 2 + 0.17 * pr)
    edge = wa & ~ndi.binary_erosion(wa, iterations=max(1, N // 320))
    b = np.asarray(r2.convert('RGB')).copy(); b[edge] = (230, 0, 0)
    pair = np.concatenate([np.asarray(w2.convert('RGB')), b], 1)
    im = Image.fromarray(pair).resize((tile * 2, tile))
    ImageDraw.Draw(im).text((6, 4), vn + ' (drawing | model + drawing outline)', fill=(0, 0, 0), font=font)
    cols.append(np.asarray(im))
rows = [np.concatenate(cols[i:i + 2], 1) if i + 1 < len(cols) else np.concatenate([cols[i], np.full_like(cols[i], 255)], 1)
        for i in range(0, len(cols), 2)]
Image.fromarray(np.concatenate(rows, 0)).save(out, quality=82)
print(out)
