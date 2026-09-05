import client from "@/services/client";
import type { UserProfile, UserProfileUpdate } from "../_types/profile";

export async function getProfile(): Promise<UserProfile> {
  const { data } = await client.get("/profile");
  return data;
}

export async function updateProfile(profile: UserProfileUpdate): Promise<UserProfile> {
  const { data } = await client.put("/profile", profile);
  return data;
}
