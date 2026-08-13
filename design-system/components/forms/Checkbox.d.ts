import * as React from "react";

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: React.ReactNode;
  description?: React.ReactNode;
  /** Header state when only some rows in a bulk selection are marked. */
  indeterminate?: boolean;
}

export declare function Checkbox(props: CheckboxProps): React.JSX.Element;
