import { Vector3 } from 'three';
import { DEG, dirToYaw, horizontalDistance, segmentSphere, wrapAngle, yawToDir } from '../core/math';
import { EventQueue } from '../core/events';
import { Rng } from '../core/rng';
import { Layer, PhysicsWorld, initPhysics } from '../physics/physics';
import type { Tuning } from '../content/tuning';
import type { AreaGeometry, Placement } from './area';
import { CameraOrbit } from './camera';
import { DT, PLAYER_CHEST } from './constants';
import { AttackTokens, type Enemy, type HitInfo } from './enemies/enemy';
import { Charger } from './enemies/charger';
import { Sentry } from './enemies/sentry';
import { ButtonEdges, emptyInput, type InputFrame } from './inputFrame';
import { LockOn } from './lockon';
import { Player } from './player';
import { Shot, type ShotSpec } from './projectiles';
import { Beacon, Breakable, Checkpoint, Chest, Npc, Pickup, Trigger, type Interactable, type PickupKind } from './props';
import { SAVE_VERSION, type SaveData } from './save';
import type { DialogueFile, EventFile } from './script';
import { Story } from './story';

export const ITEM_NAMES: Record<string, string> = {
  'special.drill': '特殊武器「ブレイクドリル」',
  'chip.charge': 'チューニングチップ「チャージ化」',
};

export interface GameInit {
  geometry: AreaGeometry;
  placement: Placement;
  tuning: Tuning;
  dialogues: DialogueFile;
  events: EventFile;
  seed?: number;
  save?: SaveData | null;
}

/** ゲームの中身。描画を知らず、Node.js でも動く */
export class Game {
  readonly physics: PhysicsWorld;
  readonly events = new EventQueue();
  readonly rng: Rng;
  readonly edges = new ButtonEdges();
  input: InputFrame = emptyInput();
  readonly cam: CameraOrbit;
  readonly lockOn: LockOn;
  readonly tokens: AttackTokens;
  readonly story: Story;
  player!: Player;

  readonly enemies: Enemy[] = [];
  readonly shots: Shot[] = [];
  readonly breakables: Breakable[] = [];
  readonly chests: Chest[] = [];
  readonly npcs: Npc[] = [];
  readonly beacons: Beacon[] = [];
  readonly pickups: Pickup[] = [];
  readonly triggers: Trigger[] = [];
  readonly checkpoints: Checkpoint[] = [];

  time = 0;
  tick = 0;
  playTime = 0;
  hitstop = 0;
  cells = 0;
  readonly items = new Set<string>();
  readonly equippedChips = new Set<string>();
  objective = '';
  checkpoint = '';
  godMode = false;
  /** このフレームのジャンプボタンを「調べる」に使ったか */
  consumedJump = false;
  /** 今「調べる」ことができる対象 */
  focus: Interactable | null = null;

  private constructor(readonly init: GameInit) {
    this.physics = new PhysicsWorld();
    this.rng = new Rng(init.seed ?? 12345);
    this.cam = new CameraOrbit(init.tuning);
    this.lockOn = new LockOn(this);
    this.tokens = new AttackTokens(() => this.tuning.enemies.maxAttackers);
    this.story = new Story(init.dialogues, init.events, {
      giveItem: (item) => this.giveItem(item),
      giveCells: (n) => this.giveCells(n),
      setFlag: () => {},
      message: (text) => this.events.push({ type: 'message', text }),
      setObjective: (text) => (this.objective = text),
      sfx: (id) => this.events.push({ type: 'sfx', id }),
    });
  }

  static async create(init: GameInit): Promise<Game> {
    await initPhysics();
    const g = new Game(init);
    g.build();
    return g;
  }

  get tuning(): Tuning {
    return this.init.tuning;
  }

  get chargeType(): boolean {
    return this.equippedChips.has('chip.charge');
  }

  private marker(name: string): { pos: Vector3; yaw: number } {
    const m = this.init.geometry.markers[name];
    if (!m) throw new Error(`目印が見つからない: ${name}`);
    return { pos: new Vector3(...m.pos), yaw: m.yaw };
  }

