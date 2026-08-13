import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const modernRoot = resolve(frontendRoot, "..");
const defaultPython = process.platform === "win32"
  ? resolve(modernRoot, ".venv", "Scripts", "python.exe")
  : resolve(modernRoot, ".venv", "bin", "python");

export function manageDatabase(action) {
  if (process.env.E2E_MANAGE_DATABASE === "false") return;
  const python = process.env.PYTHON ?? (existsSync(defaultPython) ? defaultPython : "python");
  const databaseUrl = process.env.TEST_DATABASE_URL ??
    "postgresql+psycopg://ctec:ctec_local_only@localhost:15432/ctec_gl_e2e";
  const result = spawnSync(
    python,
    ["backend/tests/e2e_database.py", action, "--url", databaseUrl],
    { cwd: modernRoot, env: { ...process.env, TEST_DATABASE_URL: databaseUrl }, encoding: "utf8" },
  );
  if (result.status !== 0) {
    throw new Error(
      `E2E database ${action} failed (${result.status ?? "no exit code"}).\n` +
      `${result.stdout ?? ""}${result.stderr ?? ""}`,
    );
  }
}
