"""町の 9 部屋（中段のほか：夜明けの甲羅・訓練場・下段・上段・ハルの家・工房・ギルド・町長の家）の組の部品（2026-10-15 の展開）。

中段（town_sets.py・town_terrace.py）と同じ作り方：部屋の geometry の箱は当たり判定のまま残し、見える面はキットの面
（白磁の壁・縁取り）で描く。ここの部品は、その箱の面に付ける飾り（柱・帯・窓・扉・日よけ・灯・配管・屋上の物）と、
箱の代わりに描く物（家具・機械・的・リフト。箱は "hide" で描かず、同じ大きさの物をここで作る）。
どれも部屋の座標のまま作ってあり、pos [0,0,0]・yaw 0 で置く（部品の一覧は PARTS）。

  lower_set      下段：訓練場の門の棟（L3）・ハルの家（L2）・住宅（L1）・東の棟 3 つ（マーサの洗濯屋）の面と屋上、昇降リフト（L4）、
                 禁足扉（L5）の門の枠
  upper_set      上段：町長の家（U1）・回収屋ギルド（U2）の面と屋上、展望台（U3）の床の縁・手すり・望遠鏡
  training_set   訓練場：段の台・的の柱・溝の縁と斜面・残骸・壁の面・入口の門・壁の向こうの家並み
  home_set / workshop_set / guild_set / mayor_set   屋内：壁の柱と帯・天井の梁・赤い布・窓・扉・家具（geometry の箱と同じ大きさ）
  opening_set    夜明けの甲羅：外殻の床の縁・係留柱・通気口・見張りの小さな台
  grime_patch    汚れの斑（床に置く 1 m の板。材質 grime_decal：キットの "blend": "mul" の材質が床の色に掛ける）

絵：W2-05 town_facilities（工房・ギルド・雑貨屋・ハルの家・訓練場・禁足扉）、town_interiors（工房・ハルの家）、
town_kit_buildings / town_props、town_mood_day。寸法は部屋の geometry（content/areas/ch1_town.json）に合わせる。

手の届く所（床から 3.85 m より下、歩ける所の横）に付ける物は、面から 6 cm まで（体が入り込まない薄さ。当たり判定は要らない）。
それより出る物（日よけ・灯・雨戸・配管）は 3.9 m より上に付けるか、dress_town.py で体だけの箱を付ける。
"""
from __future__ import annotations

import math

import numpy as np

import town_parts as P
import town_sets as S
import town_terrace as T
from town_geo import Part, Piece, beam, box, boxb, cyl, lathe, sag, sheet, tube

YAW = {'-z': 180.0, '+z': 0.0, '+x': 90.0, '-x': -90.0}
HEAD = 3.9          # これより上の物には、床から跳んでも頭が届かない（体 1.55 + 跳ぶ 2.2）


# ---------------------------------------------------------------- 面の飾り（面の座標：面は z=0、+Z が外、x は面の中心から）

def win_low(p: Part, x, y=1.05, w=0.92, h=0.8):
    """手の届く高さの窓：面から 5 cm までの平らな窓（黒鉛の枠と桟・暗い奥・木の窓台）"""
    p.add('dark', boxb(x - w / 2 + 0.08, x + w / 2 - 0.08, y, y + h, 0.0, 0.012))
    p.add('graphite', boxb(x - w / 2, x + w / 2, y + h, y + h + 0.09, 0, 0.05), boxb(x - w / 2, x - w / 2 + 0.08, y, y + h, 0, 0.05),
          boxb(x + w / 2 - 0.08, x + w / 2, y, y + h, 0, 0.05), boxb(x - 0.02, x + 0.02, y, y + h, 0, 0.03),
          boxb(x - w / 2 + 0.08, x + w / 2 - 0.08, y + h * 0.48, y + h * 0.48 + 0.04, 0, 0.03))
    p.add('wood', boxb(x - w / 2 - 0.05, x + w / 2 + 0.05, y - 0.09, y, 0, 0.06))


def door_flat(p: Part, x, w=1.0, h=2.0):
    """木の扉（面から 5 cm）：黒鉛の枠、板の継ぎ目、真鍮の取っ手と蝶番"""
    p.add('wood', boxb(x - w / 2, x + w / 2, 0, h, 0, 0.03))
    p.add('graphite', boxb(x - w / 2 - 0.1, x - w / 2, 0, h + 0.1, 0, 0.06), boxb(x + w / 2, x + w / 2 + 0.1, 0, h + 0.1, 0, 0.06),
          boxb(x - w / 2 - 0.1, x + w / 2 + 0.1, h, h + 0.1, 0, 0.06))
    n = max(2, int(round(w / 0.24)))
    for k in range(1, n):
        xx = x - w / 2 + k * w / n
        p.add('dark', boxb(xx - 0.01, xx + 0.01, 0.05, h - 0.05, 0.03, 0.035))
    p.add('brass', boxb(x + w / 2 - 0.22, x + w / 2 - 0.16, 0.9, 1.15, 0.03, 0.06),
          boxb(x - w / 2 + 0.02, x - w / 2 + 0.2, 0.3, 0.37, 0.03, 0.05), boxb(x - w / 2 + 0.02, x - w / 2 + 0.2, h - 0.37, h - 0.3, 0.03, 0.05))


