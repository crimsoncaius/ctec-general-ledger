import * as React from "react";
import type { LedgerStatus } from "../data/StatusPill";

export interface ProgressBarProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Persisted percentage from the job record, 0-100. */
  value?: number;
  status?: Extract<LedgerStatus, "queued" | "running" | "succeeded" | "failed">;
  /** Required — becomes the progressbar's accessible name. */
  label: string;
  /** Use only when the server reports no percentage. */
  indeterminate?: boolean;
}

export declare function ProgressBar(props: ProgressBarProps): React.JSX.Element;
