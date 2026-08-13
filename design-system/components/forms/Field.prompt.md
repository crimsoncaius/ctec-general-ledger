Wraps one control with its label, hint and error, and wires `aria-describedby` automatically.

```jsx
<Field label="Currency" htmlFor="ccy" immutable hint="Three-letter ISO code.">
  <Input defaultValue="USD" />
</Field>
```

Always pass `error` rather than colouring the input yourself — the wrapper keeps the message programmatically associated.
