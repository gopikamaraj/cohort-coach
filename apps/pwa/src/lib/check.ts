// From the raw boxes a teacher typed to the class result. Diagnosis itself is in diagnosis.ts;
// this file only reads her cells and fills the class-level profile.
import { classProfile, diagnoseChild, normalizeAnswer, type ChildDiagnosis, type Reading } from "./diagnosis";
import { db, type CohortDb, type ProfileRow } from "./db";
import { enqueueProfile } from "./sync";

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

export function profileRow(
  classId: string,
  term: number,
  formKey: string,
  rows: string[][],
  simulated: boolean,
): ProfileRow {
  const profile = classProfile(diagnoseAll(formKey, rows));
  return {
    id: `${classId}:${term}`,
    classId,
    term,
    formKey,
    childrenChecked: profile.children_checked,
    counts: profile.counts,
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
  term: number,
  formKey: string,
  rows: string[][],
  simulated: boolean,
  store: CohortDb = db,
): Promise<ProfileRow> {
  const row = profileRow(classId, term, formKey, rows, simulated);
  await store.profiles.put(row);
  await enqueueProfile(row, store);
  return row;
}
