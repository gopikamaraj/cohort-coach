// The results page's tables, worked out on the phone from the answers kept here: the answer map (roll
// by question), the "Why an error is flagged" matrix with this class's counts, and the per-error
// numbers behind "What each error means". Nothing is decided here: every cell is read from the
// engine's answer key through diagnoseChild, and the counts are counts (never percentages).
import { isEmptyRow, readRow } from "./check";
import { diagnoseChild, formOf, keys, type ItemKey, type MarkKind, type Reading } from "./diagnosis";

/** Two letters for each error, for the answer map (shown with a colour and a pattern too). */
export const SHORT: Record<string, string> = {
  "PV-HEARD": "PH",
  "PV-REVERSE": "PR",
  "ADD-NOCARRY": "AC",
  "SUB-SFL": "SF",
  "SUB-NODEC": "SN",
};

export interface MapItem {
  n: number;
  type: string;
  question: string; // "703 − 468", "346" for a dictation item (the number said aloud)
  extra: boolean; // an adaptive item: helps find errors, never counts in before and after
  correct: number;
}

export interface MapCell {
  n: number; // the question's number
  kind: MarkKind;
  codes: string[]; // every error this wrong answer counts for (usually one)
  code: string | null; // the one shown in the cell
  confirmed: boolean; // the child shows this error (on enough questions), not just once
  given: Reading;
  correct: number;
  untracked: string | null;
}

export interface MapRoll {
  roll: number; // 1-based, as on the Enter check page
  cells: MapCell[];
  wrong: number; // how many questions she got wrong
  shows: string[];
}

export interface LegendEntry {
  code: string;
  confirmed: number; // children who show it
  possible: number; // children with one matching answer but not enough to show it
  cells: number;
}

export interface AnswerMap {
  formKey: string;
  items: MapItem[];
  rolls: MapRoll[];
  wrongByItem: number[]; // children who got each question wrong (a blank or unreadable box is not counted)
  legend: LegendEntry[];
  absent: number[]; // roll numbers marked absent
  notEntered: number; // rolls with nothing typed that are not marked absent
}

export function questionText(item: Pick<ItemKey, "type" | "a" | "b">): string {
  if (item.type === "dictation") return String(item.a);
  if (item.type === "add_carry") return `${item.a} + ${item.b}`;
  return `${item.a} − ${item.b}`;
}

/** Roll by question. `absent` and `approved` are 0-based roll positions, as the check keeps them. */
export function buildAnswerMap(formKey: string, rows: string[][], absent: number[] = [], approved?: number[]): AnswerMap | null {
  const form = formOf(formKey);
  if (!form) return null;
  const order = keys.error_order;
  const absentSet = new Set(absent);
  const okRoll = (i: number) => (approved && approved.length > 0 ? approved.includes(i) : true);
  const items: MapItem[] = form.items.map((it) => ({
    n: it.n,
    type: it.type,
    question: questionText(it),
    extra: it.anchor === false,
    correct: it.correct,
  }));
  const rolls: MapRoll[] = [];
  const wrongByItem = form.items.map(() => 0);
  const confirmedBy = new Map<string, number>();
  const possibleBy = new Map<string, number>();
  const cellsBy = new Map<string, number>();
  let notEntered = 0;
  rows.forEach((row, i) => {
    if (absentSet.has(i)) return;
    if (isEmptyRow(row)) {
      notEntered += 1;
      return;
    }
    if (!okRoll(i)) return;
    const readings = readRow(row);
    const d = diagnoseChild(formKey, readings);
    const cells: MapCell[] = d.marks.map((m, q) => {
      const item = form.items[q] as ItemKey;
      const shown = m.codes.filter((c) => d.shows.includes(c));
      const code = m.kind === "error" ? ([...shown, ...m.codes].sort((a, b) => order.indexOf(a) - order.indexOf(b))[0] ?? null) : null;
      return {
        n: item.n,
        kind: m.kind,
        codes: m.codes,
        code,
        confirmed: shown.length > 0,
        given: readings[q] as Reading,
        correct: item.correct,
        untracked: m.untracked,
      };
    });
    cells.forEach((c, q) => {
      if (c.kind === "error" || c.kind === "other") wrongByItem[q] = (wrongByItem[q] as number) + 1;
    });
    const seen = new Set<string>();
    for (const c of cells) {
      for (const code of c.codes) {
        cellsBy.set(code, (cellsBy.get(code) ?? 0) + 1);
        seen.add(code);
      }
    }
    for (const code of seen) {
      const map = d.shows.includes(code) ? confirmedBy : possibleBy;
      map.set(code, (map.get(code) ?? 0) + 1);
    }
    rolls.push({ roll: i + 1, cells, wrong: cells.filter((c) => c.kind === "error" || c.kind === "other").length, shows: d.shows });
  });
  const legend = order
    .filter((code) => (cellsBy.get(code) ?? 0) > 0)
    .map((code) => ({ code, confirmed: confirmedBy.get(code) ?? 0, possible: possibleBy.get(code) ?? 0, cells: cellsBy.get(code) ?? 0 }));
  return { formKey, items, rolls, wrongByItem, legend, absent: absent.map((i) => i + 1).sort((a, b) => a - b), notEntered };
}

