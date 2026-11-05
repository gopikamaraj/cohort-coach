// Optional on-screen overlay for watching a Playwright run in a visible browser (E2E_OVERLAY=1; off otherwise, and
// then nothing here runs). It draws a small panel over the page, pointer-events off so it never blocks a click:
// the spec being run, its position and the overall progress, the check being made now with its expected value, and
// on a failure what was received. Test files import `expect` from ./test, which wraps the real one with this.
import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import type { Page } from "@playwright/test";

export const OVERLAY_ON = process.env["E2E_OVERLAY"] === "1";
const FILE = process.env["E2E_PROGRESS_FILE"] ?? path.join(os.tmpdir(), "e2e_progress.txt");
const TOTAL = Number(process.env["E2E_TOTAL"] ?? 0);

export interface Step {
  text: string;
  state: "now" | "ok" | "fail";
  expected?: string;
  received?: string;
}
interface State {
  title: string;
  n: number;
  total: number;
  done: number;
  steps: Step[];
}

let current: Page | null = null;
const state: State = { title: "", n: 0, total: TOTAL, done: 0, steps: [] };

/** Called once per test: counts it (shared file, so it survives workers) and remembers the page. */
export function beginTest(page: Page, title: string): void {
  current = page;
  let started = 0;
  try {
    if (!existsSync(FILE)) writeFileSync(FILE, "");
    appendFileSync(FILE, title + "\n");
    started = readFileSync(FILE, "utf-8").split("\n").filter(Boolean).length;
  } catch {
    started = state.n + 1;
  }
  state.title = title;
  state.n = started;
  state.done = Math.max(0, started - 1);
  state.steps = [];
  void push();
}

export function endTest(failed: boolean): void {
  state.done = state.n;
  state.steps.push({ text: failed ? "test failed" : "test passed", state: failed ? "fail" : "ok" });
  void push();
}

async function push(): Promise<void> {
  const page = current;
  if (!page || page.isClosed()) return;
  const s = JSON.stringify(state);
  try {
    await page.evaluate((v) => {
      window.name = "cc-e2e:" + v;
      (window as unknown as { __ccOverlay?: (v: string) => void }).__ccOverlay?.(v);
    }, s);
  } catch {
    /* the page is navigating: the init script redraws from window.name when the next one loads */
  }
}

export function note(step: Step): void {
  const last = state.steps[state.steps.length - 1];
  if (last && last.state === "now" && step.state !== "now") state.steps[state.steps.length - 1] = step;
  else state.steps.push(step);
  if (state.steps.length > 6) state.steps.shift();
  void push();
}

const short = (v: unknown): string => {
  let t: string;
  try {
    t = v instanceof RegExp ? String(v) : typeof v === "string" ? JSON.stringify(v) : JSON.stringify(v) ?? String(v);
  } catch {
    t = String(v);
  }
  return t.length > 90 ? t.slice(0, 87) + "..." : t;
};
export const describeTarget = (a: unknown): string => {
  const t = String(a).replace(/internal:testid=\[data-testid="([^"]+)"s\]/g, "#$1").replace(/internal:/g, "");
  return t.length > 70 ? t.slice(0, 67) + "..." : t;
};
export const describeArgs = (args: unknown[]): string => (args.length ? short(args[0]) : "");

/** The init script that draws the panel; it reads window.name so a page reload keeps it. */
export const overlayScript = (): void => {
  const draw = (raw: string): void => {
    let s: { title: string; n: number; total: number; done: number; steps: { text: string; state: string; expected?: string; received?: string }[] };
    try {
      s = JSON.parse(raw);
    } catch {
      return;
    }
    const doc = document;
    let box = doc.getElementById("cc-e2e-overlay");
    if (!box) {
      box = doc.createElement("div");
      box.id = "cc-e2e-overlay";
      box.setAttribute(
        "style",
        "position:fixed;left:0;right:0;bottom:0;z-index:2147483647;pointer-events:none;font:11px/1.35 ui-monospace,Consolas,monospace;color:#fff;background:rgba(17,24,39,.92);padding:6px 8px;border-top:2px solid #38bdf8;max-height:46vh;overflow:hidden",
      );
      (doc.body ?? doc.documentElement).appendChild(box);
    }
    const pct = s.total > 0 ? Math.min(100, Math.round((s.done / s.total) * 100)) : 0;
    const esc = (t: string): string => t.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c] as string);
    const rows = s.steps
      .map((st) => {
        const c = st.state === "fail" ? "#f87171" : st.state === "ok" ? "#4ade80" : "#fde047";
        const mark = st.state === "fail" ? "✗" : st.state === "ok" ? "✓" : "…";
        let h = `<div style="color:${c}">${mark} ${esc(st.text)}</div>`;
        if (st.expected !== undefined) h += `<div style="color:#cbd5e1;padding-left:12px">expected: ${esc(st.expected)}</div>`;
        if (st.received !== undefined) h += `<div style="color:#fca5a5;padding-left:12px">received: ${esc(st.received)}</div>`;
        return h;
      })
      .join("");
    box.innerHTML =
      `<div style="font-weight:700;color:#7dd3fc">${s.total > 0 ? `test ${s.n} of ${s.total} · ${pct}%` : `test ${s.n}`}</div>` +
      `<div style="height:5px;background:#374151;margin:3px 0 4px"><div style="height:5px;width:${pct}%;background:#38bdf8"></div></div>` +
      `<div style="color:#e5e7eb;word-break:break-word">${esc(s.title)}</div>${rows}`;
  };
  (window as unknown as { __ccOverlay: (v: string) => void }).__ccOverlay = draw;
  const redraw = (): void => {
    if (window.name.startsWith("cc-e2e:")) draw(window.name.slice(7));
  };
  redraw();
  document.addEventListener("DOMContentLoaded", redraw);
};
