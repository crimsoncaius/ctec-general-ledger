// spec: specs/legacy-migration.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";
import { migrationArchive } from "../support/migration-archive";

test.describe("Legacy Migration", () => {
  test("@critical should-stage-reconcile-and-block-nonempty-apply", async ({
    adminPage,
    testData,
  }) => {
    // 1. Upload a balanced DBF snapshot and run a read-only trial.
    await adminPage
      .getByLabel("Company")
      .selectOption({ label: "EDGE · ZZ Edge Cycle Demonstration Ltd" });
    await expect(
      adminPage.getByRole("heading", {
        name: "ZZ Edge Cycle Demonstration Ltd",
      }),
    ).toBeVisible();
    await adminPage.getByRole("button", { name: "admin", exact: true }).click();
    await adminPage.getByLabel("Legacy DBF snapshot").setInputFiles({
      name: `balanced-${testData.namespace}.zip`,
      mimeType: "application/zip",
      buffer: Buffer.from(migrationArchive()),
    });
    await adminPage
      .getByRole("button", { name: "Run read-only trial" })
      .click();
    await expect(
      adminPage
        .getByRole("status")
        .filter({ hasText: "Read-only trial migration reconciled" }),
    ).toBeVisible();
    await expect(
      adminPage.getByText("Balanced", { exact: true }),
    ).toBeVisible();
    await expect(
      adminPage.getByText(/account periods reconcile/),
    ).toBeVisible();
    await expect(adminPage.locator(".migration-result code")).toHaveText(
      /^[a-f0-9]{64}$/,
    );

    // 2. Confirm apply against the seeded non-empty target company.
    await adminPage
      .getByRole("button", { name: "Apply reconciled snapshot" })
      .click();
    const applyDialog = adminPage.getByRole("dialog", {
      name: "Apply legacy migration",
    });
    await applyDialog.getByLabel("Type APPLY to continue").fill("APPLY");
    await applyDialog.getByRole("button", { name: "Apply migration" }).click();
    await expect(
      adminPage
        .getByRole("status")
        .filter({ hasText: "Apply requires an empty target company" }),
    ).toBeVisible();
    await applyDialog.getByRole("button", { name: "Cancel" }).click();
    await adminPage.getByRole("button", { name: "accounts" }).click();
    await expect(
      adminPage
        .getByRole("row")
        .filter({ hasText: "1000" })
        .getByLabel("Name for 1000"),
    ).toHaveValue("Cash at Bank");
  });
});
