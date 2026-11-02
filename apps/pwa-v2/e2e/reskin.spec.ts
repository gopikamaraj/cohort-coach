import { expect, test } from "@playwright/test";

// The v2 re-skin: layout, language fit, tap targets, dark mode, offline, reduced motion.
const MAIN = ["roles", "home", "check", "practice", "cards", "profile", "officer", "assistant", "styleguide"];
const CONSENT = '{"core":true,"counts":true,"practice_ai":true,"share_rehearsal":false,"feedback":true,"v":1,"at":1}';

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate((c) => (localStorage.clear(), localStorage.setItem("cc.consent", c), localStorage.setItem("cc.role", "teacher")), CONSENT);
});

const overflow = (page: import("@playwright/test").Page) =>
  page.evaluate(() => {
    const main = document.querySelector("main") as HTMLElement;
    return { main: main.scrollWidth - main.clientWidth, page: document.documentElement.scrollWidth - innerWidth };
  });

for (const lang of ["en", "hi", "ta"]) {
  for (const size of [{ width: 360, height: 800 }, { width: 1280, height: 800 }]) {
    test(`no sideways scroll in ${lang} at ${size.width} px`, async ({ page }) => {
      await page.setViewportSize(size);
      await page.evaluate((l) => localStorage.setItem("cc.lang", l), lang);
      for (const r of MAIN) {
        await page.goto(`/#/${r}`);
        await page.waitForTimeout(250);
        expect(await overflow(page), `${r} ${lang}`).toEqual({ main: 0, page: 0 });
      }
    });
  }
}

test("text 30 percent longer still fits (no fixed-width buttons)", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  for (const r of ["roles", "home", "check", "profile", "styleguide"]) {
    await page.goto(`/#/${r}`);
    await page.waitForTimeout(250);
    await page.evaluate(() => {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const nodes: Text[] = [];
      while (w.nextNode()) nodes.push(w.currentNode as Text);
      for (const n of nodes) {
        const t = n.textContent ?? "";
        if (t.trim().length > 2 && n.parentElement && !n.parentElement.closest("script,style")) n.textContent = t + t.slice(0, Math.ceil(t.length * 0.3));
      }
    });
    expect(await overflow(page), r).toEqual({ main: 0, page: 0 });
  }
});

test("buttons and links are at least 44 px", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  for (const r of ["roles", "home", "check", "styleguide"]) {
    await page.goto(`/#/${r}`);
    await page.waitForTimeout(250);
    const small = await page.evaluate(() =>
      [...document.querySelectorAll("button, a[href], select")]
        .filter((b) => { const x = b.getBoundingClientRect(); return x.width > 0 && !b.closest(".sr") && (x.height < 43.5 || x.width < 43.5); })
        .map((b) => `${b.tagName}.${b.className}`),
    );
    expect(small, r).toEqual([]);
  }
});

test("the rail shows on a laptop and the bottom bar on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/#/home");
  const rail = await page.locator(".navbar").boundingBox();
  expect(rail?.width ?? 0).toBeGreaterThan(150);
  expect(await page.locator(".navtab-rest").first().isVisible()).toBe(true);
  await page.setViewportSize({ width: 360, height: 800 });
  const bar = await page.locator(".navbar").boundingBox();
  expect((bar?.width ?? 0)).toBeGreaterThan(300);
  expect((bar?.height ?? 999)).toBeLessThan(100);
});

test("dark mode follows the phone and keeps text readable", async ({ browser }) => {
  const ctx = await browser.newContext({ colorScheme: "dark", viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  await page.goto("/#/styleguide");
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(bg).toBe("rgb(15, 20, 20)");
  await ctx.close();
});

test("reduced motion turns transitions off", async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  await page.goto("/#/styleguide");
  await page.locator(".ui-btn").first().waitFor();
  const d = await page.evaluate(() => getComputedStyle(document.querySelector(".ui-btn")!).transitionDuration);
  expect(parseFloat(d)).toBeLessThan(0.01);
  await ctx.close();
});

test("the style guide shows every component and works offline after the first load", async ({ page, context }) => {
  await page.goto("/#/dev/styleguide");
  await expect(page.getByTestId("styleguide")).toBeVisible();
  await page.waitForTimeout(1500); // let the service worker cache the shell
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("styleguide")).toBeVisible();
  await context.setOffline(false);
});
