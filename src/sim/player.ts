import { Vector3 } from 'three';
import { DEG, approach, approachAngle, clamp, dirToYaw, horizontalDistance, yawToDir } from '../core/math';
import { Layer, type CharacterBody } from '../physics/physics';
import { KILL_Y, PLAYER_CHEST, PLAYER_HEIGHT, PLAYER_RADIUS } from './constants';
import type { Game } from './game';

export type SwordMove = 'combo1' | 'combo2' | 'combo3' | 'air' | 'dash' | 'lunge' | 'charge';

interface SwordAttack {
  move: SwordMove;
  time: number;
  duration: number;
  activeFrom: number;
  activeTo: number;
  damage: number;
  hit: Set<unknown>;
  /** コンボの次の段の先行入力 */
  buffered: boolean;
}

export type PlayerAnim =
  | 'idle' | 'run' | 'jump' | 'fall' | 'dash' | 'hurt' | 'dead' | 'drill'
  | 'combo1' | 'combo2' | 'combo3' | 'air' | 'lunge' | 'charge';

export class Player {
  readonly pos = new Vector3();
  readonly vel = new Vector3();
  yaw = 0;
  grounded = true;
  body: CharacterBody;

  hp: number;
  maxHp: number;
  invuln = 0;
  hurtTime = 0;
  dead = false;
  deadTime = 0;
  heals = 2;

  private coyote = 0;
  private jumpBuffer = 0;
  private jumping = false;
  dashTime = 0;
  private dashCooldown = 0;
  private dashDir = new Vector3();
  private dashJump = false;
  private safePos = new Vector3();

  attack: SwordAttack | null = null;
  swordHold = 0;
  private airSlashes = 0;

  gunCooldown = 0;
  gunCharge = 0;
  /** 撃っている、または構えている（上半身を銃の構えにする） */
  aiming = 0;

  drilling = false;
  private drillTick = 0;
  weaponEnergy = 100;

  constructor(private readonly game: Game, start: Vector3, yaw: number) {
    const t = game.tuning;
    this.maxHp = t.player.maxHp;
    this.hp = this.maxHp;
    this.pos.copy(start);
    this.safePos.copy(start);
    this.yaw = yaw;
    this.body = game.physics.createCharacter(start, PLAYER_RADIUS, PLAYER_HEIGHT, Layer.Player, Layer.Terrain | Layer.Breakable | Layer.Enemy);
    game.physics.setOwner(this.body.collider, this);
  }

  chest(out = new Vector3()): Vector3 {
    return out.set(this.pos.x, this.pos.y + PLAYER_CHEST, this.pos.z);
  }

  get speed(): number {
    return Math.hypot(this.vel.x, this.vel.z);
  }

  get dashInvulnerable(): boolean {
    return this.dashTime > this.game.tuning.movement.dashTime - this.game.tuning.movement.dashInvuln;
  }

  get anim(): PlayerAnim {
    if (this.dead) return 'dead';
    if (this.hurtTime > 0) return 'hurt';
    if (this.attack) return this.attack.move;
    if (this.drilling) return 'drill';
    if (this.dashTime > 0) return 'dash';
    if (!this.grounded) return this.vel.y > 0 ? 'jump' : 'fall';
    return this.speed > 0.5 ? 'run' : 'idle';
  }

  teleport(p: Vector3, yaw?: number): void {
    this.pos.copy(p);
    this.safePos.copy(p);
    this.vel.set(0, 0, 0);
    if (yaw !== undefined) this.yaw = yaw;
    this.game.physics.setFeet(this.body, p);
  }

  update(dt: number): void {
    const g = this.game;
    if (this.dead) {
      this.deadTime += dt;
      return;
    }
    this.invuln = Math.max(0, this.invuln - dt);
    this.hurtTime = Math.max(0, this.hurtTime - dt);
    this.aiming = Math.max(0, this.aiming - dt);

    this.updateMovement(dt);
    this.updateSword(dt);
    this.updateGun(dt);
    this.updateDrill(dt);

    if (g.edges.pressed('heal') && this.heals > 0 && this.hp < this.maxHp) {
      this.heals--;
      this.hp = Math.min(this.maxHp, this.hp + g.tuning.player.healAmount);
      g.events.push({ type: 'sfx', id: 'heal' });
    }
  }

  // ---------------------------------------------------------------- 移動