def door_double(p: Part, x, w=2.6, h=3.0, frame=0.2):
    """両開きの大きな扉（奥まりの奥・門）：木の板、黒鉛の枠、真鍮の帯と取っ手"""
    hw = w / 2
    for sx in (-1, 1):
        p.add('wood', boxb(min(x + sx * 0.02, x + sx * hw), max(x + sx * 0.02, x + sx * hw), 0, h, 0.0, 0.06))
        for k in range(1, 4):
            xx = x + sx * (0.02 + k * (hw - 0.02) / 4)
            p.add('dark', boxb(xx - 0.012, xx + 0.012, 0.1, h - 0.1, 0.06, 0.07))
        p.add('brass', boxb(min(x + sx * 0.16, x + sx * 0.24), max(x + sx * 0.16, x + sx * 0.24), h * 0.42, h * 0.58, 0.06, 0.11))
        for y in (0.45, h - 0.55):
            p.add('graphite', boxb(min(x + sx * 0.05, x + sx * (hw - 0.05)), max(x + sx * 0.05, x + sx * (hw - 0.05)), y, y + 0.1, 0.06, 0.09))
    p.add('graphite', boxb(x - hw - frame, x - hw, 0, h + frame, 0, 0.16), boxb(x + hw, x + hw + frame, 0, h + frame, 0, 0.16),
          boxb(x - hw - frame, x + hw + frame, h, h + frame, 0, 0.18))
    p.add('brass', boxb(x - hw - frame - 0.02, x - hw + 0.02, 0, 0.22, 0, 0.19), boxb(x + hw - 0.02, x + hw + frame + 0.02, 0, 0.22, 0, 0.19),
          boxb(x - 0.3, x + 0.3, h + 0.02, h + frame - 0.02, 0.17, 0.21))


def roll_shutter(p: Part, x, w=2.6, h=2.4):
    """巻き上げの木の戸（ハルの家の大きな戸、town_facilities）：横の板、黒鉛の枠、上の巻きの箱"""
    p.add('graphite', boxb(x - w / 2 - 0.12, x - w / 2, 0, h + 0.3, 0, 0.06), boxb(x + w / 2, x + w / 2 + 0.12, 0, h + 0.3, 0, 0.06))
    p.add('graphite', boxb(x - w / 2 - 0.15, x + w / 2 + 0.15, h, h + 0.32, 0, 0.06))
    for k in range(int(h / 0.2)):
        y = k * 0.2
        p.add('wood' if k % 2 else 'wood2', boxb(x - w / 2, x + w / 2, y + 0.01, y + 0.19, 0, 0.035))
    p.add('brass', boxb(x - 0.3, x + 0.3, 0.12, 0.2, 0.035, 0.06), boxb(x - w / 2 - 0.15, x - w / 2 + 0.05, h + 0.06, h + 0.26, 0.04, 0.06),
          boxb(x + w / 2 - 0.05, x + w / 2 + 0.15, h + 0.06, h + 0.26, 0.04, 0.06))


def plates(p: Part, x0, x1, y0, y1, step=2.0):
    """白磁の板の継ぎ目の目印：2 m ごとの縦長の真鍮の留め板（面から 2.5 cm）"""
    for x in np.arange(x0 + 0.45, x1 - 0.2, step):
        for y in np.arange(y0 + 0.8, y1 - 0.3, 2.0):
            p.add('brass', boxb(x - 0.05, x + 0.05, y - 0.09, y + 0.09, 0, 0.025))


