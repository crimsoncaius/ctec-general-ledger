import * as React from "react";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
  /** Monospace body — for pasted legacy GLREP matrix specifications and formulas. */
  mono?: boolean;
}

export declare function Textarea(props: TextareaProps): React.JSX.Element;
