import React from "react";

const TONES = {
  neutral: ["var(--n-100)", "var(--text-secondary)", "var(--border-strong)"],
  accent: ["var(--blue-50)", "var(--blue-700)", "var(--blue-200)"],
  success: ["var(--green-50)", "var(--green-700)", "var(--green-200)"],
  warning: ["var(--amber-50)", "var(--amber-700)", "var(--amber-200)"],
  danger: ["var(--red-50)", "var(--red-700)", "var(--red-200)"],
};

export function Badge({ tone = "neutral", mono = false, children, style, ...rest }) {
  const [bg, fg, bd] = TONES[tone] || TONES.neutral;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-2)",
        padding: "1px var(--space-3)",
        background: bg,
        color: fg,
        border: `1px solid ${bd}`,
        borderRadius: "var(--radius-xs)",
        font: mono ? "var(--type-mono)" : "var(--type-caption)",
        fontWeight: "var(--weight-medium)",
        whiteSpace: "nowrap",
        ...style,
      }}
      {...rest}
    >
      {children}
    </span>
  );
}
