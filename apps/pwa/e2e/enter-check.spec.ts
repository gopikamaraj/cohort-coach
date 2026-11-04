import { createHash } from "node:crypto";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";
import { begin, fillAndApprove, finishEntering, startSample } from "./sample";

// The nine changes to Enter check: an existing paper, the camera or a folder, a roll dropdown with data
// and approval states, the picture drawer, the Finish rule and the three checkboxes. The sheet reader
// (call 8) is answered by the test here, so matching, conflicts and the queue are deterministic; the
// recorded-mode replay is covered in tests/ai/test_client.py and tests/api/test_sheets.py.

const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';
const RIGHT = ["346", "728", "85", "74", "82", "35", "38", "26", "43", "54"];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => {
    (localStorage.clear(), localStorage.setItem("cc.user", "{\"id\":\"e2e tester\",\"nickname\":\"e2e tester\"}"), localStorage.setItem("cc.cacheOwner", "e2e tester"));
    localStorage.setItem("cc.consent", c);
    localStorage.setItem("cc.role", "teacher");
  }, CONSENT);
});

// ---- tiny pictures -------------------------------------------------------------------------------

function crc32(buf: Buffer): number {
  let c = ~0;
  for (const b of buf) {
    c ^= b;
    for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
  }
  return ~c >>> 0;
}
function chunk(type: string, data: Buffer): Buffer {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
}
/** A small valid PNG whose colour depends on `seed`, so every picture has its own hash. */
function png(seed: number): Buffer {
  const w = 8;
  const h = 8;
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;
  ihdr[9] = 2;
  const raw = Buffer.concat(Array.from({ length: h }, () => Buffer.concat([Buffer.from([0]), Buffer.from(Array.from({ length: w }, (_, i) => [(seed * 37) % 256, (seed * 91 + i) % 256, (seed * 53) % 256]).flat())])));
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}
const sha = (b: Buffer) => createHash("sha256").update(b).digest("hex");

type Reply = { cells?: { text: string; status: string }[]; header?: { class_code: string | null; roll_number: number | null; confidence: number } | null; status?: number; body?: unknown; delay?: number };
const OK_CELLS = RIGHT.map((text) => ({ text, status: "ok" }));

/** Answer /api/sheets/read from a table keyed by the hash of the original file the page sends. */
async function mockReader(page: Page, table: Map<string, Reply>, stats = { inflight: 0, peak: 0, calls: 0 }) {
  await page.route("**/api/sheets/read", async (route: Route) => {
    const body = route.request().postDataBuffer()?.toString("latin1") ?? "";
    const hash = /name="sha256"\r\n\r\n([0-9a-f]{64})/.exec(body)?.[1] ?? "";
    const reply = table.get(hash) ?? {};
    stats.calls += 1;
    stats.inflight += 1;
    stats.peak = Math.max(stats.peak, stats.inflight);
    await new Promise((r) => setTimeout(r, reply.delay ?? 150));
    stats.inflight -= 1;
    if (reply.status && reply.status !== 200) return route.fulfill({ status: reply.status, contentType: "application/json", body: JSON.stringify(reply.body ?? { detail: "no" }) });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ form: "x", retried: false, header: reply.header ?? null, cells: reply.cells ?? OK_CELLS }) });
  });
  return stats;
}

function folderOf(files: Record<string, Buffer>): string {
  const dir = mkdtempSync(path.join(tmpdir(), "sheets-"));
  for (const [name, data] of Object.entries(files)) writeFileSync(path.join(dir, name), data);
  return dir;
}

const roll = (page: Page, n: number) => page.getByTestId("child-select").selectOption(String(n - 1));

// ---- change 1 and 8: nothing about data sources or samples ---------------------------------------

test("the page never mentions synthetic, pilot, demo, simulated or sample data, before or after starting", async ({ page }) => {
  await page.goto("/#/check");
  const words = /synthetic|pilot|demo|simulated|sample/i;
  await expect(page.getByTestId("start-check")).toBeVisible();
  expect(await page.getByTestId("start-check").innerText()).not.toMatch(words);
  for (const id of ["data-source", "sample-paper", "use-sample", "sample-sheet", "pilot-data-card"]) await expect(page.getByTestId(id)).toHaveCount(0);
  await startSample(page, { size: 3 });
  const main = await page.locator("main").innerText();
  expect(main.replace(/Recorded AI answer/g, "")).not.toMatch(words);
  for (const id of ["data-source", "sample-paper", "use-sample", "sample-sheet", "pilot-data-card", "demo-entry"]) await expect(page.getByTestId(id)).toHaveCount(0);
});

// ---- change 2: choose a paper that exists ---------------------------------------------------------

