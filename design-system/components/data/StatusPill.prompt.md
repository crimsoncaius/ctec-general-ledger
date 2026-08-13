The canonical state marker. It owns the product's status vocabulary — never invent new state words.

```jsx
<StatusPill status="posted" />
<StatusPill status="exception" />
```

Each state carries an icon and a word, so meaning never depends on colour. Posted and closed states use a lock glyph to signal immutability.
