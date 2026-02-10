import type { CVListItem } from "../../lib/api/cvs";

interface CvCardProps {
  cv: CVListItem;
  onEdit: (id: string) => void;
  onCopy: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function CvCard({ cv, onEdit, onCopy, onDelete }: CvCardProps) {
  const templateLabel = cv.template_id.replace("generic-", "").replace("-", " ");
  const date = new Date(cv.updated_at).toLocaleDateString();

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">{cv.title}</h3>
          <p className="mt-1 text-sm text-gray-500 capitalize">{templateLabel}</p>
          <p className="mt-1 text-xs text-gray-400">Updated {date}</p>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => onEdit(cv.id)}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          Edit
        </button>
        <button
          onClick={() => onCopy(cv.id)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          Copy
        </button>
        <button
          onClick={() => onDelete(cv.id)}
          className="rounded border border-red-300 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
