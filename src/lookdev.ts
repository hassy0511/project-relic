/**
 * 見た目の確認ページ（lookdev.html）。
 * キャラクター 1 体を、塗り方・背景・カメラの距離・動作・表情を切り替えて確認する。
 * URL の引数で状態を指定でき、自動の撮影にも使う：
 *   ?model=haru_a&shade=toon&bg=dawn&view=game&anim=run&t=0.3&expr=smile&blade=1&aim=1
 */
import * as THREE from 'three';
import GUI from 'lil-gui';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { aimRightArm, CharacterLook, EXPRESSIONS, PoseOverride, rimUniforms, type Expression, type Shading } from './view/characterLook';

const BASE = import.meta.env.BASE_URL;
const params = new URLSearchParams(location.search);

const VIEWS = ['front', 'three_quarter', 'side', 'back', 'head', 'game', 'game_side', 'far', 'free', 'custom'] as const;
type View = (typeof VIEWS)[number];
const BGS = ['grey', 'dawn', 'game'] as const;
type Bg = (typeof BGS)[number];

const state = {
  model: params.get('model') ?? 'haru_a',
  shade: (params.get('shade') ?? 'soft') as Shading,
  bg: (params.get('bg') ?? 'grey') as Bg,
  view: (params.get('view') ?? 'three_quarter') as View,
  anim: params.get('anim') ?? 'idle',
  /** 動作を止める時刻（秒）。空なら再生し続ける */
  t: params.has('t') ? Number(params.get('t')) : NaN,
  expr: (params.get('expr') ?? 'normal') as Expression,
  blade: params.get('blade') === '1',
  aim: params.get('aim') === '1',
  aimPitch: Number(params.get('pitch') ?? 0),
  spin: params.get('spin') === '1',
  wire: params.get('wire') === '1',
  hud: params.get('hud') !== '0',
  backlit: params.get('backlit') === '1',
  /** 輪郭の光の強さ（0 で無し） */
  rim: Number(params.get('rim') ?? 0.45),
  /** view=custom のときのカメラ位置・注視点・画角 */
  cam: [2, 1.2, 2] as number[],
  target: [0, 1, 0] as number[],
  fov: 30,
};
const DEFAULTS = { ...state };

const canvas = document.createElement('canvas');
document.body.appendChild(canvas);
document.body.style.margin = '0';
document.body.style.overflow = 'hidden';
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.info.autoReset = false;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 500);
const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 0.8, 0);
controls.enabled = false;

const hud = document.createElement('div');
hud.style.cssText =
  'position:fixed;left:8px;bottom:8px;padding:6px 10px;background:rgba(0,0,0,.55);color:#fff;font:12px/1.5 system-ui,sans-serif;border-radius:4px;white-space:pre;pointer-events:none';
document.body.appendChild(hud);

// ---------------------------------------------------------------- 背景と光

const envRoot = new THREE.Group();
scene.add(envRoot);
const character = new THREE.Group();
scene.add(character);

