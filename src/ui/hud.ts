import * as THREE from 'three';
import type { Game } from '../sim/game';

const FACE_COLORS: Record<string, string> = {
  ヤーナ: '#b5452f',
  ナゴミ: '#ffb23e',
  ハル: '#c9a46a',
};

/**
 * HUD（プレイ中の表示）と会話ウィンドウ。HTML で描く。
 * 見た目は仮。Codex の UI デザイン（W2-08）が届いたら差し替える。
 */
export class Hud {
  private root: HTMLDivElement;
  private hpFill: HTMLDivElement;
  private hpText: HTMLSpanElement;
  private weFill: HTMLDivElement;
  private weName: HTMLSpanElement;
  private heals: HTMLSpanElement;
  private cells: HTMLDivElement;
  private objective: HTMLDivElement;
  private prompt: HTMLDivElement;
  private reticle: HTMLDivElement;
  private reticleHp: HTMLDivElement;
  private reticleWeak: HTMLDivElement;
  private reticleScan: HTMLDivElement;
  private charge: HTMLDivElement;
  private dialogue: HTMLDivElement;
  private dlgName: HTMLDivElement;
  private dlgText: HTMLDivElement;
  private dlgFace: HTMLDivElement;
  private toast: HTMLDivElement;
  private toastTime = 0;
  private dmg: HTMLDivElement;
  private dmgTime = 0;
  private lastCells = -1;
  private cellsTime = 0;
  device: 'keyboard' | 'pad' = 'keyboard';

  constructor(parent: HTMLElement) {
    this.root = el('div', 'hud', parent);
    const vitals = el('div', 'hud-vitals', this.root);
    const hpRow = el('div', 'hud-row', vitals);
    el('span', 'hud-label', hpRow).textContent = 'HP';
    const hpBar = el('div', 'hud-bar hud-hp', hpRow);
    this.hpFill = el('div', 'hud-fill', hpBar);
    this.hpText = el('span', 'hud-num', hpRow);
    const weRow = el('div', 'hud-row', vitals);
    this.weName = el('span', 'hud-label hud-we-name', weRow);
    const weBar = el('div', 'hud-bar hud-we', weRow);
    this.weFill = el('div', 'hud-fill', weBar);
    this.heals = el('span', 'hud-heals', vitals);

    this.cells = el('div', 'hud-cells', this.root);
    this.objective = el('div', 'hud-objective', this.root);
    this.prompt = el('div', 'hud-prompt', this.root);
    this.reticle = el('div', 'hud-reticle', this.root);
    this.reticleHp = el('div', 'hud-reticle-hp', this.reticle);
    this.reticleWeak = el('div', 'hud-reticle-weak', this.reticle);
    this.reticleWeak.textContent = '弱点：背面';
    this.reticleScan = el('div', 'hud-reticle-scan', this.reticle);
    this.charge = el('div', 'hud-charge', this.root);
    this.toast = el('div', 'hud-toast', this.root);
    this.dmg = el('div', 'hud-damage', this.root);

    this.dialogue = el('div', 'dlg', this.root);
    this.dlgFace = el('div', 'dlg-face', this.dialogue);
    const body = el('div', 'dlg-body', this.dialogue);
    this.dlgName = el('div', 'dlg-name', body);
    this.dlgText = el('div', 'dlg-text', body);
    el('div', 'dlg-next', this.dialogue).textContent = '▼';
  }

  setVisible(v: boolean): void {
    this.root.style.display = v ? '' : 'none';
  }

  showToast(text: string): void {
    this.toast.textContent = text;
    this.toastTime = 3;
  }

  flashDamage(): void {
    this.dmgTime = 0.4;
  }

  update(game: Game, camera: THREE.PerspectiveCamera, dt: number): void {
    const p = game.player;
    this.hpFill.style.width = `${(p.hp / p.maxHp) * 100}%`;
    this.hpFill.classList.toggle('danger', p.hp / p.maxHp < 0.3);
    this.hpText.textContent = `${Math.ceil(p.hp)}`;
    const hasDrill = game.hasItem('special.drill');
    this.weName.textContent = hasDrill ? 'ドリル' : '———';
    this.weFill.style.width = hasDrill ? `${p.weaponEnergy}%` : '0%';
    this.heals.textContent = `補修パック ×${p.heals}`;

    if (game.cells !== this.lastCells) {
      this.lastCells = game.cells;
      this.cellsTime = 3;
    }
    this.cellsTime -= dt;
    this.cells.textContent = `セル ${game.cells.toLocaleString()}`;
    this.cells.style.opacity = this.cellsTime > 0 ? '1' : '0.35';
    this.objective.textContent = game.objective ? `目的：${game.objective}` : '';

    // 調べる・話すの案内
    const f = game.focus;
    const btn = this.device === 'pad' ? 'A' : 'Space';
    this.prompt.textContent = f && !game.story.dialogue ? `[${btn}] ${f.prompt}` : '';

    // ロックオンの照準
    const t = game.lockOn.target;
    if (t) {
      const c = t.center();
      c.y += t.height * 0.1;
      const v = c.project(camera);
      const x = (v.x * 0.5 + 0.5) * window.innerWidth;
      const y = (-v.y * 0.5 + 0.5) * window.innerHeight;
      this.reticle.style.display = v.z < 1 ? 'block' : 'none';
      this.reticle.style.transform = `translate(${x}px, ${y}px)`;
      this.reticleHp.style.setProperty('--hp', `${(t.hp / t.maxHp) * 100}%`);
      const scanned = game.lockOn.scanned.has(t.kind);
      this.reticleWeak.style.display = scanned ? 'block' : 'none';
      this.reticleWeak.textContent = t.kind === 'charger' ? '弱点：激突後の側面' : '弱点：背面の核';
      this.reticleScan.style.setProperty('--scan', `${game.lockOn.scanProgress * 100}%`);
      this.reticleScan.style.display = scanned ? 'none' : 'block';
    } else {
      this.reticle.style.display = 'none';
    }

    // チャージ
    const ch = p.gunCharge;
    this.charge.style.display = ch > 0.15 ? 'block' : 'none';
    const cfg = game.tuning.gun;
    const lv = ch >= cfg.chargeLv2Time ? 2 : ch >= cfg.chargeLv1Time ? 1 : 0;
    this.charge.style.setProperty('--c', `${Math.min(1, ch / cfg.chargeLv2Time) * 100}%`);
    this.charge.dataset.lv = String(lv);

    // 会話
    const d = game.story.dialogue;
    this.dialogue.style.display = d ? 'flex' : 'none';
    if (d) {
      this.dlgName.textContent = d.who;
      this.dlgText.textContent = d.text.slice(0, d.shown);
      this.dlgFace.textContent = d.who.slice(0, 1);
      this.dlgFace.style.background = FACE_COLORS[d.who] ?? '#777';
      this.dlgFace.title = d.face;
      this.dialogue.classList.toggle('done', d.shown >= d.text.length);
    }

    this.toastTime -= dt;
    this.toast.style.opacity = this.toastTime > 0 ? String(Math.min(1, this.toastTime)) : '0';
    this.dmgTime = Math.max(0, this.dmgTime - dt);
    this.dmg.style.opacity = String(this.dmgTime * 1.5);
  }
}

export function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, parent: HTMLElement): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  e.className = cls;
  parent.appendChild(e);
  return e;
}
