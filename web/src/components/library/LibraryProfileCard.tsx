import { useState } from "react";
import { Pencil } from "lucide-react";
import Modal from "../common/Modal";
import SectionEditorPanel from "../sections/SectionEditorPanel";
import type { SectionInstance } from "../../lib/sections/types";
import type { UserProfile } from "../../lib/api/profile";

interface LibraryProfileCardProps {
  profile: UserProfile | null;
  isLoading?: boolean;
  onSave: (profile: UserProfile) => Promise<UserProfile>;
}

export default function LibraryProfileCard({ profile, isLoading = false, onSave }: LibraryProfileCardProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<UserProfile | null>(null);
  const [saving, setSaving] = useState(false);

  const handleOpen = () => {
    if (!profile) return;
    setDraft({ ...profile, social_links: [...(profile.social_links ?? [])] });
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

  const syntheticInstance: SectionInstance | null = draft
    ? {
        id: "library_profile",
        type: "profile",
        title: "Profile",
        enabled: true,
        data: draft as unknown as Record<string, unknown>,
        style: null,
      }
    : null;

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
                  {profile?.title || "Shared contact details for generated CVs"}
                </p>
                {profile?.email && <p className="mt-3 text-sm text-lib-ink-2">{profile.email}</p>}
              </>
            )}
          </div>
          <button
            type="button"
            onClick={handleOpen}
            disabled={!profile || isLoading}
            className="inline-flex items-center gap-1 rounded-md border border-lib-rule bg-lib-surface px-3 py-2 text-sm font-medium text-lib-ink hover:bg-lib-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Pencil className="h-4 w-4" />
            Edit
          </button>
        </div>
        <p className="mt-4 text-xs text-lib-ink-3">
          One profile powers tailored CV generation. It cannot be cloned or deleted.
        </p>
      </section>

      <Modal open={open} onClose={() => !saving && setOpen(false)}>
        <div className="max-h-[80vh] w-[min(640px,90vw)] overflow-y-auto">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Edit Library Profile</h2>
            <p className="mt-1 text-sm text-gray-600">This profile is reused when generating tailored CVs.</p>
          </header>
          {syntheticInstance && (
            <SectionEditorPanel
              instance={syntheticInstance}
              onChange={(_id, data) => setDraft((current) => (current ? { ...current, ...(data as UserProfile) } : current))}
            />
          )}
          <footer className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              disabled={saving}
              className="rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !draft}
              className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save profile"}
            </button>
          </footer>
        </div>
      </Modal>
    </>
  );
}
