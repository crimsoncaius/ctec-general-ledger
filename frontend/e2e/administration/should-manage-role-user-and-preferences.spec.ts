// spec: specs/administration-imports-jobs.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Administration, Imports, and Jobs", () => {
  test("should-manage-role-user-and-preferences", async ({
    adminPage,
    testData,
  }) => {
    const roleName = `Analyst ${testData.namespace}`;
    const email = `analyst-${testData.namespace}@example.com`;

    // 1. Create a uniquely named least-privilege reporting role and user.
    await adminPage.getByRole("button", { name: "admin", exact: true }).click();
    const roleForm = adminPage
      .locator("form")
      .filter({
        has: adminPage.getByRole("heading", { name: "Create reporting role" }),
      });
    await roleForm.getByLabel("Role name").fill(roleName);
    await roleForm.getByRole("button", { name: "Create role" }).click();
    await expect(
      adminPage
        .getByRole("status")
        .filter({ hasText: `Role ${roleName} created` }),
    ).toBeVisible();
    const userForm = adminPage
      .locator("form")
      .filter({
        has: adminPage.getByRole("heading", { name: "Add company user" }),
      });
    await userForm.getByLabel("Email").fill(email);
    await userForm
      .getByLabel("Display name")
      .fill(`Analyst ${testData.namespace}`);
    await userForm
      .getByLabel("Temporary password")
      .fill("Analyst-E2E-Password-2026!");
    await expect(userForm.getByLabel("Role")).toHaveValue(/.+/);
    await userForm.getByRole("button", { name: "Add user" }).click();
    await expect(
      adminPage
        .getByRole("status")
        .filter({ hasText: "Company membership created" }),
    ).toBeVisible();
    await expect(
      adminPage.getByRole("row").filter({ hasText: email }),
    ).toBeVisible();

    // 2. Change display density and save a ledger view.
    await adminPage.getByLabel("Density").selectOption("compact");
    await adminPage.getByRole("button", { name: "Save display" }).click();
    await expect(
      adminPage
        .getByRole("status")
        .filter({ hasText: "Display preference saved" }),
    ).toBeVisible();
    await adminPage.getByRole("button", { name: "Save ledger view" }).click();
    await expect(
      adminPage.getByRole("status").filter({ hasText: "Saved view created" }),
    ).toBeVisible();
  });
});
