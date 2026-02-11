import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../lib/store/authStore";
import { useCVStore } from "../lib/store/cvStore";
import CvCard from "../components/cv-list/CvCard";

export default function CvListPage() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const { cvList, isLoading, fetchCVs, createCV, deleteCV, copyCV } = useCVStore();
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  useEffect(() => {
    fetchCVs();
  }, [fetchCVs]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    await createCV(newTitle.trim());
    setNewTitle("");
    setShowCreate(false);
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">My CVs</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCreate(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            + New CV
          </button>
          <button
            onClick={async () => { await logout(); navigate("/login"); }}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Logout
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="CV title..."
            className="w-full rounded-md border border-gray-300 px-3 py-2"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <div className="mt-2 flex gap-2">
            <button onClick={handleCreate} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white">
              Create
            </button>
            <button onClick={() => setShowCreate(false)} className="rounded border px-3 py-1.5 text-sm text-gray-600">
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading && <p className="text-gray-500">Loading...</p>}

      {!isLoading && cvList.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No CVs yet. Create your first one!</p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {cvList.map((cv) => (
          <CvCard
            key={cv.id}
            cv={cv}
            onEdit={(id) => navigate(`/builder/${id}`)}
            onCopy={(id) => copyCV(id)}
            onDelete={(id) => {
              if (confirm("Delete this CV?")) deleteCV(id);
            }}
          />
        ))}
      </div>
    </div>
  );
}
