# Custom Reports Test Plan

## Application Overview

The custom report designer versions structured definitions, evaluates decimal-safe formulas, exports audited results, and classifies legacy GLREP specifications.

## Test Scenarios

### 1. Custom Reports

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-design-version-export-and-convert-report

**File:** `e2e/custom-reports/should-design-version-export-and-convert-report.spec.ts`

**Steps:**
  1. Preview and save a uniquely named reusable report.
    - expect: fixed-decimal preview and version 1 confirmation appear.
  2. Run the saved report and export PDF and Excel.
    - expect: the audited browser result and both governed downloads are produced.
  3. Analyze and import a compatible legacy definition.
    - expect: compatible classification and imported status appear.

#### 1.2. should-reject-unsafe-formula-and-classify-manual-legacy

**File:** `e2e/custom-reports/should-reject-unsafe-formula-and-classify-manual-legacy.spec.ts`

**Steps:**
  1. Replace a formula with an unsafe function call and preview.
    - expect: the server rejects the formula and no preview matrix appears.
  2. Analyze a legacy definition with unsupported constructs.
    - expect: it is classified for manual conversion with warnings.

