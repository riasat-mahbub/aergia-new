import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileUp, Loader2, Settings } from "lucide-react";

import LLMKeyDialog from "../builder/LLMKeyDialog";
import ImportCvModal from "./ImportCvModal";
import { importPDF } from "../../lib/api/imports";
import { useToastStore } from "../../lib/store/uiStore";
import { useCVStore } from "../../lib/store/cvStore";
import {
  forgetAllKeys,
  useLLMKeys,
  pickActiveProvider,
  type LLMProviderKey,
} from "../../lib/llm/keys";

const PROVIDER_DISPLAY_NAME: Record<LLMProviderKey, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  groq: "Groq",
};

/**
 * Header cluster: `Import CV` button + settings cog + LLM key dialog +
 * the pre-file modal.
 *
 * Label is `Import CV · <Provider>` when a key is held in memory
 * (live via `useLLMKeys`). Clicking the button opens
 * the modal; the modal's `onSubmit` runs the import → create →
 * navigate pipeline.
 */
export default function ImportCvButton() {
  const navigate = useNavigate();
  const addToast = useToastStore((s) => s.addToast);
  const createCV = useCVStore((s) => s.createCV);
  const keys = useLLMKeys();

  const [open, setOpen] = useState(false);
  const [showKeys, setShowKeys] = useState(false);
  const [busy, setBusy] = useState(false);

  const activeProvider = pickActiveProvider(keys);
  const label = activeProvider
    ? `Import CV · ${PROVIDER_DISPLAY_NAME[activeProvider]}`
    : "Import CV";

  const handleSubmit = async (input: {
    title: string;
    templateId: string;
    file: File;
  }) => {
    setBusy(true);
    try {
      const parsed = await importPDF(input.file);
      const cv = await createCV(
        input.title,
        input.templateId,
        parsed.sections
      );
      setOpen(false);
      navigate(`/dashboard/builder/${cv.id}`);
    } catch {
      addToast("Failed to import CV", "error");
      // Modal stays open so the user can retry without losing their
      // typed title or chosen file.
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inline-flex items-center gap-2">
      <button
        onClick={() => setOpen(true)}
        disabled={busy}
        className="flex items-center gap-1.5 rounded-md border border-blue-600 bg-white px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 disabled:opacity-50"
        title="Import a PDF and create a new CV from it"
        type="button"
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <FileUp className="h-4 w-4" />
        )}
        {busy ? "Importing..." : label}
      </button>
      <button
        onClick={() => setShowKeys(true)}
        className="flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-2 text-sm text-gray-700 hover:bg-gray-50"
        title="Configure LLM API keys"
        aria-label="Configure LLM API keys"
        type="button"
      >
        <Settings className="h-4 w-4" />
      </button>
      <ImportCvModal
        open={open}
        onClose={() => {
          if (!busy) {
            forgetAllKeys();
            setOpen(false);
          }
        }}
        onSubmit={handleSubmit}
      />
      <LLMKeyDialog
        open={showKeys}
        onClose={() => setShowKeys(false)}
      />
    </div>
  );
}
