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
const VERSION_KEY = "cc.cloud.versions";
type Fetch = typeof fetch;

/** One change waiting to go to the cloud: a document of the four tables, or a plain API write (a check-in, a
 *  module's feedback, a chat post). `status` is "pending" until it has been sent; a refusal marks it "failed"
 *  with the reason and it stays listed until she presses Retry. Nothing is dropped silently. */
export interface Pending {
  table: SyncedTable | "api";
  id: string;
  status?: "pending" | "failed";
  offline?: boolean; // made, or left unsent, while there was no connection: only these are announced when she is back
  reason?: string;
  at?: number;
  api?: { method: string; path: string; body?: unknown; label: string; headers?: Record<string, string> };
}

export interface SyncState {
  phase: "idle" | "syncing" | "done";
  total: number;
  sent: number;
  conflicts: number;
  failed: { what: string; reason: string }[];
}

let state: SyncState = { phase: "idle", total: 0, sent: 0, conflicts: 0, failed: [] };
const listeners = new Set<() => void>();
const setState = (next: SyncState): void => {
  state = next;
  for (const l of listeners) l();
};
export const syncState = (): SyncState => state;
export function subscribeSync(l: () => void): () => void {
  listeners.add(l);
  return () => void listeners.delete(l);
}
export function closeSyncNotice(): void {
  if (state.phase === "done") setState({ phase: "idle", total: 0, sent: 0, conflicts: 0, failed: [] });
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

/** How many changes still wait to go up (pending or refused). */
export function queued(): number {
  return readQueue().length;
}

// The server's version of each document this device last read or wrote, so a write says what it was based on.
function readVersions(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(VERSION_KEY) ?? "{}") as Record<string, number>;
  } catch {
    return {};
  }
}
function writeVersions(v: Record<string, number>): void {
  try {
    localStorage.setItem(VERSION_KEY, JSON.stringify(v));
  } catch {
    /* private mode */
  }
}
const vkey = (table: string, id: string): string => `${table}/${id}`;

function mark(table: SyncedTable, id: string | undefined): void {
  if (suppress > 0 || !id) return;
  const q = readQueue();
  const have = q.find((p) => p.table === table && p.id === id);
  if (have) {
    have.status = "pending"; // changed again: send the newest copy
    if (!isOnline()) have.offline = true;
    delete have.reason;
    writeQueue(q);
  } else {
    writeQueue([...q, { table, id, status: "pending", at: Date.now(), ...(isOnline() ? {} : { offline: true }) }]);
  }
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => void flushQueue(), 300); // after the write's transaction has finished
}

/** Queue a plain API write (a check-in, a module's feedback, a chat post) so it is not lost offline.
 *  Returns "sent" when the server took it now, "queued" when it waits for a connection. A refusal (4xx) is
 *  returned as "refused" with the reason and is not queued: the caller tells her. */
export async function writeOrQueue(label: string, method: "POST" | "PUT" | "DELETE", path: string, body?: unknown, extra: Record<string, string> = {}, fetchFn: Fetch = (...a) => fetch(...a), replace = false): Promise<{ result: "sent" | "queued" | "refused"; reason?: string }> {
  const send = async (): Promise<{ result: "sent" | "queued" | "refused"; reason?: string }> => {
    try {
      const res = await fetchFn(`${API_BASE}${path}`, { method, headers: { ...headers(), ...extra }, body: body === undefined ? undefined : JSON.stringify(body) });
      if (res.ok) return { result: "sent" };
      if (res.status >= 500) return { result: "queued" };
      return { result: "refused", reason: await reasonOf(res) };
    } catch {
      return { result: "queued" };
    }
  };
  const out = isOnline() ? await send() : { result: "queued" as const };
  if (out.result === "queued") {
    // `replace`: a newer copy of the same document makes an older queued one pointless (a Practice Class session is sent whole at each turn)
    const q = readQueue().filter((p) => !(replace && p.api && p.api.path === path));
    writeQueue([...q, { table: "api", id: `${method} ${path} ${Date.now()}`, status: "pending", at: Date.now(), offline: true, api: { method, path, body, label, headers: extra } }]);
  }
  return out;
}

