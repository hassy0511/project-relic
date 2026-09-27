// 見た目の確認ページ（lookdev.html）を自動で撮影する。
//   node tools/lookdev_capture.mjs <出力フォルダ> <撮影リスト.json>
// 撮影リスト：[{ "name": "front_soft", "params": { "view": "front", "shade": "soft" }, "w": 640, "h": 800 }, ...]
// 開発サーバーを起動して撮り、終わったら止める。
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from '@playwright/test';

const [outDir, listPath] = process.argv.slice(2);
if (!outDir || !listPath) {
  console.error('使い方: node tools/lookdev_capture.mjs <出力フォルダ> <撮影リスト.json>');
  process.exit(1);
}
const shots = JSON.parse(readFileSync(listPath, 'utf8'));
mkdirSync(outDir, { recursive: true });

const port = 5179;
const server = spawn('node_modules/.bin/vite', ['--port', String(port), '--strictPort'], {
  stdio: ['ignore', 'pipe', 'pipe'],
  detached: true,
});
await new Promise((resolve, reject) => {
  const t = setTimeout(() => reject(new Error('開発サーバーが起動しない')), 60000);
  server.stdout.on('data', (d) => {
    if (String(d).includes('Local')) {
      clearTimeout(t);
      resolve();
    }
  });
});

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
try {
  const page = await browser.newPage({ viewport: { width: 640, height: 800 } });
  page.on('console', (m) => {
    if (m.type() === 'error') console.log('console:', m.text());
  });
  await page.goto(`http://localhost:${port}/lookdev.html?hud=0`);
  await page.waitForFunction(() => window.__lookdev?.ready, null, { timeout: 120000 });
  for (const s of shots) {
    await page.setViewportSize({ width: s.w ?? 640, height: s.h ?? 800 });
    await page.evaluate((p) => window.__lookdev.set({ hud: false, t: 0, ...p }, true), s.params);
    // 数フレーム描かせてから撮る（影と姿勢の反映）
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(r)))));
    await page.screenshot({ path: join(outDir, `${s.name}.png`) });
    console.log('shot', s.name);
  }
  const stats = await page.evaluate(() => window.__lookdev.stats());
  console.log('stats', JSON.stringify(stats));
} finally {
  await browser.close();
  // サーバーとその子プロセスをまとめて止める
  try {
    process.kill(-server.pid, 'SIGTERM');
  } catch {
    server.kill();
  }
}
process.exit(0);
