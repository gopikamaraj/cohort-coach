// What the class gets wrong, as cards. Counts only: a teacher is never shown a percentage.
import { enteredChildren, readRow } from "./check";
import type { ProfileRow } from "./db";
import { diagnoseChild, keys } from "./diagnosis";

export const UNTRACKED_PATTERN = "ADD-WHOLE-ONES";

export interface ErrorCard {
  code: string;
  count: number;
  total: number;
  isFocus: boolean;
  example: string | null; // drawn from her own class's answers, on the phone
}

export interface CardsView {
  cards: ErrorCard[];
  childrenChecked: number;
  untracked: number;
  anchorWrong: number;
  tooSmall: boolean;
  minChildren: number;
  focus: string | null;
}

/** "52 − 29 → 37": the first child who showed this error, and the answer she wrote. */
export function exampleFor(formKey: string, code: string, rows: string[][] | null): string | null {
  if (!rows) return null;
  const form = keys.forms[formKey];
  if (!form) return null;
  for (const row of enteredChildren(rows)) {
    const readings = readRow(row);
    const diagnosis = diagnoseChild(formKey, readings);
    if (!diagnosis.shows.includes(code)) continue;
    const i = diagnosis.marks.findIndex((m) => m.kind === "error" && m.codes.includes(code));
    const item = form.items[i];
    if (!item) continue;
    const wrote = readings[i];
    if (item.type === "dictation") return `${item.a} → ${wrote}`;
    if (item.type === "add_carry") return `${item.a} + ${item.b} → ${wrote}`;
    return `${item.a} − ${item.b} → ${wrote}`;
  }
  return null;
}

export function buildCards(profile: ProfileRow, rows: string[][] | null): CardsView {
  const order = keys.error_order;
  const cards = order
    .filter((code) => (profile.counts[code] ?? 0) > 0)
    .map((code) => ({
      code,
      count: profile.counts[code] as number,
      total: profile.childrenChecked,
      isFocus: profile.track === code,
      example: exampleFor(profile.formKey, code, rows),
    }))
    .sort((a, b) => b.count - a.count || order.indexOf(a.code) - order.indexOf(b.code));
  return {
    cards,
    childrenChecked: profile.childrenChecked,
    untracked: profile.untracked[UNTRACKED_PATTERN] ?? 0,
    anchorWrong: profile.anchorWrongCount,
    tooSmall: profile.childrenChecked < keys.rules.min_children_checked,
    minChildren: keys.rules.min_children_checked,
    focus: profile.track,
  };
}
