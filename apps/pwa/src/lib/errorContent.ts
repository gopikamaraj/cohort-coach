// The text behind "What each error means" and the intervention pack. It is content (content/errors,
// content/strategies), exported to JSON by `python tasks.py export-keys`; nothing is written here.
// A language that has no text yet falls back to English and says so: nothing is machine-translated.
import raw from "../generated/error_content.json";
import type { Lang } from "../i18n";

type Texts = Partial<Record<Lang, string>>;
type Lists = Partial<Record<Lang, string[]>>;

export interface Explanation {
  what: Texts;
  why: Texts;
  spot: Texts;
  first: Texts;
}
export interface PackErrorText {
  two_minute_check: Texts;
  ten_minute_activity: Texts;
  teaching_mistakes: Lists;
  at_home: Lists;
  if_not_improving: Texts;
}
export interface StrategyRow {
  status: string;
  fits: string[];
  label: Texts;
  description: Texts;
  worked_examples: string[];
}
export interface StrategyDetail {
  materials: Texts;
  steps: Lists;
}
export interface ExtraStrategy {
  id: string;
  label: Texts;
  description: Texts;
  materials: Texts;
  steps: Lists;
}
interface ErrorContent {
  status: string;
  explanations: Record<string, Explanation>;
  pack: {
    status: string;
    source: string;
    errors: Record<string, PackErrorText>;
    strategy_details: Record<string, StrategyDetail>;
    extra_strategies: Record<string, ExtraStrategy[]>;
  };
  strategies: Record<string, StrategyRow>;
}

export const content = raw as unknown as ErrorContent;

export interface Picked<T> {
  value: T;
  fallback: boolean; // the language asked for has no text yet: English is shown
}

/** The text in the teacher's language, or English with `fallback` set. */
export function pick<T extends string | string[]>(field: Partial<Record<Lang, T>> | undefined, lang: Lang): Picked<T> | null {
  if (!field) return null;
  const own = field[lang];
  if (own !== undefined && own.length > 0) return { value: own, fallback: false };
  const en = field.en;
  return en !== undefined && en.length > 0 ? { value: en, fallback: lang !== "en" } : null;
}

export function explanationFor(code: string): Explanation | null {
  return content.explanations[code] ?? null;
}
