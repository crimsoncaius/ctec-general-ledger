// spec: specs/journal-lifecycle.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Journal Lifecycle", () => {
  test("should-manage-independent-draft-lifecycle", async ({
    adminPage,
    testData,
  }) => {
    const description = `Draft ${testData.namespace}`;
    const revised = `${description} revised`;

    // 1. Create a uniquely described balanced draft.
    await adminPage.getByRole("button", { name: "journals" }).click();
    await adminPage
      .getByLabel("Description", { exact: true })
      .fill(description);
    await adminPage.getByLabel("Amount").fill("125.55");
    await adminPage.getByRole("button", { name: "Create draft batch" }).click();
    const original = adminPage
      .locator("article.batch")
      .filter({ hasText: description })
      .first();
    await expect(original).toBeVisible();
    await expect(original.getByText("Draft", { exact: true })).toBeVisible();

    // 2. Rename and copy the draft.
    await original.getByLabel(/Draft description/).fill(revised);
    await original.getByRole("button", { name: "Save draft" }).click();
    const revisedBatch = adminPage
      .locator("article.batch")
      .filter({ hasText: revised })
      .first();
    await expect(revisedBatch).toBeVisible();
    await revisedBatch.getByRole("button", { name: "Copy" }).click();
    const copied = adminPage
      .locator("article.batch")
      .filter({ hasText: `Copy of ${revised}` })
      .first();
    await expect(copied).toBeVisible();

    // 3. Delete the copy.
    await copied.getByRole("button", { name: "Delete draft" }).click();
    await adminPage
      .getByRole("dialog", { name: "Delete draft journal" })
      .getByRole("button", { name: "Delete draft" })
      .click();
    await expect(copied).toHaveCount(0);
    await expect(revisedBatch).toBeVisible();
  });
});
