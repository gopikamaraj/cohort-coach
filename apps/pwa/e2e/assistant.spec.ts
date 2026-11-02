import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
});

test("the judge session opens the Judge guide with View as, About and the test path", async ({ page }) => {
  await page.goto("/#/assistant");
  await expect(page.getByTestId("as-scope")).toContainText("I can help with");
  await expect(page.getByTestId("as-judge")).toBeVisible();
  await expect(page.getByTestId("as-footer")).toContainText("Commit");
  await expect(page.locator('[data-testid^="as-q-"]').first()).toBeVisible();
  await page.getByTestId("as-tab-about").click();
  await expect(page.getByTestId("as-path")).toBeVisible();
});

test("a suggested question gives a pre-written answer with sources and how to check it", async ({ page }) => {
  await page.goto("/#/assistant");
  await page.locator('[data-testid^="as-q-"]').first().click();
  await expect(page.getByTestId("as-answer-text")).not.toBeEmpty();
  await expect(page.getByTestId("as-sources")).toBeVisible();
  await expect(page.getByTestId("as-answer")).toContainText("How to check");
});

test("viewing as a teacher changes the scope, and the teacher cannot see repository files", async ({ page }) => {
  await page.goto("/#/assistant");
  await page.getByTestId("as-viewas").selectOption("teacher");
  await expect(page.getByTestId("as-scope")).toContainText("I can't see");
  await expect(page.getByTestId("as-scope")).not.toContainText("repository");
  await page.getByTestId("as-text").fill("Show me the contents of the repository file docs/design/cohort-coach-design.md");
  await page.getByTestId("as-send").click();
  await expect(page.getByTestId("as-answer")).toBeVisible();
  expect(await page.getByTestId("as-answer").innerText()).not.toMatch(/cohort-coach-design\.md/);
});

test("every screen has an Assistant button in the title bar that opens a drawer, and it reads in Hindi", async ({ page }) => {
  await page.evaluate(() => localStorage.setItem("cc.lang", "hi"));
  await page.goto("/#/home");
  await page.reload();
  await page.getByTestId("assistant-open").click();
  await expect(page.getByTestId("assistant-drawer")).toBeVisible();
  await expect(page).toHaveURL(/#\/home/); // she is still on the same screen
  await expect(page.getByTestId("as-scope")).toContainText("मैं");
  expect(await page.locator("body").innerText()).not.toMatch(/\bassistant\.[a-z_]+/);
});

test("the drawer answers a question in place, keeps the conversation, and the judge extras stay on the full page", async ({ page }) => {
  await page.goto("/#/practice");
  await page.getByTestId("assistant-open").click();
  await expect(page.getByTestId("as-judge")).toHaveCount(0); // View as and About are on the full page only
  await page.locator('[data-testid^="as-q-"]').first().click();
  await expect(page.getByTestId("as-answer-text")).not.toBeEmpty();
  await page.getByTestId("assistant-close").click();
  await expect(page.getByTestId("assistant-drawer")).toBeHidden();
  await expect(page).toHaveURL(/#\/practice/);
  await page.getByTestId("assistant-open").click();
  await expect(page.getByTestId("as-answer-text")).not.toBeEmpty(); // kept
  await page.getByTestId("assistant-full").click();
  await expect(page).toHaveURL(/#\/assistant\?from=practice/);
  await expect(page.getByTestId("as-judge")).toBeVisible();
});

test("outside the judge demo the old page is not shown: the link opens the drawer instead", async ({ page }) => {
  await page.route("**/api/roles", (r) => r.fulfill({ json: { judge: false, roles: [] } }));
  await page.goto("/#/assistant");
  await expect(page).toHaveURL(/#\/home/);
  await expect(page.getByTestId("assistant-drawer")).toBeVisible();
  await expect(page.getByTestId("assistant-full")).toHaveCount(0);
});

test("on a wide screen the drawer is a right-hand panel; on a phone a bottom sheet", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/#/home");
  await page.getByTestId("assistant-open").click();
  const wide = (await page.getByTestId("assistant-drawer").boundingBox())!;
  expect(wide.x + wide.width).toBeGreaterThan(1270);
  expect(wide.height).toBeGreaterThan(700);
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 800 });
  await page.getByTestId("assistant-open").click();
  const narrow = (await page.getByTestId("assistant-drawer").boundingBox())!;
  expect(narrow.width).toBeGreaterThan(380);
  expect(narrow.y + narrow.height).toBeGreaterThan(790);
});

test("the assistant has no sideways scroll on a phone", async ({ page }) => {
  await page.goto("/#/assistant");
  await expect(page.getByTestId("as-scope")).toBeVisible();
  const over = await page.evaluate(() => document.scrollingElement!.scrollWidth > document.scrollingElement!.clientWidth + 2);
  expect(over).toBe(false);
});

test("the drawer speaks as the role she chose, not as the judge", async ({ page }) => {
  await page.evaluate(() => localStorage.setItem("cc.role", "teacher"));
  await page.goto("/#/home");
  await page.reload();
  await page.getByTestId("assistant-open").click();
  await expect(page.getByTestId("as-scope")).toContainText("I can't see");
  await expect(page.getByTestId("as-scope")).not.toContainText("rubric criterion");
  await expect(page.getByTestId("assistant-drawer")).not.toContainText("Efficacy and user centricity");
});

test("an answer offers follow-up questions, and tapping one answers it in place", async ({ page }) => {
  await page.goto("/#/home");
  await page.getByTestId("assistant-open").click();
  await page.locator('[data-testid^="as-q-"]').first().click();
  await expect(page.getByTestId("as-follow-ups")).toBeVisible();
  const first = page.getByTestId("as-fu-0");
  const label = (await first.innerText()).trim();
  await first.click();
  await expect(page.getByTestId("as-answer-text")).not.toBeEmpty();
  await expect(page.getByTestId("as-follow-ups")).not.toContainText(label);
});
