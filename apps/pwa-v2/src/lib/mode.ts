// Which back end this page talks to. One web address serves both: the judge demo (simulated data,
// no sign-in) and the pilot (staff sign-in, real consented sheets). They are two separate servers,
// so pilot data never sits behind the judge server's open roles. The choice is remembered on this
// phone; a teacher's lesson link always means the pilot. With only one back end configured (dev,
// tests, a single-mode build) there is nothing to switch.
export type Mode = "judge" | "pilot";

const KEY = "cc.mode";

export interface ModeConfig {
  judgeBase: string;
  pilotBase: string;
}

export function canSwitch(c: ModeConfig): boolean {
  return c.pilotBase !== "" && c.pilotBase !== c.judgeBase;
}

export function pickMode(c: ModeConfig, hash: string, stored: string | null): Mode {
  if (!canSwitch(c)) return "judge";
  if (/^#?\/lesson\//.test(hash)) return "pilot";
  return stored === "pilot" ? "pilot" : "judge";
}

export function baseFor(c: ModeConfig, mode: Mode): string {
  return mode === "pilot" && canSwitch(c) ? c.pilotBase : c.judgeBase;
}

export function readStored(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

/** Remember the choice and reload at the front door of the chosen mode. */
export function switchMode(mode: Mode): void {
  try {
    localStorage.setItem(KEY, mode);
  } catch {
    /* private mode: the choice lasts until the page closes */
  }
  window.location.hash = mode === "pilot" ? "#/upload" : "#/roles";
  window.location.reload();
}
