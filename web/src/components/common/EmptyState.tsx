import { motion } from "motion/react";
import { FileText } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({
  title = "Nothing here yet",
  description = "Get started by creating your first item.",
  action,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center"
    >
      <FileText className="mx-auto mb-4 h-12 w-12 text-gray-300" />
      <h3 className="text-lg font-medium text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-500">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
        >
          {action.label}
        </button>
      )}
    </motion.div>
  );
}
