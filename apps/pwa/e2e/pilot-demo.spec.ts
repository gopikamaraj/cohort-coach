import { expect, test, type Page } from "@playwright/test";

// The pilot class's sheets in the demo studio (Enter check no longer offers them: one flow, no data source). The server side (404 without the folder, consent and
// PILOT_DEMO=1; no-store headers; no AI call on auto-fill) is tested in tests/pilot_demo. Here the
// routes are stood in for with a FAKE class of five rolls and a 1-pixel picture, to test the screen:
// nothing shows on a machine without the folder, a reason shows when it is not ready, and when ready
// the first roll is read by the AI, the rest auto-fill with labels, the drawer shows the banner and
// the sheet, and nothing is stored. The demo never offers these sheets.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const PIXEL = Buffer.from("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=", "base64");
const FIRST = ["346", "728", "85", "74", "82", "35", "38", "26", "43", "54"];
const cells = (texts: string[]) => texts.map((text) => ({ text, status: "ok", confidence: 0.97 }));

const MANIFEST = {
  pilot: true,
  banner: "Pilot data: real sheets, roll numbers only",
  test: { name: "Pilot pre-test", form: "A", kind: "pre", date: "2026-10-23", paper_version: "pilot-form-a" },
  classes: [
    {
      class_code: "3A",
      teacher_label: "T1",
      strength: 5,
      test_date: "2026-10-23",
      dictation_override: false,
      rolls: [
        { roll: 1, status: "entered", has_image: true, in_answer_file: true },
        { roll: 2, status: "entered", has_image: true, in_answer_file: true },
        { roll: 3, status: "entered", has_image: true, in_answer_file: true },
        { roll: 4, status: "absent", has_image: false, in_answer_file: false },
        { roll: 5, status: "no_sheet", has_image: false, in_answer_file: false },
      ],
    },
    { class_code: "3B", teacher_label: "T2", strength: 3, test_date: "2026-10-23", dictation_override: true, rolls: [] },
  ],
  ai_reads: 0,
  ai_reads_cap: 6,
};

async function fresh(page: Page) {
  await page.goto("/");
  await page.evaluate((c) => {
    localStorage.clear();
    localStorage.setItem("cc.consent", c);
    localStorage.setItem("cc.role", "teacher");
    localStorage.setItem("cc.lang", "en");
  }, CONSENT);
}

async function mockPilot(page: Page, seen: string[]) {
  const json = (body: unknown) => ({ status: 200, contentType: "application/json", headers: { "Cache-Control": "no-store" }, body: JSON.stringify(body) });
  await page.route("**/api/pilot-data/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace("/api/pilot-data", "");
    seen.push(`${route.request().method()} ${path}`);
    if (path === "/manifest") return route.fulfill(json(MANIFEST));
    if (path.startsWith("/sheet/")) return route.fulfill({ status: 200, contentType: "image/jpeg", headers: { "Cache-Control": "no-store" }, body: PIXEL });
    if (path === "/read") return route.fulfill(json({ source: "ai", label: "Read by AI", cells: cells(FIRST), ai_reads: 1, ai_reads_cap: 6 }));
    if (path === "/autofill") {
      return route.fulfill(
        json({
          label: "Read from pilot answer file",
          sheets: [
            { roll: 2, cells: cells(FIRST), verified: true, has_image: true },
            { roll: 3, cells: cells(FIRST), verified: false, has_image: true },
          ],
          no_sheet: [5],
          unread: [],
          absent: [4],
        }),
      );
    }
    return route.fulfill({ status: 404, body: "{}" });
  });
}

// the flow: a paper is made on Papers, then Enter check chooses it (its own answer key comes with it)
async function enterCheckA(page: Page) {
  await page.goto("/#/papers");
  await page.getByTestId("papers-create").click();
  await page.getByTestId("route-rules").click();
  await page.getByTestId("paper-make").click();
  await expect(page.getByTestId("paper-view")).toBeVisible({ timeout: 30_000 });
  await page.goto("/#/check");
  await page.getByTestId("check-class-name").fill("3A Class");
  await page.getByTestId("check-expected").fill("2");
  await page.getByTestId("start-check-go").click();
  await expect(page.getByTestId("check-label")).toBeVisible();
}

test("on a machine without the pilot folder the judge sees Synthetic only", async ({ page }) => {
  await fresh(page);
  await page.goto("/#/demo?step=4");
  await expect(page.getByTestId("demo-entry")).toBeVisible();
  await expect(page.getByTestId("pilot-source")).toHaveCount(0);
  await expect(page.getByTestId("pilot-banner")).toHaveCount(0);
});

test("the demo never offers the pilot's sheets, even where the folder is there", async ({ page }) => {
  const seen: string[] = [];
  await fresh(page);
  await mockPilot(page, seen);
  await page.goto("/#/demo?step=4");
  await expect(page.getByTestId("demo-entry")).toBeVisible();
  await expect(page.getByTestId("pilot-source")).toHaveCount(0);
  await expect(page.getByTestId("pilot-banner")).toHaveCount(0);
  expect(seen).toEqual([]);
});

test("Enter check never offers the pilot's sheets, even where the folder is there", async ({ page }) => {
  const seen: string[] = [];
  await fresh(page);
  await mockPilot(page, seen);
  await enterCheckA(page);
  await expect(page.getByTestId("pilot-data-card")).toHaveCount(0);
  await expect(page.getByTestId("demo-entry")).toHaveCount(0);
  expect(seen).toEqual([]); // the page never even asks whether the folder is there
});
