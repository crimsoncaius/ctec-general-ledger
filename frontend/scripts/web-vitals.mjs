import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const modernRoot = resolve(frontendRoot, "..");
const baseURL = process.env.STAGE6_WEB_URL ?? "http://127.0.0.1:25173";
const databaseURL = process.env.STAGE6_DATABASE_URL ??
  "postgresql+psycopg://ctec_stage6:stage6_local_only@127.0.0.1:25432/ctec_gl_stage6";
const parsed = new URL(baseURL);
if (!["127.0.0.1", "localhost", "::1"].includes(parsed.hostname) ||
    ["5173", "8000"].includes(parsed.port)) {
  throw new Error("STAGE6_WEB_URL must be loopback and must not use demonstration ports 5173/8000");
}
const databaseName = new URL(databaseURL).pathname.slice(1);
if (!databaseName.startsWith("ctec_gl_stage6") &&
    !databaseName.startsWith("ctec_gl_perf") &&
    !databaseName.startsWith("ctec_gl_e2e") &&
    !databaseName.startsWith("ctec_gl_test_")) {
  throw new Error(`Refusing non-Stage 6 database ${databaseName}`);
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
await context.addInitScript(() => {
  window.__ctecVitals = { lcp: 0, cls: 0, interactions: [] };
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    window.__ctecVitals.lcp = entries.at(-1)?.startTime ?? window.__ctecVitals.lcp;
  }).observe({ type: "largest-contentful-paint", buffered: true });
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__ctecVitals.cls += entry.value;
    }
  }).observe({ type: "layout-shift", buffered: true });
  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.interactionId) window.__ctecVitals.interactions.push(entry.duration);
      }
    }).observe({ type: "event", buffered: true, durationThreshold: 16 });
  } catch {
    // The result below fails closed if the browser cannot expose interaction timing.
  }
});

const page = await context.newPage();
await page.goto(baseURL, { waitUntil: "domcontentloaded" });
await page.getByRole("heading", { name: "Welcome back" }).waitFor({ state: "visible" });
await page.getByLabel("Email").fill(process.env.STAGE6_ADMIN_EMAIL ?? "admin@example.com");
await page.getByLabel("Password").fill(
  process.env.STAGE6_ADMIN_PASSWORD ?? "CTec-Demo-Admin-2026!",
);
await page.getByRole("button", { name: "Sign in" }).click();
await page.getByRole("heading", { name: "Acme Trading Pte Ltd" }).waitFor({ state: "visible" });
const workspaces = [
  ["accounts", page.getByText("CHART OF ACCOUNTS", { exact: true })],
  ["journals", page.getByRole("heading", { name: "Journal batches", exact: true })],
  ["reports", page.getByRole("heading", { name: "Standard reports", exact: true })],
  ["overview", page.getByText("CONTROLLED BOOKS", { exact: true })],
];
for (const [workspace, ready] of workspaces) {
  await page.getByRole("button", { name: workspace, exact: true }).click();
  await ready.waitFor({ state: "visible" });
}
const values = await page.evaluate(() => window.__ctecVitals);
await browser.close();

const inp = values.interactions.length ? Math.max(...values.interactions) : null;
const failures = [];
if (values.lcp > 2500) failures.push(`LCP ${values.lcp.toFixed(1)} ms exceeded 2500 ms`);
if (values.cls > 0.1) failures.push(`CLS ${values.cls.toFixed(3)} exceeded 0.1`);
if (inp === null) failures.push("Chromium did not expose Event Timing interaction samples");
else if (inp > 200) failures.push(`INP proxy ${inp.toFixed(1)} ms exceeded 200 ms`);
const evidence = {
  passed: failures.length === 0,
  url: baseURL,
  viewport: "1440x900",
  lcp_ms: values.lcp,
  inp_proxy_ms: inp,
  cls: values.cls,
  interaction_samples: values.interactions.length,
  failures,
  note: "Single-session lab gate; production field telemetry remains a separate release control.",
};
const output = resolve(modernRoot, "artifacts", "performance", "web-vitals.json");
await mkdir(dirname(output), { recursive: true });
await writeFile(output, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");
console.log(`Web-vitals gate passed=${evidence.passed}; evidence: ${output}`);
for (const failure of failures) console.error(`FAIL: ${failure}`);
process.exitCode = evidence.passed ? 0 : 1;
