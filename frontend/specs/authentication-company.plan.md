# Authentication and Company Context Test Plan

## Application Overview

Authentication establishes a short-lived in-memory session and company membership determines every visible workspace and mutation.

## Test Scenarios

### 1. Authentication and Company Context

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-lock-new-user-after-five-failures

**File:** `e2e/auth-company/should-lock-new-user-after-five-failures.spec.ts`

**Steps:**
  1. Sign in as an administrator and create a uniquely named company user.
    - expect: the membership is recorded in the audit trail.
  2. Sign out and submit the new email with an incorrect password five times.
    - expect: every failed submission shows the generic invalid-credentials error.
  3. Submit the correct password.
    - expect: the account is reported as temporarily locked and no workspace opens.

#### 1.2. should-isolate-company-workspaces

**File:** `e2e/auth-company/should-isolate-company-workspaces.spec.ts`

**Steps:**
  1. Create a uniquely described draft in ACME.
    - expect: the draft is visible in ACME.
  2. Switch to Northstar.
    - expect: the Northstar heading appears and the ACME draft is absent.
  3. Switch back to ACME.
    - expect: the ACME draft is visible again.

#### 1.3. should-enforce-restricted-navigation

**File:** `e2e/auth-company/should-enforce-restricted-navigation.spec.ts`

**Steps:**
  1. Sign in as the restricted viewer.
    - expect: read-only account, journal, inquiry, and fiscal navigation is available.
    - expect: planning, reports, designer, and administration are unavailable.
  2. Open accounts, journals, and inquiry.
    - expect: account mutation controls, journal composer, workflow actions, and reversal controls are absent.

