// Demo Studio on the phone: the judge's demo session, the 12 steps (and the optional 13th), the API
// calls, and reading a demo sheet's label from its PNG. Everything here is a made-up class, and the
// screens say so. The server decides and computes; this file sends, stores and shows.
import { API_BASE } from "./api";
import type { Route } from "./router";

export const SESSION_KEY = "cc.demo.session";
export const STEP_KEY = "cc.demo.step";
export const READS_KEY = "cc.demo.reads";
export const PAPER_KEY = "cc.demo.paper";
export const LAST_STEP = 12; // the counted steps; step 13 (two classes) is optional

export type DemoRole = "teacher" | "coach" | "officer";

export interface DemoStep {
  n: number;
  role: DemoRole;
  route: Route;
  query?: string;
  question: string; // the judge guide's question for this screen (assistant bank id)
}

// The path: each step opens the right screen as the right role. Screens are the product's own.
export const STEPS: DemoStep[] = [
  { n: 1, role: "teacher", route: "/demo", query: "step=1", question: "j02" },
  { n: 2, role: "teacher", route: "/papers", question: "j43" },
  { n: 3, role: "teacher", route: "/demo", query: "step=3", question: "j11" },
  { n: 4, role: "teacher", route: "/demo", query: "step=4", question: "j11" },
  { n: 5, role: "teacher", route: "/demo", query: "step=5", question: "j04" },
  { n: 6, role: "teacher", route: "/demo", query: "step=6", question: "j37" },
  { n: 7, role: "teacher", route: "/demo", query: "step=7", question: "j14" },
  { n: 8, role: "teacher", route: "/demo", query: "step=8", question: "j20" },
  { n: 9, role: "teacher", route: "/practice", query: "next=ask_explain", question: "j10" },
  { n: 10, role: "teacher", route: "/demo", query: "step=10", question: "j15" },
  { n: 11, role: "coach", route: "/demo", query: "step=11", question: "j21" },
  { n: 12, role: "teacher", route: "/demo", query: "step=12", question: "j37" },
  { n: 13, role: "teacher", route: "/two-classes", query: "step=1", question: "j48" },
];

