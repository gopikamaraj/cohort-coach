import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { buildBackup, openBackup, restoreBackup, sealBackup } from "./backup";
import { addClass, deleteClass, listClasses, renameClass, setActive } from "./classes";
import { CONSENT_VERSION, getConsent, hasConsent, setConsent, withdrawAll, type KV } from "./consent";
import { CohortDb } from "./db";
import { costOf, getUsage, record, resetUsage } from "./meter";
import { persistenceStatus, requestPersistence } from "./storage";

let n = 0;
const fresh = () => new CohortDb(`profile-${n++}`);
const memory = (): KV => {
  const m = new Map<string, string>();
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, v), removeItem: (k) => void m.delete(k) };
};
const check = (classId: string, term = 1) => ({ id: `${classId}:${term}`, classId, term, formKey: "A", children: [["3", "4"]], updatedAt: 5 });

describe("persistent storage", () => {
  it("asks once, reports the answer, and survives a browser without the API", async () => {
    let asked = 0;
    const nav = { storage: { persist: async () => (asked += 1, true), persisted: async () => asked > 0, estimate: async () => ({ usage: 2048, quota: 1_000_000 }) } };
    expect(await requestPersistence(nav)).toBe(true);
    expect(await persistenceStatus(nav)).toEqual({ supported: true, persisted: true, usage: 2048, quota: 1_000_000 });
    expect(await requestPersistence({})).toBe(false);
    expect(await persistenceStatus({})).toEqual({ supported: false, persisted: false, usage: 0, quota: 0 });
  });
});

describe("multiple classes", () => {
  it("adds, renames, switches and deletes a class with all its data", async () => {
    const s = fresh();
    const a = await addClass("Class 3A", false, s);
    const b = await addClass("Class 3B", false, s);
    expect((await listClasses(s)).map((c) => c.name)).toEqual(["Class 3A", "Class 3B"]);
    expect((await listClasses(s)).find((c) => c.active)?.id).toBe(a.id); // the first one is active
    await setActive(b.id, s);
    expect((await listClasses(s)).find((c) => c.active)?.id).toBe(b.id);
    await renameClass(b.id, "  Grade 3 B  ", s);
    expect((await s.classes.get(b.id))?.name).toBe("Grade 3 B");
    await s.checks.put(check(a.id));
    await s.checks.put(check(b.id));
    await s.transcripts.add({ classId: b.id, createdAt: 1, turns: [] });
    await deleteClass(b.id, s, async () => true);
    expect(await s.checks.count()).toBe(1);
    expect(await s.transcripts.count()).toBe(0);
    expect((await listClasses(s)).find((c) => c.active)?.id).toBe(a.id); // falls back to a remaining class
  });
  it("refuses an empty name and caps the length", async () => {
    const s = fresh();
    await expect(addClass("   ", false, s)).rejects.toThrow();
    expect((await addClass("x".repeat(80), false, s)).name).toHaveLength(40);
  });
});