  private build(): void {
    const { geometry, placement, save } = this.init;
    for (const mesh of geometry.meshes) this.physics.addTrimesh(mesh.vertices, mesh.indices, Layer.Terrain);

    const broken = new Set(save?.broken ?? []);
    const opened = new Set(save?.opened ?? []);

    for (const p of placement.props) {
      const m = this.marker(p.at);
      switch (p.type) {
        case 'breakable': {
          const size = new Vector3(...p.size);
          const center = m.pos.clone().setY(m.pos.y + size.y / 2);
          const b = new Breakable(p.id, center, size, m.yaw);
          if (broken.has(p.id)) b.broken = true;
          else {
            b.collider = this.physics.addBox(center, size.clone().multiplyScalar(0.5), Layer.Breakable, m.yaw);
            this.physics.setOwner(b.collider, b);
          }
          this.breakables.push(b);
          break;
        }
        case 'chest': {
          const c = new Chest(p.id, m.pos, m.yaw, p.contents);
          c.opened = opened.has(p.id);
          this.physics.addBox(m.pos.clone().setY(m.pos.y + 0.4), new Vector3(0.6, 0.4, 0.4), Layer.Terrain, m.yaw);
          this.chests.push(c);
          break;
        }
        case 'npc': {
          this.npcs.push(new Npc(p.id, m.pos, m.yaw, p.name, p.talk));
          this.physics.addBox(m.pos.clone().setY(m.pos.y + 0.8), new Vector3(0.3, 0.8, 0.3), Layer.Terrain);
          break;
        }
        case 'beacon':
          this.beacons.push(new Beacon(p.id, m.pos));
          break;
      }
    }
    for (const t of placement.triggers) {
      const m = this.marker(t.at);
      const tr = new Trigger(t.id, m.pos.clone().setY(m.pos.y + t.size[1] / 2), new Vector3(...t.size).multiplyScalar(0.5), t.event, t.once);
      if (save?.flags[`trigger.${t.id}`]) tr.fired = true;
      this.triggers.push(tr);
    }
    for (const c of placement.checkpoints) {
      const m = this.marker(c.at);
      this.checkpoints.push(new Checkpoint(c.id, m.pos, m.yaw, c.radius));
    }
    for (const e of placement.enemies) {
      const m = this.marker(e.at);
      this.enemies.push(e.type === 'sentry' ? new Sentry(this, m.pos, m.yaw) : new Charger(this, m.pos, m.yaw));
    }

    const start = this.marker(placement.playerStart);
    this.player = new Player(this, start.pos, start.yaw);
    this.cam.yaw = start.yaw;
    this.checkpoint = placement.playerStart;
    this.objective = placement.objective;

    if (save) this.applySave(save);
    this.physics.step();
  }

  // ---------------------------------------------------------------- 1 刻み

  step(input: InputFrame): void {
    this.input = input;
    this.edges.update(input);
    this.consumedJump = false;
    this.physics.step();

    // 会話中は世界を止める
    if (this.story.blocking) {
      if (this.edges.pressed('jump') || this.edges.pressed('sword') || this.edges.pressed('fire')) this.story.confirm();
      this.story.update(DT);
      this.tick++;
      return;
    }
    this.story.update(DT);

    this.cam.applyLook(input);
    if (input.cameraReset) this.cam.requestRecenter();

    if (this.hitstop > 0) {
      this.hitstop -= DT;
      this.tick++;
      return;
    }

    this.lockOn.update(DT);
    this.updateInteraction();
    this.player.update(DT);
    for (const e of this.enemies) e.update(DT);
    this.updateShots(DT);
    this.updatePickups(DT);
    this.updateTriggers();
    this.updateRespawn(DT);

    const t = this.lockOn.target;
    this.cam.update(DT, { x: this.player.pos.x, z: this.player.pos.z, yaw: this.player.yaw, speed: this.player.speed }, t ? { x: t.pos.x, z: t.pos.z } : null);

    this.time += DT;
    this.playTime += DT;
    this.tick++;
  }

  // ---------------------------------------------------------------- 調べる

  private updateInteraction(): void {
    const p = this.player;
    this.focus = null;
    if (!p.grounded || p.attack || p.dead) return;
    let best: Interactable | null = null;
    let bestD = Infinity;
    const all: Interactable[] = [...this.chests, ...this.npcs, ...this.beacons];
    for (const it of all) {
      if (!it.enabled()) continue;
      const d = horizontalDistance(it.pos, p.pos);
      if (d > it.range || Math.abs(it.pos.y - p.pos.y) > 1.5) continue;
      if (d < bestD) {
        bestD = d;
        best = it;
      }
    }
    this.focus = best;
    if (best && this.edges.pressed('jump')) {
      this.consumedJump = true;
      this.interact(best);
    }
  }

