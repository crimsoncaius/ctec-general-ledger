import * as React from "react";

export interface PageHeaderProps extends React.HTMLAttributes<HTMLElement> {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  /** Scope line: fiscal year, period, row counts, currency. */
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  /** Freshness of the data on this page. Required on every data workspace. */
  dataState?: "current" | "loading" | "refreshing" | "stale" | "failed";
  /** Company-local timestamp of the last successful load. */
  updatedAt?: string;
}

export declare function PageHeader(props: PageHeaderProps): React.JSX.Element;
