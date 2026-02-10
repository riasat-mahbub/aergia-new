import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useCVStore } from "../lib/store/cvStore";

export default function BuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading } = useCVStore();

  useEffect(() => {
    if (id) loadCV(id);
  }, [id, loadCV]);

  if (isLoading || !currentCV) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">{isLoading ? "Loading CV..." : "CV not found"}</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b bg-white px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            &larr; Back
          </button>
          <h1 className="text-lg font-semibold text-gray-900">{currentCV.title}</h1>
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 capitalize">
            {currentCV.template_id.replace("generic-", "")}
          </span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-1/2 overflow-y-auto border-r bg-white p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Editor</h2>
          <p className="text-gray-400 text-sm">Section editors will appear here (Phase 3).</p>
        </div>

        <div className="w-1/2 overflow-y-auto bg-gray-100 p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Preview</h2>
          <div className="mx-auto max-w-[210mm] rounded bg-white p-8 shadow-sm">
            <p className="text-gray-400 text-sm">CV preview will render here (Phase 3).</p>
          </div>
        </div>
      </div>
    </div>
  );
}
