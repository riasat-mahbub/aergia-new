import ProfileEditor from "@/components/common/section-editors/profile/ProfileEditor";
import type { ProfileData } from "@/lib/cv/sectionData";
import type { UserProfile } from "../../_types/profile";

interface UserProfileEditorProps {
  profile: UserProfile;
  onChange: (profile: UserProfile) => void;
}

/**
 * Controlled profile form. It owns no persistence, modal, or store state;
 * callers decide how a draft is saved and where the editor is presented.
 */
export default function UserProfileEditor({ profile, onChange }: UserProfileEditorProps) {
  const formData: ProfileData = {
    name: profile.name ?? "",
    title: profile.title ?? "",
    email: profile.email ?? "",
    email_link: profile.email_link,
    phone: profile.phone ?? "",
    location: profile.location ?? "",
    site_text: profile.site_text ?? "",
    site_url: profile.site_url ?? "",
    summary: profile.summary ?? "",
    photo_url: profile.photo_url ?? "",
    social_links: profile.social_links.map((link) => ({ ...link })),
  };

  const handleChange = (next: ProfileData) => {
    onChange({
      ...profile,
      name: next.name ?? null,
      title: next.title ?? null,
      email: next.email ?? null,
      email_link: next.email_link ?? profile.email_link,
      phone: next.phone ?? null,
      location: next.location ?? null,
      site_text: next.site_text ?? null,
      site_url: next.site_url ?? null,
      summary: next.summary ?? null,
      photo_url: next.photo_url ?? null,
      social_links: next.social_links.map((link) => ({ ...link })),
    });
  };

  return <ProfileEditor data={formData} onChange={handleChange} />;
}
