// The record of what was entered on this phone: every check (typed or from photos), whether its class
// counts have gone to the server, and how many children were filled from a photo. Per-child answers
// are only ever here; the server holds class counts. Photos themselves are not kept anywhere.
import { db, type CohortDb } from "./db";
import { hasAnswers } from "./check";

export interface CheckSummary {
  id: string;
  formKey: string;
  paperCode?: string | null;
  kind?: string;
  checkDate?: string;
  children: number;
  viaPhoto: number;
  updatedAt: number;
  state: "sent" | "waiting" | "open"; // counts sent, counts waiting to send, check not finished
  rows: string[][];
}

export async function listChecks(store: CohortDb = db): Promise<CheckSummary[]> {
  const [checks, profiles, queue] = await Promise.all([store.checks.toArray(), store.profiles.toArray(), store.syncQueue.toArray()]);
  const finished = new Set(profiles.map((p) => p.id));
  const waiting = new Set(queue.filter((q) => q.kind === "profile").map((q) => `${q.classId}:${String(q.payload["term"]).replace(/^T/, "")}`));
  return checks
    .map((c): CheckSummary => {
      const rows = c.children.filter(hasAnswers);
      return {
        id: c.id,
        formKey: c.formKey,
        paperCode: c.paperCode,
        kind: c.kind,
        checkDate: c.checkDate,
        children: rows.length,
        viaPhoto: (c.viaPhoto ?? []).filter((i) => c.children[i] && hasAnswers(c.children[i]!)).length,
        updatedAt: c.updatedAt,
        state: !finished.has(c.id) ? "open" : waiting.has(c.id) ? "waiting" : "sent",
        rows,
      };
    })
    .sort((a, b) => b.updatedAt - a.updatedAt); // newest first, by date saved
}
