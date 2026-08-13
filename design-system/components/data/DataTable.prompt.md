The ledger table: sticky uppercase header, hairline rows, optional totals foot, horizontal scroll rather than dropped columns.

```jsx
<DataTable caption="Posted entries, period 07" columns={[
  { key: "code", header: "Account", mono: true },
  { key: "debit", header: "Debit", numeric: true, render: r => <AmountCell value={r.debit} /> },
  { key: "credit", header: "Credit", numeric: true, render: r => <AmountCell value={r.credit} /> },
]} rows={rows} footRow={{ code: "Total", debit: <AmountCell value={t.d} emphasis /> }} />
```

`caption` is mandatory for screen readers. Never hide a financially significant column to fit a narrow viewport — let the table scroll.
