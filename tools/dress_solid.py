"""飾り（dress）の "solid"：箱・樽・鉢植えのような手で触れる大きさの部品に、部品の形に合わせた当たり判定の箱を付ける。

飾りは見た目だけで当たり判定が無いので、床に置いた箱・樽の中にハルが入り込み、頭だけ出して立てた（ハリボテに見えた）。
dress の 1 件に "solid": true を付けると、ここの SOLID の表（部品の中の箱）を部品の pos・yaw・scale・count/step のとおりに置いた
描かない形（geometry の {"t": "box", …, "hide": true, "dress": <dress の番号>}）を部屋に足す。表に無い形は "solid": [箱, …] で直接書く。
書くのは tools/dress_ruins.py・tools/dress_town.py（部屋の JSON を書く）。何度流しても同じ（前に足した "dress" つきの形は消してから足す）。
書き方：docs/design/42_コンテンツの書き方.md 14.3。テスト：godot/tests/test_kit.gd の test_dress_solid_*。

箱の書き方（部品の中の座標。原点・向きは部品と同じ。x 右、y 上、z 正面）
  B(x0, x1, y0, y1, z0, z1)           軸にそろった箱
  R(cx, cz, wx, wz, y0, y1, yaw)      中心 (cx, cz)・幅 wx × 奥行き wz を yaw 度回した箱（部品の中で斜めに置いた箱・樽）
置く形はどれも軸にそろった箱（yaw なし）。部品・箱の向きが 90 度の倍数でなければ、回した広がりを囲む箱にする（くさび形のすき間を作らない）
  {"t": "stairs", "pos", "size", "steps"}   段ごとの箱（階段の手すりの帯）。RoomGeo の stairs と同じ

決まり（42 の 14.3）：出口・トリガーの箱に掛けない（0.1 m 空ける）、目印・チェックポイント・敵の出る所から 0.6 m、
調べる物・拾う物・住人から 0.5 m 空ける（check() が確かめ、だめなら書かずに止まる）。細い柱は低い箱（1.2 m まで）にする
（カメラは当たり判定の箱の手前に寄るので、背の高い細い箱は柱が後ろを横切るたびにカメラが跳ねる。体は縦の筒なので、低い箱でも柱に入らない）。
"""
import math


