import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  icon?: IconName;
  iconAfter?: IconName;
  busy?: boolean;
  fullWidth?: boolean;
}

export function Button({ variant = "secondary", size = "md", icon, iconAfter, busy = false, fullWidth = false, disabled, children, className, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={["ds-button", `ds-button--${variant}`, `ds-button--${size}`, fullWidth ? "ds-button--full" : "", className].filter(Boolean).join(" ")}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <Icon name="refresh-cw" size={14} className="ds-icon--spin" /> : icon ? <Icon name={icon} size={14} /> : null}
      <span>{children}</span>
      {iconAfter ? <Icon name={iconAfter} size={14} /> : null}
    </button>
  );
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: IconName;
  label: string;
  size?: "sm" | "md";
  selected?: boolean;
}

export function IconButton({ icon, label, size = "md", selected = false, className, ...rest }: IconButtonProps) {
  return (
    <button
      type="button"
      className={["ds-icon-button", `ds-icon-button--${size}`, selected ? "is-selected" : "", className].filter(Boolean).join(" ")}
      aria-label={label}
      title={label}
      aria-pressed={selected || undefined}
      {...rest}
    >
      <Icon name={icon} size={size === "sm" ? 14 : 16} />
    </button>
  );
}

export interface CardProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
  padded?: boolean;
}

export function Card({ title, description, actions, footer, padded = true, children, className, ...rest }: CardProps) {
  return (
    <section className={["ds-card", padded ? "" : "ds-card--flush", className].filter(Boolean).join(" ")} {...rest}>
      {title || description || actions ? (
        <header className="ds-card__header">
          <div>{title ? <h2 className="ds-card__title">{title}</h2> : null}{description ? <p className="ds-card__description">{description}</p> : null}</div>
          {actions ? <div className="ds-card__actions">{actions}</div> : null}
        </header>
      ) : null}
      <div className="ds-card__body">{children}</div>
      {footer ? <footer className="ds-card__footer">{footer}</footer> : null}
    </section>
  );
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "accent" | "success" | "warning" | "danger";
  mono?: boolean;
}

export function Badge({ tone = "neutral", mono = false, className, children, ...rest }: BadgeProps) {
  return <span className={["ds-badge", `ds-badge--${tone}`, mono ? "ds-badge--mono" : "", className].filter(Boolean).join(" ")} {...rest}>{children}</span>;
}
