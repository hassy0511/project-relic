#!/usr/bin/env python3
"""オルド背町の部屋に、キット（"kit": "town"）と飾り（"dress"）・形の "skin" / "hide" を書き込む。出力：godot/content/areas/ch1_town.json

部屋の当たり判定（geometry の位置と大きさ）・目印・出口・トリガー・住人・置く物の位置は変えない。変えるのは見た目の項目だけ
（部屋の "kit"・"dress"・"lights" の位置、形の "skin"・"hide"、看板の "board"・"yaw"・"board_w"）と、飾りの "solid" から作る
描かない当たり判定の箱（geometry の終わりの "dress" つきの形。tools/dress_solid.py）。
何度流しても同じ結果になる（dress と solid の箱は毎回作り直す）。部品の寸法と原点：tools/blender/kit/town_parts.py・town_sets.py・town_terrace.py。
絵：W2-05 town_mood_day.png（中段の広場）・town_layout.png・town_mood_emergency.png（停止の夜）。

  python3 tools/dress_town.py            キットを付ける部屋（ROOMS）を全部
  python3 tools/dress_town.py mid        1 部屋だけ
"""
import json
import os
import sys

import dress_solid

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PATH = os.path.join(ROOT, "godot", "content", "areas", "ch1_town.json")


def r3(v):
    return [round(float(x), 3) for x in v]


class Dress:
    def __init__(self):
        self.items = []

    def put(self, part, pos, yaw=0, **kw):
        d = {"part": part if "/" in part else "town/" + part, "pos": r3(pos)}
        if yaw:
            d["yaw"] = yaw % 360
        for k, v in kw.items():
            if k == "solid" and isinstance(v, list):
                # 部品の中の箱を直接（dress_solid.B・P・NOGO の辞書）。数は 3 桁に丸め、印（cam・wall・nogo）は既定と違うものだけ
                d[k] = [{**{kk: (r3(vv) if isinstance(vv, (list, tuple)) else vv) for kk, vv in b.items() if kk not in ("cam", "wall", "nogo")},
                         **{kk: b[kk] for kk, dv in (("cam", True), ("wall", False), ("nogo", False)) if b.get(kk, dv) != dv}}
                        if isinstance(b, dict) else r3(b) for b in v]
            else:
                d[k] = r3(v) if isinstance(v, (list, tuple)) else v
        self.items.append(d)
        return d

    def snug(self, part, yaw=0, y=0.0, scale=None, **edges):
        """当たり判定の箱の端を edges（x0・x1・z0・z1・x・z）に合わせて置く（dress_solid.snap。箱どうしを 2 cm 離して並べる）"""
        full = part if "/" in part else "town/" + part
        x, z = dress_solid.snap(full, yaw, scale or 1.0, **edges)
        kw = {"scale": scale} if scale is not None else {}
        return self.put(full, [x, y, z], yaw, solid=True, **kw)


def geo_index(room, pos, size):
    """geometry の中から pos・size の一致する形を探す（番号で書くと、形を足したときにずれるため）"""
    for i, g in enumerate(room["geometry"]):
        if all(abs(a - b) < 1e-3 for a, b in zip(g.get("pos", []), pos)) and all(abs(a - b) < 1e-3 for a, b in zip(g.get("size", []), size)):
            return g
    raise KeyError(f"形が無い: {pos} {size}")


def light(room, old_pos, new_pos, was=()):
    """部屋の明かりを old_pos（元の位置）から new_pos へ。was：前にこの表で動かした先（灯を動かしたとき）"""
    for l in room.get("lights", []):
        if any(all(abs(a - b) < 1e-3 for a, b in zip(l["pos"], q)) for q in (old_pos, new_pos, *was)):
            l["pos"] = r3(new_pos)
            return l
    raise KeyError(f"明かりが無い: {old_pos}")


def sign(room, text, board, yaw, board_w):
    for p in room["props"]:
        if p.get("type") == "sign" and p.get("text") == text:
            p["board"] = "town/" + board
            p["yaw"] = yaw
            p["board_w"] = board_w
            return p
    raise KeyError(f"看板が無い: {text}")


def common(room, d):
    """町の部屋に共通：キット town。オルドの体は部屋ごとに ordo() で置く"""
    room["kit"] = "town"
    room.pop("ordo", None)


# 町の下の巡礼機オルド（2026-10-16。旧遠景 ordo_far の入れ替え）。部屋の "ordo"：{"pos": 部屋の座標でのオルドの原点（背の歩行面の真ん中）}。
# 体は部屋と一緒に止まり、120 m 下の砂の床が流れる（OrdoView、RoomView が作る）。背の上の遠くの町（キットの部品 ordo_back・ordo_town）は
# "back" に書き、オルドと同じ 3 つの面にまとめて描く（飾りにすると面が 3 つ増える。中段のいちばん重い向きが前より重くなった）。
# 部屋ごとの位置（docs/art_orders/W2_オルド3D化の結果.md 9 章）：
#   中段 mid    [0, -6.5, 0]    背の面は下の段の床（y = -5.02）の 1.5 m 下。町の真ん中（オルドの z = 0）
#   下段 lower  [0, -1.5, 8]    背の面は床の 1.5 m 下。リフトの端末（z = -4）・昇降機（z = -9）をオルドの左舷のリフト（z = -12、踊り場 -21〜-3）に合わせる
#   夜明けの甲羅 opening [0, -39.5, -176]  船首の頭（背の面 +30、上の機械の箱の上 +37）の上の台。北の地平線の前に何も置かない
#   上段 upper  置かない          展望台は船首の向き。頭（背の面 +32.5）が地平線を 14 度の高さまで隠し、章末のカランの影が見えなくなる
ORDO_POS = {"mid": [0, -6.5, 0], "lower": [0, -1.5, 8], "opening": [0, -39.5, -176]}


def ordo(room, d, name, back="ordo_back", ground=True):
    """ground=False：砂の床を描かない（夜明けの甲羅：始めの場面のカメラが空から見る地平線の砂漠は空の絵のまま）"""
    room["ordo"] = {"pos": ORDO_POS[name], "back": "town/" + back}
    if not ground:
        room["ordo"]["ground"] = False


# 生活感の小物（2026-10-15）は影を落とさない（部品の種類ごとに、影の描画が影の段の数だけ増えるため。CC0 の樽と長持ちに影を付けると
# 市場の向きで描画が 16 回増え、見た目はほとんど変わらなかった）
SHADOW = {"stall", "tent", "monument", "workshop_front", "diner_front", "stage", "lamp_post", "lamp_tall", "bench",
          "stall_table", "crate", "barrel", "junk_pile", "planter_big"}

# 当たり判定を付ける部品（"solid": true。箱の形は tools/dress_solid.py の SOLID）。歩ける所に立つ、手で触れる大きさの物：
# 木箱・樽・収納箱・鉢植え・ベンチ・卓・工具棚・給水塔・洗濯綱・床の配管・外灯の台・胸壁の角の柱・露店の棚と柱と裏の木箱・
# 天幕の下の台と木箱と樽・工房の正面の足元の小物と入口の内張り・食堂の裏の木箱と樽・壇の旗竿・階段の手すり・胸壁の上の手すり・
# 北の段の配管とひさし・記念の柱の吊り灯・南の階段の下の縦の管。
# 前はどれも当たり判定が無く、ハルが樽・木箱の中に入り込んで頭だけ出して立てた（ハリボテに見えた）。
# 細い柱（露店・天幕の柱、旗竿、外灯の柱、洗濯綱の柱、胸壁の手すり）と、露店の屋根・台の上・天幕の帆布の上をふさぐ箱、
# 頭の上の張り出し（日よけ・巻き上げ帆布・吊り灯・雨戸：乗れない柱）は、体だけを止める（"cam": false。カメラは通す）。
# 箱の形は tools/dress_solid.py の SOLID。
# 木箱の山とガラクタ（crate の大きな 3 つ・junk_pile）は、前から同じ広さの描かない箱があるので付けない（solid=False）
SOLID = {"crate", "barrel", "chest", "planter", "planter_big", "bench", "stall_table", "tool_rack", "water_tower", "clothesline",
         "pipes", "lamp_post", "lamp_tall", "parapet_corner", "goods_shelf_general", "goods_shelf_junk", "stall", "tent",
         "workshop_front", "diner_front", "stage", "stair_rail_12", "stair_rail_12_r", "parapet_rail_8", "parapet_rail_4",
         "terrace_west", "terrace_east", "window_flush", "canvas_roll", "monument", "stair_well_s",
         "tank", "stool", "pipe_bend", "bollard", "hand_lantern", "cask", "plank_box", "sacks",
         # W2-05b 市場のにぎわい（2026-10-17、tools/blender/kit/town_goods.py）
         "goods_sacks", "market_general", "market_junk", "diner_table", "sign_stand", "toy_banki", "laundry_basket",
         "goods_cloth", "junk_goods", "goods_basket", "pot_succulent", "pot_shrub", "pot_vine", "wind_flag"}


# ---------------------------------------------------------------- 中段（広場と市場）

