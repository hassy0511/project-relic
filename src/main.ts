import * as THREE from 'three';
import './ui/style.css';
import placementYaml from '../content/areas/mvp.yaml?raw';
import dialogueYaml from '../content/dialogue/mvp.yaml?raw';
import eventsYaml from '../content/events/mvp.yaml?raw';
import { Audio } from './audio/audio';
import { loadTuning } from './content/tuning';
import { Debug } from './debug/debug';
import { InputManager } from './platform/input';
import { parsePlacement, validatePlacement, type AreaGeometry } from './sim/area';
import { DT } from './sim/constants';
import { Game } from './sim/game';
import { emptyInput } from './sim/inputFrame';
import { parseSave } from './sim/save';
import { parseDialogues, parseEvents, validateDialogues } from './sim/script';
import { Hud } from './ui/hud';
import { Menu } from './ui/menu';
import { loadArea } from './view/areaLoader';
import { CameraRig } from './view/cameraRig';
import { EnemyView } from './view/enemyView';
import { Fx } from './view/fx';
import { PlayerView } from './view/playerView';
import { PropsView } from './view/propsView';
import { Renderer } from './view/renderer';

const BASE = import.meta.env.BASE_URL;
const SAVE_KEY = 'arkwalker.save.slot1';
const AREA_ID = 'area.mvp';

type State = 'loading' | 'title' | 'playing' | 'paused';

class App {
  state: State = 'loading';
  readonly tuning = loadTuning();
  readonly renderer: Renderer;
  readonly input: InputManager;
  readonly audio = new Audio(BASE);
  readonly hud: Hud;
  readonly menu: Menu;
  readonly debug: Debug;
  readonly rig: CameraRig;
  game: Game | null = null;
  private geometry: AreaGeometry | null = null;
  private dynamic = new THREE.Group();
  private playerView: PlayerView | null = null;
  private enemyView: EnemyView | null = null;
  private propsView: PropsView | null = null;
  private fx: Fx | null = null;
  private acc = 0;
  private last = performance.now();
  private prevPos = new THREE.Vector3();
  private time = 0;
  /** マウスの固定が外れて自動でポーズした時刻（同じ Esc で即再開しないため） */
  private autoPausedAt = -1e9;
  readonly errors: string[] = [];

  constructor() {
    const canvas = document.getElementById('game') as HTMLCanvasElement;
    const ui = document.getElementById('ui') as HTMLDivElement;
    this.renderer = new Renderer(canvas, this.tuning.camera.fov);
    this.renderer.scene.add(this.dynamic);
    this.input = new InputManager(canvas);
    this.hud = new Hud(ui);
    this.hud.setVisible(false);
    this.menu = new Menu(ui, () => this.audio.play('ui_move'), () => this.audio.play('ui_ok'));
    this.rig = new CameraRig(this.renderer.camera);
    // マウスの固定が外れたら（Esc など）自動でポーズする
    document.addEventListener('pointerlockchange', () => {
      if (!document.pointerLockElement && this.state === 'playing' && !this.debug?.visible) {
        this.autoPausedAt = performance.now();
        this.pause();
      }
    });
    this.debug = new Debug(this.tuning, () => this.game, this.renderer.renderer, ui, {
      restartForRecording: () => void this.startGame(null),
      toast: (t) => this.hud.showToast(t),
    });
  }

  async boot(): Promise<void> {
    const loading = document.getElementById('loading');
    try {
      const { group, geometry } = await loadArea(`${BASE}assets/levels/mvp_greybox.glb`);
      this.renderer.scene.add(group);
      this.geometry = geometry;
      const placement = parsePlacement(placementYaml);
      const missing = validatePlacement(placement, geometry);
      if (missing.length) throw new Error(`地形に目印がない: ${missing.join(', ')}`);
      const dlgErrors = validateDialogues(parseDialogues(dialogueYaml));
      if (dlgErrors.length) console.warn(dlgErrors.join('\n'));
    } catch (e) {
      this.fail(e);
      return;
    }
    loading?.remove();
    this.showTitle();
    requestAnimationFrame((t) => this.frame(t));
  }

  private fail(e: unknown): void {
    const msg = e instanceof Error ? e.message : String(e);
    this.errors.push(msg);
    const loading = document.getElementById('loading');
    if (loading) loading.textContent = `読み込みに失敗しました：${msg}`;
    console.error(e);
  }

  private hasSave(): boolean {
    try {
      return !!localStorage.getItem(SAVE_KEY);
    } catch {
      return false;
    }
  }

  showTitle(): void {
    this.state = 'title';
    this.hud.setVisible(false);
    this.input.releasePointer();
    this.menu.showTitle(this.hasSave(), {
      newGame: () => void this.startGame(null),
      continue: () => {
        const s = parseSave(localStorage.getItem(SAVE_KEY) ?? '');
        void this.startGame(s);
      },
    });
  }

