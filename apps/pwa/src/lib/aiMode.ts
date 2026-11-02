// Which AI mode the server runs in (from /api/health): `live`, `recorded` (answers are replayed
// from recordings), `off` (the AI is unreachable), or `stub`/`record` for development. The screens
// only label what they show with it; the server decides everything.
import { useEffect, useState } from "react";
import { API_BASE } from "./api";

export type AiMode = "live" | "recorded" | "off" | "stub" | "record" | "unknown";

let known: AiMode = "unknown";
let devTesting = false; // DEV_TESTING=1 on the server: testing shortcuts are shown
let pending: Promise<AiMode> | null = null;
const listeners = new Set<(m: AiMode) => void>();

export async function loadAiMode(fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<AiMode> {
  if (known !== "unknown") return known;
  pending ??= fetchFn(`${API_BASE}/api/health`, { cache: "no-store" })
    .then(async (r) => {
      const body = r.ok ? ((await r.json()) as { ai_mode?: string; dev_testing?: boolean }) : {};
      const mode = body.ai_mode;
      devTesting = body.dev_testing === true;
      known = (["live", "recorded", "off", "stub", "record"] as const).find((m) => m === mode) ?? "unknown";
      listeners.forEach((fn) => fn(known));
      return known;
    })
    .catch(() => "unknown" as const)
    .finally(() => {
      pending = null;
    });
  return pending;
}

/** The server's AI mode; "unknown" until the health check answers (or when offline). */
export function useAiMode(): AiMode {
  const [mode, setMode] = useState<AiMode>(known);
  useEffect(() => {
    listeners.add(setMode);
    void loadAiMode();
    return () => {
      listeners.delete(setMode);
    };
  }, []);
  return mode;
}

/** True when the server says DEV_TESTING=1: show testing shortcuts (never on a public deployment). */
export function useDevTesting(): boolean {
  const [on, setOn] = useState(devTesting);
  useEffect(() => {
    const fn = () => setOn(devTesting);
    listeners.add(fn);
    void loadAiMode().then(fn);
    return () => {
      listeners.delete(fn);
    };
  }, []);
  return on;
}

/** True when an AI answer on screen is a replay, so it must say "Recorded AI answer". */
export const isRecorded = (m: AiMode) => m === "recorded";
/** True when AI features cannot work and the non-AI path must be offered. */
export const isAiOff = (m: AiMode) => m === "off";

/** For tests. */
export function resetAiModeForTests(m: AiMode = "unknown"): void {
  known = m;
}
