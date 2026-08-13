// spec: specs/custom-reports.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Custom Reports", () => {
  test("should-design-version-export-and-convert-report", async ({
    adminPage,
    testData,
  }) => {
    const reportName = `Statement ${testData.namespace}`;
    const legacyName = `Legacy ${testData.namespace}`;

    // 1. Preview and save a uniquely named reusable report.
    await adminPage.getByRole("button", { name: "designer" }).click();
    await adminPage.getByLabel("Definition name").first().fill(reportName);
    await adminPage.getByLabel("Reusable template").check();
    await adminPage.getByRole("button", { name: "Preview draft" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Preview calculated with fixed-decimal ledger and budget values.",
    );
    await expect(
      adminPage.getByRole("heading", { name: /Management statement/ }),
    ).toBeVisible();
    await adminPage.getByRole("button", { name: "Save definition" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Report saved as version 1.",
    );
    await expect(
      adminPage.getByRole("button", { name: "Create working copy" }),
    ).toBeVisible();

    // 2. Run the saved report and export PDF and Excel.
    await adminPage.getByRole("button", { name: "Run saved" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Browser report generated and audited.",
    );
    for (const [button, extension] of [
      ["PDF", "pdf"],
      ["Excel", "xlsx"],
    ] as const) {
      const downloadPromise = adminPage.waitForEvent("download");
      await adminPage.getByRole("button", { name: button }).click();
      expect((await downloadPromise).suggestedFilename()).toMatch(
        new RegExp(`custom-report-.*\\.${extension}$`),
      );
    }

    // 3. Analyze and import a compatible legacy definition.
    await adminPage.getByLabel("Definition name").last().fill(legacyName);
    await adminPage.getByRole("button", { name: "Analyze safely" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Legacy definition classified as compatible.",
    );
    await expect(adminPage.locator(".conversion.compatible")).toContainText(
      "Compatible",
    );
    await adminPage.getByRole("button", { name: "Import with status" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Legacy report imported with compatible status.",
    );
  });
});
