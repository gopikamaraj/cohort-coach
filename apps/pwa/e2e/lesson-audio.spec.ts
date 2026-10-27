import { expect, test } from "@playwright/test";

// A lesson's voice note can be kept on the phone and then plays with no signal. The flow step and
// the audio file are served by the test (the real files come from the lesson route).
const AUDIO = "http://localhost:4173/__lesson/l1.ogg";
const LESSON = { step_id: "t4_lesson", kind: "message", text: "Lesson 1", buttons: [], url: null, url_label: null, audio: AUDIO, scene: null, alt: null };

test("save a lesson's audio, go offline, reload: it still plays from the phone", async ({ page, context }) => {
  await page.route("**/api/flow/current", (r) =>
    r.fulfill({
      json: {
        lang: "en",
        consent: null,
        messages: [LESSON],
      },
    }),
  );
  await page.route("**/__lesson/l1.ogg", (r) =>
    r.fulfill({ status: 200, contentType: "audio/ogg", body: Buffer.from("OggS-test-bytes") }),
  );
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/#/flow");
  await expect(page.getByTestId("flow-audio-save")).toBeVisible();
  await page.getByTestId("flow-audio-save").click();
  await expect(page.getByTestId("flow-audio-saved")).toBeVisible();
  expect(await page.getByTestId("flow-audio").getAttribute("src")).toMatch(/^blob:/);

  // no signal: the audio address no longer answers, and the page is reloaded
  await page.unroute("**/__lesson/l1.ogg");
  await page.route("**/__lesson/l1.ogg", (r) => r.abort());
  await page.reload();
  await expect(page.getByTestId("flow-audio-saved")).toBeVisible();
  expect(await page.getByTestId("flow-audio").getAttribute("src")).toMatch(/^blob:/);
  void context;
});

test("a refused download says so and leaves the online player", async ({ page }) => {
  await page.route("**/api/flow/current", (r) =>
    r.fulfill({ json: { lang: "en", consent: null, messages: [LESSON] } }),
  );
  await page.route("**/__lesson/l1.ogg", (r) => r.fulfill({ status: 403, body: "no" }));
  await page.goto("/#/flow");
  await page.getByTestId("flow-audio-save").click();
  await expect(page.getByRole("alert")).toContainText("Could not save it");
  expect(await page.getByTestId("flow-audio").getAttribute("src")).toBe(AUDIO);
});
