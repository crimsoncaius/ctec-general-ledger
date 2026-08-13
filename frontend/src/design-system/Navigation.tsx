import { useId, useState, type HTMLAttributes, type ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export interface Membership {
  company: string;
  code: string;
  role: string;
  id?: string;
}
export interface CompanySwitcherProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "onSelect"> {
  company: string;
  code: string;
  role?: string;
  memberships?: Membership[];
  onSelect?: (membership: Membership) => void;
  inverse?: boolean;
}
export function CompanySwitcher({
  company,
  code,
  role,
  memberships = [],
  onSelect,
  inverse = true,
  className,
  ...rest
}: CompanySwitcherProps) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  return (
    <div
      className={[
        "ds-company-switcher",
        inverse ? "ds-company-switcher--inverse" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      <select
        className="ds-visually-hidden"
        aria-label="Company"
        value={memberships.find((item) => item.code === code)?.id ?? code}
        onChange={(event) => {
          const membership = memberships.find(
            (item) => (item.id ?? item.code) === event.target.value,
          );
          if (membership) onSelect?.(membership);
        }}
      >
        {memberships.map((membership) => (
          <option
            key={membership.id ?? membership.code}
            value={membership.id ?? membership.code}
          >
            {membership.code} · {membership.company}
          </option>
        ))}
      </select>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="ds-company-switcher__mark" aria-hidden="true">
          {code.slice(0, 2)}
        </span>
        <span>
          <strong>{company}</strong>
          <small>
            {code}
            {role ? ` · ${role}` : ""}
          </small>
        </span>
        <Icon name="chevrons-up-down" size={13} />
      </button>
      {open ? (
        <div
          role="listbox"
          id={listId}
          aria-label="Active company"
          className="ds-company-switcher__menu"
        >
          <p>Switching company reloads all company data</p>
          {memberships.map((membership) => {
            const active = membership.code === code;
            return (
              <button
                key={membership.id ?? membership.code}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => {
                  setOpen(false);
                  onSelect?.(membership);
                }}
              >
                <span>
                  <strong>{membership.company}</strong>
                  <small>
                    {membership.code} · {membership.role}
                  </small>
                </span>
                {active ? <Icon name="check" size={14} /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export interface NavItem {
  id: string;
  label: string;
  icon: IconName;
  badge?: number | string;
  readOnly?: boolean;
}
export interface NavGroup {
  label: string;
  items: NavItem[];
}
export interface SidebarNavProps extends HTMLAttributes<HTMLElement> {
  groups: NavGroup[];
  activeId?: string;
  onNavigate?: (id: string) => void;
  footer?: ReactNode;
}
export function SidebarNav({
  groups,
  activeId,
  onNavigate,
  footer,
  className,
  ...rest
}: SidebarNavProps) {
  return (
    <nav
      aria-label="Primary"
      className={["ds-sidebar", className].filter(Boolean).join(" ")}
      {...rest}
    >
      <div>
        {groups.map((group) => (
          <section key={group.label}>
            <p>{group.label}</p>
            {group.items.map((item) => {
              const active = item.id === activeId;
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-current={active ? "page" : undefined}
                  onClick={() => onNavigate?.(item.id)}
                >
                  <Icon name={item.icon} size={15} />
                  <span>{item.label}</span>
                  {item.badge != null ? (
                    <small aria-hidden="true" data-numeric="">
                      {item.badge}
                    </small>
                  ) : null}
                  {item.readOnly ? <Icon name="eye" size={12} /> : null}
                </button>
              );
            })}
          </section>
        ))}
      </div>
      {footer ? <footer>{footer}</footer> : null}
    </nav>
  );
}

export type DataState =
  | "current"
  | "loading"
  | "refreshing"
  | "stale"
  | "failed";
const DATA_STATES = {
  current: ["circle-check", "Current"],
  loading: ["refresh-cw", "Loading"],
  refreshing: ["refresh-cw", "Refreshing"],
  stale: ["clock", "Stale"],
  failed: ["alert-triangle", "Load failed"],
} as const;
export interface PageHeaderProps
  extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  eyebrow?: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  dataState?: DataState;
  updatedAt?: string;
}
export function PageHeader({
  eyebrow,
  title,
  meta,
  actions,
  dataState = "current",
  updatedAt,
  className,
  ...rest
}: PageHeaderProps) {
  const [icon, stateLabel] = DATA_STATES[dataState];
  return (
    <header
      className={["ds-page-header", className].filter(Boolean).join(" ")}
      {...rest}
    >
      <div>
        {eyebrow ? <p className="ds-page-header__eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        <div className="ds-page-header__meta">
          {meta}
          <span
            aria-live="polite"
            className={`ds-data-state ds-data-state--${dataState}`}
          >
            <Icon name={icon} size={12} />
            {stateLabel}
            {updatedAt ? ` · ${updatedAt}` : ""}
          </span>
        </div>
      </div>
      {actions ? (
        <div className="ds-page-header__actions">{actions}</div>
      ) : null}
    </header>
  );
}

export interface TabItem {
  id: string;
  label: string;
  icon?: IconName;
  count?: number | string;
}
export function Tabs({
  tabs,
  activeId,
  onChange,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  tabs: TabItem[];
  activeId: string;
  onChange?: (id: string) => void;
}) {
  function moveFocus(current: number, delta: number) {
    const next = (current + delta + tabs.length) % tabs.length;
    onChange?.(tabs[next].id);
  }
  return (
    <div
      role="tablist"
      aria-label="Sections"
      className={["ds-tabs", className].filter(Boolean).join(" ")}
      {...rest}
    >
      {tabs.map((tab, index) => {
        const active = tab.id === activeId;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange?.(tab.id)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight") moveFocus(index, 1);
              if (event.key === "ArrowLeft") moveFocus(index, -1);
            }}
          >
            {tab.icon ? <Icon name={tab.icon} size={14} /> : null}
            {tab.label}
            {tab.count != null ? (
              <span data-numeric="">{tab.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
