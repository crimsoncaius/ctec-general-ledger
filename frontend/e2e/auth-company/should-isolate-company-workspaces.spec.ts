// spec: specs/authentication-company.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Authentication and Company Context", () => {
  test("@critical should-isolate-company-workspaces", async ({ adminPage, testData }) => {
    const description = `Isolated ${testData.namespace}`;

    // 1. Create a uniquely described draft in ACME.
    await adminPage.getByRole("button", { name: "journals" }).click();
    await adminPage.getByLabel("Description", { exact: true }).fill(description);
    await adminPage.getByLabel("Amount").fill("42.25");
    await adminPage.getByRole("button", { name: "Create draft batch" }).click();
    await expect(adminPage.locator("article.batch").filter({ hasText: description })).toBeVisible();

    // 2. Switch to Northstar.
    await adminPage.getByLabel("Company").selectOption({ label: "NORTH · Northstar Services Ltd" });
    await expect(adminPage.getByRole("heading", { name: "Northstar Services Ltd" })).toBeVisible();
    await expect(adminPage.getByText(description)).toHaveCount(0);

    // 3. Switch back to ACME.
    await adminPage.getByLabel("Company").selectOption({ label: "ACME · Acme Trading Pte Ltd" });
    await expect(adminPage.getByRole("heading", { name: "Acme Trading Pte Ltd" })).toBeVisible();
    await expect(adminPage.getByText(description).first()).toBeVisible();
  });
});

