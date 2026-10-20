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
  grime_patch    汚れの斑（床に置く 1 m の板。材質 grime_decal：キットの "blend": "decal" の材質が床の上に汚れの色を重ねる）

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
from town_geo import Part, Piece, beam, box, boxb, cyl, hang, lathe, sag, sheet, sway, tube


def _pole_flag(p: Part, x, y_top, z, width, length, mat='cloth', amp=0.06, sx=0.0):
    """竿の旗：竿（x, z）の y_top から下へ length、竿から風下（-Z：町は船首の +Z から風を受ける）へ width の布。
    揺れの重みは竿の側 0 から先の 1 へ（town_geo.sway）。sx（±1）なら前のように竿から ±X へ（風の向きに関係しない飾り）"""
    if sx:
        f = lambda u, v: (x + sx * (0.1 + width * u), y_top - length * v, z + amp * math.sin(u * 4 + v))   # noqa: E731
        wfn = lambda v: np.clip((np.abs(v[:, 0] - x) - 0.1) / width, 0, 1) ** 1.2   # noqa: E731
    else:
        f = lambda u, v: (x + amp * math.sin(u * 4 + v), y_top - length * v, z - (0.1 + width * u))   # noqa: E731
        wfn = lambda v: np.clip((z - 0.1 - v[:, 2]) / width, 0, 1) ** 1.2   # noqa: E731
    p.add(mat, sway(sheet(f, 4, 3, 0.02), wfn))

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
        p.add('skyglass', boxb(x - 0.4, x + 0.4, y, y + 0.9, 0.0, 0.012))
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
    """汚れの斑：床の 3 cm 上の 1 m 四方の板（裏は無い）。材質 grime_decal はキットの "blend": "decal"（床の上に汚れの色を半透明で重ねる。
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
    # 屋上：訓練場の旗竿 2 本（赤い旗。船首からの風で風下の -Z へなびく）、給水塔、木箱
    for x in (-29.4, -18.6):
        p.add('brass', cyl((x, 6.6, 6.4), (x, 10.6, 6.4), 0.07, 8))
        p.add('brass', lathe((x, 10.6, 6.4), (x, 10.85, 6.4), [(0, 0.12), (1, 0.02)], 8))
        _pole_flag(p, x, 10.4, 6.4, 0.95, 1.5)
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
    # 操作盤（調べる所：端末の箱 x 39.6〜40.4・z -4.3〜-3.7・高さ 1.2 と同じ所）：黒鉛の台、斜めの盤、真鍮のレバー、琥珀の計器、リフトへの管
    p.add('graphite', boxb(39.6, 40.4, 0.0, 0.95, -4.3, -3.7))
    p.add('brass', boxb(39.58, 40.42, 0.0, 0.1, -4.32, -3.68), boxb(39.58, 40.42, 0.92, 0.98, -4.32, -3.68))
    from town_geo import Piece, _orient
    v = np.array([[39.62, 0.98, -4.28], [40.38, 0.98, -4.28], [40.38, 0.98, -3.72], [39.62, 0.98, -3.72],
                  [39.62, 1.2, -4.28], [40.38, 1.2, -4.28]], float)
    p.add('graphite', _orient(Piece(v, [[0, 1, 2, 3], [4, 5, 1, 0], [3, 2, 5, 4], [0, 3, 4], [1, 5, 2]])))
    p.add('amber', boxb(39.75, 40.0, 1.03, 1.12, -4.0, -3.9))
    for x in (40.12, 40.26):
        p.add('brass', cyl((x, 1.08, -3.95), (x, 1.4, -3.85), 0.018, 5))
        p.add('cloth', cyl((x, 1.4, -3.85), (x, 1.46, -3.83), 0.035, 6))
    P.pipe_run(p, (40.0, 0.3, -4.3), (40.0, 0.3, -5.0), 0.08, 0.5)


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


# ---------------------------------------------------------------- 上段（ch1.upper）

def _notice_ring(p: Part, x, y, z, r=1.5):
    """ギルドの正面の丸い依頼板（town_facilities 右上）：真鍮の輪、暗い板、貼られた紙、十字の黒鉛の棒。面 z（-Z 向き）から 12 cm まで"""
    n = 24
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        pa = np.array([x + r * math.cos(a0), y + r * math.sin(a0)])
        pb = np.array([x + r * math.cos(a1), y + r * math.sin(a1)])
        p.add('brass', beam((pa[0], pa[1], z - 0.06), (pb[0], pb[1], z - 0.06), 0.16, 0.12))
    p.add('dark', S_disc(x, y, z - 0.015, r - 0.05))
    p.add('graphite', boxb(x - r + 0.1, x + r - 0.1, y - 0.05, y + 0.05, z - 0.07, z), boxb(x - 0.05, x + 0.05, y - r + 0.1, y + r - 0.1, z - 0.07, z))
    rng = np.random.default_rng(5)
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.3
        rr = r * (0.35 + 0.35 * (k % 3) / 2)
        cx, cy = x + rr * math.cos(a), y + rr * math.sin(a)
        w, h = rng.uniform(0.3, 0.45), rng.uniform(0.4, 0.55)
        p.add('linen', box((cx, cy, z - 0.085), (w, h, 0.01), 0))
        p.add('brass', box((cx, cy + h / 2 - 0.05, z - 0.095), (0.05, 0.05, 0.01), 0))
    p.add('brass', cyl((x, y, z - 0.11), (x, y, z - 0.02), 0.2, 12))


def S_disc(x, y, z, r, n=24):
    v = [(x, y, z)] + [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n), z) for k in range(n)]
    f = [[0, 1 + (k + 1) % n, 1 + k] for k in range(n)]
    from town_geo import _orient_dir
    return _orient_dir(Piece(np.array(v, float), f), (0, 0, -1))


def _deck_rail(p: Part, a, b, y=1.2):
    """展望台の床の縁の低い壁（0.8 m 厚）の上の真鍮の手すり：2 m ごとの柱、上の棒と中の棒、4 m ごとに小さな灯"""
    T._rail(p, a, b, y, h=0.68, lamps=4.0, step=2.0)


def upper_set() -> Part:
    """上段（ch1.upper）：町長の家（U1）とギルド（U2）の面と屋上、展望台（U3）の床の縁の手すり・望遠鏡・旗"""
    p = Part('upper_set')
    # --- 町長の家（x -29〜-15、z 4〜13、高さ 7。奥まり x -23.6〜-20.4・奥 z 6・高さ 3.8。屋根の板 y 7〜7.6）：
    # 上段の落ち着いた家（緑の多いバルコニー、真鍮の帯、両開きの扉、屋上の庭）
    _house_a(p, -29.0, -15.0, 4.0, 13.0, 7.0, (-23.6, -20.4), 6.0, 3.8,
             front_l={'posts': [-26.3], 'bands': [3.5], 'low': [(-27.7, 1.05), (-25.0, 1.05)], 'high': [(-25.0, 4.9)],
                      'plates': [(-29.0, -23.6, 0.4, 7.0)]},
             front_r={'posts': [-17.7], 'bands': [3.5], 'low': [(-19.1, 1.05), (-16.3, 1.05)], 'high': [(-19.1, 4.9)],
                      'plates': [(-20.4, -15.0, 0.4, 7.0)]},
             lintel={'lamps': [(-24.0, 0.25), (-20.0, 0.25)]},
             sides={'-x': {'posts': [8.5], 'low': [(6.4, 1.05), (10.6, 1.05)], 'high': [(6.4, 4.6), (10.6, 4.6)], 'bands': [3.5]},
                    '+x': {'posts': [8.5], 'low': [(6.4, 1.05), (10.6, 1.05)], 'high': [(8.5, 4.6)], 'bands': [3.5],
                           'vents': [(10.6, 2.6)]}},
             back={'low': [(-26.0, 1.05), (-18.0, 1.05)], 'posts': [-22.0]}, roof_y=7.6)
    roof_slab(p, -29.3, -14.7, 3.7, 13.3, 7.0, 7.6)
    for x0, x1 in ((-28.6, -26.4), (-18.0, -15.8)):
        bp = Part('balcony')
        w = x1 - x0
        T._balcony(bp, -w / 2, w / 2, 4.25)               # 床の下 3.98 m（頭の上）
        T.pot(bp, -0.5, 4.25, 0.5, 0.7)
        T.pot(bp, 0.55, 4.25, 0.5, 0.6)
        p.place(bp, ((x0 + x1) / 2, 0.0, 4.0), 180)
    # 屋上の庭：大きな鉢の木 2 本、鉢植え、赤い帆布の日よけ、給水塔
    p.place(P.planter(1.2, 0.95), (-27.6, 7.6, 11.6), 0, 1.2)
    p.place(P.planter(1.2, 0.95), (-16.6, 7.6, 5.0), 0, 1.0)
    for x, z in ((-25.6, 4.5), (-24.6, 4.5), (-19.4, 4.5), (-18.4, 4.5), (-28.4, 7.0), (-15.6, 9.0)):
        T.pot(p, x, 7.6, z, 0.85)
    T.canopy(p, -24.4, -19.6, 8.4, 11.6, 7.6, 2.0, 'cloth')
    p.place(P.water_tower(), (-17.2, 7.6, 11.6), 0, 1.1)
    # --- 回収屋ギルド（x 12〜28、z 4〜13、高さ 8。奥まり x 18.4〜21.6・奥 z 6・高さ 3.8。屋根の板 y 8〜8.6）：
    # 正面の左に丸い依頼板、右に赤い日よけと品の窓、両脇に吊り灯（town_facilities 右上）
    _house_a(p, 12.0, 28.0, 4.0, 13.0, 8.0, (18.4, 21.6), 6.0, 3.8,
             front_l={'posts': [12.3], 'low': [(13.6, 1.05), (17.0, 1.05)], 'bands': [6.7], 'high': [(13.6, 6.9), (17.0, 6.9)]},
             front_r={'posts': [27.7], 'low': [(23.4, 1.05), (26.2, 1.05)], 'bands': [6.7],
                      'awn': [(22.2, 27.4, 4.55, 'hard', 1.3, 0.3)], 'high': [(23.4, 6.9), (26.2, 6.9)], 'banners': [(24.8, 6.45)]},
             lintel={'lamps': [(18.1, 0.3), (21.9, 0.3)]},
             sides={'-x': {'posts': [8.5], 'low': [(6.0, 1.05), (11.0, 1.05)], 'high': [(6.0, 4.6), (8.5, 4.6), (11.0, 4.6)],
                           'bands': [3.6, 6.7], 'pipes': [(12.6, 4.2, 8.0)]},
                    '+x': {'posts': [8.5], 'low': [(6.0, 1.05), (11.0, 1.05)], 'high': [(6.0, 4.6), (11.0, 4.6)], 'bands': [3.6, 6.7],
                           'door': [(8.5, 1.0, 2.0)]}},
             back={'low': [(15.0, 1.05), (25.0, 1.05)], 'posts': [20.0]}, roof_y=8.6)
    roof_slab(p, 11.7, 28.3, 3.7, 13.3, 8.0, 8.6)
    _notice_ring(p, 15.2, 4.65, 4.0, 1.45)
    # 屋上：旗竿（ギルドの赤い旗。風下の -Z へ）、回収の箱、給水塔、日よけ
    p.add('brass', cyl((26.6, 8.6, 5.0), (26.6, 13.4, 5.0), 0.07, 8))
    _pole_flag(p, 26.6, 13.2, 5.0, 1.3, 1.0, amp=0.08)
    p.place(P.water_tower(), (14.0, 8.6, 11.4), 0, 1.2)
    T.canopy(p, 20.5, 24.5, 8.6, 11.4, 8.6, 2.1, 'cloth2')
    for x, z, s in ((16.6, 12.2, 0.9), (17.5, 12.3, 0.75), (16.9, 12.1, 0.6)):
        p.place(P.crate(), (x, 8.6 if s > 0.7 else 9.27, z), 6 if s > 0.8 else -4, s)
    # --- 展望台（床 x -8〜8・z 16〜28、縁の低い壁 x ±(8〜8.8)・z 28〜28.8、上 1.2）：真鍮の手すり、望遠鏡、南の角の旗
    for sx in (-1, 1):
        _deck_rail(p, (sx * 8.4, 16.4), (sx * 8.4, 28.4))
    _deck_rail(p, (-8.4, 28.4), (8.4, 28.4))
    for sx in (-1, 1):
        x = sx * 8.4
        p.add('brass', cyl((x, 1.2, 16.6), (x, 5.6, 16.6), 0.06, 8))
        p.add('brass', lathe((x, 5.6, 16.6), (x, 5.85, 16.6), [(0, 0.11), (1, 0.02)], 8))
        _pole_flag(p, x, 5.45, 16.6, 1.1, 0.8)
    # 望遠鏡（geometry の台 (0, 0, 24) 1.6×1.2×1.6 と同じ大きさの白磁の台、その上の真鍮の筒）
    p.add('ivory2', boxb(-0.8, 0.8, 0.0, 1.05, 23.2, 24.8))
    p.add('graphite', boxb(-0.82, 0.82, 1.05, 1.2, 23.18, 24.82), boxb(-0.82, 0.82, 0.0, 0.12, 23.18, 24.82))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p.add('brass', boxb(sx * 0.8 - 0.1, sx * 0.8 + 0.1, 0.0, 1.22, 24 + sz * 0.8 - 0.1, 24 + sz * 0.8 + 0.1))
    p.add('graphite', cyl((0, 1.2, 24.0), (0, 1.55, 24.0), 0.28, 12))
    for sx in (-1, 1):
        p.add('brass', boxb(sx * 0.3 - 0.05, sx * 0.3 + 0.05, 1.5, 2.05, 23.9, 24.1))
    a, b = np.array([0.0, 1.75, 23.0]), np.array([0.0, 2.35, 25.6])
    p.add('brass', lathe(a, b, [(0, 0.11), (0.15, 0.13), (0.7, 0.16), (1, 0.2)], 12))
    p.add('graphite', cyl(b - (b - a) * 0.03, b + (b - a) * 0.05, 0.22, 12))
    p.add('dark', cyl(a + (a - b) * 0.04, a, 0.08, 8))
    p.add('graphite', cyl((-0.36, 1.95, 24.0), (0.36, 1.95, 24.0), 0.05, 8))
    return p


# ---------------------------------------------------------------- 訓練場（ch1.training）

def _stripes(p: Part, x0, x1, z0, z1, y, n=None, along='x'):
    """床の上の黄と黒の帯（真鍮と暗い色の交互、床の 1 cm 上）"""
    L = (x1 - x0) if along == 'x' else (z1 - z0)
    n = n or max(2, int(round(L / 0.6)))
    for k in range(n):
        a0, a1 = k / n, (k + 1) / n
        mat = 'brass' if k % 2 == 0 else 'dark'
        if along == 'x':
            p.add(mat, boxb(x0 + (x1 - x0) * a0, x0 + (x1 - x0) * a1, y, y + 0.012, z0, z1))
        else:
            p.add(mat, boxb(x0, x1, y, y + 0.012, z0 + (z1 - z0) * a0, z0 + (z1 - z0) * a1))


def _target(p: Part, x, z, h):
    """的の柱（town_facilities の訓練場：白磁の柱に丸い的の紋、黒鉛の冠、真鍮の帯）。geometry の柱（0.5 角）と同じ大きさ。
    撃つ的の球（props の switch）は柱の上に浮かぶ"""
    p.add('ivory', boxb(x - 0.25, x + 0.25, 0.0, h - 0.12, z - 0.25, z + 0.25))
    p.add('graphite', boxb(x - 0.27, x + 0.27, h - 0.12, h, z - 0.27, z + 0.27), boxb(x - 0.27, x + 0.27, 0.0, 0.12, z - 0.27, z + 0.27))
    p.add('brass', boxb(x - 0.28, x + 0.28, h * 0.45, h * 0.45 + 0.08, z - 0.28, z + 0.28))
    for k in range(16):
        a0, a1 = 2 * math.pi * k / 16, 2 * math.pi * (k + 1) / 16
        for rr, w in ((0.17, 0.035), (0.08, 0.03)):
            pa = (x + rr * math.cos(a0), h * 0.72 + rr * math.sin(a0))
            pb = (x + rr * math.cos(a1), h * 0.72 + rr * math.sin(a1))
            p.add('cloth', beam((pa[0], pa[1], z - 0.262), (pb[0], pb[1], z - 0.262), w, 0.02))
    p.add('cloth', box((x, h * 0.72, z - 0.262), (0.05, 0.05, 0.02), 0))
    # 柱の上の受け（真鍮の皿：撃つ的の球が載る）
    p.add('brass', cyl((x, h, z), (x, h + 0.06, z), 0.2, 10))


def _wreck(p: Part, c0, s0, y0_yaw, c1, s1, y1_yaw, rng):
    """残骸の山（geometry の斜めの箱 2 つと同じ大きさ）：外殻の黒鉛の板・白磁の装甲のかけら・管・歯車。面から 5 cm まで"""
    from town_geo import rot_y
    for (cx, cy, cz), (sx, sy, sz), yaw in ((c0, s0, y0_yaw), (c1, s1, y1_yaw)):
        R = rot_y(yaw)
        p.add('graphite', box((cx, cy + sy / 2, cz), (sx - 0.04, sy - 0.02, sz - 0.04), yaw))
        # 白磁の装甲のかけら（前後の面に貼る板）と、横の面の白磁の板
        for k in range(3):
            w = rng.uniform(0.5, 0.9) * sx / 2
            h = rng.uniform(0.35, 0.6) * sy
            off = rng.uniform(-sx / 4, sx / 4)
            for side in (-1, 1):
                q = R @ np.array([off, 0.0, side * (sz / 2 + 0.01)])
                yy = cy + rng.uniform(0.15, 0.4) * sy + h / 2
                p.add('ivory', box((cx + q[0], yy, cz + q[2]), (w, h, 0.03), yaw))
        for side in (-1, 1):
            q = R @ np.array([side * (sx / 2 + 0.01), 0.0, 0.0])
            p.add('ivory2', box((cx + q[0], cy + sy * 0.55, cz + q[2]), (0.03, sy * 0.5, sz * 0.6), yaw))
        top = cy + sy
        # 上の面の継ぎ目（真鍮の帯、上へは 0.04 m まで）と、横を通る管
        for t in (-0.25, 0.25):
            qa = R @ np.array([t * sx, 0.0, -sz / 2 + 0.05])
            qb = R @ np.array([t * sx, 0.0, sz / 2 - 0.05])
            p.add('brass', beam((cx + qa[0], top + 0.01, cz + qa[2]), (cx + qb[0], top + 0.01, cz + qb[2]), 0.08, 0.03))
        qa = R @ np.array([-sx / 2 + 0.1, 0.0, sz / 2 - 0.12])
        qb = R @ np.array([sx / 2 - 0.1, 0.0, sz / 2 - 0.12])
        P.pipe_run(p, (cx + qa[0], cy + sy * 0.35, cz + qa[2]), (cx + qb[0], cy + sy * 0.35, cz + qb[2]), 0.1, 0.9)
    # 横に倒れた歯車と、まわりの薄いかけら（床の上の薄い物）
    x, _, z = c0
    gx = x - s0[0] * 0.62
    p.add('brass', cyl((gx, 0.0, z + 0.9), (gx, 0.08, z + 0.9), 0.42, 14))
    p.add('graphite', cyl((gx, 0.08, z + 0.9), (gx, 0.1, z + 0.9), 0.14, 8))
    for k in range(4):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(2.2, 2.6)
        p.add('ivory2' if k % 2 else 'graphite', box((x + r * math.cos(a), 0.03, z + r * math.sin(a)),
                                                    (rng.uniform(0.3, 0.6), 0.06, rng.uniform(0.2, 0.4)), rng.uniform(0, 90)))


def _skyline(p: Part, rng, x0, x1, z0, z1, normal, y0, tops, depth=6.0):
    """壁の向こうの家並み（壁の上から見える上の部分だけ。当たり判定なし。カメラは壁の内から出ない）：
    normal（家の正面が向く向き）に面した箱の家、窓の列、屋上の物"""
    def spec(w, top):
        return {'simple': True, 'windows': [(float(u), top - y0 - 2.4) for u in np.arange(-w / 2 + 1.1, w / 2 - 0.8, 1.6)],
                'posts': [-w / 2 + 0.12, w / 2 - 0.12]}
    if normal in ('+x', '-x'):
        z = z0
        while z < z1 - 1.0:
            w = min(float(rng.uniform(5.0, 8.5)), z1 - z)
            top = float(rng.choice(tops))
            hx0, hx1 = (x1 - depth, x1) if normal == '+x' else (x0, x0 + depth)
            T.block(p, hx0, hx1, y0, top, z, z + w, {normal: spec(w, top)}, base=y0, roof='nsew')
            T.roof_items(p, rng, hx0 + 0.6, hx1 - 0.6, top, z + 0.4, z + w - 0.4, 2)
            z += w + float(rng.uniform(0.0, 0.8))
    else:
        x = x0
        while x < x1 - 1.0:
            w = min(float(rng.uniform(5.0, 8.5)), x1 - x)
            top = float(rng.choice(tops))
            hz0, hz1 = (z0, z0 + depth) if normal == '-z' else (z1 - depth, z1)
            T.block(p, x, x + w, y0, top, hz0, hz1, {normal: spec(w, top)}, base=y0, roof='nsew')
            T.roof_items(p, rng, x + 0.4, x + w - 0.4, top, hz0 + 0.6, hz1 - 0.6, 2)
            x += w + float(rng.uniform(0.0, 0.8))


def training_set() -> Part:
    """訓練場（ch1.training）：段の台の縁、的の柱、溝の縁の帯と斜面、残骸の山、壁の面（柱・帯・窓・垂れ幕）、入口の門、
    壁の向こうの家並み、宙に渡した吊り灯の綱"""
    p = Part('training_set')
    rng = np.random.default_rng(23)
    # --- ① 歩く：黄色い床の縁（黒鉛の枠、床の上 2 cm）
    x0, x1, z0, z1 = -3.5, 3.5, -9.7, -6.3
    for a, b, c, d in ((x0 - 0.12, x1 + 0.12, z0 - 0.12, z0), (x0 - 0.12, x1 + 0.12, z1, z1 + 0.12), (x0 - 0.12, x0, z0, z1), (x1, x1 + 0.12, z0, z1)):
        p.add('graphite', boxb(a, b, 0.0, 0.02, c, d))
    # --- ② 跳ぶ：段の台 2 つ（x -4〜4、z -2〜2 の高さ 1.0、z 4〜8 の高さ 1.8）の角の柱と上の縁の帯（面から 3 cm まで）
    for zc, h in ((0.0, 1.0), (6.0, 1.8)):
        za, zb = zc - 2.0, zc + 2.0
        for x in (-4.0, 4.0):
            for z in (za, zb):
                p.add('graphite', boxb(x - 0.08, x + 0.08, 0.0, h, z - 0.08, z + 0.08))
        for a, b, c, d in ((-4.03, 4.03, za - 0.03, za + 0.15), (-4.03, 4.03, zb - 0.15, zb + 0.03), (-4.03, -3.85, za, zb), (3.85, 4.03, za, zb)):
            p.add('brass', boxb(a, b, h - 0.12, h + 0.01, c, d))
        _stripes(p, -3.85, 3.85, za + 0.15, za + 0.45, h, along='x')
    # --- ③ 撃つ：的の柱 3 本
    for x, z, h in ((-8.0, 16.0, 1.3), (0.0, 18.0, 1.6), (8.0, 16.0, 1.3)):
        _target(p, x, z, h)
    # --- ④ 溝（z 26〜30、深さ 1.5）：両側の縁の黄と黒の帯・黒鉛の縁の角、斜面（x -5〜5）の縁の真鍮の帯
    for z, s in ((26.0, -1), (30.0, 1)):
        _stripes(p, -21.9, 21.9, min(z, z + s * 0.5), max(z, z + s * 0.5), 0.0, along='x')
        p.add('graphite', boxb(-22.0, 22.0, -0.12, 0.012, min(z, z - s * 0.03), max(z, z - s * 0.03)))
    for x in (-5.0, 5.0):
        p.add('brass', beam((x, -1.49, 29.4), (x, 0.01, 26.0), 0.12, 0.03))
    # --- ⑤ 残骸を片付ける：geometry の斜めの箱（下 3.4×1.3×2.4 yaw 15、上 1.6×0.8×1.4 yaw -20）と同じ形の残骸
    for (x, z), (tx, tz) in (((-10.0, 42.0), (-9.2, 42.0)), ((9.0, 46.0), (9.8, 46.0)), ((-3.0, 51.0), (-2.2, 51.0))):
        _wreck(p, (x, 0.0, z), (3.4, 1.3, 2.4), 15.0, (tx, 1.3, tz), (1.6, 0.8, 1.4), -20.0, rng)
    # --- 壁の内の面（西 x=-22・東 x=22・南 z=-26・北 z=56、床から 8.5 m）：付け柱・帯・留め板・上の窓・垂れ幕
    for normal, cx in (('+x', -22.0), ('-x', 22.0)):
        lo, hi = -26.0, 56.0
        posts = [float(z) for z in np.arange(lo + 0.1, hi, 4.0)] + [hi - 0.1]
        put(p, normal, (cx, 15.0), 0.0, {'posts': posts, 'bands': [2.0, 4.6, 8.4], 'plates': [(lo, hi, 0.4, 4.0)],
                                         'high': [(float(z), 5.4) for z in np.arange(lo + 6.0, hi - 2.0, 8.0)],
                                         'banners': [(float(z), 4.4) for z in np.arange(lo + 10.0, hi - 4.0, 16.0)]}, 82.0, 8.5)
    put(p, '-z', (0.0, 56.0), 0.0, {'posts': [float(x) for x in np.arange(-21.9, 22.0, 4.0)], 'bands': [2.0, 4.6, 8.4],
                                     'plates': [(-22.0, 22.0, 0.4, 4.0)], 'high': [(-12.0, 5.4), (-4.0, 5.4), (4.0, 5.4), (12.0, 5.4)],
                                     'banners': [(-16.0, 4.4), (16.0, 4.4)]}, 44.0, 10.5)
    # 南の壁（入口）：両開きの大きな門（出口の先。扉の前の床は出口の箱）、門の上の飾り板、両脇の灯
    put(p, '+z', (0.0, -26.0), 0.0, {'posts': [-21.9, -17.9, -13.9, -9.9, -5.4, 5.4, 9.9, 13.9, 17.9, 21.9], 'bands': [4.6, 8.4],
                                      'plates': [(-22.0, -5.6, 0.4, 4.0), (5.6, 22.0, 0.4, 4.0)],
                                      'door2': [(0.0, 4.4, 3.6)], 'lamps': [(-3.4, 4.0), (3.4, 4.0)],
                                      'high': [(-14.0, 5.4), (14.0, 5.4)], 'banners': [(-9.0, 4.4), (9.0, 4.4)]}, 44.0, 8.5)
    p.add('graphite', boxb(-2.8, 2.8, 4.7, 5.9, -26.0, -25.88))
    p.add('cloth', boxb(-2.6, 2.6, 4.82, 5.78, -25.9, -25.86))
    p.add('brass', boxb(-2.9, 2.9, 5.9, 6.02, -26.0, -25.86), boxb(-2.9, 2.9, 4.58, 4.7, -26.0, -25.86))
    # 壁の上の笠木（白磁の縁と黒鉛の帯）
    for a, b, c, d, top in ((-23.0, -22.0, -27.0, 57.0, 8.5), (22.0, 23.0, -27.0, 57.0, 8.5), (-23.0, 23.0, -27.0, -26.0, 8.5),
                            (-23.0, 23.0, 56.0, 57.0, 10.5)):
        p.add('ivory2', boxb(a, b, top, top + 0.3, c, d))
        p.add('graphite', boxb(a - 0.04, b + 0.04, top + 0.3, top + 0.36, c - 0.04, d + 0.04))
    # --- 宙に渡した吊り灯の綱（壁から壁へ、6.9 m・たるみ 0.5。町の明かりの芯）
    for z, xs in ((-10.0, (-14.0, 14.0)), (10.0, (-14.0, 14.0)), (40.0, (-9.0, 0.0, 9.0))):
        pts = sag((-22.0, 6.9, z), (22.0, 6.9, z), 16, 0.5)
        p.add('rope', tube(pts, 0.025, 5))
        for x in xs:
            t = (x + 22.0) / 44.0
            yy = 6.9 - 0.5 * 4 * t * (1 - t)
            P.lantern(p, x, yy - 0.55, z, 1.1)
            p.add('brass', cyl((x, yy - 0.2, z), (x, yy, z), 0.012, 5))
    # --- 壁の向こうの家並み（壁の上 8.5 m から見える。西・東は壁の外、北は町の中段へ上る高い家並み、南は下段の家の背）
    _skyline(p, rng, -32.0, -23.2, -27.0, 57.0, '+x', 6.0, [10.6, 11.4, 12.4, 13.2])
    _skyline(p, rng, 23.2, 32.0, -27.0, 57.0, '-x', 6.0, [10.4, 11.2, 12.2, 13.0])
    _skyline(p, rng, -30.0, 30.0, 57.2, 66.0, '-z', 8.0, [13.5, 15.0, 16.8, 18.2])
    _skyline(p, rng, -30.0, 30.0, -36.0, -27.2, '+z', 6.0, [10.2, 11.0, 12.0])
    return p


# ---------------------------------------------------------------- 屋内（town_interiors：白磁の壁に黒鉛の柱と真鍮の金具、天井の下の赤い布、明るい窓、木の家具）

def _interior(p: Part, x0, x1, z0, z1, h, door=(-1.5, 1.5), lit=None, band=2.4, beam_every=3.0, beam_axis='x', drapes='nwe',
              posts_every=2.4):
    """屋内の壁と天井の飾り。壁の内の面：x0・x1・z0・z1（南の壁 z0 に扉 door の幅）、天井 h。
    lit：{'n'|'e'|'w': [(面に沿ったワールドの座標, 下の y)]} の明るい窓。手の届く高さの物は面から 6 cm まで"""
    lit = lit or {}
    walls = {'s': ('+z', ((x0 + x1) / 2, z0), x1 - x0, x0, x1), 'n': ('-z', ((x0 + x1) / 2, z1), x1 - x0, x0, x1),
             'w': ('+x', (x0, (z0 + z1) / 2), z1 - z0, z0, z1), 'e': ('-x', (x1, (z0 + z1) / 2), z1 - z0, z0, z1)}
    for key, (normal, c, w, a0, a1) in walls.items():
        n = max(1, int(round(w / posts_every)))
        posts = [a0 + 0.1 + k * (w - 0.2) / n for k in range(n + 1)]
        if key == 's':
            posts = [u for u in posts if u < door[0] - 0.35 or u > door[1] + 0.35] + [door[0] - 0.25, door[1] + 0.25]
        spec = {'posts': posts, 'bands': [band, h - 0.1], 'plates': [(a0, a1, 0.4, band)]}
        if key in lit:
            spec['lit'] = lit[key]
        put(p, normal, c, 0.0, spec, w, h)
    # 扉の上の飾り板
    p.add('graphite', boxb(door[0] - 0.3, door[1] + 0.3, 3.35, 3.55, z0, z0 + 0.05))
    # 天井の梁（黒鉛、両端に真鍮）と真ん中の管
    if beam_axis == 'x':
        zs = np.arange(z0 + beam_every / 2, z1 - 0.5, beam_every)
        for z in zs:
            p.add('graphite', boxb(x0, x1, h - 0.24, h, z - 0.12, z + 0.12))
            for x in (x0, x1):
                p.add('brass', boxb(min(x, x + (0.3 if x == x0 else -0.3)), max(x, x + (0.3 if x == x0 else -0.3)), h - 0.3, h, z - 0.15, z + 0.15))
        P.pipe_run(p, ((x0 + x1) / 2 + 1.2, h - 0.45, z0 + 0.2), ((x0 + x1) / 2 + 1.2, h - 0.45, z1 - 0.2), 0.09, 1.5)
    # 天井の下の赤い布（壁ぎわにたるませて張る。下の端は h - 0.75 より上）
    for key in drapes:
        if key in ('n',):
            for k, (xa, xb) in enumerate(_spans(x0 + 0.3, x1 - 0.3, 3.2)):
                p.add('cloth' if k % 2 == 0 else 'cloth2', sheet(lambda u, v, xa=xa, xb=xb: (xa + (xb - xa) * u, h - 0.12 - (0.55 * math.sin(math.pi * u)) * v - 0.08 * v,
                                                                         z1 - 0.08 - 0.25 * v * math.sin(math.pi * u)), 6, 2, 0.02))
        if key in ('w', 'e'):
            x = x0 if key == 'w' else x1
            s_ = 1 if key == 'w' else -1
            for k, (za, zb) in enumerate(_spans(z0 + 0.3, z1 - 0.3, 3.2)):
                p.add('cloth2' if k % 2 == 0 else 'cloth', sheet(lambda u, v, za=za, zb=zb, x=x, s_=s_: (x + s_ * (0.08 + 0.25 * v * math.sin(math.pi * u)),
                                                                                       h - 0.12 - (0.55 * math.sin(math.pi * u)) * v - 0.08 * v,
                                                                                       za + (zb - za) * u), 6, 2, 0.02))


def _spans(a, b, every):
    n = max(1, int(round((b - a) / every)))
    return [(a + k * (b - a) / n, a + (k + 1) * (b - a) / n) for k in range(n)]


def _door_in(p: Part, x0, x1, z, h=3.2, depth=0.2):
    """部屋の入口の扉（geometry の扉の板 x0〜x1・z〜z+depth・高さ h と同じ所）：木の両開きの扉、黒鉛の枠、真鍮の帯"""
    p.add('wood', boxb(x0, x1, 0.0, h, z, z + depth))
    w = x1 - x0
    for k in range(1, 6):
        xx = x0 + k * w / 6
        p.add('dark', boxb(xx - 0.012, xx + 0.012, 0.1, h - 0.1, z + depth, z + depth + 0.01))
    p.add('graphite', boxb(x0 - 0.12, x0 + 0.06, 0.0, h + 0.12, z, z + depth + 0.05), boxb(x1 - 0.06, x1 + 0.12, 0.0, h + 0.12, z, z + depth + 0.05),
          boxb(x0 - 0.12, x1 + 0.12, h - 0.06, h + 0.12, z, z + depth + 0.05))
    for y in (0.5, h - 0.7):
        p.add('graphite', boxb(x0 + 0.08, x1 - 0.08, y, y + 0.1, z + depth, z + depth + 0.03))
    p.add('brass', boxb((x0 + x1) / 2 - 0.25, (x0 + x1) / 2 - 0.05, 1.0, 1.3, z + depth, z + depth + 0.05),
          boxb((x0 + x1) / 2 + 0.05, (x0 + x1) / 2 + 0.25, 1.0, 1.3, z + depth, z + depth + 0.05))
    p.add('dark', boxb((x0 + x1) / 2 - 0.01, (x0 + x1) / 2 + 0.01, 0.05, h - 0.05, z + depth, z + depth + 0.012))


def _rug(p: Part, x0, x1, z0, z1, main='cloth', edge='cloth2'):
    """床の敷物（1.5 cm。赤い布に濃い縁と麻の模様の帯）"""
    p.add(edge, boxb(x0, x1, 0.0, 0.012, z0, z1))
    p.add(main, boxb(x0 + 0.12, x1 - 0.12, 0.0, 0.016, z0 + 0.12, z1 - 0.12))
    for t in (0.22, 0.78):
        zz = z0 + (z1 - z0) * t
        p.add('ivory2', boxb(x0 + 0.3, x1 - 0.3, 0.0, 0.018, zz - 0.025, zz + 0.025))
    p.add(edge, boxb(x0 + 0.45, x1 - 0.45, 0.0, 0.018, z0 + (z1 - z0) * 0.3, z1 - (z1 - z0) * 0.3))
    p.add(main, boxb(x0 + 0.6, x1 - 0.6, 0.0, 0.02, z0 + (z1 - z0) * 0.34, z1 - (z1 - z0) * 0.34))
    for k in range(int((x1 - x0) / 0.6)):
        xx = x0 + 0.3 + k * 0.6
        for zz in (z0 + 0.06, z1 - 0.06):
            p.add('ivory2', box((xx, 0.009, zz), (0.07, 0.019, 0.07), 45))


def _crate_box(p: Part, x0, x1, y0, y1, z0, z1, mat='wood2'):
    """箱形の家具の箱（木の面、黒鉛の角、真鍮の角金具）。外の大きさが x0〜x1・y0〜y1・z0〜z1（geometry の箱に合わせる）"""
    p.add(mat, boxb(x0 + 0.02, x1 - 0.02, y0, y1 - 0.02, z0 + 0.02, z1 - 0.02))
    e = 0.06
    for x in (x0, x1 - e):
        for z in (z0, z1 - e):
            p.add('graphite', boxb(x, x + e, y0, y1, z, z + e))
    for y in (y0, y1 - e):
        p.add('graphite', boxb(x0, x1, y, y + e, z0, z0 + e), boxb(x0, x1, y, y + e, z1 - e, z1),
              boxb(x0, x0 + e, y, y + e, z0, z1), boxb(x1 - e, x1, y, y + e, z0, z1))
    for x in (x0, x1):
        for z in (z0, z1):
            for y in (y0, y1 - 0.12):
                p.add('brass', boxb(x - (0.0 if x == x0 else 0.1) - 0.01, x + (0.1 if x == x0 else 0.0) + 0.01, y, y + 0.12,
                                    z - (0.0 if z == z0 else 0.1) - 0.01, z + (0.1 if z == z0 else 0.0) + 0.01))


def _shelf_unit(p: Part, x0, x1, z0, z1, h, facing, rng, items=True, boards=None):
    """棚（geometry の箱と同じ外の大きさ）：黒鉛の枠、木の段板、段の上の小物（壺・瓶・本・歯車・箱）。facing：開いた面の向き '+x' '-x' '+z' '-z'"""
    boards = boards or [0.1, h * 0.36, h * 0.66, h - 0.06]
    # 背板と枠
    if facing in ('+x', '-x'):
        xb0, xb1 = (x0, x0 + 0.06) if facing == '+x' else (x1 - 0.06, x1)
        p.add('wood', boxb(xb0, xb1, 0.0, h, z0, z1))
        for z in (z0, z1 - 0.07):
            p.add('graphite', boxb(x0, x1, 0.0, h, z, z + 0.07))
        for y in boards:
            p.add('wood2', boxb(x0, x1, y - 0.05, y, z0 + 0.07, z1 - 0.07))
        L = z1 - z0
    else:
        zb0, zb1 = (z0, z0 + 0.06) if facing == '+z' else (z1 - 0.06, z1)
        p.add('wood', boxb(x0, x1, 0.0, h, zb0, zb1))
        for x in (x0, x1 - 0.07):
            p.add('graphite', boxb(x, x + 0.07, 0.0, h, z0, z1))
        for y in boards:
            p.add('wood2', boxb(x0 + 0.07, x1 - 0.07, y - 0.05, y, z0, z1))
        L = x1 - x0
    p.add('graphite', boxb(x0 - 0.02, x1 + 0.02, h - 0.06, h, z0 - 0.02, z1 + 0.02))
    if not items:
        return
    depth = (x1 - x0) if facing in ('+x', '-x') else (z1 - z0)
    for yb, yt in zip(boards[:-1], boards[1:]):
        room_h = yt - yb - 0.08
        t = 0.12
        while t < L - 0.25:
            kind = int(rng.integers(0, 6))
            u = t
            mid = 0.5 * depth
            if facing in ('+x', '-x'):
                cx, cz = (x0 + mid if facing == '+x' else x1 - mid), z0 + u
            else:
                cx, cz = x0 + u, (z0 + mid if facing == '+z' else z1 - mid)
            hh = min(room_h, float(rng.uniform(0.18, 0.4)))
            if kind == 0:
                r = float(rng.uniform(0.07, 0.12))
                p.add('ivory' if rng.random() < 0.5 else 'brass', lathe((cx, yb, cz), (cx, yb + hh, cz), [(0, r * 0.7), (0.5, r), (0.85, r * 0.55), (1, r * 0.45)], 8))
                t += 2 * r + 0.08
            elif kind == 1:
                n = int(rng.integers(3, 7))
                for j in range(n):
                    bw = 0.05
                    mat = ['cloth', 'cloth2', 'wood', 'linen', 'green'][int(rng.integers(0, 5))]
                    bh = min(room_h, float(rng.uniform(0.18, 0.3)))
                    if facing in ('+x', '-x'):
                        p.add(mat, boxb(cx - depth * 0.3, cx + depth * 0.3, yb, yb + bh, cz + j * bw, cz + j * bw + bw - 0.005))
                    else:
                        p.add(mat, boxb(cx + j * bw, cx + j * bw + bw - 0.005, yb, yb + bh, cz - depth * 0.3, cz + depth * 0.3))
                t += n * 0.05 + 0.1
            elif kind == 2:
                r = float(rng.uniform(0.1, 0.16))
                axis = (1, 0, 0) if facing in ('+x', '-x') else (0, 0, 1)
                c = np.array([cx, yb + r, cz])
                p.add('brass', cyl(c - np.array(axis) * 0.03, c + np.array(axis) * 0.03, r, 12))
                p.add('graphite', cyl(c - np.array(axis) * 0.04, c + np.array(axis) * 0.04, r * 0.35, 8))
                t += 2 * r + 0.08
            elif kind == 3:
                bw = float(rng.uniform(0.2, 0.35))
                p.add('wood2' if rng.random() < 0.5 else 'ivory2', box((cx, yb + min(room_h, 0.2) / 2, cz), (bw if facing in ('+z', '-z') else depth * 0.6, min(room_h, 0.2), depth * 0.6 if facing in ('+z', '-z') else bw), 0))
                t += bw + 0.08
            elif kind == 4:
                for j in range(3):
                    off = j * 0.09
                    if facing in ('+x', '-x'):
                        p.add('dark' if j == 1 else 'green', cyl((cx, yb, cz + off), (cx, yb + hh * 0.8, cz + off), 0.035, 6))
                    else:
                        p.add('dark' if j == 1 else 'green', cyl((cx + off, yb, cz), (cx + off, yb + hh * 0.8, cz), 0.035, 6))
                t += 0.32
            else:
                t += float(rng.uniform(0.1, 0.3))


def _table(p: Part, x0, x1, z0, z1, h, top='wood2', legs='graphite', cloth=None):
    """机・卓（geometry の箱と同じ外の大きさ）：天板、脚、前の板（引き出し）"""
    p.add(top, boxb(x0, x1, h - 0.08, h, z0, z1))
    p.add('graphite', boxb(x0 - 0.01, x1 + 0.01, h - 0.11, h - 0.08, z0 - 0.01, z1 + 0.01))
    for x in (x0 + 0.04, x1 - 0.12):
        for z in (z0 + 0.04, z1 - 0.12):
            p.add(legs, boxb(x, x + 0.08, 0.0, h - 0.08, z, z + 0.08))
    p.add('wood', boxb(x0 + 0.1, x1 - 0.1, h - 0.36, h - 0.11, z0 + 0.06, z1 - 0.06))
    p.add('wood', boxb(x0 + 0.08, x1 - 0.08, 0.12, 0.2, z0 + 0.1, z1 - 0.1))
    if cloth:
        p.add(cloth, sheet(lambda u, v: (x0 + 0.2 + (x1 - x0 - 0.4) * u if (x1 - x0) > (z1 - z0) else (x0 + x1) / 2 - 0.3 + 0.6 * u,
                                         h + 0.005 - (0.0 if v < 0.8 else (v - 0.8) * 2.0),
                                         z0 - 0.02 + (z1 - z0 + 0.04) * min(v, 0.8) / 0.8 if (x1 - x0) > (z1 - z0) else z0 + (z1 - z0) * v), 3, 5, 0.01))


def _desk_items(p: Part, x0, x1, z, y, rng, n=6):
    """机の上の物（本・紙・携行灯・小さな鉢・部品）。x0〜x1 に並べる、奥 z"""
    x = x0 + 0.15
    k = 0
    while x < x1 - 0.2 and k < n:
        kind = k % 5
        if kind == 0:
            for j in range(3):
                p.add(['cloth', 'wood', 'linen'][j], boxb(x, x + 0.32, y + j * 0.06, y + j * 0.06 + 0.055, z - 0.22, z + 0.02))
            x += 0.42
        elif kind == 1:
            p.add('linen', box((x + 0.18, y + 0.004, z - 0.15), (0.36, 0.008, 0.26), float(rng.uniform(-20, 20))))
            x += 0.42
        elif kind == 2:
            p.place(P.hand_lantern(), (x + 0.15, y, z - 0.1), 0, 0.6)
            x += 0.35
        elif kind == 3:
            T.pot(p, x + 0.15, y, z - 0.12, 0.35)
            x += 0.35
        else:
            p.add('brass', cyl((x + 0.12, y, z - 0.1), (x + 0.12, y + 0.04, z - 0.1), 0.11, 10))
            p.add('graphite', cyl((x + 0.12, y + 0.04, z - 0.1), (x + 0.12, y + 0.14, z - 0.1), 0.04, 6))
            x += 0.32
        k += 1


def _sconce(p: Part, x, y, z, normal):
    """壁の灯（平たい：真鍮の板と琥珀のガラス、面から 12 cm）"""
    lp = Part('sconce')
    lp.add('brass', boxb(-0.12, 0.12, -0.25, 0.25, 0.0, 0.03))
    lp.add('amber', boxb(-0.07, 0.07, -0.16, 0.12, 0.03, 0.11))
    lp.add('brass', boxb(-0.09, 0.09, 0.12, 0.17, 0.03, 0.13), boxb(-0.09, 0.09, -0.21, -0.16, 0.03, 0.13))
    p.place(lp, (x, y, z), YAW[normal])


def home_set() -> Part:
    """ハルの家（ch1.home：14×4.5×12、壁の内 x ±7・z ±6）。town_interiors の右：木箱で組んだベッド（赤い掛け布と枕）、
    ベッドの横の台と携行灯（調べるとベッド。端末の箱と同じ所）、机（本・灯・鉢）、ガラクタの棚（歯車・瓶・ロボの頭）、
    衣装箱、父の写真、明るい窓、赤い敷物、天井の梁と赤い布、扉"""
    p = Part('home_set')
    rng = np.random.default_rng(41)
    _interior(p, -7.0, 7.0, -6.0, 6.0, 4.5, door=(-1.5, 1.5), lit={'e': [(1.2, 1.3), (-1.6, 1.3)], 'n': [(1.6, 1.4)]}, band=2.4)
    _door_in(p, -1.5, 1.5, -6.05, 3.2, 0.2)
    # ベッド（geometry：x -7〜-4・z 1.5〜6・高さ 0.6、上に掛け布の巻き x -6.2〜-5.0・z 2.7〜4.3・y 0.6〜0.9）
    _crate_box(p, -7.0, -4.0, 0.0, 0.42, 1.5, 6.0, 'wood')
    for z in (1.5, 3.0, 4.5):
        p.add('graphite', boxb(-4.06, -4.0, 0.05, 0.37, z + 0.05, z + 1.45))
    p.add('linen', boxb(-6.95, -4.05, 0.42, 0.56, 1.55, 5.95))
    p.add('cloth', sheet(lambda u, v: (-7.0 + 3.05 * u, 0.6 + 0.012 - (0.0 if u < 0.94 else (u - 0.94) * 4.0), 1.45 + 3.2 * v), 5, 6, 0.015))
    p.add('cloth2', boxb(-6.2, -5.0, 0.6, 0.88, 2.7, 4.3))
    p.add('linen', boxb(-6.15, -5.05, 0.62, 0.9, 2.95, 3.25))
    for x in (-6.4, -5.1):
        p.add('linen', boxb(x - 0.45, x + 0.45, 0.58, 0.7, 5.2, 5.85))
    p.add('cloth', boxb(-5.2, -4.4, 0.6, 0.7, 5.25, 5.85))
    # 頭の板（北の壁ぎわ。壁から 12 cm）と、その上の父の写真
    p.add('wood', boxb(-6.95, -4.05, 0.42, 1.5, 5.88, 6.0))
    p.add('graphite', boxb(-7.0, -4.0, 1.44, 1.52, 5.86, 6.0))
    p.add('graphite', boxb(-6.05, -4.95, 2.15, 2.95, 5.95, 6.0))
    p.add('brass', boxb(-6.0, -5.0, 2.2, 2.9, 5.93, 5.96))
    p.add('linen', boxb(-5.93, -5.07, 2.27, 2.83, 5.91, 5.93))
    # ベッドの横の台（端末の箱：x -4.8〜-4.2・z 3.1〜3.9・高さ 1.2）：木箱を 2 段、上に携行灯（ベッドの明かり）
    _crate_box(p, -4.8, -4.2, 0.0, 0.6, 3.1, 3.9, 'wood2')
    _crate_box(p, -4.8, -4.2, 0.6, 1.2, 3.1, 3.9, 'ivory2')
    p.place(P.hand_lantern(), (-4.5, 1.2, 3.5), 0, 0.62)
    # 机（x 2〜5・z -2.6〜-1.4・高さ 0.9）と上の物、前の踏み台は dress_town.py（当たり判定つき）
    _table(p, 2.0, 5.0, -2.6, -1.4, 0.9)
    _desk_items(p, 2.05, 4.95, -1.55, 0.9, rng, 7)
    # ガラクタの棚（x 4.7〜6.3・z -5〜-4・高さ 2.2、開いた面は北）
    _shelf_unit(p, 4.7, 6.3, -5.0, -4.0, 2.2, '+z', rng)
    p.add('ivory', lathe((5.5, 2.2, -4.5), (5.5, 2.6, -4.5), [(0, 0.2), (0.5, 0.24), (1, 0.12)], 10))      # 棚の上のロボの頭（ガラクタ）
    p.add('amber', cyl((5.42, 2.4, -4.26), (5.42, 2.4, -4.24), 0.04, 6), cyl((5.6, 2.4, -4.26), (5.6, 2.4, -4.24), 0.04, 6))
    # 衣装箱（x -6.1〜-4.9・z -4〜-2・高さ 1.6）
    _crate_box(p, -6.1, -4.9, 0.0, 1.6, -4.0, -2.0, 'wood')
    for y in (0.4, 0.95):
        p.add('brass', boxb(-4.9, -4.86, y, y + 0.08, -3.3, -2.7))
    # 敷物と、セーブビーコンの台の真鍮の輪
    _rug(p, -2.6, 2.4, -1.2, 3.2)
    p.add('brass', cyl((4.5, 0.0, 3.0), (4.5, 0.02, 3.0), 0.95, 20))
    p.add('graphite', cyl((4.5, 0.0, 3.0), (4.5, 0.025, 3.0), 0.75, 20))
    # 東の壁の高い棚（3.2 m）と瓶、北の壁の鉢植え、壁の灯
    p.add('wood2', boxb(6.72, 7.0, 3.15, 3.22, -3.6, -0.4))
    for z in np.arange(-3.4, -0.6, 0.38):
        p.add('ivory' if int(z * 10) % 2 else 'green', lathe((6.86, 3.22, z), (6.86, 3.5, z), [(0, 0.06), (0.6, 0.09), (1, 0.04)], 8))
    _sconce(p, 6.0, 2.9, 6.0, '-z')
    _sconce(p, -3.2, 2.9, 6.0, '-z')
    _sconce(p, -7.0, 2.9, -0.8, '+x')
    _hanging(p, 0.0, 0.0, 4.5, 3.95)
    return p


def _hanging(p: Part, x, z, top, y, s=1.2):
    """天井から鎖で吊った灯（芯の高さ y）"""
    for k in range(int((top - y - 0.35) / 0.12)):
        yy = top - k * 0.12
        p.add('graphite', boxb(x - 0.02, x + 0.02, yy - 0.1, yy, z - (0.03 if k % 2 else 0.01), z + (0.03 if k % 2 else 0.01)))
    P.lantern(p, x, y, z, s)


def workshop_set() -> Part:
    """ヤーナの工房（ch1.workshop：20×6×14、壁の内 x ±10・z ±7）。town_interiors の左：大きな作業台と工具の板、
    台の前の万力の台（調べると作業台。端末の箱と同じ所）、旋盤、部品の棚、炉、天井の配管と鎖、赤い布、明るい窓"""
    p = Part('workshop_set')
    rng = np.random.default_rng(43)
    _interior(p, -10.0, 10.0, -7.0, 7.0, 6.0, door=(-1.5, 1.5), lit={'w': [(-4.6, 2.8), (4.6, 2.8)], 'e': [(3.6, 2.8)]}, band=3.0,
              beam_every=3.5, posts_every=2.5)
    _door_in(p, -1.5, 1.5, -7.05, 3.2, 0.2)
    # 作業台（x -8〜-2・z 5.2〜6.8・高さ 1.0）：厚い木の天板、黒鉛の脚、下の引き出しと木箱、上の工具・部品・灯
    _table(p, -8.0, -2.0, 5.2, 6.8, 1.0)
    for x in (-7.6, -6.4, -3.4):
        _crate_box(p, x - 0.45, x + 0.45, 0.22, 0.72, 5.35, 6.65, 'wood2')
    _desk_items(p, -7.9, -2.1, 6.65, 1.0, rng, 9)
    p.add('graphite', boxb(-4.2, -3.1, 1.0, 1.32, 5.5, 6.2))                       # 台の上の小さな機械（計器）
    p.add('brass', cyl((-3.65, 1.32, 5.85), (-3.65, 1.38, 5.85), 0.2, 12))
    # 工具の板（北の壁、台の上 1.4〜3.2 m、面から 6 cm）：板と掛けた工具
    p.add('wood', boxb(-8.0, -2.0, 1.4, 3.2, 6.94, 7.0))
    p.add('graphite', boxb(-8.05, -1.95, 1.36, 1.42, 6.9, 7.0), boxb(-8.05, -1.95, 3.18, 3.24, 6.9, 7.0))
    for k, x in enumerate(np.arange(-7.6, -2.3, 0.42)):
        L = 0.35 + 0.25 * ((k * 7) % 3) / 2
        p.add('graphite' if k % 3 else 'brass', boxb(x - 0.025, x + 0.025, 2.9 - L, 2.9, 6.88, 6.93))
        p.add('graphite', boxb(x - 0.07, x + 0.07, 2.9 - L - 0.08, 2.9 - L, 6.88, 6.93))
    for x in np.arange(-7.4, -2.5, 0.9):
        p.add('brass', boxb(x - 0.12, x + 0.12, 1.65, 1.71, 6.86, 6.94))
    # 万力の台（端末の箱 x -5.4〜-4.6・z 4.2〜4.8・高さ 1.2 と、geometry の箱 z 4.8〜5.2・高さ 1.1）：黒鉛の台、上に真鍮の万力
    p.add('graphite', boxb(-5.4, -4.6, 0.0, 1.05, 4.2, 5.2))
    p.add('brass', boxb(-5.42, -4.58, 0.0, 0.12, 4.18, 5.22), boxb(-5.42, -4.58, 0.9, 1.0, 4.18, 5.22))
    p.add('graphite', boxb(-5.3, -4.7, 1.05, 1.2, 4.3, 4.9))
    p.add('brass', boxb(-5.25, -4.75, 1.05, 1.15, 4.2, 4.3), cyl((-5.0, 1.12, 4.12), (-5.0, 1.12, 4.25), 0.035, 6))
    # 旋盤（x 4〜8・z 5.6〜6.8・高さ 1.2）
    p.add('graphite', boxb(4.02, 7.98, 0.0, 0.85, 5.62, 6.78))
    p.add('ivory2', boxb(4.1, 7.9, 0.85, 0.95, 5.65, 6.75))
    p.add('graphite', boxb(4.2, 5.2, 0.95, 1.2, 5.75, 6.65), boxb(6.9, 7.8, 0.95, 1.15, 5.8, 6.6))
    p.add('brass', cyl((5.2, 1.08, 6.2), (6.9, 1.08, 6.2), 0.05, 8), cyl((4.0, 0.7, 6.2), (4.02, 0.7, 6.2), 0.32, 14))
    for k in range(10):
        a = k * math.pi / 5
        p.add('brass', box((4.01, 0.7 + 0.34 * math.sin(a), 6.2 + 0.34 * math.cos(a)), (0.02, 0.07, 0.07), 0))
    # 部品の棚（西 x -9.2〜-7.8・z -3〜3・高さ 2.4 は東向き、東 x 7.8〜9.2・z -3.5〜1.5・高さ 2.0 は西向き）
    _shelf_unit(p, -9.2, -7.8, -3.0, 3.0, 2.4, '+x', rng)
    _shelf_unit(p, 7.8, 9.2, -3.5, 1.5, 2.0, '-x', rng, boards=[0.1, 0.7, 1.35, 1.94])
    # 炉（北東の角：x 8.4〜10・z 4〜7 の外の壁ぎわ、煙突は天井へ。橙の明かりの芯）
    p.add('graphite', boxb(8.8, 9.98, 0.0, 1.6, 2.6, 4.4))
    p.add('ivory2', boxb(8.75, 9.98, 1.6, 1.75, 2.55, 4.45))
    p.add('dark', boxb(8.74, 8.8, 0.35, 0.95, 3.0, 4.0))
    p.add('amber', boxb(8.72, 8.76, 0.38, 0.52, 3.1, 3.9))                          # 炉の口の奥の熾火（下の細い帯だけ光る）
    p.add('graphite', boxb(8.72, 8.8, 0.3, 0.38, 2.95, 4.05), boxb(8.72, 8.8, 0.92, 1.0, 2.95, 4.05))
    P.pipe_run(p, (9.4, 1.75, 3.5), (9.4, 5.95, 3.5), 0.22, 1.0)
    # 天井の配管（両側の壁の上、5 m より上）と鎖と鉤（作業台と旋盤の上）
    for x in (-9.6, 9.6):
        P.pipe_run(p, (x, 5.2, -6.8), (x, 5.2, 6.8), 0.14, 1.4)
    P.pipe_run(p, (-9.8, 4.75, 6.6), (9.8, 4.75, 6.6), 0.11, 1.4)
    for x, z, y1 in ((-5.0, 6.0, 2.6), (6.0, 6.2, 2.9)):
        for k in range(int((6.0 - y1) / 0.12)):
            y = 6.0 - k * 0.12
            p.add('graphite', boxb(x - 0.02, x + 0.02, y - 0.1, y, z - (0.04 if k % 2 else 0.01), z + (0.04 if k % 2 else 0.01)))
        p.add('brass', tube([(x, y1, z), (x, y1 - 0.18, z), (x + 0.12, y1 - 0.28, z), (x + 0.2, y1 - 0.18, z)], 0.025, 5))
    # 北の壁の高い所の大きな歯車（回収した機械の部品）と、東の壁の配管の弁
    p.add('brass', cyl((4.5, 4.4, 6.94), (4.5, 4.4, 7.0), 1.1, 24))
    p.add('graphite', cyl((4.5, 4.4, 6.9), (4.5, 4.4, 6.94), 0.35, 12))
    for k in range(14):
        a = k * math.pi / 7
        p.add('brass', box((4.5 + 1.2 * math.cos(a), 4.4 + 1.2 * math.sin(a), 6.97), (0.22, 0.22, 0.06), 0))
    for z in (-2.0, 2.4):
        p.add('graphite', boxb(9.82, 10.0, 3.2, 4.6, z - 0.08, z + 0.08))
        p.add('brass', cyl((9.7, 4.0, z), (9.86, 4.0, z), 0.22, 12))
    # 西の壁の上の段の棚（板と瓶・箱）
    p.add('wood2', boxb(-10.0, -9.72, 3.4, 3.47, -2.8, 2.8))
    for z in np.arange(-2.5, 2.6, 0.45):
        p.add('ivory' if int(z * 10) % 3 else 'brass', lathe((-9.86, 3.47, z), (-9.86, 3.75, z), [(0, 0.07), (0.6, 0.1), (1, 0.05)], 8))
    # 敷物（入口の前）と、壁の灯
    _rug(p, -2.2, 2.2, -5.6, -3.2, 'cloth2', 'cloth')
    for x in (-6.0, 2.5):
        _sconce(p, x, 3.6, 7.0, '-z')
    _sconce(p, -10.0, 3.8, -1.0, '+x')
    _sconce(p, 10.0, 3.8, -4.5, '-x')
    _hanging(p, 0.0, 0.0, 6.0, 5.1, 1.3)
    return p


def guild_set() -> Part:
    """回収屋ギルド（ch1.guild：24×6×16、壁の内 x ±12・z ±8）：受付台 2 つ（つなぎの箱つき）、バートンの前の小さな台、
    依頼板（端末の箱と、その後ろの箱が書見台）、壁の地図と大きな歯車、回収品の棚、ギルドの旗、天井の吊り灯"""
    p = Part('guild_set')
    rng = np.random.default_rng(47)
    _interior(p, -12.0, 12.0, -8.0, 8.0, 6.0, door=(-1.5, 1.5), lit={'w': [(-4.0, 2.6), (2.0, 2.6)], 'e': [(-4.0, 2.6)]}, band=3.0,
              beam_every=4.0, posts_every=2.6)
    _door_in(p, -1.5, 1.5, -8.05, 3.2, 0.2)
    # 受付台：左（x -10.5〜-3.5・z 6.4〜7.6）、真ん中（x -3〜3・z 5.9〜7.1）、つなぎ（x -3.5〜-3・z 6.4〜7.1）、
    # バートンの前の小さな台（x -0.3〜0.3・z 5.3〜5.9）。どれも高さ 1.1
    for x0, x1, z0, z1 in ((-10.5, -3.5, 6.4, 7.6), (-3.0, 3.0, 5.9, 7.1), (-3.5, -3.0, 6.4, 7.1), (-0.3, 0.3, 5.3, 5.9)):
        p.add('graphite', boxb(x0 + 0.02, x1 - 0.02, 0.0, 0.98, z0 + 0.02, z1 - 0.02))
        p.add('wood2', boxb(x0, x1, 0.98, 1.1, z0, z1))
        p.add('brass', boxb(x0 - 0.01, x1 + 0.01, 0.92, 0.98, z0 - 0.01, z1 + 0.01), boxb(x0 - 0.01, x1 + 0.01, 0.0, 0.1, z0 - 0.01, z1 + 0.01))
        for x in np.arange(x0 + 0.5, x1 - 0.3, 1.0):
            p.add('wood', boxb(x - 0.4, x + 0.4, 0.2, 0.85, z0 - 0.01, z0 + 0.02))
    # 台の上：帳面・判子・天秤・ランプ（1.1 m の上、端から 0.1 m。上に乗る所は dress_town.py の乗れない柱）
    for x in (-9.6, -7.2, -5.0):
        p.add('linen', box((x, 1.105, 7.0), (0.42, 0.01, 0.3), float(rng.uniform(-15, 15))))
        p.add('cloth', boxb(x + 0.3, x + 0.52, 1.1, 1.16, 6.8, 7.1))
    p.place(P.hand_lantern(), (-8.4, 1.1, 7.3), 0, 0.6)
    p.add('brass', cyl((1.8, 1.1, 6.7), (1.8, 1.5, 6.7), 0.02, 6), boxb(1.45, 2.15, 1.5, 1.52, 6.69, 6.71))
    for x in (1.48, 2.12):
        p.add('brass', cyl((x, 1.38, 6.7), (x, 1.4, 6.7), 0.1, 10))
    p.add('linen', box((-1.4, 1.105, 6.5), (0.5, 0.01, 0.34), 8))
    # 依頼板（geometry：x 5〜9・z 7.4〜7.8・高さ 2.4）：真鍮の枠の板と紙、上にギルドの丸い紋
    p.add('wood', boxb(5.0, 9.0, 0.0, 2.4, 7.42, 7.8))
    p.add('graphite', boxb(4.95, 9.05, 0.0, 2.45, 7.38, 7.44))
    p.add('dark', boxb(5.15, 8.85, 0.5, 2.25, 7.36, 7.38))
    p.add('brass', boxb(4.92, 9.08, 2.4, 2.5, 7.36, 7.8), boxb(4.92, 9.08, 0.42, 0.5, 7.36, 7.45))
    for k in range(14):
        x = 5.4 + (k % 7) * 0.5 + float(rng.uniform(-0.05, 0.05))
        y = 0.75 + (k // 7) * 0.75 + float(rng.uniform(-0.08, 0.08))
        p.add('linen', box((x, y, 7.35), (0.36, 0.48, 0.01), float(rng.uniform(-6, 6))))
        p.add('cloth', box((x, y + 0.2, 7.34), (0.05, 0.05, 0.01), 0))
    _notice_ring(p, 7.0, 3.6, 7.98, 0.75)
    # 書見台（端末の箱 x 6.6〜7.4・z 6.2〜6.8・高さ 1.2 と、後ろの箱 x 6.6〜7.4・z 6.8〜7.4・高さ 1.2）
    p.add('graphite', boxb(6.62, 7.38, 0.0, 1.0, 6.22, 7.38))
    p.add('wood2', boxb(6.6, 7.4, 1.0, 1.2, 6.2, 7.4))
    p.add('linen', box((7.0, 1.21, 6.6), (0.5, 0.01, 0.36), 0))
    p.add('brass', boxb(6.58, 7.42, 0.0, 0.1, 6.18, 7.42))
    # 壁：西の壁の大きな地図（オルドの背の町の配置図）、東の壁の大きな歯車（回収の誇り）、北の壁の上の旗
    p.add('graphite', boxb(-12.0, -11.95, 1.4, 3.6, -2.0, 2.0))
    p.add('linen', boxb(-11.95, -11.93, 1.5, 3.5, -1.9, 1.9))
    for z, y in ((-1.2, 2.2), (0.0, 2.8), (0.9, 2.0), (-0.4, 3.1), (1.4, 3.0)):
        p.add('cloth', boxb(-11.93, -11.92, y - 0.12, y + 0.12, z - 0.12, z + 0.12))
    p.add('brass', cyl((11.94, 3.6, 2.0), (12.0, 3.6, 2.0), 1.3, 24))
    p.add('graphite', cyl((11.9, 3.6, 2.0), (11.94, 3.6, 2.0), 0.4, 12))
    for k in range(16):
        a = k * math.pi / 8
        p.add('brass', box((11.97, 3.6 + 1.4 * math.sin(a), 2.0 + 1.4 * math.cos(a)), (0.06, 0.24, 0.24), 0))
    for x in (-9.0, -5.0, 5.0, 10.6):
        p.place(P.banner(1.0, 1.8, sway_k=0.0), (x, 5.5, 8.0), 180)      # 屋内は風が無いので揺らさない
    # 回収品の棚（東の壁、z -6〜-1 の高い棚。開いた面は西）
    _shelf_unit(p, 11.0, 11.98, -6.6, -1.4, 2.6, '-x', rng)
    # 天井の吊り灯 2 つ（4.6 m より上）
    for x in (-5.0, 5.0):
        for k in range(8):
            y = 6.0 - k * 0.12
            p.add('graphite', boxb(x - 0.02, x + 0.02, y - 0.1, y, -0.03, 0.03))
        p.add('brass', cyl((x - 0.6, 4.95, 0.0), (x + 0.6, 4.95, 0.0), 0.03, 6), cyl((x, 4.95, -0.6), (x, 4.95, 0.6), 0.03, 6))
        for dx, dz in ((-0.6, 0.0), (0.6, 0.0), (0.0, -0.6), (0.0, 0.6)):
            P.lantern(p, x + dx, 4.75, dz, 0.9)
    _rug(p, -2.0, 2.0, -6.8, -1.0, 'cloth', 'cloth2')
    return p


def mayor_set() -> Part:
    """町長の家（ch1.mayor：14×4.8×12、壁の内 x ±7・z ±6）：大きな机（町長トルーデの前）、本棚、鉢植えの多い明るい部屋、
    オルドの絵図、敷物、扉。手入れの行き届いた家（汚れの弱いキット town_tidy）"""
    p = Part('mayor_set')
    rng = np.random.default_rng(53)
    _interior(p, -7.0, 7.0, -6.0, 6.0, 4.8, door=(-1.5, 1.5), lit={'e': [(-2.6, 1.2), (0.0, 1.2), (2.6, 1.2)], 'n': [(-3.6, 1.3), (3.6, 1.3)]},
              band=2.5, drapes='nwe')
    _door_in(p, -1.5, 1.5, -6.05, 3.2, 0.2)
    # 机（x -2.5〜2.5・z 4.3〜5.7・高さ 0.9）：彫りのある木の机、緑の布、書類・判子・灯
    _table(p, -2.5, 2.5, 4.3, 5.7, 0.9, top='wood', legs='wood')
    p.add('green', boxb(-1.6, 1.6, 0.9, 0.912, 4.5, 5.5))
    _desk_items(p, -2.4, 2.4, 5.6, 0.9, rng, 7)
    for x in (-2.5, 2.48):
        p.add('brass', boxb(x, x + 0.02, 0.3, 0.8, 4.4, 5.6))
    # 本棚（x -6.1〜-4.9・z -3〜3・高さ 2.2、開いた面は東）
    _shelf_unit(p, -6.1, -4.9, -3.0, 3.0, 2.2, '+x', rng, boards=[0.1, 0.62, 1.12, 1.62, 2.14])
    # オルドの絵図（北の壁、机の上）：額と、白磁の亀の形
    p.add('graphite', boxb(-1.6, 1.6, 1.7, 3.5, 5.94, 6.0))
    p.add('linen', boxb(-1.5, 1.5, 1.8, 3.4, 5.92, 5.94))
    p.add('ivory2', box((0.0, 2.6, 5.915), (1.9, 0.9, 0.01), 0))
    p.add('brass', boxb(-1.65, 1.65, 3.45, 3.55, 5.9, 6.0), boxb(-1.65, 1.65, 1.65, 1.75, 5.9, 6.0))
    # 敷物（部屋の真ん中）と、壁の灯
    _rug(p, -3.2, 3.2, -3.4, 2.8)
    _sconce(p, -3.2, 2.9, 6.0, '-z')
    _sconce(p, 3.2, 2.9, 6.0, '-z')
    _sconce(p, 7.0, 3.0, 4.2, '-x')
    _hanging(p, 0.0, 0.0, 4.8, 4.05)
    return p


# ---------------------------------------------------------------- 夜明けの甲羅（ch1.opening）

def opening_set() -> Part:
    """夜明けの甲羅（40×40 の外殻の上、縁は ±20 の低い壁 1.2 m）：床の点検口と通気口（床の上 4 cm まで）、
    北の縁の見張りの台（木の床板と旗竿・携行灯）、縁の外の面の黒鉛の帯。プレイヤーが立つ真ん中は空ける"""
    p = Part('opening_set')
    rng = np.random.default_rng(61)
    # 点検口（真鍮の縁・黒鉛のふた・4 つの留め金）と通気口（黒鉛の格子）
    for x, z, w in ((-12.0, 8.0, 1.6), (12.0, -10.0, 1.6), (-10.0, -14.0, 1.2), (14.0, 12.0, 1.2)):
        p.add('brass', boxb(x - w / 2 - 0.1, x + w / 2 + 0.1, 0.0, 0.03, z - w / 2 - 0.1, z + w / 2 + 0.1))
        p.add('graphite', boxb(x - w / 2, x + w / 2, 0.0, 0.04, z - w / 2, z + w / 2))
        for sx in (-1, 1):
            for sz in (-1, 1):
                p.add('brass', cyl((x + sx * (w / 2 - 0.12), 0.04, z + sz * (w / 2 - 0.12)), (x + sx * (w / 2 - 0.12), 0.06, z + sz * (w / 2 - 0.12)), 0.05, 6))
    for x, z in ((-16.0, -2.0), (16.0, 2.0), (-4.0, 16.0), (6.0, -16.0), (16.0, -16.0), (-16.0, 15.0)):
        p.add('graphite', boxb(x - 0.8, x + 0.8, 0.0, 0.03, z - 0.5, z + 0.5))
        for k in range(6):
            xx = x - 0.65 + k * 0.26
            p.add('dark', boxb(xx - 0.06, xx + 0.06, 0.03, 0.035, z - 0.4, z + 0.4))
    # 外殻の継ぎ目の真鍮の留め金（4 m の板の角）
    for x in np.arange(-16.0, 17.0, 8.0):
        for z in np.arange(-16.0, 17.0, 8.0):
            if abs(x) < 6 and abs(z + 6) < 6:
                continue
            p.add('brass', cyl((x, 0.0, z), (x, 0.03, z), 0.14, 8))
    # 北の縁の見張りの台（床の上の板 4 cm、旗竿と旗、携行灯）：夜明けの地平線を見る所
    p.add('wood', boxb(-4.0, 4.0, 0.0, 0.04, 16.4, 19.9))
    p.add('graphite', boxb(-4.05, 4.05, 0.0, 0.045, 16.35, 16.45))
    for x in (-3.6, 3.6):
        p.add('brass', cyl((x, 1.2, 20.3), (x, 5.6, 20.3), 0.06, 8))
        p.add('brass', lathe((x, 5.6, 20.3), (x, 5.85, 20.3), [(0, 0.11), (1, 0.02)], 8))
        _pole_flag(p, x, 5.45, 20.3, 1.2, 0.85, amp=0.08)
    # 縁の低い壁の外の面（|x|・|z| 21）の黒鉛の帯（下の外殻へ続く継ぎ目）
    for a0, a1, c, axis in ((-21.0, 21.0, -21.0, 'z'), (-21.0, 21.0, 21.0, 'z'), (-21.0, 21.0, -21.0, 'x'), (-21.0, 21.0, 21.0, 'x')):
        for t in np.arange(a0 + 2.0, a1 - 1.0, 4.0):
            if axis == 'z':
                p.add('graphite', boxb(t - 0.1, t + 0.1, -2.0, 1.2, min(c, c + (0.06 if c > 0 else -0.06)), max(c, c + (0.06 if c > 0 else -0.06))))
            else:
                p.add('graphite', boxb(min(c, c + (0.06 if c > 0 else -0.06)), max(c, c + (0.06 if c > 0 else -0.06)), -2.0, 1.2, t - 0.1, t + 0.1))
    return p


# ---------------------------------------------------------------- 禁足扉の扉（props の door の "part"）

def gate_door() -> Part:
    """禁足扉（town_facilities の右下）：黒鉛の両開きの扉、上の角を落とした縁、縦の真鍮の帯と横の帯、真ん中の丸い錠（十字）、
    鋲。原点 = 扉の箱（6×6×1）の下の中心、正面 +Z。開くと箱ごと床へ沈む（PropsView）"""
    p = Part('gate_door')
    p.add('graphite', boxb(-3.0, 3.0, 0.0, 5.4, -0.5, 0.46))
    p.add('graphite', boxb(-2.4, 2.4, 5.4, 6.0, -0.5, 0.46))
    # 角を落とした上の縁（斜めの板）
    from town_geo import Piece, _orient
    for sx in (-1, 1):
        v = np.array([[sx * 2.4, 6.0, -0.5], [sx * 3.0, 5.4, -0.5], [sx * 2.4, 5.4, -0.5],
                      [sx * 2.4, 6.0, 0.46], [sx * 3.0, 5.4, 0.46], [sx * 2.4, 5.4, 0.46]], float)
        p.add('graphite', _orient(Piece(v, [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]])))
    # 扉の継ぎ目と、浮き出た板（縦長の板 2 枚ずつ）
    p.add('dark', boxb(-0.03, 0.03, 0.1, 5.8, 0.46, 0.5))
    for sx in (-1, 1):
        for x0, x1 in ((0.25, 1.35), (1.65, 2.75)):
            a0, a1 = sorted((sx * x0, sx * x1))
            p.add('graphite', boxb(a0, a1, 0.4, 2.55, 0.46, 0.52), boxb(a0, a1, 3.15, 5.2, 0.46, 0.52))
    # 縦の真鍮の帯（左右の扉に 2 本ずつ）と横の帯、真ん中の丸い錠と十字
    for x in (-2.0, -0.6, 0.6, 2.0):
        p.add('brass', boxb(x - 0.09, x + 0.09, 0.2, 5.6 if abs(x) < 1 else 5.3, 0.5, 0.56))
    p.add('brass', boxb(-2.9, 2.9, 2.7, 2.95, 0.5, 0.57))
    p.add('brass', cyl((0, 2.85, 0.5), (0, 2.85, 0.66), 0.75, 24))
    p.add('graphite', cyl((0, 2.85, 0.66), (0, 2.85, 0.7), 0.52, 20))
    p.add('brass', boxb(-0.45, 0.45, 2.78, 2.92, 0.66, 0.74), boxb(-0.07, 0.07, 2.4, 3.3, 0.66, 0.74))
    p.add('brass', cyl((0, 2.85, 0.7), (0, 2.85, 0.78), 0.14, 10))
    # 鋲（縁に沿って）と、足元の真鍮の板
    for x in np.arange(-2.7, 2.8, 0.6):
        for y in (0.25, 5.2):
            p.add('brass', cyl((x, y, 0.46), (x, y, 0.53), 0.05, 6))
    for y in np.arange(0.6, 5.2, 0.6):
        for x in (-2.85, 2.85):
            p.add('brass', cyl((x, y, 0.46), (x, y, 0.53), 0.05, 6))
    p.add('brass', boxb(-3.0, 3.0, 0.0, 0.18, 0.46, 0.55))
    return p


# ---------------------------------------------------------------- 通りに渡す小旗の綱

def bunting(L=10.0, sag=0.8, step=0.55) -> Part:
    """通りの上に渡す小旗の綱（town_mood_day の赤い布の町）：たるんだ綱と三角の小旗（赤・濃い赤・麻の色を順に）。
    原点 = 綱の両端の真ん中（両端は y 0、x ±L/2）。真ん中が sag 下がる。当たり判定なし（頭の上 5 m より高く渡す）"""
    p = Part('bunting')
    pts = sag_pts(L, sag, 24)
    # 揺れ：両端で留まった綱が振り子のように揺れる（両端を結ぶ線からの深さ。小旗の先 sag + 0.42 で 1）
    wfn = hang(0.0, sag + 0.42)
    p.add('rope', sway(tube(pts, 0.02, 5), wfn))
    mats = ['cloth', 'cloth2', 'linen']
    n = int(L / step)
    for k in range(1, n):
        x = -L / 2 + k * step
        t = (x + L / 2) / L
        y = -sag * 4 * t * (1 - t)
        w, h = 0.36, 0.42
        v = np.array([[x - w / 2, y, 0.0], [x + w / 2, y, 0.0], [x, y - h, 0.0]], float)
        tri = Piece(np.concatenate([v + [0, 0, 0.006], v - [0, 0, 0.006]]), [[0, 1, 2], [5, 4, 3]])
        p.add(mats[k % 3], sway(tri, wfn))
    for x in (-L / 2, L / 2):
        p.add('brass', cyl((x, -0.1, 0.0), (x, 0.1, 0.0), 0.05, 6))
    return p


def sag_pts(L, sag, n):
    return [np.array([x, -sag * 4 * ((x + L / 2) / L) * (1 - (x + L / 2) / L), 0.0]) for x in np.linspace(-L / 2, L / 2, n + 1)]


PARTS = {
    'grime_patch': grime_patch,
    'oil_patch': lambda: grime_patch('oil_decal', 'oil_patch'),
    'lower_set': lower_set,
    'upper_set': upper_set,
    'training_set': training_set,
    'home_set': home_set,
    'workshop_set': workshop_set,
    'guild_set': guild_set,
    'mayor_set': mayor_set,
    'opening_set': opening_set,
    'gate_door': gate_door,
    'bunting': bunting,
}