function buildEnv(bg: Bg): void {
  envRoot.clear();
  scene.fog = null;
  if (bg === 'grey') {
    scene.background = new THREE.Color('#dcdcd8');
    envRoot.add(new THREE.HemisphereLight('#ffffff', '#b8b4ac', 1.6));
    const key = new THREE.DirectionalLight('#fff6ea', 2.2);
    key.position.set(-2.5, 4, 4); // 手前・左上から（キャラクターの正面は +Z）
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.02;
    const kc = key.shadow.camera;
    kc.left = kc.bottom = -2;
    kc.right = kc.top = 2;
    envRoot.add(key);
    const floor = new THREE.Mesh(new THREE.CircleGeometry(3, 48), new THREE.ShadowMaterial({ opacity: 0.18 }));
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    envRoot.add(floor);
  } else if (bg === 'dawn') {
    // キービジュアルの色調の仮の場面：赤い砂、白い遺構、低い朝日
    scene.background = new THREE.Color('#e9a574');
    scene.fog = new THREE.Fog('#e9a574', 25, 140);
    envRoot.add(new THREE.HemisphereLight('#ffd9ae', '#7a3a28', 1.3));
    const sun = new THREE.DirectionalLight('#ffc98c', 3.0);
    // 低い朝日。backlit=1 でキービジュアルと同じ逆光（カメラから見て奥）、既定は右後ろから
    if (state.backlit) sun.position.set(6, 3.2, 12);
    else sun.position.set(9, 3.5, -5);
    sun.castShadow = true;
    sun.shadow.bias = -0.0004;
    sun.shadow.normalBias = 0.02;
    sun.shadow.mapSize.set(2048, 2048);
    const sc = sun.shadow.camera;
    sc.left = sc.bottom = -15;
    sc.right = sc.top = 15;
    envRoot.add(sun);
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(400, 400, 60, 60),
      new THREE.MeshStandardMaterial({ color: '#c56a45', roughness: 1, flatShading: true }),
    );
    const pos = ground.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const d = Math.hypot(x, y);
      pos.setZ(i, d < 12 ? 0 : Math.sin(x * 0.09) * Math.cos(y * 0.07) * Math.min(4, (d - 12) * 0.15));
    }
    ground.geometry.computeVertexNormals();
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    envRoot.add(ground);
    const relic = new THREE.MeshStandardMaterial({ color: '#f0e3c8', roughness: 0.9, flatShading: true });
    const dark = new THREE.MeshStandardMaterial({ color: '#4a4a44', roughness: 0.8, flatShading: true });
    const blocks: [number, number, number, number, number, number, THREE.Material][] = [
      [-6, 1.5, 8, 2, 3, 2, relic],
      [-4.2, 0.4, 7, 1.4, 0.8, 1.2, dark],
      [7, 3, 18, 2.5, 6, 2.5, relic],
      [10, 0.6, 14, 3, 1.2, 1.5, relic],
      [-14, 4, 30, 3, 8, 3, relic],
      [3.5, 0.3, -4, 1.2, 0.6, 0.8, dark],
      [16, 5, 45, 4, 10, 4, relic],
    ];
    for (const [x, y, z, w, h, d, m] of blocks) {
      const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
      b.position.set(x, y, z);
      b.castShadow = b.receiveShadow = true;
      envRoot.add(b);
    }
  } else {
    // ゲーム（MVP）と同じ光
    scene.background = new THREE.Color('#c9a27e');
    scene.fog = new THREE.Fog('#c9a27e', 60, 180);
    envRoot.add(new THREE.HemisphereLight('#ffe9c9', '#5a4636', 1.4));
    const sun = new THREE.DirectionalLight('#fff1d6', 2.6);
    sun.position.set(-20, 40, -10);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    const sc = sun.shadow.camera;
    sc.left = sc.bottom = -20;
    sc.right = sc.top = 20;
    sun.shadow.bias = -0.0005;
    sun.shadow.normalBias = 0.02;
    envRoot.add(sun);
    const grid = new THREE.Mesh(
      new THREE.PlaneGeometry(200, 200),
      new THREE.MeshStandardMaterial({ color: '#8f8a80', roughness: 1 }),
    );
    grid.rotation.x = -Math.PI / 2;
    grid.receiveShadow = true;
    envRoot.add(grid);
    const lines = new THREE.GridHelper(200, 200, '#6f6a62', '#7d786f');
    lines.position.y = 0.002;
    envRoot.add(lines);
  }
}

// ---------------------------------------------------------------- カメラ

