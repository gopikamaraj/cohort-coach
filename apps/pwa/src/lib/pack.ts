// The intervention pack for one error of a cohort, put together on the phone from approved content: the
// explanations file, the strategy library and content/errors/intervention.v1.yaml (all in
// generated/error_content.json). No AI is called. A section with no content is left out and named in
// `omitted` (not invented); every section says where it came from and whether it is still a draft.
import type { Lang } from "../i18n";
import { content, explanationFor, pick, type ExtraStrategy } from "./errorContent";
import { keys } from "./diagnosis";
import type { InThisClass } from "./results";

export type SectionId = "seeing" | "why" | "check" | "strategies" | "activity" | "mistakes" | "working" | "home" | "stuck";
export const SECTION_ORDER: SectionId[] = ["seeing", "why", "check", "strategies", "activity", "mistakes", "working", "home", "stuck"];
export const MAX_STRATEGIES = 3;

export interface PackStrategy {
  id: string;
  label: string;
  description: string;
  steps: string[];
  materials: string | null;
  worked: string[];
  draft: boolean;
  source: string;
  fallback: boolean;
}

export interface PackSection {
  id: SectionId;
  text?: string; // one paragraph
  list?: string[]; // bullet points
  strategies?: PackStrategy[];
  numbers?: { now: number; total: number; n: number }; // "how to know it is working": the class's own counts
  here?: { children: number; total: number; example: InThisClass["example"] };
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
const SRC_LIB = "Strategy library (strategies.v1)";

export interface PackInput {
  code: string;
  lang: Lang;
  children: number; // how many children showed it (from the cohort's own counts)
  total: number; // children checked
  here: InThisClass | null; // this class's own example, when the answers are on this phone
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

  add({ id: "seeing", here: { children: input.children, total: input.total, example: input.here?.example ?? null }, source: "Your class's check", draft: false, fallback: false }, "seeing");
  add(textSection("why", ex?.why, SRC_EXPLAIN, draftExplain), "why");
  add(textSection("check", pack?.two_minute_check, SRC_PACK, draftPack), "check");

  // strategies: those in the library that fit this error, then any the pack adds for an error the library misses
  const strategies: PackStrategy[] = [];
  for (const [id, s] of Object.entries(content.strategies)) {
    if (!s.fits.includes(code)) continue;
    const label = pick(s.label, lang);
    const description = pick(s.description, lang);
    const detail = content.pack.strategy_details[id];
    const steps = pick(detail?.steps, lang);
    if (!label || !description || !steps) continue;
    strategies.push({
      id,
      label: label.value,
      description: description.value,
      steps: steps.value,
      materials: pick(detail?.materials, lang)?.value ?? null,
      worked: s.worked_examples,
      draft: s.status !== "approved",
      source: SRC_LIB,
      fallback: label.fallback || description.fallback || steps.fallback,
    });
  }
  for (const x of (content.pack.extra_strategies[code] ?? []) as ExtraStrategy[]) {
    const label = pick(x.label, lang);
    const description = pick(x.description, lang);
    const steps = pick(x.steps, lang);
    if (!label || !description || !steps) continue;
    strategies.push({ id: x.id, label: label.value, description: description.value, steps: steps.value, materials: pick(x.materials, lang)?.value ?? null, worked: [], draft: true, source: SRC_PACK, fallback: label.fallback || description.fallback || steps.fallback });
  }
  const shown = strategies.slice(0, MAX_STRATEGIES);
  add(
    shown.length > 0 ? { id: "strategies", strategies: shown, source: SRC_LIB, draft: shown.some((s) => s.draft), fallback: shown.some((s) => s.fallback) } : null,
    "strategies",
  );

  add(textSection("activity", pack?.ten_minute_activity, SRC_PACK, draftPack), "activity");
  add(listSection("mistakes", pack?.teaching_mistakes), "mistakes");
  // How to know it is working comes from the rules the engine uses, not from text: the same count,
  // read again at the next check.
  add({ id: "working", numbers: { now: input.children, total: input.total, n: keys.rules.min_hits }, source: "The check's own rule", draft: false, fallback: false }, "working");
  add(listSection("home", pack?.at_home), "home");
  add(textSection("stuck", pack?.if_not_improving, SRC_PACK, draftPack), "stuck");
  return { code, sections, omitted };
}
