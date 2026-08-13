// spec: specs/authentication-company.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Authentication and Company Context", () => {
  test("@critical should-enforce-restricted-navigation", async ({ restrictedPage }) => {
    const primary = restrictedPage.getByRole("navigation", { name: "Primary" });

    // 1. Sign in as the restricted viewer.
    for (const name of ["overview", "accounts", "journals", "inquiry", "fiscal"]) {
      await expect(primary.getByRole("button", { name })).toBeVisible();
    }
    for (const name of ["planning", "reports", "designer", "admin"]) {
      await expect(primary.getByRole("button", { name })).toHaveCount(0);
    }

    // 2. Open accounts, journals, and inquiry.
    await primary.getByRole("button", { name: "accounts" }).click();
    await expect(restrictedPage.getByRole("button", { name: "Create account" })).toHaveCount(0);
    await expect(restrictedPage.getByRole("button", { name: "Save", exact: true })).toHaveCount(0);
    await primary.getByRole("button", { name: "journals" }).click();
    await expect(restrictedPage.getByRole("heading", { name: "Balanced journal" })).toHaveCount(0);
    await expect(restrictedPage.getByRole("button", { name: /Validate|Approve|Post/ })).toHaveCount(0);
    await primary.getByRole("button", { name: "inquiry" }).click();
    await expect(restrictedPage.getByRole("button", { name: "Reverse" })).toHaveCount(0);
  });
});

