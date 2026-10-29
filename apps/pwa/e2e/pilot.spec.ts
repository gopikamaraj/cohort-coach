import { expect, test, type Page, type Route } from "@playwright/test";

// Pilot mode on a phone: the server says it is in pilot mode, so the app shows sign-in and two pages
// and nothing else. The API is mocked here (the real routes are tested in tests/pilot); this proves
// the phone's side: the redirect, the consent gate, the upload queue and its statuses, offline
// queueing, the stepper, the approval-gated card actions and the share fallback.

const JPEG = Buffer.from(
  "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=",
  "base64",
);

interface State {
  audioCount: number;
  uploads: number;
  generated: boolean;
  cards: Record<string, unknown>[];
  calls: string[];
  shares: string[];
}

function card(slot: number, status: string, over: Record<string, unknown> = {}) {
  return {
    id: `a${slot}`,
    slot,
    language: "en",
    version: 1,
    title: `Lesson ${slot}: What to look for`,
    script: "Lesson one. Ask the child how they got the answer.",
    voice: "ritu",
    status,
    note: null,
    duration_s: 62,
    bytes: 500_000,
    active: true,
    stale: false,
    ready: status === "audio_ready",
    shareable: status === "approved" || status === "audio_ready",
    file_name: `cc-pilot-slot${slot}-en.m4a`,
    mime: "audio/mp4",
    created_at: "2026-10-23T10:00:00Z",
    shared_with: [],
    versions: [{ id: `a${slot}`, version: 1, status, ready: status === "audio_ready" }],
    ...over,
  };
}

async function mockApi(page: Page, roles: string[] = ["coordinator", "coach"]): Promise<State> {
  const s: State = { audioCount: 3, uploads: 0, generated: false, cards: [], calls: [], shares: [] };
  const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  await page.route("**/api/health", (r) => json(r, { status: "ok", version: "t", pilot: true }));
  await page.route("**/api/pilot/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace("/api/pilot", "");
    s.calls.push(`${req.method()} ${path}`);
    if (path === "/auth/signin") {
      const body = req.postDataJSON() as { key: string };
      return body.key === "good" ? json(route, { token: "tok", name: "ops", roles }) : json(route, { detail: "no" }, 401);
    }
    if (path === "/config")
      return json(route, {
        audio_count: s.audioCount,
        audio_default: 3,
        audio_max: 10,
        retention_days: 90,
        retention_range: [7, 365],
        languages: ["en", "hi", "ta"],
        voices: [{ id: "ritu", label: "Ritu", kind: "female" }],
        voice_default: "ritu",
        share_link_hours: 24,
      });
    if (path === "/config/audio-count") {
      s.audioCount = (req.postDataJSON() as { audio_count: number }).audio_count;
      return json(route, { audio_count: s.audioCount });
    }
    if (path === "/sheets/summary") return json(route, { uploaded: s.uploads, read: s.uploads, needs_look: 0, waiting: 0, teachers: ["T-101"], schools: ["SCH-01"] });
    if (path === "/sheets/init") return json(route, { id: `s${++s.uploads}`, duplicate: false, upload: { url: "/api/pilot/blob/token", headers: { "Content-Type": "image/jpeg" } } });
    if (path === "/blob/token") return route.fulfill({ status: 200, body: "" });
    if (/\/sheets\/s\d+\/complete/.test(path)) return json(route, { id: "s1", status: "stored" });
    if (path === "/audio")
      return json(route, { cards: s.cards, audio_count: s.audioCount, sheets_read: s.generated || s.cards.length ? 20 : s.uploads ? 20 : 0, classes_read: 1 });
    if (path === "/audio/generate") {
      s.generated = true;
      s.cards = [1, 2, 3].map((n) => card(n, "needs_review"));
      return json(route, { made: 3 });
    }
    const lessonAudio = /^\/lesson\/([\w.-]+)\/audio$/.exec(path);
    if (lessonAudio) {
      s.calls.push("voice");
      return json(route, { url: "https://store.example/lesson.m4a?sig=1", file_name: "cc-pilot-slot1-en.m4a", mime: "audio/mp4", seconds: 28, bytes: 115000 });
    }
    const lessonPage = /^\/lesson\/([\w.-]+)$/.exec(path);
    if (lessonPage) {
      if (lessonPage[1] === "ENDED-TOKEN-0000") return json(route, { detail: "ended" }, 404);
      return json(route, { title: "Lesson 1: What to look for", script: "Lesson one. Ask the child how they got the answer.", language: "en", slot: 1, audio_ready: false, seconds: 0, bytes: 0, mime: "audio/mp4" });
    }
    const act = /\/audio\/(a\d)\/([\w-]+)/.exec(path);
    if (act && act[2] === "approve") {
      s.cards = s.cards.map((c) => (c["id"] === act[1] ? card(Number(String(act[1]).slice(1)), "approved") : c));
      return json(route, { id: act[1], status: "approved" });
    }
    if (act && act[2] === "render") {
      s.cards = s.cards.map((c) => (c["id"] === act[1] ? card(Number(String(act[1]).slice(1)), "audio_ready") : c));
      return json(route, { id: act[1], status: "audio_ready" });
    }
    if (act && act[2] === "file") return route.fulfill({ status: 200, contentType: "audio/mp4", body: "FAKE-AUDIO" });
    if (act && act[2] === "lesson-link") return json(route, { url: "https://app.example/#/lesson/LESSON-TOKEN-1234", expires_in_days: 14 });
    if (act && act[2] === "shares") {
      s.shares.push(String(act[1]));
      return json(route, { recorded: 1 });
    }
    return json(route, { detail: "not mocked" }, 404);
  });
  return s;
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/#/home");
  await page.reload();
  await page.getByLabel("Name").fill("ops");
  await page.getByLabel("Key").fill("good");
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("pilot mode: sign-in, two pages, and every other address goes to Upload sheets", async ({ page }) => {
  await mockApi(page);
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Upload sheets" })).toBeVisible();
  await expect(page.locator(".p-nav a")).toHaveCount(2);
  for (const hash of ["#/home", "#/practice", "#/coach", "#/judge", "#/roles", "#/admin", "#/tour/1"]) {
    await page.evaluate((h) => (window.location.hash = h), hash);
    await expect(page).toHaveURL(/#\/upload$/);
    await expect(page.getByRole("heading", { name: "Upload sheets" })).toBeVisible();
  }
  await page.getByTestId("nav-audio").click();
  await expect(page.getByRole("heading", { name: "Intervention audio" })).toBeVisible();
});

test("a wrong key says so and does not sign in", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByLabel("Name").fill("ops");
  await page.getByLabel("Key").fill("bad");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toContainText("not right");
});

