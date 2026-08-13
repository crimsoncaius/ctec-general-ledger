In-page message for guardrails, partial success, restrictions, stale previews and unexpected failures. Announced via a live region.

```jsx
<Banner tone="warning" title="Preview no longer matches the selected file"
        actions={<Button size="sm">Re-run preview</Button>}>
  Apply stays unavailable until the preview is regenerated for the current file.
</Banner>
```

Partial success is a `warning` Banner listing succeeded and failed counts — never a success banner. Attach `correlationId` whenever the API returns one.