  private moveInput(): { dir: Vector3; mag: number } {
    const g = this.game;
    const x = g.input.moveX;
    const y = g.input.moveY;
    const mag = Math.min(1, Math.hypot(x, y));
    if (mag < 0.15) return { dir: new Vector3(), mag: 0 };
    // カメラの向きを基準にする。前 = カメラが見ている方向、右 = 画面の右
    const fwd = yawToDir(g.cam.yaw);
    const right = new Vector3(-fwd.z, 0, fwd.x);
    const dir = fwd.multiplyScalar(y).add(right.multiplyScalar(x));
    dir.normalize();
    return { dir, mag };
  }

  private updateMovement(dt: number): void {
    const g = this.game;
    const m = g.tuning.movement;
    const locked = g.lockOn.target;
    const { dir, mag } = this.moveInput();
    const busy = this.attack !== null && this.attack.move !== 'air';

    // 向き
    if (locked && !this.attack) {
      const c = locked.center();
      this.yaw = dirToYaw(c.x - this.pos.x, c.z - this.pos.z);
    } else if (mag > 0 && !busy && this.dashTime <= 0) {
      this.yaw = approachAngle(this.yaw, dirToYaw(dir.x, dir.z), m.turnSpeed * DEG * dt);
    }

    // ダッシュの開始
    this.dashCooldown = Math.max(0, this.dashCooldown - dt);
    if (g.edges.pressed('dash') && this.dashCooldown <= 0 && this.grounded && this.hurtTime <= 0) {
      this.attack = null;
      this.dashTime = m.dashTime;
      this.dashCooldown = m.dashCooldown;
      if (mag > 0) this.dashDir.copy(dir);
      else if (locked) this.dashDir.copy(yawToDir(this.yaw)).multiplyScalar(-1);
      else this.dashDir.copy(yawToDir(this.yaw));
      g.events.push({ type: 'sfx', id: 'dash' });
    }

    // 水平方向の速度
    let speedScale = 1;
    if (this.gunCharge > 0 && g.chargeType) speedScale = g.tuning.gun.chargeMoveScale;
    if (this.drilling) speedScale = 0.5;

    if (this.dashTime > 0) {
      this.dashTime -= dt;
      this.vel.x = this.dashDir.x * m.dashSpeed;
      this.vel.z = this.dashDir.z * m.dashSpeed;
    } else if (this.hurtTime > 0) {
      this.vel.x = approach(this.vel.x, 0, m.groundDecel * 0.3 * dt);
      this.vel.z = approach(this.vel.z, 0, m.groundDecel * 0.3 * dt);
    } else if (busy) {
      this.vel.x = approach(this.vel.x, 0, m.groundDecel * dt);
      this.vel.z = approach(this.vel.z, 0, m.groundDecel * dt);
    } else {
      const top = locked ? m.strafeSpeed : m.runSpeed;
      const speed = mag > 0 ? Math.max(m.minWalkSpeed, top * mag) * speedScale : 0;
      const tx = dir.x * speed;
      const tz = dir.z * speed;
      if (this.grounded) {
        const accel = mag > 0 ? m.groundAccel : m.groundDecel;
        this.accelerateTo(tx, tz, accel * dt);
      } else {
        const maxAir = this.dashJump ? m.dashJumpSpeed : m.airMaxSpeed;
        const scale = this.dashJump && mag > 0 ? maxAir / Math.max(0.01, speed) : 1;
        this.accelerateTo(tx * scale, tz * scale, m.airAccel * dt);
        const h = Math.hypot(this.vel.x, this.vel.z);
        if (h > maxAir) {
          this.vel.x *= maxAir / h;
          this.vel.z *= maxAir / h;
        }
      }
    }

    // ジャンプ（接地の猶予と先行入力つき）
    const g2 = m.gravity;
    const jumpV = Math.sqrt(2 * g2 * m.jumpHeight);
    const minJumpV = Math.sqrt(2 * g2 * m.minJumpHeight);
    if (g.edges.pressed('jump') && !g.consumedJump) this.jumpBuffer = m.jumpBuffer;
    else this.jumpBuffer = Math.max(0, this.jumpBuffer - dt);
    this.coyote = this.grounded ? m.coyoteTime : Math.max(0, this.coyote - dt);

    if (this.jumpBuffer > 0 && this.coyote > 0 && !busy && this.hurtTime <= 0) {
      this.jumpBuffer = 0;
      this.coyote = 0;
      this.vel.y = jumpV;
      this.jumping = true;
      this.grounded = false;
      if (this.dashTime > 0) {
        // ダッシュジャンプ：ダッシュの勢いを空中でも保つ
        this.dashJump = true;
        this.dashTime = 0;
        const h = Math.hypot(this.vel.x, this.vel.z);
        if (h > 0.01) {
          this.vel.x *= m.dashJumpSpeed / h;
          this.vel.z *= m.dashJumpSpeed / h;
        }
      }
      g.events.push({ type: 'sfx', id: 'jump' });
    }
    if (this.jumping && !g.edges.down('jump') && this.vel.y > minJumpV) {
      this.vel.y = minJumpV;
    }

    // 重力（空中斬りの間は落下を少し止める）
    const hang = this.attack?.move === 'air' && this.attack.time < g.tuning.sword.airHangTime;
    const vy0 = this.vel.y;
    if (hang) {
      this.vel.y = Math.max(this.vel.y, 0) * 0.5;
    } else if (!(this.grounded && this.vel.y <= 0)) {
      const grav = this.vel.y < 0 ? g2 * m.fallGravityScale : g2;
      this.vel.y = Math.max(-m.terminalFall, this.vel.y - grav * dt);
    }
    // 位置は前後の速度の平均で進める（ジャンプの高さが刻みの大きさに左右されない）
    const dy = ((vy0 + this.vel.y) / 2) * dt;

    const wasGrounded = this.grounded;
    const want = new Vector3(this.vel.x * dt, this.grounded && this.vel.y <= 0 ? -0.05 : dy, this.vel.z * dt);
    const res = g.physics.moveCharacter(this.body, want, Layer.Terrain | Layer.Breakable | Layer.Enemy, this.grounded && this.vel.y <= 0);
    g.physics.feetOf(this.body, this.pos);
    this.grounded = res.grounded && this.vel.y <= 0.01 && this.groundBelow();
    if (this.grounded) {
      if (!wasGrounded) {
        g.events.push({ type: 'sfx', id: 'land' });
        this.airSlashes = 0;
      }
      this.vel.y = 0;
      this.jumping = false;
      this.dashJump = false;
      this.safePos.copy(this.pos);
    } else if (this.vel.y > 0 && res.moved.y < want.y * 0.5) {
      // 天井に頭をぶつけた
      this.vel.y = 0;
    }

    if (this.pos.y < KILL_Y) {
      this.teleport(this.safePos);
      this.takeDamage(10, this.pos, false, true);
    }
  }

