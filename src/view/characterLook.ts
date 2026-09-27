import * as THREE from 'three';

/**
 * キャラクターの見た目の共通処理（ゲームと見た目確認ページの両方で使う）。
 * - 塗り方の切り替え：soft（読み込んだままの標準の陰影）／toon（3 段の塗り分け）
 * - 顔の表情：顔のテクスチャ（2×2 の 4 表情）のずらし量で切り替える
 * - 撃つときに右腕を照準へ向ける
 */
export type Shading = 'soft' | 'toon';

export const EXPRESSIONS = ['normal', 'smile', 'surprise', 'pain'] as const;
export type Expression = (typeof EXPRESSIONS)[number];

let toonGradient: THREE.DataTexture | null = null;

/**
 * 輪郭の光（リムライト）。視線と面がすれ違う縁だけを、暖かい色で少し明るくする。
 * 赤い砂など、服と似た色の背景の前でも人物の輪郭が読めるようにするため。全キャラクターで共有
 */
export const rimUniforms = {
  rimColor: { value: new THREE.Color('#ffe2b8') },
  rimStrength: { value: 0.45 },
};

function addRim(mat: THREE.Material): void {
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.rimColor = rimUniforms.rimColor;
    shader.uniforms.rimStrength = rimUniforms.rimStrength;
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', 'uniform vec3 rimColor;\nuniform float rimStrength;\nvoid main() {')
      .replace(
        '#include <emissivemap_fragment>',
        `#include <emissivemap_fragment>
        float rimF = 1.0 - saturate(dot(normal, normalize(vViewPosition)));
        totalEmissiveRadiance += rimColor * smoothstep(0.62, 1.0, rimF) * rimStrength;`,
      );
  };
  mat.customProgramCacheKey = () => 'rim';
  mat.needsUpdate = true;
}

/** 3 段の明るさ（暗・中・明）。境目はくっきり */
function gradient(): THREE.DataTexture {
  if (toonGradient) return toonGradient;
  const steps = [110, 190, 255];
  const data = new Uint8Array(steps.length * 4);
  steps.forEach((v, i) => data.set([v, v, v, 255], i * 4));
  toonGradient = new THREE.DataTexture(data, steps.length, 1, THREE.RGBAFormat);
  toonGradient.minFilter = THREE.NearestFilter;
  toonGradient.magFilter = THREE.NearestFilter;
  toonGradient.generateMipmaps = false;
  toonGradient.needsUpdate = true;
  return toonGradient;
}

interface MatPair {
  soft: THREE.Material;
  toon: THREE.MeshToonMaterial;
}

export class CharacterLook {
  private pairs = new Map<THREE.Mesh, MatPair[]>();
  private faceMaps: THREE.Texture[] = [];
  readonly meshes: THREE.Mesh[] = [];
  readonly bones = new Map<string, THREE.Bone>();
  readonly nodes = new Map<string, THREE.Object3D>();
  shading: Shading = 'soft';

  constructor(readonly model: THREE.Object3D) {
    model.traverse((o) => {
      this.nodes.set(o.name, o);
      if ((o as THREE.Bone).isBone) this.bones.set(o.name, o as THREE.Bone);
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      this.meshes.push(m);
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      this.pairs.set(
        m,
        mats.map((soft) => {
          const toon = toToon(soft as THREE.MeshStandardMaterial);
          // 光刃（自分で光る半透明の刃）には輪郭の光を付けない
          if (!soft.transparent) {
            addRim(soft);
            addRim(toon);
          }
          return { soft, toon };
        }),
      );
      for (const mat of mats) {
        const map = (mat as THREE.MeshStandardMaterial).map;
        if (mat.name.includes('face') && map) {
          map.matrixAutoUpdate = true;
          this.faceMaps.push(map);
        }
      }
    });
  }

  get hasFace(): boolean {
    return this.faceMaps.length > 0;
  }

  setShading(mode: Shading): void {
    this.shading = mode;
    for (const [mesh, pairs] of this.pairs) {
      const mats = pairs.map((p) => (mode === 'toon' ? p.toon : p.soft));
      mesh.material = mats.length === 1 ? mats[0] : mats;
    }
  }

  setExpression(e: Expression | number): void {
    const i = typeof e === 'number' ? e : EXPRESSIONS.indexOf(e);
    for (const map of this.faceMaps) map.offset.set((i % 2) * 0.5, Math.floor(i / 2) * 0.5);
  }

  /** 描画に関わる数（3 角形、描画の呼び出し回数の目安、材質、テクスチャ） */
  stats(): { triangles: number; meshes: number; materials: number; textures: number; drawCalls: number } {
    let triangles = 0;
    let drawCalls = 0;
    const mats = new Set<THREE.Material>();
    const texs = new Set<THREE.Texture>();
    for (const m of this.meshes) {
      const g = m.geometry;
      triangles += (g.index ? g.index.count : g.attributes.position.count) / 3;
      const list = Array.isArray(m.material) ? m.material : [m.material];
      drawCalls += Math.max(1, g.groups.length || 1);
      for (const mat of list) {
        mats.add(mat);
        const sm = mat as THREE.MeshStandardMaterial;
        for (const t of [sm.map, sm.emissiveMap, sm.normalMap]) if (t) texs.add(t);
      }
    }
    return { triangles, meshes: this.meshes.length, materials: mats.size, textures: texs.size, drawCalls };
  }
}

function toToon(src: THREE.MeshStandardMaterial): THREE.MeshToonMaterial {
  const t = new THREE.MeshToonMaterial({
    name: src.name,
    color: src.color,
    map: src.map,
    emissive: src.emissive,
    emissiveMap: src.emissiveMap,
    emissiveIntensity: src.emissiveIntensity,
    transparent: src.transparent,
    opacity: src.opacity,
    side: src.side,
    gradientMap: gradient(),
  });
  return t;
}

/**
 * 右腕を照準へ向ける。bone の回転は「休止時の回転 × ポーズの回転」。
 * pitch は上向きが正（ラジアン）。w は 0〜1 の効き具合
 */
export function aimRightArm(
  arm: THREE.Bone,
  forearm: THREE.Bone,
  restArm: THREE.Quaternion,
  restForearm: THREE.Quaternion,
  pitch: number,
  w: number,
): void {
  const aimQ = restArm.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2 - pitch * 0.9, 0, 0)));
  arm.quaternion.slerp(aimQ, w);
  forearm.quaternion.slerp(restForearm, w);
}

/**
 * アニメーションの上から手で動かす骨（照準の腕、胸のひねり）の後始末。
 * three.js の AnimationMixer は、動作の値が前のフレームと同じだと骨を書き換えない。
 * そのため手で動かした骨をそのままにすると、構えをやめても腕が戻らない（胸のひねりは毎フレーム積み重なる）。
 * mixer.update の直前に restore()、直後（手で動かす前）に capture() を呼ぶ。
 */
export class PoseOverride {
  private saved: THREE.Quaternion[];

  constructor(private readonly bones: THREE.Object3D[]) {
    this.saved = bones.map((b) => b.quaternion.clone());
  }

  /** mixer.update の前：アニメーションが最後に書いた値へ戻す */
  restore(): void {
    this.bones.forEach((b, i) => b.quaternion.copy(this.saved[i]));
  }

  /** mixer.update の後：アニメーションが書いた値を覚える */
  capture(): void {
    this.bones.forEach((b, i) => this.saved[i].copy(b.quaternion));
  }
}
