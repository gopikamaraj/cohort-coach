import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { classProfile, diagnoseChild, normalizeAnswer } from "./diagnosis";

interface ChildCase {
  name: string;
  form: string;
  raw: string[];
  expected: Record<string, unknown>;
}
interface ClassCase {
  name: string;
  form: string;
  children: string[][];
  expected: Record<string, unknown>;
}
interface Cases {
  children: ChildCase[];
  classes: ClassCase[];
}

const cases = JSON.parse(
  readFileSync(new URL("../../../../tests/fixtures/diagnosis_cases.json", import.meta.url), "utf-8"),
) as Cases;

describe("normalizeAnswer", () => {
  it("maps Devanagari and Tamil digits and flags junk", () => {
    expect(normalizeAnswer("३४६")).toBe(346);
    expect(normalizeAnswer("௩௪௬")).toBe(346);
    expect(normalizeAnswer(" 3 46 ")).toBe(346);
    expect(normalizeAnswer("")).toBe("blank");
    expect(normalizeAnswer(null)).toBe("blank");
    expect(normalizeAnswer("?")).toBe("unreadable");
    expect(normalizeAnswer("1234567890123")).toBe("unreadable");
  });
});

describe("parity with the Python engine on golden cases", () => {
  it("has a meaningful number of cases", () => {
    expect(cases.children.length).toBeGreaterThanOrEqual(100);
    expect(cases.classes.length).toBeGreaterThanOrEqual(8);
  });

  it.each(cases.children.map((c) => [c.name, c] as const))("child %s", (_name, c) => {
    const readings = c.raw.map(normalizeAnswer);
    expect(diagnoseChild(c.form, readings)).toEqual(c.expected);
  });

  it.each(cases.classes.map((c) => [c.name, c] as const))("class %s", (_name, c) => {
    const children = c.children.map((raw) => diagnoseChild(c.form, raw.map(normalizeAnswer)));
    expect(classProfile(children)).toEqual(c.expected);
  });
});
