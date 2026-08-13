# Deterministic demonstration data

`python -m app.seed` creates stable UUIDs, users, roles, capabilities, companies, calendars, and
accounts. It is idempotent and skips when a user already exists.

- **ACME**: 12-period current/next fiscal years and an empty ledger for guided entry, approval,
  posting, reversal, reporting, imports, and migration trials.
- **NORTH**: 18-period current/next fiscal years and an empty ledger used to demonstrate company
  isolation and a full close workflow without interfering with ACME.
- **EDGE** (`ZZ Edge Cycle Demonstration Ltd`, administrator only): an 18-period edge dataset with
  an SGD cash sale, EUR expense at a fixed 1.5 rate, an accrual and next-period linked reversal,
  approved revenue/expense budgets across 18 periods, a non-destructive FY2026 close and FY2027
  opening, and a pending draft for maker-checker review.

All monetary values are decimal strings/`Decimal`; base debits equal credits and period balances
are produced by the same atomic posting service used by the API. Dates and business values are
fixed. Runtime audit/post timestamps and generated reversal sequence identifiers reflect the seed
execution time, but do not change the accounting result.

The migration tests generate DBF bytes deterministically for a clean normal cutover, draft groups,
duplicate accounts, orphan transactions, unbalanced groups, unsafe archive paths, and an apply
failure after staging. No real legacy data is opened or mutated.
