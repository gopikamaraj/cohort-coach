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

test("try with hints offers three replies, and choosing one runs the turn with a move tag", async ({ page }) => {
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  await page.getByTestId("hints-toggle").check();
  await expect(page.getByTestId("hint-pose_problem")).toBeVisible();
  await page.getByTestId("hint-pose_problem").click();
  await expect(page.getByTestId("reply-1")).toBeVisible();
  await expect(page.getByTestId("move-tag-1")).toContainText("Move:");
  await expect(page.getByTestId("meters")).toBeVisible();
  await expect(page.getByTestId("hints").locator("button")).toHaveCount(3);
});
