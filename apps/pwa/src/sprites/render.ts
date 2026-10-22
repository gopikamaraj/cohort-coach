// One entry point per case, the same shape as services/api/sprites/golden.py render_case.
import { avatarSvg, personaLook, seatRow } from "./avatar";
import { loadItem, palette } from "./data";
import type { ItemSpec } from "./data";
import * as L from "./layouts";

export interface Case {
  fn: string;
  item?: string | null;
  args?: Record<string, number | number[]>;
  seed?: number;
  palette?: string;
  persona?: string;
  expression?: string;
  mouth?: string;
  children?: { persona: string; expression: string; speaking: boolean }[];
}

export function renderLayout(layout: string, itemId: string | null | undefined, args: Record<string, number | number[]>, palName = "default", seed = 0): L.Scene {
  const pal = palette(palName);
  const spec = (itemId ? loadItem(itemId) : ({} as ItemSpec));
  const n = (k: string): number => args[k] as number;
  switch (layout) {
    case "row": return L.row(spec, n("n"), pal);
    case "grid_array": return L.gridArray(spec, n("r"), n("c"), pal);
    case "ten_frame": return L.tenFrame(spec, n("n"), pal);
    case "bundle_group": return L.bundleGroup(spec, n("n"), pal);
    case "place_value_mat": return L.placeValueMat(spec, n("n"), pal);
    case "number_line": return L.numberLine(n("min"), n("max"), args.marks as number[], pal);
    case "bar_model": return L.barModel(args.parts as number[], pal);
    case "cross_out": return L.crossOut(spec, n("total"), n("marked"), pal);
    case "scatter": return L.scatter(spec, n("n"), pal, seed);
    case "two_groups": return L.twoGroups(spec, n("a"), n("b"), pal, seed);
  }
  throw new Error(`unknown layout ${layout}`);
}

export function renderCase(c: Case): string {
  if (c.fn === "avatar") return avatarSvg(personaLook(c.persona as string).look, c.expression, c.mouth);
  if (c.fn === "seat_row") {
    return seatRow(
      (c.children ?? []).map((k) => ({ look: personaLook(k.persona).look, expression: k.expression, speaking: k.speaking })),
    );
  }
  return renderLayout(c.fn, c.item, c.args ?? {}, c.palette ?? "default", c.seed ?? 0).svg;
}
