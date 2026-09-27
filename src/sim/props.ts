import { Vector3 } from 'three';
import type RAPIER from '@dimforge/rapier3d-compat';

/** ドリルで壊せる壁 */
export class Breakable {
  broken = false;
  /** 壊れるまでに必要なドリルの時間（秒） */
  toughness = 1.0;
  progress = 0;
  collider: RAPIER.Collider | null = null;

  constructor(
    readonly id: string,
    readonly center: Vector3,
    readonly size: Vector3,
    readonly yaw: number,
  ) {}

  distanceTo(p: Vector3): number {
    // 回転を考えた箱との距離（y 軸まわり）
    const dx = p.x - this.center.x;
    const dz = p.z - this.center.z;
    const c = Math.cos(-this.yaw);
    const s = Math.sin(-this.yaw);
    const lx = dx * c + dz * s;
    const lz = -dx * s + dz * c;
    const ly = p.y - this.center.y;
    const qx = Math.max(Math.abs(lx) - this.size.x / 2, 0);
    const qy = Math.max(Math.abs(ly) - this.size.y / 2, 0);
    const qz = Math.max(Math.abs(lz) - this.size.z / 2, 0);
    return Math.hypot(qx, qy, qz);
  }
}

export interface Interactable {
  readonly id: string;
  readonly pos: Vector3;
  readonly prompt: string;
  readonly range: number;
  enabled(): boolean;
}

export class Chest implements Interactable {
  opened = false;
  readonly range = 1.8;
  readonly prompt = '開ける';

  constructor(
    readonly id: string,
    readonly pos: Vector3,
    readonly yaw: number,
    readonly contents: { cells?: number; item?: string },
  ) {}

  enabled(): boolean {
    return !this.opened;
  }
}

export class Npc implements Interactable {
  readonly range = 2.2;
  readonly prompt = '話す';

  constructor(
    readonly id: string,
    readonly pos: Vector3,
    public yaw: number,
    readonly name: string,
    readonly talk: string,
  ) {}

  enabled(): boolean {
    return true;
  }
}

export class Beacon implements Interactable {
  readonly range = 2.0;
  readonly prompt = 'セーブする';
  activated = false;

  constructor(
    readonly id: string,
    readonly pos: Vector3,
  ) {}

  enabled(): boolean {
    return true;
  }
}

export type PickupKind = 'cells' | 'energy' | 'repair';

export class Pickup {
  collected = false;
  age = 0;
  readonly vel = new Vector3();

  constructor(
    readonly kind: PickupKind,
    readonly amount: number,
    readonly pos: Vector3,
  ) {}
}

export class Trigger {
  fired = false;

  constructor(
    readonly id: string,
    readonly center: Vector3,
    readonly half: Vector3,
    readonly event: string,
    readonly once: boolean,
  ) {}

  contains(p: Vector3): boolean {
    return (
      Math.abs(p.x - this.center.x) <= this.half.x &&
      Math.abs(p.y - this.center.y) <= this.half.y + 1 &&
      Math.abs(p.z - this.center.z) <= this.half.z
    );
  }
}

export class Checkpoint {
  constructor(
    readonly id: string,
    readonly pos: Vector3,
    readonly yaw: number,
    readonly radius: number,
  ) {}
}
