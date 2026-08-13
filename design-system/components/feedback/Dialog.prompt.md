Modal confirmation for high-risk actions. It names the object and states the consequence; `confirmWord` adds a typed gate.

```jsx
<Dialog tone="danger" title="Apply legacy migration"
        subject="NORTHSTAR-01 · source digest 9f2c…a41b"
        consequence="Accounts, journals, budgets, reports and lineage are imported in one transaction. The target company must be empty."
        confirmWord="APPLY" confirmLabel="Apply migration" />
```

Focus moves into the dialog on open and returns to the trigger on close. Never phrase the body as "Are you sure?".
