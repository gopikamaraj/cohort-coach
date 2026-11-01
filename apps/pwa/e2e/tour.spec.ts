import { expect, test } from "@playwright/test";
import { begin, enterRolls } from "./sample";

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => {
    localStorage.clear();
    localStorage.setItem("cc.consent", c);
  }, CONSENT);
});

test("the landing page's tour card starts the tour at step 1 as the teacher", async ({ page }) => {
  await page.goto("/#/roles");
  await page.getByTestId("card-tour").click();
  await expect(page).toHaveURL(/#\/tour\/1/);
  await expect(page.getByTestId("tour-step")).toContainText("Step 1 of 7");
  await expect(page.getByTestId("tour-banner")).toContainText("Now you're the Teacher");
  await expect(page.getByTestId("tour-notice")).toContainText("What to notice");
  await expect(page.getByTestId("tour-standard-paper")).toBeVisible();
});

test("step 1 makes the standard test paper, runs the check on it and shows the error card with stage lines, without leaving the tour", async ({ page }) => {
  await page.goto("/#/tour/1");
  await page.getByTestId("tour-standard-paper").click();
  await expect(page.getByTestId("paper-attached")).toBeVisible({ timeout: 20_000 });
  const sample = (await (await page.request.get("/api/judge/sample-sheets")).json()) as { children: string[][] };
  await begin(page, sample.children.length);
  await enterRolls(page, sample.children);
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("finish").click();
  await expect(page).toHaveURL(/#\/tour\/1/);
  await expect(page.getByTestId("stage-lines")).toBeVisible();
  await expect(page.getByTestId("simulated-banner").or(page.locator(".banner")).first()).toBeVisible();
});

test("skip and back move through the steps and switch the role banner", async ({ page }) => {
  await page.goto("/#/tour/1");
  await page.getByTestId("tour-next").click();
  await expect(page).toHaveURL(/#\/tour\/2/);
  await expect(page.getByTestId("tour-banner")).toContainText("Officer");
  await page.getByTestId("tour-next").click();
  await expect(page.getByTestId("tour-banner")).toContainText("Coach");
  await page.getByTestId("tour-back").click();
  await expect(page).toHaveURL(/#\/tour\/2/);
  await page.goto("/#/tour/6");
  await expect(page.getByTestId("break-it")).toBeVisible();
  await page.goto("/#/tour/7");
  await expect(page.getByTestId("tour-next")).toContainText("Finish");
  await expect(page.getByTestId("testing-evidence")).toBeVisible();
});

test("a step that is built in a later phase says so", async ({ page }) => {
  await page.goto("/#/tour/2");
  await expect(page.getByTestId("tour-pending")).toContainText("arrives in P12");
});

test("leaving and coming back to the deep link resumes at that step", async ({ page }) => {
  await page.goto("/#/tour/4");
  await expect(page.getByTestId("watch")).toBeVisible();
  await page.goto("/#/roles");
  await page.goto("/#/tour/4");
  await expect(page.getByTestId("tour-step")).toContainText("Step 4 of 7");
});

test("a role's walk-through opens the tour at that role's step", async ({ page }) => {
  await page.goto("/#/roles");
  await page.getByTestId("card-coach").click();
  await page.getByTestId("dlg-walk").click();
  await expect(page).toHaveURL(/#\/tour\/3/);
});
