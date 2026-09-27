import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import type { Player, PlayerAnim } from '../sim/player';
import { aimRightArm, CharacterLook, PoseOverride, type Shading } from './characterLook';

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
  private blade: THREE.Object3D;
  private bladeMat: THREE.MeshStandardMaterial | THREE.MeshBasicMaterial;
  private chargeGlow: THREE.Mesh;
  private look: CharacterLook | null = null;
  private override: PoseOverride | null = null;
  private expression = -1;
  /** 銃口の目印（モデルにあれば、溜めの光をここに付ける） */
  private muzzle: THREE.Object3D | null = null;
  private flashTime = 0;
  private visualYaw = 0;
  private meshes: THREE.Mesh[] = [];

  constructor(parent: THREE.Object3D) {
    parent.add(this.root);
    // 光刃（モデルに刃がないときの代わり。左手から出す）
    const bladeGeo = new THREE.BoxGeometry(0.05, 0.9, 0.02);
    bladeGeo.translate(0, -0.5, 0);
    this.bladeMat = new THREE.MeshBasicMaterial({ color: '#ffd27a', transparent: true, opacity: 0.9 });
    this.blade = new THREE.Mesh(bladeGeo, this.bladeMat);
    this.blade.visible = false;
    this.chargeGlow = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 12, 8),
      new THREE.MeshBasicMaterial({ color: '#ffb23e', transparent: true, opacity: 0.8, depthWrite: false }),
    );
    this.chargeGlow.visible = false;
    this.root.add(this.chargeGlow);
  }

  async load(url: string, shading: Shading = 'soft'): Promise<void> {
    try {
      const gltf = await new GLTFLoader().loadAsync(url);
      const model = gltf.scene;
      const look = new CharacterLook(model);
      this.look = look;
      look.setShading(shading);
      const modelBlade = look.nodes.get('LightBlade');
      for (const m of look.meshes) {
        m.castShadow = true;
        m.receiveShadow = true;
        // 光刃は別に表示を切り替えるので、点滅の対象から外す
        if (m !== modelBlade) this.meshes.push(m);
      }
      this.rightArm = look.bones.get('upper_armR') ?? null;
      this.rightForearm = look.bones.get('forearmR') ?? null;
      this.chest = look.bones.get('chest') ?? null;
      this.muzzle = look.nodes.get('muzzle') ?? null;
      if (modelBlade) {
        modelBlade.castShadow = false;
        this.blade = modelBlade;
        this.bladeMat = (modelBlade as THREE.Mesh).material as THREE.MeshStandardMaterial;
        this.blade.visible = false;
      } else {
        // 光刃は走査のあとで付ける（走査中に付けると点滅の対象に紛れ込むため）
        look.bones.get('handL')?.add(this.blade);
      }
      if (this.muzzle) {
        this.muzzle.add(this.chargeGlow);
        this.chargeGlow.position.set(0, 0, 0);
      }
      this.override = new PoseOverride([this.rightArm, this.rightForearm, this.chest].filter((b): b is THREE.Bone => !!b));
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
    this.override?.restore();
    this.mixer?.update(dt);
    this.override?.capture();

    // 撃っている間は右腕を照準へ向ける（上半身と下半身の分離の代わり）
    if (aimDir && this.rightArm && this.rightForearm && p.aiming > 0 && !p.attack) {
      const local = aimDir.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), -this.visualYaw);
      const pitch = Math.asin(THREE.MathUtils.clamp(local.y, -0.8, 0.8));
      const yaw = Math.atan2(local.x, local.z);
      const w = Math.min(1, p.aiming * 4);
      // 上腕を前へ振り上げて照準の高さに合わせる
      aimRightArm(this.rightArm, this.rightForearm, this.restArm, this.restForearm, pitch, w);
      if (this.chest) this.chest.rotateY(yaw * 0.5 * w);
    }

    // 光刃は攻撃中だけ出す
    this.blade.visible = p.attack !== null || p.swordHold > 0.25;
    const charged = p.swordHold >= 0.7;
    if ((this.bladeMat as THREE.MeshStandardMaterial).isMeshStandardMaterial) {
      (this.bladeMat as THREE.MeshStandardMaterial).emissiveIntensity = charged ? 3 : 1;
    } else this.bladeMat.color.set(charged ? '#fff4d0' : '#ffd27a');
    this.blade.scale.setScalar(p.swordHold > 0.25 && !p.attack ? 0.6 : 1);

    // 表情：被弾と倒れたときは痛みの顔
    const expr = p.dead || p.anim === 'hurt' ? 3 : 0;
    if (expr !== this.expression && this.look) {
      this.look.setExpression(expr);
      this.expression = expr;
    }

    // チャージの光
    this.chargeGlow.visible = p.gunCharge > 0.15;
    if (this.chargeGlow.visible) {
      const lv = p.gunCharge >= 1.2 ? 2 : p.gunCharge >= 0.6 ? 1 : 0;
      const s = 0.6 + lv * 0.5 + Math.sin(performance.now() / 50) * 0.1;
      this.chargeGlow.scale.setScalar(s);
      if (!this.muzzle) this.chargeGlow.position.set(-0.3, 1.1, 0.45);
      (this.chargeGlow.material as THREE.MeshBasicMaterial).color.set(lv === 2 ? '#ffffff' : lv === 1 ? '#ffd27a' : '#ffb23e');
    }

    // 被弾後の無敵時間は点滅
    this.flashTime += dt;
    const blink = p.invuln > 0 && !p.dead && Math.floor(this.flashTime * 20) % 2 === 0;
    for (const m of this.meshes) m.visible = !blink;
  }
}
