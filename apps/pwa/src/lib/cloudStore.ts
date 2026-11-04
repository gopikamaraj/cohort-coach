// The cloud copy of this phone's data (decided 2 Nov 2026, docs/build/DECISIONS.md). While online, every
// change to the classes, checks, results and settings is written to the server, and each time the app opens
// online it reads everything back from the server: the server is the record, and the phone holds only a cache
// and a queue of changes made offline. Rehearsal transcripts and sheet photos never go (they stay on the phone).
import { API_BASE } from "./api";
import { getUser, userHeader } from "./identity";
import { db, type CohortDb } from "./db";
import { isOnline } from "./net";

export const SYNCED = ["classes", "checks", "profiles", "settings"] as const;
export type SyncedTable = (typeof SYNCED)[number];

const QUEUE_KEY = "cc.cloud.queue";
type Fetch = typeof fetch;

interface Pending {
  table: SyncedTable;
  id: string;
}

let suppress = 0; // set while the cache is being refilled from the server, so it is not echoed back
let timer: ReturnType<typeof setTimeout> | null = null;
const watched = new WeakSet<CohortDb>();
let listening = false;
let flushing: Promise<void> | null = null;

function readQueue(): Pending[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) ?? "[]") as Pending[];
  } catch {
    return [];
  }
}

function writeQueue(q: Pending[]): void {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
  } catch {
    /* private mode: the queue lasts until the page closes */
  }
}

export function queued(): number {
  return readQueue().length;
}

function mark(table: SyncedTable, id: string | undefined): void {
  if (suppress > 0 || !id) return;
  const q = readQueue();
  if (!q.some((p) => p.table === table && p.id === id)) writeQueue([...q, { table, id }]);
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => void flushQueue(), 300); // after the write's transaction has finished
}

/** Watch the four tables: every create, change and delete is queued for the server. */
export function watchTables(store: CohortDb = db): void {
  if (watched.has(store)) return;
  watched.add(store);
  const key = (table: SyncedTable, obj: { id?: string; key?: string }): string | undefined => (table === "settings" ? obj.key : obj.id);
  for (const name of SYNCED) {
    const t = store.table(name);
    t.hook("creating", (_pk, obj) => {
      mark(name, key(name, obj as { id?: string; key?: string }));
    });
    t.hook("updating", (_mods, pk) => {
      mark(name, String(pk));
    });
    t.hook("deleting", (pk) => {
      mark(name, String(pk));
    });
  }
  if (!listening) {
    listening = true;
    window.addEventListener("online", () => void flushQueue());
  }
}

function headers(): Record<string, string> {
  return { "Content-Type": "application/json", ...userHeader() };
}

const OWNER_KEY = "cc.cacheOwner";

/** The cache belongs to one user. A different user signing in on this browser starts from an empty cache, so
 *  one person's classes can never be uploaded under another's nickname. The very first sign-in keeps what the
 *  browser already holds (it was made before nicknames were accounts) and sends it up if the cloud has nothing. */
async function claimCache(store: CohortDb): Promise<void> {
  const me = getUser()?.id ?? null;
  if (!me) return;
  let owner: string | null = null;
  try {
    owner = localStorage.getItem(OWNER_KEY);
  } catch {
    /* private mode */
  }
  if (owner !== null && owner !== me) {
    writeQueue([]);
    suppress += 1;
    try {
      for (const t of SYNCED) await store.table(t).clear();
    } finally {
      suppress -= 1;
    }
  }
  try {
    localStorage.setItem(OWNER_KEY, me);
  } catch {
    /* private mode */
  }
}

/** The nickname changed: she is a different teacher now. What waited to go up belonged to the old one. */
export function forgetQueue(): void {
  writeQueue([]);
}

