import * as THREE from 'three';
import { DEG } from '../core/math';
import { Layer } from '../physics/physics';
import type { Game } from '../sim/game';

/**
 * カメラの実際の位置を決める。向き（yaw・pitch）は sim が持ち、
 * ここでは壁への衝突回避、ロックオン時の画面の収め方、揺れを担当する。
 */
export class CameraRig {
  private dist = 5.5;
  private pivot = new THREE.Vector3();
  private initialized = false;

  constructor(private readonly camera: THREE.PerspectiveCamera) {}

  update(game: Game, playerPos: THREE.Vector3, dt: number, shake: number): void {
    const c = game.tuning.camera;
    const yaw = game.cam.yaw;
    const pitch = game.cam.pitch;

    const wantPivot = playerPos.clone().setY(playerPos.y + c.pivotHeight);
    const target = game.lockOnPoint();
    if (target) {
      // プレイヤーと対象の中間より、少しプレイヤー寄りを注視する
      wantPivot.lerp(target, 0.3);
      wantPivot.y = Math.min(wantPivot.y, playerPos.y + c.pivotHeight + 1);
    }
    if (!this.initialized) {
      this.pivot.copy(wantPivot);
      this.initialized = true;
    }
    this.pivot.lerp(wantPivot, 1 - Math.exp(-14 * dt));

    const back = new THREE.Vector3(-Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), -Math.cos(yaw) * Math.cos(pitch));
    let want = c.distance;
    if (target) want += Math.min(2, this.pivot.distanceTo(target) * 0.1);

    // 壁の手前にカメラを寄せる
    const hit = game.physics.raycast(this.pivot, back, want + 0.3, Layer.Terrain | Layer.Breakable);
    if (hit) want = Math.max(c.minDistance, hit.distance - 0.3);
    // 近づくのは素早く、離れるのはゆっくり
    this.dist += (want - this.dist) * (want < this.dist ? 1 : 1 - Math.exp(-4 * dt));

    this.camera.position.copy(this.pivot).addScaledVector(back, this.dist);
    if (shake > 0) {
      const t = performance.now() / 1000;
      this.camera.position.x += Math.sin(t * 73) * shake * 0.15;
      this.camera.position.y += Math.sin(t * 91) * shake * 0.15;
    }
    this.camera.lookAt(this.pivot);
    this.camera.fov = c.fov;
    this.camera.updateProjectionMatrix();
  }

  /** カメラの正面方向（弾の向きの表示などに使う） */
  forward(): THREE.Vector3 {
    return new THREE.Vector3(0, 0, -1).applyQuaternion(this.camera.quaternion);
  }
}

export const CAMERA_DEFAULT_PITCH = 12 * DEG;
