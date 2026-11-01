import { expect, test, type Page, type Request } from "@playwright/test";
import { chooseLanguage, chooseRole } from "./switch";
import { readFileSync } from "node:fs";

interface Item {
  correct: number;
  probes: string[];
  wrong: Record<string, string[]>;
}
const keys = JSON.parse(readFileSync(new URL("../src/generated/answer_keys.json", import.meta.url), "utf-8")) as {
  forms: Record<string, { items: Item[] }>;
};
const items = keys.forms["A"]!.items;

/** Ten children: the first three show SUB-SFL (two wrong answers on items 7-10), the rest are right. */
function tenChildren(): string[][] {
  const correct = items.map((i) => String(i.correct));
  const sfl = items.map((item, n) => {
    const wrong = Object.entries(item.wrong).find(([, codes]) => codes.length === 1 && codes[0] === "SUB-SFL")?.[0];
    return item.probes.includes("SUB-SFL") && wrong && [6, 7].includes(n) ? wrong : String(item.correct);
  });
  return Array.from({ length: 10 }, (_, i) => (i < 3 ? sfl : correct));
}

async function typeAnswer(page: Page, q: number, value: string) {
  await page.getByTestId(`input-${q + 1}`).fill(value);
}

async function enterCheck(page: Page, rows: string[][]) {
  await page.goto("/#/check");
  await page.getByTestId("form-A").click();
  for (let c = 0; c < rows.length; c++) {
    for (let q = 0; q < rows[c]!.length; q++) await typeAnswer(page, q, rows[c]![q]!);
    if (c < rows.length - 1) await page.getByTestId("next-child").click();
  }
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => (localStorage.clear(), localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}')));
});

test("judge mode loads a simulated class: Home, then cards with counts, never a percentage", async ({ page }) => {
  await page.goto("/#/judge");
  await expect(page.getByRole("heading", { name: "Judge mode" })).toBeVisible();
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await expect(page.getByRole("note")).toContainText("Simulated data");

  await page.goto("/#/home");
  await expect(page.getByTestId("home-status")).toHaveText("You checked 28 children this term.");
  await page.getByTestId("home-action").click();
  await expect(page.getByTestId("line-SUB-SFL")).toHaveText("11 of 28 children take the smaller digit from the larger.");
  await expect(page.getByTestId("card-SUB-SFL")).toContainText("From your class:");
  await expect(page.getByRole("note")).toContainText("Simulated data");
  expect(await page.locator("body").innerText()).not.toMatch(/%/);
});

test("a teacher enters a 10-child check with the phone's number keyboard and gets counts on the phone", async ({ page }) => {
  const requests: Request[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) requests.push(r);
  });
  await page.route("**/api/classes/*/profile", (route) => route.fulfill({ status: 200, contentType: "application/json", body: '{"stored":true}' }));
  await chooseRole(page, "teacher");
  await enterCheck(page, tenChildren());
  await expect(page.getByTestId("check-count")).toContainText("10 children entered");
  await page.getByTestId("finish").click();

  await expect(page.getByTestId("line-SUB-SFL")).toHaveText("3 of 10 children take the smaller digit from the larger.");
  await expect(page.getByTestId("card-SUB-SFL")).toContainText("This is the focus for your class.");
  expect(await page.locator("body").innerText()).not.toMatch(/%/);

  // Only counts left the phone: one profile POST, with exactly the allowed fields.
  await expect.poll(() => requests.filter((r) => r.method() === "POST").length).toBeGreaterThan(0);
  const posts = requests.filter((r) => r.method() === "POST");
  expect(posts.every((r) => /\/api\/classes\/c-[0-9a-f]+\/profile$/.test(r.url()))).toBe(true);
  const body = JSON.parse(posts[0]!.postData() ?? "{}") as Record<string, unknown>;
  expect(Object.keys(body).sort()).toEqual(["anchor_wrong_count", "children_checked", "counts", "form", "simulated", "term", "untracked"]);
  expect(body["children_checked"]).toBe(10);
  expect(JSON.stringify(body)).not.toMatch(/\[/); // no arrays: nothing per child
  for (const r of requests) expect(r.postData() ?? "").not.toContain(String(items[0]!.correct) + '"');
});

test("the answers are autosaved on the phone and come back after a reload", async ({ page }) => {
  await page.goto("/#/check");
  await page.getByTestId("form-A").click();
  await typeAnswer(page, 0, "346");
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await expect(page.getByTestId("check-count")).toContainText("Saved on this phone");
  await page.reload();
  await page.goto("/#/check");
  await expect(page.getByTestId("input-1")).toHaveValue("346");
});

