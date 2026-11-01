// A cohort just for this teacher's class, its intervention content (text first, from the results) and the
// "Download audio" button (a mock voice here: SPEECH_MODE=stub, so no paid call is made).
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { chooseLanguage, chooseRole } from "./switch";
import { enterRolls, finishEntering, startSample } from "./sample";

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = JSON.parse(readFileSync(path.join(here, "fixtures", "results16.json"), "utf-8")) as { children: { answers: string[] }[]; class: { counts: Record<string, number> } };
const SHOTS = path.resolve(here, "../../../data/autopilot-screens");

async function enter16(page: Page): Promise<void> {
  await startSample(page, { size: fx.children.length });
  await enterRolls(page, fx.children.map((c) => c.answers));
  await finishEntering(page);
  await page.goto("/#/cards");
  await expect(page.getByTestId("answer-map")).toBeVisible();
}

async function makeCohort(page: Page): Promise<void> {
  await page.getByTestId("class-cohort-open").click();
  await page.getByTestId("class-cohort-create").click();
  await expect(page.getByTestId("class-cohort-made")).toBeVisible();
}

test.use({ viewport: { width: 390, height: 844 } });

test("create a cohort for my class: the most common error is chosen, only counts go, and it says Just my class", async ({ page }) => {
  await enter16(page);
  await page.getByTestId("class-cohort-open").click();
  const form = page.getByTestId("class-cohort-form");
  await expect(form).toContainText("Just my class: no other teachers yet");
  await expect(page.getByTestId("pick-SUB-SFL")).toBeChecked(); // 5 children, the most common
  await expect(page.getByTestId("pick-PV-HEARD")).not.toBeChecked();
  await expect(form).toContainText("5 of 16 children");
  await expect(page.getByTestId("class-cohort-name")).toHaveValue(/Takes the smaller digit from the larger/);
  await page.getByTestId("pick-PV-HEARD").check();
  const sent = page.waitForRequest((r) => r.url().includes("/api/cohorts/class-only") && r.method() === "POST");
  await page.getByTestId("class-cohort-create").click();
  const body = (await sent).postDataJSON() as Record<string, unknown>;
  // counts of the chosen errors only: no child, no answer, no roll number
  expect(Object.keys(body).sort()).toEqual(["check_id", "children_checked", "counts", "errors", "language", "name", "simulated"]);
  expect(body["counts"]).toEqual({ "PV-HEARD": fx.class.counts["PV-HEARD"], "SUB-SFL": fx.class.counts["SUB-SFL"] });
  await expect(page.getByTestId("class-cohort-made")).toContainText("Just my class: no other teachers yet");
  await page.reload();
  await expect(page.getByTestId("class-cohort-made")).toBeVisible(); // still there after a reload
  await expect(page.getByTestId("class-cohort-open")).toHaveCount(0); // one per check
});

test("the cohort page shows the pack, text first, from the class's own results", async ({ page }) => {
  await enter16(page);
  await makeCohort(page);
  await page.getByTestId("to-class-cohort").click();
  await expect(page.getByTestId("pack")).toBeVisible();
  await expect(page.getByTestId("mine-label")).toHaveText("Just my class: no other teachers yet");
  await expect(page.getByTestId("pack-draft")).toBeVisible();
  for (const id of ["seeing", "why", "check", "strategies", "activity", "mistakes", "working", "home", "stuck"]) await expect(page.getByTestId(`pack-SUB-SFL-${id}`)).toBeVisible();
  const open = async (id: string) => page.getByTestId(`pack-SUB-SFL-${id}`).locator("summary").click();
  await open("seeing");
  await expect(page.getByTestId("pack-SUB-SFL-seeing")).toContainText("5 of 16 children show it.");
  await expect(page.getByTestId("pack-SUB-SFL-seeing")).toContainText("74 − 36"); // her own question
  await open("working");
  await expect(page.getByTestId("pack-SUB-SFL-working")).toContainText("Now: 5 of 16 children");
  await open("strategies");
  expect(await page.locator("[data-testid^=pack-strategy-]").count()).toBe(3);
  await expect(page.getByTestId("pack-SUB-SFL-strategies")).toContainText("Strategy library");
  await open("check");
  await expect(page.getByTestId("pack-SUB-SFL-check")).toContainText("Write a subtraction");
  const text = await page.getByTestId("pack").innerText();
  expect(text).not.toContain("%");
  expect(text).not.toContain("undefined");
  // nothing plays by itself
  expect(await page.locator("audio").count()).toBe(0);
  await page.screenshot({ path: path.join(SHOTS, "pack-phone.png") });
  // a second error has its own pack
  await page.goBack();
});

