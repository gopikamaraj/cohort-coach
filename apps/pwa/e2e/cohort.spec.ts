import { expect, test, type Page, type Route } from "@playwright/test";

// The cohort chat (P11, reduced). The API is mocked here; the real checks (names blocked, held posts
// invisible, the roles, retention) are tested in tests/cohorts. This proves the screen: joining needs
// her own tap, the compose notice, a blocked post asks her to rewrite, a reported post is held, the
// coach sees held posts and can hide, erase, restore and pin.

interface S {
  joined: boolean;
  open: boolean;
  posts: { id: string; author_kind: string; author_name: string; body: string | null; status: string; pinned: boolean; created_at: string }[];
  calls: string[];
}

async function mock(page: Page): Promise<S> {
  const s: S = {
    joined: false,
    open: true,
    posts: [{ id: "p0", author_kind: "coach", author_name: "Coach", body: "This week: try the bundles twice.", status: "visible", pinned: false, created_at: "2026-10-27T09:00:00Z" }],
    calls: [],
  };
  const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  const summary = () => ({ id: "co1", error: "SUB-SFL", status: "active", track_version: 1, schools: 7, members: 6, thread: s.open ? "open" : "read_only", simulated: true, joined: s.joined });
  await page.route("**/api/cohorts/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname.replace("/api/cohorts", "");
    const role = req.headers()["x-role"];
    s.calls.push(`${req.method()} ${path} ${role}`);
    if (path === "/open") return json(route, [summary()]);
    if (path === "/co1/join") {
      if (!(req.postDataJSON() as { consent: boolean }).consent) return json(route, { detail: "no" }, 403);
      s.joined = true;
      return json(route, { display_name: "Teacher 6", thread: "open" });
    }
    if (path === "/co1/thread") return json(route, { state: s.open ? "open" : "read_only", posts: s.posts.filter((p) => p.status === "visible") });
    if (path === "/co1/posts") {
      const b = (req.postDataJSON() as { body: string }).body;
      if (/Meena/.test(b)) return json(route, { detail: { codes: ["child_name"] } }, 422);
      s.posts.push({ id: `p${s.posts.length}`, author_kind: "teacher", author_name: "Teacher 6", body: b, status: "visible", pinned: false, created_at: "2026-10-27T10:00:00Z" });
      return json(route, s.posts[s.posts.length - 1]);
    }
    if (/\/posts\/p\d+\/report/.test(path)) {
      const id = path.split("/")[2];
      s.posts = s.posts.map((p) => (p.id === id ? { ...p, status: "reported" } : p));
      return json(route, { status: "held" });
    }
    if (path === "/coach/cohorts") return json(route, [summary()]);
    if (path === "/coach/cohorts/co1/thread") return json(route, s.posts);
    if (/\/coach\/posts\/p\d+\/decide/.test(path)) {
      const id = path.split("/")[3];
      const { action, identifier } = req.postDataJSON() as { action: string; identifier: boolean };
      s.posts = s.posts.map((p) => {
        if (p.id !== id) return p;
        if (action === "hide") return { ...p, status: "hidden", body: identifier ? null : p.body };
        if (action === "restore") return { ...p, status: "visible" };
        return { ...p, pinned: action === "pin" };
      });
      return json(route, {});
    }
    if (path === "/coach/cohorts/co1/prompt") {
      s.posts.push({ id: `p${s.posts.length}`, author_kind: "coach", author_name: "Coach", body: (req.postDataJSON() as { body: string }).body, status: "visible", pinned: false, created_at: "2026-10-27T11:00:00Z" });
      return json(route, {});
    }
    return json(route, { detail: "not mocked" }, 404);
  });
  return s;
}

async function asRole(page: Page, role: string) {
  await page.goto("/");
  await page.evaluate((r) => {
    localStorage.setItem("cc.role", r);
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
  }, role);
  await page.goto("/#/cohort");
  await page.reload();
}

