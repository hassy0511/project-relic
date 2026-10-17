"""飾り（dress）の "solid"：手で触れる大きさの部品に、部品の形に合わせた描かない当たり判定の箱を付ける。

飾りは見た目だけで当たり判定が無いので、床に置いた箱・樽の中にハルが入り込み、頭だけ出して立てた（ハリボテに見えた）。
dress の 1 件に "solid": true を付けると、ここの SOLID の表（部品の中の箱）を部品の pos・yaw・scale・count/step のとおりに置いた
描かない形（geometry の {"t": "box", …, "hide": true, "dress": <dress の番号>}）を部屋に足す。"solid": "<表の名前>" なら表の別の行
（同じ部品でも置き方で箱が違うとき）。表に無い形は "solid": [[cx, cz, 幅 x, 奥行き z, 下の y, 上の y, yaw], …] で直接書く。
書くのは tools/dress_ruins.py・tools/dress_town.py（部屋の JSON を書く）。何度流しても同じ（前に足した "dress" つきの形は消してから足す）。
書き方：docs/design/42_コンテンツの書き方.md 14.3.1。テスト：godot/tests/test_kit.gd の test_dress_solid_*。

箱の書き方（部品の中の座標。原点・向きは部品と同じ。x 右、y 上、z 正面）
  B(x0, x1, y0, y1, z0, z1)           軸にそろった箱
  R(cx, cz, wx, wz, y0, y1, yaw)      中心 (cx, cz)・幅 wx × 奥行き wz を yaw 度回した箱（部品の中で斜めに置いた箱・樽）
  P(cx, cz, w, y0, y1)                細い柱（体だけを止める箱。下の cam）
  {"t": "stairs", "pos", "size", "steps", "yaw"}   段ごとの箱（階段の手すりの帯）。RoomGeo の stairs と同じ。向きは 90 度の倍数だけ
どの箱にも次の印を付けられる（B(…, cam=False) のように）
  cam=False   体だけを止める（形に "cam": false。Phys.PROP：カメラの壁よけ・弾は通す）。細い柱・露店の屋根の上をふさぐ箱など、
              カメラが当たると、柱が後ろを横切るたびにカメラが前へ跳ねる物
  wall=True   壁ぎわの帯（遺構の壁の板の前の面）。出口・トリガーの箱の、壁ぎわの 1.0 m までには掛かってよい（出口の口はふさがない）
  nogo=True   乗れない柱（形に "nogo": true）。上の端は近くで跳んで届く高さより上（テストが確かめる）。NOGO() は cam=False・nogo=True
置く形はどれも軸にそろった箱（yaw なし）。部品・箱の向きが 90 度の倍数でなければ、回した広がりを囲む箱にする（くさび形のすき間を作らない）。
斜めに置くのは数度まで（4 度で囲む箱は面の真ん中で 0.04 m 外。前は 20〜40 度回した箱があり、見えない壁が 0.25〜0.5 m 手前にあった）。

張り出し（日よけ・巻き上げ帆布・吊り灯・雨戸・壁の上の太い管）：頭の上の物は、乗れない柱（NOGO：下の端から、近くで跳んで届く高さより上まで、
体だけを止める箱）にする。下の端は帆布の下の面に合わせて段にする（跳ぶと頭が当たる。前は帆布・灯の中を頭が抜けた）。
上に立てる箱にすると、上に乗って次の高い所（壁の上の通路・屋根）へ行けてしまう。上の端は、近くの一番高い足場（工具棚 1.75・給水塔 3.19）から
跳んで届く高さ（＋2.2）より上にする。

すき間をふさぐ（fill_gaps）：飾りの箱と、壁・ほかの箱との間の 0.75 m（体の太さ 0.7 m）より狭いすき間は、低いほうの高さまで箱でふさぐ。
前は箱と壁の間 0.3〜0.6 m に、箱に乗ってから歩いて落ちた体が両側の角に引っかかって宙に浮いたまま出られなくなった（立てない・跳べない）。
ふさぐ箱の上が乗れる高さ（LEDGE_TOP の 3 m より下）で FILL_WARN（0.3 m）より広いと警告を出す（見えない棚になる。置き方を直す）。

決まり（42 の 14.3.1）：出口・トリガーの箱に掛けない（0.1 m 空ける。wall の帯は壁ぎわだけ可）、目印・チェックポイント・敵の出る所から 0.6 m、
調べる物・拾う物・住人から 0.5 m 空ける（check() が確かめ、だめなら書かずに止まる）。
"""
import math

GAP = 0.75          # これより狭いすき間はふさぐ（体の太さ 0.7）
GAP_HIGH = 0.36     # ふさぐのは、両側が共通の底から段差の乗り越え（0.35）より高く立つ所だけ
GAP_LONG = 0.25     # ふさぐのは、すき間が 0.25 m より長く続く所だけ（角どうしが少し向き合うだけの所は、体が横へ抜ける）
FILL_WARN = 0.3     # これより広くふさいだら警告
WALL_REACH = 1.0    # wall の帯が出口・トリガーの箱に掛かってよい深さ（扉の 1.5 倍の帯と灯の箱で 0.8 m）
LEDGE_TOP = 3.0     # ふさいだ箱の上がこれより低いと、上に乗れる（見えない棚）。FILL_WARN より広いと警告


def _box(cx, cz, wx, wz, y0, y1, yaw=0.0, cam=True, wall=False, nogo=False):
    return {"c": (cx, cz), "w": (wx, wz), "y": (y0, y1), "yaw": yaw, "cam": cam, "wall": wall, "nogo": nogo}


