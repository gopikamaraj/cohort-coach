import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchMissingPaperKeys } from "./check";
import { db } from "./db";
import { formOf, keys } from "./diagnosis";
import { registeredForm } from "./paperKeys";

// A phone she signs in on has her checks (read from her account) but not the answer keys of the papers they used:
// those are kept per phone. Without the key the results and the answer map cannot be drawn.
describe("the answer keys a second device lacks", () => {
  beforeEach(async () => {
    const mem = new Map<string, string>();
    mem.set("cc.user", JSON.stringify({ id: "priya", nickname: "priya" }));
    vi.stubGlobal("localStorage", { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v), removeItem: (k: string) => void mem.delete(k), clear: () => mem.clear() });
    vi.stubGlobal("navigator", { onLine: true });
    await db.checks.clear();
  });

  it("fetches the key of each paper her checks used, once, and leaves built-in forms and known papers alone", async () => {
    const asked: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      asked.push(new URL(url, "http://x").pathname);
      const id = /\/papers\/([^/]+)\/key/.exec(url)?.[1] ?? "";
      return { ok: true, status: 200, json: async () => ({ forms: { [id]: keys.forms["A"] } }) } as unknown as Response;
    });
    const base = { classId: "c-1", term: 1, children: [], updatedAt: 1 };
    await db.checks.bulkPut([
      { ...base, id: "c-1:1", formKey: "P-aaaaaaaaaaaa" },
      { ...base, id: "c-1:2", formKey: "A" }, // a built-in form: nothing to fetch
      { ...base, id: "c-1:3", formKey: "P-bbbbbbbbbbbb" },
    ] as never);
    expect(formOf("P-aaaaaaaaaaaa")).toBeUndefined();
    expect(await fetchMissingPaperKeys(db)).toBe(2);
    expect(registeredForm("P-aaaaaaaaaaaa")?.items.length).toBe(10);
    expect(formOf("P-bbbbbbbbbbbb")?.items.length).toBe(10);
    expect(asked.sort()).toEqual(["/api/paper-hub/papers/P-aaaaaaaaaaaa/key", "/api/paper-hub/papers/P-bbbbbbbbbbbb/key"]);
    expect(await fetchMissingPaperKeys(db)).toBe(0); // both are known now: no second request
    expect(asked).toHaveLength(2);
  });

  it("does not stop when one key cannot be fetched (offline or refused): the rest are tried and the screen still opens", async () => {
    vi.stubGlobal("fetch", async (url: string) => {
      if (url.includes("P-cccccccccccc")) throw new TypeError("no connection");
      const id = /\/papers\/([^/]+)\/key/.exec(url)?.[1] ?? "";
      return { ok: true, status: 200, json: async () => ({ forms: { [id]: keys.forms["A"] } }) } as unknown as Response;
    });
    const base = { classId: "c-1", term: 1, children: [], updatedAt: 1 };
    await db.checks.bulkPut([{ ...base, id: "c-1:1", formKey: "P-cccccccccccc" }, { ...base, id: "c-1:2", formKey: "P-dddddddddddd" }] as never);
    expect(await fetchMissingPaperKeys(db)).toBe(1);
    expect(formOf("P-cccccccccccc")).toBeUndefined();
    expect(formOf("P-dddddddddddd")).toBeDefined();
  });
});