  private interact(it: Interactable): void {
    if (it instanceof Chest) {
      it.opened = true;
      this.events.push({ type: 'chestOpened', id: it.id });
      this.events.push({ type: 'sfx', id: 'chest' });
      if (it.contents.cells) this.giveCells(it.contents.cells);
      if (it.contents.item) this.giveItem(it.contents.item);
    } else if (it instanceof Npc) {
      it.yaw = dirToYaw(this.player.pos.x - it.pos.x, this.player.pos.z - it.pos.z);
      this.player.yaw = dirToYaw(it.pos.x - this.player.pos.x, it.pos.z - this.player.pos.z);
      const key = `${it.talk}.done`;
      const repeat = `${it.talk}.again`;
      this.story.startDialogue(this.story.flags[key] && this.init.dialogues[repeat] ? repeat : it.talk);
      this.story.flags[key] = true;
    } else if (it instanceof Beacon) {
      it.activated = true;
      this.player.hp = this.player.maxHp;
      this.player.weaponEnergy = 100;
      this.events.push({ type: 'saved' });
      this.events.push({ type: 'sfx', id: 'save' });
    }
  }

  // ---------------------------------------------------------------- 所持品

  giveItem(item: string): void {
    this.items.add(item);
    if (item === 'chip.charge') this.equippedChips.add(item);
    this.events.push({ type: 'message', text: `${ITEM_NAMES[item] ?? item} を手に入れた` });
    this.events.push({ type: 'sfx', id: 'item' });
  }

  giveCells(n: number): void {
    this.cells += n;
  }

  hasItem(item: string): boolean {
    return this.items.has(item);
  }

  toggleChip(chip: string): void {
    if (!this.items.has(chip)) return;
    if (this.equippedChips.has(chip)) this.equippedChips.delete(chip);
    else this.equippedChips.add(chip);
  }

  // ---------------------------------------------------------------- 戦闘

  /** ロックオンしていないときの「弱い自動照準」。カメラ正面から 10° 以内の敵 */
  softAimTarget(): Enemy | null {
    const chest = this.player.chest();
    let best: Enemy | null = null;
    let bestRel = 10 * DEG;
    for (const e of this.enemies) {
      if (!e.alive) continue;
      const c = e.center();
      if (c.distanceTo(chest) > this.tuning.gun.range * 1.2) continue;
      const rel = Math.abs(wrapAngle(dirToYaw(c.x - chest.x, c.z - chest.z) - this.cam.yaw));
      if (rel < bestRel) {
        bestRel = rel;
        best = e;
      }
    }
    return best;
  }

  damageEnemy(e: Enemy, amount: number, from: Vector3, info: HitInfo): void {
    if (!e.alive) return;
    const r = e.receive(amount, from, info);
    const c = e.center();
    this.events.push({ type: 'hit', x: c.x, y: c.y, z: c.z, kind: r.kind });
    this.events.push({ type: 'sfx', id: r.kind === 'weak' ? 'hit_weak' : 'hit', x: c.x, y: c.y, z: c.z });
    if (r.killed) {
      this.events.push({ type: 'enemyDestroyed', x: c.x, y: c.y, z: c.z });
      this.events.push({ type: 'sfx', id: 'explode', x: c.x, y: c.y, z: c.z });
      this.dropLoot(c);
    }
  }

  private dropLoot(at: Vector3): void {
    const n = this.rng.int(2, 4);
    for (let i = 0; i < n; i++) this.spawnPickup('cells', this.rng.int(3, 5), at);
    if (this.rng.chance(0.25)) this.spawnPickup('energy', 20, at);
    if (this.rng.chance(0.15)) this.spawnPickup('repair', 15, at);
  }

  spawnPickup(kind: PickupKind, amount: number, at: Vector3): void {
    const p = new Pickup(kind, amount, at.clone());
    const a = this.rng.range(0, Math.PI * 2);
    p.vel.set(Math.cos(a) * 2, 4, Math.sin(a) * 2);
    this.pickups.push(p);
  }

