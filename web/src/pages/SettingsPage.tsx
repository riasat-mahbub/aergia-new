import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { KeyRound, ShieldCheck } from "lucide-react";
import ProfileCard from "../components/profile/ProfileCard";
import LLMKeyDialog from "../components/builder/LLMKeyDialog";
import { useProfileStore } from "../lib/store/profileStore";

export default function SettingsPage() {
  const profile = useProfileStore((s) => s.profile);
  const profileLoading = useProfileStore((s) => s.isLoading);
  const profileLoaded = useProfileStore((s) => s.loaded);
  const fetchProfile = useProfileStore((s) => s.fetch);
  const updateProfile = useProfileStore((s) => s.update);
  const [showKeys, setShowKeys] = useState(false);

  useEffect(() => {
    if (!profileLoaded) fetchProfile();
  }, [fetchProfile, profileLoaded]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-5xl px-4 py-8"
    >
      <h1 className="mb-2 text-2xl font-bold text-app-ink">Settings</h1>
      <p className="mb-6 text-sm text-app-ink-2">Manage your profile and the tools used to import CVs.</p>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <ProfileCard
          profile={profile}
          isLoading={profileLoading}
          onSave={updateProfile}
          eyebrow="Settings Profile"
          description="Shared profile details used when building your CVs."
          testId="settings-profile-card"
          surfaceClassName="rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm"
        />

        <section className="rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm" aria-labelledby="import-settings-heading">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-app-primary-soft p-2 text-app-primary">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h2 id="import-settings-heading" className="text-lg font-semibold text-app-ink">Import settings</h2>
              <p className="mt-1 text-sm text-app-ink-2">Configure the provider used when parsing an imported CV.</p>
            </div>
          </div>
          <div className="mt-5 flex gap-3 rounded-md bg-app-primary-soft px-3 py-3 text-xs text-app-ink-2">
            <ShieldCheck className="h-4 w-4 shrink-0 text-app-primary" />
            <p>API keys stay in memory and are sent directly to the provider during import. They are not saved to browser storage or the server.</p>
          </div>
          <button
            type="button"
            onClick={() => setShowKeys(true)}
            className="mt-5 inline-flex items-center gap-1.5 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft"
          >
            <KeyRound className="h-4 w-4" />
            Configure API keys
          </button>
        </section>
      </div>

      <LLMKeyDialog open={showKeys} onClose={() => setShowKeys(false)} />
    </motion.div>
  );
}