def B(x0, x1, y0, y1, z0, z1, **f):
    return _box((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, y0, y1, **f)


def R(cx, cz, wx, wz, y0, y1, yaw=0.0, **f):
    return _box(cx, cz, wx, wz, y0, y1, yaw, **f)


def P(cx, cz, w, y0, y1, **f):
    """細い柱：体だけを止める箱（カメラは通す）"""
    f.setdefault("cam", False)
    return _box(cx, cz, w, w, y0, y1, **f)


def NOGO(x0, x1, top, steps, **f):
    """乗れない張り出しの柱：x0〜x1 で、z の段 steps = [(z0, z1, 下の y), …] ごとに、下の y から top まで（体だけを止める箱）"""
    f.setdefault("cam", False)
    f.setdefault("nogo", True)
    return [B(x0, x1, y, top, z0, z1, **f) for z0, z1, y in steps]


def _crate(cx, cz, s, yaw, y0=0.0):
    """町の木箱（town/crate：0.94 m 角・高さ 0.74）を部品の中に s 倍で置いたときの箱"""
    return R(cx, cz, 0.94 * s, 0.94 * s, y0, y0 + 0.74 * s, yaw)


def _barrel(cx, cz, s, y0=0.0):
    """町の樽（town/barrel：半径 0.36・高さ 1.0）。丸い物は半径の箱（角は 0.1 m ほど外へ出るが見えない）"""
    return R(cx, cz, 0.7 * s, 0.7 * s, y0, y0 + 1.0 * s)


def _rail_band(sx, foot_top=None):
    """町の階段の手すり（stair_rail_12：壁の面 x=0 から階段の側へ 0.18 m、踏み面の 1 m 上を 12 m で 5 m 上る）。
    手すりの下を段ごとの帯（壁から 0.4 m、段の上 1.0 m まで。下は 1.0 m から）でふさぐ。sx：階段の側（+1 / -1）。
    前は帯が 0.3 m で、手すりの柱の金具が体の肩に 0.15 m 入った。
    foot_top：下の端の上を、その高さまで乗れない柱にする（北の階段の上り口。端の上 1.05 m に下りると、角の棟の扉の日よけの柱に
    頭が当たって挟まった。南の階段の下の端は、横の壁の上 3 m から下りると柱の上に立てるので付けない）"""
    x0, x1 = sorted((0.0, sx * 0.4))
    return [
        {"t": "stairs", "pos": [sx * 0.2, 1.0, 6.0], "size": [0.4, 5.0, 12.0], "steps": 16},
        B(x0, x1, 0.0, 1.05, -0.6, 0.0),       # 下の段の床の上に出た端
        B(x0, x1, 5.0, 6.05, 12.0, 12.6),      # 上の踊り場の上に出た端
        # 手すりの上は乗れない柱（上り口から 12 m。北の階段では横の壁の上より高く、下へ 5 m 下りる南の階段では広場の胸壁・
        # 段々の壁の上から跳んで届く高さより上）。前は帯の上が幅 0.4 m の階段になっていて、跳び乗ると手すりの上を
        # 6 m まで上れ、ダッシュジャンプで上り口の門柱・段々の壁の上へ渡ると、柱と帯の間で体が縁に引っかかって宙に止まった（2026-10-15）
        B(x0, x1, 1.05, RAIL_NOGO_TOP, -0.6, 12.6, cam=False, nogo=True),
    ] + ([B(x0, x1, 1.05, foot_top, -0.6, 0.0, cam=False, nogo=True)] if foot_top else [])


RAIL_NOGO_TOP = 12.0


# ---------------------------------------------------------------- 遺構 B1（tools/blender/kit/ruins_b1.py）

LINER = 0.36        # 壁の板の前の帯の深さ（板・柱・金具・管・非常灯は壁から 0.35 m まで。ruins_b1.RELIEF）


def _ruins():
    wall = [B(-1.0, 1.0, 0.0, 4.0, 0.0, LINER, wall=True)]
    return {
        "ruins/b1_wall": wall,
        "ruins/b1_wall_plain": wall,
        # 扉：枠と柱は壁の帯と同じ深さ。左の柱の琥珀の灯（壁から 0.5 m）は灯の箱
        "ruins/b1_door": [B(-1.0, 1.0, 0.0, 4.0, 0.0, LINER, wall=True), B(-1.02, -0.78, 1.78, 2.24, 0.0, 0.52, wall=True)],
        # 部屋の内角の柱（0.5 m 角・冠まで 4.05 m）
        "ruins/b1_corner": [B(0.0, 0.5, 0.0, 4.05, 0.0, 0.5, wall=True)],
        # 壁の琥珀の灯（柱の前、壁から 0.3 m の所に付ける。灯は 0.3 m 前へ出る）。壁まで届く箱（壁の帯との間にすき間を作らない）
        "ruins/b1_lantern": [B(-0.11, 0.11, -0.2, 0.22, -0.3, 0.3, wall=True)],
        # 壁の上の管（中心線。背面へ 0.3 m の金具が壁に届く）。管の太さ・フランジまで
        "ruins/b1_pipe": [B(-1.0, 1.0, -0.23, 0.23, -0.3, 0.23, wall=True)],
        # 天井の梁（上の面が原点、0.5 m 下がる。赤い灯は 0.56 m まで）。頭の上なのでカメラは通す
        "ruins/b1_beam": [B(-1.0, 1.0, -0.5, 0.0, -0.28, 0.28, cam=False)],
        "ruins/b1_beam_red": [B(-1.0, 1.0, -0.56, 0.0, -0.28, 0.28, cam=False)],
        "ruins/b1_crate": [B(-0.52, 0.52, 0.0, 1.0, -0.52, 0.53)],
        "ruins/b1_crate_cloth": [B(-0.58, 0.58, 0.0, 1.04, -0.58, 0.58)],
        "ruins/b1_pillar": [B(-0.3, 0.3, 0.0, 4.0, -0.3, 0.3)],
        # 大型ファン：枠と羽根（壁から 0.46 m）と、両脇の下の琥珀の灯（壁から 0.65 m）
        "ruins/b1_fan": [B(-2.0, 2.0, 0.0, 4.0, 0.0, 0.5)] + [B(sx * 1.8 - 0.11, sx * 1.8 + 0.11, 0.3, 0.8, 0.0, 0.66) for sx in (-1, 1)],
        # 穴の縁の琥珀の灯の柱（台 0.34 m 角、灯の上まで 1.4 m）。壁ぎわに置く（内側の面は壁の帯から 0.3 m：体の中心は上に来ない）
        "ruins/b1_post_lamp": [B(-0.14, 0.14, 0.0, 1.4, -0.17, 0.17)],
        # 崩れた白磁の板のかけら（どれも 0.3 m 以下。段差の乗り越えで上を歩ける）
        "ruins/b1_debris": [R(-0.3, 0.1, 0.78, 0.62, 0.0, 0.28, 25), R(0.35, -0.25, 0.6, 0.5, 0.0, 0.24, -40),
                            R(0.1, 0.35, 0.42, 0.38, 0.0, 0.2, 70), R(-0.45, -0.4, 0.5, 0.55, 0.0, 0.3, 10)],
    }


# ---------------------------------------------------------------- 町（tools/blender/kit/town_parts.py・town_sets.py・town_terrace.py）

def _stall():
    """露店（town_sets.stall、原点は屋根の中心の真下の床、正面 +Z。台は z 2.1〜2.9・奥の箱は z -2.8〜-1.8、屋根の箱は y 3.2〜3.45・z ±2.6）"""
    out = [P(sx * 3.8, sz * 2.45, 0.24, 0.0, 3.2) for sx in (-1, 1) for sz in (-1, 1)]      # 四隅の柱（屋根の箱まで。上に立てない）
    out += [
        B(-4.1, 4.1, 3.45, 6.0, -2.75, 2.75, cam=False, nogo=True),     # 屋根の上（帆布は 3.45〜4.0 の丸い屋根。上を歩くと靴が帆布の下へ抜けた）
        B(-3.5, 3.5, 1.1, 6.0, 2.1, 2.9, cam=False, nogo=True),         # 台の上の品（台に跳び乗ると壺・袋の中を歩けた）
        B(-3.5, 3.5, 2.4, 3.45, -2.8, -2.6, cam=False, nogo=True),      # 奥の箱の上と屋根の間（ここに立って屋根へ跳べた）
        _crate(-2.6, -3.35, 1.0, 3), _crate(-2.5, -3.35, 0.8, -3, 0.74),     # 裏の木箱の山
        _barrel(2.7, -3.3, 0.85),
    ]
    return out


def _tent():
    """天幕（town_sets.tent、正面 +Z。4 本の真鍮の柱 (±1.9, ±1.4)、帆布は 2.6〜2.95、前の垂れは 2.3 まで）"""
    out = [P(sx * 1.9, sz * 1.4, 0.14, 0.0, 2.6) for sx in (-1, 1) for sz in (-1, 1)]
    out += [
        B(-2.1, 2.1, 2.6, 6.0, -1.6, 1.6, cam=False, nogo=True),        # 帆布の上（跳ぶと頭が帆布を抜けた）
        B(-2.1, 2.1, 2.3, 2.6, 1.45, 1.65, cam=False, nogo=True),       # 前の垂れ
        B(-1.01, 1.01, 0.0, 0.97, -0.83, 0.23),                         # 台
        B(-1.01, 1.01, 0.97, 2.6, -0.83, 0.23, cam=False, nogo=True),   # 台の上の品・吊り灯（台に乗ると品の中に立った）
        _crate(-1.4, 0.6, 0.7, 3), _barrel(1.4, 0.5, 0.8),
    ]
    return out


def _lamp(h, s=1.0):
    """外灯（town_parts.lamp_post：白磁の台 0.66 m 角・0.48、柱は 0.18 m 角で h + 0.1 まで、腕の先 (0.55, h - 0.48) に灯）。
    柱は体だけの箱（前は台だけで、台に乗ると柱が体を貫いた）。柱の上の端・腕・灯は 1 つの体だけの箱（灯の下から柱の上まで）：
    前は柱と灯の箱が別で、間（0.3 m）に体の丸い底が落ちて宙に止まった"""
    return [B(-0.33, 0.33, 0.0, 0.48, -0.33, 0.33), P(0.0, 0.0, 0.2, 0.48, h - 0.75),
            B(-0.1, 0.7, h - 0.75, h + 0.1, -0.13, 0.13, cam=False)]


def _rack():
    """工具棚（town_parts.tool_rack：背板と柱は z -0.08〜0.1、下の木箱は x -0.6〜0・z -0.05〜0.3、台は 0.1 m）。
    前は 0.6 m の箱で、上に乗ると背板の前の宙に立った"""
    return [B(-1.03, 1.03, 0.0, 1.75, -0.08, 0.1), B(-0.6, 0.0, 0.0, 0.42, -0.08, 0.3), B(-1.0, 1.0, 0.0, 0.1, -0.3, 0.2)]


def _tower(s):
    """給水塔（town_parts.water_tower）を s 倍：白磁の台と脚（脚の間は筋交いでふさがる）、槽（半径 0.55）、円すいの屋根を 3 段で"""
    return [B(-0.75 * s, 0.75 * s, 0.0, 1.3 * s, -0.75 * s, 0.75 * s),
            B(-0.56 * s, 0.56 * s, 1.3 * s, 2.2 * s, -0.56 * s, 0.56 * s),
            B(-0.4 * s, 0.4 * s, 2.2 * s, 2.3 * s, -0.4 * s, 0.4 * s),
            B(-0.25 * s, 0.25 * s, 2.3 * s, 2.38 * s, -0.25 * s, 0.25 * s),
            B(-0.12 * s, 0.12 * s, 2.38 * s, 2.45 * s, -0.12 * s, 0.12 * s)]


def _town():
    return {
        "town/crate": [B(-0.47, 0.47, 0.0, 0.74, -0.47, 0.47)],
        "town/barrel": [_barrel(0.0, 0.0, 1.0)],
        "town/chest": [B(-0.52, 0.52, 0.0, 1.0, -0.47, 0.47)],
        "town/planter": [B(-0.45, 0.45, 0.0, 1.45, -0.45, 0.45)],        # 茂みの上まで（跳んで乗ると茂みの上に立つ）
        "town/planter_big": [B(-0.68, 0.65, 0.0, 1.73, -0.66, 0.66)],
        # 座面と背板。座面の箱は座面（0.5）より少し高く 0.56 まで：広場の床の板（0.08）の上では座面が 0.42 しか無く、
        # 段差の乗り越え（0.35）と体の丸い底で角に乗り上げて、足が座面の角に入った
        "town/bench": [B(-0.99, 0.99, 0.0, 0.56, -0.34, 0.24), B(-0.99, 0.99, 0.0, 1.07, -0.34, -0.18)],
        "town/stall_table": [B(-1.01, 1.01, 0.0, 0.97, -0.53, 0.53)],
        "town/tool_rack": _rack(),
        "town/water_tower": _tower(1.0),
        # 洗濯綱（town_parts.clothesline：白磁の台 0.28 m 角・0.25、柱 0.12 m 角で 2.6 m、綱は 2.45、洗濯物の下の端は 1.75 より上）。
        # 柱は体だけの箱。洗濯物は頭より上なので下を歩ける（前は 1.2 m の箱で、上に立つと洗濯物の横の宙に立った）
        "town/clothesline": [B(sx - 0.14, sx + 0.14, 0.0, 0.25, -0.14, 0.14) for sx in (-1, 1)]
                            + [P(sx, 0.0, 0.14, 0.25, 2.6) for sx in (-1, 1)],
        "town/pipes": [B(-1.02, 1.02, 0.0, 0.46, -0.3, 0.32)],
        "town/lamp_post": _lamp(2.0),
        "town/lamp_tall": _lamp(4.4),
        # 胸壁の角の柱。南の角では、東西の低い壁の手すり（角の柱の縁 z=-14 で終わる）と胸壁の手すり（z=-14.5）の間の 0.43 m を、
        # 手すりの高さの体だけの箱でつなぐ（前は手すりの上を歩いて角へ来ると、2 本の手すりの端の間に体の丸い底が挟まって宙に止まった）
        "town/parapet_corner": [B(-0.71, 0.71, -8.2, 0.04, -0.71, 0.71), B(-0.07, 0.07, 0.0, 0.7, 0.07, 0.5, cam=False)],
        # 胸壁の上の手すり（胸壁の上の面の中心の線、高さ 0.68）：体だけの箱。胸壁の上には手すりの両脇に立てる（前は手すりの中に立った）
        # 広場の側の面の付け柱（面から 0.1 m）は、面の前の帯（床から胸壁の上の面まで。付け柱の頭は 4 cm 上へ出るが、帯は上の面にそろえる：
        # 前は帯の上が 4 cm 高く、胸壁の縁に 4 cm の段ができて、体の丸い底が段の角に載って宙に止まった）
        "town/parapet_rail_8": [B(-4.0, 4.0, 0.0, 0.7, -0.07, 0.07, cam=False), B(-4.0, 4.0, -1.2, 0.0, 0.5, 0.61)],
        "town/parapet_rail_4": [B(-2.0, 2.0, 0.0, 0.7, -0.07, 0.07, cam=False), B(-2.0, 2.0, -1.2, 0.0, 0.5, 0.61)],
        # 雨戸の無い窓（窓台と枠が面から 0.14 m。肩の高さ）
        "town/window_flush": [B(-0.53, 0.53, -0.11, 0.79, 0.0, 0.15, cam=False)],
        # 壁付けの巻き上げ帆布（原点 = 壁の面・巻きの中心の高さ。帆布は 1.2 m 下・1.0 m 前まで垂れる）：乗れない柱
        "town/canvas_roll": NOGO(-1.06, 1.06, 0.25, [(0.0, 0.6, -0.8), (0.6, 1.08, -1.22)]),
        "town/goods_shelf_general": [B(-3.4, 3.4, 0.0, 2.3, -0.03, 0.43)],
        "town/goods_shelf_junk": [B(-3.4, 3.4, 0.0, 2.3, -0.03, 0.43)],
        "town/stall": _stall(),
        "town/tent": _tent(),
        # 壇の旗竿 2 本（旗竿の上 5.2 m まで体だけの箱。前は壇の上 1.2 m までで、上に乗ると竿が体を貫いた）。
        # 四隅の黒鉛の柱は壇の箱から 0.03 m しか出ない（town_sets.stage。前は 0.12 m 出て、角へ歩くと体に入った）
        "town/stage": [P(sx * 3.65, 1.15, 0.16, 0.8, 5.2) for sx in (-1, 1)],
        "town/workshop_front": _workshop(),
        "town/diner_front": _diner(),
        "town/stair_rail_12": _rail_band(1),
        "town/stair_rail_12_r": _rail_band(-1),
        "town/stair_rail_12_foot": _rail_band(1, 5.0),
        "town/stair_rail_12_r_foot": _rail_band(-1, 5.0),
        # 北の段の擁壁の前の張り出し（部屋の座標のまま。_terrace）。
        # はしごは壁から 0.18 m まで（town_sets._retaining。前は 0.36 m 出て、壁ぎわを歩くと段の棒が体を抜けた）
        "town/terrace_west": _terrace(-1),
        "town/terrace_east": _terrace(1),
        # 広場の記念の柱（town_sets.monument を高さ 0.68 倍で置く。台と芯の柱は部屋の箱）：4 本の腕の先の吊り灯（2.2〜2.6 m）は乗れない柱。
        # 台（1.0）の上を歩くと、頭と肩が吊り灯を抜けた。上の端（6.05）は芯の柱の上（3.6）から跳んで届く 5.8 より上。
        # 台の四隅の黒鉛の柱と真鍮の笠（台の箱から 0.15 m 外、0.75 m まで）も箱（台の角を回ると膝が笠に入った）
        "town/monument": [R(x, z, 0.32, 0.32, 3.2, 8.9, cam=False, nogo=True) for x, z in ((1.45, 0.0), (-1.45, 0.0), (0.0, 1.45), (0.0, -1.45))]
                         + [R(sx * 1.6, sz * 1.6, 0.3, 0.3, 0.0, 1.1) for sx in (-1, 1) for sz in (-1, 1)],
        # 南の階段の下の踊り場の両側の壁の縦の管（壁の面 |x|=4 から 0.29 m。踊り場の床 -5 から 2.8 まで）：体だけの柱
        "town/stair_well_s": [P(sx * 3.82, -29.4, 0.22, -5.0, 2.8) for sx in (-1, 1)],
        # 生活感の小物（2026-10-15。町の中段・遺構 r02・r03 に置く）
        # 水筒形タンク（横倒しの筒 x -0.5〜0.5、端のふた 0.62・蛇口 0.75）、折り畳み踏み台、曲がり管、係留柱（床の綱と環は薄いので箱に入れない）
        "town/tank": [B(-0.52, 0.64, 0.0, 0.85, -0.34, 0.34)],
        "town/stool": [B(-0.39, 0.39, 0.0, 0.97, -0.45, 0.47)],
        "town/pipe_bend": [B(-0.62, 0.45, 0.0, 0.77, -0.27, 0.27)],
        "town/bollard": [B(-0.28, 0.28, 0.0, 1.06, -0.28, 0.28)],
        "town/sacks": [B(-0.62, 0.65, 0.0, 0.55, -0.58, 0.33)],          # 麻袋の山（3 袋）
        # 携行灯（0.26 m 角・0.69）：体だけの箱（細い。カメラは通す）。箱・台の上に置くときは pos の y をその上の面に
        "town/hand_lantern": [B(-0.13, 0.13, 0.0, 0.69, -0.13, 0.13, cam=False)],
        # ガラクタの山（junk_pile、2×1.5×1.1）：前からの中段の 1 つは描かない箱があるので solid を付けない。新しく置く物はこの箱
        "town/junk_pile": [B(-0.99, 0.97, 0.0, 1.12, -0.68, 0.79)],
        # CC0 の小物（tools/blender/kit/cc0_props.py）：膨らんだ樽、長持ち形の木箱
        "cc0/cask": [_barrel(0.0, 0.0, 1.02)],
        "cc0/plank_box": [B(-0.7, 0.7, 0.0, 0.6, -0.35, 0.35)],
        # W2-05b 市場のにぎわい（2026-10-17、tools/blender/kit/town_goods.py）
        **_goods(),
    }


def _goods():
    """W2-05b の小物（town_goods.py の寸法）。露店の組は台の前の床の品だけ（台の上・梁の吊り物は露店の乗れない柱の中）"""
    pot = [B(-0.45, 0.45, 0.0, 1.45, -0.45, 0.45)]          # W2-05 と同じ鉢（茂みの上まで。town/planter と同じ）
    return {
        # 麻袋の山（麻袋の仮の部品 town/sacks と同じ置き場所。立てた袋が 0.92 m まで）
        "town/goods_sacks": [B(-0.58, 0.58, 0.0, 0.9, -0.5, 0.43)],
        # 露店の組（原点 = 台の上の面の中心、+Z が客の側、床は y -1.1）：台の前の左右の床の品（真ん中 3 m は空ける）。台の前の面（z 0.4）から 3 cm
        "town/market_general": [B(-3.42, -1.66, -1.1, -0.55, 0.43, 1.04), B(1.64, 3.32, -1.1, -0.18, 0.43, 1.07)],
        "town/market_junk": [B(-3.42, -1.68, -1.1, -0.4, 0.43, 1.04), B(1.84, 3.27, -1.1, -0.15, 0.43, 1.07)],
        # 食堂の机（前の露店台と同じ大きさ・同じ箱）
        "town/diner_table": [B(-1.01, 1.01, 0.0, 0.97, -0.53, 0.53)],
        "town/sign_stand": [B(-0.45, 0.45, 0.0, 0.97, -0.29, 0.29)],
        "town/toy_banki": [B(-0.32, 0.46, 0.0, 0.63, -0.15, 0.28)],
        "town/laundry_basket": [B(-0.55, 0.55, 0.0, 0.52, -0.29, 0.33)],
        "town/goods_basket": [B(-0.54, 0.54, 0.0, 0.6, -0.47, 0.47)],
        # 布を干す枠：足の板と、柱と布の薄い壁（体だけ。カメラは通す。布は膝まで垂れるので下を歩けない）
        "town/goods_cloth": [B(-1.15, 1.15, 0.0, 0.05, -0.2, 0.2), B(-1.06, 1.06, 0.05, 2.05, -0.07, 0.07, cam=False)],
        # 部品を盛った陳列箱（2×1）と置物の柱（体だけ）
        "town/junk_goods": [B(-1.01, 0.95, 0.0, 0.75, -0.47, 0.5), P(0.78, 0.0, 0.3, 0.75, 0.97)],
        "town/pot_succulent": pot, "town/pot_vine": pot,
        "town/pot_shrub": [B(-0.45, 0.45, 0.0, 1.52, -0.45, 0.45)],
        # 風の旗：床の基部と竿（体だけ）。旗と吹き流しは頭の上（1.25 m より上）で当たり判定なし
        "town/wind_flag": [B(-0.23, 0.23, 0.0, 0.09, -0.23, 0.23), P(0.0, 0.0, 0.12, 0.09, 2.4)],
    }


def _workshop():
    """ヤーナの工房の正面（town_sets.workshop_front、原点 = 正面の下の中心、正面 +Z。裏の面は z=-9）"""
    return ([dict(b, c=(b["c"][0] + sx * 5.55, b["c"][1] + 0.12)) for sx in (-1, 1) for b in _rack()]      # 工具棚 2 つ
            + [_barrel(-6.3, 0.42, 1.0), R(6.0, 0.575, 0.68, 1.25, 0.0, 0.8), _crate(-3.1, 0.46, 0.8, 4), _crate(3.3, 0.44, 0.75, -3)]
            # 入口の上の赤い日よけ（固いひさし：壁で 3.77、1.9 m 前で 3.07、前の垂れは 2.83 まで）と両脇の吊り灯。工具棚（1.75）から跳んで届く 3.95 より上まで
            + NOGO(-2.15, 2.15, 4.5, [(0.08, 0.8, 3.3), (0.8, 1.45, 3.05), (1.45, 1.96, 2.82)])
            + [B(x - 0.19, x + 0.19, 2.63, 4.5, 0.2, 0.6, cam=False, nogo=True) for x in (-2.0, 2.0)]
            # 正面を横切る太い管 2 本と、両棟の上の窓（工具棚から跳ぶと頭が入った）
            + [B(-7.45, 7.45, 4.5, 5.9, 0.0, 0.76, cam=False, nogo=True)]
            # 入口の奥まり（幅 3.2 の部屋の口）の両側の黒鉛の内張り（口の側の面から 0.3 m。前は箱が無く、口へ歩くと体が内張りに 0.3 m 入った）
            + [B(x0, x1, 0.0, 3.8, -2.0, 0.0, cam=False, wall=True) for x0, x1 in ((-1.6, -1.3), (1.3, 1.6))]
            # 下の窓（雨戸の無い窓、窓台は 1.0〜1.1 で面から 0.19 m）：枠と窓台の前の帯（肩の高さ。体だけ）
            + [B(x - 0.53, x + 0.53, 0.98, 1.9, 0.0, 0.2, cam=False) for x in (-3.1, 3.1)]
            # 裏（z=-9）：縦の管（面から 0.33 m）、下の窓の雨戸（1.72 m から 0.6 m 出る）、灯
            + [B(-1.2, -0.8, 0.0, 6.8, -9.36, -9.0)]
            + [B(x - 0.47, x + 0.47, 1.7, 3.8, -9.62, -9.0, cam=False, nogo=True) for x in (2.6, -3.0, -5.4)]
            + [B(3.28, 3.62, 1.74, 3.8, -9.6, -9.0, cam=False, nogo=True)])


def _diner():
    """食堂の正面（town_sets.diner_front、原点 = 正面の下の中心、正面 +Z。西 +x・東 -x の面は x=±5、裏は z=-9）"""
    return ([B(5.0, 5.36, 0.0, 5.3, -8.05, -7.55),          # 西の面の縦の管（面から 0.33 m）
             B(4.28, 4.52, 0.0, 5.3, -9.3, -9.0),           # 裏の縦の管
             _barrel(0.4, -9.55, 0.85), _crate(-0.36, -9.6, 0.8, 4), _crate(-0.36, -9.6, 0.62, -3, 0.6),     # 裏の樽と木箱の山
             B(-1.8, 1.8, 1.0, 2.86, 0.0, 0.36)]            # 配膳の口の枠と中の棚・鍋（配膳台の上）
            # 正面の赤い日よけ（壁で 3.42、2.4 m 前で 2.62、前の垂れは 2.38 まで）と吊り灯 2 つ。配膳台・樽（1.0）から跳んで届く 3.2 より上まで
            + NOGO(-3.35, 3.35, 3.8, [(0.1, 1.3, 2.9), (1.3, 2.05, 2.65), (2.05, 2.6, 2.36)])
            + [B(x - 0.18, x + 0.18, 2.3, 2.66, 1.32, 1.68, cam=False) for x in (-1.2, 1.2)]
            # 正面の下の窓（雨戸の無い窓、窓台は 1.3〜1.4 で面から 0.19 m）：枠と窓台の前の帯（肩の高さ。前は体が窓台に 0.19 m 入った）
            + [B(x - 0.53, x + 0.53, 1.28, 2.2, 0.0, 0.2, cam=False) for x in (-3.3, 3.3)]
            # 裏：日よけ（2.35 から 1.2 m 前で 1.7）と灯、下の窓の雨戸。両側の下の窓の雨戸（西の面は路地、東の面は広場に向く）。
            # 上の端は棟の上（5.5）の少し下まで（外灯の柱の上 2.94 から跳んで届く 5.14 より上）
            + NOGO(-3.35, -1.45, 5.4, [(-9.62, -9.0, 2.05), (-10.25, -9.62, 1.68)])
            + [B(-3.52, -3.18, 1.74, 5.4, -9.6, -9.0, cam=False, nogo=True)]
            + [B(x - 0.47, x + 0.47, 1.7, 5.4, -9.62, -9.0, cam=False, nogo=True) for x in (3.3, 1.2)]
            + [B(5.0, 5.62, 1.7, 5.4, z - 0.47, z + 0.47, cam=False, nogo=True) for z in (-6.5, -2.5)]
            + [B(-5.62, -5.0, 1.7, 5.4, z - 0.47, z + 0.47, cam=False, nogo=True) for z in (-6.5, -2.5)])


def _bay(s, ax, x0, x1, y0, y1, z0, z1, **f):
    """北の段の擁壁の区画（中心 x = s * ax、壁の面 z=16 に yaw 180 で付く。town_terrace.terrace_side）の中の箱（区画の座標）を部屋の座標に"""
    xa, xb = sorted((s * ax - x0, s * ax - x1))
    return B(xa, xb, y0, y1, 16.0 - z1, 16.0 - z0, **f)


def _terrace(s):
    """北の段の擁壁の前（部屋の座標のまま。town_terrace.terrace_side）。s = -1 西 / +1 東。区画の種類 kinds は terrace_side と同じ並び。
    角の棟（|x| 4〜8）の扉の上の固いひさし（2.3 m から 1.2 m 前で 1.85）・吊り灯・下の窓の雨戸、区画 a の柔らかい日よけと吊り灯、
    区画 c の巻き上げ帆布は、乗れない柱（跳ぶと頭が当たる）。区画 b・d の 2.75・3.15 m の太い配管（壁から 0.5 m）は箱。
    5 m の通路の縁（黒鉛の梁と受け、4.35〜5.05 m、壁から 0.4 m）は、給水塔（3.19）から跳んで届く 5.4 より上まで。
    区画 b のはしご（壁から 0.18 m）は体だけの薄い箱"""
    kinds = ['a', 'd', 'c', 'b', 'a'] if s < 0 else ['b', 'c', 'a', 'd', 'b']
    x0, x1 = sorted((s * 4.55, s * 6.25))
    xw0, xw1 = sorted((s * 6.25, s * 7.4))
    xe0, xe1 = sorted((s * 8.0, s * 48.0))
    out = NOGO(x0, x1, 4.4, [(14.74, 15.15, 1.62), (15.15, 15.55, 1.8), (15.55, 16.0, 1.95)])
    out += [B(xw0, xw1, 1.7, 4.4, 15.36, 16.0, cam=False, nogo=True), B(xe0, xe1, 4.3, 6.2, 15.55, 16.0, cam=False, nogo=True)]
    # 角の棟の下の窓の枠と窓台（1.22〜2.0、面から 0.15 m）：肩の高さの帯（体だけ。上は雨戸の柱へ続く）
    out.append(B(*sorted((s * 6.42, s * 7.38)), 1.2, 1.72, 15.84, 16.0, cam=False))
    for k, ax in enumerate((12, 20, 28, 36, 44)):
        v = kinds[k]
        if v in ('b', 'd'):
            out.append(_bay(s, ax, -4.0, 4.0, 2.55, 3.35, 0.0, 0.5))
            if ax == 44:
                # 端の区画の配管の端（|x|=48）と、東西の低い壁の手すり（|x| 48.43〜48.57、上 1.9）の間：手すりの上から配管の下へ
                # 体だけの箱でつなぐ（前は手すりの上から配管の方へ下りると、手すりの角と配管の端の面の間に体が挟まって宙に止まった）
                out.append(B(*sorted((s * 48.0, s * 48.43)), 1.9, 3.35, 15.5, 16.0, cam=False))
        if v == 'b':
            # はしご（区画の x 2.5、壁から 0.18 m）：体だけの薄い箱（走る足が段の棒に入らない）
            out.append(_bay(s, ax, 2.2, 2.8, 0.0, 4.95, 0.0, 0.24, cam=False))
        if v == 'a':
            out += NOGO(*sorted((s * ax + 2.15, s * ax - 0.15)), 5.8, [(14.5, 15.2, 1.98), (15.2, 16.0, 2.25)])
            out += NOGO(*sorted((s * ax - 0.25, s * ax - 0.55)), 5.8, [(15.53, 16.0, 2.08)])
        if v == 'c':
            out += NOGO(*sorted((s * ax + 2.56, s * ax + 0.44)), 4.2, [(14.86, 15.34, 2.18), (15.34, 15.94, 2.6)])
    return out


SOLID = {**_ruins(), **_town()}


# ---------------------------------------------------------------- 置く

def _r3(v):
    return [round(float(x), 3) for x in v]


def _scale(d):
    sc = d.get("scale", 1.0)
    return [float(s) for s in sc] if isinstance(sc, list) else [float(sc)] * 3


def _rot(yaw_deg, x, z):
    """Godot の Basis(Vector3.UP, yaw)：+Z を向いた物を yaw 度回すと +X 寄りへ向く"""
    a = math.radians(yaw_deg)
    return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)


