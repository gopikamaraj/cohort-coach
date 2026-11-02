// Shared helpers for the QA walks (demo-path*.spec.ts, qa-screens.spec.ts): a fresh judge device,
// axe on a screen, a screenshot per step (synthetic data only) and layout checks.
import AxeBuilder from "@axe-core/playwright";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, type Page } from "@playwright/test";

export const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
export const SHOTS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../docs/build/qa/screens");
export const PDF = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "paper-to-import.pdf");

export const PHONE = { width: 390, height: 844 };
export const DESKTOP = { width: 1280, height: 800 };

/** A clean device: consent given, the role and language chosen, nothing else stored. */
export async function fresh(page: Page, role = "judge", lang = "en") {
  await page.goto("/");
  await page.evaluate(
    ([c, r, l]) => {
      localStorage.clear();
      localStorage.setItem("cc.consent", c);
      localStorage.setItem("cc.role", r);
      localStorage.setItem("cc.lang", l);
      localStorage.setItem("cc.voice", "0");
    },
    [CONSENT, role, lang],
  );
}

/** axe (WCAG 2 A and AA): a soft check, so one run lists every screen with a problem. */
export async function axe(page: Page, where: string) {
  const found = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect.soft(found.map((v) => `${where}: ${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

/** One screenshot per step and viewport: docs/build/qa/screens/<viewport>-<name>.jpg. */
export async function shot(page: Page, viewport: string, name: string) {
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${viewport}-${name}.jpg`), type: "jpeg", quality: 60, fullPage: true });
}

/** No horizontal page scroll (the layout fits the viewport). */
export async function fits(page: Page, where: string) {
  const wide = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect.soft(wide, `${where}: horizontal scroll of ${wide}px`).toBeLessThanOrEqual(1);
}

/** No raw string key ("demo.s4.title") and no stack trace in the visible text. */
export async function noRawText(page: Page, where: string) {
  const text = await page.locator("body").innerText();
  const keys = text.match(/\b[a-z]{2,}\.[a-z0-9_]{2,}\.[a-z0-9_.]{2,}\b/g) ?? [];
  expect.soft(keys.filter((k) => !/\.(png|pdf|json|zip|jpg|md|yaml|py|ts|tsx)$/.test(k)), `${where}: raw string keys`).toEqual([]);
  expect.soft(/Traceback|at Object\.|TypeError:|undefined is not|\[object Object\]/.test(text), `${where}: raw error text`).toBe(false);
}

/** Every visible button and link is at least 44 px tall or wide enough to tap (a soft check). */
export async function targets(page: Page, where: string) {
  const small = await page.evaluate(() => {
    const out: string[] = [];
    for (const el of Array.from(document.querySelectorAll<HTMLElement>("button, a.btn, a.chip-btn, [role=tab], select, input[type=text], input:not([type])"))) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0 || getComputedStyle(el).visibility === "hidden") continue;
      if (el.closest(".sr, [hidden]")) continue;
      if (r.height < 43.5 && !(el.closest("label") && el.closest("label")!.getBoundingClientRect().height >= 43.5)) out.push(`${el.tagName.toLowerCase()}${el.dataset["testid"] ? `#${el.dataset["testid"]}` : ""} ${Math.round(r.height)}px "${(el.innerText || el.getAttribute("aria-label") || "").slice(0, 30)}"`);
    }
    return out;
  });
  expect.soft(small, `${where}: tap targets under 44 px`).toEqual([]);
}

/** All the per-screen checks at once. */
export async function screen(page: Page, viewport: string, name: string) {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await axe(page, `${viewport} ${name}`);
  await fits(page, `${viewport} ${name}`);
  await noRawText(page, `${viewport} ${name}`);
  await targets(page, `${viewport} ${name}`);
  await shot(page, viewport, name);
}
