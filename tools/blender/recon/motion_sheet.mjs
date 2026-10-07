// 動作のこまを並べた画像（確認ページ model-viewer で撮る。ユーザーが見るのと同じ描画）。
//
//   node tools/blender/recon/motion_sheet.mjs [--glb godot/assets/models/haru_r.glb] [--clips combo1,combo2,combo3]
//        [--out docs/art_orders/haru_r_trial] [--work build/motion] [--prefix motion] [--every 1]
//        [--views back-right,front-left,left] [--active 0.25,0.7]
//
// 1 枚に 1 動作。横にこま（GLB の標本 60fps を --every 個おき）、縦に見る方向。各こまに番号・秒・当たり判定の印（●）。
// 方向：front 0・front-left 45・left 90・back-left 135・back 180・back-right 225（ゲームのカメラに近い）・right 270・
// front-right 315。数字で「方位,仰角」も書ける（例 225,60）。
// 光刃は GLB のまま見える（ゲームでは攻撃中だけ出す）。
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..', '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1]]);
  return acc;
}, []));
const GLB = path.resolve(REPO, args.glb || 'godot/assets/models/haru_r.glb');
const CLIPS = (args.clips || 'combo1,combo2,combo3').split(',');
const OUT = path.resolve(REPO, args.out || 'docs/art_orders/haru_r_trial');
const WORK = path.resolve(REPO, args.work || 'build/motion');
const PREFIX = args.prefix || 'motion';
const EVERY = parseInt(args.every || '1', 10);
const FPS = 60;
const ACTIVE = (args.active || '0.25,0.7').split(',').map(parseFloat);
const AZ = { front: 0, 'front-left': 45, left: 90, 'back-left': 135, back: 180, 'back-right': 225, right: 270,
  'front-right': 315 };
const VIEWS = (args.views || 'back-right,front-left,left').split(',').map((v) => {
  if (v in AZ) return { name: v, th: AZ[v], ph: v.startsWith('back') ? 62 : 80 };
  const [th, ph] = v.split(':').map(parseFloat);
  return { name: `${th}°/${ph}°`, th, ph: ph || 80 };
});
const MV_URL = 'https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js';
const TILE = 230;

fs.mkdirSync(WORK, { recursive: true });
fs.mkdirSync(OUT, { recursive: true });
const mvJs = path.join(WORK, 'model-viewer.min.js');
if (!fs.existsSync(mvJs)) execFileSync('curl', ['-sSfL', '-o', mvJs, MV_URL]);

