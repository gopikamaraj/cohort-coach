// Online state, with a "Simulate offline" switch for judges: forcing it makes the app behave
// exactly as it does with no signal (nothing is sent, the offline notice shows).
import { useMemo, useSyncExternalStore } from "react";

const KEY = "cc.forcedOffline";
const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((l) => l());
}

export function isForcedOffline(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function setForcedOffline(on: boolean): void {
  try {
    localStorage.setItem(KEY, on ? "1" : "0");
  } catch {
    /* private mode: the switch just does not persist */
  }
  notify();
}

export function isOnline(): boolean {
  return navigator.onLine && !isForcedOffline();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("online", listener);
  window.addEventListener("offline", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("online", listener);
    window.removeEventListener("offline", listener);
  };
}

export function useOnline(): boolean {
  return useSyncExternalStore(subscribe, isOnline, () => true);
}

export function useForcedOffline(): boolean {
  return useSyncExternalStore(subscribe, isForcedOffline, () => false);
}

// The signal, as the phone's browser already estimates it (the Network Information API, Chrome on
// Android). Reading it sends nothing and costs no data. It is a download estimate only: the browser
// gives no upload speed, and other browsers give nothing at all, so then no speed is shown.
type Conn = { effectiveType?: string; downlink?: number };
type ConnSource = Conn & {
  addEventListener?: (type: "change", listener: () => void) => void;
  removeEventListener?: (type: "change", listener: () => void) => void;
};
export type Signal = "good" | "slow" | "veryslow";
export interface LinkSpeed {
  signal: Signal;
  /** Megabits a second, ready to show: "0.4", "5", or "10+" (Chrome stops counting at 10). */
  mbps: string;
}

function connection(): ConnSource | undefined {
  return (navigator as { connection?: ConnSource }).connection;
}

export function describeLink(c: Conn | undefined): LinkSpeed | null {
  if (!c || typeof c.downlink !== "number" || !(c.downlink > 0)) return null;
  const signal: Signal | null = c.effectiveType === "4g" ? "good" : c.effectiveType === "3g" ? "slow" : c.effectiveType === "2g" || c.effectiveType === "slow-2g" ? "veryslow" : null;
  if (!signal) return null;
  const d = c.downlink;
  // tenths, rounded half up (the tiny nudge undoes binary rounding: 0.35 must read 0.4), never shown as 0
  const tenths = Math.max(1, Math.round(d * 10 + 1e-9));
  const mbps = d >= 10 ? "10+" : (tenths / 10).toFixed(tenths % 10 === 0 ? 0 : 1);
  return { signal, mbps };
}

function linkKey(): string {
  const c = connection();
  return c ? `${c.effectiveType ?? ""}|${c.downlink ?? ""}` : "";
}

function subscribeLink(listener: () => void): () => void {
  const c = connection();
  c?.addEventListener?.("change", listener);
  return () => c?.removeEventListener?.("change", listener);
}

export function useLinkSpeed(): LinkSpeed | null {
  const key = useSyncExternalStore(subscribeLink, linkKey, () => "");
  return useMemo(() => {
    const [type, down] = key.split("|");
    return describeLink({ ...(type ? { effectiveType: type } : {}), ...(down ? { downlink: Number(down) } : {}) });
  }, [key]);
}
