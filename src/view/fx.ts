import * as THREE from 'three';
import type { GameEvent } from '../core/events';
import type { Game } from '../sim/game';
import type { Shot } from '../sim/projectiles';

interface Particle {
  mesh: THREE.Mesh;
  vel: THREE.Vector3;
  life: number;
  maxLife: number;
  grow: number;
}

const SHOT_COLORS: Record<string, string> = {
  normal: '#ffd27a',
  charge1: '#ffe7a8',
  charge2: '#ffffff',
  wave: '#ffcf7a',
  enemy: '#ff9a5a',
};

/** 弾、火花、爆発、斬撃の軌跡、画面の揺れ */
export class Fx {
  private shots = new Map<Shot, THREE.Mesh>();
  private particles: Particle[] = [];
  private readonly group = new THREE.Group();
  private sparkGeo = new THREE.OctahedronGeometry(0.06);
  private ballGeo = new THREE.SphereGeometry(1, 10, 8);
  private slash: THREE.Mesh;
  private slashLife = 0;
  shake = 0;

  constructor(scene: THREE.Object3D) {
    scene.add(this.group);
    const arc = new THREE.RingGeometry(1.2, 2.2, 24, 1, -Math.PI * 0.35, Math.PI * 0.7);
    arc.rotateX(-Math.PI / 2);
    this.slash = new THREE.Mesh(
      arc,
      new THREE.MeshBasicMaterial({ color: '#ffe2a0', transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }),
    );
    this.group.add(this.slash);
  }

  handle(e: GameEvent): void {
    switch (e.type) {
      case 'hit': {
        const color = e.kind === 'weak' ? '#fff3b0' : e.kind === 'armor' ? '#c8c0b0' : '#ffb23e';
        const n = e.kind === 'weak' ? 14 : e.kind === 'armor' ? 3 : 7;
        this.burst(new THREE.Vector3(e.x, e.y, e.z), color, n, e.kind === 'weak' ? 6 : 4, 0.25);
        break;
      }
      case 'enemyDestroyed':
        this.burst(new THREE.Vector3(e.x, e.y, e.z), '#ffcf7a', 26, 8, 0.6);
        this.flashBall(new THREE.Vector3(e.x, e.y, e.z), '#ffe0a0', 1.4, 0.3);
        break;
      case 'shake':
        this.shake = Math.max(this.shake, e.strength);
        break;
      default:
        break;
    }
  }

  private burst(at: THREE.Vector3, color: string, n: number, speed: number, life: number): void {
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true });
    for (let i = 0; i < n; i++) {
      const m = new THREE.Mesh(this.sparkGeo, mat);
      m.position.copy(at);
      const v = new THREE.Vector3(Math.random() - 0.5, Math.random() * 0.8, Math.random() - 0.5).normalize().multiplyScalar(speed * (0.4 + Math.random()));
      this.group.add(m);
      this.particles.push({ mesh: m, vel: v, life, maxLife: life, grow: 0 });
    }
  }

  private flashBall(at: THREE.Vector3, color: string, size: number, life: number): void {
    const m = new THREE.Mesh(this.ballGeo, new THREE.MeshBasicMaterial({ color, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    m.position.copy(at);
    m.scale.setScalar(size * 0.3);
    this.group.add(m);
    this.particles.push({ mesh: m, vel: new THREE.Vector3(), life, maxLife: life, grow: size * 3 });
  }

  sync(game: Game, dt: number): void {
    // 弾
    const alive = new Set<Shot>();
    for (const s of game.shots) {
      alive.add(s);
      let m = this.shots.get(s);
      if (!m) {
        m = new THREE.Mesh(this.ballGeo, new THREE.MeshBasicMaterial({ color: SHOT_COLORS[s.spec.kind] ?? '#fff' }));
        // 見た目は当たり判定より小さめにして、明るい芯＋光の輪で描く
        const VIS: Record<string, number> = { normal: 0.07, charge1: 0.16, charge2: 0.32, wave: 0.35, enemy: 0.12 };
        const r = VIS[s.spec.kind] ?? 0.1;
        // 弾は進行方向に伸びた光の筋として描く
        m.scale.set(r, r, s.spec.kind === 'wave' ? r * 0.4 : r * (s.spec.kind === 'normal' ? 6 : 3));
        const halo = new THREE.Mesh(
          this.ballGeo,
          new THREE.MeshBasicMaterial({ color: SHOT_COLORS[s.spec.kind] ?? '#fff', transparent: true, opacity: 0.35, depthWrite: false, blending: THREE.AdditiveBlending }),
        );
        halo.scale.set(2.2, 2.2, 1.2);
        (halo.material as THREE.MeshBasicMaterial).opacity = 0.28;
        m.add(halo);
        this.group.add(m);
        this.shots.set(s, m);
      }
      m.position.copy(s.pos);
      m.lookAt(s.pos.clone().add(s.vel));
      if (s.spec.kind === 'wave') m.scale.x = 1.4;
    }
    for (const [s, m] of this.shots) {
      if (!alive.has(s)) {
        this.group.remove(m);
        (m.material as THREE.Material).dispose();
        ((m.children[0] as THREE.Mesh | undefined)?.material as THREE.Material | undefined)?.dispose();
        this.shots.delete(s);
      }
    }

    // 粒子
    for (const p of this.particles) {
      p.life -= dt;
      p.vel.y -= 9 * dt;
      p.mesh.position.addScaledVector(p.vel, dt);
      if (p.grow) p.mesh.scale.addScalar(p.grow * dt);
      (p.mesh.material as THREE.MeshBasicMaterial).opacity = Math.max(0, p.life / p.maxLife);
    }
    this.particles = this.particles.filter((p) => {
      if (p.life > 0) return true;
      this.group.remove(p.mesh);
      return false;
    });

    // 斬撃の軌跡
    const pl = game.player;
    const a = pl.attack;
    if (a && a.time >= a.activeFrom * 0.8 && a.time <= a.activeTo) {
      this.slashLife = 0.12;
      this.slash.position.copy(pl.pos).setY(pl.pos.y + (a.move === 'combo3' ? 1.0 : 1.05));
      const sweep = a.move === 'combo2' ? -1 : 1;
      this.slash.rotation.set(a.move === 'combo3' ? Math.PI / 2 : 0, pl.yaw + sweep * (a.time / a.duration - 0.5) * 1.2, 0);
      const s = a.move === 'charge' ? 1.6 : 1;
      this.slash.scale.setScalar(s);
    }
    this.slashLife = Math.max(0, this.slashLife - dt);
    (this.slash.material as THREE.MeshBasicMaterial).opacity = this.slashLife * 6;

    this.shake = Math.max(0, this.shake - dt * 2.5);
  }
}
