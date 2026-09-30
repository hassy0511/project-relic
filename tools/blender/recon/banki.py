"""番機 5 種（子番機・歩哨型・突撃型・盾型・浮遊型）を、Codex の手描きの絵（r2）から部品ごとの 3D にする。

  npm run banki:build
  （= .venv-blender/bin/python tools/blender/recon/banki.py --all --review）
  .venv-blender/bin/python tools/blender/recon/banki.py --type sentry [--review]
  絵は build/banki/r2/ に置く。なければ絵のブランチ（ART_REF）から git show で取り出す（_r2 の絵だけを使う）。

できるもの
  godot/assets/models/banki_<型>.glb   モデル（部品の階層・面ごとの平らな材質 白磁・真鍮・黒鉛・発光の材質 2 つ。テクスチャなし）
  build/banki/tex/banki_<型>.png      BANKI_PAINT=bake のときだけ：焼いたテクスチャ
  build/banki/review/                 --review のとき：絵と Cycles の画像の比較（正面・真横・背面・上面・斜め）と外形の重なり

■ 既定は banki_parts.py（閂と同じく、絵で測った寸法で部品をきれいな形から組む。docs/art_orders/W2_番機3D化の結果.md の 3d）。
  以下の視体積の方式は BANKI_MODEL=hull のとき（比べる用）。

■ やり方（ナゴミの「数式の部品」とハルの「視体積＋投影」の間）
  番機の絵は、白磁の板・真鍮の縁・黒鉛色の関節が細かく入り組んでいて、数式の部品で組むと手間が大きい。
  一方で全体の形は丸い卵・楔・円盤なので、正面と真横の外形を掛け合わせるだけでほぼ形になる。そこで：
  1. 形（視体積）：正面・真横（型によって真上も）の絵の外形を、ボクセルの格子（最大の寸法の 1/170）で掛け合わせる。
     2 枚の外形だけだと断面が四角くなるので、各行で「正面の外形の区間」と「真横の外形の区間」に内接する
     超楕円（|u|^p + |v|^p ≤ 1、p は型ごと）で角を落とす。真上の絵は縮尺が正面・真横と合わない
     （Codex の絵は正確な図面ではない）ので、使う型（突撃型・浮遊型）では外接の箱を正面の幅と真横の奥行きに合わせる。
  2. 部品：ボクセルを「部品の規則」（型ごとの PARTS。世界の座標 cm の条件、先に当てはまったもの）で分け、
     部品ごとに少しぼかしてから marching cubes で面にし、Blender の Decimate で三角形を減らす。
     部品の境は少し隙間が空く（板の継ぎ目に見える）。原点は回転軸（PIVOT。'top' は部品の上端の断面の重心）、
     ローカル +X が回転軸の向き（ナゴミと同じ約束。Godot で「元の姿勢 * Basis(RIGHT, 角度)」と回す）。
  3. 色（既定 = 領域で塗る。paint_regions）：絵は「どこが何色か」を決めるだけで画素は写さない。頂点ごとに見えている視点の色の割合の票 →
     メッシュのつながりでならす・小さな塊を消す・真鍮は帯か部品まるごとだけ → 色の境で三角形を切ってなめらかな線にし、面ごとの材質にする
     （閂・ナゴミと同じ平らな色。R_* の定数。docs/art_orders/W2_番機3D化の結果.md の 3c）。以下は BANKI_PAINT=bake の従来の方式。
     色（清書）：黒鉛は「関節（回転軸）のまわり・関節の部品（susp・wheel・muzzle）・部品の境の近く・型ごとの暗い領域」だけ、真鍮は絵の帯の欠けを埋めて
     小さな塊を消したもの、ほかは白磁（部品ごと・関節ごとに決める。JOINT_*・BRASS_*・DARK_*）。
     もとになる投影の色：全部品をまとめて UV を開き（Smart UV Project）、各テクセルに、正面・背面・真横（左右）・真上の絵の色を、
     その視点から見えるか（奥行き）× 外形の内側か × 面の向き^3 の重みで混ぜて焼く（texture.py と同じ考えの小さな版）。
     どの視点も見ていない所（真下など）は、3D で一番近い色の付いたテクセルの色。琥珀色（センサー・核）は暗い硝子の色に置き換える。
  4. 発光（sensor・core）：絵の琥珀色の画素を、その視点の向きから形の表面へ落として（Blender の BVH の光線）、表面から
     少し浮かせた薄い板にする。材質 banki_sensor・banki_core は別なので、Godot で色（通常 #FFBC52・警戒 #E26A4A・消灯）を
     別々に変えられる。
  5. 車輪（突撃型）は回るので、視体積ではなく円柱でつくる（視体積の車輪の所は削る）。

■ 座標（Blender、cm で計算して m で書き出す）
  原点 = 足もと（地面）の中心。正面は -Y、上は +Z、正面の絵の右（本人の左）は +X。glTF（Godot）では正面 +Z、上 +Y。
  絵の向き：Codex の「右側面」の絵は型によって向きが違う（歩哨型は顔が左＝+X から見た絵、子番機・盾型・浮遊型は顔が右＝
  -X から見た絵）。突撃型は spec の「核は本人の右」に合わせるため、側面と斜めの絵を左右反転して使う（VIEWS の flip）。
  突撃型は絵の縮尺（高さ 120cm）だと全長 230cm になるので、前後だけ Y_STRETCH 倍して spec の全長 200cm にする。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time

import numpy as np
from scipy import ndimage as ndi

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
WORK = os.path.join(REPO, 'build', 'banki')
SRC = os.path.join(WORK, 'r2')
MODELS = os.path.join(REPO, 'godot', 'assets', 'models')
ART_REF = 'origin/art/w2-banki:art/concepts/W2_banki'
IMG = 2048
UV_ANGLE = float(os.environ.get("BANKI_UV_ANGLE", 80))

COLORS = {'shell': '#F3E9D2', 'brass': '#A98749', 'dark': '#444641', 'amber': '#FFBC52', 'off': '#302F2B'}

# ---------------------------------------------------------------- 型ごとの設定
# rows：全身の絵の上端・下端の行（spec_banki_3d_r2.md の実測）。height：実寸の全高 cm（下端〜上端）。
# side：形に使う側面の絵と、その絵を見たカメラの側（+1 = +X から、-1 = -X から）と左右反転。
# views_extra：色だけに使う側面（左右の違う型は両側。左右対称の型は side の絵を反対側から見た鏡の視点を自動で足す）。
# top：真上の絵を形に使うか。p：断面の超楕円の指数（大きいほど四角い）。tris：三角形の目安（発光の板を除く）。
# PARTS：(名前, 親（'root' は一番上の空の物体）, 条件 f(x,y,z)（cm、世界）, 回転軸の位置（'top' か (x,y,z) cm）, 回転軸の向き)。上から順に当てはめ、
#        どれにも当たらないボクセルは 'body'（原点 = BODY_PIVOT）。
# DECALS：(名前, 絵, 世界の箱 ((x0,x1),(y0,y1),(z0,z1)) cm, 親)。発光の板。

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def _leg(side: str, sgn: float, bands, extra=None):
    """脚の部品（太もも・すね・足）：x の符号と高さの帯で分ける。bands = (股の高さ, 膝の高さ, 足首の高さ)"""
    hip, knee, ankle = bands
    ok = (lambda x, y, z: sgn * x > 0) if extra is None else (lambda x, y, z: (sgn * x > 0) & extra(x, y, z))
    return [
        (f'foot_{side}', f'shin_{side}', lambda x, y, z, ok=ok: ok(x, y, z) & (z < ankle), 'top', X),
        (f'shin_{side}', f'thigh_{side}', lambda x, y, z, ok=ok: ok(x, y, z) & (z < knee), 'top', X),
        (f'thigh_{side}', 'body', lambda x, y, z, ok=ok: ok(x, y, z) & (z < hip), 'top', X),
    ]


def _lobe(k: int, ang_deg: float):
    """浮遊型の葉：中心からの角度が ang_deg に一番近い扇（120 度ごと）で、ハブの外"""
    a0 = math.radians(ang_deg)

    def f(x, y, z):
        d = np.angle(np.exp(1j * (np.arctan2(y, x) - a0)))
        return (np.hypot(x, y) > 17.0) & (np.abs(d) < math.pi / 3) & (z > 15) & (z < 36)
    r = 17.0
    return (f'lobe_{k}', 'body', f, (r * math.cos(a0), r * math.sin(a0), 25.0),
            (-math.sin(a0), math.cos(a0), 0.0))


TYPES = {
    'mini': dict(
        name='子番機', height=30.0, rows=(144, 1904), center=1024,
        side=('side_right', -1, False), top=True, p=2.3, tris=3000,
        body_pivot=(0, 0, 12.0), joint_r=0.06, dark_zone=lambda x, y, z: (z > 7.0) & (z < 15.0), joints=['thigh_l', 'thigh_r', 'shin_l', 'shin_r', 'foot_l', 'foot_r'],
        parts=[
            ('horn_l', 'body', lambda x, y, z: (x > 5.5) & (z > 21.5), 'top', X),
            ('horn_r', 'body', lambda x, y, z: (x < -5.5) & (z > 21.5), 'top', X),
            *_leg('l', 1, (11.0, 5.2, 2.6)),
            *_leg('r', -1, (11.0, 5.2, 2.6)),
        ],
        decals=[('sensor', 'front', ((-9, 9), (-99, 0), (12, 19)), 'body'),
                ('core', 'back', ((-6, 6), (0, 99), (9, 14)), 'body')],
    ),
    'sentry': dict(
        name='歩哨型', height=110.0, rows=(144, 1904), center=1024,
        side=('side_right', 1, False), top=False, p=2.2, tris=5000,
        body_pivot=(0, 0, 47.0), joint_r=0.04,
        dark_zone=lambda x, y, z: (y < -4) & (z > 46) & (z < 74) & (np.abs(x) < 12),   # 正面の V の開口（砲口の奥）
        joints=['thigh_l', 'thigh_r', 'shin_l', 'shin_r', 'foot_l', 'foot_r'],
        parts=[
            ('spike', 'body', lambda x, y, z: z > 97.0, 'top', X),
            ('muzzle_cover', 'body', lambda x, y, z: (z > 46) & (z < 60) & (y < -5) & (np.abs(x) < 13), (0, -4, 48.0), X),
            *_leg('l', 1, (46.0, 31.0, 9.0)),
            *_leg('r', -1, (46.0, 31.0, 9.0)),
        ],
        decals=[('sensor', 'front', ((-15, 15), (-99, 0), (72, 82)), 'body'),
                ('core', 'back', ((-15, 15), (0, 99), (60, 97)), 'body')],
    ),
    'charger': dict(
        name='突撃型', height=120.0, rows=(564, 1484), center=1024, y_stretch=200.0 / 230.0,
        side=('side_right', -1, True), extra_sides=[('side_left', 1, True)], top=True, p=3.0, tris=6000,
        body_pivot=(0, 0, 30.0),
        # 車輪（円柱）：(名前, 親, 中心 cm（世界）, 半径, 幅)
        wheels=[('wheel_fl', 'susp_fl', (47, -28, 16.5), 16.0, 12.0), ('wheel_fr', 'susp_fr', (-47, -28, 16.5), 16.0, 12.0),
                ('wheel_rl', 'susp_rl', (47, 72, 16.5), 16.0, 12.0), ('wheel_rr', 'susp_rr', (-47, 72, 16.5), 16.0, 12.0)],
        # 箱（黒鉛色）：(名前, 親, 中心 cm（世界）, 大きさ cm)。衝角のレール（伸ばしたとき胴との間に見える）
        boxes=[('ram_rail', 'ram', (0, -61, 24), (12, 42, 8))],
        parts=[
            ('ram', 'body', lambda x, y, z: (y < -82) & (z < 60), (0, -82, 25.0), X),
            ('fin', 'body', lambda x, y, z: (z > 92) & (np.abs(x) < 9), 'top', X),
            ('core_cover', 'body', lambda x, y, z: (x < -22) & (y > -18) & (y < 30) & (z > 58) & (z < 86), (-22, 6, 86.0), (0, -1, 0)),
            ('susp_fl', 'root', lambda x, y, z: (x > 30) & (z < 42) & (np.abs(y + 28) < 26), (30, -28, 30.0), X),
            ('susp_fr', 'root', lambda x, y, z: (x < -30) & (z < 42) & (np.abs(y + 28) < 26), (-30, -28, 30.0), X),
            ('susp_rl', 'root', lambda x, y, z: (x > 30) & (z < 42) & (np.abs(y - 72) < 26), (30, 72, 30.0), X),
            ('susp_rr', 'root', lambda x, y, z: (x < -30) & (z < 42) & (np.abs(y - 72) < 26), (-30, 72, 30.0), X),
        ],
        decals=[('sensor', 'front', ((-25, 25), (-999, 0), (55, 75)), 'body'),
                ('core', 'side_right', ((-99, 0), (-30, 40), (35, 80)), 'body')],
    ),
    'shield': dict(
        name='盾型', height=180.0, rows=(144, 1904), center=1024,
        side=('side_left', 1, False), extra_sides=[('side_right', -1, False)], top=True, p=2.6, tris=8000,
        top_flip=True,
        side_split=(33.0, (-60.0, 4.0), (-8.0, 60.0)),   # x < 33cm は体（y < 4cm）、それより外は盾
        body_pivot=(0, 0, 95.0), joint_r=0.035,
        # 絵の暗い所を残す領域：腰・首・本人の左の肩（本人の右の肩と肘は関節の球）
        dark_zone=lambda x, y, z: ((z > 86) & (z < 104) & (np.abs(x) < 30)) | ((z > 128) & (z < 142) & (np.abs(x) < 20))
        | ((x > 16) & (x < 34) & (z > 118) & (z < 140)) | ((np.abs(x) > 34) & (z > 96) & (z < 112)),
        brass_min=0.16,
        joints=['thigh_l', 'thigh_r', 'shin_l', 'shin_r', 'foot_l', 'foot_r', 'upperarm_r', 'forearm_r', 'head', 'shield'],
        parts=[
            ('shield', 'body', lambda x, y, z: x > 33.0, (30, 5, 127.0), Z),
            ('head', 'body', lambda x, y, z: (z > 133) & (np.abs(x) < 19), (0, 0, 133.0), X),
            ('forearm_r', 'upperarm_r', lambda x, y, z: (x < -38) & (z < 104), (-52, 0, 104.0), X),
            ('upperarm_r', 'body', lambda x, y, z: (x < -38), (-42, 0, 130.0), X),
            *_leg('l', 1, (92.0, 52.0, 16.0)),
            *_leg('r', -1, (92.0, 52.0, 16.0)),
        ],
        decals=[('sensor', 'front', ((-15, 15), (-999, 0), (140, 155)), 'head'),
                ('core', 'back', ((-15, 15), (0, 999), (100, 150)), 'body')],
    ),
    'floater': dict(
        name='浮遊型', height=51.3, rows=(464, 1582), center=1024, px_per_cm=21.8,
        side=('side_right', -1, False), top=True, p=2.6, tris=5000,
        body_pivot=(0, 0, 25.0), brass_min=0.16, dark_zone=lambda x, y, z: (np.hypot(x, y) < 19.0) & (z < 38.0),
        parts=[
            ('crown', 'body', lambda x, y, z: (z > 37.5) & (np.hypot(x, y) < 14), (0, 8, 37.5), X),
            ('muzzle', 'body', lambda x, y, z: z < 12.5, (0, 0, 12.5), X),
            _lobe(0, 90.0), _lobe(1, 210.0), _lobe(2, 330.0),
        ],
        decals=[('sensor', 'front', ((-15, 15), (-999, 0), (18, 30)), 'body'),
                ('core', 'front', ((-10, 10), (-999, 0), (30, 45)), 'crown')],
    ),
}

# 斜めの確認用のカメラ：Codex の「右前 45 度」の絵は、+X（本人の左）前から見た向きに描かれている（突撃型は反転して使う）
THREE_Q = {'mini': (1, False), 'sentry': (1, False), 'charger': (-1, True), 'shield': (1, False), 'floater': (1, False)}


def log(msg: str) -> None:
    print(f'[banki] {msg}', flush=True)


# ---------------------------------------------------------------- 絵と視点

class View:
    """正投影の絵 1 枚。世界の点 p（cm）→ 絵の画素 (col, row) = (c0 + (p/stretch)·r * sr, r0 - (p/stretch)·u * su)"""

    def __init__(self, name, rgba, d, r, u, c0, r0, sr, su, stretch):
        self.name, self.rgba = name, rgba
        self.d, self.r, self.u = np.array(d, float), np.array(r, float), np.array(u, float)
        self.c0, self.r0, self.sr, self.su = c0, r0, sr, su
        self.stretch = np.array([1.0, stretch, 1.0])
        self.alpha = rgba[..., 3] > 128

    def project(self, p: np.ndarray):
        q = p / self.stretch
        return self.c0 + q @ self.r * self.sr, self.r0 - q @ self.u * self.su


def fetch_art() -> None:
    os.makedirs(SRC, exist_ok=True)
    for t in TYPES:
        for n in ('3d_front', '3d_back', '3d_side_right', '3d_side_left', '3d_top', '3d_front_right45'):
            p = os.path.join(SRC, f'{t}_{n}_r2.png')
            if os.path.exists(p):
                continue
            r = subprocess.run(['git', 'show', f'{ART_REF}/{t}_{n}_r2.png'], cwd=REPO, capture_output=True)
            if r.returncode == 0:
                with open(p, 'wb') as f:
                    f.write(r.stdout)


def load_rgba(t: str, n: str) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(os.path.join(SRC, f'{t}_3d_{n}_r2.png')).convert('RGBA'))


def scale_of(cfg) -> float:
    return cfg.get('px_per_cm') or (cfg['rows'][1] - cfg['rows'][0]) / cfg['height']


def side_view(t, cfg, name, cam_sign, flip, s, mirror=False):
    rgba = load_rgba(t, name)
    sgn = cam_sign * (-1 if mirror else 1)
    r = (0, 1, 0) if cam_sign > 0 else (0, -1, 0)
    if flip:
        r = tuple(-c for c in r)
    label = name + ('_mirror' if mirror else '')
    return View(label, rgba, (sgn, 0, 0), r, Z, cfg['center'], cfg['rows'][1], s, s, cfg.get('y_stretch', 1.0))


def build_views(t: str, cfg) -> dict:
    """形と色に使う視点。top は形の外接の箱に合わせる（extent_cm が要るので build_hull で後から作る）"""
    s = scale_of(cfg)
    st = cfg.get('y_stretch', 1.0)
    v = {'front': View('front', load_rgba(t, 'front'), (0, -1, 0), X, Z, cfg['center'], cfg['rows'][1], s, s, st),
         'back': View('back', load_rgba(t, 'back'), (0, 1, 0), (-1, 0, 0), Z, cfg['center'], cfg['rows'][1], s, s, st)}
    name, cs, fl = cfg['side']
    v['side'] = side_view(t, cfg, name, cs, fl, s)
    v[name] = v['side']
    extra = cfg.get('extra_sides')
    if extra:
        for n2, cs2, fl2 in extra:
            v[n2] = side_view(t, cfg, n2, cs2, fl2, s)
    else:
        v['side_mirror'] = side_view(t, cfg, name, cs, fl, s, mirror=True)
    return v


def fit_top(t: str, cfg, ext) -> View:
    """真上の絵：外形の外接の箱を、正面の幅（x）と真横の奥行き（y、絵の cm）に合わせる"""
    rgba = load_rgba(t, 'top')
    a = rgba[..., 3] > 128
    rows = np.nonzero(a.any(1))[0]
    cols = np.nonzero(a.any(0))[0]
    (x0, x1), (y0, y1) = ext
    sr = (cols[-1] + 1 - cols[0]) / (x1 - x0)
    su = (rows[-1] + 1 - rows[0]) / (y1 - y0)
    c0 = cols[0] - x0 * sr
    if cfg.get('top_flip'):
        # 盾型の真上の絵は、体が画像の上（盾の前の端）に描かれていて、真横の絵（体が前）と前後が逆
        r0 = rows[0] - y0 * su
        return View('top', rgba, (0, 0, 1), X, (0, -1, 0), c0, r0, sr, su, cfg.get('y_stretch', 1.0))
    r0 = rows[0] + y1 * su
    return View('top', rgba, (0, 0, 1), X, (0, 1, 0), c0, r0, sr, su, cfg.get('y_stretch', 1.0))


# ---------------------------------------------------------------- 形（視体積＋超楕円の断面）

def runs_along(m: np.ndarray, coord: np.ndarray):
    """m (N, K) の各列 k について、軸 0 の区間（True の続き）ごとの中点と半幅。各要素 → その区間の値"""
    n, k = m.shape
    mid = np.zeros(m.shape)
    half = np.full(m.shape, 1e-6)
    for j in range(k):
        col = m[:, j]
        if not col.any():
            continue
        lab, cnt = ndi.label(col)
        for i in range(1, cnt + 1):
            idx = np.nonzero(lab == i)[0]
            a, b = coord[idx[0]], coord[idx[-1]]
            mid[idx, j] = (a + b) / 2
            half[idx, j] = max((b - a) / 2, 1e-3) + (coord[1] - coord[0]) / 2
    return mid, half


def sample(view: View, pts: np.ndarray) -> np.ndarray:
    c, r = view.project(pts)
    ci, ri = np.floor(c).astype(int), np.floor(r).astype(int)
    ok = (ci >= 0) & (ci < IMG) & (ri >= 0) & (ri < IMG)
    out = np.zeros(len(pts), bool)
    out[ok] = view.alpha[ri[ok], ci[ok]]
    return out


def build_hull(t: str, cfg, views: dict):
    """ボクセルの視体積。戻り値：(占有 (nx,ny,nz) bool, 格子の座標 xs, ys, zs（世界 cm）, ボクセルの大きさ)"""
    s = scale_of(cfg)
    st = cfg.get('y_stretch', 1.0)
    fa, sa = views['front'].alpha, views['side'].alpha
    fc = np.nonzero(fa.any(0))[0]
    sc = np.nonzero(sa.any(0))[0]
    x0, x1 = (fc[0] - cfg['center']) / s, (fc[-1] + 1 - cfg['center']) / s
    ys_art = sorted([((sc[0] - cfg['center']) / s), ((sc[-1] + 1 - cfg['center']) / s)])
    if views['side'].r[1] < 0:   # 絵の右 = -Y
        ys_art = sorted([-ys_art[0], -ys_art[1]])
    top_px = min(np.nonzero(fa.any(1))[0][0], np.nonzero(sa.any(1))[0][0])
    z1 = (cfg['rows'][1] - top_px) / s
    ext = ((x0, x1), (ys_art[0], ys_art[1]))
    if cfg['top']:
        views['top'] = fit_top(t, cfg, ext)
    vox = max(x1 - x0, (ys_art[1] - ys_art[0]) * st, z1) / 170.0
    xs = np.arange(x0 - vox, x1 + vox, vox)
    ys = np.arange(ys_art[0] * st - vox, ys_art[1] * st + vox, vox)
    zs = np.arange(vox / 2, z1 + vox, vox)
    # 正面 (x, z)・真横 (y, z) の外形
    XZ = np.stack(np.meshgrid(xs, zs, indexing='ij'), -1).reshape(-1, 2)
    F = sample(views['front'], np.c_[XZ[:, 0], np.zeros(len(XZ)), XZ[:, 1]]).reshape(len(xs), len(zs))
    YZ = np.stack(np.meshgrid(ys, zs, indexing='ij'), -1).reshape(-1, 2)
    S = sample(views['side'], np.c_[np.zeros(len(YZ)), YZ[:, 0], YZ[:, 1]]).reshape(len(ys), len(zs))
    fm, fh = runs_along(F, xs)
    p = cfg['p']
    u = np.abs(xs[:, None, None] - fm[:, None, :]) / fh[:, None, :]
    split = cfg.get('side_split')
    if split is None:
        sm, sh = runs_along(S, ys)
        v = np.abs(ys[None, :, None] - sm[None, :, :]) / sh[None, :, :]
        occ = F[:, None, :] & S[None, :, :] & (u ** p + v ** p <= 1.0)
    else:
        # 真横の外形が 2 つの部品の重なり（盾型：体と、その横の盾）のとき、x で分けて、それぞれ奥行きの範囲を
        # 限った真横の外形を使う（体の断面が盾の幅まで広がって箱になるのを防ぐ）
        occ = np.zeros((len(xs), len(ys), len(zs)), bool)
        for sel, (y0, y1) in ((xs < split[0], split[1]), (xs >= split[0], split[2])):
            Sk = S & ((ys >= y0) & (ys <= y1))[:, None]
            sm, sh = runs_along(Sk, ys)
            v = np.abs(ys[None, :, None] - sm[None, :, :]) / sh[None, :, :]
            occ[sel] = (F[:, None, :] & Sk[None, :, :] & (u ** p + v ** p <= 1.0))[sel]
    if cfg['top']:
        XY = np.stack(np.meshgrid(xs, ys, indexing='ij'), -1).reshape(-1, 2)
        T = sample(views['top'], np.c_[XY, np.zeros(len(XY))]).reshape(len(xs), len(ys))
        occ &= T[:, :, None]
    # 車輪の所を削る（円柱は別につくる）
    for _n, _par, c, rad, w in cfg.get('wheels', []):
        dx = np.abs(xs - c[0])[:, None, None] <= w / 2 + 1.5
        rr = np.hypot((ys - c[1])[None, :, None], (zs - c[2])[None, None, :]) <= rad + 1.0
        occ &= ~(dx & rr)
    log(f'{t}: voxel {vox:.2f}cm grid {occ.shape} filled {int(occ.sum())}')
    return occ, xs, ys, zs, vox


def label_parts(cfg, occ, xs, ys, zs):
    """ボクセル → 部品の番号（0 = body）"""
    Xg, Yg, Zg = np.meshgrid(xs, ys, zs, indexing='ij')
    lab = np.zeros(occ.shape, np.int16)
    free = occ.copy()
    for i, (_n, _par, f, *_r) in enumerate(cfg['parts'], start=1):
        m = free & f(Xg, Yg, Zg)
        lab[m] = i
        free &= ~m
    lab[~occ] = -1
    return lab


def part_mesh(mask: np.ndarray, xs, ys, zs, vox):
    """部品のボクセルを少しぼかして marching cubes。戻り値：頂点 (cm、世界), 三角形"""
    from skimage import measure
    pad = np.pad(mask.astype(np.float32), 2)
    sm = ndi.gaussian_filter(pad, 0.8)
    if sm.max() < 0.5:
        return None
    v, f, _n, _ = measure.marching_cubes(sm, 0.5)
    v = (v - 2) * vox + np.array([xs[0], ys[0], zs[0]])
    if PAINT == 'region':
        v = taubin(v, f)
    return v, f[:, ::-1]   # 外向き


def pivot_of(spec, mask, xs, ys, zs):
    if spec != 'top':
        return np.array(spec, float)
    idx = np.nonzero(mask)
    ztop = idx[2].max()
    sel = idx[2] >= ztop - 2
    return np.array([xs[idx[0][sel]].mean(), ys[idx[1][sel]].mean(), zs[ztop]])


def axis_matrix(axis) -> np.ndarray:
    """ローカル +X を axis に向ける回転（3×3）。+Z はなるべく上"""
    a = np.array(axis, float)
    a /= np.linalg.norm(a)
    up = np.array([0, 0, 1.0]) if abs(a[2]) < 0.9 else np.array([0, -1.0, 0])
    yv = np.cross(up, a)
    yv /= np.linalg.norm(yv)
    zv = np.cross(a, yv)
    return np.stack([a, yv, zv], 1)


def cylinder(center, radius, width, segs=16):
    """X 軸向きの円柱（車輪）。戻り値：頂点（cm）、面（四角と多角形）"""
    c = np.array(center, float)
    vs, fs = [], []
    for sx in (-0.5, 0.5):
        for k in range(segs):
            a = 2 * math.pi * k / segs
            vs.append(c + [sx * width, radius * math.cos(a), radius * math.sin(a)])
    for k in range(segs):
        k2 = (k + 1) % segs
        fs.append([k, k2, segs + k2, segs + k])
    fs.append(list(range(segs))[::-1])
    fs.append(list(range(segs, 2 * segs)))
    return np.array(vs), fs


def c_disc(center, radius, width, segs=20, gap_deg=70.0):
    """車輪の外側の C 字の蓋（白磁）：扇の切り欠きのある薄い円盤。絵の車輪の白い「C」"""
    c = np.array(center, float)
    side = np.sign(c[0]) or 1.0
    x_in, x_out = c[0] + side * (width / 2 - 0.5), c[0] + side * (width / 2 + 1.2)
    a0 = math.radians(gap_deg / 2)
    angs = np.linspace(a0, 2 * math.pi - a0, segs)
    vs = []
    for xx in (x_in, x_out):
        vs.append([xx, c[1], c[2]])
        for a in angs:
            vs.append([xx, c[1] + radius * math.cos(a + math.pi), c[2] + radius * math.sin(a + math.pi)])
    n = segs + 1
    fs = []
    for k in range(1, segs):
        fs.append([0, k, k + 1])
        fs.append([n, n + k + 1, n + k])
        fs.append([k, n + k, n + k + 1, k + 1])
    fs.append([0, n, n + 1, 1])
    fs.append([0, segs, n + segs, n])
    return np.array(vs), fs


# ---------------------------------------------------------------- Blender

def srgb_to_linear(hexstr: str):
    h = hexstr.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def make_materials(t: str, tex_path: str | None):
    import bpy
    mats = {}
    shell = bpy.data.materials.new(f'banki_{t}_shell')
    shell.use_nodes = True
    b = shell.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.62
    if tex_path:
        img = bpy.data.images.load(tex_path)
        tn = shell.node_tree.nodes.new('ShaderNodeTexImage')
        tn.image = img
        shell.node_tree.links.new(tn.outputs['Color'], b.inputs['Base Color'])
    mats['shell'] = shell
    for key, hexc, rough, metal in (('dark', COLORS['dark'], 0.7, 0.3), ('brass', COLORS['brass'], 0.45, 0.6),
                                    ('shell_flat', '#DAD1BD', 0.62, 0.0)):   # 車輪の蓋（白磁 × SHELL_GAIN）
        m = bpy.data.materials.new(f'banki_{key}')
        m.use_nodes = True
        bb = m.node_tree.nodes['Principled BSDF']
        bb.inputs['Base Color'].default_value = (*srgb_to_linear(hexc), 1)
        bb.inputs['Roughness'].default_value = rough
        bb.inputs['Metallic'].default_value = metal
        mats[key] = m
    for key in ('sensor', 'core'):
        m = bpy.data.materials.new(f'banki_{key}')
        m.use_nodes = True
        bb = m.node_tree.nodes['Principled BSDF']
        col = srgb_to_linear(COLORS['amber'])
        bb.inputs['Base Color'].default_value = (*col, 1)
        bb.inputs['Emission Color'].default_value = (*col, 1)
        bb.inputs['Emission Strength'].default_value = 1.5
        bb.inputs['Roughness'].default_value = 0.4
        mats[key] = m
    return mats


def new_object(name: str, verts_cm, faces, mat, pivot_cm, rot3, smooth=True):
    """頂点（世界 cm）の物体を、原点 = pivot、向き = rot3 で置く（m）"""
    import bpy
    from mathutils import Matrix
    v = (np.asarray(verts_cm) - pivot_cm) @ rot3 * 0.01
    me = bpy.data.meshes.new(name)
    me.from_pydata(v.tolist(), [], [list(map(int, f)) for f in faces])
    me.validate()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    M = np.eye(4)
    M[:3, :3] = rot3
    M[:3, 3] = np.asarray(pivot_cm) * 0.01
    ob.matrix_world = Matrix(M.tolist())
    for pl in me.polygons:
        pl.use_smooth = smooth
    return ob


def decimate(ob, ratio: float) -> None:
    import bpy
    if ratio >= 1.0:
        return
    mod = ob.modifiers.new('dec', 'DECIMATE')
    mod.ratio = max(ratio, 0.01)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier='dec')


def smooth_by_angle(objs, deg=38.0) -> None:
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(deg))


def smart_uv(objs) -> None:
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(UV_ANGLE), island_margin=0.006, area_weight=0.0)
    bpy.ops.object.mode_set(mode='OBJECT')


def mesh_world(objs, ids=False):
    """物体たちの三角形（世界 cm）と UV。戻り値：頂点 (T,3,3)、UV (T,3,2)"""
    P, U, ID = [], [], []
    for k, ob in enumerate(objs):
        me = ob.data
        me.calc_loop_triangles()
        mw = np.array(ob.matrix_world)
        co = np.array([v.co for v in me.vertices]).reshape(-1, 3)
        co = (co @ mw[:3, :3].T + mw[:3, 3]) * 100.0
        uvl = me.uv_layers.active.data
        uv = np.array([d.uv for d in uvl]).reshape(-1, 2)
        lt = me.loop_triangles
        vi = np.array([t.vertices for t in lt]).reshape(-1, 3)
        li = np.array([t.loops for t in lt]).reshape(-1, 3)
        P.append(co[vi])
        U.append(uv[li])
        ID.append(np.full(len(vi), k))
    if ids:
        return np.concatenate(P), np.concatenate(U), np.concatenate(ID)
    return np.concatenate(P), np.concatenate(U)


# ---------------------------------------------------------------- 焼く（絵の投影）

def raster(p2: np.ndarray, w: int, h: int):
    """三角形 (T,3,2)（画素の連続座標）を塗る。画素の中心が入る (画素の番号, 三角形, 重心座標)。texture.py の小さな版"""
    x, y = p2[..., 0], p2[..., 1]
    x0 = np.clip(np.ceil(x.min(1) - 0.5), 0, w).astype(np.int64)
    x1 = np.clip(np.floor(x.max(1) - 0.5), -1, w - 1).astype(np.int64)
    y0 = np.clip(np.ceil(y.min(1) - 0.5), 0, h).astype(np.int64)
    y1 = np.clip(np.floor(y.max(1) - 0.5), -1, h - 1).astype(np.int64)
    nx, ny = np.maximum(x1 - x0 + 1, 0), np.maximum(y1 - y0 + 1, 0)
    cnt = nx * ny
    ax, ay, bx, by, cx, cy = x[:, 0], y[:, 0], x[:, 1], y[:, 1], x[:, 2], y[:, 2]
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    sel = np.nonzero((np.abs(area) > 1e-9) & (cnt > 0))[0]
    c = cnt[sel]
    tid = np.repeat(sel, c)
    off = np.repeat(np.cumsum(c) - c, c)
    loc = np.arange(int(c.sum())) - off
    px = x0[tid] + loc % nx[tid]
    py = y0[tid] + loc // nx[tid]
    qx, qy = px + 0.5, py + 0.5
    ar = area[tid]
    w0 = ((bx[tid] - qx) * (cy[tid] - qy) - (by[tid] - qy) * (cx[tid] - qx)) / ar
    w1 = ((cx[tid] - qx) * (ay[tid] - qy) - (cy[tid] - qy) * (ax[tid] - qx)) / ar
    w2 = 1.0 - w0 - w1
    ins = (w0 >= -1e-7) & (w1 >= -1e-7) & (w2 >= -1e-7)
    return py[ins] * w + px[ins], tid[ins], np.stack([w0[ins], w1[ins], w2[ins]], 1)


def amber_mask(rgb: np.ndarray, bright: float = 0.6) -> np.ndarray:
    """琥珀色（発光のセンサー・核）の画素。rgb は 0..1。bright：明るさの下限（真鍮の光る所と分けたいときは上げる）"""
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (mx > bright) & (sat > 0.62) & (r >= g) & (g > b) & ((g - b) / np.maximum(r - b, 1e-6) > 0.25)


# 絵の色を材質の基準色へ寄せる：各テクセルを白磁・真鍮・黒鉛のどれかに分け、spec の hex × 絵の明暗（弱め）にする。
# 視点の間のずれで混ざった中間の色（白磁と黒鉛の混ざった灰色のしみ）が消え、絵の平らな塗りに近くなる
PALETTE = {'shell': ('#F3E9D2', 0.84), 'brass': ('#A98749', 0.52), 'dark': ('#444641', 0.26)}
# 白磁の明るさの係数：spec の hex そのままだと日なたで真っ白に飛ぶ（絵の白磁は塗りの陰で平均がこれくらい暗い）
SHELL_GAIN = 0.9
SHADE_GAMMA = 0.45   # 絵の明暗をどれだけ残すか（0 = 平らな色）
MIN_COS = 0.6
MAJORITY_K = 24
VIEW_POWER = 8       # 視点の重み = (法線・視線)^これ（大きいほど一番よく見える視点だけになる）


CLEAN = os.environ.get('BANKI_CLEAN', '1') != '0'   # 平らな色へ寄せる（0 = 従来の投影の色）
DARK_VOTE = 0.5      # 黒鉛：近くの半分以上が黒鉛（絵の関節・胴の暗い所は広いので、しみだけ落とす）
DARK_MIN = 0.032     # 黒鉛の塊の最小の大きさ（全高に対する比）。これより小さい黒い点・筋は消す（視点のずれのしみ）
BRASS_MIN = 0.10     # 真鍮の塊の最小の大きさ（全高に対する比）。細い縁は連続していれば残り、孤立した点は消える
BRASS_FILL = 0.25    # 真鍮の帯の途切れ（欠け）を埋める：広い範囲の真鍮の割合がこれ以上で、まわりを囲まれている所
JOINT_PARTS = ('susp', 'wheel', 'muzzle')   # 名前がこれで始まる部品は全部黒鉛（関節・懸架・砲口）
JOINT_NEAR = 2.2     # 関節のまわりで絵の暗い所を残す範囲（joint_r の倍）
JOINT_FORCE = 0.75   # 関節（各部品の回転軸の位置）の黒鉛の球の半径（joint_r × 全高）のうち、必ず黒鉛にする範囲。外側 1.45 倍までは絵が暗い所だけ
SEAM_K = 0.65        # 継ぎ目の近さ（radius × これ）
BRASS_SAT = 0.50     # 真鍮の彩度の下限（白磁の陰の黄ばみを真鍮にしない）
BRASS_VOTE = 0.5
FLAT_GAMMA = 0.12    # 清書の色に残す絵の明暗（Godot の光で立体感は出る）


def _components(mask: np.ndarray, pos: np.ndarray, link: float):
    """mask の点を、3D で link 以内どうしにつないだ塊に分ける。戻り値：(塊の番号（mask の点ごと）, 塊ごとの外接の箱の最大の辺)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    idx = np.nonzero(mask)[0]
    if len(idx) == 0:
        return idx, np.zeros(0, int), np.zeros(0)
    pts = pos[idx]
    pr = cKDTree(pts).query_pairs(link, output_type='ndarray')
    g = coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(idx), len(idx)))
    n, lab = connected_components(g, directed=False)
    ext = np.zeros(n)
    for ax in range(3):
        mx = np.full(n, -np.inf)
        mn = np.full(n, np.inf)
        np.maximum.at(mx, lab, pts[:, ax])
        np.minimum.at(mn, lab, pts[:, ax])
        ext = np.maximum(ext, mx - mn)
    return idx, lab, ext