  /**
   * 足元の真下に地面があるか。カプセルの丸い底が段の角に引っかかっただけの状態を
   * 「接地」とみなさないため（そこから段差の自動乗り越えで登れてしまうのを防ぐ）
   */
  private groundBelow(): boolean {
    const origin = new Vector3(this.pos.x, this.pos.y + 0.3, this.pos.z);
    const hit = this.game.physics.raycast(origin, new Vector3(0, -1, 0), 0.75, Layer.Terrain | Layer.Breakable | Layer.Enemy);
    return hit !== null && this.pos.y - hit.point.y < 0.4;
  }

  private accelerateTo(tx: number, tz: number, step: number): void {
    const dx = tx - this.vel.x;
    const dz = tz - this.vel.z;
    const len = Math.hypot(dx, dz);
    if (len <= step) {
      this.vel.x = tx;
      this.vel.z = tz;
    } else {
      this.vel.x += (dx / len) * step;
      this.vel.z += (dz / len) * step;
    }
  }

  // ---------------------------------------------------------------- 光刃

  private startAttack(move: SwordMove, damage: number, duration: number): void {
    this.attack = {
      move,
      time: 0,
      duration,
      activeFrom: duration * 0.25,
      activeTo: duration * 0.7,
      damage,
      hit: new Set(),
      buffered: false,
    };
    this.game.events.push({ type: 'sfx', id: move === 'charge' ? 'slash_charge' : 'slash' });
  }

