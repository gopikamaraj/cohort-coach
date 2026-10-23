import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { classCounts, classifyChild } from "./stagecalc";
import { normalizeAnswer } from "./diagnosis";

interface Tags {
  missed?: boolean;
  missed_concepts?: string[];
  unreadable?: number;
  two_answers?: number;
}
interface ChildCase {
  name: string;
  form: string;
  raw: string[];
  tags: Tags;
  expected: Record<string, unknown>;
}
interface ClassCase {
  name: string;
  children: { form: string; raw: string[]; tags: Tags }[];
  expected: { checked: number; missed_teaching: number; missed_by_concept: Record<string, number>; not_attempted: number; by_signature: [string, string, number][]; by_stage: [string, number][] };
}
const cases = JSON.parse(readFileSync(new URL("../../../../tests/fixtures/stage_cases.json", import.meta.url), "utf-8")) as {
  children: ChildCase[];
  classes: ClassCase[];
};
const read = (raw: string[]) => raw.map((x) => normalizeAnswer(x));

describe("parity with the Python engine on the stage cases", () => {
  it("has a meaningful number of cases, including the named synthetic sheets", () => {
    expect(cases.children.length).toBeGreaterThanOrEqual(100);
    expect(cases.children.map((c) => c.name)).toEqual(expect.arrayContaining(["S01", "S07", "H04", "missed_teaching_tag"]));
  });

  it("gives the same stages for every child", () => {
    for (const c of cases.children) {
      const r = classifyChild(c.form, read(c.raw), c.tags);
      expect(r, c.name).toEqual(c.expected);
    }
  });

  it("gives the same class counts", () => {
    for (const k of cases.classes) {
      const counts = classCounts(k.children.map((c) => classifyChild(c.form, read(c.raw), c.tags)));
      expect(counts.checked, k.name).toBe(k.expected.checked);
      expect(counts.missed_teaching, k.name).toBe(k.expected.missed_teaching);
      expect(counts.not_attempted, k.name).toBe(k.expected.not_attempted);
      expect(counts.missed_by_concept, k.name).toEqual(k.expected.missed_by_concept);
      expect(counts.by_signature.map((s) => [s.code, s.stage, s.n]).sort(), k.name).toEqual([...k.expected.by_signature].sort());
      expect(counts.by_stage.map((s) => [s.stage, s.n]).sort(), k.name).toEqual([...k.expected.by_stage].sort());
    }
  });
});

describe("the stage rules", () => {
  it("S07 is Core and Output, and one hit is never enough", () => {
    expect(classifyChild("A", read("364,782,58,47,28,35,42,34,57,66".split(",")), {}).stages).toEqual(["Core", "Output"]);
    expect(classifyChild("A", read("346,728,84,74,82,35,38,26,43,54".split(",")), {}).stages).toEqual([]);
  });
});