def deco(spec: dict, w: float, h: float) -> Part:
    """面の飾り（面の座標）。spec：
      posts [x]（黒鉛の付け柱、面から 6 cm）・bands [y]（黒鉛の帯）・plates [(x0, x1, y0, y1)]・low [(x, y)]（平らな窓）・
      high [(x, y)]（雨戸の窓：3.5 m より上に）・door [(x, 幅, 高さ)]・door2 [(x, 幅, 高さ)]・roll [(x, 幅, 高さ)]・
      awn [(x0, x1, y, 'hard'|'soft', 奥行き, 下がり)]・lamps [(x, y)]・pipes [(x, y0, y1)]・hpipes [(x0, x1, y)]・
      banners [(x, y)]・vents [(x, y)]・lit [(x, y)]（明るい窓：屋内から見た外の光）"""
    p = Part('deco')
    for x in spec.get('posts', ()):
        x = min(max(x, -w / 2 + 0.09), w / 2 - 0.09)
        p.add('graphite', boxb(x - 0.09, x + 0.09, 0, h, 0, 0.06))
        for y in (0.06, min(h - 0.3, 2.0), h - 0.3) if h > 2.6 else (0.06, h - 0.3):
            p.add('brass', boxb(x - 0.11, x + 0.11, y, y + 0.2, 0, 0.075))
    for y in spec.get('bands', ()):
        p.add('graphite', boxb(-w / 2, w / 2, y - 0.06, y + 0.06, 0, 0.05))
    for x0, x1, y0, y1 in spec.get('plates', ()):
        plates(p, x0, x1, y0, y1)
    for x, y in spec.get('low', ()):
        win_low(p, x, y)
    for x, y in spec.get('high', ()):
        S._window(p, x, y, 0.01)
    for x, y in spec.get('lit', ()):
        p.add('amber', boxb(x - 0.4, x + 0.4, y, y + 0.9, 0.0, 0.012))
        p.add('graphite', boxb(x - 0.48, x + 0.48, y + 0.9, y + 0.98, 0, 0.05), boxb(x - 0.48, x - 0.4, y, y + 0.9, 0, 0.05),
              boxb(x + 0.4, x + 0.48, y, y + 0.9, 0, 0.05), boxb(x - 0.02, x + 0.02, y, y + 0.9, 0, 0.03),
              boxb(x - 0.4, x + 0.4, y + 0.43, y + 0.47, 0, 0.03))
        p.add('wood', boxb(x - 0.53, x + 0.53, y - 0.09, y, 0, 0.06))
    for x, dw, dh in spec.get('door', ()):
        door_flat(p, x, dw, dh)
    for x, dw, dh in spec.get('door2', ()):
        door_double(p, x, dw, dh)
    for x, dw, dh in spec.get('roll', ()):
        roll_shutter(p, x, dw, dh)
    for x0, x1, y, kind, out, drop in spec.get('awn', ()):
        p.place(P.awning(kind, x1 - x0, out, drop), ((x0 + x1) / 2, y, 0.01))
    for x, y in spec.get('lamps', ()):
        P.lantern(p, x, y, 0.42, 1.0)
        p.add('graphite', beam((x, y + 0.42, 0.0), (x, y + 0.42, 0.42), 0.05))
        p.add('brass', cyl((x, y + 0.42 - 0.04, 0.42), (x, y + 0.26, 0.42), 0.012, 5))
    for x, y0, y1 in spec.get('pipes', ()):
        P.pipe_run(p, (x, y0, 0.18), (x, y1, 0.18), 0.09, 1.2)
        for y in np.arange(y0 + 0.7, y1 - 0.3, 1.6):
            p.add('graphite', boxb(x - 0.04, x + 0.04, y - 0.05, y + 0.05, 0, 0.18))
    for x0, x1, y in spec.get('hpipes', ()):
        P.pipe_run(p, (x0, y, 0.22), (x1, y, 0.22), 0.12, 1.2)
        for x in np.arange(x0 + 0.8, x1 - 0.3, 1.8):
            p.add('graphite', boxb(x - 0.05, x + 0.05, y - 0.3, y + 0.05, 0, 0.22))
    for x, y in spec.get('banners', ()):
        p.place(P.banner(), (x, y, 0.0))
    for x, y in spec.get('vents', ()):
        p.add('graphite', boxb(x - 0.32, x + 0.32, y - 0.22, y + 0.22, 0, 0.05))
        for k in range(4):
            yy = y - 0.15 + k * 0.1
            p.add('dark', boxb(x - 0.26, x + 0.26, yy - 0.025, yy + 0.025, 0.05, 0.06))
    return p


def put(p: Part, normal: str, c, base, spec: dict, w: float, h: float):
    """面の飾りを付ける。c：面の中心の (x, z)（ワールド）、base：面の下の y。spec の x は面に沿ったワールドの座標
    （'-z'・'+z' の面は x、'-x'・'+x' の面は z）で書き、ここで面の座標に直す"""
    cx, cz = c
    sgn = {'-z': -1.0, '+z': 1.0, '+x': -1.0, '-x': 1.0}[normal]
    ctr = cx if normal in ('-z', '+z') else cz

    def u(v):
        return sgn * (v - ctr)

    def uu(a, b):
        return tuple(sorted((u(a), u(b))))
    s = {}
    for k, v in spec.items():
        if k in ('posts',):
            s[k] = [u(x) for x in v]
        elif k in ('bands',):
            s[k] = list(v)
        elif k in ('plates',):
            s[k] = [(*uu(a, b), y0, y1) for a, b, y0, y1 in v]
        elif k in ('low', 'high', 'lamps', 'banners', 'vents', 'lit'):
            s[k] = [(u(x), y) for x, y in v]
        elif k in ('door', 'door2', 'roll'):
            s[k] = [(u(x), a, b) for x, a, b in v]
        elif k == 'awn':
            s[k] = [(*uu(a, b), y, kind, out, drop) for a, b, y, kind, out, drop in v]
        elif k == 'pipes':
            s[k] = [(u(x), y0, y1) for x, y0, y1 in v]
        elif k == 'hpipes':
            s[k] = [(*uu(a, b), y) for a, b, y in v]
    p.place(deco(s, w, h), (cx, base, cz), YAW[normal])


def skirt(p: Part, x0, x1, z0, z1, y=0.0, faces='nsew', top=None):
    """箱の建物の足元の木の帯（0.4 m、面から 3 cm）と上の黒鉛の帯（top の高さ、面から 6 cm）。faces：帯を付ける面"""
    for f in faces:
        if f == 's':
            p.add('wood', boxb(x0 - 0.03, x1 + 0.03, y, y + 0.4, z0 - 0.03, z0))
            if top:
                p.add('graphite', boxb(x0 - 0.06, x1 + 0.06, top - 0.14, top, z0 - 0.06, z0))
        elif f == 'n':
            p.add('wood', boxb(x0 - 0.03, x1 + 0.03, y, y + 0.4, z1, z1 + 0.03))
            if top:
                p.add('graphite', boxb(x0 - 0.06, x1 + 0.06, top - 0.14, top, z1, z1 + 0.06))
        elif f == 'w':
            p.add('wood', boxb(x0 - 0.03, x0, y, y + 0.4, z0, z1))
            if top:
                p.add('graphite', boxb(x0 - 0.06, x0, top - 0.14, top, z0, z1))
        elif f == 'e':
            p.add('wood', boxb(x1, x1 + 0.03, y, y + 0.4, z0, z1))
            if top:
                p.add('graphite', boxb(x1, x1 + 0.06, top - 0.14, top, z0, z1))


