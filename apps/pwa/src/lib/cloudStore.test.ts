import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { clearCloud, flushQueue, hydrate, queued, watchTables } from "./cloudStore";
import { CohortDb } from "./db";

// A phone with a fake server: documents by collection and id, plus a switch for "no connection".
function setup() {
  const store = new Map<string, string>();
  store.set("cc.user", JSON.stringify({ id: "priya", nickname: "Priya" })); // she is signed in
  store.set("cc.cacheOwner", "priya");
  vi.stubGlobal("localStorage", { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v), removeItem: (k: string) => void store.delete(k) });
  vi.stubGlobal("navigator", { onLine: true });
  vi.stubGlobal("window", { addEventListener: () => undefined });
  const cloud: Record<string, Record<string, unknown>> = { classes: {}, checks: {}, profiles: {}, settings: {} };
  const calls: string[] = [];
  let down = false;
  const fetchFn = (async (url: string, init?: RequestInit) => {
    if (down) throw new TypeError("no connection");
    const path = new URL(url, "http://x").pathname;
    const method = init?.method ?? "GET";
    calls.push(`${method} ${path}`);
    const m = /\/api\/store\/(\w+)\/(.+)$/.exec(path);
    if (method === "PUT" && m) cloud[m[1] as string]![decodeURIComponent(m[2] as string)] = (JSON.parse(init?.body as string) as { data: unknown }).data;
    if (method === "DELETE" && m) delete cloud[m[1] as string]![decodeURIComponent(m[2] as string)];
    if (method === "DELETE" && !m) for (const k of Object.keys(cloud)) cloud[k] = {};
    return { ok: true, status: 200, json: async () => cloud } as Response;
  }) as typeof fetch;
  return { cloud, calls, fetchFn, offline: (v: boolean) => void (down = v) };
}

let n = 0;
const fresh = () => new CohortDb(`cloud-${n++}`);
const klass = { id: "c-1", name: "3A", simulated: false, createdAt: 1 };

describe("the cloud copy", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("writes a created, changed and deleted row to the server", async () => {
    const { cloud, fetchFn } = setup();
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await db.classes.update("c-1", { name: "3B" });
    expect(queued()).toBe(1); // one queued write per row, not one per change
    await flushQueue(db, fetchFn);
    expect(cloud.classes?.["c-1"]).toMatchObject({ name: "3B" });
    expect(queued()).toBe(0);
    await db.classes.delete("c-1");
    await flushQueue(db, fetchFn);
    expect(cloud.classes).toEqual({});
  });

  it("keeps a change made offline queued and sends it when the connection is back", async () => {
    const { cloud, fetchFn, offline } = setup();
    const db = fresh();
    watchTables(db);
    offline(true);
    await db.settings.put({ key: "term", value: 2 });
    await flushQueue(db, fetchFn);
    expect(queued()).toBe(1);
    expect(cloud.settings).toEqual({});
    offline(false);
    await flushQueue(db, fetchFn);
    expect(cloud.settings?.["term"]).toEqual({ key: "term", value: 2 });
  });

  it("reads everything back from the server, replacing the cache", async () => {
    const { cloud, fetchFn } = setup();
    cloud.checks = { "c-1:1": { id: "c-1:1", classId: "c-1", term: 1, children: [["3", "4"]] } };
    cloud.settings = { activeClass: { key: "activeClass", value: "c-1" } };
    const db = fresh();
    await db.classes.put({ ...klass, id: "stale" }); // a leftover that the server does not have
    expect(await hydrate(db, fetchFn)).toBe("synced");
    expect((await db.checks.toArray()).map((c) => c.id)).toEqual(["c-1:1"]);
    expect(await db.classes.count()).toBe(0);
    expect((await db.settings.get("activeClass"))?.value).toBe("c-1");
  });

  it("keeps a change that has not gone up yet when the cache is refilled from the server", async () => {
    const { cloud, fetchFn, offline } = setup();
    cloud.settings = { term: { key: "term", value: 1 }, activeClass: { key: "activeClass", value: "c-1" } };
    cloud.classes = { "c-1": klass };
    const db = fresh();
    watchTables(db);
    offline(true);
    await db.settings.put({ key: "term", value: 2 }); // she moved on to the next paper; the write is queued
    offline(false);
    cloud.settings["term"] = { key: "term", value: 1 }; // the server still has the old term when the read lands
    const flushed = flushQueue;
    void flushed; // (the queue is sent first by hydrate; here the send is held back by a failing server)
    const failing = (async (url: string, init?: RequestInit) => (init?.method === "PUT" ? ({ ok: false, status: 503 } as Response) : fetchFn(url, init))) as typeof fetch;
    await hydrate(db, failing);
    expect((await db.settings.get("term"))?.value).toBe(2);
    expect((await db.settings.get("activeClass"))?.value).toBe("c-1");
  });

  it("sends a phone's old data up when the server has none of it, instead of wiping it", async () => {
    const { cloud, fetchFn } = setup();
    const db = fresh();
    await db.classes.put(klass);
    await db.settings.put({ key: "term", value: 1 });
    expect(await hydrate(db, fetchFn)).toBe("synced");
    expect(cloud.classes?.["c-1"]).toBeDefined();
    expect(await db.classes.count()).toBe(1);
  });

  it("leaves the cache alone when it cannot reach the server", async () => {
    const { fetchFn, offline } = setup();
    const db = fresh();
    await db.classes.put(klass);
    offline(true);
    expect(await hydrate(db, fetchFn)).toBe("offline");
    expect(await db.classes.count()).toBe(1);
  });

  it("deletes the server copy on clear, and never stores rehearsals or photos", async () => {
    const { cloud, calls, fetchFn } = setup();
    cloud.classes = { "c-1": klass };
    await clearCloud(fetchFn);
    expect(cloud.classes).toEqual({});
    const db = fresh();
    watchTables(db);
    await db.transcripts.add({ classId: "c-1", createdAt: 1, turns: [] });
    await db.outbox.add({ classId: "c-1", createdAt: 1, photo: new Blob(["x"]) });
    await flushQueue(db, fetchFn);
    expect(calls.filter((c) => c.startsWith("PUT"))).toEqual([]);
  });
});

describe("the cache belongs to one user", () => {
  it("does nothing until someone is signed in", async () => {
    const { fetchFn, calls } = setup();
    localStorage.removeItem("cc.user");
    expect(await hydrate(fresh(), fetchFn)).toBe("offline");
    expect(calls).toEqual([]);
  });
  it("starts a different user from an empty cache, so one person's classes are never uploaded under another's nickname", async () => {
    const { cloud, fetchFn } = setup();
    const db = fresh();
    await db.classes.put(klass); // left on this browser by priya
    localStorage.setItem("cc.user", JSON.stringify({ id: "ravi", nickname: "Ravi" }));
    expect(await hydrate(db, fetchFn)).toBe("synced");
    expect(await db.classes.count()).toBe(0);
    expect(cloud.classes).toEqual({}); // nothing of priya's reached ravi's copy
  });
  it("keeps what the browser holds for the first user to sign in (it was made before nicknames were accounts)", async () => {
    const { cloud, fetchFn } = setup();
    localStorage.removeItem("cc.cacheOwner");
    const db = fresh();
    watchTables(db);
    await db.classes.put(klass);
    await hydrate(db, fetchFn);
    expect(cloud.classes?.["c-1"]).toMatchObject({ name: "3A" });
  });
});