test("sheets cannot be added until consent is confirmed, then they upload and show their status", async ({ page }) => {
  const s = await mockApi(page);
  await signIn(page);
  await expect(page.getByRole("heading", { name: "Roll numbers, not names" })).toBeVisible();
  await expect(page.getByText("Ask schools to write roll numbers, not names, on the sheets")).toBeVisible();
  await expect(page.getByTestId("choose-files")).toBeDisabled();
  await page.getByTestId("school-code").fill("SCH-01");
  await page.getByTestId("class-code").fill("3A");
  await page.getByTestId("teacher-code").fill("T-101");
  await expect(page.getByTestId("choose-files")).toBeDisabled(); // codes alone are not enough
  await page.getByTestId("consent-confirm").check();
  await page.getByTestId("consent-ref").fill("HM-LETTER-1");
  await expect(page.getByTestId("choose-files")).toBeEnabled();
  await page.getByTestId("file-input").setInputFiles([
    { name: "a.jpg", mimeType: "image/jpeg", buffer: JPEG },
    { name: "b.jpg", mimeType: "image/jpeg", buffer: Buffer.concat([JPEG, Buffer.from("b")]) },
  ]);
  await expect(page.getByTestId("upload-list").locator("li[data-status='stored']")).toHaveCount(2);
  expect(s.uploads).toBe(2);
  // no file name was kept or shown
  await expect(page.getByTestId("upload-list")).not.toContainText("a.jpg");
  await expect(page.getByTestId("sheet-counts")).toContainText("Uploaded");
});

test("with no signal a sheet waits in the queue, then uploads when the signal returns", async ({ page, context }) => {
  const s = await mockApi(page);
  await signIn(page);
  await page.getByTestId("school-code").fill("SCH-01");
  await page.getByTestId("class-code").fill("3A");
  await page.getByTestId("teacher-code").fill("T-101");
  await page.getByTestId("consent-confirm").check();
  await page.getByTestId("consent-ref").fill("HM-LETTER-1");
  await page.evaluate(() => localStorage.setItem("cc.forcedOffline", "1"));
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await page.getByTestId("file-input").setInputFiles({ name: "a.jpg", mimeType: "image/jpeg", buffer: JPEG });
  await expect(page.getByTestId("upload-list").locator("li[data-status='queued']")).toHaveCount(1);
  expect(s.uploads).toBe(0);
  await page.evaluate(() => localStorage.setItem("cc.forcedOffline", "0"));
  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(page.getByTestId("upload-list").locator("li[data-status='stored']")).toHaveCount(1);
});

