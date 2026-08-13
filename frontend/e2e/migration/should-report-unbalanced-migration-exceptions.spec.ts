// spec: specs/legacy-migration.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";
import { migrationArchive } from "../support/migration-archive";

test.describe("Legacy Migration", () => {
  test("should-report-unbalanced-migration-exceptions", async ({
    adminPage,
    testData,
  }) => {
    // 1. Upload an unbalanced DBF snapshot and run a read-only trial.
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
      name: `unbalanced-${testData.namespace}.zip`,
      mimeType: "application/zip",
      buffer: Buffer.from(migrationArchive({ unbalanced: true })),
    });
    await adminPage
      .getByRole("button", { name: "Run read-only trial" })
      .click();
    await expect(
      adminPage.getByRole("status").filter({ hasText: "blocking exceptions" }),
    ).toBeVisible();
    await expect(
      adminPage.getByText("Difference", { exact: true }),
    ).toBeVisible();
    await expect(
      adminPage.getByText("Global posted ledger is unbalanced"),
    ).toBeVisible();
    await expect(adminPage.getByLabel("Type APPLY to continue")).toHaveCount(0);

    // 2. Download the exception report.
    const downloadPromise = adminPage.waitForEvent("download");
    await adminPage
      .getByRole("button", { name: "Download exceptions" })
      .click();
    expect((await downloadPromise).suggestedFilename()).toMatch(
      /^migration-.*-exceptions\.csv$/,
    );
  });
});
