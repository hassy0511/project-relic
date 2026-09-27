"""claude.ai のアーティファクト（非公開のページ）として公開するための書き出し。

アーティファクトは GLB を配信できないため、GLB を中身が同じ JSON 形式の glTF（*.gltf.json）に変換し、
ビルド済みの JS の参照先を書き換える。
  npx vite build && python3 tools/build_artifact.py <出力先>
"""
import base64
import glob
import json
import os
import shutil
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIST = os.path.join(REPO, 'dist')
out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'dist-artifact'))

shutil.rmtree(out, ignore_errors=True)
os.makedirs(os.path.join(out, 'assets'))
js_src = glob.glob(os.path.join(DIST, 'assets', 'index-*.js'))[0]
css = open(glob.glob(os.path.join(DIST, 'assets', 'index-*.css'))[0], encoding='utf-8').read()
for d in ('models', 'levels', 'audio'):
    shutil.copytree(os.path.join(DIST, 'assets', d), os.path.join(out, 'assets', d))

js = open(js_src, encoding='utf-8').read()
for glb in glob.glob(os.path.join(out, 'assets', '*', '*.glb')):
    b = open(glb, 'rb').read()
    jl = struct.unpack('<I', b[12:16])[0]
    doc = json.loads(b[20:20 + jl])
    off = 20 + jl
    bl = struct.unpack('<I', b[off:off + 4])[0]
    doc['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(b[off + 8:off + 8 + bl]).decode()
    target = glb[:-4] + '.gltf.json'
    json.dump(doc, open(target, 'w'))
    os.remove(glb)
    name = os.path.basename(glb)
    js = js.replace(name, name[:-4] + '.gltf.json')
open(os.path.join(out, 'assets', 'index.js'), 'w', encoding='utf-8').write(js)

page = f"""<title>アークウォーカー</title>
<style>
{css}
</style>
<canvas id="game"></canvas>
<div id="ui"><div id="loading" class="loading">読み込み中……</div></div>
<script type="module" src="assets/index.js"></script>
"""
open(os.path.join(out, 'arkwalker.html'), 'w', encoding='utf-8').write(page)
print('wrote', out)
