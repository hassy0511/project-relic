import RAPIER from '@dimforge/rapier3d-compat';
import { Vector3 } from 'three';

/** 当たり判定のレイヤー（ビット） */
export const Layer = {
  Terrain: 1 << 0,
  Player: 1 << 1,
  Enemy: 1 << 2,
  Breakable: 1 << 3,
} as const;

function groups(membership: number, filter: number): number {
  return ((membership & 0xffff) << 16) | (filter & 0xffff);
}

let initPromise: Promise<void> | null = null;

/** Rapier の WASM を初期化する（一度だけ） */
export function initPhysics(): Promise<void> {
  if (!initPromise) initPromise = RAPIER.init();
  return initPromise;
}

export interface CharacterBody {
  collider: RAPIER.Collider;
  controller: RAPIER.KinematicCharacterController;
  radius: number;
  halfHeight: number;
}

export interface RayHit {
  distance: number;
  point: Vector3;
  normal: Vector3;
  owner: unknown;
}

/**
 * Rapier の包み。sim が物理エンジンの細部を知らなくて済むようにする。
 * キャラクターは剛体を持たないコライダーを、キャラクターコントローラーで動かす。
 */
export class PhysicsWorld {
  readonly world: RAPIER.World;
  private owners = new Map<number, unknown>();

  constructor() {
    this.world = new RAPIER.World({ x: 0, y: 0, z: 0 });
  }

  /** 当たり判定の状態を最新にする（毎刻み呼ぶ） */
  step(): void {
    this.world.step();
  }

  setOwner(collider: RAPIER.Collider, owner: unknown): void {
    this.owners.set(collider.handle, owner);
  }

  ownerOf(collider: RAPIER.Collider): unknown {
    return this.owners.get(collider.handle);
  }

  addTrimesh(vertices: Float32Array, indices: Uint32Array, layer: number = Layer.Terrain): RAPIER.Collider {
    const desc = RAPIER.ColliderDesc.trimesh(vertices, indices).setCollisionGroups(groups(layer, 0xffff));
    return this.world.createCollider(desc);
  }

  addBox(center: Vector3, half: Vector3, layer: number = Layer.Terrain, yaw = 0): RAPIER.Collider {
    const q = { x: 0, y: Math.sin(yaw / 2), z: 0, w: Math.cos(yaw / 2) };
    const desc = RAPIER.ColliderDesc.cuboid(half.x, half.y, half.z)
      .setTranslation(center.x, center.y, center.z)
      .setRotation(q)
      .setCollisionGroups(groups(layer, 0xffff));
    return this.world.createCollider(desc);
  }

  removeCollider(collider: RAPIER.Collider): void {
    this.owners.delete(collider.handle);
    this.world.removeCollider(collider, false);
  }

  /**
   * キャラクター（カプセル）を作る。position はカプセルの足元。
   * collideWith に含めたレイヤーとだけぶつかる。
   */
  createCharacter(position: Vector3, radius: number, height: number, layer: number, collideWith: number): CharacterBody {
    const halfHeight = Math.max(0.01, height / 2 - radius);
    const desc = RAPIER.ColliderDesc.capsule(halfHeight, radius)
      .setTranslation(position.x, position.y + height / 2, position.z)
      .setCollisionGroups(groups(layer, collideWith));
    const collider = this.world.createCollider(desc);
    const controller = this.world.createCharacterController(0.02);
    controller.enableAutostep(0.35, 0.2, false);
    controller.enableSnapToGround(0.3);
    controller.setMaxSlopeClimbAngle((45 * Math.PI) / 180);
    controller.setMinSlopeSlideAngle((50 * Math.PI) / 180);
    controller.setSlideEnabled(true);
    return { collider, controller, radius, halfHeight };
  }

  /**
   * キャラクターを動かす。返り値は実際に動いた量と接地しているか。
   * filter はぶつかる相手のレイヤー。
   */
  moveCharacter(body: CharacterBody, delta: Vector3, filter: number, onGround = true): { moved: Vector3; grounded: boolean } {
    // 段差の自動乗り越えと地面への吸着は、接地中だけ有効にする（空中で段に引っかかって登れてしまうのを防ぐ）
    if (onGround) {
      body.controller.enableAutostep(0.35, 0.2, false);
      body.controller.enableSnapToGround(0.3);
    } else {
      body.controller.disableAutostep();
      body.controller.disableSnapToGround();
    }
    const membership = (body.collider.collisionGroups() >>> 16) & 0xffff;
    body.controller.computeColliderMovement(
      body.collider,
      { x: delta.x, y: delta.y, z: delta.z },
      RAPIER.QueryFilterFlags.EXCLUDE_SENSORS,
      groups(membership, filter),
    );
    const m = body.controller.computedMovement();
    if (!onGround) {
      // 空中では、カプセルの丸い底が段の角に乗り上げて押し上げられる分を打ち消す
      const maxUp = Math.max(delta.y, 0) + 1e-4;
      if (m.y > maxUp) m.y = maxUp;
    }
    const t = body.collider.translation();
    body.collider.setTranslation({ x: t.x + m.x, y: t.y + m.y, z: t.z + m.z });
    return { moved: new Vector3(m.x, m.y, m.z), grounded: body.controller.computedGrounded() };
  }

  /** キャラクターの足元の位置 */
  feetOf(body: CharacterBody, out = new Vector3()): Vector3 {
    const t = body.collider.translation();
    return out.set(t.x, t.y - body.halfHeight - body.radius, t.z);
  }

  setFeet(body: CharacterBody, feet: Vector3): void {
    body.collider.setTranslation({ x: feet.x, y: feet.y + body.halfHeight + body.radius, z: feet.z });
  }

  /** レイキャスト。filter に含めたレイヤーだけに当たる */
  raycast(origin: Vector3, dir: Vector3, maxDist: number, filter: number, exclude?: RAPIER.Collider): RayHit | null {
    const ray = new RAPIER.Ray({ x: origin.x, y: origin.y, z: origin.z }, { x: dir.x, y: dir.y, z: dir.z });
    const hit = this.world.castRayAndGetNormal(
      ray,
      maxDist,
      true,
      RAPIER.QueryFilterFlags.EXCLUDE_SENSORS,
      groups(0xffff, filter),
      exclude,
    );
    if (!hit) return null;
    const p = ray.pointAt(hit.timeOfImpact);
    return {
      distance: hit.timeOfImpact,
      point: new Vector3(p.x, p.y, p.z),
      normal: new Vector3(hit.normal.x, hit.normal.y, hit.normal.z),
      owner: this.owners.get(hit.collider.handle),
    };
  }
}

/** 箱の集まりから三角形メッシュのデータを作る（テストや仮の地形用） */
export function boxesToTrimesh(boxes: { center: Vector3; half: Vector3 }[]): { vertices: Float32Array; indices: Uint32Array } {
  const verts: number[] = [];
  const idx: number[] = [];
  for (const b of boxes) {
    const base = verts.length / 3;
    for (let i = 0; i < 8; i++) {
      verts.push(
        b.center.x + (i & 1 ? b.half.x : -b.half.x),
        b.center.y + (i & 2 ? b.half.y : -b.half.y),
        b.center.z + (i & 4 ? b.half.z : -b.half.z),
      );
    }
    const faces = [
      [0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5],
    ];
    for (const f of faces) {
      idx.push(base + f[0], base + f[1], base + f[2], base + f[0], base + f[2], base + f[3]);
    }
  }
  return { vertices: new Float32Array(verts), indices: new Uint32Array(idx) };
}