def mid(room):
    d = Dress()
    common(room, d)
    G = lambda pos, size: geo_index(room, pos, size)  # noqa: E731

    # --- 地形の面
    G([0, 0, 1], [26, 0.08, 18])["skin"] = {"floor": "plaza", "wall": "stone2"}
    G([0, 0, 2], [3.2, 1.0, 3.2])["skin"] = {"floor": "stone2", "wall": "wall"}
    G([0, 1.0, 2], [1.0, 2.6, 1.0])["hide"] = True                     # 記念の柱の芯（monument が包む）
    G([0, 0, 9], [8, 0.8, 3])["skin"] = {"floor": "wood", "wall": "stone2"}
    # 階段：蹴上げは段の高さ（5/16 m）ごとに黒鉛の継ぎ目の線（面 riser の seams。段の上と下の縁に線が来る）。
    # 前は模様の無い同じ色の面で、足元から見上げると踏み面が隠れ、16 段が 1 枚のくさびに見えた
    for z in (22, -20):
        G([0, 0 if z > 0 else -5, z], [8, 5, 12])["skin"] = {"floor": "floor", "wall": "riser"}
    for g in (G([-34, 7, 8.5], [14.6, 0.6, 9.6]), G([-20, 5.5, 5], [10.6, 0.5, 9.6])):
        g["skin"] = {"wall": "graphite", "floor": "rust", "ceiling": "graphite"}
    for x in (24, 38):
        G([x, 0, 3.8], [7, 1.1, 0.8])["skin"] = "wood"                  # 露店の台
        G([x, 0, 8.6], [7, 2.4, 1.0])["skin"] = "wood"                  # 露店の奥の箱
        G([x, 3.2, 6.3], [8, 0.25, 5.2])["hide"] = True                 # 露店の屋根（stall の帆布が覆う）
    G([-20, 0, 0.3], [4, 1.0, 1.2])["skin"] = "wood"                     # 食堂の配膳台
    for pos, size in (([30.5, 0, -6], [3, 1.0, 2]), ([42, 0, -7], [2, 1.6, 2]), ([-30, 0, -7], [2.5, 1.2, 2])):
        G(pos, size)["hide"] = True                                       # 木箱の山・ガラクタ（部品で置き換え）

    # --- 北の段の壁（高さ 16 m）：奥行きのある段々の家の塊（town_terrace.py。部屋の座標のまま置く）。
    # 段の壁・階段の横の壁・門の壁の箱は当たり判定だけ残して描かない（家の塊の面が同じ所にある：擁壁 z=16、路地 |x|=4、門 z=34）
    for pos, size in (([-26.25, 0, 16.5], [43.5, 16, 1]), ([26.25, 0, 16.5], [43.5, 16, 1]),
                      ([-4.25, 0, 25], [0.5, 9, 18]), ([4.25, 0, 25], [0.5, 9, 18]), ([0, 0, 34.5], [9, 12, 1])):
        G(pos, size)["hide"] = True
    for part in ("terrace_west", "terrace_east", "stair_gate"):
        d.put(part, [0, 0, 0])

    # --- 北の階段（上の段へ）：手すりと、上り口の鉢植え・外灯。踏み段の縁（段鼻。前は低い所から見上げると 16 段が 1 枚のくさびに見えた）
    d.put("stair_rail_12", [-4.0, 0, 16.0], solid="town/stair_rail_12_foot")       # 上り口の端の上は乗れない柱（dress_solid._rail_band）
    d.put("stair_rail_12_r", [4.0, 0, 16.0], solid="town/stair_rail_12_r_foot")
    d.put("stair_treads_16", [0, 0, 22])
    for x in (-5.4, 5.4):
        d.put("planter", [x, 0, 13.95])      # 角の棟の扉のひさしの前（前は 15.2 でひさしの真下にあり、上に乗ると頭がひさしに入った）

    # --- 南の胸壁（下の段を見下ろす縁）：上に真鍮の手すり、外の面は擁壁、その下に下の段の家並み
    for sx in (-1, 1):
        for k, x in enumerate((8.5, 16.5, 24.5, 32.5, 40.5)):
            d.put("parapet_rail_8", [sx * x, 1.2, -14.5])
            d.put("retaining_" + "abcab"[k], [sx * x, -5.0, -15.0], 180)
        d.put("parapet_rail_4", [sx * 46.5, 1.2, -14.5])
        d.put("retaining_a", [sx * 46.5, -5.0, -15.0], 180, scale=[0.5, 1, 1])
    # 東西の低い壁（高さ 3.2、上の面 1.2、z -14〜16）：手すりと、外の面の擁壁（背の面まで）。
    # 北の端の 1 本は 6 m（z 10〜16）にして、壁の当たり判定の端（z=16）で止める（前は 8 m で z 18 まで出て、
    # 段の家の塊の端の横に笠木・付け柱・擁壁の端が宙に浮いていた）。端には角の柱（南の角と同じ parapet_corner）
    for sx, yaw in ((-1, 90), (1, 270)):
        for z in (-10, -2, 6):
            d.put("parapet_rail_8", [sx * 48.5, 1.2, z], yaw)
            d.put("retaining_" + ("b" if z == -2 else "a"), [sx * 49.0, -7.0, z], (yaw + 180) % 360)
        d.put("parapet_rail_8", [sx * 48.5, 1.2, 13.0], yaw, scale=[0.75, 1, 1])
        d.put("retaining_b", [sx * 49.0, -7.0, 13.0], (yaw + 180) % 360, scale=[0.75, 1, 1])
        d.put("parapet_corner", [sx * 48.5, 1.2, 15.5])
    # 南の階段（下の段へ）：手すり、上り口の背の高い外灯 2 本
    d.put("stair_rail_12", [-4.0, -5.0, -26.0])
    d.put("stair_rail_12_r", [4.0, -5.0, -26.0])
    d.put("stair_treads_16", [0, -5.0, -20])
    # 南の階段の両側の棟と奥の棟（town_terrace.py。部屋の座標のまま）。広場の南の角の柱（胸壁と東西の低い壁の間の切れ目をふさぐ）
    d.put("stair_well_s", [0, 0, 0])
    for sx in (-1, 1):
        d.put("parapet_corner", [sx * 48.5, 1.2, -14.5])
    # 上り口の背の高い外灯は胸壁の面から 0.9 m（柱と胸壁の間を体が通る。前は 0.4 m で、胸壁の縁から下りると、縁の角と柱の間に
    # 体の丸い底が挟まって宙に止まった）
    d.put("lamp_tall", [-5.4, 0, -12.9])
    d.put("lamp_tall", [5.4, 0, -12.9], 180, light={"at": [0.55, 3.92, 0], "color": "#ffc27a", "range": 14, "energy": 1.6})
    light(room, [0, 5, -10], [-4.85, 3.92, -12.9], was=[[-4.85, 3.92, -13.4]])

    # --- 下の段（胸壁の向こう、5 m 下）：床と家並み。南の階段の東の棟（外の面 x=9.5）の横の区画は x=16（前は 15.5 で、
    # 区画の家の日よけ・金具が棟の窓と同じ面で重なっていた）
    d.put("deck_slab", [0, -5.02, -35.35], shadow=False)           # 北の縁 z=-14.7（擁壁の面 z=-15 の 0.3 m 奥）まで
    for x, z, v, yaw in ((-40, -23, "a", 0), (-26, -22, "b", 180), (-15.5, -24, "c", 0), (16.0, -23, "a", 180), (26, -24, "c", 0),
                         (40, -22, "b", 0), (-34, -36, "c", 180), (-18, -38, "a", 0), (18, -36, "b", 180), (34, -38, "a", 180),
                         (-26, -50, "b", 0), (0, -46, "c", 180), (26, -50, "c", 0), (-44, -48, "a", 180), (44, -48, "b", 0)):
        d.put("lower_block_" + v, [x, -5.02, z], yaw, shadow=False)

    # --- 町の下のオルド（背の面は下の段の床の 1.5 m 下）と、下の段の向こうの遠くの町
    ordo(room, d, "mid")

    # --- 広場：中央の記念の柱（看板「広場」の文字の下に収まる高さ）、床の円、奥の壇、角の外灯、ベンチ、鉢植え
    d.put("monument", [0, 0, 2], scale=[1, 0.68, 1])
    d.put("plaza_ring", [0, 0.08, 2])
    d.put("stage", [0, 0, 9])
    for x, z, yaw in ((-12.5, -7.5, 0), (12.5, -7.5, 180), (-12.5, 9.5, 0), (12.5, 9.5, 180)):
        d.put("lamp_post", [x, 0, z], yaw, scale=1.4)
    for x, z, yaw in ((-9.5, -2, 90), (9.5, -2, 270), (-9.5, 5, 90), (9.5, 5, 270)):
        d.put("bench", [x, 0, z], yaw)
    # 胸壁から 0.35 m 離す（胸壁の上の手すりの箱との間を 0.78 m：体が下りて胸壁の上に立てる。前の -13.35 では 0.63 m で、
    # 鉢植えの上から胸壁の方へ下りると、鉢植えの縁と手すりの間に挟まって出られなくなった）
    for x in (-10, -20, -30, -40, 10, 20, 34, 44):
        d.put("planter", [x, 0, -13.2], 0)
    # 木箱の山（隠した箱と同じ広さ・高さ）
    d.put("crate", [29.75, 0, -6], 0, scale=[1.65, 1.35, 2.2], solid=False)
    d.put("crate", [31.25, 0, -6], 0, scale=[1.65, 1.35, 2.2], solid=False)
    d.put("crate", [42, 0, -7], 0, scale=[2.2, 2.16, 2.2], solid=False)
    d.put("junk_pile", [-30, 0, -7], 0, scale=[1.2, 1.05, 1.3], solid=False)
    d.put("barrel", [27.6, 0, -6.4])
    d.put("barrel", [40.4, 0, -7.6], 0, scale=0.9)

    # 広場の両脇の天幕と大きな鉢植え（town_mood_day の天幕と緑）
    d.put("tent", [-9.0, 0, 11.2], 180)
    d.put("tent", [9.0, 0, 11.2], 180)
    # 胸壁の前の 2 つは胸壁から 0.34 m（前は 0.54 m で、茂みの上から胸壁の手すりの方へ下りると間に引っかかった。
    # 0.34 m は体が入れないので床までふさぎ、手すりとの間は 0.77 m 空けて胸壁の上に下りられるようにする）
    for x, z in ((-13.2, 13.6), (13.2, 13.6), (-2.6, 13.8), (2.6, 13.8), (-36.5, -13.0), (36.5, -13.0)):
        d.put("planter_big", [x, 0, z])

    # --- 建物の横の面（何も無い白い壁）に窓
    # 下の窓は雨戸の無い窓（前は雨戸が 0.62 m 出ていて、横を歩くと肩・頭が入った）。床の配管は食堂の裏の先へ（食堂の西の面の縦の管と並ぶと 0.6 m のすき間になる）
    for x, yaw in ((-26.98, 90), (-41.02, 270)):
        for z in (6.5, 10.5):
            d.put("window_flush", [x, 1.3, z], yaw)
            d.put("window_frame", [x, 4.4, z], yaw)
    d.put("canvas_roll", [-26.98, 3.6, 8.5], 90)
    d.put("pipes", [-26.68, 0, 11.5], 90)

    # --- ヤーナの工房（正面 z=4、入口の奥まり z=6）
    d.put("workshop_front", [-34, 0, 4.0], 180)
    sign(room, "ヤーナの工房", "sign_wall_3", 180, 3.0)
    light(room, [-34, 5, -2], [-36.0, 2.9, 3.4])

    # --- 食堂（正面 z=0.5）：日よけ・配膳の窓・屋根の看板、前に卓とベンチ
    d.put("diner_front", [-20, 0, 0.5], 180)
    sign(room, "食堂", "sign_roof_2", 180, 2.2)
    light(room, [-20, 5, -2], [-21.2, 2.6, -1.1])
    # ベンチは卓の縁から 0.08 m（座面の前の縁が卓の下に入る）。前は 0.33 m 離れていて、間に落ちると両側の角に引っかかって宙に浮いた
    # 卓は W2-05b の食堂の机（diner_table：前の露店台と同じ大きさ・同じ当たり判定。赤い掛け布と食器）
    for x in (-24.6, -15.4):
        d.put("diner_table", [x, 0, -3.6], 90, scale=[1, 0.82, 1])
        d.put("bench", [x - 0.85, 0, -3.6], 90, scale=[1, 0.9, 1])
        d.put("bench", [x + 0.85, 0, -3.6], 270, scale=[1, 0.9, 1])
    d.put("barrel", [-14.2, 0, 0.0])
    d.put("crate", [-25.8, 0, 0.0], 4, scale=0.8)      # 向きは数度だけ（前は 15 度で、囲む当たり判定の箱が 0.25 m 手前で止めた）

    # --- 市場：露店 2 つ（屋根の箱の中心、正面 -Z）、台の上の品、奥の棚、看板、吊り灯の明かり
    # 台の上の品・前の梁の吊り物と絵の札・台の前の床の品は W2-05b の組（market_general・market_junk。town_goods.py、
    # town_goods_assembled の露店 1 基の密度。前は goods_general・goods_junk の台の上だけ）。台の前の真ん中 3 m は店主と話すために空ける
    for x, goods, shelf, text, board, bw in ((24, "market_general", "goods_shelf_general", "雑貨屋", "sign_post_2", 2.2),
                                              (38, "market_junk", "goods_shelf_junk", "ジャンク屋", "sign_post_3", 3.0)):
        d.put("stall", [x, 0, 6.3], 180)
        d.put(goods, [x, 1.1, 3.8], 180)
        d.put(shelf, [x, 0, 8.1], 180)
        sign(room, text, board, 180, bw)
        light(room, [x, 5, 2], [x - 2.0, 2.8, 3.7])
        d.put("barrel", [x - 4.6, 0, 4.4])
        d.put("chest", [x + 4.9, 0, 5.2], 183)      # 台の端・露店の前の柱から 0.8 m 離す（前は 0.4〜0.6 m の間に挟まった）
    d.put("tool_rack", [31, 0, 9.0], 180)
    d.put("clothesline", [31, 0, 11.5], 180)
    d.put("water_tower", [31, 0, 13.6], 0, scale=1.3)

    lived_mid(d)
    grime_mid(d)
    return finish(room, d)


