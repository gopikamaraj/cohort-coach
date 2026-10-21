// Watch mode client: asks the server for a run and plays it back. A run is plain data (the live
// system's own transcript, or a recorded run labelled as such); nothing here decides or computes.
import { API_BASE } from "./api";

export type Style = "experienced" | "struggling";

export interface MoveTag {
  id: string;
  label: string;
  quality: "strong" | "common_mistake" | "neutral";
  strategy: boolean;
}
export interface ChildMeter {
  name: string;
  level: number;
  band: "high" | "medium" | "low";
  has_error: boolean;
}
export interface Machinery {
  code: { move: { move_id: string; source?: string }; engine: Record<string, unknown> };
  ai_calls: { call: number; name: string; source: string; latency_ms: number | null }[];
  validators: { name: string; ok: boolean }[];
  checker: { passed: boolean } | null;
  fallback: string | null;
}
export interface WatchTurn {
  turn: number;
  teacher: { line: string; move: MoveTag; source: string; label: string };
  child: { speaker: string | null; text: string; text_en: string; intent: string; badge: string; written: number | null; said: number | null };
  children: ChildMeter[];
  machinery: Machinery;
  latency_ms: number;
}
export interface WatchRun {
  kind: "live run" | "recorded run";
  reason: string | null;
  provenance: { style: Style; language: string; seed: number; recorded_at?: string; cost_usd: number };
  turns: WatchTurn[];
  feedback: {
    strengths: { point: string; text: string; quote: string; turn: number; comment: string }[];
    try_next: { point: string; text: string; suggestion: string; quote: string | null; turn: number | null };
    note: string | null;
    badge: string;
  };
  summary: { turns: number; moves_used: number; rubric_points_touched: number; rubric_points: number };
}
export interface Meter {
  live_runs_this_hour: number;
  cap_per_hour: number;
  cost_usd_this_hour: number;
}

export async function fetchRun(
  style: Style,
  language: string,
  live: boolean,
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<WatchRun> {
  const res = await fetchFn(`${API_BASE}/api/practice/watch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario: "SUB-SFL", style, language, live }),
  });
  if (!res.ok) throw new Error(`watch ${res.status}`);
  return (await res.json()) as WatchRun;
}

export async function fetchMeter(fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<Meter | null> {
  try {
    const res = await fetchFn(`${API_BASE}/api/practice/watch/meter`);
    return res.ok ? ((await res.json()) as Meter) : null;
  } catch {
    return null;
  }
}

/** Playback: which turn is showing, given the speed and the clock. Pure, so it can be tested. */
export interface Playback {
  index: number; // number of turns shown
  playing: boolean;
  speed: 1 | 2;
}

export const TURN_MS = 3200;

export function nextPlayback(p: Playback, total: number, action: "tick" | "pause" | "play" | "step" | "fast" | "skip"): Playback {
  switch (action) {
    case "tick":
      return p.playing && p.index < total ? { ...p, index: p.index + 1, playing: p.index + 1 < total } : p;
    case "pause":
      return { ...p, playing: false };
    case "play":
      return { ...p, playing: p.index < total };
    case "step":
      return { ...p, playing: false, index: Math.min(total, p.index + 1) };
    case "fast":
      return { ...p, speed: p.speed === 1 ? 2 : 1 };
    case "skip":
      return { ...p, playing: false, index: total };
  }
}
