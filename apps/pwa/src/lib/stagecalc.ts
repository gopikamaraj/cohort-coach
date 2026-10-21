// Stage of breakdown, on the phone. Lookups and counting only: every signature answer and rule
// constant comes from generated/answer_keys.json, which engine/stages.py writes. A parity test
// runs this against tests/fixtures/stage_cases.json (made by the Python engine). The reads never
// leave the phone; only the class counts are kept. A stage is always "most likely".
import rawKeys from "../generated/answer_keys.json";
import { keys, type Reading } from "./diagnosis";

interface StageRules {
  min_hits: number;
  no_method_items_7_10: number;
  anchor: number;
  add_items: number[];
  sub_items: number[];
  stage_of: Record<string, string>;
  pv_reverse: { with_out_rev: string; otherwise: string };
}
interface StageKeys {
  rules: { stages: StageRules };
  forms: Record<string, { items: { n: number; correct: number; signatures: Record<string, number[]> }[] }>;
}
const stageKeys = rawKeys as unknown as StageKeys;
const rules = stageKeys.rules.stages;
void keys;

export interface Tags {
  missed?: boolean;
  unreadable?: number;
  two_answers?: number;
}
export interface StageResult {
  signatures: string[];
  signature_stages: [string, string][];
  stages: string[];
  not_attempted: boolean;
  anchor_wrong: boolean;
  no_method_possible: boolean;
  no_method_confirmed: boolean;
  missed_teaching: boolean;
}
export interface StageCounts {
  checked: number;
  missed_teaching: number;
  not_attempted: number;
  by_signature: { code: string; stage: string; n: number }[];
  by_stage: { stage: string; n: number }[];
}

export function classifyChild(formKey: string, readings: Reading[], tags: Tags = {}): StageResult {
  const form = stageKeys.forms[formKey];
  if (!form || readings.length !== form.items.length) throw new Error("expected ten answers on a known form");
  const hits = new Map<string, number>();
  const unmatched = new Map<number, boolean>();
  let blanks = 0;
  let anchorWrong = false;
  form.items.forEach((item, i) => {
    const reading = readings[i];
    if (reading === "blank" || reading === "unreadable" || reading === undefined) {
      if (reading === "blank" && rules.sub_items.includes(item.n)) blanks += 1;
      return;
    }
    if (item.n === rules.anchor) {
      anchorWrong = reading !== item.correct;
      return;
    }
    if (reading === item.correct) return;
    const matched = Object.entries(item.signatures)
      .filter(([, answers]) => answers.includes(reading))
      .map(([code]) => code);
    for (const code of matched) hits.set(code, (hits.get(code) ?? 0) + 1);
    unmatched.set(item.n, matched.length === 0);
  });
  const found = new Set([...hits].filter(([, n]) => n >= rules.min_hits).map(([code]) => code));
  const wrong710 = rules.sub_items.filter((n) => unmatched.get(n)).length;
  if (wrong710 >= rules.no_method_items_7_10 || rules.add_items.every((n) => unmatched.get(n))) found.add("NO-METHOD");
  if ((tags.unreadable ?? 0) + (tags.two_answers ?? 0) >= rules.min_hits) found.add("OUT-REC");
  const pairs: [string, string][] = [...found].map((code) => [
    code,
    code === "PV-REVERSE" ? (found.has("OUT-REV") ? rules.pv_reverse.with_out_rev : rules.pv_reverse.otherwise) : (rules.stage_of[code] as string),
  ]);
  pairs.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : 1));
  const possible = found.has("NO-METHOD");
  return {
    signatures: [...found].sort(),
    signature_stages: pairs,
    stages: [...new Set(pairs.map(([, s]) => s))].sort(),
    not_attempted: blanks >= rules.no_method_items_7_10,
    anchor_wrong: anchorWrong,
    no_method_possible: possible,
    no_method_confirmed: possible && Boolean(tags.missed),
    missed_teaching: Boolean(tags.missed),
  };
}

/** Counts per (signature, stage) for the class. Children tagged "missed the teaching" are counted
 *  on their own line and left out of the stage counts, so they do not inflate Core. */
export function classCounts(results: StageResult[]): StageCounts {
  const bySig = new Map<string, number>();
  const byStage = new Map<string, number>();
  for (const r of results) {
    if (r.missed_teaching) continue;
    for (const [code, stage] of r.signature_stages) bySig.set(`${code}|${stage}`, (bySig.get(`${code}|${stage}`) ?? 0) + 1);
    for (const stage of r.stages) byStage.set(stage, (byStage.get(stage) ?? 0) + 1);
  }
  return {
    checked: results.length,
    missed_teaching: results.filter((r) => r.missed_teaching).length,
    not_attempted: results.filter((r) => r.not_attempted).length,
    by_signature: [...bySig]
      .map(([k, n]) => ({ code: k.split("|")[0] as string, stage: k.split("|")[1] as string, n }))
      .sort((a, b) => b.n - a.n || (a.code < b.code ? -1 : 1)),
    by_stage: [...byStage].map(([stage, n]) => ({ stage, n })).sort((a, b) => b.n - a.n || (a.stage < b.stage ? -1 : 1)),
  };
}