export type SortBy = "roll" | "errors";

export function sortRolls(rolls: MapRoll[], by: SortBy): MapRoll[] {
  const copy = [...rolls];
  if (by === "errors") copy.sort((a, b) => b.wrong - a.wrong || a.roll - b.roll);
  else copy.sort((a, b) => a.roll - b.roll);
  return copy;
}

/** Which items check each error, read from the answer key's own probes (the same data the paper
 *  page's "Which items check each error" matrix shows). */
export function coverageFromKey(formKey: string): Record<string, number[]> {
  const form = formOf(formKey);
  const out: Record<string, number[]> = {};
  for (const code of keys.error_order) out[code] = [];
  for (const it of form?.items ?? []) for (const code of it.probes) (out[code] ??= []).push(it.n);
  return out;
}

export interface ClassCoverageRow {
  code: string;
  items: number[];
  confirmed: number;
  possible: number;
  assessed: boolean;
}

/** One row for every error the paper checks (also those found in 0 children), with the class counts. */
export function classCoverage(map: AnswerMap): ClassCoverageRow[] {
  const cov = coverageFromKey(map.formKey);
  return keys.error_order.map((code) => {
    const leg = map.legend.find((l) => l.code === code);
    const items = cov[code] ?? [];
    return { code, items, confirmed: leg?.confirmed ?? 0, possible: leg?.possible ?? 0, assessed: items.length > 0 };
  });
}

export interface InThisClass {
  code: string;
  children: number; // confirmed
  possible: number;
  questions: number[]; // question numbers where the error appeared
  common: { answer: number; n: number } | null; // the wrong answer most children wrote for this error
  example: { n: number; question: string; wrote: number; correct: number } | null;
}

/** What one error looks like in this class: its own question and its own children's answers. */
export function inThisClass(map: AnswerMap, code: string): InThisClass {
  const leg = map.legend.find((l) => l.code === code);
  const byItem = new Map<number, Map<number, number>>(); // question -> answer -> children
  for (const r of map.rolls) {
    for (const c of r.cells) {
      if (c.kind !== "error" || !c.codes.includes(code) || typeof c.given !== "number") continue;
      const m = byItem.get(c.n) ?? new Map<number, number>();
      m.set(c.given, (m.get(c.given) ?? 0) + 1);
      byItem.set(c.n, m);
    }
  }
  const questions = [...byItem.keys()].sort((a, b) => a - b);
  let best: { n: number; answer: number; total: number } | null = null;
  const overall = new Map<number, number>();
  for (const [n, answers] of byItem) {
    const total = [...answers.values()].reduce((s, v) => s + v, 0);
    const top = [...answers.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0] as [number, number];
    for (const [a, v] of answers) overall.set(a, (overall.get(a) ?? 0) + v);
    if (!best || total > best.total || (total === best.total && n < best.n)) best = { n, answer: top[0], total };
  }
  const topOverall = [...overall.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
  const item = best ? map.items.find((i) => i.n === (best as { n: number }).n) : undefined;
  return {
    code,
    children: leg?.confirmed ?? 0,
    possible: leg?.possible ?? 0,
    questions,
    common: topOverall ? { answer: topOverall[0], n: topOverall[1] } : null,
    example: best && item ? { n: item.n, question: item.question, wrote: best.answer, correct: item.correct } : null,
  };
}
