import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import type { Player, PlayerAnim } from '../sim/player';

const LOOPING: Record<string, boolean> = { idle: true, run: true, fall: true, drill: true };
const FADE: Partial<Record<PlayerAnim, number>> = { combo1: 0.05, combo2: 0.05, combo3: 0.05, air: 0.05, lunge: 0.05, charge: 0.05, dash: 0.06, hurt: 0.05 };

/**
 * ハルの見た目。sim の状態（anim）に合わせてアニメーションを切り替え、
 * 撃っている間は右腕を手続き的に照準の方向へ向ける。
 */
export class PlayerView {
  readonly root = new THREE.Group();
  private mixer: THREE.AnimationMixer | null = null;
  private actions = new Map<string, THREE.AnimationAction>();
  private current = '';
  private rightArm: THREE.Bone | null = null;
  private rightForearm: THREE.Bone | null = null;
  private chest: THREE.Bone | null = null;
  private restArm = new THREE.Quaternion();
  private restForearm = new THREE.Quaternion();
  private blade: THREE.Mesh;
  private chargeGlow: THREE.Mesh;
  private flashTime = 0;
  private visualYaw = 0;
  private meshes: THREE.Mesh[] = [];

  constructor(parent: THREE.Object3D) {
    parent.add(this.root);
    // 光刃（左腕の先から出る刃）
    const bladeGeo = new THREE.BoxGeometry(0.05, 0.9, 0.02);
    bladeGeo.translate(0, -0.5, 0);
    this.blade = new THREE.Mesh(bladeGeo, new THREE.MeshBasicMaterial({ color: '#ffd27a', transparent: true, opacity: 0.9 }));
    this.blade.visible = false;
    this.chargeGlow = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 12, 8),
      new THREE.MeshBasicMaterial({ color: '#ffb23e', transparent: true, opacity: 0.8, depthWrite: false }),
    );
    this.chargeGlow.visible = false;
    this.root.add(this.chargeGlow);
  }

  async load(url: string): Promise<void> {
    try {
      const gltf = await new GLTFLoader().loadAsync(url);
      const model = gltf.scene;
      let leftHand: THREE.Bone | null = null as THREE.Bone | null;
      model.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh) {
          m.castShadow = true;
          m.receiveShadow = true;
          this.meshes.push(m);
        }
        const b = o as THREE.Bone;
        if (b.isBone) {
          if (b.name === 'upper_armR') this.rightArm = b;
          if (b.name === 'forearmR') this.rightForearm = b;
          if (b.name === 'chest') this.chest = b;
          if (b.name === 'handL') leftHand = b;
        }
      });
      // 光刃は走査のあとで付ける（走査中に付けると点滅の対象に紛れ込むため）
      leftHand?.add(this.blade);
      if (this.rightArm) this.restArm.copy(this.rightArm.quaternion);
      if (this.rightForearm) this.restForearm.copy(this.rightForearm.quaternion);
      this.root.add(model);
      this.mixer = new THREE.AnimationMixer(model);
      for (const clip of gltf.animations) {
        const a = this.mixer.clipAction(clip);
        if (!LOOPING[clip.name]) {
          a.setLoop(THREE.LoopOnce, 1);
          a.clampWhenFinished = true;
        }
        this.actions.set(clip.name, a);
      }
      this.play('idle', 0);
    } catch (e) {
      console.warn('ハルのモデルを読み込めなかったので、仮の形で表示します', e);
      const capsule = new THREE.Mesh(new THREE.CapsuleGeometry(0.35, 0.85, 4, 8), new THREE.MeshStandardMaterial({ color: '#c9a46a' }));
      capsule.position.y = 0.775;
      capsule.castShadow = true;
      this.root.add(capsule);
      this.meshes.push(capsule);
    }
  }

  private play(name: string, fade: number): void {
    if (name === this.current) return;
    const next = this.actions.get(name);
    if (!next) return;
    const prev = this.actions.get(this.current);
    next.reset();
    next.setEffectiveWeight(1);
    next.play();
    if (prev) prev.crossFadeTo(next, fade, false);
    this.current = name;
  }

  update(p: Player, alphaPos: THREE.Vector3, dt: number, aimDir: THREE.Vector3 | null): void {
    this.root.position.copy(alphaPos);
    // 向きは見た目だけ少し滑らかにする
    let d = p.yaw - this.visualYaw;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    this.visualYaw += d * Math.min(1, dt * 20);
    this.root.rotation.y = this.visualYaw;

    const anim = p.anim;
    this.play(anim, FADE[anim] ?? 0.15);
    const run = this.actions.get('run');
    if (run && anim === 'run') run.timeScale = Math.max(0.6, p.speed / 7);
    this.mixer?.update(dt);

    // 撃っている間は右腕を照準へ向ける（上半身と下半身の分離の代わり）
    if (aimDir && this.rightArm && this.rightForearm && p.aiming > 0 && !p.attack) {
      const local = aimDir.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), -this.visualYaw);
      const pitch = Math.asin(THREE.MathUtils.clamp(local.y, -0.8, 0.8));
      const yaw = Math.atan2(local.x, local.z);
      const w = Math.min(1, p.aiming * 4);
      // 骨の回転は「休止時の回転 × ポーズの回転」。上腕を前へ振り上げて照準の高さに合わせる
      const aimQ = this.restArm.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2 - pitch * 0.9, 0, 0)));
      this.rightArm.quaternion.slerp(aimQ, w);
      this.rightForearm.quaternion.slerp(this.restForearm, w);
      if (this.chest) this.chest.rotateY(yaw * 0.5 * w);
    }

    // 光刃は攻撃中だけ出す
    this.blade.visible = p.attack !== null || p.swordHold > 0.25;
    const bm = this.blade.material as THREE.MeshBasicMaterial;
    bm.color.set(p.swordHold >= 0.7 ? '#fff4d0' : '#ffd27a');
    this.blade.scale.set(1, p.swordHold > 0.25 && !p.attack ? 0.6 : 1, 1);

    // チャージの光
    this.chargeGlow.visible = p.gunCharge > 0.15;
    if (this.chargeGlow.visible) {
      const lv = p.gunCharge >= 1.2 ? 2 : p.gunCharge >= 0.6 ? 1 : 0;
      const s = 0.6 + lv * 0.5 + Math.sin(performance.now() / 50) * 0.1;
      this.chargeGlow.scale.setScalar(s);
      this.chargeGlow.position.set(-0.3, 1.1, 0.45);
      (this.chargeGlow.material as THREE.MeshBasicMaterial).color.set(lv === 2 ? '#ffffff' : lv === 1 ? '#ffd27a' : '#ffb23e');
    }

    // 被弾後の無敵時間は点滅
    this.flashTime += dt;
    const blink = p.invuln > 0 && !p.dead && Math.floor(this.flashTime * 20) % 2 === 0;
    for (const m of this.meshes) m.visible = !blink;
  }
}
