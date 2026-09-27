import { z } from 'zod';
import { parse } from 'yaml';

/** 会話の 1 行、または会話の途中で起きる動作 */
const DialogueLine = z.union([
  z.object({ who: z.string(), face: z.string().default('normal'), text: z.string() }),
  z.object({ action: z.literal('give_item'), item: z.string() }),
  z.object({ action: z.literal('flag'), flag: z.string() }),
  z.object({ action: z.literal('objective'), text: z.string() }),
]);

export const DialogueFileSchema = z.record(z.string(), z.object({ lines: z.array(DialogueLine) }));
export type DialogueLine = z.infer<typeof DialogueLine>;
export type DialogueFile = z.infer<typeof DialogueFileSchema>;

/** イベントの台本の 1 手順 */
const EventStep = z.union([
  z.object({ say: z.string() }),
  z.object({ flag: z.string() }),
  z.object({ give: z.object({ cells: z.number().optional(), item: z.string().optional() }) }),
  z.object({ wait: z.number() }),
  z.object({ message: z.string() }),
  z.object({ objective: z.string() }),
  z.object({ sfx: z.string() }),
]);

export const EventFileSchema = z.record(z.string(), z.object({ steps: z.array(EventStep) }));
export type EventStep = z.infer<typeof EventStep>;
export type EventFile = z.infer<typeof EventFileSchema>;

export function parseDialogues(text: string): DialogueFile {
  return DialogueFileSchema.parse(parse(text));
}

export function parseEvents(text: string): EventFile {
  return EventFileSchema.parse(parse(text));
}

/** 会話の 1 行の長さの上限（会話ウィンドウに収まる文字数） */
export const MAX_LINE_LENGTH = 90;

export function validateDialogues(d: DialogueFile): string[] {
  const errors: string[] = [];
  for (const [id, dlg] of Object.entries(d)) {
    for (const line of dlg.lines) {
      if ('text' in line && line.text.length > MAX_LINE_LENGTH) {
        errors.push(`${id}: 1 行が長すぎる（${line.text.length} 文字）: ${line.text.slice(0, 20)}…`);
      }
    }
  }
  return errors;
}
