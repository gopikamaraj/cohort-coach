// A simulated class of 28 children for judge mode. Every answer is picked from the answer keys
// the Python engine wrote (lookups only), so the on-device diagnosis reads it back to the same
// counts. Everything made here is simulated and labelled so wherever it shows.
import { keys, type ItemKey } from "./diagnosis";
import { UNTRACKED_PATTERN } from "./cards";

export const DEMO_FORM = "A";
export const DEMO_SIZE = 28;

/** How many children show each error in each simulated term (term 2 is after the track). */
export const DEMO_COUNTS: Record<number, Record<string, number>> = {
  1: { "PV-HEARD": 2, "ADD-NOCARRY": 5, "SUB-SFL": 11, "SUB-NODEC": 3 },
  2: { "PV-HEARD": 1, "ADD-NOCARRY": 4, "SUB-SFL": 6, "SUB-NODEC": 3 },
};
const DEMO_UNTRACKED: Record<number, number> = { 1: 2, 2: 2 };
const DEMO_ANCHOR_WRONG: Record<number, number> = { 1: 1, 2: 1 };

function wrongFor(item: ItemKey, code: string): string | undefined {
  return Object.entries(item.wrong).find(([, codes]) => codes.length === 1 && codes[0] === code)?.[0];
}

/** Two wrong answers on items that probe this error (the 2-item rule), the rest correct. */
function childShowing(formKey: string, code: string): string[] {
  const items = keys.forms[formKey]?.items ?? [];
  const row = items.map((item) => String(item.correct));
  let made = 0;
  items.forEach((item, i) => {
    if (made >= 2 || !item.probes.includes(code)) return;
    const wrong = wrongFor(item, code);
    if (wrong !== undefined) {
      row[i] = wrong;
      made += 1;
    }
  });
  return row;
}

function childWithUntracked(formKey: string): string[] {
  const items = keys.forms[formKey]?.items ?? [];
  const row = items.map((item) => String(item.correct));
  let made = 0;
  items.forEach((item, i) => {
    if (made >= 1) return;
    const answer = Object.entries(item.untracked).find(([, name]) => name === UNTRACKED_PATTERN)?.[0];
    if (answer !== undefined) {
      row[i] = answer;
      made += 1;
    }
  });
  return row;
}

function childWrongAnchor(formKey: string): string[] {
  const items = keys.forms[formKey]?.items ?? [];
  return items.map((item) => (item.type === "sub_anchor" ? String(item.correct + 1) : String(item.correct)));
}

export function demoChildren(term: number, formKey: string = DEMO_FORM): string[][] {
  const counts = DEMO_COUNTS[term] ?? DEMO_COUNTS[1]!;
  const rows: string[][] = [];
  for (const code of keys.error_order) {
    for (let i = 0; i < (counts[code] ?? 0); i++) rows.push(childShowing(formKey, code));
  }
  for (let i = 0; i < (DEMO_UNTRACKED[term] ?? 0); i++) rows.push(childWithUntracked(formKey));
  for (let i = 0; i < (DEMO_ANCHOR_WRONG[term] ?? 0); i++) rows.push(childWrongAnchor(formKey));
  const correct = (keys.forms[formKey]?.items ?? []).map((item) => String(item.correct));
  while (rows.length < DEMO_SIZE) rows.push([...correct]);
  return rows;
}
