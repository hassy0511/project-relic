/**
 * 1 刻み分の入力。sim はこれだけを見て動く（キーやボタンの種類を知らない）。
 * 記録・再生（リプレイ）できるよう、ただのデータにしておく。
 */
export interface InputFrame {
  /** 移動（-1〜1）。moveY は前が +1 */
  moveX: number;
  moveY: number;
  /** カメラ操作（この刻みでの回転量、ラジアン） */
  lookX: number;
  lookY: number;
  /** カメラ操作の入力があったか（自動で背後に回る処理の判定に使う） */
  lookActive: boolean;
  /** ボタン：押されている間 true */
  jump: boolean;
  dash: boolean;
  fire: boolean;
  sword: boolean;
  special: boolean;
  lockOn: boolean;
  heal: boolean;
  /** 1 回だけ起きる操作 */
  switchTargetLeft: boolean;
  switchTargetRight: boolean;
  cameraReset: boolean;
}

export function emptyInput(): InputFrame {
  return {
    moveX: 0,
    moveY: 0,
    lookX: 0,
    lookY: 0,
    lookActive: false,
    jump: false,
    dash: false,
    fire: false,
    sword: false,
    special: false,
    lockOn: false,
    heal: false,
    switchTargetLeft: false,
    switchTargetRight: false,
    cameraReset: false,
  };
}

/** ボタンの「押した瞬間」「離した瞬間」を前の刻みとの比較で得る */
export class ButtonEdges {
  private prev = emptyInput();
  private cur = emptyInput();

  update(frame: InputFrame): void {
    this.prev = this.cur;
    this.cur = frame;
  }

  pressed(key: ButtonKey): boolean {
    return this.cur[key] && !this.prev[key];
  }

  released(key: ButtonKey): boolean {
    return !this.cur[key] && this.prev[key];
  }

  down(key: ButtonKey): boolean {
    return this.cur[key];
  }
}

export type ButtonKey = 'jump' | 'dash' | 'fire' | 'sword' | 'special' | 'lockOn' | 'heal';