  async startGame(save: ReturnType<typeof parseSave>): Promise<void> {
    await this.audio.start().catch(() => {});
    if (!this.geometry) return;
    // 前のゲームの見た目を片付ける
    this.renderer.scene.remove(this.dynamic);
    this.dynamic = new THREE.Group();
    this.renderer.scene.add(this.dynamic);

    const game = await Game.create({
      geometry: this.geometry,
      placement: parsePlacement(placementYaml),
      tuning: this.tuning,
      dialogues: parseDialogues(dialogueYaml),
      events: parseEvents(eventsYaml),
      seed: 12345,
      save,
    });
    this.game = game;
    this.playerView = new PlayerView(this.dynamic);
    await this.playerView.load(`${BASE}assets/models/haru_proxy.glb`);
    this.enemyView = new EnemyView(this.dynamic);
    this.propsView = new PropsView(this.dynamic, game);
    this.fx = new Fx(this.dynamic);
    this.prevPos.copy(game.player.pos);
    this.acc = 0;
    this.menu.hide();
    this.hud.setVisible(true);
    this.state = 'playing';
    this.audio.playMusic('bgm_trial');
    if (save) this.hud.showToast('セーブした場所から再開しました');
  }

  private pause(): void {
    if (!this.game) return;
    this.state = 'paused';
    this.input.releasePointer();
    this.audio.play('ui_ok');
    this.menu.showPause(this.game, {
      resume: () => {
        this.menu.hide();
        this.state = 'playing';
      },
      toggleChip: () => this.game?.toggleChip('chip.charge'),
      loadSave: () => {
        const s = parseSave(localStorage.getItem(SAVE_KEY) ?? '');
        if (s) void this.startGame(s);
      },
      toTitle: () => this.showTitle(),
    });
  }

  private frame(now: number): void {
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    this.time += dt;
    this.menu.poll();

    const g = this.game;
    if (this.state === 'playing' && g) {
      this.input.enabled = !this.debug.visible;
      if (this.input.takeOneShot('pause')) this.pause();
    }
    if (this.state === 'paused' && this.input.takeOneShot('pause') && now - this.autoPausedAt > 400) {
      this.menu.hide();
      this.state = 'playing';
    }

    if (this.state === 'playing' && g) {
      const frameInput = this.input.sample(dt);
      this.hud.device = this.input.lastDevice;
      this.acc += dt;
      let steps = 0;
      while (this.acc >= DT && steps < 5) {
        const f = steps === 0 ? frameInput : { ...emptyInput(), ...frameInput, lookX: 0, lookY: 0, switchTargetLeft: false, switchTargetRight: false, cameraReset: false };
        this.prevPos.copy(g.player.pos);
        this.debug.record(f);
        g.step(f);
        this.acc -= DT;
        steps++;
      }
      if (steps === 5) this.acc = 0;
      this.handleEvents(g);
    }

    if (g && this.playerView && this.enemyView && this.propsView && this.fx) {
      const alpha = this.acc / DT;
      const pos = this.prevPos.clone().lerp(g.player.pos, alpha);
      const aimTarget = g.lockOnPoint();
      const aimDir = aimTarget ? aimTarget.sub(g.playerChest()).normalize() : this.rig.forward();
      const viewDt = this.state === 'playing' ? dt : 0;
      this.playerView.update(g.player, pos, viewDt, aimDir);
      this.enemyView.sync(g.enemies, this.time);
      this.propsView.sync(g, this.time, viewDt);
      this.fx.sync(g, viewDt);
      this.rig.update(g, pos, dt, this.fx.shake);
      this.renderer.followShadow(pos);
      this.hud.update(g, this.renderer.camera, dt);
    }
    this.debug.update(dt);
    this.renderer.render();
    requestAnimationFrame((t) => this.frame(t));
  }

  private handleEvents(g: Game): void {
    const cam = this.renderer.camera;
    for (const e of g.events.drain()) {
      this.fx?.handle(e);
      switch (e.type) {
        case 'sfx':
          this.audio.play(e.id, e.x !== undefined ? new THREE.Vector3(e.x, e.y, e.z) : undefined, cam);
          break;
        case 'message':
          this.hud.showToast(e.text);
          break;
        case 'saved':
          try {
            localStorage.setItem(SAVE_KEY, JSON.stringify({ ...g.toSave(AREA_ID), savedAt: new Date().toISOString() }));
            this.hud.showToast('セーブしました（HP と武器エネルギーが回復）');
          } catch {
            this.hud.showToast('セーブできませんでした（ブラウザの保存領域を使えません）');
          }
          break;
        case 'playerHurt':
          this.hud.flashDamage();
          break;
        case 'playerDied':
          this.hud.showToast('やられた……中継地点から再開します');
          break;
        default:
          break;
      }
    }
  }
}

const app = new App();
(window as unknown as { __arkwalker: App }).__arkwalker = app;
void app.boot();
