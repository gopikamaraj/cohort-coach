// Which app to start: the full app, or the pilot app. The build flag VITE_PILOT_MODE=1 decides at
// build time; otherwise the server's /api/health says so (and the answer is remembered, so a phone
// that opens the app with no signal still gets the pilot app it had last time).
import { API_BASE } from "../lib/api";

const KEY = "cc.pilotMode";

export function buildIsPilot(): boolean {
  return (import.meta.env["VITE_PILOT_MODE"] as string | undefined) === "1";
}

function remembered(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

function remember(on: boolean): void {
  try {
    localStorage.setItem(KEY, on ? "1" : "0");
  } catch {
    /* private mode */
  }
}

export async function detectPilot(fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<boolean> {
  if (buildIsPilot()) return true;
  try {
    // a slow or missing server must not hold the app back: two seconds, then the remembered answer
    const res = await fetchFn(`${API_BASE}/api/health`, { cache: "no-store", signal: AbortSignal.timeout(2000) });
    const on = res.ok && ((await res.json()) as { pilot?: unknown }).pilot === true;
    remember(on);
    return on;
  } catch {
    return remembered();
  }
}
