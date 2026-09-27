import { Vector3 } from 'three';
import { DEG, dirToYaw, wrapAngle } from '../core/math';
import { Layer } from '../physics/physics';
import type { Enemy } from './enemies/enemy';
import type { Game } from './game';
import { PLAYER_CHEST } from './constants';

/** ロックオンの状態と、対象の選び方（docs/design/20_ゲームシステム設計.md 5 章） */
export class LockOn {
  target: Enemy | null = null;
  private sightLost = 0;
  private scanTime = 0;
  /** 解析済みの敵の種類（弱点を表示できる） */
  readonly scanned = new Set<string>();

  constructor(private readonly game: Game) {}

  get active(): boolean {
    return this.target !== null;
  }

  update(dt: number): void {
    const g = this.game;
    const input = g.input;
    const cfg = g.tuning.lockOn;

    if (!g.edges.down('lockOn')) {
      this.release();
      return;
    }
    if (g.edges.pressed('lockOn')) {
      this.target = this.pickBest(null);
      if (!this.target) g.cam.requestRecenter();
    }
    if (!this.target) return;

    // 対象を失う条件：倒した、離れすぎた、見えない時間が続いた
    const t = this.target;
    const dist = t.center().distanceTo(g.player.chest());
    if (!t.alive || dist > cfg.loseRange) {
      this.target = t.alive ? null : this.pickBest(null);
      this.scanTime = 0;
      return;
    }
    if (this.hasLineOfSight(t)) this.sightLost = 0;
    else this.sightLost += dt;
    if (this.sightLost > cfg.loseSightTime) {
      this.release();
      return;
    }

    if (input.switchTargetLeft || input.switchTargetRight) {
      const next = this.pickSide(input.switchTargetRight ? 1 : -1);
      if (next) {
        this.target = next;
        this.scanTime = 0;
      }
    }

    this.scanTime += dt;
    if (this.scanTime >= cfg.scanTime) this.scanned.add(this.target.kind);
  }

  release(): void {
    this.target = null;
    this.sightLost = 0;
    this.scanTime = 0;
  }

  /** 解析の進み具合（0〜1） */
  get scanProgress(): number {
    if (!this.target) return 0;
    if (this.scanned.has(this.target.kind)) return 1;
    return Math.min(1, this.scanTime / this.game.tuning.lockOn.scanTime);
  }

  /** 候補の敵（射程内で、視線が通っていて、カメラの前方にいる） */
  candidates(): Enemy[] {
    const g = this.game;
    const cfg = g.tuning.lockOn;
    const chest = g.player.chest();
    return g.enemies.filter((e) => {
      if (!e.alive) return false;
      const c = e.center();
      if (c.distanceTo(chest) > cfg.range) return false;
      const rel = Math.abs(wrapAngle(dirToYaw(c.x - chest.x, c.z - chest.z) - g.cam.yaw));
      if (rel > 75 * DEG) return false;
      return this.hasLineOfSight(e);
    });
  }

  private pickBest(exclude: Enemy | null): Enemy | null {
    const g = this.game;
    const cfg = g.tuning.lockOn;
    const chest = g.player.chest();
    let best: Enemy | null = null;
    let bestScore = -Infinity;
    for (const e of this.candidates()) {
      if (e === exclude) continue;
      const c = e.center();
      const rel = Math.abs(wrapAngle(dirToYaw(c.x - chest.x, c.z - chest.z) - g.cam.yaw));
      const score = cfg.centerWeight * (1 - rel / (75 * DEG)) + cfg.distanceWeight * (1 - c.distanceTo(chest) / cfg.range);
      if (score > bestScore) {
        bestScore = score;
        best = e;
      }
    }
    return best;
  }

  /** 画面上で今の対象の右（side=1）または左（side=-1）にいる、最も近い敵 */
  private pickSide(side: number): Enemy | null {
    const g = this.game;
    const chest = g.player.chest();
    const cur = this.target;
    if (!cur) return null;
    const cc = cur.center();
    const curYaw = dirToYaw(cc.x - chest.x, cc.z - chest.z);
    let best: Enemy | null = null;
    let bestDelta = Infinity;
    for (const e of this.candidates()) {
      if (e === cur) continue;
      const c = e.center();
      // yaw が小さくなる方向が画面の右
      const delta = -wrapAngle(dirToYaw(c.x - chest.x, c.z - chest.z) - curYaw) * side;
      if (delta > 0 && delta < bestDelta) {
        bestDelta = delta;
        best = e;
      }
    }
    return best;
  }

  private hasLineOfSight(e: Enemy): boolean {
    const g = this.game;
    const from = g.player.pos.clone().setY(g.player.pos.y + PLAYER_CHEST);
    const to = e.center();
    const dir = new Vector3().subVectors(to, from);
    const len = dir.length();
    if (len < 0.01) return true;
    dir.divideScalar(len);
    const hit = g.physics.raycast(from, dir, len, Layer.Terrain | Layer.Breakable);
    return hit === null;
  }
}
