# ADR 0002: Immutable posting and non-destructive close

Status: accepted

Posting is a single database transaction. A posted journal and its lines cannot be
updated or deleted; database triggers reinforce service-layer checks. Corrections
create a reversing journal linked to the original and may create a replacement.

Fiscal close never deletes journal or ledger detail. It posts explicit closing and
opening effects, records their parameters and reconciliation totals in a closing
event, and supports controlled reopen by compensating reversal. This intentionally
corrects the legacy destructive close.