def extent(part, yaw=0.0, scale=1.0, solid=True):
    """部品の当たり判定の箱（SOLID の表）を yaw・scale で置いたときの、床の上の広がり [x0, x1, z0, z1] と高さ（部品の原点から）。
    部屋の JSON を書く道具が、箱どうしをくっつけて並べるのに使う（すき間を作らない：14.3.1）"""
    shapes = shapes_of({"part": part, "pos": [0, 0, 0], "yaw": yaw, "scale": scale, "solid": solid})
    x0 = min(s["pos"][0] - s["size"][0] / 2 for s in shapes)
    x1 = max(s["pos"][0] + s["size"][0] / 2 for s in shapes)
    z0 = min(s["pos"][2] - s["size"][2] / 2 for s in shapes)
    z1 = max(s["pos"][2] + s["size"][2] / 2 for s in shapes)
    top = max(s["pos"][1] + s["size"][1] for s in shapes)
    return [x0, x1, z0, z1], top


def snap(part, yaw=0.0, scale=1.0, x0=None, x1=None, z0=None, z1=None, x=None, z=None, solid=True):
    """当たり判定の箱の端を決めた所に合わせた、部品の原点の (x, z)。x0・x1：西・東の端、z0・z1：南・北の端、x・z：原点そのもの。
    例：snap("cc0/plank_box", 0, x0=-11.56, z1=12.62) は、箱の西の端が x -11.56、北の端が z 12.62 になる原点"""
    (ex0, ex1, ez0, ez1), _ = extent(part, yaw, scale, solid)
    px = x if x is not None else (x0 - ex0 if x0 is not None else (x1 - ex1 if x1 is not None else 0.0))
    pz = z if z is not None else (z0 - ez0 if z0 is not None else (z1 - ez1 if z1 is not None else 0.0))
    return round(px, 3), round(pz, 3)


