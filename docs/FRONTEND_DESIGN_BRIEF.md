# CTec General Ledger Frontend Design Brief

**Audience:** Product designer, UX designer, interaction designer, and design-system partners  
**Coverage:** Complete modern web application  
**Status:** Functional design source of truth  
**Visual direction:** Deliberately unspecified

## 1. Purpose of this brief

CTec General Ledger is a company-scoped accounting application for maintaining accounts and fiscal calendars, preparing and governing journals, closing financial years, producing reproducible reports, administering access, and migrating data from a legacy system.

This document defines what the frontend must communicate and enable. It does not define how the product should look. The designer may rethink navigation, grouping, page composition, interaction patterns, density, responsive behavior, and terminology where clearer language improves the experience.

The design must preserve the product's accounting, authorization, audit, isolation, and immutability controls. A design is not complete if it makes a required capability difficult to find, obscures the active company, implies that a governed action succeeded before it did, or weakens a review or confirmation step.

### 1.1 What is mandatory

- Every request and result is scoped to an authenticated user's active company membership.
- Available areas and actions are determined by explicit capabilities, not by presentation-only role labels.
- Posted journals and historical financial evidence are immutable.
- Journal approval follows maker-checker separation unless self-approval is explicitly granted.
- Posting, closing, imports, and migration are atomic: the whole operation commits or none of it does.
- Fiscal close and migration require a successful review state before execution.
- Reports retain their parameters, actor, outcome, and content digest so a run can be reproduced.
- Financial values use fixed-decimal accounting rules and must never be presented as approximate.
- Errors, restrictions, warnings, progress, and success evidence must be visible and accessible.

### 1.2 What the designer owns

- Information architecture and navigation model
- Grouping of related capabilities into destinations, tasks, or progressive flows
- Page, drawer, modal, inline-editing, wizard, or other interaction patterns
- Layout, hierarchy, responsive transformations, and data-density strategy
- Visual identity, color, typography, spacing, iconography, elevation, and motion
- Component choices and design-system expression
- Final user-facing copy, provided that accounting meanings and warnings remain accurate

The existing sidebar, workspace names, cards, tables, forms, colors, fonts, capitalization, and breakpoints are implementation references only. They are not design requirements.

### 1.3 Out of scope

- Changes to backend APIs, data schemas, accounting rules, or permission enforcement
- Public deployment, billing, purchasing, or external service selection
- Reintroducing retired legacy behavior such as direct posted edits, destructive closes, arbitrary legacy code execution, device-specific printing, or physical-record identifiers
- A mood board, brand system, visual token set, or prescriptive wireframe in this brief

## 2. Product and operating model

### 2.1 Core product promise

The product helps finance teams reach financial truth with a reliable trail: users can see which company they are working in, what state each item is in, what they are allowed to do, what changed, who acted, and whether a financially significant operation reconciled.

### 2.2 Core object model

The design should make the following relationships understandable without requiring users to know the database model:

1. A user has one or more company memberships.
2. Each membership has a role, and the role grants capabilities within that company.
3. A company owns its accounts, fiscal years and periods, journals, budgets, reports, users, jobs, audit events, and migration runs.
4. A journal batch contains one or more entries; each entry contains debit and credit lines.
5. Draft batches progress through validation, approval, and posting.
6. Posted entries cannot be edited or deleted. Corrections are new, linked reversal entries.
7. Reports are calculated from governed ledger data and produce saved, digest-backed runs.

### 2.3 Representative users

Roles below describe common seeded workflows, not hard-coded product editions. The UI must respond to capabilities even when a custom role combines them differently.

| User mode | Primary goals | Typical access | Important restriction |
| --- | --- | --- | --- |
| Administrator | Configure the company, roles, imports, operations, and migration | Broad or unrestricted access | High-impact changes still require validation and audit evidence |
| Preparer | Create, revise, and validate journal drafts | Accounts and calendars for reference; journal creation and validation | Cannot approve or post under the standard maker-checker model |
| Approver | Independently review, approve, post, reverse, and reconcile | Journal workflow, inquiry, reports, and integrity | Cannot silently change the preparer's posted detail |
| Restricted viewer | Inspect authorized accounting information | Read-only accounts, journals, inquiry, and fiscal calendars | Mutation controls and unauthorized destinations are absent |

