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
    """町の部屋に共通：遠景（オルドの体・脚・砂の床）。y は町の背の面の高さ"""
    room["kit"] = "town"


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
         "tank", "stool", "pipe_bend", "bollard", "hand_lantern", "cask", "plank_box", "sacks"}


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

    # --- 遠景：オルドの体と脚・砂の床（背の面は下の段の床の 1.5 m 下）
    d.put("ordo_far", [0, -6.5, 0], shadow=False)

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
    for x in (-24.6, -15.4):
        d.put("stall_table", [x, 0, -3.6], 90, scale=[1, 0.82, 1])
        d.put("bench", [x - 0.85, 0, -3.6], 90, scale=[1, 0.9, 1])
        d.put("bench", [x + 0.85, 0, -3.6], 270, scale=[1, 0.9, 1])
    d.put("barrel", [-14.2, 0, 0.0])
    d.put("crate", [-25.8, 0, 0.0], 4, scale=0.8)      # 向きは数度だけ（前は 15 度で、囲む当たり判定の箱が 0.25 m 手前で止めた）

    # --- 市場：露店 2 つ（屋根の箱の中心、正面 -Z）、台の上の品、奥の棚、看板、吊り灯の明かり
    for x, goods, shelf, text, board, bw in ((24, "goods_general", "goods_shelf_general", "雑貨屋", "sign_post_2", 2.2),
                                              (38, "goods_junk", "goods_shelf_junk", "ジャンク屋", "sign_post_3", 3.0)):
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
    d.snug("planter", 0, x1=18.9, z0=8.1)
    d.snug("sacks", 0, x1=17.07, z0=5.6)
    # 露店の間（工具棚の前）：配達の木箱の山と長持ち（工具棚と洗濯綱の前の通り道 x 31.4〜33 は空ける）
    d.snug("crate", 0, x0=29.6, z1=8.78)
    d.snug("crate", 2, y=0.74, x0=29.66, z1=8.76, scale=0.8)
    d.snug("cc0/plank_box", 90, x0=29.6, z1=7.82)
    # 東の端：小さな 3 つ目の店（天幕。中に台・木箱・樽）。ジャンク屋の収納箱と東の低い壁から 0.75 m 以上
    d.put("tent", [45.7, 0, 5.6], 270)
    d.snug("barrel", 0, x0=44.25, z1=2.95)
    d.snug("cc0/cask", 0, x0=44.97, z1=2.95)
    d.snug("sacks", 0, x0=45.69, z1=2.95)
    # 露店の間の前（どちらの露店の前でもない x 29.6〜32.5）：小さな出店の台（赤い掛け布と真鍮の壺）と、横に木箱と麻袋。
    # 露店の台の前（z 3.4）から 4 m 離して、市場の真ん中の通り道を空ける
    d.snug("stall_table", 0, x0=30.0, z1=-0.6)
    d.snug("crate", 2, x1=29.98, z1=-0.6, scale=0.85)
    d.snug("sacks", 0, x0=32.04, z1=-0.6)
    # 雑貨屋・ジャンク屋の裏（奥の箱の山の後ろ）：長持ちと樽
    d.snug("cc0/plank_box", 0, x0=22.6, z0=10.2)
    d.snug("cc0/cask", 0, x0=24.02, z0=10.2)
    d.snug("cc0/plank_box", 0, x0=36.4, z0=10.2)
    d.snug("barrel", 0, x0=37.82, z0=10.2)
    # 市場の南（前からの木箱の山の横）：樽と長持ち
    d.snug("cc0/cask", 0, x0=32.0, z1=-5.2)
    d.snug("cc0/plank_box", 90, x1=40.98, z1=-6.3)
    # --- 広場：南の 2 つの外灯の台の横に鉢植え（外灯の台にくっつける）
    for sx in (-1, 1):
        d.snug("planter", 0, **({"x1": 12.15} if sx > 0 else {"x0": -12.15}), z=-7.5)
    # --- 広場：東の脇（雑貨屋との間）に樽と鉢植えの角、西の脇（食堂の東の面）に木箱と樽
    d.snug("planter_big", 0, x0=14.4, z1=9.2)
    d.snug("barrel", 0, x0=15.77, z1=9.2)
    d.snug("cc0/cask", 0, x0=15.77, z1=8.48)
    d.snug("crate", 0, x0=-14.98, z0=2.2)
    d.snug("barrel", 0, x0=-14.98, z0=3.16)
    d.snug("crate", 2, y=0.74, x0=-14.94, z0=2.24, scale=0.8)
    # --- 食堂の前：東の角の樽の横に鉢植え（西の角の木箱の上に積むと、上から食堂の角の方へ下りた体が角と箱の間に挟まった）
    d.snug("planter", 0, x1=-14.57, z0=-1.3)
    d.snug("sacks", 0, x0=-13.83, z0=-0.35)
    # 食堂の東の面（広場から見える白い壁）と工房の西の面に垂れ幕（壁から 0.08 m の薄い物）
    for z in (1.7, 5.0):
        d.put("banner", [-15.0, 3.6, z], 90)
    d.put("banner", [-41.0, 3.8, 8.5], 270)
    # --- ヤーナの工房の前：西に作業台（台・タンク・踏み台・携行灯）、東に部品の山（ガラクタの山と曲がり管）。
    # 入口の前（目印 from_workshop と工房の口）と、工房の見える向きの真ん中は空ける
    d.snug("stall_table", 0, x0=-40.2, z0=0.4)
    d.put("hand_lantern", [-39.65, 0.97, 0.8], solid=True)
    d.snug("tank", 0, x0=-38.16, z0=0.6)
    d.snug("stool", 0, x1=-40.22, z0=0.4)
    d.snug("junk_pile", 0, x0=-30.0, z0=0.3)
    d.snug("pipe_bend", 0, x0=-28.01, z0=0.6)
    # --- 広場の奥：壇の脇（天幕との間）に祭りの支度の木箱と樽（壇と天幕の柱から 0.75 m 以上）
    d.snug("crate", 0, x0=4.78, z0=10.62)
    d.snug("barrel", 0, x0=4.78, z0=11.58)
    d.snug("cc0/cask", 0, x0=5.5, z0=11.58)
    d.snug("cc0/plank_box", 90, x1=-4.78, z0=10.62)
    d.snug("crate", 0, x1=-5.5, z0=10.62, scale=0.85)
    # --- 北の階段の上に洗濯物（階段の両側の棟の面 |x|=4 から面へ。布の下の端は、その下の段から跳んで頭が届く高さより上：
    # z 17.4 の段は 0.6 m で頭は 4.4 m まで、布の下の端は 4.7 m。広場の看板「広場」の文字より下に見える高さ）
    d.put("laundry_line_8", [0, 5.6, 17.4])
    d.put("laundry_line_8", [0, 6.3, 19.8])
    # --- 工房と食堂の間の路地に洗濯物（壁から壁へ、頭の上 2.5 m より高い）
    d.put("laundry_line", [-26.0, 3.3, 4.7])
    d.put("laundry_line", [-26.0, 3.55, 7.3])
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
    遠景：オルドの体（ordo_far）を床の 2 m 下に（中段から見た下の段の向こうの遠くの町は、南の胸壁の 25 m 先から）。
    胸壁の外と下には何も置かない（あとでオルドの体を町の下に置き、縁から脇腹と脚が見えるようにするため）"""
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
        dress_solid.P(22.75, 5.85, 0.32, 0.0, 3.95)])
    d.put("ordo_far", [0, -2.0, 20.0], shadow=False)
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
    for z, sc in ((-10.0, 1.0), (-2.5, 0.875), (11.0, 1.0)):
        d.put("parapet_rail_8", [48.5, 1.2, z], 270, **({"scale": [sc, 1, 1]} if sc != 1.0 else {}))
    for z in (15.5, -14.5):
        d.put("parapet_corner", [48.5, 1.2, z])
    # --- 看板の板（浮いた文字の代わり。文字の位置は変えない）
    sign(room, "訓練場", "sign_wall_2", 180, 2.2)
    sign(room, "ハルの家", "sign_wall_2", 180, 2.2)
    sign(room, "昇降リフト（停止中）", "sign_post_3", 0, 3.0)
    # --- 南の胸壁の外灯（町の明かりを灯の芯へ。前は宙の 5 m）
    for (x, z), old in zip(((-34.0, -12.6), (-12.0, -12.6), (6.0, -12.6), (24.0, -12.6), (36.0, -12.6)),
                           ([-34, 5, -2], [-12, 5, 0], [0, 5, -2], [18, 5, 0], [36, 5, 0])):
        d.put("lamp_post", [x, 0, z], 0, scale=1.4)
        light(room, old, [x + 0.7, 2.15, z])
    light(room, [-42, 4, 0], [-41.0, 4.6, 0.0])
    lived_lower(d)
    grime_lower(d)
    return finish(room, d)


def lived_lower(d):
    """下段の暮らし（town_mood_day・town_facilities）：ハルの家の前のガラクタと鉢植え、訓練場の門の前の的の板と木箱、
    マーサの洗濯物、リフトの荷、胸壁の縁の係留柱とゲンのベンチ、禁足扉の前の柵の木箱。通り・戸口・住人・目印は空ける"""
    # ハルの家：巻き上げ戸の前にガラクタの山（ニコの立つ所から 1 m 後ろ）、右の窓の下に鉢植え、角の配管は体だけの柱
    d.snug("junk_pile", 0, x=14.7, z1=5.94)
    d.snug("planter", 0, x=21.2, z1=5.98)
    # 訓練場の門：左に樽と木箱、右に練習用の銃の棚（工具棚）
    d.snug("barrel", 0, x1=-26.2, z1=5.98)
    d.snug("crate", 0, x1=-27.0, z1=5.98)
    d.snug("crate", 3, y=0.74, x1=-27.04, z1=5.94, scale=0.8)
    d.snug("tool_rack", 180, x0=-21.6, z1=5.98)
    # 住宅（L1）：窓の下のベンチ（背を壁に）、扉の横の鉢植え
    d.snug("bench", 180, x=-10.75, z1=5.98)
    d.snug("planter", 0, x1=-14.62, z1=5.98)
    # マーサの洗濯屋（A の正面 z=3）：洗濯綱 2 本と籠（麻袋）・たらい（樽）。マーサ（30, 3）の前は空ける
    d.put("clothesline", [26.0, 0, 0.6], 0)
    d.put("clothesline", [26.0, 0, -1.6], 0)
    d.snug("sacks", 0, x=23.9, z=-0.5)
    d.snug("barrel", 0, x1=37.94, z1=2.98)
    d.snug("cc0/cask", 0, x1=37.2, z1=2.98)
    # リフト：床の上の荷（停止したまま）と、東の壁ぎわの木箱
    d.snug("crate", 0, x=43.6, z=-11.4, y=0.3)
    d.snug("crate", 4, x=43.75, z=-11.35, y=1.04, scale=0.8)
    d.snug("cc0/plank_box", 90, x=40.6, z=-11.6, y=0.3)
    d.snug("barrel", 0, x=44.9, z=-9.6, y=0.3)
    d.snug("crate", 0, x1=47.86, z0=-12.9)
    d.snug("crate", 0, x1=47.86, z0=-11.94)
    d.snug("sacks", 90, x1=47.86, z0=-10.0)
    # 東の物置（C）の前：樽と木箱
    d.snug("barrel", 0, x0=44.1, z1=0.95)
    # 南の胸壁の縁：係留柱、ゲンのベンチ（外を向く）、外灯の横の鉢植え
    for x in (-40.0, -22.0, 14.0, 30.0, 44.0):
        d.snug("bollard", 0, x=x, z0=-13.87)
    d.snug("bench", 180, x=-9.4, z0=-13.09)
    d.snug("bench", 180, x=20.0, z0=-13.09)
    for x in (-36.0, 26.0):
        d.put("planter", [x, 0, -13.2])
    # 禁足扉の前（北と南の門の塊の前）：通行止めの木箱と樽（ヤーナの立つ所・扉の前は空ける）
    d.snug("crate", 0, x0=-41.98, z0=6.4)
    d.snug("barrel", 0, x0=-41.98, z0=7.36)
    d.snug("crate", 2, x0=-41.98, z1=-6.4)
    d.snug("cc0/cask", 0, x0=-40.96, z1=-6.4)
    # 壁の垂れ幕（訓練場の門の西の面、東の棟 B の正面）
    d.put("banner", [-30.0, 4.2, 10.0], 270)
    d.put("banner", [41.0, 5.6, 7.0], 180)


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


ROOMS = {"mid": mid, "lower": lower}


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
