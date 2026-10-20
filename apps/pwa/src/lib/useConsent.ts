// React hook: the current consent, updated when it changes anywhere in the app.
import { useSyncExternalStore } from "react";
import { getConsent, type Consent } from "./consent";

let cache: { raw: string | null; value: Consent | null } = { raw: null, value: null };
function snapshot(): Consent | null {
  const raw = (() => {
    try {
      return localStorage.getItem("cc.consent");
    } catch {
      return null;
    }
  })();
  if (raw !== cache.raw) cache = { raw, value: getConsent() };
  return cache.value;
}

function subscribe(l: () => void): () => void {
  window.addEventListener("cc-consent", l);
  window.addEventListener("storage", l);
  return () => {
    window.removeEventListener("cc-consent", l);
    window.removeEventListener("storage", l);
  };
}

export function useConsent(): Consent | null {
  return useSyncExternalStore(subscribe, snapshot, () => null);
}
