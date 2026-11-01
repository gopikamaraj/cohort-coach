import { describe, expect, it } from "vitest";
import { keys } from "./diagnosis";
import { content } from "./errorContent";
import { buildPack, MAX_STRATEGIES, SECTION_ORDER } from "./pack";

const input = (code: string, lang: "en" | "hi" | "ta" = "en") => ({ code, lang, children: 5, total: 16, here: null });

describe("buildPack", () => {
  it("has every section, in the fixed order, for every error the check can find", () => {
    for (const code of keys.error_order) {
      const p = buildPack(input(code));
      expect(p.omitted, code).toEqual([]);
      expect(p.sections.map((s) => s.id), code).toEqual(SECTION_ORDER);
    }
  });

  it("every section says where it came from, and anything still unreviewed is marked a draft", () => {
    const p = buildPack(input("SUB-SFL"));
    for (const s of p.sections) expect(s.source.length, s.id).toBeGreaterThan(3);
    expect(p.sections.find((s) => s.id === "why")?.draft).toBe(true);
    expect(p.sections.find((s) => s.id === "strategies")?.draft).toBe(true);
    expect(content.status).toBe("draft");
  });

  it("shows at most three strategies, each from the library with steps, or the pack's own for an error the library misses", () => {
    const sfl = buildPack(input("SUB-SFL")).sections.find((s) => s.id === "strategies")!;
    expect(sfl.strategies!.length).toBe(MAX_STRATEGIES);
    for (const st of sfl.strategies!) expect(st.steps.length).toBeGreaterThan(0);
    const libraryIds = Object.keys(content.strategies);
    expect(sfl.strategies!.every((s) => libraryIds.includes(s.id))).toBe(true);
    const rev = buildPack(input("PV-REVERSE")).sections.find((s) => s.id === "strategies")!;
    expect(rev.strategies!.map((s) => s.id)).toEqual(["say_build_write"]);
    expect(rev.strategies![0]!.draft).toBe(true);
  });

  it("uses the class's own numbers, from the rule the engine uses", () => {
    const w = buildPack(input("SUB-SFL")).sections.find((s) => s.id === "working")!;
    expect(w.numbers).toEqual({ now: 5, total: 16, n: keys.rules.min_hits });
    const seeing = buildPack(input("SUB-SFL")).sections.find((s) => s.id === "seeing")!;
    expect(seeing.here).toMatchObject({ children: 5, total: 16 });
  });

  it("leaves a section out and logs it when there is no content, never inventing one", () => {
    const logged: string[] = [];
    const p = buildPack(input("NO-SUCH-ERROR"), (id, code) => logged.push(`${code}:${id}`));
    expect(p.sections.map((s) => s.id)).toEqual(["seeing", "working"]);
    expect(p.omitted).toEqual(["why", "check", "strategies", "activity", "mistakes", "home", "stuck"]);
    expect(logged).toHaveLength(7);
  });

  it("shows English with a flag when the language has no text yet", () => {
    const hi = buildPack(input("SUB-SFL", "hi"));
    expect(hi.sections.find((s) => s.id === "check")).toMatchObject({ fallback: true });
    expect(hi.sections.find((s) => s.id === "check")!.text).toContain("Write a subtraction");
    expect(buildPack(input("SUB-SFL", "en")).sections.every((s) => !s.fallback)).toBe(true);
  });

  it("holds no percentage", () => {
    const text = JSON.stringify(buildPack(input("SUB-SFL")));
    expect(text).not.toContain("%");
  });
});
