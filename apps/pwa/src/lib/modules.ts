// Improvement-track modules: the calls to the server and the types of what it sends back. The server decides
// which module comes next and holds every module and answer; this phone shows them. The last view read is kept
// per track only so the module text and downloaded audio still open when the phone is offline; it is replaced
// by the server's view whenever the phone is online, and it holds no child, no name and no roll number.
import { writeOrQueue } from "./cloudStore";
import { userHeader } from "./identity";
import { API_BASE } from "./api";

export type ModuleStatus = "planned" | "ready" | "downloaded" | "feedback_given" | "completed" | "skipped" | "expired";
export type Answer = "worked" | "partly" | "not_yet" | "not_tried";
export const CHIPS = ["no_time", "materials", "not_sure", "absent", "other"] as const;
export type Chip = (typeof CHIPS)[number];
export type NextCode = "ok" | "needs_feedback" | "no_more" | "track_cap" | "track_exhausted" | "track_done" | "track_end_date";

export interface TextPart {
  id: "smaller_step" | "purpose" | "materials" | "steps" | "example" | "check";
  text?: string;
  list?: string[];
  fallback: boolean;
  draft: boolean;
}

export interface ModuleView {
  number: number;
  status: ModuleStatus;
  title: string;
  due_date: string;
  branch: string | null;
  text?: { language: string; parts: TextPart[]; smaller: boolean };
  language?: string;
  reason?: { code: string; n: number; prev: number } | null;
  reason_text?: string;
  generated_by?: string | null;
  audio_ref?: string | null;
  played?: boolean; // she started the audio in the browser player (system: the player started)
  feedback?: { answer: Answer; note: string } | null;
  hold?: { deferrals: number; max: number; days: number; short: { parts: TextPart[] } | null };
  spoken?: string;
}

export interface TrackView {
  id: string;
  cohort_id: string;
  error: string;
  status: "active" | "completed" | "stopped";
  stop_reason: string | null;
  start_date: string;
  end_date: string;
  language: string;
  note: string | null;
  total: number;
  current: number;
  can_next: { enabled: boolean; code: NextCode; number?: number; next?: number; due_date?: string };
  modules: ModuleView[];
}

/** The write could not go now (no connection); it waits in the outbox and is sent when she is online. */
export class QueuedForLater extends Error {
  constructor() {
    super("queued");
  }
}

export class ModuleError extends Error {
  constructor(
    public status: number,
    public code = "",
  ) {
    super(`modules ${status} ${code}`);
  }
}

