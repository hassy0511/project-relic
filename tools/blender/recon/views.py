"""多視点の絵（正面・背面・右真横・右前斜め）の「カメラ」と「外形のマスク」。

ハルの 3D を、画家（Codex）が描いた多視点の絵から起こす（再構築する）ための共通の土台。
絵は正投影に近いので、各視点を「水平な向きの正投影カメラ」として扱う。

■ 座標の約束（tools/blender/lib/common.py と同じ）
  Blender は Z が上。キャラクターの正面は -Y、本人の左が +X。
  身長 1.55m（髪の先〜靴底）、靴底が z=0、胴の中心が x=0, y=0。

■ カメラの表し方
  方位角 azimuth（度）：キャラクターから見たカメラの位置の向き。
      0 = 正面（カメラは -Y 側）、90 = 本人の右（-X 側）、180 = 背面。右前斜めは 45 前後。
  視線 d  = (sin a, cos a, 0)         カメラからキャラクターへ向かう単位ベクトル
  画像の右 r = d × Z = (cos a, -sin a, 0)
  画像の上 = +Z
  世界の点 p が写る画素：u = u0 + ppm * (p・r)、v = v0 - ppm * p.z
      （u, v は画素の左上を 0 とする連続座標。画素 i は [i, i+1) を占める）
  u0, v0 は世界の原点 (0,0,0)（胴の中心の足元）が写る位置、ppm は 1m あたりの画素数。

  左右反転の「仮想の視点」（mirror=True）：点 p を x→-x に映してから元の絵で調べる。
  右前斜めの絵を反転すると、左前斜め（方位角 -a）から見た絵の代わりになる
  （体が左右対称だと仮定できる部分だけに使うこと。carve.py を参照）。

■ 較正の結果（build/recon/calib.json、carve.py で追い込んだもの）
  views.<視点>: azimuth_deg, direction, image_right, image_up, pixels_per_meter, u0, v0
  右前斜めは発注では 45 度だが、絵は約 31 度で描かれている（左右の手足の間隔の比から。carve.py を参照）。
  refine：追い込みの記録。silhouette_iou_final_mesh：最終メッシュの外形の一致。

■ 使い方（.venv-blender の python で動かす）
  python tools/blender/recon/views.py      元の絵の取り出し・マスク・最初の較正（build/recon/calib.json）
  python tools/blender/recon/carve.py      較正の追い込み・視体積・面・UV・書き出し・確認画像
"""
from __future__ import annotations

import json
import math
import os
import subprocess
from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
WORK = os.path.join(REPO, 'build', 'recon')
SRC = os.path.join(WORK, 'src')
ART_REF = 'origin/art/w1-haru3d'
ART_DIR = 'art/concepts/W1_haru_3d'
HEIGHT = 1.55
IMG = 2048

# 全身の 4 枚。azimuth は最初の値（右前斜めは較正で追い込む）
VIEWS: dict[str, dict] = {
    'front': {'file': 'haru_3d_front.png', 'azimuth': 0.0},
    'back': {'file': 'haru_3d_back.png', 'azimuth': 180.0},
    'side_right': {'file': 'haru_3d_side_right.png', 'azimuth': 90.0},
    'three_quarter': {'file': 'haru_3d_three_quarter.png', 'azimuth': 45.0},
}
SOURCE_FILES = [
    'haru_3d_front.png', 'haru_3d_back.png', 'haru_3d_side_right.png', 'haru_3d_three_quarter.png',
    'haru_face_front.png', 'haru_face_expressions.png', 'spark_gun_side.png', 'spark_gun_3d.png',
    'light_blade_gauntlet.png', 'spec_haru_3d.md',
]


# ---------------------------------------------------------------- 元の絵

def extract_sources() -> None:
    """絵のブランチから build/recon/src へ取り出す（取り出し済みなら何もしない）"""
    os.makedirs(SRC, exist_ok=True)
    for f in SOURCE_FILES:
        dst = os.path.join(SRC, f)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            continue
        data = subprocess.run(['git', '-C', REPO, 'show', f'{ART_REF}:{ART_DIR}/{f}'], check=True,
                              capture_output=True).stdout
        with open(dst, 'wb') as fp:
            fp.write(data)


def load_rgba(view: str) -> np.ndarray:
    """視点の絵を (H, W, 4) の uint8 で読む"""
    return np.asarray(Image.open(os.path.join(SRC, VIEWS[view]['file'])).convert('RGBA'))


