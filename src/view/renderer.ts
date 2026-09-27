import * as THREE from 'three';

/** WebGL の描画と、シーンの基本（光、霧、空の色） */
export class Renderer {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera: THREE.PerspectiveCamera;
  readonly sun: THREE.DirectionalLight;
  private resolutionScale = 1;

  constructor(readonly canvas: HTMLCanvasElement, fov: number) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;

    this.camera = new THREE.PerspectiveCamera(fov, 16 / 9, 0.1, 400);
    this.scene.background = new THREE.Color('#c9a27e');
    this.scene.fog = new THREE.Fog('#c9a27e', 60, 180);

    const hemi = new THREE.HemisphereLight('#ffe9c9', '#5a4636', 1.4);
    this.scene.add(hemi);
    this.sun = new THREE.DirectionalLight('#fff1d6', 2.6);
    this.sun.position.set(-20, 40, -10);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    const s = this.sun.shadow.camera;
    s.left = -40;
    s.right = 40;
    s.top = 40;
    s.bottom = -40;
    s.near = 1;
    s.far = 120;
    this.sun.shadow.bias = -0.0005;
    this.scene.add(this.sun, this.sun.target);

    window.addEventListener('resize', () => this.resize());
    this.resize();
  }

  setResolutionScale(s: number): void {
    this.resolutionScale = s;
    this.resize();
  }

  resize(): void {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2) * this.resolutionScale);
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  /** 影を落とす範囲をプレイヤーの周りに合わせる */
  followShadow(target: THREE.Vector3): void {
    this.sun.position.set(target.x - 20, target.y + 40, target.z - 10);
    this.sun.target.position.copy(target);
  }

  render(): void {
    this.renderer.render(this.scene, this.camera);
  }
}
