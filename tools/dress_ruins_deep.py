"""遺構の r04〜r20（B1 の残り・B2 配管層・B3 駆動層・B4 心臓部）に、キットと飾りを書く。tools/dress_ruins.py から呼ぶ
（python3 tools/dress_ruins.py [部屋]。この道具の Dress・light を使う）。

決まりは r02・r03 と同じ（docs/design/42_コンテンツの書き方.md 14 章、43_遺構の見た目.md）：当たり判定・目印・出口・トリガー・置く物・敵は変えない。
変えるのは見た目（部屋の kit・dress・lights、形の skin・hide・trim）と、飾りの solid から作る描かない当たり判定の箱だけ。
部品：B1 は ruins_b1.py、B2 は ruins_b2.py、B3 は ruins_b3.py、B4 は ruins_b4.py（B4 の部屋は B3 の部品を B4 の色で）、
汚れのしみは ruins_common.py（どの階層でも：管・灯の下のさびの筋、扉の前、通り道、部屋の隅）。
"""
import math

import dress_solid
from dress_solid import B, P

D = None        # tools/dress_ruins.py（Dress・light）


# ---------------------------------------------------------------- 当たり判定の箱（dress_solid の SOLID に足す）

LINER = dress_solid.LINER


def solid_table():
    band = [B(-1.0, 1.0, 0.0, 4.0, 0.0, LINER, wall=True)]
    return {
        "ruins/b2_wall": band, "ruins/b2_wall_vent": band, "ruins/b3_wall": band, "ruins/b3_wall_plain": band,
        "ruins/b2_door": band, "ruins/b3_door": band,
        "ruins/b2_corner": [B(0.0, 0.5, 0.0, 4.05, 0.0, 0.5, wall=True)],
        "ruins/b3_corner": [B(0.0, 0.5, 0.0, 4.05, 0.0, 0.5, wall=True)],
        "ruins/b2_pillar": [B(-0.31, 0.31, 0.0, 4.0, -0.31, 0.31)],
        "ruins/b3_pillar": [B(-0.34, 0.34, 0.0, 4.0, -0.34, 0.34)],
        # 動力の球の台座（球の中心は台の上 0.6 m。台の箱は 1.0 m まで）
        "ruins/b3_orb_base": [B(-0.5, 0.5, 0.0, 1.0, -0.5, 0.5)],
        # 壁の弁の輪（原点 = 壁の面・輪の中心の高さ。輪は壁から 0.3 m）
        "ruins/b2_valve": [B(-0.5, 0.5, -0.5, 0.5, 0.0, 0.34, wall=True)],
        # 壁の足元の駆動梁（壁から 0.35 m、高さ 0.27）。壁の帯の内
        "ruins/b3_drive": [B(-1.0, 1.0, 0.0, 0.3, 0.0, LINER, wall=True)],
        # 床に落ちた太い管（W2-06b の 09）と、壁にもたれた外装の板（10）
        "ruins/pipe_broken": [B(-0.82, 0.82, 0.0, 0.62, -0.33, 0.33)],
        "ruins/panel_fallen": [B(-1.0, 1.0, 0.0, 0.55, -0.95, 0.0)],
    }


def setup(base):
    global D
    D = base
    dress_solid.SOLID.update(solid_table())


# ---------------------------------------------------------------- 階層ごとの部品の組

KITS = {
    "b1": {"kit": "ruins_b1", "walls": ("b1_wall", "b1_wall_plain"), "door": "b1_door", "corner": "b1_corner",
           "beam": "b1_beam", "beam_red": "b1_beam_red", "pipe": "b1_pipe"},
    # 壁の部品は 1 種類（部品の種類 × 材質の数だけ描画が増えるので、B2・B3 は交互にしない）
    "b2": {"kit": "ruins_b2", "walls": ("b2_wall",), "door": "b2_door", "corner": "b2_corner",
           "beam": "b2_beam", "beam_red": "b2_beam_red", "pipe": "b2_pipe_drip"},
    "b3": {"kit": "ruins_b3", "walls": ("b3_wall",), "door": "b3_door", "corner": "b3_corner",
           "beam": "b3_beam", "beam_red": "b3_beam", "pipe": "b3_pipe"},
    "b4": {"kit": "ruins_b4", "walls": ("b3_wall",), "door": "b3_door", "corner": "b3_corner",
           "beam": "b3_beam", "beam_red": "b3_beam", "pipe": "b3_pipe"},
}
CORNER_YAW = {(-1, -1): 0, (-1, 1): 90, (1, 1): 180, (1, -1): 270}


def walls(d, k, side, plane, a0, a1, skip=(), y=0.0, solid=True, parts=None):
    """壁 side（内側の面 plane）に 2 m の壁の部品を a0〜a1（中心）に並べる。skip：(lo, hi) の区間に掛かる部品は置かない"""
    parts = parts or KITS[k]["walls"]
    n = int(round((a1 - a0) / 2.0)) + 1
    for i in range(n):
        a = a0 + 2.0 * i
        if any(a + 1.0 > lo + 1e-3 and a - 1.0 < hi - 1e-3 for lo, hi in skip):
            continue
        kw = {"solid": True} if solid else {}
        d.at_wall(side, plane, round(a, 3), parts[i % len(parts)], y=y, **kw)


def door(d, k, side, plane, a, width=3.0, solid=True, y=0.0):
    """出口の先の閉じた扉（2 m の部品を幅 width に。高さは 1.2 倍の 4.8 m）"""
    kw = {"solid": True} if solid else {}
    d.at_wall(side, plane, a, KITS[k]["door"], y=y, scale=[round(width / 2.0, 3), 1.2, 1.0], **kw)


def corners(d, k, x0, x1, z0, z1, solid=True):
    for (sx, sz), yaw in CORNER_YAW.items():
        kw = {"solid": True} if solid else {}
        d.put(KITS[k]["corner"], [x1 if sx > 0 else x0, 0, z1 if sz > 0 else z0], yaw, **kw)


def beams(d, k, x0, x1, y, zs, red=True):
    """天井の梁（x0〜x1 を 2 m ずつ）を z の列に。部品は 1 種類（赤い非常灯つき）：種類が増えると描画が増える"""
    n = int(round((x1 - x0) / 2.0))
    for z in zs:
        d.row(KITS[k]["beam_red"] if red else KITS[k]["beam"], [x0 + 1.0, y, z], [2.0, 0, 0], n)


# ---------------------------------------------------------------- 汚れの置き場所（しみの部品）

def grime(d, corners_at=(), doors_at=(), path=(), spots=(), y=0.0):
    """汚れているべき所に、しみの部品を置く（43 の 2 章）。
    corners_at：[(x, z, 隅の yaw)]（部屋の隅）、doors_at：[(x, z, yaw)]（扉・出口の前。yaw は壁に沿う向き）、
    path：[(x0, z0), (x1, z1), …]（通り道。4.5 m ごとに踏まれた汚れ）、spots：[(x, z, yaw, 大きさ)]（機械・管の下などの床の斑）"""
    for x, z, yaw in corners_at:
        d.put("stain_corner", [x, y, z], yaw)
    for x, z, yaw in doors_at:
        d.put("stain_floor", [x, y, z], yaw, scale=[1.4, 1.0, 1.1])
    for (x0, z0), (x1, z1) in zip(path, path[1:]):
        L = math.hypot(x1 - x0, z1 - z0)
        n = max(1, int(L / 4.5))
        yaw = round(math.degrees(math.atan2(x1 - x0, z1 - z0)) + 90.0, 1)
        for i in range(n):
            t = (i + 0.5) / n
            side = 0.45 if i % 2 else -0.45
            nx, nz = (z1 - z0) / L, -(x1 - x0) / L
            d.put("stain_path", [round(x0 + (x1 - x0) * t + nx * side, 3), y, round(z0 + (z1 - z0) * t + nz * side, 3)], yaw,
                  scale=[1.0, 1.0, 1.0 + 0.2 * (i % 2)])
    for x, z, yaw, sc in spots:
        d.put("stain_floor_b", [x, y, z], yaw, scale=[sc, 1.0, sc])


def drips(d, side, plane, a, y_top, long=False, off=0.0):
    """壁を垂れるさびの筋（上の端 y_top から下へ）。壁の面から off（壁の部品の前の面）"""
    d.at_wall(side, plane, a, "stain_drip_long" if long else "stain_drip", y=y_top, off=off)


def shell_box(room, i=0):
    g = room["geometry"][i]
    px, py, pz = g["pos"]
    sx, sy, sz = g["size"]
    return px - sx / 2, px + sx / 2, pz - sz / 2, pz + sz / 2, py, py + sy


def light(pos, color="#ffbc52", rng=8.0, energy=1.2):
    return D.light(pos, color, rng, energy)


# ================================================================ B1：換気室・崩落床

