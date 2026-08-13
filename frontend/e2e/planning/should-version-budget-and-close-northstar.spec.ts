// spec: specs/budgets-close.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Budgets and Close", () => {
  test("@critical should-version-budget-and-close-northstar", async ({
    adminPage,
    testData,
  }) => {
    const scenario = `Forecast ${testData.namespace}`;

    // 1. Switch to Northstar, save a uniquely named budget, then revise its amount.
    await adminPage
      .getByLabel("Company")
      .selectOption({ label: "NORTH · Northstar Services Ltd" });
    await expect(
      adminPage.getByRole("heading", { name: "Northstar Services Ltd" }),
    ).toBeVisible();
    await adminPage.getByRole("button", { name: "planning" }).click();
    await adminPage.getByLabel("Scenario").fill(scenario);
    await adminPage.getByLabel(/Budget amount/).fill("1000.00");
    await adminPage
      .getByRole("button", { name: "Save budget version" })
      .click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Budget version saved with audit history.",
    );
    const budgetRow = adminPage.getByRole("row").filter({ hasText: scenario });
    await expect(
      budgetRow.getByRole("cell", { name: "1000.000000 USD" }),
    ).toBeVisible();
    await adminPage.getByLabel(/Budget amount/).fill("1250.00");
    await adminPage
      .getByRole("button", { name: "Save budget version" })
      .click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Budget version saved with audit history.",
    );
    await expect(
      budgetRow.getByRole("cell", { name: "1250.000000 USD" }),
    ).toBeVisible();

    // 2. Preview the open fiscal year close into the next opening period.
    await adminPage.getByRole("button", { name: "Preview close" }).click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Preview reconciles. Review the lines before execution.",
    );
    await expect(
      adminPage.getByText("Reconciled", { exact: true }),
    ).toBeVisible();
    await expect(
      adminPage.getByRole("button", { name: "Execute non-destructive close" }),
    ).toBeEnabled();

    // 3. Execute the close.
    await adminPage
      .getByRole("button", { name: "Execute non-destructive close" })
      .click();
    await adminPage
      .getByRole("dialog", { name: "Execute fiscal close" })
      .getByRole("button", { name: "Execute close" })
      .click();
    await expect(adminPage.getByRole("status")).toHaveText(
      "Fiscal close posted. Historical periods remain immutable and closed.",
    );
    await expect(
      adminPage
        .getByLabel("Fiscal year")
        .locator("option")
        .filter({ hasText: /FY2026.*closed/ }),
    ).toHaveAttribute("disabled", "");
  });
});