def _drop_small(cls: np.ndarray, k: int, pos: np.ndarray, link: float, min_ext: float, keep=None) -> np.ndarray:
    """クラス k の塊のうち、外接の箱の最大の辺が min_ext 未満のものを白磁（0）に戻す（keep の点は残す）"""
    m = cls == k
    idx, lab, ext = _components(m, pos, link)
    if len(idx) == 0:
        return cls
    small = ext[lab] < min_ext
    if keep is not None:
        small &= ~keep[idx]
    out = cls.copy()
    out[idx[small]] = 0
    return out


def snap_palette(col: np.ndarray, pos: np.ndarray | None = None, radius: float = 2.0,
                 part: np.ndarray | None = None, pnames: list | None = None,
                 joints: np.ndarray | None = None, joint_r: float = 0.0, height: float = 100.0, zone=None, brass_min: float = BRASS_MIN) -> np.ndarray:
    mx, mn = col.max(1), col.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    lum = col.mean(1)
    cls = np.where(lum < 0.30, 2, np.where(sat > (BRASS_SAT if CLEAN else 0.38), 1, 0))
    if pos is not None:
        # 3D で近いテクセルの多数決（半径 radius cm）：視点のずれで出る小さなしみ・点を消す
        from scipy.spatial import cKDTree
        tree = cKDTree(pos)
        r = radius * (1.8 if CLEAN else 1.0)
        _, j = tree.query(pos, k=MAJORITY_K, distance_upper_bound=r)
        valid = j < len(pos)
        cj = cls[np.where(valid, j, 0)]
        frac = np.stack([((cj == k) & valid).sum(1) for k in range(3)], 1) / np.maximum(valid.sum(1, keepdims=True), 1)
        if CLEAN:
            raw = cls
            cls = np.where(frac[:, 2] >= DARK_VOTE, 2, np.where(frac[:, 1] >= BRASS_VOTE, 1, 0))
            link = radius * 0.9
            cls = _drop_small(cls, 2, pos, link, DARK_MIN * height)
            # 絵の暗い所を残すのは、関節（回転軸）のまわり・部品の境の近く・型ごとの暗い領域（zone）だけ。
            # それ以外の暗い所は、絵の陰や視点のずれのしみ（まだら）なので白磁に倒す（清書：部品ごとに黒鉛か白磁か）
            allow = np.zeros(len(pos), bool)
            if zone is not None:
                allow |= zone(pos[:, 0], pos[:, 1], pos[:, 2])
            if joints is not None and len(joints) and joint_r > 0:
                from scipy.spatial import cKDTree as _T0
                allow |= _T0(joints).query(pos)[0] < JOINT_NEAR * joint_r
            if part is not None:
                _, jn0 = tree.query(pos, k=16, distance_upper_bound=radius * 1.2)
                vn0 = jn0 < len(pos)
                allow |= ((part[np.where(vn0, jn0, 0)] != part[:, None]) & vn0).any(1)
            cls = np.where((cls == 2) & ~allow, 0, cls)
            cls = _drop_small(cls, 2, pos, link, DARK_MIN * height)   # 領域で切ったあとの残りかす
            # 真鍮の帯の欠けを埋める：広い範囲（radius × 4）に真鍮が BRASS_FILL 以上あり、その重心が自分の近く（帯の内側）の所
            _, j2 = tree.query(pos, k=64, distance_upper_bound=radius * 6.0)
            v2 = j2 < len(pos)
            jj = np.where(v2, j2, 0)
            for _it in range(2):
                b = (cls[jj] == 1) & v2
                cnt = b.sum(1)
                cen = (pos[jj] * b[..., None]).sum(1) / np.maximum(cnt, 1)[:, None] - pos
                fill = (cls == 0) & (cnt / np.maximum(v2.sum(1), 1) >= BRASS_FILL) & (np.linalg.norm(cen, axis=1) <= radius * 2.2)
                cls = np.where(fill, 1, cls)
            cls = _drop_small(cls, 1, pos, link * 1.4, brass_min * height)
            # 関節：部品ぜんぶが黒鉛の部品と、回転軸の位置のまわりの球
            forced = np.zeros(len(pos), bool)
            if part is not None and pnames is not None:
                forced |= np.array([n.startswith(JOINT_PARTS) for n in pnames])[part]
            if joints is not None and len(joints) and joint_r > 0:
                from scipy.spatial import cKDTree as _T
                d, _ = _T(joints).query(pos)
                forced |= d < JOINT_FORCE * joint_r
                forced |= (d < 1.45 * joint_r) & (raw == 2)
            cls = np.where(forced, 2, cls)
        else:
            cls = (frac * 1.0).argmax(1)
    out = np.zeros_like(col)
    gam = FLAT_GAMMA if CLEAN else SHADE_GAMMA
    for k, (hexc, ref) in enumerate(PALETTE.values()):
        m = cls == k
        base = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
        shade = np.clip(lum[m] / ref, 0.7, 1.08) ** gam * (SHELL_GAIN if k == 0 else 1.0)
        out[m] = base * shade[:, None]
    return np.clip(out, 0, 1)