  private updateSword(dt: number): void {
    const g = this.game;
    const s = g.tuning.sword;
    const locked = g.lockOn.target;

    if (g.edges.down('sword')) this.swordHold += dt;

    if (g.edges.pressed('sword') && this.hurtTime <= 0 && !this.drilling) {
      const a = this.attack;
      if (a && (a.move === 'combo1' || a.move === 'combo2')) {
        if (a.duration - a.time <= s.inputBuffer + a.duration * 0.3) a.buffered = true;
      } else if (!a) {
        if (this.dashTime > 0 && this.grounded) {
          this.dashTime = 0;
          this.startAttack('dash', s.dashSlash, 0.35);
          const f = yawToDir(this.yaw);
          this.vel.set(f.x * 9, 0, f.z * 9);
        } else if (!this.grounded) {
          if (this.airSlashes < s.airSlashMax) {
            this.airSlashes++;
            this.startAttack('air', s.airSlash, 0.3);
          }
        } else if (locked) {
          const d = horizontalDistance(locked.pos, this.pos);
          if (d >= s.lungeMin && d <= s.lungeMax) this.startAttack('lunge', s.lunge, 0.35);
          else this.startAttack('combo1', s.combo[0], s.comboTimes[0]);
        } else {
          this.startAttack('combo1', s.combo[0], s.comboTimes[0]);
        }
      }
    }

    // 長押しからの溜め斬り
    if (g.edges.released('sword')) {
      if (this.swordHold >= s.chargeTime && this.grounded && !this.drilling && this.hurtTime <= 0) {
        this.startAttack('charge', s.chargeSlash, 0.5);
        const f = yawToDir(this.yaw);
        g.spawnPlayerShot({
          origin: this.chest().addScaledVector(f, 0.8),
          dir: f,
          speed: 18,
          range: s.shockwaveRange,
          damage: s.shockwave,
          radius: 0.9,
          pierce: true,
          kind: 'wave',
        });
      }
      this.swordHold = 0;
    }

    const a = this.attack;
    if (!a) return;
    a.time += dt;

    // 踏み込み
    const f = yawToDir(this.yaw);
    if (a.move === 'lunge' && locked && a.time < a.activeFrom) {
      const d = horizontalDistance(locked.pos, this.pos) - (locked.radius + 1.0);
      const step = Math.min(Math.max(d, 0), s.lungeSpeed * dt);
      g.physics.moveCharacter(this.body, f.clone().multiplyScalar(step), Layer.Terrain | Layer.Breakable | Layer.Enemy);
      g.physics.feetOf(this.body, this.pos);
    } else if ((a.move === 'combo1' || a.move === 'combo2' || a.move === 'combo3') && a.time < 0.1 && this.grounded) {
      const step = (s.comboStep / 0.1) * dt;
      g.physics.moveCharacter(this.body, f.clone().multiplyScalar(step), Layer.Terrain | Layer.Breakable | Layer.Enemy);
      g.physics.feetOf(this.body, this.pos);
    }

    // 当たり判定
    if (a.time >= a.activeFrom && a.time <= a.activeTo) {
      const range = a.move === 'charge' ? s.range + 0.8 : s.range;
      const arc = (a.move === 'dash' || a.move === 'charge' ? 160 : s.arcDeg) * DEG;
      for (const e of g.enemies) {
        if (!e.alive || a.hit.has(e)) continue;
        const d = horizontalDistance(e.pos, this.pos) - e.radius;
        if (d > range) continue;
        if (Math.abs(e.center().y - this.chest().y) > 1.8) continue;
        const rel = Math.abs(((dirToYaw(e.pos.x - this.pos.x, e.pos.z - this.pos.z) - this.yaw + Math.PI * 3) % (Math.PI * 2)) - Math.PI);
        if (rel > arc / 2 && d > 0.3) continue;
        a.hit.add(e);
        const finisher = a.move === 'combo3' || a.move === 'charge';
        g.damageEnemy(e, a.damage, this.pos, { melee: true, launch: a.move === 'combo3' });
        g.hitstop = Math.max(
          g.hitstop,
          a.move === 'charge' ? s.hitstopCharge : finisher ? s.hitstopFinisher : s.hitstop,
        );
      }
    }

    if (a.time >= a.duration) {
      if (a.buffered && (a.move === 'combo1' || a.move === 'combo2')) {
        const next = a.move === 'combo1' ? 1 : 2;
        this.attack = null;
        this.startAttack(next === 1 ? 'combo2' : 'combo3', s.combo[next], s.comboTimes[next]);
      } else {
        this.attack = null;
      }
    }
  }

  // ---------------------------------------------------------------- 主武器

  private updateGun(dt: number): void {
    const g = this.game;
    const cfg = g.tuning.gun;
    this.gunCooldown = Math.max(0, this.gunCooldown - dt);
    if (this.hurtTime > 0 || this.drilling) {
      this.gunCharge = 0;
      return;
    }

    if (!g.chargeType) {
      if (g.edges.down('fire') && this.gunCooldown <= 0) {
        this.fire(cfg.damage, 'normal');
        this.gunCooldown = 1 / cfg.rate;
      }
      return;
    }

    // チャージ型：押すと単発、長押しで溜める
    if (g.edges.pressed('fire') && this.gunCooldown <= 0) {
      this.fire(cfg.damage, 'normal');
      this.gunCooldown = 1 / cfg.tapRate;
    }
    if (g.edges.down('fire')) {
      this.gunCharge += dt;
      this.aiming = 0.3;
    }
    if (g.edges.released('fire')) {
      if (this.gunCharge >= cfg.chargeLv2Time) this.fire(cfg.damage * cfg.chargeLv2Mult, 'charge2');
      else if (this.gunCharge >= cfg.chargeLv1Time) this.fire(cfg.damage * cfg.chargeLv1Mult, 'charge1');
      this.gunCharge = 0;
    }
  }

