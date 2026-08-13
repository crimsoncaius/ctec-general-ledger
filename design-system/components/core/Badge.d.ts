import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "accent" | "success" | "warning" | "danger";
  /** Monospace for identifiers: batch numbers, entry numbers, company codes. */
  mono?: boolean;
}

export declare function Badge(props: BadgeProps): React.JSX.Element;
