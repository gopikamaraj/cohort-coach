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

test("the landing page uses the width: one column on a phone, a grid of equal cards on a laptop", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/#/roles");
  await page.reload();
  const frame = (await page.locator(".frame").boundingBox())!;
  expect(frame.width).toBeGreaterThan(1000);
  const widths = await Promise.all(["teacher", "mentor", "coach", "officer"].map(async (r) => (await page.getByTestId(`card-${r}`).boundingBox())!.width));
  expect(Math.max(...widths) - Math.min(...widths)).toBeLessThan(2); // equal cards, not ragged
  const ys = await Promise.all(["teacher", "officer"].map(async (r) => (await page.getByTestId(`card-${r}`).boundingBox())!.y));
  expect(Math.abs(ys[0]! - ys[1]!)).toBeLessThan(2); // four across on one row
  await page.setViewportSize({ width: 390, height: 800 });
  await page.reload();
  const t = (await page.getByTestId("card-teacher").boundingBox())!;
  const o = (await page.getByTestId("card-officer").boundingBox())!;
  expect(Math.abs(t.width - o.width)).toBeLessThan(2);
  expect(t.x + t.width).toBeLessThanOrEqual(390);
});
