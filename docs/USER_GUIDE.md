# User guide

## Local demonstration access

After migrations and `python -m app.seed`, sign in at `http://localhost:5173` with one of
these local-only identities:

| Role | Email | Password | Intended workflow |
|---|---|---|---|
| Administrator | `admin@example.com` | `CTec-Demo-Admin-2026!` | Configuration and unrestricted local demonstration |
| Preparer | `preparer@example.com` | `CTec-Demo-Prepare-2026!` | Draft and validate journals; cannot approve or post |
| Approver | `approver@example.com` | `CTec-Demo-Approve-2026!` | Approve, post, reverse, and run integrity checks |

These passwords are deterministic fake-data credentials and must never be reused in a
deployed environment.

The normal seed exposes one company: `ALCAN · ALCAN GENERAL TRADING PTE LTD`. Its FY2003 calendar,
chart, opening balances, posted February 2003 activity, original/base currency values, and legacy
report sources come from the repository's read-only `GL_Data` snapshot. The migration history
shows the dry run, source digest, normalization warnings, and atomic apply record.

## Company context

The company picker shows only active memberships. Changing company reloads accounts,
periods, journals, roles, and capabilities with an `X-Company-ID` context checked by the
server. A bookmarked identifier or modified browser request cannot grant access to another
company.

## Journal workflow

1. A preparer opens **Journals**, chooses an open fiscal period and two different postable
   accounts, enters an amount, and creates a draft.
2. A user with `journals.validate` validates the batch. Validation rechecks period, account,
   currency, line-side, and base-currency balance invariants.
3. A different user with `journals.approve` approves it unless an explicitly granted
   self-approval capability applies.
4. A user with `journals.post` posts it. Entry status, posting evidence, period balances,
   and audit event commit together or all roll back.
5. Posted detail cannot be edited or deleted, including by direct SQL. Corrections use the
   reversal action, which posts equal-and-opposite linked detail into an open period.

Use the integrity action after imports, closes, or unusual operations to recompute balances
from immutable posted detail and compare them with stored period balances.

Draft batches can be renamed while preserving and revalidating their lines, copied into a new
draft, or deleted. These actions are available only with their explicit capabilities and only
before validation/approval/posting. Posted batches cannot be changed or deleted.

## Accounts and fiscal calendars

The **Accounts** workspace allows authorized users to create normalized accounts and edit names,
posting status, and active status. Codes, types, and currency identity do not change after
creation. Title accounts cannot post, retained earnings cannot be deactivated, and an account
referenced by an unposted journal cannot be deactivated. Use inactive status instead of deleting
history.

The **Fiscal** workspace lists every company period. Users with `fiscal.manage` can generate 1–18
boundaries from a first day and period length, then review/edit every label and date before save.
The server requires contiguous numbering, ordered non-overlapping dates, and all periods inside
the fiscal year.

## Company and role administration

The governed settings card maintains company name, IANA timezone, decimal places, and rounding
method; base currency remains fixed once the company is in use. The capability editor loads one
company role at a time and atomically replaces its explicit grants. Review system-role changes
carefully and retain at least one active administrator membership.

## Custom report designer

Users with `reports.custom.design` can build a report from the **Designer** workspace. A
definition contains:

- balance, budget, or calculated columns;
- account, account-range, calculated, heading, and spacer rows;
- named sections and decimal-display settings; and
- an optional reusable-template flag.

Preview calculates the unsaved definition without creating a report run. Save creates version
1; later saves require the version currently displayed in the editor, so another user's change
cannot be overwritten silently. A reusable template can be cloned into a non-template working
copy before customization.

Formula names refer only to row or column keys. The supported operators are `+`, `-`, `*`, and
`/`; the supported functions are `abs`, `min`, `max`, and `round`. Cycles, unknown names,
imports, attribute access, and calls to any other function are rejected. Accounting values are
calculated with fixed decimals. Titles may use `{company_name}`, `{company_code}`,
`{period_label}`, and `{as_of_date}`.

Running a saved report records its parameters, result digest, actor, and outcome. Browser, CSV,
Excel, and PDF downloads are generated from the same calculated rows.

## Legacy GLREP review

Paste the text of a legacy report into the compatibility panel and choose **Analyze safely**.
The application does not execute the source. It reports one of these dispositions:

- **Compatible**: the supported account, period/budget, and arithmetic constructs converted.
- **Partial**: a usable definition was produced, with warnings that require review.
- **Manual**: unsafe or ambiguous behavior prevented a runnable conversion.

Always read and resolve the warnings before relying on a converted statement. RTF commands,
embedded images, printer-specific placement, and unknown legacy expressions are deliberately
quarantined and must be rebuilt in the modern designer.

## Legacy data migration

The **Legacy migration** card is visible only with `migration.run`. Upload a flat ZIP containing
read-only copies of `GLACCNT` and `GLMAIN`, plus any available currency-mirror, pre-post, and
custom-report tables. **Run read-only trial** stages row lineage, validates the source, and shows
the ledger and account-period reconciliations without changing the target ledger.

Download the exception CSV whenever warnings or errors are reported. Apply remains unavailable
for blocking issues. A clean result requires typing `APPLY`; the server also checks the displayed
SHA-256 source digest and requires an empty target company. Apply imports normalized accounts,
budgets, opening balances, immutable posted groups, draft groups, and compatible reports in one
transaction. See `MIGRATION_GUIDE.md` for snapshot, parallel-run, and cutover controls.
