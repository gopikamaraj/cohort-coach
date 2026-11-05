import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { closeSyncNotice, failedChanges, flushQueue, hydrate, queued, retryFailed, syncState, watchTables, writeOrQueue } from "./cloudStore";
import { CohortDb } from "./db";

// A fake server that answers each request from a script, and records what it was sent.
interface Sent {
  method: string;
  path: string;
  body: Record<string, unknown> | null;
}
function setup(answer: (s: Sent) => { status: number; json?: unknown } | "down") {
  const mem = new Map<string, string>();
  mem.set("cc.user", JSON.stringify({ id: "priya", nickname: "Priya" }));
  mem.set("cc.cacheOwner", "priya");
  vi.stubGlobal("localStorage", { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v), removeItem: (k: string) => void mem.delete(k) });
  vi.stubGlobal("navigator", { onLine: true });
  vi.stubGlobal("window", { addEventListener: () => undefined });
  const sent: Sent[] = [];
  const fetchFn = (async (url: string, init?: RequestInit) => {
    const s: Sent = { method: init?.method ?? "GET", path: new URL(url, "http://x").pathname, body: init?.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : null };
    sent.push(s);
    const out = answer(s);
    if (out === "down") throw new TypeError("no connection");
    const res = { ok: out.status < 400, status: out.status, json: async () => out.json ?? {}, clone: () => res };
    return res as unknown as Response;
  }) as typeof fetch;
  return { sent, fetchFn, mem };
}

let n = 0;
const fresh = () => new CohortDb(`outbox-${n++}`);
const klass = { id: "c-1", name: "3A", simulated: false, createdAt: 1 };