def bake(views: dict, tris: np.ndarray, uvs: np.ndarray, size: int = 1024, radius: float = 2.0,
         tri_part: np.ndarray | None = None, pnames: list | None = None,
         joints: np.ndarray | None = None, joint_r: float = 0.0, height: float = 100.0, zone=None, brass_min: float = BRASS_MIN) -> np.ndarray:
    """テクセルごとに、見えている視点の絵の色を重みで混ぜる。戻り値：(size,size,3) の sRGB 0..1"""
    from scipy.spatial import cKDTree
    p2 = np.stack([uvs[..., 0] * size, (1.0 - uvs[..., 1]) * size], -1)
    pix, tri, bar = raster(p2, size, size)
    pix, first = np.unique(pix, return_index=True)
    tri, bar = tri[first], bar[first]
    pos = (tris[tri] * bar[..., None]).sum(1)
    fn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
    nrm = fn[tri]
    acc = np.zeros((len(pix), 3))
    wsum = np.zeros(len(pix))
    cbest = np.zeros(len(pix))
    ZS = 512
    for name, v in views.items():
        if name == 'side' or name.startswith('3q'):
            continue
        rgb = v.rgba[..., :3].astype(np.float32) / 255.0
        am = amber_mask(rgb)
        rgb[am] = np.array([0x30, 0x2F, 0x2B]) / 255.0
        inside = ndi.binary_erosion(v.alpha, iterations=4)
        # 奥行き（視線の向きの手前ほど大きい）
        c, r = v.project(tris.reshape(-1, 3))
        q2 = np.stack([c, r], -1).reshape(-1, 3, 2) * (ZS / IMG)
        dep = (tris.reshape(-1, 3) @ v.d).reshape(-1, 3)
        zp, zt, zb = raster(q2, ZS, ZS)
        zbuf = np.full(ZS * ZS, -np.inf)
        np.maximum.at(zbuf, zp, (dep[zt] * zb).sum(1))
        tc, tr = v.project(pos)
        ic = np.clip((tc * ZS / IMG).astype(int), 0, ZS - 1)
        ir = np.clip((tr * ZS / IMG).astype(int), 0, ZS - 1)
        near = ndi.maximum_filter(zbuf.reshape(ZS, ZS), size=3).ravel()
        vis = pos @ v.d >= np.minimum(zbuf[ir * ZS + ic], near[ir * ZS + ic]) - 1.5
        ci = np.clip(tc.astype(int), 0, IMG - 1)
        ri = np.clip(tr.astype(int), 0, IMG - 1)
        ok = vis & inside[ri, ci]
        w = np.clip(nrm @ v.d, 0, 1) ** VIEW_POWER * ok
        if name.endswith('mirror') or name == 'top':
            w *= 0.7
        acc += w[:, None] * rgb[ri, ci]
        wsum += w
        cbest = np.maximum(cbest, np.clip(nrm @ v.d, 0, 1) * ok)
    # 斜めにしか見えていないテクセル（一番よい視点でも法線と視線が MIN_COS 未満）は、絵の平らな塗りが引き伸ばされて
    # 黒い筋・しみになるので、3D で近い「よく見えているテクセル」の色で埋める
    good = (wsum > 0.02) & (cbest >= MIN_COS)
    col = np.zeros((len(pix), 3))
    col[good] = acc[good] / wsum[good, None]
    if (~good).any() and good.any():
        tree = cKDTree(pos[good])
        _, j = tree.query(pos[~good], k=6)
        col[~good] = col[good][j].mean(1)
    col = snap_palette(col, pos, radius, None if tri_part is None else tri_part[tri], pnames, joints, joint_r, height, zone, brass_min)
    img = np.zeros((size * size, 3))
    have = np.zeros(size * size, bool)
    img[pix] = col
    have[pix] = True
    _, (iy, ix) = ndi.distance_transform_edt(~have.reshape(size, size), return_indices=True)
    return img.reshape(size, size, 3)[iy, ix]


