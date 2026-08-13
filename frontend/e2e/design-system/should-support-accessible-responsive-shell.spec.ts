// spec: docs/DESIGN_SYSTEM_ADOPTION.md
// seed: e2e/seed.spec.ts
import { expect, test } from "../fixtures";

test.describe("Design system accessibility", () => {
  test("should-support-keyboard-reduced-motion-zoom-and-narrow-layouts", async ({
    adminPage,
  }) => {
    await adminPage.emulateMedia({ reducedMotion: "reduce" });
    await expect(
      adminPage.getByRole("heading", { name: "Ledger overview" }),
    ).toBeVisible();

    const transitionDuration = await adminPage
      .getByRole("button", { name: "Refresh" })
      .first()
      .evaluate((element) => getComputedStyle(element).transitionDuration);
  expect(
    transitionDuration
      .split(",")
      .every((duration) => duration.trim() === "0s"),
  ).toBe(true);

    await adminPage.keyboard.press("Tab");
    await expect
      .poll(() =>
        adminPage.evaluate(
          () =>
            document.activeElement !== document.body &&
            document.activeElement instanceof HTMLElement &&
            document.activeElement.matches(":focus-visible"),
        ),
      )
      .toBe(true);

    await adminPage.setViewportSize({ width: 640, height: 800 });
    await expect
      .poll(() =>
        adminPage.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
      )
      .toBe(true);

    await adminPage.evaluate(() => {
      document.documentElement.style.zoom = "2";
    });
    await expect(
      adminPage.getByRole("button", { name: "journals", exact: true }),
    ).toBeVisible();
    await adminPage
      .getByRole("button", { name: "journals", exact: true })
      .click();
    await expect(
      adminPage.getByRole("heading", {
        name: "Journal preparation and approval",
      }),
    ).toBeVisible();
  });
});
