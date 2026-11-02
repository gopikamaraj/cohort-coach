// The cohort chat's API calls. The server does every check; this only sends and shows. A teacher is
// identified by her phone's random device id, staff by the role they act as (and a pseudonymous
// person id in the judge deployment). Nothing here ever holds a handle or a phone number.
import { API_BASE } from "./api";
import { storeKey } from "./cloudStore";
import { deviceId } from "./consent";
import { getPrefs } from "./tester";

export interface CohortSummary {
  id: string;
  error: string;
  status: string;
  track_version: number;
  schools: number | null;
  members: number | null;
  thread: "open" | "read_only";
  simulated: boolean;
  joined?: boolean;
}

export interface Post {
  id: string;
  author_kind: "teacher" | "mentor" | "coach" | "system";
  author_name: string;
  body: string | null;
  status: "visible" | "reported" | "hidden" | "deleted";
  pinned: boolean;
  created_at: string;
}

export type Who = "teacher" | "mentor" | "coach" | "officer";

export class CohortError extends Error {
  constructor(
    public status: number,
    public codes: string[] = [],
  ) {
    super(`cohort ${status}`);
  }
}

function headers(who: Who): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json", "X-Role": who };
  if (who === "teacher") {
    h["X-Device-Id"] = deviceId();
    const key = storeKey(getPrefs().nickname);
    if (key) h["X-Store-Key"] = key; // lets the server hand her the cohorts the officer formed for her class
  }
  return h;
}

export async function ccall<T>(
  path: string,
  who: Who,
  init: { method?: string; body?: unknown } = {},
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<T> {
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/cohorts${path}`, {
      method: init.method ?? "GET",
      headers: headers(who),
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch {
    throw new CohortError(0);
  }
  if (!res.ok) {
    let codes: string[] = [];
    try {
      const d = ((await res.json()) as { detail?: { codes?: string[] } }).detail;
      codes = d?.codes ?? [];
    } catch {
      /* no body */
    }
    throw new CohortError(res.status, codes);
  }
  return (await res.json()) as T;
}

/** Pinned posts first, then oldest first: how the thread is shown. */
export function ordered(posts: Post[]): Post[] {
  return [...posts].sort((a, b) => Number(b.pinned) - Number(a.pinned) || a.created_at.localeCompare(b.created_at));
}

/** A held post's text is never shown to other members; a moderator sees it marked. */
export function showsText(post: Post, moderator: boolean): boolean {
  return post.body !== null && (moderator || post.status === "visible");
}
