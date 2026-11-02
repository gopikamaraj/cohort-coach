import { expect, test } from "@playwright/test";
import { enterJudgeSample, finishEntering } from "./sample";

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => {
    localStorage.clear();
    localStorage.setItem("cc.consent", c);
  }, CONSENT);
});

test("a made-up class is entered and approved, and the error card says where it most likely went wrong", async ({ page }) => {
  await enterJudgeSample(page);
  await page.getByTestId("child-select").selectOption("0");
  await page.getByTestId("missed-subtraction").check();
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("approve").click(); // the tag changed the roll: it is approved again
  await finishEntering(page);
  await expect(page).toHaveURL(/#\/cards/);
  await page.getByTestId("tab-unknown").click(); // the stages and what else was seen sit on the Unknown mistakes tab
  const stages = page.getByTestId("stage-lines");
  await expect(stages).toBeVisible();
  await expect(stages).toContainText("most likely");
  await expect(page.getByTestId("stage-Core")).toContainText("children:");
  await expect(page.getByTestId("probe-Core")).toContainText("One-minute check");
  await expect(page.getByTestId("stage-Output")).toBeVisible();
  await expect(page.getByTestId("stage-Input (test)")).toBeVisible();
  await expect(page.getByTestId("stage-missed-subtraction")).toContainText("1 children missed the teaching on subtraction with borrowing");
  // every finding is in the one list: mistakes, the stages and what else was seen
  const findings = page.getByTestId("findings");
  await expect(findings.getByTestId("stage-Core")).toBeVisible();
  await expect(findings.getByTestId("stage-missed-subtraction")).toBeVisible();
  await page.getByTestId("tab-known").click();
  await expect(page.getByTestId("mistakes-table").locator("[data-kind=error]").first()).toBeVisible();
  await expect(findings).toContainText("most likely");
  await expect(findings).not.toContainText("%"); // counts, never percentages
  await expect(stages).not.toContainText("%");
});

test("answers go only to the device store (decided 2026-11-02) and the stage lines still show", async ({ page }) => {
  const sent: { method: string; url: string }[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" || r.method() === "PUT") sent.push({ method: r.method(), url: r.url() });
  });
  await enterJudgeSample(page);
  await finishEntering(page);
  await expect(page).toHaveURL(/#\/cards/);
  await expect(page.getByTestId("stage-lines")).toBeVisible();
  expect(sent.filter((r) => r.url.includes("/api/stages"))).toHaveLength(0);
  // the entered check is written to the cloud copy of this phone, and nowhere else but the class counts and the paper
  const allowed = (u: string) => /\/api\/store\/(classes|checks|profiles|settings)\//.test(u) || /\/api\/classes\/c-[0-9a-f]+\/profile$/.test(u) || u.includes("/api/papers/");
  expect(sent.filter((r) => !allowed(r.url))).toEqual([]);
});

test("the stage lines are in her language", async ({ page }) => {
  await page.evaluate(() => localStorage.setItem("cc.lang", "hi"));
  await page.reload();
  await enterJudgeSample(page);
  await finishEntering(page);
  await expect(page.getByTestId("stage-lines")).toContainText("सबसे संभावित");
  await expect(page.getByTestId("probe-Core")).toContainText("एक मिनट की जाँच");
});
