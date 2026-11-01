import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { buildCards } from "./cards";
import { diagnoseAll, enteredChildren, finishCheck, profileRow, readCell } from "./check";
import { activeClass, clearPhone, CohortDb, getSetting, setSetting } from "./db";
import { DEMO_COUNTS, demoChildren } from "./demo";
import { classProfile } from "./diagnosis";
import { enqueueProfile, flush, pendingCount, PROFILE_PAYLOAD_KEYS, profilePayload } from "./sync";

let n = 0;
const fresh = () => new CohortDb(`test-${n++}`);

function walk(value: unknown, visit: (v: unknown) => void): void {
  visit(value);
  if (value && typeof value === "object") for (const v of Object.values(value)) walk(v, visit);
}

describe("reading her cells", () => {
  it("maps blank, unreadable and digits", () => {
    expect(readCell("")).toBe("blank");
    expect(readCell("_")).toBe("blank");
    expect(readCell("?")).toBe("unreadable");
    expect(readCell("37")).toBe(37);
    expect(readCell("३७")).toBe(37);
  });

  it("ignores the empty row that Next child opens", () => {
    expect(enteredChildren([["1", "", ""], ["", "", ""]])).toHaveLength(1);
  });
});

describe("the simulated class", () => {
  it("has 28 children and diagnoses back to the planned counts, term 1 and term 2", () => {
    for (const term of [1, 2]) {
      const rows = demoChildren(term);
      expect(rows).toHaveLength(28);
      const profile = classProfile(diagnoseAll("A", rows));
      expect(profile.children_checked).toBe(28);
      for (const [code, planned] of Object.entries(DEMO_COUNTS[term] as Record<string, number>)) {
        expect(profile.counts[code], `term ${term} ${code}`).toBe(planned);
      }
      expect(profile.counts["PV-REVERSE"]).toBe(0);
      expect(profile.untracked["ADD-WHOLE-ONES"]).toBe(2);
      expect(profile.anchor_wrong_count).toBe(1);
    }
  });

  it("chooses SUB-SFL as the focus in term 1", () => {
    const profile = classProfile(diagnoseAll("A", demoChildren(1)));
    expect(profile.track).toBe("SUB-SFL");
    expect(profile.eligible).toEqual(["SUB-SFL"]);
  });
});

describe("error cards", () => {
  const row = profileRow("sim-1", 1, "A", demoChildren(1), true);
  const view = buildCards(row, demoChildren(1));

  it("lists the errors by count with the focus marked, as counts", () => {
    expect(view.cards.map((c) => [c.code, c.count, c.total, c.isFocus])).toEqual([
      ["SUB-SFL", 11, 28, true],
      ["ADD-NOCARRY", 5, 28, false],
      ["SUB-NODEC", 3, 28, false],
      ["PV-HEARD", 2, 28, false],
    ]);
    expect(view.untracked).toBe(2);
    expect(view.anchorWrong).toBe(1);
    expect(view.tooSmall).toBe(false);
  });

  it("draws each example from her own class's answers", () => {
    const sfl = view.cards[0]!;
    expect(sfl.example).toMatch(/^\d+ − \d+ → \d+$/);
    expect(view.cards[1]!.example).toMatch(/^\d+ \+ \d+ → \d+$/);
    expect(view.cards[3]!.example).toMatch(/^\d+ → \d+$/);
  });

  it("has no example when the answers are not on this phone", () => {
    expect(buildCards(row, null).cards.every((c) => c.example === null)).toBe(true);
  });

  it("never holds a percentage anywhere in the view", () => {
    expect(JSON.stringify(view)).not.toMatch(/%|prevalence/i);
  });

  it("chooses no focus and says so for a class under the minimum", () => {
    const small = buildCards(profileRow("c-1", 1, "A", demoChildren(1).slice(0, 5), false), null);
    expect(small.tooSmall).toBe(true);
    expect(small.focus).toBeNull();
  });
});

