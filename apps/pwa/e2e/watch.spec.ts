import { expect, test } from "./test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => (((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")])));
});

test("watching an experienced run shows the AI label, move tags, subtitles and the feedback card", async ({ page }) => {
  await page.goto("/#/watch");
  await page.getByTestId("watch-experienced").click();
  await expect(page.getByTestId("run-kind")).toHaveText(/Recorded run/);
  await page.getByTestId("w-step").click();
  await expect(page.getByTestId("ai-label-1")).toHaveText("AI playing the teacher (demo only)");
  await expect(page.getByTestId("move-tag-1")).toContainText("Move:");
  await expect(page.getByTestId("subtitle-1")).toContainText("In English");
  await page.getByTestId("w-machinery").check();
  await expect(page.getByTestId("machinery-1")).toContainText("Call 10");
  await page.getByTestId("w-skip").click();
  await expect(page.getByTestId("feedback-experienced")).toBeVisible();
  await expect(page.getByTestId("feedback-experienced")).toContainText("Checked");
});

test("the two styles can be shown together and read differently", async ({ page }) => {
  await page.goto("/#/watch");
  await page.getByTestId("watch-experienced").click();
  await expect(page.getByTestId("run-experienced")).toBeVisible();
  await page.getByTestId("watch-struggling").click();
  await expect(page.getByTestId("run-struggling")).toBeVisible();
  for (const s of ["experienced", "struggling"]) await page.getByTestId(`run-${s}`).getByTestId("w-skip").click();
  const good = await page.getByTestId("feedback-experienced").innerText();
  const weak = await page.getByTestId("feedback-struggling").innerText();
  expect(good).not.toEqual(weak);
  expect(good).toMatch(/\d of \d points/);
});

test("asking for a live run in a recorded deployment says why a recorded run is shown", async ({ page }) => {
  await page.goto("/#/watch");
  await page.getByTestId("watch-live").check();
  await page.getByTestId("watch-struggling").click();
  await expect(page.getByTestId("run-reason")).toContainText("Showing a recorded run");
  await expect(page.getByTestId("watch-meter")).toBeVisible();
});

test("the run plays itself when left alone", async ({ page }) => {
  await page.goto("/#/watch");
  await page.getByTestId("watch-experienced").click();
  await expect(page.getByTestId("watch-turn-1")).toBeVisible({ timeout: 8000 });
  await page.getByTestId("w-fast").click();
  await expect(page.getByTestId("watch-turn-2")).toBeVisible({ timeout: 12000 });
});
