"""平らに塗る：絵は「どこが何色か」を決めるのにだけ使い、部位ごとに spec の 1 色で塗る（texture.py から呼ぶ）。

前のやり方（texture.py の 'proj'）は、各方向の絵の色をそのまま面に貼っていた。絵どうしが数 cm 食い違い、
絵の陰影と筆のむらもそのまま写るので、しみ・むら（特に顔の縁・耳・もみあげ・ほお）が出た。
ナゴミ・閂のように「部位ごとに平らな色」にすると絵の画風（W0 A 案：平らな色、線なし）に合う。

■ 体（paint_body）
  1. 焼いた色（視点の多数決の色、texel ごと）を spec の色の表（PALETTE）のどれかに分ける。表の色を出発点に、
     実際の絵の色の中央値へ少し寄せながら 3 回分け直す（絵の陰影で暗い所も同じ色に入るように）。
  2. 面の上で掃除する：texel を 3D の小さな箱（CELL、部位と法線の向きも鍵）にまとめ、箱のつながり
     （3D の近さ・法線の近さ。UV の継ぎ目をまたぐ）の上で、多数決のぼかし → 小さな島（3D の面積が
     MIN_AREA より小さい）を周りの色へ併合する。バックル・膝の琥珀・指先などの小さな本物の模様は、
     色・部位ごとに小さい閾値にして残す。
  3. 各 texel の色は、近くの箱の色の重み付きの多数決で決め、境目だけ 2 色を細く混ぜる（なめらかな境目・
     アンチエイリアス）。陰影は焼かない（光はゲームが付ける）。
■ 顔（paint_face_atlas）
  顔の絵の 4 表情の 2×2 の画像：肌の色の画素 → 体と同じ平らな肌色（継ぎ目が出ない）。目・眉・まつ毛・口
  （肌に囲まれた小さな塊）は絵の色のまま。髪・ゴーグルなど大きな塊・縁に届く塊は色の表で平らに塗る。
  鼻・ほおの陰影・赤みは肌として消える。
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy import sparse  # noqa: E402
from scipy.sparse.csgraph import connected_components  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from recon import char as CH  # noqa: E402

# spec_haru_3d.md の基準 hex（絵の色をスポイトしない。W0 の基準色）
PALETTE = CH.p('flat.PALETTE', {
    'brick': '#B75B43',      # 上着・ズボン・足首のカフ
    'ivory': '#F3E9D2',      # シャツ・肩板・太もも板・膝・すね側板・爪先・背中パネル
    'graphite': '#444641',   # 帯・手袋・暗い支持部・ゴーグル枠・靴底
    'brass': '#A98749',      # バックル・レール
    'umber': '#594333',      # 髪・襟・靴・すねの中央
    'amber': '#FFBC52',      # レンズ・膝の継ぎ目（ゲームで発光）
    'skin': '#E7B58D',       # 顔・指先・首
})
# 部位ごとに使わない色（uvparts.region_of_point：0 頭、1 胴、2/3 腕、4/5 手、6/7 脚）
FORBID = CH.p('flat.FORBID', {'0': ['ivory'], '4': ['brick', 'umber', 'amber'], '5': ['brick', 'umber', 'amber']})
# 髪・襟・靴・すねの中央の茶（umber）は、胴・腕では襟の高さより上、脚では膝より下だけ（絵の陰で暗くなった
# 上着の赤が茶に分けられて、帯の縁・脇にしみが出るのを防ぐ）
# （ハルの絵の襟の内側は上着の赤の陰なので、胴・腕には茶を使わない）
UMBER_Z = CH.p('flat.UMBER_Z', {'torso_min': 9.0, 'leg_max': 0.43})
# 首まわりのフードの襟（胴のうち、この高さより上で左右の中心に近い所）は暗い色（帯・茶）にしない（絵の陰のしみ）
NECK_NO_DARK = CH.p('flat.NECK_NO_DARK', {'z_min': 1.13, 'x': 0.075})
BOOST = CH.p('flat.BOOST', {'brass': 1.0, 'amber': 1.5})   # 多数決で細い模様（バックルの枠・琥珀の点）が消えないように
BRASS_TORSO_X = CH.p('flat.BRASS_TORSO_X', 0.03)
# 頭の琥珀（ゴーグルのレンズ）は、ぼかすと角が丸くなるので、箱の素の多数決のまま（レンズの角ばった形を残す）
SHARP_HEAD = CH.p('flat.SHARP_HEAD', ['amber'])
L_WEIGHT = 0.5          # 分けるときの明るさの差の重み（絵の陰影は主に明るさを変えるので軽く）
CENTER_PULL = 0.5       # 表の色から、分けた色の中央値へ寄せる割合
CELL = 0.003            # 掃除の箱の大きさ（m）
SMOOTH_ITERS = 4        # 多数決のぼかしの回数
SMOOTH_SIGMA = 1.0      # そのぼかしの幅（箱の何倍）
MIN_AREA = 3.5e-4       # これより小さい島（m²）は周りへ併合
MIN_AREA_LABEL = CH.p('flat.MIN_AREA_LABEL', {'brass': 0.4e-4, 'amber': 0.25e-4})
MIN_AREA_HAND = 0.3e-4  # 手（部位 4・5）の島の閾値（指先の肌・指の間）
MIN_AREA_HEAD = CH.p('flat.MIN_AREA_HEAD', {'default': 5e-4, 'amber': 1e-4})   # 頭（髪の先の肌色・ほおの髪の色のしみ）
EDGE_SIGMA = 1.0        # texel の色を決める近くの箱の重みの幅（箱の何倍）
EDGE_SHARP = 0.10       # 境目の混ぜる幅（2 色の重みの比 0.5 ± これ）


# 胸・襟・首・帯の前（正面の絵がいちばんきれいに描いている所）は、多視点の多数決でなく、正面の絵そのものを 2D で色に分けて
# 掃除した「色の地図」を正面からまっすぐ貼る（シャツの V・フードの襟・帯の肩ひも・バックルの形が絵どおりになる）
# 上を向いた面（フード・肩の上）も正面の絵の縁の色を引く（ndv の下限を 0 近くに）。絵の襟の内側の暗い陰は茶に分けてから
# 上着の赤にする（umber_to_brick_z より下）
FRONT_ZONE = CH.p('flat.FRONT_ZONE', {'z': (0.79, 1.215), 'ramp_z': 0.02, 'ndv': (-0.05, 0.15),
                                      'labels': ['brick', 'ivory', 'graphite', 'brass', 'skin', 'umber'],
                                      'umber_to_brick_z': 1.215, 'arm_z_min': 1.08, 'skin_x': 0.065, 'skin_z_max': 1.19, 'back_skin_z_min': 1.17, 'back_z_top': 1.26, 'back_neck_z': 1.185, 'back_neck_x': 0.055,
                                      'views': ['front', 'back'],
                                      'sigma_px': 2.5, 'min_px': 150, 'min_px_brass': 12, 'l_weight': 0.3})
# ゴーグルは形の部品（hair.py の枠・レンズの輪郭）で塗る：レンズ＝琥珀、枠・橋＝グラファイト
GOGGLE_PAINT = CH.p('flat.GOGGLE_PAINT', True)
# 頭の形の部品の色は形から（hair.part_fields_at の場。絵の色は使わない。head_parts）：
#   頭（部位 0。と、胴の側の neck_z より上で肌か茶に塗られた首）はまず全部肌（顔・首・あごの下。あごの下や首の後ろはどの絵もよく見ていないので決まりで）。
#   髪の場（帽子・前髪・形の段が当てはめた房）の面の上（髪の場 > hair_tol）で頭の面より外（髪の場 − 頭の場 > hair_out）＝髪の茶、
#   耳（場 > ear）＝肌、ベルト（場 > strap）＝グラファイト。ゴーグルはこのあと GOGGLE_PAINT。ramp は境目を混ぜる幅（m）
# 体（頭より下）の塗り方：'views' ＝ 1 枚の絵のきれいな形（flat_views.py。4 回目）、'vote' ＝ 視点の多数決（前のやり方）。
# 環境変数 FLAT_BODY で上書きできる
BODY_PAINT = os.environ.get('FLAT_BODY') or CH.p('flat.BODY_PAINT', 'views')
# ヒモを部品にしたか（8 回目、ハル）：形の段の帯は髪の色に塗る
STRAP_PART = CH.p('flat.STRAP_PART', True)
HEAD_PARTS = CH.p('flat.HEAD_PARTS', {'strap': -0.0012, 'ear': -0.002, 'hair_tol': -0.004, 'hair_out': 0.001, 'ramp': 0.001,
                                      'neck_z': 1.15})


def log(msg: str) -> None:
    print(f'[flat {time.strftime("%H:%M:%S")}] {msg}', flush=True)


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB 0..1 → CIE Lab（D65）"""
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]], np.float32)
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883], np.float32)
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def classify(col: np.ndarray, names: list[str], forbid: np.ndarray | None = None, iters: int = 3,
             l_weight: float = L_WEIGHT):
    """色 (n,3) → 色の表の番号。forbid (n, len(names)) の真の所は選ばない"""
    lb = lab(col.astype(np.float32))
    ref = lab(np.stack([hex_rgb(PALETTE[k]) for k in names]))
    cen = ref.copy()
    for _ in range(iters):
        d = lb[:, None, :] - cen[None]
        d[..., 0] *= l_weight
        d = (d ** 2).sum(-1)
        if forbid is not None:
            d[forbid] = 1e9
        lbl = np.argmin(d, 1)
        for i in range(len(names)):
            m = lbl == i
            if m.sum() > 100:
                cen[i] = ref[i] + CENTER_PULL * (np.median(lb[m], 0) - ref[i])
    return lbl, cen