def finish(room, d):
    """影・当たり判定の印を付けて部屋の dress に書き、飾りの solid から描かない当たり判定の箱を足す"""
    # 影を落とすのは近くで形を読ませる物だけ（キットの既定は影なし。影の描画は部品の描画の 2 倍以上かかる）
    for it in d.items:
        if it["part"].split("/")[1] in SHADOW and "shadow" not in it:
            it["shadow"] = True
        if it.get("solid") is False:
            it.pop("solid")
        elif isinstance(it.get("solid"), (str, list)):
            pass        # 表の別の行（dress_solid.SOLID の名前）か、部品の中の箱を直接
        elif it["part"].split("/")[1] in SOLID:
            it["solid"] = True
    room["dress"] = d.items
    dress_solid.apply(room)
    return room


def lived_mid(d):
    """生活感の小物（2026-10-15。town_mood_day の露店のまわりの箱・樽・布、路地の洗濯物、胸壁の縁の物）。
    どれも前からある部品（同じ部品は 1 つの MultiMesh で描くので、描画の数はほとんど増えない）と、W2-05 の小物の係留柱・
    路地に渡す洗濯物の綱、CC0 の樽・長持ち（tools/blender/kit/cc0_props.py）。手で触れる物は当たり判定つき。
    箱どうしは 2 cm 離してくっつける（間の 0.75 m より狭いすき間は道具がふさいで見えない棚になる：14.3.1）。
    広場の真ん中・露店の前・食堂と工房の入口・住人のまわり・出口と目印は空けておく"""
    # --- 市場：雑貨屋の西の脇に、箱の山と樽と鉢植えの角（露店の柱・前の樽から 0.75 m 以上）
    d.snug("crate", 0, x1=18.9, z0=5.6)
    d.snug("crate", 3, y=0.74, x1=18.85, z0=5.62, scale=0.85)
    d.snug("crate", 0, x1=17.94, z0=5.6, scale=0.9)
    d.snug("cc0/cask", 0, x1=18.9, z0=6.56)
    d.snug("pot_shrub", 0, x1=18.9, z0=8.1)             # W2-05b の鉢植え（低木）
    d.snug("goods_sacks", 0, x1=17.07, z0=5.6)
    # 露店の間（工具棚の前）：配達の木箱の山と長持ち（工具棚と洗濯綱の前の通り道 x 31.4〜33 は空ける）
    d.snug("crate", 0, x0=29.6, z1=8.78)
    d.snug("crate", 2, y=0.74, x0=29.66, z1=8.76, scale=0.8)
    d.snug("cc0/plank_box", 90, x0=29.6, z1=7.82)
    # 東の端：小さな 3 つ目の店（天幕。中に台・木箱・樽）。ジャンク屋の収納箱と東の低い壁から 0.75 m 以上
    d.put("tent", [45.7, 0, 5.6], 270)
    d.snug("barrel", 0, x0=44.25, z1=2.95)
    d.snug("cc0/cask", 0, x0=44.97, z1=2.95)
    d.snug("goods_sacks", 0, x0=45.69, z1=2.95)
    # 露店の間の前（どちらの露店の前でもない x 29.6〜32.5）：小さな出店の台（赤い掛け布と真鍮の壺）と、横に木箱と麻袋。
    # 露店の台の前（z 3.4）から 4 m 離して、市場の真ん中の通り道を空ける
    d.snug("stall_table", 0, x0=30.0, z1=-0.6)
    d.snug("crate", 2, x1=29.98, z1=-0.6, scale=0.85)
    d.snug("goods_sacks", 0, x0=32.04, z1=-0.6)
    # 雑貨屋・ジャンク屋の裏（奥の箱の山の後ろ）：長持ちと樽
    d.snug("cc0/plank_box", 0, x0=22.6, z0=10.2)
    d.snug("cc0/cask", 0, x0=24.02, z0=10.2)
    d.snug("cc0/plank_box", 0, x0=36.4, z0=10.2)
    d.snug("barrel", 0, x0=37.82, z0=10.2)
    # 市場の南（前からの木箱の山の横）：樽と長持ち
    d.snug("cc0/cask", 0, x0=32.0, z1=-5.2)
    d.snug("cc0/plank_box", 90, x1=40.98, z1=-6.3)
    # --- 広場：南の 2 つの外灯の台の横に鉢植え（外灯の台にくっつける）
    d.snug("pot_succulent", 0, x1=12.15, z=-7.5)        # W2-05b の鉢植え（多肉）
    d.snug("planter", 0, x0=-12.15, z=-7.5)
    # --- 広場：東の脇（雑貨屋との間）に樽と鉢植えの角、西の脇（食堂の東の面）に木箱と樽
    d.snug("planter_big", 0, x0=14.4, z1=9.2)
    d.snug("barrel", 0, x0=15.77, z1=9.2)
    d.snug("cc0/cask", 0, x0=15.77, z1=8.48)
    d.snug("crate", 0, x0=-14.98, z0=2.2)
    d.snug("barrel", 0, x0=-14.98, z0=3.16)
    d.snug("crate", 2, y=0.74, x0=-14.94, z0=2.24, scale=0.8)
    # --- 食堂の前：東の角の樽の横に鉢植え（西の角の木箱の上に積むと、上から食堂の角の方へ下りた体が角と箱の間に挟まった）
    d.snug("planter", 0, x1=-14.57, z0=-1.3)
    d.snug("goods_sacks", 0, x0=-13.83, z0=-0.35)
    # 食堂の東の面（広場から見える白い壁）と工房の西の面に垂れ幕（壁から 0.08 m の薄い物）
    for z in (1.7, 5.0):
        d.put("goods_cloth_wall", [-15.0, 3.6, z], 90)
    d.put("goods_cloth_wall", [-41.0, 3.8, 8.5], 270)
    # 食堂の丸い札（W2-05b の 10。鉢と湯気の絵、文字なし）：東の面の 2 枚の布の間に平らに
    d.put("sign_round", [-15.0, 2.75, 3.35], 90)
    # --- ヤーナの工房の前：西に作業台（台・タンク・踏み台・携行灯）、東に部品の山（ガラクタの山と曲がり管）。
    # 入口の前（目印 from_workshop と工房の口）と、工房の見える向きの真ん中は空ける
    d.snug("stall_table", 0, x0=-40.2, z0=0.4)
    d.put("hand_lantern", [-39.65, 0.97, 0.8], solid=True)
    d.snug("tank", 0, x0=-38.16, z0=0.6)
    d.snug("stool", 0, x1=-40.22, z0=0.4)
    d.snug("junk_pile", 0, x0=-30.0, z0=0.3)
    d.snug("pipe_bend", 0, x0=-28.01, z0=0.6)
    d.snug("sign_stand", 180, x1=-30.02, z0=0.3)          # W2-05b の立て札（レンチの絵）。ガラクタの山の西にくっつける
    # --- 広場の奥：壇の脇（天幕との間）に祭りの支度の木箱と樽（壇と天幕の柱から 0.75 m 以上）
    d.snug("crate", 0, x0=4.78, z0=10.62)
    d.snug("barrel", 0, x0=4.78, z0=11.58)
    d.snug("cc0/cask", 0, x0=5.5, z0=11.58)
    d.snug("cc0/plank_box", 90, x1=-4.78, z0=10.62)
    d.snug("crate", 0, x1=-5.5, z0=10.62, scale=0.85)
    # --- 北の階段の上に洗濯物（階段の両側の棟の面 |x|=4 から面へ。布の下の端は、その下の段から跳んで頭が届く高さより上：
    # z 17.4 の段は 0.6 m で頭は 4.4 m まで、布の下の端は 4.7 m。広場の看板「広場」の文字より下に見える高さ）
    d.put("laundry_goods_8", [0, 5.6, 17.4])
    d.put("laundry_goods_8", [0, 6.3, 19.8])
    # --- 工房と食堂の間の路地に洗濯物（壁から壁へ、頭の上 2.5 m より高い）
    d.put("laundry_goods", [-26.0, 3.3, 4.7])
    d.put("laundry_goods", [-26.0, 3.55, 7.3])
    # --- 西の端（工房の西の面と低い壁の間）：暮らしの角。洗濯綱、壁ぎわにタンク、北の角に木箱と樽と鉢植え
    d.put("clothesline", [-45.5, 0, 11.0], 0)       # 西の端の見晴らしの所（x -46.6, z 6）のカメラの前を空ける
    d.snug("tank", 90, x1=-41.02, z0=1.2)
    d.snug("crate", 0, x0=-47.98, z1=13.6)
    d.snug("planter", 0, x0=-47.02, z1=13.6)
    d.snug("barrel", 0, x0=-46.1, z1=13.6)
    d.snug("cc0/cask", 0, x0=-47.98, z1=12.64)
    # --- 南の胸壁の縁：係留柱（鉢植えの間）と、外を向いたベンチ（胸壁・低い壁の帯から 0.8 m。間に体が落ちて挟まらない）
    for x in (-44.6, -25.0, 15.0, 39.6):
        d.snug("bollard", 0, x=x, z0=-13.87)
    for x in (-33.0, 27.0):
        d.snug("bench", 180, x=x, z0=-13.09)
    d.snug("bench", 270, x0=-47.09, z=-8.0)