test("the audio page: empty state, stepper, generate, approval gates sharing; audio comes later", async ({ page }) => {
  const s = await mockApi(page);
  await signIn(page);
  await page.getByTestId("nav-audio").click();
  await expect(page.getByTestId("empty-state")).toContainText("No sheets read yet");
  await expect(page.getByTestId("generate")).toBeDisabled();
  s.uploads = 3; // sheets exist now
  await page.reload();
  await expect(page.getByTestId("count-value")).toHaveText("3");
  await page.getByTestId("count-dec").click();
  await expect(page.getByTestId("count-value")).toHaveText("2");
  await page.getByTestId("count-inc").click();
  await page.getByTestId("count-inc").click();
  await expect(page.getByTestId("count-value")).toHaveText("4");
  await page.getByTestId("count-dec").click();
  await page.getByTestId("generate").click();
  const first = page.getByTestId("card-1");
  await expect(first).toHaveAttribute("data-status", "needs_review");
  await expect(first.getByTestId("download")).toHaveCount(0); // not approved: no Download, no Share
  await expect(first.getByTestId("share")).toHaveCount(0);
  await expect(first).toContainText("Only approved lessons can be shared.");
  await first.getByText("Script").click();
  await expect(first).toContainText("Ask the child how they got the answer");
  await first.getByTestId("approve").click();
  // approving the words makes no audio: the link can be shared, the voice is paid for later
  await expect(first).toHaveAttribute("data-status", "approved");
  await expect(first.getByTestId("share")).toBeVisible();
  await expect(first.getByTestId("text-only")).toContainText("The audio is made when a teacher first taps");
  await expect(first.getByTestId("download")).toHaveCount(0);
  await expect(first.getByTestId("play")).toHaveCount(0);
  // the main action is Share; making the audio now is optional, so it waits under More options
  await expect(first.getByTestId("make-audio")).toBeHidden();
  await first.getByTestId("more").locator("summary").click();
  await first.getByTestId("make-audio").click();
  await expect(first).toHaveAttribute("data-status", "audio_ready");
  await expect(first.getByTestId("play")).toBeVisible();
  await expect(first.getByTestId("download")).toBeVisible(); // More stays open while she works
});

test("when the phone cannot share, Copy link and Open WhatsApp carry the lesson link", async ({ page }) => {
  const s = await mockApi(page);
  s.cards = [card(1, "approved"), card(2, "approved"), card(3, "approved")];
  s.generated = true;
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "canShare", { value: undefined, configurable: true });
    Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
    (window as unknown as { __opened: string[] }).__opened = [];
    window.open = (url?: string | URL) => {
      (window as unknown as { __opened: string[] }).__opened.push(String(url));
      return null;
    };
  });
  await signIn(page);
  await page.getByTestId("nav-audio").click();
  const first = page.getByTestId("card-1");
  await expect(first.getByTestId("share-fallback")).toHaveCount(0); // not until she taps Share
  await first.getByTestId("share").click();
  await expect(first.getByTestId("share-fallback")).toBeVisible();
  await expect(first.getByTestId("copy-link")).toBeVisible();
  await expect(first.getByTestId("open-whatsapp")).toBeVisible();
  await first.getByTestId("open-whatsapp").click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { __opened: string[] }).__opened.length)).toBe(1);
  const [opened] = await page.evaluate(() => (window as unknown as { __opened: string[] }).__opened);
  expect(opened).toContain("https://wa.me/?text=");
  expect(decodeURIComponent(opened ?? "")).toContain("https://app.example/#/lesson/LESSON-TOKEN-1234");
  expect(decodeURIComponent(opened ?? "")).toContain("lesson 1");
});

