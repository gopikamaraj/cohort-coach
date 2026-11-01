// Layout engines, step for step the same as services/api/sprites/layouts.py (integer maths only).
import type { ItemSpec, Palette } from "./data";
import { compileItem, validateSvg } from "./grammar";
import { Rng } from "./rng";

export const W = 240;
export const H = 160;
export const PAD = 8;
export const MAX_COUNT = 100;

export interface Report {
  item_id: string;
  count_drawn: number;
  layout?: string;
  [key: string]: unknown;
}
export interface Scene {
  svg: string;
  report: Report;
}
export class LayoutError extends Error {}

const fdiv = (a: number, b: number): number => Math.floor(a / b);
const cdiv = (a: number, b: number): number => -Math.floor(-a / b);
const isqrt = (n: number): number => Math.floor(Math.sqrt(n));

const use = (id: string, x: number, y: number, size: number, cls = "u"): string =>
  `<use href="#i-${id}" x="${x}" y="${y}" width="${size}" height="${size}" class="${cls}"/>`;

function line(x1: number, y1: number, x2: number, y2: number, stroke: string, sw = 1, cls = ""): string {
  const c = cls ? ` class="${cls}"` : "";
  return `<line${c} x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" fill="none" stroke="${stroke}" stroke-width="${sw}"/>`;
}

function rect(x: number, y: number, w: number, h: number, fill: string, stroke: string, sw: number, cls = ""): string {
  const c = cls ? ` class="${cls}"` : "";
  return `<rect${c} x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
}

export function assemble(layout: string, specs: ItemSpec[], pal: Palette, body: string, report: Report): Scene {
  const defs = specs.map((s) => compileItem(s, pal)).join("");
  const head =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" role="img" ` +
    `data-alt="sprite.scene.${layout}" data-layout="${layout}" ` +
    `data-item="${report.item_id}" data-count="${report.count_drawn}">`;
  const bg = `<rect x="0" y="0" width="${W}" height="${H}" fill="${pal.mat}"/>`;
  const svg = `${head}<defs>${defs}</defs>${bg}${body}</svg>`;
  const bad = validateSvg(svg);
  if (bad.length) throw new LayoutError(`${layout} produced SVG outside the grammar: ${bad}`);
  return { svg, report: { ...report, layout } };
}

function checkCount(n: number, lo = 0, hi = MAX_COUNT): void {
  if (!Number.isInteger(n) || n < lo || n > hi) throw new LayoutError(`count must be an integer from ${lo} to ${hi}`);
}

export function row(spec: ItemSpec, n: number, pal: Palette): Scene {
  checkCount(n);
  const perRow = Math.min(Math.max(n, 1), 20);
  const rows = n ? cdiv(n, perRow) : 0;
  const cell = Math.min(24, fdiv(W - 2 * PAD, perRow), fdiv(H - 2 * PAD, Math.max(rows, 1)));
  const x0 = fdiv(W - perRow * cell, 2);
  const y0 = fdiv(H - rows * cell, 2);
  let body = "";
  for (let i = 0; i < n; i++) body += use(spec.id, x0 + (i % perRow) * cell, y0 + fdiv(i, perRow) * cell, cell);
  return assemble("row", [spec], pal, body, { item_id: spec.id, count_drawn: n });
}

export function gridArray(spec: ItemSpec, r: number, c: number, pal: Palette): Scene {
  checkCount(r, 1, 20);
  checkCount(c, 1, 20);
  const cell = Math.min(24, fdiv(W - 2 * PAD, c), fdiv(H - 2 * PAD, r));
  const x0 = fdiv(W - c * cell, 2);
  const y0 = fdiv(H - r * cell, 2);
  let body = "";
  for (let i = 0; i < r; i++) for (let j = 0; j < c; j++) body += use(spec.id, x0 + j * cell, y0 + i * cell, cell);
  return assemble("grid_array", [spec], pal, body, { item_id: spec.id, count_drawn: r * c, rows: r, cols: c });
}

export function tenFrame(spec: ItemSpec, n: number, pal: Palette): Scene {
  checkCount(n, 0, 20);
  const ink = pal.ink as string;
  const frames = n <= 10 ? 1 : 2;
  const fx = fdiv(W - 100, 2);
  const top = fdiv(H - frames * 40 - (frames - 1) * 16, 2);
  let body = "";
  for (let k = 0; k < frames; k++) {
    const fy = top + k * 56;
    body += `<g class="frame">${rect(fx, fy, 100, 40, pal.mat as string, ink, 2)}`;
    for (const i of [1, 2, 3, 4]) body += line(fx + 20 * i, fy, fx + 20 * i, fy + 40, ink);
    body += line(fx, fy + 20, fx + 100, fy + 20, ink) + "</g>";
  }
  for (let i = 0; i < n; i++) {
    const k = fdiv(i, 10);
    const j = i % 10;
    const r = fdiv(j, 5);
    const c = j % 5;
    body += use(spec.id, fx + c * 20 + 1, top + k * 56 + r * 20 + 1, 18);
  }
  return assemble("ten_frame", [spec], pal, body, { item_id: spec.id, count_drawn: n, frames });
}

