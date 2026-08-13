import * as React from "react";

export interface SelectOption {
  value: string;
  label: string;
  /** Use for closed periods and inactive accounts — present but unselectable. */
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options?: Array<SelectOption | string>;
  placeholder?: string;
  invalid?: boolean;
}

export declare function Select(props: SelectProps): React.JSX.Element;
