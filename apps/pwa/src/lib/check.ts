// From the raw boxes a teacher typed to the class result. Diagnosis itself is in diagnosis.ts;
// this file only reads her cells and fills the class-level profile.
import { classProfile, diagnoseChild, formOf, normalizeAnswer, type ChildDiagnosis, type Reading } from "./diagnosis";
import { db, type CohortDb, type ProfileRow } from "./db";
import { fetchPaperKey } from "./paperKeys";
import { buildAnswerMap } from "./results";
import { enqueueProfile } from "./sync";
import type { StageCounts } from "./stagecalc";

export const BLANK = "_";
export const UNREADABLE = "?";

/** One typed cell -> a reading. "" (not entered) and "_" are blank; "?" is unreadable. */
export function readCell(cell: string): Reading {
  if (cell === "" || cell === BLANK) return "blank";
  if (cell === UNREADABLE) return "unreadable";
  return normalizeAnswer(cell);
}

export function readRow(row: string[]): Reading[] {
  return row.map(readCell);
}

/** Does the row hold any real answer (a digit)? Blank marks alone do not count: nothing would be lost. */
export function hasAnswers(row: string[]): boolean {
  return row.some((cell) => /\d/.test(cell));
}

/** A row with nothing typed in it yet (the empty row "Next child" opens). */
export function isEmptyRow(row: string[]): boolean {
  return row.every((cell) => cell === "");
}

export function enteredChildren(rows: string[][]): string[][] {
  return rows.filter((row) => !isEmptyRow(row));
}

export function diagnoseAll(formKey: string, rows: string[][]): ChildDiagnosis[] {
  return enteredChildren(rows).map((row) => diagnoseChild(formKey, readRow(row)));
}

/** Children per mistake who made it at least once: those who show it and those with one matching answer only. */
export function anyCounts(formKey: string, rows: string[][]): Record<string, number> {
  const map = buildAnswerMap(formKey, rows);
  const out: Record<string, number> = {};
  for (const r of map?.rolls ?? []) {
    for (const code of new Set(r.cells.flatMap((c) => c.codes))) out[code] = (out[code] ?? 0) + 1;
  }
  return out;
}

/** A paper's own answer key is kept on each phone, so a phone she signs in on has her checks (from the cloud) but not the
 *  keys of the papers they used, and the results and the answer map cannot be drawn. Fetch the missing keys. Returns
 *  how many came in. */
export async function fetchMissingPaperKeys(store: CohortDb = db): Promise<number> {
  let n = 0;
  for (const c of await store.checks.toArray()) {
    if (!c.formKey.startsWith("P-") || formOf(c.formKey)) continue;
    await fetchPaperKey(c.formKey, { role: "teacher", classId: c.classId }).catch(() => undefined);
    if (formOf(c.formKey)) n += 1;
  }
  return n;
}

/** Results saved before `anyCounts` existed get it from the check's answers (the cloud copy follows). */
export async function backfillAnyCounts(store: CohortDb = db): Promise<number> {
  let n = 0;
  for (const p of await store.profiles.toArray()) {
    if (p.anyCounts && Object.keys(p.anyCounts).length > 0) continue;
    const c = await store.checks.get(p.id);
    if (!c?.children?.length) continue;
    // a paper's own key is fetched on demand: without it the answers cannot be read
    if (!formOf(p.formKey)) await fetchPaperKey(p.formKey, { role: "teacher", classId: p.classId }).catch(() => null);
    if (!formOf(p.formKey)) continue;
    await store.profiles.update(p.id, { anyCounts: anyCounts(p.formKey, c.children) });
    n += 1;
  }
  return n;
}

export function profileRow(
  classId: string,
  seq: number,
  formKey: string,
  rows: string[][],
  simulated: boolean,
): ProfileRow {
  const profile = classProfile(diagnoseAll(formKey, rows));
  return {
    id: `${classId}:${seq}`,
    classId,
    term: seq,
    formKey,
    childrenChecked: profile.children_checked,
    counts: profile.counts,
    anyCounts: anyCounts(formKey, rows),
    eligible: profile.eligible,
    track: profile.track,
    anchorWrongCount: profile.anchor_wrong_count,
    untracked: profile.untracked,
    simulated,
    createdAt: Date.now(),
  };
}

/** Finish a check: diagnose on the phone, keep the class result, queue the counts to send. */
export async function finishCheck(
  classId: string,
  seq: number,
  formKey: string,
  rows: string[][],
  simulated: boolean,
  store: CohortDb = db,
  stages?: StageCounts | null,
): Promise<ProfileRow> {
  const row = { ...profileRow(classId, seq, formKey, rows, simulated), ...(stages ? { stages } : {}) };
  await store.profiles.put(row);
  await enqueueProfile(row, store);
  return row;
}
