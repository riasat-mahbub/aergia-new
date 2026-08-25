import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TokenPicker from "../../controls/TokenPicker";

describe("TokenPicker", () => {
  it("renders the Default pill plus every section-spacing token", () => {
    render(<TokenPicker value="comfortable" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "Default" })).toBeDefined();
    expect(screen.getByRole("radio", { name: "None" })).toBeDefined();
    expect(screen.getByRole("radio", { name: "Tight" })).toBeDefined();
    expect(screen.getByRole("radio", { name: "Comfortable" })).toBeDefined();
    expect(screen.getByRole("radio", { name: "Loose" })).toBeDefined();
    expect(screen.getByRole("radio", { name: "Spacious" })).toBeDefined();
  });

  it("marks the active token as aria-checked", () => {
    render(<TokenPicker value="tight" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "Tight" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "Comfortable" })).toHaveAttribute("aria-checked", "false");
  });

  it("calls onChange with the picked token", async () => {
    const onChange = vi.fn();
    render(<TokenPicker value="comfortable" onChange={onChange} />);
    await userEvent.click(screen.getByRole("radio", { name: "Loose" }));
    expect(onChange).toHaveBeenCalledWith("loose");
  });

  it("clicking the Default pill passes null (inherit)", async () => {
    const onChange = vi.fn();
    render(<TokenPicker value="comfortable" onChange={onChange} />);
    await userEvent.click(screen.getByRole("radio", { name: "Default" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("hides the Default pill when showDefault is false", () => {
    render(<TokenPicker value="comfortable" onChange={vi.fn()} showDefault={false} />);
    expect(screen.queryByRole("radio", { name: "Default" })).toBeNull();
  });

  it("renders a gap indicator", () => {
    render(<TokenPicker value="comfortable" onChange={vi.fn()} />);
    expect(screen.getByLabelText("24px gap indicator")).toBeDefined();
  });
});
