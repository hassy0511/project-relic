import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import type { AreaGeometry } from '../sim/area';

/**
 * 地形の GLB を読み込み、見た目（Group）と当たり判定のデータ（AreaGeometry）に分ける。
 * - メッシュは見た目にも当たり判定にも使う（名前に _nocol を含むものは当たり判定なし、_col は見た目なし）
 * - 名前が m_ で始まるノードは目印
 */
export async function loadArea(url: string): Promise<{ group: THREE.Group; geometry: AreaGeometry }> {
  const gltf = await new GLTFLoader().loadAsync(url);
  const root = gltf.scene;
  root.updateMatrixWorld(true);
  const geometry: AreaGeometry = { meshes: [], markers: {} };
  const hidden: THREE.Object3D[] = [];

  root.traverse((obj) => {
    if (obj.name.startsWith('m_')) {
      const p = new THREE.Vector3();
      const q = new THREE.Quaternion();
      obj.matrixWorld.decompose(p, q, new THREE.Vector3());
      const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(q);
      geometry.markers[obj.name.slice(2)] = { pos: [p.x, p.y, p.z], yaw: Math.atan2(fwd.x, fwd.z) };
      return;
    }
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (!mesh.name.includes('_nocol')) geometry.meshes.push(extractTriangles(mesh));
    if (mesh.name.includes('_col')) hidden.push(mesh);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.material = gridMaterial(mesh.material as THREE.MeshStandardMaterial);
  });
  for (const h of hidden) h.visible = false;
  const group = new THREE.Group();
  group.add(root);
  return { group, geometry };
}

function extractTriangles(mesh: THREE.Mesh): { vertices: Float32Array; indices: Uint32Array } {
  const geo = mesh.geometry;
  const pos = geo.getAttribute('position');
  const vertices = new Float32Array(pos.count * 3);
  const v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
    vertices[i * 3] = v.x;
    vertices[i * 3 + 1] = v.y;
    vertices[i * 3 + 2] = v.z;
  }
  let indices: Uint32Array;
  if (geo.index) indices = new Uint32Array(geo.index.array);
  else indices = Uint32Array.from({ length: pos.count }, (_, i) => i);
  return { vertices, indices };
}

const gridCache = new Map<string, THREE.Material>();

/**
 * 仮の地形用の材質。ワールド座標で 1m ごとの格子線を描き、大きさを読み取りやすくする。
 */
export function gridMaterial(base: THREE.MeshStandardMaterial): THREE.Material {
  const key = base.color.getHexString();
  const cached = gridCache.get(key);
  if (cached) return cached;
  const mat = new THREE.MeshStandardMaterial({ color: base.color, roughness: 0.9, metalness: 0 });
  mat.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWorldPos;\nvarying vec3 vWorldNormal;')
      .replace(
        '#include <worldpos_vertex>',
        '#include <worldpos_vertex>\nvWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWorldNormal = normalize(mat3(modelMatrix) * objectNormal);',
      );
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWorldPos;\nvarying vec3 vWorldNormal;')
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
        {
          vec3 n = abs(normalize(vWorldNormal));
          vec2 uv = n.y > 0.5 ? vWorldPos.xz : (n.x > 0.5 ? vWorldPos.zy : vWorldPos.xy);
          vec2 g = abs(fract(uv - 0.5) - 0.5) / fwidth(uv);
          float line = 1.0 - min(min(g.x, g.y), 1.0);
          vec2 g4 = abs(fract(uv / 4.0 - 0.5) - 0.5) / fwidth(uv / 4.0);
          float line4 = 1.0 - min(min(g4.x, g4.y), 1.0);
          diffuseColor.rgb *= 1.0 - line * 0.18 - line4 * 0.22;
        }`,
      );
  };
  gridCache.set(key, mat);
  return mat;
}
