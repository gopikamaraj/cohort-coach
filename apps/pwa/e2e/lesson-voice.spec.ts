import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

// Lesson audio (Prompt 2): the coach's review panel and the teacher's player. The lesson-audio API is
// mocked here (the real routes, roles, the rule for small cohorts and the audit rows are tested in
// tests/content/test_lesson_audio.py). The audio is a generated tone, never a voice.

const here = path.dirname(fileURLToPath(import.meta.url));
const MP3 = readFileSync(path.join(here, "fixtures", "tone-lesson.mp3"));
const SENTENCES = [
  "Today we look at 52 - 29.",
  "Meena writes 37.",
  "Ask her to show it with bundles of ten.",
  "Next week we check by adding back.",
  "23 + 29 = 52, so the answer holds.",
];
const TIMING = [
  { i: 0, start: 0, end: 1 },
  { i: 1, start: 1.25, end: 2 },
  { i: 2, start: 2.25, end: 3.5 },
  { i: 3, start: 4, end: 5 },
  { i: 4, start: 5.25, end: 6 },
];

interface State {
  status: string;
  revision: number;
  regen: unknown[];
}

const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

/** Serve the tone like a storage server does: with byte ranges, so the player can seek. */
function mp3(route: Route) {
  const range = /bytes=(\d+)-(\d*)/.exec(route.request().headers()["range"] ?? "");
  if (!range) return route.fulfill({ status: 200, contentType: "audio/mpeg", headers: { "accept-ranges": "bytes" }, body: MP3 });
  const start = Number(range[1]);
  const end = range[2] ? Number(range[2]) : MP3.length - 1;
  return route.fulfill({
    status: 206,
    contentType: "audio/mpeg",
    headers: { "accept-ranges": "bytes", "content-range": `bytes ${start}-${end}/${MP3.length}` },
    body: MP3.subarray(start, end + 1),
  });
}

async function mockReview(page: Page): Promise<State> {
  const s: State = { status: "unreviewed", revision: 1, regen: [] };
  const detail = () => ({
    id: `a${s.revision}`, part_id: "p1", track_id: "sub-sfl.v1", version: 1, language: "en", day: 1, revision: s.revision,
    provider: "bodhan", voice: "Kavya", style: "educational lecture", bytes: 1_234_000, seconds: 6, status: s.status,
    summary: { sentences: 5, checked: 5, passed: 4, flagged: 1 }, hidden: false, sentences: SENTENCES, timing: TIMING,
    checks: SENTENCES.map((_, i) => ({ i, cer: i === 2 ? 0.4 : 0.02, flagged: i === 2 })),
    audio_url: "http://127.0.0.1/lesson-a.mp3", sentence_costs_inr: [0.01, 0.01, 0.02, 0.01, 0.02],
  }); // fmt: skip
  await page.route("**/lesson-a.mp3", mp3);
  await page.route("**/api/review/**", async (route) => {
    const req = route.request();
    const p = new URL(req.url()).pathname.replace("/api/review", "");
    const role = req.headers()["x-role"];
    if (p === "/lesson-audio")
      return json(route, [
        { id: `a${s.revision}`, track_id: "sub-sfl.v1", language: "en", day: 1, revision: s.revision, status: s.status, provider: "bodhan", summary: detail().summary, hidden: false, bytes: 1_234_000, seconds: 6 },
        { id: "h1", track_id: "sub-sfl.v1", language: "hi", day: 2, revision: 1, status: "unreviewed", provider: "bodhan", summary: { sentences: 4, checked: 4, passed: 4, flagged: 0 }, hidden: true, bytes: 0, seconds: 0 },
      ]);
    if (p === "/lesson-audio/h1") return json(route, { id: "h1", part_id: "p2", track_id: "sub-sfl.v1", version: 1, language: "hi", day: 2, revision: 1, provider: "bodhan", voice: "Kavya", status: "unreviewed", summary: { sentences: 4, checked: 4, passed: 4, flagged: 0 }, hidden: true, bytes: 0, seconds: 0 });
    if (p.startsWith("/lesson-audio/a") && p.endsWith("/regenerate")) {
      if (role !== "coach") return json(route, { detail: "no" }, 403);
      s.regen.push(JSON.parse(req.postData() ?? "{}"));
      s.revision += 1;
      s.status = "unreviewed";
      return json(route, detail());
    }
    if (p.startsWith("/lesson-audio/a") && p.endsWith("/approve")) {
      if (role !== "coach") return json(route, { detail: "no" }, 403);
      s.status = "approved";
      return json(route, detail());
    }
    if (p.startsWith("/lesson-audio/a")) return json(route, detail());
    return json(route, []); // the queue, versions and audit are empty here
  });
  return s;
}

async function asRole(page: Page, role: string, lang = "en") {
  await page.goto("/");
  await page.evaluate(([r, l]) => {
    localStorage.setItem("cc.role", r);
    localStorage.setItem("cc.lang", l);
  }, [role, lang]);
}

async function playAt(page: Page, testId: string, seconds: number) {
  await page.getByTestId(testId).evaluate(async (el, t) => {
    const a = el as HTMLAudioElement;
    if (a.preload !== "none" && a.readyState < 1) {
      // a player that loads its metadata would reset a time set before the metadata arrives
      await new Promise((ok) => a.addEventListener("loadedmetadata", ok, { once: true }));
    }
    const loaded = a.readyState >= 1;
    const seeked = new Promise((ok) => a.addEventListener("seeked", ok, { once: true }));
    a.currentTime = t;
    if (loaded) await seeked; // a loaded player reports the new time once the seek is done
    a.dispatchEvent(new Event("timeupdate"));
  }, seconds);
}

