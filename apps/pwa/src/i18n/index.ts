// Typed strings in three languages. English is the source of truth: a key missing in hi or ta
// falls back to English and is remembered (`missingKeys`) so it can be listed in
// docs/build/i18n-todo.md by `python scripts/i18n.py todo`.
import en from "./en.json";
import hi from "./hi.json";
import ta from "./ta.json";

export type Lang = "en" | "hi" | "ta";
export const LANGS: readonly Lang[] = ["en", "hi", "ta"];
export const LANG_NAMES: Record<Lang, string> = { en: "English", hi: "हिन्दी", ta: "தமிழ்" };

export type Key = keyof typeof en;
type Table = Partial<Record<Key, string>>;

const tables: Record<Lang, Table> = { en, hi, ta };
const missing = new Set<string>();

export function missingKeys(): string[] {
  return [...missing].sort();
}

export function isLang(value: unknown): value is Lang {
  return typeof value === "string" && (LANGS as readonly string[]).includes(value);
}

/** Look a string up and fill `{slots}`. Slots are filled by code with values the code computed. */
export function t(lang: Lang, key: Key, params: Record<string, string | number> = {}): string {
  let text = tables[lang][key];
  if (text === undefined || text === "") {
    missing.add(`${lang}:${key}`);
    text = en[key];
  }
  return text.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in params ? String(params[name]) : whole,
  );
}

export const allTables = tables;