def corner(d, x, z, ends):
    """胸壁・低い壁の角の柱（parapet_corner）と、角へ来る手すりの端から柱の真ん中までの体だけの箱（手すりの線をつなぐ）。
    ends：{'-x': 端までの距離, …}（手すりが来る向きと、手すりの端から柱の真ん中までの m）。
    前は手すりが柱の手前 0.5 m で終わり、手すりの上から角へ下りると、2 本の手すりの端と柱の間に体の丸い底が挟まって宙に止まった"""
    boxes = [dress_solid.B(-0.71, 0.71, -8.2, 0.04, -0.71, 0.71)]
    for side, L in ends.items():
        L = L + 0.1
        if side == '-x':
            boxes.append(dress_solid.B(-L, 0.07, 0.0, 0.7, -0.07, 0.07, cam=False))
        elif side == '+x':
            boxes.append(dress_solid.B(-0.07, L, 0.0, 0.7, -0.07, 0.07, cam=False))
        elif side == '-z':
            boxes.append(dress_solid.B(-0.07, 0.07, 0.0, 0.7, -L, 0.07, cam=False))
        else:
            boxes.append(dress_solid.B(-0.07, 0.07, 0.0, 0.7, -0.07, L, cam=False))
    d.put("parapet_corner", [x, 1.2, z], solid=boxes)


# ---------------------------------------------------------------- 汚れの斑（42 章 14.2.1。汚れるべき所だけ濃く）

def dirt(d, x, z, sx, sz=None, y=0.0, yaw=0, kind="grime_patch"):
    """床の汚れの斑（town/grime_patch：床の 3 cm 上の板。真ん中ほど濃く、縁で消える）。sx・sz：広さ（m）。
    kind="oil_patch" は油じみ（工房・リフト・食堂の裏）。当たり判定・影は無い"""
    d.put(kind, [x, y, z], yaw, scale=[sx, 1, sz if sz is not None else sx])


def grime_mid(d):
    """中段の汚れの調整（2026-10-15、ユーザー：「汚れているべきところではこうだし、その辺の調整する前提だね」）。
    広場の真ん中は面 plaza を薄くし（キット）、汚れるべき所に斑を足す：食堂の前と裏、ジャンク屋のまわり、工房の入口、
    北と南の階段の足元、路地、露店の裏"""
    dirt(d, -20.0, -2.6, 9.0, 4.4)                       # 食堂の前（卓とベンチのまわり）
    dirt(d, -14.3, -0.8, 2.6, 2.4)                       # 食堂の東の角の樽
    dirt(d, -20.0, 10.6, 8.0, 2.6, kind="oil_patch")     # 食堂の裏口
    dirt(d, 38.0, 2.2, 8.0, 3.0)                         # ジャンク屋の台の前
    dirt(d, 41.6, -6.4, 4.2, 3.4, kind="oil_patch")      # ジャンク屋の木箱の山
    dirt(d, 43.6, 4.6, 3.0, 4.0)                         # ジャンク屋の東の脇
    dirt(d, -34.0, 0.6, 5.0, 3.0)                        # 工房の入口
    dirt(d, -39.0, 1.6, 3.4, 2.8, kind="oil_patch")      # 工房の前の作業台
    dirt(d, 0.0, 14.6, 7.0, 2.6)                         # 北の階段の足元
    dirt(d, 0.0, -13.2, 6.0, 2.2)                        # 南の階段の上り口
    dirt(d, -26.0, 6.0, 2.4, 6.0)                        # 工房と食堂の間の路地
    dirt(d, 30.5, 10.6, 3.4, 2.2)                        # 露店の間の裏
    dirt(d, 16.0, 9.2, 2.6, 2.4)                         # 広場の東の脇の樽


# ---------------------------------------------------------------- 下段（L1 住宅・L2 ハルの家・L3 訓練場の門・L4 昇降リフト・L5 禁足扉）

def lower(room):
    """下段：中段と同じ枠（96×30 m の床、北の 16 m の段の壁と階段、東西の低い壁、南の胸壁）。北の段々・階段・胸壁の手すりは中段と同じ部品。
    家の箱は当たり判定のまま白磁の壁（キット）で描き、面に town_rooms.lower_set の飾りを付ける。リフトの箱は描かず lower_set の昇降機。
    町の下のオルド（ORDO_POS：背の面は床の 1.5 m 下）。東の低い壁の口（z -8〜+1）の外は、オルドの左舷のリフトの踊り場（歩ける展望の台。
    x 48.5〜71・z -13〜+5、柵の外に脚 l2・l3 と 120 m 下の流れる砂の床が見える。当たり判定は部屋の形、見た目はオルド）"""
    d = Dress()
    common(room, d)
    G = lambda pos, size: geo_index(room, pos, size)  # noqa: E731
    roof = {"floor": "stone2", "wall": "graphite", "ceiling": "graphite"}
    # --- 地形の面：屋根の板、北の段の壁（家の塊が覆う）、階段、リフト（lower_set の昇降機が覆う）、禁足扉の奥
    for pos, size in (([-24, 6, 10.0], [12.6, 0.6, 8.6]), ([18, 6, 10.0], [10.6, 0.6, 8.6]), ([-12, 4.5, 9], [7.6, 0.5, 6.6])):
        G(pos, size)["skin"] = roof
    for pos, size in (([-26.25, 0, 16.5], [43.5, 16, 1]), ([26.25, 0, 16.5], [43.5, 16, 1]),
                      ([-4.25, 0, 25], [0.5, 9, 18]), ([4.25, 0, 25], [0.5, 9, 18]), ([0, 0, 34.5], [9, 12, 1])):
        G(pos, size)["hide"] = True
    G([0, 0, 22], [8, 5, 12])["skin"] = {"floor": "floor", "wall": "riser"}
    for pos, size in (([42, 0, -9], [8, 0.3, 8]), ([38.3, 0, -12.7], [0.5, 6, 0.5]), ([45.7, 0, -12.7], [0.5, 6, 0.5]),
                      ([38.3, 0, -5.3], [0.5, 6, 0.5]), ([45.7, 0, -5.3], [0.5, 6, 0.5]), ([42, 6, -9], [8.5, 0.5, 8.5])):
        G(pos, size)["hide"] = True
    G([-48.5, 0, 0], [1, 10, 6])["skin"] = "graphite"            # 禁足扉の奥（扉が開くと見える暗い通路）
    for part in ("terrace_west", "terrace_east", "stair_gate"):
        d.put(part, [0, 0, 0])
    # lower_set の当たり判定（部屋の座標）：禁足扉の両脇の段の塔（扉の面 x=-42 から 0.45〜0.8 m 出る）、ハルの家の角の配管（体だけ）
    d.put("lower_set", [0, 0, 0], solid=[
        dress_solid.B(-42.0, -41.55, 0.0, 9.0, -5.4, -3.0), dress_solid.B(-42.0, -41.55, 0.0, 9.0, 3.0, 5.4),
        dress_solid.B(-41.55, -41.18, 0.0, 3.4, -5.3, -3.1), dress_solid.B(-41.55, -41.18, 0.0, 3.4, 3.1, 5.3),
        dress_solid.P(22.75, 5.85, 0.32, 0.0, 3.95),
        # 物置（C、高さ 4）の屋上は乗れない柱（東の低い壁の手すりの上 1.9 から跳ぶと屋上に乗れ、そこから洗濯屋（A）の屋上、
        # 北の段の通路の縁の乗れない柱の上へと渡れた。2026-10-15 の詰みの確かめ）
        dress_solid.B(44.0, 48.0, 4.0, 6.4, 1.0, 7.0, cam=False, nogo=True)])
    ordo(room, d, "lower")
    # --- 北の階段（中段へ）：中段の北の階段と同じ手すり・段鼻・上り口の鉢植え
    d.put("stair_rail_12", [-4.0, 0, 16.0], solid="town/stair_rail_12_foot")
    d.put("stair_rail_12_r", [4.0, 0, 16.0], solid="town/stair_rail_12_r_foot")
    d.put("stair_treads_16", [0, 0, 22])
    for x in (-5.4, 5.4):
        d.put("planter", [x, 0, 13.95])
    # --- 南の胸壁（町の縁）と東の低い壁：上に真鍮の手すり、角の柱。外の面と下には何も付けない。
    # 西の低い壁と南の胸壁の西の端（x < -42）は禁足扉の門の塊の中。東の低い壁の z 1〜7 は物置（C）の面が付く（手すりを付けると、
    # 手すりと物置の面の間の 0.43 m に体が挟まる）
    for k in range(11):
        d.put("parapet_rail_8", [-38.0 + 8.0 * k, 1.2, -14.5])
    d.put("parapet_rail_4", [46.9, 1.2, -14.5], 0, scale=[0.45, 1, 1])
    # 東の低い壁の手すり：z -8〜+1 は踊り場への口（2026-10-16）、z 1〜7 は物置の面
    for z, sc in ((-11.0, 0.75), (8.75, 0.3125), (13.0, 0.75)):
        d.put("parapet_rail_8", [48.5, 1.2, z], 270, **({"scale": [sc, 1, 1]} if sc != 1.0 else {}))
    d.put("parapet_corner", [48.5, 1.2, 15.5])
    corner(d, 48.5, -14.5, {'-x': 0.7, '+z': 0.5})
    # --- 看板の板（浮いた文字の代わり。文字の位置は変えない）
    sign(room, "訓練場", "sign_wall_2", 180, 2.2)
    sign(room, "ハルの家", "sign_wall_2", 180, 2.2)
    sign(room, "昇降リフト（停止中）", "sign_post_3", 0, 3.0)
    # --- 南の胸壁の外灯（町の明かりを灯の芯へ。前は宙の 5 m）
    for (x, z), old in zip(((-34.0, -12.6), (-12.0, -12.6), (6.0, -12.6), (24.0, -12.6), (36.0, -12.6)),
                           ([-34, 5, -2], [-12, 5, 0], [0, 5, -2], [18, 5, 0], [36, 5, 0])):
        d.put("lamp_post", [x, 0, z], 0, scale=1.4)
        light(room, old, [x + 0.7, 2.15, z])
    # 禁足扉の赤い明かりは扉の前の上（前は扉の真ん前 1 m で、扉の面に丸い光の斑ができた）
    light(room, [-42, 4, 0], [-39.6, 7.0, 0.0], was=[[-41.0, 4.6, 0.0]])
    for p in room["props"]:
        if p.get("id") == "ch1.lower.gate":
            p["part"] = "town/gate_door"        # 扉の見た目（PropsView。開くと床へ沈む）
        if p.get("id") == "ch1.lower.lift":
            p["hide"] = True                    # 操作盤は lower_set（端末の箱と同じ所）
    lived_lower(d)
    grime_lower(d)
    return finish(room, d)


