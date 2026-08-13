import React from "react";

/** Lucide glyph rendered as a CSS mask so it inherits currentColor. */
export function Icon({ name, size = 16, label, style, ...rest }) {
  const url = `https://unpkg.com/lucide-static@0.454.0/icons/${name}.svg`;
  return (
    <span
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      style={{
        display: "inline-block",
        width: size,
        height: size,
        flex: "0 0 auto",
        backgroundColor: "currentColor",
        WebkitMaskImage: `url(${url})`,
        maskImage: `url(${url})`,
        WebkitMaskRepeat: "no-repeat",
        maskRepeat: "no-repeat",
        WebkitMaskPosition: "center",
        maskPosition: "center",
        WebkitMaskSize: "contain",
        maskSize: "contain",
        ...style,
      }}
      {...rest}
    />
  );
}