### 2.4 Capability inventory

Capabilities are company-specific. The design may group them into clearer categories, but it must support every combination and must not rely on a role name to decide visibility.

| Domain | Capabilities |
| --- | --- |
| Accounts | `accounts.view`, `accounts.create`, `accounts.update`, `accounts.delete`, `accounts.import` |
| Journals | `journals.view`, `journals.create`, `journals.update`, `journals.delete`, `journals.import`, `journals.validate`, `journals.approve`, `journals.self_approve`, `journals.post`, `journals.inquire`, `journals.reverse` |
| Fiscal and planning | `fiscal.view`, `fiscal.manage`, `fiscal.close`, `budgets.manage`, `integrity.run` |
| Standard reports | `reports.run`, `reports.saved`, `reports.chart`, `reports.trial_balance`, `reports.gl`, `reports.groups` |
| Custom reports | `reports.custom.run`, `reports.custom.design` |
| Administration | `company.manage`, `users.manage`, `preferences.manage`, `audit.view`, `administration.organize`, `migration.run` |

Authorization is enforced by the server. The frontend's responsibility is to avoid advertising unavailable actions, clearly explain a restriction when it is encountered, and never treat hidden controls as the security boundary.

## 3. Information architecture requirements

The current frontend exposes nine signed-in workspaces plus authentication. The designer may retain, merge, split, rename, or reorder these areas. The following capability coverage is required regardless of the proposed architecture.

| Current area | User question it answers | Required capability coverage |
| --- | --- | --- |
| Overview | What is the state of this company's books, and what needs attention? | Company context, posted-batch summary, recent journal activity, refresh, integrity result, task entry points |
| Accounts | What accounts can be used, and how are they governed? | Account list, creation, safe editing, posting and active status |
| Journals | What batches are being prepared, reviewed, approved, or posted? | Draft creation, draft maintenance, marking, bulk workflow, status transitions |
| Inquiry | What was posted, and how can an error be corrected safely? | Posted entry and line detail, linked reversal |
| Fiscal | Which periods exist and are open, and how is a new fiscal year defined? | Period/year visibility, 1–18-period calendar creation and review |
| Planning | What are the budgets, and can the year be closed safely? | Budget version save/list and fiscal close preview/execution |
| Reports | What governed output can be run, downloaded, or reproduced? | Standard report parameters, browser result, exports, saved runs |
| Designer | How can a structured custom statement be created and governed? | Definition library, structured editor, preview, versioning, templates, run/export, legacy report conversion |
| Administration | Who has access, how is the company configured, and what operations occurred? | Settings, roles, capabilities, memberships, imports, preferences, jobs, audit, legacy migration |

### 3.1 Global orientation

At every signed-in destination, users must be able to determine:

- the active company name and code;
- their signed-in identity and current company role;
- which destination or task is active;
- whether the displayed data is current, loading, stale, or failed;
- whether an action is unavailable because of permissions, invalid inputs, an object state, or a running operation; and
- how to switch company or sign out.

Changing company is a full context change, not a filter. Company-owned data, permissions, selections, previews, pending edits, and task state must reload or reset. The interface must never visually mix data from two companies.

### 3.2 Navigation behavior

- Destinations without any relevant capability should not appear in primary navigation.
- Read-only destinations remain useful when the user can view but not mutate their contents.
- Deep links or restored views must recheck the current membership and capability set.
- Keyboard navigation must remain possible. The current product offers shortcuts for journals, inquiry, reports, accounts, and custom reports; a redesigned shortcut model may replace these if it is discoverable, non-conflicting, and accessible.
- Navigation labels should use finance language that users can distinguish quickly. Do not rely on icons alone.

## 4. Functional design requirements by area

### 4.1 Authentication and company access

**User need:** Enter an authorized company workspace without disclosing account-security details.

Required inputs and information:

- Email and password
- In-progress sign-in state
- Generic invalid-credentials feedback
- Temporary lockout feedback after repeated failures
- No-company-access state with a safe sign-out path

Required behavior:

