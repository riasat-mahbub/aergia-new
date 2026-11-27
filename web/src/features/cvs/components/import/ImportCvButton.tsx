import { useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { FileUp } from "lucide-react";

import ImportCvModal from "./ImportCvModal";
import { importPDF } from "../../api/imports";
import { useToastStore } from "@/shared/state/uiStore";
import { useCVListStore } from "@/features/cvs/state/cvListStore";
import type { LLMProviderKey } from "@/features/llm-credentials";
import { PROVIDER_LABELS, pickActiveProvider } from "@/features/llm-credentials";
import { forgetAllKeys, loadKeys, useLLMKeys } from "@/features/llm-credentials";

/**
 * Header control for importing a PDF. API-key configuration lives in the
 * account Settings page so import actions and account settings do not compete
 * for the same visual control.
 *
 * Label is `Import CV · <Provider>` when a key is held in memory
 * (live via `useLLMKeys`). Clicking the button opens
 * the modal; the modal's `onSubmit` runs the import → create →
 * navigate pipeline.
 */
export default function ImportCvButton() {
  const navigate = useNavigate();
  const addToast = useToastStore((s) => s.addToast);
  const createCV = useCVListStore((s) => s.createCV);
  const keys = useLLMKeys();

  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);

  const activeProvider = pickActiveProvider(keys);
  const label = activeProvider
    ? `Import CV · ${PROVIDER_LABELS[activeProvider]}`
    : "Import CV";

  const handleSubmit = async (input: {
    title: string;
    templateId: string;
    file: File;
  }) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      const importKeys = loadKeys();
      const provider: LLMProviderKey | null = pickActiveProvider(importKeys);
      const apiKey = provider ? importKeys[provider] : undefined;
      const parsed = await importPDF(
        input.file,
        provider && apiKey ? { provider, apiKey } : undefined,
      );
      const cv = await createCV(
        input.title,
        input.templateId,
        parsed.sections
      );
      setOpen(false);
      navigate({ to: "/builder/$id", params: { id: cv.id } });
    } catch {
      addToast("Failed to import CV", "error");
      // Modal stays open so the user can retry without losing their
      // typed title or chosen file.
    } finally {
      forgetAllKeys();
      busyRef.current = false;
      setBusy(false);
    }
  };

  return (
    <div className="inline-flex items-center gap-2">
      <button
        onClick={() => {
          if (!busyRef.current) setOpen(true);
        }}
        disabled={busy}
        className="flex items-center gap-1.5 rounded-md border border-app-primary bg-app-surface px-3 py-2 text-sm text-app-primary hover:bg-app-primary-soft disabled:opacity-50"
        title="Import a PDF and create a new CV from it"
        type="button"
      >
        <FileUp className="h-4 w-4" />
        {label}
      </button>
      <ImportCvModal
        open={open}
        busy={busy}
        onClose={() => {
          if (busyRef.current) return;
          forgetAllKeys();
          setOpen(false);
        }}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
