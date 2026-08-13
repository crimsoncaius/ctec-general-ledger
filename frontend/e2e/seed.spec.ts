import { expect, test } from "./fixtures";

test("isolated deterministic seed is available to browser tests", async ({
  adminPage,
  seedState,
  testData,
}) => {
  expect(seedState.companies).toEqual(["ACME", "NORTH", "EDGE"]);
  expect(testData.namespace).toMatch(/^e2e-[0-9a-f]{8}$/);
  await expect(adminPage.getByRole("heading", { name: "Acme Trading Pte Ltd" })).toBeVisible();
  await expect(adminPage.getByLabel("Company")).toContainText("Northstar Services Ltd");
});
