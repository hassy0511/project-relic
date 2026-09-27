import { Vector3 } from 'three';

export const DEG = Math.PI / 180;

export function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** 角度を -π〜π に正規化する */
export function wrapAngle(a: number): number {
  a = (a + Math.PI) % (Math.PI * 2);
  if (a < 0) a += Math.PI * 2;
  return a - Math.PI;
}

/** a から b へ、最短方向に最大 maxStep だけ角度を近づける */
export function approachAngle(a: number, b: number, maxStep: number): number {
  const d = wrapAngle(b - a);
  if (Math.abs(d) <= maxStep) return b;
  return a + Math.sign(d) * maxStep;
}

/** 値を目標に向けて一定量だけ近づける */
export function approach(v: number, target: number, step: number): number {
  if (v < target) return Math.min(v + step, target);
  return Math.max(v - step, target);
}

/** フレームレートに依存しない指数的な追従の係数 */
export function dampFactor(lambda: number, dt: number): number {
  return 1 - Math.exp(-lambda * dt);
}

/** y 軸まわりの向き（ラジアン）から、水平の前方向ベクトルを得る。yaw=0 で +Z を向く */
export function yawToDir(yaw: number, out = new Vector3()): Vector3 {
  return out.set(Math.sin(yaw), 0, Math.cos(yaw));
}

/** 水平ベクトルの向き（yaw）を得る */
export function dirToYaw(x: number, z: number): number {
  return Math.atan2(x, z);
}

export function horizontalDistance(a: Vector3, b: Vector3): number {
  const dx = a.x - b.x;
  const dz = a.z - b.z;
  return Math.sqrt(dx * dx + dz * dz);
}

/** 線分 p0→p1 と球（中心 c、半径 r）が交わるなら、線分上の位置 t（0〜1）を返す */
export function segmentSphere(p0: Vector3, p1: Vector3, c: Vector3, r: number): number | null {
  const dx = p1.x - p0.x, dy = p1.y - p0.y, dz = p1.z - p0.z;
  const fx = p0.x - c.x, fy = p0.y - c.y, fz = p0.z - c.z;
  const a = dx * dx + dy * dy + dz * dz;
  if (a < 1e-9) {
    return fx * fx + fy * fy + fz * fz <= r * r ? 0 : null;
  }
  const b = 2 * (fx * dx + fy * dy + fz * dz);
  const cc = fx * fx + fy * fy + fz * fz - r * r;
  if (cc <= 0) return 0;
  const disc = b * b - 4 * a * cc;
  if (disc < 0) return null;
  const t = (-b - Math.sqrt(disc)) / (2 * a);
  return t >= 0 && t <= 1 ? t : null;
}