def r04(room):
    """換気室（24×24×9）。止まった大型ファン（東の壁、形 3〜8）、弁の台 2 つ（形 9・10）、扉の壁（形 1・2）、奥の扉は弁で開く"""
    g = room["geometry"]
    d = D.Dress()
    k = "b1"
    X, Z = 12.0, 12.0
    # 形：扉の壁は白磁の壁の面、ファンの箱（形 3）は描かず部品のファンで、羽根の十字（形 4〜8）は黒鉛の補強の桟に
    g[3]["hide"] = True
    for i in (4, 5, 6, 7, 8):
        g[i]["skin"] = "metal"
    for i in (9, 10):
        g[i]["skin"] = {"wall": "metal", "floor": "plate"}
    for i in (11, 12):
        g[i]["skin"] = {"wall": "plate", "floor": "metal"}
    g[13]["skin"] = {"wall": "plate", "floor": "sandfloor"}
    # 壁の列：南（入口の扉）、西、東（ファンの所を空ける）、扉の壁の南の面（z 9.2）
    walls(d, k, "s", -Z, -11.0, 11.0, skip=[(-1.5, 1.5)])
    door(d, k, "s", -Z, 0.0)
    walls(d, k, "w", -X, -11.0, 7.0)
    walls(d, k, "e", X, -11.0, 7.0, skip=[(-4.4, 4.4)])
    walls(d, k, "n", 9.2, -11.0, -4.0, skip=[(-10.5, -9.5)])       # 拾う物のセル（-10, 9）の前は空ける
    walls(d, k, "n", 9.2, 4.0, 11.0)
    for x, z, yaw in ((-X, -Z, 0), (X, -Z, 270), (-X, 9.2, 90), (X, 9.2, 180)):
        d.put("b1_corner", [x, 0, z], yaw, solid=True)
    # 扉の上（4〜8 m）の白磁の板と梁（扉は 4 m。上は開いていた）と、扉の奥の小部屋の先の扉（出口の先）
    d.row("b1_wall_plain", [-2.0, 4.0, 9.2], [2.0, 0, 0], 3, 180)
    d.row("b1_beam_red", [-2.0, 4.6, 9.5], [2.0, 0, 0], 3)
    door(d, k, "n", Z, 0.0)
    walls(d, k, "n", Z, -4.0, 4.0, skip=[(-1.5, 1.5)], solid=False)
    # 止まった大型ファン（東の壁、7×7 m）：部品のファン（4 m）を 1.75 倍。十字の桟（形 4〜8）は前の補強
    d.at_wall("e", X, 0.0, "b1_fan", y=1.0, scale=[1.75, 1.75, 1.2])
    d.along("e", X, -2.0, 2.0, "b1_grate_red", off=0.0, every=2.0)
    # 上の段（4〜9 m）：管と梁、壁の灯、割れ目は無い（換気の格子を上の壁に）
    for side, plane, a0, a1 in (("s", -Z, -10.0, 10.0), ("w", -X, -10.0, 8.0)):
        d.along(side, plane, a0, a1, "b1_pipe", y=7.4, off=0.62, scale=1.4)
    beams(d, k, -X, X, 9.0, (-8.0, -2.0, 4.0))
    for side, plane, xs in (("s", -Z, (-7.5, 7.5)), ("w", -X, (-7.5, 3.5)), ("e", X, (-7.5,))):
        for a in xs:
            d.at_wall(side, plane, a, "b1_lantern", y=2.4, off=0.3, solid=True)
            # 灯の下の壁の板にさびの筋（灯の金具から垂れる。壁の板の前の面 0.2 m の 1 cm 前）
            for da in (-0.42, 0.42):
                drips(d, side, plane, a + da, 2.05, off=0.21)
    d.at_wall("e", X, -4.9, "b1_redlight", y=2.6, off=0.6)
    d.at_wall("e", X, 4.9, "b1_redlight", y=2.6, off=0.6)
    # 弁の台（形 9・10）：正面に弁の輪（撃つ球はその上）
    for x in (-7.0, 7.0):
        d.put("b2_valve", [x, 0.85, 2.3], 180, solid=True)
    # 床：壁ぎわの排水格子、砂の吹きだまり（隅と壁ぎわ）、かけら、ケーブル（ファンへ）
    d.along("w", -X, -10.0, 6.0, "b1_grate", off=0.5, every=4.0)
    for pos, yaw, sc in (((-10.4, 0, -10.3), 40, 1.4), ((10.4, 0, -10.4), -35, 1.3), ((-10.6, 0, 7.6), 80, 1.2), ((10.6, 0, 7.4), 100, 1.2),
                         ((-11.0, 0, -3.0), 90, 1.1), ((5.0, 0, -11.0), 0, 1.2)):
        d.put("b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    for pos, yaw in (((-9.6, 0, -6.5), 30), ((9.4, 0, -6.0), -50), ((-2.6, 0, 4.4), 120)):
        d.put("b1_debris", pos, yaw, solid=True)
    d.put("b1_cables", [8.6, 0, -2.6], 70)
    d.put("b1_cables", [9.4, 0, 0.6], 95)
    # 砂の吹きだまり（隅と西の壁ぎわ。W2-06b の 01・02）と、ファンの横に落ちた管
    for x, z, yaw in ((-X, -Z, 0), (-X, 9.2, 90), (X, 9.2, 180)):
        d.put("sand_corner", [x, 0, z], yaw)
    d.at_wall("w", -X, -4.0, "sand_wall")
    d.snug("pipe_broken", 90, x1=X - 0.38, z1=8.0)        # 壁の帯（z 6〜8）の前。扉の壁の帯とは 0.84 m 空ける
    # 生活感の小物：前の整備の一団がファンを直そうとした跡（南東の角に道具箱と灯、箱）
    W = X - 0.38
    d.snug("town/chest", 270, x1=W, z0=-W)
    d.put_any("town/hand_lantern", [11.47, 1.0, -11.47], solid=True)
    d.snug("b1_crate", 0, x1=W, z0=-W + 1.06)
    d.snug("town/stool", 0, x1=W - 1.08, z0=-W)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, 9.2, 90), (X, 9.2, 180)],
          doors_at=[(0.0, -10.6, 0), (0.0, 8.0, 0)], path=[(0.0, -9.0), (0.0, 7.6)],
          spots=[(9.6, 0.0, 90, 1.3), (-7.0, 4.4, 0, 0.8), (7.0, 4.4, 0, 0.8)])
    for a in (-6.0, 6.0):
        drips(d, "s", -Z, a, 6.9, long=True, off=0.0)
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 8, 0], "#ffe3a8", 22.5, 2.4), light([-8, 3, 8], "#ffd28a", 12.5, 1.6),
                      light([0, 3.2, -11.0], "#ffbc52", 9.0, 1.4), light([9.6, 2.6, 0], "#ff5a40", 8.0, 1.4)]


