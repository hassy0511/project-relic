#!/usr/bin/env python3
"""遺構の部屋に、キット（"kit"）と飾り（"dress"）・形の "skin" / "hide" を書き込む。出力：godot/content/areas/ch1_ruins.json

部屋の当たり判定（geometry の位置と大きさ）・目印・出口・トリガー・置く物は変えない。変えるのは見た目の項目だけ
（部屋の "kit"・"dress"・"lights"、形の "skin"・"hide"・"trim"）と、飾りの "solid" から作る描かない当たり判定の箱
（geometry の終わりの "dress" つきの形。tools/dress_solid.py）。何度流しても同じ結果になる（dress と solid の箱は毎回作り直す）。
書き方：docs/design/42_コンテンツの書き方.md 14 章。部品の寸法と原点：tools/blender/kit/ruins_b1.py。

  python3 tools/dress_ruins.py            キットを付ける部屋（ROOMS）を全部
  python3 tools/dress_ruins.py r02        1 部屋だけ
"""
import json
import os
import sys

import dress_solid

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PATH = os.path.join(ROOT, "godot", "content", "areas", "ch1_ruins.json")

# 壁の向き：内側の面の座標の軸、部品の yaw（正面を部屋の内側へ）、壁に沿った軸
SIDES = {"s": ("z", 0, "x"), "n": ("z", 180, "x"), "w": ("x", 90, "z"), "e": ("x", 270, "z")}


def r3(v):
    return [round(float(x), 3) for x in v]


class Dress:
    def __init__(self):
        self.items = []

    def put(self, part, pos, yaw=0, **kw):
        d = {"part": "ruins/" + part, "pos": r3(pos)}
        if yaw:
            d["yaw"] = yaw
        for k, v in kw.items():
            d[k] = r3(v) if isinstance(v, (list, tuple)) else v
        self.items.append(d)
        return d

    def row(self, part, pos, step, count, yaw=0, **kw):
        if count <= 0:
            return None
        if count == 1:
            return self.put(part, pos, yaw, **kw)
        return self.put(part, pos, yaw, count=count, step=step, **kw)

    def along(self, side, plane, a0, a1, part, y=0.0, off=0.0, every=2.0, yaw_add=0, **kw):
        """壁 side（内側の面が plane）に沿って、a0〜a1 に部品の中心を every ずつ並べる。off は壁から内側へのずれ"""
        axis, yaw, along = SIDES[side]
        n = int(round((a1 - a0) / every)) + 1
        inward = {"s": 1, "n": -1, "w": 1, "e": -1}[side]
        if axis == "z":
            pos = [a0, y, plane + inward * off]
            step = [every, 0, 0]
        else:
            pos = [plane + inward * off, y, a0]
            step = [0, 0, every]
        return self.row(part, pos, step, n, (yaw + yaw_add) % 360, **kw)

    def at_wall(self, side, plane, a, part, y=0.0, off=0.0, yaw_add=0, **kw):
        axis, yaw, along = SIDES[side]
        inward = {"s": 1, "n": -1, "w": 1, "e": -1}[side]
        pos = [a, y, plane + inward * off] if axis == "z" else [plane + inward * off, y, a]
        return self.put(part, pos, (yaw + yaw_add) % 360, **kw)

    def wall_run(self, side, plane, a0, a1, y=0.0):
        """壁の部品（2 m）を a0〜a1（中心）に、管つき・無地を交互に"""
        n = int(round((a1 - a0) / 2.0)) + 1
        axis = SIDES[side][0]
        st = [4.0, 0, 0] if axis == "z" else [0, 0, 4.0]
        for k, part in enumerate(("b1_wall", "b1_wall_plain")):
            c = (n - k + 1) // 2
            if c <= 0:
                continue
            a = a0 + 2.0 * k
            axis_, yaw, _ = SIDES[side]
            pos = [a, y, plane] if axis == "z" else [plane, y, a]
            self.row(part, pos, st, c, yaw)


def light(pos, color="#ffbc52", rng=8.0, energy=1.2):
    return {"pos": r3(pos), "color": color, "range": rng, "energy": energy}


# ---------------------------------------------------------------- 部屋ごと

