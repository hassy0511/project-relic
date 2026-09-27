import { emptyInput, type InputFrame } from '../sim/inputFrame';

/** 操作の割り当て（設定画面での変更に備え、データとして持つ） */
export interface Bindings {
  keys: Record<string, string>; // KeyboardEvent.code → 操作名
  mouse: Record<number, string>; // ボタン番号 → 操作名
  pad: Record<number, string>; // 標準ゲームパッドのボタン番号 → 操作名
}

export const DEFAULT_BINDINGS: Bindings = {
  keys: {
    KeyW: 'up', KeyS: 'down', KeyA: 'left', KeyD: 'right',
    ArrowUp: 'camUp', ArrowDown: 'camDown', ArrowLeft: 'camLeft', ArrowRight: 'camRight',
    Space: 'jump', ShiftLeft: 'dash', ShiftRight: 'dash',
    KeyE: 'sword', KeyQ: 'special', KeyR: 'heal', KeyC: 'cameraReset',
    KeyF: 'lockOn', KeyJ: 'fire', KeyK: 'sword', KeyL: 'lockOn',
    Escape: 'pause', Tab: 'map',
  },
  mouse: { 0: 'fire', 2: 'lockOn', 1: 'cameraReset' },
  // Xbox 配置：0=A 1=B 2=X 3=Y 4=LB 5=RB 6=LT 7=RT 8=View 9=Menu 10=L3 11=R3 12〜15=十字キー
  pad: { 0: 'jump', 1: 'dash', 2: 'sword', 3: 'special', 6: 'lockOn', 7: 'fire', 11: 'cameraReset', 12: 'heal', 9: 'pause', 8: 'map' },
};

const BUTTONS = ['jump', 'dash', 'fire', 'sword', 'special', 'lockOn', 'heal'] as const;

/**
 * キーボード・マウス・ゲームパッドの入力を集めて、sim 用の InputFrame にする。
 * マウスはポインターロック中だけカメラを回す。
 */
export class InputManager {
  private held = new Set<string>();
  /** 前回の sample 以降に一度でも押されたボタン（フレームの間の素早い押下を取りこぼさない） */
  private latched = new Set<string>();
  private mouseDX = 0;
  private mouseDY = 0;
  private flickAccum = 0;
  private flickCooldown = 0;
  private padFlickReady = true;
  private oneShot = new Set<string>();
  private padPrev: boolean[] = [];
  bindings: Bindings = DEFAULT_BINDINGS;
  mouseSensitivity = 0.0025;
  padSensitivity = 3.2;
  invertY = false;
  /** 最後に使われた機器（ボタン表示の切り替えに使う） */
  lastDevice: 'keyboard' | 'pad' = 'keyboard';
  enabled = true;
  /** マウスの固定が使えない環境（埋め込み表示など）。クリックをそのまま操作として扱い、カメラは矢印キーで回す */
  lockUnavailable = false;
  keyLookSpeed = 2.4;

  constructor(canvas: HTMLElement) {
    window.addEventListener('keydown', (e) => this.onKey(e, true));
    window.addEventListener('keyup', (e) => this.onKey(e, false));
    window.addEventListener('blur', () => this.held.clear());
    canvas.addEventListener('mousedown', (e) => {
      if (!this.enabled) return;
      if (document.pointerLockElement !== canvas && !this.lockUnavailable) {
        this.requestLock(canvas);
        return;
      }
      const a = this.bindings.mouse[e.button];
      if (a) this.press(a);
      this.lastDevice = 'keyboard';
    });
    window.addEventListener('mouseup', (e) => {
      const a = this.bindings.mouse[e.button];
      if (a) this.held.delete(a);
    });
    window.addEventListener('mousemove', (e) => {
      if (document.pointerLockElement !== canvas) return;
      this.mouseDX += e.movementX;
      this.mouseDY += e.movementY;
      if (this.held.has('lockOn')) this.flickAccum += e.movementX;
    });
    window.addEventListener('wheel', (e) => {
      if (e.deltaY !== 0) this.oneShot.add(e.deltaY > 0 ? 'nextSpecial' : 'prevSpecial');
    });
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    document.addEventListener('pointerlockerror', () => (this.lockUnavailable = true));
  }

  private requestLock(canvas: HTMLElement): void {
    try {
      const r = canvas.requestPointerLock?.() as unknown as Promise<void> | undefined;
      if (!canvas.requestPointerLock) this.lockUnavailable = true;
      r?.catch?.(() => (this.lockUnavailable = true));
    } catch {
      this.lockUnavailable = true;
    }
  }

  private onKey(e: KeyboardEvent, down: boolean): void {
    const a = this.bindings.keys[e.code];
    if (!a) return;
    if (e.code === 'Tab' || e.code === 'Space') e.preventDefault();
    this.lastDevice = 'keyboard';
    if (down) {
      if (e.repeat) return;
      this.press(a);
    } else this.held.delete(a);
  }

  private press(a: string): void {
    this.held.add(a);
    this.latched.add(a);
    if (a === 'pause' || a === 'map' || a === 'cameraReset') this.oneShot.add(a);
  }

