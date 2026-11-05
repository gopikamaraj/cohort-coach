// Consent (India's DPDP Act): free, specific and withdrawable. Nothing is on by default, with one exception
// for the demo build: until she makes a choice, sharing class counts is ON (counts only, never a child), so a
// demo's results reach the server. VITE_DEFAULT_SHARE_COUNTS=0 turns that off; any saved choice wins. What she agreed to is
// kept on the phone with a version and a time, and each change is also sent to the server as a record under her
// user id (her nickname; no device id exists). Using the check, the cards and the history on this phone needs no consent
// beyond reading the notice ("core"); sending class counts, using the AI Practice Class, and sharing
// rehearsals each have their own switch.
import { userHeader } from "./identity";
import { API_BASE } from "./api";

export interface KV {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export const CONSENT_VERSION = 1;
export const SCOPES = ["core", "counts", "practice_ai", "share_rehearsal", "feedback", "keep_sheets"] as const;
export type Scope = (typeof SCOPES)[number];
// keep_sheets (keep my approved answer sheets for 60 days) is optional, so choices saved before it existed still fit
export type Choices = Record<Exclude<Scope, "keep_sheets">, boolean> & { keep_sheets?: boolean };
export interface Consent extends Choices {
  v: number;
  at: number;
}

const KEY = "cc.consent";
const local = (): KV | null => {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
};

export function getConsent(kv: KV | null = local()): Consent | null {
  try {
    const raw = kv?.getItem(KEY);
    return raw ? (JSON.parse(raw) as Consent) : null;
  } catch {
    return null;
  }
}

const demoShareCounts = (): boolean => (import.meta.env as Record<string, string | undefined>)["VITE_DEFAULT_SHARE_COUNTS"] !== "0";

/** Is sharing class counts on? Her saved choice if she has made one, else the demo default. */
export function countsOn(consent: Consent | null): boolean {
  return consent ? consent.counts === true : demoShareCounts();
}

export function hasConsent(scope: Scope, kv: KV | null = local()): boolean {
  const c = getConsent(kv);
  return scope === "counts" ? countsOn(c) : c?.[scope] === true;
}

export function setConsent(choices: Choices, kv: KV | null = local()): Consent {
  const c: Consent = { ...choices, v: CONSENT_VERSION, at: Date.now() };
  kv?.setItem(KEY, JSON.stringify(c));
  if (typeof window !== "undefined") window.dispatchEvent(new Event("cc-consent"));
  return c;
}

export function withdrawAll(kv: KV | null = local()): Consent {
  return setConsent({ core: false, counts: false, practice_ai: false, share_rehearsal: false, feedback: false }, kv);
}

/** Tell the server what changed, so there is a record. Best effort: the phone's own record is what counts offline. */
export async function recordOnServer(before: Consent | null, after: Consent, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<void> {
  for (const scope of SCOPES) {
    if (before?.[scope] === after[scope] && before?.v === after.v) continue;
    try {
      await fetchFn(`${API_BASE}/api/consents`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...userHeader() },
        body: JSON.stringify({ scope, granted: after[scope], version: after.v }),
      });
    } catch {
      /* offline: the next change sends it again */
    }
  }
}
