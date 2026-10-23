import { describe, expect, it } from "vitest";
import { stagesFor } from "./stages";

const clean = ["346", "728", "85", "74", "82", "35", "38", "26", "43", "54"];
const sfl = ["346", "728", "85", "74", "82", "35", "42", "34", "57", "66"];
const empty = Array.from({ length: 10 }, () => "");

describe("stagesFor", () => {
  it("counts the entered children only and puts the tag on the right child", () => {
    const c = stagesFor("A", [sfl, empty, sfl, clean], new Set([2]))!;
    expect(c.checked).toBe(3);
    expect(c.missed_teaching).toBe(1);
    expect(c.by_stage).toEqual([{ stage: "Core", n: 1 }]); // the tagged child is counted apart
  });
  it("is null for an empty class and holds no per-child rows", () => {
    expect(stagesFor("A", [empty], new Set())).toBeNull();
    expect(Object.keys(stagesFor("A", [sfl], new Set())!).sort()).toEqual(["by_signature", "by_stage", "checked", "missed_by_concept", "missed_teaching", "not_attempted"]);
  });
});

describe("what is queued to send", () => {
  it("never carries the stage counts or the tags: only the class counts leave the phone", async () => {
    const { profilePayload } = await import("./sync");
    const row = {
      id: "c:1", classId: "c-1", term: 1, formKey: "A", childrenChecked: 3, counts: { "SUB-SFL": 2 },
      eligible: [], track: null, anchorWrongCount: 0, untracked: {}, simulated: true, createdAt: 1,
      stages: stagesFor("A", [sfl, sfl, clean], new Set([2]))!,
    };
    const payload = profilePayload(row);
    expect(Object.keys(payload).sort()).toEqual(["anchor_wrong_count", "children_checked", "counts", "form", "simulated", "term", "untracked"]);
    expect(JSON.stringify(payload)).not.toContain("missed");
  });
});

describe("missed the teaching, per concept", () => {
  const s07 = "364,782,58,47,28,35,42,34,57,66".split(",");
  it("leaves out only the concept she tagged", () => {
    const only = (names: string[]) => stagesFor("A", [s07], new Map([[0, new Set(names)]]))!;
    const codes = (c: ReturnType<typeof only>) => c.by_signature.map((x) => x.code);
    expect(codes(only([]))).toEqual(expect.arrayContaining(["PV-REVERSE", "SUB-SFL"]));
    expect(codes(only(["subtraction"]))).toContain("PV-REVERSE");
    expect(codes(only(["subtraction"]))).not.toContain("SUB-SFL");
    expect(only(["subtraction"]).missed_by_concept).toEqual({ place_value: 0, addition: 0, subtraction: 1 });
  });
  it("the older whole-sheet tag still means every concept", () => {
    const c = stagesFor("A", [s07], new Set([0]))!;
    expect(c.by_signature).toEqual([]);
    expect(c.missed_by_concept).toEqual({ place_value: 1, addition: 1, subtraction: 1 });
  });
  it("a roll number left empty (an absent child) is not counted", () => {
    const empty = Array.from({ length: 10 }, () => "");
    expect(stagesFor("A", [s07, empty], new Map())!.checked).toBe(1);
  });
});
