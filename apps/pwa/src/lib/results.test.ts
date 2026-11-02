import { describe, expect, it } from "vitest";
import { diagnoseChild, formOf, keys } from "./diagnosis";
import { readRow } from "./check";
import { buildAnswerMap, classCoverage, coverageFromKey, inThisClass, questionText, SHORT, sortRolls } from "./results";

const FORM = "A";
const items = formOf(FORM)!.items;
const correct = (): string[] => items.map((i) => String(i.correct));
// the wrong answer an item's key lists for a code (the engine wrote it)
const wrongFor = (n: number, code: string): string => {
  const it = items.find((i) => i.n === n)!;
  const hit = Object.entries(it.wrong).find(([, codes]) => codes.length === 1 && codes[0] === code);
  if (!hit) throw new Error(`no ${code} answer on item ${n}`);
  return hit[0];
};
const row = (patch: Record<number, string>): string[] => correct().map((v, q) => patch[q + 1] ?? v);

// 6 children: all right; SUB-SFL on 7 and 8 (shows); SUB-SFL on 7 only (possible); both subtractions
// and a nonsense answer; blanks and a cannot-read; and one roll left empty plus one marked absent.
const ROWS: string[][] = [
  correct(),
  row({ 7: wrongFor(7, "SUB-SFL"), 8: wrongFor(8, "SUB-SFL") }),
  row({ 7: wrongFor(7, "SUB-SFL") }),
  row({ 9: wrongFor(9, "SUB-NODEC"), 10: wrongFor(10, "SUB-NODEC"), 3: "11" }),
  row({ 1: "_", 2: "?" }),
  ["", "", "", "", "", "", "", "", "", ""],
  correct(),
];

describe("buildAnswerMap", () => {
  const map = buildAnswerMap(FORM, ROWS, [6])!;

  it("has a row per entered roll and leaves out the absent and the empty ones", () => {
    expect(map.rolls.map((r) => r.roll)).toEqual([1, 2, 3, 4, 5]);
    expect(map.absent).toEqual([7]);
    expect(map.notEntered).toBe(1);
  });

  it("gives every cell the engine's own reading of that answer", () => {
    for (const r of map.rolls) {
      const d = diagnoseChild(FORM, readRow(ROWS[r.roll - 1] as string[]));
      r.cells.forEach((c, q) => {
        const m = d.marks[q]!;
        expect(c.kind).toBe(m.kind);
        expect(c.codes).toEqual(m.codes);
        expect(c.confirmed).toBe(m.codes.some((x) => d.shows.includes(x)));
      });
    }
  });

  it("marks an error seen on two questions as confirmed and on one question as possible", () => {
    const two = map.rolls.find((r) => r.roll === 2)!;
    expect(two.cells[6]).toMatchObject({ kind: "error", code: "SUB-SFL", confirmed: true });
    const one = map.rolls.find((r) => r.roll === 3)!;
    expect(one.cells[6]).toMatchObject({ kind: "error", code: "SUB-SFL", confirmed: false });
    expect(one.shows).toEqual([]);
  });

  it("shows a blank, a cannot-read box and a wrong answer with no error apart", () => {
    const five = map.rolls.find((r) => r.roll === 5)!;
    expect(five.cells[0]!.kind).toBe("blank");
    expect(five.cells[1]!.kind).toBe("unreadable");
    expect(map.rolls.find((r) => r.roll === 4)!.cells[2]!.kind).toBe("other");
  });

  it("column totals are the children who got that question wrong (blank and unreadable are not counted)", () => {
    const wrongOn = (n: number) => map.rolls.filter((r) => ["error", "other"].includes(r.cells[n - 1]!.kind)).length;
    expect(map.wrongByItem).toEqual(items.map((i) => wrongOn(i.n)));
    expect(map.wrongByItem[6]).toBe(2); // roll 2 and roll 3 on question 7
    expect(map.wrongByItem[0]).toBe(0); // the blank box is not a wrong answer
  });

  it("the legend counts children who show each error, and children with a single match apart", () => {
    const sfl = map.legend.find((l) => l.code === "SUB-SFL")!;
    expect(sfl).toMatchObject({ confirmed: 1, possible: 1 });
    const nodec = map.legend.find((l) => l.code === "SUB-NODEC")!;
    expect(nodec).toMatchObject({ confirmed: 1, possible: 0 });
    expect(map.legend.map((l) => l.code)).not.toContain("PV-HEARD");
  });

  it("is null for a paper this phone does not know", () => {
    expect(buildAnswerMap("no-such-form", ROWS)).toBeNull();
  });

  it("counts only approved rolls when approval is recorded", () => {
    const some = buildAnswerMap(FORM, ROWS, [6], [0, 1])!;
    expect(some.rolls.map((r) => r.roll)).toEqual([1, 2]);
  });
});

