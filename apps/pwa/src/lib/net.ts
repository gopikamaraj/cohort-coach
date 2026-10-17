// Online state, with a "Simulate offline" switch for judges: forcing it makes the app behave
// exactly as it does with no signal (nothing is sent, the offline notice shows).
import { useSyncExternalStore } from "react";

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
