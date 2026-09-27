import * as THREE from 'three';

const SFX_IDS = [
  'shot', 'shot_charge', 'slash', 'slash_charge', 'hit', 'hit_weak', 'explode', 'jump', 'land', 'dash', 'drill',
  'alert', 'charge', 'crash', 'chest', 'item', 'pickup', 'save', 'heal', 'wall_break', 'ui_move', 'ui_ok', 'blip',
];

/** 効果音と BGM。音はすべて ID で呼び、ファイルの差し替えだけで音を変えられる */
export class Audio {
  private ctx: AudioContext | null = null;
  private buffers = new Map<string, AudioBuffer>();
  private master!: GainNode;
  private sfxBus!: GainNode;
  private musicBus!: GainNode;
  private music: AudioBufferSourceNode | null = null;
  private lastPlayed = new Map<string, number>();
  volumes = { master: 0.8, music: 0.5, sfx: 0.8 };

  constructor(private readonly base: string) {}

  /** ブラウザの制約で、最初の操作のあとに呼ぶ */
  async start(): Promise<void> {
    if (this.ctx) return;
    this.ctx = new AudioContext();
    this.master = this.ctx.createGain();
    this.sfxBus = this.ctx.createGain();
    this.musicBus = this.ctx.createGain();
    this.sfxBus.connect(this.master);
    this.musicBus.connect(this.master);
    this.master.connect(this.ctx.destination);
    this.applyVolumes();
    await Promise.all([...SFX_IDS, 'bgm_trial'].map((id) => this.load(id)));
  }

  applyVolumes(): void {
    if (!this.ctx) return;
    this.master.gain.value = this.volumes.master;
    this.musicBus.gain.value = this.volumes.music;
    this.sfxBus.gain.value = this.volumes.sfx;
  }

  private async load(id: string): Promise<void> {
    try {
      const res = await fetch(`${this.base}assets/audio/${id}.ogg`);
      const data = await res.arrayBuffer();
      this.buffers.set(id, await this.ctx!.decodeAudioData(data));
    } catch (e) {
      console.warn('音を読み込めなかった', id, e);
    }
  }

  /** 効果音。位置を渡すと、聞き手（カメラ）との距離で音量と左右が変わる */
  play(id: string, at?: THREE.Vector3, listener?: THREE.Camera, gain = 1): void {
    const ctx = this.ctx;
    const buf = this.buffers.get(id);
    if (!ctx || !buf) return;
    // 同じ音が同時に鳴りすぎないように
    const now = ctx.currentTime;
    if (now - (this.lastPlayed.get(id) ?? -1) < 0.03) return;
    this.lastPlayed.set(id, now);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = 0.95 + Math.random() * 0.1;
    const g = ctx.createGain();
    g.gain.value = gain;
    let node: AudioNode = g;
    if (at && listener) {
      const rel = at.clone().applyMatrix4(listener.matrixWorldInverse);
      const dist = rel.length();
      g.gain.value = gain * Math.min(1, 6 / Math.max(6, dist));
      const pan = ctx.createStereoPanner();
      pan.pan.value = THREE.MathUtils.clamp(rel.x / Math.max(1, dist), -0.8, 0.8);
      g.connect(pan);
      node = pan;
    }
    src.connect(g);
    node.connect(this.sfxBus);
    src.start();
  }

  playMusic(id: string): void {
    const ctx = this.ctx;
    const buf = this.buffers.get(id);
    if (!ctx || !buf) return;
    this.music?.stop();
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    src.connect(this.musicBus);
    src.start();
    this.music = src;
  }

  setPaused(p: boolean): void {
    if (!this.ctx) return;
    if (p) void this.ctx.suspend();
    else void this.ctx.resume();
  }
}