function bundle(id: string, x: number, y: number, cell: number, ink: string): string {
  let units = "";
  for (let i = 0; i < 10; i++) units += use(id, x + (i % 5) * cell, y + fdiv(i, 5) * cell, cell);
  const band = rect(x - 1, y - 1, 5 * cell + 2, 2 * cell + 2, "none", ink, 1, "band");
  return `<g class="bundle">${units}${band}</g>`;
}

export function bundleGroup(spec: ItemSpec, n: number, pal: Palette): Scene {
  checkCount(n);
  const t = fdiv(n, 10);
  const o = n % 10;
  const rows = t ? cdiv(t, 5) : 0;
  const total = rows * 18 + Math.max(rows - 1, 0) * 4 + (rows && o ? 12 : 0) + (o ? 16 : 0);
  const y = fdiv(H - total, 2);
  let body = "";
  for (let r = 0; r < rows; r++) {
    const k = Math.min(5, t - r * 5);
    const width = k * 40 + (k - 1) * 4;
    const x0 = fdiv(W - width, 2);
    for (let j = 0; j < k; j++) body += bundle(spec.id, x0 + j * 44, y + r * 22 + 1, 8, pal.ink as string);
  }
  if (o) {
    const ly = y + (rows ? rows * 22 - 4 + 12 : 0);
    const lx = fdiv(W - o * 16, 2);
    for (let i = 0; i < o; i++) body += use(spec.id, lx + i * 16, ly, 16);
  }
  return assemble("bundle_group", [spec], pal, body, { item_id: spec.id, count_drawn: n, bundles: t, loose: o });
}

export function placeValueMat(spec: ItemSpec, n: number, pal: Palette): Scene {
  checkCount(n, 0, 99);
  const ink = pal.ink as string;
  const mat = pal.mat as string;
  const t = fdiv(n, 10);
  const o = n % 10;
  let body = rect(8, 8, 112, 144, mat, ink, 2, "frame") + rect(124, 8, 108, 144, mat, ink, 2, "frame");
  body += rect(58, 14, 14, 8, "none", ink, 1, "tick") + `<circle class="tick" cx="178" cy="18" r="4" fill="${ink}"/>`;
  for (let i = 0; i < t; i++) body += bundle(spec.id, 14 + (i % 3) * 36, 32 + fdiv(i, 3) * 22, 6, ink);
  for (let i = 0; i < o; i++) body += use(spec.id, 134 + (i % 5) * 18, 40 + fdiv(i, 5) * 22, 16);
  return assemble("place_value_mat", [spec], pal, body, { item_id: spec.id, count_drawn: n, tens: t, ones: o });
}

export function numberLine(lo: number, hi: number, marks: number[], pal: Palette): Scene {
  if (!(hi - lo >= 1 && hi - lo <= MAX_COUNT)) throw new LayoutError("the number line spans 1 to 100 steps");
  if (marks.some((m) => m < lo || m > hi)) throw new LayoutError("a mark lies outside the line");
  const ink = pal.ink as string;
  const x = (v: number): number => 12 + fdiv((v - lo) * 216, hi - lo);
  let body = line(12, 90, 228, 90, ink, 2);
  const kinds: [number, (v: number) => boolean][] = [
    [6, (v) => v % 5 !== 0],
    [10, (v) => v % 5 === 0 && v % 10 !== 0],
    [14, (v) => v % 10 === 0],
  ];
  for (const [h, pick] of kinds) {
    let d = "";
    for (let v = lo; v <= hi; v++) if (pick(v)) d += `M${x(v)} 90v${h}`;
    if (d) body += `<path class="tick" d="${d}" fill="none" stroke="${ink}" stroke-width="1"/>`;
  }
  const sorted = [...marks].sort((a, b) => a - b);
  for (const m of sorted) {
    const p = `fill="${pal.accent}" stroke="${ink}" stroke-width="1"`;
    body += `<circle class="u mk" cx="${x(m)}" cy="78" r="5" ${p}/>`;
  }
  return assemble("number_line", [], pal, body, {
    item_id: "number_line", count_drawn: marks.length, min: lo, max: hi, marks: sorted, ticks: hi - lo + 1,
  });
}