describe("export and restore", () => {
  it("round-trips classes, checks, profiles and rehearsals, never the photo outbox", async () => {
    const a = fresh();
    const c = await addClass("Class 3A", false, a);
    await a.checks.put(check(c.id));
    await a.transcripts.add({ classId: c.id, createdAt: 9, turns: [{ turn: 1 }], sessionId: "s1" });
    await a.outbox.add({ classId: c.id, createdAt: 1, photo: new Blob(["x"]) });
    const backup = await buildBackup(a);
    expect(JSON.stringify(backup)).not.toContain("outbox");
    const b = fresh();
    const res = await restoreBackup(backup, b);
    expect(res).toEqual({ classes: 1, checks: 1, transcripts: 1 });
    expect((await b.checks.get(`${c.id}:1`))?.children).toEqual([["3", "4"]]);
    expect((await b.transcripts.toArray())[0]?.sessionId).toBe("s1");
    expect(await restoreBackup(backup, b)).toEqual({ classes: 1, checks: 1, transcripts: 0 }); // no duplicate rehearsals
    expect(await b.transcripts.count()).toBe(1);
  });
  it("re-queues the class counts of restored checks that had been finished", async () => {
    const a = fresh();
    const c = await addClass("A", false, a);
    await a.profiles.put({ id: `${c.id}:1`, classId: c.id, term: 1, formKey: "A", childrenChecked: 1, counts: {}, eligible: [], track: null, anchorWrongCount: 0, untracked: {}, simulated: false, createdAt: 1 });
    const b = fresh();
    await restoreBackup(await buildBackup(a), b);
    expect(await b.profiles.count()).toBe(1);
    expect(await b.syncQueue.count()).toBe(0); // counts are only re-sent if she finishes the check again
  });
  it("can be sealed with a passphrase, and opens only with the right one", async () => {
    const backup = await buildBackup(fresh());
    const sealed = await sealBackup(backup, "correct horse");
    expect(sealed).not.toContain("classes");
    expect(await openBackup(sealed, "correct horse")).toEqual(backup);
    await expect(openBackup(sealed, "wrong")).rejects.toThrow();
    await expect(openBackup(sealed, "")).rejects.toThrow();
    expect(await openBackup(JSON.stringify(backup), "")).toEqual(backup); // a plain file needs none
  });
  it("refuses a hostile file: bad ids, wrong shapes, too many rows", async () => {
    const base = { format: "cohort-coach-backup", version: 1, exportedAt: 1, profiles: [], transcripts: [], settings: { activeClass: null, term: 1 } };
    const evil = { ...base, classes: [{ id: "../../admin", name: "x", simulated: false, createdAt: 1 }], checks: [] };
    await expect(restoreBackup(evil as never, fresh())).rejects.toThrow(/valid/);
    const s = fresh();
    const badCheck = { ...base, classes: [], checks: [{ id: "c-1234567890:1", classId: "c-1234567890", term: 1, formKey: "A", children: "nope", updatedAt: 1 }] };
    await expect(restoreBackup(badCheck as never, s)).rejects.toThrow(/valid/);
    expect(await s.checks.count()).toBe(0); // nothing was written
    const many = { ...base, classes: Array.from({ length: 20_001 }, () => ({ id: "c-1234567890", name: "x" })), checks: [] };
    await expect(restoreBackup(many as never, fresh())).rejects.toThrow(/valid/);
  });
  it("seals a large backup (no stack overflow) and records the iteration count", async () => {
    const big = { ...(await buildBackup(fresh())), classes: [], checks: [], transcripts: [], pad: "x".repeat(300_000) } as never;
    const sealed = await sealBackup(big, "pass");
    expect(JSON.parse(sealed).iterations).toBe(600_000);
    expect((await openBackup(sealed, "pass") as unknown as { pad: string }).pad).toHaveLength(300_000);
  });
  it("rejects files that are not a backup, or are from a newer version", async () => {
    await expect(restoreBackup({ format: "other" } as never, fresh())).rejects.toThrow();
    await expect(restoreBackup({ format: "cohort-coach-backup", version: 99 } as never, fresh())).rejects.toThrow();
    await expect(openBackup("not json", "")).rejects.toThrow();
  });
});

describe("data used", () => {
  it("adds up what was sent and received, converts to a cost only when she gives a price, and clears", () => {
    const kv = memory();
    record(1000, 3000, kv);
    record(500, 500, kv);
    expect(getUsage(kv)).toMatchObject({ sent: 1500, received: 3500 });
    expect(costOf(getUsage(kv), undefined)).toBeNull();
    expect(costOf({ sent: 500_000_000, received: 500_000_000, since: 0 }, 100)).toBeCloseTo(100, 5); // 1 GB at 100 per GB
    resetUsage(kv);
    expect(getUsage(kv)).toMatchObject({ sent: 0, received: 0 });
  });
});

describe("consent (DPDP)", () => {
  it("records what she agreed to, with a version and a time, and nothing is on by default", () => {
    const kv = memory();
    expect(getConsent(kv)).toBeNull();
    expect(hasConsent("counts", kv)).toBe(false);
    setConsent({ core: true, counts: true, practice_ai: false, share_rehearsal: false, feedback: true }, kv);
    expect(hasConsent("counts", kv)).toBe(true);
    expect(hasConsent("practice_ai", kv)).toBe(false);
    expect(getConsent(kv)).toMatchObject({ v: CONSENT_VERSION });
    withdrawAll(kv);
    expect(hasConsent("counts", kv)).toBe(false);
    expect(hasConsent("core", kv)).toBe(false);
  });
});
