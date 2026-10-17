// Voice for the Practice Class: when to use it, how a recording is sent, how a reply is played.
// Only the recording of her own voice goes out (to be turned into text and dropped); nothing
// is stored. Two failures in a row, or a 2g connection, switch her to typing without asking.
import { API_BASE } from "./api";
import { PracticeError, type TurnResponse } from "./practice";

export const MAX_VOICE_FAILURES = 2;
export const MAX_RECORD_MS = 25_000; // under the 30 s the speech service takes in one go

export type VoiceState = "idle" | "listening" | "thinking" | "speaking";

interface NetInfo {
  effectiveType?: string;
  saveData?: boolean;
}

export function slowLink(
  conn: NetInfo | undefined = (navigator as { connection?: NetInfo })
    .connection,
): boolean {
  return conn?.effectiveType === "slow-2g" || conn?.effectiveType === "2g";
}

export function canRecord(): boolean {
  return (
    typeof MediaRecorder !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia)
  );
}

/** Voice is the default only when the server has it, this phone can record, the link can
 * carry it, and she has not chosen typing before ("0" is remembered on this phone). */
export function voiceDefault(
  server: boolean,
  record: boolean,
  slow: boolean,
  preference: string | null,
): boolean {
  return server && record && !slow && preference !== "0";
}

export const VOICE_PREF_KEY = "cc.voice";

export function recorderMime(): string {
  for (const m of [
    "audio/webm;codecs=opus",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ]) {
    if (
      typeof MediaRecorder !== "undefined" &&
      MediaRecorder.isTypeSupported(m)
    )
      return m;
  }
  return "";
}

export interface VoiceTurn extends TurnResponse {
  heard: string;
  audio: string | null;
  audio_mime: string | null;
  speech_mode: string;
}

const TIMEOUT_MS = 30_000;

export async function postVoiceTurn(
  sessionId: string,
  clip: Blob,
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<VoiceTurn> {
  const form = new FormData();
  form.append("audio", clip, "clip.webm");
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetchFn(
      `${API_BASE}/api/practice/sessions/${sessionId}/voice-turn`,
      { method: "POST", body: form, signal: ctrl.signal },
    );
  } catch {
    throw new PracticeError("voice", 0); // no signal or too slow: counts as a voice failure
  } finally {
    clearTimeout(timer);
  }
  if (res.ok) return (await res.json()) as VoiceTurn;
  if (res.status === 503) {
    const body = (await res.json().catch(() => ({}))) as {
      detail?: { text_mode?: boolean };
    };
    throw new PracticeError(body.detail?.text_mode ? "voice" : "paused", 503);
  }
  if (res.status === 422) throw new PracticeError("unheard", 422); // silence: ask again, not a failure
  throw new PracticeError(
    res.status === 404 ? "expired" : res.status === 409 ? "finished" : "other",
    res.status,
  );
}

/** Play a base64 reply. Resolves when it ends; a blocked or broken play resolves too (the text is there). */
export function playReply(b64: string, mime: string): Promise<void> {
  return new Promise((resolve) => {
    const audio = new Audio(`data:${mime};base64,${b64}`);
    audio.onended = () => resolve();
    audio.onerror = () => resolve();
    audio.play().catch(() => resolve());
  });
}
