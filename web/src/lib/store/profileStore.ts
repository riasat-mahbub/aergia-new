import { create } from "zustand";
import * as profileApi from "../api/profile";
import type { UserProfile, UserProfileUpdate } from "../api/profile";

interface ProfileState {
  profile: UserProfile | null;
  isLoading: boolean;
  loaded: boolean;
  fetch: () => Promise<void>;
  update: (profile: UserProfileUpdate) => Promise<UserProfile>;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profile: null,
  isLoading: false,
  loaded: false,

  fetch: async () => {
    set({ isLoading: true });
    try {
      const profile = await profileApi.getProfile();
      set({ profile, isLoading: false, loaded: true });
    } catch {
      set({ isLoading: false, loaded: true });
    }
  },

  update: async (profile) => {
    const updated = await profileApi.updateProfile(profile);
    set({ profile: updated, loaded: true });
    return updated;
  },
}));
