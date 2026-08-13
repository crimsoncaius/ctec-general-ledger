import * as React from "react";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  /** A valid next step, when one exists for this user's capabilities. */
  action?: React.ReactNode;
  /** Which emptiness this is — the copy must say which. */
  kind?: "no-data" | "no-match" | "no-access" | "no-action";
}

export declare function EmptyState(props: EmptyStateProps): React.JSX.Element;
