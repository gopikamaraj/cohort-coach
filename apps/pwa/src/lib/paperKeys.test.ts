import { beforeEach, describe, expect, it, vi } from "vitest";
import { pairChecks } from "./checks";
import { diagnoseChild, formOf, keys } from "./diagnosis";
import { registerForm, registeredForm } from "./paperKeys";

// A paper's own key is read by the same error finder as a built-in form.
describe("a paper's own key", () => {
  beforeEach(() => {
    const mem = new Map<string, string>(); // the tests run in node, which has no localStorage
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => mem.get(k) ?? null,
      setItem: (k: string, v: string) => void mem.set(k, v),
      removeItem: (k: string) => void mem.delete(k),
      clear: () => mem.clear(),
    });
  });

  it("is looked up by the paper's id, and a built-in form still is by its letter", () => {
    expect(formOf("P-0123456789ab")).toBeUndefined();
    registerForm("P-0123456789ab", keys.forms["A"]!);
    expect(registeredForm("P-0123456789ab")?.items.length).toBe(10);
    expect(formOf("P-0123456789ab")?.items[2]?.correct).toBe(85);
    expect(formOf("A")?.items.length).toBe(10);
  });

  it("finds an error from the paper's key, with its own number of answers", () => {
    const a = keys.forms["A"]!;
    const longer = { ...a, items: [...a.items, { ...a.items[9]!, n: 11 }] }; // a paper with an extra item
    registerForm("P-aaaaaaaaaaaa", longer);
    const readings = longer.items.map((i) => i.correct);
    expect(diagnoseChild("P-aaaaaaaaaaaa", readings).shows).toEqual([]);
    const wrong = [...readings];
    for (const n of [3, 5]) wrong[n - 1] = Number(Object.entries(a.items[n - 1]!.wrong).find(([, c]) => c.includes("ADD-NOCARRY"))![0]);
    expect(diagnoseChild("P-aaaaaaaaaaaa", wrong).shows).toEqual(["ADD-NOCARRY"]);
    expect(() => diagnoseChild("P-aaaaaaaaaaaa", readings.slice(0, 10))).toThrow(/expected 11/);
  });

  it("leaves adaptive items out of before and after, while they still find errors", () => {
    const a = keys.forms["A"]!;
    const adaptive = { ...a.items[2]!, n: 11, anchor: false }; // an extra addition item
    registerForm("P-bbbbbbbbbbbb", { ...a, items: [...a.items.map((i) => ({ ...i, anchor: true })), adaptive] });
    const right = [...a.items.map((i) => String(i.correct)), String(adaptive.correct)];
    const wrongOn = (r: string[], ns: number[]) => r.map((v, i) => (ns.includes(i + 1) ? Object.entries([...a.items, adaptive][i]!.wrong).find(([, c]) => c.includes("ADD-NOCARRY"))![0] : v));
    // item 3 and the adaptive item 11: the error is found ...
    const before = wrongOn(right, [3, 11]);
    expect(diagnoseChild("P-bbbbbbbbbbbb", before.map(Number)).shows).toEqual(["ADD-NOCARRY"]);
    // ... but before and after count anchor items only, so this child was never flagged on them
    const p = pairChecks("P-bbbbbbbbbbbb", [before], "P-bbbbbbbbbbbb", [right]);
    expect(p.by_competency["C2"]!.flagged_before).toBe(0);
  });
});