test("the coach hears a lesson with its script highlighted, sees the flagged sentence, regenerates one sentence and approves", async ({ page }) => {
  const s = await mockReview(page);
  await asRole(page, "coach");
  await page.goto("/#/review");
  const panel = page.getByTestId("lesson-audio-review");
  await expect(panel).toBeVisible();
  await page.getByTestId("laudio-open-1-en").click();
  await expect(page.getByTestId("laudio-summary")).toHaveText("4 of 5 sentences passed the check; 1 to listen to");
  await expect(page.getByTestId("laudio-meta")).toContainText("bodhan, voice Kavya, 1.2 MB, 6 seconds");
  await expect(page.getByTestId("laudio-meta")).toContainText("AI-generated voice");
  await expect(page.getByTestId("laudio-flag-2")).toBeVisible();
  await expect(page.getByTestId("laudio-flag-1")).toHaveCount(0);
  await playAt(page, "laudio-audio", 2.5);
  await expect(page.getByTestId("laudio-sentence-2")).toHaveAttribute("aria-current", "true");
  await expect(page.getByTestId("laudio-sentence-1")).not.toHaveAttribute("aria-current", "true");
  await expect(page.getByTestId("laudio-regen-2")).toContainText("about INR 0.02");
  await page.getByTestId("laudio-regen-2").click();
  await expect(page.getByTestId("laudio-msg")).toContainText("Teachers keep hearing the approved one");
  expect(s.regen).toEqual([{ sentence: 2 }]);
  await page.getByTestId("laudio-approve").click();
  await expect(page.getByTestId("laudio-msg")).toContainText("Teachers now hear this version");
  await expect(page.getByTestId("laudio-approve")).toBeDisabled();
  const axe = await new AxeBuilder({ page }).include('[data-testid="lesson-audio-review"]').analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);
});

test("a lesson from a cohort of fewer than 5 classes shows no script and no audio", async ({ page }) => {
  await mockReview(page);
  await asRole(page, "coach");
  await page.goto("/#/review");
  await page.getByTestId("laudio-open-2-hi").click();
  await expect(page.getByTestId("laudio-hidden")).toContainText("fewer than 5 classes");
  await expect(page.getByTestId("laudio-audio")).toHaveCount(0);
  await expect(page.getByTestId("laudio-regen-lesson")).toHaveCount(0);
});

test("the officer can listen but has no regenerate or approve buttons", async ({ page }) => {
  await mockReview(page);
  await asRole(page, "officer");
  await page.goto("/#/review");
  await page.getByTestId("laudio-open-1-en").click();
  await expect(page.getByTestId("laudio-audio")).toBeVisible();
  await expect(page.getByTestId("laudio-regen-2")).toHaveCount(0);
  await expect(page.getByTestId("laudio-approve")).toHaveCount(0);
});

async function mockLesson(page: Page) {
  await page.route("**/lesson-t.mp3", mp3);
  await page.route("**/api/flow/current", (route) =>
    json(route, {
      flow: "t4", lang: "en", messages: [{
        step_id: "lesson", kind: "media", text: `Lesson 1 of 6\n\n${SENTENCES.join(" ")}`, buttons: [{ id: "next", label: "I listened" }],
        url: null, url_label: null, audio: "http://127.0.0.1/lesson-t.mp3", scene: null, alt: null,
        audio_info: { bytes: 1_234_000, seconds: 6, sentences: SENTENCES, timing: TIMING, ai_voice: true },
      }],
    }),
  ); // fmt: skip
}

test("the teacher's player says the voice is AI-generated, shows the file size, and follows the text", async ({ page }) => {
  await mockLesson(page);
  await asRole(page, "teacher");
  await page.goto("/#/flow");
  await expect(page.getByTestId("flow-ai-voice")).toHaveText("AI-generated voice");
  await expect(page.getByTestId("flow-audio-save")).toContainText("(1.2 MB)");
  await expect(page.getByTestId("flow-lesson")).toContainText("Lesson 1 of 6");
  await expect(page.getByTestId("flow-sentence-0")).toHaveText("Today we look at 52 - 29.");
  await playAt(page, "flow-audio", 4.2);
  await expect(page.getByTestId("flow-sentence-3")).toHaveAttribute("aria-current", "true");
  await playAt(page, "flow-audio", 3.75); // the pause between sections: nothing highlighted
  await expect(page.locator('[data-testid^="flow-sentence-"][aria-current="true"]')).toHaveCount(0);
  const axe = await new AxeBuilder({ page }).include('[data-testid="flow-lesson"]').analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);
});

test("Hindi and Tamil fit at 360 px in the review panel and the player", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await mockReview(page);
  await mockLesson(page);
  for (const lang of ["hi", "ta"]) {
    await asRole(page, "coach", lang);
    await page.goto("/#/review");
    await page.getByTestId("laudio-open-1-en").click();
    await expect(page.getByTestId("laudio-summary")).toBeVisible();
    let overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `review ${lang}`).toBeLessThanOrEqual(1);
    await asRole(page, "teacher", lang);
    await page.goto("/#/flow");
    await expect(page.getByTestId("flow-ai-voice")).toBeVisible();
    overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `player ${lang}`).toBeLessThanOrEqual(1);
  }
});
