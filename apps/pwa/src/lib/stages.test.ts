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
