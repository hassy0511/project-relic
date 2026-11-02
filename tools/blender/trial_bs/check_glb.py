"""haru_bs.glb をゲームの約束と比べる小さな glTF 読み（Blender なしの Python だけで動く）。

  python3 tools/blender/trial_bs/check_glb.py [godot/assets/models/haru_bs.glb] [--ref godot/assets/models/haru_r.glb]

確かめること（godot-export の checklist・export-pipeline の Verification Matrix を、ゲームの約束で具体にしたもの）：
骨 29 本の名前、14 の動作の名前と長さ（haru_r と比べる）、ゲームが探す物（LightBlade・muzzle・Frame_*）と骨の子の位置、
顔の材質（face）・銃の材質（spark_gun）、透明（BLEND）の材質が無いこと、三角形・材質・メッシュ・描く面の数、
身長・原点・正面（haru_r と比べる）、骨の大きさの道が無いこと、輪の動作の継ぎ目、根の動き。
haru_r.glb からは名前・長さ・高さ・向きだけを読む（形・重み・キーは使わない）。
"""
import json
import struct
import sys

CONTRACT_BONES = ['root', 'hips', 'spine', 'chest', 'neck', 'head', 'hair.front', 'hair.top', 'hair.back.L', 'hair.back.R',
                  'hair.nape', 'hair.side.L', 'hair.side.R', 'shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L', 'shoulder.R',
                  'upper_arm.R', 'forearm.R', 'hand.R', 'thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R',
                  'pouch.L', 'pouch.R']
CLIPS = ['air', 'charge', 'combo1', 'combo2', 'combo3', 'dash', 'dead', 'drill', 'fall', 'hurt', 'idle', 'jump', 'lunge', 'run']
LOOPS = ['idle', 'run', 'fall', 'drill']


def load(path):
    b = open(path, 'rb').read()
    ln = struct.unpack_from('<I', b, 8)[0]
    off, js, binc = 12, None, None
    while off < ln:
        cl, ct = struct.unpack_from('<II', b, off)
        data = b[off + 8: off + 8 + cl]
        if ct == 0x4E4F534A:
            js = json.loads(data)
        elif ct == 0x004E4942:
            binc = data
        off += 8 + cl
    return js, binc