def flags(d, a, b, y, sag=None):
    """通りに渡す小旗の綱（town/bunting、長さ 10 m の部品を伸ばす）：a・b は両端の (x, z)、y は両端の高さ。真ん中は長さの 1/20 下がる"""
    import math
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    yaw = math.degrees(math.atan2(-dz, dx))
    sy = (sag if sag is not None else L / 20.0) / 0.8
    d.put("bunting", [(a[0] + b[0]) / 2, y, (a[1] + b[1]) / 2], round(yaw, 2), scale=[L / 10.0, sy, 1.0])


def lived_lower(d):
    """下段の暮らし（town_mood_day・town_facilities）：ハルの家の前のガラクタと鉢植え、訓練場の門の前の的の板と木箱、
    マーサの洗濯物、リフトの荷、胸壁の縁の係留柱とゲンのベンチ、禁足扉の前の柵の木箱。通り・戸口・住人・目印は空ける"""
    # ハルの家：巻き上げ戸の前にガラクタの山（ニコの立つ所から 1 m 後ろ）、右の窓の下に鉢植え、角の配管は体だけの柱
    d.snug("junk_pile", 0, x=14.7, z1=5.94)
    d.snug("planter", 0, x=21.2, z1=5.98)
    # ニコの近く：木の玩具（番機の人形とこま。W2-05b の 14）をガラクタの山の西にくっつける（ニコから 1.3 m）
    d.snug("toy_banki", 0, x1=13.69, z0=4.47)
    # 訓練場の門：左に樽と木箱、右に練習用の銃の棚（工具棚）
    d.snug("barrel", 0, x1=-26.2, z1=5.98)
    d.snug("crate", 0, x1=-27.0, z1=5.98)
    d.snug("crate", 3, y=0.74, x1=-27.04, z1=5.94, scale=0.8)
    d.snug("tool_rack", 180, x0=-21.6, z1=5.98)
    # 住宅（L1）：窓の下のベンチ（背を壁に）、扉の横の鉢植え
    d.snug("bench", 180, x=-10.75, z1=5.98)
    d.snug("planter", 0, x1=-14.62, z1=5.98)
    d.put("sign_cloth", [-12.35, 3.3, 6.0], 180)           # 宿の布札（W2-05b の 10。家の絵、文字なし。壁から 0.08 m）
    # マーサの洗濯屋（A の正面 z=3）：洗濯綱 2 本と籠（麻袋）・たらい（樽）。マーサ（30, 3）の前は空ける
    d.put("clothesline", [26.0, 0, 0.6], 0)
    d.put("clothesline", [26.0, 0, -1.6], 0)
    d.snug("laundry_basket", 0, x=23.0, z=-0.5)          # 洗濯かご（W2-05b の 15。前は麻袋で代わりにしていた）
    d.put("goods_cloth", [29.4, 0, -1.6], 0)              # 布を干す枠（W2-05b の 04。洗濯綱の東、マーサの前の通りは空ける）
    d.put("wind_flag", [30.6, 5.0, 3.6], 0, solid=False)  # 洗濯屋の屋上の風の旗（W2-05b の 16。屋上は届かない高さ 5 m なので当たり判定なし）
    d.snug("barrel", 0, x1=37.94, z1=2.98)
    d.snug("cc0/cask", 0, x1=37.2, z1=2.98)
    # リフト：床の上の荷（停止したまま）と、東の壁ぎわの木箱
    d.snug("crate", 0, x=43.6, z=-11.4, y=0.3)
    d.snug("crate", 4, x=43.75, z=-11.35, y=1.04, scale=0.8)
    d.snug("cc0/plank_box", 90, x=40.6, z=-11.6, y=0.3)
    d.snug("barrel", 0, x=44.9, z=-9.6, y=0.3)
    d.snug("crate", 0, x1=47.86, z0=-12.9)
    d.snug("crate", 0, x1=47.86, z0=-11.94)
    d.snug("goods_sacks", 90, x1=47.86, z0=-10.0)
    # 東の物置（C）の前：樽と木箱
    d.snug("barrel", 0, x0=44.1, z1=0.95)
    # 南の胸壁の縁：係留柱、ゲンのベンチ（外を向く）、外灯の横の鉢植え
    for x in (-40.0, -22.0, 14.0, 30.0, 44.0):
        d.snug("bollard", 0, x=x, z0=-13.87)
    d.snug("bench", 180, x=-9.4, z0=-13.09)
    d.snug("bench", 180, x=20.0, z0=-13.09)
    for x in (-36.0, 27.2):
        d.put("planter", [x, 0, -13.2])
    # 禁足扉の前（北と南の門の塊の前）：通行止めの木箱と樽（ヤーナの立つ所・扉の前は空ける）
    d.snug("crate", 0, x0=-41.98, z0=6.4)
    d.snug("barrel", 0, x0=-41.98, z0=7.36)
    d.snug("crate", 2, x0=-41.98, z1=-6.4)
    d.snug("cc0/cask", 0, x0=-40.96, z1=-6.4)
    # 壁の垂れ幕（訓練場の門の西の面、東の棟 B の正面）
    d.put("goods_cloth_wall", [-30.0, 4.2, 10.0], 270)
    d.put("goods_cloth_wall", [41.0, 5.6, 7.0], 180)
    # 小旗の綱（家の角から北の段の擁壁の面へ、洗濯屋からハルの家へ。どれも端は壁・屋根の縁に付き、いちばん低い所でも 5 m より上）
    flags(d, (12.7, 5.8), (8.2, 15.95), 6.4)
    flags(d, (-17.7, 5.8), (-8.2, 15.95), 6.4)
    flags(d, (29.9, 2.95), (23.3, 5.8), 5.4, sag=0.4)


def grime_lower(d):
    """下段の汚れ：戸口・階段の足元・路地・リフト・禁足扉の前・洗濯屋の前（水はね）"""
    dirt(d, -24.0, 5.0, 5.0, 3.2)           # 訓練場の門
    dirt(d, 18.0, 5.0, 4.4, 3.2)            # ハルの家の戸口
    dirt(d, 14.7, 4.6, 3.2, 2.2, kind="oil_patch")   # 巻き上げ戸の前のガラクタ
    dirt(d, -13.6, 5.2, 2.4, 2.0)           # 住宅の扉
    dirt(d, 34.0, 2.0, 4.0, 2.6)            # 洗濯屋の戸口
    dirt(d, 26.0, -0.5, 4.0, 4.4)           # 洗濯物の下（水はね）
    dirt(d, 0.0, 14.6, 7.0, 2.6)            # 北の階段の足元
    dirt(d, 42.0, -3.8, 6.0, 2.4, kind="oil_patch")  # リフトの前
    dirt(d, 47.0, -9.0, 2.0, 7.0)           # リフトの横の壁ぎわ
    dirt(d, -39.0, 0.0, 4.0, 9.0)           # 禁足扉の前
    dirt(d, -24.0, 15.0, 12.0, 1.8)         # 訓練場の門の裏の路地
    dirt(d, 18.0, 15.0, 10.0, 1.8)          # ハルの家の裏の路地
    dirt(d, 41.0, 15.6, 6.0, 1.2)           # 東の棟の裏
    dirt(d, 46.0, 10.0, 2.4, 8.0)           # 東の棟と東の壁の間の路地
    dirt(d, 46.0, 0.2, 3.0, 1.8)            # 物置の戸口


# ---------------------------------------------------------------- 上段（U1 町長の家・U2 回収屋ギルド・U3 展望台）

def upper(room):
    """上段：汚れの弱いキット（town_tidy：上の段の手入れされた家並み）。南の階段まわりは中段の南の階段と同じ形なので同じ部品
    （stair_well_s・手すり・段鼻）。家の箱は白磁の壁のまま、面に town_rooms.upper_set の飾り。展望台の床は板張り、望遠鏡の台は
    upper_set の台（箱は描かない）。遠景のオルドの体は置かない（展望台から北の地平線の章末の場面：カランの影を隠さない）"""
    d = Dress()
    common(room, d)
    room["kit"] = "town_tidy"
    G = lambda pos, size: geo_index(room, pos, size)  # noqa: E731
    roof = {"floor": "stone2", "wall": "graphite", "ceiling": "graphite"}
    G([-22, 7, 8.5], [14.6, 0.6, 9.6])["skin"] = roof
    G([20, 8, 8.5], [16.6, 0.6, 9.6])["skin"] = roof
    G([0, -5, -20], [8, 5, 12])["skin"] = {"floor": "floor", "wall": "riser"}
    G([0, -2, 22], [16, 2, 12])["skin"] = {"floor": "wood", "wall": "stone2"}
    G([0, 0, 24], [1.6, 1.2, 1.6])["hide"] = True                 # 望遠鏡の台（upper_set の台が同じ所）
    # 展望台の縁の低い壁の上の手すり（体だけの箱）と、南の角の旗竿
    d.put("upper_set", [0, 0, 0], solid=[
        dress_solid.B(-8.47, -8.33, 1.2, 1.9, 16.4, 28.4, cam=False), dress_solid.B(8.33, 8.47, 1.2, 1.9, 16.4, 28.4, cam=False),
        dress_solid.B(-8.4, 8.4, 1.2, 1.9, 28.33, 28.47, cam=False),
        dress_solid.P(-8.4, 16.6, 0.16, 1.2, 5.6), dress_solid.P(8.4, 16.6, 0.16, 1.2, 5.6)])
    # --- 南の階段（中段へ）：中段の南の階段と同じ両側の棟・手すり・段鼻・上り口の背の高い外灯
    d.put("stair_well_s", [0, 0, 0])
    d.put("stair_rail_12", [-4.0, -5.0, -26.0])
    d.put("stair_rail_12_r", [4.0, -5.0, -26.0])
    d.put("stair_treads_16", [0, -5.0, -20])
    d.put("lamp_tall", [-5.4, 0, -12.9])
    d.put("lamp_tall", [5.4, 0, -12.9], 180)
    light(room, [0, 5, -8], [4.85, 3.92, -12.9])
    # --- 胸壁：南（階段の両側）・北（展望台の両側）・東西の低い壁の手すりと角の柱。外の面と下には何も付けない
    for sx in (-1, 1):
        for x in (8.5, 16.5, 24.5, 32.5):
            d.put("parapet_rail_8", [sx * x, 1.2, -14.5])
        d.put("parapet_rail_4", [sx * 38.25, 1.2, -14.5], 0, scale=[0.875, 1, 1])
        for x in (12.0, 20.0, 28.0, 36.0):
            d.put("parapet_rail_8", [sx * x, 1.2, 16.5], 180)
        yaw = 90 if sx < 0 else 270
        for z in (-10, -2, 6):
            d.put("parapet_rail_8", [sx * 40.5, 1.2, z], yaw)
        d.put("parapet_rail_8", [sx * 40.5, 1.2, 13.0], yaw, scale=[0.75, 1, 1])
        inner = '-x' if sx > 0 else '+x'
        corner(d, sx * 40.5, 16.5, {inner: 0.5, '-z': 0.5})
        corner(d, sx * 40.5, -14.5, {inner: 0.5, '+z': 0.5})
    # --- 看板の板
    sign(room, "町長の家", "sign_wall_2", 180, 2.2)
    sign(room, "回収屋ギルド", "sign_wall_3", 180, 3.0)
    # --- 戸口の外灯（町の明かりを灯の芯へ）と展望台の灯
    d.put("lamp_tall", [-25.4, 0, 2.4])
    d.put("lamp_tall", [17.0, 0, 2.4])
    light(room, [-22, 5, -2], [-24.85, 3.92, 2.4])
    light(room, [20, 5, -2], [17.55, 3.92, 2.4])
    d.put("lamp_post", [-6.6, 0, 17.4], 0, scale=1.4)
    light(room, [0, 3, 22], [-5.9, 2.13, 17.4])
    lived_upper(d)
    grime_upper(d)
    return finish(room, d)


