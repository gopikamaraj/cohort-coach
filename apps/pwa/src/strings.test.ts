import { describe, expect, it } from "vitest";
import { strings, t } from "./strings";

describe("strings", () => {
  it("has the same keys in en, hi and ta", () => {
    const keys = Object.keys(strings.en).sort();
    expect(Object.keys(strings.hi).sort()).toEqual(keys);
    expect(Object.keys(strings.ta).sort()).toEqual(keys);
  });
  it("returns the translated title", () => {
    expect(t("hi", "title")).toBe(strings.hi.title);
  });
});