def _spec(d):
    spec = d.get("solid")
    if not spec:
        return []
    if spec is True:
        return SOLID[d["part"]]
    if isinstance(spec, str):
        return SOLID[spec]
    return [b if isinstance(b, dict) else R(*b) for b in spec]


def shapes_of(d):
    """dress の 1 件の当たり判定の形（ワールドの geometry の形のリスト）"""
    boxes = _spec(d)
    if not boxes:
        return []
    sx, sy, sz = _scale(d)
    yaw = float(d.get("yaw", 0.0))
    step = d.get("step", [0, 0, 0])
    out = []
    for k in range(max(1, int(d.get("count", 1)))):
        px, py, pz = (float(d["pos"][i]) + float(step[i]) * k for i in range(3))
        for b in boxes:
            if b.get("t") in ("stairs", "ramp"):
                lx, ly, lz = b["pos"]
                wx, wy, wz = b["size"]
                byaw = float(b.get("yaw", 0.0))
                shape = {"t": b["t"]}
                if b["t"] == "stairs":
                    shape["steps"] = b.get("steps", 6)
                y0, hy = ly * sy, wy * sy
                flags = {k2: v for k2, v in (("cam", False), ("wall", True), ("nogo", True)) if b.get(k2) == v}
            else:
                (lx, lz), (wx, wz), (y0l, y1l), byaw = b["c"], b["w"], b["y"], float(b.get("yaw", 0.0))
                y0, hy = y0l * sy, (y1l - y0l) * sy
                shape = {"t": "box"}
                flags = {k2: v for k2, v in (("cam", False), ("wall", True), ("nogo", True)) if b.get(k2) == v}
            if byaw and abs(sx - sz) > 1e-6:
                raise ValueError(f"{d['part']}: 斜めの箱は x と z を同じ倍率にする（{sx}, {sz}）")
            dx, dz = _rot(yaw, lx * sx, lz * sz)
            fx, fz = abs(wx * sx), abs(wz * sz)
            tyaw = (yaw + byaw) % 360
            q = round(tyaw / 90.0)
            if shape["t"] != "box":
                # 階段・斜面は向きのある形：90 度の倍数の向きだけ。大きさは形の中の向きのまま、向きは yaw で渡す（RoomGeo が回す）
                if abs(tyaw - 90.0 * q) > 1e-3:
                    raise ValueError(f"{d['part']}: 階段・斜面の向きは 90 度の倍数にする（{tyaw}）")
                if round(byaw / 90.0) % 2:
                    fx, fz = abs(wx * sz), abs(wz * sx)
                shape["pos"] = _r3([px + dx, py + y0, pz + dz])
                shape["size"] = _r3([fx, abs(hy), fz])
                if q % 4:
                    shape["yaw"] = (q % 4) * 90
                shape.update(flags)
                out.append(shape)
                continue
            if abs(tyaw - 90.0 * q) > 1e-3:
                # 斜めの箱は、床の上の広がりを囲む軸にそろった箱にする。斜めの面と壁・ほかの箱の間にできるくさび形の
                # すき間に体が押し込まれると、床を抜けて沈んだ（体の物理は面を滑らせるだけなので、鋭い角で詰まる）
                a = math.radians(tyaw)
                fx, fz = (fx * abs(math.cos(a)) + fz * abs(math.sin(a)), fx * abs(math.sin(a)) + fz * abs(math.cos(a)))
            elif q % 2:
                fx, fz = fz, fx
            shape["pos"] = _r3([px + dx, py + y0, pz + dz])
            shape["size"] = _r3([fx, abs(hy), fz])
            shape.update(flags)
            out.append(shape)
    return out


