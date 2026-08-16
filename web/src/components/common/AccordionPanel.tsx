import { useState, type ReactNode } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown } from "lucide-react";

interface Props {
  title: ReactNode;
  defaultOpen?: boolean;
  onRemove?: () => void;
  /**
   * Optional secondary actions rendered to the left of Remove in the
   * header. Each entry is a node (button, link, badge) — typically a
   * callback button triggered with `entry` context from the parent.
   */
  actions?: ReactNode;
  children: ReactNode;
}

export default function AccordionPanel({
  title,
  defaultOpen = false,
  onRemove,
  actions,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-app-rule bg-app-surface">
      <div
        className="flex cursor-pointer items-center gap-2 px-3 py-2.5 select-none"
        onClick={() => setOpen(!open)}
      >
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="h-4 w-4 text-app-ink-3" />
        </motion.div>
        <span className="flex-1 text-sm font-medium text-app-ink-2 truncate">
          {title ?? "Untitled"}
        </span>
        {actions && (
          <span
            className="flex items-center gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            {actions}
          </span>
        )}
        {onRemove && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="text-xs font-medium text-app-danger hover:text-app-danger"
          >
            Remove
          </button>
        )}
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="overflow-hidden"
          >
            <div className="border-t border-app-rule-soft px-3 py-3">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
