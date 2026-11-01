import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { CohortDb } from "./db";
import { deleteAllSessions, deleteSession, impactCounts, listSessions, moveCounts, setImpact, turnsOf } from "./review";

let n = 0;
const fresh = () => new CohortDb(`review-${n++}`);
const turn = (i: number, move?: string) => ({ turn: i, teacher: `line ${i}`, child: "ok", speaker: "Priya", ...(move ? { move } : {}) });

describe("recorded rehearsals", () => {
  it("lists only rehearsals that have turns, newest first", async () => {
    const store = fresh();
    await store.transcripts.add({ classId: "c", createdAt: 100, turns: [turn(1)] });
    await store.transcripts.add({ classId: "c", createdAt: 300, turns: [turn(1), turn(2)] });
    await store.transcripts.add({ classId: "c", createdAt: 200, turns: [] }); // started, nothing said
    const rows = await listSessions(store);
    expect(rows.map((r) => r.createdAt)).toEqual([300, 100]);
    expect(turnsOf(rows[0]!)).toHaveLength(2);
  });

  it("stores her tag on the phone, lets her change or clear it, and deletes one or all", async () => {
    const store = fresh();
    const a = await store.transcripts.add({ classId: "c", createdAt: 1, turns: [turn(1)] });
    const b = await store.transcripts.add({ classId: "c", createdAt: 2, turns: [turn(1)] });
    await setImpact(a, "positive", store);
    expect((await store.transcripts.get(a))?.impact).toBe("positive");
    await setImpact(a, "negative", store);
    expect((await store.transcripts.get(a))?.impact).toBe("negative");
    await setImpact(a, undefined, store);
    expect((await store.transcripts.get(a))?.impact).toBeUndefined();
    await deleteSession(a, store);
    expect(await store.transcripts.get(a)).toBeUndefined();
    expect(await store.transcripts.get(b)).toBeDefined();
    await deleteAllSessions(store);
    expect(await store.transcripts.count()).toBe(0);
  });
});

describe("summaries are counts, never percentages", () => {
  it("counts tags, with untagged rehearsals kept apart", () => {
    expect(impactCounts([{ impact: "positive" }, { impact: "positive" }, { impact: "none" }, { impact: "negative" }, {}])).toEqual({
      positive: 2,
      none: 1,
      negative: 1,
      untagged: 1,
    });
  });
  it("counts the moves she used, most used first, and skips turns with no move", () => {
    const turns = [turn(1, "Asks to explain"), turn(2, "Shows bundles"), turn(3, "Asks to explain"), turn(4)];
    expect(moveCounts(turns)).toEqual([
      ["Asks to explain", 2],
      ["Shows bundles", 1],
    ]);
  });
});
