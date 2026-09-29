"""絵を投影して焼くテクスチャの段：再構築したメッシュ（haru_mesh.glb）に元の絵の色を付ける。

  .venv-blender/bin/python tools/blender/recon/texture.py
      [--mesh build/recon/haru_mesh.glb]   形（carve.py の出力。UV 付き）
      [--size 2048]                         焼くテクスチャの大きさ（試しは 1024 で速い）
      [--no-render]                         確認画像（Cycles）を描かない
      [--render-only]                       書き出し済みの GLB の確認画像だけ描き直す
  → build/recon/haru_textured_apose.glb（A ポーズ、骨なし、テクスチャ入り）
    build/recon/tex/haru_body_base.png・haru_body_emit.png（焼いたテクスチャ）
    build/recon/tex_check_*.png（元の絵と並べた確認画像）

■ やり方
  1. UV の三角形を numpy で 2048 角に塗り（画素の中心で重心座標を求める）、テクセルごとの世界の位置と
     法線（なめらかな頂点法線の補間）を正確に出す。
  2. 各視点（REAL_VIEWS：正面・背面・右真横・腕の無い右真横・左真横・右前 45 度・左前 45 度。W1-00b の追加の絵）の
     正投影カメラで、メッシュの奥行き（z バッファ）を同じ塗りで作る。
     テクセルは「その視点の視線で一番手前の面」（奥行きの差 DEPTH_TOL 以内）で、絵の外形のマスクの内側に
     写るときだけ、その視点の色をもらえる。重み = 見える × マスクの縁からの距離 × 奥行きの段差からの距離
     × max(0, n・(-視線))^p。奥行きの段差（腕の縁など）と外形の縁の数 px は重みを落とす
     （絵とメッシュのずれで、腕の色が胴に付くのを防ぐ）。
  3. 本人の左側は左真横・左前 45 度の実の絵から取る。左の胴の横（左真横の絵では左腕に隠れる）は、腕の無い右真横の
     絵を左右反転した「仮想の視点」で、実の視点がよく見ていない所だけ弱く補う（左右で違う部品 ASYMMETRIC では使わない）。
     頭の左側は、右真横・右前 45 度の絵の反転を主に使う（HEAD_MIRROR_VIEWS。形の頭は右の絵に合わせた左右対称の形で、
     左の絵の髪・耳の位置は形と合わない）。
  3b. 腕の無い右真横の絵（NOARM_VIEWS）：腕・手のテクセルは色をもらわず、奥行きは腕・手を除いたメッシュで調べる。
     胴・脚の右の横はこの絵から取り、腕のある右真横の絵は胴・脚には弱く（ARMED_BODY_GAIN）使う。
  4. 色は 2 つの帯に分けて混ぜる：ぼかした色（低い周波数）は広い重み（p=P_LOW）でなめらかに、
     細部（高い周波数 = 色 - ぼかした色）はほぼ一番よく見える視点だけ（p=P_HIGH）から取る。
     視点の間で線が二重になる（ゴースト）のを防ぎつつ、視点の切り替わりの継ぎ目を目立たせない。
  5. 頭の正面は、全身の正面の絵（頭が約 330px）の代わりに表情アトラス（face_atlas.png の区画 0、
     4 倍の細かさ）から取る。
  6. どの視点もよく見ていないテクセル（真上・真下を向く所）は、よく見えているテクセルの色を、
     3D の近さと法線の近さで重み付けして引いてくる（UV の島をまたがない：3D の近さで探すので）。
  7. 島の外は一番近い島の色で埋める（ミップマップで縁がにじまないように。島の縁から 8px 以上）。
  8. 顔：顔の窓（face_atlas.json の window_front_px）の中で正面を向き、正面から見える面に材質
     'haru_face' を付け、UV を正面の正投影でアトラスの区画 0（Blender の u∈[0,0.5]、v∈[0.5,1]）に置く。
     あごの下（FACE_CHIN_PX より下の首・襟）は除き、表情で変わる画素の上で正面から一番手前に見える
     三角形は向きにかかわらず加える（眉・目・口が必ず表情と一緒に変わるように。覆う割合を報告する）。
  8b. 頭の塗り分け（head_cleanup）：形に耳が無いので、絵の耳の肌色が髪の房に、もみあげ・あごの線の暗い色が
     ほおの横に写る。hair.py の顔の範囲で頭の面を肌と髪に分け、合わない色を同じ側の近くの色で塗り直す。
     顔の材質の縁の近く（FACE_FEATHER）の体のテクスチャは正面の絵（アトラスの通常）へ寄せて、
     材質の境で色がそろうようにする。
  2b. 絵の腕の遮り：右真横・右前斜め・背面の絵では、腕・手が胴の横・太ももの板の手前に描かれていて、メッシュの
     腕は絵の腕と数 cm ずれている（メッシュの奥行きでは分からない）。メッシュの腕・手（uvparts の部位）をその視点へ
     投影して ART_OCC_BAND 画素広げた帯の中の、肌・手袋の色の画素を「絵の腕」とし、そこに写る胴・脚のテクセルは
     その視点の重みを 0 にする（build/recon/tex/art_arm_<視点>.png に赤で示す）。
  8c. 体の肌色の塗り直し（body_cleanup）：肌の出るはずのない所（胴の服・えり・脚・袖）に残った肌色を、同じ部位の
     肌でない近くの色で塗り直す（絵の腕の色の写り、素肌の前腕から塗り足された袖の裏・わきの下）。えり・フードの
     上を向いた面（胴の z < 1.19、n.z > 0.5）で塗り足した所も肌にしない。
  8d. 髪の色合わせ（hair_colour_match）：髪のテクセルの色の平均・ばらつきを正面・背面の絵の髪の画素にそろえる。
  8e. 首の前（neck_cleanup）：のど・あごの下（NECK_ZONE）の肌でない色を、近くのよく見えている肌の色で塗り直す
     （haru_neck.png：首の素肌を茶色の帯で横切らない）。
  8e2. 手（hand_cleanup）：手に写った上着のれんが色を、同じ手の手袋・肌の色で塗り直す（手袋の縞）。
  8f. 靴底（sole_cleanup）：高さ SOLE_TOP より下の靴は靴底の暗い灰色の一色（視点の継ぎ目のぎざぎざを消す）。
  8g. 横を向いた髪の細部を弱める（hair_colour_match の中、HAIR_SIDE_DETAIL）：真横・斜めの絵の房の線は形の房と
     位置が合わないので、3D の近さの平均の色へ寄せ、房の形は形の陰で見せる。
  9. 発光：琥珀色（#FFBC52 付近：ゴーグルのレンズ・膝の継ぎ目・籠手のレール）を探して、発光の
     テクスチャに焼く。その所の下地は EMIT_BASE_DARKEN だけ暗くし、発光の強さは EMIT_STRENGTH（照らされた
     下地 ＋ 発光がおよそ絵の色。飽和してレモン色にならない）。材質は金属 0、粗さ 0.8、片面（閉じた面）。

■ 座標（views.py・calib.json と同じ）
  Blender は Z が上、正面 -Y、本人の左 +X、靴底 z=0。画素の座標は画像の左上を 0 とする連続値
  （画素 i は [i, i+1)）。UV の (u, v) はテクスチャの画素 (u*S, (1-v)*S) に当たる。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from recon import views as V  # noqa: E402

WORK = V.WORK
TEX_DIR = os.path.join(WORK, 'tex')
OUT_GLB = os.path.join(WORK, 'haru_textured_apose.glb')

# 色をもらう実の視点。W1-00b の追加の絵（左真横・左右の前 45 度・腕の無い右真横）で、本人の左側も実の絵から
# 取る。以前の右前斜め（three_quarter、約 31 度）は 45 度の絵と部品の位置が食い違い、斜めの色がずれたので使わない
REAL_VIEWS = ('front', 'back', 'side_right', 'side_right_noarms', 'side_left', 'front_right45', 'front_left45')
# 左右反転して本人の左側の代わりに使う視点：腕の無い右真横だけ（左真横の絵では左腕が胴の横を隠すので、
# 左の胴の横の色は、実の視点がよく見ていない所だけこれで補う）
MIRROR_VIEWS = ('side_right_noarms',)
# 腕の無い絵：腕・手のテクセルは色をもらわず、奥行きは腕・手を除いたメッシュで調べる（絵では胴の横が見えている）
NOARM_VIEWS = ('side_right_noarms',)
# 腕の無い絵がある向きの、腕のある絵の胴・脚への重みの倍率（胴の横は腕の無い絵から取る）
ARMED_BODY_GAIN = {'side_right': 0.12}
# 視点の重みの倍率。背面はゲームで一番よく見る向き（後ろからのカメラ）なので強め、真横と斜めは
# 正面・背面から描き起こした絵で部品の位置の食い違いが多いので弱め
VIEW_GAIN = {'front': 1.0, 'back': 1.2, 'side_right': 0.9, 'side_right_noarms': 0.9, 'side_left': 0.9,
             'front_right45': 0.95, 'front_left45': 0.95, 'three_quarter': 0.9}
# 向きの「ハンデ」（度）：面と視線の角度にこれを足してから重みを計算する。真横・斜めは、正面・背面より
# この角度だけよく見えているときだけ勝つ（凸凹の面で視点が細かく入れ替わって縞になるのも防ぐ）
VIEW_BIAS_DEG = {'front': 0.0, 'back': 0.0, 'side_right': 15.0, 'side_right_noarms': 15.0, 'side_left': 15.0,
                 'front_right45': 8.0, 'front_left45': 8.0, 'three_quarter': 8.0}
MIRROR_GAIN = 0.35         # 反転の視点の重み（実の視点がよく見ていない所だけ）
# 頭（uvparts の部位 0）の左側：形の頭（hair.py）は右の絵（右真横・右前斜め）に合わせた左右対称の形なので、
# 左の絵（左真横・左前斜め）の髪・耳・もみあげの位置は形と合わず、ほお・首に髪の暗い色がにじんだ。
# 頭の左側は右の絵を反転した視点を主に使い、左の絵は弱く
HEAD_MIRROR_VIEWS = ('side_right', 'front_right45')
HEAD_MIRROR_GAIN = 0.9
HEAD_LEFT_VIEW_GAIN = 0.15   # 頭の左側の、左の絵の重みの倍率
# 靴底：絵（右真横・左真横・正面、haru_shoes.png）では靴底は高さ約 4cm の暗い灰色（#444641 に近い）のゴムの帯。
# 視点の継ぎ目で靴底の縁がぎざぎざに見えたので、この高さより下の靴は靴底の色の一色に塗る
SOLE_TOP = 0.039
# 首の前（のど・あごの下）：haru_neck.png と正面の絵で素肌の範囲（あごの下 1.21 から、フードの襟の内側 |x| < 0.042、
# 首の前の半分）
NECK_ZONE = {'z': (1.155, 1.215), 'x': 0.042, 'y': 0.0}
HAIR_SIDE_DETAIL = 0.6     # 横を向いた髪の細部（3D の近さの平均からの差）を弱める割合
SOLE_RGB = (0.265, 0.25, 0.245)
MIRROR_NDV = (0.25, 0.45)  # 実の視点の一番よい n・v がこの間なら反転を弱め、上なら使わない

P_LOW = 4.0                # ぼかした色の重みの指数：max(0, n・v)^P_LOW
P_HIGH = 14.0             # 細部の重みの指数（ほぼ一番よく見える視点だけ）
SIGMA_LOW = 3.0            # 色を 2 つの帯に分けるぼかし（全身の絵の画素）
DEPTH_TOL = 0.008          # 一番手前の面とみなす奥行きの差（m）
OCC_RADIUS = 72            # 手前に別の物（腕・手）がある所からこの画素（2048）以内のテクセルは、その視点の重みを落とす
OCC_DEPTH = (0.03, 0.06)   # 「手前に別の物」とみなす奥行きの差（m）の範囲
OCC_FLOOR = 0.08           # そのときの重みの倍率（絵の腕・手の位置はメッシュと数 cm ずれるので、周りを避ける）
DEPTH_EDGE = 0.03          # 奥行きの段差とみなす差（3×3 の画素の中、m）
EDGE_RAMP = (1.0, 5.0)     # 奥行きの段差からの距離（画素）：これより近いと重み EDGE_FLOOR、遠いと 1
EDGE_FLOOR = 0.1          # 段差の近くの重みの下限（細い部品は段差に挟まれるので 0 にはしない）
NORMAL_SMOOTH = 30         # 重みに使う法線をなめらかにする回数（隣の頂点との平均）
MASK_RAMP = (0.5, 3.5)     # 絵の外形の縁からの内側への距離（画素）：同じく
W_FULL = 0.06              # 視点の重みの和がこれ以上のテクセルは、投影の色だけを使う
W_SEED = 0.10              # 塗り足しの元にするテクセルの重みの和の下限
INPAINT_K = 16             # 塗り足しで引く近いテクセルの数
FACE_FEATHER = 0.030       # 顔の材質の縁から、体のテクスチャを正面の色へ寄せる距離（m）
FACE_NDV_MIN = 0.45        # 顔の材質にする面の、正面への向きの下限（n・(-Y)）。横を向いたほお・あごは
                           # 正面の投影が引き伸ばされるので体の材質（複数の視点の色）にする
FACE_CHIN_PX = 540         # 顔の材質にする三角形の重心の下限（正面の絵の画素の y。あごの先は約 535）
HEAD_CLEAN_Z = (1.215, 1.47)  # 頭の肌と髪の塗り分けをする高さ（あごの下の首・えりより上）
SKIN_CLEAN_ZMIN = 1.20     # 肌の側の下端（あごの下の首の横まで。フードの襟は約 1.19 より下）
SKIN_CLEAN_ZMAX = 1.31     # 肌の側で暗い色を消すのはこれより下だけ（上は眉・前髪がある）
ALIGN_RES = 1024           # 視点の合わせ込み（光学的流れ）の画像の大きさ
ALIGN_SIGMA = 16.0         # 流れをなめらかにするぼかし（2048 の画素）
ALIGN_MAX = 40.0           # ずらしの上限（2048 の画素）
ALIGN_ORDER = ('front_right45', 'front_left45', 'side_right_noarms', 'side_right', 'side_left', 'back')   # 正面を基準に、この順で合わせる
DEBUG_ALIGN = True
DILATE_PX = 16             # 島の外を埋める幅の目安（実際は全面を一番近い島の色で埋める）
ROUGHNESS = 0.8
# 発光：レンズなどの琥珀色は「照らされた下地 ＋ 発光」で絵の色になるように、下地を暗くして発光を弱める
# （以前は下地そのままに同じ色の発光を 1.0 で足していて、赤と緑が飽和してレモン色になった）
EMIT_STRENGTH = 0.55
EMIT_BASE_DARKEN = 0.55    # 発光の所の下地の色を (1 - これ × 度合い) 倍に
# 絵の腕・手の遮り（ART_OCCLUDE）：右真横・右前斜め・背面の絵では、腕・手が胴・太ももの板の手前に描かれている。
# メッシュの腕は絵の腕と数 cm ずれるので、メッシュの奥行きでは遮りが分からない。絵の腕・手の画素（メッシュの腕・手を
# その視点へ投影して ART_OCC_BAND 画素広げた帯の中の、肌・手袋の色）に写る「腕・手でない」テクセルは、
# その視点の重みを 0 にする（正面の絵・塗り足しが色を出す）
ART_OCCLUDE_VIEWS = ('side_right', 'side_left', 'front_right45', 'front_left45', 'three_quarter', 'back')
ART_OCC_BAND = int(ALIGN_MAX + 10)
NECK_V_HALF = 0.055       # 首の前の素肌の V の半幅（m。これより外の首まわりはフード・えり）
HEAD_Z = V.HEIGHT - V.HEIGHT / 4.4   # 部位の分け（uvparts.region_of_point）の頭の高さ（carve.py と同じ）

# 左右で違う部品（本人の右肩の板・右太ももの板・左前腕の籠手）の範囲。世界の (x, z) の箱
# （正面の絵の mask_asymmetric_parts から、余裕を 3cm ほど足した）。本人の左側のテクセル p について、
# (x, z) が左の部品の箱に入るか、(-x, z) が右の部品の箱に入るなら、反転の視点を使わない。
ASYMMETRIC = {
    'right_shoulder_plate': ((-0.31, -0.10), (0.99, 1.22)),
    'right_thigh_plate': ((-0.27, -0.03), (0.54, 0.84)),
    'left_gauntlet': ((0.16, 0.38), (0.72, 0.96)),
}

AMBER_HEX = '#FFBC52'


def log(msg: str) -> None:
    print(f'[texture {time.strftime("%H:%M:%S")}] {msg}', flush=True)


# ---------------------------------------------------------------- メッシュ（bpy）

def import_mesh(path: str):
    """GLB を読み込み、1 つの三角形のメッシュの物体にする"""
    import bpy
    from lib import common as C
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    obj = C.join(meshes, 'haru') if len(meshes) > 1 else meshes[0]
    obj.name = 'haru'
    for o in list(bpy.context.scene.objects):
        if o is not obj:
            bpy.data.objects.remove(o, do_unlink=True)
    obj.parent = None
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = obj.data
    if any(p.loop_total != 3 for p in me.polygons):
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    return obj


def mesh_arrays(obj) -> dict:
    """位置 (nv,3)・三角形の頂点 (nt,3)・角ごとの UV (nt,3,2)"""
    me = obj.data
    nv, nl, nt = len(me.vertices), len(me.loops), len(me.polygons)
    co = np.empty(nv * 3)
    me.vertices.foreach_get('co', co)
    lv = np.empty(nl, np.int64)
    me.loops.foreach_get('vertex_index', lv)
    ls = np.empty(nt, np.int64)
    me.polygons.foreach_get('loop_start', ls)
    uv = np.empty(nl * 2)
    me.uv_layers[0].data.foreach_get('uv', uv)
    loops = ls[:, None] + np.arange(3)[None, :]
    return {'verts': co.reshape(-1, 3), 'tris': lv[loops], 'uv': uv.reshape(-1, 2)[loops], 'loops': loops}


def smooth_normals(verts: np.ndarray, tris: np.ndarray, iters: int = 0) -> np.ndarray:
    """面積で重み付けした頂点の法線。UV の切れ目で分かれた同じ位置の頂点はまとめて計算する。

    iters > 0 なら、隣の頂点の法線との平均を iters 回くり返して大きな形の向きにする（表面の細かな凸凹で
    視点の選び方がまだらにならないように。重みの計算だけに使う）。
    """
    key = np.round(verts / 1e-5).astype(np.int64)
    _, wid = np.unique(key, axis=0, return_inverse=True)
    wid = wid.ravel()
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    n = int(wid.max()) + 1
    acc = np.zeros((n, 3))
    for k in range(3):
        np.add.at(acc, wid[tris[:, k]], fn)
    acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    if iters > 0:
        from scipy import sparse
        wt = wid[tris]
        e = np.concatenate([wt[:, [0, 1]], wt[:, [1, 2]], wt[:, [2, 0]]])
        A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
        A = ((A + A.T) > 0).astype(np.float64)
        deg = np.asarray(A.sum(1)).ravel() + 1.0
        sm = acc.copy()
        for _ in range(iters):
            sm = (A @ sm + sm) / deg[:, None]
        # 平均の長さ（向きのそろい具合）が短い所（指・髪の房のように薄い所）は、元の法線を多く使う
        sm = sm + (1.0 - np.linalg.norm(sm, axis=1, keepdims=True)) * acc
        acc = sm / np.maximum(np.linalg.norm(sm, axis=1, keepdims=True), 1e-12)
    return acc[wid]


# ---------------------------------------------------------------- 三角形を画素に塗る

def raster(p2: np.ndarray, w: int, h: int, chunk: int = 6_000_000):
    """三角形 (T,3,2)（画素の連続座標）を塗る。画素の中心 (i+0.5, j+0.5) が入る組を返す。

    返り値：画素の番号 (N,)（行 * w + 列）、三角形の番号 (N,)、重心座標 (N,3)
    """
    x, y = p2[..., 0], p2[..., 1]
    x0 = np.clip(np.ceil(x.min(1) - 0.5), 0, w).astype(np.int64)
    x1 = np.clip(np.floor(x.max(1) - 0.5), -1, w - 1).astype(np.int64)
    y0 = np.clip(np.ceil(y.min(1) - 0.5), 0, h).astype(np.int64)
    y1 = np.clip(np.floor(y.max(1) - 0.5), -1, h - 1).astype(np.int64)
    nx = np.maximum(x1 - x0 + 1, 0)
    ny = np.maximum(y1 - y0 + 1, 0)
    cnt = nx * ny
    ax, ay, bx, by, cx, cy = x[:, 0], y[:, 0], x[:, 1], y[:, 1], x[:, 2], y[:, 2]
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    good = np.nonzero((np.abs(area) > 1e-9) & (cnt > 0))[0]
    pix_l, tri_l, bar_l = [], [], []
    cum = np.cumsum(cnt[good])
    start = 0
    while start < len(good):
        base = cum[start - 1] if start else 0
        end = int(np.searchsorted(cum, base + chunk, side='right'))
        end = max(end, start + 1)
        sel = good[start:end]
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
        eps = -1e-7
        ins = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
        pix_l.append(py[ins] * w + px[ins])
        tri_l.append(tid[ins])
        bar_l.append(np.stack([w0[ins], w1[ins], w2[ins]], 1))
        start = end
    return np.concatenate(pix_l), np.concatenate(tri_l), np.concatenate(bar_l)


def uv_texels(uv: np.ndarray, size: int):
    """UV の三角形を塗り、テクセルごとの（三角形、重心座標）。重なりは最初の三角形を取る"""
    p2 = np.stack([uv[..., 0] * size, (1.0 - uv[..., 1]) * size], -1)
    pix, tri, bar = raster(p2, size, size)
    pix, first = np.unique(pix, return_index=True)
    return pix, tri[first], bar[first]


def zbuffer(verts: np.ndarray, tris: np.ndarray, cam: V.Cam, size: int = V.IMG) -> np.ndarray:
    """カメラから見た奥行き（視線の向きの距離。背景は inf）。size×size の画像"""
    u, v = cam.project(verts)
    p = verts.copy()
    if cam.mirror:
        p[:, 0] = -p[:, 0]
    depth = p @ cam.d
    p2 = np.stack([u[tris], v[tris]], -1) * (size / V.IMG)
    pix, tri, bar = raster(p2, size, size)
    dz = (depth[tris[tri]] * bar).sum(1)
    z = np.full(size * size, np.inf)
    np.minimum.at(z, pix, dz)
    return z.reshape(size, size)


# ---------------------------------------------------------------- 視点の絵

def srgb_float(rgba: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """絵の RGB（0..1、sRGB のまま）と不透明度。透明な所は一番近い不透明な画素の色で埋める"""
    a = rgba[..., 3]
    hole = a < 128
    _, (iy, ix) = ndi.distance_transform_edt(hole, return_indices=True)
    rgb = rgba[..., :3][iy, ix].astype(np.float32) / 255.0
    return rgb, a.astype(np.float32) / 255.0


def blur(rgb: np.ndarray, sigma: float) -> np.ndarray:
    return np.stack([ndi.gaussian_filter(rgb[..., c], sigma, mode='nearest') for c in range(3)], -1)


def bilinear(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """画素の連続座標 (x, y)（画素 i の中心は i+0.5）で双一次の補間。img は (H,W,C)"""
    h, w = img.shape[:2]
    fx = np.clip(x - 0.5, 0, w - 1.001)
    fy = np.clip(y - 0.5, 0, h - 1.001)
    ix, iy = fx.astype(np.int64), fy.astype(np.int64)
    tx, ty = (fx - ix)[:, None], (fy - iy)[:, None]
    a = img[iy, ix] * (1 - tx) + img[iy, ix + 1] * tx
    b = img[iy + 1, ix] * (1 - tx) + img[iy + 1, ix + 1] * tx
    return a * (1 - ty) + b * ty


def nearest(img: np.ndarray, x: np.ndarray, y: np.ndarray, fill=0.0) -> np.ndarray:
    h, w = img.shape[:2]
    ix, iy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    out = np.full(x.shape, fill, dtype=np.float64)
    out[ok] = img[iy[ok], ix[ok]]
    return out


def ramp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class ViewImage:
    """1 つの視点の絵：色（全体・ぼかし）、外形の縁からの距離、（正面だけ）表情アトラスの区画 0"""

    def __init__(self, name: str, atlas_meta: dict | None = None):
        self.name = name
        rgba = V.load_rgba(name)
        self.rgb, _ = srgb_float(rgba)
        self.low = blur(self.rgb, SIGMA_LOW)
        mask = V.load_mask(name)
        self.mask_dist = ndi.distance_transform_edt(mask).astype(np.float32)
        self.atlas = None
        if atlas_meta is not None:
            a = np.asarray(Image.open(os.path.join(WORK, atlas_meta['atlas_file'])).convert('RGB'))
            q = a[:1024, :1024].astype(np.float32) / 255.0
            k = atlas_meta['atlas_px_per_front_px']
            # 体のテクスチャ（頭で約 19px/cm）はアトラス（約 56px/cm）より粗いので、少しぼかしてから拾う
            self.atlas = blur(q, 1.0)
            self.atlas_low = blur(q, SIGMA_LOW * k)
            self.k = k
            self.w0 = atlas_meta['window_front_px'][:2]
            self.q0 = atlas_meta['window_atlas_px'][:2]
            span = atlas_meta['quadrant0_front_px']
            self.span = (span[0] + 3, span[1] + 3, span[2] - 3, span[3] - 3)

    def sample(self, u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """画素の連続座標 (u, v) の色（全体, ぼかし）"""
        full = bilinear(self.rgb, u, v)
        low = bilinear(self.low, u, v)
        if self.atlas is not None:
            s = self.span
            ins = (u >= s[0]) & (u <= s[2]) & (v >= s[1]) & (v <= s[3])
            if ins.any():
                ax = self.q0[0] + (u[ins] - self.w0[0]) * self.k
                ay = self.q0[1] + (v[ins] - self.w0[1]) * self.k
                full[ins] = bilinear(self.atlas, ax, ay)
                low[ins] = bilinear(self.atlas_low, ax, ay)
        return full, low


def near_occluder_depth(z: np.ndarray) -> np.ndarray:
    """各画素のまわり OCC_RADIUS の中で一番手前の奥行き（背景は遠く）"""
    far = np.where(np.isfinite(z), z, 1e9)
    return ndi.minimum_filter(far, size=2 * OCC_RADIUS + 1).astype(np.float32)


def depth_edge_dist(z: np.ndarray) -> np.ndarray:
    """奥行きの段差（外形を含む）からの距離（画素）"""
    far = np.where(np.isfinite(z), z, np.nanmax(np.where(np.isfinite(z), z, np.nan)) + 1.0)
    rng = ndi.grey_dilation(far, size=3) - ndi.grey_erosion(far, size=3)
    edge = rng > DEPTH_EDGE
    return ndi.distance_transform_edt(~edge).astype(np.float32)


# ---------------------------------------------------------------- 焼く

def asymmetric_left(p: np.ndarray) -> np.ndarray:
    """反転の視点を使ってはいけないテクセル（本人の左側で、左右で違う部品の所）"""
    x, z = p[:, 0], p[:, 2]
    bad = np.zeros(len(p), bool)
    for (xr, zr) in ASYMMETRIC.values():
        for sx in (1.0, -1.0):   # 左の部品はそのまま、右の部品は反転した位置で調べる
            xx = sx * x
            bad |= (xx >= xr[0]) & (xx <= xr[1]) & (z >= zr[0]) & (z <= zr[1]) & (x > 0)
    return bad


def tri_regions(verts: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """三角形の部位（uvparts.region_of_point：0 頭、1 胴、2/3 右左の腕、4/5 右左の手、6/7 右左の脚）"""
    from recon import uvparts
    return uvparts.region_of_point(verts[tris].mean(1), HEAD_Z)


def art_arm_mask(name: str, cam: V.Cam, verts: np.ndarray, tris: np.ndarray, arm_tri: np.ndarray,
                 rgb: np.ndarray) -> np.ndarray:
    """絵の中の腕・手の画素（2048²）：メッシュの腕・手の投影を ART_OCC_BAND 広げた帯の中の、肌・手袋の色"""
    u, v = cam.project(verts)
    p2 = np.stack([u[tris[arm_tri]], v[tris[arm_tri]]], -1)
    pix, _, _ = raster(p2, V.IMG, V.IMG)
    img = np.zeros(V.IMG * V.IMG, bool)
    img[pix] = True
    img = img.reshape(V.IMG, V.IMG)
    band = ndi.binary_dilation(img, iterations=ART_OCC_BAND)
    flat = rgb.reshape(-1, 3)
    skin = skin_not_ivory(flat).reshape(V.IMG, V.IMG) > 0.1
    mx, mn = rgb.max(-1), rgb.min(-1)
    glove = (mx < 0.36) & (mx - mn < 0.10) & (mx > 0.05)
    m = band & (skin | glove)
    m = ndi.binary_opening(m, iterations=1)
    m = ndi.binary_dilation(m, iterations=3)
    save_png(os.path.join(TEX_DIR, f'art_arm_{name}.png'),
             np.where(m[..., None], rgb * 0.5 + np.array([0.5, 0, 0]), rgb * 0.6 + 0.4 * band[..., None]))
    return m


def view_weights(cam: V.Cam, img: ViewImage, pos: np.ndarray, nrm: np.ndarray, z: np.ndarray,
                 edist: np.ndarray, field: np.ndarray | None = None, zocc: np.ndarray | None = None,
                 bias_deg: float = 0.0, art_block: np.ndarray | None = None,
                 block_texel: np.ndarray | None = None) -> dict:
    """1 つの視点について、テクセルごとの n・v、見えるか、重みの係数、色。

    field：絵を拾う位置のずらし (2, H, W)（画素。align_view の結果）。見えるかどうかはメッシュの奥行き
    （ずらさない位置）で、色と外形のマスクはずらした位置で調べる。
    """
    p = pos.copy()
    n = nrm.copy()
    if cam.mirror:
        p[:, 0] = -p[:, 0]
        n[:, 0] = -n[:, 0]
    u = cam.u0 + cam.ppm * (p @ cam.r)
    v = cam.v0 - cam.ppm * p[:, 2]
    t = p @ cam.d
    ndv = np.clip(-(n @ cam.d), 0.0, 1.0)
    ndv_raw = ndv
    if bias_deg:
        ndv = np.cos(np.minimum(np.arccos(ndv) + math.radians(bias_deg), math.pi / 2))
    zr = nearest(z, u, v, fill=np.inf)
    zmin = nearest(ndi.grey_erosion(np.where(np.isfinite(z), z, 1e9), size=3), u, v, fill=1e9)
    zr = np.where(np.isfinite(zr), zr, zmin)
    vis = t <= zr + DEPTH_TOL
    fe = EDGE_FLOOR + (1 - EDGE_FLOOR) * ramp(nearest(edist, u, v), *EDGE_RAMP)
    if zocc is not None:   # 近くに手前の別の物（腕・手）がある：絵ではそれがここに描かれているかもしれない
        fe = fe * (1 - (1 - OCC_FLOOR) * ramp(t - nearest(zocc, u, v, fill=1e9), *OCC_DEPTH))
    us, vs = u, v
    if field is not None:
        d = bilinear(np.moveaxis(field, 0, -1), u, v)
        us, vs = u + d[:, 0], v + d[:, 1]
    fm = ramp(nearest(img.mask_dist, us, vs), *MASK_RAMP)
    base = vis * fm * fe
    blocked = np.zeros(len(p), bool)
    if art_block is not None:
        # 絵ではここに腕・手が描かれている：腕・手でないテクセルはこの視点から色をもらわない
        blocked = block_texel & (nearest(art_block.astype(np.float32), us, vs) > 0.5)
        base = base * ~blocked
    full, low = img.sample(us, vs)
    return {'ndv': ndv, 'ndv_raw': ndv_raw, 'base': base, 'vis': vis, 'fm': fm, 'full': full, 'low': low,
            'u': u, 'v': v, 'blocked': blocked}


def gray(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.4 + rgb[..., 1] * 0.45 + rgb[..., 2] * 0.15


def align_view(name: str, d: dict, img: ViewImage, ref_col: np.ndarray, ref_conf: np.ndarray,
               res: int = ALIGN_RES) -> tuple[np.ndarray, dict]:
    """視点の絵を、すでに決めた視点の色（ref_col）に合わせる「ずらし」の場を求める。

    両方がよく見ているテクセルの ref_col を、この視点の画像の位置へ置いて「予想の絵」を作り
    （置けなかった画素は絵そのもの）、絵との光学的流れ（TV-L1）を求める。流れは確かさ
    （置いたテクセルの重み）で重み付けしてなめらかにし、確かさの無い所は 0 へ戻す。
    返り値：(2, 2048, 2048) の画素のずらし（絵を (u + du, v + dv) で拾う）と統計
    """
    from skimage.registration import optical_flow_tvl1
    k = res / V.IMG
    w = ref_conf * d['base'] * d['ndv'] ** 2
    ok = w > 0.02
    iu = np.clip((d['u'][ok] * k).astype(np.int64), 0, res - 1)
    iv = np.clip((d['v'][ok] * k).astype(np.int64), 0, res - 1)
    pix = iv * res + iu
    acc = np.zeros((res * res, 3))
    wac = np.zeros(res * res)
    np.add.at(wac, pix, w[ok])
    for c in range(3):
        np.add.at(acc[:, c], pix, w[ok] * ref_col[ok, c])
    art = np.asarray(Image.fromarray((img.rgb * 255).astype(np.uint8)).resize((res, res), Image.BILINEAR),
                     np.float32) / 255
    # 置けなかった画素（テクセルの間のすき間）は、近くの置いた色でうめる（正規化した畳み込み）
    wac = ndi.gaussian_filter(wac.reshape(res, res), 1.2)
    acc = np.stack([ndi.gaussian_filter(acc[:, c].reshape(res, res), 1.2) for c in range(3)], -1)
    has = wac > 0.02
    pred = np.where(has[..., None], acc / np.maximum(wac, 1e-12)[..., None], art)
    conf = np.minimum(wac, 1.0)
    if has.sum() < 2000:   # すでに決めた視点と重なる所がほとんど無い：ずらさない
        return np.zeros((2, V.IMG, V.IMG), np.float32), {'flow_px_median': 0.0, 'skipped': True}
    t0 = time.time()
    flow = optical_flow_tvl1(gray(pred).astype(np.float32), gray(art).astype(np.float32),
                             attachment=10, tightness=0.3, num_warp=5, num_iter=30)
    # 確かさで重み付けしてなめらかに（確かさの無い所は 0 へ）
    cw = np.where(has, conf, 0.0)
    sig = ALIGN_SIGMA * k
    den = ndi.gaussian_filter(cw, sig) + 0.02
    fl = np.stack([ndi.gaussian_filter(flow[i] * cw, sig) / den for i in range(2)])
    lim = ALIGN_MAX * k
    mag = np.hypot(fl[0], fl[1])
    fl *= np.minimum(1.0, lim / np.maximum(mag, 1e-9))
    # 画素の単位を 2048 に、(dv, du) → (du, dv) の順に
    field = np.stack([fl[1], fl[0]]) / k
    field = np.stack([ndi.zoom(f, 1 / k, order=1) for f in field])
    stats = {'flow_px_median': round(float(np.median(np.hypot(fl[0], fl[1])[has]) / k), 2),
             'flow_px_p90': round(float(np.percentile(np.hypot(fl[0], fl[1])[has], 90) / k), 2),
             'secs': round(time.time() - t0, 1)}
    if DEBUG_ALIGN:
        vis_img = np.concatenate([art, pred, np.clip(0.5 + (pred - art) * 2, 0, 1)], 1)
        save_png(os.path.join(TEX_DIR, f'align_{name}.png'), vis_img)
    return field.astype(np.float32), stats


def view_gain(name: str, reg: np.ndarray) -> np.ndarray:
    """テクセルごとの視点の重みの倍率。腕の無い絵は腕・手に 0、腕の無い絵がある向きの腕のある絵は胴・脚に弱く"""
    g = np.full(len(reg), VIEW_GAIN[name], np.float32)
    arm = np.isin(reg, (2, 3, 4, 5))
    if name in NOARM_VIEWS:
        g[arm] = 0.0
    if name in ARMED_BODY_GAIN:
        g[~arm & (reg != 0)] *= ARMED_BODY_GAIN[name]
    if name in ('side_left', 'front_left45'):
        g[reg == 0] *= HEAD_LEFT_VIEW_GAIN
    return g


def bake(mesh: dict, size: int, cams: dict[str, V.Cam], atlas_meta: dict, align: bool = True) -> dict:
    verts, tris, uv = mesh['verts'], mesh['tris'], mesh['uv']
    vn = smooth_normals(verts, tris)
    vns = smooth_normals(verts, tris, NORMAL_SMOOTH)
    t0 = time.time()
    pix, tri, bar = uv_texels(uv, size)
    pos = (verts[tris[tri]] * bar[..., None]).sum(1)
    nrm = (vn[tris[tri]] * bar[..., None]).sum(1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    nrw = (vns[tris[tri]] * bar[..., None]).sum(1)
    nrw /= np.maximum(np.linalg.norm(nrw, axis=1, keepdims=True), 1e-12)
    log(f'テクセル {len(pix):,}（{len(pix) / size / size:.1%}）{time.time() - t0:.1f}s')
    treg = tri_regions(verts, tris)
    arm_tri = np.isin(treg, (2, 3, 4, 5))
    reg = treg[tri]
    # 絵の腕に遮られうるテクセル：腕・手・頭でないもの（胴・脚。首の肌は頭の近くなので z < 1.15）
    block_texel = ~np.isin(reg, (0, 2, 3, 4, 5)) & (pos[:, 2] < 1.15)
    blocks = {}

    # 視点ごと
    per = {}
    geo = {}
    for name in REAL_VIEWS:
        cam = cams[name]
        img = ViewImage(name, atlas_meta if name == 'front' else None)
        z = zbuffer(verts, tris[~arm_tri] if name in NOARM_VIEWS else tris, cam)
        geo[name] = (img, z, depth_edge_dist(z), near_occluder_depth(z))
        if name in ART_OCCLUDE_VIEWS:
            blocks[name] = art_arm_mask(name, cam, verts, tris, arm_tri, img.rgb)
        per[name] = view_weights(cam, img, pos, nrw, z, geo[name][2], None, geo[name][3], VIEW_BIAS_DEG[name],
                                 blocks.get(name), block_texel)
        per[name]['gain'] = view_gain(name, reg)
        per[name]['img'] = img
        log(f'{name}: 見える {per[name]["vis"].mean():.1%}  重み>0 {(per[name]["base"] * per[name]["ndv"] > 0).mean():.1%}')
    # 視点の合わせ込み：正面を基準に、ほかの視点の絵をメッシュの上の模様がそろうようにずらす
    align_stats = {}
    fields = {}
    if align:
        done = ['front']
        for name in ALIGN_ORDER:
            ws = {k: per[k]['base'] * per[k]['ndv'] ** P_HIGH for k in done}
            sw = sum(ws.values())
            ref = sum(ws[k][:, None] * per[k]['full'] for k in done) / np.maximum(sw, 1e-12)[:, None]
            conf = np.clip(sum(per[k]['base'] * per[k]['ndv_raw'] ** 2 for k in done), 0, 1)
            field, st = align_view(name, per[name], geo[name][0], ref, conf)
            fields[name] = field
            img, z, ed, zo = geo[name]
            gain = per[name]['gain']
            per[name] = view_weights(cams[name], img, pos, nrw, z, ed, field, zo, VIEW_BIAS_DEG[name],
                                     blocks.get(name), block_texel)
            per[name]['gain'] = gain
            per[name]['img'] = img
            align_stats[name] = st
            done.append(name)
            log(f'{name}: 合わせ込み {st}')
    best_real = np.max(np.stack([d['base'] * d['ndv_raw'] for d in per.values()], 1), 1)
    no_mirror = asymmetric_left(pos)
    for name in MIRROR_VIEWS:
        cam = cams[name].mirrored()
        img = per[name]['img']
        z = zbuffer(verts, tris[~arm_tri] if name in NOARM_VIEWS else tris, cam)
        # 実の視点で求めたずらしをそのまま使う（左右対称なら、反転した点も絵の同じ所に写るので）
        d = view_weights(cam, img, pos, nrw, z, depth_edge_dist(z), fields.get(name), near_occluder_depth(z),
                         VIEW_BIAS_DEG[name], blocks.get(name), block_texel)
        d['gain'] = MIRROR_GAIN * (1.0 - ramp(best_real, *MIRROR_NDV)) * ~no_mirror * (pos[:, 0] > 0)
        if name in NOARM_VIEWS:
            d['gain'] = d['gain'] * ~np.isin(reg, (2, 3, 4, 5))
        per[name + '_mirror'] = d
        log(f'{name}_mirror: 使う {(d["gain"] * d["base"] * d["ndv"] > 0).mean():.1%}')
    for name in HEAD_MIRROR_VIEWS:   # 頭の左側（本文の 3。HEAD_MIRROR_VIEWS）
        cam = cams[name].mirrored()
        img = per[name]['img']
        z = zbuffer(verts, tris, cam)
        d = view_weights(cam, img, pos, nrw, z, depth_edge_dist(z), fields.get(name), near_occluder_depth(z),
                         VIEW_BIAS_DEG[name], None, None)
        d['gain'] = HEAD_MIRROR_GAIN * VIEW_GAIN[name] * ((reg == 0) & (pos[:, 0] > 0.0)).astype(np.float32)
        per[name + '_head_mirror'] = d
        log(f'{name}_head_mirror: 使う {(d["gain"] * d["base"] * d["ndv"] > 0).mean():.1%}')

    if os.environ.get('TEX_DEBUG_BOX'):   # 調べる箱の中のテクセルの、視点ごとの重みを表示する（調べ物用）
        bx = [float(c) for c in os.environ['TEX_DEBUG_BOX'].split(',')]
        m = ((pos[:, 0] >= bx[0]) & (pos[:, 0] <= bx[1]) & (pos[:, 1] >= bx[2]) & (pos[:, 1] <= bx[3])
             & (pos[:, 2] >= bx[4]) & (pos[:, 2] <= bx[5]))
        log(f'debug box {int(m.sum())} texels')
        for k, d in per.items():
            w = d['gain'] * d['base'] * d['ndv'] ** P_LOW
            log(f'  {k:22s} w mean {w[m].mean():.4f} max {w[m].max():.3f} vis {d["vis"][m].mean():.2f} '
                f'ndv {d["ndv"][m].mean():.2f} col {np.round(d["full"][m].mean(0), 2)}')
    # 2 つの帯で混ぜる
    wl = {k: d['gain'] * d['base'] * d['ndv'] ** P_LOW for k, d in per.items()}
    wh = {k: d['gain'] * d['base'] * d['ndv'] ** P_HIGH for k, d in per.items()}
    sl = sum(wl.values())
    sh = sum(wh.values())
    low = sum(wl[k][:, None] * per[k]['low'] for k in per) / np.maximum(sl, 1e-12)[:, None]
    high = sum(wh[k][:, None] * (per[k]['full'] - per[k]['low']) for k in per) / np.maximum(sh, 1e-30)[:, None]
    high[sh <= 1e-30] = 0.0
    col = low + high
    # 確かさ（塗り足しを混ぜるかどうか）は、ハンデを付けない向きで測る
    sl = sum(d['gain'] * d['base'] * d['ndv_raw'] ** P_LOW for d in per.values())
    # どの視点が一番効いているか（確認用）
    keys = list(per)
    winner = np.argmax(np.stack([wl[k] for k in keys], 1), 1)
    winner[sl <= 0] = -1

    # 塗り足し：よく見えているテクセルから、3D の近さと法線の近さで
    seed = sl >= W_SEED
    need = sl < W_FULL
    log(f'塗り足し {need.mean():.1%} のテクセル（元 {seed.mean():.1%}）')
    if need.any():
        sidx = np.nonzero(seed)[0]
        tree = cKDTree(pos[sidx])
        qidx = np.nonzero(need)[0]
        dist, nb = tree.query(pos[qidx], k=INPAINT_K, workers=-1)
        nb = sidx[nb]
        cosn = np.einsum('qkc,qc->qk', nrm[nb], nrm[qidx])
        w = np.exp(-dist / 0.01) * np.clip(cosn, 0.05, 1.0) ** 2 + 1e-12
        fill = (w[..., None] * col[nb]).sum(1) / w.sum(1)[:, None]
        a = np.clip(sl[qidx] / W_FULL, 0, 1)[:, None]
        col[qidx] = a * col[qidx] + (1 - a) * fill

    # 確認：胴・脚のテクセルのうち、一番効いている視点の絵の画素が絵の腕・手の中にあるものの割合（0 のはず）
    win_blocked = np.zeros(len(pos), bool)
    for i, k in enumerate(keys):
        win_blocked |= (winner == i) & per[k]['blocked']
    occ_stats = {'blocked_texels': {k: int(d['blocked'].sum()) for k, d in per.items()},
                 'winner_in_art_arm_fraction': round(float(win_blocked[block_texel].mean()), 6)}
    log(f'絵の腕の遮り {occ_stats}')
    return {'pix': pix, 'tri': tri, 'bar': bar, 'pos': pos, 'nrm': nrm, 'col': col, 'sl': sl, 'winner': winner,
            'keys': keys, 'per': per, 'size': size, 'align': align_stats, 'reg': reg, 'art_occlusion': occ_stats}


# ---------------------------------------------------------------- 頭の肌と髪の塗り分け

def skin_likeness(col: np.ndarray, loose: bool = False) -> np.ndarray:
    """肌の色（顔・耳。影の側も含む）らしさ 0..1。col は sRGB の 0..1（hair.skin_mask の範囲をなめらかに）。

    loose：髪と混ざってくすんだ肌色（耳のまわりのぼかしの色、例 (198,134,94)）も肌とみなす
    （髪の茶色 (155,75,42) は g が低いので入らない。琥珀色は b が低いので入らない）
    """
    r, g, b = col[:, 0], col[:, 1], col[:, 2]
    r0, g0 = (0.66, 0.44) if loose else (0.74, 0.50)
    return (ramp(r, r0, r0 + 0.06) * ramp(g, g0, g0 + 0.06) * (1 - ramp(g, 0.84, 0.88))
            * ramp(b, 0.30, 0.35) * (1 - ramp(b, 0.72, 0.76)) * ramp(r - b, 0.16, 0.22))


def head_cleanup(res: dict) -> None:
    """頭の髪の房に付いた肌色（絵の耳）と、顔の横の肌に付いた髪の暗い色を、同じ側の近くの色で塗り直す。

    形には耳が無く（hair.py：耳は横の髪の中）、あごも絵より後ろまである。そのため絵の耳の肌色が髪の房の
    ところどころに、絵のもみあげ・あごの線の暗い色がほおの横に写り、斜めから見ると破れた模様になる。
    頭の面を hair.py の顔の範囲（生え際より下・y < y_face）で「肌」と「髪」に分け、分けた側に合わない色の
    テクセルを、同じ側の合う色のテクセルから 3D の近さで引いた色で置き換える。
    """
    from recon import hair as H
    pos, col = res['pos'], res['col']
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    zh = H.hairline_z(np.abs(x))
    yf = H.HAIRLINE['y_face']
    head = (z > HEAD_CLEAN_Z[0]) & (z < HEAD_CLEAN_Z[1]) & (np.abs(x) < 0.16)
    skin_zone = ((z > SKIN_CLEAN_ZMIN) & (z < SKIN_CLEAN_ZMAX) & (np.abs(x) < 0.16)
                 & (y < yf - 0.005) & (z < zh - 0.005))
    hair_zone = head & ~((y < yf + 0.005) & (z < zh + 0.005))
    sk = skin_likeness(col)
    skl = skin_likeness(col, loose=True)
    stats = {}
    # 髪の側：くすんだ肌色も消す。肌の側：肌の色でないもの（髪・線の暗い色）はすべて消す
    # 肌の側は横を向いた面（ほお・あごの横）だけ：正面・下を向いた面（あごの先・あごの下の影）は正面の絵の
    # とおりが正しい（あごの線・影を消すと顔の材質の縁が見える）
    side = ramp(np.abs(res['nrm'][:, 0]), 0.3, 0.5)
    for name, zone, bad, good_src in (('hair', hair_zone, skl, skl < 0.02),
                                      ('skin', skin_zone, (1.0 - skl) * side, sk > 0.6)):
        tgt = np.nonzero(zone & (bad > 0.02))[0]
        src = np.nonzero(zone & good_src)[0]
        stats[name] = int((zone & (bad > 0.5)).sum())
        if len(tgt) == 0 or len(src) < INPAINT_K:
            continue
        tree = cKDTree(pos[src])
        dist, nb = tree.query(pos[tgt], k=INPAINT_K, workers=-1)
        nb = src[nb]
        cosn = np.einsum('qkc,qc->qk', res['nrm'][nb], res['nrm'][tgt])
        w = np.exp(-dist / 0.006) * np.clip(cosn, 0.05, 1.0) ** 2 + 1e-12
        fill = (w[..., None] * col[nb]).sum(1) / w.sum(1)[:, None]
        # 顔の材質の縁の近く（正面の色へ寄せた所）は変えない：材質の境で色がそろうように
        a = (bad[tgt] * (1.0 - res.get('face_feather', np.zeros(len(col)))[tgt]))[:, None]
        col[tgt] = a * fill + (1 - a) * col[tgt]
    res['col'] = col
    res['head_cleanup'] = stats
    log(f'頭の塗り分け：髪の側の肌色 {stats.get("hair", 0):,}、肌の側の肌でない色 {stats.get("skin", 0):,} テクセル')


def _repaint(pos, nrm, col, tgt, src, amount, scale=0.01) -> None:
    """tgt のテクセルの色を、src のテクセルから 3D の近さ・法線の近さで引いた色へ amount だけ寄せる（col を書き換える）"""
    if len(tgt) == 0 or len(src) < INPAINT_K:
        return
    tree = cKDTree(pos[src])
    dist, nb = tree.query(pos[tgt], k=INPAINT_K, workers=-1)
    nb = src[nb]
    cosn = np.einsum('qkc,qc->qk', nrm[nb], nrm[tgt])
    w = np.exp(-dist / scale) * np.clip(cosn, 0.05, 1.0) ** 2 + 1e-12
    fill = (w[..., None] * col[nb]).sum(1) / w.sum(1)[:, None]
    a = np.clip(amount, 0, 1)[:, None]
    col[tgt] = a * fill + (1 - a) * col[tgt]


def skin_not_ivory(col: np.ndarray) -> np.ndarray:
    """肌らしさ（くすんだ肌も含む）から、影の側の象牙色（板・膝当て：r と g がほぼ同じ）を除いたもの 0..1"""
    rg = col[:, 0] - col[:, 1]
    return skin_likeness(col, loose=True) * ramp(rg, 0.10, 0.14) * (1 - ramp(rg, 0.32, 0.36))


def body_cleanup(res: dict) -> None:
    """肌の出るはずのない所（胴の服・えり・脚・腕の袖）に付いた肌色を、同じ部位の肌でない近くの色で塗り直す。

    絵の腕・手の色が胴の横・太ももの板・袖の裏に写った所や、どの視点もよく見ていないテクセルが近くの素肌の
    前腕の色で塗り足された所（腕を下ろすと見える袖の裏・わきの下）。部位（uvparts）をまたがずに引く。
    えり・フード：胴の z < 1.19 で上を向いた面（n.z > 0.5）は肌にしない（首の前の素肌は正面を向いている）。
    """
    pos, nrm, col, reg = res['pos'], res['nrm'], res['col'], res['reg']
    z = pos[:, 2]
    # えりの上を向いた面は、どの視点もよく見ていない（塗り足した）所だけ：正面から見える首の前の素肌は残す
    x, y = pos[:, 0], pos[:, 1]
    # フード・えり：首の前の V（正面の絵で |x| < 約 0.045）の外と、首の後ろは肌にしない（絵ではフードのれんが色）
    hood = (reg == 1) & (z >= 1.10) & (z < 1.215) & ((np.abs(x) > NECK_V_HALF) | (y > 0.01))
    nonskin = (((reg == 1) & (z < 1.10)) | hood | ((reg == 1) & (z < 1.19) & (nrm[:, 2] > 0.5) & (res['sl'] < 2 * W_FULL))
               | np.isin(reg, (6, 7)) | (np.isin(reg, (2, 3)) & (z > 1.01)))
    skl = skin_not_ivory(col)
    stats = {}
    for gname, group in (('torso', reg == 1), ('arms', np.isin(reg, (2, 3))), ('legs', np.isin(reg, (6, 7)))):
        zone = nonskin & group
        tgt = np.nonzero(zone & (skl > 0.02))[0]
        src = np.nonzero(zone & (skl < 0.01) & (res['sl'] >= W_SEED))[0]
        stats[gname] = int(len(tgt))
        for _ in range(2):   # 2 回（肌色の広い所の真ん中は、1 回目は肌色の混ざった色になる）
            _repaint(pos, nrm, col, tgt, src, np.clip(skl[tgt] * 3, 0, 1), 0.015)
    res['col'] = col
    res['body_cleanup'] = stats
    log(f'体の肌色の塗り直し {stats}')


def neck_cleanup(res: dict) -> None:
    """首の前（のど）とあごの下を肌の色にそろえる（haru_neck.png：首の素肌を茶色の帯で横切らない）。

    あごの下・首の上の端の面は下や上を向いていて、どの視点もよく見ていない。塗り足しで、えり・フードのれんが色や
    髪の暗い色が混ざり、のどを横切る茶色の帯に見えた。首の前の範囲（NECK_ZONE）の肌でない色を、同じ範囲の
    よく見えている肌のテクセルの色で塗り直す。
    """
    pos, nrm, col = res['pos'], res['nrm'], res['col']
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    nz = NECK_ZONE
    zone = ((z > nz['z'][0]) & (z < nz['z'][1]) & (np.abs(x) < nz['x']) & (y < nz['y'])
            & np.isin(res['reg'], (0, 1)))
    skl = skin_likeness(col)
    tgt = np.nonzero(zone & (skl < 0.6))[0]
    src = np.nonzero(zone & (skin_likeness(col) > 0.7) & (res['sl'] >= W_SEED))[0]
    if len(src) < INPAINT_K:   # 首の前によく見えた肌が無ければ、顔の下の肌から
        src = np.nonzero((z > nz['z'][0]) & (z < nz['z'][1] + 0.03) & (np.abs(x) < 0.06)
                         & (skin_likeness(col) > 0.7) & (res['sl'] >= W_SEED))[0]
    # 範囲の縁（左右・下）はなめらかに
    edge = (ramp(nz['x'] - np.abs(x[tgt]), 0.0, 0.008) * ramp(z[tgt] - nz['z'][0], 0.0, 0.008))
    for _ in range(2):
        _repaint(pos, nrm, col, tgt, src, edge * (1 - 0.8 * skl[tgt]), 0.012)
    res['col'] = col
    res['neck_cleanup'] = int(len(tgt))
    log(f'首の前の塗り直し {len(tgt):,} テクセル（元の肌 {len(src):,}）')


def hand_cleanup(res: dict) -> None:
    """手（uvparts の部位 4・5）に付いた上着のれんが色を、同じ手の近くの手袋・肌の色で塗り直す。

    真横・斜めの絵の手は、形の手と数 cm ずれて描かれていて、手の横に胴・ズボンのれんが色が写り、手袋が縞に見えた。
    """
    pos, nrm, col, reg = res['pos'], res['nrm'], res['col'], res['reg']
    r, g, b = col[:, 0], col[:, 1], col[:, 2]
    brick = ramp(r - g, 0.18, 0.28) * ramp(r, 0.45, 0.55) * (1 - ramp(g, 0.52, 0.60))
    stats = {}
    for side, rg in (('right', 4), ('left', 5)):
        hand = reg == rg
        tgt = np.nonzero(hand & (brick > 0.05))[0]
        src = np.nonzero(hand & (brick < 0.01) & (res['sl'] >= W_SEED))[0]
        stats[side] = int(len(tgt))
        for _ in range(2):
            _repaint(pos, nrm, col, tgt, src, np.clip(brick[tgt] * 2, 0, 1), 0.008)
    res['col'] = col
    res['hand_cleanup'] = stats
    log(f'手のれんが色の塗り直し {stats}')


def sole_cleanup(res: dict) -> None:
    """靴底（SOLE_TOP より下の脚のテクセル）を靴底の色の一色にする（上の縁 4mm でなめらかに）"""
    z = res['pos'][:, 2]
    a = ((np.isin(res['reg'], (6, 7))) * (1.0 - ramp(z, SOLE_TOP - 0.002, SOLE_TOP + 0.002)))[:, None]
    res['col'] = a * np.array(SOLE_RGB)[None] + (1 - a) * res['col']
    res['sole_cleanup'] = int((a[:, 0] > 0.5).sum())
    log(f'靴底の塗り {res["sole_cleanup"]:,} テクセル')


def hair_colour_match(res: dict) -> None:
    """髪のテクセルの色の平均・ばらつきを、正面・背面の絵の髪の画素にそろえる（塗り足しで灰色がかった髪を戻す）"""
    from recon import hair as H

    def hairish(c):
        r, g, b = c[..., 0], c[..., 1], c[..., 2]
        mx = np.maximum(np.maximum(r, g), b)
        return (r - b > 0.06) & (mx < 0.62) & (mx > 0.08) & (skin_likeness(c.reshape(-1, 3), True).reshape(r.shape) < 0.05)

    art = []
    cams = V.load_calib()
    for n in ('front', 'back'):
        rgb, _ = srgb_float(V.load_rgba(n))
        c = cams[n]
        sub = rgb[int(c.v_of(1.56)):int(c.v_of(1.30)), int(c.u0 - 0.18 * c.ppm):int(c.u0 + 0.18 * c.ppm)]
        mask = V.load_mask(n)[int(c.v_of(1.56)):int(c.v_of(1.30)), int(c.u0 - 0.18 * c.ppm):int(c.u0 + 0.18 * c.ppm)]
        art.append(sub[hairish(sub) & mask])
    art = np.concatenate(art)
    pos, col = res['pos'], res['col']
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    face = (y < H.HAIRLINE['y_face'] + 0.005) & (z < H.hairline_z(np.abs(x)) + 0.005)
    hz = (res['reg'] == 0) & ~face & (z > 1.25) & hairish(col)
    if hz.sum() < 100 or len(art) < 100:
        return
    m_a, s_a = art.mean(0), art.std(0)
    m_t, s_t = col[hz].mean(0), col[hz].std(0)
    new = (col[hz] - m_t) * np.clip(s_a / np.maximum(s_t, 1e-3), 0.7, 1.4) + m_a
    col[hz] = 0.3 * col[hz] + 0.7 * new
    # 横・斜めを向いた髪の細部を弱める（HAIR_SIDE_DETAIL）：真横・斜めの絵の房の線は、形の房と位置が合わず、
    # 横から見ると細かな線のまだら（丸いもじゃもじゃ）に見えた。3D の近さで平均した色（房 1 本の大きさ）へ寄せ、
    # 房の形は形の陰で見せる。正面・背面を向いた髪は絵の細部のまま
    idx = np.nonzero(hz)[0]
    if len(idx) > 1000:
        tree = cKDTree(pos[idx])
        _, nb = tree.query(pos[idx], k=24, workers=-1)
        mean = col[idx][nb].mean(1)
        side = ramp(np.abs(res['nrm'][idx, 0]), 0.35, 0.8)
        keep = (1.0 - HAIR_SIDE_DETAIL * side)[:, None]
        col[idx] = mean + keep * (col[idx] - mean)
    res['col'] = col
    res['hair_colour'] = {'art_mean': np.round(m_a * 255).tolist(), 'before_mean': np.round(m_t * 255).tolist(),
                          'texels': int(hz.sum())}
    log(f'髪の色合わせ {res["hair_colour"]}')


# ---------------------------------------------------------------- 顔の材質

def face_polys(mesh: dict, cams: dict[str, V.Cam], atlas_meta: dict) -> np.ndarray:
    """顔の材質にする三角形：顔の窓の中・正面向き・正面から見える"""
    verts, tris = mesh['verts'], mesh['tris']
    cam = cams['front']
    fu, fv = cam.project(verts)
    z = zbuffer(verts, tris, cam)
    zr = nearest(z, fu, fv, fill=np.inf)
    vis_v = (verts @ cam.d) <= np.where(np.isfinite(zr), zr, np.inf) + DEPTH_TOL
    wx0, wy0, wx1, wy1 = atlas_meta['window_front_px']
    inside_v = (fu >= wx0) & (fu <= wx1) & (fv >= wy0) & (fv <= wy1)
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    sel = inside_v[tris].all(1) & vis_v[tris].all(1) & (-fn[:, 1] > FACE_NDV_MIN)
    # 一番大きいつながり（同じ位置の頂点でつなぐ）だけを残し、中の小さな穴を埋める
    key = np.round(verts / 1e-5).astype(np.int64)
    _, wid = np.unique(key, axis=0, return_inverse=True)
    wid = wid.ravel()
    wt = wid[tris]
    from scipy import sparse
    n = int(wid.max()) + 1

    def components(mask: np.ndarray) -> np.ndarray:
        idx = np.nonzero(mask)[0]
        e = np.concatenate([wt[idx][:, [0, 1]], wt[idx][:, [1, 2]]])
        A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
        _, comp = sparse.csgraph.connected_components(A, directed=False)
        lab = np.full(len(tris), -1)
        lab[idx] = comp[wt[idx][:, 0]]
        return lab

    lab = components(sel)
    if sel.any():
        vals, cnt = np.unique(lab[sel], return_counts=True)
        sel = lab == vals[np.argmax(cnt)]
    # 穴：窓の中の選ばれていない三角形のつながりのうち、窓の縁に触れないもの
    rest = inside_v[tris].all(1) & ~sel & (-fn[:, 1] > 0.0) & vis_v[tris].any(1)
    lab2 = components(rest)
    edge_v = np.zeros(len(verts), bool)
    wx0, wy0, wx1, wy1 = atlas_meta['window_front_px']
    near_edge = (np.minimum(np.minimum(fu - wx0, wx1 - fu), np.minimum(fv - wy0, wy1 - fv)) < 6)
    edge_v |= near_edge
    for lv in np.unique(lab2[rest]):
        m = lab2 == lv
        if m.sum() < 60 and not edge_v[tris[m]].any():
            sel |= m
    # あごの下（首・フードの襟）は顔の材質にしない：横から見ると正面の投影が引き伸ばされるので
    cy = fv[tris].mean(1)
    sel &= cy <= FACE_CHIN_PX
    # 表情で変わる画素（アトラスの 4 区画が違う所）の上で正面から一番手前に見える三角形は、向きに
    # かかわらず顔の材質にする（前髪のすき間の横向きの面などで、眉の一部が表情で変わらなくなるのを防ぐ）
    expr = expression_mask_front(atlas_meta)
    pix, tri, bar = raster(np.stack([fu[tris], fv[tris]], -1), V.IMG, V.IMG)
    dz = (((verts @ cam.d)[tris[tri]]) * bar).sum(1)
    order = np.lexsort((dz, pix))
    pix, tri = pix[order], tri[order]
    first = np.r_[True, pix[1:] != pix[:-1]]
    pix, tri = pix[first], tri[first]
    hit = expr.ravel()[pix]
    add = np.zeros(len(tris), bool)
    add[tri[hit]] = True
    add &= -fn[:, 1] > 0.0
    sel |= add
    return sel


def expression_mask_front(atlas_meta: dict) -> np.ndarray:
    """表情で変わる画素（アトラスの 4 区画のどれかが区画 0 と違う所、3px 広げる）を正面の絵の画素 (2048²) で"""
    a = np.asarray(Image.open(os.path.join(WORK, atlas_meta['atlas_file'])).convert('RGB')).astype(np.int16)
    h = a.shape[0] // 2
    q0 = a[:h, :h]
    diff = np.zeros((h, h), bool)
    for qy, qx in ((0, h), (h, 0), (h, h)):
        diff |= np.abs(a[qy:qy + h, qx:qx + h] - q0).max(-1) > 3
    k = atlas_meta['atlas_px_per_front_px']
    wx0, wy0 = atlas_meta['window_front_px'][:2]
    qx0, qy0 = atlas_meta['window_atlas_px'][:2]
    ys, xs = np.nonzero(diff)
    fx = np.floor(wx0 + (xs + 0.5 - qx0) / k).astype(np.int64)
    fy = np.floor(wy0 + (ys + 0.5 - qy0) / k).astype(np.int64)
    out = np.zeros((V.IMG, V.IMG), bool)
    out[np.clip(fy, 0, V.IMG - 1), np.clip(fx, 0, V.IMG - 1)] = True
    return ndi.binary_dilation(out, iterations=3)


def expression_coverage(mesh: dict, cams: dict[str, V.Cam], atlas_meta: dict, sel: np.ndarray) -> float:
    """表情で変わる画素のうち、正面から見て顔の材質の三角形が一番手前にある割合（確認用）"""
    verts, tris = mesh['verts'], mesh['tris']
    cam = cams['front']
    fu, fv = cam.project(verts)
    pix, tri, bar = raster(np.stack([fu[tris], fv[tris]], -1), V.IMG, V.IMG)
    dz = (((verts @ cam.d)[tris[tri]]) * bar).sum(1)
    order = np.lexsort((dz, pix))
    pix, tri = pix[order], tri[order]
    first = np.r_[True, pix[1:] != pix[:-1]]
    pix, tri = pix[first], tri[first]
    expr = ndi.binary_erosion(expression_mask_front(atlas_meta), iterations=3)
    img = np.full(V.IMG * V.IMG, -1)
    img[pix] = sel[tri].astype(int)
    v = img[expr.ravel()]
    return float((v == 1).sum() / max((v >= 0).sum(), 1))


def face_uv(verts: np.ndarray, cams: dict[str, V.Cam], atlas_meta: dict) -> np.ndarray:
    """頂点の正面の投影 → 表情アトラスの区画 0 の Blender の UV（face_atlas.json の式のとおり）"""
    fu, fv = cams['front'].project(verts)
    wx0, wy0 = atlas_meta['window_front_px'][:2]
    qx0, qy0 = atlas_meta['window_atlas_px'][:2]
    k = atlas_meta['atlas_px_per_front_px']
    sz = atlas_meta['atlas_size'][0]
    ax = qx0 + (fu - wx0) * k
    ay = qy0 + (fv - wy0) * k
    return np.stack([ax / sz, 1.0 - ay / sz], -1)


def feather_face_border(res: dict, mesh: dict, sel: np.ndarray) -> None:
    """顔の材質の縁の近くの体のテクセルを、正面（アトラスの通常）の色へ寄せる"""
    verts, tris = mesh['verts'], mesh['tris']
    fv_idx = np.unique(tris[sel])
    if len(fv_idx) == 0:
        return
    tree = cKDTree(verts[fv_idx])
    d, _ = tree.query(res['pos'], k=1, workers=-1)
    fr = res['per']['front']
    a = np.clip(1.0 - d / FACE_FEATHER, 0, 1) * (fr['vis'] & (fr['fm'] > 0.5) & (fr['ndv'] > 0.05))
    # 横を向いた面（ほおの横・あご）には正面の色を持ち込まない（引き伸ばされた線・髪のしみになる）
    a = a * ramp(fr['ndv_raw'], 0.2, 0.4)
    a = a * a * (3 - 2 * a)
    res['col'] = res['col'] * (1 - a[:, None]) + fr['full'] * a[:, None]
    res['face_feather'] = a


# ---------------------------------------------------------------- 画像にする・発光

def to_image(res: dict, values: np.ndarray, fill_all: bool = True) -> np.ndarray:
    """テクセルの値を size×size の画像へ。島の外は一番近い島の値で埋める"""
    s = res['size']
    ch = values.shape[1] if values.ndim == 2 else 1
    img = np.zeros((s * s, ch), np.float32)
    img[res['pix']] = values.reshape(len(values), ch)
    img = img.reshape(s, s, ch)
    if fill_all:
        cov = np.zeros(s * s, bool)
        cov[res['pix']] = True
        cov = cov.reshape(s, s)
        _, (iy, ix) = ndi.distance_transform_edt(~cov, return_indices=True)
        img = img[iy, ix]
    return img


def amber_mask(rgb: np.ndarray) -> np.ndarray:
    """琥珀色（#FFBC52 付近）の度合い 0..1。rgb は sRGB の 0..1"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    s = (mx - mn) / np.maximum(mx, 1e-6)
    hue = np.degrees(np.arctan2(math.sqrt(3) * (g - b), 2 * r - g - b)) % 360
    m = ramp(mx, 0.78, 0.88) * ramp(s, 0.48, 0.58) * ramp(hue, 22, 28) * (1 - ramp(hue, 50, 56))
    return m


