import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60000,
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://localhost:8010",
    browserName: "firefox",
    viewport: { width: 1440, height: 980 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  reporter: [["list"], ["json", { outputFile: "../.local/e2e-results.json" }]],
});