def r02(room):
    """ジャンク溜まり（26×26×8 の殻）。南・北に出口の扉、東に近道エレベーター、西の壁に停止した大型ファン"""
    g = room["geometry"]
    # 形：0 殻、1 エレベーターの扉、2〜9 がらくたの山、10・11 折れた柱
    g[1]["skin"] = "metal"
    for i in (2, 4, 6, 7, 8, 9):
        g[i]["skin"] = {"wall": "plate", "floor": "sandfloor"}
    for i in (3, 5):
        g[i]["skin"] = {"wall": "metal", "floor": "floor"}
    for i in (10, 11):
        g[i]["hide"] = True
    d = Dress()
    H = 13.0
    # 壁の列（下の 4 m）。南・北は中央に 3 m の扉（1.5 倍）、東はエレベーターの枠、西はファン
    for side, plane in (("s", -H), ("n", H)):
        d.wall_run(side, plane, -12.5, -2.5)
        d.wall_run(side, plane, 2.5, 12.5)
        d.at_wall(side, plane, 0, "b1_door", scale=1.5)
        d.along(side, plane, -12.0, -2.0, "b1_grate", off=0.5, every=2.0)
        d.along(side, plane, 2.0, 12.0, "b1_grate", off=0.5, every=2.0)
    d.wall_run("e", H, -12.5, -4.5)
    d.wall_run("e", H, 4.5, 12.5)
    d.wall_run("w", -H, -12.5, -4.5)
    d.wall_run("w", -H, 4.5, 12.5)
    # 上の段（4〜8 m）も白磁の板と黒鉛の柱で（絵の高い外殻の壁）。割れ目・扉の上・ファンの上は空ける
    d.along("s", -H, 0.5, 12.5, "b1_wall_plain", y=4.0)
    d.along("s", -H, -12.5, -10.5, "b1_wall_plain", y=4.0)
    d.along("s", -H, -2.5, -2.5, "b1_wall_plain", y=4.0)
    d.along("n", H, -12.5, 4.5, "b1_wall_plain", y=4.0)
    d.along("n", H, 10.5, 12.5, "b1_wall_plain", y=4.0)
    d.along("w", -H, -12.5, -4.5, "b1_wall_plain", y=4.0)
    d.along("w", -H, 4.5, 12.5, "b1_wall_plain", y=4.0)
    # 角
    for (x, z), yaw in (((-H, -H), 0), ((-H, H), 90), ((H, H), 180), ((H, -H), 270)):
        d.put("b1_corner", [x, 0, z], yaw)
    # エレベーターの枠（形 1：x 12.4〜13、z -3〜3、高さ 4）
    for z in (-3.6, 3.6):
        d.put("b1_pillar", [12.6, 0, z], scale=[1, 1.15, 1], solid=True)
    d.row("b1_beam_red", [12.7, 4.6, -2.0], [0, 0, 2.0], 3, 90)
    d.at_wall("e", H, -2.4, "b1_redlight", y=2.0, off=0.6)
    d.at_wall("e", H, 2.4, "b1_redlight", y=2.0, off=0.6)
    # 西の壁の大型ファン（6×6 m）と前の排水格子
    d.at_wall("w", -H, 0, "b1_fan", y=0.9, scale=1.5, solid=True)       # 枠が壁から 0.7 m 出る（前は肩が枠に入った）
    d.along("w", -H, -3.0, 3.0, "b1_grate_red", off=0.0, every=2.0)
    # 上：東の壁の上の通路（届かない高さ 5.4 m）、天井の梁、北と南の壁の上の管
    d.row("b1_walkway", [12.0, 5.4, -12.0], [0, 0, 4.0], 7, 270)
    d.row("b1_walkway_lamp", [12.0, 5.4, -10.0], [0, 0, 4.0], 6, 270)
    # 通路の受け（4 m ごと。前は壁から通路が浮いて見えた）
    d.row("b1_bracket", [13.0, 5.4, -12.0], [0, 0, 4.0], 7, 270)
    for z in (-9.0, -3.0, 3.0, 9.0):
        d.row("b1_beam_red" if z in (-3.0, 9.0) else "b1_beam", [-12.0, 8.0, z], [2.0, 0, 0], 13)
    d.along("n", H, -12.0, 4.0, "b1_pipe", y=7.1, off=0.62, scale=1.4)
    d.along("s", -H, 0.0, 12.0, "b1_pipe", y=7.1, off=0.62, scale=1.4)
    d.along("w", -H, -12.0, -6.0, "b1_pipe", y=7.1, off=0.62, scale=1.4)
    d.along("w", -H, 6.0, 12.0, "b1_pipe", y=7.1, off=0.62, scale=1.4)
    # 外殻の割れ目（南の壁の上、西寄り）：外の光
    d.at_wall("s", -H, -6.5, "b1_crack", y=6.0, scale=[1.5, 1.0, 0.9])
    d.at_wall("s", -H, -6.5, "b1_shaft", y=6.2, off=0.1, shadow=False, scale=[1.4, 1.0, 1.0],
              light={"type": "spot", "at": [0, 0, 0.6], "dir": [0, -0.75, 0.66], "angle": 38, "range": 18, "energy": 7.0,
                     "color": "#ffd9a0", "shadow": True})
    d.at_wall("n", H, 7.5, "b1_crack", y=6.1, scale=[1.2, 1.0, 0.8])
    d.at_wall("n", H, 7.5, "b1_shaft", y=6.3, off=0.1, shadow=False, scale=[1.1, 1.0, 0.9])
    # 壁の琥珀の灯（柱の前）
    for side, plane, xs in (("s", -H, (-9.5, 9.5)), ("n", H, (-9.5, 9.5)), ("e", H, (-9.5, 9.5)), ("w", -H, (-9.5, 9.5))):
        for a in xs:
            d.at_wall(side, plane, a, "b1_lantern", y=2.4, off=0.42)
    # 折れた柱（形 10・11 の代わり）
    d.put("b1_pillar", [-5, 0, -1], scale=[2.33, 0.8, 2.33])
    d.put("b1_pillar", [5.5, 0, -2], scale=[2.0, 0.6, 2.0])
    # がらくた：箱・布・かけら・砂。角の箱は床に 1 段だけ、壁ぎわに寄せる（前は南西の角に 2 段に積んでいて、部屋の中から角へ向いて
    # 下がったカメラ（高さ約 1.9 m）が上の箱の中に入り、近くを網目に消す箱が画面の真ん中に大きな透けた塊に見えた）。
    # 箱はどれも当たり判定つき（solid。前は箱の中に入り込み、頭だけ出して立てた）。山の上の箱は、宝箱・遺物・ビー玉を取りに立つ所から
    # 0.5 m 以上離す（宝箱の山の上の段の北の縁にあった箱は、同じ山の低い段の北東の角へ。ビー玉の山の箱は北西の角へ寄せた）
    for pos, yaw, part in (((-11.8, 0, -11.85), 10, "b1_crate"), ((-10.6, 0, -11.95), -8, "b1_crate_cloth"), ((-11.9, 0, -10.65), 30, "b1_crate"),
                           ((11.8, 0, 11.8), 25, "b1_crate_cloth"), ((10.6, 0, 11.95), 0, "b1_crate"), ((11.95, 0, 10.6), 40, "b1_crate"),
                           ((-11.85, 0, 11.85), 15, "b1_crate"), ((11.8, 0, -11.8), -20, "b1_crate_cloth"),
                           ((-6.65, 1.0, -2.65), 10, "b1_crate"), ((7.9, 1.2, 4.0), -10, "b1_crate_cloth"), ((-9.98, 1.4, 7.98), 5, "b1_crate")):
        d.put(part, pos, yaw, solid=True)
    for pos, yaw, sc in (((-10.5, 0, -9.0), 30, 1.3), ((9.0, 0, 9.5), -20, 1.5), ((-6.5, 0, 9.5), 70, 1.2), ((10.5, 0, -6.0), 90, 1.4),
                         ((-2.0, 0, -11.5), 0, 1.6), ((4.5, 0, 11.4), 0, 1.4), ((-11.4, 0, 2.5), 90, 1.3), ((1.5, 0, 3.0), 45, 0.9),
                         ((-6.0, 0, -6.5), 10, 1.0), ((8.5, 0, 2.2), -30, 1.0)):
        d.put("b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    for pos, yaw in (((-3.5, 0, -2.5), 30), ((4.0, 0, -3.5), -60), ((-6.5, 0, 4.0), 100), ((10.0, 0, -10.2), 10), ((2.5, 0, 9.5), 200)):
        d.put("b1_debris", pos, yaw)
    room["kit"] = "ruins_b1"
    room["dress"] = d.items
    # 明かり：天井の 2 つ（暖かい外光）、割れ目から差す光、入口と出口の扉の灯、エレベーターの赤
    room["lights"] = [
        light([-6, 7, -3], "#ffd596", 18.0, 1.4), light([6, 7, 4], "#ffd596", 18.0, 1.4),
        light([7.5, 5.5, 10.5], "#ffd9a0", 12.0, 2.4),
        light([0, 3.2, 11.3], "#ffbc52", 9.0, 1.6), light([0, 3.2, -11.3], "#ffbc52", 9.0, 1.6),
        light([11.2, 3.0, 0], "#ff5a40", 7.0, 1.4),
    ]


def r03(room):
    """整備通路（幅 6・長さ 38・天井 5 の通路。床の段は穴をはさむ）"""
    g = room["geometry"]
    # 形：0〜3 壁、4 天井、5〜10 床の段（穴をはさむ）、11・12 箱
    for i in (11, 12):
        g[i]["skin"] = {"wall": "metal", "floor": "plate"}
    d = Dress()
    X = 3.0
    d.wall_run("w", -X, -18.0, 18.0)
    d.wall_run("e", X, -18.0, 18.0)
    # 角の柱（側の壁の端の柱が、両端の壁の板と同じ面で重なってちらついた所をふさぐ。r02 と同じ b1_corner）
    for (x, z), yaw in (((-X, -19.0), 0), ((-X, 19.0), 90), ((X, 19.0), 180), ((X, -19.0), 270)):
        d.put("b1_corner", [x, 0, z], yaw)
    # 両端の扉（南：r02 へ、北：r04 へ）
    for side, plane in (("s", -19.0), ("n", 19.0)):
        d.at_wall(side, plane, 0, "b1_door", scale=[1.5, 1.0, 1.2])
        d.at_wall(side, plane, -2.5, "b1_wall_plain")
        d.at_wall(side, plane, 2.5, "b1_wall_plain")
    # 天井の梁（4 m ごと、1 本おきに赤い灯）と壁の上の管
    for k, z in enumerate(range(-16, 17, 4)):
        d.row("b1_beam_red" if k % 2 else "b1_beam", [-2.0, 5.0, z], [2.0, 0, 0], 3)
    d.along("w", -X, -18.0, 18.0, "b1_pipe", y=4.22, off=0.3)
    d.along("e", X, -18.0, 18.0, "b1_pipe", y=4.22, off=0.3)
    # 穴：下に渡した管と、底の赤い灯。穴の下は縦穴（前は床の段の下で何も無く、灰色の空が見えた）
    for zc in (-12.25, -5.75, 1.25, 9.0, 14.75):
        d.row("b1_pipe", [-2.0, -1.4, zc], [2.0, 0, 0], 3)
    for z0, z1 in ((-13.0, -11.5), (-7.0, -4.5), (-0.5, 3.0), (7.5, 10.5), (13.5, 16.0)):
        d.put("b1_pit", [0, -2.5, (z0 + z1) / 2], scale=[1, 1, z1 - z0], shadow=False)
    # 穴の縁の目印：両側の壁ぎわに琥珀の灯の柱（跳ぶ所が遠くから分かる）
    for z0, z1 in ((-13.0, -11.5), (-7.0, -4.5), (-0.5, 3.0), (7.5, 10.5), (13.5, 16.0)):
        for z in (z0 - 0.25, z1 + 0.25):
            d.row("b1_post_lamp", [-2.3, 1.0 if 10.5 <= z <= 13.5 else 0.0, z], [4.6, 0, 0], 2)
    # 床の段の、壁ぎわの排水格子（段の上だけ）
    for z0, z1 in ((-18.0, -14.0), (-10.5, -8.0), (-3.5, -1.5), (4.0, 6.5), (17.0, 18.0)):
        d.along("w", -X, z0, z1, "b1_grate", off=0.5, every=2.0)
    # 壁の琥珀の灯と赤い非常灯
    for z in (-15.0, -3.0, 9.0):
        d.at_wall("w", -X, z, "b1_lantern", y=2.4, off=0.42)
    for z in (-9.0, 3.0, 15.0):
        d.at_wall("e", X, z, "b1_lantern", y=2.4, off=0.42)
    # 箱（当たり判定つき）・砂（壁ぎわ）。箱は南の扉の前、出口（z -19.4〜-17.4）と入ったときのトリガー（z -16〜-14）の間だけに置く。
    # 前は跳んで渡る段の上（着地する所・踏み切る所）と両端の出口の中にもあり、ハルが箱の中に入り込んだ。当たり判定を付けると跳ぶのが
    # 難しくなるので、段の上の箱はやめた（溝の縁の灯の柱も、着地・踏み切りの所にあるので当たり判定は付けない）
    for pos, yaw, part in (((2.4, 0, -16.7), -5, "b1_crate"), ((-2.4, 0, -16.7), 3, "b1_crate_cloth")):
        d.put(part, pos, yaw, solid=True)
    for pos, yaw, sc in (((-2.0, 0, -17.6), 0, 1.0), ((2.0, 0, -9.5), 90, 0.9), ((-2.1, 0, -1.2), 0, 0.8), ((2.0, 0, 4.0), 0, 0.9),
                         ((-1.8, 1.0, 11.0), 90, 0.7), ((1.8, 0, 17.2), 0, 0.9)):
        d.put("b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    room["kit"] = "ruins_b1"
    room["dress"] = d.items
    room["lights"] = [
        light([0, 4.2, -14], "#ffd596", 15.0, 2.0), light([0, 4.2, -2], "#ffd596", 15.0, 2.0), light([0, 4.2, 10], "#ffd596", 15.0, 2.0),
        light([0, -2.0, -5.75], "#ff4a3a", 5.0, 1.5), light([0, -2.0, 9.0], "#ff4a3a", 5.0, 1.5),
    ]


ROOMS = {"r02": r02, "r03": r03}


def main():
    want = sys.argv[1:] or list(ROOMS)
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    for rid in want:
        room = data["rooms"][rid]
        for s in room["geometry"]:
            for k in ("skin", "hide", "trim"):
                s.pop(k, None)
        ROOMS[rid](room)
        n = dress_solid.apply(room)
        print(rid, room["name"], "飾り", len(room["dress"]), "件・当たり判定の箱", n, "個")
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