# ---------------------------------------------------------------- 正面の絵の色の地図・ゴーグル

def front_label_maps(names: list[str], cam, view: str = 'front') -> tuple[np.ndarray, dict]:
    """正面（背面）の絵の、FRONT_ZONE の高さの帯を色に分け、2D で掃除した色ごとのなめらかな地図 (L, H, W)（texel は双線形で引く）"""
    fz = FRONT_ZONE
    path = os.path.join(CH.REPO, CH.CFG['work'], 'src', CH.CFG['views'][view]['file'])
    rgba = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32) / 255.0
    H, W = rgba.shape[:2]
    _, v_top = cam.project(np.array([0.0, 0.0, max(fz['z'][1], fz.get('back_z_top', 0)) + 0.03]))
    _, v_bot = cam.project(np.array([0.0, 0.0, fz['z'][0] - 0.03]))
    y0, y1 = max(0, int(v_top)), min(H, int(v_bot) + 1)
    sub = rgba[y0:y1]
    opaque = sub[..., 3] > 0.5
    allowed = [names.index(k) for k in fz['labels']]
    li, _ = classify(sub[..., :3].reshape(-1, 3)[opaque.ravel()], [names[i] for i in allowed], l_weight=fz['l_weight'])
    lab2 = np.full(opaque.shape, -1, int)
    lab2[opaque] = np.array(allowed)[li]
    rows_z = (cam.v0 - (np.arange(y0, y1) + 0.5)) / cam.ppm
    low = np.broadcast_to((rows_z < fz['umber_to_brick_z'])[:, None], lab2.shape)
    lab2[low & (lab2 == names.index('umber'))] = names.index('brick')
    # 肌は首の前（左右の中心の近く）だけ。襟の明るい折り目が肌に分けられないように
    cols_x = np.abs((np.arange(sub.shape[1]) + 0.5 - cam.u0) / cam.ppm)
    no_skin = (cols_x[None, :] > fz['skin_x']) & (rows_z[:, None] < fz['skin_z_max'])
    if view == 'back':   # 背中に肌は無い（首の後ろだけ）
        no_skin = no_skin | (rows_z[:, None] < fz['back_skin_z_min'])
    lab2[no_skin & (lab2 == names.index('skin'))] = names.index('brick')
    L = len(names)
    # 多数決のぼかし（mode filter）
    oh = np.stack([ndi.gaussian_filter((lab2 == i).astype(np.float32), fz['sigma_px']) for i in range(L)], 0)
    lab2 = np.where(opaque, np.argmax(oh, 0), -1)
    # 小さな島を周りの色へ
    ib = names.index('brass')
    merged = 0
    for _ in range(3):
        changed = False
        for i in range(L):
            m = lab2 == i
            if not m.any():
                continue
            cc, n = ndi.label(m)
            if not n:
                continue
            sizes = ndi.sum(m, cc, range(1, n + 1))
            lim = fz['min_px_brass'] if i == ib else fz['min_px']
            small = np.isin(cc, np.nonzero(sizes < lim)[0] + 1)
            if small.any():
                oh2 = oh.copy()
                oh2[i] = -1
                lab2[small] = np.argmax(oh2, 0)[small]
                merged += int((sizes < lim).sum())
                changed = True
        if not changed:
            break
    soft = np.zeros((L, H, W), np.float32)
    for i in range(L):
        soft[i, y0:y1] = ndi.gaussian_filter((lab2 == i).astype(np.float32), 0.8)
    return soft, {'rows': [int(y0), int(y1)], 'merged_islands_2d': merged}


