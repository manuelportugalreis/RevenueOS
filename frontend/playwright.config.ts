import { defineConfig } from "@playwright/test";
const evidence = process.env.REVENUEOS_EVIDENCE_DIR ?? "../outputs";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [
    ["list"],
    ["junit", { outputFile: `${evidence}/dashboard-browser-tests.xml` }],
  ],
  use: {
    baseURL: "http://127.0.0.1:8000",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
  timeout: 45000,
});
