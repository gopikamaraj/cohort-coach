import { defineConfig, devices } from "@playwright/test";

// Tests run against the production build (`npm run e2e` builds first), because the service
// worker and the offline behaviour only exist there.
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
    trace: "off",
  },
  webServer: {
    command: "npx vite preview --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