def goggle_colour(pos: np.ndarray, nrm: np.ndarray, reg: np.ndarray, names: list[str]):
    """ゴーグルの部品の texel と、そこでの琥珀の割合（レンズ）。hair.py の輪郭（正面の絵の枠・レンズ）から"""
    from recon import hair as HR
    if not HR.PARTS.get('goggles'):
        return None, None
    g = HR.GOGGLES
    cand = np.nonzero((reg == 0) & (pos[:, 1] < -0.03) & (pos[:, 2] > g['z'][0] - 0.01) & (pos[:, 2] < g['z'][1] + 0.01))[0]
    x, z = pos[cand, 0], pos[cand, 2]
    mx = 2 * HR.GOGGLE_MIRROR_X

    def sdf(poly):
        return np.maximum(HR.polygon_sdf2d(x, z, poly), HR.polygon_sdf2d(x, z, [(mx - a, b) for a, b in poly]))
    frame = sdf(HR.GOGGLE_FRAME)
    lens = sdf(HR.GOGGLE_LENS)
    (bx0, bx1), (bz0, bz1) = HR.GOGGLE_BRIDGE
    bridge = np.minimum(np.minimum(x - bx0, bx1 - x), np.minimum(z - bz0, bz1 - z))
    on = np.maximum(frame, bridge) > -0.0015
    front = -nrm[cand, 1]
    a = np.clip((lens - 0.0003) / 0.0012 + 0.5, 0, 1) * np.clip((front - 0.35) / 0.2, 0, 1)
    a = a * a * (3 - 2 * a)
    return cand[on], a[on]


