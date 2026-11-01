import { describe, expect, it } from "vitest";
import type { CheckRow } from "./db";
import { cohortStatus, enteredCount } from "./paperStatus";

const check = (over: Partial<CheckRow>): CheckRow => ({
  id: "c1:1",
  classId: "c1",
  term: 1,
  formKey: "A",
  children: [],
  updatedAt: 0,
  paperId: "P1",
  status: "entering",
  expectedChildren: 4,
  ...over,
});
const rows = (n: number, of = 4) => Array.from({ length: of }, (_, i) => (i < n ? ["12"] : [""]));

describe("cohortStatus", () => {
  it("says no check has used the paper, and points to Enter check", () => {
    expect(cohortStatus("P1", [], "waiting")).toMatchObject({ reason: "no_check", formed: false, action: "enter_check" });
    expect(cohortStatus("P1", [check({ paperId: "OTHER" })], "this_term").reason).toBe("no_check");
  });

  it("counts the sheets entered so far", () => {
    const s = cohortStatus("P1", [check({ children: rows(2) })], "waiting");
    expect(s).toMatchObject({ reason: "entering", entered: 2, expected: 4, action: "continue_check" });
  });

  it("counts an absent child as entered", () => {
    expect(enteredCount(check({ children: rows(2), absent: [2, 3] }))).toBe(4);
  });

  it("every sheet entered but not approved", () => {
    expect(cohortStatus("P1", [check({ children: rows(4) })], "waiting").reason).toBe("not_approved");
  });

  it("approved but not closed", () => {
    expect(cohortStatus("P1", [check({ children: rows(4), status: "approved" })], "waiting").reason).toBe("not_submitted");
  });

  it("closed and waiting for other classes", () => {
    const s = cohortStatus("P1", [check({ children: rows(4), status: "closed" })], "waiting");
    expect(s).toMatchObject({ reason: "waiting_others", formed: false, action: "none" });
  });

  it("closed and placed: formed this term or next, with the cohort size", () => {
    const closed = [check({ children: rows(4), status: "closed" })];
    expect(cohortStatus("P1", closed, "this_term", 16)).toMatchObject({ reason: "formed_this_term", formed: true, cohortSize: 16 });
    expect(cohortStatus("P1", closed, "next_term")).toMatchObject({ reason: "formed_next_term", formed: true });
  });

  it("does not guess when the programme answer is missing", () => {
    expect(cohortStatus("P1", [check({ status: "closed" })], null).reason).toBe("unknown");
  });

  it("an open check wins over an older closed one", () => {
    const s = cohortStatus("P1", [check({ id: "a", status: "closed" }), check({ id: "b", children: rows(1) })], "this_term");
    expect(s.reason).toBe("entering");
  });
});
