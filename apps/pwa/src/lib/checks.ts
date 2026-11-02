// What each check is: its kind (pre-test, post-test or termly check), paper, term, round and date, and
// the rules around it. A pre-test and a post-test are just labels on two checks of one class; the
// pairing counts, on this phone, what changed between them. Nothing here names a child: the result of
// pairing is counts only. The Python twin is engine/checkpair.py; both are tested on the same cases
// (tests/fixtures/check_pairing_cases.json).
import { diagnoseAnchors, diagnoseChild, formOf } from "./diagnosis";
import { enteredChildren, readRow } from "./check";
import type { CheckKind, CheckRow, ProfileRow } from "./db";

export const KINDS: readonly CheckKind[] = ["pre", "post", "termly"];
export type { CheckKind };

export function checkId(classId: string, term: number, round = 1): string {
  return round <= 1 ? `${classId}:${term}` : `${classId}:${term}:${round}`; // round 1 keeps the id used before labels existed
}

export function nextRound(history: CheckRow[], classId: string, term: number): number {
  const taken = history.filter((c) => c.classId === classId && c.term === term).map((c) => c.round ?? 1);
  return taken.length === 0 ? 1 : Math.max(...taken) + 1;
}

const latest = (rows: CheckRow[]): CheckRow | undefined => [...rows].sort((a, b) => b.updatedAt - a.updatedAt)[0];
const kindOf = (c: CheckRow): CheckKind => c.kind ?? "pre";

/** Pre-test when nothing is saved, post-test once a track began after a pre-test and a new term started, else termly. */
export function suggestKind(history: CheckRow[], profiles: ProfileRow[], term: number): CheckKind {
  if (history.length === 0) return "pre";
  const pre = latest(history.filter((c) => kindOf(c) === "pre"));
  if (pre && pre.status === "closed" && term > pre.term) {
    const hadTrack = profiles.some((p) => p.id === pre.id && p.track !== null);
    const answered = history.some((c) => kindOf(c) === "post" && c.updatedAt > pre.updatedAt);
    if (hadTrack && !answered) return "post";
  }
  return "termly";
}

const other = (form: string) => (form === "A" ? "B" : "A");

/** Form A for a pre-test, the other paper for a post-test and for a later check. */
export function suggestForm(kind: CheckKind, history: CheckRow[]): string {
  if (kind === "pre") return "A";
  const base = kind === "post" ? (latest(history.filter((c) => kindOf(c) === "pre")) ?? latest(history)) : latest(history);
  return base ? other(base.formKey) : kind === "post" ? "B" : "A";
}

/** The track a post-test evaluates: the one the class's latest pre-test started. */
export function trackToEvaluate(history: CheckRow[], profiles: ProfileRow[]): string | null {
  const pre = latest(history.filter((c) => kindOf(c) === "pre"));
  return pre ? (profiles.find((p) => p.id === pre.id)?.track ?? null) : null;
}

export function canClose(check: CheckRow): { ok: boolean; reason?: "no_sheets" } {
  return enteredChildren(check.children).length > 0 ? { ok: true } : { ok: false, reason: "no_sheets" };
}

export function findDuplicate(history: CheckRow[], want: { classId: string; kind: CheckKind; form: string; checkDate: string }): CheckRow | undefined {
  return history.find((c) => c.classId === want.classId && kindOf(c) === want.kind && c.formKey === want.form && c.checkDate === want.checkDate);
}

export function openCheck(history: CheckRow[], classId: string): CheckRow | undefined {
  return latest(history.filter((c) => c.classId === classId && c.status === "entering"));
}