def silhouette(rgba: np.ndarray, threshold: int = 128, min_hole: int = 30) -> np.ndarray:
    """外形のマスク。不透明度が半分以上の画素のうち、いちばん大きい塊だけを残す。

    背景に散った薄い色の点（生成のにじみ）は不透明度が低いので自然に落ちる。
    塊の中の小さな穴（min_hole 画素未満）はアンチエイリアスの欠けとみなして埋める。
    """
    m = rgba[..., 3] >= threshold
    lab, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
    holes = ndi.binary_fill_holes(m) & ~m
    lab, n = ndi.label(holes)
    if n:
        sizes = ndi.sum(holes, lab, range(1, n + 1))
        small = np.isin(lab, np.nonzero(sizes < min_hole)[0] + 1)
        m = m | small
    return m


def mask_path(view: str) -> str:
    return os.path.join(WORK, f'mask_{view}.png')


def save_mask(view: str, m: np.ndarray) -> None:
    Image.fromarray((m * 255).astype(np.uint8)).save(mask_path(view))


def load_mask(view: str) -> np.ndarray:
    return np.asarray(Image.open(mask_path(view))) > 127


def runs(row: np.ndarray) -> list[tuple[int, int]]:
    """1 行の真偽の並びを [始め, 終わり) の区間の一覧にする"""
    d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
    return list(zip(np.nonzero(d == 1)[0].tolist(), np.nonzero(d == -1)[0].tolist()))


# ---------------------------------------------------------------- カメラ