def r05(room):
    """崩落床（20×24×8）。真ん中の床が崩れる（形 1 の薄い床・形 2・3 のひび）。奥（北）は崩れた通路の跡（形 4）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b1"
    X, Z = 10.0, 12.0
    g[1]["skin"] = {"floor": "sandfloor", "wall": "metal"}
    for i in (2, 3):
        g[i]["skin"] = "metal"
    g[4]["skin"] = {"wall": "metal", "floor": "plate"}
    walls(d, k, "s", -Z, -9.0, 9.0, skip=[(-1.5, 1.5)])
    door(d, k, "s", -Z, 0.0)
    walls(d, k, "w", -X, -11.0, 11.0)
    walls(d, k, "e", X, -11.0, 11.0)
    walls(d, k, "n", Z, -9.0, 9.0, skip=[(-3.2, 3.2)])
    corners(d, k, -X, X, -Z, Z)
    # 北：崩れた通路（形 4 の箱の前に、崩れた白磁のかけらと砂、上の外殻の割れ目から光）
    d.at_wall("n", Z, 0.0, "b1_crack", y=5.6, scale=[1.6, 1.0, 1.0])
    d.at_wall("n", Z, 0.0, "b1_shaft", y=5.8, off=0.1, shadow=False, scale=[1.2, 0.8, 0.8])
    for pos, yaw in (((-2.2, 0, 9.6), 20), ((1.8, 0, 9.7), -30), ((-4.2, 0, 10.6), 70), ((3.9, 0, 10.4), 160)):
        d.put("b1_debris", pos, yaw, solid=True)
    for pos, yaw, sc in (((0.0, 0, 10.0), 0, 1.6), ((-4.6, 0, 9.6), 20, 1.0), ((4.8, 0, 9.4), -15, 1.1)):
        d.put("b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    # 崩れる床のまわり：注意の灯の柱（崩れる所の外）と、床を這うケーブル
    for x, z in ((-4.7, -0.7), (4.7, -0.7), (-4.7, 6.7), (4.7, 6.7)):
        d.put("b1_post_lamp", [x, 0, z], solid=True)
    d.put("b1_cables", [-6.4, 0, 2.0], 90)
    # 砂の吹きだまり（四隅と、崩れた通路の両脇）と、北の壁から外れて倒れた外装の板
    for (x, z), yaw in (((-X, -Z), 0), ((-X, Z), 90), ((X, Z), 180), ((X, -Z), 270)):
        d.put("sand_corner", [x, 0, z], yaw)
    for a in (-5.2, 5.2):
        d.at_wall("n", Z, a, "sand_wall")
    d.put("panel_fallen", [-7.0, 0, Z - 0.38 - 0.02 - 0.95], 180, solid=True)
    # 上：梁と管、壁の灯
    beams(d, k, -X, X, 8.0, (-6.0, 0.0, 6.0))
    for side, plane in (("w", -X), ("e", X)):
        d.along(side, plane, -10.0, 10.0, "b1_pipe", y=6.8, off=0.62, scale=1.4)
        for a in (-6.0, 6.0):
            d.at_wall(side, plane, a, "b1_lantern", y=2.4, off=0.3, solid=True)
            for da in (-0.42, 0.42):
                drips(d, side, plane, a + da, 2.05, off=0.21)
        # 上の管の継ぎ目の下（4 m の壁の板より上の、殻の壁）にさびの垂れ
        for a in (-7.0, 1.0, 9.0):
            drips(d, side, plane, a, 6.35, long=True)
    d.along("s", -Z, -8.0, -4.0, "b1_grate", off=0.5, every=4.0)
    d.along("s", -Z, 4.0, 8.0, "b1_grate", off=0.5, every=4.0)
    for pos, yaw, sc in (((-8.6, 0, -10.4), 35, 1.3), ((8.6, 0, -10.2), -30, 1.2), ((-8.8, 0, 6.0), 90, 1.4), ((8.7, 0, -2.0), 90, 1.1)):
        d.put("b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    # 生活感の小物：崩れる前に置かれた立入禁止の札代わりの箱（西の壁ぎわ）
    W = X - 0.38
    d.snug("b1_crate_cloth", 90, x0=-W, z=-6.2)
    d.snug("cc0/cask", 0, x0=-W, z1=-6.82 - 0.02)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, -10.6, 0)],
          path=[(0.0, -9.0), (0.0, 1.0)], spots=[(0.0, 8.0, 0, 1.4), (-2.5, 3.5, 30, 1.0), (2.8, 2.2, -20, 0.9)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 7, -3], "#ffe3a8", 18.0, 2.2), light([0, 5.0, 9.6], "#ffd9a0", 12.5, 2.4),
                      light([0, 3.2, -11.0], "#ffbc52", 9.0, 1.4)]


# ================================================================ B2：配管層

def b2_shell(d, room, X, Z, H, s_door=None, n_door=None, n_plane=None, skip_w=(), skip_e=(), skip_s=(), skip_n=()):
    """B2 の部屋の殻：壁の列、角、上の段の太い管（さびの筋つき）、天井の梁と赤い非常灯"""
    k = "b2"
    sk_s = list(skip_s) + ([(s_door - 1.5, s_door + 1.5)] if s_door is not None else [])
    walls(d, k, "s", -Z, -X + 1.0, X - 1.0, skip=sk_s)
    if s_door is not None:
        door(d, k, "s", -Z, s_door)
    np_ = Z if n_plane is None else n_plane
    sk_n = list(skip_n) + ([(n_door - 1.5, n_door + 1.5)] if n_door is not None else [])
    walls(d, k, "n", np_, -X + 1.0, X - 1.0, skip=sk_n)
    walls(d, k, "w", -X, -Z + 1.0, np_ - 1.0, skip=skip_w)
    walls(d, k, "e", X, -Z + 1.0, np_ - 1.0, skip=skip_e)
    for x, z, yaw in ((-X, -Z, 0), (X, -Z, 270), (-X, np_, 90), (X, np_, 180)):
        d.put("b2_corner", [x, 0, z], yaw, solid=True)


def b2_upper(d, X, Z, H, sides=("w", "e"), y=None, ceiling_z=(), red=True):
    """上の段：壁に沿った太い管（継ぎ目からさび水が垂れる）と天井の梁・赤い非常灯"""
    y = y if y is not None else min(H - 1.6, 6.0)
    for side in sides:
        plane = {"w": -X, "e": X, "s": -Z, "n": Z}[side]
        a = Z if side in ("w", "e") else X
        d.along(side, plane, -a + 2.0, a - 2.0, "b2_pipe_drip", y=y, off=0.45, scale=1.25)
    for z in ceiling_z:
        d.row("b2_beam_red" if red else "b2_beam", [-X + 1.0, H, z], [2.0, 0, 0], int(round(X)))


def r06(room):
    """落下地点（22×7×30）。B1 の床が崩れて落ちてきた所：天井の穴、崩れた床板（形 5〜7）、壁ぎわの太い管（形 1〜4）、天井の赤い非常灯（形 8〜11）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b2"
    X, Z, H = 11.0, 15.0, 7.0
    for i in (1, 2, 3, 4):
        g[i]["hide"] = True
    for i in (5, 6, 7):
        g[i]["skin"] = {"wall": "plate", "floor": "sandfloor"}
    for i in (8, 9, 10, 11):
        g[i]["skin"] = "red"
    b2_shell(d, room, X, Z, H, n_door=0.0)
    # 壁ぎわの太い管（形 1・3：1.2 m 角、y 3〜4.2。形 2・4：0.8 m 角、y 5.2〜6）を部品の管で
    for sx, yaw in ((-1, 90), (1, 270)):
        d.row("b2_pipe", [sx * 9.5, 3.6, -12.0], [0, 0, 4.0], 7, yaw, scale=2.0)
        d.row("b2_pipe", [sx * 9.5, 5.6, -12.0], [0, 0, 4.0], 7, yaw, scale=1.333)
    # 天井：梁と、落ちてきた穴（B1 の床の裏の割れ目と砂の筋）
    for z in (-6.0, 0.0, 6.0, 12.0):
        d.row("b2_beam", [-X + 1.0, H, z], [2.0, 0, 0], 11)
    d.put("b1_crack", [0.0, H - 0.02, -12.0], rot=[90, 0, 0], scale=[1.8, 1.0, 1.4])
    d.put("b1_shaft", [0.0, H - 0.1, -12.0], rot=[0, 0, 0], shadow=False, scale=[0.9, 0.9, 0.5])
    # 崩れた床板のまわり：白磁のかけら・砂（上から落ちた B1 の床）
    for pos, yaw in (((-2.6, 0, -9.6), 30), ((2.4, 0, -10.2), -40), ((-1.0, 0, -6.6), 100), ((3.4, 0, -7.0), 200), ((-6.8, 0, -7.4), 60)):
        d.put("b1_debris", pos, yaw, solid=True)
    for pos, yaw, sc in (((0.0, 0, -9.0), 0, 1.6), ((-4.0, 0, -6.5), 30, 1.0), ((4.2, 0, -4.4), -20, 0.9)):
        d.put("b1_sand", pos, yaw, scale=[sc, 1.0, sc])
    # 床：真ん中の排水溝の列（出口へ）、濡れた床、蒸気
    d.row("b2_drain", [0.0, 0, -4.0], [0, 0, 4.0], 4, 90)
    for pos, yaw in (((-5.6, 0, 2.6), 20), ((5.8, 0, 8.6), -30), ((-3.6, 0, 11.2), 10)):
        d.put("b2_puddle", pos, yaw)
    for x, z in ((-9.0, -3.0), (9.0, 6.0)):
        d.put("b2_steam", [x, 4.2, z], rot=[180, 0, 0], shadow=False)
    # 非常灯：出口の扉の上と、通路の床の道標（赤い非常灯の列は天井の形 8〜11）
    for a in (-6.0, 6.0):
        d.at_wall("n", Z, a, "b2_guide")
    for z in (-6.0, 0.0, 6.0):
        for side, plane in (("w", -X), ("e", X)):
            d.at_wall(side, plane, z, "b2_guide")
    # 上から落ちてきた B1 の外装の板（崩れた床の塊（形 5）にもたれる）と、壁ぎわの割れた管、南の隅の砂
    d.put("panel_fallen", [-5.0, 0, -5.25 - 0.02 - 0.95], 180, solid=True)
    d.snug("pipe_broken", 90, x1=X - 0.38, z=4.0)
    d.put("sand_corner", [-X, 0, -Z], 0)
    d.put("sand_corner", [X, 0, -Z], 270)
    # 生活感の小物：落ちてきた荷（B1 の回収の箱が一緒に落ちた）。宝箱（-8, 11）から 0.5 m 以上
    d.snug("b1_crate_cloth", 30 - 30, x=6.6, z=-10.6)
    d.put("b1_cables", [5.2, 0, -8.2], 40)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, 13.6, 0)],
          path=[(0.0, -10.0), (0.0, 12.0)], spots=[(-9.0, 2.0, 90, 1.2), (9.0, -8.0, 90, 1.1)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    lights = [l for l in room.get("lights", []) if l["color"] == "#ff4a3a"]
    room["lights"] = lights + [light([0, 5.5, -12], "#ffd9a0", 10.0, 1.2), light([0, 3.0, 13.4], "#ffbc52", 7.0, 1.2)]


def r07(room):
    """追跡通路（6×5×40）。互い違いの配管の壁（形 1〜4）のすき間（2.2 m）を抜ける。すき間を狭めないよう、長い壁には壁の帯を置かない
    （平らな壁の部品 b2_wall_flat、壁から 0.12 m まで）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b2"
    X, Z, H = 3.0, 20.0, 5.0
    for i in (1, 2, 3, 4):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b2_pipewall", [p[0], 0, p[2]])
    for side, plane in (("w", -X), ("e", X)):
        d.along(side, plane, -19.0, 19.0, "b2_wall_flat")
        d.along(side, plane, -18.0, 18.0, "b2_pipe", y=4.4, off=0.3, scale=[1.0, 0.6, 0.6], every=2.0)
    door(d, k, "s", -Z, 0.0, width=3.0, solid=False)
    d.at_wall("s", -Z, -2.25, "b2_wall_flat", scale=[0.75, 1.0, 1.0])
    d.at_wall("s", -Z, 2.25, "b2_wall_flat", scale=[0.75, 1.0, 1.0])
    door(d, k, "n", Z, 0.0, width=3.0, solid=False)
    d.at_wall("n", Z, -2.25, "b2_wall_flat", scale=[0.75, 1.0, 1.0])
    d.at_wall("n", Z, 2.25, "b2_wall_flat", scale=[0.75, 1.0, 1.0])
    # 天井：配管の壁の間に赤い非常灯の梁
    for z in (-15.0, -11.5, -4.5, 2.5, 9.0, 15.0):
        d.row("b2_beam_red", [-2.0, H, z], [2.0, 0, 0], 3)
    # 床：真ん中の排水溝、濡れた床、配管の壁の継ぎ目からの蒸気
    for z0, n in ((-18.0, 4), (-6.0, 2), (0.5, 2), (7.5, 2), (13.5, 2)):
        d.row("b2_drain", [0.0, 0, z0 + 1.0], [0, 0, 2.0], n, 90)
    for pos, yaw in (((-1.5, 0, -12.5), 0), ((1.6, 0, 3.6), 20), ((-1.4, 0, 10.0), -10)):
        d.put("b2_puddle", pos, yaw, scale=[0.7, 1.0, 0.7])
    for p in (g[1]["pos"], g[3]["pos"]):
        d.put("b2_steam", [p[0] + 1.6, 4.4, p[2] + 0.7], rot=[180, 0, 0], shadow=False)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, -18.8, 0), (0.0, 16.6, 0)],
          spots=[(-2.0, -8.0 + 1.2, 0, 0.6), (2.0, -1.0 + 1.2, 0, 0.6), (-2.0, 6.0 + 1.2, 0, 0.6), (2.0, 12.0 + 1.2, 0, 0.6)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [l for l in room.get("lights", []) if l["color"] == "#ff4a3a"] + [light([0, 3.4, 16.4], "#6fe3d6", 6.0, 0.8)]


def r08(room):
    """封印室（22×8×22）。物語の舞台：絵 ruins_seal_room（台座と可動リング、赤い非常灯の両脇、血縁で琥珀の回路が通電）。
    台座（形 1・2）、四隅の留め具（形 3〜6）、円く並んだ柱 8 本（形 7〜14）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b2"
    X, Z, H = 11.0, 11.0, 8.0
    g[1]["skin"] = {"wall": "metal", "floor": "plate"}
    g[2]["skin"] = "metal"
    for i in (3, 4, 5, 6):
        g[i]["skin"] = "metal"
    for i in range(7, 15):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b2_pillar", [p[0], 0, p[2]], scale=[2.0, 1.125, 2.0])
    b2_shell(d, room, X, Z, H, s_door=0.0, n_door=0.0)
    # 台座の飾り（縁・封印の板・床の琥珀の回路）と、上の可動リング
    d.put("b2_seal_dais", [0, 0, 0])
    d.put("b2_seal_ring", [0, 0, 0])
    # 上：東西の壁の太い管（両脇の配管）、天井の梁と赤い非常灯
    for sx, yaw in ((-1, 90), (1, 270)):
        d.row("b2_pipe_drip", [sx * 10.4, 5.4, -8.0], [0, 0, 4.0], 5, yaw, scale=1.5)
        d.row("b2_pipe", [sx * 10.5, 6.8, -8.0], [0, 0, 4.0], 5, yaw, scale=1.0)
    for z in (-7.0, 7.0):
        d.row("b2_beam_red", [-10.0, H, z], [2.0, 0, 0], 11)
    for x in (-4.0, 4.0):
        d.row("b2_redlight", [x, H, -4.0], [0, 0, 4.0], 3)
    # 蒸気（両脇の管の継ぎ目）
    for x, z in ((-9.6, -3.0), (9.6, 3.0)):
        d.put("b2_steam", [x, 4.4, z], rot=[180, 0, 0], shadow=False)
    # 床：入口から台座への道標（低い琥珀の灯）、壁ぎわの排水溝
    for side, plane in (("w", -X), ("e", X)):
        for a in (-6.0, -2.0, 2.0, 6.0):
            d.at_wall(side, plane, a, "b2_guide")
    d.along("s", -Z, -8.0, -4.0, "b2_drain", off=0.8, every=4.0)
    d.along("s", -Z, 4.0, 8.0, "b2_drain", off=0.8, every=4.0)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, -9.4, 0), (0.0, 9.4, 0)],
          spots=[(-9.0, -6.0, 90, 1.0), (9.0, 6.0, 90, 1.0)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    # 光：台座の琥珀（通電した回路）と両脇の赤い非常灯、上からの弱い光
    room["lights"] = [light([0, 3.0, 0], "#ffb45a", 14.0, 2.6), light([0, 7.0, 0], "#c8b8a0", 22.0, 1.0),
                      light([-9.0, 3.2, 0], "#ff4a3a", 8.0, 1.4), light([9.0, 3.2, 0], "#ff4a3a", 8.0, 1.4)]


def r09(room):
    """配管広間（20×8×24）。縦の配管（形 3〜7）が遮蔽物。全滅まで奥の扉（形 1・2 の壁の間）が閉じる"""
    g = room["geometry"]
    d = D.Dress()
    k = "b2"
    X, Z, H = 10.0, 12.0, 8.0
    for i in (1, 2):
        g[i]["skin"] = {"wall": "wall", "floor": "metal"}
    for i in (3, 4, 5, 6, 7):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b2_pipecluster", [p[0], 0, p[2]])
    for i in (8, 9):
        g[i]["skin"] = {"wall": "metal", "floor": "plate"}
    # 扉の壁の南の面：低い壁（形 9、x 1.25〜4.75）の後ろは空ける（帯との間 0.54 m がふさがれて、見えない棚になる）
    b2_shell(d, room, X, Z, H, s_door=0.0, n_plane=9.2, skip_n=[(-3.0, 4.75)])
    # 扉の上（4〜8 m）と、扉の奥の小部屋の出口の扉
    d.row("b2_wall", [-2.0, 4.0, 9.2], [2.0, 0, 0], 3, 180)
    door(d, k, "n", Z, 0.0)
    walls(d, k, "n", Z, -4.0, 4.0, skip=[(-1.5, 1.5)], solid=False)
    b2_upper(d, X, Z, H, sides=("w", "e"), y=5.6, ceiling_z=(-8.0, -3.0, 2.0, 7.0))
    d.row("b2_pipe_drip", [-8.0, 5.6, -11.55], [4.0, 0, 0], 5, 0, scale=1.25)
    # 床：排水溝、濡れた床、蒸気（配管の束から）
    d.row("b2_drain", [-6.0, 0, -9.6], [4.0, 0, 0], 4)
    for pos, yaw in (((-6.4, 0, 0.8), 20), ((6.2, 0, -5.6), -40), ((2.4, 0, 3.6), 70)):
        d.put("b2_puddle", pos, yaw, scale=[0.8, 1.0, 0.8])
    for x, z in ((-5.0, -2.0), (5.0, 5.0), (0.0, 1.5)):
        d.put("b2_steam", [x + 0.75, 6.6, z], rot=[180, 0, 0], shadow=False)
    # 生活感の小物：南西の角に、前に誰かが積んだ箱（拾う物のセル（-8.5, -9）から 0.5 m 以上）
    W = X - 0.38
    d.snug("b1_crate", 0, x0=-W, z0=-(Z - 0.38))
    d.snug("cc0/cask", 0, x0=-W + 1.06, z0=-(Z - 0.38))
    # 崩れた白磁のかけら（隅）と、壁ぎわを這うケーブル
    d.put("b1_debris", [-8.5, 0, 7.4], 110, solid=True)
    d.snug("pipe_broken", 0, x1=X - 0.38, z0=-(Z - 0.38))
    d.put("b1_cables", [-9.3, 0, -4.0], 90)
    d.put("b1_cables", [9.3, 0, 1.0], 270)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, 9.2, 90), (X, 9.2, 180)], doors_at=[(0.0, -10.6, 0), (0.0, 8.0, 0)],
          path=[(0.0, -9.0), (0.0, -3.4), (-2.6, 1.4), (0.0, 7.6)], spots=[(-5.0, -0.4, 0, 0.9), (5.0, 6.6, 0, 0.9), (0.0, 3.1, 0, 0.8)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 6.5, -8], "#c8b8a0", 15.0, 1.6), light([0, 6.5, 2], "#c8b8a0", 15.0, 1.6),
                      light([-8, 2.5, -8], "#ff4a3a", 7.5, 1.4), light([8, 2.5, 4], "#ff4a3a", 7.5, 1.4),
                      light([0, 3.2, 8.4], "#ffbc52", 8.0, 1.2)]


