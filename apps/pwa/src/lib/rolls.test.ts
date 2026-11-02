import { describe, expect, it } from "vitest";
import { afterApprove, canApprove, conceptQuestions, countRolls, dataState, finishGate, formatQuestions, isApproved, listRolls, nextToApprove, optionKey, withoutApproval, type RollSet } from "./rolls";

const E = ["", "", ""];
const A = ["1", "2", "3"];
function rs(rows: string[][], absent: number[] = [], approved: number[] = []): RollSet {
  return { rows, absent: new Set(absent), approved: new Set(approved) };
}

describe("roll state and option text", () => {
  it("covers every row of the table", () => {
    const set = rs([E, A, A, E], [3], [2]);
    expect(optionKey(set, 0)).toBe("check.opt_not_entered");
    expect(optionKey(set, 1)).toBe("check.opt_entered_not_approved");
    expect(optionKey(set, 2)).toBe("check.opt_entered_approved");
    expect(optionKey(set, 3)).toBe("check.opt_absent");
    expect(optionKey(set, 1, true)).toBe("check.opt_awaiting_check");
    expect(optionKey(set, 2, true)).toBe("check.opt_entered_approved");
  });
  it("absent is approved automatically; not entered is not approved", () => {
    const set = rs([E, E], [0]);
    expect(isApproved(set, 0)).toBe(true);
    expect(isApproved(set, 1)).toBe(false);
  });
  it("a stale approval on a roll that was emptied does not count", () => {
    expect(dataState(rs([E], [], [0]), 0)).toBe("not_entered");
    expect(isApproved(rs([E], [], [0]), 0)).toBe(false);
  });
  it("any edit sets an approved roll back", () => {
    expect([...withoutApproval(new Set([1, 2]), 1)]).toEqual([2]);
    expect(canApprove(rs([A], [], []), 0)).toBe(true);
    expect(canApprove(rs([A], [], [0]), 0)).toBe(false);
  });
});

describe("counts and moving on", () => {
  it("counts every roll up to the class size", () => {
    const c = countRolls(rs([A, A, A, E], [3], [0]), 7);
    expect(c).toMatchObject({ entered: 3, approved: 1, absent: 1, notEntered: 3, toApprove: 2, total: 7 });
  });
  it("Approve goes to the next roll to approve, then the next not entered", () => {
    const set = rs([A, A, E, A], [], [0]);
    expect(nextToApprove(set, 0, null)).toBe(1);
    expect(afterApprove(rs([A, A, E], [], [0, 1]), 1, null)).toBe(2);
    expect(afterApprove(rs([A], [], [0]), 0, null)).toBe(0);
  });
});

describe("finish gate", () => {
  it("nothing entered", () => {
    const g = finishGate(rs([E, E]), 2);
    expect(g.enabled).toBe(false);
    expect(g.notes).toEqual([{ kind: "none_entered" }]);
  });
  it("names rolls not entered and not approved, and caps at 8", () => {
    const rows = Array.from({ length: 14 }, (_, i) => (i < 2 ? A : E));
    const g = finishGate(rs(rows, [], [0]), 14);
    expect(g.enabled).toBe(false);
    expect(g.notes[0]).toMatchObject({ kind: "not_entered", rolls: [3, 4, 5, 6, 7, 8, 9, 10], more: 4 });
    expect(g.notes[1]).toMatchObject({ kind: "not_approved", rolls: [2], more: 0 });
  });
  it("enabled only when all are approved or absent, with at least one entered and approved", () => {
    expect(finishGate(rs([A, E], [1], [0]), 2).enabled).toBe(true);
    expect(finishGate(rs([E, E], [0, 1]), 2).enabled).toBe(false); // all absent: nothing to count
    const ready = finishGate(rs([A, A], [], [0, 1]), 2);
    expect(ready.notes).toEqual([{ kind: "ready", total: 2 }]);
    expect(ready).toMatchObject({ entered: 2, absent: 0 });
  });
  it("lists rolls with the language's and", () => {
    expect(listRolls([4, 9, 12], 0, "and", (n) => `${n} more`)).toBe("4, 9 and 12");
    expect(listRolls([1, 2], 3, "and", (n) => `${n} more`)).toBe("1, 2 and 3 more");
    expect(listRolls([5], 0, "and", () => "")).toBe("5");
  });
});

describe("checkbox question numbers come from the paper", () => {
  const ten = [
    ["PV-HEARD", "PV-REVERSE"], ["PV-HEARD", "PV-REVERSE"], ["ADD-NOCARRY"], ["ADD-NOCARRY"], ["ADD-NOCARRY"], [],
    ["SUB-SFL", "SUB-NODEC"], ["SUB-SFL"], ["SUB-SFL"], ["SUB-SFL"],
  ].map((probes, i) => ({ n: i + 1, probes }));
  it("10 items", () => {
    const out = conceptQuestions(ten).map((c) => [c.concept, formatQuestions(c.questions, "and")]);
    expect(out).toEqual([["addition", "3–5"], ["place_value", "1–2"], ["subtraction", "7–10"]]);
  });
  it("15 items", () => {
    const fifteen = [...ten, { n: 11, probes: ["ADD-NOCARRY"] }, { n: 12, probes: [] }, { n: 13, probes: [] }, { n: 14, probes: ["SUB-SFL"] }, { n: 15, probes: ["SUB-SFL"] }];
    const out = Object.fromEntries(conceptQuestions(fifteen).map((c) => [c.concept, formatQuestions(c.questions, "and")]));
    expect(out).toEqual({ addition: "3–5 and 11", place_value: "1–2", subtraction: "7–10 and 14–15" });
  });
  it("omits a concept the paper does not have", () => {
    expect(conceptQuestions([{ n: 1, probes: ["ADD-NOCARRY"] }]).map((c) => c.concept)).toEqual(["addition"]);
  });
});
