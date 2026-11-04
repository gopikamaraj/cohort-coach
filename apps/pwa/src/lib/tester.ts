// Tester stats (TESTER_STATS=1 on the server, public demo only). Opt-in, coarse, and quiet:
//  - stats belong to the signed-in user (the normalised nickname); there is no device id or device hash;
//  - nothing is sent (no profile, no event, no feedback) unless the person agreed;
//  - events queue on the phone and go in batches when online; nothing here can block the screen.
// Never collected: address, location, contacts, the user-agent string, typed text, voice, child data.
import { API_BASE } from "./api";
import { getUser, userHeader } from "./identity";
import { db, getSetting, setSetting, type CohortDb } from "./db";
import { isOnline } from "./net";

export type EventType =
  | "session_start" | "session_end" | "role_selected" | "view_as_role" | "screen_viewed" | "tour_started"
  | "tour_step_viewed" | "tour_completed" | "tour_skipped" | "feature_used" | "sample_input_run"
  | "error_shown" | "offline_session" | "install_accepted"; // fmt: skip

export interface EventFields {
  role?: string;
  screen_id?: string;
  tour_id?: string;
  step_id?: string;
  feature_id?: string;
  value?: Record<string, string | number | boolean>;
}
interface QueuedEvent extends EventFields {
  event_id: string;
  session_id: string;
  ts: number;
  type: EventType;
  connection_class?: "offline" | "slow" | "fast";
}
export interface QueuedFeedback {
  rating: number;
  tags: string[];
  comment?: string;
  role?: string;
  screen_id?: string;
}

export interface TesterPrefs {
  consent: "yes" | "no" | null;
  nickname: string;
  isPublic: boolean;
  paused: boolean;
  src: string | null;
  team: string | null;
  judge: boolean;
  profileKey: string; // what the server last accepted; a change re-sends the profile
}

const PREFS_KEY = "cc.tester";
const MAX_QUEUE = 500;
const BATCH = 50;
export const APP_VERSION = "0.1.0";
export const TAGS = ["easy", "confusing", "useful", "slow", "voice_problem", "hard_to_read"] as const;

type Fetch = typeof fetch;
const defaultFetch: Fetch = (...a) => fetch(...a);

// ---- pure helpers (tested) ----

export function durationBucket(ms: number): "under_10s" | "10_30s" | "30s_2m" | "over_2m" {
  if (ms < 10_000) return "under_10s";
  if (ms < 30_000) return "10_30s";
  if (ms < 120_000) return "30s_2m";
  return "over_2m";
}

export function browserFamily(ua: string): "chrome" | "safari" | "firefox" | "edge" | "samsung" | "other" {
  if (/SamsungBrowser/i.test(ua)) return "samsung";
  if (/Edg(e|A|iOS)?\//i.test(ua)) return "edge";
  if (/Firefox|FxiOS/i.test(ua)) return "firefox";
  if (/Chrome|CriOS/i.test(ua)) return "chrome";
  if (/Safari/i.test(ua)) return "safari";
  return "other";
}

export function osFamily(ua: string): "android" | "ios" | "windows" | "macos" | "linux" | "other" {
  if (/Android/i.test(ua)) return "android";
  if (/iPhone|iPad|iPod/i.test(ua)) return "ios";
  if (/Windows/i.test(ua)) return "windows";
  if (/Mac OS X|Macintosh/i.test(ua)) return "macos";
  if (/Linux|CrOS/i.test(ua)) return "linux";
  return "other";
}

export function deviceClassOf(width: number): "phone" | "tablet" | "desktop" {
  return width < 600 ? "phone" : width < 1024 ? "tablet" : "desktop";
}

export function connectionClass(online: boolean, effectiveType?: string): "offline" | "slow" | "fast" {
  if (!online) return "offline";
  return effectiveType === "slow-2g" || effectiveType === "2g" || effectiveType === "3g" ? "slow" : "fast";
}

/** The ?src= and ?team= values from the page address (before or after the #). */
export function inviteFromLocation(search: string, hash: string): { src: string | null; team: string | null } {
  const q = new URLSearchParams(search);
  const h = hash.includes("?") ? new URLSearchParams(hash.slice(hash.indexOf("?") + 1)) : new URLSearchParams();
  const src = (q.get("src") ?? h.get("src") ?? "").toLowerCase();
  const team = q.get("team") ?? h.get("team");
  return { src: /^[a-z0-9-]{1,24}$/.test(src) ? src : null, team: team && team.length <= 80 ? team : null };
}

export async function sha256Hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function randomId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}

// ---- state ----

const blank: TesterPrefs = { consent: null, nickname: "", isPublic: false, paused: false, src: null, team: null, judge: false, profileKey: "" };
let prefs: TesterPrefs = load();
const listeners = new Set<() => void>();
let queue: QueuedEvent[] = [];
let feedbackQueue: QueuedFeedback[] = [];
let queueLoaded = false;
let cfgPromise: Promise<{ enabled: boolean; salt: string }> | null = null;
let timer: ReturnType<typeof setTimeout> | null = null;
let flushing = false;
const sessionId = randomId();