def emission_image(base: np.ndarray, cov: np.ndarray) -> np.ndarray:
    m = ramp(amber_mask(base), 0.3, 0.6)   # 弱い所（肌・髪のわずかな反応）は 0 に
    # 小さな点（数テクセル）は落とす
    hard = (m > 0.5) & cov
    lab, n = ndi.label(hard)
    if n:
        sizes = ndi.sum(hard, lab, range(1, n + 1))
        small = np.isin(lab, np.nonzero(sizes < 12)[0] + 1)
        m = m * ~ndi.binary_dilation(small, iterations=2)
    return base * m[..., None]


def save_png(path: str, rgb: np.ndarray) -> None:
    Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


# ---------------------------------------------------------------- 書き出し（bpy）

def build_materials_and_export(obj, mesh: dict, sel: np.ndarray, fuv: np.ndarray, base_p: str, emit_p: str,
                               atlas_p: str, out: str) -> None:
    import bpy
    me = obj.data
    # 顔の三角形の角の UV を、区画 0 への正投影に置き換える
    uvl = mesh['uv'].copy()
    uvl[sel] = fuv[mesh['tris'][sel]]
    flat = np.zeros((len(me.loops), 2))
    flat[mesh['loops'].ravel()] = uvl.reshape(-1, 2)
    me.uv_layers[0].data.foreach_set('uv', flat.ravel())
    me.uv_layers[0].name = 'UVMap'
    old = [m for m in me.materials if m]
    me.materials.clear()
    for m in old:
        bpy.data.materials.remove(m)

    def mat(name: str, base: str, emit: str | None):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        m.use_backface_culling = True   # 閉じた面なので片面（glTF の doubleSided = false）
        nt = m.node_tree
        bsdf = nt.nodes['Principled BSDF']
        bsdf.inputs['Roughness'].default_value = ROUGHNESS
        bsdf.inputs['Metallic'].default_value = 0.0
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(base)
        tex.image.name = f'{name}_base'
        tex.location = (-400, 200)
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if emit:
            et = nt.nodes.new('ShaderNodeTexImage')
            et.image = bpy.data.images.load(emit)
            et.image.name = f'{name}_emit'
            et.location = (-400, -200)
            nt.links.new(et.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = EMIT_STRENGTH
        return m

    me.materials.append(mat('haru_body', base_p, emit_p))
    me.materials.append(mat('haru_face', atlas_p, None))
    mi = np.zeros(len(me.polygons), np.int32)
    poly_of_tri = np.arange(len(me.polygons))
    mi[poly_of_tri[sel]] = 1
    me.polygons.foreach_set('material_index', mi)
    me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), bool))
    me.update()
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, export_animations=False,
                              use_selection=True, export_image_format='AUTO')