# ---------------------------------------------------------------- 領域で塗る（絵は「どこが何色か」を決めるだけ。画素は写さない）

# BANKI_PAINT=region（既定）：部品ごとの面を白磁・真鍮・黒鉛の 3 つの平らな材質に分ける（閂・ナゴミと同じ、テクスチャなし）。
# BANKI_PAINT=bake：従来の投影で焼いたテクスチャ（比べる用）
PAINT = os.environ.get('BANKI_PAINT', 'region')
IVORY = '#E9DFC9'        # 閂と同じ白磁（spec #F3E9D2 × 0.95）
TAUBIN_ITERS = int(os.environ.get('BANKI_TAUBIN', 30))       # 表面のでこぼこをならす回数（Taubin：縮まない平滑化。外形はほぼ保つ）
R_DIFFUSE = int(os.environ.get('BANKI_R_DIFFUSE', 8))           # 票（色の割合）を面のつながりに沿ってならす回数
R_DIFFUSE_BRASS = int(os.environ.get('BANKI_R_DIFFUSE_BRASS', 3))   # 真鍮を決める票をならす回数
R_DARK_ZONE = 0.3        # 型の暗い領域（dark_zone）の中で黒鉛にする票の割合（領域の中はむらなく埋める）
R_DARK = 0.5             # 黒鉛にする票の割合
R_BRASS = 0.42           # 真鍮にする票の割合
R_CLOSE = 1              # 真鍮の帯の途切れを埋める（つながりで膨らませて縮める）輪の数
R_IVORY_MIN = 0.05       # 白磁の島（真鍮・黒鉛に囲まれた小さな白）を消す大きさ（全高に対する比）
R_BRASS_SAT = 0.38      # 絵の画素を真鍮とみなす彩度（白磁の陰は 0.3 くらい、真鍮は 0.43 以上）
R_DARK_MIN = float(os.environ.get('BANKI_R_DARK_MIN', 0.06))   # 黒鉛の塊の最小の大きさ（全高に対する比）。関節・部品の境・暗い領域に触れる塊
R_DARK_BIG = float(os.environ.get('BANKI_R_DARK_BIG', 99))      # 関節・部品の境・暗い領域の外でも、これより大きい黒鉛の塊は残す（歩哨型の正面の V の開口など。全高に対する比）
R_TRIS = 2.5            # 三角形の数（TYPES の tris）の倍率。色の境を面で表すので、焼く方式より細かくする
R_BLUR = 0.35           # 絵の色の割合の地図をぼかす幅（頂点の間隔に対する比）。頂点 1 つがまわりの平均の色を見る
R_NORMAL_SMOOTH = 10    # 票に使う法線をならす回数
R_JOINT = 1.2           # 関節の黒鉛の球の半径（joint_r に対する比）
R_JOINT_CLEAR = 2.2     # 関節の球・継ぎ目のまわりのこの範囲（RJ・RS の倍）は、絵の暗い所を票から外す
R_VIEW_POWER = float(os.environ.get('BANKI_R_POWER', 4))   # 視点の重み = (法線・視線)^これ（焼く方式の 8 より弱く：縁の帯を正面の絵からも拾う）
R_MAJORITY = int(os.environ.get('BANKI_R_MAJ', 5))         # 多数決（自分 + 隣）の回数
R_SEAM = float(os.environ.get('BANKI_R_SEAM', 0.0))   # 部品の継ぎ目の黒鉛の帯の幅（全高に対する比。ほかの部品までの距離）
R_BAND = float(os.environ.get('BANKI_R_BAND', 0.10))   # 真鍮の帯の幅の上限（全高に対する比）。これより太い塊は部品まるごと（R_WHOLE 以上）でなければ白磁
R_WHOLE = 0.3           # 部品のこの割合以上を占める真鍮の塊は、部品まるごと（角・棘）として残す
WHOLE_PARTS = ('spike', 'horn', 'fin', 'crown')   # 部品まるごと 1 色にする飾りの部品（名前の頭）
R_WHOLE_BRASS = 0.15    # 飾りの部品の票の真鍮の割合がこれ以上なら部品まるごと真鍮
R_CUT_SMOOTH = int(os.environ.get('BANKI_R_CUT', 6))        # 境の線を引く前に、色の場をならす回数（境が階段にならず、なめらかな線になる）


