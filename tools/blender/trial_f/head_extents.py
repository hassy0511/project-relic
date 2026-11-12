"""haru_f：頭の拡大の絵とモデルの輪郭を、高さごとの左右の端で比べる（cm。モデルの座標）。
  python3 tools/blender/trial_f/head_extents.py      （先に build.py --head で build/f/render/head_*.png を作る）"""
import numpy as np
from PIL import Image

PPM = 40.7 / 0.0098
ZC = 1.31 + (1151.3 - 1024) / PPM
SPAN = 2048 / PPM
ART = {'front': 'haru_face_front', 'right': 'haru_head_side_right', 'back': 'haru_head_back'}


def extents(alpha, size):
    rows = {}
    for z_cm in range(156, 117, -2):
        py = int(round((ZC + SPAN / 2 - z_cm / 100.0) / SPAN * size))
        if not (0 <= py < size):
            continue
        xs = np.where(alpha[py] > 128)[0]
        if len(xs) == 0:
            rows[z_cm] = None
        else:
            rows[z_cm] = ((xs.min() - size / 2) / size * SPAN * 100, (xs.max() - size / 2) / size * SPAN * 100)
    return rows


def main():
    for view, art in ART.items():
        ren = np.array(Image.open('build/f/render/head_%s.png' % view).convert('RGBA').getchannel('A'))
        size = ren.shape[0]
        a = np.array(Image.open('build/art_f/%s.png' % art).convert('RGBA').resize((size, size), Image.LANCZOS).getchannel('A'))
        ea, er = extents(a, size), extents(ren, size)
        print('== %s（左の端・右の端 cm：絵 → モデル（差））' % view)
        for z in ea:
            if ea[z] is None and er[z] is None:
                continue
            fa = '%6.1f %6.1f' % ea[z] if ea[z] else '   --     --'
            fr = '%6.1f %6.1f' % er[z] if er[z] else '   --     --'
            d = ''
            if ea[z] and er[z]:
                d = '   (%+5.1f %+5.1f)' % (er[z][0] - ea[z][0], er[z][1] - ea[z][1])
            print('  z %3d  %s  →  %s%s' % (z, fa, fr, d))


if __name__ == '__main__':
    main()
