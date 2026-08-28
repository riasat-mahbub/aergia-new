import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Library as LibraryIcon, ArrowRight } from "lucide-react";
import { useCVStore } from "../lib/store/cvStore";
import { useLibraryStore, countByKind } from "../lib/store/libraryStore";
import CvCard from "../components/cv-list/CvCard";
import CreateCvModal from "../components/cv-list/CreateCvModal";
import DeleteCvModal from "../components/cv-list/DeleteCvModal";
import ImportCvButton from "../components/cv-list/ImportCvButton";
import LoadingSkeleton from "../components/common/LoadingSkeleton";
import EmptyState from "../components/common/EmptyState";

export default function CvListPage() {
  const navigate = useNavigate();
  const { cvList, isLoading, fetchCVs, deleteCV, copyCV } = useCVStore();
  const libraryEntries = useLibraryStore((s) => s.entries) ?? [];
  const libraryLoaded = useLibraryStore((s) => s.loaded);
  const libraryFetch = useLibraryStore((s) => s.fetchAll);
  const [showCreate, setShowCreate] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  useEffect(() => {
    fetchCVs();
    if (!libraryLoaded) libraryFetch();
  }, [fetchCVs, libraryFetch, libraryLoaded]);

  const libraryCounts = countByKind(libraryEntries);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 flex items-center justify-between"
      >
        <h1 className="text-2xl font-bold text-gray-900">My CVs</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreate(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            + New CV
          </button>
          <ImportCvButton />
        </div>
      </motion.div>

      {/* Library card — separate from the CV grid so it doesn't compete
          visually. Sits above the CV grid for first-time discoverability. */}
      <Link
        to="/dashboard/library"
        className="mb-4 flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 shadow-sm hover:border-gray-300"
      >
        <div className="flex items-start gap-3">
          <div className="rounded-md bg-gray-100 p-2">
            <LibraryIcon className="h-5 w-5 text-gray-700" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-gray-900">Library</h2>
            <p className="text-xs text-gray-500">Your reusable content. Pull into any CV.</p>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
              {!libraryLoaded ? (
                <span>—</span>
              ) : (
                <>
                  <span>{libraryCounts.experience} experiences</span>
                  <span>{libraryCounts.education} education</span>
                  <span>{libraryCounts.skill} skills</span>
                  <span>{libraryCounts.project} projects</span>
                  <span>{libraryCounts.certification} certifications</span>
                  <span>{libraryCounts.language} languages</span>
                  <span>{libraryCounts.research} research</span>
                </>
              )}
            </div>
          </div>
        </div>
        <ArrowRight className="h-4 w-4 text-gray-400" />
      </Link>

      <CreateCvModal open={showCreate} onClose={() => setShowCreate(false)} />

      <DeleteCvModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteCV(deleteTarget.id)}
        cvTitle={deleteTarget?.title || ""}
      />

      {isLoading && <LoadingSkeleton count={6} />}

      {!isLoading && cvList.length === 0 && (
        <EmptyState
          title="No CVs yet"
          description="Create your first CV to get started."
          action={{ label: "+ New CV", onClick: () => setShowCreate(true) }}
        />
      )}

      {!isLoading && cvList.length > 0 && (
        <motion.div
          initial="hidden"
          animate="visible"
          variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {cvList.map((cv) => (
            <CvCard
              key={cv.id}
              cv={cv}
              onEdit={(id) => navigate(`/dashboard/builder/${id}`)}
              onCopy={(id) => copyCV(id)}
              onDelete={(id) => setDeleteTarget({ id, title: cv.title })}
            />
          ))}
        </motion.div>
      )}
    </div>
  );
}