describe("the sync payload is counts only", () => {
  it("has exactly the allowed keys and no arrays or per-child fields", () => {
    const row = profileRow("sim-1", 1, "A", demoChildren(1), true);
    const payload = profilePayload(row);
    expect(Object.keys(payload).sort()).toEqual([...PROFILE_PAYLOAD_KEYS].sort());
    walk(payload, (v) => {
      expect(Array.isArray(v)).toBe(false);
      expect(typeof v === "number" || typeof v === "string" || typeof v === "boolean" || typeof v === "object").toBe(true);
    });
    expect(payload.term).toBe("T1");
    expect(payload.counts["SUB-SFL"]).toBe(11);
  });

  it("is small: one class result is under 2 KB, the design target", () => {
    const bytes = new TextEncoder().encode(JSON.stringify(profilePayload(profileRow("c-1", 1, "A", demoChildren(1), true)))).length;
    expect(bytes).toBeLessThan(2048);
  });

  it("does not carry a child's raw answers, however the class is entered", () => {
    const rows = [["346", "728", "47", "52", "999", "1", "2", "3", "4", "5"]];
    const text = JSON.stringify(profilePayload(profileRow("c-1", 1, "A", rows, false)));
    for (const cell of rows[0]!) expect(text).not.toContain(`"${cell}"`);
    expect(Object.keys(JSON.parse(text)).sort()).toEqual([...PROFILE_PAYLOAD_KEYS].sort());
  });
});

describe("the device store and the queue", () => {
  it("finishing a check stores the class result and queues one counts-only payload", async () => {
    const store = fresh();
    const klass = await activeClass(true, store);
    await store.checks.put({ id: `${klass.id}:1`, classId: klass.id, term: 1, formKey: "A", children: demoChildren(1), updatedAt: 0 });
    const profile = await finishCheck(klass.id, 1, "A", demoChildren(1), true, store);
    expect(profile.counts["SUB-SFL"]).toBe(11);
    expect(await pendingCount(store)).toBe(1);
    const queued = (await store.syncQueue.toArray())[0]!;
    walk(queued.payload, (v) => expect(Array.isArray(v)).toBe(false));
    // The per-child answers are in `checks` and nowhere in the queue or the profile row.
    expect(JSON.stringify(queued)).not.toContain(demoChildren(1)[0]!.join(","));
    expect(Object.keys(await store.profiles.get(profile.id) ?? {})).not.toContain("children");
  });

  it("replaces a waiting result for the same class and term", async () => {
    const store = fresh();
    const a = profileRow("c-1", 1, "A", demoChildren(1), false);
    await enqueueProfile(a, store);
    await enqueueProfile({ ...a, counts: { ...a.counts, "SUB-SFL": 10 } }, store);
    expect(await pendingCount(store)).toBe(1);
    expect((await store.syncQueue.toArray())[0]!.payload["counts"]).toMatchObject({ "SUB-SFL": 10 });
    await enqueueProfile({ ...a, term: 2 }, store); // another term queues separately
    expect(await pendingCount(store)).toBe(2);
  });

  it("sends nothing while offline, then sends and clears when online", async () => {
    const store = fresh();
    await enqueueProfile(profileRow("c-1", 1, "A", demoChildren(1), false), store);
    const calls: { url: string; body: string }[] = [];
    const ok = (async (url: string, init: RequestInit) => {
      calls.push({ url, body: String(init.body) });
      return new Response("{}", { status: 200 });
    }) as unknown as typeof fetch;
    expect(await flush(false, store, ok)).toEqual({ sent: 0, failed: 0 });
    expect(calls).toHaveLength(0);
    expect(await flush(true, store, ok)).toEqual({ sent: 1, failed: 0 });
    expect(calls[0]!.url).toBe("/api/classes/c-1/profile");
    expect(Object.keys(JSON.parse(calls[0]!.body)).sort()).toEqual([...PROFILE_PAYLOAD_KEYS].sort());
    expect(await pendingCount(store)).toBe(0);
  });

  it("keeps a result that failed to send, and drops one the server will never accept", async () => {
    const store = fresh();
    await enqueueProfile(profileRow("c-1", 1, "A", demoChildren(1), false), store);
    const down = (async () => new Response("", { status: 503 })) as unknown as typeof fetch;
    expect(await flush(true, store, down)).toEqual({ sent: 0, failed: 1 });
    expect((await store.syncQueue.toArray())[0]!.tries).toBe(1);
    const boom = (async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    await flush(true, store, boom);
    expect((await store.syncQueue.toArray())[0]!.tries).toBe(2);
    const reject = (async () => new Response("", { status: 422 })) as unknown as typeof fetch;
    await flush(true, store, reject);
    expect(await pendingCount(store)).toBe(0);
  });

  it("keeps settings and clears the whole phone", async () => {
    const store = fresh();
    await setSetting("term", 2, store);
    expect(await getSetting("term", 1, store)).toBe(2);
    await activeClass(false, store);
    await clearPhone(store);
    expect(await getSetting("term", 1, store)).toBe(1);
    expect(await store.classes.count()).toBe(0);
  });
});