export function barModel(parts: number[], pal: Palette): Scene {
  const total = parts.reduce((a, b) => a + b, 0);
  if (!parts.length || parts.some((p) => !Number.isInteger(p) || p < 1) || total > 200) {
    throw new LayoutError("a bar model needs 1 or more positive parts totalling at most 200");
  }
  const ink = pal.ink as string;
  let body = "";
  let cum = 0;
  parts.forEach((p, i) => {
    const x1 = 12 + fdiv(cum * 216, total);
    const x2 = 12 + fdiv((cum + p) * 216, total);
    const fill = (i % 2 === 0 ? pal.item_a : pal.item_b) as string;
    body += rect(x1, 60, x2 - x1, 40, fill, ink, 1, "u");
    if (i % 2 === 1) for (let x = x1 + 4; x < x2 - 2; x += 6) body += line(x, 60, x, 100, ink, 1);
    cum += p;
  });
  body += `<polyline fill="none" stroke="${ink}" stroke-width="1" points="12,52 12,46 228,46 228,52"/>`;
  return assemble("bar_model", [], pal, body, { item_id: "bar_model", count_drawn: parts.length, parts: [...parts], total });
}

export function crossOut(spec: ItemSpec, total: number, marked: number, pal: Palette): Scene {
  checkCount(total, 1, MAX_COUNT);
  checkCount(marked, 0, total);
  const cols = isqrt(total - 1) + 1;
  const rows = cdiv(total, cols);
  const cell = Math.min(24, fdiv(W - 2 * PAD, cols), fdiv(H - 2 * PAD, rows));
  const x0 = fdiv(W - cols * cell, 2);
  const y0 = fdiv(H - rows * cell, 2);
  const accent = pal.accent as string;
  let body = "";
  for (let i = 0; i < total; i++) {
    const x = x0 + (i % cols) * cell;
    const y = y0 + fdiv(i, cols) * cell;
    if (i < marked) {
      body += use(spec.id, x, y, cell, "u x");
      body += `<g class="mk">${line(x, y, x + cell, y + cell, accent, 2)}${line(x + cell, y, x, y + cell, accent, 2)}</g>`;
    } else {
      body += use(spec.id, x, y, cell);
    }
  }
  return assemble("cross_out", [spec], pal, body, { item_id: spec.id, count_drawn: total, marked });
}

function place(n: number, ox: number, oy: number, aw: number, ah: number, rng: Rng): [number, number, number][] {
  if (n === 0) return [];
  let cell = 24;
  while (fdiv(aw, cell) * fdiv(ah, cell) < n) {
    cell -= 1;
    if (cell < 8) throw new LayoutError("too many items for the area");
  }
  const cols = fdiv(aw, cell);
  const idx = rng.shuffle(Array.from({ length: fdiv(aw, cell) * fdiv(ah, cell) }, (_, i) => i)).slice(0, n);
  return idx.map((k) => {
    const jx = rng.below(3);
    const jy = rng.below(3);
    return [ox + (k % cols) * cell + jx, oy + fdiv(k, cols) * cell + jy, cell - 2] as [number, number, number];
  });
}

export function scatter(spec: ItemSpec, n: number, pal: Palette, seed = 0): Scene {
  checkCount(n);
  const boxes = place(n, PAD, PAD, W - 2 * PAD, H - 2 * PAD, new Rng(seed));
  const body = boxes.map(([x, y, s]) => use(spec.id, x, y, s)).join("");
  return assemble("scatter", [spec], pal, body, { item_id: spec.id, count_drawn: n });
}

export function twoGroups(spec: ItemSpec, a: number, b: number, pal: Palette, seed = 0): Scene {
  checkCount(a);
  checkCount(b);
  const rng = new Rng(seed);
  const aw = fdiv(W - 2 * PAD - 8, 2);
  const ga = place(a, PAD, PAD, aw, H - 2 * PAD, rng).map(([x, y, s]) => use(spec.id, x, y, s)).join("");
  const bx = PAD + aw + 8;
  const gb = place(b, bx, PAD, aw, H - 2 * PAD, rng).map(([x, y, s]) => use(spec.id, x, y, s)).join("");
  const frame = rect(bx - 2, PAD - 2, aw + 4, H - 2 * PAD + 4, "none", pal.ink as string, 2, "frame");
  const body = `<g class="ga">${ga}</g><g class="gb">${frame}${gb}</g>`;
  return assemble("two_groups", [spec], pal, body, { item_id: spec.id, count_drawn: a + b, groups: [a, b] });
}