describe("sortRolls", () => {
  const map = buildAnswerMap(FORM, ROWS, [6])!;
  it("sorts by roll number by default and by number of wrong answers on request", () => {
    expect(sortRolls(map.rolls, "roll").map((r) => r.roll)).toEqual([1, 2, 3, 4, 5]);
    const byErrors = sortRolls(map.rolls, "errors").map((r) => r.roll);
    expect(byErrors[0]).toBe(4); // three wrong
    expect(byErrors.slice(-2)).toEqual([1, 5]); // 0 wrong, in roll order
  });
});

describe("short codes", () => {
  it("are unique, two letters, and exist for every error the paper can find", () => {
    for (const code of keys.error_order) expect(SHORT[code]).toMatch(/^[A-Z]{2,3}$/);
    expect(new Set(Object.values(SHORT)).size).toBe(Object.values(SHORT).length);
  });
});

describe("the coverage matrix", () => {
  it("is the answer key's own probes, one row per error the paper checks", () => {
    const cov = coverageFromKey(FORM);
    expect(cov["PV-HEARD"]).toEqual([1, 2]);
    expect(cov["PV-REVERSE"]).toEqual([1, 2]);
    expect(cov["ADD-NOCARRY"]).toEqual([3, 4, 5]);
    expect(cov["SUB-SFL"]).toEqual([7, 8, 9, 10]);
    expect(cov["SUB-NODEC"]).toEqual([7, 8, 9, 10]);
    for (const code of keys.error_order) {
      expect(cov[code]).toEqual(items.filter((i) => i.probes.includes(code)).map((i) => i.n));
    }
  });

  it("adds this class's counts, and keeps every error the paper checks even at 0", () => {
    const map = buildAnswerMap(FORM, ROWS, [6])!;
    const rows = classCoverage(map);
    expect(rows.map((r) => r.code)).toEqual(keys.error_order);
    expect(rows.find((r) => r.code === "SUB-SFL")).toMatchObject({ confirmed: 1, possible: 1, assessed: true });
    expect(rows.find((r) => r.code === "PV-HEARD")).toMatchObject({ confirmed: 0, possible: 0, assessed: true });
  });
});

describe("inThisClass", () => {
  const map = buildAnswerMap(FORM, ROWS, [6])!;
  it("gives the class's own question, the answer the children wrote and the correct answer", () => {
    const sfl = inThisClass(map, "SUB-SFL");
    expect(sfl.children).toBe(1);
    expect(sfl.questions).toEqual([7, 8]);
    expect(sfl.example).toEqual({ n: 7, question: questionText(items[6]!), wrote: Number(wrongFor(7, "SUB-SFL")), correct: items[6]!.correct });
    expect(sfl.common).toEqual({ answer: Number(wrongFor(7, "SUB-SFL")), n: 2 });
  });
  it("has no example for an error that did not appear", () => {
    expect(inThisClass(map, "PV-HEARD")).toMatchObject({ children: 0, questions: [], example: null, common: null });
  });
});