def head_parts(pos: np.ndarray, nrm: np.ndarray, reg: np.ndarray, names: list[str], pal: np.ndarray,
               out: np.ndarray, i1: np.ndarray) -> dict:
    """頭（部位 0）の形の部品の色を形から決める（HEAD_PARTS の説明）。out（色）と i1（色の番号）を書き換える"""
    from recon import hair as HR
    hp = HEAD_PARTS
    isk, ium, igr = names.index('skin'), names.index('umber'), names.index('graphite')
    # 頭と、首の後ろ・横の胴の側（z > neck_z。襟の色でなく肌か茶に塗られた所：房の先が首に下がる所）
    hi = np.nonzero((reg == 0) | ((reg == 1) & (pos[:, 2] > hp['neck_z']) & np.isin(i1, (isk, ium))))[0]
    f = HR.part_fields_at(pos[hi])
    rp = hp['ramp']

    def ramp_(v, t):   # 場 v が閾値 t を rp だけ越えると 1
        a = np.clip((v - t) / rp + 0.5, 0, 1)
        return a * a * (3 - 2 * a)

    def put(a, k, sel=None):
        a = a if sel is None else a * sel
        idx = hi[a > 0]
        out[idx] = a[a > 0, None] * pal[k] + (1 - a[a > 0, None]) * out[idx]
        i1[idx] = np.where(a[a > 0] > 0.5, k, i1[idx])
        return int((a > 0.5).sum())

    st = {}
    # 髪・耳・ベルト・ゴーグルでない頭の面（顔・首・あごの下）は肌（絵の多数決の茶・襟の色・ベルトの帯の塗りを使わない）。
    # 髪は次で茶に塗る（境目は髪の場で決まる）
    st['head_recoloured'] = int((i1[hi] != isk).sum())
    out[hi] = pal[isk]
    i1[hi] = isk
    # 髪の部品（帽子・房・前髪）：髪の場の面の上（hair_tol より近い）で、頭の面より外（hair_out より外）なら茶
    h = np.minimum(f['hair'] - hp['hair_tol'], f['hair'] - f['skin'] - hp['hair_out'])
    st['hair'] = put(ramp_(h, 0.0), ium)
    st['ear'] = put(ramp_(f['ear'], hp['ear']), isk)
    if 'strap' in f:
        # 8 回目：ヒモは髪の上の帯の部品（costume.build_goggle_strap）。形の段の古い帯のふくらみは髪の茶に塗る（部品の下に隠れる）
        st['strap'] = put(ramp_(f['strap'], hp['strap']), ium if STRAP_PART else igr,
                          (f['ear'] < hp['ear']).astype(np.float32))
    return st


# ---------------------------------------------------------------- 体

