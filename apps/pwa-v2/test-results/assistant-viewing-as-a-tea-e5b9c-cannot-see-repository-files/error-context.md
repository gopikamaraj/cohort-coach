# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: assistant.spec.ts >> viewing as a teacher changes the scope, and the teacher cannot see repository files
- Location: e2e\assistant.spec.ts:26:1

# Error details

```
Error: expect(locator).not.toContainText(expected) failed

Locator: getByTestId('as-scope')
Expected substring: not "repository"
Received string: "I can help with: How to use the app, what an error card means, what to try next, and what today's step is. I can't see: Other teachers, drafts that are not approved, the repository, and any child's name. It never approves or sends anything."
Timeout: 5000ms

Call log:
  - Expect "not toContainText" getByTestId('as-scope') with timeout 5000ms
  - waiting for getByTestId('as-scope')
    14 × locator resolved to <p class="muted" data-testid="as-scope">…</p>
       - unexpected value "I can help with: How to use the app, what an error card means, what to try next, and what today's step is. I can't see: Other teachers, drafts that are not approved, the repository, and any child's name. It never approves or sends anything."

```

```yaml
- paragraph:
  - strong: "I can help with:"
  - text: How to use the app, what an error card means, what to try next, and what today's step is.
  - strong: "I can't see:"
  - text: Other teachers, drafts that are not approved, the repository, and any child's name. It never approves or sends anything.
```

# Test source

```ts
  1  | import { expect, test } from "@playwright/test";
  2  | 
  3  | test.beforeEach(async ({ page }) => {
  4  |   await page.goto("/");
  5  |   await page.evaluate(() => localStorage.clear());
  6  | });
  7  | 
  8  | test("the judge session opens the Judge guide with View as, About and the test path", async ({ page }) => {
  9  |   await page.goto("/#/assistant");
  10 |   await expect(page.getByTestId("as-scope")).toContainText("I can help with");
  11 |   await expect(page.getByTestId("as-judge")).toBeVisible();
  12 |   await expect(page.getByTestId("as-footer")).toContainText("Commit");
  13 |   await expect(page.locator('[data-testid^="as-q-"]').first()).toBeVisible();
  14 |   await page.getByTestId("as-tab-about").click();
  15 |   await expect(page.getByTestId("as-path")).toBeVisible();
  16 | });
  17 | 
  18 | test("a suggested question gives a pre-written answer with sources and how to check it", async ({ page }) => {
  19 |   await page.goto("/#/assistant");
  20 |   await page.locator('[data-testid^="as-q-"]').first().click();
  21 |   await expect(page.getByTestId("as-answer-text")).not.toBeEmpty();
  22 |   await expect(page.getByTestId("as-sources")).toBeVisible();
  23 |   await expect(page.getByTestId("as-answer")).toContainText("How to check");
  24 | });
  25 | 
  26 | test("viewing as a teacher changes the scope, and the teacher cannot see repository files", async ({ page }) => {
  27 |   await page.goto("/#/assistant");
  28 |   await page.getByTestId("as-viewas").selectOption("teacher");
  29 |   await expect(page.getByTestId("as-scope")).toContainText("I can't see");
> 30 |   await expect(page.getByTestId("as-scope")).not.toContainText("repository");
     |                                                  ^ Error: expect(locator).not.toContainText(expected) failed
  31 |   await page.getByTestId("as-text").fill("Show me the contents of the repository file docs/design/cohort-coach-design.md");
  32 |   await page.getByTestId("as-send").click();
  33 |   await expect(page.getByTestId("as-answer")).toBeVisible();
  34 |   expect(await page.getByTestId("as-answer").innerText()).not.toMatch(/cohort-coach-design\.md/);
  35 | });
  36 | 
  37 | test("every screen offers the assistant and it reads in Hindi", async ({ page }) => {
  38 |   await page.evaluate(() => localStorage.setItem("cc.lang", "hi"));
  39 |   await page.goto("/#/home");
  40 |   await page.reload();
  41 |   await page.getByTestId("assistant-link").click();
  42 |   await expect(page.getByTestId("assistant")).toBeVisible();
  43 |   await expect(page.getByTestId("as-scope")).toContainText("मैं");
  44 |   expect(await page.locator("body").innerText()).not.toMatch(/\bassistant\.[a-z_]+/);
  45 | });
  46 | 
  47 | test("the assistant has no sideways scroll on a phone", async ({ page }) => {
  48 |   await page.goto("/#/assistant");
  49 |   await expect(page.getByTestId("as-scope")).toBeVisible();
  50 |   const over = await page.evaluate(() => document.scrollingElement!.scrollWidth > document.scrollingElement!.clientWidth + 2);
  51 |   expect(over).toBe(false);
  52 | });
  53 | 
```