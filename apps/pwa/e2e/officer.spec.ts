import { expect, test, type Route } from "@playwright/test";

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
  await expect(page.getByText("Aggregates only")).toBeVisible();
});

test("the officer screen reads in Hindi and has no sideways scroll on a phone", async ({ page }) => {
  await page.getByTestId("lang").selectOption("hi");
  await expect(page.getByRole("heading", { name: "ट्रैक के नतीजे" })).toBeVisible();
  const wide = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(wide).toBe(false);
});
