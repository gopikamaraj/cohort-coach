// After she has tried the technique in her real class: how like her class were the pretend children?
// Kept on this phone with the rehearsal, and sent as choices only (no free text, no name, no class id)
// so the simulator can be tuned. It is not a score of her.
import { API_BASE } from "./api";
import { db, type CohortDb } from "./db";

export type Likeness = "like" | "some" | "not_like";
export const LIKENESS: readonly Likeness[] = ["like", "some", "not_like"];
export const DIFFERENCES = ["mistakes_differ", "too_easy", "too_hard", "quieter", "more_talkative", "explained_differently"] as const;
export type Difference = (typeof DIFFERENCES)[number];

export interface Observation {
  likeness: Likeness;
  differences: Difference[];
}

type Fetch = typeof fetch;
const defaultFetch: Fetch = (...a) => fetch(...a);

async function post(scenario: string, language: string, o: Observation, fetchFn: Fetch): Promise<boolean> {
  try {
    const res = await fetchFn(`${API_BASE}/api/practice/observations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario, language, likeness: o.likeness, differences: o.differences }),
    });
    return res.ok || (res.status >= 400 && res.status < 500); // a 4xx will never succeed: stop trying
  } catch {
    return false;
  }
}

export async function saveObservation(id: number, o: Observation, online: boolean, store: CohortDb = db, fetchFn: Fetch = defaultFetch): Promise<boolean> {
  const row = await store.transcripts.get(id);
  if (!row) return false;
  const sent = online ? await post(row.scenario ?? "SUB-SFL", row.language ?? "en", o, fetchFn) : false;
  await store.transcripts.update(id, { observation: { ...o, sent, at: Date.now() } });
  return sent;
}

/** Send observations saved while offline. Returns how many went out. */
export async function sendPendingObservations(online: boolean, store: CohortDb = db, fetchFn: Fetch = defaultFetch): Promise<number> {
  if (!online) return 0;
  let n = 0;
  for (const row of await store.transcripts.toArray()) {
    const o = row.observation;
    if (!o || o.sent || row.id === undefined) continue;
    if (await post(row.scenario ?? "SUB-SFL", row.language ?? "en", o, fetchFn)) {
      await store.transcripts.update(row.id, { observation: { ...o, sent: true } });
      n += 1;
    }
  }
  return n;
}
