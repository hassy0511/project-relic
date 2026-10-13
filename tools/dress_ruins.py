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
import math
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

    def wall_run(self, side, plane, a0, a1, y=0.0, **kw):
        """壁の部品（2 m）を a0〜a1（中心）に、管つき・無地を交互に。当たり判定は壁の板の前の帯（dress_solid の LINER）"""
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
            self.row(part, pos, st, c, yaw, solid=True, **kw)


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
    # 壁の列（下の 4 m）。南・北は中央に 3 m の扉（1.5 倍）、東はエレベーターの枠、西はファン。
    # 壁の部品・扉・角の柱には、板の前の面に描かない壁の帯（当たり判定）を付ける（solid。前は柱が 0.4〜0.65 m 前へ出ていて、
    # 壁ぎわを歩くと体が柱・板の中に半分入った。部品の出っ張りは ruins_b1.RELIEF の 0.35 m までに減らした）
    for side, plane in (("s", -H), ("n", H)):
        d.wall_run(side, plane, -12.5, -2.5)
        d.wall_run(side, plane, 2.5, 12.5)
        d.at_wall(side, plane, 0, "b1_door", scale=1.5, solid=True)
        d.along(side, plane, -12.0, -2.0, "b1_grate", off=0.5, every=2.0)
        d.along(side, plane, 2.0, 12.0, "b1_grate", off=0.5, every=2.0)
    d.wall_run("e", H, -12.5, -4.5)
    d.wall_run("e", H, 4.5, 12.5)
    d.wall_run("w", -H, -12.5, -4.5)
    d.wall_run("w", -H, 4.5, 12.5)
    # 上の段（4〜8 m）も白磁の板と黒鉛の柱で（絵の高い外殻の壁）。割れ目・扉の上・ファンの上は空ける。山の上の箱から跳ぶと届くので帯も付ける
    d.along("s", -H, 0.5, 12.5, "b1_wall_plain", y=4.0, solid=True)
    d.along("s", -H, -12.5, -10.5, "b1_wall_plain", y=4.0, solid=True)
    d.along("s", -H, -2.5, -2.5, "b1_wall_plain", y=4.0, solid=True)
    d.along("n", H, -12.5, 4.5, "b1_wall_plain", y=4.0, solid=True)
    d.along("n", H, 10.5, 12.5, "b1_wall_plain", y=4.0, solid=True)
    d.along("w", -H, -12.5, -4.5, "b1_wall_plain", y=4.0, solid=True)
    d.along("w", -H, 4.5, 12.5, "b1_wall_plain", y=4.0, solid=True)
    # 角（0.5 m 角の柱）
    for (x, z), yaw in (((-H, -H), 0), ((-H, H), 90), ((H, H), 180), ((H, -H), 270)):
        d.put("b1_corner", [x, 0, z], yaw, solid=True)
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
    # 壁の琥珀の灯（柱の前。当たり判定つき）。角の箱から 3 m 離す（前は ±9.5 m で、角の箱に乗ると頭が灯の中に入った）
    for side, plane, xs in (("s", -H, (-7.5, 7.5)), ("n", H, (-7.5, 7.5)), ("e", H, (-7.5, 7.5)), ("w", -H, (-7.5, 7.5))):
        for a in xs:
            d.at_wall(side, plane, a, "b1_lantern", y=2.4, off=0.3, solid=True)
    # 折れた柱（形 10・11 の代わり）
    d.put("b1_pillar", [-5, 0, -1], scale=[2.33, 0.8, 2.33])
    d.put("b1_pillar", [5.5, 0, -2], scale=[2.0, 0.6, 2.0])
    # がらくた：箱・布・かけら・砂。角の箱は床に 1 段だけ、壁の帯（壁から 0.36 m）と角の柱にぴったり寄せ、向きは数度だけ振る。
    # 箱はどれも当たり判定つき（solid）。前は角の箱が壁から 0.3〜0.6 m 離れて 10〜40 度回っていて、
    #  - 箱に乗って角へ歩くと、箱と壁の間のすき間に落ちて両側の角に引っかかり、宙に浮いたまま出られなくなった
    #  - 回した箱を囲む当たり判定の箱が、見た目の箱の 0.25〜0.5 m 手前で体を止めた（見えない壁）
    # 箱と壁・柱の間に残る 0.14 m 以下のすき間は dress_solid がふさぐ。山の上の箱は、宝箱・遺物・ビー玉を取りに立つ所から 0.5 m 以上離す
    L = H - 0.36          # 壁の帯の面
    C = H - 0.5           # 角の柱の面
    for pos, yaw, part in (
            # 南西：西の壁ぎわ（柱の北）と南の壁ぎわ（柱の東）、西の壁ぎわにもう 1 つ
            ((-L + 0.52, 0, -C + 0.52), 2, "b1_crate"), ((-C + 0.05 + 0.58 + 0.52 + 0.52, 0, -L + 0.58), -3, "b1_crate_cloth"),
            ((-L + 0.52, 0, -C + 0.52 + 0.52 + 0.05 + 0.53), 182, "b1_crate"),
            # 北東：北の壁ぎわ（柱の西）に布の箱と箱、東の壁ぎわ（布の箱の南）に箱
            ((C - 0.58, 0, L - 0.58), 3, "b1_crate_cloth"), ((C - 0.58 - 0.58 - 0.05 - 0.52, 0, L - 0.53), 178, "b1_crate"),
            ((L - 0.53, 0, L - 1.16 - 0.05 - 0.52), 268, "b1_crate"),
            # 北西・南東：1 つずつ
            ((-L + 0.52, 0, C - 0.53), 92, "b1_crate"), ((L - 0.58, 0, -C + 0.58), -2, "b1_crate_cloth"),
            # 宝箱の山の低い段の箱：折れた柱の角から 0.76 m（前は 0.58 m で、箱の上から柱へ下りると箱の角と柱の角の間に挟まった）
            ((-6.62, 1.0, -2.9), 3, "b1_crate"), ((7.9, 1.2, 4.0), -3, "b1_crate_cloth"), ((-9.98, 1.4, 7.98), 2, "b1_crate")):
        d.put(part, pos, yaw, solid=True)
    for pos, yaw, sc in (((-10.5, 0, -9.0), 30, 1.3), ((9.0, 0, 9.5), -20, 1.5), ((-6.5, 0, 9.5), 70, 1.2), ((10.5, 0, -6.0), 90, 1.4),
                         ((-2.0, 0, -11.5), 0, 1.6), ((4.5, 0, 11.4), 0, 1.4), ((-11.4, 0, 2.5), 90, 1.3), ((1.5, 0, 3.0), 45, 0.9),
                         ((-6.0, 0, -6.5), 10, 1.0), ((8.5, 0, 2.2), -30, 1.0)):
        d.put("b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    # かけら（0.3 m 以下。当たり判定つきで、段差の乗り越えで上を歩く。前は 0.5 m の板が膝の高さで体を抜けた）
    # 折れた柱の角から 0.75 m 以上離す（前は (-3.5, -2.5) で柱の角とかけらの間に足が挟まった）
    for pos, yaw in (((-2.8, 0, -3.2), 30), ((4.0, 0, -3.5), -60), ((-6.5, 0, 4.0), 100), ((10.0, 0, -10.2), 10), ((2.5, 0, 9.5), 200)):
        d.put("b1_debris", pos, yaw, solid=True)
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
    # 壁の列と、板の前の描かない壁の帯（当たり判定。r02 と同じ。前は壁ぎわを歩くと柱が体の半分に入った）。通路の幅は帯の間で 5.3 m
    d.wall_run("w", -X, -18.0, 18.0)
    d.wall_run("e", X, -18.0, 18.0)
    # 角の柱（側の壁の端の柱が、両端の壁の板と同じ面で重なってちらついた所をふさぐ。r02 と同じ b1_corner）
    for (x, z), yaw in (((-X, -19.0), 0), ((-X, 19.0), 90), ((X, 19.0), 180), ((X, -19.0), 270)):
        d.put("b1_corner", [x, 0, z], yaw, solid=True)
    # 両端の扉（南：r02 へ、北：r04 へ）
    for side, plane in (("s", -19.0), ("n", 19.0)):
        d.at_wall(side, plane, 0, "b1_door", scale=[1.5, 1.0, 1.2], solid=True)
        d.at_wall(side, plane, -2.5, "b1_wall_plain", solid=True)
        d.at_wall(side, plane, 2.5, "b1_wall_plain", solid=True)
    # 天井の梁（4 m ごと、1 本おきに赤い灯）と壁の上の管。どちらも当たり判定つき（2.6 m の台の上に立つと頭が管に入った。台から跳ぶと梁を抜けた）
    for k, z in enumerate(range(-16, 17, 4)):
        d.row("b1_beam_red" if k % 2 else "b1_beam", [-2.0, 5.0, z], [2.0, 0, 0], 3, solid=True)
    d.along("w", -X, -18.0, 18.0, "b1_pipe", y=4.22, off=0.3, solid=True)
    d.along("e", X, -18.0, 18.0, "b1_pipe", y=4.22, off=0.3, solid=True)
    # 穴：下に渡した管と、底の赤い灯。穴の下は縦穴（前は床の段の下で何も無く、灰色の空が見えた）
    for zc in (-12.25, -5.75, 1.25, 9.0, 14.75):
        d.row("b1_pipe", [-2.0, -1.4, zc], [2.0, 0, 0], 3)
    for z0, z1 in PITS:
        d.put("b1_pit", [0, -2.5, (z0 + z1) / 2], scale=[1, 1, z1 - z0], shadow=False)
    # 穴の縁の目印：両側の壁の、穴の手前と向こうに琥珀の灯（跳ぶ所が遠くから分かる）。壁に付ける灯（b1_edge_lamp）で、壁の帯の内に収まる。
    # 前は壁から 0.7 m の床に立つ灯の柱で、当たり判定が無く体が柱を抜けた（付けると、跳んで着く所で体が柱に止められて穴に落ちる）。
    # 位置は穴の縁から 0.1〜1.0 m の、壁の板の継ぎ目の柱（奇数の z の ±0.23）と板の細い管を避けた所
    for z0, z1 in PITS:
        for edge, sgn in ((z0, -1), (z1, 1)):
            y = 1.0 if 10.5 <= edge <= 13.5 else 0.0
            for side, plane in (("w", -X), ("e", X)):
                d.at_wall(side, plane, edge_lamp_z(side, edge, sgn), "b1_edge_lamp", y=y)
    # 床の段の、壁ぎわの排水格子（段の上だけ）
    for z0, z1 in ((-18.0, -14.0), (-10.5, -8.0), (-3.5, -1.5), (4.0, 6.5), (17.0, 18.0)):
        d.along("w", -X, z0, z1, "b1_grate", off=0.5, every=2.0)
    # 壁の琥珀の灯（当たり判定つき）。穴の上と、穴の縁から 1.5 m（跳ぶ所）には付けない（跳んでいる体が灯に当たって止まり、穴に落ちる。
    # 前は z 9・3・15 が穴の上・縁にあった）。1.3 m・2.6 m の台（z -9.3〜-7.1）の横にも付けない（前は台の真横 z=-9 で、台に立つと頭が灯に入った）
    for z in (-15.0, -2.5, 5.25):
        d.at_wall("w", -X, z, "b1_lantern", y=2.4, off=0.3, solid=True)
    for z in (-15.0, 5.25, 17.62):
        d.at_wall("e", X, z, "b1_lantern", y=2.4, off=0.3, solid=True)
    # 箱（当たり判定つき）・砂（壁ぎわ）。箱は南の扉の前、出口（z -19.4〜-17.4）と入ったときのトリガー（z -16〜-14）の間だけに置く。
    # 前は跳んで渡る段の上（着地する所・踏み切る所）と両端の出口の中にもあり、ハルが箱の中に入り込んだ。当たり判定を付けると跳ぶのが
    # 難しくなるので、段の上の箱はやめた（溝の縁の灯の柱も、着地・踏み切りの所にあるので当たり判定は付けない）
    for pos, yaw, part in (((2.64 - 0.52, 0, -16.7), -2, "b1_crate"), ((-2.64 + 0.58, 0, -16.7), 0, "b1_crate_cloth")):
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


# 整備通路の床の穴（z の範囲）。床の段（geometry 5〜10）の間
PITS = ((-13.0, -11.5), (-7.0, -4.5), (-0.5, 3.0), (7.5, 10.5), (13.5, 16.0))


def edge_lamp_z(side, edge, sgn):
    """穴の縁 edge の手前（sgn -1）・向こう（+1）の壁の灯の z。壁の板（2 m、z = -18 + 2k）の継ぎ目の柱（奇数の z ±0.23）と、
    管つきの板（b1_wall：z ≡ -18 (mod 4)）の細い管（西の壁は板の中心 +0.68、東は -0.68）から、灯の半幅 0.12 m ＋ゆとりを空ける"""
    pipe_off = 0.68 if side == "w" else -0.68
    pipes = [-18.0 + 4.0 * k + pipe_off for k in range(10)]
    for k in range(19):
        z = edge + sgn * (0.1 + 0.05 * k)
        if abs(z - (2 * math.floor((z - 1) / 2) + 1)) < 0.37 or abs(z - (2 * math.ceil((z - 1) / 2) + 1)) < 0.37:
            continue
        if any(abs(z - pz) < 0.21 for pz in pipes):
            continue
        return round(z, 3)
    raise ValueError(f"穴の縁 {edge} の近くに灯を付ける所が無い")


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
