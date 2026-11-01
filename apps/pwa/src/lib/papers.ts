// Paper Studio's API calls. Papers are made on the server by code from approved rules (no AI); this
// file only sends what the screen chose and shows what comes back. The class profile it sends is
// class-level counts only, never a child.
import { API_BASE } from "./api";
import type { ProfileRow } from "./db";

export type PaperRole = "teacher" | "coach";
export type Lang = "en" | "hi" | "ta";
export const LANGS: Lang[] = ["en", "hi", "ta"];
/** A paper's languages: one, or two (each line in the first, then in the second). */
export type Layout = Lang | `${Lang}_${Lang}`;
export const LAYOUTS: Layout[] = ["en", "hi", "ta", "en_hi", "en_ta", "hi_en", "hi_ta", "ta_en", "ta_hi"];

export function layoutOf(first: Lang, second: Lang | ""): Layout {
  return second && second !== first ? (`${first}_${second}` as Layout) : first;
}

/** "हिन्दी + English": the languages of a layout, by name. */
export function layoutName(tr: (k: never) => string, layout: string): string {
  return layout
    .split("_")
    .map((l) => tr(`papers.lang.${l}` as never))
    .join(" + ");
}
export const CODES = ["PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"] as const;
export const SKILLS = ["C1", "C2", "C3"] as const;
export type Skill = (typeof SKILLS)[number];

export interface PaperItem {
  n: number;
  slot: number;
  template: string;
  competency: string;
  section: string;
  operation: "dictate" | "add" | "subtract";
  a: number;
  b: number;
  correct: number;
  wrong: Record<string, number[]>;
  untracked: Record<string, number[]>;
  is_anchor: boolean;
  difficulty: number | null;
  twin_of: number | null;
  why?: { key: string; skill?: string; codes?: string[]; params: Record<string, string | number> }[];
}

export interface Finding {
  rule: string;
  item: number | null;
  detail: string;
}

export interface Paper {
  id: string;
  check_id: string;
  check_code: string;
  form: string;
  kind: string;
  language: Layout;
  status: "auto_approved" | "queued" | "approved" | "rejected" | "draft";
  printable: boolean;
  frozen: boolean;
  custom: boolean;
  blueprint: string;
  rules_version: number;
  seed: string;
  hash: string;
  twin_of: string | null;
  profile_source: "past" | "intake" | "baseline";
  not_assessed: string[];
  coverage: Record<string, number[]>;
  items: PaperItem[];
  findings: Finding[];
  approved_by: string | null;
  rejected_reason: string | null;
}

export interface QueueRow {
  queue_id: number;
  reason: "custom" | "failed_check" | "unreviewed_words" | "spot_check";
  since: string;
  paper: Paper;
}

export interface RuleVersion {
  number: number;
  status: "draft" | "in_review" | "published" | "retired";
  author: string;
  approver: string | null;
  diff: string[];
  note: string;
  hash: string;
  published_at: string | null;
  body?: { templates: { id: string; competency: string; skill: string; digit_pattern: string; operation: string; bugs: string[]; retired: boolean }[]; blueprints: { id: string; title: string }[] };
}

export interface ProfileSpec {
  source: "past" | "intake" | "baseline";
  counts?: Record<string, number>;
  checked?: number;
  built_from?: string[];
  struggles?: Skill[];
  taught?: Skill[];
  strength?: number | null;
  similar_test?: boolean | null;
}

export class PaperError extends Error {
  constructor(
    public status: number,
    public detail: unknown = null,
  ) {
    super(`papers ${status}`);
  }
  /** The rule a refused paper broke, when the server named one. */
  get rule(): string {
    const d = this.detail as { rule?: unknown } | null;
    return d && typeof d === "object" && typeof d.rule === "string" ? d.rule : "";
  }
  get explanation(): string {
    const d = this.detail as { explanation?: unknown } | string | null;
    if (typeof d === "string") return d;
    return d && typeof d.explanation === "string" ? d.explanation : "";
  }
}

export async function pcall<T>(path: string, role: PaperRole, init: { method?: string; body?: unknown; person?: "a" | "b" } = {}, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<T> {
  const headers: Record<string, string> = { "X-Role": role };
  if (init.person) headers["X-Demo-Person"] = init.person;
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}${path}`, { method: init.method ?? "GET", headers, body: init.body === undefined ? undefined : JSON.stringify(init.body) });
  } catch {
    throw new PaperError(0);
  }
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
    } catch {
      /* no body */
    }
    throw new PaperError(res.status, detail);
  }
  return (await res.json()) as T;
}

/** The class profile to send: the latest check's class counts if it checked enough children, else what she told
 *  us in the intake form, else the standard paper. Counts only. */
export const MIN_PAST_CHILDREN = 10; // the product's own minimum for reading a class from one check

/** A past check says something about the class only when enough children were checked. */
export function pastUsable(latest: ProfileRow | null | undefined): boolean {
  return !!latest && latest.childrenChecked >= MIN_PAST_CHILDREN;
}

export function profileFrom(latest: ProfileRow | null | undefined, intake: ProfileSpec | null): ProfileSpec {
  if (latest && pastUsable(latest)) {
    return { source: "past", counts: { ...latest.counts }, checked: latest.childrenChecked, built_from: [latest.id] };
  }
  return intake ?? { source: "baseline" };
}

/** Rows of the coverage grid: for each error code, which item numbers probe it. */
export function coverageGrid(p: Pick<Paper, "coverage" | "items" | "not_assessed">): { code: string; items: Set<number>; count: number; assessed: boolean }[] {
  const skillOf: Record<string, string> = { "PV-HEARD": "C1", "PV-REVERSE": "C1", "ADD-NOCARRY": "C2", "SUB-SFL": "C3", "SUB-NODEC": "C3" };
  return CODES.map((code) => {
    const items = new Set(p.coverage[code] ?? []);
    return { code, items, count: items.size, assessed: !p.not_assessed.includes(skillOf[code] ?? "") };
  });
}

/** "3. 77 + 18" or "1. (say aloud: 346)" for the on-screen preview. */
export function itemText(it: PaperItem, say: string): string {
  if (it.operation === "dictate") return `${say}: ${it.a}`;
  return `${it.a} ${it.operation === "add" ? "+" : "−"} ${it.b}`;
}

/** Fetch a PDF with the role header and hand back an object URL to open or print. */
export async function pdfUrl(paperId: string, what: "paper" | "key", layout: Layout, role: PaperRole, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<string> {
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/papers/${encodeURIComponent(paperId)}/${what}.pdf?layout=${layout}`, { headers: { "X-Role": role } });
  } catch {
    throw new PaperError(0);
  }
  if (!res.ok) throw new PaperError(res.status);
  return URL.createObjectURL(await res.blob());
}

/** The sample paper for this class: the published numbers the judge's sample sheets and photos were
 *  made on, stored on the server as an ordinary paper (pre-test, or its post-test twin for a post-test). */
export async function samplePaper(checkId: string, kind: string, classLabel: string, term: number, language: string): Promise<Paper> {
  const out = await pcall<{ paper: Paper }>("/api/papers/generate", "teacher", {
    method: "POST",
    body: { check: { id: checkId, kind: kind === "post" ? "post" : "pre", form: kind === "post" ? "B" : "A", class_label: classLabel, term }, language, sample: true },
  });
  return out.paper;
}