def _aabbs(g):
    """部屋の形（飾りの箱でない物も）を、軸にそろった箱 [x0, x1, y0, y1, z0, z1] のリストにする（すき間を探す相手）。
    斜めの箱・斜面・階段は入れない"""
    t = g.get("t", "box")
    px, py, pz = (float(v) for v in g.get("pos", [0, 0, 0]))
    sx, sy, sz = (float(v) for v in g.get("size", [1, 1, 1]))
    if t == "box":
        yaw = float(g.get("yaw", 0.0)) % 180
        if abs(yaw) > 1e-3 and abs(yaw - 90) > 1e-3:
            return []
        if abs(yaw - 90) < 1e-3:
            sx, sz = sz, sx
        return [[px - sx / 2, px + sx / 2, py, py + sy, pz - sz / 2, pz + sz / 2]]
    if t == "shell" and not g.get("openings"):
        th = float(g.get("thick", 1.0))
        hx, hz = sx / 2, sz / 2
        return [[px - hx - th, px + hx + th, py - th, py, pz - hz - th, pz + hz + th],
                [px - hx - th, px - hx, py, py + sy, pz - hz - th, pz + hz + th],
                [px + hx, px + hx + th, py, py + sy, pz - hz - th, pz + hz + th],
                [px - hx - th, px + hx + th, py, py + sy, pz - hz - th, pz - hz],
                [px - hx - th, px + hx + th, py, py + sy, pz + hz, pz + hz + th]]
    return []


