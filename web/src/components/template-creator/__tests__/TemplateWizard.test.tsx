/** @vitest-environment jsdom */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import TemplateWizard from "../TemplateWizard";
import { templateManifestSchema } from "../../../lib/validators/sections";
import * as templatesApi from "../../../lib/api/templates";

vi.mock("../../../lib/api/render", () => ({
  fetchRendererSupport: vi.fn(() =>
    Promise.resolve({
      break_before: "FULL",
      keep_together: "FULL",
      keep_with_next: "FULL",
      heading_keeps_with_first: "FULL",
      feature_skills_inline: "FULL",
      feature_section_underline: "FULL",
      feature_anchor_styling: "FULL",
    }),
  ),
}));

vi.mock("../../../lib/api/templates", () => ({
  uploadUserTemplate: vi.fn(() => Promise.resolve({} as any)),
}));


const mockUpload = vi.mocked(templatesApi.uploadUserTemplate);

afterEach(() => {
  mockUpload.mockClear();
});

describe("TemplateWizard (Phase 3)", () => {
  it("renders the four step headings", () => {
    render(<TemplateWizard />);
    expect(screen.getByTestId("wizard-step-Basics")).toBeDefined();
    expect(screen.getByTestId("wizard-step-Layout")).toBeDefined();
    expect(screen.getByTestId("wizard-step-Global-Styles")).toBeDefined();
    expect(screen.getByTestId("wizard-step-Review")).toBeDefined();
  });

  it("does not render the deprecated Phase 2 banner copy", () => {
    render(<TemplateWizard />);
    expect(screen.queryByText(/Template creator is being rebuilt/)).toBeNull();
    expect(screen.queryByText(/incompatible with the v2 manifest pipeline/)).toBeNull();
  });

  it("typing in the name field updates manifest.name via onManifestChange", () => {
    const onManifestChange = vi.fn();
    render(<TemplateWizard onManifestChange={onManifestChange} />);

    const nameInput = screen.getByTestId("wizard-name-input");
    fireEvent.change(nameInput, { target: { value: "My Template" } });

    const lastCall = onManifestChange.mock.calls[onManifestChange.mock.calls.length - 1];
    expect(lastCall?.[0].name).toBe("My Template");
  });

  it("changing the spacing radio updates manifest.layout_defaults.spacing", () => {
    const onManifestChange = vi.fn();
    render(<TemplateWizard onManifestChange={onManifestChange} />);

    // Advance to the Layout step via the Next button.
    fireEvent.click(screen.getByText("Next"));
    fireEvent.click(screen.getByTestId("wizard-spacing-compact"));

    const lastCall = onManifestChange.mock.calls[onManifestChange.mock.calls.length - 1];
    expect(lastCall?.[0].layout_defaults?.spacing).toBe("compact");
  });
  it("changing the accent color hex updates manifest.global_styles.accent_color", () => {
    const onManifestChange = vi.fn();
    render(<TemplateWizard onManifestChange={onManifestChange} />);

    // Advance past Basics and Layout to reach Global Styles.
    fireEvent.click(screen.getByText("Next"));
    fireEvent.click(screen.getByText("Next"));
    const accent = screen.getByTestId("wizard-accent-input");
    fireEvent.change(accent, { target: { value: "#abcdef" } });

    const lastCall = onManifestChange.mock.calls[onManifestChange.mock.calls.length - 1];
    expect(lastCall?.[0].global_styles?.accent_color).toBe("#abcdef");
  });

  it("toggling show_title for a section type adds an entry to policy_overrides.by_type", () => {
    const onManifestChange = vi.fn();
    render(<TemplateWizard onManifestChange={onManifestChange} />);

    fireEvent.click(screen.getByText("Next"));
    fireEvent.click(screen.getByText("Next"));
    // profile defaults to show_title=false, so a click should set it to true.
    const checkbox = screen.getByTestId("wizard-show-title-profile") as HTMLInputElement;
    fireEvent.click(checkbox);

    const lastCall = onManifestChange.mock.calls[onManifestChange.mock.calls.length - 1];
    const byType = lastCall?.[0].policy_overrides?.by_type;
    expect(byType).toBeDefined();
    expect(byType.profile).toBeDefined();
    expect(byType.profile.show_title).toBe(true);
  });

  it("templateManifestSchema rejects a v1 manifest", () => {
    const r = templateManifestSchema.safeParse({
      manifest_version: 1,
      name: "X",
      zones: [],
      placement: {},
    });
    expect(r.success).toBe(false);
  });

  it("uses uploadUserTemplate with the v2 manifest shape on Use this template", async () => {
    mockUpload.mockResolvedValueOnce({} as any);
    const onComplete = vi.fn();
    render(<TemplateWizard onComplete={onComplete} initialManifest={{ name: "U" }} />);

    // Fill in a name
    fireEvent.change(screen.getByTestId("wizard-name-input"), { target: { value: "U" } });
    // Navigate to Review (3 Next clicks)
    fireEvent.click(screen.getByText("Next"));
    fireEvent.click(screen.getByText("Next"));
    fireEvent.click(screen.getByText("Next"));

    await waitFor(() => {
      expect(screen.getByTestId("wizard-use-template")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("wizard-use-template"));

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalled();
    });
    const call = mockUpload.mock.calls[0][0];
    expect(call.name).toBe("U");
    expect(call.manifest.manifest_version).toBe(2);
  });
});