- Credentials are not persisted by the frontend session model.
- Failed authentication must not reveal whether an email exists or which credential was wrong.
- The workspace opens only after identity and memberships are loaded.
- If the user belongs to multiple companies, they can switch among active memberships only.

### 4.2 Company overview and integrity

**User need:** Understand the active company's immediate state and reach common tasks.

Required information:

- Active company and company code
- Count or summary of posted batches
- Recent journal batches with status and basic context
- Latest integrity-check outcome when one has been run

Required actions:

- Enter journal work
- Refresh company data
- Run integrity/reconciliation when granted `integrity.run`

The overview should prioritize actionable exceptions over decorative metrics. An integrity exception must not look like a routine success notification.

### 4.3 Chart of accounts

**User need:** Find valid accounts, understand whether they can receive postings, and maintain them without damaging history.

Required list data:

- Code, name, type, currency, postable status, and active status

Required creation data:

- Account code, name, type, three-letter currency code, and postable status
- Supported types: balance sheet, revenue/expense, retained earnings, and title

Required maintenance behavior:

- Authorized users may change name, postable status, and active status.
- Code, account type, and currency identity are immutable after creation.
- Title accounts cannot be postable.
- The retained-earnings account cannot be deactivated.
- An account referenced by an unposted journal cannot be deactivated.
- Historical accounts are deactivated, not physically deleted.
- Read-only users see the same accounting facts without mutation affordances.

Changes should receive success evidence that explains that posted history remains unchanged.

### 4.4 Journal preparation and workflow

**User need:** Create balanced work, move it through controlled review, and understand why a transition is or is not available.

Required draft inputs in the current minimum composer:

- Description
- Open fiscal period
- Amount
- Two different active, postable accounts: one debit and one credit
- Base currency context

The underlying model supports batches, entries, and multiple lines. A redesign should not create a dead end that prevents the interface from growing beyond the current two-line convenience composer.

Required batch information:

- Batch number, description, status, creation date, entry count, and available next action
- Statuses at minimum: draft, validated, approved, and posted

Required draft actions, when permitted:

- Rename/save, copy, delete, validate, mark/unmark, and apply a valid bulk transition

Required workflow behavior:

- Draft creation must reject a missing period or identical debit and credit accounts.
- Validation rechecks open period, account state, currency and rate rules, line sides, and base-currency balance.
- Approval must be performed by a different user unless `journals.self_approve` is explicitly granted.
- Posting revalidates and atomically commits entry state, balances, evidence, and audit history.
- Controls for invalid transitions are absent or disabled with an understandable reason.
- Bulk operations report both succeeded and failed items; one failure must not be presented as total success.
- Draft edit/copy/delete controls disappear once the batch leaves draft state.
- Posted content can never appear editable.

### 4.5 Posted journal inquiry and reversal

**User need:** Inspect immutable detail and correct an error without rewriting history.

Required entry information:

- Entry number, description, posting date, posted state, and whether it is a reversing entry
- For each line: account code/name, debit amount, and credit amount
- Linkage or clear relationship between original and reversal where available

Required reversal behavior:

- Available only with `journals.reverse` and only for an eligible original entry.
- Requires a meaningful reason and an available open fiscal period.
- Clearly states that the action posts a new equal-and-opposite entry; it does not edit the original.
- Success returns the user to evidence showing the new linked reversal.
- Reversal action is not offered again on a reversal entry.

### 4.6 Fiscal calendars

**User need:** See period boundaries and statuses, then create a valid company-specific fiscal year.

Required period information:

- Period number, label, start date, end date, and status
- Fiscal-year label and closed state where years are selected

Required creation behavior:

- Accept a year label, first day, period count from 1 through 18, and nominal days per period.
- Generate draft boundaries for review rather than saving immediately.
- Allow every generated label, start date, and end date to be reviewed and edited before save.
- Save only contiguous, ordered, non-overlapping periods contained within the fiscal year.
- Clearly distinguish draft boundaries from saved periods.

### 4.7 Budgets and fiscal close

**User need:** Maintain audited budget values and close a fiscal year only after a reconciled preview.

Budget requirements:

