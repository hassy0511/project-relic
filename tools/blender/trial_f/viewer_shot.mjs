// 確認ページ（tools/model_viewer/index.html）を開いて画面を撮る（並べて比べる表示の確かめ）。
//   node tools/blender/trial_f/viewer_shot.mjs --query "m=haru_f&c=haru_r&a=combo1" --out build/f/viewer.png
//        [--glb haru_f=build/f/haru_f.glb] [--width 1280 --height 900] [--time 0.07] [--orbit "180deg 78deg auto"]
// GLB は既定で godot/assets/models/<名前>.glb。--glb で名前ごとに差し替える。
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..', '..');
const argv = process.argv.slice(2);
const args = {};
const glbs = {};
for (let i = 0; i < argv.length; i += 2) {
  const k = argv[i].slice(2);
  if (k === 'glb') { const [n, p] = argv[i + 1].split('='); glbs[n] = path.resolve(REPO, p); } else args[k] = argv[i + 1];
}
const MV_URL = 'https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js';
const work = path.join(REPO, 'build/f/audit_work');
fs.mkdirSync(work, { recursive: true });
const mvJs = path.join(work, 'model-viewer.min.js');
if (!fs.existsSync(mvJs)) execFileSync('curl', ['-sSfL', '-o', mvJs, MV_URL]);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: parseInt(args.width || '1280'), height: parseInt(args.height || '900') }, deviceScaleFactor: 1 });
page.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
await page.route('**/*', (route) => {
  const u = new URL(route.request().url());
  if (u.href === MV_URL) return route.fulfill({ path: mvJs, contentType: 'text/javascript' });
  if (u.host !== 'view.local') return route.abort();
  if (u.pathname === '/index.html') return route.fulfill({ path: path.join(REPO, 'tools/model_viewer/index.html'), contentType: 'text/html' });
  const m = /^\/([\w.-]+)\.glb$/.exec(u.pathname);
  if (m) {
    const p = glbs[m[1]] || path.join(REPO, 'godot/assets/models', m[1] + '.glb');
    if (fs.existsSync(p)) return route.fulfill({ path: p, contentType: 'model/gltf-binary' });
  }
  return route.fulfill({ status: 404, body: '' });
});
await page.goto(`http://view.local/index.html?${args.query || 'm=haru_f'}`);
await page.waitForFunction(() => {
  const a = document.getElementById('mv'), b = document.getElementById('mv2');
  return a && a.loaded && (document.getElementById('pane2').hidden || b.loaded);
}, null, { timeout: 180000 });
await page.waitForTimeout(1500);
if (args.orbit) {
  await page.evaluate((o) => { for (const id of ['mv', 'mv2']) { const v = document.getElementById(id); v.cameraOrbit = o; v.jumpCameraToGoal(); } }, args.orbit);
}
if (args.time !== undefined) {
  await page.evaluate(async (t) => {
    document.getElementById('pause').click();
    for (const id of ['mv', 'mv2']) { const v = document.getElementById(id); if (v.loaded) v.currentTime = t; }
    await new Promise((r) => setTimeout(r, 600));
  }, parseFloat(args.time));
}
await page.waitForTimeout(800);
const out = path.resolve(REPO, args.out || 'build/f/viewer.png');
await page.screenshot({ path: out, fullPage: args.full === '1' });
console.log('wrote', out, await page.evaluate(() => document.getElementById('time').textContent));
await browser.close();
