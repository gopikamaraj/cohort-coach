import { describe, expect, it } from "vitest";
import { stepFromHash, TOUR, TOUR_SECONDS, WALK_START } from "./tour";

describe("the guided tour", () => {
  it("has nine steps that fit in five minutes: papers, check, results, cohort, practice, profile, officer, mentor, coach", () => {
    expect(TOUR).toHaveLength(9);
    expect(TOUR.map((s) => s.route)).toEqual(["/papers", "/check", "/cards", "/cohort", "/practice", "/profile", "/officer", "/mentor", "/coach"]);
    expect(TOUR_SECONDS).toBeLessThanOrEqual(300);
    expect(TOUR.map((s) => s.n)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
  });
  it("every step names the role who does it and a notice, and only the mentor and coach pages are mocked", () => {
    for (const s of TOUR) {
      expect(["teacher", "officer", "coach", "mentor"]).toContain(s.role);
      expect(s.notice).toMatch(/^tour\.s\d\.notice$/);
    }
    expect(TOUR.filter((s) => s.mocked).map((s) => s.role)).toEqual(["mentor", "coach"]);
  });
  it("reads a step from a deep link and refuses a bad one", () => {
    expect(stepFromHash("#/tour/4")).toBe(4);
    expect(stepFromHash("#/tour/9?x=1")).toBe(9);
    expect(stepFromHash("#/tour/10")).toBeNull();
    expect(stepFromHash("#/tour/0")).toBeNull();
    expect(stepFromHash("#/home")).toBeNull();
  });
  it("starts each role's walk-through inside the nine steps, at a step that role does", () => {
    expect(Object.values(WALK_START).every((n) => n >= 1 && n <= 9)).toBe(true);
    for (const [role, n] of Object.entries(WALK_START)) expect(TOUR[n - 1]?.role).toBe(role);
  });
});
