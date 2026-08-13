Semantic `<dl>` for record detail: posted entry headers, close previews, job metadata, audit events.

```jsx
<KeyValueList columns={3} items={[
  { label: "Entry", value: "JE-2026-000482", mono: true },
  { label: "Posted", value: "2026-07-31 16:04 America/New_York", mono: true },
  { label: "Reversing", value: "No" },
]} />
```

Use it instead of a two-column table for non-tabular detail — it keeps label/value pairs programmatically associated.