def r10(room):
    """弁の間（20×8×24）。扉の上の弁の輪（撃つ）＋全滅で扉が開く。台（形 4・5）、低い壁（形 6）、太い配管の柱（形 7・8）、弁の上の梁（形 3）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b2"
    X, Z, H = 10.0, 12.0, 8.0
    for i in (1, 2):
        g[i]["skin"] = {"wall": "wall", "floor": "metal"}
    g[3]["skin"] = "metal"
    for i in (4, 5):
        g[i]["skin"] = {"wall": "metal", "floor": "plate"}
    g[6]["skin"] = {"wall": "metal", "floor": "plate"}
    for i in (7, 8):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b2_pipecluster", [p[0], 0, p[2]], scale=[1.143, 1.0, 1.143])
    b2_shell(d, room, X, Z, H, s_door=0.0, n_plane=9.2, skip_n=[(-3.0, 3.0)])
    door(d, k, "n", Z, 0.0)
    walls(d, k, "n", Z, -4.0, 4.0, skip=[(-1.5, 1.5)], solid=False)
    # 大きな弁の輪（撃つ球 (0, 5, 10.6) が輪の芯。軸は奥の壁へ、上の梁（形 3）へ吊りの棒）
    d.put("b2_valve_big", [0.0, 5.0, Z], 180)
    b2_upper(d, X, Z, H, sides=("w", "e"), y=5.6, ceiling_z=(-8.0, -3.0, 2.0))
    # 台の正面の弁（形 4・5 の南の面）
    for x in (-6.0, 6.0):
        d.put("b2_valve", [x, 1.2, -0.8], 180, solid=True)
    d.row("b2_drain", [-6.0, 0, -9.6], [4.0, 0, 0], 4)
    d.put("b1_cables", [-6.0, 0, -1.6], 0)
    d.put("b1_cables", [6.0, 0, -1.6], 180)
    for pos, yaw in (((-3.4, 0, -3.0), 20), ((5.2, 0, 4.6), -40)):
        d.put("b2_puddle", pos, yaw, scale=[0.8, 1.0, 0.8])
    for x, z in ((-8.0, -4.0), (8.0, -4.0)):
        d.put("b2_steam", [x + 0.85, 6.4, z], rot=[180, 0, 0], shadow=False)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, 9.2, 90), (X, 9.2, 180)], doors_at=[(0.0, -10.6, 0), (0.0, 8.0, 0)],
          path=[(0.0, -9.0), (0.0, 2.4), (0.0, 7.6)], spots=[(-6.0, 1.4, 0, 0.9), (6.0, 1.4, 0, 0.9), (0.0, 8.6, 0, 1.0)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 6.5, -7], "#c8b8a0", 15.0, 1.6), light([0, 6.5, 2], "#c8b8a0", 15.0, 1.6),
                      light([0, 4.2, 9.8], "#ff4a3a", 10.0, 2.0), light([-8.6, 2.6, 6.0], "#ffbc52", 7.0, 1.0)]


def r11(room):
    """縦坑（12×24×12）。足場（形 1〜10）を跳び移って下る。底にビーコン。縦の太い管と輪の梁、足場の受け"""
    g = room["geometry"]
    d = D.Dress()
    k = "b2"
    X, Z, H = 6.0, 6.0, 24.0
    g[0]["skin"] = {"wall": "panel", "floor": "floor", "ceiling": "ceiling"}       # 縦坑の高い壁は白磁の 2 m の板（上から垂れる筋）
    for i in range(1, 11):
        g[i]["skin"] = {"floor": "floor", "wall": "metal"}
    # 底の壁の列（北に出口の扉）
    walls(d, k, "s", -Z, -5.0, 5.0)
    walls(d, k, "n", Z, -5.0, 5.0, skip=[(-1.5, 1.5)])
    door(d, k, "n", Z, 0.0)
    walls(d, k, "w", -X, -5.0, 5.0)
    walls(d, k, "e", X, -5.0, 5.0)
    corners(d, k, -X, X, -Z, Z)
    # 上の出口（r10 へ、y 21 の踊り場（形 10）の西の壁）
    door(d, k, "w", -X, -4.6, width=2.0, y=21.0, solid=False)
    # 縦の太い管（四隅の近く、底から天井まで）と、6 m ごとの壁の輪の梁・赤い非常灯
    # 縦の管は足場の当たり判定の外（隅の 0.6 m の柱の所だけ。足場から 0.3 m 以上）
    for x, z in ((5.4, 5.4), (-5.4, 4.8), (5.4, -5.0)):
        d.row("b2_pipe", [x, 2.0, z], [0, 4.0, 0], 6, rot=[0, 0, 90], scale=[2.0, 1.0, 1.0])
    for y in (6.0, 12.0, 18.0):
        d.at_wall("n", Z, -3.0, "b1_redlight", y=y - 1.0, off=0.1)
        d.at_wall("s", -Z, 3.0, "b1_redlight", y=y - 1.0, off=0.1)
    # 足場の受け（壁から足場の下へ）
    for i in range(1, 9):
        p, sz = g[i]["pos"], g[i]["size"]
        top = p[1] + sz[1]
        if top < 1.5:
            continue
        x, z = p[0], p[2]
        if abs(x) >= abs(z):
            side, plane, a = ("e", X, z) if x > 0 else ("w", -X, z)
        else:
            side, plane, a = ("n", Z, x) if z > 0 else ("s", -Z, x)
        d.at_wall(side, plane, round(a, 2), "b1_bracket", y=round(p[1], 2))
    # 底：ビーコンのまわりの床の輪（排水溝）、濡れた床、蒸気
    d.put("b2_drain", [0.0, 0, -3.2])
    d.put("b2_puddle", [-2.8, 0, 2.6], 30, scale=[0.7, 1.0, 0.7])
    d.put("b2_steam", [5.2, 3.0, -2.8], rot=[180, 0, 0], shadow=False)
    for side, plane in (("w", -X), ("e", X)):
        d.at_wall(side, plane, 0.0, "b2_guide")
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, 4.6, 0)],
          spots=[(0.0, -1.0, 0, 0.9)])
    for side, plane, a in (("w", -X, 2.0), ("e", X, -2.0), ("n", Z, 3.0)):
        drips(d, side, plane, a, 15.0, long=True)
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 21, 0], "#d8c8b0", 14.0, 2.4), light([0, 15, 0], "#ff6a4a", 12.0, 1.8),
                      light([0, 9, 0], "#d8c8b0", 14.0, 2.4), light([0, 3.0, 0], "#ffbc52", 12.0, 2.4)]


# ================================================================ B3：駆動層

def b3_shell(d, k, X, Z, n_plane=None, s_door=None, n_door=None, skip_w=(), skip_e=(), skip_s=(), skip_n=(), solid=True):
    sk_s = list(skip_s) + ([(s_door - 1.5, s_door + 1.5)] if s_door is not None else [])
    walls(d, k, "s", -Z, -X + 1.0, X - 1.0, skip=sk_s, solid=solid)
    if s_door is not None:
        door(d, k, "s", -Z, s_door)
    np_ = Z if n_plane is None else n_plane
    sk_n = list(skip_n) + ([(n_door - 1.5, n_door + 1.5)] if n_door is not None else [])
    walls(d, k, "n", np_, -X + 1.0, X - 1.0, skip=sk_n, solid=solid)
    if n_door is not None:
        door(d, k, "n", np_, n_door)
    walls(d, k, "w", -X, -Z + 1.0, np_ - 1.0, skip=skip_w, solid=solid)
    walls(d, k, "e", X, -Z + 1.0, np_ - 1.0, skip=skip_e, solid=solid)
    for x, z, yaw in ((-X, -Z, 0), (X, -Z, 270), (-X, np_, 90), (X, np_, 180)):
        d.put(KITS[k]["corner"], [x, 0, z], yaw, solid=solid)


def drives(d, side, plane, a0, a1, y=0.0):
    """壁の足元の駆動梁（壁の帯の内）"""
    n = int(round((a1 - a0) / 2.0)) + 1
    for i in range(n):
        d.at_wall(side, plane, round(a0 + 2.0 * i, 3), "b3_drive", y=y, solid=True)


def r12(room):
    """駆動回廊（16×48×38、床は y -36。入口と出口の床の段（形 1・2）は y 0）。穴の上をピストン（動く足場 3 つ）で渡る。
    西の壁にひび（ドリルで壊す → r14）、東に近道のエレベーター（形 3）、動力の球 2 つ"""
    g = room["geometry"]
    d = D.Dress()
    k = "b3"
    X = 8.0
    g[1]["skin"] = {"floor": "floor", "wall": "wall"}
    g[2]["skin"] = {"floor": "floor", "wall": "wall"}
    g[3]["skin"] = "metal"
    for i in range(4, 12):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b3_pillar", [p[0], 0, p[2]], scale=[1.667, 3.0, 2.333])
        d.at_wall("e" if p[0] > 0 else "w", X if p[0] > 0 else -X, p[2], "b3_rib", y=-12.0, scale=[1.6, 1.5, 1.5])
    # 入口の段（z -19〜-10）：南の壁（出口 r11）、東西の壁（西は開口・東はエレベーター）。
    # 南の壁と段（z -18）の間は幅 1 m の溝（穴の底まで）：壁の帯を置くと溝が 0.64 m になり、落ちた体が溝の両側に引っかかって
    # 宙に止まった（詰み探し）。南の壁の部品は当たり判定なし（溝に落ちれば今までどおり穴の底へ）
    walls(d, k, "s", -19.0, -7.0, 7.0, skip=[(-1.5, 1.5)], solid=False)
    door(d, k, "s", -19.0, 0.0, solid=False)
    for side, plane in (("w", -X), ("e", X)):
        walls(d, k, side, plane, -18.0, -10.0, skip=[(-19.0, -12.0)])
        walls(d, k, side, plane, -18.0, -18.0, solid=False)
    d.put("b3_corner", [-X, 0, -19.0], 0)
    d.put("b3_corner", [X, 0, -19.0], 270)
    # 出口の段（z 15〜19）：北の壁（出口 r13）
    walls(d, k, "n", 19.0, -7.0, 7.0, skip=[(-1.5, 1.5)])
    door(d, k, "n", 19.0, 0.0)
    for side, plane in (("w", -X), ("e", X)):
        walls(d, k, side, plane, 16.0, 18.0)
    d.put("b3_corner", [-X, 0, 19.0], 90, solid=True)
    d.put("b3_corner", [X, 0, 19.0], 180, solid=True)
    # 穴の上の壁（足場は無い：当たり判定は付けない）と、穴の中の壁の梁・大きな歯車・ピストン
    for side, plane in (("w", -X), ("e", X)):
        walls(d, k, side, plane, -8.0, 14.0, skip=[(-6.8, -5.2), (-0.8, 0.8), (5.2, 6.8), (11.2, 12.8)], solid=False)
        walls(d, k, side, plane, -8.0, 14.0, y=-4.0, solid=False, parts=("b3_wall_plain",))
    for sx in (-1, 1):
        d.put("b3_gear", [sx * (X - 0.3), -5.5, 3.0], 90 if sx < 0 else 270, scale=1.4)
        d.put("b3_gear_small", [sx * (X - 0.3), -2.8, -3.0], 90 if sx < 0 else 270, scale=1.2)
    for z in (-5.5, 2.5, 10.5):
        d.put("b3_piston", [0.0, -12.0, z], scale=[2.2, 1.5, 2.2])
    # 穴の縁：入口と出口の段の縁に駆動梁（床の縁）と琥珀の道標
    # 段の縁の面（穴の側。床の下 0.34 m から）に駆動梁：床の上には出さない（跳ぶ所に段を作らない）
    d.row("b3_drive", [-6.0, -0.34, -10.0], [2.0, 0, 0], 7, 0)
    d.row("b3_drive", [-6.0, -0.34, 15.0], [2.0, 0, 0], 7, 180)
    # 天井 12 m：梁
    beams(d, k, -X, X, 12.0, (-14.0, -6.0, 2.0, 10.0, 17.0))
    # 動力の球の台座と、台座から壁へのケーブル
    for x in (-5.0, 5.0):
        d.put("b3_orb_base", [x, 0, -17.0], solid=True)
        d.put("b1_cables", [x * 1.36, 0, -18.1], 0 if x < 0 else 180, scale=[0.8, 1.0, 1.0])
    # 近道のエレベーターの扉（形 3 の西の面）
    d.at_wall("e", 7.4, -14.0, "b3_door", scale=[2.0, 1.0, 1.0])
    d.at_wall("e", 7.4, -16.3, "b1_redlight", y=2.4, off=0.05)
    d.at_wall("e", 7.4, -11.7, "b1_redlight", y=2.4, off=0.05)
    grime(d, corners_at=[(-X, -19.0, 0), (X, -19.0, 270), (-X, 19.0, 90), (X, 19.0, 180)], doors_at=[(0.0, -17.6, 0), (0.0, 17.6, 0)],
          path=[(0.0, -16.5), (0.0, -11.0)], spots=[(-5.0, -15.6, 0, 0.8), (5.0, -15.6, 0, 0.8), (5.8, -12.6, 90, 0.9), (0.0, 16.4, 0, 0.9)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 8, -14], "#ffb050", 18.0, 2.4), light([0, 8, 2], "#ffa24a", 22.5, 2.2),
                      light([0, 8, 16], "#ffa24a", 16.0, 2.2), light([0, -6, 3], "#ff4a3a", 14.0, 1.6)]


def r13(room):
    """歯車の間（20×12×30）。歯車のリフト（動く足場 2 つ）で奥の張り出し（形 1、y 4）へ。台（形 2・3）、壁の歯車箱（形 4〜9）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b3"
    X, Z, H = 10.0, 15.0, 12.0
    g[1]["skin"] = {"wall": "plate", "floor": "floor"}
    # 台と壁の歯車箱は白磁の板（黒鉛の面だと、壁に黒い箱が並んで見えた）
    for i in (2, 3):
        g[i]["skin"] = {"wall": "plate", "floor": "metal"}
    for i in range(4, 10):
        g[i]["skin"] = {"wall": "plate", "floor": "metal", "ceiling": "metal"}
    # 壁の列（壁の歯車箱の当たり判定は形のまま。壁の部品は 0〜4 m）
    b3_shell(d, k, X, Z, s_door=0.0, n_door=0.0)
    # 上の段：大きな歯車（北の壁・南の壁の上、届かない高さ）と、壁の歯車箱の横の小さな歯車
    d.at_wall("n", Z, -6.5, "b3_gear", y=8.0, off=0.3, scale=1.3)
    d.at_wall("n", Z, 6.5, "b3_gear", y=8.6, off=0.3, scale=1.1)
    d.at_wall("s", -Z, -6.0, "b3_gear", y=8.4, off=0.3, scale=1.2)
    d.at_wall("s", -Z, 6.5, "b3_gear_small", y=7.4, off=0.25, scale=1.2)
    beams(d, k, -X, X, H, (-10.0, -4.0, 2.0, 8.0))
    for side, plane in (("w", -X), ("e", X)):
        d.along(side, plane, -12.0, 12.0, "b3_rib", y=4.0, every=8.0)
    # 昇降台の床の印（動く足場のまわりの床の排水溝。床から 3 cm の薄い物：足場の下・まわりに段を作らない）
    for cx, cz in ((-5.5, 5.0), (5.5, 3.0)):
        for sz_ in (-1, 1):
            d.put("b2_drain", [cx, 0, round(cz + sz_ * 2.15, 3)], scale=[1.8, 1.0, 0.6])
    drives(d, "s", -Z, -8.0, -4.0)
    drives(d, "s", -Z, 4.0, 8.0)
    # 壁の歯車箱（形 4〜9）の上の壁のすす（歯車の油と熱）
    for i in range(4, 10):
        p = g[i]["pos"]
        side, plane = ("w", -X) if p[0] < 0 else ("e", X)
        d.at_wall(side, plane, p[2], "stain_soot", y=p[1] + 2.4, off=0.0, scale=[1.2, 0.9, 1.0])
    # 生活感の小物：歯車に油を差していた一団の樽と道具箱（南の壁ぎわ、入口の扉の東）
    W = X - 0.38
    d.snug("cc0/cask", 0, x0=5.4, z0=-(Z - 0.38))
    d.snug("cc0/cask", 0, x0=6.14, z0=-(Z - 0.38))
    d.snug("town/chest", 0, x0=6.88, z0=-(Z - 0.38))
    d.put_any("town/hand_lantern", [7.6, 1.0, -14.4], solid=True)
    d.put("b1_cables", [4.6, 0, -13.2], 20)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, -13.6, 0), (0.0, 13.6, 0)],
          path=[(0.0, -12.0), (0.0, 0.0), (-5.5, 5.0)], spots=[(-7.0, -1.8, 0, 1.0), (7.0, -1.8, 0, 1.0), (5.5, 3.0, 0, 1.1), (6.4, -13.0, 0, 0.9)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 10, -6], "#ffa24a", 20.0, 2.6), light([0, 10, 8], "#ffb050", 20.0, 2.6),
                      light([-9, 3, -9], "#ff4a3a", 8.0, 1.2), light([0, 6.5, 11.5], "#ffbc52", 8.0, 1.4)]


