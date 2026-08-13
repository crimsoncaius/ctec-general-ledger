# CTec Ledger design system

A design system for the CTec General Ledger web frontend: a multi-company, capability-governed
double-entry ledger used by finance staff to prepare, approve, post, close and report on financial
records that must stay auditable forever.

## Status and authority

| Property | Status |
| --- | --- |
| Design status | **Approved visual and interaction target** |
| Production adoption | Partial; the current frontend contains an interim CSS adaptation |
| Runtime status | Reference-only; production code must not import this directory |
| Prototype data | Fabricated and intended only to demonstrate states and workflows |
| Prototype dependencies | CDN-hosted React, Babel, fonts and icons; not approved for production |
| Screen coverage | Seven interactive screens plus explicit placeholders for areas not yet prototyped |

Authority is applied in this order:

1. Accounting, security, authorization and immutability requirements come from
   [`../docs/FRONTEND_DESIGN_BRIEF.md`](../docs/FRONTEND_DESIGN_BRIEF.md) and the project ADRs.
2. This directory is authoritative for the approved visual language, component usage and interaction
   presentation where those functional sources are silent.
3. The current frontend records implementation progress; it is not the design source of truth.

Everything here derives from the canonical frontend design brief. Where the brief is silent — the visual
direction was left deliberately open — the choices below were made and are recorded so they can be
argued with.

---

## 1. Who this is for and what it must survive

The people using this product are accountants, controllers and finance administrators. They work in
long sessions, in dense data, on desktop screens, often with two companies open in their head at once.
They are not exploring; they are producing a defensible record.

Four properties shape every decision in this system:

**Correctness is visible.** A posted entry is immutable, a period is open or closed, a preview either
reconciles or does not. The interface states these facts rather than implying them. Balances,
digests, timestamps and totals are shown in full, never abbreviated or rounded.

**Authority is legible.** What a user can do comes from capabilities, not a role name. Destinations
and actions a user cannot perform are absent rather than greyed out; where absence would be confusing
— maker-checker separation, for instance — the interface says why in words.

**Risk is proportionate.** Ordinary work is one click. Posting, closing and migration are gated
by a confirmation that names the object and states the accounting consequence. Applying a legacy
migration additionally requires a typed `APPLY`.

**Nothing is lost.** Partial success is reported item by item. Failed operations keep the user's
input. Long jobs are durable server-side records that survive navigation and reload.

## 2. Voice and content

Plain, specific, unhurried. The product speaks like a competent colleague documenting what happened.

- Name the object: "BATCH-000149 posted", not "Success".
- State the consequence, not the question: "Posting commits entry state, balances and evidence in one
  transaction. Posted detail can never be edited." — never "Are you sure?".
- Report reality: "Partial success — 8 of 11 batches validated", never a success banner over a mixed result.
- Say which emptiness this is: no data, no matching data, no company access, no available action.
- Explain guardrails where they bite: "Execution stays unavailable until the preview reconciles."
- Never blame the user, never apologise, never use exclamation marks.
- Sentence case everywhere except the uppercase overline style used for table and definition-list labels.
- Times carry their zone. Amounts carry their currency when it could be ambiguous.

Vocabulary is fixed by the domain and must not be paraphrased: draft, validated, approved, posted,
reversed; open and closed periods; trial and applied migrations; preview and execute; digest;
capability; company.

## 3. Visual direction

**Sober institutional.** This is a records system, and it should feel like one: quiet cool neutrals,
hairline structure, one restrained accent, small radii, almost no shadow. Nothing decorative competes
with the numbers. Density is a first-class preference, not an afterthought — the same screen serves a
controller scanning 400 rows and a preparer entering four.

**Colour.** A near-neutral cool grey ramp carries the whole workspace (`--n-0` to `--n-900`). One
accent, slate blue `#1F4B99`, does identity, focus and primary action, and nothing else. Status hues
are deliberately muted: a ledger exception should read as serious, not as an alarm. Every status also
carries a glyph and a word, so meaning never rests on colour. Author against the semantic aliases
(`--surface-card`, `--text-secondary`, `--status-posted-bg`), never the raw ramps.

