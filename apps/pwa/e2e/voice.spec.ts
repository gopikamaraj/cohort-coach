import { expect, test, type Page } from "@playwright/test";

// Voice in the Practice Class, with a fake microphone (Chromium's own test tone) and the stub
// speech service on the API (SPEECH_MODE=stub: scripted transcripts, a generated tone). The AI
// side replays recordings, so no paid call is made. This proves the hold-to-speak flow and the
// fallback to typing; it does not prove speech recognition (that needs a live key and a phone).

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => ((localStorage.clear(), localStorage.setItem("cc.user", "{\"id\":\"e2e tester\",\"nickname\":\"e2e tester\"}"), localStorage.setItem("cc.cacheOwner", "e2e tester")), localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}')));
});

async function begin(page: Page) {
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
}

async function hold(page: Page, ms = 1200) {
  const talk = page.getByTestId("talk");
  await expect(talk).toHaveAttribute("data-state", "idle");
  await talk.scrollIntoViewIfNeeded(); // the mouse only reaches what is inside the viewport
  const box = (await talk.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await expect(talk).toHaveAttribute("data-state", "listening");
  await page.waitForTimeout(ms);
  await page.mouse.up();
}

test("hold to speak sends the recording and shows what was heard and the child's reply", async ({
  page,
}) => {
  const stages: unknown[] = [];
  page.on("response", async (r) => {
    if (/\/voice-turn$/.test(r.url()) && r.ok())
      stages.push(
        ((await r.json()) as { layers: { evaluation: { stages: unknown } } })
          .layers.evaluation.stages,
      );
  });
  await begin(page);
  await expect(page.getByTestId("talk")).toBeVisible();
  await expect(page.getByTestId("say")).toHaveCount(0);
  await hold(page);
  await expect(page.getByTestId("reply-1")).toBeVisible();
  await expect(page.getByTestId("turn-1")).toContainText(
    /bundles|explain|add it back|Well done/,
  ); // one of the stub's scripted lines
  await expect(page.getByTestId("talk")).toHaveAttribute("data-state", "idle");
  expect(stages).toHaveLength(1);
  expect(Object.keys(stages[0] as object).sort()).toEqual([
    "stt_ms",
    "tts_wait_ms",
  ]);
});

test("a very short tap is not sent: she is asked to hold and speak", async ({
  page,
}) => {
  let sent = 0;
  page.on("request", (r) => {
    if (/\/voice-turn$/.test(r.url())) sent += 1;
  });
  await begin(page);
  const talk = page.getByTestId("talk");
  await talk.scrollIntoViewIfNeeded(); // the mouse only reaches what is inside the viewport
  const box = (await talk.boundingBox())!;
  await page.mouse.move(box.x + 10, box.y + 10);
  await page.mouse.down();
  await expect(talk).toHaveAttribute("data-state", "listening");
  await page.mouse.up();
  await expect(page.getByRole("alert")).toContainText(/hold the button/i);
  expect(sent).toBe(0);
});

test("two voice failures switch to typing by themselves, and she can switch back", async ({
  page,
}) => {
  await page.route("**/voice-turn", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: { text_mode: true, message: "off" } }),
    }),
  );
  await begin(page);
  await hold(page);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByTestId("talk")).toBeVisible(); // one failure: still offered
  await hold(page);
  await expect(page.getByTestId("say")).toBeVisible(); // two: typing takes over
  await expect(page.getByRole("alert")).toContainText(/type instead/i);
  await page.getByTestId("say").fill("Priya, what is 52 minus 29?");
  await page.getByTestId("send").click();
  await expect(page.getByTestId("reply-1")).toBeVisible();
  await page.getByTestId("use-voice").click();
  await expect(page.getByTestId("talk")).toBeVisible();
});

test("a 2g link starts in typing mode, and her choice of typing is remembered", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "connection", {
      value: { effectiveType: "2g" },
      configurable: true,
    });
  });
  await page.reload(); // the init script only runs on a new document
  await begin(page);
  await expect(page.getByTestId("say")).toBeVisible();
  await expect(page.getByTestId("talk")).toHaveCount(0);
  await expect(page.getByTestId("use-voice")).toBeVisible();
});

test("choosing to type is remembered for the next rehearsal", async ({
  page,
}) => {
  await begin(page);
  await page.getByTestId("use-text").click();
  await expect(page.getByTestId("say")).toBeVisible();
  await page.reload();
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("say")).toBeVisible();
});
