import { type Route } from "@playwright/test";
import { expect, test } from "./test";
import { chooseLanguage } from "./switch";

// The officer's view (P12, reduced). The API is mocked here; the real numbers (engine verdicts,
// suppression under 5, no ids) are tested in tests/api/test_officer.py. This proves the screen shows
// what the server sends, with sources, verdict chips, an interval chart and the hidden-group text.

const json = (route: Route, body: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

test.beforeEach(async ({ page }) => {
  await page.route("**/api/officer/error-map", (r) =>
    json(r, {
      simulated: true,
      cells: [
        { medium: "hindi", error: "SUB-SFL", hidden: false, classes: 40, showing: 14, share_percent: 35 },
        { medium: "tamil", error: "SUB-SFL", hidden: true, classes: null },
      ],
    }),
  );
  await page.route("**/api/officer/results", (r) =>
    json(r, {
      note: "A failed track counts against the track, not the teacher.",
      tracks: [
        { version: "SUB-SFL v1", verdict: "working", hidden: false, reason: "x", confidence_note: null, estimate_points: -19.5, ci_low: -24.1, ci_high: -15.1, n_track: 21, n_comparison: 23 },
        { version: "SUB-NODEC v1", verdict: "not_working", hidden: false, reason: "x", confidence_note: null, estimate_points: -0.3, ci_low: -3.3, ci_high: 2.8, n_track: 18, n_comparison: 17 },
        { version: "PV-HEARD v1", verdict: "inconclusive", hidden: true, reason: "x", confidence_note: "from 3 classes, read as directional" },
      ],
    }),
  );
  await page.route("**/api/officer/funnel", (r) =>
    json(r, {
      rows: [
        {
          error: "SUB-SFL",
          delivered: { hidden: false, teachers: 8, source: "system: lessons sent" },
          tried: { hidden: true, teachers: null, source: "self-report: tapped Tried it in class" },
          outcomes: null,
          practised: { recorded: false, source: "system: not counted per cohort (sessions are metadata only)" },
          changed: { status: "awaiting next check", source: "next check, blind-scored counts" },
        },
      ],
    }),
  );
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("cc.role", "officer"));
  await page.goto("/#/officer");
  await page.reload();
});

test("the funnel shows each step with its source and Changed waits for the next check", async ({ page }) => {
  const f = page.getByTestId("funnel-SUB-SFL");
  await expect(f).toContainText("Delivered: 8 teachers");
  await expect(f).toContainText("system: lessons sent");
  await expect(f).toContainText("fewer than 5 teachers"); // Tried is hidden under 5
  await expect(f).toContainText("self-report");
  await expect(f).toContainText("not counted per cohort");
  await expect(f).toContainText("Changed: awaiting next check");
});

test("track results show the verdict, the interval and say a failed track counts against the track", async ({ page }) => {
  const r = page.getByTestId("results");
  await expect(r).toContainText("A failed track counts against the track, not the teacher.");
  await expect(page.getByTestId("track-SUB-SFL v1").getByTestId("verdict")).toHaveText("Working");
  await expect(page.getByTestId("track-SUB-NODEC v1").getByTestId("verdict")).toHaveText("Not working");
  await expect(page.getByTestId("track-SUB-NODEC v1")).toContainText("counts against the track, not the teachers");
  await expect(page.getByTestId("chart-SUB-SFL v1")).toBeVisible();
  await expect(page.getByTestId("track-SUB-SFL v1")).toContainText("-19.5 points");
  const small = page.getByTestId("track-PV-HEARD v1");
  await expect(small).toContainText("fewer than 5 classes");
  await expect(small).toContainText("from 3 classes, read as directional");
  await expect(page.getByTestId("chart-PV-HEARD v1")).toHaveCount(0);
});

test("the error map hides a cell under 5 classes, and the screen is labelled simulated", async ({ page }) => {
  const m = page.getByTestId("error-map");
  await expect(m).toContainText("35% (14/40)");
  await expect(m).toContainText("fewer than 5 classes");
  await expect(page.getByText(/simulated/i).first()).toBeVisible();
  // 5 Nov: hidden in the demo, where every minimum group size is off (the note is for production, where the sizes apply)
  await expect(page.getByText("Aggregates only")).toHaveCount(0);
});

test("the officer screen reads in Hindi and has no sideways scroll on a phone", async ({ page }) => {
  await chooseLanguage(page, "hi");
  await expect(page.getByRole("heading", { name: "ट्रैक के नतीजे" })).toBeVisible();
  const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(wide).toBe(false);
});

test("the officer proposes a cohort, activates it and closes it with the server's rules", async ({ page }) => {
  let cohorts: Array<Record<string, unknown>> = [];
  const posts: Array<{ path: string; body: Record<string, unknown> }> = [];
  await page.route("**/api/cohorts/officer/cohorts**", async (r) => {
    const req = r.request();
    if (req.method() === "GET") return json(r, cohorts);
    const body = JSON.parse(req.postData() ?? "{}") as Record<string, unknown>;
    posts.push({ path: new URL(req.url()).pathname, body });
    const m = /cohorts\/([^/]+)\/status$/.exec(req.url());
    if (!m) {
      cohorts = [{ id: "co-1", error: body["error"], status: "proposed", track_version: 1, schools: null, members: null, thread: "read_only", simulated: true }];
    } else {
      cohorts = cohorts.map((c) => (c["id"] === m[1] ? { ...c, status: body["to"] } : c));
    }
    return json(r, cohorts[0]);
  });
  await page.reload();
  await expect(page.getByTestId("officer-cohorts")).toContainText("No cohorts yet.");
  await page.getByTestId("cohort-error").selectOption("SUB-SFL");
  await page.getByTestId("cohort-create").click();
  await expect(page.getByTestId("cohort-co-1")).toContainText("Proposed");
  await expect(page.getByTestId("cohort-co-1")).toContainText("fewer than 5"); // a count under 5 is hidden
  expect(posts[0]?.body).toMatchObject({ error: "SUB-SFL", coach_id: "coach-demo" });
  await page.getByTestId("activate-co-1").click();
  await expect(page.getByTestId("cohort-co-1")).toContainText("Active");
  await page.getByTestId("closing-co-1").click();
  await expect(page.getByTestId("cohort-co-1")).toContainText("Closing");
  // closing without the post-test needs a reason
  await expect(page.getByTestId("close-without-co-1")).toBeDisabled();
  await page.getByTestId("reason-co-1").fill("school closed for exams");
  await page.getByTestId("close-without-co-1").click();
  await expect(page.getByTestId("cohort-co-1")).toContainText("Closed");
  expect(posts.at(-1)?.body).toMatchObject({ to: "closed", post_test_received: false, reason: "school closed for exams" });
});

test("a refused change shows what happened", async ({ page }) => {
  await page.route("**/api/cohorts/officer/cohorts**", (r) => (r.request().method() === "GET" ? json(r, []) : r.fulfill({ status: 409, contentType: "application/json", body: "{}" })));
  await page.reload();
  await page.getByTestId("cohort-create").click();
  await expect(page.getByTestId("cohort-failed")).toContainText("That did not work");
});

test("the funnel says how much content has waited for review", async ({ page }) => {
  await page.route("**/api/officer/funnel", (r) => json(r, { rows: [], review_waiting: { waiting: 3, over_7_days: 2, oldest_days: 9, source: "system: review queue ages; gates never auto-approve" } }));
  await page.reload();
  await expect(page.getByTestId("review-waiting")).toContainText("3 items, 2 for more than 7 days");
  await expect(page.getByTestId("review-waiting")).toContainText("system:");
});
