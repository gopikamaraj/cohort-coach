import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => (localStorage.clear(), localStorage.setItem("cc.user", "{\"id\":\"e2e tester\",\"nickname\":\"e2e tester\"}"), localStorage.setItem("cc.cacheOwner", "e2e tester")));
  await page.goto("/#/roles");
  await page.reload();
});

test("a fresh browser lands on four role cards and the guided tour", async ({ page }) => {
  await expect(page.getByTestId("card-tour")).toBeVisible();
  await expect(page.getByTestId("card-tour")).toContainText("Start here");
  for (const r of ["teacher", "mentor", "coach", "officer", "judge", "admin"]) await expect(page.getByTestId(`card-${r}`)).toBeVisible();
  await page.getByTestId("card-judge").click(); // the judge card enters judge mode
  await expect(page).toHaveURL(/#\/judge/);
  await expect(page.getByTestId("role-chip")).toHaveText("Viewing as Judge");
  await page.goto("/#/roles");
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

test("the teacher dialog says the weekly cap, with no percentage and no mention of Telegram", async ({ page }) => {
  await page.getByTestId("card-teacher").click();
  const dialog = page.getByTestId("role-dialog");
  await expect(dialog).not.toContainText("Telegram");
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

test("the install card opens plain steps in her language, and closes again", async ({ page }) => {
  await expect(page.getByTestId("install-card")).toBeVisible();
  await page.getByTestId("install-open").click();
  const sheet = page.getByTestId("install-dialog");
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText("What is this?");
  await expect(page.getByTestId("install-steps").locator("li")).toHaveCount(5);
  await expect(sheet).toContainText("Add to Home screen");
  await expect(sheet).toContainText("The Practice Class needs signal");
  await expect(sheet).not.toContainText("%");
  await page.getByTestId("install-close").click();
  await expect(sheet).toBeHidden();
  // Esc closes it too
  await page.getByTestId("install-open").click();
  await expect(sheet).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
});

test("the install steps read in Hindi and Tamil, with no English words", async ({ page }) => {
  for (const [lang, title] of [["hi", "यह क्या है?"], ["ta", "இது என்ன?"]] as const) {
    await page.goto("/#/roles");
    await page.getByTestId(`lang-${lang}`).click();
    await page.getByTestId("install-open").click();
    const sheet = page.getByTestId("install-dialog");
    await expect(sheet).toContainText(title);
    const words = (await sheet.innerText()).match(/[A-Za-z][A-Za-z'’-]{2,}/g) ?? [];
    expect(words, lang).toEqual([]);
    await page.getByTestId("install-close").click();
  }
});

test("the install button is on My profile too, and the sheet fits a phone", async ({ page }) => {
  await page.goto("/#/profile");
  await page.getByTestId("install-open").click();
  const box = (await page.getByTestId("install-dialog").boundingBox())!;
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize()!.width + 1);
  await expect(page.getByTestId("install-close")).toBeVisible();
  expect((await page.getByTestId("install-close").boundingBox())!.height).toBeGreaterThanOrEqual(48);
});

test("offline: a short pill with the cloud-off icon, and a note on what still works", async ({ page }) => {
  await expect(page.getByTestId("offline-note")).toHaveCount(0);
  await page.context().setOffline(true);
  await expect(page.getByTestId("status")).toHaveText("Offline");
  await expect(page.getByTestId("status").locator("svg")).toHaveCount(1);
  await expect(page.getByTestId("offline-note")).toContainText("saved lessons");
  await expect(page.getByTestId("offline-note")).toContainText("Practice Class needs signal");
  // the app name stays on one line beside the pill
  const brand = (await page.getByTestId("brand").boundingBox())!;
  expect(brand.height).toBeLessThan(60);
  await page.context().setOffline(false);
  await expect(page.getByTestId("status")).toContainText("Online");
  await expect(page.getByTestId("offline-note")).toHaveCount(0);
});

test("online, the pill adds the browser's own signal estimate when it has one", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "connection", { value: { effectiveType: "3g", downlink: 1.65, addEventListener() {}, removeEventListener() {} }, configurable: true });
  });
  await page.reload();
  await expect(page.getByTestId("status-speed")).toContainText("Slow signal · 1.7 Mbps");
  await expect(page.getByTestId("status")).toHaveAttribute("title", /Upload speed is not shown/);
  await page.context().setOffline(true);
  await expect(page.getByTestId("status-speed")).toHaveCount(0); // no speed while offline
  await page.context().setOffline(false);
});

test("no speed is shown when the browser gives no estimate", async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, "connection", { value: undefined, configurable: true }));
  await page.reload();
  await expect(page.getByTestId("status")).toContainText("Online");
  await expect(page.getByTestId("status-speed")).toHaveCount(0);
});

