# Guarded release rehearsal

## Safety model

The running Compose database `ctec_gl` may be used as a read-only backup source, but never as a
restore or upgrade target. Restore/upgrade targets must be pre-provisioned, empty databases named
`ctec_gl_restore_*` or `ctec_gl_rehearsal_*`. The tooling rejects the live database name, rejects
identical source/target identities, verifies the backup checksum before restore, refuses non-empty
targets, never overwrites a backup, and contains no downgrade operation.

`pg_dump`, `pg_restore`, and `psql` must be available. Supply credentials via a protected URL or
PostgreSQL credential facility; never commit them. Commands redact passwords in output.

## Synthetic legacy data

`backend/tests/fixtures/legacy_dbf/profiles.json` defines small, medium, corrupt, and boundary
synthetic datasets. Generate ZIPs and controls under ignored artifacts, or validate generation in
memory:

```powershell
python scripts/generate_legacy_fixtures.py --check
python scripts/generate_legacy_fixtures.py
```

Each generated manifest identifies the source profile checksum. Each control file records archive
SHA-256, expected disposition, counts, opening net, ledger debit/credit totals, periods, and
expected faults. Replace none of these fixtures with real data.

## Backup and isolated restore

Set protected shell variables for the read source and clean isolated target, then run:

```powershell
python scripts/release_rehearsal.py self-check
python scripts/release_rehearsal.py backup --source-url $env:REHEARSAL_SOURCE_DATABASE_URL --output artifacts/release/pre-upgrade.dump
python scripts/release_rehearsal.py restore --source-url $env:REHEARSAL_SOURCE_DATABASE_URL --target-url $env:REHEARSAL_TARGET_DATABASE_URL --backup artifacts/release/pre-upgrade.dump --sha256 <recorded-sha256> --acknowledge "RESTORE TO ISOLATED TARGET"
python scripts/release_rehearsal.py upgrade --target-url $env:REHEARSAL_TARGET_DATABASE_URL --acknowledge "RESTORE TO ISOLATED TARGET"
python scripts/release_rehearsal.py verify --target-url $env:REHEARSAL_TARGET_DATABASE_URL | Tee-Object artifacts/release/restore-verification.json
```

Run the critical smoke pack against API/web instances configured on non-live ports and pointing
only at the restored target: authentication, company context, balanced journal, maker-checker,
posting, inquiry, reversal, integrity, trial balance, saved-report reproduction, and worker job.
The `verify` command is deliberately read-only and reports migration revision plus key row counts;
financial reconciliation, immutability, saved digests, and smoke results must be attached separately.

## Rollback rehearsal

Provision a second empty `ctec_gl_rehearsal_*` database and restore the same pre-upgrade dump into
it. Start the previous application image against that replacement and run its compatible smoke
pack. Do not run `alembic downgrade`, drop the upgraded database, repoint the running demonstration
stack, or overwrite evidence. Record elapsed restore/recovery time and the observable data-loss
window. RPO 24 hours and RTO 4 hours are planning targets, not achieved claims.

## Evidence and release decision

Generate a draft evidence manifest:

```powershell
python scripts/release_evidence.py
python scripts/release_evidence.py --validate artifacts/release/evidence-manifest.json
```

Validation is expected to remain blocked until all artifacts and named human approvals are
present. The generator explicitly initializes long performance, external security, UAT, and
release approval claims as false/pending. Reviewers may update the manifest only after examining
the referenced immutable evidence.

The evidence generator consumes the Stage 6 tool outputs at
`artifacts/performance/load-release.json` and `artifacts/resilience/summary.json`, together with
`artifacts/security/summary.json`. An unavailable Git worktree is recorded as `unavailable`; it is
not mislabeled as a dirty release candidate.
