#!/usr/bin/env python3
"""第 1 章の遺構（B1〜B4 の部屋 r02〜r20）の部屋データを作る。出力：godot/content/areas/ch1_ruins.json

灰色の箱の部屋を、寸法の表（docs/design/30_レベルデザイン設計.md 4.4）から組むための道具。
出力の JSON が正本：細かい直しは JSON を直接編集してよい（その場合はこのスクリプトを再実行しない）。
使い方：python3 tools/gen_ch1_ruins.py
"""
import json
import math
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "godot", "content", "areas", "ch1_ruins.json")

# 階層ごとの色（壁・床／出っ張り／配管／光）
LAYER = {
    "B1": dict(mood="ruin_b1", floor="遺構 B1", wall="#6e6559", acc="#8a7d68", dark="#4b443b", light="#ffe3a8", lamp="#ffd28a"),
    "B2": dict(mood="ruin_b2", floor="遺構 B2", wall="#454c57", acc="#5b6573", dark="#2f353e", light="#7fb0ff", lamp="#ff4a3a", pipe="#7a4a3a"),
    "B3": dict(mood="ruin_b3", floor="遺構 B3", wall="#5e5446", acc="#8c6a3a", dark="#3d3429", light="#ffa24a", lamp="#ffb050"),
    "B4": dict(mood="ruin_b4", floor="遺構 B4", wall="#3f3a52", acc="#5a5272", dark="#2b2740", light="#6fe3d6", lamp="#6fe3d6"),
}


def r2(x):
    return round(x, 3)


class Room:
    def __init__(self, layer, name, gx, gy, objective=""):
        self.L = LAYER[layer]
        self.layer = layer
        self.d = {
            "name": name, "mood": self.L["mood"],
            "map": {"floor": self.L["floor"], "x": gx, "y": gy, "w": 1, "h": 1},
            "geometry": [], "markers": {}, "playerStart": "start", "objective": objective,
            "lights": [], "props": [], "enemies": [], "checkpoints": [], "triggers": [],
        }

    # ---- 形
    def shell(self, w, h, d, y=0, tint=None, ceiling=True, openings=None):
        s = {"t": "shell", "pos": [0, y, 0], "size": [w, h, d], "thick": 1, "ceiling": ceiling, "tint": tint or self.L["wall"]}
        if openings:
            s["openings"] = openings
        self.d["geometry"].append(s)

    def walls(self, w, h, d, y=0, tint=None, ceiling=True, t=1):
        """床の無い囲い（穴のある床の部屋用）"""
        tint = tint or self.L["wall"]
        g = self.d["geometry"]
        g.append({"t": "box", "pos": [0, y, -(d / 2 + t / 2)], "size": [w + 2 * t, h, t], "tint": tint})
        g.append({"t": "box", "pos": [0, y, d / 2 + t / 2], "size": [w + 2 * t, h, t], "tint": tint})
        g.append({"t": "box", "pos": [-(w / 2 + t / 2), y, 0], "size": [t, h, d], "tint": tint})
        g.append({"t": "box", "pos": [w / 2 + t / 2, y, 0], "size": [t, h, d], "tint": tint})
        if ceiling:
            g.append({"t": "box", "pos": [0, y + h, 0], "size": [w + 2 * t, t, d + 2 * t], "tint": tint})

    def box(self, x, y, z, w, h, d, tint=None, yaw=0):
        s = {"t": "box", "pos": [r2(x), r2(y), r2(z)], "size": [r2(w), r2(h), r2(d)], "tint": tint or self.L["acc"]}
        if yaw:
            s["yaw"] = yaw
        self.d["geometry"].append(s)

    def ramp(self, x, y, z, w, h, d, yaw=0, tint=None):
        s = {"t": "ramp", "pos": [x, y, z], "size": [w, h, d], "tint": tint or self.L["acc"]}
        if yaw:
            s["yaw"] = yaw
        self.d["geometry"].append(s)

    def stairs(self, x, y, z, w, h, d, steps, yaw=0, tint=None):
        s = {"t": "stairs", "pos": [x, y, z], "size": [w, h, d], "steps": steps, "tint": tint or self.L["acc"]}
        if yaw:
            s["yaw"] = yaw
        self.d["geometry"].append(s)

    # ---- 目印・明かり
    def marker(self, name, x, y, z, yaw=0):
        self.d["markers"][name] = {"pos": [x, y, z], "yaw": yaw}

    def start(self, name, x, y, z, yaw=0):
        self.marker(name, x, y, z, yaw)
        self.marker("start", x, y, z, yaw)
        self.d["playerStart"] = name
        self.d["checkpoints"].append({"id": "%s.cp" % self.rid, "pos": [x, y, z], "yaw": yaw, "radius": 4})

    def light(self, x, y, z, color=None, rng=14, energy=1.2):
        self.d["lights"].append({"pos": [x, y, z], "color": color or self.L["light"], "range": round(rng * 1.25, 1), "energy": round(energy * 2.0, 2)})

    # ---- 置く物
    def prop(self, **kw):
        self.d["props"].append(kw)

    def exit(self, name, to, spawn, x, y, z, size=(6, 4, 2), lock=None, text=None):
        p = {"type": "exit", "id": "%s.%s" % (self.rid, name), "to": to, "spawn": spawn, "pos": [x, y, z], "size": list(size)}
        if lock is not None:
            p["lock"] = lock
        if text:
            p["text"] = text
        self.prop(**p)

    def sign(self, text, x, y, z, color=None, size=40):
        self.prop(type="sign", text=text, pos=[x, y, z], size=size, color=color or self.L["light"])

    def enemy(self, typ, x, y, z, yaw=0, **kw):
        e = {"type": typ, "pos": [x, y, z], "yaw": yaw}
        e.update(kw)
        self.d["enemies"].append(e)

    def trigger(self, name, x, y, z, w, h, d, event, **kw):
        t = {"id": "%s.%s" % (self.rid, name), "pos": [x, y, z], "size": [w, h, d], "event": event}
        t.update(kw)
        self.d["triggers"].append(t)

    def flag_trigger(self, name, cond, event, **kw):
        t = {"id": "%s.%s" % (self.rid, name), "on": "flag", "cond": cond, "event": event}
        t.update(kw)
        self.d["triggers"].append(t)

    rid = ""


