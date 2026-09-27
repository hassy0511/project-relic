import type { DialogueFile, DialogueLine, EventFile, EventStep } from './script';

/** 会話を表示中の状態。UI はこれを読んで描く */
export interface DialogueView {
  id: string;
  who: string;
  face: string;
  text: string;
  /** 1 文字ずつ表示している途中の文字数 */
  shown: number;
  index: number;
  total: number;
}

export interface StoryHost {
  giveItem(item: string): void;
  giveCells(n: number): void;
  setFlag(flag: string): void;
  message(text: string): void;
  setObjective(text: string): void;
  sfx(id: string): void;
}

const CHARS_PER_SEC = 45;

/** 会話とイベントの台本を進める */
export class Story {
  readonly flags: Record<string, boolean> = {};
  dialogue: DialogueView | null = null;
  private lines: DialogueLine[] = [];
  private lineIndex = 0;
  private shownF = 0;
  private eventQueue: EventStep[] = [];
  private waitTime = 0;
  private waitingDialogue = false;

  constructor(
    private readonly dialogues: DialogueFile,
    private readonly events: EventFile,
    private readonly host: StoryHost,
  ) {}

  /** 会話中、またはイベントが止めている間は true（プレイヤーは操作できない） */
  get blocking(): boolean {
    return this.dialogue !== null;
  }

  get runningEvent(): boolean {
    return this.eventQueue.length > 0 || this.waitingDialogue || this.waitTime > 0;
  }

  startDialogue(id: string): void {
    const d = this.dialogues[id];
    if (!d) throw new Error(`会話が見つからない: ${id}`);
    this.lines = d.lines;
    this.lineIndex = 0;
    this.dialogue = null;
    this.advanceToText(id);
  }

  startEvent(id: string): void {
    const e = this.events[id];
    if (!e) throw new Error(`イベントが見つからない: ${id}`);
    this.eventQueue.push(...e.steps);
  }

  /** 決定ボタンが押されたとき。表示途中なら全文を出し、出し終わっていれば次の行へ */
  confirm(): void {
    const d = this.dialogue;
    if (!d) return;
    if (d.shown < d.text.length) {
      d.shown = d.text.length;
      this.shownF = d.text.length;
      return;
    }
    this.lineIndex++;
    this.advanceToText(d.id);
  }

  update(dt: number): void {
    if (this.dialogue) {
      const d = this.dialogue;
      if (d.shown < d.text.length) {
        this.shownF += CHARS_PER_SEC * dt;
        d.shown = Math.min(d.text.length, Math.floor(this.shownF));
      }
      return;
    }
    if (this.waitingDialogue) this.waitingDialogue = false;
    if (this.waitTime > 0) {
      this.waitTime -= dt;
      return;
    }
    while (this.eventQueue.length > 0 && !this.dialogue && this.waitTime <= 0) {
      const step = this.eventQueue.shift()!;
      this.runStep(step);
    }
  }

  private runStep(step: EventStep): void {
    const h = this.host;
    if ('say' in step) {
      this.startDialogue(step.say);
      this.waitingDialogue = true;
    } else if ('flag' in step) {
      this.flags[step.flag] = true;
      h.setFlag(step.flag);
    } else if ('give' in step) {
      if (step.give.cells) h.giveCells(step.give.cells);
      if (step.give.item) h.giveItem(step.give.item);
    } else if ('wait' in step) {
      this.waitTime = step.wait;
    } else if ('message' in step) {
      h.message(step.message);
    } else if ('objective' in step) {
      h.setObjective(step.objective);
    } else if ('sfx' in step) {
      h.sfx(step.sfx);
    }
  }

  /** 次の「セリフ」の行まで進める。途中の動作（アイテムを渡す等）はその場で実行する */
  private advanceToText(id: string): void {
    while (this.lineIndex < this.lines.length) {
      const line = this.lines[this.lineIndex];
      if ('who' in line) {
        this.shownF = 0;
        this.dialogue = {
          id,
          who: line.who,
          face: line.face,
          text: line.text,
          shown: 0,
          index: this.lineIndex,
          total: this.lines.length,
        };
        return;
      }
      if (line.action === 'give_item') this.host.giveItem(line.item);
      else if (line.action === 'objective') this.host.setObjective(line.text);
      else if (line.action === 'flag') {
        this.flags[line.flag] = true;
        this.host.setFlag(line.flag);
      }
      this.lineIndex++;
    }
    this.dialogue = null;
  }
}
