/**
 * Phase 2: TemplateWizard is stubbed. The original tests pinned the
 * legacy multi-step wizard copy (basics / layout / styles / assets).
 * That wizard writes the v1 `{colors, fonts, spacing, flags}` shape
 * which Phase 2 rejects at the Customizations boundary.
 *
 * See tracker/tasks/TASK-01KZJ0PHASE2QA-phase-3-template-creator-and-global-customizations.md
 * for the rewrite.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TemplateWizard from "../TemplateWizard";

describe("TemplateWizard (Phase 2 stub)", () => {
  it("renders the deprecation banner", () => {
    render(<TemplateWizard />);
    expect(
      screen.getByText(/Template creator is being rebuilt/),
    ).toBeDefined();
    expect(
      screen.getByText(/incompatible with the v2 manifest pipeline/),
    ).toBeDefined();
  });

  it("does not render the legacy wizard steps", () => {
    render(<TemplateWizard />);
    expect(screen.queryByText(/Arrange zones/)).toBeNull();
    expect(screen.queryByText(/Underline Section Titles/)).toBeNull();
  });
});
