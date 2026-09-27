import * as THREE from 'three';
import type { Enemy } from '../sim/enemies/enemy';

/**
 * 番機の仮の見た目（MVP）。Codex の設定画が届いたら GLB に差し替える。
 * 先史の技術の見た目の仮決め：白い陶器のような外装、真鍮の継ぎ目、スリット状のセンサー。
 */
const PORCELAIN = new THREE.MeshStandardMaterial({ color: '#e9e3d6', roughness: 0.35 });
const BRASS = new THREE.MeshStandardMaterial({ color: '#b08a4a', roughness: 0.4, metalness: 0.6 });
const DARK = new THREE.MeshStandardMaterial({ color: '#3a3530', roughness: 0.7 });

interface Built {
  root: THREE.Group;
  body: THREE.Group;
  sensor: THREE.MeshBasicMaterial;
  core: THREE.MeshBasicMaterial;
  flashMats: THREE.MeshStandardMaterial[];
  alert: THREE.Sprite;
  legs: THREE.Object3D[];
}

function makeSentry(): Built {
  const root = new THREE.Group();
  const body = new THREE.Group();
  root.add(body);
  const shell = PORCELAIN.clone();
  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.45, 0.55, 10), shell);
  torso.position.y = 0.72;
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.38, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), shell);
  cap.position.y = 0.99;
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.04, 6, 16), BRASS);
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.5;
  const sensorMat = new THREE.MeshBasicMaterial({ color: '#ffb23e' });
  const sensor = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.05, 0.05), sensorMat);
  sensor.position.set(0, 0.9, 0.36);
  const gun = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.3, 8), DARK);
  gun.rotation.x = Math.PI / 2;
  gun.position.set(0, 0.7, 0.45);
  const coreMat = new THREE.MeshBasicMaterial({ color: '#ffcf7a' });
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 8), coreMat);
  core.position.set(0, 0.75, -0.42);
  body.add(torso, cap, ring, sensor, gun, core);
  const legs: THREE.Object3D[] = [];
  for (let i = 0; i < 3; i++) {
    const a = (i / 3) * Math.PI * 2;
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.55, 0.09), BRASS);
    leg.position.set(Math.sin(a) * 0.3, 0.27, Math.cos(a) * 0.3);
    leg.rotation.set(Math.cos(a) * 0.35, 0, -Math.sin(a) * 0.35);
    legs.push(leg);
    root.add(leg);
  }
  return { root, body, sensor: sensorMat, core: coreMat, flashMats: [shell], alert: makeAlert(1.6), legs };
}

function makeCharger(): Built {
  const root = new THREE.Group();
  const body = new THREE.Group();
  root.add(body);
  const shell = PORCELAIN.clone();
  const hull = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.7, 1.7), shell);
  hull.position.y = 0.65;
  const ram = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.5, 0.35), BRASS);
  ram.position.set(0, 0.6, 0.95);
  const horn = new THREE.Mesh(new THREE.ConeGeometry(0.18, 0.5, 6), BRASS);
  horn.rotation.x = Math.PI / 2;
  horn.position.set(0, 0.65, 1.3);
  const sensorMat = new THREE.MeshBasicMaterial({ color: '#ffb23e' });
  const sensor = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.06, 0.05), sensorMat);
  sensor.position.set(0, 0.95, 0.86);
  const coreMat = new THREE.MeshBasicMaterial({ color: '#ffcf7a' });
  const coreL = new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 8), coreMat);
  coreL.position.set(0.56, 0.65, 0);
  const coreR = coreL.clone();
  coreR.position.x = -0.56;
  body.add(hull, ram, horn, sensor, coreL, coreR);
  const legs: THREE.Object3D[] = [];
  for (const [x, z] of [[0.45, 0.55], [-0.45, 0.55], [0.45, -0.55], [-0.45, -0.55]]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.4, 0.16), DARK);
    leg.position.set(x, 0.2, z);
    legs.push(leg);
    root.add(leg);
  }
  return { root, body, sensor: sensorMat, core: coreMat, flashMats: [shell], alert: makeAlert(1.9), legs };
}

function makeAlert(height: number): THREE.Sprite {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#ffcc33';
  ctx.font = 'bold 56px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('!', 32, 34);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false }));
  s.scale.setScalar(0.6);
  s.position.y = height;
  s.visible = false;
  return s;
}

export class EnemyView {
  private built = new Map<Enemy, Built>();

  constructor(private readonly scene: THREE.Object3D) {}

  sync(enemies: Enemy[], time: number): void {
    for (const e of enemies) {
      let b = this.built.get(e);
      if (!b) {
        b = e.kind === 'charger' ? makeCharger() : makeSentry();
        b.root.add(b.alert);
        b.root.traverse((o) => ((o as THREE.Mesh).castShadow = true));
        this.scene.add(b.root);
        this.built.set(e, b);
      }
      if (!e.alive) {
        // 撃破：少し沈んで消える
        b.root.visible = e.deadTime < 0.3;
        b.root.scale.setScalar(Math.max(0.01, 1 - e.deadTime * 3));
        continue;
      }
      b.root.position.copy(e.pos);
      b.root.rotation.y = e.yaw;
      // 通常は琥珀、警戒・攻撃中は赤みを帯びる
      const hostile = e.state !== 'idle';
      b.sensor.color.set(hostile ? '#ff5a2a' : '#ffb23e');
      // 予備動作：核とセンサーが明滅する（避ける合図）
      const tele = e.telegraphing ? 0.5 + 0.5 * Math.sin(time * 40) : 0;
      b.core.color.setRGB(1, 0.8 - tele * 0.5, 0.48 - tele * 0.4);
      for (const m of b.flashMats) m.emissive.setRGB(e.flash, e.flash * 0.9, e.flash * 0.7);
      b.alert.visible = e.alerting;
      // 歩きの揺れ
      const moving = Math.hypot(e.vel.x, e.vel.z) > 0.3;
      b.body.position.y = moving ? Math.abs(Math.sin(time * 12)) * 0.05 : 0;
      b.body.rotation.z = e.state === 'stunned' ? Math.sin(time * 30) * 0.08 : 0;
      b.legs.forEach((l, i) => (l.rotation.x = moving ? Math.sin(time * 12 + i * 2) * 0.4 : 0));
    }
  }
}
