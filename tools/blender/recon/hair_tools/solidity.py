"""Silhouette 'roundness' per view: solidity = area / convex-hull area (1 = convex blob; spiky outlines are lower) and
outline length / sqrt(area) (higher = more jagged), for the drawing and for render dirs, above z 1.25 (top view: within 0.2 m of the head axis).
usage: solidity.py dir1 [dir2 ...]"""
import os, sys
import numpy as np
from PIL import Image
from scipy.spatial import ConvexHull
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align import ART, CEN, T, W  # noqa: E402
ZC = 1.25
def keep_mask(vn, N):
    pr = N / W; ch, cv = CEN[vn]
    if vn == 'top':
        yy, xx = np.mgrid[:N, :N]
        return ((xx + 0.5 - N / 2) ** 2 + (yy + 0.5 - N / 2) ** 2) < (0.2 * pr) ** 2
    rows = cv - (np.arange(N) + 0.5 - N / 2) / pr
    return np.broadcast_to((rows > ZC)[:, None], (N, N))
def art_mask(vn, N):
    fn, ppm, ho, zo = T[vn]; ch, cv = CEN[vn]; pr = N / W
    dr = Image.open(os.path.join(ART, fn)).convert('RGBA'); a = ppm / pr
    w = dr.transform((N, N), Image.AFFINE, (a, 0, (ch - N / 2 / pr - ho) * ppm, 0, a, (zo - cv - N / 2 / pr) * ppm), resample=Image.BILINEAR)
    return np.asarray(w)[..., 3] > 128
def stats(m):
    m = ndi.binary_opening(m, iterations=1)
    lab, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n + 1)); m = lab == (1 + int(np.argmax(sizes)))
    ys, xs = np.nonzero(m)
    pts = np.stack([xs, ys], 1).astype(float)
    hull = ConvexHull(pts)
    area = m.sum(); sol = area / hull.volume
    edge = m & ~ndi.binary_erosion(m)
    jag = edge.sum() / np.sqrt(area)
    return sol, jag
dirs = sys.argv[1:]
for vn in ['side_right', 'back', 'front_right45', 'top']:
    N = 768
    k = keep_mask(vn, N)
    s = [f'{vn:14s}']
    a = art_mask(vn, N) & k
    sol, jag = stats(a); s.append(f'drawing sol {sol:.3f} jag {jag:.2f}')
    for d in dirs:
        im = Image.open(os.path.join(d, vn + '.png')).convert('RGBA').resize((N, N))
        m = (np.asarray(im)[..., 3] > 128) & k
        sol, jag = stats(m); s.append(f'{os.path.basename(d)} sol {sol:.3f} jag {jag:.2f}')
    print(' | '.join(s))
