import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LibraryEntryCard from "../LibraryEntryCard";

const entry = {
  id: "lib_1",
  kind: "experience" as const,
  payload: [{ title: "Senior Engineer", company: "Acme" }],
  created_at: "2026-01-01",
  updated_at: "2026-01-02",
};

describe("LibraryEntryCard", () => {
  it("renders title and meta from payload", () => {
    render(<LibraryEntryCard entry={entry} />);
    expect(screen.getByText("Senior Engineer")).toBeInTheDocument();
    expect(screen.getByText(/Acme/)).toBeInTheDocument();
  });

  it("invokes onEdit and onDelete callbacks", async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const user = userEvent.setup();
    render(
      <LibraryEntryCard entry={entry} onEdit={onEdit} onDelete={onDelete} />,
    );

    await user.click(screen.getByRole("button", { name: /edit entry/i }));
    expect(onEdit).toHaveBeenCalledOnce();

    await user.click(screen.getByRole("button", { name: /delete entry/i }));
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("falls back to kind capitalised when payload has no title", () => {
    render(
      <LibraryEntryCard
        entry={{ ...entry, payload: [{ foo: "bar" }] }}
      />,
    );
    expect(screen.getByText("Experience")).toBeInTheDocument();
  });
});