test("languages switch at runtime and the page language follows", async ({ page }) => {
  await page.goto("/#/home");
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
  await chooseLanguage(page, "hi");
  await expect(page.getByRole("heading", { name: "होम" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await chooseLanguage(page, "ta");
  await expect(page.getByRole("heading", { name: "முகப்பு" })).toBeVisible();
  await chooseLanguage(page, "en");
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
});

test("role and language are chosen on the landing page only; the name leads back to it", async ({ page }) => {
  await page.goto("/#/roles");
  await page.getByTestId("lang").selectOption("hi");
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await page.getByTestId("lang").selectOption("en");
  for (const route of ["home", "check", "practice", "profile", "judge"]) {
    await page.goto(`/#/${route}`);
    await expect(page.getByTestId("role")).toHaveCount(0);
    await expect(page.getByTestId("lang")).toHaveCount(0);
  }
  await page.goto("/#/profile");
  await page.getByTestId("change-role").click();
  await expect(page).toHaveURL(/#\/roles/);
  await expect(page.getByTestId("role")).toBeVisible();
  await page.goto("/#/home");
  await page.getByTestId("brand").click();
  await expect(page).toHaveURL(/#\/roles/);
});

test("is installable: a valid manifest and an active service worker", async ({ page }) => {
  await page.goto("/");
  const active = await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.ready;
    return Boolean(reg.active);
  });
  expect(active).toBe(true);
  const href = await page.locator('link[rel="manifest"]').getAttribute("href");
  const manifest = (await (await page.request.get(href!)).json()) as {
    name: string; display: string; start_url: string; icons: { sizes: string; type: string; purpose?: string }[];
  };
  expect(manifest.name).toBe("Cohort Coach");
  expect(manifest.display).toBe("standalone");
  const sizes = manifest.icons.map((i) => i.sizes);
  expect(sizes).toContain("192x192");
  expect(sizes).toContain("512x512");
  expect(manifest.icons.some((i) => i.purpose === "maskable")).toBe(true);
});

test("works offline after the first load: Home, Enter check and My class", async ({ page, context }) => {
  await page.goto("/#/judge");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  // Let the worker finish precaching, then cut the network.
  await page.waitForFunction(async () => (await caches.keys()).length > 0);
  await context.setOffline(true);
  await page.reload();

  await page.goto("/#/home");
  await expect(page.getByTestId("home-status")).toHaveText("You checked 28 children this term.");
  await expect(page.getByTestId("status")).toContainText("Offline");
  await page.goto("/#/check");
  await expect(page.getByTestId("child-title")).toHaveText("Child 1");
  await page.goto("/#/cards");
  await expect(page.getByTestId("line-SUB-SFL")).toHaveText("11 of 28 children take the smaller digit from the larger.");
  await context.setOffline(false);
});

test("Simulate offline stops sending and keeps the result waiting, then sends when back online", async ({ page }) => {
  const sent: string[] = [];
  await page.route("**/api/classes/*/profile", (route) => {
    sent.push(route.request().url());
    return route.fulfill({ status: 200, contentType: "application/json", body: '{"stored":true}' });
  });
  await page.goto("/#/judge");
  await page.getByTestId("offline-toggle").click();
  await expect(page.getByTestId("status")).toContainText("Offline mode is on");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await expect(page.getByTestId("status")).toContainText("Offline mode is on");
  expect(sent).toHaveLength(0);
  await page.getByTestId("offline-toggle").click();
  await expect.poll(() => sent.length).toBe(1);
  await expect(page.getByTestId("status")).toContainText("Online");
});

test("Advance to Term 2 starts a new term for the simulated class", async ({ page }) => {
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await page.getByTestId("advance").click();
  await page.goto("/#/home");
  await expect(page.getByTestId("home-status")).toHaveText("You have not entered this term's check yet.");
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await page.goto("/#/cards");
  await expect(page.getByTestId("line-SUB-SFL")).toHaveText("6 of 28 children take the smaller digit from the larger.");
});

test("each role has its own home, and role switching works", async ({ page }) => {
  await chooseRole(page, "mentor");
  await expect(page.getByTestId("mentor")).toBeVisible();
  await chooseRole(page, "coach");
  await expect(page.getByTestId("coach")).toBeVisible();
  await chooseRole(page, "admin");
  await expect(page.getByTestId("admin")).toBeVisible();
  await chooseRole(page, "teacher");
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
});
