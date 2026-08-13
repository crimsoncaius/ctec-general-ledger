// spec: specs/standard-reports.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Standard Reports", () => {
  test("@critical should-run-reproduce-and-export-standard-report", async ({
    adminPage,
  }) => {
    // 1. Run the chart of accounts in the browser.
    await adminPage.getByRole("button", { name: "reports" }).click();
    await adminPage.getByLabel("Report").selectOption("chart_of_accounts");
    await adminPage.getByRole("button", { name: "Run report" }).click();
    await expect(
      adminPage.getByRole("heading", { name: "Chart of Accounts" }),
    ).toBeVisible();
    await expect(
      adminPage.getByRole("cell", { name: "Cash at Bank" }),
    ).toBeVisible();
    const digest = await adminPage
      .locator(".report-output .ds-digest code")
      .textContent();
    expect(digest).toMatch(/[a-f0-9]{64}/);

    // 2. Reproduce the newest saved run.
    await adminPage.locator(".saved-runs button").first().click();
    await expect(
      adminPage.getByRole("heading", { name: "Chart of Accounts" }),
    ).toBeVisible();
    await expect(
      adminPage.locator(".report-output .ds-digest code"),
    ).toHaveText(digest ?? "");

    // 3. Export the report as PDF, CSV, and Excel.
    for (const [format, extension] of [
      ["pdf", "pdf"],
      ["csv", "csv"],
      ["xlsx", "xlsx"],
    ] as const) {
      await adminPage.getByLabel("Output").selectOption(format);
      const downloadPromise = adminPage.waitForEvent("download");
      await adminPage.getByRole("button", { name: "Run report" }).click();
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(
        new RegExp(`chart_of_accounts-.*\\.${extension}$`),
      );
      await expect(adminPage.getByRole("status")).toContainText(
        `${format.toUpperCase()} export generated`,
      );
    }
  });
});