function store(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function newSessionId(): string {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return "demo-" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function demoSession(): string | null {
  return store()?.getItem(SESSION_KEY) ?? null;
}

export function demoStep(): number | null {
  const v = Number(store()?.getItem(STEP_KEY) ?? "");
  return Number.isInteger(v) && v >= 1 && v <= STEPS.length ? v : null;
}

export function setDemoStep(n: number | null): void {
  const s = store();
  if (!s) return;
  if (n === null) s.removeItem(STEP_KEY);
  else s.setItem(STEP_KEY, String(n));
  window.dispatchEvent(new Event("cc-demo"));
}

export function stepHref(step: DemoStep): string {
  return `#${step.route}${step.query ? `?${step.query}` : ""}`;
}

/** The server's plain message from an error body (a string, or {message}); "" when there is none. */
export function detailText(detail: unknown): string {
  const d = detail as { message?: unknown } | string | null;
  if (typeof d === "string") return d;
  return d && typeof d === "object" && typeof d.message === "string" ? d.message : "";
}

export class DemoError extends Error {
  constructor(
    public status: number,
    public detail: unknown = null,
  ) {
    // The message is the server's own words (never "demo 503"): screens show it as it is, or their
    // own fallback when it is empty. (A getter would be hidden by the message Error sets itself.)
    super(detailText(detail));
    this.name = "DemoError";
  }
}

export async function dcall<T>(path: string, init: { method?: string; body?: unknown; form?: FormData } = {}, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetchFn(`${API_BASE}/api/demo${path}`, { method: init.method ?? (init.body !== undefined || init.form ? "POST" : "GET"), headers, body: init.form ?? (init.body === undefined ? undefined : JSON.stringify(init.body)) });
  } catch {
    throw new DemoError(0);
  }
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
    } catch {
      /* no body */
    }
    throw new DemoError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function demoBlob(path: string, fetchFn: typeof fetch = (...a) => fetch(...a)): Promise<Blob> {
  const res = await fetchFn(`${API_BASE}/api/demo${path}`);
  if (!res.ok) throw new DemoError(res.status);
  return res.blob();
}

/** Start (or resume) this device's demo session. */
export async function startDemo(seed?: number): Promise<DemoSummary> {
  const sid = demoSession() ?? newSessionId();
  store()?.setItem(SESSION_KEY, sid);
  return dcall<DemoSummary>("/session", { body: { session: sid, ...(seed !== undefined ? { seed } : {}) } });
}

/** Reset: the server clears this session's rows; this phone forgets its demo state. */
export async function resetDemo(): Promise<void> {
  const sid = demoSession();
  if (sid) await dcall(`/session/${sid}`, { method: "DELETE" }).catch(() => undefined);
  for (const k of [SESSION_KEY, STEP_KEY, READS_KEY, PAPER_KEY]) store()?.removeItem(k);
  window.dispatchEvent(new Event("cc-demo"));
}

export interface DemoSummary {
  session: string;
  simulated: boolean;
  label: string;
  seed: number;
  class_code: string;
  strength: number;
  form: string;
  paper_id: string | null;
  ai_reads: number;
  ai_reads_cap: number;
}

export interface ReadCell {
  text: string;
  status: "ok" | "check" | "blank";
  confidence?: number;
}

export interface ReadsFile {
  demo: boolean;
  class_code: string;
  check_code: string;
  form: string;
  sheets: Record<string, { roll: number; cells: ReadCell[]; hard: string | null }>;
}

export function saveReads(reads: ReadsFile): void {
  try {
    store()?.setItem(READS_KEY, JSON.stringify(reads));
  } catch {
    /* storage full: the server keeps its copy */
  }
}

export function loadReads(): ReadsFile | null {
  try {
    const raw = store()?.getItem(READS_KEY);
    const data = raw ? (JSON.parse(raw) as ReadsFile) : null;
    return data && data.demo && data.sheets ? data : null;
  } catch {
    return null;
  }
}

/** The text chunks of a PNG (tEXt), read on the phone. A demo sheet carries `cohort-coach-demo`. */
export function pngText(bytes: Uint8Array): Record<string, string> {
  const out: Record<string, string> = {};
  const sig = [137, 80, 78, 71, 13, 10, 26, 10];
  if (bytes.length < 8 || sig.some((b, i) => bytes[i] !== b)) return out;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let p = 8;
  const latin1 = new TextDecoder("latin1");
  const utf8 = new TextDecoder("utf-8");
  while (p + 8 <= bytes.length) {
    const len = view.getUint32(p);
    const type = latin1.decode(bytes.subarray(p + 4, p + 8));
    const data = bytes.subarray(p + 8, p + 8 + len);
    if (type === "tEXt") {
      const zero = data.indexOf(0);
      if (zero > 0) out[latin1.decode(data.subarray(0, zero))] = latin1.decode(data.subarray(zero + 1));
    } else if (type === "iTXt") {
      const zero = data.indexOf(0);
      if (zero > 0) {
        const key = latin1.decode(data.subarray(0, zero));
        let q = zero + 3; // compression flag, method
        q = data.indexOf(0, q) + 1; // language tag
        q = data.indexOf(0, q) + 1; // translated keyword
        out[key] = utf8.decode(data.subarray(q));
      }
    } else if (type === "IEND") break;
    p += 12 + len;
  }
  return out;
}

export interface SheetMatch {
  roll: number | null;
  demo: boolean;
  by: "name" | "label" | null;
  checkCode: string | null;
}

/** Which roll number an uploaded sheet is: the file name first (3A-roll07.png), then the sheet's
 *  printed demo label in its metadata. */
export function matchSheet(name: string, meta: Record<string, string>, classCode: string): SheetMatch {
  const demo = meta["cohort-coach-demo"] === "1";
  const checkCode = meta["demo-check-code"] ?? null;
  const m = new RegExp(`^${classCode.replace(/[^A-Za-z0-9]/g, "")}-roll(\\d{2})\\.png$`, "i").exec(name.trim());
  if (m) return { roll: Number(m[1]), demo, by: "name", checkCode };
  const r = Number(meta["demo-roll"] ?? "");
  if (demo && Number.isInteger(r) && r > 0) return { roll: r, demo, by: "label", checkCode };
  return { roll: null, demo, by: null, checkCode };
}

/** A row of answers (as the check screen stores them) from read cells. */
export function rowFrom(cells: ReadCell[], items: number): string[] {
  return Array.from({ length: items }, (_, i) => {
    const c = cells[i];
    return !c || c.status === "blank" ? "" : c.text;
  });
}

export type RollStatus = "empty" | "needs_review" | "approved" | "absent" | "no_sheet";

export const DEMO_CLASS_NAME = (code: string) => `Class ${code} (demo)`;

/** Reset on the phone: only the demo class, its checks and its results go; nothing else. */
export async function clearDemoClass(): Promise<void> {
  const { db, getSetting, setSetting } = await import("./db");
  const demo = (await db.classes.toArray()).filter((c) => / \(demo\)$/.test(c.name));
  for (const c of demo) {
    await db.checks.where("classId").equals(c.id).delete();
    await db.profiles.where("classId").equals(c.id).delete();
    await db.classes.delete(c.id);
    if ((await getSetting<string | null>("activeClass", null)) === c.id) await setSetting("activeClass", null);
  }
  for (const k of ["cc.demo.entry", "cc.demo.paper.code"]) store()?.removeItem(k);
}

// --- pilot sheets as a local data source (only on a machine that has the folder) ---------------------

export const SOURCE_KEY = "cc.demo.source";
export type DemoSource = "synthetic" | "pilot";

export function demoSource(): DemoSource {
  return store()?.getItem(SOURCE_KEY) === "pilot" ? "pilot" : "synthetic";
}

export function setDemoSource(source: DemoSource): void {
  store()?.setItem(SOURCE_KEY, source);
  window.dispatchEvent(new Event("cc-demo"));
}

export interface PilotRoll {
  roll: number;
  status: "entered" | "absent" | "no_sheet";
  has_image: boolean;
  in_answer_file: boolean;
}
export interface PilotClassInfo {
  class_code: string;
  teacher_label: string;
  strength: number;
  test_date: string;
  rolls: PilotRoll[];
  dictation_override: boolean;
}
export interface PilotManifest {
  banner: string;
  classes: PilotClassInfo[];
  ai_reads: number;
  ai_reads_cap: number;
}
export type PilotProbe = { state: "hidden" } | { state: "disabled"; reason: string } | { state: "ready"; manifest: PilotManifest };

export interface PilotAutofill {
  label: string;
  sheets: { roll: number; cells: ReadCell[]; verified: boolean; has_image: boolean }[];
  no_sheet: number[];
  unread: number[];
  absent: number[];
}

/** A call to the pilot data routes (Enter check, on a machine that has the pilot folder). They never run in the browser's cache. */
export async function pilotFetch(path: string, init: RequestInit = {}): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/pilot-data${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new DemoError(0);
  }
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = ((await res.json()) as { detail?: unknown }).detail ?? null;
    } catch {
      /* no body */
    }
    throw new DemoError(res.status, detail);
  }
  return res;
}

