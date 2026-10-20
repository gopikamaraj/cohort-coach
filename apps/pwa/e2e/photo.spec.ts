import { expect, test, type Page } from "@playwright/test";

// Photo of a sheet in the Check page. The reading API is mocked here (the model call itself is
// tested in tests/api/test_sheets.py with a fake model); this proves the phone's side: the photo
// is shrunk and sent with the form id only, the boxes fill in, unsure boxes are marked, the
// teacher corrects one and goes on to the next child, and nothing is stored from the photo.

// A real 8x8 PNG, so the phone's downscaling path runs for real.
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFUlEQVR4nGP88OEDAzbAhFV00EoAADQGAuBmG04kAAAAAElFTkSuQmCC", "base64");

const CELLS = [
  { text: "346", status: "ok" },
  { text: "728", status: "ok" },
  { text: "75", status: "ok" },
  { text: "999", status: "check" },
  { text: "", status: "blank" },
  { text: "", status: "check" },
  { text: "38", status: "ok" },
  { text: "26", status: "ok" },
  { text: "43", status: "ok" },
  { text: "54", status: "ok" },
];

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => (localStorage.clear(), localStorage.setItem("cc.consent", '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}')));
});

async function begin(page: Page) {
  await page.goto("/#/check");
  await page.getByTestId("form-A").click();
}

test("a photo fills the boxes, marks the unsure ones, and she corrects and moves on", async ({ page }) => {
  let sent: { form: string | null; fields: string[]; type: string | undefined; size: number } | undefined;
  await page.route("**/api/sheets/read", async (route) => {
    const req = route.request();
    const body = req.postDataBuffer()?.toString("latin1") ?? "";
    sent = {
      form: /name="form"\r\n\r\n(\w+)/.exec(body)?.[1] ?? null,
      fields: [...body.matchAll(/name="(\w+)"/g)].map((m) => m[1] ?? ""),
      type: /Content-Type: (image\/[\w+]+)/.exec(body)?.[1],
      size: body.length,
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ form: "A", retried: false, cells: CELLS }) });
  });
  await begin(page);
  await page.getByTestId("photo-input").setInputFiles({ name: "sheet.png", mimeType: "image/png", buffer: PNG });

  await expect(page.getByTestId("photo-note")).toContainText("Filled in from the photo");
  await expect(page.getByTestId("box-1")).toContainText("346");
  await expect(page.getByTestId("box-3")).toContainText("75");
  await expect(page.getByTestId("box-4")).toHaveAttribute("data-check", "true");
  await expect(page.getByTestId("box-6")).toHaveAttribute("data-check", "true");
  await expect(page.getByTestId("box-1")).not.toHaveAttribute("data-check", "true");
  await expect(page.getByTestId("box-5")).toContainText("blank");
  await expect(page.getByTestId("box-4")).toHaveAttribute("aria-pressed", "true"); // the first box to check is selected

  // she fixes box 4: it is no longer marked
  await page.getByRole("button", { name: "5", exact: true }).click();
  await page.getByRole("button", { name: "8", exact: true }).click();
  await expect(page.getByTestId("box-4")).toContainText("58");
  await expect(page.getByTestId("box-4")).not.toHaveAttribute("data-check", "true");

  await page.getByTestId("next-child").click();
  await expect(page.getByTestId("child-title")).toContainText("2");
  await expect(page.getByTestId("box-1")).not.toContainText("346");

  // what went to the server: the form id and an image, nothing else, and a JPEG (shrunk)
  expect(sent?.form).toBe("A");
  expect(sent?.fields.sort()).toEqual(["form", "image"]);
  expect(sent?.type).toBe("image/jpeg");

  // nothing from the photo is kept on the phone
  const stored = await page.evaluate(async () => {
    const dbs = await indexedDB.databases();
    let found = false;
    for (const info of dbs) {
      if (!info.name) continue;
      const open = indexedDB.open(info.name);
      await new Promise<void>((resolve) => {
        open.onsuccess = () => {
          const db = open.result;
          for (const name of Array.from(db.objectStoreNames)) {
            if (name === "outbox") {
              const count = db.transaction(name).objectStore(name).count();
              count.onsuccess = () => {
                if (count.result > 0) found = true;
              };
            }
          }
          db.close();
          setTimeout(resolve, 50);
        };
      });
    }
    return found;
  });
  expect(stored).toBe(false);
});

test("when reading fails she is told to type, and her typing still works", async ({ page }) => {
  await page.route("**/api/sheets/read", (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: { needs_typing: true } }) }),
  );
  await begin(page);
  await page.getByTestId("photo-input").setInputFiles({ name: "sheet.png", mimeType: "image/png", buffer: PNG });
  await expect(page.getByTestId("photo-note")).toContainText("Type the answers");
  await page.getByRole("button", { name: "3", exact: true }).click();
  await expect(page.getByTestId("box-1")).toContainText("3");
});

test("offline, the photo is not sent and she is told to type", async ({ page, context }) => {
  let calls = 0;
  await page.route("**/api/sheets/read", async (route) => {
    calls += 1;
    await route.abort();
  });
  await begin(page);
  await context.setOffline(true);
  await page.getByTestId("photo-input").setInputFiles({ name: "sheet.png", mimeType: "image/png", buffer: PNG });
  await expect(page.getByTestId("photo-note")).toContainText("needs a connection");
  expect(calls).toBe(0);
  await context.setOffline(false);
});

test("it only asks before replacing when the child already has digits written", async ({ page }) => {
  const allBlank = Array.from({ length: 10 }, () => ({ text: "", status: "blank" }));
  let reply: unknown[] = allBlank;
  await page.route("**/api/sheets/read", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ form: "A", retried: false, cells: reply }) }),
  );
  const asked: string[] = [];
  page.on("dialog", async (d) => {
    asked.push(d.message());
    await d.accept();
  });
  await begin(page);
  const photo = { name: "sheet.png", mimeType: "image/png", buffer: PNG };
  await page.getByTestId("photo-input").setInputFiles(photo); // nothing written yet
  await expect(page.getByTestId("box-1")).toContainText("blank");
  expect(asked).toHaveLength(0);
  await page.getByTestId("photo-input").setInputFiles(photo); // only blank marks so far: still nothing to lose
  await expect(page.getByTestId("photo-note")).toBeVisible();
  expect(asked).toHaveLength(0);
  reply = CELLS;
  await page.getByTestId("photo-input").setInputFiles(photo);
  await expect(page.getByTestId("box-1")).toContainText("346");
  await page.getByTestId("photo-input").setInputFiles(photo); // now digits are there: she is asked
  await expect.poll(() => asked.length).toBe(1);
  expect(asked[0]).toContain("Replace them");
});
