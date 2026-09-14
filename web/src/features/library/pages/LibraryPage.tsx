import { useEffect, useState } from "react";
import { Plus, Archive } from "lucide-react";
import { LIBRARY_KIND_LABELS, LIBRARY_KINDS } from "@/features/library/domain/catalog";
import type { LibraryEntry, LibraryEntryKind } from "@/features/library/types";
import { useLibraryStore } from "@/features/library/state/libraryStore";
import { useProfileStore } from "@/features/profile";
import { useToastStore } from "@/shared/state/uiStore";
import LibraryKindGroup from "../components/LibraryKindGroup";
import LibraryCreateModal from "../components/LibraryCreateModal";
import LibraryProfileCard from "../components/LibraryProfileCard";
import ConfirmModal from "@/shared/ui/ConfirmModal";
import { countByKind, selectByKind } from "../domain/librarySelectors";

export interface LibraryPageProps {
  initialKind?: string;
}

export default function LibraryPage({ initialKind }: LibraryPageProps) {

  const entries = useLibraryStore((s) => s.entries) ?? [];
  const isLoading = useLibraryStore((s) => s.isLoading);
  const loaded = useLibraryStore((s) => s.loaded);
  const error = useLibraryStore((s) => s.error);
  const fetchProfile = useProfileStore((s) => s.fetch);
  const profile = useProfileStore((s) => s.profile);
  const profileLoading = useProfileStore((s) => s.isLoading);
  const profileError = useProfileStore((s) => s.error);
  const updateProfile = useProfileStore((s) => s.update);
  const fetchAll = useLibraryStore((s) => s.fetchAll);
  const remove = useLibraryStore((s) => s.remove);
  const addToast = useToastStore((s) => s.addToast);

  const [createOpen, setCreateOpen] = useState(false);
  const [createKind, setCreateKind] = useState<LibraryEntryKind | undefined>();
  const [editTarget, setEditTarget] = useState<LibraryEntry | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<LibraryEntry | null>(null);
  const buckets = selectByKind(entries);
  const counts = countByKind(entries);
  const isEmpty = entries.length === 0;
  const closeEntryModal = () => {
    setCreateOpen(false);
    setCreateKind(undefined);
    setEditTarget(null);
  };

  const openCreateModal = (kind?: LibraryEntryKind) => {
    setCreateKind(kind);
    setCreateOpen(true);
  };

  useEffect(() => {
    fetchAll();
    fetchProfile();
  }, [fetchAll, fetchProfile]);

  const handleDelete = async (entry: LibraryEntry) => {
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
            onClick={() => openCreateModal()}
            className="inline-flex items-center gap-1 rounded-md border border-lib-rule bg-lib-surface px-3 py-2 text-sm font-medium text-lib-ink hover:bg-lib-surface-2"
          >
            <Plus className="h-4 w-4" />
            Add entry
          </button>
        </header>
        <LibraryProfileCard
          profile={profile}
          isLoading={profileLoading}
          error={profileError}
          onRetry={fetchProfile}
          onSave={updateProfile}
        />

        {error && !isLoading && (
          <div className="rounded-lg border border-lib-accent/40 bg-lib-surface p-5 text-sm text-lib-ink-2" role="alert">
            <p>{error}</p>
            <button type="button" onClick={fetchAll} className="mt-3 rounded-md border border-lib-rule px-3 py-1.5 font-medium hover:bg-lib-surface-2">
              Try again
            </button>
          </div>
        )}
        {!error && !loaded && isLoading && <p className="text-sm text-lib-ink-2">Loading…</p>}

        {!error && loaded && isEmpty ? (
          <div className="rounded-lg border-2 border-dashed border-lib-rule bg-lib-surface px-6 py-12 text-center">
            <Archive className="mx-auto mb-4 h-12 w-12 text-lib-ink-3" />
            <h2 className="text-lg font-semibold text-lib-ink">Your library is empty</h2>
            <p className="mt-1 text-sm text-lib-ink-2">
              Promote a CV&apos;s entries, or add your first one.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <a
                href="/cvs"
                className="inline-flex items-center rounded-md border border-lib-rule bg-lib-surface px-4 py-2 text-sm font-medium text-lib-ink hover:bg-lib-surface-2"
              >
                Open a CV to promote
              </a>
              <button
                type="button"
                onClick={() => openCreateModal()}
                className="inline-flex items-center rounded-md bg-lib-accent px-4 py-2 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover"
              >
                + Add entry
              </button>
            </div>
          </div>
        ) : !error && loaded ? (
          <div className="space-y-8">
            {LIBRARY_KINDS.map((kind) => (
              <LibraryKindGroup
                onEditEntry={(entry) => {
                  setEditTarget(entry);
                  setCreateOpen(false);
                  setCreateKind(undefined);
                }}
                key={kind}
                kind={kind}
                entries={buckets[kind]}
                onAdd={openCreateModal}
                onDeleteEntry={(entry) => setDeleteTarget(entry)}
                highlighted={initialKind === kind}
              />
            ))}
          </div>
        ) : null}
      </div>

      <ConfirmModal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget ? handleDelete(deleteTarget) : undefined}
        onError={() => addToast("Unable to delete this library entry", "error")}
        title="Delete library entry?"
        description={deleteTarget ? (
          <>Delete this <span className="font-medium text-app-ink">{LIBRARY_KIND_LABELS[deleteTarget.kind]}</span> entry from your library? This action cannot be undone.</>
        ) : null}
        confirmLabel="Delete entry"
      />
      <LibraryCreateModal
        open={createOpen || !!editTarget}
        onClose={closeEntryModal}
        initialKind={createKind}
        entry={editTarget}
        onSaved={(entry) => {
          addToast(`${editTarget ? "Updated" : "Added to"} ${LIBRARY_KIND_LABELS[entry.kind]}`, "success");
          setEditTarget(null);
        }}
      />
    </div>
  );
}
