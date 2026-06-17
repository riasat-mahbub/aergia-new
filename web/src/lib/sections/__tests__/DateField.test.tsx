import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DateField, {
  formatDateRange,
  formatSingleDate,
  DATE_STYLE_OPTIONS,
} from "../DateField";
import type { DateStyle } from "../types";

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
  it("uses the style's separator to join the range when style is provided", () => {
    const style: DateStyle = { key: "MM/YYYY", rangeSep: "/" };
    expect(formatDateRange("2021-03", "2022-01", false, style)).toBe("03/2021/01/2022");
  });
  it("reformats both bounds when style is provided", () => {
    const style: DateStyle = { key: "Month YYYY", rangeSep: " – " };
    expect(formatDateRange("2021-03", "2022-01", false, style)).toBe("March 2021 – January 2022");
  });
  it("current still wins over end when style is provided", () => {
    const style: DateStyle = { key: "Month YYYY", rangeSep: " – " };
    expect(formatDateRange("2021-03", "2022-01", true, style)).toBe("March 2021 – Present");
  });
});

describe("formatSingleDate", () => {
  it("returns empty string for empty input", () => {
    expect(formatSingleDate("")).toBe("");
    expect(formatSingleDate("", { key: "Mon YYYY", rangeSep: " – " })).toBe("");
  });
  it("returns empty string for null/undefined input", () => {
    expect(formatSingleDate(null)).toBe("");
    expect(formatSingleDate(undefined)).toBe("");
    expect(formatSingleDate(null, { key: "Mon YYYY", rangeSep: " – " })).toBe("");
  });
  it("returns raw value when no style is provided", () => {
    expect(formatSingleDate("2021-03")).toBe("2021-03");
    expect(formatSingleDate("2021-03", null)).toBe("2021-03");
  });
  it("returns raw value when style is missing key", () => {
    expect(
      formatSingleDate("2021-03", { key: "" as DateStyle["key"], rangeSep: "x" }),
    ).toBe("2021-03");
  });
  it("returns raw value for legacy year-only inputs", () => {
    expect(formatSingleDate("2020", { key: "Mon YYYY", rangeSep: " – " })).toBe("2020");
  });
  it("returns raw value for out-of-range months", () => {
    expect(formatSingleDate("2021-13", { key: "Mon YYYY", rangeSep: " – " })).toBe("2021-13");
  });
  it("returns raw value for unknown preset keys", () => {
    expect(
      formatSingleDate("2021-03", { key: "Garbage" as DateStyle["key"], rangeSep: "x" }),
    ).toBe("2021-03");
  });

  it.each(DATE_STYLE_OPTIONS.map((o) => [o.value, o.rangeSep]) as [DateStyle["key"], string][])(
    "renders %s for 2021-03",
    (key, rangeSep) => {
      const expected: Record<string, string> = {
        "YYYY-MM": "2021-03",
        "YYYY/MM": "2021/03",
        "MM/YYYY": "03/2021",
        "MM-YYYY": "03-2021",
        "MM.YYYY": "03.2021",
        "YYYY.MM": "2021.03",
        "Mon YYYY": "Mar 2021",
        "Month YYYY": "March 2021",
        "YYYY": "2021",
        "Mon-YYYY": "Mar-2021",
      };
      expect(formatSingleDate("2021-03", { key, rangeSep })).toBe(expected[key]);
    },
  );
});

describe("DATE_STYLE_OPTIONS", () => {
  it("has 10 entries", () => {
    expect(DATE_STYLE_OPTIONS).toHaveLength(10);
  });
  it("uses the same keys as the Python DATE_STYLE_OPTIONS contract", () => {
    expect(DATE_STYLE_OPTIONS.map((o) => o.value)).toEqual([
      "YYYY-MM",
      "YYYY/MM",
      "MM/YYYY",
      "MM-YYYY",
      "MM.YYYY",
      "YYYY.MM",
      "Mon YYYY",
      "Month YYYY",
      "YYYY",
      "Mon-YYYY",
    ]);
  });
  it("encodes a non-empty rangeSep for each option", () => {
    for (const opt of DATE_STYLE_OPTIONS) {
      expect(opt.rangeSep.length).toBeGreaterThan(0);
    }
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
    const { container } = render(
      <div style={{ overflow: "hidden", maxHeight: 80 }}>
        <DateField value="" onChange={vi.fn()} label="Start Date" />
      </div>,
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
