import * as React from "react";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: string;
  /** Required — becomes both aria-label and tooltip. */
  label: string;
  size?: "sm" | "md";
  selected?: boolean;
}

export declare function IconButton(props: IconButtonProps): React.JSX.Element;