@dataclass
class Cam:
    """水平な向きの正投影カメラ。mirror=True は左右反転の仮想の視点"""
    name: str
    azimuth: float
    ppm: float
    u0: float
    v0: float
    mirror: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def d(self) -> np.ndarray:
        a = math.radians(self.azimuth)
        return np.array([math.sin(a), math.cos(a), 0.0])

    @property
    def r(self) -> np.ndarray:
        a = math.radians(self.azimuth)
        return np.array([math.cos(a), -math.sin(a), 0.0])

    def project(self, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """世界の点 (..., 3) → 画素の連続座標 (u, v)"""
        x, y, z = p[..., 0], p[..., 1], p[..., 2]
        if self.mirror:
            x = -x
        r = self.r
        return self.u0 + self.ppm * (x * r[0] + y * r[1]), self.v0 - self.ppm * z

    def u_of(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """水平面の座標 (x, y) → 画素の列 u（連続値）"""
        if self.mirror:
            x = -x
        r = self.r
        return self.u0 + self.ppm * (x * r[0] + y * r[1])

    def v_of(self, z: np.ndarray) -> np.ndarray:
        return self.v0 - self.ppm * z

    def mirrored(self) -> 'Cam':
        """左右反転した仮想の視点（方位角は -a と同じ見え方）"""
        return Cam(self.name + '_mirror', self.azimuth, self.ppm, self.u0, self.v0, mirror=not self.mirror)

    def blender_camera(self) -> dict:
        """Blender の正投影カメラを置くための値（確認画像用）。画像の中心が見る点"""
        # 画像の中心 (IMG/2, IMG/2) に写る世界の点（視線上の奥行きは 0）
        if self.mirror:
            raise ValueError('左右反転の仮想の視点は、絵と同じ画素には描けない（方位角 -a で描くこと）')
        cu, cv = IMG / 2, IMG / 2
        h = (cu - self.u0) / self.ppm
        z = (self.v0 - cv) / self.ppm
        d, r = self.d, self.r
        center = r * h + np.array([0, 0, z])
        return {'center': center.tolist(), 'direction': d.tolist(), 'right': r.tolist(),
                'ortho_scale': IMG / self.ppm}

    def to_json(self) -> dict:
        return {
            'azimuth_deg': self.azimuth,
            'direction': [round(float(c), 6) for c in self.d],
            'image_right': [round(float(c), 6) for c in self.r],
            'image_up': [0.0, 0.0, 1.0],
            'pixels_per_meter': self.ppm,
            'u0': self.u0,
            'v0': self.v0,
            'image_size': [IMG, IMG],
            'file': VIEWS[self.name]['file'] if self.name in VIEWS else None,
            **self.extra,
        }


CALIB_PATH = os.path.join(WORK, 'calib.json')
CALIB_NOTE = ('正投影カメラ。世界（Blender、Z 上、正面 -Y、本人の左 +X、靴底 z=0）の点 p は '
              'u = u0 + pixels_per_meter * dot(p, image_right)、v = v0 - pixels_per_meter * p.z の画素に写る。'
              'u, v は画像の左上を 0 とする連続座標（画素 i は [i, i+1)）。direction はカメラからキャラクターへの向き。')


def save_calib(cams: dict[str, Cam], extra: dict | None = None) -> None:
    os.makedirs(WORK, exist_ok=True)
    out = {'note': CALIB_NOTE, 'height_m': HEIGHT, 'views': {k: c.to_json() for k, c in cams.items()}}
    if extra:
        out.update(extra)
    with open(CALIB_PATH, 'w') as fp:
        json.dump(out, fp, indent=2, ensure_ascii=False)


def load_calib() -> dict[str, Cam]:
    with open(CALIB_PATH) as fp:
        data = json.load(fp)
    cams = {}
    for k, v in data['views'].items():
        cams[k] = Cam(k, v['azimuth_deg'], v['pixels_per_meter'], v['u0'], v['v0'])
    return cams


# ---------------------------------------------------------------- 最初の較正

def _vertical(m: np.ndarray) -> tuple[float, float]:
    """外形の上端と下端（画素の境目の連続座標）"""
    rows = np.nonzero(m.any(1))[0]
    return float(rows[0]), float(rows[-1] + 1)


def _center_of_runs(m: np.ndarray, rows: range, pick) -> float:
    """指定した行で pick が選んだ区間の中点の平均"""
    cs = []
    for y in rows:
        rs = runs(m[y])
        sel = pick(rs)
        if sel:
            cs.append((sel[0][0] + sel[-1][1]) / 2)
    return float(np.median(cs))


def initial_calib(masks: dict[str, np.ndarray]) -> dict[str, Cam]:
    """絵の外形から最初の較正を作る。

    高さ：各絵の外形の上端〜下端を 1.55m とする（ppm, v0）。
    正面の u0：両脚の中心の中点（膝下〜足首の行）。x=0 を体の左右の中心に置く。
    背面の u0：正面の外形を左右反転して最もよく重なる位置。
    右真横の u0：胴（胸〜腰）の前後の中点。
    右前斜めの u0：脚の 2 本の中点（carve.py で視体積と重ねて追い込む）。
    """
    cams: dict[str, Cam] = {}
    for name, m in masks.items():
        top, bottom = _vertical(m)
        ppm = (bottom - top) / HEIGHT
        cams[name] = Cam(name, VIEWS[name]['azimuth'], ppm, IMG / 2, bottom)

    def two_legs(rs):
        rs = [r for r in rs if r[1] - r[0] > 40]
        return rs if len(rs) == 2 else None

    f = cams['front']
    leg_rows = range(int(f.v_of(0.30)), int(f.v_of(0.12)), 4)
    f.u0 = _center_of_runs(masks['front'], leg_rows, two_legs)
    tq = cams['three_quarter']
    tq.u0 = _center_of_runs(masks['three_quarter'], leg_rows, two_legs)

    # 背面：背面の画素 u は x = (b - u) / ppm。正面ではその x は f + (b - u) に写る。
    # よって背面を「正面の見え方」に並べ直すと F'(u) = B(b + f - u)。これが正面と最もよく重なる b を探す
    fm, bm = masks['front'], masks['back']
    cols = np.arange(IMG) + 0.5
    best = None
    for s2 in range(-120, 121):
        b = f.u0 + s2 / 2
        src = np.floor(b + f.u0 - cols).astype(int)
        ok = (src >= 0) & (src < IMG)
        as_front = np.zeros_like(bm)
        as_front[:, ok] = bm[:, src[ok]]
        iou = (as_front & fm).sum() / (as_front | fm).sum()
        if best is None or iou > best[0]:
            best = (iou, b)
    cams['back'].u0 = best[1]
    cams['back'].extra['mirror_iou_vs_front'] = round(float(best[0]), 4)

    s = cams['side_right']
    torso_rows = range(int(s.v_of(1.02)), int(s.v_of(0.85)), 4)
    s.u0 = _center_of_runs(masks['side_right'], torso_rows, lambda rs: [max(rs, key=lambda r: r[1] - r[0])])
    return cams


def main() -> None:
    extract_sources()
    masks = {}
    for v in VIEWS:
        m = silhouette(load_rgba(v))
        save_mask(v, m)
        masks[v] = m
        print(f'{v}: {int(m.sum())} px, rows {_vertical(m)}')
    cams = initial_calib(masks)
    save_calib(cams, {'stage': 'initial'})
    for k, c in cams.items():
        print(k, json.dumps(c.to_json(), ensure_ascii=False))


if __name__ == '__main__':
    main()
