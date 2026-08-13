import {
  Children,
  cloneElement,
  isValidElement,
  useEffect,
  useRef,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactElement,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { Icon } from "./Icon";

type InvalidControl = ReactElement<{
  id?: string;
  invalid?: boolean;
  "aria-describedby"?: string;
  "aria-label"?: string;
}>;

export interface FieldProps extends HTMLAttributes<HTMLDivElement> {
  label: ReactNode;
  htmlFor: string;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  immutable?: boolean;
}

export function Field({
  label,
  htmlFor,
  hint,
  error,
  required = false,
  immutable = false,
  children,
  className,
  ...rest
}: FieldProps) {
  const describedBy =
    [hint ? `${htmlFor}-hint` : "", error ? `${htmlFor}-error` : ""]
      .filter(Boolean)
      .join(" ") || undefined;
  return (
    <div
      className={["ds-field", className].filter(Boolean).join(" ")}
      {...rest}
    >
      <label htmlFor={htmlFor} className="ds-field__label">
        {label}
        {required ? (
          <span className="ds-field__qualifier" aria-hidden="true">
            required
          </span>
        ) : null}
        {immutable ? (
          <span className="ds-field__qualifier" aria-hidden="true">
            <Icon name="lock" size={11} /> fixed after creation
          </span>
        ) : null}
      </label>
      {Children.map(children, (child) => {
        if (!isValidElement(child)) return child;
        const control = child as InvalidControl;
        return cloneElement(control, {
          id: control.props.id || htmlFor,
          invalid: control.props.invalid ?? Boolean(error),
          "aria-describedby": describedBy,
          "aria-label": control.props["aria-label"] ?? (typeof label === "string" ? label : undefined),
        });
      })}
      {hint && !error ? (
        <p id={`${htmlFor}-hint`} className="ds-field__hint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${htmlFor}-error`} className="ds-field__error">
          <Icon name="alert-circle" size={12} />
          {error}
        </p>
      ) : null}
    </div>
  );
}

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "prefix"> {
  invalid?: boolean;
  numeric?: boolean;
  prefix?: ReactNode;
  suffix?: ReactNode;
}

export function Input({
  invalid = false,
  numeric = false,
  prefix,
  suffix,
  className,
  ...rest
}: InputProps) {
  return (
    <span
      className={[
        "ds-input",
        invalid ? "is-invalid" : "",
        rest.disabled ? "is-disabled" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {prefix ? <span className="ds-control-adornment">{prefix}</span> : null}
      <input
        className={
          numeric
            ? "ds-input__control ds-input__control--numeric"
            : "ds-input__control"
        }
        aria-invalid={invalid || undefined}
        {...rest}
      />
      {suffix ? <span className="ds-control-adornment">{suffix}</span> : null}
    </span>
  );
}

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}
export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options?: Array<SelectOption | string>;
  placeholder?: string;
  invalid?: boolean;
}

export function Select({
  options = [],
  placeholder,
  invalid = false,
  className,
  children,
  ...rest
}: SelectProps) {
  return (
    <span
      className={[
        "ds-select",
        invalid ? "is-invalid" : "",
        rest.disabled ? "is-disabled" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <select
        className="ds-select__control"
        aria-invalid={invalid || undefined}
        {...rest}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {children ??
          options.map((option) => {
            const item =
              typeof option === "string"
                ? { value: option, label: option }
                : option;
            return (
              <option
                key={item.value}
                value={item.value}
                disabled={item.disabled}
              >
                {item.label}
              </option>
            );
          })}
      </select>
      <Icon name="chevron-down" size={14} className="ds-select__icon" />
    </span>
  );
}

export interface TextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
  mono?: boolean;
}
export function Textarea({
  invalid = false,
  mono = false,
  className,
  ...rest
}: TextareaProps) {
  return (
    <textarea
      className={[
        "ds-textarea",
        invalid ? "is-invalid" : "",
        mono ? "ds-textarea--mono" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      aria-invalid={invalid || undefined}
      {...rest}
    />
  );
}

export interface CheckboxProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: ReactNode;
  description?: ReactNode;
  indeterminate?: boolean;
}
export function Checkbox({
  label,
  description,
  indeterminate = false,
  className,
  ...rest
}: CheckboxProps) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <label className={["ds-checkbox", className].filter(Boolean).join(" ")}>
      <input ref={ref} type="checkbox" {...rest} />
      <span className="ds-checkbox__box" aria-hidden="true">
        {indeterminate ? (
          <Icon name="minus" size={11} />
        ) : rest.checked ? (
          <Icon name="check" size={11} />
        ) : null}
      </span>
      {label || description ? (
        <span>
          <span className="ds-checkbox__label">{label}</span>
          {description ? (
            <span className="ds-checkbox__description">{description}</span>
          ) : null}
        </span>
      ) : null}
    </label>
  );
}

export interface SwitchProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: ReactNode;
}
export function Switch({ label, className, ...rest }: SwitchProps) {
  return (
    <label className={["ds-switch", className].filter(Boolean).join(" ")}>
      <input type="checkbox" {...rest} />
      <span className="ds-switch__track" aria-hidden="true">
        <span />
      </span>
      {label ? <span>{label}</span> : null}
    </label>
  );
}
