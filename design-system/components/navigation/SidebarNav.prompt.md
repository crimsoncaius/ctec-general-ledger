Primary workspace navigation, grouped by finance task. Items are derived from capabilities, never from a role label.

```jsx
<SidebarNav activeId="journals" groups={[
  { label: "Ledger", items: [{ id: "journals", label: "Journals", icon: "file-stack", badge: 6 }] },
]} onNavigate={go} />
```

A destination with no relevant capability is absent, not disabled. `readOnly` marks view-only destinations with an eye glyph so the restriction is visible before entry.
