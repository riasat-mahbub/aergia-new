import { useState } from "react";
import { motion } from "motion/react";
import { Archive } from "lucide-react";
import { promoteCvToLibrary } from "../../lib/api/library";
import { useToastStore } from "../../lib/store/uiStore";
import { useLibraryStore } from "../../lib/store/libraryStore";

interface PromoteToLibraryButtonProps {
  cvId: string;
  /** Optional label override; defaults to "Promote to library". */
  label?: string;
}

function formatPromoted(promoted: Record<string, number>): string {
  const entries = Object.entries(promoted).filter(([, n]) => n > 0);
  if (entries.length === 0) return "no new entries";
  return entries
    .map(([kind, n]) => `${n} ${kind}${n === 1 ? "" : "s"}`)
    .join(", ");
}

export default function PromoteToLibraryButton({
  cvId,
  label = "Promote to library",
}: PromoteToLibraryButtonProps) {
  const [busy, setBusy] = useState(false);
  const addToast = useToastStore((s) => s.addToast);
  const fetchAll = useLibraryStore((s) => s.fetchAll);

  const handleClick = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const resp = await promoteCvToLibrary(cvId);
      const total = Object.values(resp.promoted).reduce((a, b) => a + b, 0);
      if (total === 0) {
        addToast(
          resp.skipped.length > 0
            ? `No new entries (${resp.skipped.length} section${resp.skipped.length === 1 ? "" : "s"} skipped — not library-eligible)`
            : "All entries already in your library",
          "info",
        );
      } else {
        addToast(`Added ${formatPromoted(resp.promoted)} to your Library.`, "success");
      }
      await fetchAll();
    } catch {
      addToast("Unable to promote this CV to the Library", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.button
      type="button"
      onClick={handleClick}
      disabled={busy}
      whileTap={{ scale: 0.97 }}
      className="inline-flex items-center gap-1.5 rounded-md border border-lib-rule bg-lib-surface px-3 py-1.5 text-xs font-medium text-lib-ink-2 hover:bg-lib-surface-2 disabled:opacity-50"
    >
      <Archive className="h-3.5 w-3.5" />
      <span>{busy ? "Promoting…" : label}</span>
    </motion.button>
  );
}