def corner_posts(p: Part, x0, x1, z0, z1, top, corners=('sw', 'se', 'nw', 'ne'), y=0.0):
    """箱の建物の角の黒鉛の柱と真鍮の金具（角から 6 cm 外）"""
    for c in corners:
        x = x0 if 'w' in c else x1
        z = z0 if 's' in c else z1
        p.add('graphite', boxb(x - 0.08, x + 0.08, y, top + 0.05, z - 0.08, z + 0.08))
        for yy in (y + 0.06, y + (top - y) * 0.5, top - 0.3):
            p.add('brass', boxb(x - 0.1, x + 0.1, yy, yy + 0.22, z - 0.1, z + 0.1))


def roof_slab(p: Part, x0, x1, z0, z1, y0, y1):
    """屋根の板（geometry の屋根の箱と同じ所）の縁：黒鉛の帯と真鍮の角。上の面はキットの面（stone2）"""
    for a, b, c, d in ((x0, x1, z0, z0 + 0.12), (x0, x1, z1 - 0.12, z1), (x0, x0 + 0.12, z0, z1), (x1 - 0.12, x1, z0, z1)):
        p.add('graphite', boxb(a - 0.02, b + 0.02, y0 + 0.05, y1 + 0.04, c - 0.02, d + 0.02))
    for sx, sz in ((x0, z0), (x0, z1), (x1, z0), (x1, z1)):
        p.add('brass', boxb(sx - 0.16, sx + 0.16, y0, y1 + 0.06, sz - 0.16, sz + 0.16))


def recess(p: Part, rx0, rx1, zf, zb, rh, door=None):
    """入口の奥まり（rx0〜rx1、正面 zf から奥 zb、高さ rh）：両側の面の黒鉛の内張り（面から 3 cm）、まぐさの下の梁、奥の扉"""
    for x, s in ((rx0, 1), (rx1, -1)):
        p.add('graphite', boxb(min(x, x + s * 0.03), max(x, x + s * 0.03), 0, rh, min(zf, zb), max(zf, zb)))
        p.add('brass', boxb(min(x, x + s * 0.05), max(x, x + s * 0.05), 0, 0.25, min(zf, zb), max(zf, zb)))
    p.add('graphite', boxb(rx0, rx1, rh - 0.04, rh, min(zf, zb), min(zf, zb) + 0.2))
    if door:
        dw, dh = door
        put(p, '-z' if zb > zf else '+z', ((rx0 + rx1) / 2, zb), 0.0, {'door2': [((rx0 + rx1) / 2, dw, dh)]}, rx1 - rx0, rh)


def canopy_roof(p: Part, x0, x1, z0, z1, y, hgt=2.0, mat='cloth'):
    T.canopy(p, x0, x1, z0, z1, y, hgt, mat)


# ---------------------------------------------------------------- 汚れの斑（床に置く板）

def grime_patch(mat='grime_decal', name='grime_patch') -> Part:
    """汚れの斑：床の 3 cm 上の 1 m 四方の板（裏は無い）。材質 grime_decal はキットの "blend": "mul"（床の色に汚れの色を掛ける。
    斑の形は汚れの型の絵をワールドの座標で読み、板の真ん中ほど濃く、縁で消える）。大きさは scale で。oil_patch は油じみ（oil_decal）"""
    p = Part(name)
    v = np.array([[-0.5, 0.03, -0.5], [0.5, 0.03, -0.5], [0.5, 0.03, 0.5], [-0.5, 0.03, 0.5]], float)
    from town_geo import _orient_dir
    p.add(mat, _orient_dir(Piece(v, [[0, 1, 2, 3]]), (0, 1, 0)))
    return p


# ---------------------------------------------------------------- 下段（ch1.lower）

