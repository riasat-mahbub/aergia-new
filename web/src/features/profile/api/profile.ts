import client from "@/shared/api/client";
import type { UserProfile, UserProfileUpdate } from "../types";

export async function getProfile(): Promise<UserProfile> {
  const { data } = await client.get("/profile");
  return data;
}

export async function updateProfile(profile: UserProfileUpdate): Promise<UserProfile> {
  const { data } = await client.put("/profile", profile);
  return data;
}
