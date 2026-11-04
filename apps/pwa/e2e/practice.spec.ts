import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type Request } from "@playwright/test";
import { chooseRole } from "./switch";

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
    output: { source: string; badge: string };
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
    if (line.startsWith("/tap ")) {
      await page.getByTestId(`tap-${line.slice(5)}`).click();
    } else {
      await page.getByTestId("say").fill(line);
      await page.getByTestId("send").click();
    }
    await expect(page.getByTestId(`reply-${n}`)).toBeVisible();
  }
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    (localStorage.clear(), localStorage.setItem("cc.user", "{\"id\":\"e2e tester\",\"nickname\":\"e2e tester\"}"), localStorage.setItem("cc.cacheOwner", "e2e tester"));
    localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}');
    localStorage.setItem("cc.voice", "0"); // these tests type; e2e/voice.spec.ts covers speaking
  });
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
  for (const r of requests.filter((x) => !x.url().endsWith("/api/roles") && !x.url().endsWith("/api/tester/config") && !x.url().endsWith("/api/health"))) {
    expect(r.method()).toBe("POST");
    expect(r.url()).toMatch(/\/api\/practice\/sessions(\/[^/]+\/(turns|end))?$/);
  }
  // the only other calls are the tester-stats switch (a GET with no data) and the server's answer to "is this the judge demo?" (no teacher data)
  for (const r of requests.filter((x) => x.url().endsWith("/api/roles"))) expect(r.method()).toBe("GET");
  expect(turns).toHaveLength(7);
});

test("the AI-layers overlay matches the API trace, for judges only", async ({ page }) => {
  const turns: TurnJson[] = [];
  await rehearse(page, turns);
  await expect(page.getByTestId("layers-panel")).toHaveCount(0);
  await page.getByTestId("side-judge").click();
  await page.getByTestId("layers-toggle").click();
  const panel2 = page.getByTestId("trace-2").getByTestId("layers-panel");
  const t2 = turns[1]!;
  await expect(panel2.getByTestId("layer-input")).toHaveText("Tell me how you got that.");
  await expect(panel2.getByTestId("layer-label")).toContainText(t2.layers.processing.label.move_id);
  await expect(panel2.getByTestId("layer-engine")).toContainText(String(t2.layers.processing.engine.answer));
  await expect(panel2.getByTestId("layer-eval")).toContainText(`${t2.layers.evaluation.latency_ms} ms`);
  await expect(panel2.getByTestId("layer-output")).toHaveText(`${t2.layers.output.source} · ${t2.layers.output.badge}`);
  for (const label of ["Input", "Processing", "Guardrails", "Evaluation", "Output"]) await expect(panel2).toContainText(label);

  await chooseRole(page, "teacher");
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("layers-toggle")).toHaveCount(0); // not for teachers
});

test("the server request log holds no transcript text (application logs: tests/practice/test_api.py)", async ({ page }) => {
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
  await expect(page.getByText("The AI model is not switched on here, so a simple reply was used.").first()).toBeVisible();
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
  await expect(page.getByTestId("start-check")).toBeVisible();
});

test("the AI map shows 10 calls by 5 layers and the audit trail shows metadata only", async ({ page }) => {
  await rehearse(page, []);
  await page.goto("/#/aimap");
  await expect(page.getByTestId("ai-map").locator("tbody tr")).toHaveCount(15); // calls 1 to 8 and 10 to 16 (call 9 is not built)
  await expect(page.getByTestId("ai-map").locator("thead th")).toHaveCount(6);
  await page.goto("/#/audit");
  await expect(page.getByTestId("audit-table")).toBeVisible();
  await expect(page.getByTestId("audit-table").locator("li").first()).toContainText("Checks passed");
  const text = await page.locator("main").innerText();
  expect(text).toContain("c01_child_voice");
  expect(text).toContain("c07_checker");
  for (const line of LINES.filter((l) => !l.startsWith("/tap"))) expect(text).not.toContain(line);
});

