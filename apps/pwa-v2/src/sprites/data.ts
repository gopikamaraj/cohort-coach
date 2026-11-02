// The sprite data, read from content/sprites (the same files the Python renderer reads).
import avatarParts from "../../../../content/sprites/avatar_parts.v1.json";
import expressionsFile from "../../../../content/sprites/expressions.v1.json";
import palettesFile from "../../../../content/sprites/palettes.v1.json";
import personasFile from "../../../../content/sprites/personas.v1.json";

export type Part = Record<string, string | number>;
export interface Gradient {
  type: "radialGradient" | "linearGradient";
  id: string;
  stops: { offset: number; color: string }[];
  [key: string]: unknown;
}
export interface ItemSpec {
  id: string;
  version: number;
  category: string;
  viewBox: number[];
  parts: Part[];
  defs?: Gradient[];
  count: { mode: string; n?: number };
  alt: { key: string };
  topics: string[];
}
export type Palette = Record<string, string>;
export interface Look {
  body: string;
  skin: number;
  hair_style: string;
  hair_colour: number;
  outfit: string;
  cloth_a: number;
  cloth_b: number;
  accessory: string;
}

const itemFiles = import.meta.glob("../../../../content/sprites/items/*.v1.json", { eager: true, import: "default" }) as Record<string, ItemSpec>;
const ITEMS: Record<string, ItemSpec> = {};
for (const spec of Object.values(itemFiles)) ITEMS[spec.id] = spec;

export function loadItem(id: string): ItemSpec {
  const spec = ITEMS[id];
  if (!spec) throw new Error(`unknown item ${id}`);
  return spec;
}
export const itemIds = (): string[] => Object.keys(ITEMS).sort();

export const SLOTS = ["skin", "hair", "cloth_a", "cloth_b", "accent", "item_a", "item_b", "mat", "ink"] as const;
const PALETTES = palettesFile.palettes as Record<string, Palette>;
export const palette = (name = "default"): Palette => ({ ...(PALETTES[name] as Palette) });
export const skinTones: string[] = palettesFile.skin_tones;
export const hairColours: string[] = palettesFile.hair_colours;
export const clothColours: string[] = palettesFile.cloth_colours;

export const parts = avatarParts as unknown as {
  bodies: Record<string, Part[]>;
  outfits: Record<string, Part[]>;
  head: Part[];
  hair_styles: Record<string, Part[]>;
  accessories: Record<string, Part[]>;
};
export const expressionFile = expressionsFile as unknown as {
  parts: Record<"eyes" | "brows" | "mouth_closed" | "mouth_open", Record<string, Part[]>>;
  expressions: Record<string, { eyes: string; brows: string; mouth_closed: string; mouth_open: string }>;
};
export const personas = Object.fromEntries(personasFile.personas.map((p) => [p.id, p])) as Record<string, { id: string; seed: number; look: string | Partial<Look> }>;