describe("the outbox", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    closeSyncNotice();
  });

  it("sends the version a row was based on, and remembers the version the server gives back", async () => {
    let version = 4;
    const { sent, fetchFn } = setup((s) => (s.method === "PUT" ? { status: 200, json: { ok: true, version: ++version, conflict: false } } : { status: 200, json: {} }));
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await flushQueue(db, fetchFn);
    expect(sent[0]?.body).not.toHaveProperty("base_version"); // nothing read yet: no base
    await db.classes.update("c-1", { name: "3B" });
    await flushQueue(db, fetchFn);
    expect(sent[1]?.body?.["base_version"]).toBe(5); // the version the first write returned
  });

  it("keeps a refused change listed with the server's reason instead of dropping it", async () => {
    const { fetchFn } = setup(() => ({ status: 413, json: { detail: "This document is too large." } }));
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await flushQueue(db, fetchFn);
    expect(queued()).toBe(1); // still there
    expect(failedChanges()).toEqual([{ what: "classes c-1", reason: "This document is too large." }]);
  });

  it("a refused change goes again when she presses Retry, and leaves the list once saved", async () => {
    let refuse = true;
    const { fetchFn } = setup(() => (refuse ? { status: 422, json: { detail: "Bad document." } } : { status: 200, json: { ok: true, version: 1 } }));
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await flushQueue(db, fetchFn);
    refuse = false;
    await retryFailed(db, fetchFn);
    expect(queued()).toBe(0);
    expect(syncState().phase).toBe("done");
    expect(syncState().sent).toBe(1);
  });

  it("a server error leaves the change waiting (not failed) and stops, so the rest keep their order", async () => {
    const { sent, fetchFn } = setup(() => ({ status: 503 }));
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await db.settings.put({ key: "lang", value: "ta" });
    await flushQueue(db, fetchFn);
    expect(sent.length).toBe(1); // it stopped at the first
    expect(queued()).toBe(2);
    expect(failedChanges()).toEqual([]);
  });

  it("announces how many changes were made offline, then the result, only when asked", async () => {
    const { fetchFn } = setup(() => ({ status: 200, json: { ok: true, version: 1 } }));
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await db.settings.put({ key: "lang", value: "hi" });
    await flushQueue(db, fetchFn); // a normal save while online: no notice
    expect(syncState().phase).toBe("idle");
    vi.stubGlobal("navigator", { onLine: false }); // the two changes are made with no connection
    await db.classes.update("c-1", { name: "3C" });
    await db.settings.put({ key: "lang", value: "ta" });
    vi.stubGlobal("navigator", { onLine: true });
    await flushQueue(db, fetchFn, true); // the connection came back with two changes waiting
    expect(syncState()).toMatchObject({ phase: "done", total: 2, sent: 2, failed: [] });
    closeSyncNotice();
    expect(syncState().phase).toBe("idle");
  });

  it("counts a write that replaced a newer version from another device", async () => {
    const { fetchFn } = setup(() => ({ status: 200, json: { ok: true, version: 3, conflict: true } }));
    const db = fresh();
    watchTables(db);
    vi.stubGlobal("navigator", { onLine: false });
    await db.classes.put(klass);
    vi.stubGlobal("navigator", { onLine: true });
    await flushQueue(db, fetchFn, true);
    expect(syncState().conflicts).toBe(1);
  });

  it("queues a plain write (a module's feedback) when offline, and sends it later", async () => {
    let down = true;
    const { sent, fetchFn } = setup(() => (down ? "down" : { status: 200, json: { ok: true } }));
    const out = await writeOrQueue("module 2 feedback", "POST", "/api/modules/tracks/t1/modules/2/feedback", { answer: "worked", note: "" }, { "X-Role": "teacher" }, fetchFn);
    expect(out.result).toBe("queued");
    expect(queued()).toBe(1);
    down = false;
    await flushQueue(fresh(), fetchFn);
    expect(queued()).toBe(0);
    expect(sent.at(-1)).toMatchObject({ method: "POST", path: "/api/modules/tracks/t1/modules/2/feedback", body: { answer: "worked", note: "" } });
  });

  it("does not queue a plain write that the server refused: she is told", async () => {
    const { fetchFn } = setup(() => ({ status: 403, json: { detail: "That is not your track." } }));
    const out = await writeOrQueue("module 2 feedback", "POST", "/api/modules/tracks/t1/modules/2/feedback", {}, {}, fetchFn);
    expect(out).toEqual({ result: "refused", reason: "That is not your track." });
    expect(queued()).toBe(0);
  });

  it("keeps a refused change in the cache when the cache is refilled from the server", async () => {
    const { fetchFn } = setup((s) => (s.method === "PUT" ? { status: 422, json: { detail: "no" } } : { status: 200, json: { classes: {}, checks: {}, profiles: {}, settings: { x: { key: "x", value: 1 } } } }));
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await flushQueue(db, fetchFn);
    await hydrate(db, fetchFn);
    expect(await db.classes.get("c-1")).toBeDefined(); // not deleted while it is unsynced
    expect(await db.settings.get("x")).toBeDefined();
  });

  // Practice Class sessions (decided 4 Nov 2026): saved to her account, whole at each change, read only by her user id.
  const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

  it("sends a Practice Class session to her account whole, the newest copy replacing an older one still waiting", async () => {
    const { sent, fetchFn } = setup(() => ({ status: 200, json: { ok: true, version: 1 } }));
    vi.stubGlobal("fetch", fetchFn);
    const db = fresh();
    watchTables(db);
    vi.stubGlobal("navigator", { onLine: false }); // no signal while she rehearses
    const id = await db.transcripts.add({ classId: "c-1", createdAt: 1, turns: [], sessionId: "p-abc", scenario: "SUB-SFL", ended: false });
    await wait(600);
    await db.transcripts.update(id, { turns: [{ turn: 1, teacher: "Show it with bundles.", child: "403", speaker: "Asha" }] });
    await wait(600);
    expect(queued()).toBe(1); // one waiting copy, not one per change
    vi.stubGlobal("navigator", { onLine: true });
    await flushQueue(db, fetchFn);
    const put = sent.filter((x) => x.method === "PUT" && x.path === "/api/store/transcripts/p-abc");
    expect(put).toHaveLength(1);
    expect((put[0]?.body as { data: { turns: unknown[]; sessionId: string } }).data.turns).toHaveLength(1);
    expect((put[0]?.body as { data: Record<string, unknown> }).data).not.toHaveProperty("id"); // the phone's own row number stays here
  });

  it("removes a deleted session from her account too, and brings one made on another device onto this phone", async () => {
    const { sent, fetchFn } = setup((s) =>
      s.method === "GET"
        ? { status: 200, json: { classes: {}, checks: {}, profiles: {}, settings: {}, transcripts: { "p-other": { classId: "c-9", createdAt: 5, turns: [{ turn: 1, teacher: "Ask her to explain.", child: "34", speaker: "Ravi" }], sessionId: "p-other", ended: true } } } }
        : { status: 200, json: { ok: true, version: 1 } },
    );
    vi.stubGlobal("fetch", fetchFn);
    const db = fresh();
    watchTables(db);
    await hydrate(db, fetchFn);
    const row = (await db.transcripts.toArray()).find((r) => r.sessionId === "p-other");
    expect(row?.turns).toHaveLength(1); // a session made on the other device is here
    expect(sent.filter((x) => x.method === "PUT" && x.path.includes("transcripts/p-other"))).toHaveLength(0); // and was not sent back
    await db.transcripts.delete(row?.id as number);
    await wait(100);
    expect(sent.some((x) => x.method === "DELETE" && x.path === "/api/store/transcripts/p-other")).toBe(true);
  });
});
