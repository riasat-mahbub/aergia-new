import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SettingsPage from "../SettingsPage";
import { useProfileStore } from "../../lib/store/profileStore";
import type { UserProfile } from "../../lib/api/profile";

vi.mock("../../lib/api/profile", () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

vi.mock("../../lib/store/uiStore", () => ({
  useToastStore: (selector: (state: { addToast: ReturnType<typeof vi.fn> }) => unknown) =>
    selector({ addToast: vi.fn() }),
}));

import * as profileApi from "../../lib/api/profile";

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

beforeEach(() => {
  useProfileStore.setState({ profile: null, isLoading: false, loaded: false });
  vi.clearAllMocks();
});

describe("SettingsPage", () => {
  it("loads and renders the shared profile editor", async () => {
    vi.mocked(profileApi.getProfile).mockResolvedValue(profile);

    render(<SettingsPage />);

    expect(await screen.findByText("Ada Lovelace")).toBeInTheDocument();
    expect(profileApi.getProfile).toHaveBeenCalledOnce();
    expect(screen.getByText("Settings Profile")).toBeInTheDocument();
  });

  it("saves profile edits through the profile store", async () => {
    const user = userEvent.setup();
    const updated = { ...profile, name: "Grace Hopper" };
    vi.mocked(profileApi.updateProfile).mockResolvedValue(updated);
    useProfileStore.setState({ profile, loaded: true });

    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /^edit$/i }));
    const name = screen.getByDisplayValue("Ada Lovelace");
    await user.clear(name);
    await user.type(name, "Grace Hopper");
    await user.click(screen.getByRole("button", { name: /save profile/i }));

    await waitFor(() => expect(profileApi.updateProfile).toHaveBeenCalledWith(expect.objectContaining({ name: "Grace Hopper" })));
  });

  it("keeps API-key configuration in the account settings surface", async () => {
    const user = userEvent.setup();
    useProfileStore.setState({ profile, loaded: true });

    render(<SettingsPage />);

    expect(screen.getByRole("heading", { name: "Import settings" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /configure api keys/i }));
    expect(screen.getByText(/stored only in memory/i)).toBeInTheDocument();
  });

  it("does not render a password-change form", () => {
    useProfileStore.setState({ profile, loaded: true });
    render(<SettingsPage />);

    expect(screen.queryByRole("heading", { name: /change password/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/current password/i)).not.toBeInTheDocument();
  });
});