ROOMS = {}


def new(rid, layer, name, gx, gy, objective=""):
    r = Room(layer, name, gx, gy, objective)
    r.rid = "ch1." + rid
    ROOMS[rid] = r
    return r


def pile(r, x, z, w, d, h, y=0, tint=None):
    r.box(x, y, z, w, h, d, tint or r.L["acc"])


# ================================================================== B1 外殻層
r = new("r02", "B1", "ジャンク溜まり", 1, 0)
r.shell(26, 8, 26)
r.start("from_r01", 0, 0, -10, 0)
r.marker("from_r03", 0, 0, 10, 180)
r.marker("from_elevator", 8.5, 0, 0, 270)
r.exit("to_r01", "r01", "from_r02", 0, 0, -12)
r.exit("to_r03", "r03", "from_r02", 0, 0, 12)
r.exit("to_r17", "r17", "from_r02", 12, 0, 0, size=(2, 4, 6), lock="ch1.shortcut_open",
       text="エレベーターの扉は閉まっている。内側から開けないと動かない。")
r.box(12.7, 0, 0, 0.6, 4, 6, "#3a3d44")
r.sign("近道エレベーター", 12.3, 4.3, 0, "#9ad0ff", 28)
# ガラクタの山（収集の練習。1.0 → 1.8 と積んである）
pile(r, -8, -4, 4, 4, 1.0, tint="#7c6f5c")
pile(r, -8.5, -4.5, 2.5, 2.5, 0.8, y=1.0, tint="#8d7f69")
pile(r, 7, 5, 3.4, 3.4, 1.2, tint="#7c6f5c")
pile(r, 7.2, 5.2, 2.0, 2.0, 0.6, y=1.2, tint="#8d7f69")
pile(r, -4, 6, 5, 3, 0.7, tint="#6a5f4f")
pile(r, 3, -5, 2, 2, 1.6, tint="#7c6f5c")
pile(r, 9, -8, 3, 3, 0.9, tint="#6a5f4f")
pile(r, -9, 7, 3, 3, 1.4, tint="#6a5f4f")
r.box(-5, 0, -1, 1.4, 3.2, 1.4, "#59606a")
r.box(5.5, 0, -2, 1.2, 2.4, 1.2, "#59606a")
r.prop(type="chest", id="ch1.r02.chest1", pos=[-8.5, 1.8, -4.5], yaw=45, contents={"cells": 50})
r.prop(type="loot", id="ch1.r02.relic1", pos=[7.2, 1.8, 5.2], contents={"relics": ["relic.old_gear"]})
r.prop(type="loot", id="ch1.r02.marble", pos=[-9, 1.4, 7], contents={"item": "quest.marble"}, when="ch1.ordo_restarted")
r.light(-6, 7, -3, "#ffe3a8", 16, 1.5)
r.light(6, 7, 4, "#ffe3a8", 16, 1.5)
r.light(0, 3, 10, "#ffd28a", 12, 1.0)
r.trigger("enter", 0, 0, -8, 12, 3, 3, "ch1.r02.enter")
r.sign("外殻層 B1", 0, 4.4, 12.6, "#ffe3a8", 40)

r = new("r03", "B1", "整備通路", 2, 0)
# 穴のある通路：床は点々。落ちても 10 ダメージで直前の足場へ戻る
r.walls(6, 7.5, 38, y=-2.5, ceiling=True)
PL = [(-19, -13, 0), (-11.5, -7, 0), (-4.5, -0.5, 0), (3, 7.5, 0), (10.5, 13.5, 1.0), (16, 19, 0)]
for z0, z1, top in PL:
    r.box(0, -2.5, (z0 + z1) / 2, 6, 2.5 + top, z1 - z0, "#7a6e5d")
r.start("from_r02", 0, 0, -16, 0)
r.marker("from_r04", 0, 0, 16.5, 180)
r.exit("to_r02", "r02", "from_r03", 0, 0, -18.4)
r.exit("to_r04", "r04", "from_r03", 0, 0, 18.4)
# 高い場所の遺物（1.3 の段 → 2.6 の張り出し）
r.box(1.8, 0, -8.2, 2.2, 1.3, 2.2, "#8d7f69")
r.box(-1.8, 0, -8.2, 2.2, 2.6, 2.2, "#8d7f69")
r.prop(type="loot", id="ch1.r03.relic1", pos=[-1.8, 2.6, -8.2], contents={"relics": ["relic.rusty_valve"]})
r.light(0, 4.2, -14, "#ffe3a8", 14, 1.4)
r.light(0, 4.2, -2, "#ffe3a8", 14, 1.4)
r.light(0, 4.2, 10, "#ffe3a8", 14, 1.4)
r.sign("跳ぶ長さで、高さが変わる", 0, 3.4, -18.2, "#ffe3a8", 28)
r.trigger("enter", 0, 0, -15, 6, 3, 2, "ch1.r03.enter")

