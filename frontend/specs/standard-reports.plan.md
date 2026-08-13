# Standard Reports Test Plan

## Application Overview

Standard reports produce deterministic browser results, saved-run digests, reproducible history, and governed downloads.

## Test Scenarios

### 1. Standard Reports

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-run-reproduce-and-export-standard-report

**File:** `e2e/reports/should-run-reproduce-and-export-standard-report.spec.ts`

**Steps:**
  1. Run the chart of accounts in the browser.
    - expect: the report renders with a 64-character digest and account rows.
  2. Reproduce the newest saved run.
    - expect: the title and digest match the original run.
  3. Export the report as PDF, CSV, and Excel.
    - expect: each download has the corresponding governed filename extension.

