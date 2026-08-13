Switches between views of the same object or dataset — draft/validated/approved/posted, or settings sections.

```jsx
<Tabs activeId="drafts" onChange={setTab} tabs={[
  { id: "drafts", label: "Drafts", count: 6 },
  { id: "posted", label: "Posted", count: 148 },
]} />
```

Do not use tabs to move between destinations — that is `SidebarNav`. Tabs never hide a governed action behind a second click without a hint that it exists.