def r14(room):
    """隠し部屋（10×6×10）。ひび割れた壁の奥。台座（形 1）にライフコア、宝箱。誰かが隠した物：昔の回収屋の野営の跡"""
    g = room["geometry"]
    d = D.Dress()
    k = "b3"
    X, Z = 5.0, 5.0
    g[1]["skin"] = {"wall": "metal", "floor": "glow"}
    walls(d, k, "s", -Z, -4.0, 4.0)
    walls(d, k, "n", Z, -4.0, 4.0)
    walls(d, k, "w", -X, -4.0, 4.0)
    walls(d, k, "e", X, -4.0, 4.0, skip=[(-2.0, 2.0)])
    corners(d, k, -X, X, -Z, Z)
    # 東の入口（壊した壁）：崩れた白磁のかけらと砂
    d.put("b1_sand", [4.0, 0, -2.6], 90, scale=[0.8, 1.0, 0.8])
    d.put("b1_sand", [4.0, 0, 2.6], 90, scale=[0.8, 1.0, 0.8])
    # 台座のまわりの床の琥珀の線（台座の縁から 2 cm）と、天井の梁
    beams(d, k, -X, X, 6.0, (-2.0, 2.0))
    # 昔の回収屋の野営（北西の角）：布の箱・樽・携行灯・ケーブル（宝箱（-3.5, -3.5）から 0.5 m 以上）
    W = X - 0.38
    d.snug("b1_crate_cloth", 0, x0=-W, z1=W)
    d.snug("town/sacks", 0, x0=-W + 1.18, z1=W)
    d.snug("cc0/cask", 0, x1=W, z1=W)
    d.put_any("town/hand_lantern", [-4.47, 1.04, 4.47], solid=True)
    d.put("b1_cables", [-1.6, 0, 3.4], 10)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(3.4, 0.0, 90)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 4, 0], "#ffb050", 12.0, 2.6), light([-3.8, 1.8, 3.8], "#ffbc52", 5.0, 1.0)]


