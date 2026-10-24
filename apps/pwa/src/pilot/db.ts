// What the pilot app keeps on the phone: the upload queue (photos until they are stored), the
// queued Generate requests, and the last audio list for offline viewing. A separate database from
// the main app's, so pilot mode never touches the teacher app's data.
import Dexie, { type Table } from "dexie";

export type UploadStatus = "queued" | "uploading" | "stored" | "failed";

export interface UploadRow {
  id?: number;
  blob: Blob; // emptied once the sheet is stored
  mime: string;
  sha256: string;
  bytes: number;
  schoolCode: string;
  classCode: string;
  teacherRef: string;
  consentRef: string;
  status: UploadStatus;
  duplicate?: boolean; // the server already had this exact photo
  sheetId?: string;
  error?: string;
  createdAt: number;
}

export interface JobRow {
  id?: number;
  kind: "generate";
  body: { language: string; voice: string; force: boolean };
  createdAt: number;
}

export interface KvRow {
  key: string;
  value: unknown;
}

export class PilotDb extends Dexie {
  uploads!: Table<UploadRow, number>;
  jobs!: Table<JobRow, number>;
  kv!: Table<KvRow, string>;

  constructor(name = "cohort-coach-pilot") {
    super(name);
    this.version(1).stores({ uploads: "++id, status, sha256", jobs: "++id", kv: "key" });
  }
}

export const pilotDb = new PilotDb();

export async function kvGet<T>(key: string, fallback: T, store: PilotDb = pilotDb): Promise<T> {
  try {
    const row = await store.kv.get(key);
    return row ? (row.value as T) : fallback;
  } catch {
    return fallback;
  }
}

export async function kvSet(key: string, value: unknown, store: PilotDb = pilotDb): Promise<void> {
  try {
    await store.kv.put({ key, value });
  } catch {
    /* storage blocked: the page still works, it just cannot show a saved copy offline */
  }
}
