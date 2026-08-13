Displays a report content digest or a migration source digest as selectable, copyable monospace.

```jsx
<DigestValue value={run.digest} />
<DigestValue value={snapshot.sourceDigest} label="Source digest" truncate />
```

Show the digest in full wherever a user must verify it — migration apply, report reproduction. `truncate` is only for dense history lists.