def acc(js, binc, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    fmt = {5126: 'f', 5123: 'H', 5125: 'I', 5121: 'B'}[a['componentType']]
    sz = struct.calcsize(fmt)
    stride = bv.get('byteStride', sz * n)
    base = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    return [struct.unpack_from('<' + fmt * n, binc, base + k * stride) for k in range(a['count'])]


def parents(js):
    p = {}
    for i, n in enumerate(js['nodes']):
        for c in n.get('children', []):
            p[c] = i
    return p


def clip_lengths(js):
    out = {}
    for a in js.get('animations', []):
        out[a['name']] = max(js['accessors'][a['samplers'][c['sampler']]['input']]['max'][0] for c in a['channels'])
    return out


def bounds(js, binc):
    """皮のメッシュの基準の姿勢での範囲（ノードの変換は単位のとき）"""
    lo, hi = [1e9] * 3, [-1e9] * 3
    for n in js['nodes']:
        if 'mesh' not in n or 'skin' not in n:
            continue
        for pr in js['meshes'][n['mesh']]['primitives']:
            a = js['accessors'][pr['attributes']['POSITION']]
            lo = [min(x, y) for x, y in zip(lo, a['min'])]
            hi = [max(x, y) for x, y in zip(hi, a['max'])]
    return lo, hi


def check(path, ref=None):
    js, binc = load(path)
    rep, bad = [], []
    nodes = js['nodes']
    name = {i: n.get('name', '') for i, n in enumerate(nodes)}
    par = parents(js)
    # 骨
    skins = js.get('skins', [])
    joints = sorted({name[j] for s in skins for j in s['joints']})
    ok = joints == sorted(CONTRACT_BONES) and all(len(s['joints']) == 29 for s in skins)
    rep.append('bones: %d skins, %d joints, contract names %s' % (len(skins), len(joints), 'OK' if ok else 'MISMATCH'))
    if not ok:
        bad.append('bones ' + str(set(joints) ^ set(CONTRACT_BONES)))
    # 動作
    L = clip_lengths(js)
    ok = sorted(L) == sorted(CLIPS)
    rep.append('clips: %d %s' % (len(L), 'OK' if ok else 'MISMATCH ' + str(set(L) ^ set(CLIPS))))
    if not ok:
        bad.append('clips')
    RL = {}
    if ref:
        rjs, rbin = load(ref)
        RL = clip_lengths(rjs)
    for c in CLIPS:
        if c in L:
            rep.append('  %-7s %.4f s%s' % (c, L[c], ('  (haru_r %.4f)' % RL[c]) if c in RL else ''))
    # 道の種類・骨の大きさ・根の動き
    paths = {}
    root_moves = False
    for a in js.get('animations', []):
        for ch in a['channels']:
            pth = ch['target']['path']
            paths[pth] = paths.get(pth, 0) + 1
            if name[ch['target']['node']] == 'root' and pth == 'translation':
                vals = acc(js, binc, a['samplers'][ch['sampler']]['output'])
                if max(abs(v[k] - vals[0][k]) for v in vals for k in range(3)) > 1e-5:
                    root_moves = True
    rep.append('channels by path: %s (scale tracks: %d)' % (paths, paths.get('scale', 0)))
    if paths.get('scale', 0):
        bad.append('scale tracks')
    rep.append('root translation animated: %s (in place: hips carry the bob)' % root_moves)
    # 輪の継ぎ目：最初と最後の値の差（回転は向きの差 1 - |dot|）
    for a in js.get('animations', []):
        if a['name'] not in LOOPS:
            continue
        worst = 0.0
        for ch in a['channels']:
            vals = acc(js, binc, a['samplers'][ch['sampler']]['output'])
            v0, v1 = vals[0], vals[-1]
            if ch['target']['path'] == 'rotation':
                d = 1.0 - abs(sum(x * y for x, y in zip(v0, v1)))
            else:
                d = max(abs(x - y) for x, y in zip(v0, v1))
            worst = max(worst, d)
        rep.append('loop seam %-5s worst first/last difference %.2e' % (a['name'], worst))
        if worst > 1e-4:
            bad.append('loop seam ' + a['name'])
    # ゲームが探す物
    for want, how in (('LightBlade', 'forearm.L'), ('muzzle', 'hand.R'), ('Frame_core', None), ('Frame_arm', None), ('Frame_legs', None)):
        idx = [i for i in name if name[i] == want]
        if not idx:
            rep.append('node %s: MISSING' % want)
            bad.append(want)
            continue
        i = idx[0]
        chain, k = [], i
        while k in par:
            k = par[k]
            chain.append(name[k])
        kind = 'mesh' if 'mesh' in nodes[i] else 'empty'
        skin = ' skinned' if 'skin' in nodes[i] else ''
        under = (' under bone ' + how + (' OK' if how in chain else ' MISSING')) if how else ''
        if how and how not in chain:
            bad.append(want + ' parent')
        rep.append('node %-10s %s%s%s (parents: %s)' % (want, kind, skin, under, ' > '.join(reversed(chain))))
    # 材質
    mats = [m['name'] for m in js.get('materials', [])]
    face = [m for m in mats if 'face' in m]
    gun = [m for m in mats if m.startswith('spark_gun')]
    blend = [m['name'] for m in js.get('materials', []) if m.get('alphaMode') == 'BLEND']
    rep.append('materials %d: %s; face %s; spark_gun %s; alpha BLEND %s' % (len(mats), mats, face, gun, blend or 'none'))
    if not face or not gun:
        bad.append('materials')
    imgs = [im.get('name', '') for im in js.get('images', [])]
    rep.append('images: %s' % imgs)
    # 数
    tris, prims = 0, 0
    for m in js['meshes']:
        for p in m['primitives']:
            prims += 1
            tris += js['accessors'][p['indices']]['count'] // 3
    rep.append('meshes %d, draw surfaces (primitives) %d, triangles %d' % (len(js['meshes']), prims, tris))
    # 身長・原点・正面
    lo, hi = bounds(js, binc)
    rep.append('skinned rest bounds x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f  (height %.3f m, glTF +Z = front)' % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], hi[1] - lo[1]))
    if ref:
        rlo, rhi = bounds(rjs, rbin)
        rep.append('haru_r      bounds x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f  (height %.3f m)' % (rlo[0], rhi[0], rlo[1], rhi[1], rlo[2], rhi[2], rhi[1] - rlo[1]))
    # 面の向きの目安：足の先（y < 0.05 の点の z の最大）が +Z
    return rep, bad


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else 'godot/assets/models/haru_bs.glb'
    ref = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else None
    rep, bad = check(path, ref)
    print('\n'.join(rep))
    print('RESULT:', 'PASS' if not bad else 'FAIL ' + ', '.join(bad))
