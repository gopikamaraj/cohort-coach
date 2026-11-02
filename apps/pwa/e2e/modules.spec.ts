// Improvement-track modules in the browser: the timeline, the closed Get the next module button and its reason,
// feedback, the next module, axe, offline, and Hindi and Tamil at 360 px. (Written to run on the production
// build with SPEECH_MODE=stub; not yet run: the browser tests are with Gopi.)
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { enterRolls, finishEntering, startSample } from "./sample";
import { chooseLanguage, chooseRole } from "./switch";

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = JSON.parse(readFileSync(path.join(here, "fixtures", "results16.json"), "utf-8")) as { children: { answers: string[] }[] };

async function trackStarted(page: Page): Promise<void> {
  await startSample(page, { size: fx.children.length });
  await enterRolls(page, fx.children.map((c) => c.answers));
  await finishEntering(page);
  await page.goto("/#/cards");
  await page.getByTestId("class-cohort-open").click();
  await page.getByTestId("class-cohort-create").click();
  await expect(page.getByTestId("class-cohort-made")).toBeVisible();
  await page.goto("/#/cohort");
  await page.getByTestId("module-start").click();
  await expect(page.getByTestId("module-1")).toBeVisible();
}

test.use({ viewport: { width: 360, height: 800 } });

test("starting makes Module 1 only; later modules show a title and a due date; Get the next module is closed with its reason", async ({ page }) => {
  await trackStarted(page);
  await expect(page.getByTestId("module-1-status")).toContainText("Ready");
  await expect(page.getByTestId("module-1-text")).toBeVisible();
  await expect(page.getByTestId("module-2-status")).toContainText("Coming");
  await expect(page.getByTestId("module-2-due")).toContainText("Due");
  await expect(page.getByTestId("module-2-text")).toHaveCount(0); // not made, so no content
  await expect(page.getByTestId("module-next")).toBeDisabled();
  await expect(page.getByTestId("module-next-note")).toContainText("Give feedback on Module 1 to get Module 2, or it will arrive on");
  const body = await page.getByTestId("module-track").innerText();
  expect(body).not.toMatch(/lesson/i);
  expect(body).not.toContain("%");
});

test("an answer opens the button, and Get the next module makes Module 2 with the reason", async ({ page }) => {
  await trackStarted(page);
  await page.getByTestId("module-1-fb-partly").check();
  await page.getByTestId("module-1-fb-send").click();
  await expect(page.getByTestId("module-1-answered")).toBeVisible();
  await expect(page.getByTestId("module-next")).toBeEnabled();
  await page.getByTestId("module-next").click();
  await expect(page.getByTestId("module-2-status")).toContainText("Ready");
  await page.getByTestId("module-2-why").locator("summary").click();
  await expect(page.getByTestId("module-2-why")).toContainText("Module 2 is a smaller step of the same approach because you told us Module 1 partly worked.");
  await expect(page.getByTestId("module-1-status")).toContainText("Done");
});

test("Download audio on a module saves a file named for the module and marks it taken", async ({ page }) => {
  await trackStarted(page);
  const download = page.waitForEvent("download");
  await page.getByTestId("module-1-audio").click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^Cohort-Coach-Improvement-Track-Module-1-.*-en-\d{4}-\d{2}-\d{2}\.mp3$/);
  await expect(page.getByTestId("module-1-status")).toContainText("Audio taken");
});

test("the track passes axe", async ({ page }) => {
  await trackStarted(page);
  const found = (await new AxeBuilder({ page }).include("[data-testid=module-track]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(",")}`)).toEqual([]);
});

for (const lang of ["hi", "ta"]) {
  test(`${lang}: the timeline fits at 360 px`, async ({ page }) => {
    await trackStarted(page);
    await chooseLanguage(page, lang);
    await page.goto("/#/cohort");
    await expect(page.getByTestId("module-list")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("offline: the saved module text opens and getting the next module says it needs a connection", async ({ page, context }) => {
  await trackStarted(page);
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.waitForFunction(async () => (await caches.keys()).length > 0);
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("module-1-text")).toBeVisible();
  await expect(page.getByTestId("module-next")).toBeDisabled();
  await expect(page.getByTestId("module-next-note")).toContainText("needs a connection");
  await context.setOffline(false);
});

test("a coach sees counts per module and can move the remaining dates", async ({ page }) => {
  await trackStarted(page);
  await chooseRole(page, "coach");
  await page.goto("/#/cohort");
  const box = page.getByTestId("class-only-coach");
  await expect(box.locator("[data-testid^=coach-modules-]")).toBeVisible();
  await expect(page.getByTestId("coach-module-1")).toBeVisible();
  await page.getByTestId("coach-shift-days").fill("3");
  await page.getByTestId("coach-shift-reason").fill("school holiday");
  await page.getByTestId("coach-shift-apply").click();
  const text = await box.innerText();
  expect(text).not.toMatch(/[0-9a-f]{16}/); // no device id
});

test("the feedback card has four answers with icons, and Send is closed until one is chosen", async ({ page }) => {
  await trackStarted(page);
  const card = page.getByTestId("module-1-feedback");
  await expect(card).toContainText("How did Module 1 go?");
  for (const a of ["worked", "partly", "not_yet", "not_tried"]) await expect(page.getByTestId(`module-1-fb-${a}`)).toBeVisible();
  await expect(card).toContainText("It worked");
  await expect(card).toContainText("It partly worked");
  await expect(card).toContainText("Not yet working");
  await expect(card).toContainText("I didn't try it yet");
  await expect(card).toContainText("A short note (optional, no names)");
  await expect(page.getByTestId("module-1-fb-send")).toBeDisabled();
  await page.getByTestId("module-1-fb-worked").check();
  await expect(page.getByTestId("module-1-fb-send")).toBeEnabled();
});

test("I didn't try it yet holds the module: one question, a shorter version, a way to ask, and the next module still works", async ({ page }) => {
  await trackStarted(page);
  await page.getByTestId("module-1-fb-not_tried").check();
  await page.getByTestId("module-1-fb-send").click();
  const hold = page.getByTestId("module-1-hold");
  await expect(hold).toContainText("Why not yet?");
  await expect(hold).toContainText("not counted as a result");
  for (const c of ["no_time", "materials", "not_sure", "absent", "other"]) await expect(page.getByTestId(`module-1-chip-${c}`)).toBeVisible();
  await page.getByTestId("module-1-chip-no_time").click();
  await expect(hold).toContainText("We noted: No time");
  await hold.getByText("Try a shorter version").click();
  await expect(page.getByTestId("module-1-short")).toBeVisible();
  await expect(page.getByTestId("module-1-ask")).toBeVisible();
  await expect(page.getByTestId("module-1-status")).not.toContainText("Done"); // the module stays open
  await expect(page.getByTestId("module-next")).toBeEnabled(); // always works for her
  const box = await page.getByTestId("module-1-chip-no_time").boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  const found = (await new AxeBuilder({ page }).include("[data-testid=module-track]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => v.id)).toEqual([]);
  for (const lang of ["hi", "ta"]) {
    await chooseLanguage(page, lang);
    await page.goto("/#/cohort");
    await expect(page.getByTestId("module-1-hold")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  }
});