test("joining needs her own tap, then she is in and sees the prompt", async ({ page }) => {
  const s = await mock(page);
  await asRole(page, "teacher");
  await expect(page.getByTestId("join")).toBeDisabled();
  await page.getByTestId("join-consent").check();
  await page.getByTestId("join").click();
  await expect.poll(() => s.joined).toBe(true);
  await expect(page.getByTestId("posts")).toContainText("This week: try the bundles twice.");
  await expect(page.getByTestId("cohort-notice")).toContainText("Do not write a child's name");
});

test("a post with a child's name is not posted and she is asked to rewrite", async ({ page }) => {
  const s = await mock(page);
  await asRole(page, "teacher");
  await page.getByTestId("join-consent").check();
  await page.getByTestId("join").click();
  await page.getByTestId("compose").fill("Meena failed again");
  await page.getByTestId("send-post").click();
  await expect(page.getByTestId("cohort-msg")).toContainText("rewrite");
  await expect(page.getByTestId("cohort-msg")).toContainText("child_name");
  expect(s.posts).toHaveLength(1);
  await page.getByTestId("compose").fill("I used bundles and they liked it");
  await page.getByTestId("send-post").click();
  await expect(page.getByTestId("posts")).toContainText("I used bundles and they liked it");
  await expect(page.getByTestId("posts")).toContainText("Teacher 6");
});

test("reporting a post holds it: other members stop seeing it", async ({ page }) => {
  await mock(page);
  await asRole(page, "teacher");
  await page.getByTestId("join-consent").check();
  await page.getByTestId("join").click();
  await page.getByTestId("compose").fill("I used bundles and they liked it");
  await page.getByTestId("send-post").click();
  await page.getByTestId("report").click();
  await expect(page.getByTestId("cohort-msg")).toContainText("Held for the coach");
  await expect(page.getByTestId("posts")).not.toContainText("I used bundles");
});

test("the coach sees held posts and can hide, erase the text, restore and pin", async ({ page }) => {
  const s = await mock(page);
  s.posts.push({ id: "p1", author_kind: "teacher", author_name: "Teacher 2", body: "a reported post", status: "reported", pinned: false, created_at: "2026-10-27T09:30:00Z" });
  await asRole(page, "coach");
  await page.getByTestId("coach-open").click();
  const held = page.getByTestId("post-p1");
  await expect(held).toContainText("Reported");
  await expect(held).toContainText("a reported post"); // a moderator reads it
  await held.getByRole("button", { name: "Restore" }).click();
  await expect(held).toHaveAttribute("data-status", "visible");
  await held.getByTestId("erase-p1").click();
  await expect(held).toHaveAttribute("data-status", "hidden");
  await expect(held).not.toContainText("a reported post"); // the text was erased
  await page.getByTestId("post-p0").getByRole("button", { name: "Pin" }).click();
  await expect.poll(() => s.posts.find((p) => p.id === "p0")?.pinned).toBe(true);
  await page.getByTestId("coach-prompt").fill("Try it twice this week.");
  await page.getByTestId("coach-post").click();
  await expect(page.getByTestId("posts")).toContainText("Try it twice this week.");
});

test("a read-only thread says why, and the chat reads in Hindi and Tamil", async ({ page }) => {
  const s = await mock(page);
  s.open = false;
  s.joined = true;
  await asRole(page, "teacher");
  await page.getByTestId("open-cohort").click();
  await expect(page.getByTestId("read-only")).toContainText("read-only");
  await expect(page.getByTestId("compose")).toHaveCount(0);
  await page.getByTestId("lang").selectOption("hi");
  await expect(page.getByRole("heading", { name: "कोहॉर्ट चैट" })).toBeVisible();
  await page.getByTestId("lang").selectOption("ta");
  await expect(page.getByRole("heading", { name: "குழு அரட்டை" })).toBeVisible();
});
