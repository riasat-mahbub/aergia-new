import { useState } from "react";
import { Pencil } from "lucide-react";
import Modal from "../common/Modal";
import SectionEditorPanel from "../sections/SectionEditorPanel";
import type { SectionInstance } from "../../lib/sections/types";
import type { UserProfile } from "../../lib/api/profile";

interface ProfileCardProps {
  profile: UserProfile | null;
  isLoading?: boolean;
  onSave: (profile: UserProfile) => Promise<UserProfile>;
  eyebrow?: string;
  description?: string;
  testId?: string;
  editorTestId?: string;
  surfaceClassName?: string;
  modalTitle?: string;
  modalDescription?: string;
}

export default function ProfileCard({
  profile,
  isLoading = false,
  onSave,
  eyebrow = "Profile",
  description = "Shared contact details for your CVs",
  testId = "profile-card",
  editorTestId = "profile-editor",
  surfaceClassName = "mb-6 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm",
  modalTitle = "Edit Profile",
  modalDescription = "These details are reused across your CVs.",
}: ProfileCardProps) {
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
        id: "profile_editor",
        type: "profile",
        title: "Profile",
        enabled: true,
        data: draft as unknown as Record<string, unknown>,
        style: null,
      }
    : null;

  return (
    <>
      <section className={surfaceClassName} data-testid={testId}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-app-primary">{eyebrow}</p>
            {isLoading ? (
              <p className="mt-2 text-sm text-app-ink-2">Loading profile…</p>
            ) : (
              <>
                <h2 className="mt-1 text-xl font-semibold text-app-ink">
                  {profile?.name || "Complete your profile"}
                </h2>
                <p className="mt-1 text-sm text-app-ink-2">{profile?.title || description}</p>
                {profile?.email && <p className="mt-3 text-sm text-app-ink-2">{profile.email}</p>}
              </>
            )}
          </div>
          <button
            type="button"
            onClick={handleOpen}
            disabled={!profile || isLoading}
            className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong bg-app-surface px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Pencil className="h-4 w-4" />
            Edit
          </button>
        </div>
        <p className="mt-4 text-xs text-app-ink-3">{description}</p>
      </section>

      <Modal open={open} onClose={() => !saving && setOpen(false)} size="wide">
        <div data-testid={editorTestId} className="max-h-[80vh] w-full min-w-0 overflow-y-auto">
          <header className="mb-4">
            <h2 className="text-xl font-semibold text-app-ink">{modalTitle}</h2>
            <p className="mt-1 text-sm text-app-ink-2">{modalDescription}</p>
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
              className="rounded-md px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !draft}
              className="rounded-md bg-app-ink px-4 py-2 text-sm font-medium text-white hover:bg-app-surface-muted disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save profile"}
            </button>
          </footer>
        </div>
      </Modal>
    </>
  );
}