test("there is one app: no Mode menu, no mode chip and no pilot switch on the landing page", async ({ page }) => {
  await expect(page.getByTestId("mode")).toHaveCount(0);
  await expect(page.getByTestId("mode-banner")).toHaveCount(0); // the role is in the title bar, not here
  await expect(page.getByTestId("role-chip")).toHaveCount(0); // and not on the picker itself
  await expect(page.getByTestId("card-tour")).toBeVisible();
  await expect(page.getByRole("button", { name: /Open the pilot/ })).toHaveCount(0);
  await expect(page.getByText(/pilot/i)).toHaveCount(0);
});

test("the tour card sits in the first screen of a phone, above the fold", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await page.reload();
  const tour = (await page.getByTestId("card-tour").boundingBox())!;
  expect(tour.y + tour.height).toBeLessThanOrEqual(640 - 56); // above the bottom bar
});

test("the title bar shows the page and what it is for, the connection, a language switch and the role", async ({ page }) => {
  await page.goto("/#/roles");
  await expect(page.locator(".strip")).toHaveCount(0); // no role or language dropdowns under the bar
  await expect(page.getByTestId("role")).toHaveCount(0);
  await expect(page.getByTestId("top-title")).toHaveText("Choose your role");
  await expect(page.getByTestId("top-sub")).not.toBeEmpty();
  await expect(page.getByTestId("status")).toBeVisible();
  await expect(page.getByTestId("role-chip")).toHaveCount(0); // the picker is where the role is chosen
  await expect(page.getByTestId("lang-en")).toHaveAttribute("aria-pressed", "true");
  await page.goto("/#/papers");
  await expect(page.getByTestId("top-title")).toHaveText("Papers");
  await expect(page.getByTestId("top-sub")).toContainText("check paper");
  await expect(page.getByTestId("role-chip")).toHaveText("Viewing as Teacher");
  await page.getByTestId("lang-hi").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await expect(page.getByTestId("lang-hi")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("top-title")).toHaveText("पेपर");
  await expect(page.getByTestId("role-chip")).toContainText("शिक्षक");
  await page.getByTestId("lang-ta").click();
  await expect(page.getByTestId("top-title")).toHaveText("தாள்கள்");
  await page.getByTestId("role-chip").click(); // the role leads back to the role picker
  await expect(page).toHaveURL(/#\/roles/);
});

test("the title bar fits a phone and a laptop without sideways scrolling, in every language", async ({ page }) => {
  for (const [w, h] of [[360, 700], [1280, 800]]) {
    await page.setViewportSize({ width: w, height: h });
    for (const lang of ["en", "hi", "ta"]) {
      await page.goto("/#/practice");
      await page.getByTestId(`lang-${lang}`).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
      for (const id of ["lang-en", "lang-hi", "lang-ta", "role-chip"]) {
        const box = (await page.getByTestId(id).boundingBox())!;
        expect(box.height).toBeGreaterThanOrEqual(43.5);
        expect(box.x + box.width).toBeLessThanOrEqual(w + 1);
      }
    }
  }
});
