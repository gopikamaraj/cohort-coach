import { expect, type Page } from "@playwright/test";

// Enter check no longer makes a paper or offers a sample: it chooses a paper that already exists. These
// helpers make the standard test paper (the published pilot-test numbers, the same numbers the test
// folder's sheets were made on) for this browser's class through the API, as the seed script does for
// a hosted test class, then start the check on it by the page's own controls.

/** The id of this browser's class. A fresh phone has none until something needs one (a saved check, a
 *  paper), so the same row the app would make is written here when it is missing. */
export async function classIdOf(page: Page): Promise<string> {
  // the app opens its database when it loads; wait for it rather than create an empty one
  await expect
    .poll(() => page.evaluate(async () => (await indexedDB.databases()).some((d) => d.name === "cohort-coach")), { timeout: 20_000 })
    .toBe(true);
  return page.evaluate(
    () =>
      new Promise<string>((resolve, reject) => {
        const open = indexedDB.open("cohort-coach");
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
          const db = open.result;
          const tx = db.transaction(["settings", "classes"], "readwrite");
          const get = tx.objectStore("settings").get("activeClass");
          get.onsuccess = () => {
            const have = (get.result as { value?: string } | undefined)?.value;
            if (have) return resolve(have);
            const id = `c-${Array.from(crypto.getRandomValues(new Uint8Array(5)), (b) => b.toString(16).padStart(2, "0")).join("")}`;
            tx.objectStore("classes").put({ id, name: "My class", simulated: false, createdAt: Date.now() });
            tx.objectStore("settings").put({ key: "activeClass", value: id });
            tx.oncomplete = () => resolve(id);
          };
        };
      }),
  );
}

/** Make the standard test paper for this class (pre-test A, or its post-test twin). Returns its id. */
export async function makeTestPaper(page: Page, kind: "pre" | "post" = "pre", term = 1): Promise<string> {
  const classId = await classIdOf(page);
  const out = await page.request.post("/api/papers/generate", {
    headers: { "X-Role": "teacher" },
    data: { check: { id: `${classId}:${term}`, kind, form: kind === "post" ? "B" : "A", class_label: "3A", term }, language: "en", sample: true },
  });
  expect(out.ok()).toBeTruthy();
  return ((await out.json()) as { paper: { id: string } }).paper.id;
}

/** From a fresh browser: open Enter check with the standard test paper made for this class and chosen. */
export async function openWithPaper(page: Page, opts: { kind?: "pre" | "post" } = {}): Promise<void> {
  await page.goto("/#/check");
  const paperId = await makeTestPaper(page, opts.kind ?? "pre");
  await page.reload();
  await expect(page.getByTestId("paper-chooser")).toBeVisible();
  if (opts.kind && opts.kind !== "pre") await page.getByTestId(`kind-${opts.kind}`).click();
  // papers are shared, so the test database holds every earlier test's paper too: choose this one by id
  const select = page.getByTestId("paper-select");
  await select.waitFor({ timeout: 20_000 });
  await select.selectOption(paperId);
  await expect(page.getByTestId("paper-attached")).toBeVisible({ timeout: 20_000 });
}

/** Give the class size and press Start the check. */
export async function begin(page: Page, size = 1): Promise<void> {
  await page.getByTestId("check-class-name").fill("3A Class");
  await page.getByTestId("check-expected").fill(String(size));
  await page.getByTestId("start-check-go").click();
  await expect(page.getByTestId("child-title")).toBeVisible();
}

/** The two together: the usual way into an entering check. */
export async function startSample(page: Page, opts: { size?: number; kind?: "pre" | "post" } = {}): Promise<void> {
  await openWithPaper(page, opts);
  await begin(page, opts.size ?? 1);
}

/** Type one roll's answers and approve it (there is no picture, so the confirmation is accepted). */
export async function fillAndApprove(page: Page, values: string[]): Promise<void> {
  for (let q = 0; q < values.length; q++) await page.getByTestId(`input-${q + 1}`).fill(values[q] as string);
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("approve").click();
}

/** Press Finish entering and accept the confirmation. */
export async function finishEntering(page: Page): Promise<void> {
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("finish").click();
}

/** Roll by roll: type the answers (a blank or unreadable box is left empty), then approve. Ends on the next roll. */
export async function enterRolls(page: Page, rows: string[][]): Promise<void> {
  for (const row of rows) {
    for (let q = 0; q < row.length; q++) {
      const v = row[q] as string;
      if (v !== "" && v !== "_" && v !== "?") await page.getByTestId(`input-${q + 1}`).fill(v);
    }
    page.once("dialog", (d) => void d.accept());
    await page.getByTestId("approve").click();
  }
}

/** The made-up class the judge's sample used to load (rows from the server), entered by typing, approved. */
export async function enterJudgeSample(page: Page): Promise<number> {
  const sample = (await (await page.request.get("/api/judge/sample-sheets")).json()) as { children: string[][] };
  await startSample(page, { size: sample.children.length });
  await enterRolls(page, sample.children);
  return sample.children.length;
}