# ---------------------------------------------------------------- 確認画像（Cycles）

BG = np.array([128, 128, 128], np.float32)


def art_on_gray(name_or_path: str, res: int) -> np.ndarray:
    p = name_or_path if os.path.isabs(name_or_path) else os.path.join(V.SRC, name_or_path)
    im = Image.open(p).convert('RGBA')
    bg = Image.new('RGBA', im.size, (128, 128, 128, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert('RGB').resize((res, res), Image.LANCZOS))


def render_setup(glb: str, samples: int):
    import bpy
    from lib import common as C
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=glb)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 3
    scene.render.film_transparent = True
    scene.render.use_persistent_data = True
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    world = bpy.data.worlds.new('tex_world')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    # 材質ごとに「照明なし（下地の色をそのまま）」の出力を用意する
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if not bsdf or not out:
            continue
        em = nt.nodes.new('ShaderNodeEmission')
        em.name = 'unlit'
        if bsdf.inputs['Base Color'].links:
            nt.links.new(bsdf.inputs['Base Color'].links[0].from_socket, em.inputs['Color'])
        else:
            em.inputs['Color'].default_value = bsdf.inputs['Base Color'].default_value
    cam_data = bpy.data.cameras.new('tex_cam')
    cam_data.type = 'ORTHO'
    cam_data.clip_end = 20
    cam = bpy.data.objects.new('tex_cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun = bpy.data.lights.new('tex_key', 'SUN')
    sun.energy = 0.0
    sun.angle = math.radians(20)
    so = bpy.data.objects.new('tex_key', sun)
    scene.collection.objects.link(so)
    return scene, cam, so


def set_mode(scene, sun_obj, lit: bool) -> None:
    import bpy
    for m in bpy.data.materials:
        if not m.use_nodes or 'unlit' not in m.node_tree.nodes:
            continue
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        src = bsdf.outputs['BSDF'] if lit else nt.nodes['unlit'].outputs['Emission']
        nt.links.new(src, out.inputs['Surface'])
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55 if lit else 0.0
    sun_obj.data.energy = 2.2 if lit else 0.0


def shoot(scene, cam, sun_obj, center, az: float, elev: float, ortho: float, res: int, path: str,
          lit: bool = False) -> np.ndarray:
    import bpy
    from mathutils import Matrix, Vector
    a, e = math.radians(az), math.radians(elev)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e))).normalized()
    r = Vector((math.cos(a), -math.sin(a), 0.0)).normalized()
    up = r.cross(d).normalized()
    rot = Matrix((r, up, -d)).transposed()
    cam.matrix_world = Matrix.Translation(Vector(center) - d * 5.0) @ rot.to_4x4()
    cam.data.ortho_scale = ortho
    key = (up * 1.0 - r * 0.6 - d * 1.0).normalized()   # 左上手前から
    sun_obj.matrix_world = key.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    set_mode(scene, sun_obj, lit)
    scene.cycles.samples = 24 if lit else 8
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32)
    al = img[..., 3:4] / 255
    return (img[..., :3] * al + BG * (1 - al)).astype(np.uint8)


