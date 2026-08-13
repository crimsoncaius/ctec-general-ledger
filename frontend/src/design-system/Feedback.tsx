import {
  useEffect,
  useId,
  useRef,
  useState,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { Button } from "./Core";
import { StatusPill, type LedgerStatus } from "./Data";
import { Icon, type IconName } from "./Icon";

export interface BannerProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  tone?: "info" | "success" | "warning" | "danger";
  title?: ReactNode;
  actions?: ReactNode;
  correlationId?: string;
  onDismiss?: () => void;
  live?: "off" | "polite" | "assertive";
}
const BANNER_ICONS = {
  info: "info",
  success: "circle-check",
  warning: "alert-triangle",
  danger: "alert-octagon",
} as const;
export function Banner({
  tone = "info",
  title,
  actions,
  correlationId,
  onDismiss,
  live,
  children,
  className,
  ...rest
}: BannerProps) {
  return (
    <div
      role={live === "off" ? "note" : tone === "danger" ? "alert" : "status"}
      aria-live={live ?? (tone === "danger" ? "assertive" : "polite")}
      className={["ds-banner", `ds-banner--${tone}`, className]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      <Icon name={BANNER_ICONS[tone]} size={16} />
      <div className="ds-banner__content">
        {title ? <p className="ds-banner__title">{title}</p> : null}
        {children ? <div>{children}</div> : null}
        {correlationId ? (
          <p className="ds-banner__correlation">Reference {correlationId}</p>
        ) : null}
        {actions ? <div className="ds-banner__actions">{actions}</div> : null}
      </div>
      {onDismiss ? (
        <button
          type="button"
          className="ds-banner__dismiss"
          aria-label="Dismiss"
          onClick={onDismiss}
        >
          <Icon name="x" size={14} />
        </button>
      ) : null}
    </div>
  );
}

export interface DialogProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  open?: boolean;
  title: ReactNode;
  subject?: ReactNode;
  consequence?: ReactNode;
  tone?: "neutral" | "danger";
  confirmLabel?: string;
  confirmWord?: string;
  cancelLabel?: string;
  busy?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}
export function Dialog({
  open = true,
  title,
  subject,
  consequence,
  tone = "neutral",
  confirmLabel = "Confirm",
  confirmWord,
  cancelLabel = "Cancel",
  busy = false,
  onConfirm,
  onCancel,
  children,
  className,
  ...rest
}: DialogProps) {
  const [typed, setTyped] = useState("");
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const cancelRef = useRef(onCancel);
  useEffect(() => {
    cancelRef.current = onCancel;
  }, [onCancel]);
  useEffect(() => {
    if (!open) return;
    returnFocus.current = document.activeElement as HTMLElement | null;
    const dialog = dialogRef.current;
    const focusable = dialog?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
    );
    (focusable?.[0] ?? dialog)?.focus();
    function keydown(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) cancelRef.current?.();
      if (event.key !== "Tab" || !dialog) return;
      const available = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (!available.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = available[0];
      const last = available[available.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      returnFocus.current?.focus();
    };
  }, [busy, open]);
  if (!open) return null;
  const gated = Boolean(
    confirmWord && typed.trim().toUpperCase() !== confirmWord.toUpperCase(),
  );
  return (
    <div
      className="ds-dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onCancel?.();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={["ds-dialog", className].filter(Boolean).join(" ")}
        {...rest}
      >
        <header>
          {tone === "danger" ? <Icon name="alert-octagon" size={18} /> : null}
          <div>
            <h2 id={titleId}>{title}</h2>
            {subject ? <p>{subject}</p> : null}
          </div>
        </header>
        <div className="ds-dialog__body">
          {consequence ? <p>{consequence}</p> : null}
          {children}
          {confirmWord ? (
            <label>
              Type {confirmWord} to continue
              <input
                autoComplete="off"
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
              />
            </label>
          ) : null}
        </div>
        <footer>
          <Button variant="ghost" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "danger" : "primary"}
            disabled={gated}
            busy={busy}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </footer>
      </div>
    </div>
  );
}

export function ProgressBar({
  value = 0,
  status = "running",
  label,
  indeterminate = false,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  value?: number;
  status?: Extract<LedgerStatus, "queued" | "running" | "succeeded" | "failed">;
  label: string;
  indeterminate?: boolean;
}) {
  const percentage = Math.max(0, Math.min(100, value));
  return (
    <div
      className={["ds-progress", `ds-progress--${status}`, className]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      <div className="ds-progress__header">
        <span>{label}</span>
        <span>
          <StatusPill status={status} size="sm" />
          {!indeterminate ? <span data-numeric="">{percentage}%</span> : null}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={indeterminate ? undefined : percentage}
        className="ds-progress__track"
      >
        <span style={{ width: indeterminate ? "35%" : `${percentage}%` }} />
      </div>
    </div>
  );
}

export function EmptyState({
  icon = "inbox",
  title,
  description,
  action,
  kind = "no-data",
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  icon?: IconName;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  kind?: "no-data" | "no-match" | "no-access" | "no-action";
}) {
  return (
    <div
      className={["ds-empty", className].filter(Boolean).join(" ")}
      data-empty-kind={kind}
      {...rest}
    >
      <Icon name={icon} size={20} />
      <h2 className="ds-empty__title">{title}</h2>
      {description ? <p>{description}</p> : null}
      {action ? <div>{action}</div> : null}
    </div>
  );
}
