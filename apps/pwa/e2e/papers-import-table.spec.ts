import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

// The import table: a row with something to check is highlighted, carries a warning icon, and the
// details are in its tooltip. The reader is replayed from a recording made for tests; no paid call.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const PDF = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "paper-to-import.pdf");

async function open(page: Page) {
  await page.goto("/");
  await page.evaluate((c) => {
    localStorage.clear();
    localStorage.setItem("cc.consent", c);
    localStorage.setItem("cc.role", "teacher");
  }, CONSENT);
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-pdf").click();
}

test("an answer key that differs highlights the row, with the details in its tooltip; clean rows stay plain", async ({ page }) => {
  test.setTimeout(120_000);
  await open(page);
  // item 3 is 38 + 47 = 85: the key file says 86, so that row needs a look; item 4 agrees
  const key = "1: 305\n3: 86\n4: 74\n";
  await page.getByTestId("import-file").setInputFiles([
    { name: "paper-to-import.pdf", mimeType: "application/pdf", buffer: (await import("node:fs")).readFileSync(PDF) },
    { name: "key.txt", mimeType: "text/plain", buffer: Buffer.from(key) },
  ]);
  await expect(page.getByTestId("import-key-1")).toContainText("Answer key · 3 answers");
  await page.getByTestId("import-read").click();
  await expect(page.getByTestId("import-review")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("import-class")).toHaveCount(0); // papers are shared: no class is asked
  await expect(page.getByTestId("import-kind")).toHaveCount(0); // the kind was chosen before the upload

  const warned = page.getByTestId("item-row-3");
  await expect(warned).toHaveAttribute("data-warn", "true");
  await expect(page.getByTestId("item-3-warn")).toBeVisible();
  await expect(page.getByTestId("item-3-warn-text")).toContainText("The answer key file says 86; the computed answer is 85.");
  await expect(page.getByTestId("item-row-4")).not.toHaveAttribute("data-warn", "true");
  await expect(page.getByTestId("item-4-warn")).toHaveCount(0);
  // the first row (dictation) took its number from the key and says so in a small caption, not a chip
  await expect(page.getByTestId("item-1-from-key")).toHaveText("From the answer key");
  await expect(page.getByTestId("item-row-1")).not.toHaveAttribute("data-warn", "true");
  // no "You changed this" tag anywhere
  await expect(page.getByText("You changed this")).toHaveCount(0);
  // the tooltip opens on focus too (keyboard and touch)
  await page.getByTestId("item-3-warn").focus();
  await expect(page.getByTestId("item-3-warn-text")).toBeVisible();
  const found = (await new AxeBuilder({ page }).include("[data-testid=import-table]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
});

test("Confirm the paper: the paper appears in the list, shared, and can be chosen in Enter check", async ({ page }) => {
  test.setTimeout(120_000);
  await open(page);
  await page.getByTestId("import-file").setInputFiles(PDF);
  await page.getByTestId("import-read").click();
  await expect(page.getByTestId("import-review")).toBeVisible({ timeout: 60_000 });
  // the reader was unsure of item 10: she confirms the numbers it shows, then the paper can be confirmed
  await page.getByTestId("ask-send").click();
  await expect(page.getByTestId("import-confirm")).toBeEnabled();
  await page.getByTestId("import-confirm").click();
  await expect(page.getByTestId("import-review")).toHaveCount(0, { timeout: 30_000 });
  await expect(page.getByTestId("paper-row-A").first()).toBeVisible({ timeout: 20_000 }); // the new paper is listed
  // opening an imported paper shows it (it once blanked the screen on a missing string)
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.getByRole("button", { name: "Open", exact: true }).first().click();
  await expect(page.locator("main")).toContainText("Brought in from a PDF or an answered sheet");
  expect(errors).toEqual([]);
  await page.goto("/#/check");
  await expect(page.getByTestId("paper-select")).toContainText("8 items · Checked");
  // a shared paper outlives the test and every browser, so delete it: other specs expect an empty class
  await page.goto("/#/papers");
  await page.getByTestId("paper-delete-A").first().click();
  await page.getByTestId("delete-yes").click();
  await expect(page.getByTestId("paper-row-A")).toHaveCount(0, { timeout: 20_000 });
});

test("the Automatic checks heading has an info icon whose tooltip lists what is checked, including the pre and post twin", async ({ page }) => {
  test.setTimeout(90_000);
  await open(page);
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("paper-checks-info").first().focus();
  const tip = page.getByTestId("paper-checks-info-text").first();
  await expect(tip).toBeVisible();
  await expect(tip).toContainText("a child cannot just remember answers");
  await expect(tip).toContainText("worked out again from the numbers");
});

test("an imported pre-test gets a post-test twin with new numbers; importing a post-test with the same numbers is warned about", async ({ page }) => {
  test.setTimeout(150_000);
  await open(page);
  await page.getByTestId("import-file").setInputFiles(PDF);
  await page.getByTestId("import-read").click();
  await expect(page.getByTestId("import-review")).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("ask-send").click();
  await page.getByTestId("import-confirm").click();
  await expect(page.getByTestId("paper-row-A").first()).toBeVisible({ timeout: 20_000 });

  await page.getByTestId("paper-twin-A").first().click();
  await expect(page.getByTestId("paper-row-B")).toHaveCount(1, { timeout: 20_000 });
  await expect(page.getByTestId("paper-twin-A")).toHaveCount(0); // it has its twin now

  // the same file again, as a post-test: its numbers repeat the pre-test's
  if (!(await page.getByTestId("create-kind").isVisible())) await page.getByTestId("papers-create").click();
  await page.getByTestId("create-kind").selectOption("post");
  await page.getByTestId("route-pdf").click();
  await page.getByTestId("import-file").setInputFiles(PDF);
  await page.getByTestId("import-read").click();
  await expect(page.getByTestId("import-review")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("import-reuses")).toContainText("repeats numbers from the pre-test");

  // clean up: deleting the pre-test takes its twin with it
  await page.goto("/#/papers");
  await page.getByTestId("paper-delete-A").first().click();
  await page.getByTestId("delete-yes").click();
  await expect(page.getByTestId("paper-row-A")).toHaveCount(0, { timeout: 20_000 });
  await expect(page.getByTestId("paper-row-B")).toHaveCount(0);
});
