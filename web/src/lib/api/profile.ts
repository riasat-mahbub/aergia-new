import client from "./client";

export interface ProfileSocialLink {
  label: string;
  url: string;
  icon: string;
}

export interface UserProfile {
  name?: string | null;
  title?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  site_text?: string | null;
  site_url?: string | null;
  summary?: string | null;
  photo_url?: string | null;
  email_link: boolean;
  social_links: ProfileSocialLink[];
}

export type UserProfileUpdate = UserProfile;

export async function getProfile(): Promise<UserProfile> {
  const { data } = await client.get("/profile");
  return data;
}

export async function updateProfile(profile: UserProfileUpdate): Promise<UserProfile> {
  const { data } = await client.put("/profile", profile);
  return data;
}
