// On-device diagnosis. Lookups and counting only: every wrong answer, rule and threshold comes
// from generated/answer_keys.json, which the Python engine writes. No bug arithmetic lives here.
import rawKeys from "../generated/answer_keys.json";

export interface ItemKey {
  n: number;
  type: string;
  a: number; // operands, for showing a class's own example (b is 0 for a dictation item)
  b: number;
  correct: number;
  probes: string[];
  wrong: Record<string, string[]>;
  untracked: Record<string, string>;
}
interface AnswerKeys {
  error_order: string[];
  rules: {
    min_hits: number;
    min_prevalence: { numerator: number; denominator: number };
    min_children_checked: number;
    tracked: string[];
  };
  forms: Record<string, { label: string; items: ItemKey[] }>;
  content_hash: string;
}

export const keys = rawKeys as unknown as AnswerKeys;

export type Reading = number | "blank" | "unreadable";
export type MarkKind = "correct" | "error" | "other" | "blank" | "unreadable";

export interface AnswerMark {
  kind: MarkKind;
  codes: string[];
  untracked: string | null;
}
export interface ChildDiagnosis {
  marks: AnswerMark[];
  shows: string[];
  anchor_wrong: boolean;
  other_count: number;
  blank_count: number;
  unreadable_count: number;
  untracked: Record<string, number>;
}
export interface ClassProfile {
  children_checked: number;
  counts: Record<string, number>;
  prevalence: Record<string, number>;
  eligible: string[];
  track: string | null;
  anchor_wrong_count: number;
  untracked: Record<string, number>;
}

const MAX_DIGITS = 9;
const DEVANAGARI_ZERO = 0x0966;
const TAMIL_ZERO = 0x0be6;

/** Raw box text -> number, "blank" or "unreadable". Mirrors engine/normalize.py. */
export function normalizeAnswer(raw: string | null): Reading {
  if (raw === null) return "blank";
  let text = "";
  for (const ch of raw.replace(/\s+/g, "")) {
    const cp = ch.codePointAt(0) as number;
    if (cp >= DEVANAGARI_ZERO && cp <= DEVANAGARI_ZERO + 9) text += String(cp - DEVANAGARI_ZERO);
    else if (cp >= TAMIL_ZERO && cp <= TAMIL_ZERO + 9) text += String(cp - TAMIL_ZERO);
    else text += ch;
  }
  if (text === "") return "blank";
  if (!/^[0-9]+$/.test(text) || text.length > MAX_DIGITS) return "unreadable";
  return Number(text);
}

export function classify(item: ItemKey, reading: Reading): AnswerMark {
  if (reading === "blank") return { kind: "blank", codes: [], untracked: null };
  if (reading === "unreadable") return { kind: "unreadable", codes: [], untracked: null };
  if (reading === item.correct) return { kind: "correct", codes: [], untracked: null };
  const codes = item.wrong[String(reading)];
  if (codes) return { kind: "error", codes: [...codes].sort(), untracked: null };
  return { kind: "other", codes: [], untracked: item.untracked[String(reading)] ?? null };
}

function bump(tally: Record<string, number>, key: string, by = 1): void {
  tally[key] = (tally[key] ?? 0) + by;
}

function sortedTally(tally: Record<string, number>): Record<string, number> {
  return Object.fromEntries(Object.entries(tally).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
}

/** Apply the 2-item rule to one child's readings (in item order). */
export function diagnoseChild(formKey: string, readings: Reading[]): ChildDiagnosis {
  const form = keys.forms[formKey];
  if (!form) throw new Error(`unknown form ${formKey}`);
  if (readings.length !== form.items.length) {
    throw new Error(`expected ${form.items.length} answers, got ${readings.length}`);
  }
  const marks = form.items.map((item, i) => classify(item, readings[i] as Reading));
  const hits: Record<string, number> = {};
  for (const m of marks) if (m.kind === "error") for (const c of m.codes) bump(hits, c);
  const shows = Object.entries(hits)
    .filter(([, n]) => n >= keys.rules.min_hits)
    .map(([code]) => code)
    .sort();
  const untracked: Record<string, number> = {};
  for (const m of marks) if (m.untracked) bump(untracked, m.untracked);
  return {
    marks,
    shows,
    anchor_wrong: form.items.some(
      (item, i) =>
        item.type === "sub_anchor" &&
        ((marks[i] as AnswerMark).kind === "other" || (marks[i] as AnswerMark).kind === "error"),
    ),
    other_count: marks.filter((m) => m.kind === "other").length,
    blank_count: marks.filter((m) => m.kind === "blank").length,
    unreadable_count: marks.filter((m) => m.kind === "unreadable").length,
    untracked: sortedTally(untracked),
  };
}

/** Class counts, prevalence, eligible errors and the chosen track. Prevalence is a fraction. */
export function classProfile(children: ChildDiagnosis[]): ClassProfile {
  const checked = children.length;
  const order = keys.error_order;
  const counts: Record<string, number> = {};
  const prevalence: Record<string, number> = {};
  for (const code of order) {
    counts[code] = children.filter((c) => c.shows.includes(code)).length;
    prevalence[code] = checked ? (counts[code] as number) / checked : 0;
  }
  const { numerator, denominator } = keys.rules.min_prevalence;
  const eligible = order.filter(
    (code) =>
      checked >= keys.rules.min_children_checked &&
      (counts[code] as number) * denominator >= checked * numerator,
  );
  const candidates = eligible.filter((code) => keys.rules.tracked.includes(code));
  let track: string | null = null;
  if (candidates.includes("PV-HEARD")) track = "PV-HEARD";
  else {
    for (const code of candidates) {
      if (track === null || (counts[code] as number) > (counts[track] as number)) track = code;
    }
  }
  const untracked: Record<string, number> = {};
  for (const c of children) for (const [k, n] of Object.entries(c.untracked)) bump(untracked, k, n);
  return {
    children_checked: checked,
    counts,
    prevalence,
    eligible,
    track,
    anchor_wrong_count: children.filter((c) => c.anchor_wrong).length,
    untracked: sortedTally(untracked),
  };
}
