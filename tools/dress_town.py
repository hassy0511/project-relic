#!/usr/bin/env python3
"""オルド背町の部屋に、キット（"kit": "town"）と飾り（"dress"）・形の "skin" / "hide" を書き込む。出力：godot/content/areas/ch1_town.json

部屋の当たり判定（geometry の位置と大きさ）・目印・出口・トリガー・住人・置く物の位置は変えない。変えるのは見た目の項目だけ
（部屋の "kit"・"dress"・"lights" の位置、形の "skin"・"hide"、看板の "board"・"yaw"・"board_w"）。
何度流しても同じ結果になる（dress は毎回作り直す）。部品の寸法と原点：tools/blender/kit/town_parts.py・town_sets.py。
絵：W2-05 town_mood_day.png（中段の広場）・town_layout.png・town_mood_emergency.png（停止の夜）。

  python3 tools/dress_town.py            キットを付ける部屋（ROOMS）を全部
  python3 tools/dress_town.py mid        1 部屋だけ
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PATH = os.path.join(ROOT, "godot", "content", "areas", "ch1_town.json")


def r3(v):
    return [round(float(x), 3) for x in v]


class Dress:
    def __init__(self):
        self.items = []

    def put(self, part, pos, yaw=0, **kw):
        d = {"part": "town/" + part, "pos": r3(pos)}
        if yaw:
            d["yaw"] = yaw % 360
        for k, v in kw.items():
            d[k] = r3(v) if isinstance(v, (list, tuple)) else v
        self.items.append(d)
        return d


def geo_index(room, pos, size):
    """geometry の中から pos・size の一致する形を探す（番号で書くと、形を足したときにずれるため）"""
    for i, g in enumerate(room["geometry"]):
        if all(abs(a - b) < 1e-3 for a, b in zip(g.get("pos", []), pos)) and all(abs(a - b) < 1e-3 for a, b in zip(g.get("size", []), size)):
            return g
    raise KeyError(f"形が無い: {pos} {size}")


def light(room, old_pos, new_pos):
    for l in room.get("lights", []):
        if all(abs(a - b) < 1e-3 for a, b in zip(l["pos"], old_pos)) or all(abs(a - b) < 1e-3 for a, b in zip(l["pos"], new_pos)):
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
    for z in (22, -20):
        G([0, 0 if z > 0 else -5, z], [8, 5, 12])["skin"] = {"floor": "floor", "wall": "stone2"}
    for g in (G([-34, 7, 8.5], [14.6, 0.6, 9.6]), G([-20, 5.5, 5], [10.6, 0.5, 9.6])):
        g["skin"] = {"wall": "graphite", "floor": "rust", "ceiling": "graphite"}
    for x in (24, 38):
        G([x, 0, 3.8], [7, 1.1, 0.8])["skin"] = "wood"                  # 露店の台
        G([x, 0, 8.6], [7, 2.4, 1.0])["skin"] = "wood"                  # 露店の奥の箱
        G([x, 3.2, 6.3], [8, 0.25, 5.2])["hide"] = True                 # 露店の屋根（stall の帆布が覆う）
    G([-20, 0, 0.3], [4, 1.0, 1.2])["skin"] = "wood"                     # 食堂の配膳台
    for pos, size in (([30.5, 0, -6], [3, 1.0, 2]), ([42, 0, -7], [2, 1.6, 2]), ([-30, 0, -7], [2.5, 1.2, 2])):
        G(pos, size)["hide"] = True                                       # 木箱の山・ガラクタ（部品で置き換え）

    # --- 北の段の壁（高さ 16 m）：段々の町の正面。壁の面 z=16、正面は -Z（yaw 180）
    west = ["a", "b", "c", "d", "a"]
    east = ["b", "c", "a", "d", "b"]
    for k, x in enumerate((-44, -36, -28, -20, -12)):
        d.put("terrace_" + west[k], [x, 0, 16.0], 180)
    for k, x in enumerate((12, 20, 28, 36, 44)):
        d.put("terrace_" + east[k], [x, 0, 16.0], 180)
    for x in (-6.25, 6.25):
        d.put("terrace_4", [x, 0, 16.0], 180, scale=[0.875, 1, 1])

    # --- 北の階段（上の段へ）：手すりと、上り口の鉢植え・外灯
    d.put("stair_rail_12", [-4.0, 0, 16.0])
    d.put("stair_rail_12_r", [4.0, 0, 16.0])
    for x in (-5.4, 5.4):
        d.put("planter", [x, 0, 15.2])

    # --- 南の胸壁（下の段を見下ろす縁）：上に真鍮の手すり、外の面は擁壁、その下に下の段の家並み
    for sx in (-1, 1):
        for k, x in enumerate((8.5, 16.5, 24.5, 32.5, 40.5)):
            d.put("parapet_rail_8", [sx * x, 1.2, -14.5])
            d.put("retaining_" + "abcab"[k], [sx * x, -5.0, -15.0], 180)
        d.put("parapet_rail_4", [sx * 46.5, 1.2, -14.5])
        d.put("retaining_a", [sx * 46.5, -5.0, -15.0], 180, scale=[0.5, 1, 1])
    # 東西の低い壁（高さ 3.2、上の面 1.2）：手すりと、外の面の擁壁（背の面まで）
    for sx, yaw in ((-1, 90), (1, 270)):
        for z in (-10, -2, 6, 14):
            d.put("parapet_rail_8", [sx * 48.5, 1.2, z], yaw)
            d.put("retaining_" + ("b" if z in (-2, 14) else "a"), [sx * 49.0, -7.0, z], (yaw + 180) % 360)
    # 南の階段（下の段へ）：手すり、上り口の背の高い外灯 2 本
    d.put("stair_rail_12", [-4.0, -5.0, -26.0])
    d.put("stair_rail_12_r", [4.0, -5.0, -26.0])
    d.put("lamp_tall", [-5.4, 0, -13.4])
    d.put("lamp_tall", [5.4, 0, -13.4], 180, light={"at": [0.55, 3.92, 0], "color": "#ffc27a", "range": 14, "energy": 1.6})
    light(room, [0, 5, -10], [-4.85, 3.92, -13.4])

    # --- 下の段（胸壁の向こう、5 m 下）：床と家並み
    d.put("deck_slab", [0, -5.02, -36.0], shadow=False)
    for x, z, v, yaw in ((-40, -23, "a", 0), (-26, -22, "b", 180), (-14, -24, "c", 0), (14, -23, "a", 180), (26, -24, "c", 0),
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
    for x in (-10, -20, -30, -40, 10, 20, 34, 44):
        d.put("planter", [x, 0, -13.35], 0)
    # 木箱の山（隠した箱と同じ広さ・高さ）
    d.put("crate", [29.75, 0, -6], 0, scale=[1.65, 1.35, 2.2])
    d.put("crate", [31.25, 0, -6], 0, scale=[1.65, 1.35, 2.2])
    d.put("crate", [42, 0, -7], 0, scale=[2.2, 2.16, 2.2])
    d.put("junk_pile", [-30, 0, -7], 0, scale=[1.2, 1.05, 1.3])
    d.put("barrel", [27.6, 0, -6.4])
    d.put("barrel", [40.4, 0, -7.6], 0, scale=0.9)

    # --- ヤーナの工房（正面 z=4、入口の奥まり z=6）
    d.put("workshop_front", [-34, 0, 4.0], 180)
    sign(room, "ヤーナの工房", "sign_wall_3", 180, 3.0)
    light(room, [-34, 5, -2], [-36.0, 2.9, 3.4])

    # --- 食堂（正面 z=0.5）：日よけ・配膳の窓・屋根の看板、前に卓とベンチ
    d.put("diner_front", [-20, 0, 0.5], 180)
    sign(room, "食堂", "sign_roof_2", 180, 2.2)
    light(room, [-20, 5, -2], [-21.2, 2.6, -1.1])
    for x in (-24.6, -15.4):
        d.put("stall_table", [x, 0, -3.6], 90, scale=[1, 0.82, 1])
        d.put("bench", [x - 1.1, 0, -3.6], 90, scale=[1, 0.9, 1])
        d.put("bench", [x + 1.1, 0, -3.6], 270, scale=[1, 0.9, 1])
    d.put("barrel", [-14.2, 0, 0.0])
    d.put("crate", [-25.8, 0, 0.0], 15, scale=0.8)

    # --- 市場：露店 2 つ（屋根の箱の中心、正面 -Z）、台の上の品、奥の棚、看板、吊り灯の明かり
    for x, goods, shelf, text, board, bw in ((24, "goods_general", "goods_shelf_general", "雑貨屋", "sign_post_2", 2.2),
                                              (38, "goods_junk", "goods_shelf_junk", "ジャンク屋", "sign_post_3", 3.0)):
        d.put("stall", [x, 0, 6.3], 180)
        d.put(goods, [x, 1.1, 3.8], 180)
        d.put(shelf, [x, 0, 8.1], 180)
        sign(room, text, board, 180, bw)
        light(room, [x, 5, 2], [x - 2.0, 2.8, 3.7])
        d.put("barrel", [x - 4.6, 0, 4.4])
        d.put("chest", [x + 4.6, 0, 4.6], 200)
    d.put("tool_rack", [31, 0, 9.0], 180)
    d.put("clothesline", [31, 0, 11.5], 180)
    d.put("water_tower", [31, 0, 13.6], 0, scale=1.3)

    room["dress"] = d.items
    return room


ROOMS = {"mid": mid}


def main():
    data = json.load(open(PATH, encoding="utf-8"))
    names = sys.argv[1:] or list(ROOMS)
    for n in names:
        ROOMS[n](data["rooms"][n])
        print(f"{n}: dress {len(data['rooms'][n]['dress'])} 件")
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main()
