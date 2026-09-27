import { Vector3 } from 'three';
import { loadTuning, type Tuning } from '../../src/content/tuning';
import { boxesToTrimesh } from '../../src/physics/physics';
import type { AreaGeometry, Placement } from '../../src/sim/area';
import { DT } from '../../src/sim/constants';
import { Game } from '../../src/sim/game';
import { emptyInput, type InputFrame } from '../../src/sim/inputFrame';

export interface Box {
  center: [number, number, number];
  size: [number, number, number];
}

/** 箱の地形と目印から、テスト用のゲームを作る */
export async function makeGame(opts: {
  boxes?: Box[];
  markers?: Record<string, [number, number, number]>;
  placement?: Partial<Placement>;
  tuning?: Tuning;
}): Promise<Game> {
  const boxes: Box[] = [{ center: [0, -0.5, 0], size: [200, 1, 200] }, ...(opts.boxes ?? [])];
  const mesh = boxesToTrimesh(
    boxes.map((b) => ({ center: new Vector3(...b.center), half: new Vector3(...b.size).multiplyScalar(0.5) })),
  );
  const markers: AreaGeometry['markers'] = { start: { pos: [0, 0, 0], yaw: 0 } };
  for (const [k, v] of Object.entries(opts.markers ?? {})) markers[k] = { pos: v, yaw: 0 };
  const placement: Placement = {
    id: 'test',
    name: 'test',
    model: '',
    playerStart: 'start',
    objective: '',
    enemies: [],
    props: [],
    triggers: [],
    checkpoints: [],
    ...opts.placement,
  };
  return Game.create({
    geometry: { meshes: [mesh], markers },
    placement,
    tuning: opts.tuning ?? loadTuning(),
    dialogues: { hello: { lines: [{ who: 'a', face: 'normal', text: 'やあ' }, { action: 'give_item', item: 'special.drill' }] } },
    events: { ev: { steps: [{ flag: 'x' }, { say: 'hello' }] } },
    seed: 1,
  });
}

/** 入力を与えて n 刻み進める。各刻みで入力を作る関数を渡せる */
export function run(g: Game, ticks: number, input: Partial<InputFrame> | ((i: number) => Partial<InputFrame>)): void {
  for (let i = 0; i < ticks; i++) {
    const p = typeof input === 'function' ? input(i) : input;
    g.step({ ...emptyInput(), ...p });
  }
}

export function seconds(s: number): number {
  return Math.round(s / DT);
}
