// Improvement-track modules in the browser: the timeline, the closed Get the next module button and its reason,
// feedback, the next module, axe, offline, and Hindi and Tamil at 360 px. (Written to run on the production
// build with SPEECH_MODE=stub; not yet run: the browser tests are with Gopi.)
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { type Page } from "@playwright/test";
import { expect, test } from "./test";
import { enterRolls, finishEntering, startSample } from "./sample";
import { chooseLanguage, chooseRole } from "./switch";

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = JSON.parse(readFileSync(path.join(here, "fixtures", "results16.json"), "utf-8")) as { children: { answers: string[] }[] };

async function trackStarted(page: Page): Promise<void> {
  await startSample(page, { size: fx.children.length });
  await enterRolls(page, fx.children.map((c) => c.answers));
  await finishEntering(page);
  await page.goto("/#/cards");
  await page.getByTestId("class-cohort-open").click();
  await page.getByTestId("class-cohort-create").click();
  await expect(page.getByTestId("class-cohort-made")).toBeVisible();
  await page.goto("/#/cohort");
  await page.getByTestId("module-start").click();
  await expect(page.getByTestId("module-1")).toBeVisible({ timeout: 45_000 }); // Module 1 is made when she starts (recorded AI, stub voice); on a slow machine that takes longer than 5 seconds
}

test.use({ viewport: { width: 360, height: 800 } });

test("starting makes Module 1 only; later modules show a title and a due date; Get the next module is closed with its reason", async ({ page }) => {
  await trackStarted(page);
  await expect(page.getByTestId("module-1-status")).toContainText("Ready");
  await expect(page.getByTestId("module-1-text")).toBeVisible();
  await expect(page.getByTestId("module-2-status")).toContainText("Coming");
  await expect(page.getByTestId("module-2-due")).toContainText("Due");
  await expect(page.getByTestId("module-2-text")).toHaveCount(0); // not made, so no content
  await expect(page.getByTestId("module-next")).toBeDisabled();
  await expect(page.getByTestId("module-next-note")).toContainText("Give feedback on Module 1 to get Module 2, or it will arrive on");
  const body = await page.getByTestId("module-track").innerText();
  expect(body).not.toMatch(/lesson/i);
  expect(body).not.toContain("%");
});

test("an answer opens the button, and Get the next module makes Module 2 with the reason", async ({ page }) => {
  await trackStarted(page);
  await page.getByTestId("module-1-fb-partly").check();
  await page.getByTestId("module-1-fb-send").click();
  await expect(page.getByTestId("module-1-answered")).toBeVisible();
  await expect(page.getByTestId("module-next")).toBeEnabled();
  await page.getByTestId("module-next").click();
  await expect(page.getByTestId("module-2-status")).toContainText("Ready");
  await page.getByTestId("module-2-why").locator("summary").click();
  await expect(page.getByTestId("module-2-why")).toContainText("Module 2 is a smaller step of the same approach because you told us Module 1 partly worked.");
  await expect(page.getByTestId("module-1-status")).toContainText("Done");
});

test("Download audio on a module saves a file named for the module and marks it taken", async ({ page }) => {
  await trackStarted(page);
  const download = page.waitForEvent("download");
  await page.getByTestId("module-1-audio").click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^Cohort-Coach-Improvement-Track-Module-1-.*-en-\d{4}-\d{2}-\d{2}\.mp3$/);
  await expect(page.getByTestId("module-1-status")).toContainText("Audio taken");
});

