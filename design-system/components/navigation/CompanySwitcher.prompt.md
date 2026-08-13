Shows the active company, its code and the signed-in role, and switches between active memberships.

```jsx
<CompanySwitcher company="Northstar Manufacturing" code="NORTHSTAR-01" role="Approver"
                 memberships={memberships} onSelect={switchCompany} />
```

Switching is a full context change: company-owned data, capabilities, selections, previews and pending edits must reload or reset. The menu says so explicitly.
