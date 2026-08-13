# Security guide

## Controls implemented

- Argon2 password hashing, generic login failures, persistent failed-attempt counters, and a
  timed lock after five failed attempts.
- Short-lived signed bearer tokens. The browser keeps the token in memory; sign-out or refresh
  removes it.
- Active company membership plus company-owned role capabilities on every protected route.
- Company predicates and composite tenant foreign keys throughout the data model.
- Maker-checker approval by default; self-approval requires an explicit capability.
- Fixed-decimal validation, atomic posting, immutable posted rows, reversals, append-only closes,
  and audited administrative/configuration changes.
- Safe formula AST evaluation, non-executing legacy report parsing, bounded ZIP extraction, and
  read-only DBF snapshots.
- Correlation IDs and defensive browser headers (`nosniff`, frame deny, no-referrer).
- Production startup rejects the bundled JWT secret and wildcard CORS.

## Deployment requirements

Set `ENVIRONMENT=production`, generate an independent high-entropy `JWT_SECRET`, rotate default
database credentials, and inject secrets without committing `.env`. Terminate TLS at an approved
proxy, redirect HTTP to HTTPS, restrict origins exactly, and allow PostgreSQL only from the API
network and authorized operators. Run containers as non-root (the API image does), keep base
images/dependencies patched, scan images, and use encrypted storage/backups.

Do not share demo accounts or passwords outside local evaluation. Create named users, assign the
least-privilege role, disable memberships promptly, and review role capabilities and audit events
regularly. Separate application, migration, backup, and database-administration duties where
staffing permits.

## Threat boundaries and residual risk

The shared-schema tenant model assumes no untrusted direct database access; PostgreSQL RLS is not
enabled. Infrastructure administrators can access all companies and must be governed separately.
Bearer-token theft grants access until expiry, so TLS, endpoint security, and short token lifetime
matter. The application does not supply an external WAF, SIEM, malware scanner, key-management
service, or continuous database recovery; those require authorized infrastructure choices.

Uploaded CSV/ZIP size and structure are bounded and parsed as data, but production should also
enforce proxy request limits and malware policy. PDF/Excel exports may contain sensitive ledger
data and inherit the requesting user's responsibility after download.

## Security operations

Review authentication lockouts, permission changes, membership changes, migration attempts,
failed background operations, and integrity exceptions. Preserve audit/database/log evidence on
an incident. Never repair posted data using SQL; use a linked reversal or an approved recovery.
Report vulnerabilities privately to the system owner with reproduction steps and correlation IDs,
without testing against real financial data.