def paint_body(res: dict, mesh: dict, cams: dict | None = None) -> dict:
    t0 = time.time()
    names = list(PALETTE)
    pal = np.stack([hex_rgb(PALETTE[k]) for k in names])
    L = len(names)
    pos, nrm, col, reg = res['pos'], res['nrm'], res['col'], res['reg']
    verts, tris = mesh['verts'], mesh['tris']
    # texel の 3D の面積（三角形の面積 ÷ その三角形の texel の数）
    ta = 0.5 * np.linalg.norm(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]]), axis=1)
    cnt = np.bincount(res['tri'], minlength=len(tris))
    area = (ta / np.maximum(cnt, 1))[res['tri']]
    forbid = np.zeros((len(col), L), bool)
    for r, bad in FORBID.items():
        for k in bad:
            forbid[reg == int(r), names.index(k)] = True
    iu = names.index('umber')
    z = pos[:, 2]
    forbid[np.isin(reg, (1, 2, 3)) & (z < UMBER_Z['torso_min']), iu] = True
    forbid[np.isin(reg, (6, 7)) & (z > UMBER_Z['leg_max']), iu] = True
    neck = (reg == 1) & (z > NECK_NO_DARK['z_min']) & (np.abs(pos[:, 0]) < NECK_NO_DARK['x'])
    forbid[neck, names.index('graphite')] = True
    forbid[neck, iu] = True
    forbid[neck, names.index('brass')] = True
    # 真鍮は籠手のレール（腕・手）とバックル（胴の中心）だけ。帯の下の縁の陰が真鍮に分けられないように
    forbid[~np.isin(reg, (0, 2, 3, 4, 5)) & ~((reg == 1) & (np.abs(pos[:, 0]) < BRASS_TORSO_X)), names.index('brass')] = True
    lbl, cen = classify(col, names, forbid)
    # 頭の真鍮に近い色は、ゴーグルのレンズの縁の暗い琥珀（絵の陰）→ 琥珀
    lbl[(reg == 0) & (lbl == names.index('brass'))] = names.index('amber')
    log(f'分け {time.time() - t0:.0f}s：' + ', '.join(f'{k} {np.mean(lbl == i):.1%}' for i, k in enumerate(names)))

    # 箱（3D の位置・部位・法線の主な向き）
    q = np.floor(pos / CELL).astype(np.int64) + 2048
    ax = np.argmax(np.abs(nrm), 1)
    sg = (nrm[np.arange(len(nrm)), ax] > 0).astype(np.int64)
    key = ((q[:, 0] * 4096 + q[:, 1]) * 4096 + q[:, 2]) * 64 + reg.astype(np.int64) * 8 + ax * 2 + sg
    ukey, cell = np.unique(key, return_inverse=True)
    nc = len(ukey)
    carea = np.bincount(cell, area, nc)
    cpos = np.stack([np.bincount(cell, pos[:, i] * area, nc) for i in range(3)], 1) / carea[:, None]
    cnrm = np.stack([np.bincount(cell, nrm[:, i] * area, nc) for i in range(3)], 1)
    cnrm /= np.maximum(np.linalg.norm(cnrm, axis=1, keepdims=True), 1e-12)
    creg = np.bincount(cell, reg.astype(np.float64) * area, nc) / carea   # 箱は部位を鍵に含むので一つの値
    creg = np.rint(creg).astype(int)
    hist = np.zeros((nc, L))
    np.add.at(hist, (cell, lbl), area)
    log(f'箱 {nc:,}（{time.time() - t0:.0f}s）')

    # 箱のつながり
    tree = cKDTree(cpos)
    K = 20
    dist, nb = tree.query(cpos, k=K, distance_upper_bound=CELL * 2.6, workers=-1)
    ok = np.isfinite(dist) & (nb < nc)
    nb = np.where(ok, nb, 0)
    cosn = np.einsum('nkc,nc->nk', cnrm[nb], cnrm)
    ok &= cosn > 0.2
    w = np.where(ok, np.exp(-0.5 * (dist / (CELL * SMOOTH_SIGMA)) ** 2), 0.0)
    # 多数決のぼかし（面積で重み）
    boost = np.array([BOOST.get(k, 1.0) for k in names])
    p = hist / np.maximum(hist.sum(1, keepdims=True), 1e-12) * boost
    for _ in range(SMOOTH_ITERS):
        p = (w[..., None] * p[nb] * carea[nb][..., None]).sum(1)
        p /= np.maximum(p.sum(1, keepdims=True), 1e-12)
    clab = np.argmax(p, 1)
    raw = np.argmax(hist, 1)
    for k in SHARP_HEAD:
        i = names.index(k)
        m = (creg == 0) & ((raw == i) | (clab == i))
        clab[m] = raw[m]
    # 小さな島を周りへ併合
    rows = np.repeat(np.arange(nc), K)[ok.ravel()]
    cols = nb.ravel()[ok.ravel()]
    thr = np.array([MIN_AREA_LABEL.get(k, MIN_AREA) for k in names])
    thr_head = np.array([MIN_AREA_HEAD.get(k, MIN_AREA_HEAD['default']) for k in names])
    merged = 0
    for it in range(6):
        same = clab[rows] == clab[cols]
        g = sparse.coo_matrix((np.ones(same.sum()), (rows[same], cols[same])), shape=(nc, nc))
        ncomp, comp = connected_components(g, directed=False)
        comp_area = np.bincount(comp, carea, ncomp)
        comp_lab = np.zeros(ncomp, int)
        comp_lab[comp] = clab
        comp_hand = np.zeros(ncomp, bool)
        comp_hand[comp[np.isin(creg, (4, 5))]] = True
        comp_head = np.zeros(ncomp, bool)
        comp_head[comp[creg == 0]] = True
        cthr = np.where(comp_hand, np.minimum(thr[comp_lab], MIN_AREA_HAND), thr[comp_lab])
        cthr = np.where(comp_head, np.maximum(cthr, thr_head[comp_lab]), cthr)
        small = comp_area < cthr
        if not small.any():
            break
        # 島の縁の隣の色（自分の色以外、面積で重み）
        diff = ~same & small[comp[rows]]
        votes = np.zeros((ncomp, L))
        np.add.at(votes, (comp[rows[diff]], clab[cols[diff]]), carea[cols[diff]])
        has = votes.sum(1) > 0
        # 一番小さい島から：同じ回では、隣が自分より大きい島だけ
        tgt = np.argmax(votes, 1)
        change = small & has
        if not change.any():
            break
        clab = np.where(change[comp], tgt[comp], clab)
        merged += int(change.sum())
    log(f'小さな島の併合 {merged}（{time.time() - t0:.0f}s）')

    # texel の色：近くの箱の色の重み付きの多数決、境目だけ 2 色を細く混ぜる
    KT = 16
    dist, nbt = tree.query(pos, k=KT, workers=-1)
    wt = np.exp(-0.5 * (dist / (CELL * EDGE_SIGMA)) ** 2) * (np.einsum('nkc,nc->nk', cnrm[nbt], nrm) > 0.2)
    wt += 1e-9 * (np.arange(KT) == 0)
    pv = np.zeros((len(pos), L), np.float32)
    for k in range(KT):
        np.add.at(pv, (np.arange(len(pos)), clab[nbt[:, k]]), wt[:, k])
    o = np.argsort(-pv, 1)
    i1, i2 = o[:, 0], o[:, 1]
    p1 = pv[np.arange(len(pv)), i1]
    p2 = pv[np.arange(len(pv)), i2]
    t = p1 / np.maximum(p1 + p2, 1e-12)
    a = np.clip((t - 0.5) / (2 * EDGE_SHARP) + 0.5, 0, 1)
    a = a * a * (3 - 2 * a)
    out = a[:, None] * pal[i1] + (1 - a[:, None]) * pal[i2]
    # 頭の琥珀（レンズ）の縁は、箱でなく texel の近さの多数決で引き直す（レンズの角ばった形。箱の近くの琥珀の所だけ）
    ia = names.index('amber')
    near = (reg == 0) & (pv[:, ia] > 0)
    if near.any():
        hi = np.nonzero(reg == 0)[0]
        ht = cKDTree(pos[hi])
        qi = np.nonzero(near)[0]
        dd, nn = ht.query(pos[qi], k=24, workers=-1)
        nn = hi[nn]
        wn = np.exp(-0.5 * (dd / 0.0015) ** 2) * (np.einsum('qkc,qc->qk', nrm[nn], nrm[qi]) > 0.3)
        fa = (wn * (lbl[nn] == ia)).sum(1) / np.maximum(wn.sum(1), 1e-12)
        other = np.where(i1[qi] != ia, i1[qi], np.where(i2[qi] != ia, i2[qi], names.index('graphite')))
        aa = np.clip((fa - 0.5) / 0.3 + 0.5, 0, 1)
        aa = aa * aa * (3 - 2 * aa)
        out[qi] = aa[:, None] * pal[ia] + (1 - aa[:, None]) * pal[other]
        i1[qi] = np.where(fa > 0.5, ia, other)
    stats = {}
    use_views = BODY_PAINT == 'views' and cams is not None
    if use_views:   # 体は 1 枚の絵のきれいな形で（flat_views.py）。正面の地図（FRONT_ZONE）はこれに含まれる
        from recon import flat_views as FV
        bi, bc, bl, stats['body_views'] = FV.paint(res, mesh, cams, names, pal, classify)
        out[bi] = bc
        i1[bi] = bl
    # 胸・襟・首・帯の前：正面の絵の色の地図
    for view in (FRONT_ZONE or {}).get('views', []) if (cams is not None and not use_views) else []:
        fz = FRONT_ZONE
        cam = cams[view]
        soft, stats[f'{view}_zone'] = front_label_maps(names, cam, view)
        z = pos[:, 2]
        ztop = fz['back_z_top'] if view == 'back' else fz['z'][1]   # 首の後ろ（髪とフードの間のまだら）まで
        tz = np.clip((z - fz['z'][0]) / fz['ramp_z'], 0, 1) * np.clip((ztop - z) / fz['ramp_z'], 0, 1)
        n0 = np.full(len(z), fz['ndv'][0])
        if view == 'back':   # 首の後ろの下を向いた面（髪の下・フードの上）も背面の絵から（首の幅の中だけ。ほおの横は除く）
            n0[z > fz['back_neck_z']] = -0.35
            tz = tz * ((z < fz['z'][1]) | (np.abs(pos[:, 0]) < fz['back_neck_x']))
        tn = np.clip((-(nrm @ cam.d) - n0) / (fz['ndv'][1] - fz['ndv'][0]), 0, 1)
        t = tz * tn * (np.isin(reg, (0, 1)) | (np.isin(reg, (2, 3)) & (z > fz['arm_z_min'])))
        zi = np.nonzero(t > 0)[0]
        u, v = cam.project(pos[zi])
        from recon import texture as T
        pz = T.bilinear(np.ascontiguousarray(soft.transpose(1, 2, 0)), u, v)
        ok = pz.sum(1) > 0.5
        zi, pz = zi[ok], pz[ok]
        zc = (pz[:, :, None] * pal[None]).sum(1) / pz.sum(1, keepdims=True)
        tt = t[zi][:, None]
        out[zi] = tt * zc + (1 - tt) * out[zi]
        i1[zi] = np.where(t[zi] > 0.5, np.argmax(pz, 1), i1[zi])
        stats[f'{view}_zone']['texels'] = int(len(zi))
    # 頭の部品（ベルト・耳・髪・あごの下）：形で
    if HEAD_PARTS:
        stats['head_parts'] = head_parts(pos, nrm, reg, names, pal, out, i1)
        log(f'頭の部品 {stats["head_parts"]}')
    # ゴーグル：部品の形で
    if GOGGLE_PAINT:
        gi, ga = goggle_colour(pos, nrm, reg, names)
        if gi is not None:
            ia, ig = names.index('amber'), names.index('graphite')
            out[gi] = ga[:, None] * pal[ia] + (1 - ga[:, None]) * pal[ig]
            i1[gi] = np.where(ga > 0.5, ia, ig)
            stats['goggle_texels'] = int(len(gi))
    res['col'] = out.astype(np.float32)
    res['flat_label'] = i1
    frac = {k: round(float((area * (i1 == i)).sum() / area.sum()), 4) for i, k in enumerate(names)}
    log(f'平らな色 {time.time() - t0:.0f}s：{frac}')
    return {**stats, 'cells': int(nc), 'merged_islands': merged, 'area_fraction': frac,
            'centres_lab': {k: [round(float(v), 1) for v in cen[i]] for i, k in enumerate(names)}}


