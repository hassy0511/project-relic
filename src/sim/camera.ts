import { DEG, approachAngle, clamp, dampFactor, dirToYaw, wrapAngle } from '../core/math';
import type { Tuning } from '../content/tuning';
import type { InputFrame } from './inputFrame';

/**
 * カメラの向き（yaw・pitch）。移動の向きに関わるので sim が持つ。
 * 実際のカメラ位置（壁の回避など）は view が決める。
 * yaw は「カメラが見ている水平方向」。yaw=0 で +Z を見る。
 */
export class CameraOrbit {
  yaw = Math.PI;
  pitch = 12 * DEG;
  private idleLook = 0;
  private recentering = 0;

  constructor(private readonly t: Tuning) {
    this.pitch = t.camera.defaultPitch * DEG;
  }

  applyLook(input: InputFrame): void {
    const c = this.t.camera;
    this.yaw = wrapAngle(this.yaw - input.lookX * c.sensitivityX);
    this.pitch = clamp(this.pitch + input.lookY * c.sensitivityY, c.minPitch * DEG, c.maxPitch * DEG);
    if (input.lookActive) {
      this.idleLook = 0;
      this.recentering = 0;
    }
  }

  /** プレイヤーの背後へ素早く回す（ロックオン対象がないときのロックオンボタン、R3） */
  requestRecenter(): void {
    this.recentering = 0.35;
  }

  update(
    dt: number,
    player: { x: number; z: number; yaw: number; speed: number },
    target: { x: number; z: number } | null,
  ): void {
    const c = this.t.camera;
    this.idleLook += dt;
    if (target) {
      // ロックオン中：プレイヤーの後ろから対象を見る向きへ寄せる
      const want = dirToYaw(target.x - player.x, target.z - player.z);
      this.yaw = wrapAngle(this.yaw + wrapAngle(want - this.yaw) * dampFactor(c.lockOnYawSpeed, dt));
      this.pitch += (c.defaultPitch * DEG - this.pitch) * dampFactor(3, dt);
      return;
    }
    if (this.recentering > 0) {
      this.recentering -= dt;
      this.yaw = wrapAngle(this.yaw + wrapAngle(player.yaw - this.yaw) * dampFactor(14, dt));
      this.pitch += (c.defaultPitch * DEG - this.pitch) * dampFactor(10, dt);
      return;
    }
    if (this.idleLook > c.autoRecenterDelay && player.speed > 2) {
      // 操作がしばらくないときは、移動の向きの背後へゆっくり回る
      const rate = c.autoRecenterSpeed * clamp(player.speed / 7, 0, 1) * dt;
      this.yaw = approachAngle(this.yaw, player.yaw, rate);
    }
  }
}
