// Read an answer-sheet photo (call 8, on the server) into one child's boxes. The photo is shrunk on
// the phone, sent, and dropped: it is never saved here or on the server. The reads come back as
// suggestions: boxes the model was unsure of are marked, and the teacher checks every box anyway.
import { API_BASE } from "./api";
import { BLANK } from "./check";
import type { Header } from "./folder";

export type CellStatus = "ok" | "check" | "blank";

export interface SheetCell {
  text: string;
  status: CellStatus;
}

export type SheetFail = "offline" | "typing" | "bad_photo" | "paused" | "cancelled" | "other";

export class SheetError extends Error {
  constructor(public kind: SheetFail) {
    super(kind);
  }
}

const MAX_EDGE = 1600;
const JPEG_QUALITY = 0.7;
const TIMEOUT_MS = 30_000;

/** The reads as a row of typed cells, and which boxes the teacher should look at first. */
export function applyReads(cells: SheetCell[], items: number): { row: string[]; flagged: number[] } {
  const row: string[] = [];
  const flagged: number[] = [];
  for (let i = 0; i < items; i += 1) {
    const cell = cells[i];
    if (!cell) {
      row.push("");
      flagged.push(i);
    } else if (cell.status === "blank") {
      row.push(BLANK);
    } else {
      row.push(cell.text);
      if (cell.status === "check") flagged.push(i);
    }
  }
  return { row, flagged };
}

/** Shrink to about 1600 px on the long edge as a JPEG (about 150 KB), so it uploads on a weak signal. */
export async function downscale(file: Blob): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("no canvas");
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
    if (!blob) throw new Error("no blob");
    return blob;
  } catch {
    throw new SheetError("bad_photo");
  }
}

export interface SheetRead {
  cells: SheetCell[];
  header: Header | null;
}

/** Read one sheet. `sha256` is the hash of the original file, so a recording can be replayed by file. */
export async function readSheetFull(photo: Blob, form: string, opts: { sha256?: string; signal?: AbortSignal; fetchFn?: typeof fetch } = {}): Promise<SheetRead> {
  const fetchFn = opts.fetchFn ?? ((...a: Parameters<typeof fetch>) => fetch(...a));
  const body = new FormData();
  body.append("image", photo, "sheet.jpg");
  body.append("form", form);
  if (opts.sha256) body.append("sha256", opts.sha256);
  const ctrl = new AbortController();
  opts.signal?.addEventListener("abort", () => ctrl.abort());
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/sheets/read`, { method: "POST", body, signal: ctrl.signal });
  } catch {
    throw new SheetError(opts.signal?.aborted ? "cancelled" : "offline");
  } finally {
    clearTimeout(timer);
  }
  if (res.ok) {
    const out = (await res.json()) as { cells: SheetCell[]; header?: Header | null };
    return { cells: out.cells, header: out.header ?? null };
  }
  if (res.status === 503) {
    const detail = ((await res.json().catch(() => ({}))) as { detail?: { message?: string } }).detail;
    throw new SheetError(detail?.message === "Reading is paused." ? "paused" : "typing");
  }
  if (res.status === 413 || res.status === 422) throw new SheetError("bad_photo");
  throw new SheetError("other");
}

export async function readSheet(photo: Blob, form: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<SheetCell[]> {
  return (await readSheetFull(photo, form, { fetchFn })).cells;
}