def _house_a(p: Part, x0, x1, zf, zb, top, rx, rz, rh, front_l, front_r, lintel, sides, back, roof_y):
    """入口の奥まりのある家（訓練場の門の棟・ハルの家・町長の家・ギルド）：geometry の箱（左右の棟・奥の棟・まぐさ・屋根の板）の面の飾り"""
    rx0, rx1 = rx
    skirt(p, x0, rx0, zf, zb, faces='s')
    skirt(p, rx1, x1, zf, zb, faces='s')
    skirt(p, x0, x1, zf, zb, faces='wen')
    corner_posts(p, x0, x1, zf, zb, top)
    for x in (rx0, rx1):
        p.add('graphite', boxb(x - 0.1, x + 0.1, 0, top + 0.05, zf - 0.1, zf + 0.04))
        p.add('brass', boxb(x - 0.13, x + 0.13, 0.06, 0.28, zf - 0.13, zf + 0.04), boxb(x - 0.13, x + 0.13, rh - 0.3, rh - 0.08, zf - 0.13, zf + 0.04))
    p.add('graphite', boxb(x0 - 0.06, x1 + 0.06, top - 0.14, top, zf - 0.06, zf))
    recess(p, rx0, rx1, zf, rz, rh, door=(rx1 - rx0 - 0.6, min(3.0, rh - 0.35)))
    if front_l:
        put(p, '-z', ((x0 + rx0) / 2, zf), 0.0, front_l, rx0 - x0, top)
    if front_r:
        put(p, '-z', ((rx1 + x1) / 2, zf), 0.0, front_r, x1 - rx1, top)
    if lintel:
        put(p, '-z', ((rx0 + rx1) / 2, zf), rh, lintel, rx1 - rx0, top - rh)
    for n, spec in sides.items():
        if n == '-x':
            put(p, '-x', (x0, (zf + zb) / 2), 0.0, spec, zb - zf, top)
        else:
            put(p, '+x', (x1, (zf + zb) / 2), 0.0, spec, zb - zf, top)
    if back:
        put(p, '+z', ((x0 + x1) / 2, zb), 0.0, back, x1 - x0, top)


def _box_house(p: Part, x0, x1, z0, z1, top, faces: dict, corners=('sw', 'se', 'nw', 'ne'), skirt_faces='nsew'):
    """入口の奥まりの無い箱の家（geometry の箱 1 つ）の面の飾り。faces：'-z' '+z' '-x' '+x' → spec"""
    skirt(p, x0, x1, z0, z1, faces=skirt_faces, top=top)
    corner_posts(p, x0, x1, z0, z1, top, corners)
    for n, spec in faces.items():
        if n in ('-z', '+z'):
            put(p, n, ((x0 + x1) / 2, z0 if n == '-z' else z1), 0.0, spec, x1 - x0, top)
        else:
            put(p, n, (x0 if n == '-x' else x1, (z0 + z1) / 2), 0.0, spec, z1 - z0, top)


