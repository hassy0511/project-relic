import { z } from 'zod';

export const SAVE_VERSION = 1;

export const SaveSchema = z.object({
  version: z.literal(SAVE_VERSION),
  savedAt: z.string(),
  playTime: z.number(),
  area: z.string(),
  checkpoint: z.string(),
  pos: z.tuple([z.number(), z.number(), z.number()]),
  yaw: z.number(),
  hp: z.number(),
  maxHp: z.number(),
  heals: z.number(),
  weaponEnergy: z.number(),
  cells: z.number(),
  items: z.array(z.string()),
  equippedChips: z.array(z.string()),
  flags: z.record(z.string(), z.boolean()),
  opened: z.array(z.string()),
  broken: z.array(z.string()),
  scanned: z.array(z.string()),
  objective: z.string(),
});

export type SaveData = z.infer<typeof SaveSchema>;

/** 保存されたデータを読む。形式が合わなければ null。版が変わったらここで変換する */
export function parseSave(json: string): SaveData | null {
  try {
    const raw = JSON.parse(json);
    const r = SaveSchema.safeParse(raw);
    return r.success ? r.data : null;
  } catch {
    return null;
  }
}
