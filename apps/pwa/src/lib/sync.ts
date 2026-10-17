// Counts-only sync. The payload is built from the class-level profile, field by field, so a
// per-child value cannot get in by accident; the server's schema rejects anything else too.
import { db, type CohortDb, type ProfileRow } from "./db";

export interface ProfilePayload {
  term: string;
  form: string;
  children_checked: number;
  counts: Record<string, number>;
  anchor_wrong_count: number;
  untracked: Record<string, number>;
  simulated: boolean;
}

export const PROFILE_PAYLOAD_KEYS = [
  "anchor_wrong_count",
  "children_checked",
  "counts",
  "form",
  "simulated",
  "term",
  "untracked",
] as const;

export function profilePayload(row: ProfileRow): ProfilePayload {
  return {
    term: `T${row.term}`,
    form: row.formKey,
    children_checked: row.childrenChecked,
    counts: { ...row.counts },
    anchor_wrong_count: row.anchorWrongCount,
    untracked: { ...row.untracked },
    simulated: row.simulated,
  };
}

export async function enqueueProfile(row: ProfileRow, store: CohortDb = db): Promise<void> {
  // A newer result for the same class and term replaces the one still waiting.
  const waiting = await store.syncQueue.where("classId").equals(row.classId).toArray();
  for (const w of waiting) {
    if (w.kind === "profile" && w.payload["term"] === `T${row.term}` && w.id !== undefined) {
      await store.syncQueue.delete(w.id);
    }
  }
  await store.syncQueue.add({
    kind: "profile",
    classId: row.classId,
    payload: { ...profilePayload(row) },
    createdAt: Date.now(),
    tries: 0,
  });
}

export async function pendingCount(store: CohortDb = db): Promise<number> {
  return store.syncQueue.where("kind").equals("profile").count();
}

export interface FlushResult {
  sent: number;
  failed: number;
}

const running = new WeakMap<CohortDb, Promise<FlushResult>>();

/** Send what is waiting. Safe to call any time (a second call joins the one in flight);
 * nothing is sent while offline. */
export function flush(
  online: boolean,
  store: CohortDb = db,
  fetchFn: typeof fetch = (...args) => fetch(...args),
  base = "",
): Promise<FlushResult> {
  const active = running.get(store);
  if (active) return active;
  const job = sendAll(online, store, fetchFn, base).finally(() => running.delete(store));
  running.set(store, job);
  return job;
}

async function sendAll(
  online: boolean,
  store: CohortDb = db,
  fetchFn: typeof fetch = (...args) => fetch(...args),
  base = "",
): Promise<FlushResult> {
  const result: FlushResult = { sent: 0, failed: 0 };
  if (!online) return result;
  const waiting = await store.syncQueue.where("kind").equals("profile").toArray();
  for (const item of waiting) {
    if (item.id === undefined) continue;
    try {
      const res = await fetchFn(`${base}/api/classes/${item.classId}/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item.payload),
      });
      if (res.ok || (res.status >= 400 && res.status < 500)) {
        // A 4xx can never succeed on retry; drop it rather than loop on it.
        await store.syncQueue.delete(item.id);
        if (res.ok) result.sent += 1;
        else result.failed += 1;
      } else {
        await store.syncQueue.update(item.id, { tries: item.tries + 1 });
        result.failed += 1;
      }
    } catch {
      await store.syncQueue.update(item.id, { tries: item.tries + 1 });
      result.failed += 1;
    }
  }
  return result;
}