/** Send what is queued: the row as it is now, or a delete if it is gone. A failure leaves it queued. */
export async function flushQueue(store: CohortDb = db, fetchFn: Fetch = (...a) => fetch(...a)): Promise<void> {
  if (flushing) return flushing;
  flushing = (async () => {
    if (!isOnline()) return;
    let q = readQueue();
    while (q.length > 0) {
      const next = q[0] as Pending;
      const row = (await store.table(next.table).get(next.id)) as unknown;
      const url = `${API_BASE}/api/store/${next.table}/${encodeURIComponent(next.id)}`;
      try {
        const res = row === undefined ? await fetchFn(url, { method: "DELETE", headers: headers() }) : await fetchFn(url, { method: "PUT", headers: headers(), body: JSON.stringify({ data: row }) });
        if (!res.ok && res.status >= 500) return; // the server is unwell: try again later
        // a 4xx means this document will never be accepted: drop it from the queue rather than loop on it
      } catch {
        return; // no connection: it stays queued
      }
      q = readQueue().slice(1);
      writeQueue(q);
    }
  })().finally(() => {
    flushing = null;
  });
  return flushing;
}

type Everything = Record<SyncedTable, Record<string, unknown>>;

/**
 * Read everything from the server into the cache. Anything this phone changed offline is sent first. A phone
 * that already holds data the server has never seen (it was used before the cloud copy existed) sends it up
 * instead of being wiped. Offline, or if the server cannot be reached, the cache is left as it is.
 */
export async function hydrate(store: CohortDb = db, fetchFn: Fetch = (...a) => fetch(...a)): Promise<"synced" | "offline"> {
  if (!isOnline()) return "offline";
  try {
    if (!getUser()) return "offline"; // not signed in: nothing to read yet
    await claimCache(store);
    await flushQueue(store, fetchFn);
    const res = await fetchFn(`${API_BASE}/api/store`, { headers: headers() });
    if (!res.ok) return "offline";
    const cloud = (await res.json()) as Everything;
    const cloudEmpty = SYNCED.every((t) => Object.keys(cloud[t] ?? {}).length === 0);
    if (cloudEmpty) {
      for (const t of SYNCED) {
        for (const row of (await store.table(t).toArray()) as { id?: string; key?: string }[]) mark(t, t === "settings" ? row.key : row.id);
      }
      await flushQueue(store, fetchFn);
      return "synced";
    }
    suppress += 1;
    try {
      await store.transaction("rw", SYNCED.map((t) => store.table(t)), async () => {
        // a change made here that is still waiting to go up is newer than the server's copy: keep it
        const waiting = readQueue();
        for (const t of SYNCED) {
          const keep = new Set(waiting.filter((p) => p.table === t).map((p) => p.id));
          const table = store.table(t);
          const pk = table.schema.primKey.name;
          for (const k of await table.toCollection().primaryKeys()) if (!keep.has(String(k))) await table.delete(k);
          const docs = Object.values(cloud[t] ?? {}).filter((d) => !keep.has(String((d as Record<string, unknown>)[pk])));
          if (docs.length > 0) await table.bulkPut(docs);
        }
      });
    } finally {
      suppress -= 1;
    }
    return "synced";
  } catch {
    return "offline";
  }
}

export interface Peer {
  teacher: string; // a nickname she chose, or "Teacher N"
  class: string;
  errors: string[];
}

/** The other teachers whose class results show any of these mistakes. Names and classes only, never a count. */
export async function peersFor(errors: string[], fetchFn: Fetch = (...a) => fetch(...a)): Promise<Peer[]> {
  if (errors.length === 0 || !isOnline()) return [];
  try {
    const res = await fetchFn(`${API_BASE}/api/store/peers?errors=${encodeURIComponent(errors.join(","))}`, { headers: headers() });
    return res.ok ? ((await res.json()) as Peer[]) : [];
  } catch {
    return [];
  }
}

/** Delete everything the server holds for this phone (the "clear this phone" action). */
export async function clearCloud(fetchFn: Fetch = (...a) => fetch(...a)): Promise<void> {
  writeQueue([]);
  if (!isOnline()) return;
  try {
    await fetchFn(`${API_BASE}/api/store`, { method: "DELETE", headers: headers() });
  } catch {
    /* offline: nothing to delete there yet */
  }
}
