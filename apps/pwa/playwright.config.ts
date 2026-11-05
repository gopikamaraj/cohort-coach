import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

// Tests run against the production build (`npm run e2e` builds first), because the service
// worker and the offline behaviour only exist there. The API runs in recorded mode: the
// Practice Class replays a rehearsal recorded live on 2026-10-17 (ai/fixtures/recorded), so no
// test calls a paid API. Its log goes to e2e-api.log so a test can check it holds no transcript.
// PYTHON wins; else the repo's own virtual environment (absolute, because the API starts from the
// repo root); else whatever `python` is on the PATH.
const venvPython = ["Scripts/python.exe", "bin/python"]
  .map((p) => path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../.venv", p))
  .find((p) => existsSync(p));
export const E2E_USER = "e2e tester";
const python = process.env["PYTHON"] ?? venvPython ?? "python";
// A port of its own, so the tests never meet a dev server someone left running on 8000.
const apiPort = "8011";
// A second API with the AI switched off (AI_MODE=off: every call fails as if the service were
// unreachable) and a second preview pointed at it, for e2e/demo-path-ai-off.spec.ts.
const offApiPort = "8012";
const SERVER_ENV = { SHEETS_LOCAL_STORE: "1", PILOT_MODE: "0", SPEECH_MODE: "stub", ADMIN_OPEN: "1", JUDGE_MODE: "1", RATE_LIMIT_PRACTICE_SESSION_PER_MIN: "0", RATE_LIMIT_PRACTICE_TURN_PER_MIN: "0", RATE_LIMIT_PRACTICE_VOICE_PER_MIN: "0", RATE_LIMIT_PRACTICE_WATCH_PER_MIN: "0", RATE_LIMIT_SHEETS_READ_PER_MIN: "0", RATE_LIMIT_ASSISTANT_PER_MIN: "0", RETRIEVAL: "off", PRACTICE_SKIP_CHECKER: "0", PRACTICE_AI_INTENTS: "all", PILOT_DEMO: "0", DEV_TESTING: "0", SIMULATOR_MODEL: "legacy" };

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts", // registers the tests' user on both APIs
  use: {
    baseURL: "http://localhost:4173",
    // Every request carries the test user (the API needs a signed-in user for every route), and the browser starts
    // signed in as the same user. Tests of sign-in itself clear it.
    extraHTTPHeaders: { "X-User": E2E_USER },
    storageState: { cookies: [], origins: ["http://localhost:4173", "http://localhost:4174"].map((origin) => ({ origin, localStorage: [{ name: "cc.user", value: JSON.stringify({ id: E2E_USER, nickname: E2E_USER }) }, { name: "cc.cacheOwner", value: E2E_USER }] })) },
    ...devices["Pixel 5"], // a phone-sized viewport and touch
    serviceWorkers: "allow",
    permissions: ["microphone"],
    launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"], slowMo: Number(process.env["E2E_SLOWMO"] ?? 0) },
    trace: "off",
  },
  webServer: [
    {
      command: "npx vite preview --port 4173 --strictPort",
      url: "http://localhost:4173",
      reuseExistingServer: true,
      timeout: 60_000,
      env: { API_PORT: apiPort },
    },
    {
      command: `"${python}" -m uvicorn services.api.main:app --port ${apiPort} --log-level info > e2e-api.log 2>&1`,
      cwd: "../..",
      url: `http://localhost:${apiPort}/api/health`,
      reuseExistingServer: true,
      timeout: 60_000,
      env: { ...SERVER_ENV, AI_MODE: "recorded", DATABASE_URL: "sqlite:///./e2e.sqlite", PAPER_IMPORT_DIR: "./e2e-imports" },
    },
    {
      command: `"${python}" -m uvicorn services.api.main:app --port ${offApiPort} --log-level warning > e2e-api-off.log 2>&1`,
      cwd: "../..",
      url: `http://localhost:${offApiPort}/api/health`,
      reuseExistingServer: true,
      timeout: 60_000,
      env: { ...SERVER_ENV, AI_MODE: "off", DATABASE_URL: "sqlite:///./e2e-off.sqlite", PAPER_IMPORT_DIR: "./e2e-imports-off" },
    },
    {
      command: "npx vite preview --port 4174 --strictPort",
      url: "http://localhost:4174",
      reuseExistingServer: true,
      timeout: 60_000,
      env: { API_PORT: offApiPort },
    },
  ],
});
