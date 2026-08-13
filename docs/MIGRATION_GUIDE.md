# Legacy DBF migration guide

## Safety boundary

Never point the legacy application and the migration workflow at the same writable directory.
The modern application accepts only a ZIP copy. It does not write DBFs, rebuild NTX indexes,
pack soft-deleted records, or mutate the legacy system.

Before a trial or cutover:

1. Back up and verify the legacy company directory using the existing operational procedure.
2. Stop legacy posting for the snapshot window and ensure no user has the company open.
3. Copy the company data to a separate read-only staging location.
4. ZIP the DBF files at the archive root, without subdirectories. Include at least
   `GLACCNT.DAT` and `GLMAIN.DAT`; also include `GLACCNX.DAT`, `GLGP.DAT`, `GLTRANS.DAT`,
   `GLREP.DAT`, and matching `.DBT`/`.FPT` memo files when present.
5. Keep the source snapshot and its external backup checksum until cutover sign-off.

## Trial migration

Create an empty target company, configure its base currency, and configure the fiscal year and
1–18 periods represented by the current legacy account arrays. Grant `migration.run` only to
the cutover operator.

In **Administration → Legacy migration**, select the ZIP and choose **Run read-only trial**.
The result records per-file hashes, a canonical source digest, row counts, exceptions, and these
reconciliations:

- global opening balance net is zero;
- posted ledger debits equal credits;
- every account's `BAL_n` equals posted detail for period `n`; and
- every `CURR_BAL` equals `OPEN_BAL + sum(BAL_n)`.

Download the CSV exception report, correct issues in a safe copy or in the governed legacy
system, take a new snapshot, and repeat. Do not modify staged payloads in PostgreSQL.

## Apply and verification

Apply is available only for a successful, fully reconciled trial. Type `APPLY` and submit the
displayed source digest. The target company must contain no accounts or journals. The operation
is atomic: a closed period, invalid record, database failure, or accounting failure leaves no
target accounts, budgets, journals, balances, or applied-run record.

After apply:

1. Run integrity checks and trial balances for every period.
2. Compare the modern trial balance, GL listing, account-period totals, budget totals, draft
   groups, and custom-report disposition with the signed legacy control reports.
3. Resolve all `partial` report conversions and manually reconstruct `manual` reports.
4. Have accounting and operations independently sign the reconciliation evidence.
5. Run a parallel accounting period before approving final cutover.

The final production snapshot and parallel sign-off require external legacy data and authorized
operators; the application supplies the repeatable tooling and evidence but does not bypass that
control.
