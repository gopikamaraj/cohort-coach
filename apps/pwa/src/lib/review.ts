// The Practice Class review: rehearsals recorded on this phone only, replayed turn by turn, and
// tagged by the teacher herself. The tag is her own private note about whether the rehearsal
// helped; it is never sent anywhere and nothing scores her. Counts only, never percentages.
import { db, type CohortDb, type TranscriptRow } from "./db";

export type Impact = "positive" | "none" | "negative";
export const IMPACTS: readonly Impact[] = ["positive", "none", "negative"];

export interface ReviewTurn {
  turn: number;
  teacher: string;
  child: string;
  speaker: string | null;
  move?: string;
}

export function turnsOf(row: TranscriptRow): ReviewTurn[] {
  return (row.turns as ReviewTurn[]).filter((t) => typeof t?.teacher === "string");
}

/** Recorded rehearsals with at least one turn, newest first. */
export async function listSessions(store: CohortDb = db): Promise<TranscriptRow[]> {
  const rows = await store.transcripts.toArray();
  return rows.filter((r) => turnsOf(r).length > 0).sort((a, b) => b.createdAt - a.createdAt);
}

export async function setImpact(id: number, impact: Impact | undefined, store: CohortDb = db): Promise<void> {
  await store.transcripts.update(id, { impact });
}

export async function deleteSession(id: number, store: CohortDb = db): Promise<void> {
  await store.transcripts.delete(id);
}

export async function deleteAllSessions(store: CohortDb = db): Promise<void> {
  await store.transcripts.clear();
}

export function impactCounts(rows: { impact?: Impact }[]): Record<Impact | "untagged", number> {
  const out = { positive: 0, none: 0, negative: 0, untagged: 0 };
  for (const r of rows) out[r.impact ?? "untagged"] += 1;
  return out;
}

/** The moves she used, most used first: ["Asks the child to explain her steps", 2], ... */
export function moveCounts(turns: ReviewTurn[]): [string, number][] {
  const counts = new Map<string, number>();
  for (const t of turns) if (t.move) counts.set(t.move, (counts.get(t.move) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}