  drillBreakable(b: Breakable, dt: number): void {
    b.progress += dt;
    this.events.push({ type: 'hit', x: b.center.x, y: b.center.y, z: b.center.z, kind: 'armor' });
    if (b.progress >= b.toughness && !b.broken) {
      b.broken = true;
      if (b.collider) this.physics.removeCollider(b.collider);
      b.collider = null;
      this.events.push({ type: 'wallBroken', id: b.id });
      this.events.push({ type: 'sfx', id: 'wall_break' });
      this.events.push({ type: 'shake', strength: 0.4 });
    }
  }

  alertNoise(at: Vector3, radius: number): void {
    for (const e of this.enemies) {
      if (e.alive && e.state === 'idle' && horizontalDistance(e.pos, at) <= radius) e.becomeAlert();
    }
  }

  spawnPlayerShot(spec: ShotSpec): void {
    this.shots.push(new Shot(spec, true));
  }

  spawnEnemyShot(origin: Vector3, dir: Vector3, speed: number, damage: number): void {
    this.shots.push(new Shot({ origin, dir, speed, range: 40, damage, radius: 0.25, pierce: false, kind: 'enemy' }, false));
  }

  private updateShots(dt: number): void {
    const homing = this.tuning.lockOn.homingDegPerSec * DEG;
    for (const s of this.shots) {
      if (!s.alive) continue;
      // 追尾：ロックオン対象へ緩やかに曲げる
      if (s.spec.homing && s.spec.homing.alive) {
        const want = s.spec.homing.center().sub(s.pos).normalize();
        const cur = s.vel.clone().normalize();
        const angle = cur.angleTo(want);
        const maxTurn = homing * dt;
        if (angle > 1e-4) {
          const t = Math.min(1, maxTurn / angle);
          cur.lerp(want, t).normalize();
          s.vel.copy(cur.multiplyScalar(s.spec.speed));
        }
      }
      s.prev.copy(s.pos);
      const move = s.vel.clone().multiplyScalar(dt);
      const len = move.length();
      const end = s.pos.clone().add(move);

      // 地形
      const terrain = this.physics.raycast(s.pos, move.clone().divideScalar(len), len, Layer.Terrain | Layer.Breakable);
      let stopAt = terrain ? terrain.distance / len : 1;

      if (s.fromPlayer) {
        for (const e of this.enemies) {
          if (!e.alive || s.hit.has(e)) continue;
          const t = segmentSphere(s.pos, end, e.center(), e.radius + s.spec.radius);
          if (t === null || t > stopAt) continue;
          s.hit.add(e);
          this.damageEnemy(e, s.spec.damage, s.pos, { armorBreak: s.spec.kind !== 'normal' });
          if (!s.spec.pierce) {
            stopAt = t;
            s.alive = false;
            break;
          }
        }
      } else {
        const p = this.player;
        const t = segmentSphere(s.pos, end, p.chest(), 0.45 + s.spec.radius);
        if (t !== null && t <= stopAt && !p.dead) {
          // 無敵中（ダッシュや被弾直後）でも弾はプレイヤーで消す。すり抜けた弾がカメラの目の前を横切らないように
          p.takeDamage(s.spec.damage, s.pos, false);
          s.alive = false;
          stopAt = t;
        }
      }

      s.pos.lerp(end, stopAt);
      s.traveled += len * stopAt;
      if (terrain && stopAt < 1 && s.alive) {
        s.alive = false;
        this.events.push({ type: 'hit', x: s.pos.x, y: s.pos.y, z: s.pos.z, kind: 'armor' });
      }
      if (s.traveled >= s.spec.range) s.alive = false;
    }
    for (let i = this.shots.length - 1; i >= 0; i--) if (!this.shots[i].alive) this.shots.splice(i, 1);
  }