test("starting needs a paper and a class size, each with its reason on screen; Create a paper is a link", async ({ page }) => {
  await page.goto("/#/check");
  await expect(page.getByTestId("start-check-go")).toBeDisabled();
  await expect(page.getByTestId("start-need-paper")).toBeVisible();
  await expect(page.getByTestId("chooser-none")).toContainText("No paper");
  await expect(page.getByTestId("chooser-create")).toHaveAttribute("href", /#\/papers/);
  await expect(page.getByTestId("check-expected")).toHaveAttribute("required", "");
  await expect(page.locator("text=optional")).toHaveCount(0);
  await expect(page.getByTestId("check-expected")).toHaveAccessibleDescription(/including those absent/); // the hint says what to enter
});

test("the paper that exists is chosen for her, the count is required, and the paper's key is on the phone", async ({ page }) => {
  await startSample(page, { size: 2 });
  await expect(page.getByTestId("check-paper-code")).toBeVisible();
  const key = await page.evaluate(() => Object.keys(JSON.parse(localStorage.getItem("cc.paperkeys") ?? "{}")).length);
  expect(key).toBeGreaterThan(0);
  await expect(page.getByTestId("child-select").locator("option")).toHaveCount(2);
});

// ---- change 4: the roll dropdown -----------------------------------------------------------------

test("every option shows its data state and approval state, the counts line follows, absent approves, an edit reverts", async ({ page }) => {
  await startSample(page, { size: 4 });
  const opts = page.getByTestId("child-select").locator("option");
  await expect(opts).toHaveCount(4);
  await expect(opts.nth(0)).toHaveText("Roll no 1 · Not entered");
  await expect(page.getByTestId("roll-counts")).toHaveText("0 entered · 0 approved · 0 absent · 4 not entered");

  await page.getByTestId("input-1").fill("346");
  await expect(opts.nth(0)).toHaveText("Roll no 1 · Entered · Not approved");
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Entered · Not approved");

  await fillAndApprove(page, RIGHT);
  await expect(page.getByTestId("child-title")).toHaveText("Roll no 2"); // moved on (no roll left to approve: next not entered)
  await expect(opts.nth(0)).toHaveText("Roll no 1 · Entered · Approved");

  await page.getByTestId("absent").check();
  await expect(opts.nth(1)).toHaveText("Roll no 2 · Absent · Approved"); // absent approves at once
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Absent · Approved");
  await expect(page.getByTestId("roll-counts")).toHaveText("1 entered · 1 approved · 1 absent · 2 not entered");
  await page.getByTestId("absent").uncheck();
  await expect(opts.nth(1)).toHaveText("Roll no 2 · Not entered");

  await roll(page, 1);
  await page.getByTestId("input-3").fill("84"); // any change sets an approved roll back
  await expect(opts.nth(0)).toHaveText("Roll no 1 · Entered · Not approved");
  await expect(page.getByTestId("next-approve")).toBeEnabled();
});

test("Approve moves to the next roll to approve, then the next not entered; with nothing to approve it says so", async ({ page }) => {
  await startSample(page, { size: 3 });
  await expect(page.getByTestId("next-approve")).toBeDisabled();
  await expect(page.getByTestId("nothing-to-approve")).toHaveText("Nothing to approve");
  for (let n = 1; n <= 2; n++) {
    await roll(page, n);
    for (let q = 0; q < 10; q++) await page.getByTestId(`input-${q + 1}`).fill(RIGHT[q] as string);
  }
  await roll(page, 1);
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("approve").click();
  await expect(page.getByTestId("child-title")).toHaveText("Roll no 2"); // the next one to approve
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("approve").click();
  await expect(page.getByTestId("child-title")).toHaveText("Roll no 3"); // none left to approve: next not entered
});

test("a roll with no picture asks before it is approved", async ({ page }) => {
  await startSample(page, { size: 1 });
  for (let q = 0; q < 10; q++) await page.getByTestId(`input-${q + 1}`).fill(RIGHT[q] as string);
  let asked = "";
  page.once("dialog", (d) => {
    asked = d.message();
    void d.dismiss();
  });
  await page.getByTestId("approve").click();
  expect(asked).toContain("There is no picture to check against. Approve anyway?");
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Not approved");
});

// ---- change 9: the three checkboxes --------------------------------------------------------------

test("three Missed the teaching checkboxes are always visible, in order, with the paper's own question numbers", async ({ page }) => {
  await startSample(page, { size: 2 });
  const group = page.getByTestId("missed-group");
  await expect(group).toBeVisible();
  await expect(group.locator("legend")).toHaveText("Missed the teaching (from my register)");
  const boxes = group.locator("label.check");
  await expect(boxes).toHaveCount(3);
  await expect(boxes.nth(0)).toHaveText("Missed the teaching on addition with carrying (questions 3–5)");
  await expect(boxes.nth(1)).toHaveText("Missed the teaching on place value (questions 1–2)");
  await expect(boxes.nth(2)).toHaveText("Missed the teaching on subtraction with borrowing (questions 7–10)");
  await expect(group.locator("input[type=checkbox]")).toHaveCount(3);
  await expect(page.locator("details", { has: group })).toHaveCount(0); // never inside a disclosure
});

test("the tags belong to the roll, stay on the phone, are never sent, and changing one needs approving again", async ({ page }) => {
  const sent: string[] = [];
  page.on("request", (r) => {
    if (r.method() !== "GET") sent.push(`${r.url()} ${r.postData() ?? ""}`);
  });
  await startSample(page, { size: 2 });
  await fillAndApprove(page, RIGHT);
  await roll(page, 1);
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Approved");
  await page.getByTestId("missed-addition").check();
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Not approved");
  await roll(page, 2);
  await expect(page.getByTestId("missed-addition")).not.toBeChecked(); // per roll
  await roll(page, 1);
  await expect(page.getByTestId("missed-addition")).toBeChecked();
  expect(sent.filter((s) => /missed|addition/i.test(s))).toEqual([]);
});

// ---- change 7: Finish entering -------------------------------------------------------------------

test("Finish is disabled with a note on the page saying why, names the rolls, and caps the list at 8", async ({ page }) => {
  await startSample(page, { size: 14 });
  const finish = page.getByTestId("finish");
  await expect(finish).toBeDisabled();
  await expect(page.getByTestId("finish-note")).toContainText("Enter at least one child's answers first.");
  await expect(finish).toHaveAttribute("aria-describedby", "finish-note");

  await fillAndApprove(page, RIGHT); // roll 1 approved
  await roll(page, 2);
  for (let q = 0; q < 10; q++) await page.getByTestId(`input-${q + 1}`).fill(RIGHT[q] as string); // roll 2 not approved
  await expect(page.getByTestId("finish-note-not_entered")).toContainText("Roll no 3, 4, 5, 6, 7, 8, 9, 10 and 4 more are not entered. Enter them, or mark them absent.");
  await expect(page.getByTestId("finish-note-not_approved")).toContainText("Roll no 2 are not approved. Open the sheet, check the answers, and approve.");
  await expect(finish).toBeDisabled();
});

test("Finish is enabled only when every roll is approved or absent; it asks, closes the check and Reopen keeps the approvals", async ({ page }) => {
  await startSample(page, { size: 3 });
  await fillAndApprove(page, RIGHT);
  await page.getByTestId("absent").check(); // roll 2
  await roll(page, 3);
  await expect(page.getByTestId("finish")).toBeDisabled();
  await page.getByTestId("absent").check();
  await expect(page.getByTestId("finish")).toBeEnabled();
  await expect(page.getByTestId("finish-note")).toContainText("All 3 roll numbers are approved or absent.");
  let asked = "";
  page.once("dialog", (d) => {
    asked = d.message();
    void d.accept();
  });
  await page.getByTestId("finish").click();
  await expect(page).toHaveURL(/#\/cards/);
  expect(asked).toBe("Finish entering? 1 children entered, 2 marked absent. You can reopen the check later.");
  await page.goto("/#/check");
  await expect(page.getByTestId("check-finished")).toBeVisible();
  await expect(page.getByTestId("check-finished-counts")).toContainText("1 children entered, 2 roll numbers marked absent");
  await page.getByTestId("check-reopen").click();
  await roll(page, 1);
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Entered · Approved");
  await expect(page.getByTestId("finish")).toBeEnabled();
  await finishEntering(page);
  await expect(page).toHaveURL(/#\/cards/);
  await page.goto("/#/check");
  await expect(page.getByTestId("check-finished")).toBeVisible();
});

test("nothing is marked absent for her any more", async ({ page }) => {
  await startSample(page, { size: 3 });
  await fillAndApprove(page, RIGHT);
  await expect(page.getByTestId("finish")).toBeDisabled();
  await roll(page, 3);
  await expect(page.getByTestId("absent")).not.toBeChecked();
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Not entered");
});

// ---- change 3 and 6: the camera, and the picture drawer ------------------------------------------

test("a camera read fills the roll as Entered, Not approved, labelled; the image icon opens the drawer; Approve moves on", async ({ page }) => {
  await mockReader(page, new Map());
  await startSample(page, { size: 3 });
  await expect(page.getByTestId("show-sheet")).toBeDisabled(); // no picture yet, and it says why
  await expect(page.getByTestId("show-sheet")).toHaveAttribute("title", "No picture for this roll");
  await page.getByTestId("photo-input").setInputFiles({ name: "x.png", mimeType: "image/png", buffer: png(1) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Entered · Not approved");
  await expect(page.getByTestId("roll-source")).toContainText(/Read by AI|Recorded AI answer/);
  await page.getByTestId("show-sheet").click();
  const drawer = page.getByTestId("sheet-drawer");
  await expect(drawer).toBeVisible();
  await expect(drawer).toHaveAttribute("role", "complementary");
  await expect(page.getByTestId("drawer-image")).toHaveAttribute("alt", "The answer sheet for roll no 1");
  await page.getByTestId("input-2").fill("728"); // not modal: the page is still editable
  await page.getByTestId("drawer-approve").click();
  await expect(page.getByTestId("child-title")).toHaveText("Roll no 2"); // none to approve: next not entered
  await expect(page.getByTestId("drawer-none")).toBeVisible(); // it follows the dropdown; this roll has no picture
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await roll(page, 1);
  await expect(page.getByTestId("child-select").locator("option:checked")).toContainText("Entered · Approved");
});

test("the drawer is 40% of the height at the bottom on a phone and 40% of the width at the side on a laptop", async ({ page }) => {
  await mockReader(page, new Map());
  await page.setViewportSize({ width: 390, height: 844 });
  await startSample(page, { size: 2 });
  await page.getByTestId("photo-input").setInputFiles({ name: "x.png", mimeType: "image/png", buffer: png(2) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await page.getByTestId("show-sheet").click();
  const box = (await page.getByTestId("sheet-drawer").boundingBox())!;
  expect(Math.abs(box.height - 844 * 0.4)).toBeLessThan(4);
  expect(Math.abs(box.y + box.height - 844)).toBeLessThan(2);
  expect(box.width).toBeGreaterThan(385);
  await page.getByTestId("drawer-close").click();
  await expect(page.getByTestId("show-sheet")).toBeFocused(); // focus returns to the icon

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.getByTestId("show-sheet").click();
  const side = (await page.getByTestId("sheet-drawer").boundingBox())!;
  expect(Math.abs(side.width - 1280 * 0.4)).toBeLessThan(4);
  expect(Math.abs(side.x + side.width - 1280)).toBeLessThan(2);
});

test("a re-read is offered for a roll that was read, and the picture goes when the page is left (never stored)", async ({ page }) => {
  await mockReader(page, new Map());
  await startSample(page, { size: 1 });
  await page.getByTestId("photo-input").setInputFiles({ name: "x.png", mimeType: "image/png", buffer: png(3) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await page.getByTestId("show-sheet").click();
  await expect(page.getByTestId("drawer-reread")).toBeEnabled();
  const stored = await page.evaluate(async () => {
    const found: string[] = [];
    for (const k of Object.keys(localStorage)) if (/data:image|blob:/.test(localStorage.getItem(k) ?? "")) found.push(`localStorage:${k}`);
    for (const name of await caches.keys()) for (const r of await (await caches.open(name)).keys()) if (/\.(png|jpe?g)$/i.test(r.url) && !r.url.includes("/icon")) found.push(`cache:${r.url}`);
    return found;
  });
  expect(stored).toEqual([]);
  await page.reload();
  await expect(page.getByTestId("show-sheet")).toBeDisabled();
  await expect(page.getByTestId("no-pic-reason")).toContainText("pictures are kept in memory only");
});

// ---- change 3: a folder of pictures --------------------------------------------------------------

test("a folder: names and headers are matched to rolls, the summary says what is left, three are read at a time", async ({ page }) => {
  const a = png(11);
  const b = png(12);
  const c = png(13);
  const d = png(14);
  const e = png(15);
  const table = new Map<string, Reply>([
    [sha(c), { header: { class_code: "3A", roll_number: 4, confidence: 0.95 } }],
    [sha(d), { header: null }],
  ]);
  const stats = await mockReader(page, table);
  const dir = folderOf({ "3A-roll01.png": a, "3A-roll02.png": b, "scan_0003.png": c, "scan_0004.png": d, "scan_0005.png": e, "notes.txt": Buffer.from("not a picture") });
  await startSample(page, { size: 6 });
  await expect(page.getByTestId("folder-button-text")).toHaveText("Select a folder of pictures");
  await page.getByTestId("folder-input").setInputFiles(dir);
  await expect(page.getByTestId("folder-summary")).toContainText("5 pictures found, 3 matched to roll numbers, 2 need a roll number.", { timeout: 20_000 });
  await expect(page.getByTestId("folder-summary")).toContainText("1 skipped");
  expect(stats.peak).toBeLessThanOrEqual(3);
  expect(stats.peak).toBeGreaterThan(1);
  // matched ones are filled in: Entered, Not approved
  const opts = page.getByTestId("child-select").locator("option");
  await expect(opts.nth(0)).toHaveText("Roll no 1 · Entered · Not approved");
  await expect(opts.nth(1)).toHaveText("Roll no 2 · Entered · Not approved");
  await expect(opts.nth(3)).toHaveText("Roll no 4 · Entered · Not approved"); // by the header the reader saw
  // two need her: choose a roll for one, skip the other
  await expect(page.getByTestId("folder-pending-needs_roll")).toHaveCount(2);
  await page.getByTestId("folder-roll-choose").first().selectOption("4");
  await expect(opts.nth(4)).toHaveText("Roll no 5 · Entered · Not approved");
  await page.getByTestId("folder-skip").first().click();
  await expect(page.getByTestId("folder-pending-needs_roll")).toHaveCount(0);
  await expect(opts.nth(2)).toHaveText("Roll no 3 · Not entered");
});

test("a folder: a picture of another class is held until she confirms, a duplicate is chosen, a roll with answers asks Replace or Keep mine", async ({ page }) => {
  const a = png(21);
  const b = png(22);
  const c = png(23);
  const dup1 = png(24);
  const dup2 = png(25);
  await mockReader(page, new Map<string, Reply>([[sha(a), { cells: RIGHT.map((text) => ({ text: text === "346" ? "347" : text, status: "ok" })) }]]));
  const dir = folderOf({ "3B-roll01.png": b, "3A-roll02.png": c, "3A-roll03.png": dup1, "3A-roll03-copy.png": dup2, "3A-roll04.png": a });
  await startSample(page, { size: 5 });
  // roll 4 already has her own answers
  await roll(page, 4);
  await page.getByTestId("input-1").fill("111");
  await page.getByTestId("folder-input").setInputFiles(dir);
  await expect(page.getByTestId("folder-pending-other_class")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("folder-pending-other_class")).toContainText("class 3B, not 3A");
  await expect(page.getByTestId("folder-pending-duplicate")).toHaveCount(2);
  await expect(page.getByTestId("folder-pending-exists")).toContainText("Roll no 4 already has answers.");
  const opts = page.getByTestId("child-select").locator("option");
  await expect(opts.nth(1)).toHaveText("Roll no 2 · Entered · Not approved"); // the clear one was filled in
  await expect(opts.nth(0)).toHaveText("Roll no 1 · Not entered"); // the other class is not used yet
  // keep mine
  await page.getByTestId("folder-keep").click();
  await roll(page, 4);
  await expect(page.getByTestId("input-1")).toHaveValue("111");
  // the duplicate: use one, the other is skipped
  await page.getByTestId("folder-use-this").first().click();
  await expect(page.getByTestId("folder-pending-duplicate")).toHaveCount(0);
  await expect(opts.nth(2)).toHaveText("Roll no 3 · Entered · Not approved");
  // the other class, used on purpose
  await page.getByTestId("folder-use-anyway").click();
  await expect(opts.nth(0)).toHaveText("Roll no 1 · Entered · Not approved");
});

test("the team's test folder, read in recorded mode with no mock: every sheet is matched by its header and labelled Recorded AI answer", async ({ page }) => {
  test.setTimeout(120_000);
  const dir = fileURLToPath(new URL("../../../demo/test-sheets", import.meta.url));
  await startSample(page, { size: 28 });
  await page.getByTestId("folder-input").setInputFiles(dir);
  await expect(page.getByTestId("folder-summary")).toContainText("10 pictures found, 9 matched to roll numbers, 1 need a roll number.", { timeout: 90_000 });
  await expect(page.getByTestId("folder-summary")).toContainText("1 skipped"); // the folder's README is not a picture
  // one header was read with confidence 0.7, under the 0.8 bar: she chooses its roll number
  await expect(page.getByTestId("roll-counts")).toContainText("9 entered · 0 approved · 0 absent · 19 not entered");
  await expect(page.getByTestId("folder-pending-needs_roll")).toHaveCount(1);
  await expect(page.getByTestId("folder-pending-other_class")).toHaveCount(0); // "SO-3A" and "S0-3A" are both class 3A
  await page.getByTestId("child-select").selectOption("6"); // roll no 7 is sheet H01, all correct
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await expect(page.getByTestId("roll-source")).toHaveText("Recorded AI answer");
  await page.getByTestId("show-sheet").click();
  await expect(page.getByTestId("drawer-image")).toBeVisible();
});

test("a folder: Cancel stops starting new reads; a failed picture shows its reason and Try again", async ({ page }) => {
  const files: Record<string, Buffer> = {};
  const table = new Map<string, Reply>();
  for (let i = 1; i <= 8; i++) {
    const p = png(30 + i);
    files[`3A-roll0${i}.png`] = p;
    table.set(sha(p), { delay: 400 });
  }
  const bad = png(40);
  files["3A-roll09.png"] = bad;
  table.set(sha(bad), { status: 422, delay: 50 });
  const stats = await mockReader(page, table);
  const dir = folderOf(files);
  await startSample(page, { size: 9 });
  await page.getByTestId("folder-input").setInputFiles(dir);
  await expect(page.getByTestId("folder-progress")).toContainText(/Reading \d+ of 9/);
  await page.getByTestId("folder-cancel").click();
  await expect(page.getByTestId("folder-cancel")).toHaveCount(0, { timeout: 20_000 });
  expect(stats.calls).toBeLessThan(9);
  // read the failing one alone, then fix it and try again
  const dir2 = folderOf({ "3A-roll09.png": bad });
  await page.getByTestId("folder-input").setInputFiles(dir2);
  await expect(page.getByTestId("folder-failed")).toHaveCount(1, { timeout: 20_000 });
  await expect(page.getByTestId("folder-failed")).toContainText("could not be used");
  table.set(sha(bad), {});
  await page.getByTestId("folder-retry").click();
  await expect(page.getByTestId("child-select").locator("option").nth(8)).toHaveText("Roll no 9 · Entered · Not approved");
});

test("a folder: the cost limit is said plainly and the rest is left for typing", async ({ page }) => {
  const p = png(50);
  await mockReader(page, new Map<string, Reply>([[sha(p), { status: 503, body: { detail: { needs_typing: true, message: "Reading is paused." } } }]]));
  const dir = folderOf({ "3A-roll01.png": p });
  await startSample(page, { size: 2 });
  await page.getByTestId("folder-input").setInputFiles(dir);
  await expect(page.getByTestId("folder-failed")).toContainText("limit for this session", { timeout: 20_000 });
  await expect(page.getByTestId("folder-retry")).toHaveCount(0);
  await expect(page.getByTestId("input-1")).toBeEditable();
});

test("where a browser cannot choose a folder, the button says Choose pictures and many pictures still work", async ({ page }) => {
  await page.addInitScript(() => {
    delete (HTMLInputElement.prototype as unknown as Record<string, unknown>)["webkitdirectory"];
  });
  const a = png(61);
  const b = png(62);
  await mockReader(page, new Map());
  await startSample(page, { size: 3 });
  await expect(page.getByTestId("folder-button-text")).toHaveText("Choose pictures");
  await expect(page.getByTestId("folder-fallback-note")).toBeVisible();
  await expect(page.getByTestId("pictures-input")).toHaveAttribute("multiple", "");
  await expect(page.getByTestId("pictures-input")).not.toHaveAttribute("webkitdirectory", /.*/);
  await page.getByTestId("pictures-input").setInputFiles([
    { name: "3A-roll01.png", mimeType: "image/png", buffer: a },
    { name: "3A-roll02.png", mimeType: "image/png", buffer: b },
  ]);
  await expect(page.getByTestId("folder-summary")).toContainText("2 pictures found, 2 matched", { timeout: 20_000 });
  await expect(page.getByTestId("child-select").locator("option").nth(1)).toHaveText("Roll no 2 · Entered · Not approved");
});

// ---- states, privacy, accessibility ---------------------------------------------------------------

test("offline: the camera and the folder are disabled with the reason, and typing stays", async ({ page, context }) => {
  await startSample(page, { size: 2 });
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await expect(page.getByTestId("photo-input")).toBeDisabled();
  await expect(page.getByTestId("folder-input")).toBeDisabled();
  await expect(page.getByTestId("add-blocked")).toContainText("needs a connection");
  await page.getByTestId("input-1").fill("346");
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await context.setOffline(false);
});

test("no picture data ends up in any browser storage after a run, and the checkbox state is never sent", async ({ page }) => {
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST") posts.push(`${r.url()} ${(r.postData() ?? "").slice(0, 400)}`);
  });
  await mockReader(page, new Map());
  await startSample(page, { size: 1 });
  await page.getByTestId("photo-input").setInputFiles({ name: "x.png", mimeType: "image/png", buffer: png(70) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await page.getByTestId("missed-subtraction").check();
  await page.getByTestId("approve").click(); // there is a picture to check against: no question
  await finishEntering(page);
  await expect(page).toHaveURL(/#\/cards/);
  const found = await page.evaluate(async () => {
    const hits: string[] = [];
    for (const k of Object.keys(localStorage)) if (/data:image|blob:|iVBOR/.test(localStorage.getItem(k) ?? "")) hits.push(`localStorage:${k}`);
    for (const name of await caches.keys()) for (const r of await (await caches.open(name)).keys()) if (/\.(png|jpe?g)$/i.test(r.url) && !r.url.includes("icon")) hits.push(`cache:${r.url}`);
    const dbs = await indexedDB.databases();
    for (const info of dbs) {
      const db = await new Promise<IDBDatabase>((res) => {
        const o = indexedDB.open(info.name as string);
        o.onsuccess = () => res(o.result);
      });
      for (const store of Array.from(db.objectStoreNames)) {
        const all = await new Promise<unknown[]>((res) => {
          const g = db.transaction(store).objectStore(store).getAll();
          g.onsuccess = () => res(g.result);
        });
        if (all.some((row) => row instanceof Blob || /data:image|iVBOR|\/9j\//.test(JSON.stringify(row)))) hits.push(`indexedDB:${info.name}/${store}`);
      }
      db.close();
    }
    return hits;
  });
  expect(found).toEqual([]);
  expect(posts.filter((p) => /missed|subtraction|place_value/i.test(p))).toEqual([]);
});

test("Hindi and Tamil fit at 360 px with no sideways scroll", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await startSample(page, { size: 3 });
  for (const lang of ["hi", "ta"]) {
    await page.evaluate((l) => localStorage.setItem("cc.lang", l), lang);
    await page.reload();
    await expect(page.getByTestId("missed-group")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, lang).toBeLessThanOrEqual(1);
    const cut = await page.evaluate(() => [...document.querySelectorAll(".missed-box label, .roll-line select, .finish-bar button")].filter((el) => el.scrollWidth > el.clientWidth + 1).length);
    expect(cut, lang).toBe(0);
  }
});

test("axe finds nothing in the entering state, with the drawer open, or in the finish note", async ({ page }) => {
  await mockReader(page, new Map());
  await startSample(page, { size: 2 });
  const run = async () => (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze()).violations.map((v) => `${v.id}: ${v.nodes[0]?.html.slice(0, 80)}`);
  expect(await run()).toEqual([]);
  await page.getByTestId("photo-input").setInputFiles({ name: "x.png", mimeType: "image/png", buffer: png(80) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await page.getByTestId("show-sheet").click();
  expect(await run()).toEqual([]);
});

test("a full keyboard path: the roll list, the boxes, the checkboxes, Approve", async ({ page }) => {
  await startSample(page, { size: 1 });
  await page.getByTestId("input-1").focus();
  for (let q = 0; q < 10; q++) {
    await page.keyboard.type(RIGHT[q] as string);
    if (q < 9) await page.keyboard.press("Enter");
  }
  await expect(page.getByTestId("input-10")).toHaveValue("54");
  await page.getByTestId("missed-addition").focus();
  await page.keyboard.press("Space");
  await expect(page.getByTestId("missed-addition")).toBeChecked();
  for (const id of ["show-sheet", "child-select", "absent", "approve", "finish"]) {
    const size = await page.getByTestId(id).evaluate((el) => {
      const r = (el.closest("label") ?? el).getBoundingClientRect(); // a checkbox is tapped through its label
      return Math.min(r.width, r.height);
    });
    expect(size, id).toBeGreaterThanOrEqual(43.5);
  }
});

test("a wrong paper chosen by mistake: Choose another paper goes back to the list, free before any answer, asking first after", async ({ page }) => {
  await startSample(page, { size: 2 });
  await page.getByTestId("choose-another").click(); // nothing entered yet: no question
  await expect(page.getByTestId("start-check")).toBeVisible();
  await expect(page.getByTestId("paper-select")).toBeVisible();
  await expect(page.getByTestId("paper-attached")).toBeVisible({ timeout: 20_000 }); // the only checked paper is chosen again
  await begin(page, 2);
  await page.getByTestId("input-1").fill("346");
  let asked = "";
  page.once("dialog", (d) => {
    asked = d.message();
    void d.dismiss();
  });
  await page.getByTestId("choose-another").click();
  await expect.poll(() => asked).toContain("clears the 1 roll numbers entered so far");
  await expect(page.getByTestId("input-1")).toHaveValue("346"); // she said no: nothing lost
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("choose-another").click();
  await expect(page.getByTestId("start-check")).toBeVisible();
});

test("the drawer's tools are on one line, its actions are on one line, and the picture gets half the phone's height", async ({ page }) => {
  await mockReader(page, new Map());
  await page.setViewportSize({ width: 390, height: 844 });
  await startSample(page, { size: 2 });
  await page.getByTestId("photo-input").setInputFiles({ name: "x.png", mimeType: "image/png", buffer: png(90) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await page.getByTestId("show-sheet").click();
  const y = async (id: string) => Math.round((await page.getByTestId(id).boundingBox())!.y);
  expect(new Set([await y("drawer-zoom-in"), await y("drawer-zoom-out"), await y("drawer-rotate"), await y("drawer-fit")]).size).toBe(1);
  expect(new Set([await y("drawer-approve"), await y("drawer-reread"), await y("drawer-close-text")]).size).toBe(1);
  const image = (await page.locator(".sheet-drawer-body").boundingBox())!;
  expect(image.height).toBeGreaterThanOrEqual(844 * 0.45); // about half the screen
  expect(image.width).toBeLessThanOrEqual(390);
});

test("while pictures are read, a loader says the AI is working on it", async ({ page }) => {
  const a = png(91);
  const b = png(92);
  await mockReader(page, new Map<string, Reply>([[sha(a), { delay: 1500 }], [sha(b), { delay: 1500 }]]));
  const dir = folderOf({ "3A-roll01.png": a, "3A-roll02.png": b });
  await startSample(page, { size: 3 });
  await page.getByTestId("folder-input").setInputFiles(dir);
  await expect(page.getByTestId("folder-busy")).toContainText("AI is working on it.");
  await expect(page.getByTestId("folder-busy")).toContainText(/Reading \d of 2/);
  await expect(page.getByTestId("folder-busy")).toHaveCount(0, { timeout: 20_000 });
  // and for one photo from the camera
  await mockReader(page, new Map<string, Reply>([[sha(png(93)), { delay: 1500 }]]));
  await page.getByTestId("child-select").selectOption("2");
  await page.getByTestId("photo-input").setInputFiles({ name: "y.png", mimeType: "image/png", buffer: png(93) });
  await expect(page.getByTestId("photo-busy")).toContainText("AI is working on it.");
});

test("an approved sheet is kept for her only if she agreed, comes back after a reload, and she can delete the copy", async ({ page }) => {
  test.setTimeout(120_000);
  const puts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "PUT" && r.url().includes("/api/sheet-keep/")) puts.push(r.url());
  });
  await mockReader(page, new Map());
  await startSample(page, { size: 3 });
  await expect(page.getByTestId("keep-ask")).toContainText("Keep your approved sheets for 60 days?");

  // not now: the approved sheet is not kept
  await page.getByTestId("keep-no").click();
  await expect(page.getByTestId("keep-ask")).toHaveCount(0);
  await page.getByTestId("photo-input").setInputFiles({ name: "a.png", mimeType: "image/png", buffer: png(95) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  await page.getByTestId("approve").click();
  await page.waitForTimeout(800);
  expect(puts).toEqual([]);

  // she agrees (My profile switch), and the next approved sheet is kept
  await page.evaluate(() => {
    const c = JSON.parse(localStorage.getItem("cc.consent") ?? "{}");
    localStorage.setItem("cc.consent", JSON.stringify({ ...c, keep_sheets: true }));
  });
  await page.reload();
  await page.getByTestId("child-select").selectOption("1");
  await page.getByTestId("photo-input").setInputFiles({ name: "b.png", mimeType: "image/png", buffer: png(96) });
  await expect(page.getByTestId("input-1")).toHaveValue("346");
  const stored = page.waitForResponse((r) => r.request().method() === "PUT" && r.url().includes("/api/sheet-keep/"));
  await page.getByTestId("approve").click();
  expect((await stored).status()).toBe(200);
  expect(puts.length).toBe(1);

  // after a reload the picture is gone from memory, but the kept copy opens
  await page.reload();
  await page.getByTestId("child-select").selectOption("1");
  await expect(page.getByTestId("show-sheet")).toBeVisible();
  await page.getByTestId("show-sheet").click();
  await expect(page.getByTestId("drawer-image")).toBeVisible();
  await expect(page.getByTestId("kept-until")).toContainText("A copy is kept for you until");

  // delete it now
  await page.getByTestId("kept-delete").click();
  await expect(page.getByTestId("keep-note")).toContainText("is deleted");
  await page.reload();
  await page.getByTestId("child-select").selectOption("1");
  await expect(page.getByTestId("show-sheet")).toHaveCount(0);
});

test("Clear entered data asks first, then empties every roll number on the same paper and class size", async ({ page }) => {
  await startSample(page, { size: 3 });
  await expect(page.getByTestId("clear-entered")).toBeDisabled(); // nothing to clear yet
  await fillAndApprove(page, RIGHT);
  await roll(page, 2);
  await page.getByTestId("absent").check();
  await expect(page.getByTestId("roll-counts")).toContainText("1 entered · 1 approved · 1 absent · 1 not entered");
  let asked = "";
  page.once("dialog", (d) => {
    asked = d.message();
    void d.dismiss();
  });
  await page.getByTestId("clear-entered").click();
  await expect.poll(() => asked).toContain("clears the 2 roll numbers entered so far");
  await expect(page.getByTestId("roll-counts")).toContainText("1 entered"); // she said no: nothing lost
  page.once("dialog", (d) => void d.accept());
  await page.getByTestId("clear-entered").click();
  await expect(page.getByTestId("roll-counts")).toHaveText("0 entered · 0 approved · 0 absent · 3 not entered");
  await expect(page.getByTestId("child-title")).toHaveText("Roll no 1");
  await expect(page.getByTestId("check-paper-code")).toBeVisible(); // the paper stays
  await page.reload();
  await expect(page.getByTestId("roll-counts")).toHaveText("0 entered · 0 approved · 0 absent · 3 not entered"); // and it is saved
});

test("the camera and the folder buttons sit on one line", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await startSample(page, { size: 2 });
  const cam = (await page.getByTestId("photo-label").boundingBox())!;
  const folder = (await page.getByTestId("folder-label").boundingBox())!;
  expect(Math.abs(cam.y - folder.y)).toBeLessThan(2);
  expect(cam.x + cam.width).toBeLessThanOrEqual(folder.x + 1); // side by side, not stacked
  expect(folder.x + folder.width).toBeLessThanOrEqual(390);
});

test("with DEV_TESTING on, Approve all entered approves every entered roll at once; off, there is no such button", async ({ page }) => {
  await startSample(page, { size: 3 });
  await page.getByTestId("input-1").fill("346");
  await expect(page.getByTestId("next-approve")).toBeEnabled(); // a roll waits for approval...
  await expect(page.getByTestId("approve-all-dev")).toHaveCount(0); // ...but the test server does not set DEV_TESTING
  await page.route("**/api/health", async (route) => {
    const res = await route.fetch();
    await route.fulfill({ response: res, json: { ...(await res.json()), dev_testing: true } });
  });
  await page.reload();
  await page.getByTestId("next-child").click();
  await page.getByTestId("input-1").fill("347");
  await page.getByTestId("approve-all-dev").click(); // no question about the missing pictures
  const pick = page.getByTestId("child-select");
  await expect(pick.locator("option").nth(0)).toContainText("Approved");
  await expect(pick.locator("option").nth(1)).toContainText("Approved");
  await expect(pick.locator("option").nth(2)).toContainText("Not entered");
  await expect(page.getByTestId("approve-all-dev")).toHaveCount(0); // nothing left to approve
});

test("with DEV_TESTING on, a box marks every roll number with nothing entered absent, and unticking it undoes that", async ({ page }) => {
  await startSample(page, { size: 4 });
  await expect(page.getByTestId("absent-rest-dev")).toHaveCount(0); // the test server does not set DEV_TESTING
  await page.route("**/api/health", async (route) => {
    const res = await route.fetch();
    await route.fulfill({ response: res, json: { ...(await res.json()), dev_testing: true } });
  });
  await page.reload();
  await page.getByTestId("input-1").fill("346"); // roll 1 has answers; rolls 2 to 4 have nothing
  const box = page.getByTestId("absent-rest-dev");
  await box.check();
  const opts = page.getByTestId("child-select").locator("option");
  await expect(opts.nth(0)).toContainText("Entered");
  for (const i of [1, 2, 3]) await expect(opts.nth(i)).toContainText("Absent");
  await box.uncheck();
  for (const i of [1, 2, 3]) await expect(opts.nth(i)).toContainText("Not entered");
  await expect(opts.nth(0)).toContainText("Entered"); // the roll with answers is untouched
});
