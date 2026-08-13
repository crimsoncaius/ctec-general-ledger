import * as React from "react";

/**
 * @startingPoint section="Feedback" subtitle="Info, success, guardrail and failure messages" viewport="700x260"
 */
export interface BannerProps extends React.HTMLAttributes<HTMLDivElement> {
  tone?: "info" | "success" | "warning" | "danger";
  title?: React.ReactNode;
  /** Buttons for recovery paths: retry, view failed rows, reload newer version. */
  actions?: React.ReactNode;
  /** API-supplied correlation reference for unexpected failures. */
  correlationId?: string;
  onDismiss?: () => void;
  /** Override the announcement politeness. Danger defaults to assertive. */
  live?: "off" | "polite" | "assertive";
}

export declare function Banner(props: BannerProps): React.JSX.Element;