def lower_set() -> Part:
    """下段（ch1.lower）の家の面と屋上・昇降リフト・禁足扉の門の枠"""
    p = Part('lower_set')
    rng = np.random.default_rng(11)
    # --- 訓練場の門の棟（L3 の入口。x -30〜-18、z 6〜14、高さ 6。奥まり x -25.6〜-22.4・奥 z 8・高さ 3.8。屋根の板 y 6〜6.6）
    _house_a(p, -30.0, -18.0, 6.0, 14.0, 6.0, (-25.6, -22.4), 8.0, 3.8,
             front_l={'posts': [-27.8], 'bands': [3.0], 'low': [(-28.9, 1.05), (-26.7, 1.05)], 'high': [(-27.8, 4.05)],
                      'banners': [(-29.25, 5.35)]},
             front_r={'posts': [-20.2], 'bands': [3.0], 'low': [(-21.3, 1.05), (-19.1, 1.05)], 'high': [(-20.2, 4.05)],
                      'banners': [(-18.75, 5.35)]},
             lintel={'awn': [(-25.4, -22.6, 0.75, 'hard', 1.0, 0.3)], 'lamps': [(-25.9, 0.45), (-22.1, 0.45)]},
             sides={'-x': {'posts': [10.0], 'low': [(8.2, 1.05), (11.8, 1.05)], 'high': [(8.2, 4.05), (11.8, 4.05)], 'bands': [3.0],
                           'vents': [(10.0, 2.4)]},
                    '+x': {'posts': [10.0], 'low': [(8.0, 1.05), (12.0, 1.05)], 'bands': [3.0], 'high': [(10.0, 4.05)]}},
             back={'posts': [-24.0], 'low': [(-27.0, 1.05), (-21.0, 1.05)], 'bands': [3.0]}, roof_y=6.6)
    roof_slab(p, -30.3, -17.7, 5.7, 14.3, 6.0, 6.6)
    # 屋上：訓練場の旗竿 2 本（赤い旗）、給水塔、木箱
    for x in (-29.4, -18.6):
        p.add('brass', cyl((x, 6.6, 6.4), (x, 10.6, 6.4), 0.07, 8))
        p.add('brass', lathe((x, 10.6, 6.4), (x, 10.85, 6.4), [(0, 0.12), (1, 0.02)], 8))
        p.add('cloth', sheet(lambda u, v, x=x: (x + (0.12 + 0.95 * u) * (1 if x < -24 else -1), 10.4 - 1.5 * v,
                                                 6.4 + 0.06 * math.sin(u * 3 + v * 2)), 3, 4, 0.02))
    p.place(P.water_tower(), (-21.0, 6.6, 12.0), 0, 1.15)
    p.place(P.crate(), (-27.5, 6.6, 12.6), 8, 0.9)
    p.place(P.crate(), (-26.6, 6.6, 12.8), -5, 0.7)
    # --- ハルの家（L2。x 13〜23、z 6〜14、高さ 6。奥まり x 16.4〜19.6・奥 z 8・高さ 3.8）。town_facilities：大きな巻き上げ戸と赤い日よけ、
    # 屋上の庭（鉢植え・赤い帆布の日よけ）、角の真鍮の配管
    _house_a(p, 13.0, 23.0, 6.0, 14.0, 6.0, (16.4, 19.6), 8.0, 3.8,
             front_l={'roll': [(14.7, 2.5, 2.5)], 'awn': [(13.3, 16.1, 4.45, 'hard', 1.1, 0.3)], 'high': [(14.7, 4.85)]},
             front_r={'low': [(21.3, 1.1)], 'high': [(21.3, 4.05)], 'bands': [3.0], 'posts': [22.2]},
             lintel={'lamps': [(16.1, 0.45)]},
             sides={'-x': {'posts': [10.0], 'low': [(8.4, 1.05), (11.8, 1.05)], 'high': [(10.0, 4.05)], 'bands': [3.0], 'vents': [(11.8, 2.5)]},
                    '+x': {'posts': [10.0], 'low': [(8.2, 1.05)], 'high': [(8.2, 4.05), (11.8, 4.05)], 'bands': [3.0],
                           'door': [(11.9, 0.95, 2.0)]}},
             back={'low': [(15.0, 1.05), (21.0, 1.05)], 'posts': [18.0]}, roof_y=6.6)
    roof_slab(p, 12.7, 23.3, 5.7, 14.3, 6.0, 6.6)
    # 角の真鍮の配管（屋根の上まで立ち上がる。3.9 m より下は面から 0.3 m 出るので体だけの柱：dress_town.py）
    for x, z in ((22.75, 5.85),):
        P.pipe_run(p, (x, 0.2, z), (x, 7.9, z), 0.11, 1.1)
        p.add('brass', lathe((x, 7.9, z), (x, 8.3, z), [(0, 0.16), (1, 0.06)], 8))
    # 屋上の庭：鉢植え・赤い帆布の日よけ・ハルが集めたガラクタ・アンテナ
    for x, z in ((13.6, 6.5), (14.6, 6.5), (22.3, 13.5), (21.3, 13.6)):
        T.pot(p, x, 6.6, z, 1.0)
    canopy_roof(p, 18.0, 21.8, 9.6, 12.8, 6.6, 2.0, 'cloth')
    p.place(P.junk_pile(), (15.0, 6.6, 12.2), 15, 0.9)
    p.add('graphite', cyl((19.2, 6.6, 7.0), (19.2, 9.8, 7.0), 0.04, 6))
    p.add('brass', cyl((18.6, 9.4, 7.0), (19.8, 9.4, 7.0), 0.025, 5), cyl((18.8, 9.0, 7.0), (19.6, 9.0, 7.0), 0.025, 5))
    # --- 住宅（L1。x -15.5〜-8.5、z 6〜12、高さ 4.5。屋根の板 y 4.5〜5）
    _box_house(p, -15.5, -8.5, 6.0, 12.0, 4.5, {
        '-z': {'door': [(-13.6, 1.0, 2.0)], 'low': [(-11.6, 1.05), (-9.9, 1.05)], 'posts': [-12.6],
               'awn': [(-14.5, -12.7, 4.35, 'soft', 1.0, 0.2)]},
        '-x': {'low': [(9.0, 1.05)], 'posts': [9.0]},
        '+x': {'low': [(8.0, 1.05), (10.4, 1.05)], 'vents': [(9.2, 2.6)]},
        '+z': {'low': [(-12.0, 1.05)]}})
    roof_slab(p, -15.8, -8.2, 5.7, 12.3, 4.5, 5.0)
    T.canopy(p, -14.6, -11.8, 8.4, 11.2, 5.0, 1.9, 'cloth2')
    T.pot(p, -9.2, 5.0, 6.3, 0.9)
    P.pipe_run(p, (-10.0, 5.0, 11.2), (-10.0, 6.6, 11.2), 0.14, 1.0)
    # --- 東の棟（マーサの洗濯屋）：A（x 30〜38、z 3〜13、高さ 5）・B（x 37〜45、z 7〜15、高さ 7）・C（x 44〜48、z 1〜7、高さ 4）
    _box_house(p, 30.0, 38.0, 3.0, 13.0, 5.0, {
        '-z': {'door2': [(34.0, 2.4, 2.8)], 'low': [(31.4, 1.05), (36.6, 1.05)], 'posts': [32.4, 35.6], 'bands': [3.5],
               'awn': [(32.6, 35.4, 4.4, 'hard', 1.2, 0.25)], 'banners': [(31.4, 4.7)]},
        '-x': {'low': [(5.0, 1.05), (8.0, 1.05), (11.0, 1.05)], 'posts': [6.5, 9.5], 'bands': [3.5]}},
        corners=('sw', 'se', 'nw'), skirt_faces='sw')
    roof_slab(p, 29.85, 38.15, 2.85, 13.15, 4.9, 5.1)
    for z in (5.0, 7.4, 9.8):
        p.place(P.laundry_line(2.0), (34.0, 6.55, z), 0, (3.6, 1, 1))
    for x in (32.15, 35.85):
        p.add('graphite', boxb(x - 0.06, x + 0.06, 5.1, 6.75, 4.4, 10.4))
        p.add('brass', boxb(x - 0.08, x + 0.08, 5.1, 5.3, 4.3, 10.5))
    _box_house(p, 38.0, 45.0, 7.0, 15.0, 7.0, {
        '-z': {'low': [(39.5, 1.05), (42.5, 1.05)], 'high': [(39.5, 4.3), (42.5, 4.3)], 'bands': [3.5], 'posts': [41.0]},
        '+x': {'low': [(9.0, 1.05), (12.5, 1.05)], 'high': [(11.0, 4.3)], 'posts': [11.0], 'bands': [3.5]}},
        corners=('se', 'ne'), skirt_faces='se')
    roof_slab(p, 36.85, 45.15, 6.85, 15.15, 6.9, 7.1)
    p.place(P.water_tower(), (42.5, 7.1, 12.0), 0, 1.25)
    T.canopy(p, 38.2, 41.0, 8.0, 10.6, 7.1, 2.0, 'cloth')
    _box_house(p, 44.0, 48.0, 1.0, 7.0, 4.0, {
        '-z': {'roll': [(46.0, 2.6, 2.4)], 'vents': [(46.0, 3.3)]},
        '-x': {'low': [(4.0, 1.05)], 'posts': [2.5]}},
        corners=('sw', 'nw'), skirt_faces='sw')
    roof_slab(p, 43.85, 48.0, 0.85, 7.15, 3.9, 4.1)
    p.place(P.crate(), (45.0, 4.1, 5.8), 4, 0.8)
    p.place(P.barrel(), (46.6, 4.1, 5.9), 0, 0.8)
    # --- 昇降リフト（L4。床 x 38〜46・z -13〜-5・高さ 0.3、四隅の柱 0.5 角・6 m、上の枠 y 6〜6.5）：geometry の箱は描かず、ここで作る
    _lift(p)
    # --- 禁足扉（L5）：門の塊（x -48〜-42、z ±(3〜16)、高さ 10）・まぐさ（y 6.5〜10）の面の飾り（town_facilities の右下）
    _gate(p)
    return p


