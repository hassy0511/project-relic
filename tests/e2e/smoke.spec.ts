import { expect, test, type Page } from '@playwright/test';

/**
 * ブラウザでの通し確認。起動 → タイトル → はじめから → 会話 → 戦闘 → ドリル → 撮影。
 * コンソールのエラーがないこと、ゲームが進んでいることを確かめる。撮影した画像は目視で確認する。
 * （ヘッドレスは描画が遅くキー入力のタイミングが不安定なため、会話や移動は一部を直接操作する。
 *  ゲームの仕組みそのものは tests/sim で確かめている）
 */
test('起動してタイトルからゲームを始められる', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });

  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/');
  await expect(page.getByText('はじめから')).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: 'test-results/shots/01-title.png' });

  await page.getByText('はじめから').click();
  await waitTicks(page, 30);
  await page.screenshot({ path: 'test-results/shots/02-start.png' });

  // キーボードで少し歩く
  await page.keyboard.down('KeyW');
  await waitTicks(page, 40);
  await page.keyboard.up('KeyW');
  const z = await page.evaluate(() => (window as any).__arkwalker.game.player.pos.z);
  expect(z).toBeGreaterThan(-5.5);

  // ヤーナとの会話
  await page.evaluate(() => (window as any).__arkwalker.game.story.startDialogue('mvp.yana'));
  await waitTicks(page, 40);
  await page.screenshot({ path: 'test-results/shots/03-dialogue.png' });
  await page.evaluate(() => {
    const story = (window as any).__arkwalker.game.story;
    for (let i = 0; i < 40 && story.dialogue; i++) story.confirm();
  });
  expect(await page.evaluate(() => (window as any).__arkwalker.game.hasItem('special.drill'))).toBe(true);

  // 戦闘の部屋へ
  await page.evaluate(() => {
    const g = (window as any).__arkwalker.game;
    g.player.teleport(g.player.pos.clone().set(0, 0, 47), 0);
    g.cam.yaw = 0;
    g.godMode = true;
  });
  await waitTicks(page, 60);
  await page.evaluate(() => {
    const story = (window as any).__arkwalker.game.story;
    for (let i = 0; i < 20 && story.dialogue; i++) story.confirm();
  });
  await page.mouse.click(640, 360); // ポインターロック
  await page.mouse.down({ button: 'right' });
  await page.mouse.down({ button: 'left' });
  await waitTicks(page, 45);
  await page.screenshot({ path: 'test-results/shots/04-combat.png' });
  await page.mouse.up({ button: 'left' });
  await page.mouse.up({ button: 'right' });

  // ひび割れた壁の前でドリル
  await page.evaluate(() => {
    const g = (window as any).__arkwalker.game;
    for (const e of g.enemies) e.hp = 0.01;
    g.player.teleport(g.player.pos.clone().set(0, 0, 62.6), 0);
    g.cam.yaw = 0;
  });
  await waitTicks(page, 10);
  await page.keyboard.down('KeyQ');
  await waitTicks(page, 30);
  await page.screenshot({ path: 'test-results/shots/05-drill.png' });
  await waitTicks(page, 60);
  await page.keyboard.up('KeyQ');

  const info = await page.evaluate(() => {
    const a = (window as any).__arkwalker;
    return { tick: a.game.tick, broken: a.game.breakables[0].broken, errors: a.errors };
  });
  expect(info.tick).toBeGreaterThan(200);
  expect(info.broken).toBe(true);
  expect(info.errors).toEqual([]);
  expect(errors).toEqual([]);
});

async function waitTicks(page: Page, n: number): Promise<void> {
  const start = await page.evaluate(() => (window as any).__arkwalker.game?.tick ?? 0);
  await page.waitForFunction((target) => ((window as any).__arkwalker.game?.tick ?? 0) >= target, start + n, { timeout: 60_000 });
}
