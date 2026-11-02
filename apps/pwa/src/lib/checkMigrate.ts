// The labels for checks saved before they had any. Kept apart from checks.ts because the database upgrade
// (db.ts) runs it, and checks.ts reads the database.
import type { CheckRow } from "./db";

/** The label fields for a check saved before labels existed. Empty for one that has them already. */
export function legacyFields(c: CheckRow, all: CheckRow[], withResult: Set<string>): Partial<CheckRow> {
  if (c.kind !== undefined) return {};
  const mine = all.filter((x) => x.classId === c.classId).sort((a, b) => a.updatedAt - b.updatedAt);
  const first = mine[0]?.id === c.id;
  return {
    kind: first ? "pre" : c.formKey === "B" ? "post" : "termly",
    round: 1,
    checkDate: new Date(c.updatedAt).toISOString().slice(0, 10),
    paperVersion: "legacy",
    trackId: null,
    expectedChildren: null,
    status: withResult.has(c.id) ? "closed" : "entering",
    confirm: true, // she can correct the guess on the Start a check screen
  };
}
