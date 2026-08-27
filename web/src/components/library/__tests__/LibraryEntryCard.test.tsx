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

  it("renders normal experience fields and date range", () => {
    render(
      <LibraryEntryCard
        entry={{
          ...entry,
          payload: [{
            id: "exp_1",
            company: "Acme",
            position: "Lead Engineer",
            start_date: "2020",
            end_date: "2024",
          }],
        }}
      />,
    );
    expect(screen.getByText("Lead Engineer")).toBeInTheDocument();
    expect(screen.getByText("Acme · 2020 – 2024")).toBeInTheDocument();
  });

  it("renders normal education fields and date range", () => {
    render(
      <LibraryEntryCard
        entry={{
          ...entry,
          kind: "education",
          payload: [{
            id: "edu_1",
            institution: "State U",
            degree: "BS Computer Science",
            start_date: "2018",
            end_date: "2022",
          }],
        }}
      />,
    );
    expect(screen.getByText("BS Computer Science")).toBeInTheDocument();
    expect(screen.getByText("State U · 2018 – 2022")).toBeInTheDocument();
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