  private fire(damage: number, kind: 'normal' | 'charge1' | 'charge2'): void {
    const g = this.game;
    const cfg = g.tuning.gun;
    const origin = this.chest();
    const right = new Vector3(-Math.cos(this.yaw), 0, Math.sin(this.yaw));
    origin.addScaledVector(right, -0.3).addScaledVector(yawToDir(this.yaw), 0.4);

    const target = g.lockOn.target ?? g.softAimTarget();
    let dir: Vector3;
    if (target) {
      dir = target.center().sub(origin).normalize();
      if (!g.lockOn.target) {
        this.yaw = dirToYaw(dir.x, dir.z);
      }
    } else {
      // カメラの向きに撃つ（上下は少しだけ反映する）
      const pitch = clamp(-g.cam.pitch * 0.5, -20 * DEG, 20 * DEG);
      dir = yawToDir(g.cam.yaw).multiplyScalar(Math.cos(pitch)).setY(Math.sin(pitch)).normalize();
      if (!this.attack) this.yaw = g.cam.yaw;
    }
    g.spawnPlayerShot({
      origin,
      dir,
      speed: cfg.speed * (kind === 'charge2' ? 1.1 : 1),
      range: cfg.range * (kind === 'normal' ? 1 : 1.3),
      damage,
      radius: kind === 'charge2' ? 0.6 : kind === 'charge1' ? 0.35 : 0.2,
      pierce: kind !== 'normal',
      kind,
      homing: g.lockOn.target ?? undefined,
    });
    this.aiming = 0.5;
    g.alertNoise(this.pos, 12);
    g.events.push({ type: 'sfx', id: kind === 'normal' ? 'shot' : 'shot_charge' });
  }

  // ---------------------------------------------------------------- 特殊武器（ブレイクドリル）

  private updateDrill(dt: number): void {
    const g = this.game;
    const cfg = g.tuning.drill;
    const can = g.hasItem('special.drill') && this.weaponEnergy > 0 && this.hurtTime <= 0 && !this.attack;
    const was = this.drilling;
    this.drilling = can && g.edges.down('special');
    if (!this.drilling) {
      this.drillTick = 0;
      return;
    }
    if (!was) g.events.push({ type: 'sfx', id: 'drill' });
    this.weaponEnergy = Math.max(0, this.weaponEnergy - cfg.energyPerSec * dt);
    this.drillTick -= dt;
    if (this.drillTick > 0) return;
    this.drillTick = cfg.tickInterval;

    const f = yawToDir(this.yaw);
    const tip = this.chest().addScaledVector(f, cfg.range * 0.6);
    for (const e of g.enemies) {
      if (!e.alive) continue;
      if (e.center().distanceTo(tip) <= cfg.range * 0.6 + e.radius) {
        g.damageEnemy(e, cfg.damagePerTick, this.pos, { melee: true, armorBreak: true });
      }
    }
    for (const b of g.breakables) {
      if (!b.broken && b.distanceTo(tip) <= cfg.range * 0.7) {
        g.drillBreakable(b, cfg.tickInterval);
      }
    }
  }

  // ---------------------------------------------------------------- 被弾

  takeDamage(amount: number, from: Vector3, heavy: boolean, ignoreInvuln = false): boolean {
    const g = this.game;
    if (this.dead || g.godMode) return false;
    if (!ignoreInvuln && (this.invuln > 0 || this.dashInvulnerable)) return false;
    this.hp = Math.max(0, this.hp - amount);
    this.invuln = g.tuning.player.hurtInvuln;
    this.hurtTime = heavy ? 0.6 : 0.25;
    this.attack = null;
    this.drilling = false;
    this.dashTime = 0;
    const away = new Vector3(this.pos.x - from.x, 0, this.pos.z - from.z);
    if (away.lengthSq() < 1e-4) away.copy(yawToDir(this.yaw)).multiplyScalar(-1);
    away.normalize().multiplyScalar(heavy ? 7 : 4);
    this.vel.x = away.x;
    this.vel.z = away.z;
    if (heavy && this.grounded) this.vel.y = 4;
    g.events.push({ type: 'playerHurt', amount });
    g.events.push({ type: 'shake', strength: heavy ? 0.5 : 0.25 });
    if (this.hp <= 0) {
      this.dead = true;
      this.deadTime = 0;
      g.events.push({ type: 'playerDied' });
    }
    return true;
  }
}