r = new("r04", "B1", "換気室", 3, 0)
r.shell(24, 9, 24)
r.start("from_r03", 0, 0, -9.5, 0)
r.marker("from_r05", 0, 0, 7.5, 180)
r.exit("to_r03", "r03", "from_r04", 0, 0, -11)
r.exit("to_r05", "r05", "from_r04", 0, 0, 11)
r.prop(type="door", id="ch1.r04.door", pos=[0, 0, 9.5], yaw=0, size=[6, 4, 0.6], opens="auto",
       lock={"all": ["switch.ch1.r04.v1", "switch.ch1.r04.v2"]}, text="換気の弁が詰まっていて、扉が動かない。")
# 止まった大型ファン（東の壁）と弁
r.box(11.2, 1, 0, 0.6, 7, 7, "#3a3d44")
for a in (0, 45, 90, 135):
    r.box(10.6, 4.5, 0, 0.3, 0.5, 8, "#59606a", yaw=0)
r.box(10.6, 1.0, 0, 0.3, 7.0, 0.5, "#59606a")
r.box(-7, 0, 3, 1.4, 1.6, 1.4, "#59606a")
r.box(7, 0, 3, 1.4, 1.6, 1.4, "#59606a")
r.prop(type="switch", id="ch1.r04.v1", pos=[-7, 2.1, 3], mode="shoot", radius=0.6)
r.prop(type="switch", id="ch1.r04.v2", pos=[7, 2.1, 3], mode="shoot", radius=0.6)
r.sign("弁", -7, 3.2, 3, "#ffd28a", 28)
r.sign("弁", 7, 3.2, 3, "#ffd28a", 28)
r.box(-4, 0, -3, 1.5, 3, 1.5, "#59606a")
r.box(4, 0, -3, 1.5, 3, 1.5, "#59606a")
r.box(-9, 0, 6, 3, 1.0, 1.5, "#7c6f5c")
r.enemy("mini", -6, 0, 6, 180, group="r04_mini")
r.enemy("mini", 6, 0, 7, 180, group="r04_mini")
r.prop(type="loot", id="ch1.r04.cells", pos=[-10, 0, 9], contents={"cells": 40})
r.light(0, 8, 0, "#ffe3a8", 18, 1.4)
r.light(-8, 3, 8, "#ffd28a", 10, 0.9)
r.trigger("enter", 0, 0, -7, 14, 3, 3, "ch1.r04.enter")

r = new("r05", "B1", "崩落床", 4, 0)
r.shell(20, 8, 24)
r.start("from_r04", 0, 0, -9.5, 0)
r.exit("to_r04", "r04", "from_r05", 0, 0, -11)
r.box(0, 0, 3, 8, 0.05, 9, "#3b3631")        # ひびの入った床
r.box(-3, 0, 1, 0.1, 0.07, 6, "#241f1b")
r.box(2, 0, 4, 0.1, 0.07, 6, "#241f1b")
r.box(0, 0, 11.2, 6, 4, 0.6, "#3a3d44")      # 奥の封じた扉
r.sign("この先は崩れている？", 0, 4.4, 11.6, "#ffd28a", 28)
r.light(0, 7, 0, "#ffe3a8", 16, 1.4)
r.light(0, 3, 9, "#ffd28a", 10, 1.0)
r.trigger("collapse", 0, 0, 3, 8, 3, 6, "ch1.collapse")

# ================================================================== B2 配管層
r = new("r06", "B2", "落下地点", 0, 1)
r.shell(22, 7, 30)
r.start("fall", 0, 0, -12, 0)
r.marker("from_r07", 0, 0, 11, 180)
r.exit("to_r07", "r07", "from_r06", 0, 0, 14)
for i, x in enumerate((-9.5, 9.5)):
    r.box(x, 3.0, 0, 1.2, 1.2, 28, "#7a4a3a")
    r.box(x, 5.2, 0, 0.8, 0.8, 28, "#5b3b30")
r.box(-5, 0, -4, 3, 1.4, 2.5, "#35404f")
r.box(6, 0, 2, 2.5, 2.0, 2.5, "#35404f")
r.box(-7, 0, 9, 4, 1.0, 2.5, "#35404f")
r.prop(type="chest", id="ch1.r06.chest1", pos=[-8, 0, 11], yaw=120, contents={"heals": 1})
# 非常灯が進む方向を示す
for i, z in enumerate((-8, -2, 4, 10)):
    r.light(0, 3.2, z, "#ff4a3a", 6, 1.0 + 0.1 * i)
    r.box(0, 6.6, z, 0.5, 0.3, 0.5, "#ff4a3a")
r.light(0, 6, -12, "#7fb0ff", 10, 0.3)
r.sign("非常口 →", 0, 3.6, 13, "#ff4a3a", 30)

