// A cohort just for this teacher's class. The server holds it: the page reads it from there each time, so a
// cohort deleted on the server is gone here too. This phone keeps a copy only of one that could not be
// sent (made offline, or the network failed), until it goes through; then the copy is removed. Counts only,
// never a child or an answer. The server makes one per check, so a retry or a second tap returns the same cohort.
import { ccall, CohortError } from "./cohort";
import { getUser } from "./identity";

export interface ClassCohort {
  id: string; // "local-..." until the server has it
  checkId: string;
  name: string;
  errors: string[];
  counts: Record<string, number>;
  childrenChecked: number;
  simulated: boolean;
  synced: boolean;
  rule?: number; // 2 confirmed, 1 possible: the rule its counts were made under
}

const KEY = "cc.classCohorts";
// The server's list is the record. A copy of it is kept on the phone for this user (a cache, replaced at every online
// visit) so her cohort, its track and its modules still open with no signal.
const cacheKey = (): string => `cc.classCohorts.cache.${getUser()?.id ?? "-"}`;
function readCache(): ClassCohort[] {
  try {
    const v = JSON.parse(localStorage.getItem(cacheKey()) ?? "[]") as unknown;
    return Array.isArray(v) ? (v as ClassCohort[]) : [];
  } catch {
    return [];
  }
}
function writeCache(rows: ClassCohort[]): void {
  try {
    localStorage.setItem(cacheKey(), JSON.stringify(rows));
  } catch {
    /* private window */
  }
}
let served: ClassCohort[] | null = null; // read from the server this visit; until then (offline) the cached copy

/** Only the ones still waiting to be sent are kept on the phone; an older saved copy that was sent is ignored. */
function pending(): ClassCohort[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "[]") as unknown;
    return Array.isArray(v) ? (v as ClassCohort[]).filter((c) => !c.synced) : [];
  } catch {
    return [];
  }
}

function writePending(rows: ClassCohort[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(rows));
  } catch {
    /* private window: it lives in memory for this visit only */
  }
}

/** What is known now: the server's list (once read) and any waiting to be sent. */
export function readAll(): ClassCohort[] {
  const list = served ?? readCache();
  const wait = pending().filter((p) => !list.some((s) => keyOf(s) === keyOf(p)));
  return [...list, ...wait];
}

/** One cohort per mistake: a cohort is known by its check and the mistakes it works on. */
const keyOf = (c: { checkId: string; errors: string[] }): string => `${c.checkId}|${[...c.errors].sort().join(",")}`;

/** The first cohort made from this check, if there is one. */
export function forCheck(checkId: string): ClassCohort | null {
  return readAll().find((c) => c.checkId === checkId) ?? null;
}

/** Every cohort made from this check: one for each mistake she has made one for. */
export function allForCheck(checkId: string): ClassCohort[] {
  return readAll().filter((c) => c.checkId === checkId);
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
  check_id?: string;
  name: string;
  errors: string[];
  counts: Record<string, number>;
  children_checked: number;
  simulated: boolean;
  rule?: { min_hits: number };
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

function fromServer(g: Served): ClassCohort {
  return { id: g.id, checkId: g.check_id ?? "", name: g.name, errors: g.errors, counts: g.counts, childrenChecked: g.children_checked, simulated: g.simulated, synced: true, rule: g.rule?.min_hits };
}

/** Make it: sent now when online, and then it lives on the server only. A refused name is thrown (so she can
 *  change it); a network failure keeps it on this phone to send later. */
export async function create(input: Input, online: boolean, fetchFn?: typeof fetch): Promise<ClassCohort> {
  const have = allForCheck(input.checkId).find((c) => keyOf(c) === keyOf(input));
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
      const made = { ...row, id: got.id, synced: true };
      served = [...(served ?? readCache()).filter((s) => keyOf(s) !== keyOf(made)), made];
      return made;
    } catch (e) {
      if (e instanceof CohortError && e.status > 0) throw e; // refused: she can change the name
    }
  }
  writePending([...pending(), row]);
  return row;
}

/** Try to send one phone-only cohort now and say why when the server refuses (the caller shows the status and reason). */
export async function sendNow(id: string, language: string, fetchFn?: typeof fetch): Promise<void> {
  const row = pending().find((r) => r.id === id);
  if (!row) return;
  await send(row, language, fetchFn); // throws CohortError with the server's reason
  await syncPending(language, fetchFn); // sent: drop the phone copy and read the list again
}

/** Send the ones made offline (and drop their phone copy once sent), then read her list from the server.
 *  Quiet when it fails: a failed read changes nothing and it tries again next time. */
export async function syncPending(language: string, fetchFn?: typeof fetch): Promise<void> {
  const rows = pending();
  const left: ClassCohort[] = [];
  for (const r of rows) {
    try {
      await send(r, language, fetchFn);
    } catch {
      left.push(r); // still offline, or refused: keep it here
    }
  }
  if (left.length !== rows.length || localStorage.getItem(KEY) !== null) writePending(left);
  try {
    const list = await ccall<Served[]>("/class-only", "teacher", {}, fetchFn);
    served = list.map(fromServer);
    writeCache(served);
  } catch {
    /* offline: what was read earlier this visit, or the cached copy, stays */
  }
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