function load(): TesterPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? { ...blank, ...(JSON.parse(raw) as Partial<TesterPrefs>) } : { ...blank };
  } catch {
    return { ...blank };
  }
}

function save(next: Partial<TesterPrefs>): void {
  const before = prefs.nickname;
  prefs = { ...prefs, ...next };
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* private mode: the choice lasts until the page closes */
  }
  listeners.forEach((l) => l());
  if (prefs.nickname !== before && typeof window !== "undefined" && typeof window.dispatchEvent === "function") window.dispatchEvent(new Event("cc:identity")); // she is a different teacher now
}

export function getPrefs(): TesterPrefs {
  return prefs;
}
export function subscribePrefs(l: () => void): () => void {
  listeners.add(l);
  return () => listeners.delete(l);
}
export function getSessionId(): string {
  return sessionId;
}

/** Test hook: forget everything held in memory so a test can start clean. */
export function resetForTests(): void {
  prefs = { ...blank };
  queue = [];
  feedbackQueue = [];
  queueLoaded = false;
  cfgPromise = null;
  flushing = false;
  if (timer) clearTimeout(timer);
  timer = null;
}

export const sharing = (p: TesterPrefs = prefs): boolean => p.consent === "yes" && !p.paused;

async function loadQueues(store: CohortDb = db): Promise<void> {
  if (queueLoaded) return;
  queueLoaded = true;
  try {
    queue = [...(await getSetting<QueuedEvent[]>("tester.queue", [], store)), ...queue].slice(-MAX_QUEUE);
    feedbackQueue = [...(await getSetting<QueuedFeedback[]>("tester.fbqueue", [], store)), ...feedbackQueue];
  } catch {
    /* no storage: the queue lives in memory for this visit */
  }
}

async function persistQueues(store: CohortDb = db): Promise<void> {
  try {
    await setSetting("tester.queue", queue, store);
    await setSetting("tester.fbqueue", feedbackQueue, store);
  } catch {
    /* kept in memory */
  }
}

// ---- server config and the device hash ----

export function testerConfig(fetchFn: Fetch = defaultFetch): Promise<{ enabled: boolean; salt: string }> {
  cfgPromise ??= (async () => {
    try {
      const res = await fetchFn(`${API_BASE}/api/tester/config`);
      if (!res.ok) return { enabled: false, salt: "" }; // 404: the feature is off here
      const j = (await res.json()) as { enabled?: boolean; salt?: string };
      return { enabled: j.enabled === true, salt: j.salt ?? "" };
    } catch {
      cfgPromise = null; // offline or down: ask again next time
      return { enabled: false, salt: "" };
    }
  })();
  return cfgPromise;
}

/** Stats are sent for the signed-in user (the server names the row by the user id; there is no device hash). */
export function signedInForStats(): boolean {
  return getUser() !== null;
}

// ---- consent and settings ----

export function captureInvite(search = window.location.search, hash = window.location.hash): void {
  const { src, team } = inviteFromLocation(search, hash);
  const patch: Partial<TesterPrefs> = {};
  if (src && !prefs.src) patch.src = src; // the first link opened says where this person came from
  if (src === "judge" && !prefs.judge) patch.judge = true;
  if (team && team !== prefs.team) patch.team = team;
  if (Object.keys(patch).length) save(patch);
}

export function markJudge(): void {
  if (!prefs.judge) save({ judge: true });
}

export function giveConsent(nickname: string, isPublic: boolean): void {
  save({ consent: "yes", nickname: nickname.trim().slice(0, 30), isPublic, paused: false, profileKey: "" });
  track("session_start");
  scheduleFlush(300);
}
export function declineSharing(): void {
  save({ consent: "no", nickname: "", isPublic: false });
  queue = [];
  feedbackQueue = [];
  void persistQueues();
}
export function changeNickname(nickname: string, isPublic: boolean): void {
  save({ nickname: nickname.trim().slice(0, 30), isPublic, profileKey: "" });
  scheduleFlush(300);
}
/** The name shown beside the role in the title bar. It lives on this phone; it is sent only if she shares testing data. */
export function setNickname(nickname: string): void {
  save({ nickname: nickname.trim().slice(0, 30), profileKey: "" });
  if (sharing()) scheduleFlush(300);
}
export function pauseSharing(paused: boolean): void {
  save({ paused });
  if (paused) {
    queue = [];
    void persistQueues();
  } else scheduleFlush(300);
}

// ---- tracking ----

function currentConnection(): "offline" | "slow" | "fast" {
  const c = (navigator as unknown as { connection?: { effectiveType?: string } }).connection;
  return connectionClass(isOnline(), c?.effectiveType);
}

