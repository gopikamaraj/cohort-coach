import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// Paper Studio: a teacher makes a paper inside Start a check (the pilot paper, or a new one for her
// class with its key and coverage grid), sees it on Papers, and a coach reviews the queue and reads
// the rules. Papers are made by code on the server; nothing here is AI.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

async function as(page: Page, role: string) {
  await page.goto("/");
  await page.evaluate(
    ([c, r]) => {
      localStorage.clear();
      localStorage.setItem("cc.consent", c);
      localStorage.setItem("cc.role", r);
    },
    [CONSENT, role],
  );
}

async function makeNewPaper(page: Page, layout = "en") {
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await expect(page.getByTestId("paper-profile-source")).toContainText("standard paper");
  await page.getByTestId("paper-language").selectOption(layout);
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
}

test("a new paper shows its anchor and adaptive items, the coverage grid, the key and its twin", async ({ page }) => {
  test.setTimeout(90_000);
  await as(page, "teacher");
  await makeNewPaper(page);
  await expect(page.getByTestId("paper-code")).toContainText(/^PRE · .+ · T1$/);
  await expect(page.getByTestId("paper-status")).toHaveText("Approved by the rules");
  await expect(page.getByTestId("paper-anchors").locator("li")).toHaveCount(10);
  await expect(page.getByTestId("paper-adaptive").locator("li")).toHaveCount(5);
  await expect(page.getByTestId("coverage-SUB-SFL")).toBeVisible();
  await expect(page.getByTestId("paper-checks-ok")).toBeVisible();
  await expect(page.getByTestId("paper-twin-note")).toBeVisible();
  await page.getByTestId("paper-key-toggle").click();
  await expect(page.getByTestId("paper-item-3")).toContainText("ADD-NOCARRY");
  // the print button fetches a real PDF
  const pdf = page.waitForResponse((r) => r.url().includes("/paper.pdf"));
  await page.getByTestId("paper-print").click();
  expect((await pdf).headers()["content-type"]).toContain("application/pdf");
});

test("a paper can be in two languages, and the loader says what is happening", async ({ page }) => {
  test.setTimeout(90_000);
  await as(page, "teacher");
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-language").selectOption("hi");
  await page.getByTestId("paper-language-2").selectOption("en");
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-busy")).toContainText("Making the paper");
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("paper-source")).toContainText("हिन्दी (Hindi) + English");
  await expect(page.getByTestId("paper-status")).toHaveText("Waiting for a reviewer"); // the Hindi wording is not reviewed yet
  await page.getByTestId("paper-key-toggle").click();
  await expect(page.getByTestId("paper-item-6")).toContainText("no error tracked");
});

test("the intake form leaves an untaught topic off the paper", async ({ page }) => {
  test.setTimeout(90_000);
  await as(page, "teacher");
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await expect(page.getByTestId("intake-form")).toBeVisible(); // open by default: no data yet
  await page.getByTestId("intake-taught-C3").uncheck();
  await page.getByTestId("intake-struggle-C2").check();
  await page.getByTestId("intake-save").click();
  await expect(page.getByTestId("paper-profile-source")).toContainText("teacher's answers");
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-not-assessed")).toContainText("Taking away with borrowing", { timeout: 30_000 });
});

test("a paper made from the rules is attached to the check, and its code shows in the check header", async ({ page }) => {
  test.setTimeout(90_000);
  await as(page, "teacher");
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await expect(page.getByTestId("paper-choice-pilot")).toHaveCount(0); // no separate pilot paper: every paper is made from the rules
  await expect(page.getByTestId("intake-form")).toBeVisible(); // no past check: she tells us about the class first
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
  await page.goto("/#/check"); // Enter check only chooses a paper that exists
  await expect(page.getByTestId("paper-chooser")).toBeVisible();
  await expect(page.getByTestId("paper-attached")).toContainText("PRE ·");
  await page.getByTestId("check-class-name").fill("3A Class");
  await page.getByTestId("check-expected").fill("2");
  await page.getByTestId("start-check-go").click();
  await expect(page.getByTestId("check-paper-code")).toContainText("PRE ·");
  await page.getByTestId("input-1").fill("346");
  await page.goto("/#/papers");
  await expect(page.getByTestId("paper-row-A").first()).toBeVisible();
});