def taubin(v: np.ndarray, f: np.ndarray, iters: int = TAUBIN_ITERS, lam: float = 0.5, mu: float = -0.53) -> np.ndarray:
    """縮まない平滑化（Taubin）。v (N,3), f (M,3)"""
    if iters <= 0:
        return v
    from scipy.sparse import coo_matrix
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    A = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(v), len(v))).tocsr()
    A.data[:] = 1.0
    deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1)[:, None]
    v = v.copy()
    for _ in range(iters):
        for k in (lam, mu):
            v = v + k * (A @ v / deg - v)
    return v


def _adjacency(f: np.ndarray, n: int):
    from scipy.sparse import coo_matrix
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    A = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    return A


def _diffuse(A, x: np.ndarray, iters: int, keep=None) -> np.ndarray:
    deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1)[:, None]
    x0 = x
    for _ in range(iters):
        x = 0.5 * x + 0.5 * (A @ x) / deg
        if keep is not None:
            x[keep] = x0[keep]
    return x


def _class_maps(v: View, sigma: float = 2.0) -> np.ndarray:
    """絵の画素を 白磁 0・真鍮 1・黒鉛 2 に分けた割合の地図 (H,W,3)。筆の粗さは中央値でならしてから分ける"""
    rgb = v.rgba[..., :3].astype(np.float32) / 255.0
    rgb = ndi.median_filter(rgb, size=(7, 7, 1))
    am = amber_mask(rgb, 0.5)
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    lum = rgb.mean(-1)
    cls = np.where(am, 3, np.where(lum < 0.30, 2, np.where(sat > R_BRASS_SAT, 1, 0)))
    # 琥珀色（センサー・核）は発光の板が覆うので票にしない（全部 0 → まわりの色で埋まる）
    oh = np.stack([(cls == k).astype(np.float32) for k in range(3)], -1)
    return ndi.gaussian_filter(oh, (sigma, sigma, 0))


