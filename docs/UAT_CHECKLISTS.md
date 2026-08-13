# Finance user-acceptance checklists

## Rules and evidence

Run these scripts only in the isolated staging release candidate. Record tester, role, build SHA,
dataset manifest SHA, start/end time, result, screenshots/report digests, defects, and comments for
every scenario. A tester must not approve a scenario they performed under a different role. Mark
an item `blocked`, never `pass`, when prerequisite data or authority is missing. Store the signed
result as `artifacts/release/uat-results.json` using this shape:

```json
{
  "release_candidate": "git-sha",
  "dataset_manifest_sha256": "sha256",
  "scenarios": [{"id": "UAT-PREP-01", "tester": "name", "result": "pass|fail|blocked", "evidence": ["reference"], "defects": []}],
  "approvals": {"accounting": {"status": "pending", "approver": null, "timestamp": null}}
}
```

Human approval is mandatory; generating this file does not constitute approval.

## Administrator

- `UAT-ADM-01`: Create an empty migration company, assign base currency and configure all source
  fiscal periods; prove a missing calendar blocks staging.
- `UAT-ADM-02`: Grant `migration.run` to the cutover role only; prove another role receives a
  permission denial and cannot view another company's run identifier.
- `UAT-ADM-03`: Stage the sanitized small and boundary archives, download exceptions, compare the
  source digest/file hashes with the fixture manifest, and confirm staging changed no ledger rows.
- `UAT-ADM-04`: Prove wrong digest, wrong confirmation, blocked fixture, and non-empty target all
  prevent apply. Apply the clean fixture once and confirm a repeated request returns the same run.
- `UAT-ADM-05`: Review users, roles, audit events, worker completion, and configuration guardrails.

## Preparer

- `UAT-PREP-01`: Inspect imported draft groups, account, date, period, reference, description,
  debit/credit, currency, and source lineage; do not post them.
- `UAT-PREP-02`: Enter and validate routine, correction, FX, and period-boundary journals. Confirm
  validation explains unbalanced, invalid-account, and closed-period failures.
- `UAT-PREP-03`: Compare imported budgets with signed source totals for each scenario and period.

## Approver

- `UAT-APPR-01`: Independently inspect and approve a preparer's journal, then confirm the preparer
  cannot self-approve when maker-checker separation applies.
- `UAT-APPR-02`: Post, inquire, and reverse the approved journal. Confirm the original posted entry
  is immutable, the reversal is linked, and both actions are audited.
- `UAT-APPR-03`: Review imported posted batches against source group counts and debit/credit totals.

## Finance lead

- `UAT-FIN-01`: Reconcile account count, opening/current net, per-period balances, posted/draft
  groups, budgets, and report dispositions against signed controls.
- `UAT-FIN-02`: Run trial balance, GL listing, transaction group, budget comparison, and compatible
  custom reports; retain parameters, digests, and exports.
- `UAT-FIN-03`: Preview and execute year-end close in a separate UAT company; validate retained
  earnings, opening entries, repeat-close prevention, and compensating correction.
- `UAT-FIN-04`: Classify every legacy difference as defect, corrected legacy behavior, or
  intentionally retired behavior, with approver and evidence reference.

## Operations

- `UAT-OPS-01`: Record release image identifiers, application version, migration head, environment
  guardrails, and dataset checksums.
- `UAT-OPS-02`: Perform the guarded backup, checksum, isolated restore, upgrade, smoke, and
  read-only verification procedure in `RELEASE_REHEARSAL.md`; record actual RPO/RTO observations.
- `UAT-OPS-03`: Rehearse rollback by restoring the pre-upgrade backup into a second clean replacement
  database. Never downgrade or overwrite staging.
- `UAT-OPS-04`: Confirm logs/correlation IDs, monitoring, worker recovery, retained evidence, and
  documented go/no-go contacts.

## Acceptance

Every scenario must pass or have an explicitly approved disposition. There must be zero P0/P1,
financial-integrity, tenant-isolation, migration-atomicity, or restore failures. Accounting, QA,
security, operations, and the release owner must approve the evidence manifest separately.
