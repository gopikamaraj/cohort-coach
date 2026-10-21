// The Practice Class client. Each turn goes to the API (the one live feature); the transcript is
// kept in IndexedDB on this phone and is sent nowhere else.
import { API_BASE } from "./api";
import { db, type CohortDb } from "./db";

export interface PracticeChild {
  name: string;
  shy: boolean;
}

export interface PracticeMove {
  id: string;
  label: string;
  examples: string[]; // things she could say, in her language (empty for a move that is never cued)
}

export interface CreatedSession {
  session_id: string;
  seed: number;
  language: string;
  judge: boolean;
  children: PracticeChild[];
  materials: string[];
  turn_cap: number;
  goal: { error: string; tips: string[] };
  voice: { available: boolean; mode: string };
  moves: PracticeMove[];
}

export interface Layers {
  input: { teacher_text: string | null; material: string | null; stt_confidence: number | null };
  processing: {
    label: { move_id: string; addressed?: string | null; confidence?: number; forced?: string | null; source?: string };
    posed_problem: { kind: string; a: number; b: number } | null;
    engine: {
      speaker: string | null;
      intent: string;
      answer: number | null;
      correct: boolean | null;
      error_code: string | null;
      problem: { kind: string; a: number; b: number } | null;
      steps: { op: string; numbers: number[] }[];
      mood: string;
      strength_before: Record<string, number>;
      strength_after: Record<string, number>;
    };
  };
  guardrails: {
    validators: { name: string; ok: boolean; codes: string[] }[];
    checker: { passed: boolean; failed_items: string[] } | null;
    retries: number;
    fallback_used: string | null;
  };
  evaluation: {
    latency_ms: number;
    tokens: { in: number; out: number; cache_read: number };
    cost_usd: number;
    calls: string[];
    stages?: { stt_ms: number; tts_wait_ms: number };
    call_ms?: { label?: number; child?: number; check?: number };
  };
  output: { child_line: string; source: string; badge: string };
}

export interface TurnResponse {
  turn: number;
  speaker: string | null;
  child_text: string;
  intent: string;
  numbers: number[];
  badge: string;
  explanation: string;
  layers: Layers;
  latency_ms: number;
  finished: boolean;
  finished_reason: string | null;
  turns_left: number;
  child_text_en?: string;
  move?: { id: string; label: string; quality: string; strategy: boolean };
  children?: { name: string; level: number; band: "high" | "medium" | "low"; has_error: boolean }[];
}

export interface FeedbackCard {
  strengths: { point: string; text: string; comment: string; quote: string; turn_id: number }[];
  try_next: { point: string; text: string; suggestion: string; quote: string | null; turn_id: number | null };
  note: string | null;
  source: string;
  badge: string;
}

export interface EndResponse {
  card: FeedbackCard;
  layers: Record<string, unknown>;
  transcript: { turn: number; teacher: string; child: string; speaker: string | null }[];
  explanation: string;
}

export type FailKind = "paused" | "expired" | "finished" | "offline" | "invalid" | "voice" | "unheard" | "other";

export class PracticeError extends Error {
  constructor(
    public kind: FailKind,
    public status: number,
  ) {
    super(kind);
  }
}

const TIMEOUT_MS = 25_000;

async function call<T>(path: string, body: unknown, fetchFn: typeof fetch): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: ctrl.signal,
    });
  } catch {
    throw new PracticeError("offline", 0); // no signal, or too slow: she can try again
  } finally {
    clearTimeout(timer);
  }
  if (res.ok) return (await res.json()) as T;
  const kind: FailKind = res.status === 503 ? "paused" : res.status === 404 ? "expired" : res.status === 409 ? "finished" : res.status === 422 ? "invalid" : "other";
  throw new PracticeError(kind, res.status);
}

export interface CreateOptions {
  scenario: string;
  language: string;
  judge: boolean;
  counts?: Record<string, number>;
  checked?: number;
  seed?: number;
}

export function createSession(opts: CreateOptions, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<CreatedSession> {
  return call("/api/practice/sessions", opts, fetchFn);
}

export function postTurn(
  sessionId: string,
  body: { text?: string; material?: string },
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<TurnResponse> {
  return call(`/api/practice/sessions/${sessionId}/turns`, body, fetchFn);
}

export function endSession(sessionId: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<EndResponse> {
  return call(`/api/practice/sessions/${sessionId}/end`, undefined, fetchFn);
}

/** The error to rehearse for a class: its focus if it has one a scenario exists for, else SUB-SFL. */
export function scenarioFor(track: string | null): string {
  return track && ["PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"].includes(track) ? track : "SUB-SFL";
}

// --- the transcript: on this phone only ---------------------------------------------------

export async function startTranscript(
  sessionId: string,
  classId: string,
  scenario: string,
  store: CohortDb = db,
  meta: { language?: string; seed?: number } = {},
): Promise<number> {
  return store.transcripts.add({ classId, createdAt: Date.now(), turns: [], sessionId, scenario, ended: false, ...meta });
}

export async function appendTurn(
  rowId: number,
  entry: { turn: number; teacher: string; child: string; speaker: string | null; move?: string },
  store: CohortDb = db,
): Promise<void> {
  const row = await store.transcripts.get(rowId);
  if (!row) return;
  await store.transcripts.update(rowId, { turns: [...row.turns, entry] });
}

export async function finishTranscript(rowId: number, card: FeedbackCard, store: CohortDb = db): Promise<void> {
  await store.transcripts.update(rowId, { ended: true, card, endedAt: Date.now() });
}