async function call<T>(path: string, init: { method?: string; body?: unknown; role?: "teacher" | "coach" } = {}, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<T> {
  const role = init.role ?? "teacher";
  const headers: Record<string, string> = { "Content-Type": "application/json", "X-Role": role, ...userHeader() };
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/modules${path}`, { method: init.method ?? "GET", headers, body: init.body === undefined ? undefined : JSON.stringify(init.body) });
  } catch {
    throw new ModuleError(0);
  }
  if (!res.ok) {
    let code = "";
    try {
      code = ((await res.json()) as { detail?: { code?: string } }).detail?.code ?? "";
    } catch {
      /* no body */
    }
    throw new ModuleError(res.status, code);
  }
  return (await res.json()) as T;
}

const cacheKey = (cohortId: string, error: string) => `cc.track.${cohortId}.${error}`;

function readCache(cohortId: string, error: string): TrackView | null {
  try {
    const raw = localStorage.getItem(cacheKey(cohortId, error));
    return raw ? (JSON.parse(raw) as TrackView) : null;
  } catch {
    return null;
  }
}

function writeCache(view: TrackView): void {
  try {
    localStorage.setItem(cacheKey(view.cohort_id, view.error), JSON.stringify(view));
  } catch {
    /* private window: nothing is kept */
  }
}

function dropCache(cohortId: string, error: string): void {
  try {
    localStorage.removeItem(cacheKey(cohortId, error));
  } catch {
    /* nothing to drop */
  }
}

/** Her track for this error: from the server when online (and the phone's copy is replaced); the last copy
 *  only when the server cannot be reached. `null` means she has not started one. */
export async function loadTrack(cohortId: string, error: string, lang: string, fetchFn?: typeof fetch): Promise<{ track: TrackView | null; offline: boolean }> {
  try {
    const all = await call<TrackView[]>(`/tracks?cohort_id=${encodeURIComponent(cohortId)}&lang=${lang}`, {}, fetchFn);
    const mine = all.find((t) => t.error === error) ?? null;
    if (mine) writeCache(mine);
    else dropCache(cohortId, error);
    return { track: mine, offline: false };
  } catch (e) {
    if (e instanceof ModuleError && e.status > 0) throw e;
    return { track: readCache(cohortId, error), offline: true };
  }
}

async function remember(view: TrackView): Promise<TrackView> {
  writeCache(view);
  return view;
}

export async function startTrack(cohortId: string, error: string, lang: string, fetchFn?: typeof fetch): Promise<TrackView> {
  return remember(await call<TrackView>("/tracks", { method: "POST", body: { cohort_id: cohortId, error, language: lang } }, fetchFn));
}

export async function getNext(trackId: string, lang: string, fetchFn?: typeof fetch): Promise<TrackView> {
  return remember(await call<TrackView>(`/tracks/${trackId}/next?lang=${lang}`, { method: "POST" }, fetchFn));
}

export async function sendFeedback(trackId: string, number: number, answer: Answer, note: string, lang: string, fetchFn?: typeof fetch): Promise<TrackView> {
  const path = `/tracks/${trackId}/modules/${number}/feedback?lang=${lang}`;
  try {
    return remember(await call<TrackView>(path, { method: "POST", body: { answer, note } }, fetchFn));
  } catch (e) {
    if (!(e instanceof ModuleError && e.status === 0)) throw e;
    // no connection: her answer is kept in the outbox and sent when she is online
    await writeOrQueue(`module ${number} feedback`, "POST", `/api/modules${path}`, { answer, note }, { "X-Role": "teacher" });
    throw new QueuedForLater();
  }
}

export async function sendWhyNot(trackId: string, number: number, chip: Chip, lang: string, fetchFn?: typeof fetch): Promise<TrackView> {
  return remember(await call<TrackView>(`/tracks/${trackId}/modules/${number}/why?lang=${lang}`, { method: "POST", body: { chip } }, fetchFn));
}

export interface ReviewView {
  state: "none" | "asked" | "answered" | "skipped" | "safety" | "failed";
  follow_ups: { id: string; kind: "bank" | "free"; text: string; chips: { id: string; label: string }[] }[];
  safety: boolean;
  changes: string | null; // "What changes next", written by code from the validated tags
}

/** After her answer: the AI review of her note. Never blocks: any failure reads as "no questions". */
export async function runReview(trackId: string, number: number, lang: string, fetchFn?: typeof fetch): Promise<ReviewView> {
  try {
    return await call<ReviewView>(`/tracks/${trackId}/modules/${number}/review?lang=${lang}`, { method: "POST" }, fetchFn);
  } catch {
    return { state: "none", follow_ups: [], safety: false, changes: null };
  }
}

export async function answerReview(trackId: string, number: number, answers: { id: string; chip?: string; text?: string }[], skip: boolean, lang: string, fetchFn?: typeof fetch): Promise<ReviewView> {
  return call<ReviewView>(`/tracks/${trackId}/modules/${number}/review/answers?lang=${lang}`, { method: "POST", body: { answers, skip } }, fetchFn);
}

export async function markDownloaded(trackId: string, number: number, audioRef: string, lang: string, fetchFn?: typeof fetch): Promise<TrackView> {
  const path = `/tracks/${trackId}/modules/${number}/downloaded?lang=${lang}`;
  try {
    return remember(await call<TrackView>(path, { method: "POST", body: { audio_ref: audioRef } }, fetchFn));
  } catch (e) {
    if (!(e instanceof ModuleError && e.status === 0)) throw e;
    await writeOrQueue(`module ${number} downloaded`, "POST", `/api/modules${path}`, { audio_ref: audioRef }, { "X-Role": "teacher" });
    throw new QueuedForLater();
  }
}

/** She started a module's audio in the browser player. With no connection it waits in the outbox. */
export async function markPlayed(trackId: string, number: number, lang: string, fetchFn?: typeof fetch): Promise<TrackView | null> {
  const path = `/tracks/${trackId}/modules/${number}/played?lang=${lang}`;
  try {
    return await remember(await call<TrackView>(path, { method: "POST" }, fetchFn));
  } catch (e) {
    if (!(e instanceof ModuleError && e.status === 0)) throw e;
    await writeOrQueue(`module ${number} played`, "POST", `/api/modules${path}`, undefined, { "X-Role": "teacher" });
    return null;
  }
}

/** Testing only (DEV_TESTING=1): make every module that is still planned, without feedback. */
export async function generateAllModules(trackId: string, lang: string, fetchFn?: typeof fetch): Promise<TrackView> {
  return remember(await call<TrackView>(`/tracks/${trackId}/generate-all?lang=${lang}`, { method: "POST" }, fetchFn));
}

/** Testing only (DEV_TESTING=1): word the module's script again; `reworded` says whether call 18's wording is stored. */
export async function refreshNarration(trackId: string, number: number, lang: string, fetchFn?: typeof fetch): Promise<{ reworded: boolean; track: TrackView }> {
  const r = await call<{ reworded: boolean; track: TrackView }>(`/tracks/${trackId}/modules/${number}/narration/refresh?lang=${lang}`, { method: "POST" }, fetchFn);
  return { reworded: r.reworded, track: await remember(r.track) };
}

// ---- the coach: counts only ------------------------------------------------------------------------------

export interface CoachModule {
  number: number;
  at: number;
  generated: number;
  downloaded: number;
  feedback: Record<Answer, number>;
  overdue: number;
  failed: number;
  not_downloaded_flag: number;
}

export interface CoachModules {
  cohort_id: string;
  tracks: number;
  modules: CoachModule[];
  stopped: { cap: number; exhausted: number };
  moved?: number;
  generated?: number;
  call_me?: number;
}

export async function coachModules(cohortId: string, fetchFn?: typeof fetch): Promise<CoachModules> {
  return call<CoachModules>(`/coach/cohorts/${encodeURIComponent(cohortId)}`, { role: "coach" }, fetchFn);
}

export async function coachShift(cohortId: string, days: number, reason: string, fetchFn?: typeof fetch): Promise<CoachModules> {
  return call<CoachModules>(`/coach/cohorts/${encodeURIComponent(cohortId)}/shift`, { method: "POST", role: "coach", body: { days, reason } }, fetchFn);
}

export async function coachGenerate(cohortId: string, fetchFn?: typeof fetch): Promise<CoachModules> {
  return call<CoachModules>(`/coach/cohorts/${encodeURIComponent(cohortId)}/generate`, { method: "POST", role: "coach" }, fetchFn);
}

/** The reason a "Get the next module" button is closed, as a string key and its slots. */
export function nextBlocked(t: TrackView): { key: "module.next_blocked"; slots: { n: number; next: number; date: string } } | null {
  const c = t.can_next;
  if (c.enabled || c.code !== "needs_feedback") return null;
  return { key: "module.next_blocked", slots: { n: c.number ?? t.current, next: c.next ?? t.current + 1, date: c.due_date ?? "" } };
}

/** The banner at the end of a track, or null while it is running. */
export function endBanner(t: TrackView): "module.cap_banner" | "module.exhausted_banner" | "module.end_banner" | null {
  if (t.status === "active") return null;
  if (t.stop_reason === "cap") return "module.cap_banner";
  if (t.stop_reason === "exhausted") return "module.exhausted_banner";
  return "module.end_banner";
}

// ---- the private check-in, and sharing a summary ----------------------------------------------------------

export type ShareField = "how" | "note" | "help" | "counts" | "name";
export const SHARE_FIELDS: ShareField[] = ["how", "note", "help", "counts", "name"];

export interface ChatState {
  available: boolean;
  reason: string | null;
  cohort_id: string | null;
  open: boolean;
  unread: number;
}

export interface CheckinState {
  answer: Answer | null;
  note: string;
  review: ReviewView;
  chat: ChatState;
  share: {
    shared: boolean;
    retracted: boolean;
    posted_text: string | null;
    fields: Record<ShareField, boolean> | null;
    anonymous: boolean | null;
    can_share: boolean;
    share_later_open: boolean;
    default_fields: Record<ShareField, boolean>;
    draft: string;
  };
}

export class BlockedError extends Error {
  constructor(public problems: string[]) {
    super("blocked");
  }
}

export async function getCheckin(trackId: string, number: number, lang: string, since?: string, fetchFn?: typeof fetch): Promise<CheckinState> {
  const q = `lang=${lang}${since ? `&since=${encodeURIComponent(since)}` : ""}`;
  return call<CheckinState>(`/tracks/${trackId}/modules/${number}/checkin?${q}`, {}, fetchFn);
}

export async function draftCheckin(trackId: string, number: number, lang: string, body: { fields?: Record<string, boolean>; text?: string }, fetchFn?: typeof fetch): Promise<{ text: string; problems: string[] }> {
  return call(`/tracks/${trackId}/modules/${number}/checkin/draft?lang=${lang}`, { method: "POST", body }, fetchFn);
}

/** Share the text she confirmed. A 422 "blocked" comes back as a BlockedError naming what to remove. */
export async function shareCheckin(trackId: string, number: number, lang: string, body: { text: string; fields: Record<string, boolean>; named: boolean; ai_help: boolean }, fetchFn?: typeof fetch): Promise<CheckinState> {
  let res: Response;
  try {
    res = await (fetchFn ?? ((...a: Parameters<typeof fetch>) => fetch(...a)))(`${API_BASE}/api/modules/tracks/${trackId}/modules/${number}/checkin/share?lang=${lang}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Role": "teacher", ...userHeader() },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ModuleError(0);
  }
  if (res.status === 422) {
    const d = ((await res.json().catch(() => ({}))) as { detail?: { code?: string; problems?: string[] } }).detail;
    if (d?.code === "blocked") throw new BlockedError(d.problems ?? []);
  }
  if (!res.ok) throw new ModuleError(res.status);
  return (await res.json()) as CheckinState;
}

export async function retractCheckin(trackId: string, number: number, lang: string, fetchFn?: typeof fetch): Promise<CheckinState> {
  return call<CheckinState>(`/tracks/${trackId}/modules/${number}/checkin/retract?lang=${lang}`, { method: "POST" }, fetchFn);
}

export async function callMe(trackId: string, number: number, fetchFn?: typeof fetch): Promise<void> {
  await call(`/tracks/${trackId}/modules/${number}/checkin/call-me`, { method: "POST" }, fetchFn);
}

/** For the Open cohort chat button: is there a chat, and how many new posts since she last opened it. */
export async function chatState(trackId: string, since?: string, fetchFn?: typeof fetch): Promise<ChatState> {
  return call<ChatState>(`/tracks/${trackId}/chat${since ? `?since=${encodeURIComponent(since)}` : ""}`, {}, fetchFn);
}
