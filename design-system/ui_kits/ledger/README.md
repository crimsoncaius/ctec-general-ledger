# Ledger workspace UI kit

A click-through recreation of the signed-in CTec General Ledger experience, composed entirely from the
system's own components. This is a reference prototype with fabricated data, not a production frontend.

From the `modern` directory, run:

```powershell
py -m http.server 5174 --bind 127.0.0.1 --directory design-system
```

Then open `http://127.0.0.1:5174/ui_kits/ledger/index.html`.

## What is here

| File | Screen | Brief coverage |
| --- | --- | --- |
| `SignIn.jsx` | Authentication | Generic failure, lockout, no-company-access, pending state (§4.1) |
| `AppShell.jsx` | Global chrome | Company + code + role, capability-filtered nav, density preference, sign out (§3.1) |
| `OverviewScreen.jsx` | Overview | Posted-batch summary, recent batches, integrity exception ranked above metrics, durable job progress (§4.2) |
| `JournalsScreen.jsx` | Journal workflow | Draft lifecycle, marking, bulk transition with partial-success reporting, maker-checker gating, per-status controls (§4.4) |
| `InquiryScreen.jsx` | Posted inquiry | Immutable line detail, linked reversal with mandatory reason, reversal-of-reversal blocked (§4.5) |
| `CloseScreen.jsx` | Fiscal close | Prepare → preview → execute, stale-preview invalidation, repeat-close prevention (§4.7) |
| `ReportsScreen.jsx` | Reports | Parameters, browser result with digest, exports, saved-run reproduction, cleared stale result (§4.8) |
| `MigrationScreen.jsx` | Legacy migration | Read-only trial, reconciliation, record exceptions, digest + typed APPLY gate (§4.10) |

## Interactions worth trying

- **Capability set** switcher, bottom right: swap between Administrator, Preparer, Approver and Restricted
  viewer. Destinations and actions appear and disappear; the Preparer sees an explanation of maker-checker
  rather than greyed-out approve buttons.
- **Company switcher** in the header: the menu states that switching reloads all company data.
- **Density** toggle in the header: repriced rows, same type sizes.
- **Journals**: mark two drafts, run the bulk validation — the result is a partial-success banner, not a
  success banner.
- **Fiscal close**: change the fiscal year or opening period after previewing; the preview is discarded and
  execution becomes unavailable.
- **Migration**: stage a trial, then switch between exception and apply-ready outcomes; apply is gated on a
  typed `APPLY`.

## Not yet built

Chart of accounts, fiscal-calendar generation, budgets, custom report designer and administration were left
out of this first pass. Navigation to an unimplemented area opens an explicit reference placeholder rather
than implying that a working product screen exists. The components those areas need (immutable fields,
boundary-review tables, version-conflict banners) all exist.

## Implementation note

`loader.js` fetches the JSX, strips the ES imports and compiles everything in one Babel pass, so the kit needs
no build step but must be served over HTTP. The screen sources keep their imports so they read correctly in
an editor. React, Babel, fonts and icons are CDN-hosted for this prototype only.
