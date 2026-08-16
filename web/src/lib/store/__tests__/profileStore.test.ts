import { beforeEach, describe, expect, it, vi } from "vitest";
import { useProfileStore } from "../profileStore";
import type { UserProfile } from "../../api/profile";

vi.mock("../../api/profile", () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

import * as profileApi from "../../api/profile";

const profile: UserProfile = {
  name: "Ada",
  title: "Engineer",
  email: "ada@example.com",
  phone: null,
  location: null,
  site_text: null,
  site_url: null,
  summary: null,
  photo_url: null,
  email_link: true,
  social_links: [],
};

beforeEach(() => {
  useProfileStore.setState({ profile: null, isLoading: false, loaded: false });
  vi.clearAllMocks();
});

describe("useProfileStore", () => {
  it("fetches and stores the singleton profile", async () => {
    vi.mocked(profileApi.getProfile).mockResolvedValue(profile);

    await useProfileStore.getState().fetch();

    expect(useProfileStore.getState().profile).toEqual(profile);
    expect(useProfileStore.getState().loaded).toBe(true);
    expect(useProfileStore.getState().isLoading).toBe(false);
  });

  it("returns and stores the updated profile", async () => {
    const updated = { ...profile, name: "Grace" };
    vi.mocked(profileApi.updateProfile).mockResolvedValue(updated);

    await expect(useProfileStore.getState().update(updated)).resolves.toEqual(updated);
    expect(useProfileStore.getState().profile).toEqual(updated);
  });
});
