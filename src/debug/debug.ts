import GUI from 'lil-gui';
import type * as THREE from 'three';
import { tuningToYaml, type Tuning } from '../content/tuning';
import type { Game } from '../sim/game';
import type { InputFrame } from '../sim/inputFrame';

/** 入力の記録（リプレイ用） */
export interface Recording {
  version: 1;
  seed: number;
  tuning: Tuning;
  frames: InputFrame[];
}

/**
 * 開発用の機能：調整パネル、入力の記録、性能の表示。
 * 調整パネルの「YAML としてコピー」で、手触りの数値をそのまま Claude に渡せる。
 */
export class Debug {
  private gui: GUI;
  private perf: HTMLDivElement;
  private frames = 0;
  private acc = 0;
  private fps = 0;
  recording: InputFrame[] | null = null;
  showPerf = false;

  constructor(
    private readonly tuning: Tuning,
    private readonly getGame: () => Game | null,
    private readonly renderer: THREE.WebGLRenderer,
    parent: HTMLElement,
    actions: { restartForRecording: () => void; toast: (t: string) => void },
  ) {
    this.gui = new GUI({ title: '調整パネル（F1 で開閉）' });
    this.gui.domElement.classList.add('interactive');
    this.gui.close();
    this.gui.hide();

    const m = this.gui.addFolder('移動');
    const mv = tuning.movement;
    m.add(mv, 'runSpeed', 3, 12, 0.1).name('走る速さ');
    m.add(mv, 'groundAccel', 10, 120, 1).name('加速');
    m.add(mv, 'groundDecel', 10, 120, 1).name('減速');
    m.add(mv, 'airAccel', 5, 60, 1).name('空中の加速');
    m.add(mv, 'gravity', 10, 40, 0.5).name('重力');
    m.add(mv, 'fallGravityScale', 1, 2.5, 0.05).name('落下の重力倍率');
    m.add(mv, 'jumpHeight', 1, 4, 0.05).name('ジャンプの高さ');
    m.add(mv, 'minJumpHeight', 0.3, 2, 0.05).name('最低ジャンプの高さ');
    m.add(mv, 'coyoteTime', 0, 0.3, 0.01).name('着地の猶予');
    m.add(mv, 'jumpBuffer', 0, 0.3, 0.01).name('ジャンプ先行入力');
    m.add(mv, 'dashSpeed', 6, 30, 0.5).name('ダッシュの速さ');
    m.add(mv, 'dashTime', 0.08, 0.5, 0.01).name('ダッシュの時間');
    m.add(mv, 'dashInvuln', 0, 0.3, 0.01).name('ダッシュの無敵');
    m.add(mv, 'dashJumpSpeed', 7, 16, 0.5).name('ダッシュジャンプの速さ');
    m.add(mv, 'turnSpeed', 180, 1440, 10).name('振り向きの速さ');
    m.add(mv, 'strafeSpeed', 2, 10, 0.1).name('ロックオン中の速さ');

    const c = this.gui.addFolder('カメラ');
    const cam = tuning.camera;
    c.add(cam, 'distance', 2, 12, 0.1).name('距離');
    c.add(cam, 'pivotHeight', 0.5, 3, 0.05).name('注視点の高さ');
    c.add(cam, 'fov', 40, 90, 1).name('視野角');
    c.add(cam, 'sensitivityX', 0.2, 3, 0.05).name('感度（横）');
    c.add(cam, 'sensitivityY', 0.2, 3, 0.05).name('感度（縦）');
    c.add(cam, 'autoRecenterDelay', 0.5, 10, 0.1).name('自動で背後へ（秒）');
    c.add(cam, 'lockOnYawSpeed', 1, 20, 0.5).name('ロックオン時の追従');

    const l = this.gui.addFolder('ロックオン');
    l.add(tuning.lockOn, 'range', 10, 60, 1).name('距離');
    l.add(tuning.lockOn, 'homingDegPerSec', 0, 120, 1).name('弾の追尾（度/秒）');
    l.add(tuning.lockOn, 'scanTime', 0.2, 5, 0.1).name('解析の時間');

    const gun = this.gui.addFolder('主武器');
    gun.add(tuning.gun, 'damage', 1, 20, 0.5).name('威力');
    gun.add(tuning.gun, 'rate', 1, 15, 0.1).name('連射（発/秒）');
    gun.add(tuning.gun, 'range', 5, 60, 1).name('射程');
    gun.add(tuning.gun, 'speed', 10, 80, 1).name('弾速');
    gun.add(tuning.gun, 'chargeLv1Time', 0.2, 2, 0.05).name('溜め 1 段目');
    gun.add(tuning.gun, 'chargeLv2Time', 0.4, 3, 0.05).name('溜め 2 段目');

    const sw = this.gui.addFolder('光刃');
    sw.add(tuning.sword, 'range', 1, 4, 0.05).name('届く距離');
    sw.add(tuning.sword, 'arcDeg', 60, 240, 5).name('範囲（度）');
    sw.add(tuning.sword, 'lungeMax', 3, 12, 0.5).name('踏み込みの最大距離');
    sw.add(tuning.sword, 'chargeTime', 0.3, 2, 0.05).name('溜め時間');
    sw.add(tuning.sword, 'hitstop', 0, 0.2, 0.005).name('ヒットストップ');
    sw.add(tuning.sword, 'hitstopFinisher', 0, 0.3, 0.005).name('ヒットストップ（とどめ）');

    const en = this.gui.addFolder('敵');
    en.add(tuning.enemies, 'maxAttackers', 1, 5, 1).name('同時に攻撃する数');
    en.add(tuning.enemies.sentry, 'windup', 0.1, 2, 0.05).name('歩哨型の予備動作');
    en.add(tuning.enemies.sentry, 'shotSpeed', 5, 40, 1).name('歩哨型の弾速');
    en.add(tuning.enemies.charger, 'windup', 0.2, 2, 0.05).name('突撃型の予備動作');
    en.add(tuning.enemies.charger, 'chargeSpeed', 5, 30, 0.5).name('突撃型の速さ');

    const tools = this.gui.addFolder('道具');
    const state = { god: false, perf: false };
    tools.add(state, 'god').name('無敵').onChange((v: boolean) => {
      const g = this.getGame();
      if (g) g.godMode = v;
    });
    tools.add(state, 'perf').name('性能の表示').onChange((v: boolean) => (this.showPerf = v));
    tools.add({ copy: () => this.copyYaml(actions.toast) }, 'copy').name('YAML としてコピー');
    tools.add({ rec: () => this.startRecording(actions) }, 'rec').name('入力の記録を開始（最初から）');
    tools.add({ stop: () => this.stopRecording(actions.toast) }, 'stop').name('記録を止めて保存');

    this.perf = document.createElement('div');
    this.perf.className = 'perf';
    this.perf.style.display = 'none';
    parent.appendChild(this.perf);

    window.addEventListener('keydown', (e) => {
      if (e.code === 'F1' || e.code === 'Backquote') {
        e.preventDefault();
        this.toggle();
      }
    });
  }