- Capture scenario, fiscal period, active postable account, base-currency code, and fixed-decimal amount.
- Saving a changed amount creates audited version history; it must not imply that prior evidence was erased.
- Show the currently returned budget rows with scenario, period, account, amount, and currency.
- Confirm successful version saves and expose validation failures near the affected task.

Fiscal-close requirements:

- Choose an open fiscal year and a valid later opening period.
- Generate a preview before execution.
- Preview must show reconciled versus exception status, profit/loss, closing-line count, and opening-line count.
- Execution remains unavailable until the current preview is balanced.
- Changing the fiscal year or opening period invalidates the existing preview.
- Execution posts immutable retained-earnings and opening entries and records the close; it never deletes or rewrites journals.
- Success must make the newly closed year state clear and prevent an accidental repeat close.

### 4.8 Standard reports

**User need:** Run a governed report, inspect it in the browser, download it, or reproduce a prior run.

Required report types:

- Trial balance
- General ledger listing
- Chart of accounts
- Transaction groups
- Pre-post journals
- Closing history
- Integrity report

Required parameters and outputs:

- Trial balance and general ledger require a fiscal-period selection.
- Output options are browser, PDF, CSV, and Excel.
- Browser output includes title, columns, rows, row count, and a 64-character content digest.
- Downloaded formats originate from the same calculated result and use governed filenames.
- Saved-run history identifies report type and run time and can reproduce the prior parameters and digest.
- Loading, generation, download, failure, and empty-result states must be distinguishable.

### 4.9 Custom report designer

**User need:** Build a safe structured statement without code execution, preview it, version it, and generate governed outputs.

Required library information:

- Definition name, report/template identity, version, conversion status, and current selection

Required definition data:

- Name, report title, decimal places from 0 through 6, and reusable-template status
- Columns with key, label, source, period/scope or formula, and budget scenario when applicable
- Column sources: ledger balance, budget, and formula
- Rows with key, label, type, source details, and emphasis flag
- Row types: account, account range, formula, heading, and spacer
- Named sections, their included rows, and supported page-break metadata

Required behavior:

- Preview evaluates the unsaved draft without creating a saved report run.
- Saving a new definition creates version 1.
- Updating requires the version currently loaded; a stale version must produce a conflict that protects the newer definition.
- A reusable template can be cloned to a non-template working copy.
- A saved definition can be run in the browser and exported to PDF or Excel from the current interface; the platform also supports CSV output.
- Results show title, rows, columns, row count, and digest.
- Keys must be understandable as formula references and remain valid when renamed.

Formula guardrails:

- References are limited to row or column keys.
- Operators are `+`, `-`, `*`, and `/`.
- Functions are `abs`, `min`, `max`, and `round`.
- Cycles, unknown names, imports, attribute access, and other function calls are rejected.
- Titles may use `{company_name}`, `{company_code}`, `{period_label}`, and `{as_of_date}`.
- Formula failures must identify the problem and must not leave a stale preview looking current.

Legacy GLREP conversion:

- Accept a definition name and pasted legacy matrix specification.
- Analysis never executes the legacy source.
- Classify the result as compatible, partial, or manual and show all warnings.
- Import is available only after analysis and retains the conversion status.
- Unsupported printer positioning, RTF commands, images, unsafe expressions, and ambiguous constructs require manual reconstruction.

### 4.10 Administration

Administration may be redesigned as several focused destinations. Do not force unrelated high-density tasks into one page merely because the current implementation does.

#### Company settings and role capabilities

- Company settings: name, fixed base currency display, IANA timezone, decimal places from 0 through 6, and rounding method.
- Base currency cannot be changed once the company is in use.
- Role configuration loads one role at a time and shows every capability with its description.
- Saving capabilities atomically replaces the role's explicit grants.
- System-role changes require especially clear scope and consequences.
- The company must retain at least one active administrator membership.

#### Users and roles

- Create a role with a name.
- Add a company user with email, display name, temporary password, and role.
- Display membership name, email, role, and active status.
- Change a membership's role or active status and save explicitly.
- Confirm changes with company-scoped audit evidence.
- Password and lockout copy must avoid leaking sensitive account details.

#### CSV imports