def r15(room):
    """伝導路（20×9×24）。頭の上を往復する足場（動く足場 2 つ）。柱（形 1〜3）、低い壁（形 4・5）、宝箱の台（形 6）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b3"
    X, Z, H = 10.0, 12.0, 9.0
    for i in (1, 2, 3):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b3_pillar", [p[0], 0, p[2]], scale=[2.667, 2.25, 2.667])
    for i in (4, 5):
        g[i]["skin"] = {"wall": "plate", "floor": "metal"}
    g[6]["skin"] = "metal"
    b3_shell(d, k, X, Z, s_door=0.0, n_door=0.0, skip_e=[(9.0, 11.0)])
    # 伝導路：壁の足元の駆動梁（琥珀の灯）と天井の梁、上の段の管
    drives(d, "w", -X, -10.0, 10.0, y=0.0)
    beams(d, k, -X, X, H, (-8.0, -3.0, 2.0, 7.0))
    for side, plane in (("w", -X), ("e", X)):
        d.along(side, plane, -10.0, 10.0, "b3_pipe", y=6.2, off=0.4, every=2.0)
        d.along(side, plane, -8.0, 8.0, "b3_rib", y=4.0, every=8.0)
    for side, plane in (("s", -Z), ("n", Z)):
        d.at_wall(side, plane, -6.0, "b3_gear_small", y=6.4, off=0.25, scale=1.1)
        d.at_wall(side, plane, -6.0, "stain_soot", y=4.0, scale=[1.0, 0.8, 1.0])
    # 生活感の小物：北西の角に、前に通った一団の箱と樽（足場の下の通り道・宝箱から離す）
    W = X - 0.38
    d.snug("b1_crate_cloth", 0, x0=-W, z1=W)
    d.snug("cc0/cask", 0, x0=-W + 1.18, z1=W)
    d.put("b1_cables", [-6.6, 0, 10.6], 10)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, -10.6, 0), (0.0, 10.6, 0)],
          path=[(0.0, -9.0), (-3.0, -3.6), (-3.0, 3.6), (0.0, 9.0)], spots=[(0.0, 8.2, 0, 0.9), (0.0, -7.2, 0, 0.9), (8.6, 10.0, 90, 0.8)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 8, -8], "#ffa24a", 17.5, 2.2), light([0, 8, 2], "#ffa24a", 17.5, 2.2),
                      light([0, 8, 9], "#ffb050", 14.0, 2.0), light([-9.4, 1.0, 0], "#ffbc52", 8.0, 1.0)]


def r16(room):
    """中央縦坑（12×26×12）。上の段（形 1 の上、y 20）からリフト（乗ると下へ 20 m）で底へ。底に待ち伏せ"""
    g = room["geometry"]
    d = D.Dress()
    k = "b3"
    X, Z, H = 6.0, 6.0, 26.0
    g[1]["skin"] = {"wall": "wall", "floor": "floor"}
    # 底の壁の列（北に出口の扉、南は上の段の壁（形 1 の北の面 z -2.4））
    walls(d, k, "n", Z, -5.0, 5.0, skip=[(-1.5, 1.5)])
    door(d, k, "n", Z, 0.0)
    # 上の段（形 1）の東西の横は幅 1 m のすき間（y 20 から床まで）。z -2.4 で部屋へ開く：口をふさがない
    # （壁の帯・角の柱を置くと、口が 0.64 m になり、上から落ちた体が出られなくなった（詰み探し））
    walls(d, k, "w", -X, 0.6, 4.6)
    walls(d, k, "e", X, 0.6, 4.6)
    walls(d, k, "s", -2.4, -4.0, 4.0, parts=("b3_wall_plain",))
    for x, z, yaw in ((-X, Z, 90), (X, Z, 180)):
        d.put("b3_corner", [x, 0, z], yaw, solid=True)
    # リフトのガイド（上の段の北の面の縦の梁、リフトの外の x ±3.1。底から上の段まで）
    for x in (-3.1, 3.1):
        d.row("b3_rib", [x, 0.0, -2.4], [0, 8.0, 0], 3, 0, scale=[1.0, 1.0, 0.85])
    # 上の段（y 20）の壁と、縦坑の壁の梁・赤い非常灯・歯車
    walls(d, k, "s", -Z, -5.0, 5.0, y=20.0, solid=False, skip=[(-1.5, 1.5)])
    door(d, k, "s", -Z, 0.0, y=20.0, solid=False)
    for side, plane in (("w", -X), ("e", X)):
        d.along(side, plane, -4.0, 4.0, "b3_rib", y=4.0, every=4.0)
        d.along(side, plane, -4.0, 4.0, "b3_rib", y=12.0, every=4.0)
    d.at_wall("n", Z, 0.0, "b3_gear", y=12.0, off=0.3, scale=1.2)
    d.at_wall("n", Z, -3.6, "b3_gear_small", y=17.0, off=0.25, scale=1.0)
    for y in (6.0, 14.0, 22.0):
        d.at_wall("w", -X, 0.0, "b1_redlight", y=y, off=0.05)
        d.at_wall("e", X, 0.0, "b1_redlight", y=y, off=0.05)
    beams(d, k, -X, X, H, (-3.0, 3.0))
    # 待ち伏せの跡：北の壁から外れて倒れた外装の板（突撃型がぶつかった）、壁と床のすす、ケーブル
    d.put("panel_fallen", [-4.5, 0, Z - 0.38 - 0.02 - 0.95], 180, solid=True)
    d.at_wall("n", Z, 3.6, "stain_soot", y=0.0, scale=[1.2, 1.0, 1.0])
    d.at_wall("e", X, 2.0, "stain_soot", y=0.0)
    d.put("b1_cables", [4.6, 0, -1.4], 90)
    grime(d, corners_at=[(-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, 4.6, 0)],
          spots=[(0.0, 0.4, 0, 1.2)])
    d.put("stain_floor", [0.0, 20.0, -4.0], 0, scale=[1.2, 1.0, 1.0])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 22, 0], "#ffa24a", 14.0, 2.2), light([0, 15, 0], "#ff4a3a", 12.0, 1.4),
                      light([0, 8, 0], "#ffa24a", 14.0, 2.0), light([0, 2.4, 0], "#ffa24a", 14.0, 2.2)]


def r17(room):
    """近道（12×6×12）。内側のレバー（形 2・端末）で近道を開ける。西の壁に r02 へのエレベーター（形 1）、東に r12 への口"""
    g = room["geometry"]
    d = D.Dress()
    k = "b3"
    X, Z = 6.0, 6.0
    g[1]["skin"] = "metal"
    g[2]["skin"] = "metal"
    walls(d, k, "s", -Z, -5.0, 5.0)
    walls(d, k, "n", Z, -5.0, 5.0)
    walls(d, k, "w", -X, -5.0, 5.0, skip=[(-5.0, -1.0)])
    walls(d, k, "e", X, -5.0, 5.0, skip=[(1.0, 5.0)])
    corners(d, k, -X, X, -Z, Z)
    door(d, k, "e", X, 3.0, width=3.0)
    # エレベーター（形 1 の東の面 x -5.3）：扉、両脇の赤い非常灯、上の巻上機の箱
    d.at_wall("w", -5.3, -3.0, "b3_door", scale=[1.5, 0.9, 1.0])
    for z in (-4.7, -1.3):
        d.at_wall("w", -X, z, "b1_redlight", y=2.2, off=0.05)
    d.at_wall("w", -X, -3.0, "b3_gear_small", y=4.6, off=0.25, scale=0.7)
    beams(d, k, -X, X, 6.0, (-3.0, 3.0))
    # 生活感の小物：レバーを引いた人の置いた道具箱（東の壁ぎわ、北）
    W = X - 0.38
    d.snug("town/chest", 0, x1=2.0, z1=W)
    d.snug("b1_crate", 0, x1=0.9, z1=W)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(4.6, 3.0, 90), (-4.0, -3.0, 90)],
          path=[(3.6, 3.0), (0.4, -2.8)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 4.5, 0], "#ffb050", 14.0, 2.4), light([-5.0, 2.6, -3.0], "#ff4a3a", 6.0, 1.2)]


# ================================================================ B4：心臓部

def r18(room):
    """心臓部前室（20×8×24）。診断の台（形 3・4）、太い柱（形 5・6）、奥の大扉（形 1・2 の間、高さ 5 m）"""
    g = room["geometry"]
    d = D.Dress()
    k = "b4"
    X, Z, H = 10.0, 12.0, 8.0
    for i in (1, 2):
        g[i]["skin"] = {"wall": "wall", "floor": "metal"}
    g[3]["skin"] = {"wall": "metal", "floor": "plate"}
    g[4]["skin"] = {"wall": "metal", "floor": "glow"}
    for i in (5, 6):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b4_column_wide", [p[0], 0, p[2]])
    b3_shell(d, k, X, Z, s_door=0.0, n_plane=9.3, skip_n=[(-3.0, 3.0)])
    # 大扉のまわり：丸い枠（炉心の扉と同じ）と、扉の奥の小部屋の先の扉
    d.put("b4_vault", [0.0, 0.0, 9.3], 180, scale=[1.0, 1.0, 1.0])
    door(d, k, "n", Z, 0.0, width=4.0, solid=False)
    # 上の段：赤い非常灯の帯（外周）と天井の梁、白磁の柱の灯
    for side, plane in (("w", -X), ("e", X)):
        d.along(side, plane, -11.0, 8.0, "b4_band", y=5.4, every=2.0)
    d.along("s", -Z, -9.0, 9.0, "b4_band", y=5.4, every=2.0)
    beams(d, k, -X, X, H, (-8.0, -2.0, 4.0))
    d.put("b1_debris", [-8.6, 0, -10.6], 25, solid=True)
    # 診断の台（形 3・4）から壁の柱へ這うケーブル（古い整備の跡）
    for pos, yaw in (((-3.4, 0, 0.6), 10), ((3.4, 0, -0.4), 190), ((-6.2, 0, 1.4), 20)):
        d.put("b1_cables", pos, yaw)
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, 9.3, 90), (X, 9.3, 180)], doors_at=[(0.0, -10.6, 0), (0.0, 8.0, 0)],
          path=[(0.0, -9.0), (0.0, -2.6), (0.0, 7.6)], spots=[(-5.0, 4.4, 0, 0.8)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 5, 0], "#ffc27a", 18.0, 2.0), light([0, 5.0, 8.6], "#ffb45a", 10.0, 2.0),
                      light([-9.0, 4.0, -6.0], "#ff4a3a", 8.0, 1.2), light([9.0, 4.0, -6.0], "#ff4a3a", 8.0, 1.2)]


def r19(room):
    """心臓部（直径 32 m の円形の広間、壁 36 枚（形 1〜35）・入口の通路（形 36〜38）・外周のレール（形 39〜74）・炉心の扉（形 75・76））。
    ボスの戦いの場：床・柱は白磁で読みやすく、外周は黒鉛と真鍮、赤い非常灯は外周、琥珀は柱と扉（絵 ruins_mood_b4）。
    当たり判定・ボスの動き・壊れる柱（ゲームの物）は変えない"""
    g = room["geometry"]
    d = D.Dress()
    k = "b4"
    g[0]["skin"] = {"floor": "floor", "wall": "metal"}
    for i in range(1, 36):
        g[i]["skin"] = {"wall": "wall", "floor": "metal"}
        g[i]["trim"] = False
        p, yaw = g[i]["pos"], g[i].get("yaw", 0.0)
        a = math.radians(yaw)
        # 区画の内の面（中心から 16.0 m）に壁の区画の部品
        nx, nz = -math.sin(a), -math.cos(a)
        d.put("b4_arena_panel", [round(p[0] + nx * 0.5, 3), 0, round(p[2] + nz * 0.5, 3)], round((yaw + 180) % 360, 2), scale=[0.85, 1.0, 1.0])
    for i in (36, 37, 38):
        g[i]["skin"] = {"wall": "wall", "floor": "metal"}
    for i in range(39, 75):
        g[i]["skin"] = "rail"
    g[75]["skin"] = "metal"
    g[76]["skin"] = "glow"
    # 炉心の扉の丸い枠（形 75 の南の面 z -15.2）、天井、床の同心の輪
    d.put("b4_vault", [0.0, 0.0, -15.2], 0, scale=[1.0, 1.0, 1.0])
    d.put("b4_ceiling", [0.0, 16.0, 0.0])
    d.put("b4_floor_rings", [0.0, 0.0, 0.0])
    # 入口の通路（形 36〜38）の扉
    door(d, k, "n", 19.0, 0.0, width=4.0, solid=False)
    grime(d, doors_at=[(0.0, 15.6, 0)], spots=[(0.0, -13.0, 0, 1.2), (4.6, 4.6, 45, 0.9), (-4.6, -4.6, 45, 0.9)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 12, 0], "#ffd2a0", 34.0, 2.4), light([0, 6, 12], "#ff6a4a", 18.0, 1.4),
                      light([0, 6, -12], "#ffb45a", 18.0, 1.8)]


def r20(room):
    """炉心（20×10×20）。物語の舞台：絵 ruins_core（直立した円筒の発電装置、管が柱へ、外周の赤い非常灯）。入ると再始動。
    台（形 1）・芯（形 2）・冠（形 3）に炉心の部品、柱 8 本（形 4〜11）に白磁の覆い"""
    g = room["geometry"]
    d = D.Dress()
    k = "b4"
    X, Z, H = 10.0, 10.0, 10.0
    g[1]["skin"] = {"wall": "metal", "floor": "plate"}
    g[2]["skin"] = "metal"
    g[3]["skin"] = "metal"
    d.put("b4_core", [0.0, 0.0, 2.0])
    d.put("b4_floor_rings", [0.0, 0.0, 2.0], scale=[0.6, 1.0, 0.6])        # 炉心のまわりの床の同心の輪（絵 ruins_core）
    for i in range(4, 12):
        g[i]["hide"] = True
        p = g[i]["pos"]
        d.put("b4_column", [p[0], 0, p[2]])
        # 芯から柱へ太い管（頭の上 6.4 m）
        dx, dz = p[0] - 0.0, p[2] - 2.0
        L = math.hypot(dx, dz)
        yaw = math.degrees(math.atan2(dx, dz)) - 90.0
        mid = (1.3 + L - 0.5) / 2.0
        d.put("b2_pipe", [round(dx / L * mid, 3), 6.4, round(2.0 + dz / L * mid, 3)], round(yaw % 360, 2),
              scale=[round((L - 1.8) / 2.0, 3), 1.2, 1.2])
    b3_shell(d, k, X, Z, s_door=0.0)
    for side, plane in (("w", -X), ("e", X), ("n", Z), ("s", -Z)):
        d.along(side, plane, -9.0, 9.0, "b4_band", y=5.6, every=2.0)
        d.along(side, plane, -9.0, 9.0, "b4_band", y=8.4, every=2.0)
    beams(d, k, -X, X, H, (-6.0, 10.0 - 0.3))
    grime(d, corners_at=[(-X, -Z, 0), (X, -Z, 270), (-X, Z, 90), (X, Z, 180)], doors_at=[(0.0, -8.6, 0)],
          spots=[(0.0, -1.6, 0, 1.2), (2.8, 2.0, 90, 0.9), (-2.8, 2.0, 90, 0.9)])
    room["kit"] = KITS[k]["kit"]
    room["dress"] = d.items
    room["lights"] = [light([0, 5.5, 2], "#ffa040", 18.0, 3.2), light([0, 9, 0], "#ffd2a0", 22.0, 1.2),
                      light([-8.0, 4.0, -8.0], "#ff4a3a", 8.0, 1.2), light([8.0, 4.0, -8.0], "#ff4a3a", 8.0, 1.2)]


ROOMS = {"r04": r04, "r05": r05, "r06": r06, "r07": r07, "r08": r08, "r09": r09, "r10": r10, "r11": r11,
         "r12": r12, "r13": r13, "r14": r14, "r15": r15, "r16": r16, "r17": r17, "r18": r18, "r19": r19, "r20": r20}
