import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LibraryProfileCard from "../LibraryProfileCard";
import type { UserProfile } from "../../../lib/api/profile";

const profile: UserProfile = {
  name: "Ada Lovelace",
  title: "Platform Engineer",
  email: "ada@example.com",
  phone: null,
  location: "London",
  site_text: null,
  site_url: null,
  summary: "Builds reliable systems.",
  photo_url: null,
  email_link: true,
  social_links: [],
};

describe("LibraryProfileCard", () => {
  it("renders one editable profile without entry mutation actions", () => {
    render(<LibraryProfileCard profile={profile} onSave={vi.fn().mockResolvedValue(profile)} />);

    expect(screen.getByTestId("library-profile-card")).toBeInTheDocument();
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^edit$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /clone|delete|create/i })).toBeNull();
  });

  it("reuses the ProfileEditor fields and persists edited data", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(profile);
    render(<LibraryProfileCard profile={profile} onSave={onSave} />);

    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    const name = screen.getAllByRole("textbox")[0];
    await user.clear(name);
    await user.type(name, "Grace Hopper");
    await user.click(screen.getByRole("button", { name: /save profile/i }));

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ name: "Grace Hopper" }));
  });
});
