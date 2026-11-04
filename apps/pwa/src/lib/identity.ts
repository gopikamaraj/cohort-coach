// Who is using the app: the nickname is the user id.
//
// A nickname is normalised (NFKC, single spaces, lower case) and that string is the user id; the server keeps
// nicknames unique. Every request to our own API carries `X-User` (the id, URL-encoded). There is NO password:
// whoever types a nickname is that user. That is demo-grade identity, and the sign-in screen says so.
import { API_BASE } from "./api";

const KEY = "cc.user";

export interface AppUser {
  id: string;
  nickname: string;
}

export function normalise(nickname: string): string {
  return nickname.normalize("NFKC").replace(/\s+/g, " ").trim().toLowerCase();
}

let lastRaw: string | null | undefined;
let lastUser: AppUser | null = null;

/** The signed-in user (the same object until it changes, so React can subscribe to it). */
export function getUser(): AppUser | null {
  let raw: string | null;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    raw = null;
  }
  if (raw === lastRaw) return lastUser;
  lastRaw = raw;
  try {
    const v = raw ? (JSON.parse(raw) as Partial<AppUser>) : null;
    lastUser = v && typeof v.id === "string" && v.id ? { id: v.id, nickname: typeof v.nickname === "string" ? v.nickname : v.id } : null;
  } catch {
    lastUser = null;
  }
  return lastUser;
}

function setUser(u: AppUser | null): void {
  try {
    if (u) localStorage.setItem(KEY, JSON.stringify(u));
    else localStorage.removeItem(KEY);
  } catch {
    /* private mode: she signs in again next time */
  }
  if (typeof window !== "undefined") window.dispatchEvent(new Event("cc:identity"));
}

/** The one header every request to our API carries. Empty until she has signed in. */
export function userHeader(): Record<string, string> {
  const u = getUser();
  return u ? { "X-User": encodeURIComponent(u.id) } : {};
}

export type SignInCode = "taken" | "unknown" | "length" | "characters" | "reserved" | "offline";
export type SignInResult = { ok: true; user: AppUser } | { ok: false; code: SignInCode; message: string };

async function call(path: "register" | "signin", nickname: string, fetchFn: typeof fetch): Promise<SignInResult> {
  try {
    const res = await fetchFn(`${API_BASE}/api/users/${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nickname }) });
    const body = (await res.json().catch(() => ({}))) as { id?: string; nickname?: string; detail?: { code?: string; message?: string } };
    if (res.ok && body.id) {
      const user = { id: body.id, nickname: body.nickname ?? body.id };
      setUser(user);
      return { ok: true, user };
    }
    const d = body.detail ?? {};
    return { ok: false, code: (d.code as SignInCode | undefined) ?? "unknown", message: d.message ?? "" };
  } catch {
    return { ok: false, code: "offline", message: "" };
  }
}

/** A new nickname: refused with code "taken" when someone has it already. */
export const register = (nickname: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<SignInResult> => call("register", nickname, fetchFn);

/** An existing nickname: whoever types it is that user (no password; demo-grade). */
export const signIn = (nickname: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<SignInResult> => call("signin", nickname, fetchFn);

export function signOut(): void {
  setUser(null);
}

let installed = false;

/** Make every fetch to our own API carry the user header, so no call site has to remember it. */
export function installIdentity(): void {
  if (installed || typeof window === "undefined" || typeof window.fetch !== "function") return;
  installed = true;
  const original = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const ours = url.startsWith(`${API_BASE}/api/`) || url.startsWith("/api/") || (API_BASE === "" && url.includes("/api/"));
    const h = userHeader();
    if (!ours || !h["X-User"]) return original(input, init);
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    if (!headers.has("X-User")) headers.set("X-User", h["X-User"]);
    return original(input, { ...init, headers });
  };
}