def _lift(p: Part):
    """昇降リフト（停止中）：格子の床（黄と黒の縁）、黒鉛の柱、上の枠の巻き上げ機（太い胴・歯車・綱）。geometry と同じ大きさ"""
    x0, x1, z0, z1 = 38.0, 46.0, -13.0, -5.0
    p.add('graphite', boxb(x0, x1, 0.0, 0.26, z0, z1))
    p.add('graphite', boxb(x0 + 0.3, x1 - 0.3, 0.26, 0.3, z0 + 0.3, z1 - 0.3))
    for k in range(int((x1 - x0 - 0.6) / 0.5) + 1):
        x = x0 + 0.3 + k * 0.5
        p.add('brass', boxb(x - 0.02, x + 0.02, 0.29, 0.305, z0 + 0.3, z1 - 0.3))
    # 縁の黄と黒の帯（帆布の赤の代わりに町の真鍮と黒鉛）
    n = 16
    for side in range(4):
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            mat = 'brass' if k % 2 == 0 else 'dark'
            if side == 0:
                p.add(mat, boxb(x0 + (x1 - x0) * t0, x0 + (x1 - x0) * t1, 0.26, 0.31, z1 - 0.3, z1))
            elif side == 1:
                p.add(mat, boxb(x0 + (x1 - x0) * t0, x0 + (x1 - x0) * t1, 0.26, 0.31, z0, z0 + 0.3))
            elif side == 2:
                p.add(mat, boxb(x0, x0 + 0.3, 0.26, 0.31, z0 + 0.3 + (z1 - z0 - 0.6) * t0, z0 + 0.3 + (z1 - z0 - 0.6) * t1))
            else:
                p.add(mat, boxb(x1 - 0.3, x1, 0.26, 0.31, z0 + 0.3 + (z1 - z0 - 0.6) * t0, z0 + 0.3 + (z1 - z0 - 0.6) * t1))
    for x in (38.3, 45.7):
        for z in (-12.7, -5.3):
            p.add('graphite', boxb(x - 0.25, x + 0.25, 0.0, 6.0, z - 0.25, z + 0.25))
            for y in (0.0, 2.0, 4.0, 5.75):
                p.add('brass', boxb(x - 0.28, x + 0.28, y, y + 0.25, z - 0.28, z + 0.28))
            p.add('ivory2', boxb(x - 0.32, x + 0.32, 0.0, 0.5, z - 0.32, z + 0.32))
    # 上の枠（y 6〜6.5、8.5 m 角）：黒鉛の梁、真鍮の角
    fx0, fx1, fz0, fz1 = 37.75, 46.25, -13.25, -4.75
    for a, b, c, d in ((fx0, fx1, fz0, fz0 + 0.5), (fx0, fx1, fz1 - 0.5, fz1), (fx0, fx0 + 0.5, fz0, fz1), (fx1 - 0.5, fx1, fz0, fz1)):
        p.add('graphite', boxb(a, b, 6.0, 6.5, c, d))
    for a, b in ((fx0, fz0), (fx0, fz1), (fx1, fz0), (fx1, fz1)):
        p.add('brass', boxb(a - 0.05 if a < 42 else a - 0.6, a + 0.6 if a < 42 else a + 0.05, 5.95, 6.55,
                            b - 0.05 if b < -9 else b - 0.6, b + 0.6 if b < -9 else b + 0.05))
    for x in (40.0, 44.0):
        p.add('graphite', boxb(x - 0.2, x + 0.2, 6.0, 6.45, fz0 + 0.5, fz1 - 0.5))
    # 巻き上げ機：太い胴（真鍮の輪）・両側の歯車・機械の箱、胴から床の四隅へ下りる綱（停止して床は下にある）
    p.add('graphite', cyl((39.6, 7.2, -9.0), (44.4, 7.2, -9.0), 0.7, 14))
    for x in np.arange(40.0, 44.3, 0.6):
        p.add('brass', cyl((x - 0.05, 7.2, -9.0), (x + 0.05, 7.2, -9.0), 0.74, 14))
    for x in (39.4, 44.6):
        p.add('brass', cyl((x - 0.12, 7.2, -9.0), (x + 0.12, 7.2, -9.0), 1.0, 16))
        for k in range(12):
            a = k * math.pi / 6
            p.add('brass', box((x, 7.2 + 1.05 * math.sin(a), -9.0 + 1.05 * math.cos(a)), (0.2, 0.18, 0.18), 0))
        p.add('graphite', boxb(x - 0.3, x + 0.3, 6.45, 6.9, -9.6, -8.4))
    p.add('graphite', boxb(42.6, 44.2, 6.45, 7.6, -7.6, -6.2))
    p.add('brass', boxb(42.5, 44.3, 7.6, 7.7, -7.7, -6.1))
    p.add('amber', boxb(43.0, 43.8, 6.9, 7.2, -6.21, -6.18))
    for x, z in ((39.0, -12.0), (45.0, -12.0), (39.0, -6.0), (45.0, -6.0)):
        p.add('rope', cyl((x, 0.3, z), (x * 0.25 + 42.0 * 0.75, 6.6, z * 0.25 - 9.0 * 0.75), 0.03, 5, cap=False))
    # 床の真ん中の荷（停止したまま積まれた木箱と樽）は dress_town.py で置く（当たり判定つき）