def label(arr: np.ndarray, text: str) -> np.ndarray:
    im = Image.fromarray(arr)
    ImageDraw.Draw(im).text((8, 6), text, fill=(255, 255, 0))
    return np.asarray(im)


def diff_image(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.abs(a.astype(np.float32) - b.astype(np.float32)).mean(-1)
    t = np.clip(d / 80.0, 0, 1)
    out = np.stack([t * 255, (1 - np.abs(t - 0.5) * 2) * 200, (1 - t) * 60], -1)
    return out.astype(np.uint8)


def render_checks(glb: str, res: int = 1024) -> dict:
    """元の絵の 4 視点・左前 45 度・顔の近写を Cycles で描き、元の絵と並べる"""
    cams = V.load_calib()
    scene, cam, sun = render_setup(glb, 8)
    tmp = os.path.join(TEX_DIR, 'render')
    os.makedirs(tmp, exist_ok=True)
    stats = {}
    for name in REAL_VIEWS:
        bc = cams[name].blender_camera()
        img = shoot(scene, cam, sun, bc['center'], cams[name].azimuth, 0.0, bc['ortho_scale'], res,
                    os.path.join(tmp, f'{name}.png'))
        art = art_on_gray(V.VIEWS[name]['file'], res)
        mask = np.asarray(Image.fromarray(V.load_mask(name)).resize((res, res))) > 0
        d = np.abs(art.astype(np.float32) - img.astype(np.float32)).mean(-1)
        stats[name] = {'mean_abs_diff_in_mask': round(float(d[mask].mean()), 2)}
        lit = shoot(scene, cam, sun, bc['center'], cams[name].azimuth, 0.0, bc['ortho_scale'], res,
                    os.path.join(tmp, f'{name}_lit.png'), lit=True)
        row = np.concatenate([label(art, f'art {name}'), label(img, 'textured (unlit, albedo)'),
                              label(lit, 'textured (lit)'), label(diff_image(art, img), 'abs diff (red = large)')], 1)
        Image.fromarray(row).save(os.path.join(WORK, f'tex_check_{name}.png'))
    # 絵の無い向き（左後ろ斜め、少し上から）
    fr = cams['front'].blender_camera()
    center = fr['center']
    ortho = fr['ortho_scale']
    imgs = [label(shoot(scene, cam, sun, center, -135.0, 10.0, ortho, res, os.path.join(tmp, 'bl.png'), lit=True),
                  'back-left 135 el10 (lit)'),
            label(shoot(scene, cam, sun, center, 135.0, 10.0, ortho, res, os.path.join(tmp, 'br.png'), lit=True),
                  'back-right 135 el10 (lit)')]
    Image.fromarray(np.concatenate(imgs, 1)).save(os.path.join(WORK, 'tex_check_back_oblique.png'))
    # 顔の近写：顔の絵（haru_face_front.png）と同じ範囲を正面から
    with open(os.path.join(WORK, 'face_align.json')) as fp:
        fa = json.load(fp)['face_to_front']
    M = np.array(fa['matrix'])
    fc = M @ np.array([1024.0, 1024.0, 1.0])
    f = cams['front']
    cx, cz = (fc[0] - f.u0) / f.ppm, (f.v0 - fc[1]) / f.ppm
    ortho_f = 2048 * fa['scale'] / f.ppm
    face_art = art_on_gray(os.path.join(V.SRC, 'haru_face_front.png'), res)
    fimg = shoot(scene, cam, sun, (cx, 0.0, cz), 0.0, 0.0, ortho_f, res, os.path.join(tmp, 'face.png'))
    flit = shoot(scene, cam, sun, (cx, 0.0, cz), 0.0, 0.0, ortho_f, res, os.path.join(tmp, 'face_lit.png'), lit=True)
    # 右前斜め（45 度の絵）と左前斜めの頭
    tq = cams['front_right45']
    hu, hv = tq.project(np.array([cx, 0.0, cz]))
    half = ortho_f * tq.ppm / 2
    tq_art = np.asarray(Image.fromarray(art_on_gray(V.VIEWS['front_right45']['file'], 2048)).crop(
        (int(hu - half), int(hv - half), int(hu + half), int(hv + half))).resize((res, res), Image.LANCZOS))
    center_tq = np.array([cx, 0.0, cz]) + 0.0
    tq_img = shoot(scene, cam, sun, center_tq, tq.azimuth, 0.0, ortho_f, res, os.path.join(tmp, 'face_tq.png'))
    left_img = shoot(scene, cam, sun, center_tq, -tq.azimuth, 0.0, ortho_f, res, os.path.join(tmp, 'face_tql.png'),
                     lit=True)
    top = np.concatenate([label(face_art, 'art haru_face_front'), label(fimg, 'textured front (unlit)'),
                          label(flit, 'textured front (lit)')], 1)
    bot = np.concatenate([label(tq_art, 'art front-right 45 crop'), label(tq_img, 'textured front-right 45 (unlit)'),
                          label(left_img, 'textured front-left 45 (lit)')], 1)
    Image.fromarray(np.concatenate([top, bot], 0)).save(os.path.join(WORK, 'tex_check_face.png'))
    # 一覧（小さく）
    rows = []
    for name in REAL_VIEWS:
        im = np.asarray(Image.open(os.path.join(WORK, f'tex_check_{name}.png')))
        rows.append(im[:, :res * 2])
    allv = np.concatenate(rows, 1)
    Image.fromarray(allv).resize((allv.shape[1] // 2, allv.shape[0] // 2), Image.LANCZOS).save(
        os.path.join(WORK, 'tex_check_all.png'))
    return stats


# ---------------------------------------------------------------- 確認用の UV 画像

def debug_images(res: dict, base: np.ndarray) -> None:
    """どの視点が一番効いたか（色分け）と重みの和の UV 画像"""
    colors = np.array([[230, 60, 60], [60, 120, 230], [60, 200, 90], [230, 200, 50], [170, 80, 220],
                       [60, 210, 210], [240, 140, 40], [150, 150, 150], [120, 60, 30], [250, 120, 200],
                       [20, 90, 60], [200, 230, 120]], np.float32) / 255
    w = res['winner']
    c = np.where((w >= 0)[:, None], colors[np.clip(w, 0, None) % len(colors)], 0.1)
    s = res['size']
    win = to_image(res, c, fill_all=False)
    conf = to_image(res, np.clip(res['sl'] / W_FULL, 0, 1)[:, None], fill_all=False)[..., 0]
    img = np.concatenate([base, win, np.repeat(conf[..., None], 3, -1)], 1)
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    im = im.resize((im.width * 1024 // s, im.height * 1024 // s), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    dr.text((8, 6), 'baked base', fill=(255, 255, 0))
    dr.text((1032, 6), 'winner: ' + ', '.join(f'{k}' for k in res['keys']) + ' (red, blue, green, yellow, purple, cyan)',
            fill=(255, 255, 0))
    dr.text((2056, 6), f'weight sum / {W_FULL} (dark = inpainted)', fill=(255, 255, 0))
    im.save(os.path.join(WORK, 'tex_check_uv.png'))


def numpy_render(mesh: dict, cam: V.Cam, tex: np.ndarray, res: int = 1024) -> np.ndarray:
    """確認用の簡単な描画：メッシュを正投影カメラで塗り、UV でテクスチャ（最も近いテクセル）を拾う"""
    verts, tris, uv = mesh['verts'], mesh['tris'], mesh['uv']
    u, v = cam.project(verts)
    depth = verts @ cam.d
    k = res / V.IMG
    pix, tri, bar = raster(np.stack([u[tris], v[tris]], -1) * k, res, res)
    dz = (depth[tris[tri]] * bar).sum(1)
    order = np.lexsort((dz, pix))
    pix, tri, bar = pix[order], tri[order], bar[order]
    first = np.r_[True, pix[1:] != pix[:-1]]
    pix, tri, bar = pix[first], tri[first], bar[first]
    tuv = (uv[tri] * bar[..., None]).sum(1)
    s = tex.shape[0]
    tx = np.clip((tuv[:, 0] * s).astype(np.int64), 0, s - 1)
    ty = np.clip(((1 - tuv[:, 1]) * s).astype(np.int64), 0, s - 1)
    out = np.full((res * res, 3), 0.5, np.float32)
    out[pix] = tex[ty, tx, :3]
    return out.reshape(res, res, 3)


# ---------------------------------------------------------------- 本体

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mesh', default=os.path.join(WORK, 'haru_mesh.glb'))
    ap.add_argument('--out', default=OUT_GLB)
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--no-align', action='store_true')
    ap.add_argument('--no-head-cleanup', action='store_true')
    ap.add_argument('--render-only', action='store_true')
    ap.add_argument('--render-res', type=int, default=1024)
    args = ap.parse_args([a for a in sys.argv[1:] if a != '--'])
    os.makedirs(TEX_DIR, exist_ok=True)
    t0 = time.time()
    if not args.render_only:
        V.extract_sources()
        copy = os.path.join(TEX_DIR, 'haru_mesh_in.glb')
        shutil.copyfile(args.mesh, copy)   # ほかの作業が書き換えている最中でも崩れないように
        with open(os.path.join(WORK, 'face_atlas.json')) as fp:
            atlas_meta = json.load(fp)
        cams = V.load_calib()
        obj = import_mesh(copy)
        mesh = mesh_arrays(obj)
        log(f'メッシュ {len(mesh["verts"]):,} 頂点、{len(mesh["tris"]):,} 三角形')
        res = bake(mesh, args.size, cams, atlas_meta, align=not args.no_align)
        sel = face_polys(mesh, cams, atlas_meta)
        cover = expression_coverage(mesh, cams, atlas_meta, sel)
        log(f'顔の材質 {int(sel.sum()):,} 三角形、表情で変わる画素の {cover:.2%} を覆う')
        feather_face_border(res, mesh, sel)
        if not args.no_head_cleanup:
            head_cleanup(res)
        body_cleanup(res)
        neck_cleanup(res)
        hand_cleanup(res)
        sole_cleanup(res)
        hair_colour_match(res)
        cov = np.zeros(args.size * args.size, bool)
        cov[res['pix']] = True
        cov = cov.reshape(args.size, args.size)
        base = to_image(res, res['col'])
        emit = emission_image(base, cov)
        # 発光の所の下地を暗く（照らされた下地 ＋ 発光 ≒ 絵の色。飽和してレモン色にならないように）
        em = ramp(amber_mask(base), 0.3, 0.6) * (emit.max(-1) > 0)
        base = base * (1 - EMIT_BASE_DARKEN * em)[..., None]
        base_p = os.path.join(TEX_DIR, 'haru_body_base.png')
        emit_p = os.path.join(TEX_DIR, 'haru_body_emit.png')
        save_png(base_p, base)
        save_png(emit_p, emit)
        debug_images(res, base)
        if os.environ.get('TEX_DEBUG_RENDER'):
            colors = np.array([[230, 60, 60], [60, 120, 230], [60, 200, 90], [230, 200, 50], [170, 80, 220],
                               [60, 210, 210]], np.float32) / 255
            w = res['winner']
            wimg = to_image(res, np.where((w >= 0)[:, None], colors[np.clip(w, 0, None)], 0.1))
            row = [np.concatenate([numpy_render(mesh, cams[n], base), numpy_render(mesh, cams[n], wimg)], 0)
                   for n in REAL_VIEWS]
            save_png(os.path.join(TEX_DIR, 'debug_winner.png'), np.concatenate(row, 1))
        fuv = face_uv(mesh['verts'], cams, atlas_meta)
        build_materials_and_export(obj, mesh, sel, fuv, base_p, emit_p,
                                   os.path.join(WORK, atlas_meta['atlas_file']), args.out)
        log(f'書き出し {args.out}（{time.time() - t0:.0f}s）')
        report = {
            'mesh': os.path.relpath(args.mesh, V.REPO), 'size': args.size,
            'texels': int(len(res['pix'])), 'texel_fraction': round(len(res['pix']) / args.size ** 2, 4),
            'inpainted_fraction': round(float((res['sl'] < W_FULL).mean()), 4),
            'face_tris': int(sel.sum()),
            'head_cleanup_texels': res.get('head_cleanup', {}),
            'face_expression_coverage': round(cover, 4),
            'align': res['align'],
            'emissive_fraction': round(float((emit.max(-1) > 0.05).mean()), 5),
            'emit_strength': EMIT_STRENGTH, 'emit_base_darken': EMIT_BASE_DARKEN,
            'art_occlusion': res.get('art_occlusion'), 'body_cleanup_texels': res.get('body_cleanup'),
            'hair_colour': res.get('hair_colour'),
        }
    else:
        report = {}
    if not args.no_render:
        report['render'] = render_checks(args.out, args.render_res)
        log(f'確認画像（{time.time() - t0:.0f}s）')
    with open(os.path.join(TEX_DIR, 'texture_report.json'), 'w') as fp:
        json.dump(report, fp, indent=2, ensure_ascii=False)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
