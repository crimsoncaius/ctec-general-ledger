import * as React from "react";

/**
 * @startingPoint section="Controls" subtitle="Primary, secondary, ghost and danger actions" viewport="700x150"
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** primary = one per view. danger = irreversible or high-risk execution. */
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  /** Leading Lucide icon name. */
  icon?: string;
  /** Trailing Lucide icon name — chevrons, external links. */
  iconAfter?: string;
  /** In-flight state. Keeps the label, blocks re-submission, sets aria-busy. */
  busy?: boolean;
  fullWidth?: boolean;
}

export declare function Button(props: ButtonProps): React.JSX.Element;
