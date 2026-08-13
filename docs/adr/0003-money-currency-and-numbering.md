# ADR 0003: Fixed-decimal money, explicit FX, and gap-tolerant numbers

Status: accepted

Database monetary values use `NUMERIC(20, 6)` and exchange rates use
`NUMERIC(20, 10)`. Python uses `Decimal` with explicit half-even or company
configured rounding at conversion boundaries. Original and base amounts are both
stored on journal lines so posted history does not change when rates change.

Human-facing group and reference sequences are allocated atomically and may have
gaps after cancellation. They are identifiers, not evidence of transaction
completeness; audit events provide that evidence.

