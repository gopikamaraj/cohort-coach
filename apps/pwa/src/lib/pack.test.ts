import { describe, expect, it } from "vitest";
import { keys } from "./diagnosis";
import { content } from "./errorContent";
import { buildPack, SECTION_ORDER } from "./pack";

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
    expect(p.sections.find((s) => s.id === "activity")?.draft).toBe(true);
    expect(content.status).toBe("draft");
  });

  it("does not repeat what the modules carry: no strategies, no two-minute check, no 'if it does not improve'", () => {
    for (const code of keys.error_order) {
      const ids = buildPack(input(code)).sections.map((s) => s.id) as string[];
      for (const gone of ["strategies", "check", "stuck"]) expect(ids, `${code} ${gone}`).not.toContain(gone);
    }
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
    expect(p.omitted).toEqual(["why", "activity", "mistakes", "home"]);
    expect(logged).toHaveLength(4);
  });

  it("shows English with a flag when the language has no text yet", () => {
    const hi = buildPack(input("SUB-SFL", "hi"));
    const en = buildPack(input("SUB-SFL", "en"));
    for (const s of hi.sections.filter((x) => x.fallback)) expect(s.text ?? s.list).toEqual(en.sections.find((x) => x.id === s.id)!.text ?? en.sections.find((x) => x.id === s.id)!.list);
    expect(buildPack(input("SUB-SFL", "en")).sections.every((s) => !s.fallback)).toBe(true);
  });

  it("holds no percentage", () => {
    const text = JSON.stringify(buildPack(input("SUB-SFL")));
    expect(text).not.toContain("%");
  });
});
