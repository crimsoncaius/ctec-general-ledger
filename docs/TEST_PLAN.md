# CTec General Ledger production-release test plan

## Purpose and release policy

This plan qualifies the application in disposable local/CI databases and a production-like
staging environment. The running demonstration stack on ports 5173 and 8000 is read-only test
reference data and must never be the target of stateful automation. Playwright defaults to API
port 18000, web port 15173, and a guarded `ctec_gl_e2e*` database that is recreated for every run.

Release requires zero P0/P1 defects, zero unresolved accounting, authorization, isolation,
immutability, or recovery failures, and approval from accounting, QA, security, operations, and
the release owner. Critical browser tests run with retries disabled. The supported browser is
stable desktop Chrome.

## Stages and gates

| Stage | Sections | Gate |
| --- | --- | --- |
| 1. Infrastructure | Isolated database/ports, deterministic seed and roles, artifacts, coverage, portable commands | Seed smoke reaches only the isolated app; repeated runs recreate deterministic state |
| 2. Preflight | Ruff, mypy, ESLint, TypeScript, unit smoke, builds, Alembic upgrade/drift, OpenAPI contract, production config | Every check passes without ignored warnings |
| 3. Backend/accounting | Authentication, tenant RBAC, accounts/calendars, journals/posting, budgets/close, reports, worker/imports/designer/migration | 90% critical-service branch coverage, 80% overall, no integrity leak or partial commit |
| 4. Frontend | Workspace states, role controls, errors, keyboard/focus/semantics/contrast, three Chrome viewports | 80% overall coverage and no critical accessibility or layout defect |
| 5. Browser workflows | Auth/company, administration, journal lifecycle, budget/close, reports, imports/jobs, designer, migration | Critical and full suites pass twice with retries disabled and independent data |
| 6. Non-functional | SAST/dependencies/DAST, 15-user load and 30-user spike, concurrency, restart/outage recovery | No critical/high finding; latency/error/integrity thresholds met twice |
| 7. Legacy/UAT | Sanitized DBF sets, control-total reconciliation, idempotence/rollback, finance role scripts | Exact reconciliation or finance-approved disposition for every difference |
| 8. Release rehearsal | Immutable candidate, backup/restore, smoke, clean replacement rollback, evidence/sign-off | Restore and rollback proven; complete evidence package and approvals |

## Requirements traceability matrix

The detailed scenarios are implemented in the stage named in the Test column. Evidence paths are
stable so local runs and CI can publish the same artifacts.

| ID | Requirement/control | Test | Evidence | Owner |
| --- | --- | --- | --- | --- |
| SEC-01 | Login, lockout, expiry, disabled users and generic errors | Stage 3 API + Stage 5 auth | Backend XML/HTML, Playwright trace | Engineering/QA |
| SEC-02 | Capability enforcement and maker-checker separation | Stage 3 API + Stage 5 roles | API assertions, audit rows, trace | Security/QA |
| TEN-01 | No cross-company read, write, reference, job, report or migration access | Stage 3 isolation matrix + Stage 5 company switch | DB assertions and traces | Security |
| ACC-01 | Account rules and 1–18-period calendars | Stage 3 domain + Stage 5 administration | Coverage and browser evidence | Accounting |
| JRN-01 | Draft validation, decimal/FX rules and atomic posting | Stage 3 accounting + Stage 5 lifecycle | Exact decimal/rollback assertions | Accounting |
| JRN-02 | Posted detail is immutable; reversal is linked and auditable | Stage 3 trigger/concurrency + Stage 5 inquiry | Trigger assertions and trace | Accounting |
| CLS-01 | Budget versions, close/opening entries, repeat prevention and compensation | Stage 3 close + Stage 5 close | Reconciliation output | Accounting |
| RPT-01 | Standard/custom report formats agree and saved digests reproduce | Stage 3 report contracts + Stage 5 downloads | Digests and retained downloads | Accounting/QA |
| OPS-01 | Jobs claim/retry durably and recover after restart | Stage 3 worker + Stage 6 resilience | Logs, correlation IDs, DB state | Operations |
| IMP-01 | Imports are validated, atomic, repeat-safe and formula-safe | Stage 3 negative paths + Stage 5 imports | API/DB evidence | Security/Accounting |
| MIG-01 | Archives are read-only, bounded, repeatable, isolated and atomic | Stage 3 migration + Stage 7 DBF controls | Dataset checksum/reconciliation | Accounting/QA |
| UI-01 | All workspaces expose accessible loading/empty/error/role states | Stage 4 components/a11y | Frontend coverage and a11y report | QA |
| PERF-01 | p95 reads <750 ms, writes <1.5 s, browser reports <5 s, exports <10 s | Stage 6 load | Load report/query plans | Operations |
| PERF-02 | LCP ≤2.5 s, INP ≤200 ms and CLS ≤0.1 | Stage 6 browser performance | Browser metrics | QA |
| REC-01 | No loss/duplicate/partial posting under outage or concurrency | Stage 6 resilience | DB reconciliation and logs | Operations |
| REL-01 | Backup restores within RTO 4 h; RPO target 24 h; rollback uses clean replacement | Stage 8 rehearsal | Checksums and timed runbook | Operations |
| UAT-01 | Role-based accounting acceptance is recorded and independently approved | Stage 7 UAT checklists | UAT result JSON and approval references | Accounting/QA |
| REL-02 | Release evidence cannot imply missing tests or human approval | Stage 8 manifest validation | Evidence manifest and validation output | Release owner |

