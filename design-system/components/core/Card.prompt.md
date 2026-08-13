The workspace panel. Groups one task or one dataset; the footer strip carries audit evidence.

```jsx
<Card title="Trial balance" description="FY2026 · Period 07" padded={false}
      footer={<>Digest <DigestValue value={digest} /></>}>
  <DataTable … />
</Card>
```

Use `padded={false}` whenever the body is a table so rows meet the card edge.
