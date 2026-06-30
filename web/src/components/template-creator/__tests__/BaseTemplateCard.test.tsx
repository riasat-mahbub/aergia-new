/** @vitest-environment jsdom */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import BaseTemplateCard from "../BaseTemplateCard";
import type { UserTemplate } from "../../../lib/api/templates";

vi.mock("motion/react", () => ({
  motion: { button: ({ children, ...props }: any) => <button {...props}>{children}</button> },
}));

function makeTemplate(manifest: Record<string, any>): UserTemplate {
  return {
    id: "t1",
    name: "Modern",
    description: "desc",
    preview_image_url: null,
    layout_config: {},
    section_schema: {},
    default_customizations: null,
    content: "",
    layout_template: null,
    manifest,
    is_user_template: false,
    is_system: true,
    user_id: null,
    created_at: "2026-01-01",
  };
}

describe("BaseTemplateCard zone strip", () => {
  it("renders a flat strip of zone rectangles sized by styles.width", () => {
    const template = makeTemplate({
      zones: [
        { id: "a", styles: { width: "40%" } },
        { id: "b", styles: { width: "60%" } },
      ],
    });
    const { container } = render(<BaseTemplateCard template={template} onSelect={() => {}} />);
    const rects = container.querySelectorAll("div.h-full.rounded");
    expect(rects).toHaveLength(2);
  });

  it("defaults missing widths to equal share", () => {
    const template = makeTemplate({
      zones: [{ id: "a", styles: {} }, { id: "b", styles: {} }],
    });
    const { container } = render(<BaseTemplateCard template={template} onSelect={() => {}} />);
    const rects = container.querySelectorAll("div.h-full.rounded");
    expect(rects).toHaveLength(2);
    rects.forEach((rect) => {
      expect((rect as HTMLElement).style.width).toBe("50%");
    });
  });

  it("renders a flat strip even when zones carry legacy row data", () => {
    const template = makeTemplate({
      zones: [
        { id: "a", row: 0, styles: { width: "narrow" } },
        { id: "b", row: 1, styles: { width: "half" } },
      ],
    });
    const { container } = render(<BaseTemplateCard template={template} onSelect={() => {}} />);
    const rects = container.querySelectorAll("div.h-full.rounded");
    expect(rects).toHaveLength(2);
    expect((rects[0] as HTMLElement).style.width).toBe("30%");
    expect((rects[1] as HTMLElement).style.width).toBe("50%");
  });
});
