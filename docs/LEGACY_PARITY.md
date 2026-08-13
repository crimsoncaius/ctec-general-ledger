# Legacy workflow parity and retirement register

This register uses the dossier and supplied source as evidence. Missing legacy modules and known
defects are not treated as requirements.

| Legacy workflow | Modern disposition |
|---|---|
| Account add/modify/delete, inquiry, currency mirror | Covered by normalized account create/update, safe deactivation, stable-ID inquiry, currency/rate fields, and audit. Physical deletion and orphan mirrors are retired. |
| Account CSV/DBF import | Covered by previewed atomic CSV import and read-only DBF cutover with exceptions/reconciliation. |
| Transaction group add/modify/copy/delete/import/browse | Covered by draft batches, edit/copy/delete controls, atomic CSV import, saved views, marking/bulk controls, and company-scoped browse. |
| Validate and post groups | Covered by validation, maker-checker approval, locked atomic posting, period balances, posting evidence, and bulk transitions. |
| Posted inquiry and correction | Covered by account-filtered immutable detail, correct debit/credit labels, audit, and linked reversal. Direct posted edits and history clearing are retired. |
| Budgets and amount comparison | Covered by scenario/period/account budgets, version-preserving audit behavior, budget columns in custom reports, and period comparison reports. |
| 1–18-period fiscal settings | Covered by browser creation with generated/editable period boundaries, backend overlap/order validation, period status, and company settings. |
| Close, retained earnings, closing report | Covered by previewed non-destructive close, retained-earnings and next-year opening entries, immutable close event, reconciliation, close report, and compensating correction. Destructive ledger purge is retired. |
| Integrity and organize | Covered by recomputation/reconciliation, exception results, audited background operations, PostgreSQL indexes/constraints, and database maintenance outside user-facing record packing. DBF pack/reindex is retired. |
| Chart, trial balance, GL listing, transaction/pre-post groups | Covered with saved parameters/digests and one reconciled dataset for browser/PDF/CSV/Excel. Legacy accumulator and brought-forward defects are corrected. |
| Custom GLREP author/print | Covered by typed rows/columns/sections/templates, fixed-decimal safe formulas, placeholders, version conflicts, preview/run/history, and four output formats. |
| Legacy GLREP compatibility | Covered by a non-executing compatible/partial/manual converter and DBF import. Arbitrary RTF commands, pictures, printer positioning, and unsafe expressions require manual reconstruction. |
| Users, 28 permissions, screen options | Covered by named users, company roles, explicit capabilities, membership status, role-capability editor, saved views, and practical display preferences. Legacy encrypted passwords are not migrated. |
| Operation error viewer | Covered by structured operation state, error text, immutable audit history, and correlation IDs. |
| Direct printer/profile/spool files | Intentionally retired. Browser print and deterministic PDF/CSV/Excel downloads replace device-specific printer persistence. |
| Physical-record marking and keyboard navigation | Covered by stable-ID marking, range/bulk actions, Alt workspace shortcuts, and accessible browser controls. Record-number bitsets are retired. |
| Hidden update/purge/debug forms, inert toolbar, abandoned helpers | Intentionally retired as non-meaningful compiled artifacts. |

External cutover sign-off against real DBFs and legacy control reports remains an operational
activity because no representative production DBFs or golden outputs were supplied. The tooling,
exception evidence, and parallel-verification procedure are complete; real data is never assumed.
