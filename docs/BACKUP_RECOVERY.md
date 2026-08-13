# Backup and recovery

## Policy

PostgreSQL contains the authoritative ledger, configuration, audit history, report run evidence,
and migration lineage. Back up the entire database, not selected accounting tables. Encrypt
backups, restrict access, keep an off-host copy, define retention with finance/compliance, and
test restoration regularly. A backup is not accepted until its checksum and isolated restore are
verified.

The business owner must set recovery point and recovery time objectives. A reasonable starting
control is nightly full logical backups plus database-level continuous recovery for production,
with quarterly restore exercises; this is guidance, not an achieved SLA in local Compose.

## Compose backup rehearsal

Create a timestamped directory, then have PostgreSQL write a custom-format dump inside its own
container and copy it out:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = Join-Path (Get-Location) "backups\$stamp"
New-Item -ItemType Directory -Path $backupDir | Out-Null
docker compose exec db pg_dump -U ctec -d ctec_gl -Fc -f /tmp/ctec-gl.dump
docker compose cp db:/tmp/ctec-gl.dump "$backupDir\ctec-gl.dump"
docker compose exec db rm -f /tmp/ctec-gl.dump
Get-FileHash "$backupDir\ctec-gl.dump" -Algorithm SHA256 | Format-List
```

Do not store long-lived backups in the repository or on the same disk as PostgreSQL.

## Isolated restore test

Never test a restore over the live database. Provision a separate PostgreSQL instance/database,
copy the dump into it, and run:

```powershell
createdb -h <rehearsal-host> -U <restore-role> ctec_gl_restore_test
pg_restore -h <rehearsal-host> -U <restore-role> -d ctec_gl_restore_test --exit-on-error .\backups\<stamp>\ctec-gl.dump
```

Point an isolated API instance at the restored database and verify:

- Alembic reports the expected revision;
- table counts and the backup checksum match the evidence record;
- users can authenticate only with rehearsal credentials/network controls;
- each company passes integrity and period-balance reconciliation;
- trial balance agrees with journal detail;
- posted immutability triggers reject mutation;
- closing and migration history are present; and
- representative saved reports reproduce their digests.

Destroy the rehearsal environment through the approved infrastructure process after evidence is
retained.

## Production recovery sequence

Recovery is an authorized destructive operation and must be approved by the incident owner:

1. Preserve the failed database, logs, and last known-good backup metadata.
2. Isolate application writers.
3. Provision a clean replacement database rather than overwriting evidence.
4. Restore the selected full backup and, when configured, replay WAL to the approved point.
5. Run migrations only if the application release requires them.
6. Complete every isolated-restore verification above.
7. Repoint the API, start read-only acceptance, then reopen writes with finance sign-off.
8. Record actual data-loss window, recovery duration, checks, approvers, and follow-up actions.

For the guarded portable implementation, use `scripts/release_rehearsal.py` as documented in
`docs/RELEASE_REHEARSAL.md`. It rejects live-name restore targets, non-empty targets, checksum
mismatches, and source/target identity. It has no downgrade command.
