// The review queue's API calls (P3). The server decides who may do what; the screen only sends the
// role the person is acting as in the judge deployment (X-Role) and shows what comes back.
import { API_BASE } from "./api";

export type QueueRole = "coach" | "officer";

export interface ItemSummary {
  item_id: string;
  content_type: string;
  language: string;
  kind: string;
  day: number;
  status: string;
  age_hours: number;
  explanation: string;
  track_id: string;
}

export interface Check {
  name: string;
  ok: boolean;
  codes: string[];
  details: string[];
}

export interface ItemDetail {
  item_id: string;
  status: string;
  badge: string;
  language: string;
  kind: string;
  day: number;
  script: string;
  original_script: string | null;
  results: Check[];
  slots_used: string[];
  strategies: string[];
  explanation: string;
  content_status: string;
  method_card_id: string | null;
  history: Record<string, unknown>[];
}

export interface Version {
  id: string;
  content_type: string;
  content_id: string;
  version: number;
  status: "draft" | "in_review" | "approved" | "active" | "retired";
  parent_version: number | null;
  coach_approved_by: string | null;
  officer_activated_by: string | null;
}

export interface AuditRow {
  at: string;
  role: string;
  actor: string;
  action: string;
  content_type: string;
  content_id: string;
  version: number;
  detail: Record<string, unknown>;
}

export const REASONS = ["wrong_maths", "culturally_off", "too_complex_for_medium", "tone_issue", "factually_shaky"] as const;
export type Reason = (typeof REASONS)[number];

export class QueueError extends Error {
  constructor(
    public status: number,
    public detail: unknown = null,
  ) {
    super(`queue ${status}`);
  }
  /** The server's one-line reason for a refused edit, if it gave one. */
  get explanation(): string {
    const d = this.detail as { explanation?: unknown } | string | null;
    if (typeof d === "string") return d;
    return d && typeof d.explanation === "string" ? d.explanation : "";
  }
}

export async function qcall<T>(
  path: string,
  role: QueueRole,
  init: { method?: string; body?: unknown } = {},
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<T> {
  const headers: Record<string, string> = { "X-Role": role };
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/review${path}`, {
      method: init.method ?? "GET",
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch {
    throw new QueueError(0);
  }
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
    } catch {
      /* no body */
    }
    throw new QueueError(res.status, detail);
  }
  return (await res.json()) as T;
}

/** "5 hours" or "2 days": the age a row shows, from the hours the server computed. */
export function ageParts(hours: number): { unit: "hours" | "days"; n: number } {
  return hours < 48 ? { unit: "hours", n: Math.max(0, Math.round(hours)) } : { unit: "days", n: Math.round(hours / 24) };
}

/** Oldest first, as the screen lists them (nothing waits unseen). */
export function oldestFirst<T extends { age_hours: number }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => b.age_hours - a.age_hours);
}

/** Why a version cannot be switched on yet: only a coach-approved one can be. */
export function canActivate(v: Pick<Version, "status">): boolean {
  return v.status === "approved";
}

export function canApprove(v: Pick<Version, "status">): boolean {
  return v.status === "in_review";
}
