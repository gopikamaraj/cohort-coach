import { describe, expect, it, vi } from "vitest";
import type { ProfileRow } from "./db";
import { coverageGrid, itemText, pcall, PaperError, profileFrom, type PaperItem } from "./papers";

const latest = { id: "c-1:1", classId: "c-1", term: 1, formKey: "A", childrenChecked: 18, counts: { "SUB-SFL": 9 }, eligible: [], track: null, anchorWrongCount: 0, untracked: {}, simulated: false, createdAt: 1 } as unknown as ProfileRow;

describe("the class profile sent for a paper", () => {
  it("ignores a past check of too few children and falls back to the intake form", () => {
    const few = { id: "c-1:1", counts: { "SUB-SFL": 1 }, childrenChecked: 1 } as never;
    const intake = { source: "intake", struggles: ["C3"] } as never;
    expect(profileFrom(few, intake)).toBe(intake);
    expect(profileFrom(few, null)).toEqual({ source: "baseline" });
  });

  it("uses the last check's class counts when there is one", () => {
    expect(profileFrom(latest, null)).toEqual({ source: "past", counts: { "SUB-SFL": 9 }, checked: 18, built_from: ["c-1:1"] });
  });
  it("falls back to the intake answers, then to the standard paper", () => {
    const intake = { source: "intake" as const, struggles: ["C3" as const], taught: ["C1" as const, "C3" as const] };
    expect(profileFrom(null, intake)).toBe(intake);
    expect(profileFrom(null, null)).toEqual({ source: "baseline" });
  });
  it("sends counts only: no child, row or answer", () => {
    const p = profileFrom(latest, null);
    expect(Object.keys(p).sort()).toEqual(["built_from", "checked", "counts", "source"]);
  });
});

describe("the coverage grid", () => {
  it("lists every error with the items that check it, and marks skills not on the paper", () => {
    const grid = coverageGrid({ coverage: { "PV-HEARD": [1, 2], "SUB-SFL": [7, 8, 9] }, items: [], not_assessed: ["C2"] });
    expect(grid.map((r) => r.code)).toEqual(["PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"]);
    expect(grid[0]).toMatchObject({ count: 2, assessed: true });
    expect(grid[2]).toMatchObject({ count: 0, assessed: false });
    expect([...(grid[3]?.items ?? [])]).toEqual([7, 8, 9]);
  });
});

describe("item text", () => {
  const base = { n: 1, slot: 1, template: "t", competency: "C1", section: "dictation", correct: 0, wrong: {}, untracked: {}, is_anchor: true, difficulty: null, twin_of: null };
  it("shows a dictation item as the number to say aloud", () => {
    expect(itemText({ ...base, operation: "dictate", a: 346, b: 0 } as PaperItem, "Say aloud")).toBe("Say aloud: 346");
  });
  it("shows sums with their sign", () => {
    expect(itemText({ ...base, operation: "subtract", a: 52, b: 29 } as PaperItem, "x")).toBe("52 − 29");
  });
});

describe("pcall", () => {
  it("sends the role and, in the demo, the person acting", async () => {
    const fetchFn = vi.fn(async () => new Response("{}", { status: 200 }));
    await pcall("/api/paper-rules/2/publish", "coach", { method: "POST", person: "b" }, fetchFn as unknown as typeof fetch);
    const init = (fetchFn.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(init.headers).toMatchObject({ "X-Role": "coach", "X-Demo-Person": "b" });
  });
  it("keeps the rule a refused paper broke", async () => {
    const body = JSON.stringify({ detail: { rule: "coverage", explanation: "nothing to check" } });
    const fetchFn = vi.fn(async () => new Response(body, { status: 422 }));
    const err = await pcall("/api/papers/generate", "teacher", { method: "POST", body: {} }, fetchFn as unknown as typeof fetch).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(PaperError);
    expect((err as PaperError).rule).toBe("coverage");
    expect((err as PaperError).explanation).toBe("nothing to check");
  });
});
