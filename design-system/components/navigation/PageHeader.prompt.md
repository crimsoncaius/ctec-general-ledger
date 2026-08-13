Every workspace starts with one. Carries the h1, the scope line and the data-freshness indicator the brief requires.

```jsx
<PageHeader eyebrow="Ledger" title="Journal batches" dataState="refreshing"
            updatedAt="16:04 America/New_York"
            meta="FY2026 · 42 batches · USD"
            actions={<Button variant="primary" icon="plus">New draft</Button>} />
```

`dataState` announces politely on change, so users learn when content is stale rather than assuming it is current.