const browser = await chromium.launch({
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({ viewport: { width: 760, height: 900 } });
page.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
const name = path.basename(GLB, '.glb');
const files = {
  '/index.html': [path.join(REPO, 'tools/model_viewer/index.html'), 'text/html'],
  [`/${name}.glb`]: [GLB, 'model/gltf-binary'],
};
await page.route('**/*', (route) => {
  const u = new URL(route.request().url());
  if (u.href === MV_URL) return route.fulfill({ path: mvJs, contentType: 'text/javascript' });
  if (u.host === 'audit.local' && files[u.pathname]) {
    return route.fulfill({ path: files[u.pathname][0], contentType: files[u.pathname][1] });
  }
  if (u.host === 'audit.local') return route.fulfill({ status: 404, body: '' });
  return route.abort();
});
await page.goto(`http://audit.local/index.html?m=${name}`);
await page.waitForFunction(() => { const mv = document.getElementById('mv'); return mv && mv.loaded; }, null,
  { timeout: 180000 });
await page.evaluate(() => {
  const mv = document.getElementById('mv');
  mv.style.width = '560px'; mv.style.height = '560px';
  mv.minCameraOrbit = 'auto 0deg 0.05m'; mv.maxCameraOrbit = 'auto 180deg auto'; mv.minFieldOfView = '5deg';
  mv.interpolationDecay = 1;
});

for (const clip of CLIPS) {
  // 動作を選び、実際に進んだのを確かめてから止める（audit_viewer.mjs と同じ）
  const duration = await page.evaluate(async (clip) => {
    const mv = document.getElementById('mv');
    if (!mv.availableAnimations.includes(clip)) return -1;
    mv.animationName = clip; mv.play();
    const t0 = Date.now();
    await new Promise((r) => setTimeout(r, 600));
    while (mv.currentTime < 0.03 && Date.now() - t0 < 10000) await new Promise((r) => setTimeout(r, 150));
    mv.pause();
    return mv.duration;
  }, clip);
  if (duration < 0) { console.log('動作が無い：', clip); continue; }
  const nFrames = Math.round(duration * FPS);
  const frames = [];
  for (let f = 0; f <= nFrames; f += EVERY) frames.push(f);
  const tdir = path.join(WORK, 'tiles', `${PREFIX}_${clip}`);
  fs.mkdirSync(tdir, { recursive: true });
  const rows = [];
  for (const v of VIEWS) {
    await page.evaluate(async ({ th, ph }) => {
      const mv = document.getElementById('mv');
      mv.cameraTarget = '0m 0.85m 0m';
      mv.cameraOrbit = `${th}deg ${ph}deg 3.6m`;
      mv.fieldOfView = '34deg';
      mv.jumpCameraToGoal();
      await new Promise((r) => setTimeout(r, 300));
    }, v);
    const tiles = [];
    for (const f of frames) {
      // 動作の終わり（= duration）は 0 秒に巻き戻るので、わずかに手前で止める
      const t = Math.min(duration - 0.002, f / FPS);
      await page.evaluate(async (t) => {
        const mv = document.getElementById('mv');
        mv.currentTime = t;
        await new Promise((r) => setTimeout(r, 160));
      }, t);
      const file = path.join(tdir, `${v.name}_${String(f).padStart(2, '0')}.png`);
      await page.locator('#mv').screenshot({ path: file });
      const ratio = t / duration;
      const active = ratio >= ACTIVE[0] - 1e-6 && ratio <= ACTIVE[1] + 1e-6;
      tiles.push({ file, label: `${f}  ${t.toFixed(3)}s${active ? ' ●' : ''}` });
    }
    rows.push({ view: v.name, tiles });
  }
  // 並べる：方向ごとに 1 区画。1 行は最大 COLS こま（長い動作は折り返す）
  const COLS = parseInt(args.cols || '10', 10);
  const img = (t) => `<div style="position:relative;flex:none"><img src="data:image/png;base64,${fs.readFileSync(t.file).toString('base64')}"
        style="width:${TILE}px;height:${TILE}px;display:block"><span style="position:absolute;left:3px;top:2px;
        background:rgba(0,0,0,.55);padding:1px 4px;border-radius:3px">${t.label}</span></div>`;
  const html = `<html><body style="margin:0;background:#222;font:12px sans-serif;color:#eee">
    <div style="padding:6px 8px;font-size:14px">${name}.glb ／ ${clip}（${duration.toFixed(3)} 秒、${nFrames} こま、60fps）
      ● = 当たり判定（${ACTIVE[0] * 100}〜${ACTIVE[1] * 100}%）</div>
    ${rows.map((r) => `<div style="padding:4px 4px 2px;color:#ccc;border-top:1px solid #444">${r.view}</div>
      ${Array.from({ length: Math.ceil(r.tiles.length / COLS) }, (_, i) => `<div style="display:flex;gap:2px;padding:0 4px 2px">
        ${r.tiles.slice(i * COLS, (i + 1) * COLS).map(img).join('')}</div>`).join('')}`).join('')}
    </body></html>`;
  const sheet = await browser.newPage({ viewport: { width: Math.min(frames.length, COLS) * (TILE + 2) + 10, height: 400 } });
  await sheet.setContent(html);
  await sheet.waitForTimeout(200);
  const out = path.join(OUT, `${PREFIX}_${clip}.jpg`);
  await sheet.screenshot({ path: out, fullPage: true, type: 'jpeg', quality: 80 });
  await sheet.close();
  console.log('wrote', path.relative(REPO, out), `${frames.length} こま × ${VIEWS.length} 方向`);
}
await browser.close();
