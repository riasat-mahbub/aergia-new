/** @vitest-environment jsdom */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TemplateWizard from "../TemplateWizard";

vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

vi.mock("lucide-react", () => {
  const stub = (props: any) => <svg data-testid="icon" {...props} />;
  return {
    ArrowLeft: stub,
    ArrowRight: stub,
    Check: stub,
    Loader2: stub,
    X: stub,
  };
});

vi.mock("../TemplateLayoutView", () => ({
  default: () => <div data-testid="layout-view" />,
}));

vi.mock("../../customization/StyleEditor", () => ({
  default: () => <div data-testid="style-editor" />,
}));

describe("TemplateWizard step copy", () => {
  it("layout step says Arrange zones, never rows", () => {
    render(<TemplateWizard />);
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getAllByText("Layout").length).toBeGreaterThan(0);
    expect(screen.getByText("Arrange zones")).toBeDefined();
    expect(screen.queryByText(/rows/i)).toBeNull();
  });
});
