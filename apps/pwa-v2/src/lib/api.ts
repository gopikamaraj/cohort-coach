// Where the API lives. Empty in dev and in tests (the dev and preview servers proxy /api);
// set VITE_API_BASE to the API's https address when the PWA is hosted separately (staging).
// A web address that serves both modes also sets VITE_PILOT_API_BASE (the pilot server); the mode
// chosen on the landing page then decides which of the two every call goes to (lib/mode.ts).
import { baseFor, canSwitch, pickMode, readStored, type ModeConfig } from "./mode";

const env = import.meta.env as Record<string, string | undefined>;

export const MODE_CONFIG: ModeConfig = {
  judgeBase: env["VITE_API_BASE"] ?? "",
  pilotBase: env["VITE_PILOT_API_BASE"] ?? "",
};
export const CAN_SWITCH_MODE: boolean = canSwitch(MODE_CONFIG);
export const MODE = pickMode(MODE_CONFIG, typeof window === "undefined" ? "" : window.location.hash, readStored());
export const API_BASE: string = baseFor(MODE_CONFIG, MODE);
