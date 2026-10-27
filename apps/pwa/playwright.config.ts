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
const python = process.env["PYTHON"] ?? venvPython ?? "python";
// A port of its own, so the tests never meet a dev server someone left running on 8000.
const apiPort = "8011";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:4173",
    ...devices["Pixel 5"], // a phone-sized viewport and touch
    serviceWorkers: "allow",
    permissions: ["microphone"],
    launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] },
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
      env: { PILOT_MODE: "0", AI_MODE: "recorded", SPEECH_MODE: "stub", ADMIN_OPEN: "1", JUDGE_MODE: "1", DATABASE_URL: "sqlite:///./e2e.sqlite" },
    },
  ],
});
