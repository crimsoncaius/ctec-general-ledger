// spec: specs/accounts-fiscal.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Accounts and Fiscal Calendars", () => {
  test("should-enforce-account-and-calendar-boundaries", async ({ adminPage }) => {
    // 1. Inspect the seeded title and retained-earnings accounts.
    await adminPage.getByRole("button", { name: "accounts" }).click();
    const title = adminPage.getByRole("row").filter({ hasText: "9000" });
    const retained = adminPage.getByRole("row").filter({ hasText: "3000" });
    await expect(title.getByLabel("Postable")).toBeDisabled();
    await expect(retained.getByLabel("Active")).toBeDisabled();

    // 2. Enter 19 fiscal periods.
    await adminPage.getByRole("button", { name: "fiscal" }).click();
    await adminPage.getByLabel("Periods").fill("19");
    await expect(adminPage.getByRole("button", { name: "Generate boundaries" })).toBeDisabled();

    // 3. Enter 18 fiscal periods and generate boundaries.
    await adminPage.getByLabel("Periods").fill("18");
    await adminPage.getByRole("button", { name: "Generate boundaries" }).click();
    await expect(adminPage.getByLabel("Label for period 18")).toHaveValue("P18");
    await expect(adminPage.getByLabel("Label for period 19")).toHaveCount(0);
  });
});

