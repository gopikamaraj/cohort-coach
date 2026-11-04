import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { type Page } from "@playwright/test";
import { expect, test } from "./test";

// Practice Class speech (Prompt 3): the visible timer and the 25-second limit, the microphone fed
// from a file (a generated tone: never a voice), the recording format, and "voice is off" when the
// session's speech allowance is used. The API runs the stub speech service (SPEECH_MODE=stub) and
// replays recorded AI answers, so no paid call is made. Speech recognition itself is tested on the
// server with mock providers (tests/speech/test_practice_voice.py).

const here = path.dirname(fileURLToPath(import.meta.url));
const MIC = path.join(here, "fixtures", "tone-mic.wav");

test.use({
  launchOptions: {
    args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream", `--use-file-for-fake-audio-capture=${MIC}`],
  },
});

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => ((((u: (string | null)[]) => (localStorage.clear(), u[0] && localStorage.setItem("cc.user", u[0]), u[1] && localStorage.setItem("cc.cacheOwner", u[1])))([localStorage.getItem("cc.user"), localStorage.getItem("cc.cacheOwner")])), localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}')));
});

async function begin(page: Page, lang = "en") {
  await page.evaluate((l) => localStorage.setItem("cc.lang", l), lang);
  await page.goto("/#/practice?seed=5");
  await page.reload(); // a fresh screen, even when the hash did not change
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
}

async function pressTalk(page: Page) {
  const talk = page.getByTestId("talk");
  await expect(talk).toHaveAttribute("data-state", "idle");
  await talk.scrollIntoViewIfNeeded();
  const box = (await talk.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await expect(talk).toHaveAttribute("data-state", "listening");
}

test("a timer counts to 25 seconds, and at 25 the recording stops by itself and says why", async ({ page }) => {
  await page.clock.install();
  const sent: string[] = [];
  page.on("request", (r) => {
    if (/\/voice-turn$/.test(r.url())) sent.push(r.headers()["content-type"] ?? "");
  });
  await begin(page);
  await pressTalk(page);
  await page.clock.runFor(7_000);
  await expect(page.getByTestId("rec-timer")).toHaveText("7 of 25 seconds");
  await page.clock.runFor(18_500); // past 25 s while she still holds the button
  await expect(page.getByTestId("rec-limit")).toHaveText("That is the longest we can listen to at once. Say the rest in a second message.");
  await page.mouse.up();
  await expect.poll(() => sent.length).toBe(1); // what she said in those 25 s is still sent
  await expect(page.getByTestId("rec-timer")).toHaveCount(0);
});

test("the microphone recording goes out in a format the phone supports, and the reply comes back", async ({ page }) => {
  // the upload's file type, read where the app sends it (a Blob body is not visible to request events)
  await page.addInitScript(() => {
    const w = window as unknown as { __uploads: string[]; fetch: typeof fetch };
    w.__uploads = [];
    const real = w.fetch.bind(window);
    w.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/voice-turn") && init?.body instanceof FormData) {
        const f = init.body.get("audio");
        w.__uploads.push(f instanceof Blob ? f.type : "");
      }
      return real(input, init);
    };
  });
  await page.reload();
  await begin(page);
  const supported = await page.evaluate(() =>
    ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((m) => MediaRecorder.isTypeSupported(m)) ?? "",
  );
  await pressTalk(page);
  await page.waitForTimeout(1500);
  await page.mouse.up();
  await expect(page.getByTestId("reply-1")).toBeVisible();
  const uploads = await page.evaluate(() => (window as unknown as { __uploads: string[] }).__uploads);
  expect(uploads).toHaveLength(1);
  expect(uploads[0].split(";")[0]).toBe(supported.split(";")[0]); // sent as recorded; the server converts
});

test("when the session's speech allowance is used, voice turns off at once and typing carries on", async ({ page }) => {
  await page.route("**/voice-turn", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: { text_mode: true, voice_off: true, message: "Voice is off for the rest of this practice. The text continues." } }),
    }),
  );
  await begin(page);
  await pressTalk(page);
  await page.waitForTimeout(800);
  await page.mouse.up();
  await expect(page.getByTestId("say")).toBeVisible(); // one answer is enough: not a failure count
  await expect(page.getByText("Voice is off for the rest of this practice. The text continues.")).toBeVisible();
  await page.getByTestId("say").fill("Priya, what is 52 minus 29?");
  await page.getByTestId("send").click();
  await expect(page.getByTestId("reply-1")).toBeVisible();
});

test("the voice controls pass axe and fit at 360 px in Hindi and Tamil, timer showing", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await page.clock.install();
  for (const lang of ["hi", "ta"]) {
    await begin(page, lang);
    const talk = page.getByTestId("talk");
    await talk.focus(); // at 360 px, hold the button with the keyboard (Space), which it supports
    await page.keyboard.down(" ");
    await expect(talk).toHaveAttribute("data-state", "listening");
    await page.clock.runFor(3_000);
    await expect(page.getByTestId("rec-timer")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, lang).toBeLessThanOrEqual(1);
    const axe = await new AxeBuilder({ page }).include(".pcx-mic").analyze();
    expect(axe.violations.map((v) => v.id), lang).toEqual([]);
    await page.keyboard.up(" ");
    await expect(page.getByTestId("talk")).toHaveAttribute("data-state", "idle", { timeout: 20_000 });
  }
});
