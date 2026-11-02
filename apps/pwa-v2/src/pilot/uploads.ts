// The upload queue behind Upload sheets. Photos are shrunk on the phone, checksummed, saved in
// IndexedDB, and sent one at a time: ask the server for a signed URL, PUT the file to the private
// store, tell the server it is there. With no signal a sheet stays "queued" and goes when the
// signal returns. Nothing here reads a photo or knows a child: only codes and bytes.
import { downscale } from "../lib/sheets";
import { jsonInit, pilotFetch, resolveUrl, type Session, PilotApiError } from "./api";
import { pilotDb, type PilotDb, type UploadRow } from "./db";

export const ACCEPT = "image/jpeg,image/png,image/heic,image/heif,application/pdf";
const BY_EXT: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  heic: "image/heic",
  heif: "image/heif",
  pdf: "application/pdf",
};
const MIMES = new Set(Object.values(BY_EXT));
export const MAX_BYTES = 8_000_000;

export interface Meta {
  schoolCode: string;
  classCode: string;
  teacherRef: string;
  consentRef: string;
}

/** The kind of file, from its type or (some phones leave the type empty for HEIC) its extension. */
export function fileMime(file: { type: string; name: string }): string | null {
  const type = file.type.toLowerCase();
  if (MIMES.has(type)) return type === "image/heif" ? "image/heic" : type;
  const ext = file.name.toLowerCase().split(".").pop() ?? "";
  const byExt = BY_EXT[ext];
  return byExt ? (byExt === "image/heif" ? "image/heic" : byExt) : null;
}

const CODE = /^[A-Za-z0-9][A-Za-z0-9-]{1,23}$/;
const CLASS = /^[A-Za-z0-9][A-Za-z0-9-]{0,11}$/;
const CONSENT = /^[A-Za-z0-9][A-Za-z0-9 ./_-]{2,59}$/;

/** Why sheets cannot be added yet, or "ok". The server checks the same things again. */
export function gate(meta: Meta, consentConfirmed: boolean): "ok" | "codes" | "consent" {
  if (!consentConfirmed || !CONSENT.test(meta.consentRef.trim())) return "consent";
  const good =
    CODE.test(meta.schoolCode.trim()) && CLASS.test(meta.classCode.trim()) && CODE.test(meta.teacherRef.trim());
  return good ? "ok" : "codes";
}

export async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Shrink a photo to about 80 KB; a file the browser cannot decode (HEIC on some phones) or a PDF is sent as it is. */
export async function prepare(file: File, mime: string): Promise<Blob> {
  if (mime === "application/pdf") return file;
  try {
    return await downscale(file);
  } catch {
    return file;
  }
}

export interface AddResult {
  added: number;
  skipped: number;
  rejected: number;
}

export async function addFiles(
  files: File[],
  meta: Meta,
  store: PilotDb = pilotDb,
  prep: (file: File, mime: string) => Promise<Blob> = prepare,
): Promise<AddResult> {
  const out: AddResult = { added: 0, skipped: 0, rejected: 0 };
  for (const file of files) {
    const mime = fileMime(file);
    if (!mime || file.size > MAX_BYTES * 4) {
      out.rejected += 1;
      continue;
    }
    const blob = await prep(file, mime);
    // a shrunk photo is a JPEG whatever it was before
    const sent = blob === file ? mime : "image/jpeg";
    if (blob.size > MAX_BYTES) {
      out.rejected += 1;
      continue;
    }
    const sha256 = await sha256Hex(blob);
    const same = await store.uploads.where("sha256").equals(sha256).toArray();
    if (same.some((r) => r.schoolCode === meta.schoolCode.trim())) {
      out.skipped += 1;
      continue;
    }
    await store.uploads.add({
      blob,
      mime: sent,
      sha256,
      bytes: blob.size,
      schoolCode: meta.schoolCode.trim(),
      classCode: meta.classCode.trim(),
      teacherRef: meta.teacherRef.trim(),
      consentRef: meta.consentRef.trim(),
      status: "queued",
      createdAt: Date.now(),
    });
    out.added += 1;
  }
  return out;
}

