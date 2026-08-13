Single-choice control for periods, fiscal years, accounts, report types and output formats.

```jsx
<Select placeholder="Select an open period" options={[
  { value: "2026-07", label: "P07 · Jul 2026" },
  { value: "2026-06", label: "P06 · Jun 2026 (closed)", disabled: true },
]} />
```

Keep ineligible options visible-but-disabled so users learn why a period cannot be used, rather than silently filtering them out.