**Type.** Public Sans for interface text, JetBrains Mono for anything a person might read digit by
digit — amounts, account codes, batch and entry numbers, company codes, digests, timestamps. Every
figure is tabular so columns align down the page. Body text sits at 13.5px; table text at 12.5px;
headings tighten their tracking, overlines open theirs up. Nothing financial ever renders in a
proportional face.

**Structure.** Cards and tables separate with 1px hairlines. Shadow is reserved for things that
genuinely float — menus, drawers, dialogs, the sticky table header. Radii stay small: 3px on controls,
5px on panels. The result is a page that reads as a document, not as a collection of floating tiles.

**Motion.** Short and functional: 120ms on controls, 180ms on surfaces, 280ms on progress. Nothing
animates for delight. `prefers-reduced-motion` zeroes every duration.

**Layout.** A dark application header carries product identity, company context and session controls.
A light sidebar carries capability-filtered destinations. Content sits in a single scrolling column
capped at 1360px, with a page header that always states scope and data freshness.

## 4. Accessibility

WCAG 2.2 AA is the floor. Text pairs meet 4.5:1 and the design targets are recorded in the
"Contrast and focus" specimen. Focus is a two-layer ring visible on both light and dark surfaces.
Every table has a caption, every icon-only control an accessible name, every form control a
programmatically associated label, hint and error. Live regions announce data-freshness changes
politely and failures assertively. Status is never colour alone. Layouts hold at 200% zoom because
tables scroll horizontally rather than dropping financially significant columns.

## 5. What is in the box

- `styles.css` — the single entry point; imports every token file.
- `tokens/` — colour, type, spacing, elevation, motion, density, and base resets.
- `components/` — 24 React components in five groups (core, forms, data, feedback, navigation), each
  with a `.d.ts` contract and a `.prompt.md` usage note.
- `guidelines/` — foundation specimens: colour ramps, semantic aliases, type scale and roles,
  monospace and tabular figures, spacing, density comparison, radii, elevation, motion, iconography,
  contrast.
- `ui_kits/ledger/` — a click-through recreation of the signed-in product across seven screens, with a
  capability-set switcher so the same screens can be viewed as administrator, preparer, approver or
  restricted viewer.

### Preview the reference

The UI kit fetches its JSX at runtime, so serve it over HTTP rather than opening the HTML file directly.
From the `modern` directory:

```powershell
py -m http.server 5174 --bind 127.0.0.1 --directory design-system
```

Then open `http://127.0.0.1:5174/` and choose **Ledger workspace**. Port 5174 is registered for the
CTec Ledger design-system reference.

## 6. Caveats — things that were substituted, not supplied

These are the honest gaps. Replace them when real material arrives.

**No brand assets exist.** No logo, wordmark, colour or typeface was supplied. `CTec Ledger` is set in
type as a placeholder and the palette and pairing were chosen from scratch. Do not substitute an
invented mark.

**Fonts load from Google Fonts.** Public Sans and JetBrains Mono are pulled from the CDN in
`tokens/fonts.css`. There is no local `assets/fonts` payload because no licensed binaries were
provided. Self-host before production.

**Icons are Lucide, pulled from a CDN.** No icon set was supplied, so Lucide 0.454 stands in, rendered
as a CSS mask so glyphs inherit text colour. Any coherent 1.5px-stroke outline set can replace it by
changing `Icon.jsx` alone.

**No imagery.** The product has none and needs none. Nothing here uses illustration or photography.

**Contrast ratios are design targets** computed against the token values, not measured against a
built product. Re-measure after any palette change.

**Data in the UI kit is fabricated** and internally consistent only within a screen. It exists to
exercise states, not to be arithmetically true across the whole kit.

**Five of the brief's nine areas are recreated.** Chart of accounts, fiscal-calendar generation,
budgets, the custom report designer and administration are not built as screens; the components they
require — immutable fields, boundary tables, version-conflict banners, capability guards — all exist.