test("the track passes axe", async ({ page }) => {
  await trackStarted(page);
  const found = (await new AxeBuilder({ page }).include("[data-testid=module-track]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(",")}`)).toEqual([]);
});

for (const lang of ["hi", "ta"]) {
  test(`${lang}: the timeline fits at 360 px`, async ({ page }) => {
    await trackStarted(page);
    await chooseLanguage(page, lang);
    await page.goto("/#/cohort");
    await expect(page.getByTestId("module-list")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("offline: the saved module text opens and getting the next module says it needs a connection", async ({ page, context }) => {
  await trackStarted(page);
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.waitForFunction(async () => (await caches.keys()).length > 0);
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("module-1-text")).toBeVisible();
  await expect(page.getByTestId("module-next")).toBeDisabled();
  await expect(page.getByTestId("module-next-note")).toContainText("needs a connection");
  await context.setOffline(false);
});

test("a coach sees module counts only for cohorts assigned to her, never a teacher's own class cohort", async ({ page }) => {
  // A teacher's own single-class cohort is not assigned to any coach (decided 3 Nov 2026, clean-up step C), so a coach who
  // opens the page sees no module counts for it and nothing that names the teacher. Counts and the date shift for a cohort a
  // coach is assigned to are covered by tests/modules/test_api.py and tests/api/test_identity_and_access.py.
  await trackStarted(page);
  await chooseRole(page, "coach");
  await page.goto("/#/cohort");
  await expect(page.locator("[data-testid^=coach-modules-]")).toHaveCount(0); // no module counts for a class that is not assigned to her
  const text = await page.locator("main").innerText();
  expect(text).not.toMatch(/[0-9a-f]{16}/); // no device id or other id
  expect(text).not.toContain(await page.evaluate(() => (JSON.parse(localStorage.getItem("cc.user") ?? "{}") as { id: string }).id)); // not her nickname
});

test("the feedback card has four answers with icons, and Send is closed until one is chosen", async ({ page }) => {
  await trackStarted(page);
  const card = page.getByTestId("module-1-feedback");
  await expect(card).toContainText("How did Module 1 go?");
  for (const a of ["worked", "partly", "not_yet", "not_tried"]) await expect(page.getByTestId(`module-1-fb-${a}`)).toBeVisible();
  await expect(card).toContainText("It worked");
  await expect(card).toContainText("It partly worked");
  await expect(card).toContainText("Not yet working");
  await expect(card).toContainText("I didn't try it yet");
  await expect(card).toContainText("A short note (optional, no names)");
  await expect(page.getByTestId("module-1-fb-send")).toBeDisabled();
  await page.getByTestId("module-1-fb-worked").check();
  await expect(page.getByTestId("module-1-fb-send")).toBeEnabled();
});

test("I didn't try it yet holds the module: one question, a shorter version, a way to ask, and the next module still works", async ({ page }) => {
  await trackStarted(page);
  await page.getByTestId("module-1-fb-not_tried").check();
  await page.getByTestId("module-1-fb-send").click();
  const hold = page.getByTestId("module-1-hold");
  await expect(hold).toContainText("Why not yet?");
  await expect(hold).toContainText("not counted as a result");
  for (const c of ["no_time", "materials", "not_sure", "absent", "other"]) await expect(page.getByTestId(`module-1-chip-${c}`)).toBeVisible();
  await page.getByTestId("module-1-chip-no_time").click();
  await expect(hold).toContainText("We noted: No time");
  await hold.getByText("Try a shorter version").click();
  await expect(page.getByTestId("module-1-short")).toBeVisible();
  await expect(page.getByTestId("module-1-ask")).toBeVisible();
  await expect(page.getByTestId("module-1-status")).not.toContainText("Done"); // the module stays open
  await expect(page.getByTestId("module-next")).toBeEnabled(); // always works for her
  const box = await page.getByTestId("module-1-chip-no_time").boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  const found = (await new AxeBuilder({ page }).include("[data-testid=module-track]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => v.id)).toEqual([]);
  for (const lang of ["hi", "ta"]) {
    await chooseLanguage(page, lang);
    await page.goto("/#/cohort");
    await expect(page.getByTestId("module-1-hold")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  }
});

// ---- Part C: the private check-in and sharing (written, not run) ------------------------------------------------

const mockCheckin = (chat: { available: boolean; open: boolean }, over: Record<string, unknown> = {}) => ({
  answer: "partly",
  note: "The children were quiet.",
  review: { state: "none", follow_ups: [], safety: false, changes: "Nothing changes: the plan stays as it is." },
  chat: { ...chat, reason: chat.available ? null : "no_peers", cohort_id: "co-1", unread: 2 },
  share: { shared: false, retracted: false, posted_text: null, fields: null, anonymous: null, can_share: chat.available, share_later_open: true, default_fields: { how: true, note: true, help: true, counts: false, name: false }, draft: "Module 1, Ask the child to explain her steps: it partly worked. Any ideas that could help?", ...over },
});

test("the check-in is private on every step, nothing is posted until she shares, and Don't share closes it", async ({ page }) => {
  await trackStarted(page);
  let posted = 0;
  await page.route("**/api/modules/tracks/*/modules/1/checkin/share*", (r) => {
    posted++;
    return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockCheckin({ available: true, open: true }, { shared: true, posted_text: "x" })) });
  });
  await page.route("**/api/modules/tracks/*/modules/1/checkin?*", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockCheckin({ available: true, open: true })) }));
  await page.getByTestId("module-1-fb-partly").check();
  await page.getByTestId("module-1-fb-send").click();
  await expect(page.getByTestId("checkin-private").first()).toContainText("Private: only you can see this. Nothing is shared unless you choose.");
  await page.getByTestId("module-1-share-open").click();
  await expect(page.getByTestId("module-1-share")).toContainText("Share a summary with your cohort?");
  await expect(page.getByTestId("module-1-share-text")).toHaveValue(/Module 1/);
  await expect(page.getByTestId("module-1-field-counts")).not.toBeChecked(); // counts and name are off by default
  await expect(page.getByTestId("module-1-field-name")).not.toBeChecked();
  for (const b of ["share-go", "share-edit", "share-no"]) expect((await page.getByTestId(`module-1-${b}`).boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44);
  expect(posted).toBe(0); // nothing was sent
  await page.getByTestId("module-1-share-no").click();
  await expect(page.getByTestId("module-1-share-closed")).toContainText("Not shared. Only you can see this check-in.");
  expect(posted).toBe(0);
  const found = (await new AxeBuilder({ page }).include("[data-testid=module-1-checkin]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
  expect(found.map((v) => v.id)).toEqual([]);
});

test("a cohort with no chat shows No peers yet and no Open cohort chat button", async ({ page }) => {
  await trackStarted(page);
  await page.route("**/api/modules/tracks/*/chat*", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ available: false, reason: "no_peers", cohort_id: null, open: false, unread: 0 }) }));
  await page.reload();
  await expect(page.getByTestId("open-chat-header-none")).toContainText("No peers yet");
  await expect(page.getByTestId("open-chat-header")).toHaveCount(0);
});

test("the Open cohort chat button has a badge for new posts and says new messages need a connection when offline", async ({ page, context }) => {
  await trackStarted(page);
  await page.route("**/api/modules/tracks/*/chat*", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ available: true, reason: null, cohort_id: "co-1", open: true, unread: 3 }) }));
  await page.reload();
  await expect(page.getByTestId("open-chat-header")).toContainText("Open cohort chat");
  await expect(page.getByTestId("open-chat-header-unread")).toContainText("3 new");
  await context.setOffline(true);
  await expect(page.getByTestId("open-chat-header-offline")).toContainText("New messages need a connection.");
  await context.setOffline(false);
});