  get visible(): boolean {
    return !this.gui._hidden;
  }

  toggle(): void {
    if (this.gui._hidden) {
      this.gui.show();
      this.gui.open();
      document.exitPointerLock?.();
    } else this.gui.hide();
  }

  private copyYaml(toast: (t: string) => void): void {
    const text = tuningToYaml(this.tuning);
    navigator.clipboard?.writeText(text).then(
      () => toast('調整した数値を YAML としてコピーしました'),
      () => {
        console.log(text);
        toast('コピーできなかったので、コンソールに出力しました');
      },
    );
  }

  private startRecording(actions: { restartForRecording: () => void; toast: (t: string) => void }): void {
    actions.restartForRecording();
    this.recording = [];
    actions.toast('入力の記録を始めました');
  }

  private stopRecording(toast: (t: string) => void): void {
    if (!this.recording) return;
    const rec: Recording = { version: 1, seed: 12345, tuning: this.tuning, frames: this.recording };
    const blob = new Blob([JSON.stringify(rec)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `arkwalker-replay-${Date.now()}.json`;
    a.click();
    this.recording = null;
    toast(`入力の記録を保存しました（${rec.frames.length} 刻み）`);
  }

  record(f: InputFrame): void {
    this.recording?.push(f);
  }

  update(dt: number): void {
    this.frames++;
    this.acc += dt;
    if (this.acc >= 0.5) {
      this.fps = this.frames / this.acc;
      this.frames = 0;
      this.acc = 0;
    }
    this.perf.style.display = this.showPerf ? 'block' : 'none';
    if (this.showPerf) {
      const info = this.renderer.info;
      this.perf.textContent = `fps ${this.fps.toFixed(0)}\n描画 ${info.render.calls} 回\n三角形 ${info.render.triangles.toLocaleString()}`;
    }
  }
}