def _vertex_votes(views: dict, V: np.ndarray, N: np.ndarray, tris: np.ndarray, spacing: float = 2.0):
    """頂点ごとの色の票 (N,3) と、一番よい視点の向き（法線・視線）"""
    ZS = 512
    acc = np.zeros((len(V), 3))
    wsum = np.zeros(len(V))
    cbest = np.zeros(len(V))
    for name, v in views.items():
        if name == 'side' or name.startswith('3q'):
            continue
        cm = _class_maps(v, max(2.0, R_BLUR * spacing * v.sr))
        inside = ndi.binary_erosion(v.alpha, iterations=4)
        c, r = v.project(tris.reshape(-1, 3))
        q2 = np.stack([c, r], -1).reshape(-1, 3, 2) * (ZS / IMG)
        dep = (tris.reshape(-1, 3) @ v.d).reshape(-1, 3)
        zp, zt, zb = raster(q2, ZS, ZS)
        zbuf = np.full(ZS * ZS, -np.inf)
        np.maximum.at(zbuf, zp, (dep[zt] * zb).sum(1))
        near = ndi.maximum_filter(zbuf.reshape(ZS, ZS), size=3).ravel()
        tc, tr = v.project(V)
        ic = np.clip((tc * ZS / IMG).astype(int), 0, ZS - 1)
        ir = np.clip((tr * ZS / IMG).astype(int), 0, ZS - 1)
        vis = V @ v.d >= np.minimum(zbuf[ir * ZS + ic], near[ir * ZS + ic]) - 1.5
        ci = np.clip(tc.astype(int), 0, IMG - 1)
        ri = np.clip(tr.astype(int), 0, IMG - 1)
        ok = vis & inside[ri, ci]
        cosv = np.clip(N @ v.d, 0, 1) * ok
        w = cosv ** R_VIEW_POWER
        if name.endswith('mirror') or name == 'top':
            w *= 0.7
        cv = cm[ri, ci]
        acc += w[:, None] * cv
        wsum += w * cv.sum(1)
        cbest = np.maximum(cbest, cosv)
    good = (wsum > 1e-3) & (cbest >= MIN_COS * 0.9)
    S = np.zeros((len(V), 3))
    S[good] = acc[good] / wsum[good, None]
    return S, good


def _components_graph(A, mask: np.ndarray):
    from scipy.sparse.csgraph import connected_components
    idx = np.nonzero(mask)[0]
    sub = A[idx][:, idx]
    n, lab = connected_components(sub, directed=False)
    return idx, lab, n


def _relabel_small(A, lab: np.ndarray, k: int, V: np.ndarray, min_ext: float, keep: np.ndarray, allow=None, big: float = 0.0) -> np.ndarray:
    """ラベル k の塊で、外接の箱の最大の辺が min_ext 未満のものを、まわりで一番多いラベルにする"""
    idx, cl, n = _components_graph(A, lab == k)
    if n == 0:
        return lab
    out = lab.copy()
    for c in range(n):
        m = idx[cl == c]
        if keep[m].any():
            continue
        p = V[m]
        lim = min_ext if allow is None or allow[m].any() else max(big, min_ext)
        if (p.max(0) - p.min(0)).max() >= lim:
            continue
        nb = A[m].indices
        nb = nb[lab[nb] != k]
        if len(nb) == 0:
            continue
        out[m] = np.bincount(lab[nb], minlength=3).argmax()
    return out


def _drop_blobs(A, lab: np.ndarray, V: np.ndarray, F: np.ndarray, part: np.ndarray, band: float) -> np.ndarray:
    """真鍮は「帯」（縁の細い線）か「部品まるごと」（角・棘）だけ。太い塊（幅 = 面積 / 長さ が band より大きく、
    部品の R_WHOLE に満たない）は視点のずれのしみなので白磁にする"""
    fa = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    va = np.zeros(len(V))
    for j in range(3):
        np.add.at(va, F[:, j], fa / 3.0)
    idx, cl, n = _components_graph(A, lab == 1)
    out = lab.copy()
    for c in range(n):
        m = idx[cl == c]
        p = V[m]
        ext = (p.max(0) - p.min(0)).max()
        pk = np.bincount(part[m]).argmax()
        whole = len(m) >= R_WHOLE * (part == pk).sum()
        if not whole and va[m].sum() / max(ext, 1e-6) > band:
            out[m] = 0
    return out


def paint_regions(t: str, cfg, views: dict, shell_objs, joints, mats) -> dict:
    """殻の部品を、頂点の票 → つながりで掃除 → 境の線で三角形を切る → 面ごとの材質（白磁・真鍮・黒鉛）にする"""
    import bpy
    H = cfg['height']
    radius = H / 60.0
    joint_r = cfg.get('joint_r', 0.04) * H
    zone = cfg.get('dark_zone')
    brass_min = float(os.environ.get('BANKI_R_BRASS_MIN', 0.08))   # 真鍮の塊の最小の長さ（全高に対する比。太い塊は _drop_blobs が消すので、型ごとの brass_min より短くてよい)
    # 全部品の頂点と三角形（世界 cm）をまとめる（つながりは部品の中だけ）
    Vs, Fs, P, off = [], [], [], 0
    for k, ob in enumerate(shell_objs):
        me = ob.data
        me.calc_loop_triangles()
        mw = np.array(ob.matrix_world)
        co = np.array([v.co for v in me.vertices]).reshape(-1, 3)
        Vs.append((co @ mw[:3, :3].T + mw[:3, 3]) * 100.0)
        Fs.append(np.array([tt.vertices for tt in me.loop_triangles]).reshape(-1, 3) + off)
        P.append(np.full(len(co), k))
        off += len(co)
    V, F, part = np.concatenate(Vs), np.concatenate(Fs), np.concatenate(P)
    A = _adjacency(F, len(V))
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    Nv = np.zeros_like(V)
    for j in range(3):
        np.add.at(Nv, F[:, j], fn)
    Nv /= np.maximum(np.linalg.norm(Nv, axis=1, keepdims=True), 1e-9)
    # 票に使う向きは、ならした法線（面の細かなでこぼこで、正面の点が横の絵の色を拾わないように）
    Nv = _diffuse(A, Nv, R_NORMAL_SMOOTH)
    Nv /= np.maximum(np.linalg.norm(Nv, axis=1, keepdims=True), 1e-9)
    # 1. 票
    el = np.linalg.norm(V[F[:, 1]] - V[F[:, 0]], axis=1).mean()
    S, good = _vertex_votes(views, V, Nv, V[F], el)
    raw_dark = S[:, 2] >= R_DARK
    # 見えていない頂点は、つながりに沿って見えている頂点の票を広げる
    if (~good).any():
        known = good.copy()
        for _ in range(60):
            if known.all():
                break
            s = A @ (S * known[:, None])
            c = A @ known.astype(float)
            new = ~known & (c > 0)
            S[new] = s[new] / c[new, None]
            known |= new
        S[~known] = (1, 0, 0)
    # 2. 部品の規則：黒鉛は関節のまわり・部品の境・型の暗い領域だけ。関節の部品と回転軸の球は必ず黒鉛
    from scipy.spatial import cKDTree
    pnames = [o.name.split('.')[0] for o in shell_objs]
    allow = np.zeros(len(V), bool)
    if zone is not None:
        allow |= zone(V[:, 0], V[:, 1], V[:, 2])
    forced = np.array([n.startswith(JOINT_PARTS) for n in pnames])[part]
    # 関節は回転軸を中心の球（半径 RJ）で黒鉛にする。境は球の面（きれいな円）。まわりの絵の暗い所（関節の円盤の
    # 投影のずれ）は票から外す（しみにしない）
    # 部品の継ぎ目：ほかの部品の面に近い所（距離 < RS）を黒鉛の帯にする（板と板の間の暗い隙間。境は距離の等高線）
    RJ = R_JOINT * joint_r
    q = np.full(len(V), np.inf)      # 関節の球・継ぎ目までの距離（半径で割った値。1 未満が黒鉛）
    if joints is not None and len(joints):
        q = cKDTree(joints).query(V)[0] / RJ
    if R_SEAM > 0:
        for k in range(len(shell_objs)):
            m = part == k
            if m.all():
                continue
            ds = cKDTree(V[~m]).query(V[m], distance_upper_bound=4 * R_SEAM * H)[0]
            q[m] = np.minimum(q[m], ds / (R_SEAM * H))
    forced |= q < 1.0
    near = (q < R_JOINT_CLEAR) & ~forced
    S[near, 0] += S[near, 2]
    S[near, 2] = 0
    # 3. ならして分ける
    S0 = S.copy()
    # 真鍮の縁は細いので、ならす回数を少なくした票で決める（黒鉛・白磁は強くならした票）
    Sb = _diffuse(A, S, R_DIFFUSE_BRASS)
    S = _diffuse(A, S, R_DIFFUSE)
    zin = zone(V[:, 0], V[:, 1], V[:, 2]) if zone is not None else np.zeros(len(V), bool)
    lab = np.where(S[:, 2] >= np.where(zin, R_DARK_ZONE, R_DARK), 2, np.where(Sb[:, 1] >= R_BRASS, 1, 0))
    # 飾りの小さな部品（角・棘・ひれ・冠）は部品まるごと 1 色（票の真鍮の割合で真鍮か白磁か。閂と同じ考え）
    whole = np.zeros(len(V), bool)
    for k, n in enumerate(pnames):
        if n.startswith(WHOLE_PARTS):
            m = part == k
            whole |= m
            lab[m] = 1 if S0[m, 1].mean() >= R_WHOLE_BRASS else 0
            log(f'  paint {n}: brass vote {S0[m, 1].mean():.2f} -> {"brass" if lab[m][0] == 1 else "ivory"}')
    lw = lab.copy()
    lab[forced] = 2
    # 4. つながりで掃除：真鍮の帯の途切れを埋め、小さな黒鉛・真鍮の塊と小さな白磁の島を消す
    for _ in range(R_CLOSE):
        grow = (lab == 0) & ((A @ (lab == 1).astype(float)) >= 2)
        lab[grow] = 1
    for _ in range(R_CLOSE):
        shrink = (lab == 1) & ((A @ (lab == 0).astype(float)) >= 2) & ~(Sb[:, 1] >= R_BRASS)
        lab[shrink] = 0
    lab = _relabel_small(A, lab, 2, V, R_DARK_MIN * H, forced, allow, R_DARK_BIG * H)
    lab = _relabel_small(A, lab, 1, V, brass_min * H, np.zeros(len(V), bool))
    lab = _drop_blobs(A, lab, V, F, part, R_BAND * H)
    lab = _relabel_small(A, lab, 0, V, R_IVORY_MIN * H, np.zeros(len(V), bool))
    # 多数決（自分 + 隣）を R_MAJORITY 回：ぎざぎざの 1 点の出っ張りを消す
    for _ in range(R_MAJORITY):
        cnt = np.stack([(A @ (lab == k).astype(float)) + (lab == k) for k in range(3)], 1)
        new = cnt.argmax(1)
        lab = np.where(forced, 2, np.where(cnt.max(1) > cnt[np.arange(len(lab)), lab], new, lab))
    fix = whole & ~forced
    lab[fix] = lw[fix]
    if os.environ.get('BANKI_DEBUG'):
        np.savez(os.environ["BANKI_DEBUG"], F=F, V=V, N=Nv, S=S, lab=lab, part=part, allow=allow, forced=forced, good=good)
    # 5. 境の線：ラベルの 1 つ有りの場をならし、辺の上で 2 つのラベルの場が等しくなる所で三角形を切る
    Fld = _diffuse(A, np.eye(3)[lab], R_CUT_SMOOTH)
    # 関節の球の近くは、球の距離で境を決める（円の境）
    nj = q < 2.0
    if nj.any():
        g = np.clip(1.5 - q[nj], 0, 1)
        rest = Fld[nj, :2] / np.maximum(Fld[nj, :2].sum(1, keepdims=True), 1e-6)
        Fld[nj, :2] = rest * (1 - g)[:, None]
        Fld[nj, 2] = g
    counts = np.bincount(lab, minlength=3)
    mlist = [mats['ivory'], mats['brass'], mats['dark']]
    for k, ob in enumerate(shell_objs):
        sel = part == k
        base = np.nonzero(sel)[0][0]
        fk = F[part[F[:, 0]] == k]
        verts, faces, fmat = _cut(V, fk, lab, Fld)
        # 重なった・つぶれた三角形を先に除く（validate が面を消すと材質の番号がずれる）
        seen, keep = set(), []
        for i, fc in enumerate(faces):
            key = tuple(sorted(fc))
            if len(set(fc)) == 3 and key not in seen:
                seen.add(key)
                keep.append(i)
        faces = [faces[i] for i in keep]
        fmat = [int(fmat[i]) for i in keep]
        mw = np.array(ob.matrix_world)
        loc = ((np.asarray(verts) * 0.01) - mw[:3, 3]) @ np.linalg.inv(mw[:3, :3]).T
        me = bpy.data.meshes.new(ob.data.name + '_r')
        me.from_pydata(loc.tolist(), [], faces)
        me.validate()
        if len(me.polygons) != len(faces):
            log(f'  paint {ob.name}: validate changed faces {len(faces)} -> {len(me.polygons)}')
        for m in mlist:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', fmat)
        me.polygons.foreach_set('use_smooth', [True] * len(faces))
        old = ob.data
        nm = old.name
        ob.data = me
        bpy.data.meshes.remove(old)
        me.name = nm
    smooth_by_angle(shell_objs)
    res = {'ivory': int(counts[0]), 'brass': int(counts[1]), 'dark': int(counts[2])}
    log(f'  paint {t}: vertices {res}')
    return res