test("a blocked share says what to remove, and the sharing step fits in Hindi and Tamil at 360 px", async ({ page }) => {
  await trackStarted(page);
  await page.route("**/api/modules/tracks/*/modules/1/checkin?*", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockCheckin({ available: true, open: true })) }));
  await page.route("**/api/modules/tracks/*/modules/1/checkin/share*", (r) => r.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ detail: { code: "blocked", problems: ["child_name"] } }) }));
  await page.getByTestId("module-1-fb-partly").check();
  await page.getByTestId("module-1-fb-send").click();
  await page.getByTestId("module-1-share-open").click();
  await page.getByTestId("module-1-share-go").click();
  await expect(page.getByTestId("module-1-share-problems")).toContainText("Please remove: a child's name");
  for (const lang of ["hi", "ta"]) {
    await chooseLanguage(page, lang);
    await page.goto("/#/cohort");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  }
});

test("a module's audio plays in the browser: no autoplay, play and pause, seek, speeds, a played event, and a copy for offline", async ({ page, context }) => {
  await trackStarted(page);
  await expect(page.getByTestId("module-1-player-audio")).toHaveCount(0); // nothing is made or played until she presses Listen
  await page.getByTestId("module-1-listen").click();
  await expect(page.getByTestId("module-1-toggle")).toBeVisible({ timeout: 45_000 });
  const audio = page.getByTestId("module-1-player-audio");
  const paused = () => audio.evaluate((a: HTMLAudioElement) => a.paused);
  expect(await paused()).toBe(true); // no autoplay
  await expect(page.getByTestId("module-1-time")).toContainText("0:00 /");
  await expect(page.getByTestId("module-1-seek")).toBeVisible();
  await page.getByTestId("module-1-speed-0.75").click();
  expect(await audio.evaluate((a: HTMLAudioElement) => a.playbackRate)).toBe(0.75);
  await page.getByTestId("module-1-speed-1.25").click();
  expect(await audio.evaluate((a: HTMLAudioElement) => a.playbackRate)).toBe(1.25);
  await page.getByTestId("module-1-speed-1").click();
  const played = page.waitForResponse((r) => r.url().includes("/modules/1/played") && r.request().method() === "POST");
  await page.getByTestId("module-1-toggle").click();
  expect((await played).ok()).toBe(true); // the first start is recorded on the module
  await expect.poll(paused).toBe(false);
  await page.getByTestId("module-1-toggle").click();
  await expect.poll(paused).toBe(true);
  await expect(page.getByTestId("module-1-save")).toBeVisible(); // Download sits next to the player
  await expect(page.getByTestId("module-1-kept")).toBeVisible(); // a copy is kept on the phone
  // offline: the kept copy plays with no signal
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("module-1-toggle")).toBeVisible({ timeout: 20_000 });
  await context.setOffline(false);
});