- Support account and journal CSV files.
- Separate file selection, preview, and apply.
- Preview reports total rows, valid rows or entries, and row-specific exceptions.
- Apply remains unavailable if validation errors exist or the preview no longer matches the selected file.
- A valid apply is atomic and returns a clear created/applied summary.
- Partial or stale results must never look like a successful full import.

#### Preferences and saved views

- Support comfortable and compact density preferences.
- Save a company-scoped display preference and a ledger view.
- Confirm which preference or view was saved.

#### Background operations

- Start integrity and trial-balance jobs when authorized.
- Show operation kind, status, and progress percentage.
- Support queued, running, succeeded, and failed/error outcomes.
- Results survive navigation and worker restarts; the UI should not imply that leaving the page cancels a durable job.

#### Audit history

- Show action, entity type, entity identifier, and company-local timestamp.
- Preserve the distinction between audit evidence and editable activity notes.
- Provide a refresh path and an understandable empty state.
- Unexpected failures should expose a correlation reference when one is supplied by the API.

#### Legacy data migration

- Accept a flat ZIP containing read-only DBF snapshots, including required account and ledger tables and optional currency, pre-post, and report tables.
- Stage a read-only trial before any apply action.
- Show staged row count, blocking-row count, warnings, ledger balanced/difference state, debit and credit totals, account-period reconciliation, source digest, and blocking reason.
- Show record-level exceptions with source table, record number, severity, issue code, message, and blocking status; support a governed exception CSV download.
- Preserve a history of trial and apply runs with source, trial/applied identity, and status.
- Apply is available only when the current trial is apply-ready, all blocking differences are cleared, and the target company is empty.
- Apply requires the exact source digest and an explicit `APPLY` confirmation.
- Application is atomic across accounts, journals, budgets, reports, and lineage.
- A failed or blocked apply must leave existing target data visibly unchanged.

## 5. Critical end-to-end journeys

The designer should validate the proposed architecture against these journeys. A journey may cross several destinations; users should not lose company context, selections, review evidence, or their understanding of object state.

| Journey | Prerequisites | Required progression | Success evidence | Important failure/recovery behavior |
| --- | --- | --- | --- | --- |
| Sign in and switch company | Valid user with at least one active membership | Authenticate → load memberships → enter company → optionally switch company | New company name/code, role, capabilities, and company-owned data are visibly active | Generic authentication errors; lockout state; no-access state; switch clears old-company task state |
| Journal maker-checker lifecycle | Open period, two active postable accounts, required capabilities distributed across users | Create draft → optionally edit/copy → validate → independent approve → post → inspect | Status advances at each step; posting evidence and immutable inquiry detail appear | Explain validation errors; block self-approval unless granted; prevent invalid/repeated transitions; never show partial posting |
| Correct a posted journal | Posted original, open period, reversal capability | Find entry → inspect lines → enter reason → post linked reversal | Original remains visible and unchanged; reversing entry and relationship are visible | Block when no open period exists; preserve entered context after recoverable failure |
| Maintain accounts and calendar | Company-management capabilities | Create/update account; generate 1–18 periods → review every boundary → save year | Audit-aware account confirmation; validated fiscal year and periods appear | Explain protected title/retained-earnings states, referenced accounts, period overlaps, gaps, and invalid bounds |
| Version budget and close year | Budget/close capabilities, open year, later opening period | Save/revise budget → select year/opening period → preview → review reconciliation → execute | Version-save confirmation; closed year and immutable closing/opening evidence | Invalidate stale preview; block unbalanced or repeated close; never imply history was replaced |
| Run and reproduce report | Report capability and required period | Choose report/parameters/output → run → inspect or download → select saved run → reproduce | Result title, rows, digest, saved-run entry, or governed download | Keep parameter context on failure; distinguish empty result from error; never display stale output as the new run |
| Design custom report | Custom design/run capabilities | Select/new → edit structure → preview → save/version → run/export or clone template | Valid matrix preview, version number, digest, and audited output | Surface formula errors; clear stale preview; protect concurrent edits with a version conflict |
| Preview and apply CSV | Import capability and selected CSV | Select file → preview → resolve errors → apply matching validated file | Row/entry summary and atomic apply confirmation | Disable apply on errors or changed file; show row-level issues and partial-success detail if returned |
| Administer access and operations | Relevant admin capabilities | Configure settings/roles/memberships/preferences; start job; inspect audit | Explicit company-scoped confirmations and durable status/audit evidence | Protect last administrator; explain permission denial; retain failed job details and correlation reference |
| Migrate legacy snapshot | Migration capability, complete snapshot, empty target for apply | Upload ZIP → read-only trial → inspect digest/reconciliation/exceptions → type confirmation → apply | Reconciled trial, matching digest, atomic apply result, and run history | Block source/reconciliation errors, wrong digest/confirmation, or non-empty target; show that the ledger was not changed |

