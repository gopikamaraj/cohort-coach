import { describe, expect, it } from "vitest";
import { sectionOf, classCodeOf, duplicates, folderPickerSupported, isPicture, matchPicture, parseFileName, runQueue, summarise } from "./folder";

describe("matching pictures to roll numbers", () => {
  it("reads the roll from a file name", () => {
    expect(parseFileName("3A-roll07.jpg")).toEqual({ classCode: "3A", roll: 7 });
    expect(parseFileName("roll_12.png")).toEqual({ classCode: undefined, roll: 12 });
    expect(parseFileName("IMG_4521.jpg")).toBeNull();
    expect(parseFileName("roll0.jpg")).toBeNull();
  });
  it("class code of a paper", () => {
    expect(classCodeOf("PRE · 3A · T1")).toBe("3A");
    expect(classCodeOf(null)).toBeNull();
  });
  it("name first, then header, else the teacher chooses", () => {
    expect(matchPicture("3A-roll07.jpg", null, "3A", 28)).toEqual({ state: "matched", roll: 7, by: "name" });
    expect(matchPicture("IMG_1.jpg", { class_code: "3A", roll_number: 9, confidence: 0.9 }, "3A", 28)).toEqual({ state: "matched", roll: 9, by: "header" });
    expect(matchPicture("IMG_1.jpg", { class_code: "3A", roll_number: 9, confidence: 0.4 }, "3A", 28)).toEqual({ state: "needs_roll" });
    expect(matchPicture("IMG_1.jpg", null, "3A", 28)).toEqual({ state: "needs_roll" });
  });
  it("a header's class code is compared by its grade and section, so a misread prefix does not block", () => {
    expect(sectionOf("S0-3A")).toBe("3A");
    expect(sectionOf("SO-3A")).toBe("3A");
    expect(sectionOf("3a")).toBe("3A");
    expect(sectionOf("Class")).toBeNull();
    expect(matchPicture("x.jpg", { class_code: "SO-3A", roll_number: 7, confidence: 0.85 }, "3A", 28)).toEqual({ state: "matched", roll: 7, by: "header" });
    expect(matchPicture("x.jpg", { class_code: "Hello", roll_number: 7, confidence: 0.85 }, "3A", 28)).toEqual({ state: "matched", roll: 7, by: "header" });
  });
  it("a different class is flagged, never used silently", () => {
    expect(matchPicture("3B-roll02.jpg", null, "3A", 28)).toEqual({ state: "other_class", roll: 2, found: "3B" });
    expect(matchPicture("x.jpg", { class_code: "4C", roll_number: 3, confidence: 0.95 }, "3A", 28)).toEqual({ state: "other_class", roll: 3, found: "4C" });
  });
  it("summary and duplicates", () => {
    const m = [matchPicture("3A-roll01.jpg", null, "3A", 5), matchPicture("a.jpg", null, "3A", 5), matchPicture("3B-roll02.jpg", null, "3A", 5)];
    expect(summarise(4, 1, m)).toEqual({ found: 4, matched: 1, needRoll: 1, otherClass: 1, skipped: 1 });
    expect([...duplicates([1, 2, 1, null])]).toEqual([[1, [0, 2]]]);
  });
  it("what is a picture", () => {
    expect(isPicture({ name: "a.JPG" })).toBe(true);
    expect(isPicture({ name: "notes.txt", type: "text/plain" })).toBe(false);
    expect(isPicture({ name: "x", type: "image/heic" })).toBe(true);
  });
  it("detects the folder picker by feature", () => {
    expect(folderPickerSupported({ webkitdirectory: true })).toBe(true);
    expect(folderPickerSupported({})).toBe(false);
  });
});

describe("reading queue", () => {
  it("reads at most three at a time and keeps going when one fails", async () => {
    let running = 0;
    let peak = 0;
    const seen: number[] = [];
    await runQueue([1, 2, 3, 4, 5, 6, 7], async (n) => {
      running += 1;
      peak = Math.max(peak, running);
      await new Promise((r) => setTimeout(r, 5));
      running -= 1;
      if (n === 3) throw new Error("fails");
      seen.push(n);
    });
    expect(peak).toBe(3);
    expect(seen.sort()).toEqual([1, 2, 4, 5, 6, 7]);
  });
  it("Cancel stops starting new ones", async () => {
    const ctrl = new AbortController();
    const started = await runQueue([1, 2, 3, 4, 5, 6], async (n) => {
      if (n === 3) ctrl.abort();
      await new Promise((r) => setTimeout(r, 2));
    }, { signal: ctrl.signal });
    expect(started.length).toBeLessThan(6);
  });
});
