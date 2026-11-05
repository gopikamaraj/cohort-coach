// Tester stats in a real browser. The tester endpoints are answered by the test (page.route), so the
// shared recorded API stays unchanged; the checks are about what the browser sends and when.
import { type Page } from "@playwright/test";
import { expect, test } from "./test";

const SALT = "cc-tester-v1";
interface Sent { url: string; method: string; body: string; headers: Record<string, string> }

async function mockTester(page: Page): Promise<Sent[]> {
  const sent: Sent[] = [];
  await page.route("**/api/tester/**", async (route) => {
    const req = route.request();
    if (req.url().endsWith("/api/tester/config")) return route.fulfill({ json: { enabled: true, salt: SALT, retention_days: 90 } });
    sent.push({ url: req.url(), method: req.method(), body: req.postData() ?? "", headers: req.headers() });
    return route.fulfill({ json: { ok: true } });
  });
  return sent;
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(async () => {
    (((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")]));
    for (const d of (await indexedDB.databases?.()) ?? []) if (d.name) indexedDB.deleteDatabase(d.name);
  });
});

test("a new device sees the name sheet once; declining sends nothing and the app works", async ({ page }) => {
  const sent = await mockTester(page);
  await page.goto("/#/roles?src=teachers");
  await expect(page.getByTestId("tester-first")).toBeVisible();
  await expect(page.getByTestId("tester-first")).toContainText("Please don't type any child's name");
  await page.getByTestId("tester-skip").click();
  await expect(page.getByTestId("tester-first")).toHaveCount(0);
  await page.getByTestId("card-teacher").click();
  await page.getByTestId("dlg-enter").click();
  await expect(page).toHaveURL(/#\/home/);
  await page.getByTestId("tester-fb-open").click();
  await expect(page.getByTestId("tester-fb-sheet")).toContainText("Sharing is off");
  await page.keyboard.press("Escape");
  await page.reload();
  await expect(page.getByTestId("tester-first")).toHaveCount(0); // asked once only
  await page.waitForTimeout(800);
  expect(sent).toEqual([]);
});

test("agreeing sends only the salted hash, the nickname choice and coarse fields", async ({ page }) => {
  const sent = await mockTester(page);
  await page.goto("/#/roles?src=edu-mentor");
  await page.getByTestId("tester-name").fill("Asha");
  await page.getByTestId("tester-save").click();
  await page.getByTestId("card-teacher").click();
  await page.getByTestId("dlg-enter").click();
  await expect.poll(() => sent.some((s) => s.url.endsWith("/events")), { timeout: 10_000 }).toBe(true);
  const profile = sent.find((s) => s.url.endsWith("/profile"));
  const p = JSON.parse(profile!.body);
  // Updated 4 Nov: the nickname is the user id (DECISIONS 2026-11-03), so the profile carries no device hash and the
  // phone keeps no device id; the server names the row by the signed-in user.
  expect(p).not.toHaveProperty("device_hash");
  expect(p).toMatchObject({ consent_stats: true, nickname: "Asha", nickname_public: false, invite_source: "edu-mentor", is_judge: false });
  expect(Object.keys(p).sort()).toEqual(
    ["app_version", "browser_family", "consent_stats", "device_class", "installed_pwa", "invite_source", "is_judge", "language", "nickname", "nickname_public", "os_family"].sort(),
  );
  const raw = await page.evaluate(async () => {
    const db = await new Promise<IDBDatabase>((res) => { const r = indexedDB.open("cohort-coach"); r.onsuccess = () => res(r.result); });
    return new Promise<string>((res) => { const r = db.transaction("settings").objectStore("settings").get("tester.deviceId"); r.onsuccess = () => res((r.result?.value as string) ?? ""); });
  });
  expect(raw).toBe(""); // no device id is made or kept
  const events = JSON.parse(sent.find((s) => s.url.endsWith("/events"))!.body).events as { type: string }[];
  expect(events.map((e) => e.type)).toContain("session_start");
});

test("the feedback sheet sends a rating, tags and a comment, and says thank you", async ({ page }) => {
  const sent = await mockTester(page);
  await page.goto("/#/roles");
  await page.getByTestId("tester-name").fill("Asha");
  await page.getByTestId("tester-save").click();
  await page.getByTestId("tester-fb-open").click();
  await page.getByTestId("tester-star-4").click();
  await page.getByTestId("tester-tag-easy").click();
  await page.getByTestId("tester-tag-useful").click();
  await page.getByTestId("tester-comment").fill("Clear screens");
  await page.getByTestId("tester-fb-send").click();
  await expect(page.getByTestId("toast").first()).toContainText("Thank you");
  await expect.poll(() => sent.some((s) => s.url.endsWith("/feedback")), { timeout: 10_000 }).toBe(true);
  expect(JSON.parse(sent.find((s) => s.url.endsWith("/feedback"))!.body)).toMatchObject({ rating: 4, tags: ["easy", "useful"], comment: "Clear screens", screen_id: "roles" });
});

test("Delete my data in My profile calls the server and stops sharing", async ({ page }) => {
  // Replaces "... calls the server by hash": the nickname is the user id (DECISIONS 2026-11-03), so there is no device
  // code to show and the delete goes by the signed-in user. The server side is tested in tests/tester.
  const sent = await mockTester(page);
  await page.goto("/#/roles");
  await page.getByTestId("tester-name").fill("Asha");
  await page.getByTestId("tester-save").click();
  await page.goto("/#/profile");
  await expect(page.getByTestId("tester-device")).toHaveCount(0); // no device code is shown or kept
  await page.getByTestId("tester-delete").click();
  await page.getByTestId("tester-delete").click();
  await expect.poll(() => sent.some((s) => s.method === "DELETE"), { timeout: 10_000 }).toBe(true);
  await expect(page.getByTestId("tester-settings")).toContainText("Sharing is off");
});

test("the feature is invisible when the server has it off", async ({ page }) => {
  await page.goto("/#/roles");
  await expect(page.getByTestId("tester-first")).toHaveCount(0);
  await expect(page.getByTestId("tester-fb-open")).toHaveCount(0);
});

const EMPTY = {
  include_flagged: false,
  cards: { testers: 0, sessions: 0, returning_testers: 0, roles_tried_avg: null, tours_completed: 0, feedback_received: 0, average_rating: null, offline_share: null, date_from: null, date_to: null },
  testers_by_day: [], role_funnel: [], tour_funnel: [], by_source: [], device_class: [], language: [], testers: [], feedback: [], changes: [],
  excluded: { judge_devices: 0, team_devices: 0 },
};

test("Testing evidence shows honest empty states with no data", async ({ page }) => {
  await page.route("**/api/judge/testing-evidence**", (r) => r.fulfill({ json: EMPTY }));
  await page.goto("/#/testing");
  await expect(page.getByTestId("te-range")).toContainText("Nothing collected yet");
  await expect(page.getByTestId("te-testers")).toContainText("0");
  await expect(page.getByTestId("te-rating")).toContainText("None yet");
  await expect(page.getByTestId("te-feedback-empty")).toBeVisible();
  await expect(page.getByTestId("te-changes-empty")).toBeVisible();
});

for (const lang of ["en", "hi", "ta"] as const) {
  test(`Testing evidence fits a phone without sideways scroll (${lang})`, async ({ page }) => {
    const data = {
      ...EMPTY,
      cards: { ...EMPTY.cards, testers: 3, sessions: 5, roles_tried_avg: 1.7, feedback_received: 1, average_rating: 4, offline_share: 0.33, date_from: "2026-10-30", date_to: "2026-10-31" },
      testers_by_day: [{ day: "2026-10-30", testers: 2 }], role_funnel: [{ stage: "selected", testers: 3 }],
      tour_funnel: [{ stage: "started", testers: 2 }, { stage: "step_1", testers: 2 }], by_source: [{ label: "teachers", testers: 2 }],
      testers: [{ name: "Anonymous tester 01", listed: false, hash6: "abc123", roles_tried: 2, tours_completed: 1, features_used: 3, sessions: 2, last_seen: "2026-10-31", rating: 4 }],
      feedback: [{ rating: 4, role: "teacher", screen_id: "home", tags: ["easy"], comment: "Clear", day: "2026-10-31" }],
    };
    await page.route("**/api/judge/testing-evidence**", (r) => r.fulfill({ json: data }));
    await page.addInitScript((l) => localStorage.setItem("cc.lang", l), lang);
    await page.goto("/#/testing");
    await expect(page.getByTestId("te-table")).toBeVisible();
    await expect(page.getByTestId("te-days").locator("svg")).toHaveAttribute("aria-label", /2026-10-30/);
    const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(over).toBeLessThanOrEqual(0);
  });
}
