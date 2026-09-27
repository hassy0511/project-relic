import { describe, expect, it } from 'vitest';
import { makeGame, run, seconds } from './helpers';

/**
 * 手触りの数値テスト。docs/design/20_ゲームシステム設計.md 4 章と
 * docs/design/30_レベルデザイン設計.md 1.2 の値が守られていることを確かめる。
 * 調整した値が知らないうちに壊れるのを防ぐ。
 */
describe('プレイヤーの移動の手触り', () => {
  it('走る速さは 7m/s に達する', async () => {
    const g = await makeGame({});
    run(g, seconds(1), { moveY: 1 });
    expect(g.player.speed).toBeCloseTo(7, 1);
  });

  it('ジャンプの最高点は約 2.2m', async () => {
    const g = await makeGame({});
    run(g, 5, {});
    let maxY = 0;
    run(g, seconds(1.2), (i) => {
      maxY = Math.max(maxY, g.player.pos.y);
      return { jump: i < seconds(0.6) };
    });
    expect(maxY).toBeGreaterThan(2.1);
    expect(maxY).toBeLessThan(2.3);
  });

  it('ボタンをすぐ離すと低いジャンプになる（約 0.8m）', async () => {
    const g = await makeGame({});
    run(g, 5, {});
    let maxY = 0;
    run(g, seconds(1), (i) => {
      maxY = Math.max(maxY, g.player.pos.y);
      return { jump: i < 1 };
    });
    expect(maxY).toBeGreaterThan(0.7);
    expect(maxY).toBeLessThan(1.05);
  });

  it('ダッシュは約 3.3m 進む', async () => {
    const g = await makeGame({});
    run(g, 5, {});
    const z0 = g.player.pos.z;
    run(g, seconds(0.22), (i) => ({ dash: i === 0 }));
    const d = Math.abs(g.player.pos.z - z0);
    expect(d).toBeGreaterThan(3.0);
    expect(d).toBeLessThan(3.6);
  });

  it('1.8m の段には登れ、2.4m の段には登れない', async () => {
    for (const [h, reachable] of [[1.8, true], [2.4, false]] as const) {
      const g = await makeGame({ boxes: [{ center: [0, h / 2, 6], size: [6, h, 4] }] });
      run(g, 5, {});
      // 段の手前まで走り、跳んで前へ進み続ける
      let onTop = false;
      run(g, seconds(1.6), (i) => {
        if (g.player.grounded && g.player.pos.y > h - 0.1) onTop = true;
        return { moveY: 1, jump: i > seconds(0.35) && i < seconds(0.9) };
      });
      expect(onTop, `段の高さ ${h}m`).toBe(reachable);
    }
  });

  it('走りジャンプで 4.5m の溝を越えられ、ダッシュジャンプで 7m の溝を越えられる', async () => {
    // 手前の足場は z<0、溝のあと向こう側の足場。床は溝の下に落ちる
    const make = (gap: number) =>
      makeGame({
        boxes: [
          { center: [0, 5, -10], size: [6, 10, 20] },
          { center: [0, 5, gap + 10], size: [6, 10, 20] },
        ],
        markers: { start: [0, 10, -6] },
      });
    // 通常のジャンプ
    {
      const g = await make(4.5);
      run(g, 5, {});
      run(g, seconds(2.5), (i) => {
        const nearEdge = g.player.pos.z > -0.5;
        return { moveY: 1, jump: nearEdge && i < seconds(2.5) };
      });
      expect(g.player.pos.y).toBeGreaterThan(9.5);
      expect(g.player.pos.z).toBeGreaterThan(4.5);
    }
    // ダッシュジャンプ
    {
      const g = await make(7);
      run(g, 5, {});
      let dashed = false;
      run(g, seconds(2.5), () => {
        const z = g.player.pos.z;
        const dash = !dashed && z > -3.6;
        if (dash) dashed = true;
        return { moveY: 1, dash, jump: z > -0.6 };
      });
      expect(g.player.pos.y).toBeGreaterThan(9.5);
      expect(g.player.pos.z).toBeGreaterThan(7);
    }
  });
});
