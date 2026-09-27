/** sim の固定刻み（60Hz） */
export const DT = 1 / 60;

/** プレイヤーの寸法（docs/design/30_レベルデザイン設計.md 1.1） */
export const PLAYER_RADIUS = 0.35;
export const PLAYER_HEIGHT = 1.55;
/** 胸の高さ（撃つ位置、狙われる位置） */
export const PLAYER_CHEST = 1.1;

/** 奈落の高さ。これより下に落ちたら直前の足場に戻す */
export const KILL_Y = -30;
