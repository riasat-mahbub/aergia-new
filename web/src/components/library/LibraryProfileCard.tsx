import ProfileCard from "../profile/ProfileCard";
import type { UserProfile } from "../../lib/api/profile";

interface LibraryProfileCardProps {
  profile: UserProfile | null;
  isLoading?: boolean;
  onSave: (profile: UserProfile) => Promise<UserProfile>;
}

export default function LibraryProfileCard({ profile, isLoading = false, onSave }: LibraryProfileCardProps) {
  return (
    <ProfileCard
      profile={profile}
      isLoading={isLoading}
      onSave={onSave}
      eyebrow="Library Profile"
      description="One profile powers tailored CV generation. It cannot be cloned or deleted."
      testId="library-profile-card"
      editorTestId="library-profile-editor"
      surfaceClassName="mb-8 rounded-lg border border-lib-accent/40 bg-lib-surface p-5 shadow-sm"
      modalTitle="Edit Library Profile"
      modalDescription="This profile is reused when generating tailored CVs."
    />
  );
}
