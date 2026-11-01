import { expect, test } from "@playwright/test";
import { startSample } from "./sample";
import { PDF, axe, fresh, shot } from "./qa";

// The demo path with the AI OFF (a second API with AI_MODE=off on port 8012, served to the preview
// on 4174: every AI call fails as if the service were unreachable). Each AI widget must say so, keep
// the user's work and offer the non-AI path; nothing crashes and nothing pretends. What a user can
// still do is listed in docs/build/reports/QA-DEMO.md.

test.use({ baseURL: "http://localhost:4174", actionTimeout: 30_000 });

test("with the AI off, every AI widget says so and the demo still runs on its non-AI paths", async ({ page }) => {
  test.setTimeout(900_000);
  const shotOff = (name: string) => shot(page, "off", name);
  await fresh(page);

  // The header says the AI is off
  await page.goto("/#/demo?step=1");
  await expect(page.getByTestId("ai-mode-badge")).toHaveText("AI: off");
  await page.getByTestId("demo-begin").click();

  // Papers: Generate from rules needs no AI; import from a PDF says it is off and is disabled
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-code")).toHaveText("PRE · 3A · T1", { timeout: 60_000 });
  await page.reload(); // Create a paper is still open from the first paper: start the page afresh
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-pdf").click();
  await expect(page.getByTestId("import-ai-off")).toContainText("Generate from rules still works");
  await expect(page.getByTestId("import-file")).toBeDisabled();
  await page.getByTestId("import-file").setInputFiles(PDF, { force: true }).catch(() => undefined);
  await expect(page.getByTestId("import-review")).toHaveCount(0);
  await axe(page, "off import");
  await shotOff("01-import-off");

  // Demo sheets, then entry: the AI read is off with a reason; Auto-fill still works
  await page.goto("/#/demo?step=3");
  await page.getByTestId("demo-make-sheets").click();
  await expect(page.getByTestId("demo-sheet-list").locator("li")).toHaveCount(20, { timeout: 300_000 });
  await page.goto("/#/demo?step=4");
  await expect(page.getByTestId("demo-ai-off")).toContainText("Auto-fill");
  await expect(page.getByTestId("demo-use-1")).toBeDisabled();
  await page.getByTestId("demo-autofill").click();
  await expect(page.getByTestId("demo-entry-msg")).toContainText("20 sheets loaded from the demo answer file", { timeout: 60_000 });
  await page.getByTestId("demo-preview-1").click();
  await expect(page.getByTestId("demo-reread")).toBeDisabled();
  await expect(page.getByTestId("demo-reread-off")).toContainText("Type the answers");
  await page.getByTestId("demo-cell-1").fill("346"); // typing still works in the drawer
  await axe(page, "off drawer");
  await shotOff("02-entry-off");
  for (let i = 0; i < 20 && (await page.getByTestId("demo-drawer").count()) > 0; i++) await page.getByTestId("demo-approve").click();
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("demo-finish").click();
  await expect(page).toHaveURL(/step=6/);
  await page.getByTestId("demo-simulate").click();
  await expect(page.getByTestId("demo-cohorts").locator("li")).toHaveCount(3);

  // Lesson 1: the approved template and the script as text, and a note saying why
  await page.goto("/#/demo?step=8");
  await expect(page.getByTestId("demo-audio-ai-off")).toBeVisible();
  await page.getByTestId("demo-audio").click();
  await expect(page.getByTestId("demo-audio-card")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByTestId("demo-audio-script")).not.toBeEmpty();
  expect.soft(await page.getByTestId("demo-audio-recorded").count(), "no Recorded AI answer label when the AI is off").toBe(0);
  await shotOff("03-lesson-off");

  // Practice Class: a note, set lines, and the screen keeps working
  await page.goto("/#/practice");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("practice-ai-off")).toContainText("not recognised");
  await page.getByTestId("say").fill("Priya, what is 52 minus 29?");
  await page.getByTestId("send").click();
  await expect(page.getByTestId("reply-1")).toBeVisible({ timeout: 60_000 });
  await axe(page, "off practice");
  await shotOff("04-practice-off");

  // Chat: the question waits for a person; nothing pretends to be an AI answer
  await page.goto("/#/demo?step=10");
  await expect(page.getByTestId("demo-chat-ai-off")).toBeVisible();
  await page.getByTestId("demo-chat-text").fill("How do I help children who take the smaller digit from the bigger one?");
  await page.getByTestId("demo-chat-ask").click();
  await expect(page.getByTestId("demo-chat-thread").locator("li")).toHaveCount(1, { timeout: 60_000 });
  if (await page.getByTestId("demo-chat-skip").count()) await page.getByTestId("demo-chat-skip").click();
  await expect(page.getByTestId("demo-chat-waiting")).toBeVisible({ timeout: 60_000 });
  await shotOff("05-chat-off");

  // Coach: no AI draft, the coach answers in her own words; the officer dashboard needs no AI
  await page.goto("/#/demo?step=11");
  await expect(page.getByTestId("demo-coach")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByTestId("demo-q-no-draft")).toBeVisible();
  await page.getByTestId("demo-tab-officer").click();
  await expect(page.getByTestId("demo-dashboard")).toContainText("simulated");
  await shotOff("06-coach-officer-off");

  // Enter check: the photo read is off with a reason; typing works
  await startSample(page, { size: 2 });
  await expect(page.getByTestId("add-blocked")).toContainText("off right now");
  await expect(page.getByTestId("photo-input")).toBeDisabled();
  await expect(page.getByTestId("folder-input")).toBeDisabled();
  await page.getByTestId("input-1").fill("346"); // typing works
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await shotOff("07-check-off");

  // The assistant answers from the repository documents with no AI
  await page.goto("/#/assistant");
  await expect(page.locator("main")).toBeVisible();
  await axe(page, "off assistant");
  await shotOff("08-assistant-off");
});
