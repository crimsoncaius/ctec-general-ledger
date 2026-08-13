# CTec Ledger Design-System Adoption

**Status:** Consumer migration and release hardening complete; compatibility retirement deferred  
**Last verified:** 2026-08-14  
**Target reference:** [`../design-system/README.md`](../design-system/README.md)  
**Functional authority:** [`FRONTEND_DESIGN_BRIEF.md`](FRONTEND_DESIGN_BRIEF.md)

## Current state

The production frontend owns its semantic tokens and typed React primitives under
`frontend/src/design-system/`. Public components are exported through
`frontend/src/design-system/index.ts`; production has no runtime imports from the reference
`modern/design-system/` package.

Vite bundles local Public Sans and JetBrains Mono WOFF2 assets, and the typed `Icon` component renders the
approved build-time Lucide glyph allowlist. Color, typography, spacing, density, elevation, motion and focus
styling is expressed through production semantic tokens. Existing `--ledger-*` names remain only as
compatibility aliases to those tokens.

Accounting behavior remains governed by the frontend brief and ADRs. The migration preserves company
isolation, capability filtering, maker-checker boundaries, posted-record immutability, audit digests,
fixed-decimal amount formatting, debit/credit separation and explicit partial-success results.

## Adoption phases

### Phase 1 — semantic foundations — complete

- [x] Production semantic color, typography, spacing, density, elevation, motion and focus tokens.
- [x] Existing `--ledger-*` variables mapped to semantic tokens as compatibility aliases.
- [x] Self-hosted production fonts and compile-time icons; no runtime font or icon CDN.
- [x] Reduced-motion, focus visibility, narrow layout and 200% zoom checks.

### Phase 2 — typed primitives — complete

- [x] Core primitives: Button, IconButton, Card, Badge, PageHeader and layout helpers.
- [x] Form primitives: Field, Select, Textarea, Checkbox, Switch and immutable display fields.
- [x] Data primitives: DataTable, AmountCell, StatusPill and DigestDisplay.
- [x] Feedback primitives: Banner, Dialog, EmptyState and Progress.
- [x] Navigation primitives: Sidebar, Tabs and CompanySwitcher.
- [x] Unit coverage for keyboard behavior, accessible names, supported states, dialogs, digests and financial
      formatting.

### Phase 3 — application composition — complete

Workspaces were migrated and kept operational in the approved sequence:

| Sequence | Workspace | Status | Preserved behavior |
| --- | --- | --- | --- |
| 1 | Application shell, company context, navigation and page headers | Complete | Company reset/isolation, capability-filtered navigation and responsive shell |
| 2 | Journal preparation and approval | Complete | Maker-checker controls, separate debit/credit inputs and confirmation-gated posting |
| 3 | Posted inquiry and reversal | Complete | Immutable posted detail, full audit digest and confirmation-gated reversal |
| 4 | Fiscal close | Complete | Capability checks, period state and destructive confirmation |
| 5 | Reports | Complete | Fixed-decimal amounts, reproducible runs, export state and full digests |
| 6 | Legacy migration | Complete | Validation/apply separation, row outcomes and explicit partial-success reporting |
| 7 | Accounts and fiscal calendars | Complete | Account/calendar boundary rules and immutable identifiers |
| 8 | Budgets, report designer and administration | Complete | Capability constraints, financial entry semantics and administrative policy controls |

### Phase 4 — retirement and hardening — partially complete

- [x] Full lint, type, unit, coverage, build and Playwright release gates.
- [x] Administrator, preparer, approver and restricted-viewer workflows exercised.
- [x] Keyboard navigation, focus entry/trapping/return, narrow layouts, 200% zoom and reduced motion verified.
- [x] Production audit found no page-local raw colors, no raw form/button consumers outside the design-system
      implementation, and no reference-package runtime imports.
- [ ] Remove compatibility aliases and superseded layout selectors only after the remaining class-hook consumers
      are migrated and independently verified.

The final retirement step is intentionally deferred. Production workspaces still use legacy layout class hooks
from `frontend/src/styles.css`; their declarations now consume semantic tokens, but deleting the selectors
would break those consumers. The `--ledger-*` aliases are also retained as a documented compatibility
surface. No legacy styles were removed during this migration.

## Verification evidence

The following commands passed from `frontend/` on 2026-08-14:

| Gate | Result |
| --- | --- |
| `npm run lint` | Passed |
| `npm run typecheck` | Passed |
| `npm test` | 54 tests passed |
| `npm run test:coverage` | Passed: 88.83% statements, 80.74% branches, 86.79% functions, 90.30% lines |
| `npm run build` | Passed |
| `npm run test:e2e` | 18 Chromium workflows passed |

The Playwright matrix covers administrator, preparer, approver and restricted profiles. Its design-system
workflow additionally checks keyboard focus visibility, reduced-motion transition elimination, navigation and
dialog focus behavior, body containment at a 640 px narrow viewport, and layout containment at 200% CSS zoom.

Static audits confirmed:

- No runtime import path references `modern/design-system/`.
- No raw hexadecimal, RGB/HSL or named presentation color remains in page/workspace CSS; source palette values
  are centralized in `frontend/src/design-system/tokens.css`.
- No raw `button`, `input`, `select` or `textarea` consumer remains outside the design-system
  implementation and its tests.
- No legacy status-pill or status-message markup remains in production TSX.
- Legacy layout selectors and semantic `--ledger-*` aliases still have production consumers and therefore
  remain pending Phase 4 retirement.

## Intentional divergences

- Domain-heavy editable grids retain native semantic table composition rather than forcing every grid through
  `DataTable`. Their controls, amounts, statuses, digests and visual tokens still come from the production
  design system; this preserves inline editing and accounting-specific table behavior.
- Informational banners that reflect stable page state use non-live note semantics to avoid repeated assistive
  technology announcements. Action results and errors retain live status/alert semantics.
- `CompanySwitcher` keeps a native hidden select as a resilient form and automation surface alongside the
  approved styled menu.
- Compatibility aliases and legacy layout selectors remain by requirement until their consumers can be removed
  in a dedicated, verified retirement change.

There are no intentional divergences from accounting, authorization, audit or company-isolation behavior.

## Production asset licenses and attribution

- **Public Sans** variable WOFF2 files were obtained from `@fontsource-variable/public-sans` 5.3.0,
  sourced from the [USWDS Public Sans project](https://github.com/uswds/public-sans), and are licensed under
  the SIL Open Font License 1.1.
- **JetBrains Mono** variable WOFF2 files were obtained from `@fontsource-variable/jetbrains-mono` 5.3.0,
  sourced from the [JetBrains Mono project](https://github.com/JetBrains/JetBrainsMono), and are licensed
  under the SIL Open Font License 1.1.
- **Lucide** icons are compiled from the pinned `lucide-react` dependency and are licensed under the ISC
  license, with listed Feather-derived glyphs covered by MIT.
- Required license texts live in `frontend/public/licenses/` and ship in every production build.

## Change control

Accounting and authorization behavior cannot be changed through design-system adoption. When sources conflict,
the frontend design brief and ADRs win for functional behavior; the approved design system wins for visual and
interaction presentation.
