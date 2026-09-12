import type { RichTextBlock } from "@/shared/cv/schema";

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
  summary?: string | RichTextBlock[] | null;
  photo_url?: string | null;
  email_link: boolean;
  social_links: ProfileSocialLink[];
}

export type UserProfileUpdate = UserProfile;
