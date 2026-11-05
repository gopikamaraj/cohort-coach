import { type Page } from "@playwright/test";
import { expect, test } from "./test";
import { DESKTOP, PDF, PHONE, fresh, screen } from "./qa";

test.use({ actionTimeout: 30_000 });

// The full demo script in RECORDED mode (AI_MODE=recorded: every AI answer is replayed from
// ai/fixtures/recorded, nothing is paid for), on a phone and on a desktop, checking each step's
// widgets and labels against docs/build/qa/WIDGETS.md and the requirements in
// docs/build/reports/QA-DEMO.md. Every screen also gets axe, a layout check, a raw-text check, a
// tap-target check and a screenshot (docs/build/qa/screens/). Synthetic data only.

const CHAT_Q = "How do I help children who take the smaller digit from the bigger one?";

async function nextStep(page: Page, n: number) {
  await page.getByTestId("demo-next").click();
  await expect.soft(page.getByTestId("demo-panel-n")).toContainText(n <= 12 ? `${n} of 12` : "Optional");
}

for (const [vp, size] of [["phone", PHONE], ["desktop", DESKTOP]] as const) {
  test.describe(`demo path, recorded AI answers, ${vp}`, () => {
    test.use({ viewport: size, isMobile: vp === "phone", hasTouch: vp === "phone" });

    test(`every demo step, widget and label (${vp})`, async ({ page }) => {
      test.setTimeout(900_000);
      await fresh(page);

      // 1. Start: the judge, the demo bar, the AI mode badge, the connection pill, the assistant
      await page.goto("/#/roles");
      await expect(page.getByTestId("ai-mode-badge")).toHaveText("AI: recorded answers");
      await expect(page.getByTestId("status")).toBeVisible();
      await expect(page.getByTestId("lang")).toBeVisible();
      await screen(page, vp, "00-landing");
      await page.goto("/#/demo?step=1");
      await expect.soft(page.getByTestId("demo-panel-n")).toHaveText("Demo step 1 of 12");
      await expect(page.getByTestId("demo-label")).toContainText("Demo: made-up class 3A");
      await expect(page.getByRole("button", { name: /assistant/i }).first()).toBeVisible();
      await screen(page, vp, "01-start");
      await page.getByTestId("demo-begin").click();

      // 2. Home as the teacher: navigation order, Assigned to you, the class summary
      await expect(page).toHaveURL(/#\/papers/);
      await page.goto("/#/home");
      const order = await page.locator(".navbar a").evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).hash));
      expect.soft(order.slice(0, 6), "navigation order").toEqual(["#/home", "#/papers", "#/check", "#/cards", "#/practice", "#/programme"]);
      expect.soft(await page.getByTestId("assigned-home").count(), "Assigned to you card on Home").toBe(1);
      await expect(page.getByTestId("home-status")).toBeVisible();
      await screen(page, vp, "02-home");

      // 3. Papers: create a pre-test from the rules
      await page.goto("/#/papers");
      await expect(page.getByTestId("papers-mine")).toBeVisible();
      await screen(page, vp, "03-papers-list");
      await page.getByTestId("papers-create").click();
      await expect(page.getByTestId("route-rules")).toBeVisible();
      await expect(page.getByTestId("route-pdf")).toBeVisible();
      await page.getByTestId("route-rules").click();
      await expect(page.getByTestId("paper-maker")).toBeVisible();
      await screen(page, vp, "03-papers-create");
      await page.getByTestId("paper-make").click();
      await expect(page.getByTestId("paper-code")).toHaveText("PRE · 3A", { timeout: 60_000 }); // terms are off: the code has no term (was "PRE · 3A · T1")
      await expect(page.getByTestId("paper-twin-note")).toBeVisible();
      await screen(page, vp, "03-paper-made");

      // 4. Files and demo sheets
      await page.goto("/#/demo?step=3");
      await page.getByTestId("demo-make-sheets").click();
      await expect(page.getByTestId("demo-sheet-list").locator("li")).toHaveCount(20, { timeout: 300_000 });
      await expect(page.getByTestId("demo-sheet-list")).toContainText("3A-roll07.png");
      await expect(page.getByTestId("demo-sheets-label")).toContainText("Not real children's work");
      await expect(page.getByTestId("demo-reads")).toBeVisible();
      await screen(page, vp, "04-demo-sheets");

      // 5. Import from a PDF, with a recorded read (authored for tests: see the fixture's note)
      await page.goto("/#/papers");
      await page.getByTestId("papers-create").click();
      await page.getByTestId("route-pdf").click();
      await expect(page.getByTestId("import-note")).toBeVisible();
      await page.getByTestId("import-file").setInputFiles(PDF);
      await expect(page.getByTestId("import-review")).toBeVisible({ timeout: 60_000 });
      await expect(page.getByTestId("import-recorded")).toHaveText("Recorded AI answer");
      await expect(page.getByTestId("import-table")).toBeVisible();
      await expect(page.getByTestId("import-coverage")).toBeVisible();
      await screen(page, vp, "05-import-review");
      await page.getByTestId("import-abandon").click();

      // 6. Enter the check (demo step 4): sheet 1 by the AI, the rest from the answer file
      await page.goto("/#/demo?step=4");
      await expect.soft(page.getByTestId("demo-panel-n")).toHaveText("Demo step 4 of 12");
      await expect(page.getByTestId("demo-entry")).toBeVisible();
      await expect.soft(page.getByTestId("demo-roll-1")).toContainText("Roll no 1");
      await page.getByTestId("demo-use-1").click();
      // A new demo sheet has no recording to replay (its paper fingerprint is new): it says so.
      await expect(page.getByTestId("demo-entry-msg")).toBeVisible({ timeout: 60_000 });
      await expect.soft(page.getByTestId("demo-entry-msg")).toContainText("no recorded AI read");
      await page.getByTestId("demo-autofill").click();
      await expect(page.getByTestId("demo-entry-msg")).toContainText("loaded from the demo answer file", { timeout: 60_000 });
      await expect(page.getByTestId("demo-roll-6")).toContainText("Read from demo answer file");
      expect.soft(await page.getByTestId("demo-next-empty").count(), "Next not entered").toBe(1);
      await screen(page, vp, "06-entry");

      // 7. Review drawer: 40% of the height on a phone, 40% of the width bottom right on a desktop
      await page.getByTestId("demo-preview-6").click();
      const drawer = page.getByTestId("demo-drawer");
      await expect(drawer).toBeVisible();
      await expect(page.getByTestId("demo-drawer-img")).toBeVisible();
      const box = (await drawer.boundingBox())!;
      if (vp === "phone") expect.soft(Math.abs(box.height - 0.4 * size.height), "drawer 40% of the height").toBeLessThan(4);
      else {
        expect.soft(Math.abs(box.width - 0.4 * size.width), "drawer 40% of the width").toBeLessThan(4);
        expect.soft(Math.round(box.x + box.width), "drawer anchored right").toBe(size.width);
      }
      for (const id of ["demo-approve", "demo-next-unreviewed", "demo-absent", "demo-reread"]) await expect(page.getByTestId(id)).toBeVisible();
      await expect(drawer.locator(".demo-cell-low")).toHaveCount(1);
      await expect(page.getByTestId("demo-drawer-close")).toBeFocused();
      await screen(page, vp, "07-drawer");
      await page.keyboard.press("Escape");
      await expect(drawer).toHaveCount(0);
      await page.getByTestId("demo-preview-1").click();
      for (let i = 0; i < 20 && (await drawer.count()) > 0; i++) await page.getByTestId("demo-approve").click();
      await expect(page.getByTestId("demo-entry-progress")).toContainText("20 approved, 0 to review");

      // 8. Submit and the class card
      page.once("dialog", (d) => void d.accept());
      await page.getByTestId("demo-finish").click();
      await expect(page).toHaveURL(/step=6/);
      await expect(page.getByTestId("demo-my-counts")).toContainText("SUB-SFL");
      await screen(page, vp, "08-submitted");
      await page.goto("/#/cards");
      await expect(page.locator("body")).toContainText(/children/);
      await screen(page, vp, "08-class-card");

      // 9. The other classes: three cohorts, her class in two (one this term, one next term)
      await page.goto("/#/demo?step=6");
      await page.getByTestId("demo-simulate").click();
      await expect(page).toHaveURL(/step=7/);
      await expect(page.getByTestId("demo-cohorts").locator("li")).toHaveCount(3);
      for (const card of await page.getByTestId("demo-cohorts").locator("li").all()) await expect(card).toContainText("Simulated");
      expect.soft(await page.getByTestId("demo-in-two").count(), "her class shown in 2 of 3 cohorts").toBe(1);
      await screen(page, vp, "09-cohorts");

      // 10. First audio lesson
      await nextStep(page, 8);
      await page.getByTestId("demo-audio").click();
      await expect(page.getByTestId("demo-audio-badge")).toHaveText("Demo: pre-approved", { timeout: 120_000 });
      await expect(page.getByTestId("demo-audio-script")).not.toBeEmpty();
      if (await page.getByTestId("demo-audio-player").count()) await expect(page.getByTestId("demo-audio-download")).toBeVisible();
      await screen(page, vp, "10-lesson");

      // 12. Practice Class: five children, text always shown, masking of her input
      await nextStep(page, 9);
      await expect(page).toHaveURL(/#\/practice/);
      await expect(page.getByTestId("practice-next")).toBeVisible();
      await screen(page, vp, "12-practice-intro");
      await page.getByTestId("start-practice").click();
      await expect(page.getByTestId("kid-4")).toBeVisible();
      await page.getByTestId("say").fill("Rahul, what is 52 minus 29?");
      await page.getByTestId("send").click();
      await expect(page.getByTestId("reply-1")).toBeVisible({ timeout: 60_000 });
      await page.getByTestId("side-judge").click();
      const input = page.getByTestId("layers-panel");
      if (await input.count()) expect.soft(await input.innerText(), "a real name never reaches the AI").not.toContain("Rahul");
      expect.soft(await page.locator("body").innerText(), "no Bayesian claim").not.toMatch(/bayes|belief model/i);
      await screen(page, vp, "12-practice-turn");

      // 13. Cohort chat
      await page.goto("/#/demo?step=10");
      await page.getByTestId("demo-chat-text").fill(CHAT_Q);
      await page.getByTestId("demo-chat-ask").click();
      await expect(page.getByTestId("demo-chat-thread").locator("li")).toHaveCount(1, { timeout: 60_000 });
      await screen(page, vp, "13-chat");
      if (await page.getByTestId("demo-chat-skip").count()) await page.getByTestId("demo-chat-skip").click();

      // 14 and 15. The coach's queue and the SCERT officer's dashboard
      await page.goto("/#/demo?step=11");
      await expect(page.getByTestId("demo-coach")).toBeVisible({ timeout: 120_000 });
      await expect(page.getByTestId("demo-mentor-planned")).toContainText("planned");
      await expect(page.getByTestId("demo-mentor-status")).toHaveText("Awaiting coach");
      await screen(page, vp, "14-coach");
      await page.getByTestId("demo-tab-officer").click();
      await expect(page.getByTestId("demo-dashboard")).toContainText("simulated");
      await expect(page.getByTestId("demo-dash-cohorts")).toContainText("Hidden (under 5)");
      await screen(page, vp, "15-officer");

      // 16. Optional post-test: anchors only, with the small-sample note
      await page.goto("/#/demo?step=12");
      await page.getByTestId("demo-post").click();
      await expect(page.getByTestId("before-after")).toBeVisible();
      await expect(page.getByTestId("ba-demo")).toBeVisible();
      await screen(page, vp, "16-post-test");

      // Optional step 13: two classes to a cohort (walked in full by e2e/two-classes.spec.ts)
      await page.goto("/#/demo?step=12");
      await nextStep(page, 13);
      await expect(page).toHaveURL(/#\/two-classes/);
      await expect.soft(page.getByTestId("demo-panel")).toBeVisible();
      await screen(page, vp, "16b-two-classes");

      // 17. Judge extras: testing evidence, the judge guide, the AI map
      await page.goto("/#/testing");
      await screen(page, vp, "17-testing-evidence");
      await page.goto("/#/assistant");
      await screen(page, vp, "17-assistant");
      await page.goto("/#/aimap");
      await screen(page, vp, "17-ai-map");
    });
  });
}
