"""haru_f：動作を GLB に焼き込む（numpy だけ）。

  python3 -m tools.blender.trial_f.anim_bake --in build/f/haru_f_mesh.glb --out build/f/haru_f.glb [--only combo1,combo2] [--report]

入力の GLB（build.py の書き出し：動作なし・皮つき）から骨の基準の姿勢を読み、anim.py の 14 動作を 60 こま/秒で標本にして
差し込む。回転は骨ごとのクォータニオン、腰は移動も、root は上下だけ（床合わせ）。大きさの道は書かない。
皮の変形を自分で計算して、床の下へ出るこまは root を上げる（dead は一番低い体の頂点を床に合わせる）。
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys

import numpy as np

from . import anim as A
from .anim import V, nrm, rx, ry, rz, euler, frame

SPINE = [('spine', 'sp'), ('chest', 'ch'), ('neck', 'nk'), ('head', 'hd')]
STATIC = ['hair.front', 'hair.top', 'hair.back.L', 'hair.back.R', 'hair.nape', 'hair.side.L', 'hair.side.R', 'pouch.L', 'pouch.R']
ANIMATED = ['hips', 'spine', 'chest', 'neck', 'head', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L', 'shoulder.R', 'upper_arm.R',
            'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R']
# 脚の向き：基準の姿勢（絵の A の姿勢）は足を開いてつま先・膝が外を向く。動作ではそれを戻す
MESH_TOE = 13.0     # 靴のメッシュが基準の姿勢で外を向く角度
REST_KNEE = 9.0     # 膝当て・すね当てが基準の姿勢で外を向く角度
TOE_OUT = 5.0       # 足の向きの既定（姿勢の yaw 0 で、つま先がこれだけ外を向く）
KNEE_OUT = 1.0      # 膝の向きの既定（外へ）
KNEE_FOLLOW = 0.7   # 膝が足の向きについていく割合
NARROW = 0.030      # 足の置き場所を内へ寄せる量（m。基準の姿勢の足の開きを戻す）
FK_ADDUCT = 5.0     # 回転で書く脚（空中・倒れ）：ももを内へ戻す角度
BALL, HEEL = 0.185, 0.085
TOE_TIP = 0.024     # 母指球の回転の軸からつま先の先まで。かかとを上げたとき、つま先の先が床に沈まないよう足を上げる


def load_glb(path):
    b = open(path, 'rb').read()
    ln = struct.unpack_from('<I', b, 8)[0]
    off, js, binc = 12, None, b''
    while off < ln:
        cl, ct = struct.unpack_from('<II', b, off)
        d = b[off + 8: off + 8 + cl]
        if ct == 0x4E4F534A:
            js = json.loads(d)
        elif ct == 0x004E4942:
            binc = d
        off += 8 + cl
    return js, binc


def save_glb(path, js, binc):
    j = json.dumps(js, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    j += b' ' * ((4 - len(j) % 4) % 4)
    binc = bytes(binc) + b'\0' * ((4 - len(binc) % 4) % 4)
    total = 12 + 8 + len(j) + 8 + len(binc)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(j), 0x4E4F534A))
        f.write(j)
        f.write(struct.pack('<II', len(binc), 0x004E4942))
        f.write(binc)


def accessor(js, binc, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8, 5120: np.int8, 5122: np.int16}[a['componentType']]
    base = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0)
    isz = np.dtype(dt).itemsize * n
    if stride and stride != isz:
        raw = np.frombuffer(binc, dtype=np.uint8, count=stride * (a['count'] - 1) + isz, offset=base)
        idx = (np.arange(a['count'])[:, None] * stride + np.arange(isz)[None, :]).ravel()
        arr = np.frombuffer(raw[idx].tobytes(), dtype=dt)
    else:
        arr = np.frombuffer(binc, dtype=dt, count=a['count'] * n, offset=base)
    arr = arr.reshape(a['count'], n).astype(np.float64 if dt == np.float32 else np.int64)
    if a.get('normalized') and dt != np.float32:
        arr = arr / float(np.iinfo(dt).max)
    return arr


def q_to_m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def m_to_q(m):
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = ((m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s)
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = (0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s)
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = ((m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s)
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = ((m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s)
    q = np.array(q)
    return q / np.linalg.norm(q)


class Rig:
    def __init__(self, js, binc):
        self.js, self.binc = js, binc
        nodes = js['nodes']
        self.idx = {n.get('name'): i for i, n in enumerate(nodes)}
        self.par = {}
        for i, n in enumerate(nodes):
            for c in n.get('children', []):
                self.par[c] = i
        self.lt = [np.array(n.get('translation', [0, 0, 0]), dtype=float) for n in nodes]
        self.lr = [q_to_m(n.get('rotation', [0, 0, 0, 1])) for n in nodes]
        self.Gr, self.Pr = {}, {}

        def glob(i):
            if i in self.Gr:
                return self.Gr[i], self.Pr[i]
            if i in self.par:
                g, p = glob(self.par[i])
                self.Gr[i], self.Pr[i] = g @ self.lr[i], p + g @ self.lt[i]
            else:
                self.Gr[i], self.Pr[i] = self.lr[i], self.lt[i]
            return self.Gr[i], self.Pr[i]
        for i in range(len(nodes)):
            glob(i)
        skin = js['skins'][0]
        self.joints = skin['joints']
        self.jname = [nodes[j]['name'] for j in self.joints]
        ibm = accessor(js, binc, skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        self.ibm = ibm
        # メッシュ
        self.meshes = []
        for ni, n in enumerate(nodes):
            if 'mesh' not in n:
                continue
            for pr in js['meshes'][n['mesh']]['primitives']:
                pos = accessor(js, binc, pr['attributes']['POSITION'])
                mat = js['materials'][pr['material']]['name'] if 'material' in pr else ''
                held = any(w in (mat + ' ' + n.get('name', '')).lower() for w in ('gun', 'blade'))
                if 'skin' in n:
                    J = accessor(js, binc, pr['attributes']['JOINTS_0']).astype(int)
                    W = accessor(js, binc, pr['attributes']['WEIGHTS_0'])
                    self.meshes.append(dict(name=n['name'], pos=pos, J=J, W=W, held=held, node=None))
                else:
                    self.meshes.append(dict(name=n['name'], pos=pos, J=None, W=None, held=True, node=ni))
        g = lambda n: self.Gr[self.idx[n]]
        p = lambda n: self.Pr[self.idx[n]]
        self.g, self.p = g, p
        self.arm_rest = {}
        for side, sfx in ((1, '.L'), (-1, '.R')):
            u1 = nrm(p('forearm' + sfx) - p('upper_arm' + sfx))
            u2 = nrm(p('hand' + sfx) - p('forearm' + sfx))
            self.arm_rest[sfx] = (frame(u1, V(0, 0, 1)), frame(u2, V(side, 0, 0)))
        self.leg_rest = {}
        for side, sfx in ((1, '.L'), (-1, '.R')):
            kfwd = ry(side * REST_KNEE) @ V(0, 0, 1)        # 基準の姿勢での膝の正面
            fwd = ry(side * MESH_TOE) @ V(0, 0, 1)          # 基準の姿勢での靴の正面（かかと・爪先の回る軸に使う）
            u1 = nrm(p('shin' + sfx) - p('thigh' + sfx))
            u2 = nrm(p('foot' + sfx) - p('shin' + sfx))
            self.leg_rest[sfx] = (frame(u1, kfwd), frame(u2, kfwd), fwd,
                                  float(np.linalg.norm(p('shin' + sfx) - p('thigh' + sfx))), float(np.linalg.norm(p('foot' + sfx) - p('shin' + sfx))))

    def tl(self, name):
        return self.lt[self.idx[name]]

    stretch = {}

    def solve(self, pose, clip, lift=0.0):
        """姿勢 → 骨ごとの M（基準からの回転、モデルの軸）と位置 P"""
        M, Pp = {}, {}
        G = lambda n: M[n] @ self.g(n)
        M['root'] = np.eye(3)
        Pp['root'] = V(0, lift, 0)
        M['hips'] = euler(pose['hr'])
        Pp['hips'] = self.p('hips') + V(*pose['hp']) + V(0, lift, 0)
        prev = 'hips'
        for b, key in SPINE:
            M[b] = M[prev] @ euler(pose[key])
            Pp[b] = Pp[prev] + G(prev) @ self.tl(b)
            prev = b
        for b in STATIC:
            par = self.js['nodes'][self.par[self.idx[b]]]['name']
            M[b] = M[par]
            Pp[b] = Pp[par] + G(par) @ self.tl(b)
        C = np.eye(3) if clip.abs_arms else M['chest']
        for side, sfx, k in ((1, '.L', 'L'), (-1, '.R', 'R')):
            sh = 'shoulder' + sfx
            M[sh] = M['chest'] @ euler(pose['sh' + k])
            Pp[sh] = Pp['chest'] + G('chest') @ self.tl(sh)
            u = C @ nrm(pose['a%su' % k])
            fd = C @ nrm(pose['a%sf' % k])
            o = C @ nrm(pose['a%so' % k])
            f = fd - u * np.dot(fd, u) + 0.03 * (C @ nrm(V(0, 0.3, 1.0)))
            F1r, F2r = self.arm_rest[sfx]
            ua, fa, ha = 'upper_arm' + sfx, 'forearm' + sfx, 'hand' + sfx
            M[ua] = frame(u, f) @ F1r.T
            M[fa] = frame(fd, o) @ F2r.T
            M[ha] = M[fa] @ euler(pose['h' + k])
            Pp[ua] = Pp[sh] + G(sh) @ self.tl(ua)
            Pp[fa] = Pp[ua] + G(ua) @ self.tl(fa)
            Pp[ha] = Pp[fa] + G(fa) @ self.tl(ha)
        for side, sfx, k in ((1, '.L', 'L'), (-1, '.R', 'R')):
            th, shn, ft = 'thigh' + sfx, 'shin' + sfx, 'foot' + sfx
            H = Pp['hips'] + G('hips') @ self.tl(th)
            Pp[th] = H
            if clip.legs == 'fk':
                M[th] = M['hips'] @ euler(pose['t' + k]) @ rz(-side * FK_ADDUCT)
                M[shn] = M[th] @ euler(pose['s' + k])
                M[ft] = M[shn] @ euler(pose['ft' + k]) @ ry(-side * (MESH_TOE - TOE_OUT))
                Pp[shn] = H + G(th) @ self.tl(shn)
                Pp[ft] = Pp[shn] + G(shn) @ self.tl(ft)
                continue
            F1r, F2r, fwd, L1, L2 = self.leg_rest[sfx]
            pitch, yaw, roll = pose['f%sr' % k]
            yaw_w = yaw + side * TOE_OUT                     # つま先の向き（モデルの座標。正で本人の左）
            Mf = ry(yaw_w - side * MESH_TOE) @ rx(pitch) @ rz(roll)
            ank = self.p(ft)
            floor = V(ank[0], 0.0, ank[2])
            piv = floor + fwd * BALL if pitch >= 0 else floor - fwd * HEEL
            toe = TOE_TIP * math.sin(math.radians(min(pitch, 90.0))) if pitch > 0 else 0.0
            Aw = piv + V(*pose['f' + k]) + V(-side * NARROW, lift + toe, 0) + Mf @ (ank - piv)
            v = Aw - H
            d = float(np.linalg.norm(v))
            dirv = v / d
            self.stretch[k] = d / (L1 + L2)             # 1 を超えると脚が届かず足が浮く
            d = min(max(d, abs(L1 - L2) + 1e-4), L1 + L2 - 1e-4)
            pole = ry(KNEE_FOLLOW * yaw_w + side * KNEE_OUT + pose['k' + k]) @ V(0, 0, 1)
            pp = pole - dirv * np.dot(pole, dirv)
            pp = nrm(pp)
            a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
            h = math.sqrt(max(0.0, L1 * L1 - a * a))
            K = H + dirv * a + pp * h
            A2 = H + dirv * d
            M[th] = frame(K - H, pp) @ F1r.T
            M[shn] = frame(A2 - K, pp) @ F2r.T
            M[ft] = Mf
            Pp[shn], Pp[ft] = K, A2
        return M, Pp

    def world(self, M, Pp):
        W = {}
        for n in M:
            w = np.eye(4)
            w[:3, :3] = M[n] @ self.g(n)
            w[:3, 3] = Pp[n]
            W[n] = w
        return W

    def verts(self, W):
        """部品ごとの世界の頂点。戻り値 [(名前, held, (N,3))]"""
        S = np.stack([W[n] @ self.ibm[i] for i, n in enumerate(self.jname)])
        out = []
        for m in self.meshes:
            p = np.concatenate([m['pos'], np.ones((len(m['pos']), 1))], axis=1)
            if m['J'] is None:
                node = self.js['nodes'][m['node']]
                par = self.js['nodes'][self.par[m['node']]]['name']
                loc = np.eye(4)
                loc[:3, :3] = self.lr[m['node']]
                loc[:3, 3] = self.lt[m['node']]
                wp = (W[par] @ loc @ p.T).T[:, :3]
            else:
                wp = np.zeros((len(p), 3))
                for k in range(4):
                    w = m['W'][:, k]
                    if not np.any(w > 0):
                        continue
                    Sk = S[m['J'][:, k]]                                   # (N,4,4)
                    wp += (np.einsum('nij,nj->ni', Sk, p)[:, :3]) * w[:, None]
            out.append((m['name'], m['held'], wp, m))
        return out

    def locals(self, M, Pp):
        """骨ごとの局所の回転（クォータニオン）。腰は移動も"""
        out = {}
        for n in ANIMATED:
            par = self.js['nodes'][self.par[self.idx[n]]]['name']
            Gp = M[par] @ self.g(par)
            out[n] = m_to_q(Gp.T @ (M[n] @ self.g(n)))
        return out


def bake_clip(rig, clip, report=None):
    N = clip.frames
    times = np.arange(N + 1) / A.FPS
    rot = {n: [] for n in ANIMATED}
    hips_t, root_t = [], []
    stats = dict(min_all=1e9, min_feet=1e9, min_held=1e9, lift_max=0.0, feet_low_each=[], stretch=0.0)
    for k in range(N + 1):
        t = float(k) if not (clip.loop and k == N) else 0.0
        pose = clip.pose(t)
        M, Pp = rig.solve(pose, clip)
        vs = rig.verts(rig.world(M, Pp))
        body_min = min(float(v[:, 1].min()) for _n, held, v, _m in vs if not held)
        held_min = min([float(v[:, 1].min()) for _n, held, v, _m in vs if held] or [1e9])
        if clip.floor == 'contact':
            lift = -body_min
            lift = max(lift, -(held_min + 0.004))
        else:
            lift = max(0.0, -(body_min - 0.0005), -(held_min + 0.004))
        if abs(lift) > 1e-6:
            M, Pp = rig.solve(pose, clip, lift) if clip.legs == 'fk' or clip.floor == 'contact' else (M, {n: p + V(0, lift, 0) for n, p in Pp.items()})
        L = rig.locals(M, Pp)
        for n in ANIMATED:
            q = L[n]
            if rot[n] and np.dot(rot[n][-1], q) < 0:
                q = -q
            rot[n].append(q)
        hips_t.append(Pp['hips'] - Pp['root'])
        root_t.append(Pp['root'].copy())
        # 記録
        vs2 = rig.verts(rig.world(M, Pp))
        allmin = min(float(v[:, 1].min()) for _n, _h, v, _m in vs2)
        feet = []
        for _n, held, v, m in vs2:
            if m['J'] is None:
                continue
            for fb in ('foot.L', 'foot.R'):
                ji = rig.jname.index(fb)
                sel = ((m['J'] == ji) & (m['W'] > 0.5)).any(axis=1)
                if sel.any():
                    feet.append(float(v[sel, 1].min()))
        stats['min_all'] = min(stats['min_all'], allmin)
        stats['min_feet'] = min(stats['min_feet'], min(feet))
        stats['feet_low_each'].append(min(feet))
        stats['min_held'] = min(stats['min_held'], min([float(v[:, 1].min()) for _n, h, v, _m in vs2 if h] or [1e9]))
        stats['lift_max'] = max(stats['lift_max'], abs(lift))
        if clip.legs != 'fk':
            stats['stretch'] = max(stats['stretch'], max(rig.stretch.values() or [0.0]))
    if report is not None:
        report[clip.name] = stats
    return times, rot, np.array(hips_t), np.array(root_t)


def inject(js, binc, rig, clips, only=None):
    binc = bytearray(binc)
    js['animations'] = []
    report = {}

    def add_acc(arr, typ, minmax=False):
        nonlocal binc
        arr = np.ascontiguousarray(arr, dtype=np.float32)
        while len(binc) % 4:
            binc += b'\0'
        off = len(binc)
        binc += arr.tobytes()
        js['bufferViews'].append({'buffer': 0, 'byteOffset': off, 'byteLength': arr.nbytes})
        acc = {'bufferView': len(js['bufferViews']) - 1, 'componentType': 5126, 'count': int(arr.shape[0]), 'type': typ}
        if minmax:
            acc['min'], acc['max'] = [float(arr.min())], [float(arr.max())]
        js['accessors'].append(acc)
        return len(js['accessors']) - 1

    for name in sorted(clips):
        if only and name not in only:
            continue
        clip = clips[name]
        times, rot, hips_t, root_t = bake_clip(rig, clip, report)
        ti = add_acc(times.reshape(-1, 1), 'SCALAR', True)
        samplers, channels = [], []

        def chan(node, path, data, typ):
            samplers.append({'input': ti, 'output': add_acc(data, typ), 'interpolation': 'LINEAR'})
            channels.append({'sampler': len(samplers) - 1, 'target': {'node': rig.idx[node], 'path': path}})
        for n in ANIMATED:
            chan(n, 'rotation', np.array(rot[n]), 'VEC4')
        chan('hips', 'translation', hips_t, 'VEC3')
        chan('root', 'translation', root_t, 'VEC3')
        js['animations'].append({'name': name, 'samplers': samplers, 'channels': channels})
    js['buffers'][0]['byteLength'] = len(binc) + ((4 - len(binc) % 4) % 4)
    return js, binc, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='build/f/haru_f_mesh.glb')
    ap.add_argument('--out', default='build/f/haru_f.glb')
    ap.add_argument('--only', default='')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()
    js, binc = load_glb(args.inp)
    rig = Rig(js, binc)
    clips = A.build_clips()
    js, binc, rep = inject(js, binc, rig, clips, set(args.only.split(',')) if args.only else None)
    save_glb(args.out, js, binc)
    print('wrote', args.out, '%d clips' % len(js['animations']))
    if args.report:
        for n, s in rep.items():
            touch = min(s['feet_low_each'])
            print('  %-7s frames %3d  min all %+.3f  feet %+.3f..%+.3f  held %+.3f  lift %.3f  leg %.2f%s' % (
                n, clips[n].frames, s['min_all'], touch, max(s['feet_low_each']), s['min_held'], s['lift_max'], s['stretch'],
                '  ← 脚が届かない' if s['stretch'] > 1.0 else ''))


if __name__ == '__main__':
    main()
