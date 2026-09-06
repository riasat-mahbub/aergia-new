import { create } from "zustand";
import * as profileApi from "../api/profile";
import type { UserProfile, UserProfileUpdate } from "../types";

interface ProfileState {
  profile: UserProfile | null;
  isLoading: boolean;
  loaded: boolean;
  error: string | null;
  fetch: () => Promise<void>;
  update: (profile: UserProfileUpdate) => Promise<UserProfile>;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profile: null,
  isLoading: false,
  loaded: false,
  error: null,

  fetch: async () => {
    set({ isLoading: true, error: null });
    try {
      const profile = await profileApi.getProfile();
      set({ profile, isLoading: false, loaded: true, error: null });
    } catch {
      set({
        isLoading: false,
        loaded: true,
        error: "Unable to load your profile. Please try again.",
      });
    }
  },

  update: async (profile) => {
    const updated = await profileApi.updateProfile(profile);
    set({ profile: updated, loaded: true });
    return updated;
  },
}));
