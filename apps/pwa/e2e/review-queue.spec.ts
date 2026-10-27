import { expect, test, type Page, type Route } from "@playwright/test";

// P3: the review queue and the two keys. The API is mocked here (the real routes, the gates and the
// audit rows are tested in tests/content); this proves the screen: what it lists, what a return
// needs, that a coach's key alone switches nothing on, and that the audit shows both keys.

interface QState {
  itemStatus: string;
  versionStatus: string;
  audit: { role: string; action: string }[];
  rejects: unknown[];
  edits: string[];
}

async function mockQueue(page: Page): Promise<QState> {
  const s: QState = { itemStatus: "pending", versionStatus: "in_review", audit: [], rejects: [], edits: [] };
  const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  const detail = () => ({
    item_id: "i1", status: s.itemStatus, badge: "checked", language: "hi", kind: "lesson", day: 3,
    script: "Lesson three. Open one bundle.", original_script: null,
    results: [
      { name: "arithmetic", ok: true, codes: [], details: [] },
      { name: "prefilter", ok: true, codes: [], details: [] },
      { name: "checker", ok: false, codes: ["tone"], details: [] },
    ],
    slots_used: [], strategies: [], explanation: "Held for a person to read.", content_status: "held_by_checker", method_card_id: null, history: [],
  }); // fmt: skip
  await page.route("**/api/review/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname.replace("/api/review", "");
    const role = req.headers()["x-role"];
    if (path === "/items") return json(route, [{ item_id: "i1", content_type: "lesson", language: "hi", kind: "lesson", day: 3, status: s.itemStatus, age_hours: 50, explanation: "", track_id: "sub-sfl" }]);
    if (path === "/items/i1") return json(route, detail());
    if (path === "/items/i1/approve") {
      if (role !== "coach") return json(route, { detail: "no" }, 403);
      s.itemStatus = "approved";
      s.audit.unshift({ role: "coach", action: "item_approved" });
      return json(route, detail());
    }
    if (path === "/items/i1/reject") {
      s.rejects.push(req.postDataJSON());
      s.itemStatus = "rejected";
      return json(route, detail());
    }
    if (path === "/items/i1/edit") {
      const script = (req.postDataJSON() as { script: string }).script;
      if (script.includes("37")) return json(route, { detail: { codes: ["arithmetic_wrong"], explanation: "A sum is wrong." } }, 422);
      s.edits.push(script);
      return json(route, { ...detail(), script });
    }
    if (path === "/versions") return json(route, [{ id: "v2", content_type: "track", content_id: "sub-sfl", version: 2, status: s.versionStatus, parent_version: 1, coach_approved_by: null, officer_activated_by: null }]);
    if (path === "/versions/v2/approve") {
      if (role !== "coach") return json(route, { detail: "no" }, 403);
      s.versionStatus = "approved";
      s.audit.unshift({ role: "coach", action: "coach_approved" });
      return json(route, {});
    }
    if (path === "/versions/v2/activate") {
      if (s.versionStatus !== "approved") return json(route, { detail: "not approved" }, 409);
      s.versionStatus = "active";
      s.audit.unshift({ role: "officer", action: "officer_activated" });
      return json(route, {});
    }
    if (path.startsWith("/audit")) return json(route, s.audit.map((a, i) => ({ at: `2026-10-27T10:0${i}:00Z`, role: a.role, actor: `${a.role}-demo`, action: a.action, content_type: "track", content_id: "sub-sfl", version: 2, detail: {} })));
    return json(route, { detail: "not mocked" }, 404);
  });
  return s;
}

async function asRole(page: Page, role: "coach" | "officer" | "judge") {
  await page.goto("/");
  await page.evaluate((r) => localStorage.setItem("cc.role", r), role);
  await page.goto("/#/review");
  await page.reload();
}

test("the queue lists what waits, with its age, status and automatic checks", async ({ page }) => {
  await mockQueue(page);
  await asRole(page, "coach");
  const row = page.getByTestId("queue-list").locator("li").first();
  await expect(row).toContainText("Lesson 3");
  await expect(row).toContainText("Awaiting coach");
  await expect(row).toContainText("2 days");
  await page.getByTestId("open-i1").click();
  const checks = page.getByTestId("checks");
  await expect(checks).toContainText("arithmetic: passed");
  await expect(checks).toContainText("checker: held (tone)");
  await expect(page.getByTestId("held-note")).toBeVisible();
  await expect(page.getByTestId("queue-rule")).toContainText("Neither key alone publishes");
});

test("a return needs a reason; with one it is sent", async ({ page }) => {
  const s = await mockQueue(page);
  await asRole(page, "coach");
  await page.getByTestId("open-i1").click();
  await page.getByTestId("reject-item").click();
  await expect(page.getByTestId("need-reason")).toBeVisible();
  expect(s.rejects).toHaveLength(0);
  await page.getByTestId("reject-reason").selectOption("tone_issue");
  await page.getByTestId("reject-item").click();
  await expect.poll(() => s.rejects).toEqual([{ reason: "tone_issue", note: "" }]);
});

test("an edit that fails the checks is not saved and says why; a good edit is", async ({ page }) => {
  const s = await mockQueue(page);
  await asRole(page, "coach");
  await page.getByTestId("open-i1").click();
  await page.getByTestId("edit-script").fill("52 minus 29 is 37.");
  await page.getByTestId("save-edit").click();
  await expect(page.getByRole("alert")).toContainText("A sum is wrong.");
  await page.getByTestId("edit-script").fill("Lesson three. Open one bundle, then take away.");
  await page.getByTestId("save-edit").click();
  await expect.poll(() => s.edits).toEqual(["Lesson three. Open one bundle, then take away."]);
});

test("the coach's key alone does not switch a version on; the officer's key does, and the audit shows both", async ({ page }) => {
  await mockQueue(page);
  await asRole(page, "coach");
  const version = page.getByTestId("version-2");
  await expect(version.getByTestId("version-status")).toHaveText("In review");
  await version.getByTestId("key-coach").click();
  await expect(version.getByTestId("version-status")).toContainText("Approved by coach, not yet on");
  await expect(version.getByTestId("key-officer")).toHaveCount(0); // a coach has no officer key
  await expect(version).toContainText("Waiting for the officer");
  await asRole(page, "officer");
  await expect(page.getByTestId("version-2").getByTestId("key-coach")).toHaveCount(0);
  await page.getByTestId("version-2").getByTestId("key-officer").click();
  await expect(page.getByTestId("version-2").getByTestId("version-status")).toHaveText("On for the block");
  const rows = page.getByTestId("audit-row");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toContainText("officer activated by officer, version 2");
  await expect(rows.nth(1)).toContainText("coach approved by coach, version 2");
});

test("the queue reads in Hindi and Tamil, and the targets are 44 px", async ({ page }) => {
  await mockQueue(page);
  await asRole(page, "coach");
  await page.getByTestId("lang").selectOption("hi");
  await expect(page.getByRole("heading", { name: "समीक्षा कतार" })).toBeVisible();
  await page.getByTestId("lang").selectOption("ta");
  await expect(page.getByRole("heading", { name: "மதிப்பாய்வு வரிசை" })).toBeVisible();
  const small = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("main button, main select, main input")]
      .filter((e) => e.offsetParent !== null)
      .map((e) => Math.round(e.getBoundingClientRect().height))
      .filter((h) => h > 0 && h < 44),
  );
  expect(small).toEqual([]);
});
