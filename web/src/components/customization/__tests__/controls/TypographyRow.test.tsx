import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TypographyRow from "../../controls/TypographyRow";

describe("TypographyRow", () => {
  it("renders the live preview with the sample text", () => {
    render(<TypographyRow label="Name" sample="Alex Rivera" current={{}} onChange={vi.fn()} />);
    expect(screen.getByText("Alex Rivera")).toBeDefined();
  });

  it("toggles bold and writes the key to onChange", async () => {
    const onChange = vi.fn();
    render(<TypographyRow label="Name" sample="Alex" current={{}} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Bold"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ bold: true }));
  });

  it("toggles italic and writes the key", async () => {
    const onChange = vi.fn();
    render(<TypographyRow label="Name" sample="Alex" current={{}} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Italic"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ italic: true }));
  });

  it("toggles underline (newly exposed)", async () => {
    const onChange = vi.fn();
    render(<TypographyRow label="Name" sample="Alex" current={{}} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Underline"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ underline: true }));
  });

  it("toggles strikethrough (newly exposed)", async () => {
    const onChange = vi.fn();
    render(<TypographyRow label="Name" sample="Alex" current={{}} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Strikethrough"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ strike: true }));
  });

  it("writes font_size when a size is picked", async () => {
    const onChange = vi.fn();
    render(<TypographyRow label="Name" sample="Alex" current={{}} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText("Font size"), "large");
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ font_size: "large" }));
  });

  it("drops a key from the wire when toggling back to the default", async () => {
    const onChange = vi.fn();
    render(<TypographyRow label="Name" sample="Alex" current={{ bold: true }} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText("Bold"));
    expect(onChange).toHaveBeenCalledWith({});
  });

  it("renders a redirect note for rich text fields and no controls", () => {
    render(<TypographyRow label="Summary" sample="Hello" current={{}} onChange={vi.fn()} isRichText />);
    expect(screen.getByText(/rich text field/i)).toBeDefined();
    expect(screen.queryByLabelText("Bold")).toBeNull();
    expect(screen.queryByLabelText("Font size")).toBeNull();
  });

  it("renders the preview with bold applied when current.bold is true", () => {
    render(<TypographyRow label="Name" sample="Alex" current={{ bold: true }} onChange={vi.fn()} />);
    const preview = screen.getByLabelText("Name preview") as HTMLElement;
    expect(preview.style.fontWeight).toBe("700");
  });
});
