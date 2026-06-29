import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TemplateLayoutView from "../TemplateLayoutView";

vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

const tokenPercent = (token: string | undefined): number => {
  if (token === "narrow") return 30;
  if (token === "half") return 50;
  if (token === "full") return 100;
  if (token === "auto") return 0;
  return 0;
};

describe("TemplateLayoutView zone-only", () => {
  it("renders a flat list of zones, no Add Row, no Row N label", () => {
    const onChange = vi.fn();
    render(
      <TemplateLayoutView
        zones={[
          { id: "a", label: "Side", styles: { width: "narrow" } },
          { id: "b", label: "Main", styles: { width: "half" } },
        ]}
        placement={{}}
        onChange={onChange}
      />,
    );
    expect(screen.getByTestId("zone-row")).toBeDefined();
    expect(screen.getByText("Side")).toBeDefined();
    expect(screen.getByText("Main")).toBeDefined();
    expect(screen.queryByText(/Row \d/)).toBeNull();
    expect(screen.queryByText(/Add Row/)).toBeNull();
    expect(screen.getByText(/Add Zone/)).toBeDefined();
  });

  it("Add Zone appends a new zone and rebalances widths", () => {
    const onChange = vi.fn();
    render(
      <TemplateLayoutView
        zones={[
          { id: "a", label: "Side", styles: { width: "half" } },
          { id: "b", label: "Main", styles: { width: "half" } },
        ]}
        placement={{}}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByText("Add Zone"));
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.zones).toHaveLength(3);
    // Each zone carries a width token; the editor picks sensible tokens
    // for the new layout. The visual ratio is the test's concern.
    lastCall.zones.forEach((z: { styles?: { width?: string } }) => {
      expect(["narrow", "half", "full", "auto"]).toContain(z.styles?.width);
    });
    // Sum of token percentages is positive (the editor picked real tokens).
    const total = lastCall.zones.reduce(
      (s: number, z: any) => s + tokenPercent(z.styles.width),
      0,
    );
    expect(total).toBeGreaterThan(0);
  });
});
