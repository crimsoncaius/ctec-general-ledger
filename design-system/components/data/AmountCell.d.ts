import * as React from "react";

export interface AmountCellProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Pass a pre-formatted fixed-decimal string when the server already formatted it. */
  value: number | string | null;
  /** ISO code, shown whenever currency could be ambiguous. */
  currency?: string;
  /** Recorded for column semantics; it does not change the presentation. */
  side?: "debit" | "credit";
  /** What an empty side renders as. Default "—". */
  zeroAs?: string;
  /** Totals and subtotals. */
  emphasis?: boolean;
}

export declare function AmountCell(props: AmountCellProps): React.JSX.Element;
