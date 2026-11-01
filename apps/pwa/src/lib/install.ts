// Saving the app to the home screen. Chrome on Android fires `beforeinstallprompt` once, early, and
// only if the page is installable; we keep it so our own button can show the phone's install
// dialog. Browsers that never fire it (iPhone Safari, or Chrome after install) get the written steps
// only. Installing is optional: nothing in the app depends on it.
import { useSyncExternalStore } from "react";
import { track } from "./tester";

interface InstallEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferred: InstallEvent | null = null;
let installed = false;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());

export function isStandalone(): boolean {
  try {
    return window.matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true;
  } catch {
    return false;
  }
}

if (typeof window !== "undefined") {
  installed = isStandalone();
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault(); // keep it for our own button
    deferred = e as InstallEvent;
    notify();
  });
  window.addEventListener("appinstalled", () => {
    installed = true;
    deferred = null;
    notify();
  });
}

export interface InstallState {
  installed: boolean;
  canPrompt: boolean;
}

let last: InstallState = { installed, canPrompt: false };
function snapshot(): InstallState {
  const next = { installed, canPrompt: deferred !== null };
  if (next.installed !== last.installed || next.canPrompt !== last.canPrompt) last = next;
  return last;
}

export function useInstall(): InstallState {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    snapshot,
    () => ({ installed: false, canPrompt: false }),
  );
}

/** Show the phone's own install dialog. Resolves true if she accepted. */
export async function promptInstall(): Promise<boolean> {
  const e = deferred;
  if (!e) return false;
  await e.prompt();
  const { outcome } = await e.userChoice;
  deferred = null; // the browser allows one prompt per event
  if (outcome === "accepted") {
    installed = true;
    track("install_accepted");
  }
  notify();
  return outcome === "accepted";
}
