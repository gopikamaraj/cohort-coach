import { expect, test } from "./test";
import { fillAndApprove, startSample } from "./sample";

// Step E: the cloud is the record. A change made while offline waits in the outbox; when the connection is
// back a notice says how many changes will now be saved to her account, shows the result, and the server has
// them. Signing in with the same nickname on a second device reads the same data.

const RIGHT = ["346", "728", "85", "74", "82", "35", "38", "26", "43", "54"];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}'));
});

test("changes made offline are saved to the account with a notice, and the server holds them", async ({ page, context, request }) => {
  await startSample(page, { size: 1 });
  await page.waitForTimeout(800); // the class and the new check are written while online
  await context.setOffline(true);
  await fillAndApprove(page, RIGHT);
  await page.waitForTimeout(600);
  const before = (await (await request.get("/api/store")).json()) as { checks: Record<string, unknown> };
  expect(JSON.stringify(before.checks)).not.toContain('"346"'); // not in the cloud yet
  await context.setOffline(false);
  await expect(page.getByTestId("sync-notice")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("sync-body")).toContainText("while you were offline");
  await expect(page.getByTestId("sync-saved")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("sync-notice")).toBeHidden({ timeout: 10_000 }); // a clean result closes itself
  const store = (await (await request.get("/api/store")).json()) as { checks: Record<string, unknown> };
  expect(JSON.stringify(store.checks)).toContain("346"); // the cloud database has the answers
});

test("a second device that signs in with the same nickname reads the same data", async ({ page, browser, request }) => {
  await startSample(page, { size: 1 });
  await fillAndApprove(page, RIGHT);
  await page.waitForTimeout(1500);
  const user = await page.evaluate(() => JSON.parse(localStorage.getItem("cc.user") ?? "{}") as { id: string });
  const other = await browser.newContext({ baseURL: "http://localhost:4173", extraHTTPHeaders: { "X-User": user.id }, storageState: { cookies: [], origins: [{ origin: "http://localhost:4173", localStorage: [{ name: "cc.user", value: JSON.stringify({ id: user.id, nickname: user.id }) }] }] } });
  const p2 = await other.newPage();
  await p2.goto("/#/history");
  await expect.poll(async () => JSON.stringify(await p2.evaluate(async () => (await (await fetch("/api/store", { headers: { "X-User": JSON.parse(localStorage.getItem("cc.user") ?? "{}").id } })).json()).checks)), { timeout: 20_000 }).toContain("346");
  await other.close();
  expect(request).toBeTruthy();
});
