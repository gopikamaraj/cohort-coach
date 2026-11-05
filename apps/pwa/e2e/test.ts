// Every test is its own signed-in user. Data now belongs to a user and is kept in the cloud, so one shared
// test nickname would carry the classes, checks and papers entered by earlier tests into every later browser.
// This `test` registers a fresh nickname for each test on both test APIs, starts the browser signed in as it
// and sends it as X-User on every request the test makes. Import `test` and `expect` from here.
import { expect as baseExpect, test as base } from "@playwright/test";
import { beginTest, describeArgs, describeTarget, endTest, note, OVERLAY_ON, overlayScript } from "./overlay";

const ORIGINS = ["http://localhost:4173", "http://localhost:4174"];

export const test = base.extend<{ e2eUser: string; overlay: void }>({
  e2eUser: async ({}, use, testInfo) => {
    const id = `e2e-${testInfo.workerIndex}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    for (const port of [8011, 8012]) {
      try {
        await fetch(`http://localhost:${port}/api/users/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nickname: id }) });
      } catch {
        /* the second API is only needed by the AI-off spec */
      }
    }
    await use(id);
  },
  storageState: async ({ e2eUser }, use) => {
    const user = JSON.stringify({ id: e2eUser, nickname: e2eUser });
    await use({ cookies: [], origins: ORIGINS.map((origin) => ({ origin, localStorage: [{ name: "cc.user", value: user }, { name: "cc.cacheOwner", value: e2eUser }] })) });
  },
  extraHTTPHeaders: async ({ e2eUser }, use) => {
    await use({ "X-User": e2eUser });
  },
  // With E2E_OVERLAY=1 (scripts/e2e_watch.ps1) a panel over the page shows the spec, the progress and each check.
  overlay: [
    async ({ page }, use, testInfo) => {
      if (OVERLAY_ON) {
        await page.addInitScript(overlayScript);
        beginTest(page, `${testInfo.file.split(/[\/]/).pop()} › ${testInfo.title}`);
      }
      await use();
      if (OVERLAY_ON) endTest(testInfo.status !== testInfo.expectedStatus);
    },
    { auto: true },
  ],
});

type Matchers = Record<string, unknown>;
function wrapMatchers(real: Matchers, actual: unknown): Matchers {
  const live = typeof (actual as { page?: unknown })?.page === "function" || typeof (actual as { goto?: unknown })?.goto === "function";
  return new Proxy(real, {
    get(target, prop) {
      const v = Reflect.get(target, prop) as unknown;
      if (prop === "not" && v && typeof v === "object") return wrapMatchers(v as Matchers, actual);
      if (typeof prop !== "string" || !prop.startsWith("to") || typeof v !== "function") return v;
      return (...args: unknown[]) => {
        const text = `${describeTarget(actual)}.${prop}()`;
        const expected = describeArgs(args);
        note({ text, state: "now", expected });
        const fail = (e: unknown): never => {
          const m = (e as { matcherResult?: { actual?: unknown } }).matcherResult;
          note({ text, state: "fail", expected, received: m?.actual === undefined ? String((e as Error).message).split(String.fromCharCode(10))[0] : JSON.stringify(m.actual) });
          throw e;
        };
        let out: unknown;
        try {
          out = (v as (...a: unknown[]) => unknown).apply(target, args);
        } catch (e) {
          return fail(e);
        }
        if (live && out && typeof (out as Promise<unknown>).then === "function") {
          return (out as Promise<unknown>).then((r) => (note({ text, state: "ok", expected }), r), fail);
        }
        note({ text, state: "ok", expected });
        return out;
      };
    },
  });
}

const wrapped = ((actual: unknown, message?: string) => wrapMatchers(baseExpect(actual, message) as unknown as Matchers, actual)) as unknown as typeof baseExpect;
Object.assign(wrapped, baseExpect);
export const expect: typeof baseExpect = OVERLAY_ON ? wrapped : baseExpect;
