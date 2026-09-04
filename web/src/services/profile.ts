import client from "./client";
import type { UserProfile, UserProfileUpdate } from "@/contracts/profile";

export async function getProfile(): Promise<UserProfile> {
  const { data } = await client.get("/profile");
  return data;
}

export async function updateProfile(profile: UserProfileUpdate): Promise<UserProfile> {
  const { data } = await client.put("/profile", profile);
  return data;
}
