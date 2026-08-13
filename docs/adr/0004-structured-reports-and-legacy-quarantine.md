# ADR 0004: Structured reports and legacy compatibility quarantine

Status: Accepted — 2026-08-10

## Context

The legacy GLREP feature combines account selections, period/budget matrices, arithmetic,
RTF layout, and executable-style expression strings. Reproducing its permissive parser would
allow unauditable calculations and unsafe content. Users still need equivalent financial
statements and a controlled path for inspecting existing definitions.

## Decision

- Store modern custom reports as versioned, typed JSON definitions owned by one company.
- Model columns, rows, sections, and formatting explicitly. Ledger and budget values always
  originate from reconciled period balances and versioned budgets.
- Evaluate formula cells with a small AST allowlist over `Decimal` values. Never use `eval`,
  imports, attribute access, or binary floating-point accounting arithmetic.
- Permit only documented title placeholders and reject unknown placeholders as validation
  errors.
- Serialize concurrent designer updates with a row lock and require the caller's current
  version, returning a conflict for stale edits.
- Produce browser, CSV, Excel, and PDF output from one calculated report dataset and retain a
  digest and audit record for each saved run.
- Parse legacy text in an isolated, non-executing converter. Classify each definition as
  `compatible`, `partial`, or `manual`, retain conversion warnings, and block execution of
  definitions that require manual reconstruction.
- Ignore legacy RTF control words, embedded images, arbitrary printer placement, and unknown
  formula constructs. They may be reconstructed in the modern designer after review, but are
  never interpreted as executable instructions.

## Consequences

Custom-report arithmetic is deterministic, tenant-scoped, auditable, and consistent across
all output formats. Most ordinary legacy account, range, total, period, budget, and arithmetic
statements can be migrated. Pixel-identical legacy layouts and unsafe expressions are
intentionally retired and reported as exceptions instead of being silently approximated.
