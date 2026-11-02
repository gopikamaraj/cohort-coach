// The last action's cost and time. When she starts an action (download the audio, print the pack, take a
// practice turn) the app makes an id, sends it on every request of that action as X-Action-Id, times the action
// from the click to its visible end, and then asks the server what the action cost, summed over every call it
// caused. Only the LAST action is kept: starting another throws the old numbers away. Nothing is added up
// across actions, and nothing but ids, names and numbers is sent or kept.
import { API_BASE } from "./api";

export interface KindUsage {
  calls: number;
  failed: number;
  retried: number;
  cost_usd: number;
  priced: boolean;
  input_tokens?: number;
  output_tokens?: number;
  cache_read_tokens?: number;
  cache_write_tokens?: number;
  characters?: number;
  seconds?: number;
  request_ms?: number;
  estimated?: boolean;
  cold?: boolean;
}

export interface UsageReply {
  action_id: string;
  name: string;
  complete: boolean;
  totals: { cost_usd: number; priced: boolean; entries: number };
  by_kind: { llm: KindUsage; tts: KindUsage; stt: KindUsage; cloud_run: KindUsage };
  time: { calls_sum_ms: number; calls_wall_ms: number; request_ms: number };
  display: { currency: string; inr_per_usd: number | null };
}

export type ActionPhase = "running" | "measuring" | "done" | "gone";

export interface ActionState {
  id: string;
  name: string;
  phase: ActionPhase; // running: the action itself; measuring: asking the server; done: the numbers are final
  wallMs: number | null; // from the click to the visible end, measured here
  usage: UsageReply | null;
}

const POLL_MS = 1200;
const GIVE_UP_MS = 30_000;
const FOOTER_KEY = "cc.usageFooter";

let state: ActionState | null = null;
let startedAt = 0;
let token = 0; // a newer action makes an older one stop asking
const subscribers = new Set<() => void>();

function set(next: ActionState | null): void {
  state = next;
  subscribers.forEach((f) => f());
}

export function subscribe(f: () => void): () => void {
  subscribers.add(f);
  return () => subscribers.delete(f);
}
export const getAction = (): ActionState | null => state;

/** The headers every request of the running action carries. */
export function actionHeaders(): Record<string, string> {
  return state && state.phase === "running" ? { "X-Action-Id": state.id, "X-Action-Name": state.name } : {};
}

function newId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return Array.from({ length: 4 }, () => Math.random().toString(16).slice(2, 10)).join("-");
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function fetchUsage(id: string, fetchFn: typeof fetch): Promise<UsageReply | null> {
  try {
    const res = await fetchFn(`${API_BASE}/api/actions/${encodeURIComponent(id)}/usage`);
    return res.ok ? ((await res.json()) as UsageReply) : null;
  } catch {
    return null;
  }
}

/** After the action's visible end: ask until the server says it is complete (or we give up), then once
 *  more to catch a late entry. Each answer updates the footer as it arrives. */
export async function measure(id: string, mine: number, fetchFn: typeof fetch = (...a) => fetch(...a), wait: (ms: number) => Promise<unknown> = sleep): Promise<void> {
  const begun = Date.now();
  let seen: UsageReply | null = null;
  while (mine === token) {
    const got = await fetchUsage(id, fetchFn);
    if (mine !== token) return;
    if (got && state) {
      seen = got;
      set({ ...state, usage: got });
      if (got.complete) break;
    }
    if (Date.now() - begun > GIVE_UP_MS) break;
    await wait(POLL_MS);
  }
  if (mine !== token || !state) return;
  if (seen?.complete) {
    await wait(600); // one more look for an entry written just after complete
    const last = await fetchUsage(id, fetchFn);
    if (mine === token && last && state) set({ ...state, usage: last });
  }
  if (mine === token && state) set({ ...state, phase: "done" });
}

/** Run one action: the requests made while `fn` runs belong to it, and its time is the click to the end. */
export async function runAction<T>(name: string, fn: () => Promise<T>, fetchFn?: typeof fetch): Promise<T> {
  const mine = ++token;
  const id = newId();
  startedAt = performance.now();
  set({ id, name, phase: "running", wallMs: null, usage: null });
  try {
    return await fn();
  } finally {
    if (mine === token && state) {
      set({ ...state, phase: "measuring", wallMs: Math.round(performance.now() - startedAt) });
      void measure(id, mine, fetchFn);
    }
  }
}

/** For tests: forget everything. */
export function resetAction(): void {
  token++;
  set(null);
}

// --- the setting: show the bar or hide it (this phone only) ------------------------------------------

const env = import.meta.env as Record<string, string | undefined>;
export const footerAllowed = (): boolean => env["VITE_USAGE_FOOTER"] !== "0"; // a deployment can switch it off

let chosen: boolean | null = null; // this visit's choice, for when the browser will not store it

/** The bar is on for everyone, teachers included, until a person hides it on this phone (Profile).
 *  A deployment can remove it with VITE_USAGE_FOOTER=0. */
export function footerOn(): boolean {
  if (!footerAllowed()) return false;
  if (chosen !== null) return chosen;
  try {
    return localStorage.getItem(FOOTER_KEY) !== "0";
  } catch {
    return true;
  }
}
export function setFooterOn(on: boolean): void {
  chosen = on;
  try {
    localStorage.setItem(FOOTER_KEY, on ? "1" : "0");
  } catch {
    /* private window: the choice lasts for this visit only */
  }
  subscribers.forEach((f) => f());
}

// --- numbers for the footer --------------------------------------------------------------------------------

export function money(usd: number, display: { currency: string; inr_per_usd: number | null }): string {
  if (display.currency === "INR" && display.inr_per_usd) {
    const v = usd * display.inr_per_usd;
    return `₹${v < 1 ? v.toFixed(3) : v.toFixed(2)}`;
  }
  return `$${usd < 1 ? usd.toFixed(4) : usd.toFixed(2)}`;
}

/** "$0.0123", "$0.0123 + n/a" (some lines have no price) or "n/a" (none does). */
export function totalText(u: UsageReply, na: string): string {
  const any = u.totals.entries > 0;
  if (u.totals.priced && any) return money(u.totals.cost_usd, u.display);
  if (u.totals.cost_usd > 0) return `${money(u.totals.cost_usd, u.display)} + ${na}`;
  return na;
}

export function seconds(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}
