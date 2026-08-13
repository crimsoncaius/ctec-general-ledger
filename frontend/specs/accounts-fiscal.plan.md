# Accounts and Fiscal Calendar Test Plan

## Application Overview

Company-scoped account maintenance and configurable fiscal calendars define valid journal dimensions.

## Test Scenarios

### 1. Accounts and Fiscal Calendars

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-maintain-account-and-calendar

**File:** `e2e/accounts-fiscal/should-maintain-account-and-calendar.spec.ts`

**Steps:**
  1. Create and rename a uniquely coded balance-sheet account.
    - expect: creation and immutable-history update confirmations appear.
  2. Generate a uniquely labelled 13-period fiscal year.
    - expect: period 13 is generated and the validated calendar is saved.

#### 1.2. should-enforce-account-and-calendar-boundaries

**File:** `e2e/accounts-fiscal/should-enforce-account-and-calendar-boundaries.spec.ts`

**Steps:**
  1. Inspect the seeded title and retained-earnings accounts.
    - expect: a title account cannot be made postable and retained earnings cannot be deactivated.
  2. Enter 19 fiscal periods.
    - expect: boundary generation is disabled.
  3. Enter 18 fiscal periods and generate boundaries.
    - expect: period 18 is generated and period 19 is absent.

