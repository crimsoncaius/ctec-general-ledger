Every financial figure in the product. Right-aligned, tabular, never abbreviated or rounded.

```jsx
<AmountCell value={12480} currency="USD" side="debit" />
<AmountCell value={-320.5} />   {/* renders (320.50) */}
```

Negatives use accounting parentheses, not colour. Debit and credit stay in separate labelled columns — never a signed single column.