r = new("r07", "B2", "追跡通路", 1, 1)
r.shell(6, 5, 40)
r.start("from_r06", 0, 0, -16, 0)
r.marker("from_r08", 0, 0, 14, 180)
r.exit("to_r06", "r06", "from_r07", 0, 0, -19, size=(4, 4, 2))
r.exit("to_r08", "r08", "from_r07", 0, 0, 18.6, size=(4, 4, 1.6), lock="ch1.r07.seal_open", text="")
# 配管のすき間（左右互い違い。幅 2.2m）
for z, side in ((-8, 1), (-1, -1), (6, 1), (12, -1)):
    x0 = -3 if side == 1 else -0.8
    x1 = 0.8 if side == 1 else 3
    r.box((x0 + x1) / 2, 0, z, x1 - x0, 5, 1.2, "#7a4a3a")
r.prop(type="door", id="ch1.r07.seal", pos=[0, 0, 17.4], yaw=0, size=[4, 4.2, 0.6], opens="auto",
       lock="ch1.r07.seal_open", text="行き止まりだ。")
r.sign("封", 0, 4.3, 16.9, "#6fe3d6", 36)
for z in (-12, -4, 4, 12):
    r.light(0, 3.8, z, "#ff4a3a", 7, 0.9)
r.trigger("chase", 0, 0, -12, 6, 3, 2, "ch1.chase")
r.trigger("dead", 0, 0, 14, 6, 3, 2, "ch1.r07.dead")

r = new("r08", "B2", "封印室", 2, 1)
r.shell(22, 8, 22)
r.start("from_r07", 0, 0, -8.5, 0)
r.marker("from_r09", 0, 0, 8, 180)
r.exit("to_r07", "r07", "from_r08", 0, 0, -10, lock="ch1.frame_fitted", text="")
r.exit("to_r09", "r09", "from_r08", 0, 0, 10, lock="ch1.r08.trained", text="まだ何か、呼ばれている気がする。")
r.box(0, 0, 0, 5, 0.4, 5, "#3b5a60")         # 台座
r.box(0, 0.4, 0, 1.4, 0.2, 1.4, "#6fe3d6")
for a in range(4):
    x = 2.6 * math.sin(math.radians(a * 90 + 45))
    z = 2.6 * math.cos(math.radians(a * 90 + 45))
    r.box(x, 1.4, z, 0.7, 1.4, 0.7, "#6fe3d6")  # 浮いている部品
for i in range(8):
    a = math.radians(i * 45)
    r.box(8.5 * math.sin(a), 0, 8.5 * math.cos(a), 1.2, 4.5, 1.2, "#2f4a50")
r.light(0, 3, 0, "#6fe3d6", 14, 1.8)
r.light(0, 7, 0, "#7fb0ff", 18, 0.8)
r.trigger("fit", 0, 0, -4, 10, 3, 3, "ch1.frame_fit")

r = new("r09", "B2", "配管広間", 3, 1)
r.shell(20, 8, 24)
r.start("from_r08", 0, 0, -9.5, 0)
r.marker("from_r10", 0, 0, 7.5, 180)
r.exit("to_r08", "r08", "from_r09", 0, 0, -11)
r.exit("to_r10", "r10", "from_r09", 0, 0, 11)
r.prop(type="door", id="ch1.r09.door", pos=[0, 0, 9.5], yaw=0, size=[6, 4, 0.6], opens="auto",
       lock="ch1.r09.cleared", text="扉が閉じている。敵を片づけないと開かない。")
for x, z in ((-5, -2), (5, -2), (-5, 5), (5, 5), (0, 1.5)):
    r.box(x, 0, z, 1.4, 8, 1.4, "#7a4a3a")                    # 縦の配管（遮蔽物）
r.box(-3, 0, -6, 3.5, 1.3, 1.0, "#35404f")
r.box(3, 0, 8, 3.5, 1.3, 1.0, "#35404f")
r.enemy("sentry", -6, 0, 7, 180, group="r09_w1", unless="ch1.r09.cleared")
r.enemy("sentry", 6, 0, 8, 180, group="r09_w1", unless="ch1.r09.cleared")
r.enemy("sentry", 0, 0, 6, 180, group="r09_w1", unless="ch1.r09.cleared")
r.flag_trigger("w2", {"all": [{"cleared": "r09_w1"}, {"not": "ch1.r09.cleared"}]}, "ch1.r09.wave2", persist=False)
r.prop(type="loot", id="ch1.r09.cells", pos=[-8.5, 0, -9], contents={"cells": 60})
for z in (-8, 0, 8):
    r.light(0, 6.5, z, "#7fb0ff", 12, 1.0)
    r.light(-8, 2.5, z, "#ff4a3a", 6, 0.7)

r = new("r10", "B2", "弁の間", 4, 1)
r.shell(20, 8, 24)
r.start("from_r09", 0, 0, -9.5, 0)
r.marker("from_r11", 0, 0, 7.5, 180)
r.exit("to_r09", "r09", "from_r10", 0, 0, -11)
r.exit("to_r11", "r11", "from_r10", 0, 0, 11)
r.prop(type="door", id="ch1.r10.door", pos=[0, 0, 9.5], yaw=0, size=[6, 4, 0.6], opens="auto",
       lock={"all": [{"cleared": "r10_w1"}, "switch.ch1.r10.valve"]}, text="扉が閉じている。弁の輪を回して、敵を片づけよう。")