def _cut(V: np.ndarray, F: np.ndarray, lab: np.ndarray, Fld: np.ndarray):
    """三角形を頂点のラベルの境で切る。境の点は辺ごとに 1 つ（隣の三角形と共有）。戻り値：(頂点, 面, 面の材質の番号)"""
    vid = {}
    verts = []

    def vert(i):
        if i not in vid:
            vid[i] = len(verts)
            verts.append(V[i])
        return vid[i]

    emid = {}

    def edge(i, j):
        key = (i, j) if i < j else (j, i)
        if key not in emid:
            a, b = key
            la, lb = lab[a], lab[b]
            sa = Fld[a, la] - Fld[a, lb]
            sb = Fld[b, la] - Fld[b, lb]
            tt = sa / (sa - sb) if (sa > 0 and sb < 0) else 0.5
            tt = min(max(tt, 0.2), 0.8)
            emid[key] = len(verts)
            verts.append(V[a] * (1 - tt) + V[b] * tt)
        return emid[key]
    faces, fmat = [], []
    for tri in F:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        la, lb, lc = lab[a], lab[b], lab[c]
        if la == lb == lc:
            faces.append([vert(a), vert(b), vert(c)])
            fmat.append(la)
            continue
        if la != lb and lb != lc and la != lc:
            cen = len(verts)
            verts.append((V[a] + V[b] + V[c]) / 3.0)
            pab, pbc, pca = edge(a, b), edge(b, c), edge(c, a)
            for q, l in (([vert(a), pab, cen, pca], la), ([vert(b), pbc, cen, pab], lb), ([vert(c), pca, cen, pbc], lc)):
                faces += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
                fmat += [l, l]
            continue
        # 2 つが同じ：回して (x, y) が同じ、z が違う形にする
        for (x, y, z) in ((a, b, c), (b, c, a), (c, a, b)):
            if lab[x] == lab[y]:
                break
        pxz, pyz = edge(x, z), edge(y, z)
        faces += [[vert(x), vert(y), pyz], [vert(x), pyz, pxz], [pxz, pyz, vert(z)]]
        fmat += [lab[x], lab[x], lab[z]]
    return np.array(verts), faces, fmat


# ---------------------------------------------------------------- 発光の板（絵の琥珀色を形の表面へ落とす）

def decal(view: View, box, objs, cell_px: float, name: str, mat, parent_ob, bright: float = 0.6):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    rgb = view.rgba[..., :3].astype(np.float32) / 255.0
    m = amber_mask(rgb, bright) & view.alpha
    m = ndi.binary_opening(m, iterations=2)
    # 世界の箱を絵へ写して、その中だけ使う
    (bx0, bx1), (by0, by1), (bz0, bz1) = box
    corners = np.array([[x, y, z] for x in (bx0, bx1) for y in (by0, by1) for z in (bz0, bz1)], float)
    cc, rr = view.project(corners)
    c0, c1 = int(max(cc.min(), 0)), int(min(cc.max(), IMG))
    r0, r1 = int(max(rr.min(), 0)), int(min(rr.max(), IMG))
    sub = np.zeros_like(m)
    sub[r0:r1, c0:c1] = m[r0:r1, c0:c1]
    if sub.sum() < 30:
        log(f'  decal {name}: no amber in {view.name}')
        return None
    # 格子：セルの中心で琥珀色の割合 > 0.35
    rows = np.nonzero(sub.any(1))[0]
    cols = np.nonzero(sub.any(0))[0]
    gc = np.arange(cols[0] - cell_px, cols[-1] + 2 * cell_px, cell_px)
    gr = np.arange(rows[0] - cell_px, rows[-1] + 2 * cell_px, cell_px)
    cov = np.zeros((len(gr) - 1, len(gc) - 1))
    for i in range(len(gr) - 1):
        for j in range(len(gc) - 1):
            blk = sub[int(gr[i]):int(gr[i + 1]), int(gc[j]):int(gc[j + 1])]
            cov[i, j] = blk.mean() if blk.size else 0
    cells = cov > 0.35
    # 画素 → 世界の点（視線に沿う直線上）。r・u の基底で逆算（stretch を戻す）
    deps = []
    for ob in objs:
        deps.append(ob)
    bm_list = []
    import bmesh
    bm = bmesh.new()
    for ob in deps:
        tmp = ob.data.copy()
        tmp.transform(ob.matrix_world)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    st = view.stretch

    def ray_point(col, row):
        a = (col - view.c0) / view.sr
        b = (view.r0 - row) / view.su
        q = view.r * a + view.u * b          # 絵の cm
        p = q * st * 0.01 + view.d * 5.0     # 世界 m、カメラの側の遠く
        hit = tree.ray_cast(Vector(p.tolist()), Vector((-view.d).tolist()), 20.0)
        if hit[0] is None:
            return None
        return np.array(hit[0]) + view.d * 0.004
    vid = {}
    verts, faces = [], []
    for i in range(cells.shape[0]):
        for j in range(cells.shape[1]):
            if not cells[i, j]:
                continue
            quad = []
            for (ii, jj) in ((i + 1, j), (i + 1, j + 1), (i, j + 1), (i, j)):
                if (ii, jj) not in vid:
                    pt = ray_point(gc[jj], gr[ii])
                    vid[(ii, jj)] = None if pt is None else len(verts)
                    if pt is not None:
                        verts.append(pt)
                quad.append(vid[(ii, jj)])
            if None not in quad:
                faces.append(quad)
    if not faces:
        return None
    verts = np.array(verts) * 100.0
    # 面の向き：視点の方を向くように
    f0 = faces[0]
    nrm = np.cross(verts[f0[1]] - verts[f0[0]], verts[f0[2]] - verts[f0[0]])
    if nrm @ view.d < 0:
        faces = [f[::-1] for f in faces]
    piv = np.array(parent_ob.matrix_world.translation) * 100.0
    ob = new_object(name, verts, faces, mat, piv, np.eye(3), smooth=True)
    mw = ob.matrix_world.copy()
    ob.parent = parent_ob
    ob.matrix_world = mw
    log(f'  decal {name}: {len(faces)} quads from {view.name}')
    return ob


# ---------------------------------------------------------------- 組み立て

