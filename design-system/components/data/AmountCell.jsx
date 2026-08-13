import React from "react";

export function AmountCell({ value, currency, side, zeroAs = "—", emphasis = false, style, ...rest }) {
  const isZero = value === 0 || value === "0" || value === null || value === undefined;
  const negative = typeof value === "number" ? value < 0 : String(value).trim().startsWith("-");
  const shown =
    isZero
      ? zeroAs
      : typeof value === "number"
      ? Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : String(value).replace("-", "");
  return (
    <span
      data-numeric=""
      data-side={side}
      style={{
        display: "inline-flex",
        justifyContent: "flex-end",
        gap: "var(--space-3)",
        width: "100%",
        font: "var(--type-amount)",
        fontVariantNumeric: "tabular-nums",
        fontWeight: emphasis ? "var(--weight-semibold)" : "var(--weight-regular)",
        color: isZero ? "var(--text-muted)" : "var(--text-body)",
        ...style,
      }}
      {...rest}
    >
      <span>
        {negative && !isZero ? "(" : ""}
        {shown}
        {negative && !isZero ? ")" : ""}
      </span>
      {currency && !isZero && (
        <span style={{ color: "var(--text-muted)", font: "var(--type-caption)", alignSelf: "center" }}>{currency}</span>
      )}
    </span>
  );
}