## 6. High-risk action safeguards

The interaction pattern is a design decision, but each action below must have the listed protection. Disabled controls alone are insufficient when the reason is not obvious.

| Action | Required safeguard before execution | Required result communication |
| --- | --- | --- |
| Delete draft batch | Confirm the exact draft; action only exists in draft state and with permission | Draft is absent after refresh; unrelated batches remain |
| Validate, approve, or post | Show current status and next transition; enforce capability and maker-checker rules | New status or specific failure; posting reports no success until the atomic commit finishes |
| Bulk journal transition | Show selection count and intended transition; exclude or explain ineligible items | Counts and identities of succeeded and failed items |
| Reverse posted entry | Show the original entry, require reason, explain linked equal-and-opposite posting | Original remains immutable; reversal link and posting result appear |
| Deactivate account | Explain protected/reference conditions and historical preservation | New inactive state or precise blocking reason |
| Save fiscal year | Require review of every generated boundary | Saved year/periods or field-level boundary errors |
| Execute fiscal close | Current balanced preview tied to selected year and opening period | Closed state plus immutable close/opening evidence; no ambiguous retry |
| Apply CSV import | Preview of the same file with zero blocking errors | Atomic row/entry summary; no partial-success presentation unless explicitly reported |
| Replace role capabilities | Identify company and role and communicate whole-set replacement | Updated grants and audit confirmation |
| Deactivate membership | Identify user/company and protect the last active administrator | Updated membership or explicit guardrail failure |
| Apply legacy migration | Apply-ready trial, empty target, visible digest, and exact `APPLY` confirmation | Atomic imported counts/lineage or proof that nothing changed |

## 7. Shared states and feedback

Every destination and task must account for the following states. The designer should specify these states at the component and page level rather than providing only ideal populated screens.

| State | Design requirement |
| --- | --- |
| Initial loading | Identify what is loading; prevent actions that rely on missing company data; announce long waits accessibly |
| Refreshing | Preserve usable current content where safe while indicating that newer data is being requested |
| Empty | Explain whether there is no data, no matching data, no company access, or no available action; provide a valid next step when one exists |
| Validation error | Associate errors with affected inputs and provide an error summary for complex forms; preserve valid user input |
| Authorization restriction | Omit unavailable primary actions and provide a clear permission explanation when a deep link or changed role causes denial |
| Domain guardrail | Explain accounting reasons such as closed period, protected retained earnings, non-postable account, non-empty migration target, or unbalanced journal |
| Partial success | Identify succeeded and failed records individually or by actionable counts; never collapse into a generic success banner |
| Stale-version conflict | Preserve the user's draft, explain that a newer custom-report version exists, and provide a safe path to compare/reload before retrying |
| Background progress | Show queued/running status and persisted progress; allow navigation without implying cancellation |
| Completion | State what changed, in which company, and what evidence or next state is available |
| Destructive confirmation | Name the affected object and consequence; avoid vague confirmations such as “Are you sure?” |
| Unexpected failure | State that the action did not complete, retain recoverable input, offer retry where safe, and show a correlation reference when available |
| Stale result | Visually distinguish an earlier preview/report from the parameters currently being edited, or clear it when it is no longer valid |

Feedback must use more than color. Status text, icons, labels, and accessible announcements should communicate the same meaning.

## 8. Data, content, and formatting rules

### 8.1 Financial data

