import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { CohortDb } from "./db";
import { listChecks } from "./history";
import { saveObservation, sendPendingObservations } from "./observation";

let n = 0;
const fresh = () => new CohortDb(`hist-${n++}`);
const row = (term: number, kids: number, extra: object = {}) => ({
  id: `c-1:${term}`,
  classId: "c-1",
  term,
  formKey: "A",
  children: Array.from({ length: kids }, () => Array.from({ length: 10 }, () => "5")),
  updatedAt: term * 1000,
  ...extra,
});
const profile = (term: number) => ({ id: `c-1:${term}`, classId: "c-1", term, formKey: "A", childrenChecked: 3, counts: {}, eligible: [], track: null, anchorWrongCount: 0, untracked: {}, simulated: false, createdAt: 1 });

describe("the check history", () => {
  it("lists every check newest first with its children, photo count and send state", async () => {
    const s = fresh();
    await s.checks.put(row(1, 3, { viaPhoto: [0, 2] }));
    await s.checks.put(row(2, 2));
    await s.checks.put(row(3, 1));
    await s.profiles.put(profile(1));
    await s.profiles.put(profile(2));
    await s.syncQueue.add({ kind: "profile", classId: "c-1", payload: { term: "T2" }, createdAt: 1, tries: 0 });
    const list = await listChecks(s);
    expect(list.map((c) => c.id)).toEqual(["c-1:3", "c-1:2", "c-1:1"]); // newest first, by date saved
    expect(list.find((c) => c.id === "c-1:1")).toMatchObject({ children: 3, viaPhoto: 2, state: "sent" });
    expect(list.find((c) => c.id === "c-1:2")).toMatchObject({ children: 2, viaPhoto: 0, state: "waiting" });
    expect(list.find((c) => c.id === "c-1:3")?.state).toBe("open");
  });

  it("does not count a child with nothing written", async () => {
    const s = fresh();
    await s.checks.put({ ...row(1, 2), children: [Array(10).fill("5"), Array(10).fill("")] });
    expect((await listChecks(s))[0]?.children).toBe(1);
  });
});

describe("the classroom observation", () => {
  const turns = [{ turn: 1, teacher: "x", child: "y", speaker: "Priya" }];
  it("is kept on the phone, and sent as choices only when online", async () => {
    const s = fresh();
    const id = await s.transcripts.add({ classId: "c", createdAt: 1, turns, scenario: "SUB-SFL", language: "hi" });
    let body = "";
    const ok = (async (_u: string, init: RequestInit) => {
      body = String(init.body);
      return new Response("{}", { status: 200 });
    }) as unknown as typeof fetch;
    await saveObservation(id, { likeness: "some", differences: ["quieter", "too_easy"] }, true, s, ok);
    expect(JSON.parse(body)).toEqual({ scenario: "SUB-SFL", language: "hi", likeness: "some", differences: ["quieter", "too_easy"] });
    expect((await s.transcripts.get(id))?.observation).toMatchObject({ likeness: "some", sent: true });
  });

  it("waits while offline and goes out on the next try, once", async () => {
    const s = fresh();
    const id = await s.transcripts.add({ classId: "c", createdAt: 1, turns, scenario: "SUB-SFL", language: "en" });
    let calls = 0;
    const ok = (async () => {
      calls += 1;
      return new Response("{}", { status: 200 });
    }) as unknown as typeof fetch;
    await saveObservation(id, { likeness: "like", differences: [] }, false, s, ok);
    expect(calls).toBe(0);
    expect((await s.transcripts.get(id))?.observation?.sent).toBe(false);
    expect(await sendPendingObservations(true, s, ok)).toBe(1);
    expect(await sendPendingObservations(true, s, ok)).toBe(0);
    expect(calls).toBe(1);
  });
});
