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

test("every screen offers the assistant and it reads in Hindi", async ({ page }) => {
  await page.evaluate(() => localStorage.setItem("cc.lang", "hi"));
  await page.goto("/#/home");
  await page.reload();
  await page.getByTestId("assistant-link").click();
  await expect(page.getByTestId("assistant")).toBeVisible();
  await expect(page.getByTestId("as-scope")).toContainText("मैं");
  expect(await page.locator("body").innerText()).not.toMatch(/\bassistant\.[a-z_]+/);
});

test("the assistant has no sideways scroll on a phone", async ({ page }) => {
  await page.goto("/#/assistant");
  await expect(page.getByTestId("as-scope")).toBeVisible();
  const over = await page.evaluate(() => document.scrollingElement!.scrollWidth > document.scrollingElement!.clientWidth + 2);
  expect(over).toBe(false);
});
