// spec: specs/administration-imports-jobs.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Administration, Imports, and Jobs", () => {
  test("@critical should-preview-import-and-run-integrity-job", async ({
    adminPage,
    testData,
  }) => {
    const accountCode = String(
      800000 + (parseInt(testData.namespace.slice(-5), 16) % 99999),
    );

    // 1. Preview an invalid account CSV.
    await adminPage.getByRole("button", { name: "admin", exact: true }).click();
    const accountImport = adminPage
      .locator("article.import-card")
      .filter({ hasText: "Account import" });
    await accountImport.getByLabel("Account CSV").setInputFiles({
      name: `invalid-${testData.namespace}.csv`,
      mimeType: "text/csv",
      buffer: Buffer.from(
        "code,name,account_type,currency_code,postable\nBAD,Invalid,balance_sheet,ZZZ,true\n",
      ),
    });
    await accountImport.getByRole("button", { name: "Preview" }).click();
    await expect(accountImport.getByRole("status")).toHaveText(
      "Preview contains validation exceptions.",
    );
    await expect(accountImport.getByText("unknown currency")).toBeVisible();
    await expect(
      accountImport.getByRole("button", { name: "Apply validated file" }),
    ).toBeDisabled();

    // 2. Preview and apply a uniquely coded valid account CSV.
    await accountImport.getByLabel("Account CSV").setInputFiles({
      name: `valid-${testData.namespace}.csv`,
      mimeType: "text/csv",
      buffer: Buffer.from(
        `code,name,account_type,currency_code,postable\n${accountCode},Imported ${testData.namespace},balance_sheet,SGD,true\n`,
      ),
    });
    await accountImport.getByRole("button", { name: "Preview" }).click();
    await expect(accountImport.getByRole("status")).toHaveText(
      "Preview is valid and ready to apply.",
    );
    await accountImport
      .getByRole("button", { name: "Apply validated file" })
      .click();
    await expect(accountImport.getByRole("status")).toHaveText(
      "1 accounts created; 0 updated.",
    );

    // 3. Run the integrity background operation.
    await adminPage.getByRole("button", { name: "Run integrity job" }).click();
    await expect(
      adminPage
        .getByRole("status")
        .filter({ hasText: "integrity operation completed" }),
    ).toBeVisible();
    await expect(
      adminPage
        .locator(".ds-progress")
        .filter({ hasText: "integrity" })
        .first()
        .getByText("Succeeded"),
    ).toBeVisible();
    await expect(
      adminPage.getByRole("heading", { name: "Audit history" }),
    ).toBeVisible();
  });
});
