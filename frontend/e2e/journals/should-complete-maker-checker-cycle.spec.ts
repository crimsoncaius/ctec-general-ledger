// spec: specs/journal-lifecycle.plan.md
// seed: e2e/seed.spec.ts
import { expect, signInAs, test } from "../fixtures";

test.describe("Journal Lifecycle", () => {
  test("@critical should-complete-maker-checker-cycle", async ({
    preparerPage,
    testData,
  }) => {
    const description = `Maker checker ${testData.namespace}`;
    const reason = `Reviewed correction ${testData.namespace}`;

    // 1. As preparer, create and validate a uniquely described draft.
    await preparerPage.getByRole("button", { name: "journals" }).click();
    await preparerPage
      .getByLabel("Description", { exact: true })
      .fill(description);
    await preparerPage.getByLabel("Amount").fill("315.75");
    await preparerPage
      .getByRole("button", { name: "Create draft batch" })
      .click();
    const prepared = preparerPage
      .locator("article.batch")
      .filter({ hasText: description });
    await prepared.getByRole("button", { name: "Validate" }).click();
    await expect(
      prepared.getByText("Validated", { exact: true }),
    ).toBeVisible();
    await expect(
      prepared.getByRole("button", { name: /Approve|Post/ }),
    ).toHaveCount(0);

    // 2. As approver, approve and post the batch.
    await preparerPage.getByRole("button", { name: "Sign out" }).click();
    await signInAs(preparerPage, "approver");
    await preparerPage.getByRole("button", { name: "journals" }).click();
    const approved = preparerPage
      .locator("article.batch")
      .filter({ hasText: description });
    await approved.getByRole("button", { name: "Approve" }).click();
    await expect(approved.getByText("Approved", { exact: true })).toBeVisible();
    await approved.getByRole("button", { name: "Post" }).click();
    await preparerPage
      .getByRole("dialog", { name: "Post approved journal batch" })
      .getByRole("button", { name: "Post batch" })
      .click();
    await expect(approved.getByText("Posted", { exact: true })).toBeVisible();
    await expect(approved.getByLabel(/Draft description/)).toHaveCount(0);

    // 3. Find the posted entry in inquiry and post a linked reversal.
    await preparerPage.getByRole("button", { name: "inquiry" }).click();
    const entry = preparerPage
      .locator("article.entry-detail")
      .filter({ hasText: description });
    await expect(entry).toBeVisible();
    await entry.getByRole("button", { name: "Reverse" }).click();
    await preparerPage.getByLabel("Reversal reason").fill(reason);
    await preparerPage
      .getByRole("button", { name: "Post linked reversal" })
      .click();
    await expect(
      preparerPage.getByText(new RegExp(`Reversal of .*${reason}`)).first(),
    ).toBeVisible();
  });
});
