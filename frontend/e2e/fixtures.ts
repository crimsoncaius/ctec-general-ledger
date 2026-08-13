import { expect, test as base } from "@playwright/test";
import type { Download, Page } from "@playwright/test";

const apiOrigin = process.env.E2E_API_URL ??
  `http://127.0.0.1:${process.env.E2E_API_PORT ?? "18000"}`;
const parsedApiOrigin = new URL(apiOrigin);
if (
  parsedApiOrigin.port === "8000" &&
  ["127.0.0.1", "localhost", "::1"].includes(parsedApiOrigin.hostname)
) {
  throw new Error("E2E_API_URL/E2E_API_PORT must not target the live local API on port 8000");
}

export const roles = {
  administrator: {
    email: "admin@example.com",
    password: "CTec-Demo-Admin-2026!",
    company: "Acme Trading Pte Ltd",
  },
  preparer: {
    email: "preparer@example.com",
    password: "CTec-Demo-Prepare-2026!",
    company: "Acme Trading Pte Ltd",
  },
  approver: {
    email: "approver@example.com",
    password: "CTec-Demo-Approve-2026!",
    company: "Acme Trading Pte Ltd",
  },
  restricted: {
    email: "restricted@example.com",
    password: "CTec-E2E-Restricted-2026!",
    company: "Acme Trading Pte Ltd",
  },
} as const;

type RoleName = keyof typeof roles;
type SeedState = {
  companies: readonly ["ACME", "NORTH", "EDGE"];
  roles: typeof roles;
};
type Fixtures = {
  seedState: SeedState;
  testData: { namespace: string };
  adminPage: Page;
  preparerPage: Page;
  approverPage: Page;
  restrictedPage: Page;
  failureEvidence: void;
};

function apiUrl(path: string): string {
  return new URL(`/api/v1${path}`, parsedApiOrigin).toString();
}

export async function signInAs(page: Page, role: RoleName): Promise<void> {
  const identity = roles[role];
  await page.goto("/");
  await page.getByLabel("Email").fill(identity.email);
  await page.getByLabel("Password").fill(identity.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: identity.company })).toBeVisible();
}

function namespaceFor(title: string, repeatEachIndex: number): string {
  let hash = 2166136261;
  for (const character of `${title}:${repeatEachIndex}`) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return `e2e-${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

export const test = base.extend<Fixtures>({
  seedState: [async ({ request }, use) => {
    const login = await request.post(apiUrl("/auth/token"), {
      data: { email: roles.administrator.email, password: roles.administrator.password },
    });
    expect(login.ok()).toBeTruthy();
    const token = (await login.json() as { access_token: string }).access_token;
    const me = await request.get(apiUrl("/auth/me"), {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(me.ok()).toBeTruthy();
    const companyCodes = (await me.json() as { companies: { code: string }[] }).companies
      .map((company) => company.code)
      .sort();
    expect(companyCodes).toEqual(["ACME", "EDGE", "NORTH"]);
    await use({ companies: ["ACME", "NORTH", "EDGE"], roles });
  }, { auto: true }],
  testData: async ({}, use, testInfo) => {
    await use({ namespace: namespaceFor(testInfo.titlePath.join("/"), testInfo.repeatEachIndex) });
  },
  adminPage: async ({ page }, use) => { await signInAs(page, "administrator"); await use(page); },
  preparerPage: async ({ page }, use) => { await signInAs(page, "preparer"); await use(page); },
  approverPage: async ({ page }, use) => { await signInAs(page, "approver"); await use(page); },
  restrictedPage: async ({ page }, use) => { await signInAs(page, "restricted"); await use(page); },
  failureEvidence: [async ({ page }, use, testInfo) => {
    const responses: { status: number; url: string; correlationId: string | null }[] = [];
    const downloads: Download[] = [];
    page.on("response", (response) => {
      if (response.url().includes("/api/") && response.status() >= 400) {
        responses.push({
          status: response.status(),
          url: response.url(),
          correlationId: response.headers()["x-correlation-id"] ?? null,
        });
      }
    });
    page.on("download", (download) => downloads.push(download));
    await use();
    if (testInfo.status !== testInfo.expectedStatus) {
      await testInfo.attach("failed-api-responses.json", {
        body: Buffer.from(JSON.stringify(responses, null, 2)),
        contentType: "application/json",
      });
      for (const [index, download] of downloads.entries()) {
        const path = await download.path();
        if (path) await testInfo.attach(`download-${index}-${download.suggestedFilename()}`, { path });
      }
    }
  }, { auto: true }],
});

export { expect };
