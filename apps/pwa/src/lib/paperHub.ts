// The Papers page's API calls: import from a PDF, the scoped list and detail, assignments. The
// server decides who may do what and computes every answer; this file sends and shows. Counts only.
import { API_BASE } from "./api";
import { deviceId } from "./consent";

export type HubRole = "teacher" | "mentor" | "coach";

import type { WhyLine } from "../components/WhyLines";

export class HubError extends Error {
  constructor(
    public status: number,
    public detail: unknown = null,
  ) {
    super(`hub ${status}`);
  }
  get explanation(): string {
    const d = this.detail;
    return typeof d === "string" ? d : "";
  }
}

export interface HubIdentity {
  role: HubRole;
  classId: string | null;
}

export async function hcall<T>(path: string, who: HubIdentity, init: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = { "X-Role": who.role };
  if (who.classId) headers["X-Class-Id"] = who.classId;
  headers["X-Device-Id"] = deviceId();
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/paper-hub${path}`, { method: init.method ?? (init.body !== undefined || init.form ? "POST" : "GET"), headers, body: init.form ?? (init.body === undefined ? undefined : JSON.stringify(init.body)) });
  } catch {
    throw new HubError(0);
  }
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
    } catch {
      /* no body */
    }
    throw new HubError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function hblob(path: string, who: HubIdentity): Promise<Blob> {
  const headers: Record<string, string> = { "X-Role": who.role, "X-Device-Id": deviceId() };
  if (who.classId) headers["X-Class-Id"] = who.classId;
  const res = await fetch(`${API_BASE}/api/paper-hub${path}`, { headers });
  if (!res.ok) throw new HubError(res.status);
  return res.blob();
}

export interface DraftItem {
  n: number;
  operation: "dictate" | "add" | "subtract" | "other";
  a: number | null;
  b: number | null;
  supported: boolean;
  reason: string | null;
  include: boolean;
  unsure: boolean;
  disagreement?: boolean;
  from_guide?: boolean;
  from_key?: boolean;
  key_file?: number;
  key_mismatch: boolean;
  correct: number | null;
  competency: string | null;
  skill: string | null;
  error_probes: string[];
  wrong: Record<string, number[]>;
}

export interface OpenQuestion {
  id: string;
  why: string;
  options: string[] | null;
  blocking: boolean;
  field: string;
}

export interface Draft {
  header: { form_letter: string | null; check_code: string | null; class_code: string | null };
  language: string;
  contains_handwritten_answers: boolean;
  sheets_read: number;
  items: DraftItem[];
  class_id: string | null;
  kind: string | null;
  form: string | null;
  coverage: Record<string, number[]>;
  coverage_warnings: string[];
  open_questions: OpenQuestion[];
  changes?: Record<string, { old: unknown; via: "user" | "assistant" }>;
}

export interface ImportView {
  id: string;
  status: string;
  pages: number;
  expires_at: string;
  paper_id: string | null;
  draft: Draft;
  can_undo: boolean;
  blocking: string[];
  reuses?: string[]; // pre-tests whose number pairs a post-test repeats
  note: string;
}

export interface HubPaper {
  id: string;
  twin_of?: string | null;
  rules_version?: number;
  title: string;
  check_code: string;
  class_id: string;
  form: string;
  kind: string;
  language: string;
  items: number;
  status: string;
  source: "generated" | "imported_pdf";
  review: "awaiting_review" | "in_queue" | "none";
  frozen: boolean;
  frozen_reason: string | null;
  printable: boolean;
  phone_form: string | null;
  cohorts: { formed: boolean; count: number; reason: string };
  assignments: { assigned: number; opened: number; completed: number };
  created_by: string;
}

export interface Assignment {
  id: string;
  paper_id: string;
  class_id: string;
  cohort_id: string | null;
  kind: string;
  form: string;
  start_date: string | null;
  due_date: string | null;
  status: string;
  note: string;
  sheets_entered: number;
  sheets_expected: number;
}

export interface Assignable {
  classes: string[];
  cohorts: { id: string; error: string; status: string; classes: number }[];
  note: string;
}

export interface PaperDetailData {
  overview: HubPaper;
  questions: { n: number; operation: string; a: number; b: number; correct: number; competency: string; wrong: Record<string, number[]>; why?: WhyLine[] }[];
  editable: boolean;
  edit_mode: "in_place" | "new_version";
  deletable: boolean;
  in_use: string | null;
  locked_reason: string | null;
  coverage: Record<string, number[]>;
  usage: { assignments: { id: string; kind: string; status: string; due_date: string | null; sheets_entered: number; sheets_expected: number }[] };
  history: { at: string; event: string; actor: string; detail: string }[];
  files: { paper_pdf: boolean; key_pdf: boolean; layout: string; imported: boolean };
}

/** The edit that answers an open question, as the field and value the server's whitelist accepts. */
export function editFor(q: OpenQuestion, answer: string | number | boolean): { field: string; value: string | number | boolean }[] {
  if (q.id.startsWith("unsupported-")) {
    return answer === "leave_out" ? [{ field: `items.${q.id.slice(12)}.include`, value: false }] : [];
  }
  if (q.id.startsWith("key-")) return answer === "use_computed" ? [{ field: `items.${q.id.slice(4)}.acknowledged`, value: true }] : [];
  return [{ field: q.field, value: answer }];
}