r.box(0, 6.2, 11.2, 4, 0.5, 0.5, "#7a4a3a")
r.prop(type="switch", id="ch1.r10.valve", pos=[0, 5.0, 10.6], mode="shoot", radius=0.9)
r.sign("弁の輪（撃って回す）", 0, 6.8, 10.9, "#ffd28a", 30)
for x in (-6, 6):
    r.box(x, 0, 0, 1.6, 2.4, 1.6, "#35404f")
r.box(0, 0, 4, 5, 1.2, 1.0, "#35404f")
r.box(-8, 0, -4, 1.6, 8, 1.6, "#7a4a3a")
r.box(8, 0, -4, 1.6, 8, 1.6, "#7a4a3a")
r.enemy("shield", 0, 0, 5, 180, group="r10_w1")
r.enemy("sentry", -6, 0, 7, 180, group="r10_w1")
r.enemy("sentry", 6, 0, 7, 180, group="r10_w1")
r.prop(type="chest", id="ch1.r10.chest1", pos=[9, 0, -9], yaw=-45, contents={"cells": 120, "relics": ["relic.valve_ring"]})
for z in (-7, 2, 8):
    r.light(0, 6.5, z, "#7fb0ff", 12, 1.0)
r.light(0, 4, 10, "#ff4a3a", 8, 1.0)
r.trigger("enter", 0, 0, -7, 14, 3, 3, "ch1.r10.enter")

r = new("r11", "B2", "縦坑", 5, 1)
H = 24
r.shell(12, H, 12, ceiling=True)
# 足場が上から降りていく（上は y=21、下は床）
STEPS = [(-4, 21.0, -4), (0.5, 18.6, -4.5), (4.2, 16.2, -1.5), (3.5, 13.8, 3.5), (-0.5, 11.4, 4.5),
         (-4.2, 9.0, 1.5), (-3.8, 6.6, -3.5), (0.5, 4.2, -4.0), (3.8, 2.0, -2.0)]
for x, y, z in STEPS:
    r.box(x, y - 1.0, z, 3.0, 1.0, 3.0, "#7a6e5d")
r.box(-4.5, 20.0, -4.5, 3.0, 1.0, 3.0, "#8d7f69")
r.start("from_r10", -3, 21.0, -3.5, 135)
r.marker("from_r12", 0, 0, 2.5, 180)
r.exit("to_r10", "r10", "from_r11", -5.0, 21.0, -5.0, size=(2, 4, 2))
r.exit("to_r12", "r12", "from_r11", 0, 0, 5, size=(6, 4, 2))
r.prop(type="beacon", id="ch1.r11.bc", pos=[0, 0, -1], flag="ch1.first_beacon", event="ch1.beacon")
r.prop(type="loot", id="ch1.r11.relic1", pos=[-4.2, 9.0, 1.5], contents={"relics": ["relic.pipe_gauge"]})
for y in (20, 14, 8, 2):
    r.light(0, y, 0, "#7fb0ff", 10, 1.0)
r.sign("遺構 B2 の底", 0, 3.8, 5.6, "#7fb0ff", 30)

# ================================================================== B3 駆動層
r = new("r12", "B3", "駆動回廊", 1, 2)
# 穴の底（y=-6）に床、側面のスロープから戻れる。足場＝ピストン
r.shell(16, 18, 38, y=-6, openings=[{"side": "w", "at": -14, "w": 4, "h": 4, "y": 6}])
r.box(0, -6, -14, 16, 6, 8, "#6a5a48")        # 手前の足場（上面 y=0、z -18〜-10）
r.box(0, -6, 17, 16, 6, 4, "#6a5a48")         # 奥の足場（z 15〜19）
r.ramp(-6, -6, 0, 4, 6, 20, yaw=180, tint="#5a4a3a")   # 穴の底から手前の足場へ戻るスロープ
r.start("from_r11", 0, 0, -16, 0)
r.marker("from_r13", 0, 0, 14.5, 180)
r.marker("from_r17", 5.5, 0, -14, 270)
r.marker("from_r14", -5.5, 0, -14, 90)
r.exit("to_r11", "r11", "from_r12", 0, 0, -18, size=(6, 4, 2))
r.exit("to_r13", "r13", "from_r12", 0, 0, 18, size=(6, 4, 2))
r.exit("to_r17", "r17", "from_r12", 7.2, 0, -14, size=(1.6, 4, 4))
r.exit("to_r14", "r14", "from_r12", -7.2, 0, -14, size=(1.6, 4, 4), lock="broken.ch1.r12.crack",
       text="壁にひびが入っている。普通の弾では壊せそうにない。")
r.prop(type="breakable", id="ch1.r12.crack", pos=[-8.5, 0, -14], size=[1.0, 4, 4], toughness=1.0)
r.box(7.7, 0, -14, 0.6, 4, 4, "#3a3d44")      # 近道エレベーターの扉
r.sign("近道エレベーター", 7.4, 4.3, -14, "#9ad0ff", 26)
r.prop(type="switch", id="ch1.r12.s1", pos=[-5, 1.6, -17], mode="shoot", radius=0.7)
r.prop(type="switch", id="ch1.r12.s2", pos=[5, 1.6, -17], mode="shoot", radius=0.7)
r.sign("動力の球（撃つ）", -5, 2.9, -17.5, "#ffb050", 26)
r.sign("動力の球（撃つ）", 5, 2.9, -17.5, "#ffb050", 26)
# ピストン（動力が通ると往復する）
for i, (z, spd, wait, mv) in enumerate(((-5.5, 2.2, 1.0, 3.6), (0.5, 2.8, 1.6, 3.6), (6.5, 2.0, 0.8, 3.6))):
    r.prop(type="mover", id="ch1.r12.p%d" % (i + 1), pos=[0, -2.6, z], size=[5, 0.5, 5], move=[0, mv, 0],
           speed=spd, mode="pingpong", wait=wait, cond="ch1.drive_powered")
