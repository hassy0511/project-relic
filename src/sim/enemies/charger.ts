import { Vector3 } from 'three';
import { horizontalDistance } from '../../core/math';
import { Layer } from '../../physics/physics';
import type { Game } from '../game';
import { Enemy } from './enemy';

/** 突撃型：溜めてから一直線に突進する。壁に激突すると動けなくなり、側面の核が露出する */
export class Charger extends Enemy {
  readonly kind = 'charger';
  private cooldown = 1.5;
  private chargeDir = new Vector3();
  private hitPlayer = false;

  constructor(game: Game, spawn: Vector3, yaw: number) {
    const c = game.tuning.enemies.charger;
    super(game, spawn, yaw, 0.7, 1.2, c.hp, c.poise);
  }

  /** 壁に激突して動けない間は、全身が弱点になる */
  protected override damageMultiplier(): { mult: number; kind: 'normal' | 'weak' | 'armor' } {
    return this.state === 'stunned' ? { mult: 1.5, kind: 'weak' } : { mult: 1, kind: 'normal' };
  }

  protected think(dt: number): void {
    const g = this.game;
    const c = g.tuning.enemies.charger;
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
        this.faceTowards(p.pos, 240, dt);
        const d = this.distToPlayer();
        const toP = new Vector3(p.pos.x - this.pos.x, 0, p.pos.z - this.pos.z).normalize();
        if (d > 10 || !seen) this.moveDir(toP, c.moveSpeed, dt);
        else if (d < 5) this.moveDir(toP.clone().multiplyScalar(-1), c.moveSpeed * 0.7, dt);
        else this.brake(dt);
        if (seen && this.cooldown <= 0 && d < 16 && g.tokens.request(this)) this.setState('windup');
        break;
      }
      case 'windup':
        // 予備動作：プレイヤーの方を向いて力を溜める。最後の瞬間の向きで突進する
        this.brake(dt, 30);
        this.faceTowards(p.pos, 400, dt);
        if (this.stateTime >= c.windup) {
          this.chargeDir.copy(this.forward());
          this.hitPlayer = false;
          this.setState('attack');
          g.events.push({ type: 'sfx', id: 'charge', x: this.pos.x, y: this.pos.y, z: this.pos.z });
        }
        break;
      case 'attack': {
        this.vel.x = this.chargeDir.x * c.chargeSpeed;
        this.vel.z = this.chargeDir.z * c.chargeSpeed;
        if (!this.hitPlayer && horizontalDistance(this.pos, p.pos) < this.radius + 0.6 && Math.abs(p.pos.y - this.pos.y) < 1.2) {
          this.hitPlayer = p.takeDamage(c.damage, this.pos, true) || this.hitPlayer;
          if (this.hitPlayer) {
            this.finishCharge(false);
            break;
          }
        }
        if (this.stateTime >= c.chargeTime) this.finishCharge(false);
        break;
      }
      case 'stunned':
        this.brake(dt, 40);
        if (this.stateTime >= c.stunTime) this.setState('recover');
        break;
      case 'recover':
        this.brake(dt, 30);
        if (this.stateTime >= c.recover) this.setState('engage');
        break;
      default:
        this.setState('engage');
    }
  }

  private finishCharge(wall: boolean): void {
    const g = this.game;
    g.tokens.release(this);
    this.cooldown = 2 + g.rng.range(0, 1);
    this.vel.x = 0;
    this.vel.z = 0;
    if (wall) {
      this.setState('stunned');
      g.events.push({ type: 'sfx', id: 'crash', x: this.pos.x, y: this.pos.y, z: this.pos.z });
      g.events.push({ type: 'shake', strength: 0.3 });
    } else {
      this.setState('recover');
    }
  }

  /** 突進中はプレイヤーをすり抜ける（ダッシュで避けられたときに、プレイヤーを壁と誤認しないため） */
  protected override moveFilter(): number {
    const f = super.moveFilter();
    return this.state === 'attack' ? f & ~Layer.Player : f;
  }

  protected override integrate(dt: number): number {
    const blocked = super.integrate(dt);
    // 突進中に大きく止められたら、壁への激突とみなす
    if (this.state === 'attack' && this.stateTime > 0.1 && blocked > 0.6) this.finishCharge(true);
    return blocked;
  }
}