async function reasonOf(res: Response): Promise<string> {
  try {
    const j = (await res.json()) as { detail?: unknown; message?: unknown };
    const d = j.detail ?? j.message;
    if (typeof d === "string") return d;
    if (d && typeof d === "object" && "message" in d) return String((d as { message: unknown }).message);
  } catch {
    /* no body */
  }
  return `The server answered ${res.status}.`;
}

/** Watch the four tables: every create, change and delete is queued for the server. */
// ---- Practice Class sessions (decided 4 Nov 2026) --------------------------------------------------------------
// They are saved to her account like her checks and read only by her user id; the phone keeps a copy. A session's
// document id is its session id, so the same session is one document on every device. Each change sends the whole
// session (the newest copy replaces an older one still waiting in the outbox).
const sessionKey = (row: { sessionId?: string; createdAt?: number }): string => row.sessionId ?? `t${row.createdAt ?? 0}`;
const docPath = (key: string): string => `/api/store/transcripts/${encodeURIComponent(key)}`;

async function pushTranscript(store: CohortDb, pk: number): Promise<void> {
  const row = await store.transcripts.get(pk);
  if (!row) return;
  const { id: _id, ...data } = row;
  await writeOrQueue("practice session", "PUT", docPath(sessionKey(row)), { data }, {}, undefined, true);
}

const pushTimers = new Map<number, ReturnType<typeof setTimeout>>();
function schedulePush(store: CohortDb, pk: number): void {
  if (suppress > 0) return;
  const t = pushTimers.get(pk);
  if (t) clearTimeout(t);
  pushTimers.set(
    pk,
    setTimeout(() => {
      pushTimers.delete(pk);
      void pushTranscript(store, pk).catch(() => undefined);
    }, 400), // after the write's transaction has finished
  );
}

/** Bring her sessions from the account into this phone (one she made on another device), and send up any this phone
 *  has that the account does not. Returns how many came in. */
