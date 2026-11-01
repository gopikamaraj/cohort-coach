import { describe, expect, it } from "vitest";
import { dialogSeen, markDialogSeen } from "./roles";

function memory() {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
}

describe("the role dialog flag", () => {
  it("is off until a role has been entered, per role", () => {
    const kv = memory();
    expect(dialogSeen("coach", kv)).toBe(false);
    markDialogSeen("coach", kv);
    expect(dialogSeen("coach", kv)).toBe(true);
    expect(dialogSeen("officer", kv)).toBe(false);
  });
  it("never throws when storage is unavailable", () => {
    expect(dialogSeen("coach", null)).toBe(false);
    expect(() => markDialogSeen("coach", null)).not.toThrow();
  });
});
