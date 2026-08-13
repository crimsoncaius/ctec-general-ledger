# Administration, Imports, and Jobs Test Plan

## Application Overview

Administration governs atomic imports, users, roles, preferences, durable jobs, and audit evidence.

## Test Scenarios

### 1. Administration, Imports, and Jobs

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-preview-import-and-run-integrity-job

**File:** `e2e/administration/should-preview-import-and-run-integrity-job.spec.ts`

**Steps:**
  1. Preview an invalid account CSV.
    - expect: validation exceptions appear and apply remains disabled.
  2. Preview and apply a uniquely coded valid account CSV.
    - expect: one account is created atomically.
  3. Run the integrity background operation.
    - expect: the operation succeeds and its audit history is visible.

#### 1.2. should-manage-role-user-and-preferences

**File:** `e2e/administration/should-manage-role-user-and-preferences.spec.ts`

**Steps:**
  1. Create a uniquely named least-privilege reporting role and user.
    - expect: role and membership confirmations appear and the user row is visible.
  2. Change display density and save a ledger view.
    - expect: both company-scoped preference confirmations appear.