def _contains(a, b):
    """箱 a が箱 b を丸ごと含むか"""
    return all(a[2 * k] - 1e-4 <= b[2 * k] and b[2 * k + 1] <= a[2 * k + 1] + 1e-4 for k in range(3))


def _ground(solids, x, z, y1):
    """点 (x, z) の、高さ y1 までの一番上の面（箱の中で y1 より上まで届く物があれば None：もうふさがっている）"""
    top = -1e9
    for c in solids:
        a = c[0]
        if a[0] - 1e-4 <= x <= a[1] + 1e-4 and a[4] - 1e-4 <= z <= a[5] + 1e-4:
            if a[3] > y1 + 1e-3 and a[2] < y1 - 1e-3:
                return None
            if a[3] <= y1 + 1e-3:
                top = max(top, a[3])
    return top


def _floor(solids, box):
    """すき間の箱の床（すき間の上から見て一番低い所の面）。全部ふさがっていれば None"""
    lows = []
    for i in range(4):
        for j in range(4):
            x = box[0] + (box[1] - box[0]) * (0.1 + 0.8 * i / 3)
            z = box[4] + (box[5] - box[4]) * (0.1 + 0.8 * j / 3)
            g = _ground(solids, x, z, box[3])
            if g is not None:
                lows.append(g)
    return min(lows) if lows else None