## Test data, isolation and evidence

- The application seed supplies stable companies, accounts, 12/18-period calendars, users,
  journals and budgets. The E2E bootstrap adds an isolated restricted viewer. Browser fixtures
  expose administrator, preparer, approver, restricted, and deterministic per-test namespaces.
- `TEST_DATABASE_URL` must name a database starting with `ctec_gl_e2e` for Playwright or
  `ctec_gl_test_` for pytest. Database setup is a command-line test utility, never a public API.
- Override `E2E_API_PORT`, `E2E_WEB_PORT`, `E2E_BASE_URL`, `TEST_DATABASE_URL`,
  `E2E_REUSE_SERVER`, `E2E_SKIP_WEBSERVER`, or `E2E_MANAGE_DATABASE` only for an explicitly
  isolated test environment. Server reuse is false by default.
- Failed browser runs retain trace, screenshot, video, failed API status/correlation IDs and
  downloads under `artifacts/playwright`. Backend/frontend coverage is under
  `artifacts/coverage`; backend XML is `artifacts/coverage/backend.xml` and backend HTML is
  `artifacts/coverage/backend-html`. Web-server stdout/stderr is piped into the Playwright run log.
- Legacy fixtures are sanitized, checksummed and paired with approved source control totals.
  Real financial or personal data is prohibited.

## Local commands

From `modern`, after installing `backend[dev]` and running `npm ci --prefix frontend`:

```text
python scripts/test.py backend
python scripts/test.py frontend
python scripts/test.py e2e-seed
python scripts/test.py all
```

The E2E command recreates and drops only its guarded test database. To inspect configuration
without starting servers or changing data, run `npm --prefix frontend exec playwright test --list`.

## Stage 6 implementation

Stage 6 has a dedicated Compose project, hard URL/database guards, fail-closed scanner inventory,
authenticated ZAP runner, deterministic 100,000-line data loader, smoke/release load profiles,
Chrome web-vital capture, and an API/worker/database recovery drill. The demonstration services on
ports 5173/8000 and database `ctec_gl` are rejected by these tools. Exact prerequisites, commands,
thresholds, safety behavior, and evidence locations are in `docs/NON_FUNCTIONAL_TESTING.md`.

## Stage 7 and 8 implementation

Synthetic legacy profiles, control totals, reconciliation coverage, role-specific UAT, and the
guarded release rehearsal are documented in `docs/RELEASE_REHEARSAL.md` and
`docs/UAT_CHECKLISTS.md`. Restore targets must use the guarded database prefixes; tooling does not
provide destructive downgrade or overwrite operations. Draft evidence generation leaves all
external tests, UAT, approvals, and the release decision explicitly pending.