def build(t: str, out_glb: str) -> dict:
    import bpy
    from mathutils import Matrix
    cfg = TYPES[t]
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    views = build_views(t, cfg)
    occ, xs, ys, zs, vox = build_hull(t, cfg, views)
    lab = label_parts(cfg, occ, xs, ys, zs)
    names = ['body'] + [p[0] for p in cfg['parts']]
    parents = {'body': None, **{p[0]: p[1] for p in cfg['parts']}}
    specs = {'body': (cfg['body_pivot'], X), **{p[0]: (p[3], p[4]) for p in cfg['parts']}}
    mats = make_materials(t, None)
    raw = {}
    for i, n in enumerate(names):
        mask = lab == i
        if mask.sum() < 20:
            log(f'  part {n}: empty')
            continue
        mm = part_mesh(mask, xs, ys, zs, vox)
        if mm is None:
            continue
        raw[n] = (mm, pivot_of(specs[n][0], mask, xs, ys, zs))
    total = sum(len(mm[1]) for mm, _ in raw.values())
    ratio = cfg['tris'] * (R_TRIS if PAINT == 'region' else 1.0) / max(total, 1)
    objs = {}
    for n, ((v, f), piv) in raw.items():
        ob = new_object(n, v, f, mats['shell'], piv, axis_matrix(specs[n][1]))
        decimate(ob, ratio * (1.6 if len(f) * ratio < 150 else 1.0))
        objs[n] = ob
    shell_objs = list(objs.values())
    smooth_by_angle(shell_objs)
    # 車輪（円柱、黒鉛色）と真鍮の軸の蓋
    for n, par, c, rad, w in cfg.get('wheels', []):
        v, f = cylinder(c, rad, w, 18)
        ob = new_object(n, v, f, mats['dark'], np.array(c, float), np.eye(3), smooth=False)
        for suffix, (vv, ff), mt in (('_cover', c_disc(c, rad * 0.8, w, 20), mats['shell_flat']),
                                     ('_hub', cylinder((c[0] + np.sign(c[0]) * (w / 2 + 1.6), c[1], c[2]), rad * 0.22, 1.6, 10),
                                      mats['brass'])):
            cap = new_object(n + suffix, vv, ff, mt, np.array(c, float), np.eye(3), smooth=False)
            mw = cap.matrix_world.copy()
            cap.parent = ob
            cap.matrix_world = mw
        objs[n] = ob
        parents[n] = par
    for n, par, c, size in cfg.get('boxes', []):
        c = np.array(c, float)
        h = np.array(size, float) / 2
        v = np.array([c + h * [sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
        f = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
        objs[n] = new_object(n, v, f, mats['dark'], c, np.eye(3), smooth=False)
        parents[n] = par
    # 階層（親子）：世界の姿勢を保ったまま
    root = bpy.data.objects.new(f'banki_{t}', None)
    bpy.context.scene.collection.objects.link(root)
    for n, ob in objs.items():
        par = objs.get(parents.get(n)) if parents.get(n) else root
        mw = ob.matrix_world.copy()
        ob.parent = par if par is not None else root
        ob.matrix_world = mw
    jn = [n for n in cfg.get('joints', []) if n in raw]
    joints = np.array([raw[n][1] for n in jn]) if jn else None
    if PAINT == 'region':
        # 面ごとの平らな材質（テクスチャなし）。白磁は名前を banki_<型>_shell のままにする（Godot の被弾の光が使う）
        mats['shell'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*srgb_to_linear(IVORY), 1)
        paint_regions(t, cfg, views, shell_objs, joints, {'ivory': mats['shell'], 'brass': mats['brass'], 'dark': mats['dark']})
    else:
        bake_texture(t, cfg, views, shell_objs, raw, joints, mats)
    # 発光の板
    s = scale_of(cfg)
    for name, vname, box, par, *opt in cfg['decals']:
        v = views.get(vname) or views.get('side')
        ob = decal(v, box, shell_objs, max(vox * s * 0.5, 12.0),
                   name, mats[name], objs.get(par, objs['body']), *opt)
        if ob is not None:
            objs[name] = ob
    tri_count = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in bpy.data.objects if ob.type == 'MESH')
    # 書き出し
    os.makedirs(os.path.dirname(out_glb), exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_yup=True, export_apply=False,
                              export_animations=False, use_selection=True)
    info = {'type': t, 'triangles': tri_count, 'voxel_cm': round(vox, 2), 'parts': sorted(objs.keys()),
            'seconds': round(time.time() - t0, 1), 'glb': os.path.relpath(out_glb, REPO)}
    log(json.dumps(info, ensure_ascii=False))
    return info


def bake_texture(t, cfg, views, shell_objs, raw, joints, mats) -> None:
    """従来の色（BANKI_PAINT=bake）：UV を開いて絵を投影で焼いたテクスチャ 1 枚"""
    import bpy
    smart_uv(shell_objs)
    tris, uvs, tid = mesh_world(shell_objs, ids=True)
    tex = bake(views, tris, uvs, 1024, cfg['height'] / 60.0, tid, [o.name.split('.')[0] for o in shell_objs],
               joints, cfg.get('joint_r', 0.04) * cfg['height'], cfg['height'], cfg.get('dark_zone'), cfg.get('brass_min', BRASS_MIN))
    from PIL import Image
    os.makedirs(os.path.join(WORK, 'tex'), exist_ok=True)
    tex_path = os.path.join(WORK, 'tex', f'banki_{t}.png')
    Image.fromarray((np.clip(tex, 0, 1) * 255).astype(np.uint8)).save(tex_path)
    img = bpy.data.images.load(tex_path)
    nt = mats['shell'].node_tree
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = img
    nt.links.new(tn.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])


# ---------------------------------------------------------------- 確認（絵と Cycles の画像を並べる）

TILE = int(os.environ.get("BANKI_TILE", 400))   # 比較の画像の 1 枚の大きさ（px）


def review_views(t: str):
    """比較する視点：(名前, 絵, カメラの向き, 上, 反転)"""
    cfg = TYPES[t]
    sname, cs, fl = cfg['side']
    sx, fl3 = THREE_Q[t]
    out = [('front', 'front', (0, -1, 0), Z, False), (sname, sname, (cs, 0, 0), Z, fl),
           ('back', 'back', (0, 1, 0), Z, False), ('top', 'top', (0, 0, 1), (0, 1, 0), False),
           ('front_right45', 'front_right45', (sx * 0.7071, -0.7071, 0), Z, fl3)]
    for n2, cs2, fl2 in cfg.get('extra_sides', []):
        out.insert(2, (n2, n2, (cs2, 0, 0), Z, fl2))
    return out


def render_review(t: str, out_dir: str, samples: int = 16) -> dict:
    import bpy
    from mathutils import Matrix, Vector
    from PIL import Image, ImageDraw
    cfg = TYPES[t]
    s = scale_of(cfg)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.resolution_x = sc.render.resolution_y = TILE
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.8, 0.8, 0.82, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    sc.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 2.0
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = IMG / s / 100.0
    cam.data.clip_end = 50
    sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    # 絵の中央の画素（1024, 1024）に写る世界の点を、カメラの中心にする
    zc = (cfg['rows'][1] - IMG / 2) / s / 100.0
    tiles, scores = [], {}
    bg = (150, 150, 155)
    for name, art, d, up, flip in review_views(t):
        p = os.path.join(SRC, f'{t}_3d_{art}_r2.png')
        if not os.path.exists(p):
            continue
        d = Vector(d).normalized()
        if name == 'top':
            center = Vector((0, 0, 0))
        else:
            center = Vector((0, 0, zc))
        z = d
        x = Vector(up).cross(z).normalized()
        y = z.cross(x)
        rot = Matrix((x, y, z)).transposed()
        cam.matrix_world = Matrix.Translation(center + d * 10.0) @ rot.to_4x4()
        sun.matrix_world = (rot @ Matrix.Rotation(math.radians(-25), 3, 'X')
                            @ Matrix.Rotation(math.radians(-20), 3, 'Y')).to_4x4()
        rp = os.path.join(out_dir, f'render_{t}_{name}.png')
        sc.render.filepath = rp
        bpy.ops.render.render(write_still=True)
        ren = Image.open(rp).convert('RGBA')
        if flip:
            ren = ren.transpose(Image.FLIP_LEFT_RIGHT)
        artim = Image.open(p).convert('RGBA')
        if name == 'top':
            # 真上の絵は縮尺が違うので、外接の箱どうしを合わせて比べる（盾型は前後を反転した絵）
            if cfg.get('top_flip'):
                artim = artim.transpose(Image.FLIP_TOP_BOTTOM)
            artim = _fit_bbox(artim, ren)
        else:
            artim = artim.resize((TILE, TILE), Image.LANCZOS)
            st = cfg.get('y_stretch', 1.0)
            if st != 1.0 and abs(d.x) > 0.1:
                k = st if abs(d.y) < 0.1 else math.hypot(0.7071 * st, 0.7071)
                wn = int(round(TILE * k))
                sq = artim.resize((wn, TILE), Image.LANCZOS)
                artim = Image.new('RGBA', (TILE, TILE), (0, 0, 0, 0))
                artim.paste(sq, ((TILE - wn) // 2, 0))
        a1 = np.asarray(artim)[..., 3] > 64
        a2 = np.asarray(ren)[..., 3] > 64
        scores[name] = round(float((a1 & a2).sum() / max(1, (a1 | a2).sum())), 3)
        diff = np.zeros((TILE, TILE, 3), np.uint8) + np.array(bg, np.uint8)
        diff[a1 & ~a2] = (220, 60, 60)
        diff[a2 & ~a1] = (60, 110, 230)
        diff[a1 & a2] = (235, 235, 235)
        row = []
        for im in (artim, ren):
            tt = Image.new('RGB', (TILE, TILE), bg)
            tt.paste(im, (0, 0), im)
            row.append(tt)
        row.append(Image.fromarray(diff))
        tiles.append((name, row))
    cols = 2
    W = Image.new('RGB', (cols * 3 * TILE, ((len(tiles) + 1) // cols) * (TILE + 24)), (40, 40, 44))
    dr = ImageDraw.Draw(W)
    for k, (name, row) in enumerate(tiles):
        x0 = (k % cols) * 3 * TILE
        y0 = (k // cols) * (TILE + 24)
        dr.text((x0 + 6, y0 + 4), f'{t} {name}  art | render | silhouette (red=art only, blue=model only)  IoU {scores[name]}',
                fill=(230, 230, 230))
        for j, im in enumerate(row):
            W.paste(im, (x0 + j * TILE, y0 + 24))
    W.save(os.path.join(out_dir, f'{t}_compare.png'))
    small = W.copy()
    small.thumbnail((1600, 1600))
    small.convert('RGB').save(os.path.join(out_dir, f'{t}_compare_small.jpg'), quality=88)
    return scores


def _fit_bbox(art, ren):
    """絵の外形の箱を、描いた画像の外形の箱に合わせて置き直す（真上の比較用）"""
    from PIL import Image
    a = np.asarray(art)[..., 3] > 64
    b = np.asarray(ren)[..., 3] > 64
    if not b.any():
        return art.resize((TILE, TILE), Image.LANCZOS)
    ra, ca = np.nonzero(a.any(1))[0], np.nonzero(a.any(0))[0]
    rb, cb = np.nonzero(b.any(1))[0], np.nonzero(b.any(0))[0]
    crop = art.crop((ca[0], ra[0], ca[-1] + 1, ra[-1] + 1)).resize((cb[-1] + 1 - cb[0], rb[-1] + 1 - rb[0]), Image.LANCZOS)
    out = Image.new('RGBA', (TILE, TILE), (0, 0, 0, 0))
    out.paste(crop, (cb[0], rb[0]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--type', choices=list(TYPES), action='append')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--review', action='store_true', help='絵との比較の画像を build/banki/review/ に作る')
    args = ap.parse_args()
    types = list(TYPES) if args.all or not args.type else args.type
    fetch_art()
    report = {}
    rp = os.path.join(WORK, 'review', 'report.json')
    if os.path.exists(rp):
        with open(rp) as f:
            report = json.load(f)
    for t in types:
        # 既定は部品を形で組む方式（banki_parts.py、閂と同じ）。その型の組み方がまだない・BANKI_MODEL=hull のときは視体積
        import banki_parts as BP
        if os.environ.get('BANKI_MODEL', 'parts') != 'hull' and t in BP.BUILDERS:
            info = BP.build(t, os.path.join(MODELS, f'banki_{t}.glb'))
        else:
            info = build(t, os.path.join(MODELS, f'banki_{t}.glb'))
        if args.review:
            info['iou'] = render_review(t, os.path.join(WORK, 'review'))
            log(f'{t} IoU {info["iou"]}')
        report[t] = info
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    with open(rp, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
