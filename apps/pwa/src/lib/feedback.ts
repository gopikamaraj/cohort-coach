// Feedback: app, simulation, content and card flags go to the server and are reviewed by the admin. Anonymous:
// no name, class or device id is sent. Free text is limited to 500 characters and the server refuses phone
// numbers, emails and ID-like numbers. When offline it waits in the send queue and goes when a signal returns.
import { API_BASE } from "./api";
import { db, type CohortDb } from "./db";

export type FeedbackKind = "app" | "simulation" | "content" | "card_flag";

export interface FeedbackBody {
  kind: FeedbackKind;
  rating?: number;
  text?: string;
  language: string;
  role: string;
  context?: string;
}

type Fetch = typeof fetch;
const defaultFetch: Fetch = (...a) => fetch(...a);

async function post(body: FeedbackBody, fetchFn: Fetch): Promise<"sent" | "retry" | "refused"> {
  try {
    const res = await fetchFn(`${API_BASE}/api/feedback`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) return "sent";
    return res.status >= 400 && res.status < 500 ? "refused" : "retry";
  } catch {
    return "retry";
  }
}

/** Send now if online, else queue. Returns "refused" when the server rejected it (for example personal data in the text). */
export async function sendFeedback(body: FeedbackBody, online: boolean, store: CohortDb = db, fetchFn: Fetch = defaultFetch): Promise<"sent" | "queued" | "refused"> {
  if (online) {
    const r = await post(body, fetchFn);
    if (r !== "retry") return r === "sent" ? "sent" : "refused";
  }
  await store.syncQueue.add({ kind: "feedback", classId: "-", payload: { ...body }, createdAt: Date.now(), tries: 0 });
  return "queued";
}

export async function flushFeedback(online: boolean, store: CohortDb = db, fetchFn: Fetch = defaultFetch): Promise<number> {
  if (!online) return 0;
  let n = 0;
  for (const row of await store.syncQueue.where("kind").equals("feedback").toArray()) {
    const r = await post(row.payload as unknown as FeedbackBody, fetchFn);
    if (r !== "retry" && row.id !== undefined) {
      await store.syncQueue.delete(row.id);
      if (r === "sent") n += 1;
    }
  }
  return n;
}
