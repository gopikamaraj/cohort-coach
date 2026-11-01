// A cohort just for this teacher's class. The record is kept on this phone first (so it works offline
// and after a reload) and sent to the server when online: counts only, never a child or an answer.
// The server makes one per check, so a retry or a second tap returns the same cohort.
import { ccall, CohortError } from "./cohort";

export interface ClassCohort {
  id: string; // "local-..." until the server has it
  checkId: string;
  name: string;
  errors: string[];
  counts: Record<string, number>;
  childrenChecked: number;
  simulated: boolean;
  synced: boolean;
}

const KEY = "cc.classCohorts";

export function readAll(): ClassCohort[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "[]") as unknown;
    return Array.isArray(v) ? (v as ClassCohort[]) : [];
  } catch {
    return [];
  }
}

function writeAll(rows: ClassCohort[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(rows));
  } catch {
    /* private window: it lives in memory for this visit only */
  }
}

/** The cohort made from this check, if there is one. */
export function forCheck(checkId: string): ClassCohort | null {
  return readAll().find((c) => c.checkId === checkId) ?? null;
}

export interface Input {
  checkId: string;
  name: string;
  errors: string[];
  counts: Record<string, number>;
  childrenChecked: number;
  simulated: boolean;
  language: string;
}

interface Served {
  id: string;
  name: string;
  errors: string[];
  counts: Record<string, number>;
  children_checked: number;
  simulated: boolean;
}

function localId(): string {
  const b = new Uint8Array(6);
  crypto.getRandomValues(b);
  return "local-" + Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
}

/** Counts of the chosen errors only: nothing else of the class leaves the phone. */
export function pickCounts(errors: string[], counts: Record<string, number>): Record<string, number> {
  return Object.fromEntries(errors.map((e) => [e, counts[e] ?? 0]));
}

async function send(c: ClassCohort, language: string, fetchFn?: typeof fetch): Promise<Served> {
  return ccall<Served>(
    "/class-only",
    "teacher",
    { method: "POST", body: { check_id: c.checkId, name: c.name, errors: c.errors, counts: pickCounts(c.errors, c.counts), children_checked: c.childrenChecked, simulated: c.simulated, language } },
    fetchFn,
  );
}

/** Make it: kept here at once, sent now when online. A refused name is thrown (so she can change it);
 *  a network failure keeps it here to send later. */
export async function create(input: Input, online: boolean, fetchFn?: typeof fetch): Promise<ClassCohort> {
  const have = forCheck(input.checkId);
  if (have) return have;
  const row: ClassCohort = {
    id: localId(),
    checkId: input.checkId,
    name: input.name.trim(),
    errors: input.errors,
    counts: pickCounts(input.errors, input.counts),
    childrenChecked: input.childrenChecked,
    simulated: input.simulated,
    synced: false,
  };
  if (online) {
    try {
      const got = await send(row, input.language, fetchFn);
      row.id = got.id;
      row.synced = true;
    } catch (e) {
      if (e instanceof CohortError && e.status > 0) throw e; // refused: she can change the name
    }
  }
  writeAll([...readAll(), row]);
  return row;
}

/** Send the ones made offline. Quiet when it fails: it tries again next time. */
export async function syncPending(language: string, fetchFn?: typeof fetch): Promise<void> {
  const rows = readAll();
  let changed = false;
  for (const r of rows) {
    if (r.synced) continue;
    try {
      const got = await send(r, language, fetchFn);
      r.id = got.id;
      r.synced = true;
      changed = true;
    } catch {
      /* still offline, or refused: leave it here */
    }
  }
  if (changed) writeAll(rows);
}

export interface CoachRow {
  id: string;
  name: string;
  scope: string;
  errors: string[];
  counts: Record<string, number>;
  children_checked: number;
  classes: number;
  simulated: boolean;
}

export async function forCoach(fetchFn?: typeof fetch): Promise<CoachRow[]> {
  return ccall<CoachRow[]>("/class-only/coach", "coach", {}, fetchFn);
}