/** Hidden on any machine without the folder (the hosted demo); disabled, with a reason, when the folder
 *  is there but not ready (no manifest, no consent note, no answer file). */
export async function pilotProbe(): Promise<PilotProbe> {
  try {
    return { state: "ready", manifest: (await (await pilotFetch("/manifest")).json()) as PilotManifest };
  } catch (e) {
    const d = e instanceof DemoError ? (e.detail as { show?: boolean; reason?: string } | null) : null;
    return d && typeof d === "object" && d.show ? { state: "disabled", reason: d.reason ?? "" } : { state: "hidden" };
  }
}

export async function pilotRead(classCode: string, roll: number, file?: Blob, paperId?: string | null): Promise<{ cells: ReadCell[] }> {
  const form = new FormData();
  form.append("class_code", classCode);
  form.append("roll", String(roll));
  if (paperId) form.append("paper_id", paperId); // read with the chosen paper's own key
  if (file) form.append("image", file, "sheet.jpg");
  return (await pilotFetch("/read", { method: "POST", body: form })).json();
}

export async function pilotAutofill(classCode: string, skip: number[]): Promise<PilotAutofill> {
  return (await pilotFetch("/autofill", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ class_code: classCode, skip }) })).json();
}

export async function pilotSheet(classCode: string, roll: number): Promise<Blob> {
  return (await pilotFetch(`/sheet/${encodeURIComponent(classCode)}/${roll}`)).blob();
}
