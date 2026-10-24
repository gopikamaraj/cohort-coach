// Pilot mode's API calls. Every call carries the sign-in token in a header; nothing is cookie-based.
// A call that cannot reach the server throws PilotApiError(0) so the caller can queue instead.
import { API_BASE } from "../lib/api";

const TOKEN_KEY = "cc.pilot.session";

export interface Session {
  token: string;
  name: string;
  roles: string[];
}

export class PilotApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown = null,
  ) {
    super(`pilot api ${status}`);
  }
  get offline(): boolean {
    return this.status === 0;
  }
  /** The server's reason code for a 409 such as { reason: "no_sheets" }, if it sent one. */
  get reason(): string | null {
    const d = this.detail as { reason?: unknown } | null;
    return d && typeof d === "object" && typeof d.reason === "string" ? d.reason : null;
  }
}

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as Session;
    return typeof s.token === "string" && typeof s.name === "string" && Array.isArray(s.roles) ? s : null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session | null): void {
  try {
    if (session) localStorage.setItem(TOKEN_KEY, JSON.stringify(session));
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode: the session just does not persist */
  }
}

const endListeners = new Set<() => void>();

/** Called when the server says the sign-in has ended (a 401), so the app can ask to sign in again. */
export function onSessionEnded(listener: () => void): () => void {
  endListeners.add(listener);
  return () => endListeners.delete(listener);
}

export function resolveUrl(url: string): string {
  return url.startsWith("/") ? `${API_BASE}${url}` : url;
}

export async function pilotFetch(
  path: string,
  init: RequestInit = {},
  session: Session | null,
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (session) headers.set("Authorization", `Bearer ${session.token}`);
  let res: Response;
  try {
    res = await fetchFn(resolveUrl(path), { ...init, headers });
  } catch {
    throw new PilotApiError(0);
  }
  if (res.status === 401 && session) endListeners.forEach((l) => l());
  return res;
}

export async function pilotJson<T>(
  path: string,
  init: RequestInit,
  session: Session | null,
  fetchFn?: typeof fetch,
): Promise<T> {
  const res = await pilotFetch(path, init, session, fetchFn);
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
    } catch {
      /* no body */
    }
    throw new PilotApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export function jsonInit(method: string, body?: unknown): RequestInit {
  return body === undefined
    ? { method }
    : { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

// ---- shapes the server returns --------------------------------------------------------------

export interface Config {
  audio_count: number;
  audio_default: number;
  audio_max: number;
  retention_days: number;
  retention_range: [number, number];
  languages: string[];
  voices: { id: string; label: string; kind: string }[];
  voice_default: string;
  share_link_hours: number;
}

export interface Summary {
  uploaded: number;
  read: number;
  needs_look: number;
  waiting: number;
  teachers: string[];
  schools: string[];
}

export type AudioStatus = "draft" | "needs_review" | "approved" | "audio_ready" | "failed";

export interface Card {
  id: string;
  slot: number;
  language: string;
  version: number;
  title: string;
  script: string;
  voice: string;
  status: AudioStatus;
  note: string | null;
  duration_s: number;
  bytes: number;
  active: boolean;
  stale: boolean;
  ready: boolean;
  file_name: string;
  mime: string;
  created_at: string;
  shared_with: string[];
  versions: { id: string; version: number; status: AudioStatus; ready: boolean }[];
}

export interface AudioPage {
  cards: Card[];
  audio_count: number;
  sheets_read: number;
  classes_read: number;
}

export function canDo(session: Session | null, role: string): boolean {
  return !!session && session.roles.includes(role);
}
