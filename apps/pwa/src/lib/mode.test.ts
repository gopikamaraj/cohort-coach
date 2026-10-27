import { describe, expect, it } from "vitest";
import { baseFor, canSwitch, pickMode } from "./mode";

const both = { judgeBase: "https://j", pilotBase: "https://p" };

describe("mode", () => {
  it("has nothing to switch with one back end", () => {
    for (const c of [
      { judgeBase: "", pilotBase: "" },
      { judgeBase: "https://j", pilotBase: "https://j" },
    ]) {
      expect(canSwitch(c)).toBe(false);
      expect(pickMode(c, "#/lesson/abc", "pilot")).toBe("judge");
      expect(baseFor(c, "pilot")).toBe(c.judgeBase);
    }
  });
  it("defaults to the judge demo and remembers the pilot", () => {
    expect(pickMode(both, "#/roles", null)).toBe("judge");
    expect(pickMode(both, "#/roles", "pilot")).toBe("pilot");
    expect(pickMode(both, "", "junk")).toBe("judge");
  });
  it("sends a lesson link to the pilot whatever was remembered", () => {
    expect(pickMode(both, "#/lesson/abcdefghijk", "judge")).toBe("pilot");
  });
  it("picks the base for the mode", () => {
    expect(baseFor(both, "judge")).toBe("https://j");
    expect(baseFor(both, "pilot")).toBe("https://p");
  });
});
