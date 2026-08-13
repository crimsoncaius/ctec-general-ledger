Renders a single Lucide glyph in the current text colour; use it for every icon rather than inlining SVG.

```jsx
<Icon name="circle-check" size={16} label="Reconciled" />
```

Icons never carry meaning alone — always pair with text or an aria-label. Decorative icons omit `label` and become `aria-hidden`.
