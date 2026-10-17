import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { allTables, missingKeys, t, type Key } from "./index";
import en from "./en.json";

const SRC = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === "generated" ? [] : sourceFiles(path);
    return /\.(ts|tsx)$/.test(name) && !/\.test\./.test(name) ? [path] : [];
  });
}

describe("strings", () => {
  const keys = Object.keys(en).sort();

  it("has the same keys in en, hi and ta", () => {
    expect(Object.keys(allTables.hi).sort()).toEqual(keys);
    expect(Object.keys(allTables.ta).sort()).toEqual(keys);
  });

  it("has no empty string in any language", () => {
    for (const lang of ["en", "hi", "ta"] as const) {
      for (const [key, value] of Object.entries(allTables[lang])) {
        expect(value, `${lang}:${key}`).not.toBe("");
      }
    }
  });

  it("uses the same {slots} in every language for every key", () => {
    const slots = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    for (const key of keys as Key[]) {
      expect(slots(allTables.hi[key] as string), `hi:${key}`).toEqual(slots(en[key]));
      expect(slots(allTables.ta[key] as string), `ta:${key}`).toEqual(slots(en[key]));
    }
  });

  it("never shows a teacher a percentage sign", () => {
    for (const lang of ["en", "hi", "ta"] as const) {
      for (const [key, value] of Object.entries(allTables[lang])) {
        expect(value, `${lang}:${key}`).not.toMatch(/%|प्रतिशत|சதவீதம்|percent/i);
      }
    }
  });

  it("covers every key the code asks for (English completeness)", () => {
    const used = new Set<string>();
    for (const file of sourceFiles(SRC)) {
      const text = readFileSync(file, "utf-8");
      for (const m of text.matchAll(/\btr?\(\s*(?:[\w.]+\s*,\s*)?"([a-z]+\.[^"]+)"/g)) used.add(m[1] as string);
      for (const m of text.matchAll(/\bkey:\s*"([a-z]+\.[\w.-]+)"/g)) used.add(m[1] as string);
    }
    expect(used.size).toBeGreaterThan(20);
    const absent = [...used].filter((k) => !(k in en));
    expect(absent).toEqual([]);
  });

  it("fills slots, and falls back to English and remembers a missing key", () => {
    expect(t("en", "cards.line", { n: 11, total: 28, desc: "x" })).toBe("11 of 28 children x.");
    expect(t("hi", "cards.line", { n: 11, total: 28, desc: "x" })).toContain("28 में से 11");
    const saved = allTables.hi["common.back"];
    delete allTables.hi["common.back"];
    expect(t("hi", "common.back")).toBe("Back");
    expect(missingKeys()).toContain("hi:common.back");
    allTables.hi["common.back"] = saved;
  });
});
