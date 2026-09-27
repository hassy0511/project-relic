import { Vector3 } from 'three';
import { DEG, dirToYaw, wrapAngle } from '../../core/math';
import type { Game } from '../game';
import { Enemy, type HitInfo } from './enemy';

/** 歩哨型：距離を保って 3 連射する基本の敵。弱点は背中の核 */
export class Sentry extends Enemy {
  readonly kind = 'sentry';
  private cooldown = 1;
  private shotsLeft = 0;
  private shotTimer = 0;
  private strafeDir = 1;
  private strafeTimer = 0;

  constructor(game: Game, spawn: Vector3, yaw: number) {
    const c = game.tuning.enemies.sentry;
    super(game, spawn, yaw, 0.45, 1.1, c.hp, c.poise);
  }

  protected override damageMultiplier(from: Vector3): { mult: number; kind: 'normal' | 'weak' | 'armor' } {
    // 背後（向きから 110° 以上）から当てると弱点
    const rel = Math.abs(wrapAngle(dirToYaw(from.x - this.pos.x, from.z - this.pos.z) - this.yaw));
    return rel > 110 * DEG ? { mult: 1.5, kind: 'weak' } : { mult: 1, kind: 'normal' };
  }

  protected think(dt: number): void {
    const g = this.game;
    const c = g.tuning.enemies.sentry;
    const p = g.player;
    this.cooldown -= dt;

    switch (this.state) {
      case 'idle':
        this.wander(dt, c.moveSpeed * 0.5);
        if (this.canSeePlayer(c.sight)) this.becomeAlert();
        break;
      case 'alert':
        this.brake(dt);
        this.faceTowards(p.pos, 360, dt);
        if (this.stateTime > 0.6) this.setState('engage');
        break;
      case 'engage': {
        const seen = this.trackSight(dt, c.sight);
        if (this.state !== 'engage') break;
        this.faceTowards(p.pos, 300, dt);
        const d = this.distToPlayer();
        const toP = new Vector3(p.pos.x - this.pos.x, 0, p.pos.z - this.pos.z).normalize();
        this.strafeTimer -= dt;
        if (this.strafeTimer <= 0) {
          this.strafeTimer = g.rng.range(1.5, 3);
          this.strafeDir = g.rng.chance(0.5) ? 1 : -1;
        }
        const [near, far] = c.keepDistance;
        if (d < near) this.moveDir(toP.clone().multiplyScalar(-1), c.moveSpeed, dt);
        else if (d > far || !seen) this.moveDir(toP, c.moveSpeed, dt);
        else this.moveDir(new Vector3(-toP.z, 0, toP.x).multiplyScalar(this.strafeDir), c.moveSpeed * 0.6, dt);
        if (seen && this.cooldown <= 0 && d <= far + 4 && g.tokens.request(this)) this.setState('windup');
        break;
      }
      case 'windup':
        this.brake(dt, 30);
        this.faceTowards(p.pos, 360, dt);
        if (this.stateTime >= c.windup) {
          this.setState('attack');
          this.shotsLeft = c.burstCount;
          this.shotTimer = 0;
        }
        break;
      case 'attack':
        this.brake(dt, 30);
        this.faceTowards(p.pos, 180, dt);
        this.shotTimer -= dt;
        if (this.shotTimer <= 0 && this.shotsLeft > 0) {
          this.shotsLeft--;
          this.shotTimer = c.burstInterval;
          const muzzle = this.center().addScaledVector(this.forward(), this.radius + 0.1);
          g.spawnEnemyShot(muzzle, this.aimAtPlayer(muzzle), c.shotSpeed, c.shotDamage);
        }
        if (this.shotsLeft <= 0 && this.shotTimer <= 0) {
          g.tokens.release(this);
          this.cooldown = c.cooldown + g.rng.range(0, 0.6);
          this.setState('engage');
        }
        break;
      default:
        this.setState('engage');
    }
  }

  override receive(amount: number, from: Vector3, info: HitInfo) {
    const r = super.receive(amount, from, info);
    if (!r.killed && this.state === 'stagger') this.shotsLeft = 0;
    return r;
  }
}
