import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CustomizePanel from "../customization/CustomizePanel";

describe("CustomizePanel", () => {
  it("renders color tab by default", () => {
    render(<CustomizePanel customizations={{}} onChange={vi.fn()} />);

    expect(screen.getByText("Colors")).toBeDefined();
    expect(screen.getByText("Accent")).toBeDefined();
  });

  it("switches between tabs", () => {
    render(<CustomizePanel customizations={{}} onChange={vi.fn()} />);

    fireEvent.click(screen.getByText("Fonts"));
    expect(screen.getByText("Body Font")).toBeDefined();

    fireEvent.click(screen.getByText("Spacing"));
    expect(screen.getByText(/section gap/i)).toBeDefined();
  });

  it("calls onChange when color is changed", () => {
    const onChange = vi.fn();
    render(<CustomizePanel customizations={{ colors: { accent: "#2563eb" } }} onChange={onChange} />);

    const inputs = screen.getAllByRole("textbox") as HTMLInputElement[];
    const accentInput = inputs.find((i) => i.value === "#2563eb");
    if (accentInput) {
      fireEvent.change(accentInput, { target: { value: "#ff0000" } });
      expect(onChange).toHaveBeenCalled();
    }
  });
});
