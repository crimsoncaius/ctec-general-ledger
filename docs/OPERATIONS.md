# Operations runbook

## Supported topology

The supplied Compose topology is intended for local evaluation and controlled private hosting.
Production requires an approved HTTPS reverse proxy/load balancer, managed secret injection,
restricted PostgreSQL networking, durable encrypted storage, monitoring, and the backup controls
in `BACKUP_RECOVERY.md`. Do not expose the Compose ports directly to the public internet.

## Start and stop

From `modern/`:

```powershell
Copy-Item .env.example .env
# Replace JWT_SECRET and database credentials before any shared environment.
docker compose up --build -d
docker compose exec api python -m app.seed
docker compose ps
```

Open `http://localhost:5173`; API health is `http://localhost:8000/health`. The seed command is
idempotent: it creates the complete deterministic demonstration only when no user exists.

Graceful stop preserves the named PostgreSQL volume:

```powershell
docker compose stop
```

`docker compose down` removes containers and the network but preserves the volume unless `-v` is
explicitly supplied. Never use `-v` against an environment whose data has not been backed up and
verified.

## Upgrade

1. Take and verify a backup.
2. Review new ADRs and migration notes.
3. Build images: `docker compose build`.
4. Inspect migration SQL in a rehearsal database.
5. Stop write traffic, then run `docker compose run --rm api alembic upgrade head`.
6. Start services and verify `/health`, sign-in, company context, integrity, trial balance, and a
   saved report reproduction.
7. Retain the previous images and backup until acceptance.

Alembic migrations are forward-oriented. Database rollback for a failed production release uses
the verified pre-upgrade backup; do not improvise destructive downgrades.

## Health, logs, and jobs

```powershell
docker compose ps
docker compose logs --since 15m api
docker compose logs --since 15m worker
docker compose logs --since 15m db
docker compose exec api alembic current
```

Use the response `X-Correlation-ID` to locate a request. The worker durably claims queued jobs
from PostgreSQL; run at least one worker and scale it only after monitoring database capacity.
Application audit history is business
evidence and is not a substitute for infrastructure logs. Background integrity/report jobs show
queued/running/succeeded/failed state and error details in Administration.

Alert on repeated API/container restarts, database health failures, authentication lockouts,
failed operations, migration failures, integrity differences, backup failures, storage growth,
and clock drift. Keep hosts and containers synchronized to trusted time.

## Incident response

1. Stop or restrict write traffic; do not delete evidence.
2. Record time, company, user, correlation IDs, operation IDs, and observed balances.
3. Export relevant audit/operation history and preserve logs.
4. Run read-only reports/integrity checks only if they cannot worsen the incident.
5. Restore in an isolated environment for analysis when corruption is suspected.
6. Corrections to posted accounting use reversals; never edit database rows directly.
7. Follow the recovery and validation sequence in `BACKUP_RECOVERY.md` before reopening writes.
