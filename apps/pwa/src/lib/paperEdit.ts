// The edit form's typing, not its rules: turn "38 + 47" into two numbers. Whether the numbers fit the
// item's rule, and what the answer is, are worked out by the server (POST /papers/{id}/items/check).
export type Parsed = { ok: true; a: number; b: number } | { ok: false; why: "shape" | "sign" };

const SIGNS: Record<string, string> = { "+": "+", "-": "-", "−": "-", "–": "-" };

export function signOf(operation: string): string {
  return operation === "add" ? "+" : operation === "subtract" ? "-" : "";
}

export function parseQuestion(operation: string, text: string): Parsed {
  const t = text.trim();
  if (operation === "dictate") {
    return /^\d{1,3}$/.test(t) ? { ok: true, a: Number(t), b: 0 } : { ok: false, why: "shape" };
  }
  const m = /^(\d{1,3})\s*([+\-−–])\s*(\d{1,3})$/.exec(t);
  if (!m) return { ok: false, why: "shape" };
  if (SIGNS[m[2] as string] !== signOf(operation)) return { ok: false, why: "sign" };
  return { ok: true, a: Number(m[1]), b: Number(m[3]) };
}
