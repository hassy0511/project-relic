import * as THREE from 'three';
import type { Game } from '../sim/game';

/** 宝箱、NPC、セーブビーコン、壊せる壁、拾える物の見た目 */
export class PropsView {
  private walls = new Map<string, THREE.Mesh>();
  private chests = new Map<string, { lid: THREE.Object3D; glow: THREE.PointLight }>();
  private beaconBeams: THREE.Mesh[] = [];
  private npcRoots = new Map<string, THREE.Group>();
  private pickups = new Map<object, THREE.Mesh>();
  private readonly group = new THREE.Group();

  constructor(scene: THREE.Object3D, game: Game) {
    scene.add(this.group);
    const crackTex = crackTexture();
    for (const b of game.breakables) {
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(b.size.x, b.size.y, b.size.z),
        new THREE.MeshStandardMaterial({ color: '#8c7b63', map: crackTex, roughness: 0.95 }),
      );
      mesh.position.copy(b.center);
      mesh.rotation.y = b.yaw;
      mesh.castShadow = mesh.receiveShadow = true;
      mesh.visible = !b.broken;
      this.group.add(mesh);
      this.walls.set(b.id, mesh);
    }
    for (const c of game.chests) {
      const root = new THREE.Group();
      root.position.copy(c.pos);
      root.rotation.y = c.yaw;
      const base = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.55, 0.8), new THREE.MeshStandardMaterial({ color: '#e9e3d6', roughness: 0.35 }));
      base.position.y = 0.275;
      const band = new THREE.Mesh(new THREE.BoxGeometry(1.22, 0.08, 0.82), new THREE.MeshStandardMaterial({ color: '#b08a4a', metalness: 0.6, roughness: 0.4 }));
      band.position.y = 0.45;
      const lidPivot = new THREE.Group();
      lidPivot.position.set(0, 0.55, -0.4);
      const lid = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.22, 0.8), new THREE.MeshStandardMaterial({ color: '#d9d2c3', roughness: 0.35 }));
      lid.position.set(0, 0.11, 0.4);
      lidPivot.add(lid);
      const glow = new THREE.PointLight('#ffb23e', c.opened ? 0 : 2, 3);
      glow.position.y = 1;
      root.add(base, band, lidPivot, glow);
      root.traverse((o) => ((o as THREE.Mesh).castShadow = true));
      if (c.opened) lidPivot.rotation.x = -1.9;
      this.group.add(root);
      this.chests.set(c.id, { lid: lidPivot, glow });
    }
    for (const n of game.npcs) {
      const root = new THREE.Group();
      root.position.copy(n.pos);
      root.rotation.y = n.yaw;
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 1.0, 4, 8), new THREE.MeshStandardMaterial({ color: '#7a5a3a' }));
      body.position.y = 0.8;
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 8), new THREE.MeshStandardMaterial({ color: '#d9a07a' }));
      head.position.y = 1.55;
      const apron = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.7, 0.05), new THREE.MeshStandardMaterial({ color: '#4d5a4a' }));
      apron.position.set(0, 0.8, 0.3);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.6, 0.12), new THREE.MeshStandardMaterial({ color: '#8a8a8a', metalness: 0.7, roughness: 0.3 }));
      arm.position.set(-0.4, 0.95, 0);
      root.add(body, head, apron, arm, nameTag(n.name));
      this.npcRoots.set(n.id, root);
      root.traverse((o) => ((o as THREE.Mesh).castShadow = true));
      this.group.add(root);
    }
    for (const b of game.beacons) {
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.7, 0.4, 12), new THREE.MeshStandardMaterial({ color: '#e9e3d6', roughness: 0.35 }));
      base.position.copy(b.pos).setY(b.pos.y + 0.2);
      const beam = new THREE.Mesh(
        new THREE.CylinderGeometry(0.25, 0.35, 12, 12, 1, true),
        new THREE.MeshBasicMaterial({ color: '#ffcf7a', transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide }),
      );
      beam.position.copy(b.pos).setY(b.pos.y + 6.2);
      this.beaconBeams.push(beam);
      this.group.add(base, beam);
    }
  }

  sync(game: Game, time: number, dt: number): void {
    for (const b of game.breakables) {
      const m = this.walls.get(b.id);
      if (!m) continue;
      m.visible = !b.broken;
      // ドリルで削られている間は震える
      const shaking = b.progress > 0 && !b.broken;
      m.position.x = b.center.x + (shaking ? Math.sin(time * 90) * 0.02 : 0);
    }
    for (const c of game.chests) {
      const v = this.chests.get(c.id);
      if (!v) continue;
      if (c.opened) {
        v.lid.rotation.x += (-1.9 - v.lid.rotation.x) * Math.min(1, dt * 8);
        v.glow.intensity = Math.max(0, v.glow.intensity - dt * 2);
      }
    }
    for (const n of game.npcs) {
      const r = this.npcRoots.get(n.id);
      if (r) {
        let d = n.yaw - r.rotation.y;
        d = Math.atan2(Math.sin(d), Math.cos(d));
        r.rotation.y += d * Math.min(1, dt * 8);
      }
    }
    for (const beam of this.beaconBeams) {
      (beam.material as THREE.MeshBasicMaterial).opacity = 0.25 + Math.sin(time * 2) * 0.08;
    }
    // 拾える物
    const alive = new Set<object>();
    for (const k of game.pickups) {
      alive.add(k);
      let m = this.pickups.get(k);
      if (!m) {
        const color = k.kind === 'cells' ? '#ffcf3a' : k.kind === 'energy' ? '#5ad1ff' : '#7dff8a';
        m = new THREE.Mesh(new THREE.OctahedronGeometry(k.kind === 'cells' ? 0.12 : 0.18), new THREE.MeshBasicMaterial({ color }));
        this.group.add(m);
        this.pickups.set(k, m);
      }
      m.position.copy(k.pos);
      m.position.y += Math.sin(time * 4 + k.age) * 0.05;
      m.rotation.y = time * 3;
    }
    for (const [k, m] of this.pickups) {
      if (!alive.has(k)) {
        this.group.remove(m);
        this.pickups.delete(k);
      }
    }
  }
}

function crackTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#b8a88e';
  ctx.fillRect(0, 0, 256, 256);
  ctx.strokeStyle = '#3a2e22';
  ctx.lineWidth = 5;
  // ドリルで壊せる印（稲妻状のひび）
  const lines = [
    [[128, 20], [110, 80], [140, 120], [100, 170], [130, 240]],
    [[110, 80], [60, 100], [30, 90]],
    [[140, 120], [200, 140], [235, 130]],
    [[100, 170], [60, 200]],
  ];
  for (const l of lines) {
    ctx.beginPath();
    ctx.moveTo(l[0][0], l[0][1]);
    for (const p of l.slice(1)) ctx.lineTo(p[0], p[1]);
    ctx.stroke();
  }
  ctx.strokeStyle = '#ffb23e';
  ctx.lineWidth = 2;
  ctx.strokeRect(8, 8, 240, 240);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function nameTag(text: string): THREE.Sprite {
  const c = document.createElement('canvas');
  c.width = 256;
  c.height = 64;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = 'rgba(20,16,12,0.6)';
  ctx.fillRect(0, 8, 256, 48);
  ctx.fillStyle = '#ffe7b8';
  ctx.font = 'bold 30px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 128, 33);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false }));
  s.scale.set(1.2, 0.3, 1);
  s.position.y = 2.1;
  return s;
}