const LOCALE: Record<string, string> = { en: "en-GB", hi: "hi-IN", ta: "ta-IN" };
export function formatDate(iso: string, lang: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(LOCALE[lang] ?? "en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}
export const today = (): string => new Date().toISOString().slice(0, 10);

type Tr = (key: never, params?: Record<string, string | number>) => string;
export function kindName(tr: Tr, kind: CheckKind): string {
  return tr(`check.kind.${kind}` as never);
}

/** The class name to show: the names the app gives by default are translated; a name she typed is hers. */
export function shownClassName(tr: Tr, klass: { name: string; simulated: boolean } | null | undefined): string {
  if (!klass) return "";
  if (klass.simulated && klass.name === "Class 3B (simulated)") return tr("check.default_sim_class" as never);
  if (!klass.simulated && klass.name === "My class") return tr("check.default_class" as never);
  return klass.name;
}

/** What names the paper of a check: its printed code ("PRE · 3A · T1"), or "Sample paper A" for the judge's sample. */
export function formName(tr: Tr, c: Pick<CheckRow, "formKey" | "paperCode">): string {
  return c.paperCode ?? tr("check.form_n" as never, { f: c.formKey });
}

/** "Pre-test · PRE · 3A · T1 · Class 3A · 29 Oct 2026". */
export function formatCheckLabel(tr: Tr, c: CheckRow, className: string, lang: string): string {
  const parts = [kindName(tr, kindOf(c)), formName(tr, c), className, c.checkDate ? formatDate(c.checkDate, lang) : ""];
  return parts.filter(Boolean).join(" · ");
}

export function summaryOf(c: CheckRow): { kind: CheckKind; form: string; date: string | undefined; papers: number } {
  return { kind: kindOf(c), form: c.formKey, date: c.checkDate, papers: enteredChildren(c.children).length };
}

export { legacyFields } from "./checkMigrate";

// --- pairing -------------------------------------------------------------------------------------

export const COMPETENCIES: Record<string, string[]> = {
  C1: ["PV-HEARD", "PV-REVERSE"],
  C2: ["ADD-NOCARRY"],
  C3: ["SUB-SFL", "SUB-NODEC"],
};
export const SMALL_SAMPLE_BELOW = 10;

export interface Change {
  flagged_before: number;
  fixed: number;
  still_flagged: number;
  newly_flagged: number;
}
export interface Pairing {
  paired: number;
  excluded_absent: number;
  excluded_not_entered: number;
  excluded_unmatched: number;
  small_sample: boolean;
  by_competency: Record<string, Change>;
}

const entered = (row: string[]) => row.some((cell) => cell !== "");
// Before and after compare the anchor items only: a paper's adaptive items help find errors but never
// count as improvement. A built-in form has no adaptive items.
function flags(form: string, row: string[]): Set<string> {
  const items = formOf(form)?.items ?? [];
  const keep = items.map((it) => it.anchor !== false);
  const shows = keep.every(Boolean) ? diagnoseChild(form, readRow(row)).shows : diagnoseAnchors(form, readRow(row), keep).shows;
  return new Set(Object.entries(COMPETENCIES).filter(([, codes]) => codes.some((c) => shows.includes(c))).map(([name]) => name));
}

/** Match children by roll position, leave out the absent and the unentered, and count the change per competency. */
export function pairChecks(preForm: string, preRows: string[][], postForm: string, postRows: string[][], preAbsent: Set<number> = new Set(), postAbsent: Set<number> = new Set()): Pairing {
  const common = Math.min(preRows.length, postRows.length);
  const by: Record<string, Change> = {};
  for (const name of Object.keys(COMPETENCIES)) by[name] = { flagged_before: 0, fixed: 0, still_flagged: 0, newly_flagged: 0 };
  let paired = 0;
  let absent = 0;
  let notEntered = 0;
  for (let i = 0; i < common; i++) {
    const pre = preRows[i] as string[];
    const post = postRows[i] as string[];
    if (preAbsent.has(i) || postAbsent.has(i)) absent += 1;
    else if (!entered(pre) || !entered(post)) notEntered += 1;
    else {
      paired += 1;
      const before = flags(preForm, pre);
      const after = flags(postForm, post);
      for (const [name, t] of Object.entries(by)) {
        if (before.has(name)) {
          t.flagged_before += 1;
          if (after.has(name)) t.still_flagged += 1;
          else t.fixed += 1;
        } else if (after.has(name)) t.newly_flagged += 1;
      }
    }
  }
  return {
    paired,
    excluded_absent: absent,
    excluded_not_entered: notEntered,
    excluded_unmatched: Math.abs(preRows.length - postRows.length),
    small_sample: paired < SMALL_SAMPLE_BELOW,
    by_competency: by,
  };
}
