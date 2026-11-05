#!/usr/bin/env python3
"""2 つの GLB の形が同じか（動作を焼き直した後の確かめ。Blender なし、numpy の入った Python で）。

  python3 tools/blender/recon/glb_shape_diff.py 前.glb 後.glb
      （この機械では /usr/bin/python3 か .venv-blender/bin/python）

形：ノードの名前・親子・基準の TRS・メッシュ・皮、材質（中身・テクスチャ・サンプラーも）・画像（バイトも）、皮の骨の名前・逆バインド行列、
メッシュの面ごとの頂点の数・位置・法線・UV・重み・三角の番号（差 1e-5 まで）。違いがあれば終了コード 1。
動作：動作ごとに、骨の名前と道（translation・rotation・scale）で比べた最大の差（変えた動作だけが大きいはず）と、つなぎ（STEP・LINEAR）の違い。
"""
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glb_audit import Glb  # noqa: E402


def summary(g: Glb):
    js = g.js
    nodes = [(n.get('name'), tuple(n.get('children', [])), tuple(np.round(n.get('translation', [0, 0, 0]), 6)),
              tuple(np.round(n.get('rotation', [0, 0, 0, 1]), 6)), tuple(np.round(n.get('scale', [1, 1, 1]), 6)),
              n.get('mesh'), n.get('skin')) for n in js['nodes']]
    mats = [m.get('name') for m in js.get('materials', [])]
    # 材質は名前のほか中身（色・テクスチャの番号・設定）、画像は名前のほかバイトの指紋も比べる
    mat_js = [json.dumps(m, sort_keys=True) for m in js.get('materials', [])]
    imgs = [(i.get('name'), i.get('mimeType'),
             hashlib.sha1(g.view_bytes(i['bufferView'])).hexdigest() if 'bufferView' in i else i.get('uri'))
            for i in js.get('images', [])]
    mats = (mats, mat_js, json.dumps(js.get('textures', []), sort_keys=True), json.dumps(js.get('samplers', []), sort_keys=True))
    skins = []
    for s in js.get('skins', []):
        skins.append(([js['nodes'][j].get('name') for j in s['joints']], g.acc(s['inverseBindMatrices'])))
    meshes = []
    for m in js['meshes']:
        prims = []
        for p in m['primitives']:
            at = p['attributes']
            d = {k: g.acc(v) for k, v in at.items()}
            d['_idx'] = g.acc(p['indices']) if 'indices' in p else None
            d['_mat'] = mats[0][p['material']] if 'material' in p else None
            d['_targets'] = len(p.get('targets', []))
            prims.append(d)
        meshes.append((m.get('name'), prims, m.get('extras', {}).get('targetNames')))
    anims = sorted((a.get('name'), len(a['channels'])) for a in js.get('animations', []))
    return nodes, mats, imgs, skins, meshes, anims