def patch_empty_tris(img: np.ndarray, cov: np.ndarray, res: dict, mesh: dict) -> int:
    """UV がつぶれて texel を 1 つも持たない三角形（首の後ろなど、合わせて約 300cm²）は、隣の島の色を拾って
    まだらになる。その三角形の UV の角・重心のまわり 3×3 の画素（ほかの texel でない所）へ、3D で一番近い texel の色を書く"""
    verts, tris, uv = mesh['verts'], mesh['tris'], mesh['uv']
    S = img.shape[0]
    cnt = np.bincount(res['tri'], minlength=len(tris))
    e = np.nonzero(cnt == 0)[0]
    if not len(e):
        return 0
    cen = verts[tris[e]].mean(1)
    fn = np.cross(verts[tris[e, 1]] - verts[tris[e, 0]], verts[tris[e, 2]] - verts[tris[e, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    tree = cKDTree(res['pos'])
    d, nb = tree.query(cen, k=8, workers=-1)
    good = np.einsum('ekc,ec->ek', res['nrm'][nb], fn) > 0.3
    pick = np.where(good.any(1), np.argmax(good, 1), 0)
    colour = res['col'][nb[np.arange(len(e)), pick]]
    uvt = uv[e] if uv.ndim == 3 else uv[tris[e]]
    pts = np.concatenate([uvt, uvt.mean(1, keepdims=True)], 1)   # (n, 4, 2)
    px = np.clip((pts[..., 0] * S).astype(int), 0, S - 1)
    py = np.clip(((1 - pts[..., 1]) * S).astype(int), 0, S - 1)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            X = np.clip(px + dx, 0, S - 1)
            Y = np.clip(py + dy, 0, S - 1)
            free = ~cov[Y, X]
            for k in range(pts.shape[1]):
                f = free[:, k]
                img[Y[f, k], X[f, k]] = colour[f]
    return int(len(e))


# ---------------------------------------------------------------- 顔

FACE_SKIN_D = (10.0, 18.0)   # 肌の度合い：肌の色からの差（明るさは L_WEIGHT_FACE 倍）がこの間で 1 → 0
L_WEIGHT_FACE = 0.6
FACE_FEATURE_MAX = 0.06      # 区画の面積のこれより小さく、区画の縁に届かない肌でない塊は、目・眉・口（絵の色のまま）
FACE_SPECK = 24              # これより小さな塊（画素）は肌へ
FACE_REGION = ['umber', 'skin']   # 顔の材質の所（顔の窓の中）にあるのは髪と肌だけ（ゴーグル・襟は窓の外）


def paint_face_atlas(atlas_p: str, meta: dict, out_p: str) -> str:
    t0 = time.time()
    rgb = np.asarray(Image.open(atlas_p).convert('RGB')).astype(np.float32) / 255.0
    H, W = rgb.shape[:2]
    lb = lab(rgb)
    skin_hex = hex_rgb(PALETTE['skin'])
    # 絵の肌の色（表の色の近くの画素の中央値）
    d0 = np.linalg.norm((lb - lab(skin_hex)) * [L_WEIGHT_FACE, 1, 1], axis=-1)
    ref = np.median(lb[d0 < 20], 0)
    d = np.linalg.norm((lb - ref) * [L_WEIGHT_FACE, 1, 1], axis=-1)
    s = 1.0 - np.clip((d - FACE_SKIN_D[0]) / (FACE_SKIN_D[1] - FACE_SKIN_D[0]), 0, 1)
    nonskin = s < 0.5
    feature = np.zeros((H, W), bool)
    region = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in meta['quadrants_atlas_px'].values():
        sub = nonskin[y0:y1, x0:x1]
        lab_, n = ndi.label(sub)
        if not n:
            continue
        sizes = ndi.sum(sub, lab_, range(1, n + 1))
        border = np.zeros(n + 1, bool)
        for edge in (lab_[0], lab_[-1], lab_[:, 0], lab_[:, -1]):
            border[edge] = True
        big = (sizes > FACE_FEATURE_MAX * sub.size) | border[1:]
        speck = sizes < FACE_SPECK
        # 目・眉・口は表情の範囲の中だけ（あごの下の陰などは肌）
        zx0, zy0, zx1, zy1 = meta['expression_zone_atlas_px']
        inzone = np.zeros(n + 1, bool)
        inzone[np.unique(lab_[zy0:zy1, zx0:zx1])] = True
        feat = ~big & ~speck & inzone[1:]
        feature[y0:y1, x0:x1] = np.isin(lab_, np.nonzero(feat)[0] + 1)
        region[y0:y1, x0:x1] = np.isin(lab_, np.nonzero(big)[0] + 1)
    # 大きな塊（髪・ゴーグルなど）は色の表で平らに（多数決で掃除し、境目は細く混ぜる）
    rl, _ = classify(rgb.reshape(-1, 3), FACE_REGION)
    rl = rl.reshape(H, W)
    rl[~region] = FACE_REGION.index('skin')
    pal = np.stack([hex_rgb(PALETTE[k]) for k in FACE_REGION])
    onehot = np.stack([ndi.gaussian_filter((rl == i).astype(np.float32), 3.0) for i in range(len(FACE_REGION))], -1)
    rl = np.argmax(onehot, -1)
    soft = np.stack([ndi.gaussian_filter((rl == i).astype(np.float32), 0.9) for i in range(len(FACE_REGION))], -1)
    flat = (soft[..., :, None] * pal[None, None]).sum(-2) / np.maximum(soft.sum(-1, keepdims=True), 1e-6)
    # 目・眉・口：絵の色のまま。縁の画素（肌との混ざり）だけ、肌の度合い s で平らな肌色と混ぜる
    near_f = ndi.binary_dilation(feature, iterations=2)
    sf = np.where(near_f, s, 1.0)[..., None]
    out = np.where(near_f[..., None], sf * skin_hex + (1 - sf) * rgb, flat)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out_p)
    log(f'顔の画像 {out_p}：目・眉・口 {feature.mean():.2%}、髪など {(rl != FACE_REGION.index("skin")).mean():.1%}'
        f'（{time.time() - t0:.0f}s）')
    return out_p


if __name__ == '__main__':   # 調べ物用：保存した焼いた色（TEX_DUMP）と顔の画像で試す
    import json
    work = os.path.join(CH.REPO, CH.CFG['work'])
    tex = os.path.join(work, 'tex')
    out_dir = sys.argv[1] if len(sys.argv) > 1 else tex
    meta = json.load(open(os.path.join(work, 'face_atlas.json')))
    paint_face_atlas(os.path.join(work, meta['atlas_file']), meta, os.path.join(out_dir, 'face_atlas_flat_test.png'))
    c = np.load(os.path.join(tex, 'res_cache.npz'))
    res = {k: c[k] for k in ('pix', 'tri', 'bar', 'pos', 'nrm', 'col', 'reg')}
    res['size'] = 2048
    mesh = {'verts': c['verts'], 'tris': c['tris']}
    from recon import views as V
    print(paint_body(res, mesh, V.load_calib()))
    from recon import texture as T
    T.save_png(os.path.join(out_dir, 'flat_test.png'), T.to_image(res, res['col']))
