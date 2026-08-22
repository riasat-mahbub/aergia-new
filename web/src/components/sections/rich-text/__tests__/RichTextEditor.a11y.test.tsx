import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import RichTextEditor from "../RichTextEditor";

describe("RichTextEditor accessibility and link controls", () => {
  it("exposes a labelled toolbar and formatting buttons", () => {
    render(<RichTextEditor value={[{ type: "paragraph", items: [{ text: "Hello" }] }]} onChange={vi.fn()} />);

    expect(screen.getByRole("toolbar", { name: "Rich text formatting" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /bold/i })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: /bullet list/i })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("combobox", { name: "Font size" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Rich text editor" })).toBeInTheDocument();
  });

  it("shows guidance when a rich-text field is empty", () => {
    render(<RichTextEditor value={[]} onChange={vi.fn()} />);

    expect(screen.getByText("Write a concise description…")).toBeInTheDocument();
  });

  it("opens an application-styled link dialog and validates unsafe URLs", async () => {
    const user = userEvent.setup();
    render(<RichTextEditor value={[{ type: "paragraph", items: [{ text: "Hello" }] }]} onChange={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /add link/i }));
    expect(screen.getByRole("dialog", { name: "Add link" })).toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "URL" }), "javascript:alert(1)");
    await user.type(screen.getByRole("textbox", { name: "Display text" }), "Unsafe");
    await user.click(screen.getByRole("button", { name: "Save link" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/safe/i);
  });
});
