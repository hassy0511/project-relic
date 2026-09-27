import { z } from 'zod';
import { parse } from 'yaml';

/** 地形のデータ。描画側（GLB の読み込み）かテストが作り、sim に渡す */
export interface AreaGeometry {
  /** 当たり判定用の三角形メッシュ（ワールド座標） */
  meshes: { vertices: Float32Array; indices: Uint32Array }[];
  /** 名前つきの目印（Blender の Empty。名前の先頭の m_ は取り除く） */
  markers: Record<string, { pos: [number, number, number]; yaw: number }>;
}

const Vec3 = z.tuple([z.number(), z.number(), z.number()]);

const EnemyPlacement = z.object({
  type: z.enum(['sentry', 'charger']),
  at: z.string(),
});

const PropPlacement = z.discriminatedUnion('type', [
  z.object({ type: z.literal('breakable'), id: z.string(), at: z.string(), size: Vec3, breaksWith: z.literal('drill') }),
  z.object({
    type: z.literal('chest'),
    id: z.string(),
    at: z.string(),
    contents: z.object({ cells: z.number().optional(), item: z.string().optional() }),
  }),
  z.object({ type: z.literal('npc'), id: z.string(), at: z.string(), name: z.string(), talk: z.string() }),
  z.object({ type: z.literal('beacon'), id: z.string(), at: z.string() }),
]);

const TriggerPlacement = z.object({
  id: z.string(),
  at: z.string(),
  size: Vec3,
  event: z.string(),
  once: z.boolean().default(true),
});

const CheckpointPlacement = z.object({ id: z.string(), at: z.string(), radius: z.number().default(4) });

export const PlacementSchema = z.object({
  id: z.string(),
  name: z.string(),
  model: z.string(),
  playerStart: z.string(),
  objective: z.string().default(''),
  enemies: z.array(EnemyPlacement).default([]),
  props: z.array(PropPlacement).default([]),
  triggers: z.array(TriggerPlacement).default([]),
  checkpoints: z.array(CheckpointPlacement).default([]),
});

export type Placement = z.infer<typeof PlacementSchema>;
export type PropDef = z.infer<typeof PropPlacement>;

export function parsePlacement(yamlText: string): Placement {
  return PlacementSchema.parse(parse(yamlText));
}

/** 配置が参照している目印が、地形にすべてあるか確かめる */
export function validatePlacement(p: Placement, geo: AreaGeometry): string[] {
  const missing: string[] = [];
  const need = [
    p.playerStart,
    ...p.enemies.map((e) => e.at),
    ...p.props.map((e) => e.at),
    ...p.triggers.map((e) => e.at),
    ...p.checkpoints.map((e) => e.at),
  ];
  for (const m of need) if (!geo.markers[m]) missing.push(m);
  return missing;
}
