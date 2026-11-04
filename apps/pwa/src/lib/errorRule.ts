// The one error rule (decided 3 Nov 2026). An error is CONFIRMED when it is seen in two or more questions and
// POSSIBLE when it is seen in one. She chooses which a view counts under; the choice is saved with her settings
// (so it goes to the cloud and follows her to another device), defaults to two or more, and is the same on every
// screen that shows counts: the results page, the cohort page, the coach pages and the officer page. Nothing here
// counts anything: the server and the engine do, and take this number as a parameter (`min_hits`).
import { useEffect, useState } from "react";
import { db } from "./db";

export type Rule = 1 | 2;
export const RULE_KEY = "errorRule";

let current: Rule = 2;
let hooked = false;
const listeners = new Set<(r: Rule) => void>();

const asRule = (v: unknown): Rule => (v === 1 || v === "1" ? 1 : 2);

function emit(): void {
  for (const l of listeners) l(current);
}

export async function loadRule(): Promise<Rule> {
  try {
    current = asRule((await db.settings.get(RULE_KEY))?.value);
  } catch {
    current = 2;
  }
  emit();
  return current;
}

export async function setRule(rule: Rule): Promise<void> {
  current = rule;
  emit();
  await db.settings.put({ key: RULE_KEY, value: rule });
}

export const currentRule = (): Rule => current;

/** Re-read the rule when the cache is refilled from the cloud (another device changed it). */
function watch(): void {
  if (hooked) return;
  hooked = true;
  db.settings.hook("creating", (key) => void (key === RULE_KEY && queueMicrotask(() => void loadRule())));
  db.settings.hook("updating", (_m, key) => void (key === RULE_KEY && queueMicrotask(() => void loadRule())));
}

export function useErrorRule(): [Rule, (r: Rule) => void] {
  const [rule, setLocal] = useState<Rule>(current);
  useEffect(() => {
    watch();
    listeners.add(setLocal);
    void loadRule();
    return () => void listeners.delete(setLocal);
  }, []);
  return [rule, (r) => void setRule(r)];
}

/** The `?min_hits=` query for a count endpoint. */
export const ruleQuery = (rule: Rule): string => `min_hits=${rule}`;
