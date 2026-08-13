// spec: specs/authentication-company.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Authentication and Company Context", () => {
  test("@critical should-lock-new-user-after-five-failures", async ({
    adminPage,
    testData,
  }) => {
    const email = `${testData.namespace}@example.com`;
    const password = "Unique-E2E-Password-2026!";

    // 1. Sign in as an administrator and create a uniquely named company user.
    await adminPage.getByRole("button", { name: "admin", exact: true }).click();
    const userForm = adminPage
      .locator("form")
      .filter({
        has: adminPage.getByRole("heading", { name: "Add company user" }),
      });
    await expect(userForm.getByLabel("Role")).toBeEnabled();
    await userForm.getByLabel("Email").fill(email);
    await userForm
      .getByLabel("Display name")
      .fill(`Locked user ${testData.namespace}`);
    await userForm.getByLabel("Temporary password").fill(password);
    await userForm.getByLabel("Role").selectOption({ label: "Preparer" });
    await userForm.getByRole("button", { name: "Add user" }).click();
    await expect(
      adminPage
        .getByRole("status")
        .filter({ hasText: "Company membership created" }),
    ).toBeVisible();

    // 2. Sign out and submit the new email with an incorrect password five times.
    await adminPage.getByRole("button", { name: "Sign out" }).click();
    await adminPage.getByLabel("Email").fill(email);
    await adminPage.getByLabel("Password").fill("incorrect-password");
    for (let attempt = 0; attempt < 5; attempt += 1) {
      await adminPage.getByRole("button", { name: "Sign in" }).click();
      await expect(adminPage.getByRole("alert")).toHaveText(
        "Invalid credentials",
      );
    }

    // 3. Submit the correct password.
    await adminPage.getByLabel("Password").fill(password);
    await adminPage.getByRole("button", { name: "Sign in" }).click();
    await expect(adminPage.getByRole("alert")).toHaveText(
      "Account is temporarily locked",
    );
    await expect(
      adminPage.getByRole("heading", { name: "Acme Trading Pte Ltd" }),
    ).toHaveCount(0);
  });
});
