import { test, expect, Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
const evidence = process.env.REVENUEOS_EVIDENCE_DIR ?? "../outputs";

async function login(page: Page, user = "executive") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(user);
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.REVENUEOS_DEMO_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Revenue command center" }),
  ).toBeVisible();
  await expect(
    page.getByText("Historical synthetic snapshot.", { exact: false }),
  ).toBeVisible();
}

test("executive to cited draft to exact human approval, then logout", async ({
  page,
  browser,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page);
  await expect(
    page.getByText("Synthetic demonstration", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "€4,000.20", exact: true }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: `${evidence}/RevenueOS-Dashboard-Desktop.png`,
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Lead priorities", exact: true })
    .click();
  const reference = JSON.parse(
    readFileSync("../work/dashboard-demo-reference.json", "utf8"),
  );
  const row = page
    .getByRole("row")
    .filter({ hasText: reference.lead_id.slice(0, 8) });
  await row.getByRole("button").click();
  const submitted = page.waitForRequest(
    (request) =>
      request.url().endsWith("/api/workflows") && request.method() === "POST",
  );
  await page
    .getByRole("button", { name: "Prepare cited recommendation" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Recommendation: contact" }),
  ).toBeVisible();
  const originalRequest = await submitted;
  const csrf = (await (await page.request.get("/api/session")).json()).csrf;
  const requestKey = originalRequest.headers()["idempotency-key"];
  expect(requestKey).toMatch(/^[0-9a-f-]{36}$/);
  const original = await (await originalRequest.response())!.json();
  const replay = await page.request.post("/api/workflows", {
    data: originalRequest.postDataJSON(),
    headers: {
      Origin: "http://127.0.0.1:8000",
      "X-CSRF-Token": csrf,
      "Idempotency-Key": requestKey,
    },
  });
  expect(replay.status()).toBe(200);
  expect((await replay.json()).workflow_id).toBe(original.workflow_id);
  await page
    .getByRole("button", { name: "View supporting citation 1" })
    .click();
  await expect(
    page.getByRole("region", { name: "Source evidence" }),
  ).toContainText("configuration checklist");
  await page.getByRole("button", { name: "Close source" }).click();
  await page.getByRole("button", { name: "Approvals", exact: true }).click();
  await expect(
    page.getByText("Your account is not assigned as a reviewer.", {
      exact: false,
    }),
  ).toBeVisible();
  const reviewer = await browser.newContext();
  const review = await reviewer.newPage();
  await login(review, "reviewer");
  await review.getByRole("button", { name: "Approvals", exact: true }).click();
  await review
    .getByRole("button", { name: /^Inspect / })
    .first()
    .click();
  await expect(
    review.getByText("lead1@one.example", { exact: false }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page: review }).analyze()).violations).toEqual(
    [],
  );
  await review.screenshot({
    path: `${evidence}/RevenueOS-Dashboard-Approval.png`,
    fullPage: true,
  });
  await review.getByRole("button", { name: "Approve this version" }).click();
  await expect(
    review.getByText("Version approved. No message was sent.", { exact: true }),
  ).toBeVisible();
  await review.getByRole("button", { name: "Evaluation", exact: true }).click();
  await expect(
    review.getByRole("heading", { name: "Independent quality review pending" }),
  ).toBeVisible();
  await expect(
    review.getByRole("heading", {
      name: "Recommendation quality gate: failed",
    }),
  ).toBeVisible();
  await reviewer.close();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  expect((await page.request.get("/api/dashboard")).status()).toBe(401);
  expect(errors).toEqual([]);
});

test("mobile navigation, forbidden origin, expired session and API error", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Recommendation quality gate: failed" }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: `${evidence}/RevenueOS-Dashboard-Mobile.png`,
    fullPage: true,
  });
  expect(
    (
      await page.request.post("/api/workflows", {
        headers: { Origin: "https://attacker.example" },
        data: {},
      })
    ).status(),
  ).toBe(403);
  await page.route("**/api/dashboard", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "service_unavailable", request_id: "test-outage" },
      }),
    }),
  );
  await page.getByRole("button", { name: "Refresh data" }).click();
  await expect(page.getByRole("alert")).toContainText("test-outage");
  await page.unroute("**/api/dashboard");
  await page.context().clearCookies();
  await page.getByRole("button", { name: "Refresh data" }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
});
