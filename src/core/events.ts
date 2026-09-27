/** sim から view・audio・UI へ伝える出来事。sim は描画を知らないので、出来事だけを積んでおく */
export type GameEvent =
  | { type: 'sfx'; id: string; x?: number; y?: number; z?: number }
  | { type: 'hit'; x: number; y: number; z: number; kind: 'normal' | 'weak' | 'armor' }
  | { type: 'enemyDestroyed'; x: number; y: number; z: number }
  | { type: 'wallBroken'; id: string }
  | { type: 'chestOpened'; id: string }
  | { type: 'message'; text: string }
  | { type: 'saved' }
  | { type: 'playerHurt'; amount: number }
  | { type: 'playerDied' }
  | { type: 'shake'; strength: number };

export class EventQueue {
  private items: GameEvent[] = [];

  push(e: GameEvent): void {
    this.items.push(e);
  }

  /** 積まれた出来事を取り出して空にする */
  drain(): GameEvent[] {
    const out = this.items;
    this.items = [];
    return out;
  }
}