- Align comparable numeric columns consistently and use tabular numerals or an equivalent readable treatment.
- Keep debit and credit in distinct, explicitly labelled columns.
- Display the relevant currency code with amounts whenever currency could be ambiguous.
- Preserve configured decimal places and fixed-decimal values; do not abbreviate amounts in transactional or reconciliation views.
- Negative values, zero values, totals, variances, and exceptions must remain distinguishable without color alone.
- Report and reconciliation tables must remain readable with long account names and large values.

### 8.2 Dates and times

- Display fiscal dates unambiguously and consistently.
- Period labels do not replace start and end dates where boundary review matters.
- Operational and audit timestamps use the active company's configured IANA timezone.
- If a localized display format is used, machine-readable or unambiguous detail should remain available where audit interpretation matters.

### 8.3 Identifiers and evidence

- Preserve meaningful business identifiers such as company code, account code, batch number, and entry number.
- Technical UUIDs may be secondary but must remain available in audit and support contexts where they are the recorded entity identifier.
- Source and result digests should be selectable/copyable and shown in full where verification is required.
- Do not use physical record numbers as general application identity; legacy record numbers appear only as migration lineage evidence.

### 8.4 Language

- Use precise states: draft, validated, approved, posted, open, closed, trial, applied, queued, running, succeeded, failed, compatible, partial, and manual.
- Do not use “delete” when the accounting behavior is deactivation or reversal.
- Do not describe fiscal close as destructive; it appends closing and opening entries.
- Explain specialized terms in context, particularly maker-checker, digest, reconciliation, retained earnings, and apply-ready.

## 9. Responsive and accessibility requirements

The current release target is stable desktop Chrome and tests cover three Chrome viewport sizes. The redesigned experience must remain usable at desktop, compact desktop/tablet, and narrow/mobile widths even when dense accounting data requires horizontal scrolling or a focused detail view.

### 9.1 Responsive behavior

- Preserve task priority and active-company context at every viewport.
- Do not hide financially significant fields merely to fit a narrow layout.
- Tables may transform, scroll, or split into summary/detail views, but row identity and column meaning must remain clear.
- Bulk selection and actions must remain associated with the selected records.
- Long forms and designers should preserve section progress and entered values when their layout changes.
- Sticky regions must not trap content, obscure focused controls, or consume the narrow viewport.
- Download and report workflows must remain operable on a narrow viewport even if detailed report review is optimized for larger screens.

### 9.2 Accessibility

- Meet WCAG 2.2 AA as the design target.
- Provide a logical heading structure, landmarks, form labels, table captions or equivalent context, and programmatic status relationships.
- All navigation, selection, editing, confirmation, and dismissal must work by keyboard.
- Focus order follows the visible task order; focus is restored or moved intentionally after navigation, errors, dialogs, and completed actions.
- Focus indicators remain visible against every surface and state.
- Errors and asynchronous status changes use appropriate live announcement behavior without repeatedly interrupting the user.
- Color contrast meets AA, and meaning never depends on color alone.
- Touch targets and spacing support users with reduced dexterity.
- Motion respects reduced-motion preferences and is never the only way a state change is communicated.
- Dense data remains understandable under browser zoom and text resizing.

## 10. Expected design handoff

The designer's output should include:

- A proposed information architecture mapping every required capability in this brief
- Primary journeys for preparer, approver, administrator, and restricted-viewer modes
- Responsive designs for authentication, a representative data workspace, journal workflow, a high-risk preview/execute flow, reporting, and administration
- Interaction specifications for capability-based visibility, company switching, status transitions, bulk actions, previews, confirmations, and stale results
- Component and state coverage for tables, forms, status labels, banners/notifications, empty/loading/error states, progress, and confirmations
- Accessibility annotations for keyboard order, focus management, live regions, table semantics, and responsive transformations
- A short rationale for any regrouping or renaming of the nine current areas

The handoff does not need to preserve current React component boundaries. It must make clear how each mandatory behavior is represented and how engineers can distinguish design intent from optional enhancement.

## 11. Traceability matrix

The following sources are implementation evidence, not visual references.

