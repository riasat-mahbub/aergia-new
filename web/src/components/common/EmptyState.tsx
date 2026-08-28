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
      className="rounded-lg border-2 border-dashed border-app-rule-strong p-12 text-center"
    >
      <FileText className="mx-auto mb-4 h-12 w-12 text-app-ink-muted" />
      <h3 className="text-lg font-medium text-app-ink">{title}</h3>
      <p className="mt-1 text-sm text-app-ink-3">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 rounded-md bg-app-primary px-4 py-2 text-sm text-white hover:bg-app-primary-hover"
        >
          {action.label}
        </button>
      )}
    </motion.div>
  );
}
