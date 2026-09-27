import { Vector3 } from 'three';
import type { Enemy } from './enemies/enemy';

export type ShotKind = 'normal' | 'charge1' | 'charge2' | 'wave' | 'enemy';

export interface ShotSpec {
  origin: Vector3;
  dir: Vector3;
  speed: number;
  range: number;
  damage: number;
  radius: number;
  pierce: boolean;
  kind: ShotKind;
  homing?: Enemy;
}

/** 弾。剛体にはせず、毎刻み線分で当たりを調べる */
export class Shot {
  readonly pos = new Vector3();
  readonly prev = new Vector3();
  readonly vel = new Vector3();
  traveled = 0;
  alive = true;
  readonly hit = new Set<unknown>();

  constructor(
    readonly spec: ShotSpec,
    readonly fromPlayer: boolean,
  ) {
    this.pos.copy(spec.origin);
    this.prev.copy(spec.origin);
    this.vel.copy(spec.dir).normalize().multiplyScalar(spec.speed);
  }
}