for z in (-6, 0, 6, 12):
    r.box(-7.4, 0, z, 1.0, 12, 1.4, "#3d3429")
    r.box(7.4, 0, z, 1.0, 12, 1.4, "#3d3429")
r.light(0, 8, -12, "#ffb050", 18, 1.4)
r.light(0, 8, 2, "#ffa24a", 18, 1.2)
r.light(0, 8, 14, "#ffa24a", 18, 1.2)
r.flag_trigger("powered", ["switch.ch1.r12.s1", "switch.ch1.r12.s2"], "ch1.r12.powered")
r.trigger("enter", 0, 0, -15, 14, 3, 2, "ch1.r12.enter")

r = new("r13", "B3", "歯車の間", 2, 2)
r.shell(20, 12, 30)
r.start("from_r12", 0, 0, -12.5, 0)
r.marker("from_r15", 0, 0, 12.5, 180)
r.exit("to_r12", "r12", "from_r13", 0, 0, -14, size=(6, 4, 2))
r.exit("to_r15", "r15", "from_r13", 0, 0, 14, size=(6, 4, 2))
# 歯車のリフト（動力が通っていると往復）で、奥の張り出し（y=4）へ
r.box(0, 0, 11, 8, 4.0, 5, "#8c6a3a")        # 張り出し（上面 y=4、z 8.5〜13.5）
r.prop(type="mover", id="ch1.r13.lift1", pos=[-5.5, 0.1, 5.0], size=[3.5, 0.4, 3.5], move=[0, 3.9, 0],
       speed=2.0, mode="pingpong", wait=1.2, cond="ch1.drive_powered")
r.prop(type="mover", id="ch1.r13.lift2", pos=[5.5, 2.0, 3.0], size=[3.5, 0.4, 3.5], move=[0, 2.0, 0],
       speed=1.6, mode="pingpong", wait=0.8, cond="ch1.drive_powered")
r.prop(type="chest", id="ch1.r13.chest1", pos=[0, 4.0, 11.5], yaw=180, contents={"cells": 150, "relics": ["relic.big_gear"]})
for x in (-7, 7):
    r.box(x, 0, -4, 2.4, 3.0, 2.4, "#5a4a3a")
for i in range(3):
    r.box(-9.6, 3 + i * 3, -6 + i * 6, 0.8, 2.4, 2.4, "#3d3429")
    r.box(9.6, 3 + i * 3, -2 + i * 6, 0.8, 2.4, 2.4, "#3d3429")
r.enemy("floater", -5, 4.5, -2, 0, group="r13_w1", unless="ch1.r13.cleared")
r.enemy("floater", 5, 5.0, 0, 0, group="r13_w1", unless="ch1.r13.cleared")
r.enemy("floater", 0, 5.5, 4, 180, group="r13_w1", unless="ch1.r13.cleared")
r.flag_trigger("done", {"cleared": "r13_w1"}, "ch1.r13.done")
r.light(0, 10, -6, "#ffa24a", 16, 1.5)
r.light(0, 10, 8, "#ffb050", 16, 1.5)
r.trigger("enter", 0, 0, -10, 14, 3, 2, "ch1.r13.enter")

r = new("r14", "B3", "隠し部屋", 1, 3)
r.shell(10, 6, 10)
r.start("from_r12", 3, 0, 0, 90)
r.exit("to_r12", "r12", "from_r14", 4.2, 0, 0, size=(1.6, 4, 4))
r.box(0, 0, 0, 2.4, 0.8, 2.4, "#8c6a3a")
r.prop(type="loot", id="ch1.r14.lifecore", pos=[0, 0.8, 0], contents={"lifecore": True})
r.prop(type="chest", id="ch1.r14.chest1", pos=[-3.5, 0, -3.5], yaw=45, contents={"cells": 100})
r.light(0, 4, 0, "#ffb050", 12, 1.6)
r.sign("誰かの隠した物", 0, 3.4, 4.6, "#ffb050", 28)

r = new("r15", "B3", "伝導路", 3, 2)
r.shell(20, 9, 24)
r.start("from_r13", 0, 0, -9.5, 0)
r.marker("from_r16", 0, 0, 9.5, 180)
r.exit("to_r13", "r13", "from_r15", 0, 0, -11)
r.exit("to_r16", "r16", "from_r15", 0, 0, 11)
# 動くピストン（頭上を行き来する足場。乗ると高い位置から撃てる）
r.prop(type="mover", id="ch1.r15.p1", pos=[-5, 1.9, -2], size=[4, 0.5, 4], move=[0, 2.8, 0], speed=1.8, mode="pingpong", wait=0.6, cond=None)
r.prop(type="mover", id="ch1.r15.p2", pos=[5, 1.9, 4], size=[4, 0.5, 4], move=[0, 2.8, 0], speed=1.8, mode="pingpong", wait=0.9, cond=None)
for x, z in ((-8, 5), (8, -5), (0, 0)):
    r.box(x, 0, z, 1.6, 9, 1.6, "#8c6a3a")
