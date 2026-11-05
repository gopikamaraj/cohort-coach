import AxeBuilder from "@axe-core/playwright";
import { type Page } from "@playwright/test";
import { expect, test } from "./test";
import path from "node:path";
import { fileURLToPath } from "node:url";

// The Papers page: a teacher imports a paper from a PDF (the reader is replayed from a recording
// made for tests), the assistant panel asks what is missing one question at a time, a person
// confirms, and the paper then appears on the list as imported and awaiting review, is never
// printed, and can be chosen in Enter check. No paid API is called.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const PDF = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "paper-to-import.pdf");

async function as(page: Page, role: string) {
  await page.goto("/");
  await page.evaluate(
    ([c, r]) => {
      (((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")]));
      localStorage.setItem("cc.consent", c);
      localStorage.setItem("cc.role", r);
    },
    [CONSENT, role],
  );
}

async function scan(page: Page) {
  const found = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

async function upload(page: Page) {
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-pdf").click();
  await expect(page.getByTestId("import-note")).toContainText("Handwriting and names are ignored and not kept");
  await page.getByTestId("import-file").setInputFiles(PDF);
  await expect(page.getByTestId("import-review")).toBeVisible({ timeout: 60_000 });
}

test("a paper is read from a PDF, the assistant asks what is missing, and a person confirms it", async ({ page }) => {
  test.setTimeout(180_000);
  await as(page, "teacher");
  await upload(page);

  // code computed every key; the AI never gave one
  await expect(page.getByTestId("item-3-key")).toHaveText("85");
  await expect(page.getByTestId("item-7-key")).toHaveText("38");
  await expect(page.getByTestId("item-1-key")).toHaveText("-"); // a dictated number is told, never guessed
  await expect(page.getByTestId("item-row-10")).toContainText("The reader was unsure");
  await expect(page.getByTestId("item-row-11")).toContainText("Not supported yet");
  await expect(page.getByTestId("item-11-include")).toBeDisabled();
  await expect(page.getByTestId("import-page")).toBeVisible();
  await expect(page.getByTestId("coverage-warn-PV-HEARD")).toBeVisible(); // the dictated items probe nothing yet
  await scan(page);

  // Confirm is off while questions that block it are open
  await expect(page.getByTestId("import-confirm")).toBeDisabled();
  await expect(page.getByTestId("import-blocked")).toContainText("open question");

  // the assistant asks one at a time; its answers are tagged and undoable
  await expect(page.getByTestId("ask-kind")).toBeVisible();
  await page.getByTestId("ask-opt-pre").click();
  await expect(page.getByTestId("changed-kind")).toContainText("Assistant changed this");
  await page.getByTestId("import-undo").click();
  await expect(page.getByTestId("ask-kind")).toBeVisible(); // undone: asked again
  await page.getByTestId("ask-opt-pre").click();
  await expect(page.getByTestId("ask-form")).toHaveCount(0); // no form letter is asked: it follows from the kind
  await expect(page.getByTestId("ask-unsure-10")).toBeVisible();
  await page.getByTestId("ask-a").fill("81");
  await page.getByTestId("ask-b").fill("27");
  await page.getByTestId("ask-send").click();
  await expect(page.getByTestId("item-10-key")).toHaveText("54");

  // nothing blocks now: Confirm is on, and the assistant has only optional questions left
  await expect(page.getByTestId("import-confirm")).toBeEnabled();
  await page.getByTestId("ask-text").fill("346");
  await page.getByTestId("ask-send").click();
  await expect(page.getByTestId("item-1-key")).toHaveText("346");
  await page.getByTestId("ask-text").fill("728");
  await page.getByTestId("ask-send").click();
  await expect(page.getByTestId("item-2-key")).toHaveText("728");
  await page.getByTestId("ask-opt-leave_out").click();
  await scan(page);

  await page.getByTestId("import-confirm").click();
  await expect(page.getByTestId("import-review")).toHaveCount(0);

  // it is on the list: imported, awaiting review, not printed, with cohort status and details
  const row = page.getByTestId("paper-row-A");
  await expect(row).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("paper-source-A")).toHaveText("Imported, awaiting review");
  await expect(page.getByTestId("paper-cohort-A")).toHaveAttribute("data-reason", "no_check");
  await page.getByTestId("paper-details-A").click();
  await expect(page.getByTestId("paper-detail")).toBeVisible();
  await page.getByTestId("tab-questions").click();
  await expect(page.getByTestId("tab-panel-questions")).toContainText("Item 3: 38 + 47 = 85");
  await page.getByTestId("tab-files").click();
  await expect(page.getByTestId("tab-panel-files")).toContainText("already printed");
  await scan(page);

  // Enter check only chooses: the imported paper is on offer
  await page.goto("/#/check");
  await expect(page.getByTestId("paper-chooser")).toBeVisible();
  await expect(page.getByTestId("paper-details")).toHaveCount(0); // papers are no longer made here
  await expect(page.getByTestId("paper-chooser")).toContainText("Imported, awaiting review");
});

test("the upload can be discarded", async ({ page }) => {
  test.setTimeout(120_000);
  await as(page, "teacher");
  await upload(page);
  await page.getByTestId("import-abandon").click();
  await expect(page.getByTestId("import-upload")).toBeVisible();
});

test("Enter check offers the paper to choose, or a link to create one", async ({ page }) => {
  await as(page, "teacher");
  await page.goto("/#/check");
  await expect(page.getByTestId("paper-chooser")).toBeVisible();
  await expect(page.getByTestId("chooser-none")).toBeVisible();
  await page.getByTestId("chooser-create").click();
  await expect(page).toHaveURL(/#\/papers/);
});

async function importAndConfirm(page: Page) {
  await upload(page);
  await page.getByTestId("ask-opt-pre").click();
  await page.getByTestId("ask-a").fill("81");
  await page.getByTestId("ask-b").fill("27");
  await page.getByTestId("ask-send").click();
  await expect(page.getByTestId("import-confirm")).toBeEnabled();
  await page.getByTestId("import-confirm").click();
  await expect(page.getByTestId("paper-row-A")).toBeVisible({ timeout: 30_000 });
}

test("an imported paper can be edited in place, and deleted after a confirmation", async ({ page }) => {
  test.setTimeout(180_000);
  await as(page, "teacher");
  await importAndConfirm(page);

  // edit: change a number, save, and the answer is worked out again by code
  await page.getByTestId("paper-edit-A").click();
  await expect(page.getByTestId("tab-panel-questions")).toContainText("Item 1: 38 + 47 = 85"); // the dictated items were left out, so the first sum is item 1
  await expect(page.getByTestId("tab-panel-questions")).toContainText("goes back to review");
  await page.getByTestId("edit-q-1").fill("38 + 48");
  await page.getByTestId("edit-save").click();
  await expect(page.getByTestId("detail-msg")).toContainText("Every answer was worked out again");
  await expect(page.getByTestId("tab-panel-questions")).toContainText("Item 1: 38 + 48 = 86");
  await expect(page.getByTestId("paper-source-A")).toHaveText("Imported, awaiting review");

  // delete: nothing happens until she confirms, and "keep it" keeps the paper
  await page.getByTestId("paper-delete-A").click();
  await expect(page.getByTestId("delete-confirm")).toBeVisible();
  await expect(page.getByTestId("delete-confirm")).toContainText("This cannot be undone");
  await page.getByTestId("delete-no").click();
  await expect(page.getByTestId("paper-row-A")).toBeVisible();
  await page.getByTestId("paper-delete-A").click();
  await page.getByTestId("delete-yes").click();
  await expect(page.getByTestId("paper-row-A")).toHaveCount(0);
});

async function makeGenerated(page: Page) {
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
}

test("a generated paper is edited in the same paper, with no copy, and goes back to review", async ({ page }) => {
  test.setTimeout(120_000);
  await as(page, "teacher");
  await makeGenerated(page);
  const rows = await page.getByTestId("paper-row-A").count();
  await page.getByTestId("paper-edit-A").first().click();
  await expect(page.getByTestId("tab-panel-questions")).toContainText("Changes are saved in this paper");
  await expect(page.getByTestId("detail-edit")).toHaveCount(0); // the row's Edit and Delete are the only ones
  await expect(page.getByTestId("detail-delete")).toHaveCount(0);
  const q = page.getByTestId("edit-q-3");
  const [a, b] = (await q.inputValue()).split("+").map((x) => Number(x));
  await q.fill("5 + 4"); // a number that does not fit the rule: the server says so and Save stays off
  await expect(page.getByTestId("edit-note-3")).toContainText("Does not fit the rule");
  await expect(page.getByTestId("edit-save")).toBeDisabled();
  await q.fill(`${a} - ${b}`); // the sign of an item cannot change
  await expect(page.getByTestId("edit-note-3")).toContainText("The sign stays +");
  await page.getByTestId("edit-q-3").fill(`${a! + b! + 10 <= 99 ? a! + 10 : a! - 10} + ${b}`);
  await expect(page.getByTestId("edit-note-3")).toContainText("Fits the rule");
  await expect(page.getByTestId("edit-save")).toBeEnabled();
  await page.getByTestId("edit-save").click();
  await expect(page.getByTestId("detail-msg")).toBeVisible();
  await expect(page.getByTestId("paper-row-A")).toHaveCount(rows); // no copy was made
  await expect(page.getByTestId("paper-row-A").first()).toContainText("Waiting for a reviewer");
  await page.getByTestId("paper-edit-A").first().click();
  await page.getByTestId("edit-close").click(); // closes the editor without saving
  await expect(page.getByTestId("paper-detail")).toHaveCount(0);
});

test("papers are shared and the assignment interface is off: no Assign button and no Assigned to you panel", async ({ page }) => {
  // Replaces "an assigned paper cannot be deleted, and says why" (DECISIONS 2026-11-04, correction 2): assignment is
  // hidden behind a flag that is off (VITE_ASSIGNMENT_ENABLED), so this screen cannot assign. The rule that an
  // assigned paper cannot be deleted stays in tests/papers_hub/test_api.py, which runs with the flag on.
  test.setTimeout(120_000);
  await as(page, "teacher");
  await makeGenerated(page);
  await expect(page.getByTestId("paper-row-A").first()).toBeVisible(); // the paper is listed for everyone
  await expect(page.locator("[data-testid^=paper-assign-]")).toHaveCount(0);
  await expect(page.getByTestId("assign-go")).toHaveCount(0);
  await expect(page.getByText("Assigned to you")).toHaveCount(0);
  const scan = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(scan.map((v) => v.id)).toEqual([]);
});

test("each question says why it is on a generated paper, in plain words", async ({ page }) => {
  test.setTimeout(120_000);
  await as(page, "teacher");
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
  // in the paper view
  await page.getByTestId("why-1").first().locator("summary").click();
  await expect(page.getByTestId("why-1").first()).toContainText("rule template dictate-3d (Write a 3-digit number said aloud)");
  await expect(page.getByTestId("why-1").first()).toContainText("An anchor item");
  // in the detail, with the rules version
  await page.getByTestId("paper-details-A").first().click();
  await expect(page.getByTestId("rules-line")).toContainText("paper rules version");
  await page.getByTestId("tab-questions").click();
  await page.getByTestId("tab-panel-questions").getByTestId("why-3").locator("summary").click();
  await expect(page.getByTestId("tab-panel-questions").getByTestId("why-3")).toContainText("A wrong answer here points to");
  await expect(page.getByTestId("tab-panel-questions").getByTestId("why-12")).toContainText("An extra item");
  const text = await page.getByTestId("tab-panel-questions").innerText();
  expect(text).not.toMatch(/%/); // counts, never percentages
  const scan = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(scan.map((v) => v.id)).toEqual([]);
});