def lived_upper(d):
    """上段：手入れされた鉢植えとベンチ（外を向く）、ギルドの前の回収の箱、展望台の見張りの腰掛け。戸口・住人・望遠鏡は空ける"""
    # 町長の家：扉の両脇の鉢植え、窓の下のベンチ
    d.snug("pot_vine", 0, x1=-23.8, z1=3.98)              # W2-05b の鉢植え（つる・多肉。同じ鉢・同じ当たり判定）
    d.snug("pot_succulent", 0, x0=-20.2, z1=3.98)
    d.snug("planter_big", 0, x0=-28.9, z1=3.98)
    d.snug("bench", 180, x=-16.4, z1=3.98)
    # ギルド：丸い依頼板の下のベンチ、右の日よけの下の回収の箱（積んで紐で縛った箱・長持ち・樽）
    d.snug("bench", 180, x=15.2, z1=3.98)
    d.snug("crate", 0, x1=27.9, z1=3.98)
    d.snug("crate", 3, y=0.74, x1=27.86, z1=3.94, scale=0.8)
    d.snug("cc0/plank_box", 0, x1=26.94, z1=3.98)
    d.snug("barrel", 0, x0=21.9, z1=3.98)
    d.snug("junk_goods", 0, x0=22.62, z1=3.98)            # 回収の陳列箱（W2-05b の 09：部品を盛った箱と置物）
    # 南の胸壁の縁：鉢植えと外を向いたベンチ
    for sx in (-1, 1):
        for x in (10.0, 22.0, 34.0):
            d.put("planter", [sx * x, 0, -13.2])
        d.snug("bench", 180, x=sx * 16.0, z0=-13.09)
        d.snug("bench", 180, x=sx * 28.0, z0=-13.09)
    # 北の胸壁の縁（家の裏の向こう）：外を向いたベンチと鉢植え
    for sx in (-1, 1):
        d.snug("bench", 0, x=sx * 34.0, z1=15.09)
        d.snug("planter_big", 0, x=sx * 38.4, z1=15.55)
        d.snug("planter", 0, x=sx * 31.0, z1=15.87)
    # 東西の低い壁の前の鉢植え
    for sx in (-1, 1):
        for z in (-6.0, 4.0):
            d.put("planter", [sx * 39.2, 0, z])
    # 展望台：北の縁の前の外を向いたベンチ 2 つ、角の鉢植え、見張りの木箱と携行灯
    for x in (-4.6, 4.6):
        d.snug("bench", 0, x=x, z1=27.2)
    d.snug("planter", 0, x0=-7.98, z1=27.98)
    d.snug("planter", 0, x1=7.98, z1=27.98)
    d.snug("crate", 0, x0=-7.98, z=20.0)
    d.put("hand_lantern", [-7.51, 0.74, 20.0], solid=True)
    # 町長の家とギルドの間（広場の上）の小旗の綱
    flags(d, (-14.8, 4.2), (11.8, 4.2), 7.0, sag=1.2)
    flags(d, (-14.8, 12.8), (11.8, 12.8), 7.0, sag=1.2)


def grime_upper(d):
    """上段の汚れ：薄いキット（town_tidy）に、人の出入りの多い所だけ斑（ギルドの戸口と回収の箱のまわり、南の階段の上り口）"""
    dirt(d, 20.0, 3.0, 4.0, 2.4)            # ギルドの戸口
    dirt(d, 26.4, 3.0, 3.6, 2.0)            # 回収の箱
    dirt(d, 0.0, -13.2, 6.0, 2.0)           # 南の階段の上り口
    dirt(d, 0.0, -26.0, 6.0, 2.4)           # 南の階段の足元（踊り場）


# ---------------------------------------------------------------- 訓練場（L3）

def training(room):
    """訓練場：①〜⑤ の課題の形（黄色い床・段の台・的の柱・溝と斜面・残骸）は大きさをそのまま、読みやすく描く。
    黄色い床は面 paint、段の台は板張りの上と白磁の横、溝の底は砂、斜面は板。的の柱と残骸の箱は描かず、
    town_rooms.training_set の同じ大きさの的・残骸。壁の内の面に柱・帯・窓・垂れ幕、南の壁に入口の門、壁の向こうに家並み"""
    d = Dress()
    common(room, d)
    G = lambda pos, size: geo_index(room, pos, size)  # noqa: E731
    G([0, 0, -8], [7, 0.06, 3.4])["skin"] = "paint"
    for pos, size in (([0, 0, 0], [8, 1.0, 4]), ([0, 0, 6], [8, 1.8, 4])):
        G(pos, size)["skin"] = {"floor": "wood", "wall": "stone2"}
    G([0, -3.5, 28], [44, 2, 4])["skin"] = {"floor": "sand", "wall": "stone2"}
    for g in room["geometry"]:
        if g.get("t") == "ramp":
            g["skin"] = {"floor": "wood", "wall": "stone2"}
    for pos, size in (([-8, 0, 16], [0.5, 1.3, 0.5]), ([0, 0, 18], [0.5, 1.6, 0.5]), ([8, 0, 16], [0.5, 1.3, 0.5]),
                      ([-10, 0, 42], [3.4, 1.3, 2.4]), ([-9.2, 1.3, 42], [1.6, 0.8, 1.4]), ([9, 0, 46], [3.4, 1.3, 2.4]),
                      ([9.8, 1.3, 46], [1.6, 0.8, 1.4]), ([-3, 0, 51], [3.4, 1.3, 2.4]), ([-2.2, 1.3, 51], [1.6, 0.8, 1.4])):
        G(pos, size)["hide"] = True
    d.put("training_set", [0, 0, 0])
    # 吊り灯の綱の灯の芯へ町の明かりを（前は宙の 6 m。ほぼ同じ所）
    light(room, [-14, 6, -10], [-14.0, 6.05, -10.0])
    light(room, [14, 6, 10], [14.0, 6.05, 10.0])
    light(room, [0, 6, 40], [0.0, 5.85, 40.0])
    lived_training(d)
    grime_training(d)
    return finish(room, d)


def lived_training(d):
    """訓練場の道具と休む所：入口の西に練習用の銃の棚、東に見物のベンチ、四隅に木箱と樽と麻袋、的の前の砂袋。
    課題の通り道（段・的・溝の縁から 1.5 m・ニコ・出口・トリガー）は空ける"""
    # 入口の西（バートンの後ろ）：銃の棚 2 つと木箱
    d.snug("tool_rack", 90, x0=-21.98, z=-19.0)
    d.snug("tool_rack", 90, x0=-21.98, z=-21.1)
    d.snug("crate", 0, x0=-21.98, z0=-25.98)
    d.snug("crate", 0, x0=-21.02, z0=-25.98)
    d.snug("crate", 4, y=0.74, x0=-21.95, z0=-25.95, scale=0.8)
    d.snug("barrel", 0, x0=-21.98, z0=-25.02)
    # 入口の東：見物のベンチ（壁を背に）と水の樽
    d.snug("bench", 270, x1=21.98, z=-16.0)
    d.snug("bench", 270, x1=21.98, z=-12.0)
    d.snug("barrel", 0, x1=21.98, z0=-25.98)
    d.snug("cc0/cask", 0, x1=21.24, z0=-25.98)
    d.snug("goods_sacks", 0, x1=21.98, z0=-25.24)
    # 中ほどの壁ぎわ：見物のベンチと休みの木箱
    d.snug("bench", 90, x0=-21.98, z=6.0)
    d.snug("bench", 270, x1=21.98, z=2.0)
    d.snug("crate", 0, x1=21.98, z0=12.0)
    d.snug("cc0/plank_box", 90, x1=21.98, z0=13.0)
    # 溝の手前の四隅（溝の縁から 1.5 m より外）：木箱と樽
    d.snug("crate", 0, x0=-21.98, z1=24.0)
    d.snug("barrel", 0, x0=-21.02, z1=24.0)
    # 北の奥の隅：片付けた残骸の置き場（木箱・ガラクタの山・麻袋）
    d.snug("junk_pile", 0, x0=-21.98, z1=55.98)
    d.snug("crate", 0, x0=-19.98, z1=55.98)
    d.snug("goods_sacks", 0, x1=21.98, z1=55.98)
    d.snug("barrel", 0, x1=21.98, z1=55.22)
    d.snug("cc0/plank_box", 0, x1=20.6, z1=55.98)


def grime_training(d):
    """訓練場の汚れ：入口の門の前、的の足元、溝の着地の所、残骸のまわり（油）、壁の足元の隅"""
    dirt(d, 0.0, -24.0, 9.0, 3.0)           # 入口の門の前
    for x, z in ((-8.0, 16.0), (0.0, 18.0), (8.0, 16.0)):
        dirt(d, x, z - 0.3, 2.4, 2.0)       # 的の足元（撃った弾の焦げ・踏み跡）
    dirt(d, 0.0, 31.4, 16.0, 2.6)           # 溝を跳び越えた着地の所
    dirt(d, 0.0, 24.4, 12.0, 2.0)           # 溝の手前の踏み切り
    for x, z in ((-10.0, 42.0), (9.0, 46.0), (-3.0, 51.0)):
        dirt(d, x, z, 5.6, 4.6, kind="oil_patch")   # 残骸のまわり
    dirt(d, 0.0, 3.0, 9.0, 2.0)             # 段の台の間の踏み跡
    dirt(d, -20.6, -23.0, 3.0, 6.0)         # 入口の西の隅
    dirt(d, 20.6, 54.0, 3.0, 4.0)           # 北の奥の隅


# ---------------------------------------------------------------- 屋内（ハルの家・ヤーナの工房・回収屋ギルド・町長の家）

