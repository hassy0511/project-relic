#!/usr/bin/env python3
"""人物の GLB の「ゲームに入れてよいか」の確かめ（Blender なし。Python 3 と numpy で .glb を直接読む）。

  python3 tools/blender/recon/glb_audit.py godot/assets/models/haru_r.glb [more.glb ...] [--json out.json] [--strict]
      （numpy の入った Python で。例：/usr/bin/python3 か .venv-blender/bin/python）

1 体ごとに表（Markdown）を出す。--json は数をすべて書き出す。--strict は「失敗」が 1 つでもあれば終了コード 1。
  a) 数：三角形・頂点・材質・描く面（プリミティブ）・テクスチャの大きさ。40_技術設計.md §5.4 の目安は「注」（失敗にしない）
  b) 骨と皮：骨の数、1 頂点の重みの本数の最大、重みの合計が 1 でない頂点、重みの無い頂点
  c) 基準の姿勢：身長、原点が床か（皮の最も低い点の y）、正面の向き、腰・胸・頭の原点からの横のずれ（x, z）、
     重みの一番大きい骨から 80 cm より遠い頂点（迷子の部品）
  d) 動作ごと：長さ、輪の動作の最初と最後のこまの差、値がすべて 1 の大きさの道、
     60 こま/秒で標本して（位置は直線・回転は slerp）逆バインド行列で皮を変形した、こまごとの最も低い点（部位別）
  e) 立って待つ動作（idle・walk・cower）で両足とも床から 2 cm より上のこま＝浮き。dead の最後のこまは床に寝ていること
床の決まり：足は床の 1.5 cm 下まで、ほかの部位は 1 cm 下まで。部位は頂点の重みが一番大きい骨で決める（銃・刃などの材質と、
骨の子の硬い物体は「持ち物」。光刃 LightBlade はゲームが攻撃の間だけ出すので攻撃の動作でだけ見る）。
Blender 4.5 の glTF 読み込み（評価したメッシュ）と頂点ごとに比べて、差は 3 µm 以内だった（2026-11-05、haru_r・yana・burton・nico ほか）。
考え方の出所：arjun988/blender-skills（MIT）の書き出しの前の確認の一覧に、床の接地と原点のずれを足して自動にしたもの。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys

import numpy as np

FPS = 60
FEET_MIN = -0.015      # 足は床の 1.5 cm 下まで（靴底の丸み・接地の揺れ）
OTHER_MIN = -0.010     # ほかの部位は 1 cm 下まで
FLOAT_MIN = 0.020      # 立って待つ動作で両足とも 2 cm より上なら浮き
DEAD_REST_MAX = 0.030  # dead の最後のこまの最も低い点は 3 cm 以内（床に寝ている）
ORIGIN_TOL = 0.010     # 基準の姿勢の最も低い点が原点（床）から 1 cm 以内
DRIFT_WARN = 0.030     # 腰・胸・頭が原点から横に 3 cm より離れたら注意
FAR_WARN = 0.80       # 重みの一番大きい骨から 80 cm より遠い頂点は迷子の部品かもしれない（スカートの裾・杖の先で約 70 cm）
SEAM_TOL = 0.005       # 輪の動作の最初と最後のこまの頂点の差 5 mm まで
WEIGHT_TOL = 1e-3

LOOPS = ('idle', 'run', 'fall', 'drill', 'walk', 'cower')   # player_view.gd の LOOPING と props_view.gd の NPC_LOOPS
GROUNDED = ('idle', 'walk', 'cower')                        # 立って待つ・歩く（足が床に着いているはずの動作）
PARTS = ('foot.L', 'foot.R', 'legs', 'body', 'arms', 'hands', 'head', 'hair', 'held')
HELD_WORDS = ('gun', 'blade', 'weapon', 'staff', 'cane', 'hammer', 'sword')
TOGGLED = ('LightBlade',)   # ゲームが攻撃の間だけ出す物（player_view.gd）。攻撃の動作でだけ床を見る
ATTACK_CLIPS = ('combo1', 'combo2', 'combo3', 'lunge', 'charge', 'air')
BUDGET = {'main': ('主要キャラ', 6000, 10000, 1024), 'town': ('町の住人', 3000, 5000, 512)}
MAIN_CHARS = ('haru', 'yana')   # W1 の主要キャラ。ほかの人物は町の住人として目安を見る

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}
NORM = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


# ---------------------------------------------------------------- GLB を読む

class Glb:
    def __init__(self, path: str):
        b = open(path, 'rb').read()
        magic, _ver, ln = struct.unpack_from('<4sII', b, 0)
        if magic != b'glTF':
            raise ValueError('%s: not a GLB' % path)
        off, self.js, self.bin = 12, None, b''
        while off < ln:
            cl, ct = struct.unpack_from('<II', b, off)
            data = b[off + 8: off + 8 + cl]
            if ct == 0x4E4F534A:
                self.js = json.loads(data)
            elif ct == 0x004E4942:
                self.bin = data
            off += 8 + cl
        self.path = path
        self.nodes = self.js['nodes']
        self.parent = {}
        for i, n in enumerate(self.nodes):
            for c in n.get('children', []):
                self.parent[c] = i
        sc = self.js['scenes'][self.js.get('scene', 0)]
        self.order = []                      # 親が先に来る順
        stack = list(reversed(sc['nodes']))
        while stack:
            i = stack.pop()
            self.order.append(i)
            stack.extend(reversed(self.nodes[i].get('children', [])))

    def view_bytes(self, bv_index: int) -> bytes:
        bv = self.js['bufferViews'][bv_index]
        o = bv.get('byteOffset', 0)
        return self.bin[o: o + bv['byteLength']]

    def acc(self, i: int) -> np.ndarray:
        """アクセサーを (数, 成分) の float64 で（正規化した整数は 0〜1 に、JOINTS などの整数はそのまま）"""
        a = self.js['accessors'][i]
        n, ct, count = NCOMP[a['type']], a['componentType'], a['count']
        dt = np.dtype(COMP[ct]).newbyteorder('<')
        out = np.zeros((count, n), dtype=np.float64)
        if 'bufferView' in a:
            bv = self.js['bufferViews'][a['bufferView']]
            item = dt.itemsize * n
            stride = bv.get('byteStride') or item
            start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
            raw = np.frombuffer(self.bin, dtype=np.uint8, count=stride * (count - 1) + item, offset=start)
            if stride != item:
                raw = np.lib.stride_tricks.as_strided(raw, shape=(count, item), strides=(stride, 1)).copy()
            out = raw.view(dt).reshape(count, n).astype(np.float64)
        sp = a.get('sparse')
        if sp:
            ii = sp['indices']
            idt = np.dtype(COMP[ii['componentType']]).newbyteorder('<')
            ib = self.js['bufferViews'][ii['bufferView']]
            idx = np.frombuffer(self.bin, dtype=idt, count=sp['count'], offset=ib.get('byteOffset', 0) + ii.get('byteOffset', 0))
            vv = sp['values']
            vb = self.js['bufferViews'][vv['bufferView']]
            vals = np.frombuffer(self.bin, dtype=dt, count=sp['count'] * n, offset=vb.get('byteOffset', 0) + vv.get('byteOffset', 0))
            out = out.copy()
            out[idx.astype(np.int64)] = vals.reshape(-1, n)
        if a.get('normalized') and ct in NORM:
            out = np.maximum(out / NORM[ct], -1.0)
        return out


def quat_to_mat(q: np.ndarray) -> np.ndarray:
    """(…, 4) の x, y, z, w → (…, 3, 3)"""
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    x, y, z, w = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    m = np.empty(q.shape[:-1] + (3, 3))
    m[..., 0, 0] = 1 - 2 * (y * y + z * z)
    m[..., 0, 1] = 2 * (x * y - z * w)
    m[..., 0, 2] = 2 * (x * z + y * w)
    m[..., 1, 0] = 2 * (x * y + z * w)
    m[..., 1, 1] = 1 - 2 * (x * x + z * z)
    m[..., 1, 2] = 2 * (y * z - x * w)
    m[..., 2, 0] = 2 * (x * z - y * w)
    m[..., 2, 1] = 2 * (y * z + x * w)
    m[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return m


def trs_to_mat(t: np.ndarray, r: np.ndarray, s: np.ndarray) -> np.ndarray:
    """(F, 3), (F, 4), (F, 3) → (F, 4, 4)"""
    f = t.shape[0]
    m = np.zeros((f, 4, 4))
    m[:, :3, :3] = quat_to_mat(r) * s[:, None, :]
    m[:, :3, 3] = t
    m[:, 3, 3] = 1.0
    return m


def node_trs(n: dict):
    if 'matrix' in n:
        m = np.array(n['matrix'], dtype=np.float64).reshape(4, 4).T
        t = m[:3, 3].copy()
        s = np.linalg.norm(m[:3, :3], axis=0)
        rm = m[:3, :3] / s
        # 行列 → 四元数（大きさが正、ねじれなしと仮定）
        tr = np.trace(rm)
        if tr > 0:
            w = math.sqrt(1 + tr) / 2
            q = [(rm[2, 1] - rm[1, 2]) / (4 * w), (rm[0, 2] - rm[2, 0]) / (4 * w), (rm[1, 0] - rm[0, 1]) / (4 * w), w]
        else:
            i = int(np.argmax(np.diag(rm)))
            j, k = (i + 1) % 3, (i + 2) % 3
            r = math.sqrt(max(1e-12, 1 + rm[i, i] - rm[j, j] - rm[k, k]))
            q = [0.0, 0.0, 0.0, (rm[k, j] - rm[j, k]) / (2 * r)]
            q[i] = r / 2
            q[j] = (rm[j, i] + rm[i, j]) / (2 * r)
            q[k] = (rm[k, i] + rm[i, k]) / (2 * r)
        return t, np.array(q), s
    return (np.array(n.get('translation', [0, 0, 0]), dtype=np.float64),
            np.array(n.get('rotation', [0, 0, 0, 1]), dtype=np.float64),
            np.array(n.get('scale', [1, 1, 1]), dtype=np.float64))


def slerp(q0: np.ndarray, q1: np.ndarray, u: np.ndarray) -> np.ndarray:
    d = np.sum(q0 * q1, axis=-1)
    q1 = np.where(d[:, None] < 0, -q1, q1)
    d = np.abs(d)
    near = d > 0.9995
    th = np.arccos(np.clip(d, -1, 1))
    sn = np.where(near, 1.0, np.sin(th))
    a = np.where(near, 1 - u, np.sin((1 - u) * th) / sn)
    b = np.where(near, u, np.sin(u * th) / sn)
    q = a[:, None] * q0 + b[:, None] * q1
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def sample_channel(times: np.ndarray, vals: np.ndarray, interp: str, path: str, t: np.ndarray) -> np.ndarray:
    """glTF の標本器を時刻 t (F,) で読む。範囲の外は端の値"""
    k = len(times)
    if interp == 'CUBICSPLINE':
        a_in, v, b_out = vals[0::3], vals[1::3], vals[2::3]
    else:
        v = vals
    if k == 1:
        return np.repeat(v[:1], len(t), axis=0)
    tc = np.clip(t, times[0], times[-1])
    i = np.clip(np.searchsorted(times, tc, side='right') - 1, 0, k - 2)
    t0, t1 = times[i], times[i + 1]
    dt = np.where(t1 > t0, t1 - t0, 1.0)
    u = np.clip((tc - t0) / dt, 0.0, 1.0)
    if interp == 'STEP':
        return np.where((tc >= t1)[:, None], v[i + 1], v[i])
    if interp == 'CUBICSPLINE':
        u2, u3 = u * u, u * u * u
        h00, h10, h01, h11 = 2 * u3 - 3 * u2 + 1, u3 - 2 * u2 + u, -2 * u3 + 3 * u2, u3 - u2
        out = (h00[:, None] * v[i] + (h10 * dt)[:, None] * b_out[i] + h01[:, None] * v[i + 1] + (h11 * dt)[:, None] * a_in[i + 1])
        if path == 'rotation':
            out = out / np.linalg.norm(out, axis=-1, keepdims=True)
        return out
    if path == 'rotation':
        return slerp(v[i], v[i + 1], u)
    return v[i] * (1 - u)[:, None] + v[i + 1] * u[:, None]


# ---------------------------------------------------------------- 姿勢と皮

class Model:
    def __init__(self, path: str):
        self.g = g = Glb(path)
        self.name = os.path.splitext(os.path.basename(path))[0]
        self.rest_trs = [node_trs(n) for n in g.nodes]
        mats = g.js.get('materials', [])
        self.mat_names = [m.get('name', '') for m in mats]
        self.skins = g.js.get('skins', [])
        self.ibm = [g.acc(s['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1) if 'inverseBindMatrices' in s
                    else np.tile(np.eye(4), (len(s['joints']), 1, 1)) for s in self.skins]
        self.joint_names = {j: g.nodes[j].get('name', '') for s in self.skins for j in s['joints']}
        self.meshes = []       # 皮のメッシュ（node, skin, 位置, 重み (V, J), 部位, 材質）と、硬い物体（skin=None）
        for ni in g.order:
            n = g.nodes[ni]
            if 'mesh' not in n:
                continue
            for pr in g.js['meshes'][n['mesh']]['primitives']:
                if pr.get('mode', 4) != 4:
                    continue
                pos = g.acc(pr['attributes']['POSITION'])
                mat = self.mat_names[pr['material']] if 'material' in pr else ''
                held_mat = any(w in mat.lower() for w in HELD_WORDS)
                if 'skin' in n:
                    sk = n['skin']
                    nj = len(self.skins[sk]['joints'])
                    W = np.zeros((len(pos), nj))
                    nset = 0
                    while 'JOINTS_%d' % nset in pr['attributes']:
                        jj = g.acc(pr['attributes']['JOINTS_%d' % nset]).astype(np.int64)
                        ww = g.acc(pr['attributes']['WEIGHTS_%d' % nset])
                        for c in range(4):
                            np.add.at(W, (np.arange(len(pos)), jj[:, c]), ww[:, c])
                        nset += 1
                    infl = np.count_nonzero(W > 0, axis=1)
                    part = np.full(len(pos), PARTS.index('body'))
                    if held_mat:
                        part[:] = PARTS.index('held')
                    else:
                        dom = np.argmax(W, axis=1)
                        jnames = [g.nodes[j].get('name', '') for j in self.skins[sk]['joints']]
                        pj = np.array([PARTS.index(part_of_bone(x)) for x in jnames])
                        part = pj[dom]
                    self.meshes.append(dict(node=ni, skin=sk, pos=pos, W=W, part=part, mat=mat, infl=infl, prim=pr,
                                            name=n.get('name', '')))
                else:
                    self.meshes.append(dict(node=ni, skin=None, pos=pos, W=None, part=np.full(len(pos), PARTS.index('held')),
                                            mat=mat, infl=None, prim=pr, name=n.get('name', ''),
                                            toggled=n.get('name', '') in TOGGLED))
        self.anims = []
        for a in g.js.get('animations', []):
            chans = []
            length = 0.0
            for ch in a['channels']:
                sm = a['samplers'][ch['sampler']]
                tgt = ch['target']
                if 'node' not in tgt or tgt['path'] not in ('translation', 'rotation', 'scale'):
                    continue
                times = g.acc(sm['input'])[:, 0]
                vals = g.acc(sm['output'])
                chans.append((tgt['node'], tgt['path'], times, vals, sm.get('interpolation', 'LINEAR')))
                length = max(length, float(times[-1]))
            self.anims.append(dict(name=a.get('name', 'anim%d' % len(self.anims)), chans=chans, length=length))

    # 姿勢：各ノードの世界の行列 (F, 4, 4)
    def world(self, anim: dict | None, t: np.ndarray) -> dict:
        f = len(t)
        trs = {i: [np.tile(x, (f, 1)) for x in self.rest_trs[i]] for i in range(len(self.g.nodes))}
        if anim:
            k = {'translation': 0, 'rotation': 1, 'scale': 2}
            for node, path, times, vals, interp in anim['chans']:
                trs[node][k[path]] = sample_channel(times, vals, interp, path, t)
        wm = {}
        for i in self.g.order:
            loc = trs_to_mat(*trs[i])
            p = self.g.parent.get(i)
            wm[i] = loc if p is None else np.matmul(wm[p], loc)
        return wm

    def joint_mats(self, wm: dict, sk: int) -> np.ndarray:
        """(F, J, 4, 4) = 骨の世界の行列 × 逆バインド行列（glTF の決まり：皮のメッシュのノード自身の変換は使わない）"""
        js = self.skins[sk]['joints']
        return np.stack([np.matmul(wm[j], self.ibm[sk][k]) for k, j in enumerate(js)], axis=1)

    def positions(self, wm: dict) -> list:
        """メッシュごとの変形した位置 (F, V, 3)"""
        out = []
        for m in self.meshes:
            vh = np.concatenate([m['pos'], np.ones((len(m['pos']), 1))], axis=1)
            if m['skin'] is None:
                out.append(np.einsum('frc,vc->fvr', wm[m['node']][:, :3, :], vh))
                continue
            M = self.joint_mats(wm, m['skin'])[:, :, :3, :]                # (F, J, 3, 4)
            B = np.einsum('vj,fjrc->fvrc', m['W'], M)                       # 頂点ごとに混ぜた行列
            out.append(np.einsum('fvrc,vc->fvr', B, vh))
        return out

    def heights(self, wm: dict) -> list:
        """メッシュごとの変形した y だけ (F, V)（重み × 骨の行列の 2 行目。全部の位置より軽い）"""
        out = []
        for m in self.meshes:
            vh = np.concatenate([m['pos'], np.ones((len(m['pos']), 1))], axis=1)
            if m['skin'] is None:
                out.append(np.einsum('fc,vc->fv', wm[m['node']][:, 1, :], vh))
                continue
            R1 = self.joint_mats(wm, m['skin'])[:, :, 1, :]                 # (F, J, 4)
            ys = []
            for a in range(0, R1.shape[0], 32):                            # 32 こまずつ（メモリを抑える）
                P = np.einsum('vj,fjc->fvc', m['W'], R1[a:a + 32])
                ys.append(np.einsum('fvc,vc->fv', P, vh))
            out.append(np.concatenate(ys, axis=0))
        return out


def part_of_bone(name: str) -> str:
    n = name.lower()
    for words, part in ((('hair',), 'hair'), (('foot', 'toe'), 'foot'), (('hand', 'finger', 'thumb'), 'hands'),
                        (('thigh', 'shin', 'leg', 'knee', 'calf'), 'legs'), (('arm', 'shoulder', 'elbow'), 'arms'),
                        (('head', 'neck', 'jaw', 'eye'), 'head')):
        if any(w in n for w in words):
            if part == 'foot':
                return 'foot.R' if n.endswith(('.r', '_r', 'right')) else 'foot.L'
            return part
    return 'body'


def frame_times(length: float) -> np.ndarray:
    n = max(1, int(round(length * FPS)))
    return np.minimum(np.arange(n + 1) / FPS, length)


def find_node(model: Model, *names: str):
    for want in names:
        for j, n in model.joint_names.items():
            if n == want:
                return j
    return None


# ---------------------------------------------------------------- 数

def image_size(g: Glb, im: dict):
    if 'bufferView' not in im:
        return None
    b = g.view_bytes(im['bufferView'])
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', b[16:24])
    if b[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            mk = b[i + 1]
            if mk in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack('>HH', b[i + 5: i + 9])
                return (w, h)
            i += 2 + struct.unpack('>H', b[i + 2: i + 4])[0]
    return None


def counts(model: Model) -> dict:
    g = model.g
    tris = verts = surfaces = 0
    for ni in g.order:
        n = g.nodes[ni]
        if 'mesh' not in n:
            continue
        for pr in g.js['meshes'][n['mesh']]['primitives']:
            surfaces += 1
            verts += g.js['accessors'][pr['attributes']['POSITION']]['count']
            if pr.get('mode', 4) == 4:
                tris += (g.js['accessors'][pr['indices']]['count'] if 'indices' in pr
                         else g.js['accessors'][pr['attributes']['POSITION']]['count']) // 3
    tex = [image_size(g, im) for im in g.js.get('images', [])]
    cls = 'main' if model.name.startswith(MAIN_CHARS) else 'town'
    label, lo, hi, texmax = BUDGET[cls]
    notes = []
    if tris > hi:
        notes.append('三角形 %s は %s の目安 %s〜%s の %.1f 倍' % (f'{tris:,}', label, f'{lo:,}', f'{hi:,}', tris / hi))
    big = [t for t in tex if t and max(t) > texmax]
    if big:
        notes.append('テクスチャ %s は %s の目安 %d² より大きい' % (', '.join('%dx%d' % t for t in big), label, texmax))
    return dict(triangles=tris, vertices=verts, materials=len(model.mat_names), surfaces=surfaces,
                textures=['%dx%d' % t if t else '?' for t in tex], budget_class=label,
                budget='%s〜%s 三角形・%d²' % (f'{lo:,}', f'{hi:,}', texmax), budget_notes=notes)


def skin_report(model: Model) -> dict:
    infl, bad_sum, zero = 0, 0, 0
    for m in model.meshes:
        if m['skin'] is None:
            continue
        s = m['W'].sum(axis=1)
        infl = max(infl, int(m['infl'].max()))
        zero += int(np.count_nonzero(s <= 0))
        bad_sum += int(np.count_nonzero((s > 0) & (np.abs(s - 1) > WEIGHT_TOL)))
    bones = sorted({len(s['joints']) for s in model.skins})
    return dict(bones=bones[0] if len(bones) == 1 else bones, max_influences=infl, weight_sum_not_1=bad_sum, unweighted=zero)


# ---------------------------------------------------------------- 姿勢の確かめ

def part_lows(model: Model, hs: list, clip: str = '') -> np.ndarray:
    """(部位, F) の最も低い y。重みの無い頂点と、攻撃の外の出し入れする物（光刃）は除く（その部位が無ければ +inf）"""
    f = hs[0].shape[0]
    low = np.full((len(PARTS), f), np.inf)
    for m, h in zip(model.meshes, hs):
        if m.get('toggled') and clip not in ATTACK_CLIPS:
            continue
        ok = np.ones(len(m['pos']), bool) if m['W'] is None else m['W'].sum(axis=1) > 0
        for p in range(len(PARTS)):
            sel = ok & (m['part'] == p)
            if sel.any():
                low[p] = np.minimum(low[p], h[:, sel].min(axis=1))
    return low


def rest_report(model: Model) -> dict:
    wm = model.world(None, np.zeros(1))
    ps = model.positions(wm)
    body = [p[0][(m['part'] != PARTS.index('held')) & (np.ones(len(m['pos']), bool) if m['W'] is None else m['W'].sum(1) > 0)]
            for m, p in zip(model.meshes, ps) if m['skin'] is not None]
    allp = np.concatenate(body, axis=0) if body else np.zeros((1, 3))
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    # 正面：足の頂点の重心が足首の骨よりどちらに出ているか（つま先の向き）
    fwd = None
    fl, fr = PARTS.index('foot.L'), PARTS.index('foot.R')
    feet = [p[0][(m['part'] == fl) | (m['part'] == fr)] for m, p in zip(model.meshes, ps) if m['skin'] is not None]
    feet = np.concatenate(feet, axis=0) if feet else np.zeros((0, 3))
    fj = [j for j, n in model.joint_names.items() if part_of_bone(n).startswith('foot')]
    if len(feet) and fj:
        ank = np.mean([wm[j][0, :3, 3] for j in fj], axis=0)
        d = feet.mean(axis=0) - ank
        ax = 0 if abs(d[0]) > abs(d[2]) else 2
        fwd = ('+' if d[ax] > 0 else '-') + 'XZ'[ax // 2]
    drift = {}
    for key, names in (('hips', ('hips', 'pelvis')), ('chest', ('chest', 'spine.002', 'spine')), ('head', ('head',))):
        j = find_node(model, *names)
        if j is not None:
            x, _y, z = wm[j][0, :3, 3]
            drift[key] = (float(x), float(z))
    # 骨から遠い頂点（重みの一番大きい骨の原点からの距離）
    far = (0.0, '', 0, [0.0, 0.0])
    for m, p in zip(model.meshes, ps):
        if m['skin'] is None:
            continue
        js = model.skins[m['skin']]['joints']
        dom = np.argmax(m['W'], axis=1)
        d = np.linalg.norm(p[0] - np.array([wm[j][0, :3, 3] for j in js])[dom], axis=1)
        i = int(np.argmax(d))
        if d[i] > far[0]:
            sel = d > FAR_WARN
            yr = [float(p[0][sel, 1].min()), float(p[0][sel, 1].max())] if sel.any() else [0.0, 0.0]
            far = (float(d[i]), model.joint_names[js[dom[i]]], int(np.count_nonzero(sel)), yr)
    low_parts = part_lows(model, model.heights(wm))[:, 0]
    return dict(height=float(hi[1] - lo[1]), lowest_y=float(lo[1]), forward=fwd, drift=drift, far=far,
                bounds=[[float(v) for v in lo], [float(v) for v in hi]],
                rest_lows={PARTS[p]: float(v) for p, v in enumerate(low_parts) if np.isfinite(v)})


def clip_report(model: Model, anim: dict) -> dict:
    t = frame_times(anim['length'])
    wm = model.world(anim, t)
    low = part_lows(model, model.heights(wm), anim['name'])   # (部位, F)
    r = dict(name=anim['name'], length=anim['length'], frames=len(t), findings=[])
    r['part_low'] = {PARTS[p]: (float(low[p].min()), int(low[p].argmin())) for p in range(len(PARTS)) if np.isfinite(low[p]).any()}
    fails, notes = [], []

    def group(parts, label, limit):
        """部位の組の、こまごとの最も低い点 (F,) と最も深いこま。limit より下なら失敗"""
        idx = [PARTS.index(x) for x in parts if np.isfinite(low[PARTS.index(x)]).any()]
        if not idx:
            return None
        y = low[idx].min(axis=0)
        f = int(np.argmin(y))
        part = PARTS[idx[int(np.argmin(low[idx][:, f]))]]
        r[label] = (float(y[f]), f, part)
        if y[f] < limit:
            fails.append('%s が床の下 %.1f cm（こま %d）' % (part, -y[f] * 100, f))
            r['findings'].append(dict(clip=anim['name'], part=part, depth_cm=round(float(-y[f]) * 100, 1), frame=f))
        return y

    feet = group(('foot.L', 'foot.R'), 'feet_low', FEET_MIN)
    body = group(('legs', 'body', 'arms', 'hands', 'head', 'hair'), 'body_low', OTHER_MIN)
    held = group(('held',), 'held_low', OTHER_MIN)
    # 大きさの道
    sc = [v for _n, path, _t, v, _i in anim['chans'] if path == 'scale']
    r['scale_tracks'] = len(sc)
    r['scale_tracks_all_1'] = sum(1 for v in sc if np.allclose(v, 1.0, atol=1e-5))
    # 輪の継ぎ目：最初と最後のこまの頂点の差
    if anim['name'] in LOOPS and len(t) > 1:
        ps = model.positions(model.world(anim, np.array([t[0], t[-1]])))
        seam = max(float(np.linalg.norm(p[0] - p[1], axis=1).max()) for p in ps)
        r['loop_seam'] = seam
        if seam > SEAM_TOL:
            fails.append('輪の継ぎ目 %.1f cm' % (seam * 100))
    # 浮き：立って待つ動作で、両足とも 2 cm より上のこま
    if anim['name'] in GROUNDED and feet is not None:
        fh = int(np.argmax(feet))
        r['feet_high'] = (float(feet[fh]), fh)
        n_float = int(np.count_nonzero(feet > FLOAT_MIN))
        r['floating_frames'] = n_float
        if n_float:
            fails.append('両足とも床から %.1f cm 上（浮き、こま %d、%d/%d こま）' % (feet[fh] * 100, fh, n_float, len(t)))
            r['findings'].append(dict(clip=anim['name'], part='feet (floating)', depth_cm=round(float(-feet[fh]) * 100, 1), frame=fh))
    # dead の最後のこま：床に寝ている（最も低い点が 0〜3 cm）
    if anim['name'] == 'dead':
        last = float(min(y[-1] for y in (feet, body) if y is not None))
        r['dead_last_low'] = last
        if last > DEAD_REST_MAX:
            fails.append('最後のこまで体が床から %.1f cm 上（寝ていない）' % (last * 100))
            r['findings'].append(dict(clip='dead', part='body (not resting)', depth_cm=round(-last * 100, 1), frame=len(t) - 1))
    r['fails'], r['notes'] = fails, notes
    return r


def audit(path: str) -> dict:
    model = Model(path)
    rep = dict(model=model.name, path=path, counts=counts(model), skin=skin_report(model), rest=rest_report(model),
               clips=[clip_report(model, a) for a in model.anims])
    fails, warns = [], []
    sk = rep['skin']
    if sk['weight_sum_not_1']:
        fails.append('重みの合計が 1 でない頂点 %d' % sk['weight_sum_not_1'])
    if sk['unweighted']:
        fails.append('重みの無い頂点 %d' % sk['unweighted'])
    if sk['max_influences'] > 4:
        warns.append('1 頂点の重みが %d 本（4 本を超える）' % sk['max_influences'])
    rs = rep['rest']
    if abs(rs['lowest_y']) > ORIGIN_TOL:
        fails.append('基準の姿勢の最も低い点が床から %+.1f cm（原点が足元にない）' % (rs['lowest_y'] * 100))
    for k, (x, z) in rs['drift'].items():
        if math.hypot(x, z) > DRIFT_WARN:
            warns.append('%s が原点から横に %.1f cm（x %+.1f, z %+.1f）' % (k, math.hypot(x, z) * 100, x * 100, z * 100))
    if rs['far'][0] > FAR_WARN:
        d, b, n, yr = rs['far']
        warns.append('骨から遠い頂点 %d（%s から最大 %.2f m、高さ %.2f〜%.2f m。迷子の部品か。身長の値もこれを含む）' % (n, b, d, yr[0], yr[1]))
    if rs['forward'] not in (None, '+Z'):
        warns.append('正面が %s（ゲームは +Z）' % rs['forward'])
    for c in rep['clips']:
        fails += ['%s: %s' % (c['name'], f) for f in c['fails']]
        warns += ['%s: %s' % (c['name'], f) for f in c['notes']]
    ones = [c['scale_tracks_all_1'] for c in rep['clips'] if c['scale_tracks_all_1']]
    if ones:
        warns.append('値がすべて 1 の大きさの道：%d 動作で計 %d 本（Godot は取り込みで消すが、書き出しの設定で外せる）' % (len(ones), sum(ones)))
    rep['findings'] = [dict(model=rep['model'], **f) for c in rep['clips'] for f in c['findings']]
    rep['fails'], rep['warns'] = fails, warns
    return rep


# ---------------------------------------------------------------- 表

def cm(v: float) -> str:
    return '%+.1f' % (v * 100)


def render(rep: dict) -> str:
    c, sk, rs = rep['counts'], rep['skin'], rep['rest']
    out = ['## %s' % rep['model'], '',
           '- 数：三角形 %s・頂点 %s・材質 %d・描く面 %d・テクスチャ %s' % (f"{c['triangles']:,}", f"{c['vertices']:,}", c['materials'],
                                                         c['surfaces'], ', '.join(c['textures']) or 'なし'),
           '- 目安（注）：%s として見た（%s）。%s' % (c['budget_class'], c['budget'], '；'.join(c['budget_notes']) or '目安の中'),
           '- 骨と皮：骨 %s・1 頂点の重みの最大 %d 本・合計が 1 でない頂点 %d・重みの無い頂点 %d'
           % (sk['bones'], sk['max_influences'], sk['weight_sum_not_1'], sk['unweighted']),
           '- 基準の姿勢：身長 %.3f m・最も低い点 %s cm・正面 %s・原点からの横のずれ（x, z cm）%s'
           % (rs['height'], cm(rs['lowest_y']), rs['forward'],
              '・'.join('%s (%s, %s)' % (k, cm(x), cm(z)) for k, (x, z) in rs['drift'].items())),
           '']
    if rep['clips']:
        out += ['| 動作 | 長さ s | こま | 足の最も低い点 cm（こま） | 体の最も低い点 cm（部位・こま） | 持ち物 cm（こま） | 輪の継ぎ目 cm | 立つ動作の両足の最も高い点 cm | 判定 |',
                '|---|---|---|---|---|---|---|---|---|']

        def cell(v, with_part=False):
            if v is None:
                return '—'
            return '%s（%s%d）' % (cm(v[0]), (v[2] + '・') if with_part else '', v[1])
        for cl in rep['clips']:
            seam = '%.2f' % (cl['loop_seam'] * 100) if 'loop_seam' in cl else '—'
            fh = ('%s（%d）' % (cm(cl['feet_high'][0]), cl['feet_high'][1])) if 'feet_high' in cl else '—'
            verdict = '**失敗**：' + '；'.join(cl['fails']) if cl['fails'] else 'OK'
            out.append('| %s | %.3f | %d | %s | %s | %s | %s | %s | %s |'
                       % (cl['name'], cl['length'], cl['frames'], cell(cl.get('feet_low')), cell(cl.get('body_low'), True),
                          cell(cl.get('held_low')), seam, fh, verdict))
        out.append('')
    out.append('- 結果：%s' % ('失敗 %d 件' % len(rep['fails']) if rep['fails'] else '失敗なし'))
    out += ['  - 失敗：' + f for f in rep['fails']]
    out += ['  - 注意：' + w for w in rep['warns']]
    out.append('')
    return '\n'.join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='人物の GLB の「ゲームに入れてよいか」の確かめ')
    ap.add_argument('glb', nargs='+')
    ap.add_argument('--json', help='数をすべて JSON で書き出す')
    ap.add_argument('--strict', action='store_true', help='失敗が 1 つでもあれば終了コード 1')
    a = ap.parse_args(argv)
    reps = []
    print('# GLB の確かめ（glb_audit.py）\n')
    print('床の決まり：足は %.1f cm 下まで・ほかの部位は %.1f cm 下まで。立つ動作（%s）で両足とも %.0f cm より上は浮き。%d こま/秒で標本。\n'
          % (-FEET_MIN * 100, -OTHER_MIN * 100, '・'.join(GROUNDED), FLOAT_MIN * 100, FPS))
    for p in a.glb:
        rep = audit(p)
        reps.append(rep)
        print(render(rep))
        sys.stdout.flush()
    print('## まとめ\n')
    print('| モデル | 三角形 | 失敗 | 注意 |')
    print('|---|---|---|---|')
    for r in reps:
        print('| %s | %s | %d | %d |' % (r['model'], f"{r['counts']['triangles']:,}", len(r['fails']), len(r['warns'])))
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, 'w') as f:
            json.dump(reps, f, ensure_ascii=False, indent=1)
    return 1 if a.strict and any(r['fails'] for r in reps) else 0


if __name__ == '__main__':
    sys.exit(main())
