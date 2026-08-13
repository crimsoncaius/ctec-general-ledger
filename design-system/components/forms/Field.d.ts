import * as React from "react";

export interface FieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label: React.ReactNode;
  /** Id given to the wrapped control; also derives hint/error ids. Required. */
  htmlFor: string;
  hint?: React.ReactNode;
  /** Present error text; also flips the wrapped control to its invalid style. */
  error?: React.ReactNode;
  required?: boolean;
  /** Marks accounting-immutable inputs: account code, type, currency, base currency. */
  immutable?: boolean;
}

export declare function Field(props: FieldProps): React.JSX.Element;
