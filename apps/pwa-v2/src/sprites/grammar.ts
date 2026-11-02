// The compiler for item specs, and a guard for rendered SVG. Mirrors services/api/sprites/grammar.py.
// The server is the authority on the grammar (it validates every spec and every scene); the guard
// here only refuses markup that must never reach the page.
import type { Gradient, ItemSpec, Palette, Part } from "./data";

export const SPEC_SHAPES: Record<string, string[]> = {
  circle: ["cx", "cy", "r"],
  ellipse: ["cx", "cy", "rx", "ry"],
  rect: ["x", "y", "width", "height", "rx"],
  line: ["x1", "y1", "x2", "y2"],
  polyline: ["points"],
  polygon: ["points"],
  path: ["d"],
};

const FORBIDDEN = /<\s*(script|foreignObject|image|text|tspan|title|desc|style|a|animate|animateTransform|set)[\s>/]/i;
const EVENT_ATTR = /\son[a-z]+\s*=/i;
const HREF = /\s(?:xlink:)?href\s*=\s*"([^"]*)"/gi;

/** Rule ids broken by this SVG; empty when it passes the guard. */
export function validateSvg(svg: string): string[] {
  const out: string[] = [];
  if (FORBIDDEN.test(svg)) out.push("forbidden_element");
  if (EVENT_ATTR.test(svg)) out.push("event_attribute");
  if (/\sstyle\s*=/i.test(svg)) out.push("style_attribute");
  for (const m of svg.matchAll(HREF)) if (!(m[1] ?? "").startsWith("#")) out.push("external_href");
  if (/xlink:/i.test(svg)) out.push("attribute_not_allowed:xlink");
  return [...new Set(out)].sort();
}

function paint(value: string, pal: Palette, scope: string): string {
  if (value === "none") return "none";
  if (value.startsWith("grad:")) return `url(#${scope}-${value.slice(5)})`;
  return pal[value] as string;
}

export function partMarkup(part: Part, pal: Palette, scope: string): string {
  const shape = String(part.shape);
  const attrs: string[] = [];
  for (const k of SPEC_SHAPES[shape] as string[]) if (k in part) attrs.push(`${k}="${part[k]}"`);
  attrs.push(`fill="${paint(String(part.fill ?? "none"), pal, scope)}"`);
  if ("stroke" in part) {
    attrs.push(`stroke="${paint(String(part.stroke), pal, scope)}"`);
    attrs.push(`stroke-width="${part.stroke_width ?? 1}"`);
  }
  if ("transform" in part) attrs.push(`transform="${part.transform}"`);
  return `<${shape} ${attrs.join(" ")}/>`;
}

export function gradientMarkup(g: Gradient, pal: Palette, scope: string): string {
  const keys = g.type === "radialGradient" ? ["cx", "cy", "r"] : ["x1", "y1", "x2", "y2"];
  const geo = keys.map((k) => `${k}="${g[k]}"`).join(" ");
  const stops = g.stops.map((s) => `<stop offset="${s.offset}%" stop-color="${pal[s.color]}"/>`).join("");
  return `<${g.type} id="${scope}-${g.id}" gradientUnits="userSpaceOnUse" ${geo}>${stops}</${g.type}>`;
}

/** The reusable definition of one item: a nested svg that scenes instance with `use`. */
export function compileItem(spec: ItemSpec, pal: Palette): string {
  const scope = `i-${spec.id}`;
  const vb = (spec.viewBox ?? [0, 0, 24, 24]).join(" ");
  let inner = (spec.defs ?? []).map((g) => gradientMarkup(g, pal, scope)).join("");
  if (inner) inner = `<defs>${inner}</defs>`;
  inner += spec.parts.map((p) => partMarkup(p, pal, scope)).join("");
  return `<svg id="${scope}" viewBox="${vb}">${inner}</svg>`;
}