function placeCamera(view: View): void {
  controls.enabled = view === 'free';
  if (view === 'free') return;
  const H = 1.55;
  const setOrbit = (az: number, dist: number, targetY: number, fov: number, camY = targetY) => {
    camera.fov = fov;
    const a = (az * Math.PI) / 180;
    // 正面（az=0）はキャラクターの前（+Z）側から
    camera.position.set(Math.sin(a) * dist, camY, Math.cos(a) * dist);
    controls.target.set(0, targetY, 0);
    camera.lookAt(controls.target);
  };
  switch (view) {
    case 'custom':
      camera.fov = state.fov;
      camera.position.set(state.cam[0], state.cam[1], state.cam[2]);
      controls.target.set(state.target[0], state.target[1], state.target[2]);
      camera.lookAt(controls.target);
      break;
    case 'front': setOrbit(0, 4.2, H / 2, 25); break;
    case 'three_quarter': setOrbit(35, 4.2, H / 2, 25); break;
    case 'side': setOrbit(90, 4.2, H / 2, 25); break;
    case 'back': setOrbit(180, 4.2, H / 2, 25); break;
    case 'head': setOrbit(20, 1.4, 1.36, 20); break;
    case 'game':
    case 'game_side':
    case 'far': {
      // ゲームのカメラ：注視点の高さ 1.4m、距離 5.5m（遠景は 10m）、見下ろし 12 度、画角 60 度
      const dist = view === 'far' ? 10 : 5.5;
      const yaw = view === 'game_side' ? 70 : 0;
      const pitch = (12 * Math.PI) / 180;
      const y = (yaw * Math.PI) / 180;
      camera.fov = 60;
      controls.target.set(0, 1.4, 0);
      camera.position.set(-Math.sin(y) * Math.cos(pitch) * dist, 1.4 + Math.sin(pitch) * dist, -Math.cos(y) * Math.cos(pitch) * dist);
      camera.lookAt(controls.target);
      break;
    }
  }
  camera.updateProjectionMatrix();
}

// ---------------------------------------------------------------- キャラクター

let look: CharacterLook | null = null;
let mixer: THREE.AnimationMixer | null = null;
const actions = new Map<string, THREE.AnimationAction>();
let currentAction: THREE.AnimationAction | null = null;
let model: THREE.Object3D | null = null;
let rest: { arm: THREE.Quaternion; fore: THREE.Quaternion } | null = null;
let override: PoseOverride | null = null;
let fileBytes = 0;

async function loadModel(name: string): Promise<void> {
  character.clear();
  actions.clear();
  const url = `${BASE}assets/models/${name}.glb`;
  const buf = await (await fetch(url)).arrayBuffer();
  fileBytes = buf.byteLength;
  const gltf = await new GLTFLoader().parseAsync(buf, `${BASE}assets/models/`);
  model = gltf.scene;
  model.traverse((o) => {
    const m = o as THREE.Mesh;
    if (m.isMesh) m.castShadow = m.receiveShadow = true;
  });
  character.add(model);
  look = new CharacterLook(model);
  mixer = new THREE.AnimationMixer(model);
  for (const clip of gltf.animations) actions.set(clip.name, mixer.clipAction(clip));
  const arm = look.bones.get('upper_armR');
  const fore = look.bones.get('forearmR');
  rest = arm && fore ? { arm: arm.quaternion.clone(), fore: fore.quaternion.clone() } : null;
  override = arm && fore ? new PoseOverride([arm, fore]) : null;
  applyAll();
}

function playAnim(name: string): void {
  const a = actions.get(name) ?? actions.get('idle');
  if (!a) return;
  if (currentAction && currentAction !== a) currentAction.stop();
  a.reset();
  a.setLoop(THREE.LoopRepeat, Infinity);
  a.play();
  currentAction = a;
}

function applyAll(): void {
  if (!look) return;
  look.setShading(state.shade);
  rimUniforms.rimStrength.value = state.rim;
  look.setExpression(state.expr);
  const blade = look.nodes.get('LightBlade');
  if (blade) blade.visible = state.blade;
  for (const m of look.meshes) {
    const list = Array.isArray(m.material) ? m.material : [m.material];
    for (const mat of list) (mat as THREE.MeshStandardMaterial).wireframe = state.wire;
  }
  playAnim(state.anim);
  buildEnv(state.bg);
  placeCamera(state.view);
  hud.style.display = state.hud ? 'block' : 'none';
}

// ---------------------------------------------------------------- 操作パネル

