// The judge's Testing evidence: the shape the server returns, and the call. The server counts
// everything; this file only fetches it and picks the funnel label keys.
import { API_BASE } from "./api";

export interface Evidence {
  include_flagged: boolean;
  cards: {
    testers: number;
    sessions: number;
    returning_testers: number;
    roles_tried_avg: number | null;
    tours_completed: number;
    feedback_received: number;
    average_rating: number | null;
    offline_share: number | null;
    date_from: string | null;
    date_to: string | null;
  };
  testers_by_day: { day: string; testers: number }[];
  role_funnel: { stage: string; testers: number }[];
  tour_funnel: { stage: string; testers: number }[];
  by_source: { label: string; testers: number }[];
  device_class: { label: string; testers: number }[];
  language: { label: string; testers: number }[];
  testers: {
    name: string;
    listed: boolean;
    hash6: string;
    roles_tried: number;
    tours_completed: number;
    features_used: number;
    sessions: number;
    last_seen: string;
    rating: number | null;
  }[];
  feedback: { rating: number; role: string | null; screen_id: string | null; tags: string[]; comment: string | null; day: string }[];
  changes: { date: string; feedback: string; change: string; commit: string | null }[];
  excluded: { judge_devices: number; team_devices: number };
}

export async function loadEvidence(includeFlagged: boolean, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<Evidence> {
  const res = await fetchFn(`${API_BASE}/api/judge/testing-evidence?include_flagged=${includeFlagged}`, { headers: { "X-Role": "judge" } });
  if (!res.ok) throw new Error(`testing-evidence ${res.status}`);
  return (await res.json()) as Evidence;
}

/** "step_3" -> {key: "step", n: 3}; the other stages are plain keys. */
export function stageLabel(stage: string): { key: "selected" | "screen" | "feature" | "started" | "completed" | "skipped" | "step"; n?: number } {
  const m = /^step_(.+)$/.exec(stage);
  if (m) return { key: "step", n: Number(m[1]) };
  return { key: stage as "selected" | "screen" | "feature" | "started" | "completed" | "skipped" };
}

export const percent = (share: number): string => `${Math.round(share * 100)}%`;