/** Queue one event. Does nothing unless the person agreed; never throws; never waits. */
export function track(type: EventType, fields: EventFields = {}): void {
  try {
    if (!sharing()) return;
    queue.push({ event_id: randomId(), session_id: sessionId, ts: Date.now(), type, connection_class: currentConnection(), ...fields });
    if (queue.length > MAX_QUEUE) queue = queue.slice(-MAX_QUEUE);
    void loadQueues().then(() => persistQueues());
    scheduleFlush(queue.length >= 20 ? 300 : 5000);
  } catch {
    /* tracking must never break the app */
  }
}

export function queueFeedback(f: QueuedFeedback): void {
  if (!sharing()) return;
  feedbackQueue.push(f);
  void persistQueues();
  scheduleFlush(300);
}

export function queuedCounts(): { events: number; feedback: number } {
  return { events: queue.length, feedback: feedbackQueue.length };
}

function scheduleFlush(ms: number): void {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => void flush(), ms);
}

function profileBody(): Record<string, unknown> {
  const ua = navigator.userAgent;
  const standalone = window.matchMedia?.("(display-mode: standalone)").matches === true;
  const lang = document.documentElement.lang;
  return {
    consent_stats: true,
    nickname: prefs.nickname || "Tester",
    nickname_public: prefs.isPublic,
    app_version: APP_VERSION,
    browser_family: browserFamily(ua),
    os_family: osFamily(ua),
    device_class: deviceClassOf(window.innerWidth),
    language: lang === "hi" || lang === "ta" ? lang : "en",
    installed_pwa: standalone,
    invite_source: prefs.src ?? undefined,
    is_judge: prefs.judge,
    team_token: prefs.team ?? undefined,
  };
}

async function post(path: string, body: unknown, fetchFn: Fetch, keepalive = false): Promise<number> {
  try {
    const res = await fetchFn(`${API_BASE}${path}`, { method: "POST", headers: { "Content-Type": "application/json", ...userHeader() }, body: JSON.stringify(body), keepalive });
    return res.status;
  } catch {
    return 0;
  }
}

/** Send the profile (if changed), then queued events in batches, then queued feedback. Safe to call anytime. */
export async function flush(fetchFn: Fetch = defaultFetch, store: CohortDb = db, keepalive = false): Promise<void> {
  if (flushing || !sharing() || !isOnline()) return;
  flushing = true;
  try {
    await loadQueues(store);
    if (!signedInForStats() || !sharing()) return;
    const body = profileBody();
    const key = JSON.stringify([body.nickname, body.nickname_public, body.language, body.device_class, body.installed_pwa, body.is_judge, body.invite_source, body.team_token]);
    if (prefs.profileKey !== key) {
      const st = await post("/api/tester/profile", body, fetchFn, keepalive);
      if (st < 200 || st >= 300) return; // try again at the next flush
      save({ profileKey: key });
    }
    while (queue.length > 0 && sharing()) {
      const batch = queue.slice(0, BATCH);
      const st = await post("/api/tester/events", { events: batch }, fetchFn, keepalive);
      if (st === 403) {
        save({ profileKey: "" }); // the server lost the profile: send it again next time
        return;
      }
      if (st === 0 || st >= 500 || st === 429) return; // offline or busy: keep the batch for later
      queue = queue.slice(batch.length); // sent, or refused as malformed (not worth retrying)
    }
    while (feedbackQueue.length > 0 && sharing()) {
      const f = feedbackQueue[0]!;
      const st = await post("/api/tester/feedback", { ...f }, fetchFn, keepalive);
      if (st === 0 || st >= 500 || st === 429 || st === 403) return;
      feedbackQueue = feedbackQueue.slice(1);
    }
  } catch {
    /* try again at the next flush */
  } finally {
    flushing = false;
    await persistQueues(store);
  }
}

/** Delete this person's server rows (by hash), then clear everything held on the device. */
export async function deleteMyData(fetchFn: Fetch = defaultFetch, store: CohortDb = db): Promise<"deleted" | "device_only"> {
  let server: "deleted" | "device_only" = "device_only";
  try {
    if (signedInForStats() && isOnline()) {
      const res = await fetchFn(`${API_BASE}/api/tester/me`, { method: "DELETE", headers: { ...userHeader() } });
      if (res.ok) server = "deleted";
    }
  } catch {
    /* offline: the device is still cleared; the server rows go with the 90-day retention */
  }
  queue = [];
  feedbackQueue = [];
  try {
    await store.settings.delete("tester.queue");
    await store.settings.delete("tester.fbqueue");
  } catch {
    /* nothing more to clear */
  }
  save({ consent: "no", nickname: "", isPublic: false, profileKey: "" });
  return server;
}

/** The first-run sheet shows once: when the feature is on here and no choice has been made. */
export async function needsFirstRun(fetchFn: Fetch = defaultFetch): Promise<boolean> {
  if (prefs.consent !== null) return false;
  return (await testerConfig(fetchFn)).enabled;
}
