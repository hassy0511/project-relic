// 確認ページ（tools/model_viewer/index.html、model-viewer）でモデルを開き、決まった格子の方向から撮って並べる。
// ユーザーが見るのと同じ画面（同じページ・同じ光・GLB をそのまま読む）で、仕上げの報告の前に全部の方向を見るためのもの。
//
//   node tools/blender/recon/audit_viewer.mjs [--glb godot/assets/models/haru_r.glb] [--out docs/art_orders/haru_r_trial]
//        [--work build/audit] [--zones full,head,torso,hips,legs] [--anim idle] [--time 0] [--prefix audit]
//
// 格子（固定。比べられるように変えない）：
//   full（全身）：方位 8 つ（0 = 正面から 45 度ずつ、+ = 本人の左へ回る）× 高さ 3 つ（下から・水平・上から）
//   head（頭・首）・torso（胴・腕）・hips（腰・太もも）・legs（膝・すね・靴）：方位 8 つ × 高さ 2 つ（水平・上から）の近写
// 出力：<out>/<prefix>_<zone>.jpg（1 枚に 1 区域。各こまに方位・高さの名前）。こまは <work>/tiles/<zone>/ にも残す。
// ページは手元のファイルを Playwright の route で配る（サーバーは要らない）。model-viewer の JS は最初に一度だけ
// 取ってきて <work>/model-viewer.min.js に置く（プロキシ経由で取れる）。
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
const OUT = path.resolve(REPO, args.out || 'docs/art_orders/haru_r_trial');
const WORK = path.resolve(REPO, args.work || 'build/audit');
const ANIM = args.anim || 'idle';
const TIME = parseFloat(args.time || '0');
const PREFIX = args.prefix || 'audit';
// --track foot.L,foot.R：見る所を、その骨（複数なら中点）の今の位置にする（動作の確認：走り・跳躍・倒れなど）
// three.js は骨の名前の '.' を消す（foot.L → footL）ので、'.'・'_' を除いて比べる
const TRACK = args.track ? args.track.split(',').map((n) => n.replace(/[._]/g, '')) : null;
const MV_URL = 'https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js';

// 区域：見る所の高さ（モデルの座標、m。足の裏 = 0、身長 1.55）・距離・画角・高さの一覧（極角、度。90 = 水平）
const AZ = [0, 45, 90, 135, 180, 225, 270, 315];
const ZONES = {
  full: { y: 0.80, dist: 3.6, fov: 30, el: [['below', 105], ['level', 88], ['above', 62]] },
  head: { y: 1.36, dist: 0.85, fov: 26, el: [['level', 88], ['above', 62]] },
  torso: { y: 1.02, dist: 1.05, fov: 30, el: [['level', 88], ['above', 62]] },
  hips: { y: 0.66, dist: 1.25, fov: 30, el: [['level', 88], ['above', 62]] },
  legs: { y: 0.27, dist: 1.35, fov: 30, el: [['level', 88], ['above', 62]] },
};
const zones = (args.zones || 'full,head,torso,hips,legs').split(',');
const AZ_NAME = { 0: 'front', 45: 'front-left', 90: 'left', 135: 'back-left', 180: 'back', 225: 'back-right',
  270: 'right', 315: 'front-right' };

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
// こまを正方形にする（ページの見た目はそのまま、model-viewer の大きさだけ）
await page.evaluate(() => {
  const mv = document.getElementById('mv');
  mv.style.width = '640px'; mv.style.height = '640px';
});
// 動作は一度だけ選び、少し流してから止めて時刻を合わせる（こまごとに選び直すと前の動作との混ぜ合わせが残る）
await page.evaluate(async ({ ANIM, TIME }) => {
  const mv = document.getElementById('mv');
  mv.animationName = ANIM; mv.play();
  await new Promise((r) => setTimeout(r, 1500));
  mv.pause(); mv.currentTime = TIME;
  await new Promise((r) => setTimeout(r, 300));
}, { ANIM, TIME });

for (const zone of zones) {
  const z = ZONES[zone];
  const tdir = path.join(WORK, 'tiles', zone);
  fs.mkdirSync(tdir, { recursive: true });
  const tiles = [];
  for (const [eln, ph] of z.el) {
    for (const th of AZ) {
      await page.evaluate(async ({ th, ph, z, TRACK }) => {
        const mv = document.getElementById('mv');
        mv.minCameraOrbit = 'auto 0deg 0.05m'; mv.maxCameraOrbit = 'auto 180deg auto'; mv.minFieldOfView = '5deg';
        let tgt = `0m ${z.y}m 0m`;
        if (TRACK) {
          const sym = Object.getOwnPropertySymbols(mv).find((q) => q.description === 'scene');
          const scene = mv[sym];
          scene.updateMatrixWorld(true);
          const ps = [];
          scene.traverse((o) => {
            const nm = o.name.replace(/[._]/g, '');
            if (TRACK.includes(nm) && !ps.some((p) => p.name === nm)) ps.push({ name: nm, p: o.getWorldPosition(o.position.clone()) });
          });
          if (ps.length) {
            const c = ps[0].p.clone();
            for (const q of ps.slice(1)) c.add(q.p);
            c.multiplyScalar(1 / ps.length);
            (scene.target || scene).worldToLocal(c);
            tgt = `${c.x}m ${c.y}m ${c.z}m`;
          }
        }
        mv.cameraTarget = tgt;
        mv.cameraOrbit = `${th}deg ${ph}deg ${z.dist}m`;
        mv.fieldOfView = `${z.fov}deg`;
        mv.jumpCameraToGoal();
        await new Promise((r) => setTimeout(r, 350));
      }, { th, ph, z, TRACK });
      const f = path.join(tdir, `${eln}_${String(th).padStart(3, '0')}.png`);
      await page.locator('#mv').screenshot({ path: f });
      tiles.push({ f, label: `${zone} ${AZ_NAME[th]} (${th}°) / ${eln} (${ph}°)` });
    }
  }
  // 並べる：横 8（方位）× 縦（高さ）
  const cols = 8, size = 360;
  const html = `<html><body style="margin:0;background:#222;font:13px sans-serif;color:#eee">
    <div style="display:grid;grid-template-columns:repeat(${cols},${size}px);gap:4px;padding:4px">
    ${tiles.map((t) => `<div style="position:relative"><img src="data:image/png;base64,${fs.readFileSync(t.f).toString('base64')}"
      style="width:${size}px;height:${size}px;display:block"><span style="position:absolute;left:4px;top:3px;
      background:rgba(0,0,0,.55);padding:1px 5px;border-radius:3px">${t.label}</span></div>`).join('')}
    </div></body></html>`;
  const sheet = await browser.newPage({ viewport: { width: cols * (size + 4) + 4, height: 400 } });
  await sheet.setContent(html);
  await sheet.waitForTimeout(200);
  const out = path.join(OUT, `${PREFIX}_${zone}.jpg`);
  await sheet.screenshot({ path: out, fullPage: true, type: 'jpeg', quality: 82 });
  await sheet.close();
  console.log('wrote', path.relative(REPO, out), tiles.length, 'tiles');
}
await browser.close();