def B(x0, x1, y0, y1, z0, z1):
    return ((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, y0, y1, 0.0)


def R(cx, cz, wx, wz, y0, y1, yaw=0.0):
    return (cx, cz, wx, wz, y0, y1, yaw)


def _crate(cx, cz, s, yaw, y0=0.0):
    """町の木箱（town/crate：0.94 m 角・高さ 0.74）を部品の中に s 倍で置いたときの箱"""
    return R(cx, cz, 0.94 * s, 0.94 * s, y0, y0 + 0.74 * s, yaw)


def _barrel(cx, cz, s, y0=0.0):
    """町の樽（town/barrel：半径 0.36・高さ 1.0）。丸い物は半径の箱（角は 0.1 m ほど外へ出るが見えない）"""
    return R(cx, cz, 0.7 * s, 0.7 * s, y0, y0 + 1.0 * s)


def _post(cx, cz, w=0.24, h=1.2):
    """細い柱：低い箱（カメラが跳ねないように。体は柱に入らない）"""
    return R(cx, cz, w, w, 0.0, h)


def _rail_band(sx):
    """町の階段の手すり（stair_rail_12：壁の面 x=0 から階段の側へ 0.18 m、踏み面の 1 m 上を 12 m で 5 m 上る）。
    手すりの下を段ごとの帯（壁から 0.3 m、段の上 1.0 m まで。下は 1.0 m から）でふさぐ。sx：階段の側（+1 / -1）"""
    x0, x1 = sorted((0.0, sx * 0.3))
    return [
        {"t": "stairs", "pos": [sx * 0.15, 1.0, 6.0], "size": [0.3, 5.0, 12.0], "steps": 16},
        B(x0, x1, 0.0, 1.05, -0.6, 0.0),       # 下の段の床の上に出た端
        B(x0, x1, 5.0, 6.05, 12.0, 12.6),      # 上の踊り場の上に出た端
    ]


# 部品 → 部品の中の箱。寸法は tools/blender/kit/ruins_b1.py・town_parts.py・town_sets.py（godot/assets/kit/town/parts.json）
SOLID = {
    # 遺構 B1
    "ruins/b1_crate": [B(-0.52, 0.52, 0.0, 1.0, -0.52, 0.52)],
    "ruins/b1_crate_cloth": [B(-0.56, 0.56, 0.0, 1.04, -0.56, 0.56)],
    "ruins/b1_pillar": [B(-0.3, 0.3, 0.0, 4.0, -0.3, 0.3)],
    "ruins/b1_fan": [B(-2.0, 2.0, 0.0, 4.0, 0.0, 0.5)],              # 枠と羽根（壁から 0.45 m）
    # 町の小物
    "town/crate": [B(-0.47, 0.47, 0.0, 0.74, -0.47, 0.47)],
    "town/barrel": [_barrel(0.0, 0.0, 1.0)],
    "town/chest": [B(-0.52, 0.52, 0.0, 1.0, -0.47, 0.47)],
    "town/planter": [B(-0.45, 0.45, 0.0, 1.45, -0.45, 0.45)],        # 茂みの上まで（跳んで乗ると茂みの上に立つ）
    "town/planter_big": [B(-0.68, 0.65, 0.0, 1.73, -0.66, 0.66)],
    # 座面と背板。座面の箱は座面（0.5）より少し高く 0.56 まで：広場の床の板（0.08）の上では座面が 0.42 しか無く、
    # 段差の乗り越え（0.35）と体の丸い底で角に乗り上げて、足が座面の角に入った
    "town/bench": [B(-0.99, 0.99, 0.0, 0.56, -0.34, 0.24), B(-0.99, 0.99, 0.0, 1.07, -0.34, -0.18)],
    "town/stall_table": [B(-1.01, 1.01, 0.0, 0.97, -0.53, 0.53)],
    "town/tool_rack": [B(-1.03, 1.03, 0.0, 1.75, -0.3, 0.3)],
    "town/water_tower": [B(-0.75, 0.75, 0.0, 2.45, -0.75, 0.75)],
    "town/clothesline": [B(-1.14, 1.14, 0.0, 1.2, -0.14, 0.14)],     # 洗濯物の下は通れない。低い箱（カメラ）
    "town/pipes": [B(-1.02, 1.02, 0.0, 0.46, -0.3, 0.32)],
    "town/lamp_post": [B(-0.33, 0.33, 0.0, 0.48, -0.33, 0.33)],     # 白磁の台（細い柱は台の内）
    "town/lamp_tall": [B(-0.33, 0.33, 0.0, 0.48, -0.33, 0.33)],
    "town/parapet_corner": [B(-0.71, 0.71, -8.2, 0.04, -0.71, 0.71)],
    "town/goods_shelf_general": [B(-3.4, 3.4, 0.0, 2.3, -0.03, 0.43)],
    "town/goods_shelf_junk": [B(-3.4, 3.4, 0.0, 2.3, -0.03, 0.43)],
    # 組の部品の中の小物（town_sets.py）
    # 露店：四隅の柱（0.16 m）と、裏の木箱の山・樽
    "town/stall": [_post(sx * 3.8, sz * 2.45) for sx in (-1, 1) for sz in (-1, 1)]
                  + [R(-2.6, -3.35, 1.06, 1.06, 0.0, 1.33), _barrel(2.7, -3.3, 0.85)],
    # 天幕：台・木箱・樽（4 本の真鍮の柱は細いので無し）
    "town/tent": [B(-1.01, 1.01, 0.0, 0.97, -0.83, 0.23), _crate(-1.4, 0.6, 0.7, 10), _barrel(1.4, 0.5, 0.8)],
    # 壇の上の旗竿 2 本（壇の上 1.2 m まで）
    "town/stage": [R(sx * 3.65, 1.15, 0.16, 0.16, 0.8, 2.0) for sx in (-1, 1)],
    # 工房の正面の足元：工具棚 2 つ、樽、タンク、木箱 2 つ
    "town/workshop_front": [B(-6.58, -4.52, 0.0, 1.75, -0.18, 0.42), B(4.52, 6.58, 0.0, 1.75, -0.18, 0.42),
                            _barrel(-6.3, 0.7, 1.0), R(6.0, 0.575, 0.68, 1.25, 0.0, 0.8), _crate(-3.1, 0.75, 0.8, 12), _crate(3.3, 0.7, 0.75, -8)],
    # 食堂の裏（z=-9）の樽と木箱の山
    "town/diner_front": [_barrel(0.9, -9.55, 0.85), R(-0.6, -9.6, 0.76, 0.76, 0.0, 1.12, 12)],
    "town/stair_rail_12": _rail_band(1),
    "town/stair_rail_12_r": _rail_band(-1),
}


def _r3(v):
    return [round(float(x), 3) for x in v]


def _scale(d):
    sc = d.get("scale", 1.0)
    return [float(s) for s in sc] if isinstance(sc, list) else [float(sc)] * 3


def _rot(yaw_deg, x, z):
    """Godot の Basis(Vector3.UP, yaw)：+Z を向いた物を yaw 度回すと +X 寄りへ向く"""
    a = math.radians(yaw_deg)
    return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)