test("a coach sees a paper in unreviewed wording in the queue and approves it", async ({ page }) => {
  test.setTimeout(120_000);
  await as(page, "teacher");
  await makeNewPaper(page, "ta");
  await expect(page.getByTestId("paper-status")).toHaveText("Waiting for a reviewer");
  const code = (await page.getByTestId("paper-code").textContent()) ?? "";
  await page.evaluate(() => localStorage.setItem("cc.role", "coach"));
  await page.goto("/#/papers");
  await page.reload();
  const row = page.getByTestId("queue-row").filter({ hasText: code }).filter({ hasText: "Wording not yet reviewed" }).first();
  await row.getByTestId("queue-open").click();
  await expect(row.getByTestId("coverage-grid")).toBeVisible();
  await row.getByTestId("queue-approve").click();
  await expect(page.getByText("Approved.")).toBeVisible();
});

test("the coach reads the published rules and tests them", async ({ page }) => {
  test.setTimeout(90_000);
  await as(page, "coach");
  await page.goto("/#/papers");
  await expect(page.getByTestId("rules-published")).toContainText("rules version");
  await expect(page.getByTestId("rules-templates")).toContainText("sub-borrow");
  await page.locator('[data-testid^="rules-test-"]').first().click();
  await expect(page.getByTestId("rules-test-result")).toContainText("sample papers passed", { timeout: 60_000 });
});

test("a teacher reads the rules but never sees the review queue or the test button", async ({ page }) => {
  await as(page, "teacher");
  await page.goto("/#/papers");
  await expect(page.getByTestId("papers-mine")).toBeVisible();
  await expect(page.getByTestId("papers-queue")).toHaveCount(0);
  await expect(page.getByTestId("papers-rules")).toBeVisible();
  await expect(page.getByTestId("rules-templates")).toContainText("add-carry");
  await expect(page.getByTestId("rules-test-1")).toHaveCount(0);
});

test("Paper Studio screens pass axe", async ({ page }) => {
  test.setTimeout(120_000);
  await as(page, "teacher");
  await makeNewPaper(page);
  const scan = async () => (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(await scan()).toEqual([]);
  await expect(page.getByTestId("intake-form")).toBeVisible(); // open by default: no data yet
  expect(await scan()).toEqual([]);
  await page.goto("/#/papers");
  await expect(page.getByTestId("papers-mine")).toBeVisible();
  expect(await scan()).toEqual([]);
  await page.evaluate(() => localStorage.setItem("cc.role", "coach"));
  await page.goto("/#/papers");
  await page.reload();
  await expect(page.getByTestId("rules-templates")).toBeVisible();
  expect(await scan()).toEqual([]);
});

test("Papers sits between Home and Enter check, and each paper says whether cohorts formed and why not", async ({ page }) => {
  test.setTimeout(120_000);
  await as(page, "teacher");
  await makeNewPaper(page);
  await page.goto("/#/papers");
  // the order of the left navigation
  const labels = await page.locator("nav a, nav button").allInnerTexts();
  const names = labels.map((l) => l.trim());
  expect(names.indexOf("Papers")).toBeGreaterThan(names.indexOf("Home"));
  expect(names.indexOf("Papers")).toBeLessThan(names.indexOf("Enter check"));
  // a paper no check has used: the reason and the next step, as counts and words only
  const row = page.getByTestId("paper-row-A");
  await expect(row).toContainText("PRE ·"); // named by its printed code, not by a form
  await expect(row).toContainText("Made by the rules");
  await expect(page.getByTestId("paper-cohort-A")).toHaveAttribute("data-reason", "no_check");
  await expect(page.getByTestId("paper-cohort-A")).toContainText("No cohort yet");
  await expect(page.getByTestId("paper-cohort-A")).toContainText("no check has used this paper");
  await expect(page.getByTestId("paper-next-A")).toHaveText("Enter a check");
  // there is no filter by form; the post-test twin is listed on its own
  await expect(page.getByTestId("papers-filter-form")).toHaveCount(0);
  await expect(page.getByTestId("paper-row-B")).toBeVisible();
  const scan = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(scan.map((v) => v.id)).toEqual([]);
});
