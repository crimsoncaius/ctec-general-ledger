# Budgets and Fiscal Close Test Plan

## Application Overview

Planning stores versioned budgets and requires a reconciled preview before an append-only fiscal close.

## Test Scenarios

### 1. Budgets and Close

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-version-budget-and-close-northstar

**File:** `e2e/planning/should-version-budget-and-close-northstar.spec.ts`

**Steps:**
  1. Switch to Northstar, save a uniquely named budget, then revise its amount.
    - expect: the latest budget amount is visible and both saves are confirmed as audited versions.
  2. Preview the open fiscal year close into the next opening period.
    - expect: the preview reconciles and execution becomes available.
  3. Execute the close.
    - expect: immutable close confirmation appears and the closed year is marked closed.
