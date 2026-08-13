// spec: specs/accounts-fiscal.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Accounts and Fiscal Calendars", () => {
  test("should-maintain-account-and-calendar", async ({ adminPage, testData }) => {
    const suffix = parseInt(testData.namespace.slice(-5), 16);
    const code = String(700000 + (suffix % 99999));
    const yearLabel = `FY-${testData.namespace}`;

    // 1. Create and rename a uniquely coded balance-sheet account.
    await adminPage.getByRole("button", { name: "accounts" }).click();
    await adminPage.getByLabel("Account code").fill(code);
    await adminPage.getByLabel("Account name").fill(`Lifecycle ${testData.namespace}`);
    await adminPage.getByRole("button", { name: "Create account" }).click();
    await expect(adminPage.getByRole("status")).toHaveText("Account created with company-scoped audit evidence.");
    const row = adminPage.getByRole("row").filter({ hasText: code });
    await row.getByLabel(`Name for ${code}`).fill(`Lifecycle revised ${testData.namespace}`);
    await row.getByRole("button", { name: "Save" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(`Account ${code} updated. Posted history remains immutable.`);

    // 2. Generate a uniquely labelled 13-period fiscal year.
    await adminPage.getByRole("button", { name: "fiscal" }).click();
    await adminPage.getByLabel("Year label").fill(yearLabel);
    await adminPage.getByLabel("Periods").fill("13");
    await adminPage.getByRole("button", { name: "Generate boundaries" }).click();
    await expect(adminPage.getByLabel("Label for period 13")).toHaveValue("P13");
    await adminPage.getByRole("button", { name: "Save fiscal year" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(`${yearLabel} created with 13 validated periods.`);
  });
});

