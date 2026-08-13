Boolean input, and the row-marking control for bulk journal transitions.

```jsx
<Checkbox indeterminate={some} checked={all} onChange={toggleAll} label="Select all drafts" />
```

In a bulk table the header checkbox is `indeterminate` when the selection is partial; always show the selection count next to the intended transition.
