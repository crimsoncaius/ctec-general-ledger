import { defineConfig, devices } from "@playwright/test";

const apiPort = process.env.E2E_API_PORT ?? "18000";
const webPort = process.env.E2E_WEB_PORT ?? "15173";
const apiOrigin = `http://127.0.0.1:${apiPort}`;
const webOrigin = `http://127.0.0.1:${webPort}`;
const baseURL = process.env.E2E_BASE_URL ?? webOrigin;
const testDatabaseUrl =
  process.env.TEST_DATABASE_URL ??
  "postgresql+psycopg://ctec:ctec_local_only@localhost:15432/ctec_gl_e2e";
const reuseExistingServer = process.env.E2E_REUSE_SERVER === "true";
const skipWebServer = process.env.E2E_SKIP_WEBSERVER === "true";
const python = process.env.PYTHON ??
  (process.platform === "win32" ? "..\\.venv\\Scripts\\python.exe" : "../.venv/bin/python");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.E2E_DIAGNOSTIC_RETRIES === "true" ? 1 : 0,
  outputDir: "../artifacts/playwright/test-results",
  globalSetup: "./e2e/global-setup.mjs",
  globalTeardown: "./e2e/global-teardown.mjs",
  reporter: [
    ["list"],
    ["html", { outputFolder: "../artifacts/playwright/report", open: "never" }],
    ["junit", { outputFile: "../artifacts/playwright/results.xml" }],
  ],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    acceptDownloads: true,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: skipWebServer
    ? undefined
    : [
        {
          command: `${python} -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port ${apiPort}`,
          url: `${apiOrigin}/health`,
          env: {
            CORS_ORIGINS: webOrigin,
            DATABASE_URL: testDatabaseUrl,
            ENVIRONMENT: "test",
            INLINE_OPERATION_JOBS: "true",
            JWT_SECRET: "e2e-only-secret-that-is-longer-than-thirty-two-characters",
          },
          reuseExistingServer,
          timeout: 60_000,
          stdout: "pipe",
          stderr: "pipe",
        },
        {
          command: `npm run dev -- --host 127.0.0.1 --port ${webPort} --strictPort`,
          url: webOrigin,
          env: { VITE_API_URL: `${apiOrigin}/api/v1` },
          reuseExistingServer,
          timeout: 60_000,
          stdout: "pipe",
          stderr: "pipe",
        },
      ],
});
