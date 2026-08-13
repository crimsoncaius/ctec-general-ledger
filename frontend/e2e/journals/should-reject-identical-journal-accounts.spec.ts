// spec: specs/journal-lifecycle.plan.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Journal Lifecycle", () => {
  test("should-reject-identical-journal-accounts", async ({ preparerPage, testData }) => {
    const description = `Invalid same account ${testData.namespace}`;

    // 1. Choose the same account for debit and credit and submit the composer.
    await preparerPage.getByRole("button", { name: "journals" }).click();
    await preparerPage.getByLabel("Description", { exact: true }).fill(description);
    const debit = preparerPage.getByLabel("Debit account");
    const firstDebitOption = debit.locator("option").first();
    await expect(firstDebitOption).toBeAttached();
    const accountId = await firstDebitOption.getAttribute("value");
    expect(accountId).toBeTruthy();
    await preparerPage.getByLabel("Credit account").selectOption({ value: accountId! });
    await preparerPage.getByRole("button", { name: "Create draft batch" }).click();
    await expect(preparerPage.getByRole("alert")).toHaveText("Choose a period and two different accounts.");
    await expect(preparerPage.locator("article.batch").filter({ hasText: description })).toHaveCount(0);
  });
});
