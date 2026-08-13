# Legacy Migration Test Plan

## Application Overview

Legacy DBF archives are staged read-only, hashed, reconciled, and blocked from apply when either source integrity or target isolation rules fail.

## Test Scenarios

### 1. Legacy Migration

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-stage-reconcile-and-block-nonempty-apply

**File:** `e2e/migration/should-stage-reconcile-and-block-nonempty-apply.spec.ts`

**Steps:**
  1. Upload a balanced DBF snapshot and run a read-only trial.
    - expect: the ledger balances, account periods reconcile, and a repeatable digest is shown.
  2. Confirm apply against the seeded non-empty target company.
    - expect: apply is rejected to prevent ledger mixing and existing company data remains visible.

#### 1.2. should-report-unbalanced-migration-exceptions

**File:** `e2e/migration/should-report-unbalanced-migration-exceptions.spec.ts`

**Steps:**
  1. Upload an unbalanced DBF snapshot and run a read-only trial.
    - expect: blocking exceptions and a ledger difference are visible.
    - expect: apply confirmation is unavailable.
  2. Download the exception report.
    - expect: a governed migration exception CSV is downloaded.

