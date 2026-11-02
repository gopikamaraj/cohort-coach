// Many sheet pictures at once: a folder of pictures (or several pictures chosen from the gallery) is
// matched to roll numbers, then read three at a time. Nothing here keeps a picture: the caller holds the
// shrunk copies in memory only. File names are only a hint (mobile Safari can scramble them), so a
// picture is matched by its file name, then by the class code and roll number written in its header,
// and otherwise the teacher chooses.

export const READ_AT_ONCE = 3;

/** Can this browser choose a whole folder? Feature detection, never the browser's name. */
export function folderPickerSupported(proto: object = typeof HTMLInputElement === "undefined" ? {} : HTMLInputElement.prototype): boolean {
  return "webkitdirectory" in proto;
}

const PICTURE_EXT = /\.(jpe?g|png|webp|heic|heif)$/i;

export function isPicture(file: { name: string; type?: string }): boolean {
  return (file.type ?? "").startsWith("image/") || PICTURE_EXT.test(file.name);
}

/** "3A-roll07.jpg" -> { classCode: "3A", roll: 7 }; "roll_12.png" -> { roll: 12 }; "IMG_4521.jpg" -> null. */
export function parseFileName(name: string): { classCode?: string; roll: number } | null {
  const base = name.replace(/\.[^.]+$/, "");
  const m = /(?:^|[^a-z0-9])(?:(\d{1,2}[a-z])[\s_-]*)?roll[\s_-]*0*(\d{1,3})(?:$|[^0-9])/i.exec(base);
  if (!m) return null;
  const roll = Number(m[2]);
  if (!(roll >= 1)) return null;
  return { classCode: m[1]?.toUpperCase(), roll };
}

/** The class code in a paper's printed check code: "PRE · 3A · T1" -> "3A". */
export function classCodeOf(paperCode: string | null | undefined): string | null {
  const m = /\b(\d{1,2}[A-Z])\b/.exec((paperCode ?? "").toUpperCase());
  return m ? (m[1] as string) : null;
}

/** "S0-3A", "SO-3A" and "3A" all mean class 3A: the grade and section at the end of a header's class code.
 *  A code with no such ending is unknown, and an unknown code never blocks a picture. */
export function sectionOf(code: string | null | undefined): string | null {
  const m = /(\d{1,2})\s*([A-Za-z])\s*$/.exec((code ?? "").trim());
  return m ? `${m[1]}${(m[2] as string).toUpperCase()}` : null;
}

export interface Header {
  class_code: string | null;
  roll_number: number | null;
  confidence: number;
}

export const HEADER_BAR = 0.8;

export type Match =
  | { state: "matched"; roll: number; by: "name" | "header" }
  | { state: "other_class"; roll: number; found: string }
  | { state: "needs_roll" };

/** Match one picture. `header` is what the reader saw in the sheet's header, when it was read. */
export function matchPicture(name: string, header: Header | null | undefined, classCode: string | null, size: number | null): Match {
  const inRange = (n: number) => n >= 1 && (size === null || n <= Math.max(size, 100));
  const fromName = parseFileName(name);
  if (fromName && inRange(fromName.roll)) {
    if (fromName.classCode && classCode && fromName.classCode !== classCode.toUpperCase()) return { state: "other_class", roll: fromName.roll, found: fromName.classCode };
    return { state: "matched", roll: fromName.roll, by: "name" };
  }
  if (header && header.confidence >= HEADER_BAR) {
    const hc = sectionOf(header.class_code);
    const roll = header.roll_number;
    if (roll !== null && inRange(roll)) {
      if (hc && classCode && hc !== classCode.toUpperCase()) return { state: "other_class", roll, found: hc };
      return { state: "matched", roll, by: "header" };
    }
  }
  return { state: "needs_roll" };
}

export interface Summary {
  found: number;
  matched: number;
  needRoll: number;
  otherClass: number;
  skipped: number;
}

export function summarise(all: number, skipped: number, matches: Match[]): Summary {
  return {
    found: all,
    matched: matches.filter((m) => m.state === "matched").length,
    needRoll: matches.filter((m) => m.state === "needs_roll").length,
    otherClass: matches.filter((m) => m.state === "other_class").length,
    skipped,
  };
}

/** Rolls claimed by more than one picture (index lists), so she can choose one. */
export function duplicates(rolls: (number | null)[]): Map<number, number[]> {
  const by = new Map<number, number[]>();
  rolls.forEach((r, i) => {
    if (r !== null) by.set(r, [...(by.get(r) ?? []), i]);
  });
  for (const [r, list] of by) if (list.length < 2) by.delete(r);
  return by;
}

export async function sha256Hex(blob: Blob): Promise<string> {
  const buf = await blob.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export interface QueueProgress {
  done: number;
  total: number;
}

/** Run `work` over `items`, at most `limit` at a time. A failure of one does not stop the rest; Cancel
 *  (the signal) stops starting new ones. Resolves with the indexes that were started. */
export async function runQueue<T>(items: T[], work: (item: T, index: number) => Promise<void>, opts: { limit?: number; signal?: AbortSignal; onProgress?: (p: QueueProgress) => void } = {}): Promise<number[]> {
  const limit = Math.max(1, opts.limit ?? READ_AT_ONCE);
  const started: number[] = [];
  let next = 0;
  let done = 0;
  const lane = async () => {
    while (!opts.signal?.aborted) {
      const i = next++;
      if (i >= items.length) return;
      started.push(i);
      try {
        await work(items[i] as T, i);
      } catch {
        /* the worker reports its own failure on the item */
      }
      done += 1;
      opts.onProgress?.({ done, total: items.length });
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, lane));
  return started;
}
