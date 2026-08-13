import * as React from "react";

export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open?: boolean;
  title: React.ReactNode;
  /** Names the affected object exactly — batch number, account code, company. */
  subject?: React.ReactNode;
  /** States what will happen in accounting terms, not "are you sure?". */
  consequence?: React.ReactNode;
  tone?: "neutral" | "danger";
  confirmLabel?: string;
  /** Typed-confirmation gate, e.g. "APPLY" for legacy migration. */
  confirmWord?: string;
  cancelLabel?: string;
  busy?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}

export declare function Dialog(props: DialogProps): React.JSX.Element;