def shapes_of(d):
    """dress の 1 件の当たり判定の形（ワールドの geometry の形のリスト）"""
    spec = d.get("solid")
    if not spec:
        return []
    boxes = SOLID[d["part"]] if spec is True else [tuple(b) if isinstance(b, list) else b for b in spec]
    sx, sy, sz = _scale(d)
    yaw = float(d.get("yaw", 0.0))
    step = d.get("step", [0, 0, 0])
    out = []
    for k in range(max(1, int(d.get("count", 1)))):
        px, py, pz = (float(d["pos"][i]) + float(step[i]) * k for i in range(3))
        for b in boxes:
            if isinstance(b, dict):
                lx, ly, lz = b["pos"]
                wx, wy, wz = b["size"]
                byaw = float(b.get("yaw", 0.0))
                shape = {"t": b["t"], "steps": b.get("steps", 6)}
                y0 = ly * sy
                hy = wy * sy
            else:
                lx, lz, wx, wz, y0l, y1l, byaw = (list(b) + [0.0])[:7]
                y0, hy = y0l * sy, (y1l - y0l) * sy
                wy = None
                shape = {"t": "box"}
            if byaw and abs(sx - sz) > 1e-6:
                raise ValueError(f"{d['part']}: 斜めの箱は x と z を同じ倍率にする（{sx}, {sz}）")
            dx, dz = _rot(yaw, lx * sx, lz * sz)
            fx, fz = abs(wx * sx), abs(wz * sz)
            tyaw = (yaw + byaw) % 360
            q = round(tyaw / 90.0)
            if abs(tyaw - 90.0 * q) > 1e-3:
                # 斜めの箱は、床の上の広がりを囲む軸にそろった箱にする。斜めの面と壁・ほかの箱の間にできるくさび形の
                # すき間に体が押し込まれると、床を抜けて沈んだ（体の物理は面を滑らせるだけなので、鋭い角で詰まる）。
                # 軸にそろった箱どうし・壁との角は直角だけなので詰まらない。斜めの面の真ん中では最大 0.2 m ほど手前で止まる
                a = math.radians(tyaw)
                fx, fz = (fx * abs(math.cos(a)) + fz * abs(math.sin(a)), fx * abs(math.sin(a)) + fz * abs(math.cos(a)))
                tyaw = 0.0
            elif q % 2:
                fx, fz = fz, fx
            shape["pos"] = _r3([px + dx, py + y0, pz + dz])
            shape["size"] = _r3([fx, abs(hy), fz])
            out.append(shape)
    return out


def apply(room):
    """部屋の dress の "solid" から、描かない当たり判定の形を geometry の終わりに足す（前に足した形は消す）。足した数を返す"""
    geo = [g for g in room["geometry"] if "dress" not in g]
    n = 0
    for i, d in enumerate(room.get("dress", [])):
        for s in shapes_of(d):
            s["hide"] = True
            s["tint"] = "#5a5048"
            s["dress"] = i
            geo.append(s)
            n += 1
    room["geometry"] = geo
    check(room)
    return n


# ---------------------------------------------------------------- 決まりの確かめ（godot/tests/test_kit.gd と同じ）

CLEAR_BOX = 0.1      # 出口・トリガーの箱から
CLEAR_MARK = 0.6     # 目印・チェックポイント・敵の出る所から（体の半径 0.35 ＋ゆとり）
CLEAR_PROP = 0.5     # 調べる物・拾う物・住人から
BODY = 1.6           # 体の高さ（1.55）


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


def check(room):
    """足した形が、出口・トリガー・目印・調べる物などの決まりの距離を守っているか。だめなら ValueError"""
    bad = []
    marks = [(n, m["pos"]) for n, m in room.get("markers", {}).items()]
    marks += [(c["id"], c["pos"]) for c in room.get("checkpoints", [])]
    marks += [(e.get("id", e.get("kind", "敵")), e["pos"]) for e in room.get("enemies", []) if "pos" in e]
    boxes = [(t["id"], t["pos"], t["size"]) for t in room.get("triggers", []) if "pos" in t and "size" in t]
    points = []
    for p in room.get("props", []):
        if p.get("type") == "sign":
            continue
        if "size" in p and isinstance(p["size"], list):
            boxes.append((p.get("id", p["type"]), p["pos"], p["size"]))
        elif "pos" in p:
            points.append((p.get("id", p["type"]), p["pos"]))
    for g in room["geometry"]:
        if "dress" not in g:
            continue
        _, _, _, _, _, y0, y1 = footprint(g)
        tag = f"{room['dress'][g['dress']]['part']} {g['pos']}"
        for name, pos, clear in [(n, p, CLEAR_MARK) for n, p in marks] + [(n, p, CLEAR_PROP) for n, p in points]:
            if y1 > pos[1] - 0.2 and y0 < pos[1] + BODY and dist_point(g, pos[0], pos[2]) < clear:
                bad.append(f"{tag} が {name} {pos} に近い")
        for name, pos, size in boxes:
            half = [size[0] / 2, size[1] / 2, size[2] / 2]
            center = [pos[0], pos[1] + half[1], pos[2]]
            if overlaps_box(g, center, half, CLEAR_BOX):
                bad.append(f"{tag} が {name} の箱に掛かる")
    if bad:
        raise ValueError("solid の箱の置き場所がだめ：\n  " + "\n  ".join(bad))