test("a Hindi page shows English content with a note, never a machine translation", async ({ page }) => {
  await enter16(page);
  await makeCohort(page);
  await chooseLanguage(page, "hi");
  await page.goto("/#/cohort");
  await expect(page.getByTestId("pack-lang-missing")).toBeVisible();
  await page.getByTestId("pack-SUB-SFL-check").locator("summary").click();
  await expect(page.getByTestId("pack-SUB-SFL-check")).toContainText("Write a subtraction"); // English, as written
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("Download audio: nothing is made until pressed, then an MP3 named for the error and language downloads", async ({ page }) => {
  await enter16(page);
  await makeCohort(page);
  await page.goto("/#/cohort");
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/audio/")) requests.push(r.url());
  });
  await expect(page.getByTestId("audio-SUB-SFL-all")).toBeVisible();
  await expect(page.getByTestId("audio-SUB-SFL-all-box")).toContainText("AI-generated voice");
  expect(requests).toEqual([]); // not pressed: no call
  const download = page.waitForEvent("download");
  await page.getByTestId("audio-SUB-SFL-all").click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("intervention-sub-sfl-en.mp3");
  const bytes = readFileSync(await file.path());
  expect(bytes.length).toBeGreaterThan(1000);
  await expect(page.getByTestId("audio-SUB-SFL-all-done")).toContainText("Downloaded intervention-sub-sfl-en.mp3");
  await expect(page.getByTestId("audio-SUB-SFL-all-done")).toContainText("KB");
  // one section
  const one = page.waitForEvent("download");
  await page.getByTestId("pack-SUB-SFL-check").locator("summary").click();
  await page.getByTestId("audio-SUB-SFL-check").click();
  expect((await one).suggestedFilename()).toBe("intervention-sub-sfl-check-en.mp3");
});

test("Download audio is switched off, with the reason, when the phone is offline", async ({ page, context }) => {
  await enter16(page);
  await makeCohort(page);
  await page.goto("/#/cohort");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.waitForFunction(async () => (await caches.keys()).length > 0);
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("audio-SUB-SFL-all")).toBeDisabled();
  await expect(page.getByTestId("audio-SUB-SFL-all-box")).toContainText("Audio needs an internet connection.");
  await expect(page.getByTestId("pack")).toBeVisible(); // the text is still there
  await context.setOffline(false);
});

test("a coach sees the cohort of one class in counts, labelled", async ({ page }) => {
  await enter16(page);
  await makeCohort(page);
  await chooseRole(page, "coach");
  await page.goto("/#/cohort");
  const box = page.getByTestId("class-only-coach");
  await expect(box).toContainText("Just my class: no other teachers yet");
  await expect(box).toContainText("1 class, 16 children checked");
  await expect(box).toContainText(`Takes the smaller digit from the larger: ${fx.class.counts["SUB-SFL"]}`);
  const text = await box.innerText();
  expect(text).not.toMatch(/[0-9a-f]{16}/); // no device id
});

test("the cohort form and the pack pass axe", async ({ page }) => {
  await enter16(page);
  await page.getByTestId("class-cohort-open").click();
  let found = (await new AxeBuilder({ page }).include("[data-testid=class-cohort-form]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
  await page.getByTestId("class-cohort-create").click();
  await expect(page.getByTestId("class-cohort-made")).toBeVisible();
  await page.goto("/#/cohort");
  await page.getByTestId("pack-SUB-SFL-strategies").locator("summary").click();
  found = (await new AxeBuilder({ page }).include("[data-testid=pack]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(",")}`)).toEqual([]);
});

test("with no cohort yet the cohort page says how to make one", async ({ page }) => {
  await page.goto("/#/cohort");
  await expect(page.getByTestId("mine-none")).toBeVisible();
  await expect(page.getByTestId("pack")).toHaveCount(0);
});