def _gate(p: Part):
    """禁足扉の門（town_facilities の右下）：両側の白磁の段の塔、黒鉛の扉の枠、真鍮の配管と尖塔。扉そのものは props の door（動く）"""
    # 門の塊の東の面 x=-42（z 3〜16 と -16〜-3、高さ 10）と、まぐさの東の面（z -3〜3、y 6.5〜10）
    for sz in (-1, 1):
        za, zb = sorted((sz * 3.0, sz * 16.0))
        put(p, '+x', (-42.0, (za + zb) / 2), 0.0, {'posts': [sz * 3.1, sz * 7.5, sz * 12.0, sz * 15.9],
                                                     'bands': [3.0, 6.5], 'plates': [(za, zb, 0.0, 10.0)],
                                                     'vents': [(sz * 9.8, 1.6)]}, zb - za, 10.0)
        # 扉の両脇の段の塔（白磁の大きな板と黒鉛の段、上に真鍮の尖塔）
        z0, z1 = sorted((sz * 3.0, sz * 5.4))
        p.add('ivory', boxb(-42.0, -41.55, 0.0, 9.0, z0, z1))
        p.add('ivory2', boxb(-41.55, -41.2, 0.0, 3.2, z0 + 0.1, z1 - 0.1))
        p.add('graphite', boxb(-42.02, -41.5, 9.0, 9.3, z0 - 0.02, z1 + 0.02), boxb(-41.57, -41.18, 3.2, 3.4, z0 + 0.08, z1 - 0.08))
        p.add('brass', boxb(-41.59, -41.16, 0.0, 0.22, z0 + 0.06, z1 - 0.06))
        for zz in (z0 + 0.6, z1 - 0.6):
            P.pipe_run(p, (-42.0, 9.3, zz), (-42.0, 12.2, zz), 0.13, 1.0)
            p.add('brass', lathe((-42.0, 12.2, zz), (-42.0, 13.0, zz), [(0, 0.17), (1, 0.03)], 8))
    # 扉の枠（黒鉛の太い縁、上の角を落とした形）と、まぐさの面の真鍮の飾り板
    p.add('graphite', boxb(-42.0, -41.75, 6.0, 6.5, -3.0, 3.0))
    p.add('graphite', boxb(-42.0, -41.7, 6.5, 7.4, -2.4, 2.4))
    p.add('brass', boxb(-41.72, -41.62, 6.6, 7.3, -1.6, 1.6))
    p.add('cloth2', boxb(-41.64, -41.6, 6.72, 7.18, -1.45, 1.45))
    put(p, '+x', (-42.0, 0.0), 7.4, {'posts': [-2.9, 2.9], 'bands': [9.6 - 7.4]}, 6.0, 2.6)
    # 門の塊の上：真鍮の配管と機械の箱（扉を動かす機械。町の側からは上だけ見える）
    p.add('graphite', boxb(-47.0, -43.0, 10.0, 11.4, -2.6, 2.6))
    p.add('brass', boxb(-47.1, -42.9, 11.4, 11.55, -2.7, 2.7))
    for z in (-1.8, 0.0, 1.8):
        P.pipe_run(p, (-43.2, 10.2, z), (-43.2, 13.8, z), 0.16, 1.0)
        p.add('brass', lathe((-43.2, 13.8, z), (-43.2, 14.4, z), [(0, 0.22), (1, 0.05)], 8))


PARTS = {
    'grime_patch': grime_patch,
    'oil_patch': lambda: grime_patch('oil_decal', 'oil_patch'),
    'lower_set': lower_set,
}