r.box(0, 0, 7, 5, 1.2, 1.0, "#5a4a3a")
r.box(0, 0, -6, 5, 1.2, 1.0, "#5a4a3a")
r.enemy("sentry", -6, 0, 6, 180, group="r15_w1", unless="ch1.r15.cleared")
r.enemy("sentry", 6, 0, 7, 180, group="r15_w1", unless="ch1.r15.cleared")
r.enemy("shield", 0, 0, 4, 180, group="r15_w1", unless="ch1.r15.cleared")
r.flag_trigger("w2", {"all": [{"cleared": "r15_w1"}, {"not": "ch1.r15.cleared"}]}, "ch1.r15.wave2", persist=False)
r.prop(type="chest", id="ch1.r15.chest1", pos=[9, 0, 10], yaw=-90, contents={"items": ["chip.charge"], "cells": 80})
for z in (-8, 0, 8):
    r.light(0, 8, z, "#ffa24a", 14, 1.3)

r = new("r16", "B3", "中央縦坑", 4, 2)
r.shell(12, 26, 12)
r.box(0, 0, -4.2, 10, 20.0, 3.6, "#5a4a3a")       # 上の足場（上面 y=20）
r.start("from_r15", 0, 20.0, -3.0, 0)
r.marker("from_r18", 0, 0, -3.5, 0)
r.exit("to_r15", "r15", "from_r16", 0, 20.0, -5.0, size=(5, 4, 1.4))
r.exit("to_r18", "r18", "from_r16", 0, 0, 5, size=(6, 4, 2))
r.prop(type="mover", id="ch1.r16.lift", pos=[0, 19.6, 0.4], size=[5, 0.4, 4], move=[0, -19.6, 0], speed=4.5, mode="ride")
r.sign("リフト（乗ると降りる）", 0, 22.2, -2.4, "#ffb050", 30)
r.enemy("charger", -4, 0, 3, 180, group="r16_w1", unless="ch1.r16.cleared")
r.enemy("charger", 4, 0, 3.5, 180, group="r16_w1", unless="ch1.r16.cleared")
r.flag_trigger("done", {"cleared": "r16_w1"}, "ch1.r16.done")
for y in (22, 15, 8, 2):
    r.light(0, y, 0, "#ffa24a", 12, 1.2)

r = new("r17", "B3", "近道", 0, 2)
r.shell(12, 6, 12)
r.start("from_r12", 3, 0, 0, 90)
r.marker("from_r02", 3, 0, 0, 90)
r.exit("to_r12", "r12", "from_r17", 4.6, 0, 3, size=(1.6, 4, 3))
r.exit("to_r02", "r02", "from_elevator", -4.6, 0, -3, size=(1.6, 4, 3), lock="ch1.shortcut_open",
       text="エレベーターはまだ動かない。レバーを引こう。")
r.box(-5.6, 0, -3, 0.6, 3.6, 3, "#3a3d44")
r.box(0, 0, -4.8, 0.6, 1.3, 0.6, "#6a5a48")
r.prop(type="terminal", id="ch1.r17.lever", pos=[0, 0, -4.2], event="ch1.r17.lever", prompt="レバーを引く")
r.sign("近道エレベーター（外殻層へ）", -5.2, 4.4, -3, "#9ad0ff", 26)
r.light(0, 4.5, 0, "#ffb050", 12, 1.4)

# ================================================================== B4 心臓部
r = new("r18", "B4", "心臓部前室", 4, 3)
r.shell(20, 8, 24)
r.start("from_r16", 0, 0, -10, 0)
r.marker("from_r19", 0, 0, 8, 180)
r.exit("to_r19", "r19", "from_r18", 0, 0, 11, lock="ch1.diagnosis", text="大きな扉は閉ざされている。……ナゴミが何か言いたそうだ。")
r.prop(type="door", id="ch1.r18.door", pos=[0, 0, 9.6], yaw=0, size=[6, 5, 0.6], opens="auto", lock="ch1.diagnosis")
r.prop(type="beacon", id="ch1.r18.bc", pos=[-5, 0, 3], flag="ch1.r18_beacon", event="ch1.beacon")
r.prop(type="chest", id="ch1.r18.chest1", pos=[7, 0, -6], yaw=-60, contents={"heals": 2})
r.box(0, 0, 0, 3, 0.5, 3, "#5a5272")
r.box(0, 0.5, 0, 0.8, 1.6, 0.8, "#6fe3d6")
for x in (-8.5, 8.5):
    r.box(x, 0, 2, 1.4, 8, 1.4, "#2b2740")
r.light(0, 5, 0, "#6fe3d6", 16, 1.2)
r.light(0, 4, 9, "#9a7cff", 10, 1.0)
r.sign("心臓部", 0, 5.4, 10.4, "#6fe3d6", 40)
r.trigger("diagnosis", 0, 0, -3, 14, 3, 3, "ch1.diagnosis")

# 心臓部：直径 32m の円形（壁 36 枚）
r = new("r19", "B4", "心臓部", 5, 3)
R = 16.0
SEG = 36
seg_len = 2 * math.pi * (R + 0.5) / SEG + 0.4
r.box(0, -1, 0, 40, 1, 40, "#2b2740")
for i in range(SEG):
    if i == 0:
        continue                                  # 入口（北＝+Z）の隙間。ボスはレールの南の端（-Z）で待つので、入口から遠い
    a = 2 * math.pi * i / SEG
    r.d["geometry"].append({"t": "box", "pos": [r2(math.sin(a) * (R + 0.5)), 0, r2(math.cos(a) * (R + 0.5))],
                            "size": [r2(seg_len), 16, 1.0], "yaw": r2(math.degrees(a)), "tint": "#3f3a52"})
