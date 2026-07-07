import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ZoneCreationModal from "../customization/ZoneCreationModal";

describe("ZoneCreationModal — closed design vocabulary", () => {
  it("emits width and padding tokens, not raw CSS", () => {
    const onCreate = vi.fn();
    render(
      <ZoneCreationModal
        open
        onClose={vi.fn()}
        onCreate={onCreate}
        existingZoneCount={1}
      />
    );

    // name field defaults to "Zone 2"
    fireEvent.click(screen.getByRole("button", { name: /^Add Zone$/ }));

    expect(onCreate).toHaveBeenCalledTimes(1);
    const zone = onCreate.mock.calls[0][0];
    // Default slider: width 50 → "half", padding 24 → "comfortable"
    expect(zone.styles.width).toBe("half");
    expect(zone.styles.padding).toBe("comfortable");
    // No raw CSS values and no keys outside the closed vocabulary.
    expect(zone.styles.width).not.toMatch(/%/);
    expect(zone.styles.padding).not.toMatch(/px/);
    expect(zone.styles).not.toHaveProperty("font");
    expect(zone.styles).not.toHaveProperty("color");
    expect(zone.styles).not.toHaveProperty("background-color");
  });

  it("writes the background as a color ref under the canonical key", () => {
    const onCreate = vi.fn();
    render(
      <ZoneCreationModal
        open
        onClose={vi.fn()}
        onCreate={onCreate}
        existingZoneCount={0}
      />
    );

    const colorInput = screen.getAllByDisplayValue("#ffffff")[0];
    fireEvent.change(colorInput, { target: { value: "#123456" } });
    fireEvent.click(screen.getByRole("button", { name: /^Add Zone$/ }));

    const zone = onCreate.mock.calls[0][0];
    expect(zone.styles.background).toBe("#123456");
  });
});