async function mergeTranscripts(store: CohortDb, cloud: Record<string, unknown> | undefined): Promise<number> {
  const docs = cloud ?? {};
  const local = await store.transcripts.toArray();
  const byKey = new Map(local.map((r) => [sessionKey(r), r]));
  let added = 0;
  suppress += 1;
  try {
    for (const [key, doc] of Object.entries(docs)) {
      const d = doc as { turns?: unknown[]; ended?: boolean };
      const mine = byKey.get(key);
      if (!mine) {
        await store.transcripts.add({ ...(doc as object), sessionId: (doc as { sessionId?: string }).sessionId ?? key } as never);
        added += 1;
      } else if ((d.turns?.length ?? 0) > mine.turns.length || (d.ended && !mine.ended)) {
        await store.transcripts.update(mine.id as number, doc as never); // the account has the further-along copy
      }
    }
  } finally {
    suppress -= 1;
  }
  for (const r of local) if (!(sessionKey(r) in docs) && r.id !== undefined) schedulePush(store, r.id); // first sync of what only this phone has
  return added;
}

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
  const tr = store.transcripts;
  tr.hook("creating", function (_pk, _obj) {
    // the id is given by the database after the write: send once it is known
    this.onsuccess = (pk: unknown) => schedulePush(store, pk as number);
  });
  tr.hook("updating", (_mods, pk) => {
    schedulePush(store, pk as number);
  });
  tr.hook("deleting", (_pk, obj) => {
    if (suppress > 0) return;
    void writeOrQueue("practice session", "DELETE", docPath(sessionKey(obj)), undefined, {}, undefined, true);
  });
  if (!listening) {
    listening = true;
    window.addEventListener("online", () => void flushQueue(db, undefined, true));
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

/** A write the server refused (4xx) from outside this file: keep it in the same list as a failed change, with
 *  the reason, so it is shown with the others and can be retried. Nothing is dropped silently. */
export function parkFailed(label: string, method: "POST" | "PUT" | "DELETE", path: string, body: unknown, reason: string): void {
  writeQueue([...readQueue(), { table: "api", id: `${method} ${path} ${Date.now()}`, status: "failed", reason, at: Date.now(), api: { method, path, body, label } }]);
}

/** Name a waiting change for the notice: "classes 3A", "checks c-1:2" or an API write's label. */
const whatOf = (p: Pending): string => (p.api ? p.api.label : `${p.table} ${p.id}`);

/**
 * Send what is queued, oldest first: the row as it is now, or a delete if it is gone. A connection problem or a
 * server error leaves the rest queued for later. A refusal (4xx) is not dropped: the change stays listed as
 * failed with the server's reason until she presses Retry. With `announce` (the app opened or the connection
 * came back with changes waiting) the progress and the result are published for the notice on screen.
 */
/** What is still waiting after a failed send was left because the connection or the server failed: it is announced later. */
function holdOffline(): void {
  writeQueue(readQueue().map((p) => (p.status === "failed" ? p : { ...p, offline: true })));
}

export async function flushQueue(store: CohortDb = db, fetchFn: Fetch = (...a) => fetch(...a), announce = false): Promise<void> {
  if (flushing) return flushing;
  flushing = (async () => {
    if (!isOnline()) return;
    const waiting = readQueue().filter((p) => p.status !== "failed");
    const show = announce && waiting.some((p) => p.offline); // a change that only had not been sent yet when the page closed is not an offline spell
    let sent = 0;
    let conflicts = 0;
    const failed: { what: string; reason: string }[] = [];
    if (show) setState({ phase: "syncing", total: waiting.length, sent: 0, conflicts: 0, failed: [] });
    const versions = readVersions();
    for (const item of waiting) {
      let res: Response;
      try {
        if (item.api) {
          res = await fetchFn(`${API_BASE}${item.api.path}`, { method: item.api.method, headers: { ...headers(), ...(item.api.headers ?? {}) }, body: item.api.body === undefined ? undefined : JSON.stringify(item.api.body) });
        } else {
          const table = item.table as SyncedTable;
          const row = (await store.table(table).get(item.id)) as unknown;
          const url = `${API_BASE}/api/store/${table}/${encodeURIComponent(item.id)}`;
          const base = versions[vkey(table, item.id)];
          res = row === undefined ? await fetchFn(url, { method: "DELETE", headers: headers() }) : await fetchFn(url, { method: "PUT", headers: headers(), body: JSON.stringify({ data: row, ...(base === undefined ? {} : { base_version: base }) }) });
        }
      } catch {
        holdOffline();
        break; // no connection: it stays queued
      }
      if (!res.ok && res.status >= 500) {
        holdOffline();
        break; // the server is unwell: try again later
      }
      const q = readQueue();
      const at = q.findIndex((p) => p.table === item.table && p.id === item.id);
      if (res.ok) {
        if (at >= 0) q.splice(at, 1);
        sent += 1;
        if (!item.api) {
          try {
            const j = (await res.clone().json()) as { version?: unknown; conflict?: unknown };
            if (typeof j.version === "number") versions[vkey(item.table, item.id)] = j.version;
            if (j.conflict === true) conflicts += 1;
          } catch {
            /* an answer without a version */
          }
        }
      } else {
        const reason = await reasonOf(res); // a 4xx will not be accepted as it is: keep it, say why, let her retry
        if (at >= 0) q[at] = { ...item, status: "failed", reason };
        failed.push({ what: whatOf(item), reason });
      }
      writeQueue(q);
      if (show) setState({ phase: "syncing", total: waiting.length, sent, conflicts, failed: [...failed] });
    }
    writeVersions(versions);
    if (show) setState({ phase: "done", total: waiting.length, sent, conflicts, failed });
  })().finally(() => {
    flushing = null;
  });
  return flushing;
}

/** Put every refused change back to waiting and send it again (the notice's Retry). */
export async function retryFailed(store: CohortDb = db, fetchFn: Fetch = (...a) => fetch(...a)): Promise<void> {
  writeQueue(readQueue().map((p) => (p.status === "failed" ? { ...p, status: "pending" as const, reason: undefined, offline: true } : p)));
  await flushQueue(store, fetchFn, true);
}

/** The changes that were refused and still wait for a Retry. */
export function failedChanges(): { what: string; reason: string }[] {
  return readQueue().filter((p) => p.status === "failed").map((p) => ({ what: whatOf(p), reason: p.reason ?? "" }));
}

export interface Conflict {
  id: number;
  collection: string;
  doc_id: string;
  at: string;
  data: unknown; // the version that a later write replaced
}

/** The versions of her documents that a later write replaced (a short list), newest first. */
export async function listConflicts(fetchFn: Fetch = (...a) => fetch(...a)): Promise<Conflict[]> {
  if (!isOnline() || !getUser()) return [];
  try {
    const res = await fetchFn(`${API_BASE}/api/store/conflicts`, { headers: headers() });
    return res.ok ? ((await res.json()) as Conflict[]) : [];
  } catch {
    return [];
  }
}

export async function dismissConflict(id: number, fetchFn: Fetch = (...a) => fetch(...a)): Promise<void> {
  try {
    await fetchFn(`${API_BASE}/api/store/conflicts/${id}`, { method: "DELETE", headers: headers() });
  } catch {
    /* offline: still listed next time */
  }
}

type Everything = Record<SyncedTable, Record<string, unknown>>;

const stable = (v: unknown): string => JSON.stringify(v, (_k, x: unknown) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.entries(x as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b))) : x));

