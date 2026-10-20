// Export and restore: one file holding her classes, checks (with per-child answers), results and rehearsals,
// so a lost or changed phone does not lose her work. The file holds children's answers, so it can be sealed
// with a passphrase (AES-GCM, key from PBKDF2). The photo outbox is never included. A restore merges: it never
// deletes what is already on the phone.
import { db, type CheckRow, type ClassRow, type CohortDb, type ProfileRow, type TranscriptRow } from "./db";

export const BACKUP_FORMAT = "cohort-coach-backup";
export const BACKUP_VERSION = 1;
const MAX_ROWS = 20_000;
const CLASS_ID = /^(c|sim)-[0-9a-f]{10}$/;
const KDF_ITERATIONS = 600_000; // OWASP guidance for PBKDF2-SHA256; the count is stored in the file

export interface Backup {
  format: typeof BACKUP_FORMAT;
  version: number;
  exportedAt: number;
  classes: ClassRow[];
  checks: CheckRow[];
  profiles: ProfileRow[];
  transcripts: TranscriptRow[];
  settings: { activeClass: string | null; term: number };
}

export async function buildBackup(store: CohortDb = db): Promise<Backup> {
  const [classes, checks, profiles, transcripts, active, term] = await Promise.all([
    store.classes.toArray(),
    store.checks.toArray(),
    store.profiles.toArray(),
    store.transcripts.toArray(),
    store.settings.get("activeClass"),
    store.settings.get("term"),
  ]);
  return {
    format: BACKUP_FORMAT,
    version: BACKUP_VERSION,
    exportedAt: Date.now(),
    classes,
    checks,
    profiles,
    transcripts: transcripts.map((row) => {
      const copy = { ...row };
      delete copy.id; // ids are local to this phone
      return copy;
    }),
    settings: { activeClass: (active?.value as string | null) ?? null, term: (term?.value as number | undefined) ?? 1 },
  };
}

/** A backup file is untrusted: check its shape, size and ids before anything is written. */
function validate(b: Backup): void {
  const bad = () => new Error("This file is not a valid Cohort Coach backup.");
  for (const key of ["classes", "checks", "profiles", "transcripts"] as const) {
    const rows = b[key] ?? [];
    if (!Array.isArray(rows) || rows.length > MAX_ROWS) throw bad();
  }
  for (const c of b.classes ?? []) if (typeof c?.id !== "string" || !CLASS_ID.test(c.id) || typeof c.name !== "string") throw bad();
  for (const row of [...(b.checks ?? []), ...(b.profiles ?? [])]) {
    if (typeof row?.id !== "string" || typeof row.classId !== "string" || !CLASS_ID.test(row.classId) || !Number.isInteger(row.term)) throw bad();
  }
  for (const c of b.checks ?? []) if (!Array.isArray(c.children) || c.children.length > 500 || c.children.some((r) => !Array.isArray(r) || r.length > 20 || r.some((v) => typeof v !== "string" || v.length > 12))) throw bad();
  for (const t of b.transcripts ?? []) if (typeof t?.classId !== "string" || !CLASS_ID.test(t.classId) || !Array.isArray(t.turns) || t.turns.length > 200) throw bad();
}

export interface RestoreResult {
  classes: number;
  checks: number;
  transcripts: number;
}

export async function restoreBackup(b: Backup, store: CohortDb = db): Promise<RestoreResult> {
  if (!b || b.format !== BACKUP_FORMAT) throw new Error("This file is not a Cohort Coach backup.");
  if (b.version > BACKUP_VERSION) throw new Error("This backup is from a newer version of the app.");
  validate(b);
  await store.classes.bulkPut(b.classes ?? []);
  await store.checks.bulkPut(b.checks ?? []);
  await store.profiles.bulkPut(b.profiles ?? []);
  const have = new Set((await store.transcripts.toArray()).map((t) => `${t.sessionId ?? ""}:${t.createdAt}`));
  let added = 0;
  for (const t of b.transcripts ?? []) {
    const key = `${t.sessionId ?? ""}:${t.createdAt}`;
    if (have.has(key)) continue;
    await store.transcripts.add(t);
    have.add(key);
    added += 1;
  }
  if ((await store.settings.get("activeClass")) === undefined && b.settings?.activeClass) await store.settings.put({ key: "activeClass", value: b.settings.activeClass });
  return { classes: (b.classes ?? []).length, checks: (b.checks ?? []).length, transcripts: added };
}

// ---- sealing with a passphrase -----------------------------------------------------------------

const enc = new TextEncoder();
const b64 = (u: Uint8Array) => {
  let s = "";
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000));
  return btoa(s);
};
const unb64 = (s: string): Uint8Array<ArrayBuffer> => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

async function key(pass: string, salt: Uint8Array<ArrayBuffer>, iterations: number): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey("raw", enc.encode(pass), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", salt, iterations, hash: "SHA-256" }, base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}

export async function sealBackup(b: Backup, pass: string): Promise<string> {
  const salt = crypto.getRandomValues(new Uint8Array(new ArrayBuffer(16)));
  const iv = crypto.getRandomValues(new Uint8Array(new ArrayBuffer(12)));
  const data = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await key(pass, salt, KDF_ITERATIONS), enc.encode(JSON.stringify(b))));
  return JSON.stringify({ format: `${BACKUP_FORMAT}-sealed`, version: BACKUP_VERSION, iterations: KDF_ITERATIONS, salt: b64(salt), iv: b64(iv), data: b64(data) });
}

/** Read a backup file's text: plain JSON, or a sealed file with its passphrase. */
export async function openBackup(text: string, pass: string): Promise<Backup> {
  let obj: Record<string, string>;
  try {
    obj = JSON.parse(text) as Record<string, string>;
  } catch {
    throw new Error("This file is not a Cohort Coach backup.");
  }
  if (obj["format"] === `${BACKUP_FORMAT}-sealed`) {
    if (!pass) throw new Error("This backup needs its passphrase.");
    try {
      const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(obj["iv"]!) }, await key(pass, unb64(obj["salt"]!), Math.min(Number(obj["iterations"]) || 200_000, 2_000_000)), unb64(obj["data"]!));
      return JSON.parse(new TextDecoder().decode(plain)) as Backup;
    } catch {
      throw new Error("The passphrase is wrong, or the file is damaged.");
    }
  }
  return obj as unknown as Backup;
}
