import * as React from "react";

export type LedgerStatus =
  | "draft" | "validated" | "approved" | "posted" | "reversed"
  | "open" | "closed"
  | "trial" | "applied"
  | "queued" | "running" | "succeeded" | "failed"
  | "reconciled" | "exception"
  | "compatible" | "partial" | "manual";

/**
 * @startingPoint section="Data" subtitle="The full ledger status vocabulary" viewport="700x150"
 */
export interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: LedgerStatus;
  /** Override the default wording only when the surrounding copy demands it. */
  label?: string;
  size?: "sm" | "md";
}

export declare function StatusPill(props: StatusPillProps): React.JSX.Element;
