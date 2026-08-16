import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SettingsPage from "../SettingsPage";
import { useAuthStore } from "../../lib/store/authStore";
import { useProfileStore } from "../../lib/store/profileStore";
import type { UserProfile } from "../../lib/api/profile";

vi.mock("../../lib/api/client", () => ({
  default: { post: vi.fn() },
}));

vi.mock("../../lib/api/profile", () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

vi.mock("../../lib/store/uiStore", () => ({
  useToastStore: (selector: (state: { addToast: ReturnType<typeof vi.fn> }) => unknown) =>
    selector({ addToast: vi.fn() }),
}));

import client from "../../lib/api/client";
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
  useAuthStore.setState({ isAuthenticated: true, isLoading: false });
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

  it("keeps the password change request separate from the profile data", async () => {
    const user = userEvent.setup();
    vi.mocked(client.post).mockResolvedValue({ data: undefined });
    useProfileStore.setState({ profile, loaded: true });

    render(<SettingsPage />);

    expect(screen.getByLabelText("Current Password")).toHaveValue("");
    await user.type(screen.getByLabelText("Current Password"), "old-password");
    await user.type(screen.getByLabelText("New Password"), "new-password");
    await user.type(screen.getByLabelText("Confirm New Password"), "new-password");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    await waitFor(() => expect(client.post).toHaveBeenCalledWith("/auth/change-password", {
      old_password: "old-password",
      new_password: "new-password",
    }));
    expect(screen.getByLabelText("Current Password")).toHaveValue("");
  });

  it("does not expose or prefill a current password and uses password-manager scopes", async () => {
    const user = userEvent.setup();
    useProfileStore.setState({ profile, loaded: true });
    vi.mocked(client.post).mockResolvedValue({ data: undefined });

    render(<SettingsPage />);

    const current = screen.getByLabelText("Current Password");
    const next = screen.getByLabelText("New Password");
    const confirm = screen.getByLabelText("Confirm New Password");
    expect(current).toHaveAttribute("type", "password");
    expect(current).toHaveAttribute("name", "current_password");
    expect(current).toHaveAttribute("autocomplete", "current-password");
    expect(current).toHaveValue("");
    expect(next).toHaveAttribute("autocomplete", "new-password");
    expect(confirm).toHaveAttribute("autocomplete", "new-password");

    await user.type(current, "old-password");
    await user.type(next, "1234567");
    await user.type(confirm, "1234567");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    expect(await screen.findByText("Password must be at least 8 characters")).toBeInTheDocument();
    expect(client.post).not.toHaveBeenCalled();
  });

  it("clears all transient password fields after a successful change", async () => {
    const user = userEvent.setup();
    useProfileStore.setState({ profile, loaded: true });
    vi.mocked(client.post).mockResolvedValue({ data: undefined });
    render(<SettingsPage />);

    await user.type(screen.getByLabelText("Current Password"), "old-password");
    await user.type(screen.getByLabelText("New Password"), "new-password");
    await user.type(screen.getByLabelText("Confirm New Password"), "new-password");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    await waitFor(() => {
      expect(screen.getByLabelText("Current Password")).toHaveValue("");
      expect(screen.getByLabelText("New Password")).toHaveValue("");
      expect(screen.getByLabelText("Confirm New Password")).toHaveValue("");
    });
  });
});
