// "Download audio": send the text she is reading to the server, get an MP3 back, hand it to the browser
// as a file download. Nothing is made until she presses the button, and nothing is kept on the phone
// beyond the file she downloads (the object URL is dropped at once).
import { API_BASE } from "./api";
import { deviceId } from "./consent";

export type AudioFailure = "offline" | "cap" | "unavailable" | "other";

export class PackAudioError extends Error {
  constructor(public kind: AudioFailure) {
    super(`pack audio ${kind}`);
  }
}

export interface Made {
  blob: Blob;
  filename: string;
  bytes: number;
  seconds: number;
  provider: string;
  cached: boolean;
}

/** A file name from the error and the language, e.g. intervention-sub-sfl-en (a section adds its id). */
export function fileName(code: string, language: string, section?: string): string {
  const base = code.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return ["intervention", base, section, language].filter(Boolean).join("-");
}

/** The name the audio and the saved PDF share: Cohort-Coach-Improvement-Track-PV-HEARD-en-2026-11-02.
 *  The language code stays in it. */
export function exportStem(code: string, language: string, kind: string = "Improvement-Track", date: Date = new Date()): string {
  return ["Cohort-Coach", kind, code, language, date.toISOString().slice(0, 10)].join("-");
}

/** "412 KB" or "1.3 MB". */
export function sizeText(bytes: number): { key: "audio.size_kb" | "audio.size_mb"; n: string } {
  if (bytes < 1024 * 1024) return { key: "audio.size_kb", n: String(Math.max(1, Math.round(bytes / 1024))) };
  return { key: "audio.size_mb", n: (bytes / (1024 * 1024)).toFixed(1) };
}

/** What the server needs to write the spoken script itself: the error, her class's counts and, when the
 *  answers are on this phone, the roll numbers and one example. Or her own edited spoken `text`. */
export interface AudioRequest {
  language: string;
  name: string;
  text?: string;
  code?: string;
  children?: number;
  total?: number;
  rolls?: { confirmed: number[]; possible: number[] } | null;
  example?: { question: string; wrote: string; correct: string } | null;
}

export interface SpokenPreview {
  text: string;
  language: string;
  fallback: boolean;
  words: number;
}

/** The spoken text for this request, to read and change before it is voiced. Nothing is voiced. */
export async function previewScript(input: AudioRequest, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<SpokenPreview> {
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/audio/pack/script`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Role": "teacher", "X-Device-Id": deviceId() },
      body: JSON.stringify(input),
    });
  } catch {
    throw new PackAudioError("offline");
  }
  if (!res.ok) throw new PackAudioError("other");
  return (await res.json()) as SpokenPreview;
}

export async function makeAudio(
  input: AudioRequest,
  fetchFn: typeof fetch = (...a) => fetch(...a),
): Promise<Made> {
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/audio/pack`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Role": "teacher", "X-Device-Id": deviceId() },
      body: JSON.stringify(input),
    });
  } catch {
    throw new PackAudioError("offline");
  }
  if (res.status === 429) throw new PackAudioError("cap");
  if (res.status === 503) throw new PackAudioError("unavailable");
  if (!res.ok) throw new PackAudioError("other");
  const blob = await res.blob();
  return {
    blob,
    filename: `${input.name}.mp3`,
    bytes: blob.size,
    seconds: Number(res.headers.get("X-Audio-Seconds") ?? 0),
    provider: res.headers.get("X-Audio-Provider") ?? "",
    cached: res.headers.get("X-Audio-Cached") === "1",
  };
}

/** Hand the file to the browser, then let go of it. */
export function saveFile(made: Made): void {
  const url = URL.createObjectURL(made.blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = made.filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
