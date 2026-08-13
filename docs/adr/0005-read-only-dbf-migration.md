# ADR 0005: Read-only DBF staging and atomic cutover

Status: Accepted — 2026-08-10

## Context

Legacy company data consists of mutable directory-scoped DBF/CodeBase tables without foreign
keys or transactions. Opening those live directories through the old application can acquire
locks or change indexes, deletion state, and metadata. Directly inserting extracted rows into
the normalized ledger would also risk partial or unreconciled books.

## Decision

- Migration accepts an operator-created ZIP snapshot. It never opens or modifies the live
  legacy directory. Archive paths, expansion size, file count, and required tables are checked
  before parsing.
- Compute a canonical SHA-256 digest from sorted DBF/memo filenames and their bytes. ZIP names,
  timestamps, and compression do not affect repeatability.
- Retain every active source record in company-scoped staging with table name, physical record
  number, natural key, normalized payload, severity, and structured issues.
- Validate account duplicates/types, retained earnings, currencies, orphans, periods/dates,
  numeric values, line sides, transaction groups, pre-post groups, and legacy-report conversion
  status. Unknown or ambiguous behavior is a blocking exception rather than an approximation.
- Reconcile opening balances, account current balances, account-period arrays, global posted
  debits and credits, and transaction totals. Apply remains disabled until the result is clean.
- Require an empty target company and an explicit digest confirmation for cutover. Accounts,
  budgets, opening balances, posted groups, draft groups, compatible reports, period balances,
  staging lineage, and audit evidence commit in one PostgreSQL transaction. Any error rolls the
  entire apply back.
- Repeating an identical trial or successful apply returns the existing digest-owned run.

## Consequences

Trial migrations are safe to repeat and compare, while a cutover cannot silently mix ledgers or
leave partial mutations. Operators must configure the target company and fiscal calendar first,
and must take a quiesced read-only snapshot for the final run. Foreign-currency draft groups are
blocked because the authoritative legacy conversion routine is missing; they require review or
posting in the legacy system before the final snapshot.
