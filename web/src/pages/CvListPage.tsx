import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCVStore } from "../lib/store/cvStore";
import CvCard from "../components/cv-list/CvCard";
import CreateCvModal from "../components/cv-list/CreateCvModal";
import DeleteCvModal from "../components/cv-list/DeleteCvModal";
import ImportCvButton from "../components/cv-list/ImportCvButton";
import LoadingSkeleton from "../components/common/LoadingSkeleton";
import EmptyState from "../components/common/EmptyState";
import { motion } from "motion/react";

export default function CvListPage() {
  const navigate = useNavigate();
  const { cvList, isLoading, fetchCVs, deleteCV, copyCV } = useCVStore();
  const [showCreate, setShowCreate] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  useEffect(() => {
    fetchCVs();
  }, [fetchCVs]);

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
