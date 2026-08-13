import * as React from "react";

/**
 * @startingPoint section="Forms" subtitle="Text, numeric, prefixed and invalid inputs" viewport="700x150"
 */
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  /** Right-aligned tabular monospace — use for every amount and rate. */
  numeric?: boolean;
  prefix?: React.ReactNode;
  /** Trailing adornment — currency code, "days", "%". */
  suffix?: React.ReactNode;
}

export declare function Input(props: InputProps): React.JSX.Element;
