"""ハルの頭の拡大の絵と、頭の正射影の画像（hair_preview.py）を重ねるための値（H1、2026-11）。

絵は形の段が取り出した build/recon/src/（無ければ views の段を先に）。画像は中心 CEN（真横は (y, z)、背面・斜め・正面は (x, z)、
真上は (x, y)）、幅 W（m）の正方形。絵の 1 m あたりの画素 ppm と、絵の左上の画素が指す世界の位置 (横の値, 高さ) の表 T：
  横の値 = 絵の左の端の世界の値（真横は y、ほかは x。真上は x）、高さ = 絵の上の端の世界の z（真上は y）
"""
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
ART = os.path.join(REPO, 'build', 'recon', 'src')
W = 0.56
CEN = {'side_right': (-0.035, 1.37), 'back': (0.0, 1.37), 'front_right45': (-0.02475, 1.37), 'top': (0.0, 0.035),
       'front': (0.0, 1.37)}
T = {'side_right': ('haru_head_side_right.png', 4425, -0.24278, 1.57904),
     'back': ('haru_head_back.png', 4425, -0.23096, 1.57904),
     'front_right45': ('haru_head_front_right45.png', 4325, -0.23604, 1.5859),
     'top': ('haru_head_top.png', 4388, -0.23336, 0.2587),
     'front': ('haru_3d_front.png', 1161.29, -0.88997, 1.65678)}


def warp(vn: str, N: int):
    """絵 vn を N×N の画像の枠（中心 CEN、幅 W）へ移した RGBA の画像"""
    from PIL import Image
    fn, ppm, ho, zo = T[vn]
    ch, cv = CEN[vn]
    pr = N / W
    dr = Image.open(os.path.join(ART, fn)).convert('RGBA')
    a = ppm / pr
    return dr.transform((N, N), Image.AFFINE, (a, 0, (ch - N / 2 / pr - ho) * ppm, 0, a, (zo - cv - N / 2 / pr) * ppm),
                        resample=Image.BILINEAR)
