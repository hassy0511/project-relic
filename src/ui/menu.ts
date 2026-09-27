import type { Game } from '../sim/game';
import { el } from './hud';

const HELP: [string, string][] = [
  ['移動', 'WASD ／ 左スティック'],
  ['カメラ', 'マウス（画面をクリックで固定）／ 矢印キー ／ 右スティック'],
  ['ジャンプ・調べる', 'Space ／ A'],
  ['ダッシュ', 'Shift ／ B'],
  ['主武器', '左クリック ／ RT（チャージ型は長押しで溜め）'],
  ['光刃', 'E ／ X（連打でコンボ、長押しで溜め斬り）'],
  ['特殊武器', 'Q ／ Y（押しっぱなし）'],
  ['ロックオン', '右クリック ／ LT（押している間）'],
  ['対象の切り替え', 'ロックオン中にマウスを横に振る ／ 右スティックを弾く'],
  ['回復', 'R ／ 十字キー上'],
  ['カメラを背後へ', 'C ／ R3'],
  ['ポーズ', 'Esc ／ Menu'],
  ['調整パネル', 'F1'],
];

/** タイトルとポーズのメニュー。キーボードとゲームパッドで選べる */
export class Menu {
  private root: HTMLDivElement;
  private buttons: HTMLButtonElement[] = [];
  private index = 0;
  private padPrev: Record<number, boolean> = {};
  private padAxisReady = true;

  constructor(
    parent: HTMLElement,
    private readonly onMove: () => void,
    private readonly onOk: () => void,
  ) {
    this.root = el('div', 'screen interactive', parent);
    this.root.style.display = 'none';
    window.addEventListener('keydown', (e) => {
      if (this.root.style.display === 'none') return;
      if (e.code === 'ArrowDown' || e.code === 'KeyS') this.move(1);
      else if (e.code === 'ArrowUp' || e.code === 'KeyW') this.move(-1);
      else if (e.code === 'Enter' || e.code === 'Space') {
        e.preventDefault();
        this.activate();
      }
    });
  }

  get open(): boolean {
    return this.root.style.display !== 'none';
  }

  hide(): void {
    this.root.style.display = 'none';
  }

  private build(title: boolean, items: [string, () => void, boolean?][], extra?: (root: HTMLElement) => void): void {
    this.root.innerHTML = '';
    this.root.className = `screen interactive${title ? ' title' : ''}`;
    this.root.style.display = 'flex';
    if (extra) extra(this.root);
    const menu = el('div', 'menu', this.root);
    this.buttons = items.map(([label, fn, disabled]) => {
      const b = el('button', '', menu);
      b.textContent = label;
      b.disabled = !!disabled;
      b.addEventListener('click', () => {
        this.onOk();
        fn();
      });
      b.addEventListener('mouseenter', () => this.focus(this.buttons.indexOf(b)));
      return b;
    });
    const help = el('div', 'help', this.root);
    for (const [k, v] of HELP) {
      el('b', '', help).textContent = k;
      el('span', '', help).textContent = v;
    }
    this.index = this.buttons.findIndex((b) => !b.disabled);
    this.focus(this.index);
  }

  showTitle(hasSave: boolean, cb: { newGame: () => void; continue: () => void }): void {
    this.build(
      true,
      [
        ['はじめから', cb.newGame],
        ['つづきから', cb.continue, !hasSave],
      ],
      (root) => {
        el('div', 'logo', root).textContent = 'ARKWALKER';
        el('div', 'logo-sub', root).textContent = 'アークウォーカー';
        el('div', 'badge', root).textContent = 'MVP 試遊版（仮の見た目）';
      },
    );
  }

  showPause(game: Game, cb: { resume: () => void; toggleChip: () => void; loadSave: () => void; toTitle: () => void }): void {
    const hasChip = game.hasItem('chip.charge');
    const chipLabel = hasChip
      ? `チップ「チャージ化」：${game.chargeType ? '装着中（外す）' : '外している（付ける）'}`
      : 'チップ：まだ持っていない';
    this.build(false, [
      ['ゲームに戻る', cb.resume],
      [
        chipLabel,
        () => {
          cb.toggleChip();
          this.showPause(game, cb);
        },
        !hasChip,
      ],
      ['最後のセーブから再開', cb.loadSave],
      ['タイトルへ', cb.toTitle],
    ], (root) => {
      el('div', 'logo', root).textContent = 'PAUSE';
      el('div', 'note', root).textContent = `セル ${game.cells}　／　プレイ時間 ${Math.floor(game.playTime / 60)} 分`;
    });
  }

  private focus(i: number): void {
    this.buttons.forEach((b, k) => b.classList.toggle('focus', k === i));
    this.index = i;
  }

  private move(d: number): void {
    if (!this.buttons.length) return;
    let i = this.index;
    for (let n = 0; n < this.buttons.length; n++) {
      i = (i + d + this.buttons.length) % this.buttons.length;
      if (!this.buttons[i].disabled) break;
    }
    if (i !== this.index) this.onMove();
    this.focus(i);
  }

  private activate(): void {
    const b = this.buttons[this.index];
    if (b && !b.disabled) b.click();
  }

  /** ゲームパッドでの操作（毎フレーム呼ぶ） */
  poll(): void {
    if (!this.open) return;
    const pad = (navigator.getGamepads?.() ?? []).find((p) => p);
    if (!pad) return;
    const pressed = (i: number) => {
      const now = !!pad.buttons[i]?.pressed;
      const edge = now && !this.padPrev[i];
      this.padPrev[i] = now;
      return edge;
    };
    const y = pad.axes[1] ?? 0;
    if (Math.abs(y) < 0.3) this.padAxisReady = true;
    if (this.padAxisReady && Math.abs(y) > 0.6) {
      this.move(y > 0 ? 1 : -1);
      this.padAxisReady = false;
    }
    if (pressed(12)) this.move(-1);
    if (pressed(13)) this.move(1);
    if (pressed(0)) this.activate();
  }
}
