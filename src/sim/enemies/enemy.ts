import { Vector3 } from 'three';
import { DEG, approachAngle, dirToYaw, horizontalDistance, wrapAngle, yawToDir } from '../../core/math';
import { Layer, type CharacterBody } from '../../physics/physics';
import type { Game } from '../game';
import { PLAYER_CHEST } from '../constants';

export type EnemyState = 'idle' | 'alert' | 'engage' | 'windup' | 'attack' | 'recover' | 'stunned' | 'stagger' | 'dead';

export interface HitInfo {
  melee?: boolean;
  armorBreak?: boolean;
  launch?: boolean;
}

/** 番機の共通部分。型ごとの行動はサブクラスで書く */
export abstract class Enemy {
  abstract readonly kind: string;
  readonly pos = new Vector3();
  readonly home = new Vector3();
  readonly vel = new Vector3();
  yaw = 0;
  hp: number;
  maxHp: number;
  poise: number;
  maxPoise: number;
  private poiseTimer = 0;
  state: EnemyState = 'idle';
  stateTime = 0;
  alive = true;
  /** 被弾の瞬間の光（view 用） */
  flash = 0;
  /** 撃破からの経過時間（view の演出用） */
  deadTime = 0;
  body: CharacterBody;
  private grounded = true;
  private noSight = 0;
  protected wanderTarget = new Vector3();

  constructor(
    protected readonly game: Game,
    spawn: Vector3,
    yaw: number,
    readonly radius: number,
    readonly height: number,
    hp: number,
    poise: number,
  ) {
    this.pos.copy(spawn);
    this.home.copy(spawn);
    this.wanderTarget.copy(spawn);
    this.yaw = yaw;
    this.hp = this.maxHp = hp;
    this.poise = this.maxPoise = poise;
    this.body = game.physics.createCharacter(spawn, radius, height, Layer.Enemy, Layer.Terrain | Layer.Breakable | Layer.Player | Layer.Enemy);
    game.physics.setOwner(this.body.collider, this);
  }

  center(out = new Vector3()): Vector3 {
    return out.set(this.pos.x, this.pos.y + this.height * 0.5, this.pos.z);
  }

  setState(s: EnemyState): void {
    if (this.state === s) return;
    this.state = s;
    this.stateTime = 0;
  }

  /** 攻撃の予備動作中か（view で光らせる） */
  get telegraphing(): boolean {
    return this.state === 'windup';
  }

  /** 見つかった時の「！」を出している間 */
  get alerting(): boolean {
    return this.state === 'alert';
  }

  update(dt: number): void {
    if (!this.alive) {
      this.deadTime += dt;
      return;
    }
    this.stateTime += dt;
    this.flash = Math.max(0, this.flash - dt * 4);
    this.poiseTimer += dt;
    if (this.poiseTimer > 2) this.poise = this.maxPoise;

    if (this.state === 'stagger') {
      this.brake(dt, 30);
      if (this.stateTime > 0.6) this.setState('engage');
    } else {
      this.think(dt);
    }
    this.integrate(dt);
  }

  protected abstract think(dt: number): void;

  /** 被弾の倍率（弱点など）。型ごとに上書きする */
  protected damageMultiplier(from: Vector3, _info: HitInfo): { mult: number; kind: 'normal' | 'weak' | 'armor' } {
    void from;
    return { mult: 1, kind: 'normal' };
  }

  /** ダメージを受ける。倒れたら true */
  receive(amount: number, from: Vector3, info: HitInfo): { killed: boolean; kind: 'normal' | 'weak' | 'armor'; dealt: number } {
    const { mult, kind } = this.damageMultiplier(from, info);
    const dealt = amount * mult;
    this.hp -= dealt;
    this.flash = 1;
    this.poiseTimer = 0;
    this.poise -= dealt;
    if (this.state === 'idle') this.becomeAlert();
    if (this.hp <= 0) {
      this.alive = false;
      this.setState('dead');
      this.game.physics.removeCollider(this.body.collider);
      this.game.tokens.release(this);
      return { killed: true, kind, dealt };
    }
    if (this.poise <= 0 && this.state !== 'stunned') {
      this.poise = this.maxPoise;
      this.game.tokens.release(this);
      this.setState('stagger');
      const away = new Vector3(this.pos.x - from.x, 0, this.pos.z - from.z).normalize().multiplyScalar(info.melee ? 3 : 1.5);
      this.vel.x = away.x;
      this.vel.z = away.z;
      if (info.launch) this.vel.y = 6;
    }
    return { killed: false, kind, dealt };
  }

  // ------------------------------------------------------------ 知覚

  protected distToPlayer(): number {
    return horizontalDistance(this.pos, this.game.player.pos);
  }

