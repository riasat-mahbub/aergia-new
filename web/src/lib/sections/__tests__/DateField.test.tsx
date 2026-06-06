import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DateField, { formatDateRange } from "../DateField";

describe("formatDateRange", () => {
  it("returns empty string when start is empty", () => {
    expect(formatDateRange("", null, false)).toBe("");
    expect(formatDateRange("", "", false)).toBe("");
  });
  it("returns just start when end is empty and current is false", () => {
    expect(formatDateRange("2021-03", null, false)).toBe("2021-03");
    expect(formatDateRange("2021-03", "", false)).toBe("2021-03");
  });
  it("returns start + ' – Present' when current is true and end is empty", () => {
    expect(formatDateRange("2021-03", null, true)).toBe("2021-03 – Present");
    expect(formatDateRange("2021-03", "", true)).toBe("2021-03 – Present");
  });
  it("returns start + ' – ' + end when both are set", () => {
    expect(formatDateRange("2021-03", "2022-01", false)).toBe("2021-03 – 2022-01");
  });
  it("ignores end when current is true", () => {
    expect(formatDateRange("2021-03", "2022-01", true)).toBe("2021-03 – Present");
  });
});

describe("DateField", () => {
  it("renders an empty month input when value is empty", () => {
    render(<DateField value="" onChange={vi.fn()} label="Start Date" />);
    const input = screen.getByLabelText("Start Date") as HTMLInputElement;
    expect(input.type).toBe("month");
    expect(input.value).toBe("");
  });
  it("calls onChange with the new value when input changes", () => {
    const onChange = vi.fn();
    render(<DateField value="" onChange={onChange} label="Start Date" />);
    const input = screen.getByLabelText("Start Date") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "2021-03" } });
    expect(onChange).toHaveBeenCalledWith("2021-03");
  });
  it("does not show a clear button when value is empty", () => {
    render(<DateField value="" onChange={vi.fn()} label="Start Date" />);
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });
  it("shows a clear button when value is set and click clears the value", () => {
    const onChange = vi.fn();
    const { container } = render(<DateField value="2021-03" onChange={onChange} label="Start Date" />);
    const clear = screen.getByRole("button", { name: "Clear" });
    fireEvent.click(clear);
    expect(onChange).toHaveBeenCalledWith("");
    // The clear button must not be positioned at right-8 — that slot is reserved
    // for the calendar icon so the native picker chevron stays clickable.
    expect(clear.className).toContain("right-1");
    expect(clear.className).not.toContain("right-8");
    // Calendar icon present (visible affordance for the native picker).
    expect(container.querySelector("svg.lucide-calendar")).toBeTruthy();
  });
  it("renders a decorative calendar icon next to the input even when empty", () => {
    const { container } = render(<DateField value="" onChange={vi.fn()} label="Start Date" />);
    const cal = container.querySelector("svg.lucide-calendar");
    expect(cal).toBeTruthy();
    // pointer-events-none so clicks pass through to the native input
    expect((cal as Element).getAttribute("class") || "").toContain("pointer-events-none");
  });
  it("does not show a clear button when disabled", () => {
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" disabled />);
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });
  it("disables the input when disabled prop is set", () => {
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" disabled />);
    const input = screen.getByLabelText("Start Date") as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });
});
