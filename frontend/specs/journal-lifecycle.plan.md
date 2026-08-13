# Journal Lifecycle Test Plan

## Application Overview

Journals remain editable drafts until validation, require maker-checker approval, become immutable on posting, and are corrected by linked reversal.

## Test Scenarios

### 1. Journal Lifecycle

**Seed:** `e2e/seed.spec.ts`

#### 1.1. should-manage-independent-draft-lifecycle

**File:** `e2e/journals/should-manage-independent-draft-lifecycle.spec.ts`

**Steps:**
  1. Create a uniquely described balanced draft.
    - expect: the draft is visible with draft status.
  2. Rename and copy the draft.
    - expect: the revised original and independently named copy are visible.
  3. Delete the copy.
    - expect: the copy disappears while the original remains.

#### 1.2. should-complete-maker-checker-cycle

**File:** `e2e/journals/should-complete-maker-checker-cycle.spec.ts`

**Steps:**
  1. As preparer, create and validate a uniquely described draft.
    - expect: the batch reaches validated status and has no approval or posting action.
  2. As approver, approve and post the batch.
    - expect: the batch reaches posted status and draft editing controls are absent.
  3. Find the posted entry in inquiry and post a linked reversal.
    - expect: an immutable reversing entry containing the reason is visible.

#### 1.3. should-reject-identical-journal-accounts

**File:** `e2e/journals/should-reject-identical-journal-accounts.spec.ts`

**Steps:**
  1. Choose the same account for debit and credit and submit the composer.
    - expect: a user-visible validation error requests two different accounts.
    - expect: no batch with the attempted description is created.

