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
    expect(Object.keys(stagesFor("A", [sfl], new Set())!).sort()).toEqual(["by_signature", "by_stage", "checked", "missed_teaching", "not_attempted"]);
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