/** True when the cache already holds exactly what the cloud holds (and nothing waits to go up). */
async function sameAsCache(store: CohortDb, cloud: Everything): Promise<boolean> {
  if (readQueue().length > 0) return false;
  for (const t of SYNCED) {
    const table = store.table(t);
    const pk = table.schema.primKey.name;
    const local = new Map((await table.toArray()).map((r: Record<string, unknown>) => [String(r[pk]), stable(r)]));
    const docs = Object.values(cloud[t] ?? {}) as Record<string, unknown>[];
    if (docs.length !== local.size) return false;
    for (const d of docs) if (local.get(String(d[pk])) !== stable(d)) return false;
  }
  return true;
}

/** Remember the server's version of each document, so the next write says what it was based on. */
async function readCloudVersions(fetchFn: Fetch): Promise<void> {
  try {
    const res = await fetchFn(`${API_BASE}/api/store/versions`, { headers: headers() });
    if (!res.ok) return;
    const all = (await res.json()) as Record<string, Record<string, unknown>>;
    const mine = readVersions();
    const waiting = new Set(readQueue().map((p) => vkey(p.table, p.id)));
    for (const t of SYNCED) {
      for (const [id, v] of Object.entries(all[t] ?? {})) {
        if (typeof v === "number" && !waiting.has(vkey(t, id))) mine[vkey(t, id)] = v;
      }
    }
    writeVersions(mine);
  } catch {
    /* versions are an aid: without them a write simply carries no base version */
  }
}

/**
 * Read everything from the server into the cache. Anything this phone changed offline is sent first. A phone
 * that already holds data the server has never seen (it was used before the cloud copy existed) sends it up
 * instead of being wiped. Offline, or if the server cannot be reached, the cache is left as it is.
 */
export async function hydrate(store: CohortDb = db, fetchFn: Fetch = (...a) => fetch(...a)): Promise<"synced" | "same" | "offline"> {
  if (!isOnline()) return "offline";
  try {
    if (!getUser()) return "offline"; // not signed in: nothing to read yet
    await claimCache(store);
    await flushQueue(store, fetchFn, true); // changes left from an offline spell go first, with the notice
    const res = await fetchFn(`${API_BASE}/api/store`, { headers: headers() });
    if (!res.ok) return "offline";
    const cloud = (await res.json()) as Everything;
    const cloudEmpty = SYNCED.every((t) => Object.keys(cloud[t] ?? {}).length === 0);
    const cameIn = await mergeTranscripts(store, (cloud as unknown as { transcripts?: Record<string, unknown> }).transcripts);
    if (cloudEmpty) {
      for (const t of SYNCED) {
        for (const row of (await store.table(t).toArray()) as { id?: string; key?: string }[]) mark(t, t === "settings" ? row.key : row.id);
      }
      await flushQueue(store, fetchFn);
      return "synced";
    }
    await readCloudVersions(fetchFn);
    if (await sameAsCache(store, cloud)) return cameIn > 0 ? "synced" : "same"; // nothing to refill: the screen is left as it is (she may be typing)
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

/** Delete everything the server holds for this phone (the "clear this phone" action). */
export async function clearCloud(fetchFn: Fetch = (...a) => fetch(...a)): Promise<void> {
  writeQueue([]);
  writeVersions({});
  if (!isOnline()) return;
  try {
    await fetchFn(`${API_BASE}/api/store`, { method: "DELETE", headers: headers() });
  } catch {
    /* offline: nothing to delete there yet */
  }
}
