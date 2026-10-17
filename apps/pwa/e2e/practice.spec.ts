import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type Request } from "@playwright/test";

// The recorded rehearsal (evals/sets/practice_scripts/sub-sfl-en.txt, seed 5).
const LINES = [
  "Priya, what is 52 minus 29?",
  "Tell me how you got that.",
  "/tap bundles",
  "Priya, you only have 2 loose ones. Open a bundle to exchange it for ten sticks.",
  "Let us check by adding back. What is 23 plus 29?",
  "Priya, now try 74 minus 46.",
  "Well done, thank you for trying.",
];
const API_LOG = fileURLToPath(new URL("../../../e2e-api.log", import.meta.url));

interface TurnJson {
  turn: number;
  speaker: string | null;
  child_text: string;
  latency_ms: number;
  layers: {
    processing: { label: { move_id: string }; engine: { answer: number | null; intent: string } };
    evaluation: { latency_ms: number };
  };
}

async function rehearse(page: Page, turns: TurnJson[]) {
  page.on("response", async (r) => {
    if (/\/api\/practice\/sessions\/[^/]+\/turns$/.test(r.url()) && r.ok()) turns.push((await r.json()) as TurnJson);
  });
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  let n = 0;
  for (const line of LINES) {
    n += 1;
    if (line.startsWith("/tap ")) await page.getByTestId(`tap-${line.slice(5)}`).click();
    else {
      await page.getByTestId("say").fill(line);
      await page.getByTestId("send").click();
    }
    await expect(page.getByTestId(`reply-${n}`)).toBeVisible();
  }
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
});

test("a rehearsal of 7 turns with a material tap ends in two strengths with her own quotes", async ({ page }) => {
  const turns: TurnJson[] = [];
  const requests: Request[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) requests.push(r);
  });
  await rehearse(page, turns);
  await expect(page.getByTestId("turn-counter")).toContainText("Turn 7 of 40");
  await page.getByTestId("end").click();

  await expect(page.getByTestId("feedback")).toBeVisible();
  await expect(page.getByTestId("fb-badge")).toHaveText("Checked ✓");
  await expect(page.getByTestId("strength-0")).toBeVisible();
  await expect(page.getByTestId("strength-1")).toBeVisible();
  const quotes = await page.locator("[data-testid^=strength-] mark").allInnerTexts();
  expect(quotes).toHaveLength(2);
  for (const q of quotes) expect(LINES.some((l) => l.includes(q))).toBe(true); // verbatim, hers
  expect(await page.locator("body").innerText()).not.toMatch(/%/);

  // The transcript is on this phone, and the only server calls were the practice session's.
  const stored = await page.evaluate(
    () =>
      new Promise<{ turns: unknown[]; ended: boolean }>((resolve, reject) => {
        const open = indexedDB.open("cohort-coach");
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
          const all = open.result.transaction("transcripts").objectStore("transcripts").getAll();
          all.onsuccess = () => resolve(all.result[0] as { turns: unknown[]; ended: boolean });
        };
      }),
  );
  expect(stored.turns).toHaveLength(7);
  expect(stored.ended).toBe(true);
  for (const r of requests) {
    expect(r.method()).toBe("POST");
    expect(r.url()).toMatch(/\/api\/practice\/sessions(\/[^/]+\/(turns|end))?$/);
  }
  expect(turns).toHaveLength(7);
});

test("the AI-layers overlay matches the API trace, for judges only", async ({ page }) => {
  const turns: TurnJson[] = [];
  await rehearse(page, turns);
  await expect(page.getByTestId("layers-panel")).toHaveCount(0);
  await page.getByTestId("layers-toggle").click();
  const panel2 = page.getByTestId("turn-2").getByTestId("layers-panel");
  const t2 = turns[1]!;
  await expect(panel2.getByTestId("layer-input")).toHaveText("Tell me how you got that.");
  await expect(panel2.getByTestId("layer-label")).toContainText(t2.layers.processing.label.move_id);
  await expect(panel2.getByTestId("layer-engine")).toContainText(String(t2.layers.processing.engine.answer));
  await expect(panel2.getByTestId("layer-eval")).toContainText(`${t2.layers.evaluation.latency_ms} ms`);
  await expect(panel2.getByTestId("layer-output")).toContainText("checked");
  for (const label of ["Input", "Processing", "Guardrails", "Evaluation", "Output"]) await expect(panel2).toContainText(label);

  await page.getByTestId("role").selectOption("teacher");
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("layers-toggle")).toHaveCount(0); // not for teachers
});

