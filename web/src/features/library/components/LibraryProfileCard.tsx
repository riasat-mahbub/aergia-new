import { useState } from "react";
import { Pencil } from "lucide-react";
import Modal from "@/shared/ui/Modal";
import { UserProfileEditor } from "@/features/profile";
import type { UserProfile } from "@/features/profile";

interface LibraryProfileCardProps {
  profile: UserProfile | null;
  isLoading?: boolean;
  onSave: (profile: UserProfile) => Promise<UserProfile>;
}

export default function LibraryProfileCard({
  profile,
  isLoading = false,
  onSave,
}: LibraryProfileCardProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<UserProfile | null>(null);
  const [saving, setSaving] = useState(false);

  const handleOpen = () => {
    if (!profile) return;
    setDraft({ ...profile, social_links: [...profile.social_links] });
    setOpen(true);
  };

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    try {
      await onSave(draft);
      setOpen(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <section className="mb-8 rounded-lg border border-lib-accent/40 bg-lib-surface p-5 shadow-sm" data-testid="library-profile-card">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lib-accent">Library Profile</p>
            {isLoading ? (
              <p className="mt-2 text-sm text-lib-ink-2">Loading profile…</p>
            ) : (
              <>
                <h2 className="mt-1 text-xl font-semibold text-lib-ink">
                  {profile?.name || "Complete your profile"}
                </h2>
                <p className="mt-1 text-sm text-lib-ink-2">
                  {profile?.title || "One profile powers tailored CV generation."}
                </p>
                {profile?.email && <p className="mt-3 text-sm text-lib-ink-2">{profile.email}</p>}
              </>
            )}
          </div>
          <button
            type="button"
            onClick={handleOpen}
            disabled={!profile || isLoading}
            className="inline-flex items-center gap-1 rounded-md border border-lib-rule bg-lib-surface px-3 py-2 text-sm font-medium text-lib-ink-2 hover:bg-lib-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Pencil className="h-4 w-4" />
            Edit
          </button>
        </div>
        <p className="mt-4 text-xs text-lib-ink-3">One profile powers tailored CV generation. It cannot be cloned or deleted.</p>
      </section>

      <Modal open={open} onClose={() => !saving && setOpen(false)} size="wide">
        <div data-testid="library-profile-editor" className="max-h-[80vh] w-full min-w-0 overflow-y-auto bg-lib-surface text-lib-ink">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-lib-ink">Edit Library Profile</h2>
            <p className="mt-1 text-sm text-lib-ink-2">This profile is reused when generating tailored CVs.</p>
          </header>
          {draft && <UserProfileEditor profile={draft} onChange={setDraft} />}
          <footer className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              disabled={saving}
              className="rounded-md px-3 py-2 text-sm font-medium text-lib-ink-2 hover:bg-lib-surface-2 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !draft}
              className="rounded-md bg-lib-accent px-4 py-2 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save profile"}
            </button>
          </footer>
        </div>
      </Modal>
    </>
  );
}
