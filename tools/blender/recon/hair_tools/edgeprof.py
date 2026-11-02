"""Side-view back edge (y) per height for the drawing and render dirs: edgeprof.py dir1 [dir2 ...]"""
import numpy as np, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align import ART, CEN, T, W  # noqa: E402
ch, cv = CEN['side_right']; fn, ppm, ho, zo = T['side_right']
N = 768; pr = N / W
dr = Image.open(os.path.join(ART, fn)).convert('RGBA'); a = ppm / pr
w = dr.transform((N, N), Image.AFFINE, (a, 0, (ch - N / 2 / pr - ho) * ppm, 0, a, (zo - cv - N / 2 / pr) * ppm), resample=Image.BILINEAR)
ms = {'drawing': np.asarray(w)[..., 3] > 128}
for d in sys.argv[1:]:
    ms[os.path.basename(d.rstrip('/'))] = np.asarray(Image.open(os.path.join(d, 'side_right.png')).convert('RGBA').resize((N, N)))[..., 3] > 128
print('z     ' + ' '.join(f'{k:>8s}' for k in ms))
for z in np.arange(1.56, 1.24, -0.01):
    r = int(round((cv - z) * pr + N / 2 - 0.5))
    vals = []
    for k, m in ms.items():
        xs = np.nonzero(m[r])[0]
        vals.append(f'{-(ch - W / 2 + (xs.min() + 0.5) / pr):8.3f}' if len(xs) else '     -  ')
    print(f'{z:.2f} ' + ' '.join(vals))
