# Stage 6 security, performance, and resilience

## Safety boundary

Stage 6 is deliberately separate from the demonstration Compose stack. Its fixed defaults are:

| Resource | Stage 6 | Demonstration resource that is refused |
| --- | --- | --- |
| Compose project | `ctec-stage6` | default project |
| PostgreSQL database/port | `ctec_gl_stage6` / 25432 | `ctec_gl` / 15432 |
| API port | 28000 | 8000 |
| Web port | 25173 | 5173 |
| Volume | `ctec-stage6_ctec_stage6_pgdata` | `ctec_pgdata` |

Every Python/Chrome entry point validates its URL and database name before making requests.
Stateful tools accept only database names beginning `ctec_gl_stage6`, `ctec_gl_perf`,
`ctec_gl_e2e`, or `ctec_gl_test_`. Do not weaken these guards. The resilience drill stops and
restarts services and must never be pointed at a shared environment.

Start and seed the isolated stack from `modern`:

```powershell
docker compose -p ctec-stage6 -f docker-compose.stage6.yml up --build -d
docker compose -p ctec-stage6 -f docker-compose.stage6.yml ps
```

Remove it only when its resolved project is visibly `ctec-stage6`:

```powershell
docker compose -p ctec-stage6 -f docker-compose.stage6.yml down
# Add --volumes only when the disposable Stage 6 dataset should be destroyed.
```

## Security gate

The gate is fail-closed. A missing scanner, missing pinned image, finding, or scanner execution
error fails `stage6-security`; inventory mode reports gaps but never represents release approval.

Required versions and setup:

- Gitleaks 8.27.2 on `PATH` for source secret scanning with `.gitleaks.toml`.
- The backend dev extra, which pins Bandit 1.8.6 and pip-audit 2.9.0.
- Node.js 22/npm for `npm audit --package-lock-only --audit-level=high`.
- Trivy 0.65.0 on `PATH`; build `ctec-gl-api:stage6` and `ctec-gl-web:stage6` first.
- Pinned `zaproxy/zap-stable:2.16.1` present locally. The ZAP runner authenticates to the isolated
  API, selects ACME from the explicit `app.test_seed` synthetic fixture, injects bearer/company
  headers without writing them to evidence, imports the OpenAPI contract, and fails on ZAP
  warnings or alerts.

```powershell
pip install -e ".\backend[dev]"
python scripts/test.py stage6-security-inventory
docker pull zaproxy/zap-stable:2.16.1
python scripts/test.py stage6-security
```

Evidence is written under `artifacts/security`: redacted scanner logs/reports, Trivy JSON, ZAP
HTML/JSON/Markdown, and `summary.json`. Review JWT lifetime/lockout, CORS and security headers,
tenant IDOR, privilege escalation, maker-checker separation, upload traversal/bombs, spreadsheet
formula injection, report formulas, sensitive exports, and error leakage manually as well. The
release gate permits no critical/high finding; medium findings require owner, mitigation, and due
date in the release evidence.

## Performance and browser metrics

Populate at least 100,000 journal lines and three fiscal years for every active company. The loader
uses deterministic balanced two-line entries, posting evidence, and reconciled period balances in
the guarded database only:

```powershell
python scripts/test.py stage6-data
```

The smoke profile is an eight-second 2-user phase plus an eight-second 3-user spike. It proves the
harness and thresholds without claiming release scale. The release profile runs 15 users for 30
minutes followed by a five-minute 30-user spike and refuses datasets below 100,000 lines for the
selected company.

```powershell
python scripts/test.py stage6-load-smoke
python scripts/test.py stage6-load-release
python scripts/test.py stage6-web-vitals
```

The load mix includes ordinary reads, preference writes, browser-equivalent trial-balance reports,
and CSV exports. It requires error rate below 1%, p95 reads below 750 ms, writes below 1.5 seconds,
reports below 5 seconds, and exports below 10 seconds. It snapshots immutable ledger counts/totals
before and after and runs the application integrity endpoint. The Chrome lab gate requires LCP at
most 2.5 seconds, interaction latency at most 200 ms, and CLS at most 0.1 at 1440x900. Run both
gates twice consecutively for release evidence. Results are under `artifacts/performance`.

## Resilience and concurrency drill

The drill is intentionally disruptive to `ctec-stage6`. It verifies all of the following:

1. A job remains queued while the worker is stopped and succeeds after restart.
2. Three workers claim 12 unique integrity jobs exactly once using the durable queue.
3. The API accepts authenticated traffic after restart.
4. Requests fail during the isolated database outage and recover after restart.
5. Posted-entry/line/evidence counts and debit/credit totals remain exactly unchanged.

```powershell
python scripts/test.py stage6-resilience
```

The script restores the database and one-worker topology in `finally` and captures the last 500
API/worker/database log lines. Evidence is in `artifacts/resilience`. A failed recovery requires
manual confirmation that the isolated database is running before retrying; do not substitute the
demonstration Compose file or ports.

## Release evidence checklist

- Scanner inventory has no `missing` entries and `artifacts/security/summary.json` says passed.
- Authenticated ZAP, both image scans, dependency scans, SAST, and secret scan have reviewed output.
- Two consecutive full load and web-vital runs meet thresholds on the required dataset.
- Resilience summary says passed, logs show no duplicate claims, and ledger snapshots match.
- No credentials appear in artifacts; correlation IDs are retained for failed HTTP samples.
- Security and operations owners record approvals and dispositions outside generated evidence.
