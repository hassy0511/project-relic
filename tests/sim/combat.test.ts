import { describe, expect, it } from 'vitest';
import { makeGame, run, seconds } from './helpers';

describe('ロックオン', () => {
  it('カメラの前方にいる敵をロックオンし、離すと解除する', async () => {
    const g = await makeGame({
      markers: { e1: [0, 0, 10], e2: [0, 0, -10] },
      placement: { enemies: [{ type: 'sentry', at: 'e1' }, { type: 'sentry', at: 'e2' }] },
    });
    run(g, 2, { lockOn: true });
    expect(g.lockOn.target).toBe(g.enemies[0]);
    run(g, 2, { lockOn: false });
    expect(g.lockOn.target).toBeNull();
  });

  it('スティックを弾くと、画面の横にいる別の敵に切り替わる', async () => {
    const g = await makeGame({
      markers: { e1: [0, 0, 10], e2: [5, 0, 10] },
      placement: { enemies: [{ type: 'sentry', at: 'e1' }, { type: 'sentry', at: 'e2' }] },
    });
    // カメラは +Z を見ている。+X は画面の左
    run(g, 2, { lockOn: true });
    const first = g.lockOn.target;
    expect(first).toBe(g.enemies[0]);
    run(g, 1, { lockOn: true, switchTargetLeft: true });
    expect(g.lockOn.target).toBe(g.enemies[1]);
  });

  it('壁の向こうの敵はロックオンできない', async () => {
    const g = await makeGame({
      boxes: [{ center: [0, 2, 5], size: [10, 4, 1] }],
      markers: { e1: [0, 0, 10] },
      placement: { enemies: [{ type: 'sentry', at: 'e1' }] },
    });
    run(g, 2, { lockOn: true });
    expect(g.lockOn.target).toBeNull();
  });
});

describe('主武器と光刃', () => {
  it('ロックオンして撃ち続けると歩哨型を倒せる', async () => {
    const g = await makeGame({
      markers: { e1: [0, 0, 8] },
      placement: { enemies: [{ type: 'sentry', at: 'e1' }] },
    });
    g.godMode = true;
    run(g, seconds(6), { lockOn: true, fire: true });
    expect(g.enemies[0].alive).toBe(false);
    expect(g.pickups.length + g.cells).toBeGreaterThan(0);
  });

  it('光刃の 3 段コンボが当たる', async () => {
    const g = await makeGame({
      markers: { e1: [0, 0, 1.6] },
      placement: { enemies: [{ type: 'charger', at: 'e1' }] },
    });
    g.godMode = true;
    const hp0 = g.enemies[0].hp;
    run(g, seconds(1.5), (i) => ({ sword: i % 8 < 2 }));
    expect(g.enemies[0].hp).toBeLessThan(hp0 - 30);
  });
});

describe('敵の行動', () => {
  it('歩哨型は見つけると距離を保って撃ってくる', async () => {
    const g = await makeGame({
      markers: { e1: [0, 0, 6] },
      placement: { enemies: [{ type: 'sentry', at: 'e1' }] },
    });
    g.enemies[0].yaw = Math.PI; // プレイヤーの方を向かせる
    run(g, seconds(6), {});
    const d = g.enemies[0].pos.distanceTo(g.player.pos);
    expect(d).toBeGreaterThan(7);
    expect(g.player.hp).toBeLessThan(g.player.maxHp);
  });

  it('突撃型はダッシュで避けられると壁に激突して動けなくなる', async () => {
    const g = await makeGame({
      boxes: [{ center: [0, 2, -6], size: [20, 4, 1] }],
      markers: { e1: [0, 0, 10] },
      placement: { enemies: [{ type: 'charger', at: 'e1' }] },
    });
    const c = g.enemies[0];
    c.yaw = Math.PI;
    let stunned = false;
    run(g, seconds(8), () => {
      if (c.state === 'stunned') stunned = true;
      // 突進が来たら横へダッシュで避ける
      const dodge = c.state === 'attack' && c.pos.distanceTo(g.player.pos) < 5;
      return { moveX: dodge ? 1 : 0, dash: dodge };
    });
    expect(stunned).toBe(true);
  });

  it('同時に攻撃してくるのは最大 2 体', async () => {
    const g = await makeGame({
      markers: { e1: [-3, 0, 9], e2: [0, 0, 9], e3: [3, 0, 9], e4: [6, 0, 9] },
      placement: {
        enemies: [
          { type: 'sentry', at: 'e1' },
          { type: 'sentry', at: 'e2' },
          { type: 'sentry', at: 'e3' },
          { type: 'sentry', at: 'e4' },
        ],
      },
    });
    for (const e of g.enemies) e.yaw = Math.PI;
    g.godMode = true;
    let maxAttackers = 0;
    run(g, seconds(8), () => {
      maxAttackers = Math.max(maxAttackers, g.tokens.count);
      return {};
    });
    expect(maxAttackers).toBeLessThanOrEqual(2);
    expect(maxAttackers).toBeGreaterThan(0);
  });
});

