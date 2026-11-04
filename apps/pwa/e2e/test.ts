// Every test is its own signed-in user. Data now belongs to a user and is kept in the cloud, so one shared
// test nickname would carry the classes, checks and papers entered by earlier tests into every later browser.
// This `test` registers a fresh nickname for each test on both test APIs, starts the browser signed in as it
// and sends it as X-User on every request the test makes. Import `test` and `expect` from here.
import { expect, test as base } from "@playwright/test";

const ORIGINS = ["http://localhost:4173", "http://localhost:4174"];

export const test = base.extend<{ e2eUser: string }>({
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
});

export { expect };
