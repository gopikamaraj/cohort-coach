// The same feature specs, run against a deployed web app (QA_BASE) instead of a local build. No local
// servers start. Specs that need the recorded-mode API or a pilot build are expected to differ; the
// QA summary says which.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  testIgnore: ["screenshots.spec.ts", "pilot.spec.ts"],
  timeout: 90_000,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env["QA_BASE"] ?? "https://cohort-coach-pwa-1097171252131.asia-south1.run.app",
    ...devices["Pixel 5"],
    serviceWorkers: "allow",
    permissions: ["microphone"],
    launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] },
    trace: "off",
  },
});
