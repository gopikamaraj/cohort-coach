// Child avatars, step for step the same as services/api/sprites/avatar.py.
import { clothColours, expressionFile, hairColours, palette, parts, personas, skinTones } from "./data";
import type { Look, Palette, Part } from "./data";
import { partMarkup, validateSvg } from "./grammar";
import { Rng } from "./rng";

const sortedKeys = (o: Record<string, unknown>): string[] => Object.keys(o).sort();

export const expressionIds = (): string[] => Object.keys(expressionFile.expressions);

export function lookFromSeed(seed: number): Look {
  const rng = new Rng(seed);
  const pick = (o: Record<string, unknown>): string => sortedKeys(o)[rng.below(Object.keys(o).length)] as string;
  // object literal fields evaluate in order, matching the Python dict
  return {
    body: pick(parts.bodies),
    skin: rng.below(skinTones.length),
    hair_style: pick(parts.hair_styles),
    hair_colour: rng.below(hairColours.length),
    outfit: pick(parts.outfits),
    cloth_a: rng.below(clothColours.length),
    cloth_b: rng.below(clothColours.length),
    accessory: pick(parts.accessories),
  };
}

export function personaLook(id: string): { persona: string; seed: number; look: Look } {
  const rec = personas[id];
  if (!rec) throw new Error(`unknown persona ${id}`);
  const look = lookFromSeed(rec.seed);
  if (typeof rec.look === "object") Object.assign(look, rec.look);
  return { persona: id, seed: rec.seed, look };
}

export const personaIds = (): string[] => Object.keys(personas);

function avatarPalette(look: Look, base = "default"): Palette {
  const pal = palette(base);
  pal.skin = skinTones[look.skin] as string;
  pal.hair = hairColours[look.hair_colour] as string;
  pal.cloth_a = clothColours[look.cloth_a] as string;
  pal.cloth_b = look.outfit !== "outfit_a" ? (clothColours[look.cloth_b] as string) : (pal.cloth_b as string);
  return pal;
}

function group(cls: string, shapes: Part[], pal: Palette, extra = ""): string {
  return `<g class="${cls}"${extra}>${shapes.map((s) => partMarkup(s, pal, "av")).join("")}</g>`;
}

export function avatarSvg(look: Look, expression = "neutral", mouth = "closed", base = "default"): string {
  const face = expressionFile.expressions[expression];
  if (!face) throw new Error(`unknown expression ${expression}`);
  const fp = expressionFile.parts;
  const pal = avatarPalette(look, base);
  const body = group("body", [...(parts.bodies[look.body] as Part[]), ...(parts.outfits[look.outfit] as Part[])], pal);
  const head = group(
    "head",
    [...parts.head, ...(parts.hair_styles[look.hair_style] as Part[]), ...(parts.accessories[look.accessory] as Part[])],
    pal,
  );
  const eyes = group("face", [...(fp.eyes[face.eyes] as Part[]), ...(fp.brows[face.brows] as Part[])], pal);
  const closedVisible = mouth === "closed";
  const closed = group("mouth mouth-closed", fp.mouth_closed[face.mouth_closed] as Part[], pal, closedVisible ? "" : ' opacity="0"');
  const opened = group("mouth mouth-open", fp.mouth_open[face.mouth_open] as Part[], pal, closedVisible ? ' opacity="0"' : "");
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 72" role="img" ' +
    `data-alt="sprite.avatar.child" data-expression="${expression}">${body}${head}${eyes}${closed}${opened}</svg>`;
  const bad = validateSvg(svg);
  if (bad.length) throw new Error(`avatar outside the grammar: ${bad}`);
  return svg;
}

export interface Seat {
  look: Look;
  expression?: string;
  speaking?: boolean;
}

export function seatRow(children: Seat[], base = "default"): string {
  let inner = "";
  children.forEach((c, i) => {
    const svg = avatarSvg(c.look, c.expression ?? "neutral", c.speaking ? "open" : "closed", base);
    const body = svg.slice(svg.indexOf(">") + 1, svg.length - "</svg>".length);
    inner += `<svg class="seat" x="${i * 64}" y="0" width="64" height="72" viewBox="0 0 64 72">${body}</svg>`;
  });
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${64 * children.length} 72" role="img" ` +
    `data-alt="sprite.scene.seat_row">${inner}</svg>`
  );
}
