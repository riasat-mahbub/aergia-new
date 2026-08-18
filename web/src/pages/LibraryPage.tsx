import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, Archive } from "lucide-react";
import {
  LIBRARY_KIND_LABELS,
  LIBRARY_KINDS,
  type LibraryEntry,
  type LibraryEntryKind,
} from "../lib/api/library";
import { useLibraryStore, selectByKind, countByKind } from "../lib/store/libraryStore";
import { useProfileStore } from "../lib/store/profileStore";
import { useToastStore } from "../lib/store/uiStore";
import LibraryKindGroup from "../components/library/LibraryKindGroup";
import LibraryCreateModal from "../components/library/LibraryCreateModal";
import LibraryProfileCard from "../components/library/LibraryProfileCard";

export default function LibraryPage() {
  const [searchParams] = useSearchParams();
  const initialKind = searchParams.get("kind") as LibraryEntryKind | null;

  const entries = useLibraryStore((s) => s.entries) ?? [];
  const isLoading = useLibraryStore((s) => s.isLoading);
  const loaded = useLibraryStore((s) => s.loaded);
  const fetchProfile = useProfileStore((s) => s.fetch);
  const profile = useProfileStore((s) => s.profile);
  const profileLoading = useProfileStore((s) => s.isLoading);
  const updateProfile = useProfileStore((s) => s.update);
  const fetchAll = useLibraryStore((s) => s.fetchAll);
  const remove = useLibraryStore((s) => s.remove);
  const addToast = useToastStore((s) => s.addToast);

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<LibraryEntry | null>(null);
  const buckets = selectByKind(entries);
  const counts = countByKind(entries);
  const isEmpty = entries.length === 0;
  const closeEntryModal = () => {
    setCreateOpen(false);
    setEditTarget(null);
  };

  useEffect(() => {
    fetchAll();
    fetchProfile();
  }, [fetchAll, fetchProfile]);

  const handleDelete = async (entry: LibraryEntry) => {
    if (!confirm(`Delete "${LIBRARY_KIND_LABELS[entry.kind]}" entry from library?`)) return;
    await remove(entry.id);
    addToast("Library entry deleted", "info");
  };

  return (
    <div className="min-h-screen bg-lib-canvas text-lib-ink">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-lib-ink">Library</h1>
            <p className="mt-1 text-sm text-lib-ink-2">
              Your reusable content. Pull into any CV.
            </p>
            <p className="mt-2 text-xs font-medium uppercase tracking-wider text-lib-ink-3">
              {LIBRARY_KINDS.map((k) => `${counts[k]} ${LIBRARY_KIND_LABELS[k].toLowerCase()}`).join(" · ")}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-1 rounded-md border border-lib-rule bg-lib-surface px-3 py-2 text-sm font-medium text-lib-ink hover:bg-lib-surface-2"
          >
            <Plus className="h-4 w-4" />
            Add entry
          </button>
        </header>
        <LibraryProfileCard profile={profile} isLoading={profileLoading} onSave={updateProfile} />

        {!loaded && isLoading && <p className="text-sm text-lib-ink-2">Loading…</p>}

        {loaded && isEmpty ? (
          <div className="rounded-lg border-2 border-dashed border-lib-rule bg-lib-surface px-6 py-12 text-center">
            <Archive className="mx-auto mb-4 h-12 w-12 text-lib-ink-3" />
            <h2 className="text-lg font-semibold text-lib-ink">Your library is empty</h2>
            <p className="mt-1 text-sm text-lib-ink-2">
              Promote a CV&apos;s entries, or add your first one.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <a
                href="/dashboard/cvs"
                className="inline-flex items-center rounded-md border border-lib-rule bg-lib-surface px-4 py-2 text-sm font-medium text-lib-ink hover:bg-lib-surface-2"
              >
                Open a CV to promote
              </a>
              <button
                type="button"
                onClick={() => setCreateOpen(true)}
                className="inline-flex items-center rounded-md bg-lib-accent px-4 py-2 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover"
              >
                + Add entry
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {LIBRARY_KINDS.map((kind) => (
              <LibraryKindGroup
                onEditEntry={(entry) => {
                  setEditTarget(entry);
                  setCreateOpen(false);
                }}
                key={kind}
                kind={kind}
                entries={buckets[kind]}
                onAdd={() => setCreateOpen(true)}
                onDeleteEntry={handleDelete}
                highlighted={initialKind === kind}
              />
            ))}
          </div>
        )}
      </div>

      <LibraryCreateModal
        open={createOpen || !!editTarget}
        onClose={closeEntryModal}
        entry={editTarget}
        onSaved={(entry) => {
          addToast(`${editTarget ? "Updated" : "Added to"} ${LIBRARY_KIND_LABELS[entry.kind]}`, "success");
          setEditTarget(null);
        }}
      />
    </div>
  );
}