def fill_gaps(geo, dress_shapes, ok=lambda s: True):
    """飾りの箱と、壁・ほかの箱との間の GAP より狭いすき間をふさぐ箱を作る。返り値：[(dress の番号, 形), …] と、広くふさいだ所の警告。
    すき間の深さは、すき間の下の床（ほかの箱・前にふさいだ箱の上の面）から測る（ベンチの背と卓の間は座面が床：浅いのでふさがない）。
    低いすき間から順にふさぐ。ok(形) が偽の箱（出口・トリガー・目印の決まりの距離に入る）は足さない"""
    solid = []      # [aabb, cam, wall, 飾りの番号（部屋の形なら None）, nogo]
    for g in geo:
        for a in _aabbs(g):
            solid.append([a, g.get("cam", True), False, None, False])
    for i, s in dress_shapes:
        if s["t"] == "box":
            solid.append([_aabbs(s)[0], s.get("cam", True), s.get("wall", False), i, s.get("nogo", False)])
    fills, warn = [], []
    first = 0       # この回に調べる組：どちらかが前の回に足した箱（初めは全部）
    for _ in range(4):
        cands = []
        for ia in range(len(solid)):
            a, cam_a, wall_a, own_a, nogo_a = solid[ia]
            if own_a is None:
                continue
            for ib in range(len(solid)):
                b, cam_b, wall_b, own_b, nogo_b = solid[ib]
                if ib == ia or max(ia, ib) < first or (own_b is not None and ib < ia) or own_b == own_a:
                    continue        # 同じ飾りの中の箱どうしは、部品を作るときに決めた形のまま
                y0, y1 = max(a[2], b[2]), min(a[3], b[3])
                if y1 - y0 < GAP_HIGH:
                    continue
                for ax, ox in ((0, 4), (4, 0)):
                    o0, o1 = max(a[ox], b[ox]), min(a[ox + 1], b[ox + 1])
                    if o1 - o0 < GAP_LONG:
                        continue
                    if b[ax] >= a[ax + 1]:
                        g0, g1 = a[ax + 1], b[ax]
                    elif a[ax] >= b[ax + 1]:
                        g0, g1 = b[ax + 1], a[ax]
                    else:
                        continue
                    if not 1e-3 < g1 - g0 < GAP:
                        continue
                    box = [0.0] * 6
                    box[ax], box[ax + 1] = g0, g1
                    box[ox], box[ox + 1] = o0, o1
                    box[2], box[3] = y0, y1
                    if _shrink(solid, box, ax, ox):
                        nogo = (nogo_a and abs(a[3] - y1) < 1e-3) or (nogo_b and abs(b[3] - y1) < 1e-3)
                        cands.append((y1, box, cam_a and cam_b, wall_a or wall_b, own_a, own_b, nogo))
        new = []
        # 低い物から、同じ高さなら狭い物から（狭いすき間を先にふさぐと、それを床にして広い方の重なりを捨てられる）
        for y1, box, cam, wall, own_a, own_b, nogo in sorted(cands, key=lambda c: (c[0], min(c[1][1] - c[1][0], c[1][5] - c[1][4]), c[1])):
            fl = _floor(solid + new, box)
            if fl is None or y1 - max(box[2], fl) < GAP_HIGH:
                continue        # もうふさがっている・床が高くて浅い
            shape = _fill_shape(box, cam, wall, nogo)
            if not ok(shape):
                warn.append(f"dress {own_a} のすき間 {_r3([box[0], box[2], box[4]])}〜{_r3([box[1], box[3], box[5]])} は出口・目印などに近いのでふさがない")
                continue
            new.append([box, cam, wall, own_a, nogo, own_b])
        if not new:
            break
        first = len(solid)
        solid += [c[:5] for c in new]
        fills += new
    # 後から足した大きい箱に丸ごと入った箱は捨てる（低い方から足すので、同じすき間を 2 度ふさぐことがある）
    keep = [f for k, f in enumerate(fills) if not any(j != k and _contains(g[0], f[0]) and (g[0] != f[0] or j < k) for j, g in enumerate(fills))]
    for box, cam, wall, own_a, nogo, own_b in keep:
        gap = min(box[1] - box[0], box[5] - box[4])
        if gap > FILL_WARN and box[3] < LEDGE_TOP:
            other = f"dress {own_b}" if own_b is not None else "部屋の形"
            warn.append(f"dress {own_a} と {other} の間 {gap:.2f} m を {_r3([box[0], box[2], box[4]])}〜{_r3([box[1], box[3], box[5]])} でふさいだ")
    return [(own, _fill_shape(box, cam, wall, nogo)) for box, cam, wall, own, nogo, _ in keep], warn


