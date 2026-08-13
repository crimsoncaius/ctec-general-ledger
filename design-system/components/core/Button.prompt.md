The standard action control; one `primary` per view, `danger` only for execution of an irreversible operation.

```jsx
<Button variant="primary" icon="check" onClick={post}>Post batch</Button>
<Button variant="secondary">Cancel</Button>
<Button variant="danger" busy={posting}>Execute close</Button>
```

Never disable a governed action without an adjacent reason — pair a disabled Button with a Banner or hint text explaining the guardrail. `busy` retains the label rather than swapping it for a spinner.