# 入口の通路
r.box(0, 0, 19.5, 8, 16, 1, "#3f3a52")
r.box(-3.8, 0, 18, 0.6, 16, 4, "#3f3a52")
r.box(3.8, 0, 18, 0.6, 16, 4, "#3f3a52")
# 外周のレール（見た目。半径 10.5m）
for i in range(SEG):
    a = 2 * math.pi * i / SEG
    r.d["geometry"].append({"t": "box", "pos": [r2(math.sin(a) * 10.5), 0, r2(math.cos(a) * 10.5)],
                            "size": [2.1, 0.06, 0.5], "yaw": r2(math.degrees(a) + 90), "tint": "#6fe3d6"})
# 炉心の扉（奥の壁）
r.box(0, 0, -15.5, 7, 9, 0.6, "#5a5272")
r.box(0, 0, -15.2, 2, 9, 0.3, "#6fe3d6")
r.prop(type="door", id="ch1.r19.furnace", pos=[0, 0, -15.0], yaw=180, size=[6, 4.5, 0.4], opens="auto",
       lock="ch1.boss_defeated", text="炉心の扉は固く閉ざされている。")
r.start("from_r18", 0, 0, 14.9, 180)
r.exit("to_r18", "r18", "from_r19", 0, 0, 17.6, size=(4, 4, 1.2))
r.marker("from_r20", 0, 0, -12, 0)
r.exit("to_r20", "r20", "from_r19", 0, 0, -14.3, size=(5, 4.5, 1.6), lock="ch1.boss_defeated", text="")
for i in range(4):
    a = math.pi * 0.25 + math.pi * 0.5 * i
    r.prop(type="breakable", id="ch1.r19.pillar_%d" % i, pos=[r2(math.sin(a) * 6.5), 0, r2(math.cos(a) * 6.5)],
           size=[1.6, 6, 1.6], toughness=9999.0, persist=False)
r.enemy("kannuki", 0, 0, 0, 0, id="kannuki", unless="ch1.boss_defeated")
r.light(0, 12, 0, "#6fe3d6", 30, 1.6)
r.light(0, 8, 12, "#9a7cff", 16, 1.0)
r.light(0, 8, -12, "#9a7cff", 16, 1.0)
r.trigger("intro", 0, 0, 15.6, 8, 3, 2.4, "ch1.r19.enter", persist=False, cond={"not": "ch1.boss_defeated"})
r.flag_trigger("down", "ch1.boss_defeated", "ch1.boss_down")

r = new("r20", "B4", "炉心", 6, 3)
r.shell(20, 10, 20)
r.start("from_r19", 0, 0, -8, 0)
r.exit("to_r19", "r19", "from_r20", 0, 0, -9.4, size=(5, 4, 1.2))
r.box(0, 0, 2, 5, 0.6, 5, "#5a5272")
r.box(0, 0.6, 2, 2.4, 3.4, 2.4, "#6fe3d6")        # 炉心（止まっている）
r.box(0, 4.0, 2, 3.2, 0.4, 3.2, "#5a5272")
for a in range(8):
    x = 8 * math.sin(math.radians(a * 45))
    z = 2 + 8 * math.cos(math.radians(a * 45))
    r.box(x, 0, z, 1.0, 9, 1.0, "#2b2740")
r.light(0, 3, 2, "#6fe3d6", 16, 1.8)
r.light(0, 9, 0, "#9a7cff", 18, 0.8)
r.trigger("enter", 0, 0, -5, 14, 3, 3, "ch1.restart", cond={"not": "ch1.ordo_restarted"})

# ================================================================== 出力
# ---- 検査：出口の行き先の目印があること、目印が自分の部屋の出口の範囲に入っていないこと
town = json.load(open(os.path.join(ROOT, "godot", "content", "areas", "ch1_town.json"), encoding="utf-8"))["rooms"]
known = {k: set(v["markers"]) for k, v in town.items()}
known.update({k: set(v.d["markers"]) for k, v in ROOMS.items()})
bad = 0
for k, rm in ROOMS.items():
    for p in rm.d["props"]:
        if p["type"] != "exit":
            continue
        if p["spawn"] not in known.get(p["to"], set()):
            print("出口の行き先の目印が無い：", rm.rid, p["to"], p["spawn"]); bad += 1
        for mk, m in rm.d["markers"].items():
            mx, my, mz = m["pos"]
            px, py, pz = p["pos"]; sx, sy, sz = p["size"]
            if abs(mx - px) <= sx / 2 and abs(mz - pz) <= sz / 2 and py - 0.1 <= my <= py + sy:
                print("目印が出口の中：", rm.rid, mk, p["id"]); bad += 1
if bad:
    raise SystemExit("検査に失敗")

out = {"id": "ch1", "name": "第 1 章（遺構 B1〜B4）", "rooms": {k: v.d for k, v in ROOMS.items()}}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("書き出し：%s（部屋 %d）" % (os.path.relpath(OUT, ROOT), len(ROOMS)))
