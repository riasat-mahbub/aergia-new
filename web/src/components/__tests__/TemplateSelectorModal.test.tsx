import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TemplateSelectorModal from "../customization/TemplateSelectorModal";

vi.mock("../../lib/api/templates", () => ({
  fetchSystemTemplates: vi.fn(),
}));

import { fetchSystemTemplates } from "../../lib/api/templates";

const mockFetchSystemTemplates = vi.mocked(fetchSystemTemplates);

beforeEach(() => {
  mockFetchSystemTemplates.mockReset();
});

describe("TemplateSelectorModal (Phase 6 step 1 — system-templates only)", () => {
  it("renders system templates by name and description", async () => {
    mockFetchSystemTemplates.mockResolvedValueOnce([
      {
        id: "generic-modern",
        name: "Modern",
        description: "Two-column layout with a narrow sidebar.",
        preview_image_url: null,
        layout_config: {},
        section_schema: {},
        default_customizations: null,
        content: "",
        layout_template: null,
        manifest: {},
        is_system: true,
        user_id: null,
        created_at: "2026-01-01",
      },
      {
        id: "generic-classic",
        name: "Classic",
        description: "Single-column layout with serif fonts.",
        preview_image_url: null,
        layout_config: {},
        section_schema: {},
        default_customizations: null,
        content: "",
        layout_template: null,
        manifest: {},
        is_system: true,
        user_id: null,
        created_at: "2026-01-01",
      },
    ]);

    render(
      <TemplateSelectorModal
        open
        onClose={vi.fn()}
        templateId="generic-modern"
        onSelect={vi.fn()}
      />,
    );

    expect(await screen.findByText("Modern")).toBeDefined();
    expect(await screen.findByText("Classic")).toBeDefined();
    expect(screen.queryByText(/your templates/i)).toBeNull();
  });

  it("does not render the file-upload affordance", () => {
    mockFetchSystemTemplates.mockResolvedValueOnce([]);
    render(
      <TemplateSelectorModal
        open
        onClose={vi.fn()}
        templateId="generic-modern"
        onSelect={vi.fn()}
      />,
    );
    expect(screen.queryByText(/add new template/i)).toBeNull();
    expect(screen.queryByText(/choose file/i)).toBeNull();
  });

  it("calls onSelect when a system template is clicked", async () => {
    mockFetchSystemTemplates.mockResolvedValueOnce([
      {
        id: "generic-modern",
        name: "Modern",
        description: null,
        preview_image_url: null,
        layout_config: {},
        section_schema: {},
        default_customizations: null,
        content: "",
        layout_template: null,
        manifest: {},
        is_system: true,
        user_id: null,
        created_at: "2026-01-01",
      },
    ]);
    const onSelect = vi.fn();
    render(
      <TemplateSelectorModal
        open
        onClose={vi.fn()}
        templateId="generic-modern"
        onSelect={onSelect}
      />,
    );
    const button = await screen.findByText("Modern");
    fireEvent.click(button);
    expect(onSelect).toHaveBeenCalledWith("generic-modern");
  });
});
