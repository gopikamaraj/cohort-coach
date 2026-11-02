import { describe, expect, it } from "vitest";
import { roleChanged, stepFromHash, TOUR, TOUR_SECONDS, WALK_START } from "./tour";

describe("the guided tour", () => {
  it("has six steps that fit in five minutes and start with the check", () => {
    expect(TOUR).toHaveLength(6);
    expect(TOUR[0]?.screen).toBe("check");
    expect(TOUR_SECONDS).toBeLessThanOrEqual(300);
    expect(TOUR.map((s) => s.n)).toEqual([1, 2, 3, 4, 5, 6]);
  });
  it("every step names the role who does it and a notice", () => {
    for (const s of TOUR) {
      expect(["teacher", "officer", "coach"]).toContain(s.role);
      expect(s.notice).toMatch(/^tour\.s\d\.notice$/);
    }
  });
  it("reads a step from a deep link and refuses a bad one", () => {
    expect(stepFromHash("#/tour/4")).toBe(4);
    expect(stepFromHash("#/tour/6?x=1")).toBe(6);
    expect(stepFromHash("#/tour/7")).toBeNull();
    expect(stepFromHash("#/tour/0")).toBeNull();
    expect(stepFromHash("#/home")).toBeNull();
  });
  it("shows the Now-you-are banner only when the role changes", () => {
    expect([1, 2, 3, 4, 5, 6].map(roleChanged)).toEqual([true, true, true, true, true, true]);
    expect(Object.values(WALK_START).every((n) => n >= 1 && n <= 6)).toBe(true);
  });
});