describe('ブレイクドリルと仕掛け', () => {
  it('ドリルでひび割れた壁を壊せる。ドリルを持っていなければ壊せない', async () => {
    const make = () =>
      makeGame({
        markers: { wall: [0, 0, 1.4] },
        placement: { props: [{ type: 'breakable', id: 'w1', at: 'wall', size: [4, 4, 1], breaksWith: 'drill' }] },
      });
    const g1 = await make();
    run(g1, seconds(2), { special: true });
    expect(g1.breakables[0].broken).toBe(false);

    const g2 = await make();
    g2.giveItem('special.drill');
    run(g2, seconds(2), { special: true });
    expect(g2.breakables[0].broken).toBe(true);
    expect(g2.player.weaponEnergy).toBeLessThan(100);
  });

  it('宝箱を開けると中身が手に入る', async () => {
    const g = await makeGame({
      markers: { c: [0, 0, 1.2] },
      placement: { props: [{ type: 'chest', id: 'c1', at: 'c', contents: { cells: 200, item: 'chip.charge' } }] },
    });
    run(g, 2, {});
    expect(g.focus?.id).toBe('c1');
    run(g, 1, { jump: true });
    expect(g.cells).toBe(200);
    expect(g.hasItem('chip.charge')).toBe(true);
    expect(g.chargeType).toBe(true);
  });
});

describe('会話・イベント・セーブ', () => {
  it('トリガーに入るとイベントが走り、会話の途中でアイテムを受け取る', async () => {
    const g = await makeGame({
      markers: { t: [0, 0, 3] },
      placement: { triggers: [{ id: 't1', at: 't', size: [4, 2, 2], event: 'ev', once: true }] },
    });
    run(g, seconds(1), { moveY: 1 });
    expect(g.story.flags['x']).toBe(true);
    expect(g.story.dialogue?.text).toBe('やあ');
    // 決定ボタンで全文表示 → 次へ
    run(g, 2, { jump: true });
    run(g, 1, {});
    run(g, 2, { jump: true });
    run(g, 2, {});
    expect(g.story.dialogue).toBeNull();
    expect(g.hasItem('special.drill')).toBe(true);
  });

  it('セーブしたデータから同じ状態を復元できる', async () => {
    const g = await makeGame({});
    g.giveCells(123);
    g.giveItem('special.drill');
    run(g, seconds(0.5), { moveY: 1 });
    const save = g.toSave('test');
    const { Game } = await import('../../src/sim/game');
    const g2 = await Game.create({ ...g.init, save });
    expect(g2.cells).toBe(123);
    expect(g2.hasItem('special.drill')).toBe(true);
    expect(g2.player.pos.distanceTo(g.player.pos)).toBeLessThan(0.05);
  });

  it('同じ入力なら同じ結果になる（リプレイの前提）', async () => {
    const script = (i: number) => ({ moveY: 1, moveX: Math.sin(i / 20), fire: i % 30 < 10, lockOn: i > 60 });
    const opts = {
      markers: { e1: [0, 0, 12] as [number, number, number], e2: [4, 0, 14] as [number, number, number] },
      placement: { enemies: [{ type: 'sentry' as const, at: 'e1' }, { type: 'charger' as const, at: 'e2' }] },
    };
    const a = await makeGame(opts);
    const b = await makeGame(opts);
    run(a, seconds(5), script);
    run(b, seconds(5), script);
    expect(a.player.pos.toArray()).toEqual(b.player.pos.toArray());
    expect(a.enemies.map((e) => e.hp)).toEqual(b.enemies.map((e) => e.hp));
  });
});
