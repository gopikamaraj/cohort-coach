// Parity: the TypeScript renderer must give the same bytes as the Python one for every golden case.
import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import golden from "../../../../tests/fixtures/sprite_golden.json";
import { renderCase } from "./render";
import type { Case } from "./render";

describe("sprite renderer parity with Python", () => {
  it("has the golden cases", () => {
    expect(golden.cases.length).toBeGreaterThan(100);
  });
  for (const g of golden.cases) {
    const c = g.case as unknown as Case;
    const name = `${c.fn} ${JSON.stringify(c.args ?? c.persona ?? "")} ${c.item ?? ""} ${c.expression ?? ""} ${c.mouth ?? ""}`.trim();
    it(`matches ${name}`, () => {
      const svg = renderCase(c);
      expect(svg.length).toBe(g.length);
      expect(createHash("sha256").update(svg, "utf8").digest("hex")).toBe(g.sha256);
    });
  }
});
