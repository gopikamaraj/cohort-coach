import AxeBuilder from "@axe-core/playwright";
import { writeFileSync } from "node:fs";
import { type Page } from "@playwright/test";
import { expect, test } from "./test";

// The judge's demo flow, all 11 steps and the optional 12th, on the product's own screens and the
// real API (recorded AI answers: ai/fixtures/recorded). Every made-up thing must say Demo or
// Simulated. One judge device, one demo session; Reset clears it.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

async function fresh(page: Page, lang = "en") {
  await page.goto("/");
  await page.evaluate(
    ([c, l]) => {
      (((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")]));
      localStorage.setItem("cc.consent", c);
      localStorage.setItem("cc.role", "judge");
      localStorage.setItem("cc.lang", l);
    },
    [CONSENT, lang],
  );
}

async function axe(page: Page) {
  const found = (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

async function next(page: Page, n: number) {
  await page.getByTestId("demo-next").click();
  await expect(page.getByTestId("demo-panel-n")).toContainText(`${n} of 12`);
}

test("a judge runs all 12 demo steps, and every made-up thing is labelled", async ({ page }) => {
  test.setTimeout(600_000);
  const started = Date.now();
  await fresh(page);

  // 1. Start: a teacher, in English, with a made-up class
  await page.goto("/#/demo?step=1");
  await expect(page.getByTestId("demo-panel-n")).toHaveText("Demo step 1 of 12");
  await expect(page.getByTestId("demo-label")).toContainText("Demo: made-up class 3A");
  await axe(page);
  await page.getByTestId("demo-begin").click();

  // 2. Generate a paper: the short intake form, then the pilot paper (Form A) in Paper Studio
  await expect(page).toHaveURL(/#\/papers/);
  await expect(page.getByTestId("demo-panel-n")).toHaveText("Demo step 2 of 12");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-code")).toHaveText("PRE · 3A · T1", { timeout: 60_000 });

  // 3. Generate 20 filled demo sheets, named by class and roll number
  await next(page, 3);
  await page.getByTestId("demo-make-sheets").click();
  await expect(page.getByTestId("demo-sheet-list").locator("li")).toHaveCount(20, { timeout: 300_000 });
  await expect(page.getByTestId("demo-sheet-list")).toContainText("3A-roll07.png");
  await expect(page.getByTestId("demo-sheets-label")).toContainText("Not real children's work");
  const zip = page.waitForEvent("download");
  await page.getByTestId("demo-zip").click();
  expect((await zip).suggestedFilename()).toBe("3A-demo-sheets.zip");

  // 4. Enter the check: sheet 1 read by the AI, the rest auto-filled from the answer file.
  // The demo paper is made from the rules in step 2, so its sheets are new pictures with no recorded
  // AI read to replay here: the read is stood in for with what the sheet says (the server's read of a
  // demo sheet is tested in tests/demo).
  await page.route("**/api/demo/*/read", async (route) => {
    const sid = new URL(route.request().url()).pathname.split("/")[3];
    const reads = (await (await page.request.get(`/api/demo/${sid}/reads.json`)).json()) as { check_code: string; sheets: Record<string, { cells: { text: string; status: string }[] }> };
    const first = Object.values(reads.sheets)[0]!;
    await route.fulfill({ json: { source: "ai", label: "Read by AI", cached: false, cells: first.cells.map((c) => ({ text: c.text, status: c.status })), demo_sheet: true, roll: 1, check_code: reads.check_code, ai_reads: 1, ai_reads_cap: 6 } });
  });
  await next(page, 4);
  await page.getByTestId("demo-use-1").click();
  await expect(page.getByTestId("demo-roll-1")).toHaveAttribute("data-status", "needs_review", { timeout: 60_000 });
  await expect(page.getByTestId("demo-roll-1")).toContainText("Read by AI");
  await page.getByTestId("demo-autofill").click();
  await expect(page.getByTestId("demo-entry-msg")).toContainText("19 sheets loaded from the demo answer file, with no AI call", { timeout: 60_000 });
  await expect(page.getByTestId("demo-roll-6")).toContainText("Read from demo answer file");
  await expect(page.getByTestId("demo-roll-20")).toHaveAttribute("data-status", "needs_review");
  await axe(page);

  // 5. Review: the drawer shows the sheet beside the read; the smudged sheet is marked unsure
  await next(page, 5);
  await page.getByTestId("demo-preview-6").click();
  const drawer = page.getByTestId("demo-drawer");
  await expect(drawer).toBeVisible();
  await expect(page.getByTestId("demo-drawer-img")).toBeVisible();
  const box = await drawer.boundingBox();
  const vh = page.viewportSize()?.height ?? 851;
  expect(Math.abs((box?.height ?? 0) - 0.4 * vh)).toBeLessThan(4); // 40% of the height on a phone
  await expect(drawer.locator(".demo-cell-low")).toHaveCount(1);
  await expect(page.getByTestId("demo-drawer-close")).toBeFocused(); // keyboard: focus moves in
  await axe(page);
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await page.getByTestId("demo-preview-1").click();
  for (let i = 0; i < 20; i++) {
    if ((await drawer.count()) === 0) break;
    await page.getByTestId("demo-approve").click();
  }
  await expect(page.getByTestId("demo-entry-progress")).toContainText("20 approved, 0 to review");

  // 6. Submit the check; the error finder ran on the phone; then simulate the other classes
  await page.getByTestId("demo-finish").click();
  await expect(page).toHaveURL(/step=6/);
  await expect(page.getByTestId("demo-my-counts")).toContainText("SUB-SFL");
  // the summary counts the server's own AI reads; here the read was stood in for (see step 4)
  await expect(page.getByTestId("demo-reading-summary")).toHaveCount(0);
  await page.getByTestId("demo-simulate").click();

  // 7. Three cohorts; her class in one this term and eligible for a second next term
  await expect(page).toHaveURL(/step=7/);
  await expect(page.getByTestId("demo-cohorts").locator("li")).toHaveCount(3);
  await expect(page.getByTestId("demo-cohort-you-SUB-SFL")).toContainText("Your class is in this cohort");
  await expect(page.getByTestId("demo-cohort-you-ADD-NOCARRY")).toContainText("next term");
  for (const card of await page.getByTestId("demo-cohorts").locator("li").all()) await expect(card).toContainText("Simulated");
  await axe(page);

  // 8. The first audio lesson, with the Demo: pre-approved badge
  await next(page, 8);
  await page.getByTestId("demo-audio").click();
  await expect(page.getByTestId("demo-audio-badge")).toHaveText("Demo: pre-approved", { timeout: 120_000 });
  await expect(page.getByTestId("demo-audio-script")).not.toBeEmpty();

  // 9. Practice Class with the lesson's next step
  await next(page, 9);
  await expect(page).toHaveURL(/#\/practice/);
  await expect(page.getByTestId("practice-next")).toBeVisible();

  // 10. Cohort chat: ask, wait or skip; the answer is labelled
  await next(page, 10);
  await page.getByTestId("demo-chat-text").fill("How do I help children who take the smaller digit from the bigger one?");
  await page.getByTestId("demo-chat-ask").click();
  await expect(page.getByTestId("demo-chat-thread").locator("li")).toHaveCount(1, { timeout: 60_000 });
  if (await page.getByTestId("demo-chat-skip").count()) await page.getByTestId("demo-chat-skip").click();
  await axe(page);

  // 11. The coach's queue and the SCERT officer's dashboard (counts, cells under 5 hidden)
  await next(page, 11);
  await expect(page.getByTestId("demo-coach")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByTestId("demo-q-mentor")).toContainText("Simulated mentor");
  // the AI found no approved material, so the question waits for a person: the coach answers
  await expect(page.getByTestId("demo-q-no-draft")).toBeVisible();
  await page.getByTestId("demo-q-own").fill("Let the child make the top number with bundles and open one bundle when the ones are too few.");
  await page.getByTestId("demo-q-own-send").click();
  await expect(page.getByTestId("demo-q-no-draft")).toHaveCount(0);
  await page.getByTestId("demo-mentor-approve").click();
  await expect(page.getByTestId("demo-mentor-status")).toHaveText("Approved");
  await axe(page);
  await page.getByTestId("demo-tab-officer").click();
  await expect(page.getByTestId("demo-dashboard")).toContainText("simulated");
  await expect(page.getByTestId("demo-dash-cohorts")).toContainText("Hidden (under 5)");
  await expect(page.getByTestId("demo-dashboard")).not.toContainText("Teacher");
  await axe(page);

  // 12. Optional: the post-test, before and after
  await next(page, 12);
  await page.getByTestId("demo-post").click();
  await expect(page.getByTestId("before-after")).toBeVisible();
  await expect(page.getByTestId("ba-demo")).toBeVisible();

  // The run's time, for docs/evidence/demo_synthetic_reading.md (scripts/demo_evidence.py reads it)
  writeFileSync("test-results/demo-run.json", JSON.stringify({ seconds: Math.round((Date.now() - started) / 1000), at: new Date().toISOString(), steps: 12 }));

  // Reset clears this demo and starts again
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("demo-reset").click();
  await expect(page).toHaveURL(/step=1/);
  await expect(page.getByTestId("demo-panel-n")).toHaveText("Demo step 1 of 12");
});

test("the review drawer is a bottom drawer 40% of the width on a desktop", async ({ page }) => {
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 1280, height: 900 });
  await fresh(page);
  await page.goto("/#/demo?step=1");
  await page.getByTestId("demo-begin").click();
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-code")).toBeVisible({ timeout: 60_000 });
  await page.goto("/#/demo?step=3");
  await page.getByTestId("demo-make-sheets").click();
  await expect(page.getByTestId("demo-sheet-list").locator("li")).toHaveCount(20, { timeout: 300_000 });
  await page.goto("/#/demo?step=4");
  await page.getByTestId("demo-autofill").click();
  await expect(page.getByTestId("demo-roll-2")).toHaveAttribute("data-status", "needs_review", { timeout: 60_000 });
  await page.getByTestId("demo-preview-2").click();
  const box = await page.getByTestId("demo-drawer").boundingBox();
  expect(Math.abs((box?.width ?? 0) - 0.4 * 1280)).toBeLessThan(4);
  expect(Math.round((box?.x ?? 0) + (box?.width ?? 0))).toBe(1280); // anchored bottom right
});

test("the main demo screens are in Hindi when Hindi is chosen", async ({ page }) => {
  await fresh(page, "hi");
  await page.goto("/#/demo?step=1");
  await expect(page.getByTestId("demo-panel-n")).toHaveText("डेमो चरण 1 / 12");
  await expect(page.getByTestId("demo-label")).toContainText("डेमो");
  await expect(page.getByTestId("demo-begin")).toHaveText("शिक्षक के रूप में शुरू करें");
  await page.goto("/#/demo?step=4");
  await expect(page.getByTestId("demo-entry")).toContainText("रोल नंबर");
  await axe(page);
});

test("two judge devices never see each other's demo", async ({ browser }) => {
  const a = await browser.newContext();
  const b = await browser.newContext();
  const pa = await a.newPage();
  const pb = await b.newPage();
  await fresh(pa);
  await fresh(pb);
  await pa.goto("/#/demo?step=1");
  await pb.goto("/#/demo?step=1");
  await expect(pa.getByTestId("demo-label")).toBeVisible();
  await expect(pb.getByTestId("demo-label")).toBeVisible();
  const sa = await pa.evaluate(() => localStorage.getItem("cc.demo.session"));
  const sb = await pb.evaluate(() => localStorage.getItem("cc.demo.session"));
  expect(sa).not.toBe(sb);
  // each device has its own session on the server, and a new one starts empty
  const api = "http://localhost:8011/api/demo/session/";
  const ja = await (await pa.request.get(api + sa)).json();
  const jb = await (await pb.request.get(api + sb)).json();
  expect(ja.session).toBe(sa);
  expect(jb.session).toBe(sb);
  expect(jb.paper_id).toBeNull();
  expect(jb.ai_reads).toBe(0);
  await a.close();
  await b.close();
});