  private updatePickups(dt: number): void {
    const p = this.player;
    const chest = p.chest();
    for (const k of this.pickups) {
      if (k.collected) continue;
      k.age += dt;
      const d = k.pos.distanceTo(chest);
      if (k.age > 0.4 && d < 3) {
        // 近づくと吸い寄せられる
        const pull = chest.clone().sub(k.pos).normalize().multiplyScalar(14 * dt);
        k.pos.add(pull);
      } else {
        k.vel.y -= 18 * dt;
        k.pos.addScaledVector(k.vel, dt);
        const hit = this.physics.raycast(k.pos.clone().setY(k.pos.y + 0.5), new Vector3(0, -1, 0), 0.7, Layer.Terrain);
        if (hit) {
          k.pos.y = hit.point.y + 0.2;
          k.vel.set(0, 0, 0);
        }
      }
      if (k.pos.distanceTo(chest) < 0.8 || (k.age > 0.4 && d < 1.0)) {
        k.collected = true;
        if (k.kind === 'cells') this.cells += k.amount;
        else if (k.kind === 'energy') p.weaponEnergy = Math.min(100, p.weaponEnergy + k.amount);
        else p.hp = Math.min(p.maxHp, p.hp + k.amount);
        this.events.push({ type: 'sfx', id: 'pickup' });
      }
      if (k.age > 30) k.collected = true;
    }
    for (let i = this.pickups.length - 1; i >= 0; i--) if (this.pickups[i].collected) this.pickups.splice(i, 1);
  }

  private updateTriggers(): void {
    const pos = this.player.pos;
    for (const t of this.triggers) {
      if (t.fired && t.once) continue;
      if (t.contains(pos)) {
        t.fired = true;
        this.story.flags[`trigger.${t.id}`] = true;
        this.story.startEvent(t.event);
      }
    }
    for (const c of this.checkpoints) {
      if (c.id !== this.checkpoint && horizontalDistance(c.pos, pos) <= c.radius) this.checkpoint = c.id;
    }
  }

  private updateRespawn(_dt: number): void {
    const p = this.player;
    if (!p.dead || p.deadTime < 2) return;
    // やられたら直前の中継地点から再開（ノーマルでは何も失わない）
    const cp = this.checkpoints.find((c) => c.id === this.checkpoint);
    const at = cp ? { pos: cp.pos, yaw: cp.yaw } : this.marker(this.init.placement.playerStart);
    p.dead = false;
    p.hp = p.maxHp;
    p.invuln = 2;
    p.teleport(at.pos, at.yaw);
    this.cam.yaw = at.yaw;
    this.lockOn.release();
    for (const s of this.shots) if (!s.fromPlayer) s.alive = false;
    for (const e of this.enemies) this.tokens.release(e);
  }

  // ---------------------------------------------------------------- セーブ

  toSave(areaId: string): SaveData {
    const p = this.player;
    const flags: Record<string, boolean> = { ...this.story.flags };
    return {
      version: SAVE_VERSION,
      savedAt: new Date(0).toISOString(),
      playTime: this.playTime,
      area: areaId,
      checkpoint: this.checkpoint,
      pos: [p.pos.x, p.pos.y, p.pos.z],
      yaw: p.yaw,
      hp: p.hp,
      maxHp: p.maxHp,
      heals: p.heals,
      weaponEnergy: p.weaponEnergy,
      cells: this.cells,
      items: [...this.items],
      equippedChips: [...this.equippedChips],
      flags,
      opened: this.chests.filter((c) => c.opened).map((c) => c.id),
      broken: this.breakables.filter((b) => b.broken).map((b) => b.id),
      scanned: [...this.lockOn.scanned],
      objective: this.objective,
    };
  }

  private applySave(s: SaveData): void {
    const p = this.player;
    p.teleport(new Vector3(...s.pos), s.yaw);
    this.cam.yaw = s.yaw;
    p.hp = s.hp;
    p.maxHp = s.maxHp;
    p.heals = s.heals;
    p.weaponEnergy = s.weaponEnergy;
    this.cells = s.cells;
    for (const i of s.items) this.items.add(i);
    for (const c of s.equippedChips) this.equippedChips.add(c);
    Object.assign(this.story.flags, s.flags);
    for (const k of s.scanned) this.lockOn.scanned.add(k);
    this.checkpoint = s.checkpoint;
    this.playTime = s.playTime;
    this.objective = s.objective;
  }

  /** プレイヤーの正面方向（view やテスト用） */
  playerForward(): Vector3 {
    return yawToDir(this.player.yaw);
  }

  /** ロックオン照準の位置（view 用） */
  lockOnPoint(): Vector3 | null {
    const t = this.lockOn.target;
    return t ? t.center() : null;
  }

  /** プレイヤーの胸の位置（view 用） */
  playerChest(): Vector3 {
    return this.player.pos.clone().setY(this.player.pos.y + PLAYER_CHEST);
  }
}