def compare_shape(a, b):
    A, B = summary(Glb(a)), summary(Glb(b))
    ok = True

    def bad(msg):
        nonlocal ok
        ok = False
        print('違い：', msg)

    if A[0] != B[0]:
        na, nb = {n[0] for n in A[0]}, {n[0] for n in B[0]}
        bad('ノード：%d 対 %d、片方だけ %s / %s' % (len(A[0]), len(B[0]), sorted(na - nb)[:10], sorted(nb - na)[:10]))
        for x, y in zip(A[0], B[0]):
            if x != y:
                print('   ', x, '\n   ', y)
                break
    else:
        print('ノード：同じ（%d、名前・親子・基準の TRS・メッシュ・皮）' % len(A[0]))
    print('材質：', '同じ' if A[1] == B[1] else '違う', A[1][0], '（中身・テクスチャ・サンプラーも）')
    if A[1] != B[1]:
        bad('材質 %s / %s' % (A[1][0], B[1][0]) if A[1][0] != B[1][0] else '材質の中身・テクスチャ・サンプラー')
    print('画像：', '同じ' if A[2] == B[2] else '違う', len(A[2]), '（バイトも）')
    if A[2] != B[2]:
        bad('画像')
    if len(A[3]) != len(B[3]):
        bad('皮の数')
    for (ja, ia), (jb, ib) in zip(A[3], B[3]):
        if ja != jb:
            bad('皮の骨の名前')
        d = np.abs(ia - ib).max() if ia.shape == ib.shape else np.inf
        print('皮：骨 %d 本、名前 %s、逆バインド行列の差の最大 %.2e' % (len(ja), '同じ' if ja == jb else '違う', d))
        if d > 1e-6:
            bad('逆バインド行列')
    tot_a = tot_b = 0
    for (ma, pa, ta), (mb, pb, tb) in zip(A[4], B[4]):
        if ma != mb or len(pa) != len(pb) or ta != tb:
            bad('メッシュ %s / %s（面 %d / %d、形キー %s / %s）' % (ma, mb, len(pa), len(pb), ta, tb))
            continue
        for i, (x, y) in enumerate(zip(pa, pb)):
            n_a, n_b = len(x['POSITION']), len(y['POSITION'])
            tot_a += n_a
            tot_b += n_b
            if n_a != n_b or x['_mat'] != y['_mat'] or set(x) != set(y):
                bad('%s[%d]：頂点 %d / %d、材質 %s / %s、属性 %s / %s' % (ma, i, n_a, n_b, x['_mat'], y['_mat'], sorted(set(x) - {'_idx', '_mat', '_targets'}), sorted(set(y) - {'_idx', '_mat', '_targets'})))
                continue
            worst = {}
            for k in x:
                if k in ('_mat', '_targets'):
                    continue
                if x[k] is None or y[k] is None:
                    continue
                if x[k].shape != y[k].shape:
                    bad('%s[%d] %s の形' % (ma, i, k))
                    continue
                worst[k] = float(np.abs(x[k] - y[k]).max()) if x[k].size else 0.0
            if any(v > 1e-5 for v in worst.values()):
                bad('%s[%d] %s' % (ma, i, {k: '%.2e' % v for k, v in worst.items() if v > 1e-5}))
    print('頂点の合計：%d / %d' % (tot_a, tot_b))
    print('動作：', A[5] == B[5] and '同じ名前・道の数' or '違う', [x[0] for x in B[5]])
    print('結論：', '形は同じ（動作の外）' if ok else '形に違いがある')
    return 0 if ok else 1



def chans(g):
    out = {}
    for a in g.js.get('animations', []):
        d = {}
        for c in a['channels']:
            s = a['samplers'][c['sampler']]
            nm = g.js['nodes'][c['target']['node']].get('name')
            d[(nm, c['target']['path'])] = (g.acc(s['input'])[:, 0], g.acc(s['output']), s.get('interpolation', 'LINEAR'))
        out[a['name']] = d
    return out


def compare_anims(a, b):
    A, B = chans(Glb(a)), chans(Glb(b))
    for name in sorted(set(A) | set(B)):
        if name not in A or name not in B:
            print(name, '片方だけ')
            continue
        da, db = A[name], B[name]
        worst = 0.0
        wk = None
        interp = []
        for k in sorted(set(da) | set(db)):
            if k not in da or k not in db:
                print(name, '道が片方だけ', k)
                continue
            ta, va, ia = da[k]
            tb, vb, ib = db[k]
            if ia != ib:
                # つなぎ（STEP・LINEAR・CUBICSPLINE）が違うと、こまと値が同じでも動きが変わる（動く道で STEP ならかくかく）。
                # 値が一定の道なら STEP と LINEAR は同じ動き（焼き直すと書き出しがどちらかを選ぶ：dash の root.translation）
                const = {ia, ib} <= {'STEP', 'LINEAR'} and all(len(v) and np.abs(v - v[0]).max() <= 1e-5 for v in (va, vb))
                interp.append('%s.%s %s→%s%s' % (k[0], k[1], ia, ib, '（値が一定なので動きは同じ）' if const else ''))
            if ta.shape != tb.shape or np.abs(ta - tb).max() > 1e-5:
                # こまの置き方が違う（作り直した動作）。差は測らない
                worst, wk = np.inf, ('こま %d → %d' % (len(ta), len(tb)), k[0])
                continue
            if va.shape != vb.shape:
                worst, wk = np.inf, ('値の数 %d → %d' % (len(va), len(vb)), k[0])
                continue
            x = va.copy()
            if k[1] == 'rotation':
                sgn = np.sign(np.sum(va * vb, axis=1))[:, None]
                x = va * sgn
            d = float(np.abs(x - vb).max())
            if d > worst:
                worst, wk = d, k
        print('%-8s 道 %d / %d、最大の差 %s %s' % (name, len(da), len(db), '%.2e' % worst if worst < np.inf else 'こまが違う', wk or ''))
        if interp:
            print('         つなぎが違う：%s' % '、'.join(interp))


if __name__ == '__main__':
    rc = compare_shape(sys.argv[1], sys.argv[2])
    print('動作ごとの最大の差：')
    compare_anims(sys.argv[1], sys.argv[2])
    sys.exit(rc)
