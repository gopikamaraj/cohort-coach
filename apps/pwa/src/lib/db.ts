// Everything the phone keeps. Per-child answers (`checks`) live here and only here: nothing in
// this file sends them anywhere. The sync queue holds class-level counts only.
import type { Difference } from "./observation";
import Dexie, { type Table } from "dexie";
import { legacyFields } from "./checkMigrate";

export interface ClassRow {
  id: string;
  name: string;
  simulated: boolean;
  createdAt: number;
}

/** One class, one term, one paper. `children[i][q]` is the raw text of child i's answer to
 * question q: digits, "_" for a blank box, "?" for one she cannot read, "" for not entered.
 * Rows are in roll order; only this phone knows which row is which child. */
import type { StageCounts } from "./stagecalc";

export type CheckKind = "pre" | "post" | "termly";
export type CheckStatus = "draft" | "entering" | "approved" | "closed";

export interface CheckRow {
  id: string;
  classId: string;
  term: number;
  formKey: string;
  children: string[][];
  updatedAt: number;
  viaPhoto?: number[]; // which children were filled from a photo (the photo itself is never kept)
  missed?: number[]; // older whole-sheet tag: children she tagged "missed the teaching" (stays on this phone)
  missedConcepts?: Record<number, string[]>; // per child, the concepts she tagged "missed the teaching on this"
  absent?: number[]; // roll numbers she skipped because the child was away
  approved?: number[]; // roll numbers whose answers she has checked and approved (absent rolls count as approved)
  // What this check is. Checks saved before these existed get them from the version 2 upgrade (confirm: true).
  kind?: CheckKind;
  round?: number; // 1, 2, 3 within the term; round 1 keeps the id classId:term
  checkDate?: string; // YYYY-MM-DD
  paperVersion?: string; // which printed paper (the answer keys hash, or "legacy")
  trackId?: string | null; // a post-test: the track it evaluates; a pre-test: the track it starts
  expectedChildren?: number | null;
  status?: CheckStatus;
  notes?: string;
  paperId?: string | null; // the Paper Studio paper this check uses (pilot papers only, for now)
  paperCode?: string | null; // its printed check code, e.g. "PRE · 3A · T1"
  confirm?: boolean; // the label was guessed from older data: ask her to confirm it
}

/** The class-level result: how many children showed each error. No child appears here. */
export interface ProfileRow {
  id: string;
  classId: string;
  term: number;
  formKey: string;
  childrenChecked: number;
  counts: Record<string, number>;
  eligible: string[];
  track: string | null;
  anchorWrongCount: number;
  untracked: Record<string, number>;
  stages?: StageCounts; // counts per (error, stage) for the class; never a child
  simulated: boolean;
  createdAt: number;
}

export interface QueueRow {
  id?: number;
  kind: "profile" | "flag" | "feedback";
  classId: string;
  payload: Record<string, unknown>;
  createdAt: number;
  tries: number;
}

export interface TranscriptRow {
  id?: number;
  classId: string;
  createdAt: number;
  turns: unknown[]; // Practice Class transcripts: device only (P06)
  sessionId?: string;
  scenario?: string;
  ended?: boolean;
  card?: unknown;
  ratings?: Record<string, string>;
  // Review (kept on this phone only): which language and seed, when it ended, and her own tag.
  language?: string;
  seed?: number;
  endedAt?: number;
  impact?: "positive" | "none" | "negative";
  observation?: { likeness: "like" | "some" | "not_like"; differences: Difference[]; sent: boolean; at: number };
}

export interface OutboxRow {
  id?: number;
  classId: string;
  createdAt: number;
  photo: Blob; // queued answer-sheet photos (P08)
}

export interface SettingRow {
  key: string;
  value: unknown;
}

export class CohortDb extends Dexie {
  classes!: Table<ClassRow, string>;
  checks!: Table<CheckRow, string>;
  profiles!: Table<ProfileRow, string>;
  syncQueue!: Table<QueueRow, number>;
  transcripts!: Table<TranscriptRow, number>;
  outbox!: Table<OutboxRow, number>;
  settings!: Table<SettingRow, string>;

  constructor(name = "cohort-coach") {
    super(name);
    this.version(1).stores({
      classes: "id",
      checks: "id, classId",
      profiles: "id, classId",
      syncQueue: "++id, kind, classId",
      transcripts: "++id, classId",
      outbox: "++id, classId",
      settings: "key",
    });
    // Version 2: every check says what it is (pre-test, post-test or termly, its date). Checks saved
    // before this get a guessed label, marked confirm: true; their sheets are not touched.
    this.version(2)
      .stores({ checks: "id, classId, checkDate" })
      .upgrade(async (tx) => {
        const checks = (await tx.table("checks").toArray()) as CheckRow[];
        const withResult = new Set(((await tx.table("profiles").toArray()) as ProfileRow[]).map((p) => p.id));
        for (const c of checks) {
          const add = legacyFields(c, checks, withResult);
          if (Object.keys(add).length > 0) await tx.table("checks").update(c.id, add);
        }
      });
  }
}

export const db = new CohortDb();

export async function getSetting<T>(key: string, fallback: T, store: CohortDb = db): Promise<T> {
  const row = await store.settings.get(key);
  return row ? (row.value as T) : fallback;
}

export async function setSetting(key: string, value: unknown, store: CohortDb = db): Promise<void> {
  await store.settings.put({ key, value });
}

export function newClassId(simulated: boolean): string {
  const bytes = crypto.getRandomValues(new Uint8Array(5));
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${simulated ? "sim" : "c"}-${hex}`;
}

/** The class this phone works with; created on first use. */
export async function activeClass(simulated: boolean, store: CohortDb = db): Promise<ClassRow> {
  const id = await getSetting<string | null>("activeClass", null, store);
  const existing = id ? await store.classes.get(id) : undefined;
  if (existing && existing.simulated === simulated) return existing;
  const row: ClassRow = {
    id: newClassId(simulated),
    name: simulated ? "Class 3B (simulated)" : "My class",
    simulated,
    createdAt: Date.now(),
  };
  await store.classes.put(row);
  await setSetting("activeClass", row.id, store);
  return row;
}

/** Clear everything on this phone: checks, results, queue, settings. */
export async function clearPhone(store: CohortDb = db): Promise<void> {
  await Promise.all(
    [store.classes, store.checks, store.profiles, store.syncQueue, store.transcripts, store.outbox, store.settings].map(
      (table) => table.clear(),
    ),
  );
}