  protected canSeePlayer(sight: number): boolean {
    const p = this.game.player;
    if (p.dead) return false;
    const d = this.distToPlayer();
    if (d > sight) return false;
    const rel = Math.abs(wrapAngle(dirToYaw(p.pos.x - this.pos.x, p.pos.z - this.pos.z) - this.yaw));
    if (this.state === 'idle' && rel > 60 * DEG) return false;
    return this.lineOfSight();
  }

  protected lineOfSight(): boolean {
    const from = this.center();
    const to = this.game.player.chest();
    const dir = new Vector3().subVectors(to, from);
    const len = dir.length();
    if (len < 0.01) return true;
    return this.game.physics.raycast(from, dir.divideScalar(len), len, Layer.Terrain | Layer.Breakable) === null;
  }

  becomeAlert(): void {
    if (this.state === 'idle') {
      this.setState('alert');
      this.game.events.push({ type: 'sfx', id: 'alert', x: this.pos.x, y: this.pos.y, z: this.pos.z });
    }
  }

  /** 交戦中に見失ったら、しばらく探してから持ち場に戻る */
  protected trackSight(dt: number, sight: number): boolean {
    if (this.canSeePlayer(sight * 1.3)) {
      this.noSight = 0;
      return true;
    }
    this.noSight += dt;
    if (this.noSight > 5) {
      this.noSight = 0;
      this.game.tokens.release(this);
      this.setState('idle');
    }
    return false;
  }

  // ------------------------------------------------------------ 移動

  protected faceTowards(p: Vector3, degPerSec: number, dt: number): void {
    this.yaw = approachAngle(this.yaw, dirToYaw(p.x - this.pos.x, p.z - this.pos.z), degPerSec * DEG * dt);
  }

  protected moveDir(dir: Vector3, speed: number, dt: number, accel = 20): void {
    const tx = dir.x * speed;
    const tz = dir.z * speed;
    const dx = tx - this.vel.x;
    const dz = tz - this.vel.z;
    const len = Math.hypot(dx, dz);
    const step = accel * dt;
    if (len <= step) {
      this.vel.x = tx;
      this.vel.z = tz;
    } else {
      this.vel.x += (dx / len) * step;
      this.vel.z += (dz / len) * step;
    }
  }

  protected brake(dt: number, decel = 20): void {
    this.moveDir(new Vector3(), 0, dt, decel);
  }

  protected wander(dt: number, speed: number): void {
    if (horizontalDistance(this.pos, this.wanderTarget) < 0.5 || this.stateTime > 6) {
      const r = this.game.rng;
      this.wanderTarget.set(this.home.x + r.range(-3, 3), this.home.y, this.home.z + r.range(-3, 3));
      this.stateTime = 0;
    }
    if (this.stateTime < 1.5) {
      this.brake(dt);
      return;
    }
    const dir = new Vector3(this.wanderTarget.x - this.pos.x, 0, this.wanderTarget.z - this.pos.z).normalize();
    this.faceTowards(this.wanderTarget, 180, dt);
    this.moveDir(dir, speed, dt);
  }

  /** 実際の移動。壁にぶつかった割合（0〜1）を返す */
  protected integrate(dt: number): number {
    if (!(this.grounded && this.vel.y <= 0)) this.vel.y = Math.max(-25, this.vel.y - 22 * dt);
    const want = new Vector3(this.vel.x * dt, this.grounded && this.vel.y <= 0 ? -0.05 : this.vel.y * dt, this.vel.z * dt);
    const res = this.game.physics.moveCharacter(this.body, want, this.moveFilter(), this.grounded && this.vel.y <= 0);
    this.game.physics.feetOf(this.body, this.pos);
    this.grounded = res.grounded && this.vel.y <= 0.01;
    if (this.grounded) this.vel.y = 0;
    const wantH = Math.hypot(want.x, want.z);
    if (wantH < 1e-4) return 0;
    return 1 - Math.hypot(res.moved.x, res.moved.z) / wantH;
  }

  /** 移動でぶつかる相手のレイヤー */
  protected moveFilter(): number {
    return Layer.Terrain | Layer.Breakable | Layer.Player | Layer.Enemy;
  }

  /** プレイヤーの胸へ向かう単位ベクトル */
  protected aimAtPlayer(from: Vector3): Vector3 {
    const p = this.game.player;
    return new Vector3(p.pos.x, p.pos.y + PLAYER_CHEST, p.pos.z).sub(from).normalize();
  }

  protected forward(): Vector3 {
    return yawToDir(this.yaw);
  }
}

/** 同時に攻撃してくる敵の数を制限する（死角から理不尽に殴られないように） */
export class AttackTokens {
  private holders = new Set<Enemy>();

  constructor(private max: () => number) {}

  request(e: Enemy): boolean {
    if (this.holders.has(e)) return true;
    if (this.holders.size >= this.max()) return false;
    this.holders.add(e);
    return true;
  }

  release(e: Enemy): void {
    this.holders.delete(e);
  }

  get count(): number {
    return this.holders.size;
  }
}