const gui = new GUI({ title: '見た目の確認' });
gui.add(state, 'model', ['haru_a', 'haru_proxy']).name('モデル').onChange((v: string) => void loadModel(v));
gui.add(state, 'shade', { 柔らかい陰影: 'soft', '3段の塗り分け': 'toon' }).name('塗り方').onChange(applyAll);
gui.add(state, 'bg', { 明るい灰色: 'grey', 赤い砂と朝日: 'dawn', ゲームの光: 'game' }).name('背景').onChange(applyAll);
gui
  .add(state, 'view', {
    正面: 'front', 斜め: 'three_quarter', 横: 'side', 背面: 'back', 顔: 'head',
    'ゲーム（5.5m）': 'game', 'ゲーム（横から）': 'game_side', '遠く（10m）': 'far', 自由: 'free',
  })
  .name('カメラ')
  .onChange(applyAll);
const animNames = ['idle', 'run', 'jump', 'fall', 'dash', 'combo1', 'combo2', 'combo3', 'air', 'lunge', 'charge', 'drill', 'hurt', 'dead'];
gui.add(state, 'anim', animNames).name('動作').onChange(applyAll);
gui.add(state, 'expr', [...EXPRESSIONS]).name('表情').onChange(applyAll);
gui.add(state, 'blade').name('光刃を出す').onChange(applyAll);
gui.add(state, 'aim').name('銃を構える');
gui.add(state, 'aimPitch', -0.8, 0.8, 0.01).name('照準の上下');
gui.add(state, 'rim', 0, 1.5, 0.05).name('輪郭の光').onChange(applyAll);
gui.add(state, 'backlit').name('逆光（朝日）').onChange(applyAll);
gui.add(state, 'spin').name('回転');
gui.add(state, 'wire').name('線で表示').onChange(applyAll);
if (!state.hud) gui.hide();

// ---------------------------------------------------------------- ループ

function resize(): void {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

const clock = new THREE.Clock();
let frames = 0;
let fpsTime = 0;
let fps = 0;

function tick(): void {
  const dt = Math.min(0.1, clock.getDelta());
  override?.restore();
  if (mixer && currentAction) {
    if (Number.isFinite(state.t)) {
      currentAction.time = state.t;
      mixer.update(0);
    } else mixer.update(dt);
  }
  override?.capture();
  if (look && rest && state.aim) {
    const arm = look.bones.get('upper_armR');
    const fore = look.bones.get('forearmR');
    if (arm && fore) aimRightArm(arm, fore, rest.arm, rest.fore, state.aimPitch, 1);
  }
  if (state.spin) character.rotation.y += dt * 0.6;
  if (controls.enabled) controls.update();
  renderer.info.reset();
  renderer.render(scene, camera);
  frames++;
  fpsTime += dt;
  if (fpsTime > 0.5) {
    fps = frames / fpsTime;
    frames = 0;
    fpsTime = 0;
  }
  if (look && state.hud) {
    const s = look.stats();
    hud.textContent =
      `3角形 ${s.triangles.toLocaleString()}（光刃を含む）\n` +
      `メッシュ ${s.meshes}　材質 ${s.materials}　テクスチャ ${s.textures}\n` +
      `描画の呼び出し（画面全体） ${renderer.info.render.calls}\n` +
      `ファイル ${(fileBytes / 1024).toFixed(0)} KB　${fps.toFixed(0)} fps`;
  }
  requestAnimationFrame(tick);
}

declare global {
  interface Window {
    __lookdev?: { ready: boolean; stats: () => unknown; set: (p: Partial<typeof state>, reset?: boolean) => Promise<void> };
  }
}

window.__lookdev = {
  ready: false,
  stats: () => ({ ...look?.stats(), fileBytes, calls: renderer.info.render.calls }),
  /** 状態を設定する。reset=true なら、指定のない項目は既定の値に戻す（撮影で前の状態を持ち越さない） */
  set: async (p, reset = false) => {
    const modelChanged = p.model && p.model !== state.model;
    if (reset) Object.assign(state, { ...DEFAULTS, model: state.model, hud: state.hud });
    Object.assign(state, p);
    if (modelChanged) await loadModel(state.model);
    else applyAll();
  },
};

loadModel(state.model).then(() => {
  requestAnimationFrame(tick);
  window.__lookdev!.ready = true;
});