| Requirement or journey | Current implementation evidence | Acceptance evidence |
| --- | --- | --- |
| Authentication, lockout, company isolation, restricted access | `frontend/src/App.tsx`; `backend/app/api/routes/auth.py` | `frontend/e2e/auth-company/should-lock-new-user-after-five-failures.spec.ts`; `should-isolate-company-workspaces.spec.ts`; `should-enforce-restricted-navigation.spec.ts` |
| Overview, global company context, capability navigation | `frontend/src/App.tsx` | `frontend/src/AppWorkspaces.test.tsx`; auth/company E2E scenarios |
| Accounts | `frontend/src/AccountManager.tsx`; `backend/app/api/routes/accounts.py` | `frontend/e2e/accounts-fiscal/should-maintain-account-and-calendar.spec.ts`; `should-enforce-account-and-calendar-boundaries.spec.ts` |
| Fiscal calendars | `frontend/src/FiscalCalendarManager.tsx`; `backend/app/api/routes/fiscal.py` | Accounts/fiscal E2E scenarios |
| Journal draft lifecycle and maker-checker posting | `frontend/src/App.tsx`; `backend/app/api/routes/journals.py`; `backend/app/services/accounting.py` | `frontend/e2e/journals/should-manage-independent-draft-lifecycle.spec.ts`; `should-complete-maker-checker-cycle.spec.ts`; `should-reject-identical-journal-accounts.spec.ts` |
| Posted inquiry and reversal | `frontend/src/App.tsx`; journal routes and accounting service | `frontend/e2e/journals/should-complete-maker-checker-cycle.spec.ts` |
| Budgets and close | `frontend/src/App.tsx`; `backend/app/api/routes/planning.py`; `backend/app/services/closing.py` | `frontend/e2e/planning/should-version-budget-and-close-northstar.spec.ts` |
| Standard reports and saved runs | `frontend/src/App.tsx`; `backend/app/api/routes/reports.py` | `frontend/e2e/reports/should-run-reproduce-and-export-standard-report.spec.ts` |
| Custom report design and GLREP conversion | `frontend/src/CustomReportDesigner.tsx`; custom-report route/service | `frontend/e2e/custom-reports/should-design-version-export-and-convert-report.spec.ts`; `should-reject-unsafe-formula-and-classify-manual-legacy.spec.ts` |
| Company settings and role capabilities | `frontend/src/AdministrationSettings.tsx`; administration routes | `frontend/e2e/administration/should-manage-role-user-and-preferences.spec.ts` |
| Memberships, CSV imports, preferences, jobs, audit | `frontend/src/App.tsx`; administration/import routes; worker | `frontend/e2e/administration/should-preview-import-and-run-integrity-job.spec.ts`; `should-manage-role-user-and-preferences.spec.ts` |
| Legacy data migration | `frontend/src/LegacyMigrationPanel.tsx`; migration route/service | `frontend/e2e/migration/should-stage-reconcile-and-block-nonempty-apply.spec.ts`; `should-report-unbalanced-migration-exceptions.spec.ts` |
| Cross-cutting accounting and release controls | `docs/ARCHITECTURE.md`; `docs/USER_GUIDE.md`; `docs/LEGACY_PARITY.md` | `docs/TEST_PLAN.md`; `docs/UAT_CHECKLISTS.md` |

## 12. Design acceptance checklist

A design proposal is ready for engineering review when all answers below are yes.

- Can every user identify the active company before reading or changing financial data?
- Does the design work for arbitrary capability combinations rather than only the four representative roles?
- Can a preparer complete work without seeing approval/posting as if they were available?
- Can an approver review provenance and state before approving or posting?
- Are posted entries always presented as immutable, with reversal as the correction path?
- Do close, import, and migration clearly separate preparation or preview from execution?
- Does every high-risk action state its scope and provide unambiguous success or failure evidence?
- Are partial success, stale previews, version conflicts, and background progress designed explicitly?
- Can reports and reconciliations be inspected without losing columns, currency, precision, or digest evidence?
- Are all loading, empty, read-only, error, restricted, and completion states covered?
- Are keyboard, focus, semantics, contrast, zoom, and narrow-width behavior annotated?
- Can engineers map every designed area back to the traceability matrix without consulting the current visual styling?