def interior(room, kit, set_part, hide, terminals=(), floor="floor_in"):
    """屋内の共通：キット、部屋の箱の面（床は継ぎ目のある白磁の板 floor_in）、geometry の家具の箱を描かず set_part の家具、
    端末の箱（調べる所）を描かない（"hide"：家具が同じ所にある。props_view）"""
    d = Dress()
    common(room, d)
    room["kit"] = kit
    G = lambda pos, size: geo_index(room, pos, size)  # noqa: E731
    for g in room["geometry"]:
        if g.get("t") == "shell":
            g["skin"] = {"floor": floor, "wall": "wall", "ceiling": "ceiling"}
    for pos, size in hide:
        G(pos, size)["hide"] = True
    for p in room["props"]:
        if p.get("type") == "terminal" and p.get("id") in terminals:
            p["hide"] = True
    return d, G


def home(room):
    """ハルの家：town_interiors の右（木箱のベッド・ガラクタの棚・父の写真・机・赤い敷物と布）。汚れは町の既定"""
    d, G = interior(room, "town", "home_set",
                    [([0, 0, -5.95], [3, 3.2, 0.2]), ([-5.5, 0, 3.75], [3.0, 0.6, 4.5]), ([-5.6, 0.6, 3.5], [1.2, 0.3, 1.6]),
                     ([3.5, 0, -2], [3, 0.9, 1.2]), ([5.5, 0, -4.5], [1.6, 2.2, 1.0]), ([-5.5, 0, -3], [1.2, 1.6, 2])],
                    terminals=("ch1.home.bed",))
    # 机の上の物（奥の半分）は乗れない柱（机に跳び乗ると本・灯の中に立った）
    d.put("home_set", [0, 0, 0], solid=[dress_solid.B(2.0, 5.0, 0.9, 5.6, -1.85, -1.4, cam=False, nogo=True)])      # 上の端は天井の板の中（扉の板の上 3.2 から跳んで届く 5.4 より上）
    sign(room, "ハルの家", "sign_wall_2", 0, 2.2)
    # ガラクタ（ハルが集めた物）：北東の隅のガラクタの山、西の壁ぎわの木箱、机の前の踏み台、東の窓の下の鉢植え
    d.snug("junk_pile", 0, x1=6.98, z1=5.98)
    d.snug("crate", 0, x0=-6.98, z0=-1.2)
    d.snug("crate", 3, y=0.74, x0=-6.95, z0=-1.17, scale=0.8)
    d.snug("cc0/cask", 0, x0=-6.98, z0=-0.24)
    d.snug("goods_basket", 0, x0=-6.98, z0=0.52)          # 実のかご（W2-05b の 01。ベッドの足元）
    d.snug("stool", 180, x=3.5, z0=-1.38)
    d.snug("planter", 0, x1=6.98, z1=-2.3)
    d.snug("goods_sacks", 0, x1=6.98, z0=4.0)
    dirt(d, 0.0, -4.6, 3.6, 2.2)            # 入口
    dirt(d, 5.6, 4.6, 2.6, 2.6, kind="oil_patch")   # ガラクタの山のまわり
    dirt(d, 3.5, -0.9, 2.4, 1.4)            # 机の前
    return finish(room, d)


def workshop(room):
    """ヤーナの工房：town_interiors の左（作業台と工具の板・万力・旋盤・部品の棚・炉・鎖）。汚れの強いキット（town_worn）に油じみ"""
    d, G = interior(room, "town_worn", "workshop_set",
                    [([0, 0, -6.95], [3, 3.2, 0.2]), ([-5, 0, 6], [6, 1.0, 1.6]), ([6, 0, 6.2], [4, 1.2, 1.2]),
                     ([-8.5, 0, 0], [1.4, 2.4, 6]), ([8.5, 0, -1], [1.4, 2.0, 5]), ([-5, 0, 5.0], [0.8, 1.1, 0.4])],
                    terminals=("ch1.workshop.bench",))
    # 作業台の上の物（奥）・旋盤の上は乗れない柱、炉（x 8.75〜10・z 2.55〜4.45・高さ 1.75）は箱、天井の鎖は体だけ
    d.put("workshop_set", [0, 0, 0], solid=[
        dress_solid.B(-8.0, -2.0, 1.0, 6.0, 6.3, 6.8, cam=False, nogo=True),
        dress_solid.B(8.75, 10.0, 0.0, 1.75, 2.55, 4.45)])
    sign(room, "ヤーナの工房", "sign_wall_3", 0, 3.0)
    light(room, [-6, 3, 4], [8.3, 1.0, 3.5])           # 橙の明かりは炉の口へ
    # 壁ぎわの道具と材料：樽・タンク・曲がり管・木箱・麻袋・ガラクタ
    d.snug("barrel", 0, x0=-9.98, z1=6.98)
    d.snug("tank", 90, x1=9.98, z0=-6.98)
    d.snug("pipe_bend", 0, x1=9.98, z0=-5.8)
    d.snug("crate", 0, x0=-9.98, z0=-6.98)
    d.snug("crate", 2, y=0.74, x0=-9.95, z0=-6.95, scale=0.8)
    d.snug("cc0/plank_box", 90, x0=-9.0, z0=-6.98)
    d.snug("goods_sacks", 0, x0=-8.28, z0=-6.98)
    d.snug("junk_pile", 0, x1=9.98, z0=4.6)
    d.snug("crate", 0, x1=3.98, z1=6.98)
    d.snug("barrel", 0, x1=3.02, z1=6.98)
    # 西の壁ぎわ（棚と作業台の間）：工具棚と木箱の山、東の壁ぎわ（棚と炉の間）：タンクと樽
    d.snug("tool_rack", 90, x0=-9.98, z1=6.26)
    d.snug("crate", 0, x0=-9.98, z1=-3.82)
    d.snug("crate", 3, y=0.74, x0=-9.95, z1=-3.86, scale=0.8)
    d.snug("tank", 90, x1=9.98, z0=1.62)
    d.snug("cc0/cask", 0, x1=9.98, z0=-5.24)
    # 南の壁ぎわ（入口の東）：部品の木箱と麻袋、壊れた機械の部品（ガラクタの山）
    d.snug("cc0/plank_box", 0, x0=3.0, z0=-6.98)
    d.snug("goods_sacks", 0, x0=4.5, z0=-6.98)
    d.snug("junk_pile", 0, x0=5.79, z0=-6.98)
    dirt(d, -5.0, 3.6, 7.0, 3.0, kind="oil_patch")     # 作業台と万力の前
    dirt(d, 6.0, 4.9, 5.0, 2.2, kind="oil_patch")      # 旋盤の前
    dirt(d, 8.0, 3.5, 2.6, 3.0, kind="oil_patch")      # 炉の前（煤）
    dirt(d, 0.0, -5.6, 3.6, 2.2)            # 入口
    dirt(d, 0.0, 1.0, 9.0, 6.0)             # 真ん中の踏み跡
    dirt(d, -7.0, 0.0, 1.6, 5.0)            # 西の棚の前
    return finish(room, d)


def guild(room):
    """回収屋ギルド：受付台・依頼板・地図・大きな歯車・回収品の棚・旗・吊り灯。汚れは町の既定（入口と受付の前に泥）"""
    d, G = interior(room, "town", "guild_set",
                    [([0, 0, -7.95], [3, 3.2, 0.2]), ([-7, 0, 7], [7, 1.1, 1.2]), ([0, 0, 6.5], [6, 1.1, 1.2]), ([7, 0, 7.6], [4, 2.4, 0.4]),
                     ([0, 0, 5.6], [0.6, 1.1, 0.6]), ([-3.25, 0, 6.75], [0.5, 1.1, 0.7]), ([7, 0, 7.1], [0.8, 1.2, 0.6])],
                    terminals=("ch1.guild.board",))
    # 東の壁の回収品の棚（x 11〜12・z -6.6〜-1.4・高さ 2.6）は箱
    d.put("guild_set", [0, 0, 0], solid=[dress_solid.B(11.0, 12.0, 0.0, 2.6, -6.6, -1.4)])
    sign(room, "回収屋ギルド", "sign_wall_3", 0, 3.0)
    # 待合のベンチ（西の壁ぎわ）、回収の木箱と樽（南東）、入口の鉢植え
    d.snug("bench", 90, x0=-11.98, z=-3.5)
    d.snug("bench", 90, x0=-11.98, z=0.5)
    d.snug("crate", 0, x0=-11.98, z0=-7.98)
    d.snug("crate", 3, y=0.74, x0=-11.95, z0=-7.95, scale=0.8)
    d.snug("barrel", 0, x0=-11.02, z0=-7.98)
    d.snug("cc0/plank_box", 90, x1=11.98, z0=-0.6)
    d.snug("junk_pile", 0, x1=11.98, z1=7.98)
    d.snug("junk_goods", 90, x0=-11.98, z0=2.3)           # 持ち込まれた回収品の陳列箱（W2-05b の 09）
    for x in (-3.0, 3.0):
        d.snug("planter", 0, x=x, z0=-7.98)
    dirt(d, 0.0, -6.6, 4.0, 2.4)            # 入口（泥の足跡）
    dirt(d, -4.0, 4.6, 9.0, 2.0)            # 受付の前
    dirt(d, 7.0, 5.6, 3.0, 2.0)             # 依頼板の前
    dirt(d, 10.0, -5.0, 2.6, 4.0, kind="oil_patch")    # 回収品のまわり
    return finish(room, d)


def mayor(room):
    """町長の家：大きな机・本棚・絵図・鉢植え・敷物。汚れの弱いキット（town_tidy）。汚れの斑は入口だけ、ごく薄く"""
    d, G = interior(room, "town_tidy", "mayor_set",
                    [([0, 0, -5.95], [3, 3.2, 0.2]), ([0, 0, 5], [5, 0.9, 1.4]), ([-5.5, 0, 0], [1.2, 2.2, 6])])
    d.put("mayor_set", [0, 0, 0])
    sign(room, "町長の家", "sign_wall_2", 0, 2.2)
    # 鉢植え（四隅と窓の間）、腰掛け（ベンチ 2 つを向かい合わせ）、収納箱
    d.snug("planter_big", 0, x1=6.98, z1=5.98)
    d.snug("planter_big", 0, x0=-6.98, z1=5.98)
    d.snug("pot_shrub", 0, x1=6.98, z0=-5.98)             # W2-05b の鉢植え（低木・つる。同じ鉢・同じ当たり判定）
    d.snug("pot_vine", 0, x0=-6.98, z0=-5.98)
    d.snug("planter", 0, x1=6.98, z=1.3)
    d.snug("bench", 270, x1=6.0, z=-2.6)
    d.snug("chest", 0, x0=3.6, z1=5.98)
    return finish(room, d)


# ---------------------------------------------------------------- 禁足扉の前室（遺構 B1 外殻層の入口。遺構のキット ruins_b1 の部品で）