export async function retryUpload(id: number, store: PilotDb = pilotDb): Promise<void> {
  await store.uploads.update(id, { status: "queued", error: undefined });
}

export async function removeUpload(id: number, store: PilotDb = pilotDb): Promise<void> {
  await store.uploads.delete(id);
}

export async function clearFinished(store: PilotDb = pilotDb): Promise<void> {
  await store.uploads.where("status").equals("stored").delete();
}

let running = false;

/** Send every queued sheet, oldest first. Stops quietly at the first sign of no signal. */
export async function flushUploads(
  session: Session,
  store: PilotDb = pilotDb,
  fetchFn: typeof fetch = (...a) => fetch(...a),
  onChange: () => void = () => undefined,
): Promise<void> {
  if (running) return;
  running = true;
  try {
    const queued = await store.uploads.where("status").equals("queued").sortBy("id");
    for (const row of queued) {
      if (row.id === undefined) continue;
      await store.uploads.update(row.id, { status: "uploading", error: undefined });
      onChange();
      const outcome = await sendOne(row, session, fetchFn);
      if (outcome.kind === "offline" || outcome.kind === "ended") {
        await store.uploads.update(row.id, { status: "queued" });
        onChange();
        return;
      }
      if (outcome.kind === "failed") await store.uploads.update(row.id, { status: "failed", error: outcome.error });
      else
        await store.uploads.update(row.id, {
          status: "stored",
          duplicate: outcome.duplicate,
          sheetId: outcome.id,
          blob: new Blob([]), // the server has it; free the phone's space
        });
      onChange();
    }
  } finally {
    running = false;
  }
}

type Outcome =
  | { kind: "stored"; id: string; duplicate: boolean }
  | { kind: "failed"; error: string }
  | { kind: "offline" }
  | { kind: "ended" };

async function sendOne(row: UploadRow, session: Session, fetchFn: typeof fetch): Promise<Outcome> {
  try {
    const init = await pilotFetch(
      "/api/pilot/sheets/init",
      jsonInit("POST", {
        school_code: row.schoolCode,
        class_code: row.classCode,
        teacher_ref: row.teacherRef,
        consent_confirmed: true,
        consent_ref: row.consentRef,
        sha256: row.sha256,
        bytes: row.bytes,
        mime: row.mime,
      }),
      session,
      fetchFn,
    );
    if (init.status === 401) return { kind: "ended" };
    if (!init.ok) return { kind: "failed", error: `init ${init.status}` };
    const body = (await init.json()) as {
      id: string;
      duplicate: boolean;
      upload?: { url: string; headers: Record<string, string> };
    };
    if (body.duplicate || !body.upload) return { kind: "stored", id: body.id, duplicate: true };
    const put = await fetchFn(resolveUrl(body.upload.url), {
      method: "PUT",
      headers: body.upload.headers,
      body: row.blob,
    });
    if (!put.ok) return { kind: "failed", error: `upload ${put.status}` };
    const done = await pilotFetch(`/api/pilot/sheets/${body.id}/complete`, { method: "POST" }, session, fetchFn);
    if (done.status === 401) return { kind: "ended" };
    if (!done.ok) return { kind: "failed", error: `complete ${done.status}` };
    return { kind: "stored", id: body.id, duplicate: false };
  } catch (e) {
    if (e instanceof PilotApiError && e.offline) return { kind: "offline" };
    if (e instanceof TypeError) return { kind: "offline" }; // the PUT could not reach the store
    return { kind: "failed", error: "error" };
  }
}

export function tally(rows: UploadRow[]): Record<UploadRow["status"], number> {
  const t = { queued: 0, uploading: 0, stored: 0, failed: 0 };
  for (const r of rows) t[r.status] += 1;
  return t;
}
