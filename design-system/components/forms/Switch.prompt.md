A setting that takes effect on save: postable status, active status, reusable-template flag, emphasis on a designer row.

```jsx
<Switch checked={postable} onChange={setPostable} label="Postable" />
```

Use `Checkbox` for selection and multi-choice; use `Switch` only for a single on/off property of an object. A switch never triggers a governed action on its own — the user still presses Save.
