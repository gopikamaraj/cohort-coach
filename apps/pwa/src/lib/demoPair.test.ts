import { describe, expect, it } from "vitest";
import { classProfile } from "./diagnosis";
import { diagnoseAll } from "./check";
import { COMPETENCIES, pairChecks } from "./checks";
import { DEMO_COUNTS, DEMO_SIZE, demoPair } from "./demo";

describe("the demo pre-test and post-test", () => {
  const { pre, post } = demoPair();

  it("is Form A before and Form B after, the same size, with the demo counts for each", () => {
    expect(pre).toHaveLength(DEMO_SIZE);
    expect(post).toHaveLength(DEMO_SIZE);
    const before = classProfile(diagnoseAll("A", pre));
    const after = classProfile(diagnoseAll("B", post));
    for (const code of Object.keys(DEMO_COUNTS[1] ?? {})) {
      expect(before.counts[code]).toBe(DEMO_COUNTS[1]?.[code]);
      expect(after.counts[code]).toBe(DEMO_COUNTS[2]?.[code]);
    }
  });

  it("pairs child by child: the fall in each error is the number fixed, nobody is newly flagged", () => {
    const p = pairChecks("A", pre, "B", post);
    expect(p.paired).toBe(DEMO_SIZE);
    expect(p.small_sample).toBe(false);
    for (const [name, codes] of Object.entries(COMPETENCIES)) {
      const before = codes.reduce((n, c) => n + (DEMO_COUNTS[1]?.[c] ?? 0), 0);
      const after = codes.reduce((n, c) => n + (DEMO_COUNTS[2]?.[c] ?? 0), 0);
      const got = p.by_competency[name];
      expect(got).toEqual({ flagged_before: before, fixed: before - after, still_flagged: after, newly_flagged: 0 });
    }
  });
});