  /** UI 用：一度だけの操作（ポーズ等）を取り出す */
  takeOneShot(a: string): boolean {
    if (this.oneShot.has(a)) {
      this.oneShot.delete(a);
      return true;
    }
    return false;
  }

  releasePointer(): void {
    if (document.pointerLockElement) document.exitPointerLock();
  }

  /** このフレームの入力を作る。look はこのフレームの回転量の合計 */
  sample(dtFrame: number): InputFrame {
    const f = emptyInput();
    if (!this.enabled) {
      this.mouseDX = this.mouseDY = 0;
      return f;
    }
    // キーボード
    f.moveX = (this.held.has('right') ? 1 : 0) - (this.held.has('left') ? 1 : 0);
    f.moveY = (this.held.has('up') ? 1 : 0) - (this.held.has('down') ? 1 : 0);
    const len = Math.hypot(f.moveX, f.moveY);
    if (len > 1) {
      f.moveX /= len;
      f.moveY /= len;
    }
    f.lookX = this.mouseDX * this.mouseSensitivity;
    f.lookY = this.mouseDY * this.mouseSensitivity * (this.invertY ? -1 : 1);
    f.lookActive = this.mouseDX !== 0 || this.mouseDY !== 0;
    // 矢印キーでもカメラを回せる（マウスの固定が使えない環境向け）
    const kx = (this.held.has('camRight') ? 1 : 0) - (this.held.has('camLeft') ? 1 : 0);
    const ky = (this.held.has('camDown') ? 1 : 0) - (this.held.has('camUp') ? 1 : 0);
    if (kx || ky) {
      f.lookX += kx * this.keyLookSpeed * dtFrame;
      f.lookY += ky * this.keyLookSpeed * 0.6 * dtFrame * (this.invertY ? -1 : 1);
      f.lookActive = true;
    }
    this.mouseDX = this.mouseDY = 0;
    for (const b of BUTTONS) f[b] = this.held.has(b) || this.latched.has(b);
    this.latched.clear();

    // マウスを大きく横に振ると、ロックオン対象の切り替え
    this.flickCooldown = Math.max(0, this.flickCooldown - dtFrame);
    if (this.held.has('lockOn') && this.flickCooldown <= 0 && Math.abs(this.flickAccum) > 60) {
      if (this.flickAccum > 0) f.switchTargetRight = true;
      else f.switchTargetLeft = true;
      this.flickCooldown = 0.25;
      this.flickAccum = 0;
    }
    if (!this.held.has('lockOn')) this.flickAccum = 0;
    this.flickAccum *= 0.9;

    // ゲームパッド
    const pads = navigator.getGamepads?.() ?? [];
    for (const pad of pads) {
      if (!pad) continue;
      const dz = (v: number) => (Math.abs(v) < 0.18 ? 0 : v);
      const lx = dz(pad.axes[0] ?? 0);
      const ly = dz(pad.axes[1] ?? 0);
      const rx = dz(pad.axes[2] ?? 0);
      const ry = dz(pad.axes[3] ?? 0);
      if (lx || ly) {
        f.moveX = lx;
        f.moveY = -ly;
        this.lastDevice = 'pad';
      }
      const lockHeld = !!pad.buttons[6]?.pressed;
      if (lockHeld) {
        // ロックオン中の右スティックは、弾いて対象を切り替える
        if (this.padFlickReady && Math.abs(rx) > 0.6) {
          if (rx > 0) f.switchTargetRight = true;
          else f.switchTargetLeft = true;
          this.padFlickReady = false;
        }
        if (Math.abs(rx) < 0.3) this.padFlickReady = true;
      } else if (rx || ry) {
        f.lookX += rx * Math.abs(rx) * this.padSensitivity * dtFrame;
        f.lookY += ry * Math.abs(ry) * this.padSensitivity * 0.7 * dtFrame * (this.invertY ? -1 : 1);
        f.lookActive = true;
      }
      pad.buttons.forEach((btn, i) => {
        const a = this.bindings.pad[i];
        if (!a) return;
        const pressed = btn.pressed || btn.value > 0.5;
        if (pressed) {
          this.lastDevice = 'pad';
          if ((BUTTONS as readonly string[]).includes(a)) f[a as (typeof BUTTONS)[number]] = true;
          if (!this.padPrev[i] && (a === 'pause' || a === 'map' || a === 'cameraReset')) this.oneShot.add(a);
        }
        this.padPrev[i] = pressed;
      });
      if (pad.buttons[4]?.pressed && !this.padPrev[4]) this.oneShot.add('prevSpecial');
      if (pad.buttons[5]?.pressed && !this.padPrev[5]) this.oneShot.add('nextSpecial');
      this.padPrev[4] = !!pad.buttons[4]?.pressed;
      this.padPrev[5] = !!pad.buttons[5]?.pressed;
      break;
    }
    if (this.takeOneShot('cameraReset')) f.cameraReset = true;
    return f;
  }
}
