// The intervention pack for one error of a cohort, put together on the phone from approved content: the
// explanations file and content/errors/intervention.v1.yaml (in generated/error_content.json). The strategies,
// their steps and worked examples, the two-minute check and what to do when it is not improving are in the
// modules (ModuleTrack), so they are not repeated here. No AI is called. A section with no content is left out and named in
// `omitted` (not invented); every section says where it came from and whether it is still a draft.
import type { Key, Lang } from "../i18n";
import { content, explanationFor, pick } from "./errorContent";
import { keys } from "./diagnosis";
import type { InThisClass } from "./results";

export type SectionId = "seeing" | "why" | "activity" | "mistakes" | "working" | "home";
export const SECTION_ORDER: SectionId[] = ["seeing", "why", "activity", "mistakes", "working", "home"];

export interface PackSection {
  id: SectionId;
  text?: string; // one paragraph
  list?: string[]; // bullet points
  numbers?: { now: number; total: number; n: number }; // "how to know it is working": the class's own counts
  here?: { children: number; total: number; example: InThisClass["example"]; rolls: { confirmed: number[]; possible: number[] } | null };
  source: string;
  draft: boolean;
  fallback: boolean; // the language asked for has no text yet: English is shown
}

export interface Pack {
  code: string;
  sections: PackSection[];
  omitted: SectionId[];
}

const SRC_EXPLAIN = "What each error means";
const SRC_PACK = "Intervention text (content/errors/intervention.v1)";

export interface PackInput {
  code: string;
  lang: Lang;
  children: number; // how many children showed it (from the cohort's own counts)
  total: number; // children checked
  here: InThisClass | null; // this class's own example, when the answers are on this phone
  rolls?: { confirmed: number[]; possible: number[] } | null; // the roll numbers, when the answers are on this phone
}

/** Build the pack. Anything with no text is left out of `sections` and named in `omitted`. */
export function buildPack(input: PackInput, onOmit: (id: SectionId, code: string) => void = () => undefined): Pack {
  const { code, lang } = input;
  const ex = explanationFor(code);
  const pack = content.pack.errors[code];
  const draftPack = content.pack.status !== "approved";
  const draftExplain = content.status !== "approved";
  const sections: PackSection[] = [];
  const omitted: SectionId[] = [];
  const add = (s: PackSection | null, id: SectionId) => {
    if (s) sections.push(s);
    else {
      omitted.push(id);
      onOmit(id, code);
    }
  };
  const textSection = (id: SectionId, field: Partial<Record<Lang, string>> | undefined, source: string, draft: boolean): PackSection | null => {
    const p = pick(field, lang);
    return p ? { id, text: p.value, source, draft, fallback: p.fallback } : null;
  };
  const listSection = (id: SectionId, field: Partial<Record<Lang, string[]>> | undefined): PackSection | null => {
    const p = pick(field, lang);
    return p && p.value.length > 0 ? { id, list: p.value, source: SRC_PACK, draft: draftPack, fallback: p.fallback } : null;
  };

  add({ id: "seeing", here: { children: input.children, total: input.total, example: input.here?.example ?? null, rolls: input.rolls ?? null }, source: "Your class's check", draft: false, fallback: false }, "seeing");
  add(textSection("why", ex?.why, SRC_EXPLAIN, draftExplain), "why");
  add(textSection("activity", pack?.ten_minute_activity, SRC_PACK, draftPack), "activity");
  add(listSection("mistakes", pack?.teaching_mistakes), "mistakes");
  // How to know it is working comes from the rules the engine uses, not from text: the same count,
  // read again at the next check.
  add({ id: "working", numbers: { now: input.children, total: input.total, n: keys.rules.min_hits }, source: "The check's own rule", draft: false, fallback: false }, "working");
  add(listSection("home", pack?.at_home), "home");
  return { code, sections, omitted };
}

export type Tr = (key: Key, params?: Record<string, string | number>) => string;

/** Every line of a section, in the order it is shown. The screen and the audio both read these, so
 *  the audio is always the text on the screen. Each ends in a full stop so it is spoken as a sentence. */
export function sectionLines(s: PackSection, tr: Tr): string[] {
  // {pv:N} marks a place-value number for the spoken version; on the screen it is just the number
  const end = (raw: string) => {
    const t = raw.replace(/\{pv:(\d+)\}/g, "$1");
    return /[.?!।]$/.test(t.trim()) ? t.trim() : `${t.trim()}.`;
  };
  const out: string[] = [];
  if (s.here) {
    out.push(tr("results.explain.children_line", { n: s.here.children, total: s.here.total }));
    const rolls = s.here.rolls;
    if (rolls && rolls.confirmed.length > 0) out.push(tr("pack.rolls", { list: rolls.confirmed.join(", ") }));
    if (rolls && rolls.possible.length > 0) out.push(tr("pack.rolls_possible", { list: rolls.possible.join(", ") }));
    const e = s.here.example;
    if (e) {
      out.push(tr(/^\d+$/.test(e.question) ? "results.explain.example_say" : "results.explain.example", { question: e.question, wrote: e.wrote, correct: e.correct }));
    }
  }
  if (s.text) out.push(s.text);
  if (s.list) out.push(...s.list);
  if (s.numbers) out.push(tr("pack.working_line", s.numbers));
  return out.map(end);
}

export const SECTION_TITLE: Record<SectionId, Key> = {
  seeing: "pack.sec.seeing",
  why: "pack.sec.why",
  activity: "pack.sec.activity",
  mistakes: "pack.sec.mistakes",
  working: "pack.sec.working",
  home: "pack.sec.home",
};

/** The text of the whole pack for one error: each section's title, then its lines. */
export function packText(pack: Pack, tr: Tr): string {
  return pack.sections.map((s) => [tr(SECTION_TITLE[s.id]), ...sectionLines(s, tr)].map((l) => (/[.?!।]$/.test(l.trim()) ? l.trim() : `${l.trim()}.`)).join("\n")).join("\n\n");
}
