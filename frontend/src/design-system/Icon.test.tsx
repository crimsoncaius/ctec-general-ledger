import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Icon } from "./Icon";

describe("Icon", () => {
  it("exposes a supplied accessible name", () => {
    render(<Icon name="circle-check" label="Reconciled" />);

    const icon = screen.getByRole("img", { name: "Reconciled" });
    expect(icon).not.toHaveAttribute("aria-hidden");
    expect(icon.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("hides an unlabeled decorative icon from assistive technology", () => {
    const { container } = render(<Icon name="refresh-cw" size={14} />);

    const icon = container.querySelector(".ds-icon");
    expect(icon).toHaveAttribute("aria-hidden", "true");
    expect(icon).not.toHaveAttribute("role");
    expect(icon).toHaveStyle({ width: "14px", height: "14px" });
  });
});
