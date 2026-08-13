An icon-only affordance for secondary utilities: refresh, copy digest, row overflow, drawer close.

```jsx
<IconButton icon="refresh-cw" label="Refresh company data" onClick={reload} />
```

Never use it for a primary or destructive action — those need a written label. `label` is mandatory.
