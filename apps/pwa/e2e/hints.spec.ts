import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
    localStorage.setItem("cc.voice", "0");
  });
});

test("try to break it shows which check stopped each prepared line, in her language", async ({ page }) => {
  await page.goto("/#/aimap");
  for (const [kind, text] of [["injection", "instruction to the system"], ["phone", "phone number"], ["child_name", "child's name"], ["harsh", "harsh word"]]) {
    await page.getByTestId(`break-${kind}`).click();
    await expect(page.getByTestId("break-explanation")).toContainText(text as string);
  }
  await expect(page.getByTestId("break-result")).toContainText("pre-filter");
});

test("try to break it checks a line the visitor types, and says when it passes", async ({ page }) => {
  await page.goto("/#/aimap");
  await page.getByTestId("break-text").fill("Call me on 98765 43210");
  await page.getByTestId("break-check").click();
  await expect(page.getByTestId("break-verdict")).toHaveText("Held back");
  await expect(page.getByTestId("break-explanation")).toContainText("phone number");
  await expect(page.getByTestId("break-result")).toContainText("Call me on 98765 43210");
  await page.getByTestId("break-text").fill("Show the bundle of ten sticks");
  await page.getByTestId("break-check").click();
  await expect(page.getByTestId("break-verdict")).toHaveText("Passed");
  await expect(page.getByTestId("break-explanation")).toContainText("Passed the rule-based checks");
});

test("a typed remark that puts a child down is held back, in its own words", async ({ page }) => {
  await page.goto("/#/aimap");
  await page.getByTestId("break-text").fill("you are not clever");
  await page.getByTestId("break-check").click();
  await expect(page.getByTestId("break-verdict")).toHaveText("Held back");
  await expect(page.getByTestId("break-explanation")).toContainText("puts a child down");
});

test("the prepared lines are chips that sit several to a row", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/#/aimap");
  await expect(page.locator(".chips .chip-btn")).toHaveCount(4);
  const tops = await page.locator(".chips .chip-btn").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
  expect(tops).toHaveLength(4);
  expect(new Set(tops).size).toBeLessThan(4); // at least two chips share a row
});

test("try with hints offers three replies, and choosing one runs the turn with a move tag", async ({ page }) => {
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  await page.getByTestId("side-judge").click();
  await page.getByTestId("hints-toggle").check();
  await page.getByTestId("side-turn").click();
  await expect(page.getByTestId("hint-pose_problem")).toBeVisible();
  await page.getByTestId("hint-pose_problem").click();
  await expect(page.getByTestId("reply-1")).toBeVisible();
  await expect(page.getByTestId("move-tag-1")).toContainText("Move:");
  await expect(page.getByTestId("hints").locator("button")).toHaveCount(3);
  await page.getByTestId("side-judge").click(); // the per-child meters sit in the judge trace
  await expect(page.getByTestId("meters")).toBeVisible();
});