test("the server logs hold no transcript text", async ({ page }) => {
  await rehearse(page, []);
  const log = readFileSync(API_LOG, "utf-8");
  expect(log).toContain("/api/practice/sessions"); // the requests were logged ...
  for (const line of LINES.filter((l) => !l.startsWith("/tap"))) {
    expect(log).not.toContain(line); // ... but never what she said
    expect(log).not.toContain(encodeURIComponent(line));
  }
  expect(log).not.toMatch(/52 minus 29|loose ones/);
});

test("retry uses the same children", async ({ page }) => {
  await rehearse(page, []);
  const names = await page.locator(".kid-name").allInnerTexts();
  await page.getByTestId("end").click();
  await expect(page.getByTestId("feedback")).toBeVisible();
  await page.getByTestId("retry").click();
  await expect(page.locator(".kid-name")).toHaveText(names);
});

test("a class's own counts seat the children, and a slow reply is explained", async ({ page }) => {
  const bodies: Record<string, unknown>[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && /\/api\/practice\/sessions$/.test(r.url())) bodies.push(JSON.parse(r.postData() ?? "{}") as Record<string, unknown>);
  });
  await page.goto("/#/judge");
  await page.getByTestId("load-demo").click();
  await expect(page.getByTestId("demo-loaded")).toBeVisible();
  await page.goto("/#/home");
  await page.getByTestId("home-practice").click();
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("kid-4")).toBeVisible();
  expect(bodies[0]!["counts"]).toMatchObject({ "SUB-SFL": 11 });
  expect(bodies[0]!["checked"]).toBe(28);
  expect(bodies[0]!["scenario"]).toBe("SUB-SFL");
  await expect(page.getByRole("note")).toContainText("Simulated data");
  // These seats were never recorded, so the model is not available in recorded mode: a template
  // line is used and the teacher is told why.
  await page.getByTestId("say").fill("Who can tell me 52 minus 29?");
  await page.getByTestId("send").click();
  await expect(page.getByTestId("reply-1")).toBeVisible();
  await expect(page.getByText("The connection is slow, so a simple reply was used.")).toBeVisible();
});

test("when practice is paused the teacher can watch a recorded sample", async ({ page }) => {
  await page.route("**/api/practice/sessions", (route) => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"paused"}' }));
  await page.goto("/#/practice");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("practice-state")).toHaveText("Practice is paused for today.");
  await page.getByTestId("watch-sample").click();
  await expect(page.getByTestId("sample")).toContainText("Tell me how you got that.");
  await expect(page.getByTestId("sample")).toContainText("recorded sample");
});

test("offline, practice says so and sends nothing; everything else still opens", async ({ page }) => {
  const calls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/practice")) calls.push(r.url());
  });
  await page.goto("/#/judge");
  await page.getByTestId("offline-toggle").click();
  await page.goto("/#/practice");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("practice-state")).toContainText("Practice needs a connection");
  expect(calls).toHaveLength(0);
  await page.goto("/#/check");
  await expect(page.getByTestId("form-A")).toBeVisible();
});

test("the AI map shows 8 calls by 5 layers and the audit trail shows metadata only", async ({ page }) => {
  await rehearse(page, []);
  await page.goto("/#/aimap");
  await expect(page.getByTestId("ai-map").locator("tbody tr")).toHaveCount(8);
  await expect(page.getByTestId("ai-map").locator("thead th")).toHaveCount(6);
  await page.goto("/#/audit");
  await expect(page.getByTestId("audit-table")).toBeVisible();
  const text = await page.locator("main").innerText();
  expect(text).toContain("c01_child_voice");
  expect(text).toContain("c07_checker");
  for (const line of LINES.filter((l) => !l.startsWith("/tap"))) expect(text).not.toContain(line);
});
