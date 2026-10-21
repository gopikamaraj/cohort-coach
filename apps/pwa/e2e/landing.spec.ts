import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/#/roles");
  await page.reload();
});

test("a fresh browser lands on four role cards and the guided tour", async ({ page }) => {
  await expect(page.getByTestId("card-tour")).toBeVisible();
  await expect(page.getByTestId("card-tour")).toContainText("Start here if you're judging");
  for (const r of ["teacher", "mentor", "coach", "officer"]) await expect(page.getByTestId(`card-${r}`)).toBeVisible();
  await expect(page.getByTestId("card-coach")).toContainText("DIET");
  await expect(page.getByTestId("card-officer")).toContainText("programme staff");
});

test("picking a role shows what it can and cannot do, then enters the dashboard once", async ({ page }) => {
  await page.getByTestId("card-officer").click();
  const dialog = page.getByTestId("role-dialog");
  await expect(dialog).toBeVisible();
  await expect(page.getByTestId("dlg-cannot")).toContainText("counts only, and nothing under 5 classes");
  await expect(dialog).toContainText("Simulated");
  await page.getByTestId("dlg-back").click();
  await expect(page.getByTestId("role-dialog")).toHaveCount(0);
  await page.getByTestId("card-officer").click();
  await page.getByTestId("dlg-enter").click();
  await expect(page).toHaveURL(/#\/officer/);
  // the second time the dialog is skipped
  await page.goto("/#/roles");
  await page.getByTestId("card-officer").click();
  await expect(page).toHaveURL(/#\/officer/);
});

test("the teacher dialog says what is on Telegram and the weekly cap, with no percentage", async ({ page }) => {
  await page.getByTestId("card-teacher").click();
  const dialog = page.getByTestId("role-dialog");
  await expect(dialog).toContainText("Telegram");
  await expect(dialog).toContainText("At most 20 minutes a week");
  await expect(dialog).not.toContainText("%");
});

test("a role has a deep link that opens its dialog", async ({ page }) => {
  await page.goto("/#/roles?open=coach");
  await expect(page.getByTestId("role-dialog")).toContainText("BRC, CRC, DIET faculty member or head teacher");
});
