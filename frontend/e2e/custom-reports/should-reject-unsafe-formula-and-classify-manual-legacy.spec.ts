// spec: specs/custom-reports.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Custom Reports", () => {
  test("@critical should-reject-unsafe-formula-and-classify-manual-legacy", async ({ adminPage, testData }) => {
    // 1. Replace a formula with an unsafe function call and preview.
    await adminPage.getByRole("button", { name: "designer" }).click();
    await adminPage.getByLabel("Formula", { exact: true }).first().fill("process.exit()");
    await adminPage.getByRole("button", { name: "Preview draft" }).click();
    await expect(adminPage.getByRole("status")).toHaveText("Only abs, min, max, and round functions are allowed");
    await expect(adminPage.locator(".custom-preview")).toHaveCount(0);

    // 2. Analyze a legacy definition with unsupported constructs.
    await adminPage.getByLabel("Definition name").last().fill(`Manual ${testData.namespace}`);
    await adminPage.getByLabel("Legacy matrix specification").fill("A: [C1%R1]\n0: ^unsupported");
    await adminPage.getByRole("button", { name: "Analyze safely" }).click();
    await expect(adminPage.getByRole("status")).toHaveText("Legacy definition classified as manual.");
    await expect(adminPage.locator(".conversion.manual")).toContainText("manual");
    await expect(adminPage.locator(".conversion.manual li")).not.toHaveCount(0);
  });
});
