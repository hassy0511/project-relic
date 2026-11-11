// haru_f：動作のこまを並べた画像（three.js で描く。真後ろ＝ゲームのカメラ、真横、正面）。
//
//   node tools/blender/trial_f/motion_sheet.mjs [--glb build/f/haru_f.glb] [--clips combo1,combo2] [--out build/f/motion]
//        [--every 1] [--frames 0-10] [--views back,left,front] [--tile 200]
//
// three.js は build/f/three（npm pack three@0.160.0 を展開）から読む。無ければ取り寄せる。
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..', '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1]]);
  return acc;
}, []));
const GLB = path.resolve(REPO, args.glb || 'build/f/haru_f.glb');
const OUT = path.resolve(REPO, args.out || 'build/f/motion');
const EVERY = parseInt(args.every || '1', 10);
const TILE = parseInt(args.tile || '200', 10);
const VIEWS = (args.views || 'back,left,front').split(',');
const ATTACK = ['combo1', 'combo2', 'combo3', 'lunge', 'charge', 'air', 'dash'];
const THREE_DIR = path.join(REPO, 'build/f/three/package');
if (!fs.existsSync(path.join(THREE_DIR, 'build/three.module.js'))) {
  fs.mkdirSync(path.join(REPO, 'build/f/three'), { recursive: true });
  execFileSync('npm', ['pack', 'three@0.160.0'], { cwd: path.join(REPO, 'build/f') });
  execFileSync('tar', ['-xzf', 'three-0.160.0.tgz', '-C', 'three'], { cwd: path.join(REPO, 'build/f') });
}
fs.mkdirSync(OUT, { recursive: true });

const HTML = `<!doctype html><html><body style="margin:0;background:#888">
<script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9a9ca4);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8478, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-2, 5, -3); scene.add(sun);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(6, 6), new THREE.MeshBasicMaterial({ color: 0x7c7e86 }));
floor.rotation.x = -Math.PI / 2; scene.add(floor);
const grid = new THREE.GridHelper(6, 12, 0x555555, 0x6a6c74); grid.position.y = 0.001; scene.add(grid);
const cam = new THREE.PerspectiveCamera(20, 1, 0.1, 50);
let mixer, clips, model, blade;
window.ready = new Promise((res) => new GLTFLoader().load('/model.glb', (g) => {
  model = g.scene; scene.add(model); clips = g.animations; mixer = new THREE.AnimationMixer(model);
  model.traverse((o) => { if (o.name === 'LightBlade') blade = o; if (o.isMesh) o.frustumCulled = false; });
  res(clips.map((c) => [c.name, c.duration]));
}));
function setView(v) {
  const el = 12 * Math.PI / 180;
  if (v === 'back') { cam.fov = 21; cam.position.set(0, 0.95 + 5.5 * Math.sin(el), -5.5 * Math.cos(el)); cam.lookAt(0, 0.85, 0.15); }
  else if (v === 'left') { cam.fov = 21; cam.position.set(5.6, 0.95, 0.15); cam.lookAt(0, 0.85, 0.15); }
  else if (v === 'right') { cam.fov = 21; cam.position.set(-5.6, 0.95, 0.15); cam.lookAt(0, 0.85, 0.15); }
  else if (v === 'front') { cam.fov = 21; cam.position.set(0, 1.0, 5.8); cam.lookAt(0, 0.85, 0.1); }
  else if (v === 'top') { cam.fov = 21; cam.position.set(0, 6.4, 0.2); cam.up.set(0, 0, 1); cam.lookAt(0, 0, 0.2); cam.up.set(0, 1, 0); }
  else { const [az, e] = v.split(':').map(parseFloat); const a = az * Math.PI / 180, ee = (e || 10) * Math.PI / 180;
    cam.fov = 21; cam.position.set(5.6 * Math.sin(a) * Math.cos(ee), 0.95 + 5.6 * Math.sin(ee), 5.6 * Math.cos(a) * Math.cos(ee)); cam.lookAt(0, 0.85, 0.1); }
  cam.updateProjectionMatrix();
}
window.sheet = (name, frames, views, tile, showBlade, strike) => {
  const clip = clips.find((c) => c.name === name);
  mixer.stopAllAction();
  const act = mixer.clipAction(clip); act.setLoop(THREE.LoopOnce); act.clampWhenFinished = true; act.play();
  if (blade) blade.visible = showBlade;
  renderer.setSize(tile, tile, false);
  const cv = document.createElement('canvas'); cv.width = tile * frames.length; cv.height = tile * views.length;
  const ctx = cv.getContext('2d'); ctx.font = '12px sans-serif';
  frames.forEach((f, i) => {
    mixer.setTime(Math.min(clip.duration - 1e-5, f / 60));
    views.forEach((v, r) => {
      setView(v); renderer.render(scene, cam);
      ctx.drawImage(renderer.domElement, i * tile, r * tile);
      if (r === 0) { ctx.fillStyle = (strike !== null && Math.abs(f - strike) < 0.51) ? '#ff3020' : '#111'; ctx.fillText(String(f), i * tile + 4, 13); }
    });
  });
  return cv.toDataURL('image/jpeg', 0.9);
};
</script></body></html>`;

const browser = await chromium.launch({
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
page.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
await page.route('**/*', (route) => {
  const u = new URL(route.request().url());
  if (u.pathname === '/') return route.fulfill({ body: HTML, contentType: 'text/html' });
  if (u.pathname === '/model.glb') return route.fulfill({ path: GLB, contentType: 'model/gltf-binary' });
  if (u.pathname.startsWith('/three/')) {
    const p = path.join(THREE_DIR, u.pathname.slice(7));
    if (fs.existsSync(p)) return route.fulfill({ path: p, contentType: 'text/javascript' });
  }
  return route.fulfill({ status: 404, body: '' });
});
await page.goto('http://sheet.local/');
const info = await page.evaluate(() => window.ready);
const want = args.clips ? args.clips.split(',') : info.map((c) => c[0]);
for (const [name, dur] of info) {
  if (!want.includes(name)) continue;
  const n = Math.round(dur * 60);
  const frames = [];
  const [f0, f1] = args.frames ? args.frames.split('-').map(Number) : [0, n];
  if (args.list) for (const f of args.list.split(',').map(Number)) { if (f <= n) frames.push(f); }
  else for (let f = f0; f <= Math.min(n, f1); f += EVERY) frames.push(f);
  const strike = ATTACK.includes(name) ? n * 0.25 : null;
  const url = await page.evaluate(([nm, fr, vw, tile, sb, st]) => window.sheet(nm, fr, vw, tile, sb, st), [name, frames, VIEWS, TILE, ATTACK.includes(name), strike]);
  const file = path.join(OUT, `${name}.jpg`);
  fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  console.log(file, `${frames.length} frames x ${VIEWS.length} views`);
}
await browser.close();
