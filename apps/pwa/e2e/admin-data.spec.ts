import { expect, test } from "@playwright/test";
import { CONSENT, fresh } from "./qa";

// Admin: the Admin card on the landing page, what testers said, and deleting one scope of data to
// start fresh (only after typing DELETE). The AI audit log and the paid-read cache are not offered.

test("the Admin card opens Admin; testers' inputs show; a scope deletes only after DELETE is typed", async ({ page, request }) => {
  await fresh(page);
  await page.goto("/#/roles");
  await page.evaluate((c) => localStorage.setItem("cc.consent", c), CONSENT);
  const posted = await request.post("http://localhost:8011/api/feedback", { data: { kind: "app", rating: 4, text: "admin data test line", language: "en", role: "teacher" } });
  expect(posted.ok()).toBe(true);

  await page.getByTestId("card-admin").click();
  await expect(page).toHaveURL(/#\/admin/);
  await expect(page.getByTestId("role-chip")).toHaveText("Viewing as Admin");
  await expect(page.getByTestId("admin-testers")).toBeVisible();
  await expect(page.getByTestId("admin-testing-link")).toBeVisible();

  const rows = page.getByTestId("admin-rows-feedback");
  await expect(rows).not.toHaveText("0 rows");
  await expect(page.getByTestId("admin-delete-feedback")).toBeDisabled(); // nothing typed yet
  await page.getByTestId("admin-confirm-feedback").fill("delete");
  await expect(page.getByTestId("admin-delete-feedback")).toBeDisabled(); // the exact word only
  await page.getByTestId("admin-confirm-feedback").fill("DELETE");
  await page.getByTestId("admin-delete-feedback").click();
  await expect(page.getByTestId("admin-deleted")).toContainText("Deleted");
  await expect(rows).toHaveText("0 rows");
  await expect(page.getByTestId("admin-scope-observations")).toBeVisible(); // other scopes are still listed
  await expect(page.locator("main")).toContainText("AI audit log");
});
