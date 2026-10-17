import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./showcase-e2e",
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["junit", { outputFile: "../outputs/public-demo-tests.xml" }],
  ],
  use: {
    baseURL:
      process.env.REVENUEOS_PUBLIC_DEMO_URL ??
      "http://127.0.0.1:4173/RevenueOS/",
    browserName: "chromium",
  },
  webServer: process.env.REVENUEOS_PUBLIC_DEMO_URL
    ? undefined
    : {
        command: "npm run preview:showcase",
        url: "http://127.0.0.1:4173/RevenueOS/",
        reuseExistingServer: false,
      },
});
