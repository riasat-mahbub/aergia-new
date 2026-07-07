import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import ZoneStyleEditor from "../customization/ZoneStyleEditor";

describe("ZoneStyleEditor — closed design vocabulary", () => {
  it("writes width as a token when the slider moves", () => {
    const onChange = vi.fn();
    const { container } = render(
      <ZoneStyleEditor
        zone={{ id: "z1", label: "Sidebar", styles: { width: "narrow", padding: "comfortable" } }}
        onChange={onChange}
      />
    );

    const slider = container.querySelectorAll('input[type="range"]')[0] as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "60" } });

    expect(onChange).toHaveBeenCalled();
    const zone = onChange.mock.calls[0][0];
    expect(zone.styles.width).toBe("half"); // 60% → half token
    expect(zone.styles.width).not.toMatch(/%/);
  });

  it("writes padding as a token and keeps the background key canonical", () => {
    const onChange = vi.fn();
    const { container } = render(
      <ZoneStyleEditor
        zone={{ id: "z1", label: "Main", styles: { width: "full", padding: "loose", background: "#aabbcc" } }}
        onChange={onChange}
      />
    );

    const slider = container.querySelectorAll('input[type="range"]')[1] as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "12" } });

    expect(onChange).toHaveBeenCalled();
    const zone = onChange.mock.calls[0][0];
    expect(zone.styles.padding).toBe("tight"); // 12px → tight token
    expect(zone.styles.padding).not.toMatch(/px/);
    expect(zone.styles.background).toBe("#aabbcc");
    expect(zone.styles).not.toHaveProperty("background-color");
  });
});