test("feedback thumbs stay on the phone, the flag goes to the team; sharing is off by default and remembered", async ({ page }) => {
  const flags: string[] = [];
  page.on("request", (r) => {
    if (/\/api\/feedback$/.test(r.url())) flags.push(r.postData() ?? "");
  });
  await page.goto("/#/practice?seed=5");
  const share = page.getByRole("checkbox");
  await expect(share).not.toBeChecked(); // off by default
  await share.check();
  await page.waitForTimeout(500); // the choice is written to IndexedDB asynchronously; reloading at once races it
  await page.reload();
  await page.goto("/#/practice?seed=5");
  await expect(page.getByRole("checkbox")).toBeChecked(); // the choice is saved
  await page.getByRole("checkbox").uncheck();
  await rehearse(page, []);
  await page.getByTestId("end").click();
  await expect(page.getByTestId("strength-0")).toBeVisible();
  await page.getByTestId("strength-0").getByRole("button", { name: /Helpful/ }).first().click();
  await expect(page.getByText("Thanks for telling us.")).toBeVisible();
  await page.getByRole("button", { name: "This is wrong" }).click();
  await expect(page.getByText("The team will review this card")).toBeVisible();
  await expect.poll(() => flags.length).toBe(1);
  expect(JSON.parse(flags[0]!)).toMatchObject({ kind: "card_flag", context: "practice" });
  const kept = await page.evaluate(
    () =>
      new Promise<{ ratings?: Record<string, string>; flags: number }>((resolve, reject) => {
        const open = indexedDB.open("cohort-coach");
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
          const db = open.result;
          const tr = db.transaction(["transcripts", "syncQueue"]);
          const rows = tr.objectStore("transcripts").getAll();
          const queue = tr.objectStore("syncQueue").getAll();
          tr.oncomplete = () => resolve({ ratings: (rows.result[0] as { ratings?: Record<string, string> }).ratings, flags: (queue.result as { kind: string }[]).filter((q) => q.kind === "flag").length });
        };
      }),
  );
  expect(Object.values(kept.ratings ?? {})).toContain("up");
  expect(kept.flags).toBe(0); // it went to the team, not into the phone queue
});

test("each child shows how they look right now, in words, under the name", async ({ page }) => {
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  for (let i = 0; i < 5; i++) {
    const mood = page.getByTestId(`kid-mood-${i}`);
    await expect(mood).toBeVisible();
    await expect(mood).toHaveText(/^(Confused|Distracted|Got it|Listening|Shy|Thinking|Unsure)$/);
  }
  await expect(page.getByTestId("board")).toHaveCount(0); // no problem posed yet
});

test("the side panel is tabs: your turn, coaching and, for judges, the judge panel", async ({ page }) => {
  await page.goto("/#/practice?seed=5");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("side-turn")).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("say")).toBeVisible();
  await page.getByTestId("side-coach").click();
  await expect(page.getByTestId("say")).toBeHidden();
  await expect(page.getByTestId("coaching")).toBeVisible();
  await page.getByTestId("side-judge").click();
  await expect(page.getByTestId("layers-toggle")).toBeVisible();
  await expect(page.getByTestId("tab-practise")).toHaveAttribute("aria-selected", "true");
});

test("on a wide screen the pages are a side rail; on a phone a bottom bar", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/#/practice");
  const wide = await page.locator("nav.navbar").boundingBox();
  expect(wide!.x).toBe(0);
  expect(wide!.width).toBeLessThan(160);
  expect(wide!.height).toBeGreaterThan(600);
  await page.setViewportSize({ width: 390, height: 800 });
  const narrow = await page.locator("nav.navbar").boundingBox();
  expect(narrow!.width).toBeGreaterThan(300);
  expect(narrow!.height).toBeLessThan(120);
});

test("the screen says what she is practising and lists the moves to try", async ({ page }) => {
  await page.goto("/#/practice?seed=5");
  await expect(page.getByTestId("goal-intro")).toContainText("take the smaller digit from the larger");
  await page.getByTestId("start-practice").click();
  await expect(page.getByTestId("goal")).toBeVisible();
  await expect(page.getByTestId("goal")).toContainText("What to practise");
  expect(await page.getByTestId("goal").locator("li").count()).toBeGreaterThanOrEqual(3);
  await expect(page.getByTestId("goal")).toContainText(/bundle/i);
});

test("other children join in on some turns, and the log shows each by name", async ({ page }) => {
  const turns: (TurnJson & { others?: { speaker: string; child_text: string }[] })[] = [];
  await rehearse(page, turns);
  const joined = turns.filter((t) => (t.others ?? []).length > 0);
  expect(joined.length).toBeGreaterThan(0); // one to three children speak; over 7 turns some turns have more than one
  const t = joined[0]!;
  for (const [i, o] of (t.others ?? []).entries()) {
    const line = page.getByTestId(`other-${t.turn}-${i}`);
    await expect(line).toContainText(o.speaker);
    await expect(line).toContainText(o.child_text);
  }
  for (const x of turns) expect(x.layers.output.source).toBe("ai"); // the first speaker is still the AI's line
});

test("every child who spoke is highlighted, and the log shows the newest turn first with its time", async ({ page }) => {
  const turns: (TurnJson & { speaker: string | null; others?: { speaker: string }[] })[] = [];
  await rehearse(page, turns);
  const last = turns[turns.length - 1]!;
  const spoke = [last.speaker, ...(last.others ?? []).map((o) => o.speaker)].filter(Boolean);
  await expect(page.locator(".kid[data-speaking='true']")).toHaveCount(spoke.length);
  for (const name of spoke) await expect(page.locator(".kid[data-speaking='true']", { hasText: name! })).toHaveCount(1);
  await expect(page.getByTestId("log").locator(".exchange").first()).toHaveAttribute("data-testid", `turn-${last.turn}`);
  await expect(page.getByTestId(`turn-time-${last.turn}`)).toHaveText(/\d/);
});
