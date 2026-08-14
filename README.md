# CTec General Ledger Modernization

This directory contains the modern CTec General Ledger. The legacy VB6 application in `../I26`
remains untouched and can coexist with it; PostgreSQL is authoritative for the modern system and
legacy DBFs are read-only migration inputs.

## Clean Compose start

Prerequisite: Docker Desktop with Compose.

```powershell
Copy-Item .env.example .env
# For any shared environment, replace database credentials and JWT_SECRET first.
docker compose up --build -d
docker compose exec api python -m app.seed
docker compose ps
```

Open `http://localhost:5173`; API documentation is `http://localhost:8000/docs`. The seed imports
the packaged read-only ALCAN legacy sample; deterministic local credentials and workflows are in
`docs/USER_GUIDE.md` and `docs/DEMO_DATA.md`.
Compose starts PostgreSQL, the API, the static web client, and a separate durable-operation worker.

## Local development

Prerequisites: Docker Desktop, Node.js 22+, and Python 3.12+.

```powershell
Copy-Item .env.example .env
docker compose up -d db
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".\backend[dev]"
alembic -c backend/alembic.ini upgrade head
python -m app.seed

Set-Location frontend
npm ci
npm run dev
```

`python -m app.seed` never replaces an existing database. Automated tests use the separate
`python -m app.test_seed` synthetic fixture entry point.

In another terminal:

```powershell
Set-Location modern
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --app-dir backend --reload --port 8000
```

## Verification

```powershell
docker compose up -d db
.\.venv\Scripts\Activate.ps1
ruff format --check backend/app backend/tests backend/alembic
ruff check backend/app backend/tests backend/alembic
mypy --config-file backend/pyproject.toml backend/app
pytest backend
python scripts/test.py backend
alembic -c backend/alembic.ini current
alembic -c backend/alembic.ini check

Set-Location frontend
npm ci
npm run lint
npm run typecheck
npm test
npm run test:coverage
npm run build
npx playwright test --retries=0
```

The portable test entry point can run the same gates from the `modern` directory:

```powershell
python scripts/test.py frontend
python scripts/test.py e2e-seed
python scripts/test.py all
```

Playwright uses isolated ports 18000/15173 and a guarded `ctec_gl_e2e` database by default; it
does not reuse the demonstration services on ports 8000/5173. See `docs/TEST_PLAN.md` for
environment overrides, traceability, artifact locations, and release gates.

Stage 6 security/performance/resilience uses a separate named Compose project and does not run as
part of `all`. Inventory scanners before release, then follow the disruptive-test runbook:

```powershell
python scripts/test.py stage6-security-inventory
docker compose -p ctec-stage6 -f docker-compose.stage6.yml up --build -d
python scripts/test.py stage6-load-smoke
```

See `docs/NON_FUNCTIONAL_TESTING.md` before running the full security, 35-minute load, Chrome
metrics, or API/worker/database resilience gates.

Stage 7/8 synthetic migration and release-control checks are non-destructive:

```powershell
python scripts/test.py stage7-fixtures
python scripts/test.py stage7-migration
python scripts/test.py stage8-controls
python scripts/test.py stage8-rehearsal-self-check
python scripts/test.py stage8-evidence-draft
```

The evidence draft intentionally remains blocked until external runs and human approvals are
attached. See `docs/UAT_CHECKLISTS.md` and `docs/RELEASE_REHEARSAL.md` before any rehearsal.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/FRONTEND_DESIGN_BRIEF.md` — functional frontend source of truth
- `design-system/README.md` — approved visual and interaction reference
- `docs/DESIGN_SYSTEM_ADOPTION.md` — phased production-adoption roadmap
- `docs/USER_GUIDE.md`
- `docs/DEMO_DATA.md`
- `docs/MIGRATION_GUIDE.md`
- `docs/OPERATIONS.md`
- `docs/BACKUP_RECOVERY.md`
- `docs/SECURITY.md`
- `docs/LEGACY_PARITY.md`
- `docs/IMPLEMENTATION_TRACKER.md`
- `docs/TEST_PLAN.md`
- `docs/NON_FUNCTIONAL_TESTING.md`
- `docs/UAT_CHECKLISTS.md`
- `docs/RELEASE_REHEARSAL.md`
- `docs/adr/`

No public deployment, service purchase, credential exposure, or real legacy-data mutation is part
of this repository workflow.
