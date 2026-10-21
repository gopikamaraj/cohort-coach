import { expect, test } from "@playwright/test";

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => {
    localStorage.clear();
    localStorage.setItem("cc.consent", c);
  }, CONSENT);
});

test("sample sheets run a check, mark the unsure boxes, and the error card says where it most likely went wrong", async ({ page }) => {
  await page.goto("/#/check");
  await page.getByTestId("use-sample").click();
  await expect(page.getByTestId("photo-note")).toContainText("recorded reads of made-up sheets");
  await expect(page.locator("[data-check='true']").first()).toBeVisible();
  await page.getByTestId("missed-teaching").check();
  await page.getByTestId("finish").click();
  await expect(page).toHaveURL(/#\/cards/);
  const stages = page.getByTestId("stage-lines");
  await expect(stages).toBeVisible();
  await expect(stages).toContainText("most likely");
  await expect(page.getByTestId("stage-Core")).toContainText("children:");
  await expect(page.getByTestId("probe-Core")).toContainText("One-minute check");
  await expect(page.getByTestId("stage-Output")).toBeVisible();
  await expect(page.getByTestId("stage-Input (test)")).toBeVisible();
  await expect(page.getByTestId("stage-missed")).toContainText("1 children missed the teaching");
  await expect(stages).not.toContainText("%"); // counts, never percentages
});

test("the sheets never leave the phone: no request carries the answers and the stage lines still show", async ({ page }) => {
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST") posts.push(r.url());
  });
  await page.goto("/#/check");
  await page.getByTestId("use-sample").click();
  await page.getByTestId("finish").click();
  await expect(page).toHaveURL(/#\/cards/);
  await expect(page.getByTestId("stage-lines")).toBeVisible();
  expect(posts.filter((u) => u.includes("/api/stages"))).toHaveLength(0);
  expect(posts.every((u) => /\/api\/classes\/c-[0-9a-f]+\/profile$/.test(u))).toBe(true); // counts only
});

test("the stage lines are in her language", async ({ page }) => {
  await page.evaluate(() => localStorage.setItem("cc.lang", "hi"));
  await page.goto("/#/check");
  await page.reload();
  await page.getByTestId("use-sample").click();
  await page.getByTestId("finish").click();
  await expect(page.getByTestId("stage-lines")).toContainText("सबसे संभावित");
  await expect(page.getByTestId("probe-Core")).toContainText("एक मिनट की जाँच");
});