def _shrink(solid, box, ax, ox):
    """すき間の箱（ax がすき間の向き）を、両端からすき間の幅いっぱい・高さいっぱいに入り込んだ物の分だけ縮める。残れば True"""
    changed = True
    while changed and box[ax + 1] - box[ax] > 1e-3:
        changed = False
        for c in solid:
            a = c[0]
            if a[ox] > box[ox] + 1e-4 or a[ox + 1] < box[ox + 1] - 1e-4 or a[2] > box[2] + 1e-4 or a[3] < box[3] - 1e-4:
                continue
            if a[ax] <= box[ax] + 1e-4 and box[ax] + 1e-3 < a[ax + 1]:
                box[ax] = min(a[ax + 1], box[ax + 1])
                changed = True
            if a[ax + 1] >= box[ax + 1] - 1e-4 and a[ax] < box[ax + 1] - 1e-3:
                box[ax + 1] = max(a[ax], box[ax])
                changed = True
            if box[ax + 1] - box[ax] <= 1e-3:
                return False
    return box[ax + 1] - box[ax] > 1e-3


def _fill_shape(box, cam, wall, nogo=False):
    """ふさぐ箱の形。乗れない柱と同じ高さまでふさぐ箱は、乗れない柱（nogo）にする"""
    s = {"t": "box", "pos": _r3([(box[0] + box[1]) / 2, box[2], (box[4] + box[5]) / 2]),
         "size": _r3([box[1] - box[0], box[3] - box[2], box[5] - box[4]]), "fill": True}
    if not cam:
        s["cam"] = False
    if wall:
        s["wall"] = True
    if nogo:
        s["nogo"] = True
    return s


def apply(room):
    """部屋の dress の "solid" から、描かない当たり判定の形を geometry の終わりに足す（前に足した形は消す）。足した数を返す"""
    geo = [g for g in room["geometry"] if "dress" not in g]
    shapes = [(i, s) for i, d in enumerate(room.get("dress", [])) for s in shapes_of(d)]
    fills, warn = fill_gaps(geo, shapes, lambda sh: not problems(room, sh))
    for w in warn:
        print("  警告：", w)
    out = list(geo)
    for i, s in shapes + fills:
        s["hide"] = True
        s["tint"] = "#5a5048"
        s["dress"] = i
        out.append(s)
    room["geometry"] = out
    check(room)
    return len(shapes) + len(fills)


# ---------------------------------------------------------------- 決まりの確かめ（godot/tests/test_kit.gd と同じ）

CLEAR_BOX = 0.1      # 出口・トリガーの箱から
CLEAR_MARK = 0.6     # 目印・チェックポイント・敵の出る所から（体の半径 0.35 ＋ゆとり）
CLEAR_PROP = 0.5     # 調べる物・拾う物・住人から
BODY = 1.6           # 体の高さ（1.55）
AREA = 4.0           # 両辺がこれより広いトリガーは「場所」（広場など。どこからでも歩いて入る）
SMALL = 0.5          # 場所のトリガーの中には、床の上の広がりがこれより小さい形（吊り灯の柱など）は立ててよい


def footprint(g):
    """形の床の上の広がり：(中心 x, 中心 z, 半幅 x, 半幅 z, yaw 度, 下の y, 上の y)"""
    hx, hz = g["size"][0] / 2, g["size"][2] / 2
    return g["pos"][0], g["pos"][2], hx, hz, float(g.get("yaw", 0.0)), g["pos"][1], g["pos"][1] + g["size"][1]


def dist_point(g, x, z):
    """点 (x, z) から形の床の上の広がりまでの距離（中なら 0）"""
    cx, cz, hx, hz, yaw, _, _ = footprint(g)
    lx, lz = _rot(-yaw, x - cx, z - cz)
    return math.hypot(max(abs(lx) - hx, 0.0), max(abs(lz) - hz, 0.0))


def overlaps_box(g, center, half, clear):
    """形が軸にそろった箱（中心・半幅）に clear まで近いか（高さも見る）。形の角 4 つと箱の辺で調べる（分離軸）"""
    cx, cz, hx, hz, yaw, y0, y1 = footprint(g)
    if y1 < center[1] - half[1] - clear or y0 > center[1] + half[1] + 1.0 + clear:
        return False
    a = math.radians(yaw)
    ex = abs(hx * math.cos(a)) + abs(hz * math.sin(a))
    ez = abs(hx * math.sin(a)) + abs(hz * math.cos(a))
    if abs(cx - center[0]) >= ex + half[0] + clear or abs(cz - center[2]) >= ez + half[2] + clear:
        return False
    # 形の軸で見る（回した形）
    for ax, az, h in ((math.cos(a), -math.sin(a), hx), (math.sin(a), math.cos(a), hz)):
        r = abs(half[0] * ax) + abs(half[2] * az)
        if abs((center[0] - cx) * ax + (center[2] - cz) * az) >= h + r + clear:
            return False
    return True


def wall_edge_only(g, center, half):
    """wall の帯が出口・トリガーの箱に、壁ぎわの WALL_REACH までしか掛かっていないか（重なりの幅か奥行きが WALL_REACH 以下）"""
    cx, cz, hx, hz, _, _, _ = footprint(g)
    ox = min(cx + hx, center[0] + half[0]) - max(cx - hx, center[0] - half[0]) + 2 * CLEAR_BOX
    oz = min(cz + hz, center[2] + half[2]) - max(cz - hz, center[2] - half[2]) + 2 * CLEAR_BOX
    return min(ox, oz) <= WALL_REACH


def _targets(room):
    marks = [(n, m["pos"]) for n, m in room.get("markers", {}).items()]
    marks += [(c["id"], c["pos"]) for c in room.get("checkpoints", [])]
    marks += [(e.get("id", e.get("kind", "敵")), e["pos"]) for e in room.get("enemies", []) if "pos" in e]
    boxes = [(t["id"], t["pos"], t["size"], t["size"][0] >= AREA and t["size"][2] >= AREA)
             for t in room.get("triggers", []) if "pos" in t and "size" in t]
    points = []
    for p in room.get("props", []):
        if p.get("type") == "sign":
            continue
        if "size" in p and isinstance(p["size"], list):
            boxes.append((p.get("id", p["type"]), p["pos"], p["size"], False))
        elif "pos" in p:
            points.append((p.get("id", p["type"]), p["pos"]))
    return marks, points, boxes


def problems(room, g, targets=None):
    """足す形 g が、出口・トリガー・目印・調べる物などの決まりの距離に入っていれば、その一覧"""
    marks, points, boxes = targets or _targets(room)
    bad = []
    _, _, _, _, _, y0, y1 = footprint(g)
    for name, pos, clear in [(n, p, CLEAR_MARK) for n, p in marks] + [(n, p, CLEAR_PROP) for n, p in points]:
        if y1 > pos[1] - 0.2 and y0 < pos[1] + BODY and dist_point(g, pos[0], pos[2]) < clear:
            bad.append(f"{name} {pos} に近い")
    small = footprint(g)[2] * 2 <= SMALL and footprint(g)[3] * 2 <= SMALL
    for name, pos, size, area in boxes:
        if area and small:
            continue
        half = [size[0] / 2, size[1] / 2, size[2] / 2]
        center = [pos[0], pos[1] + half[1], pos[2]]
        if overlaps_box(g, center, half, CLEAR_BOX) and not (g.get("wall") and wall_edge_only(g, center, half)):
            bad.append(f"{name} の箱に掛かる")
    return bad


def check(room):
    """足した形が、出口・トリガー・目印・調べる物などの決まりの距離を守っているか。だめなら ValueError"""
    targets = _targets(room)
    bad = []
    for g in room["geometry"]:
        if "dress" in g:
            bad += [f"{room['dress'][g['dress']]['part']} {g['pos']} が {b}" for b in problems(room, g, targets)]
    if bad:
        raise ValueError("solid の箱の置き場所がだめ：\n  " + "\n  ".join(bad))
