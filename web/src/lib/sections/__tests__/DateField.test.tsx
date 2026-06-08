import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DateField, { formatDateRange } from "../DateField";

describe("formatDateRange", () => {
  it("returns empty string when start is empty", () => {
    expect(formatDateRange("", "", false)).toBe("");
  });
  it("returns just start when end is empty and current is false", () => {
    expect(formatDateRange("2021-03", "", false)).toBe("2021-03");
  });
  it("returns start + ' – Present' when current is true and end is empty", () => {
    expect(formatDateRange("2021-03", "", true)).toBe("2021-03 – Present");
  });
  it("returns start + ' – ' + end when both are set", () => {
    expect(formatDateRange("2021-03", "2022-01", false)).toBe("2021-03 – 2022-01");
  });
  it("ignores end when current is true", () => {
    expect(formatDateRange("2021-03", "2022-01", true)).toBe("2021-03 – Present");
  });
});

/** Returns the inner <button> of the first gridcell with the given label, scoped to the dialog. */
function dayButton(dialog: HTMLElement, label: string): HTMLButtonElement {
  const cell = within(dialog).getAllByRole("gridcell", { name: label })[0];
  // The gridcell wraps a <button>. Clicking the button fires react-day-picker's onSelect.
  return cell.querySelector("button") as HTMLButtonElement;
}

describe("DateField", () => {
  it("renders a trigger button with the placeholder when value is empty", () => {
    render(<DateField value="" onChange={vi.fn()} label="Start Date" placeholder="Pick a month" />);
    const trigger = screen.getByRole("button", { name: "Start Date" });
    expect(trigger).toBeTruthy();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveAttribute("aria-haspopup", "dialog");
    expect(trigger.textContent).toContain("Pick a month");
  });

  it("renders the formatted value when one is provided", () => {
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" />);
    const trigger = screen.getByRole("button", { name: "Start Date" });
    expect(trigger.textContent).toContain("March 2021");
  });

  it("opens the popup with a calendar when the trigger is clicked", async () => {
    const user = userEvent.setup();
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" />);
    const trigger = screen.getByRole("button", { name: "Start Date" });
    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeTruthy();
    expect(within(dialog).getByRole("grid")).toBeTruthy();
  });

  it("emits YYYY-MM when a day is selected", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DateField value="" onChange={onChange} label="Start Date" />);
    await user.click(screen.getByRole("button", { name: "Start Date" }));
    const dialog = screen.getByRole("dialog");
    await user.click(dayButton(dialog, "15"));
    expect(onChange).toHaveBeenCalledTimes(1);
    const emitted = onChange.mock.calls[0][0] as string;
    expect(emitted).toMatch(/^\d{4}-\d{2}$/);
  });

  it("closes the popup after a selection and reflects aria-expanded=false", async () => {
    const user = userEvent.setup();
    render(<DateField value="" onChange={vi.fn()} label="Start Date" />);
    const trigger = screen.getByRole("button", { name: "Start Date" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog");
    await user.click(dayButton(dialog, "15"));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("closes the popup when Escape is pressed", async () => {
    const user = userEvent.setup();
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" />);
    await user.click(screen.getByRole("button", { name: "Start Date" }));
    expect(screen.getByRole("dialog")).toBeTruthy();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("does not show a clear button when value is empty", () => {
    render(<DateField value="" onChange={vi.fn()} label="Start Date" />);
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });

  it("shows a clear button when value is set; click clears the value", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<DateField value="2021-03" onChange={onChange} label="Start Date" />);
    const clear = screen.getByRole("button", { name: "Clear" });
    await user.click(clear);
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("renders a calendar icon as a visible affordance", () => {
    const { container } = render(<DateField value="" onChange={vi.fn()} label="Start Date" />);
    expect(container.querySelector("svg.lucide-calendar")).toBeTruthy();
  });

  it("does not show a clear button when disabled", () => {
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" disabled />);
    expect(screen.queryByRole("button", { name: "Clear" })).toBeNull();
  });

  it("disables the trigger when disabled prop is set", () => {
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" disabled />);
    const trigger = screen.getByRole("button", { name: "Start Date" });
    expect(trigger).toBeDisabled();
  });

  it("does not open the popup when disabled", () => {
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" disabled />);
    const trigger = screen.getByRole("button", { name: "Start Date" });
    fireEvent.click(trigger);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("exposes a data-testid for integration tests", () => {
    const { container } = render(<DateField value="" onChange={vi.fn()} label="Start Date" />);
    expect(container.querySelector('[data-testid="datefield"]')).toBeTruthy();
  });

  it("renders the popup in a portal so ancestor overflow cannot clip it", async () => {
    const user = userEvent.setup();
    // Wrap the field in a container with overflow:hidden to mimic the
    // accordion body. The popup must still mount in document.body.
    const { container } = render(
      <div style={{ overflow: "hidden", maxHeight: 80 }}>
        <DateField value="" onChange={vi.fn()} label="Start Date" />
      </div>
    );
    await user.click(screen.getByRole("button", { name: "Start Date" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeTruthy();
    expect(container.contains(dialog)).toBe(false);
    expect(document.body.contains(dialog)).toBe(true);
  });

  it("positions the popover using fixed coordinates anchored to the trigger", async () => {
    const user = userEvent.setup();
    render(<DateField value="2021-03" onChange={vi.fn()} label="Start Date" />);
    await user.click(screen.getByRole("button", { name: "Start Date" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog.style.position).toBe("fixed");
    expect(dialog.style.top).not.toBe("");
    expect(dialog.style.left).not.toBe("");
  });
});
