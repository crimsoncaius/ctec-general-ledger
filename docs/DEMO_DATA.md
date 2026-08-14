# Deterministic demonstration data

`python -m app.seed` creates stable modern users, roles, capabilities, and one company, then
imports the repository's read-only `GL_Data` snapshot through the same staged migration service
used by the API. It is idempotent and skips when a user already exists; it never resets or mixes
an existing database.

- **ALCAN** (`ALCAN GENERAL TRADING PTE LTD`): SGD base currency and FY2003, with 12 calendar
  periods from February 2003 through January 2004.
- **Ledger**: 141 accounts, a balanced 35-line opening entry, and one balanced five-line posted
  group with current-period debits and credits of SGD 605.88.
- **Currencies**: legacy `S$` and `US$` identifiers are normalized to `SGD` and `USD`. Original
  source values remain in migration staging; `GLACCNX` supplies available original-currency
  opening amounts.
- **Reports**: all ten `.FMT` sources are preserved. Seven have partial structured conversions
  and three require manual conversion; neither disposition is runnable until reviewed and saved
  as a converted modern report.

The legacy `HOPEN_BAL`, `HBAL_*`, and `HBUG_*` arrays remain in the staged source evidence but are
not turned into invented prior-year journals because the sample has no supporting historical
transaction detail. Legacy plaintext users and passwords are never imported.

Automated backend, Playwright, load, resilience, and Stage 6 environments explicitly use
`python -m app.test_seed`. That test-only seed retains the synthetic ACME/NORTH/EDGE scenarios
needed for multi-company, close, maker-checker, FX, and failure-boundary coverage.
