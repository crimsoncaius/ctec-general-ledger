# Implementation tracker

Last updated: 2026-08-10

| Phase | Status | Exit condition / verification |
|---|---|---|
| Evidence and architecture gate | Complete | Plan and dossier read in full; relevant legacy startup, settings, security, accounts, transaction entry/posting, inquiry, close, integrity, standard reporting, and custom-report code reviewed. |
| 1 — Foundation | Complete | Docker/PostgreSQL, Alembic, FastAPI, React/Vite, sign-in, capability RBAC, company selection, isolated deterministic 12/18-period sample data, and pytest/Vitest/Playwright harnesses verified. |
| 2 — Core GL | Complete | Draft/validate/maker-checker approve/atomic post/inquiry/linked reversal, fixed-decimal currency, fiscal UI, immutability triggers, isolation, rollback, reconciliation, and browser lifecycle verified. |
| 3 — Balances, budgets, close | Complete | Versioned budgets, period-balance reconciliation, integrity checks, close preview, immutable retained-earnings/opening entries, and compensating close controls verified against PostgreSQL. |
| 4 — Standard reporting | Complete | Chart, trial balance, GL listing, transaction/pre-post groups, close, and integrity reports reconcile and share one browser/PDF/CSV/XLSX dataset; saved runs reproduce deterministic digests. |
| 5 — Administration and parity | Complete | Previewed/atomic/repeat-safe account and journal imports, user/role membership maintenance, sequences, saved views, display preferences, marking/bulk/keyboard workflows, audit/operation history, and durable worker job polling verified. |
| 6 — Custom reports | Complete | Typed matrix designer, templates and version conflicts, fixed-decimal formula sandbox, sections/formatting, common-data browser/PDF/CSV/XLSX runs, and isolated legacy conversion flags verified. |
| 7 — Legacy migration | Complete | Canonically hashed read-only DBF snapshots, lineage staging, corrupt-data exceptions, account/ledger reconciliation, atomic empty-target apply, repeatability, isolation, and browser trial workflow verified. |
| Final hardening | Complete | Full regression gates, clean-container build/migrate/seed/login verification, production configuration guardrails, deterministic normal/edge demonstrations, and architecture/operations/security/backup/recovery/user/parity documentation pass. |

## Current work

- None. All modernization phases and exit conditions are complete.

## Remaining phases

- None.

## Accounting and authorization invariants

- Every tenant-owned row carries `company_id`; composite foreign keys prevent cross-company references.
- A request may act in a company only through an active membership and a capability granted by a role in that same company.
- Every journal has at least two lines, exactly one positive side per line, balanced base debits/credits, valid postable accounts, and dates mapped to open fiscal periods.
- Posting creates ledger detail, posting evidence, audit evidence, and balance mutations in one database transaction.
- Posted entries and lines are immutable. Corrections use linked reversing entries.
- Currency and accounting values use fixed decimal types with explicit rounding; binary floats are prohibited.
- Closing appends closing evidence and entries without deleting ledger history.
- Custom-report formulas operate only on typed row/column keys through a Decimal AST allowlist; legacy text and RTF are never executed.
- Migration sources are opened read-only, every staged row retains lineage, and no applied run may bypass exceptions or reconciliation.

## Known risks / evidence gaps

- The authoritative legacy posting, security, currency, DB wrapper, and print modules are missing. Modern behavior follows accounting controls and visible call sites rather than guessing unsafe details.
- Representative legacy DBF files and golden report outputs were not supplied. Migration tooling will include synthetic corrupt fixtures; production cutover reconciliation remains an operational activity requiring read-only copies of real data.
- The legacy executable differs from the supplied source revision and is not a reliable golden oracle.

## Verification log

| Date | Check | Result |
|---|---|---|
| 2026-08-10 | Legacy tree protection baseline | New work isolated under `modern/`; no legacy files modified. |
| 2026-08-10 | Local prerequisites | Docker 29.5.2, Compose 5.1.4, Node 22.14.0, npm 11.6.0, Python 3.12 available. |
| 2026-08-10 | Phase 1–4 migration and regression gates | Revisions `0001_initial`–`0003_reporting` apply; posting/reversal, budgets/close, report reconciliation/reproduction, and PDF/CSV/XLSX integrations pass against PostgreSQL. |
| 2026-08-10 | Phase 5 verification | Revision `0004_preferences`, 11 backend tests, ESLint, TypeScript, 2 Vitest tests, Vite build, and 4 no-retry Chromium workflows pass. |
| 2026-08-10 | Phase 6 schema gate | Revision `0005_custom_reports` applies cleanly from an empty database; current/head/check report no drift. Historical migration metadata is insulated from later ORM fields. |
| 2026-08-10 | Phase 6 backend gate | Ruff formatting/lint, strict mypy, and all 13 PostgreSQL integration tests pass, including formula rejection, optimistic versioning, exports, audit evidence, and company isolation. |
| 2026-08-10 | Phase 6 frontend/build gate | ESLint, TypeScript, 2 Vitest interactions, and the Vite production build pass. |
| 2026-08-10 | Phase 6 browser exit flow | 5 Chromium tests pass without retries; the designer previews, versions, templates, runs, exports PDF, and classifies/imports a safe legacy definition. |
| 2026-08-10 | Phase 7 schema gate | Revision `0006_legacy_migration` applies on live and empty databases; current/head/check report no drift, and the historical `0001` snapshot does not leak later constraints. |
| 2026-08-10 | Phase 7 migration gate | All 16 PostgreSQL tests pass, including repeatable canonical digests, normal and corrupt DBFs, draft/posted mapping, exception CSV, company isolation, atomic apply, and rollback with no partial accounts. |
| 2026-08-10 | Phase 7 browser exit flow | 6 Chromium tests pass without retries; an administrator uploads an in-memory DBF archive, runs a read-only trial, sees reconciliation, and reaches digest-confirmed apply controls. |
| 2026-08-10 | Final backend gate | Ruff format/lint and strict mypy pass; all 18 PostgreSQL integration tests pass with company isolation, draft lifecycle, atomic posting/rollback, close, reports, administration, and migration coverage. |
| 2026-08-10 | Final frontend/browser gate | ESLint, TypeScript, 4 Vitest tests, Vite production build, and all 7 no-retry Chromium workflows pass. |
| 2026-08-10 | Clean Compose exit gate | Fresh isolated volume builds API/worker/web images, migrates to `0006_legacy_migration`, seeds three deterministic companies, starts all four services, authenticates the administrator, and proves the dedicated worker claims and completes a durable integrity job. |
| 2026-08-10 | Final migration drift gate | Alembic current/head both report `0006_legacy_migration`; autogenerate check reports no new operations. |
