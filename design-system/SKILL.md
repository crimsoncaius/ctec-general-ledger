---
name: CTec Ledger design system
description: Design system for the CTec General Ledger frontend — a multi-company, capability-governed double-entry ledger. Use when designing any CTec Ledger screen, or any audit-critical financial workspace built on these tokens and components.
---

# CTec Ledger design system

> **Project authoring guide.** This file guides contributors and agents composing CTec Ledger UI.
> It is not an independently installed package and production code must not import from this reference
> directory. Functional requirements in `../docs/FRONTEND_DESIGN_BRIEF.md` and the ADRs take precedence.

Sober institutional. Cool near-neutral greys, one slate-blue accent, hairline structure, monospace for
every figure. The product is a permanent financial record; the interface's job is to make correctness,
authority and risk visible.

## Setup

Link `styles.css` once. It imports every token file, including the Google Fonts request.

```html
<link rel="stylesheet" href="styles.css" />
```

Set `data-density="comfortable" | "compact"` on the app root. It reprices row heights, control heights
and padding; type sizes never change.

Author against semantic tokens, never raw ramps:
`--surface-card`, `--surface-page`, `--surface-sunken`, `--text-primary`, `--text-secondary`,
`--text-muted`, `--border-hairline`, `--action-primary-bg`, `--status-{state}-{bg|fg|border}`,
`--feedback-{tone}-{bg|border|fg}`, `--type-{h1|h2|h3|body|body-sm|label|caption|overline|mono|amount}`,
`--space-1..12`, `--radius-{xs|sm|md|lg|pill}`, `--shadow-{raised|menu|dialog}`, `--focus-ring`.

## Components

**Core** — `Icon`, `Button`, `IconButton`, `Card`, `Badge`
**Forms** — `Field`, `Input`, `Textarea`, `Select`, `Checkbox`, `Switch`
**Data** — `DataTable` (+`SortHeader`), `AmountCell`, `StatusPill`, `DigestValue`, `KeyValueList`
**Feedback** — `Banner`, `Dialog`, `ProgressBar`, `EmptyState`
**Navigation** — `AppShell` pieces: `CompanySwitcher`, `SidebarNav`, `PageHeader`, `Tabs`

Each component directory holds `Name.jsx`, `Name.d.ts` (the prop contract) and `Name.prompt.md`
(when to use it). Read the `.prompt.md` before composing.

## Rules that are not negotiable

1. **Every financial figure uses `AmountCell`** — right-aligned, tabular monospace, fixed decimals,
   never abbreviated or rounded. Negatives use accounting parentheses, not colour. Debit and credit
   stay in separate labelled columns; never a signed single column.
2. **Every lifecycle state uses `StatusPill`.** It owns the vocabulary (draft, validated, approved,
   posted, reversed, open, closed, trial, applied, queued, running, succeeded, failed, reconciled,
   exception, compatible, partial, manual). Never invent state words; never signal state with colour alone.
3. **Capabilities drive the UI.** A destination or action the user cannot perform is absent, not
   disabled. When absence could confuse — maker-checker separation, missing `fiscal.close` — add an
   `info` Banner or an `EmptyState` of kind `no-action` that explains it. Never gate on a role name.
4. **Every workspace opens with `PageHeader`** carrying an h1, a scope line (company, fiscal year,
   period, currency, counts) and `dataState` — current, loading, refreshing, stale or failed.
5. **High-risk actions go through `Dialog`**, which names the object and states the accounting
   consequence. Posting, closing, reversal, deletion, migration apply. Migration apply also takes
   `confirmWord="APPLY"`. Never write "Are you sure?".
6. **Partial success is a `warning` Banner** listing succeeded and failed counts with a path to the
   failures. Never a success banner over a mixed result.
7. **Immutability is stated, not implied.** Posted entries and closed periods show a lock glyph and a
   sentence: corrections are new linked reversals. Accounting-immutable form fields use
   `Field immutable`.
8. **Previews invalidate.** When parameters change, discard the stale result, say so, and keep the
   execute action unavailable until a fresh valid preview exists.
9. **Long jobs use `ProgressBar`** against a persisted server percentage, with copy confirming that
   navigating away does not cancel the job.
10. **Digests are shown in full** via `DigestValue` wherever a user must verify one; `truncate` is only
    for dense history lists.
11. **Tables always carry a caption**, scroll horizontally rather than dropping financially significant
    columns, and put totals in `footRow`.
12. **Failures preserve input** and surface the API's correlation reference via `Banner correlationId`.

## Composition defaults

- Page: `PageHeader` → banners (most severe first) → `Tabs` if the dataset has states → content grid.
- Content grid: a wide primary `Card` and a narrower detail or summary column, `gap: var(--stack-gap)`,
  `align-items: start`.
- Tables live in a `Card padded={false}` so rows meet the card edge; audit evidence goes in the card footer.
- Record detail uses `KeyValueList`, not a two-column table.
- One `primary` Button per view. `danger` only for irreversible execution.
- Layout uses flex/grid with `gap`; never margin chains or inline-flow spacing.

## Reference

`README.md` — status, authority, full context, content voice, visual foundations, accessibility, and caveats
listing what was substituted (no brand assets, CDN fonts, Lucide icons).
`ui_kits/ledger/index.html` — click-through workspace: sign-in, overview, journals with maker-checker
and bulk partial success, posted inquiry with reversal, fiscal close with stale-preview invalidation,
reports with digests, legacy migration with the typed apply gate. The capability-set switcher at bottom
right re-renders every screen as administrator, preparer, approver or restricted viewer.