R01_SIDES = {"s": ("z", 0), "n": ("z", 180), "w": ("x", 90), "e": ("x", 270)}


def r01(room):
    """禁足扉の前室（20×8×28 の殻、遺構 B1 外殻層の入口）：遺構 B1 のキット（ruins_b1）と部品（遺構の担当の部品を読むだけ）。
    壁の列（下 4 m は管つきと無地を交互、上 4 m は無地）、四隅の柱、両端の扉、天井の梁、壁の灯。
    箱（形）は白磁の板・黒鉛の面、柱は遺構の柱。ニコの隠れた隅（北東）に木箱と携行灯。トリガー（z -7.5〜-4.5）の中には当たり判定を置かない"""
    d = Dress()
    room["kit"] = "ruins_b1"
    G = lambda pos, size: geo_index(room, pos, size)  # noqa: E731
    for pos, size in (([0, 0, -13.9], [6, 4, 0.3]), ([0, 0, 13.9], [6, 4, 0.3])):
        G(pos, size)["hide"] = True
    for pos, size in (([-5, 0, 0], [2, 2.4, 2]), ([5.5, 0, 2], [2.4, 1.6, 2]), ([-6, 0, 7], [3, 1.2, 1.4]), ([7.5, 0, -6], [2, 1.2, 3])):
        G(pos, size)["skin"] = {"wall": "plate", "floor": "sandfloor"}
    G([0, 0, -5], [1.4, 3.4, 1.4])["hide"] = True
    X, Z = 10.0, 14.0

    def run(side, plane, a0, a1, y=0.0, plain=False):
        axis, yaw = R01_SIDES[side]
        n = int(round((a1 - a0) / 2.0)) + 1
        if plain:
            pos = [a0, y, plane] if axis == "z" else [plane, y, a0]
            d.put("ruins/b1_wall_plain", pos, yaw, count=n, step=[2.0, 0, 0] if axis == "z" else [0, 0, 2.0], solid=True)
            return
        for k, part in enumerate(("ruins/b1_wall", "ruins/b1_wall_plain")):
            c = (n - k + 1) // 2
            if c <= 0:
                continue
            a = a0 + 2.0 * k
            pos = [a, y, plane] if axis == "z" else [plane, y, a]
            kw = {"count": c, "step": [4.0, 0, 0] if axis == "z" else [0, 0, 4.0]} if c > 1 else {}
            d.put(part, pos, yaw, solid=True, **kw)

    for side, plane in (("w", -X), ("e", X)):
        run(side, plane, -13.0, 13.0)
        run(side, plane, -13.0, 13.0, y=4.0, plain=True)
    for side, plane in (("s", -Z), ("n", Z)):
        run(side, plane, -9.0, -5.0)
        run(side, plane, 5.0, 9.0)
        run(side, plane, -9.0, 9.0, y=4.0, plain=True)
        axis, yaw = R01_SIDES[side]
        d.put("ruins/b1_door", [0, 0, plane], yaw, scale=[3.0, 1.0, 1.0], solid=True)
        d.put("ruins/sand_door", [0, 0, plane], yaw, scale=[1.6, 1.0, 1.0])     # 戸口の砂（W2-06b の 03。真ん中の通り道は低い）
        for x in (-3.5, 3.5):
            d.put("ruins/b1_pillar", [x, 0, plane + (0.36 if side == "s" else -0.36)], 0, scale=[0.8, 1.0, 0.8], solid=True)
    for (x, z), yaw in (((-X, -Z), 0), ((-X, Z), 90), ((X, Z), 180), ((X, -Z), 270)):
        d.put("ruins/b1_corner", [x, 0, z], yaw, solid=True)
    # 天井の梁（8 m）と壁の上の管、壁の琥珀の灯（ニコの戦いのトリガーの中には当たり判定の灯を付けない）
    for z in (-10.0, -4.0, 2.0, 8.0):
        d.put("ruins/b1_beam_red" if z in (-4.0, 8.0) else "ruins/b1_beam", [-9.0, 8.0, z], 0, count=10, step=[2.0, 0, 0])
    for side, plane in (("w", -X), ("e", X)):
        axis, yaw = R01_SIDES[side]
        d.put("ruins/b1_pipe", [plane + (0.62 if side == "w" else -0.62), 7.1, -12.0], yaw, count=13, step=[0, 0, 2.0], scale=1.4)
        for z in (-11.0, 0.0, 10.5):
            d.put("ruins/b1_lantern", [plane + (0.3 if side == "w" else -0.3), 2.4, z], yaw, solid=True)
    # 真ん中の折れた柱（形 (0, 0, -5) 1.4×3.4×1.4 の代わり。当たり判定は形のまま）
    d.put("ruins/b1_pillar", [0, 0, -5], 0, scale=[2.33, 0.85, 2.33])
    # 床：砂の吹きだまりとかけら（トリガーの外）、排水格子
    for pos, yaw, sc in (((-7.5, 0, -11.0), 20, 1.2), ((7.0, 0, 11.4), -15, 1.3), ((-8.0, 0, 3.0), 90, 1.0), ((2.5, 0, 9.0), 40, 0.9),
                         ((8.4, 0, -11.5), 0, 1.0)):
        d.put("ruins/b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    for pos, yaw in (((-3.0, 0, 4.0), 30), ((3.4, 0, -10.5), -60), ((-7.4, 0, -1.2), 100)):
        d.put("ruins/b1_debris", pos, yaw, solid=True)
    for side, plane in (("w", -X), ("e", X)):
        axis, yaw = R01_SIDES[side]
        d.put("ruins/b1_grate", [plane + (0.5 if side == "w" else -0.5), 0, -8.0], yaw, count=3, step=[0, 0, 2.0])
    # ニコの隠れた北東の隅：木箱と布の箱、床の携行灯（ニコの明かり）、ケーブル
    W = X - 0.38
    d.snug("ruins/tarp_crate", 0, x1=W, z1=Z - 0.38)      # 布をかけた木箱（W2-06b の 14。前の布の箱と同じ箱）
    d.snug("ruins/b1_crate", 0, x1=W, z1=12.44)
    d.snug("town/crate", 3, y=1.04, x1=W - 0.06, z1=Z - 0.44, scale=0.8)
    d.put("town/hand_lantern", [6.6, 0, 8.3], solid=True)
    d.put("ruins/cable_floor", [7.2, 0, 6.0], 80)          # 床のケーブルの束（W2-06b の 07。前の b1_cables と同じ所）
    # 南西の隅：町から持ち込んだ物（禁足扉の見張りの名残）
    d.snug("town/crate", 0, x0=-W, z0=-Z + 0.38)
    d.snug("town/barrel", 0, x0=-W + 0.96, z0=-Z + 0.38)
    room["dress"] = d.items
    # 明かり：天井の青い外光はそのまま、ニコの携行灯の明かりを灯の上へ
    light(room, [6, 1.4, 8], [6.6, 0.9, 8.3])
    dress_solid.apply(room)
    return room


# ---------------------------------------------------------------- 夜明けの甲羅（オープニング）

def opening(room):
    """夜明けの甲羅：外殻の床（4 m の板の継ぎ目の面 hullplate）、縁の低い壁の上の真鍮の手すりと角の柱、点検口・通気口、北の縁の見張りの台。
    遠くの砂漠の箱（形）は描かない（キットの夜明けの空の絵の砂漠と遺跡が見える。当たり判定は残る）。
    始めの場面のカメラ（ch1.opening：96 m 前の空から北の地平線を見る）の前に物を置かない"""
    d = Dress()
    common(room, d)
    G = lambda pos, size: geo_index(room, pos, size)  # noqa: E731
    G([0, -2, 0], [40, 2, 40])["skin"] = {"floor": "hullplate", "wall": "stone2"}
    # 町の下のオルド：この台は船首の頭の上（ORDO_POS）。南を向くと背の町の全体（ordo_town）、北は船首の先と地平線
    ordo(room, d, "opening", back="ordo_town", ground=False)
    for pos, size in (([-80, -30, 160], [120, 34, 60]), ([70, -30, 210], [160, 38, 60]), ([0, -30, 320], [400, 44, 80])):
        G(pos, size)["hide"] = True
    # 縁の低い壁（1 m 厚、上 1.2）：手すりと角の柱（南は yaw 0、北は 180、西は 90、東は 270）
    for x in (-16.0, -8.0, 0.0, 8.0, 16.0):
        d.put("parapet_rail_8", [x, 1.2, -20.5])
        d.put("parapet_rail_8", [x, 1.2, 20.5], 180)
    for z in (-16.0, -8.0, 0.0, 8.0, 16.0):
        d.put("parapet_rail_8", [-20.5, 1.2, z], 90)
        d.put("parapet_rail_8", [20.5, 1.2, z], 270)
    for x in (-20.5, 20.5):
        for z in (-20.5, 20.5):
            corner(d, x, z, {('-x' if x > 0 else '+x'): 0.5, ('-z' if z > 0 else '+z'): 0.5})
    # 北の縁の旗竿（壁の上 1.2〜5.6 m：体だけの柱）
    d.put("opening_set", [0, 0, 0], solid=[dress_solid.P(-3.6, 20.3, 0.16, 1.2, 5.6), dress_solid.P(3.6, 20.3, 0.16, 1.2, 5.6)])
    # 見張りの台：外を向いたベンチ、木箱と携行灯、係留柱
    d.snug("bench", 0, x=-1.6, z1=19.09)
    d.snug("crate", 0, x0=1.2, z1=19.87)
    d.put("hand_lantern", [1.67, 0.74, 19.4], solid=True)
    for z in (-12.0, 4.0):
        d.snug("bollard", 90, x0=-19.87, z=z)
        d.snug("bollard", 270, x1=19.87, z=z)
    # 明かり：夜明けの外灯（北の 2 つは背の高い外灯の芯へ、真ん中は見張りの台の携行灯の上）
    d.put("lamp_tall", [-8.0, 0, 18.6])
    d.put("lamp_tall", [8.0, 0, 18.6], 180)
    light(room, [-8, 2, 14], [-7.45, 3.92, 18.6])
    light(room, [8, 2, 14], [7.45, 3.92, 18.6])
    dirt(d, 0.0, 18.0, 8.0, 3.0)            # 見張りの台の前
    return finish(room, d)


ROOMS = {"mid": mid, "lower": lower, "upper": upper, "training": training, "home": home, "workshop": workshop, "guild": guild,
         "mayor": mayor, "r01": r01, "opening": opening}


def main():
    data = json.load(open(PATH, encoding="utf-8"))
    names = sys.argv[1:] or list(ROOMS)
    for n in names:
        ROOMS[n](data["rooms"][n])
        solid = sum(1 for g in data["rooms"][n]["geometry"] if "dress" in g)
        print(f"{n}: dress {len(data['rooms'][n]['dress'])} 件・当たり判定の箱 {solid} 個")
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main()