test("sharing with the share sheet sends the lesson link and then asks who received it", async ({ page }) => {
  const s = await mockApi(page);
  s.cards = [card(1, "approved"), card(2, "approved"), card(3, "approved")];
  s.generated = true;
  await page.addInitScript(() => {
    (window as unknown as { __shared: unknown[] }).__shared = [];
    Object.defineProperty(navigator, "share", {
      value: async (d: ShareData) => {
        (window as unknown as { __shared: unknown[] }).__shared.push({ url: d.url, text: d.text, files: d.files?.length ?? 0 });
      },
      configurable: true,
    });
  });
  await signIn(page);
  await page.getByTestId("nav-audio").click();
  await page.getByTestId("card-2").getByTestId("share").click();
  const read = () => page.evaluate(() => (window as unknown as { __shared: { url: string; text: string; files: number }[] }).__shared);
  await expect.poll(async () => (await read()).length).toBe(1);
  const shared = await read();
  expect(shared[0]?.url).toBe("https://app.example/#/lesson/LESSON-TOKEN-1234");
  expect(shared[0]?.files).toBe(0); // a link, not a file: no audio was made to send it
  expect(shared[0]?.text).toContain("lesson 2");
  const log = page.getByTestId("share-log");
  await expect(log).toContainText("does not show that anyone received");
  await log.getByLabel("T-101").check();
  await log.getByTestId("log-save").click();
  await expect.poll(() => s.shares).toEqual(["a2"]);
  await page.getByTestId("share-all").click();
  await expect(page.getByTestId("share-log")).toBeVisible();
});

test("the audio page works in Hindi and Tamil", async ({ page }) => {
  await mockApi(page);
  await signIn(page);
  await page.getByRole("button", { name: "हिं" }).click();
  await expect(page.getByRole("heading", { name: "पत्रक अपलोड करें" })).toBeVisible();
  await page.getByRole("button", { name: "தமி" }).click();
  await expect(page.getByRole("heading", { name: "தாள்களைப் பதிவேற்று" })).toBeVisible();
});

test("the pilot pages have no horizontal scroll and 44 px targets on a phone", async ({ page }) => {
  const s = await mockApi(page);
  s.cards = [card(1, "audio_ready")];
  s.generated = true;
  await signIn(page);
  for (const tab of ["nav-upload", "nav-audio"]) {
    await page.getByTestId(tab).click();
    const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(wide).toBe(false);
    const small = await page.evaluate(() =>
      [...document.querySelectorAll<HTMLElement>("button, a, .p-check, .p-checks label, select")]
        .filter((e) => e.offsetParent !== null && !e.closest("[aria-hidden=true]"))
        .map((e) => ({ t: e.textContent?.trim().slice(0, 20) ?? "", h: Math.round(e.getBoundingClientRect().height) }))
        .filter((x) => x.h < 44 && x.h > 0),
    );
    expect(small).toEqual([]);
  }
});

test("a teacher opens a lesson link with no sign-in, reads it, and the first tap makes the audio", async ({ page }) => {
  const s = await mockApi(page);
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  // the real store answers with Content-Disposition: attachment, so the page stays put while it saves
  await page.route("https://store.example/**", (r) => r.fulfill({ status: 200, contentType: "audio/mp4", headers: { "Content-Disposition": 'attachment; filename="cc-pilot-slot1-en.m4a"' }, body: "FAKE" }));
  await page.goto("/#/lesson/LESSON-TOKEN-1234");
  await page.reload();
  await expect(page.getByTestId("lesson-card")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Lesson 1: What to look for" })).toBeVisible();
  await expect(page.getByTestId("lesson-text")).toContainText("Ask the child how they got the answer");
  await expect(page.getByTestId("lesson-badge")).toContainText("Checked");
  await expect(page.locator(".p-nav")).toHaveCount(0); // none of the staff pages, no sign-in
  await expect(page.getByLabel("Key")).toHaveCount(0);
  expect(s.calls.filter((c) => c === "voice")).toHaveLength(0); // opening the page made no audio
  await page.getByTestId("lesson-download").click();
  await expect(page.getByTestId("lesson-audio")).toBeVisible();
  expect(s.calls.filter((c) => c === "voice")).toHaveLength(1);
  expect(s.calls.some((c) => c.includes("/auth/") || c.includes("/sheets"))).toBe(false);
});

test("a lesson link that has ended says so and shows nothing else", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/#/lesson/ENDED-TOKEN-0000");
  await page.reload();
  await expect(page.getByTestId("lesson-ended")).toContainText("This link has ended or is not right");
  await expect(page.getByTestId("lesson-card")).toHaveCount(0);
});
