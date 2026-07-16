import { expect, test } from "@playwright/test";

/**
 * Smoke: register workspace → dashboard → create program.
 * Requires a running web + API (see CI e2e job or local docker).
 */
test("login path via register then create program", async ({ page }) => {
  const stamp = Date.now();
  const slug = `e2e-${stamp}`;
  const email = `e2e.${stamp}@example.com`;
  const password = "SecurePass123!";

  await page.goto("/register");
  await page.getByLabel("Organization name").fill(`E2E Org ${stamp}`);
  await page.getByLabel("Slug").fill(slug);
  await page.getByLabel("First name").fill("E2E");
  await page.getByLabel("Last name").fill("Tester");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel(/Password/).fill(password);
  await page.getByLabel("Country code").fill("KE");
  await page.getByRole("button", { name: /Create workspace/i }).click();

  await expect(page).toHaveURL(/\/app/, { timeout: 30_000 });
  await expect(page.getByText(/MEAL|Dashboard|ImpactFlow/i).first()).toBeVisible();

  await page.goto("/app/programs");
  await page.getByLabel("Name").fill(`E2E Program ${stamp}`);
  await page.getByRole("button", { name: /Create program/i }).click();
  await expect(page.getByText(`E2E Program ${stamp}`)).toBeVisible({ timeout: 15_000 });
});
