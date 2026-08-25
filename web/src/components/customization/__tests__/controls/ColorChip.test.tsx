import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ColorChip from "../../controls/ColorChip";

describe("ColorChip", () => {
  it("shows the swatch and hex when a value is set", () => {
    render(<ColorChip value="#ff0000" onChange={vi.fn()} />);
    const text = screen.getByPlaceholderText("#RRGGBB") as HTMLInputElement;
    expect(text.value).toBe("#ff0000");
  });

  it("calls onChange with null when the hex input is cleared", () => {
    const onChange = vi.fn();
    render(<ColorChip value="#ff0000" onChange={onChange} />);
    const text = screen.getByPlaceholderText("#RRGGBB");
    fireEvent.change(text, { target: { value: "" } });
    fireEvent.blur(text);
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("calls onChange with the new value when a valid hex is typed", () => {
    const onChange = vi.fn();
    render(<ColorChip value="#000000" onChange={onChange} />);
    const text = screen.getByPlaceholderText("#RRGGBB");
    fireEvent.change(text, { target: { value: "#abcdef" } });
    fireEvent.blur(text);
    expect(onChange).toHaveBeenCalledWith("#abcdef");
  });

  it("does NOT propagate invalid hex strings", () => {
    const onChange = vi.fn();
    render(<ColorChip value="#000000" onChange={onChange} />);
    const text = screen.getByPlaceholderText("#RRGGBB");
    fireEvent.change(text, { target: { value: "not-a-color" } });
    fireEvent.blur(text);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows revert button only when showRevert is true and onRevert is given", () => {
    const onRevert = vi.fn();
    const { rerender } = render(<ColorChip value="#ff0000" onChange={vi.fn()} />);
    expect(screen.queryByLabelText("Revert to inherited")).toBeNull();
    rerender(<ColorChip value="#ff0000" onChange={vi.fn()} showRevert onRevert={onRevert} />);
    fireEvent.click(screen.getByLabelText("Revert to inherited"));
    expect(onRevert).toHaveBeenCalledTimes(1);
  });

  it("Enter commits the value", () => {
    const onChange = vi.fn();
    render(<ColorChip value="#000000" onChange={onChange} />);
    const text = screen.getByPlaceholderText("#RRGGBB");
    fireEvent.change(text, { target: { value: "#123456" } });
    fireEvent.keyDown(text, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("#123456");
  });
});
