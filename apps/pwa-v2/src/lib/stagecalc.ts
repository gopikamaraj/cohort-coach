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
  concepts: Record<string, number[]>;
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
  missed?: boolean; // the whole sheet: every concept
  missed_concepts?: string[];
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
  missed_concepts: string[];
  excluded: string[];
}
export interface StageCounts {
  checked: number;
  missed_teaching: number;
  missed_by_concept: Record<string, number>;
  not_attempted: number;
  by_signature: { code: string; stage: string; n: number }[];
  by_stage: { stage: string; n: number }[];
}

/** The concepts the worksheet covers, with the items each rests on (from the engine's rules). */
export const CONCEPTS: Record<string, number[]> = rules.concepts;

export function classifyChild(formKey: string, readings: Reading[], tags: Tags = {}): StageResult {
  const form = stageKeys.forms[formKey];
  if (!form || readings.length !== form.items.length) throw new Error("expected ten answers on a known form");
  const missed = new Set(tags.missed ? Object.keys(CONCEPTS) : (tags.missed_concepts ?? []));
  for (const name of missed) if (!(name in CONCEPTS)) throw new Error(`unknown concept ${name}`);
  const hits = new Map<string, number>();
  const support = new Map<string, Set<number>>();
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
    for (const code of matched) {
      hits.set(code, (hits.get(code) ?? 0) + 1);
      support.set(code, (support.get(code) ?? new Set<number>()).add(item.n));
    }
    unmatched.set(item.n, matched.length === 0);
  });
  const found = new Set([...hits].filter(([, n]) => n >= rules.min_hits).map(([code]) => code));
  const wrong710 = rules.sub_items.filter((n) => unmatched.get(n)).length;
  if (wrong710 >= rules.no_method_items_7_10 || rules.add_items.every((n) => unmatched.get(n))) {
    found.add("NO-METHOD");
    support.set("NO-METHOD", new Set([...unmatched].filter(([, gone]) => gone).map(([n]) => n)));
  }
  if ((tags.unreadable ?? 0) + (tags.two_answers ?? 0) >= rules.min_hits) found.add("OUT-REC");
  const missedItems = new Set([...missed].flatMap((name) => CONCEPTS[name] as number[]));
  const allMissed = missed.size === Object.keys(CONCEPTS).length;
  const excluded = [...found].filter((code) => {
    const rests = support.get(code);
    return (rests !== undefined && rests.size > 0 && [...rests].every((n) => missedItems.has(n))) || (allMissed && code === "OUT-REC");
  });
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
    no_method_confirmed: possible && excluded.includes("NO-METHOD"),
    missed_teaching: missed.size > 0,
    missed_concepts: [...missed].sort(),
    excluded: excluded.sort(),
  };
}

/** Counts per (signature, stage) for the class. What a child missed the teaching on is counted on
 *  its own lines (once per concept) and left out of the stage counts, so it does not inflate Core;
 *  what she did not miss still counts. */
export function classCounts(results: StageResult[]): StageCounts {
  const bySig = new Map<string, number>();
  const byStage = new Map<string, number>();
  const byConcept: Record<string, number> = Object.fromEntries(Object.keys(CONCEPTS).map((name) => [name, 0]));
  for (const r of results) {
    for (const name of r.missed_concepts) byConcept[name] = (byConcept[name] ?? 0) + 1;
    const kept = r.signature_stages.filter(([code]) => !r.excluded.includes(code));
    for (const [code, stage] of kept) bySig.set(`${code}|${stage}`, (bySig.get(`${code}|${stage}`) ?? 0) + 1);
    for (const stage of new Set(kept.map(([, s]) => s))) byStage.set(stage, (byStage.get(stage) ?? 0) + 1);
  }
  return {
    checked: results.length,
    missed_teaching: results.filter((r) => r.missed_teaching).length,
    missed_by_concept: byConcept,
    not_attempted: results.filter((r) => r.not_attempted).length,
    by_signature: [...bySig]
      .map(([k, n]) => ({ code: k.split("|")[0] as string, stage: k.split("|")[1] as string, n }))
      .sort((a, b) => b.n - a.n || (a.code < b.code ? -1 : 1)),
    by_stage: [...byStage].map(([stage, n]) => ({ stage, n })).sort((a, b) => b.n - a.n || (a.stage < b.stage ? -1 : 1)),
  };
}
