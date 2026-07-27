import { useState, type FormEvent } from "react";
import { Save, Trash2, X } from "lucide-react";

import Modal from "../common/Modal";
import { useToastStore } from "../../lib/store/uiStore";
import {
  PROVIDER_AUTOCOMPLETE,
  PROVIDER_PREFIXES,
  detectProviderShape,
  forgetAllKeys,
  forgetKey,
  loadKeys,
  saveKeys,
  type LLMKeyMap,
  type LLMProviderKey,
} from "../../lib/llm/keys";

interface Props {
  open: boolean;
  onClose: () => void;
}

const PROVIDER_LABEL: Record<LLMProviderKey, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  groq: "Groq",
};

const PROVIDERS: LLMProviderKey[] = ["openai", "anthropic", "gemini", "groq"];

/**
 * Settings dialog for per-provider LLM API keys.
 *
 * Three rules baked in:
 *
 *  1. Keys are stored in sessionStorage only — never localStorage, never
 *     a module cache. Tab-scoped lifetime.
 *  2. Inputs render as ``type="password"`` with provider-specific
 *     ``autoComplete`` so password managers don't cross-fill.
 *  3. A persistent (NOT toast) security warning sits at the top of the
 *     dialog so the user sees the trade-off every save.
 *
 * Controlled-input state for the mismatch warning. The parent uses
 * ``key={open ? 1 : 0}`` (a small wrapper component) to remount the
 * tree on every open, seeding the buffer from sessionStorage.
 */
export default function LLMKeyDialog({ open, onClose }: Props) {
  return open ? (
    <LLMKeyDialogBody onClose={onClose} />
  ) : null;
}

function LLMKeyDialogBody({ onClose }: { onClose: () => void }) {
  const addToast = useToastStore((s) => s.addToast);
  const [values, setValues] = useState<LLMKeyMap>(() => loadKeys());

  const handleSave = (e: FormEvent) => {
    e.preventDefault();
    saveKeys(values);
    const savedProviders = Object.keys(values).filter(
      (k) => typeof values[k as LLMProviderKey] === "string"
        && (values[k as LLMProviderKey] ?? "").trim().length > 0
    );
    if (savedProviders.length === 0) {
      addToast("API keys cleared from this browser tab.", "info");
    } else {
      const labels = savedProviders
        .map((p) => PROVIDER_LABEL[p as LLMProviderKey])
        .join(", ");
      addToast(`Saved API keys for: ${labels}`, "success");
    }
    onClose();
  };

  const handleForgetAll = () => {
    forgetAllKeys();
    setValues({});
    addToast("API keys cleared from this browser tab.", "info");
  };

  const handleForgetOne = (provider: LLMProviderKey) => {
    const next = forgetKey(provider);
    setValues(next);
  };

  return (
    <Modal open onClose={onClose}>
      <form onSubmit={handleSave} className="space-y-4">
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold text-gray-900">LLM API keys</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-gray-500 hover:bg-gray-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Your API keys are stored only in this browser tab&rsquo;s
          sessionStorage and sent directly to the provider each import.
          They are NOT saved across sessions or to any server.
        </p>

        <div className="space-y-3">
          {PROVIDERS.map((provider) => {
            const current = values[provider] ?? "";
            const detected = detectProviderShape(current);
            const mismatch =
              detected !== null && detected !== provider ? detected : null;
            return (
              <div key={provider} className="space-y-1">
                <label
                  htmlFor={`key-${provider}`}
                  className="block text-sm font-medium text-gray-700"
                >
                  {PROVIDER_LABEL[provider]}
                </label>
                <div className="flex items-center gap-2">
                  <input
                    id={`key-${provider}`}
                    name={`key-${provider}`}
                    type="password"
                    autoComplete={PROVIDER_AUTOCOMPLETE[provider]}
                    spellCheck={false}
                    autoCorrect="off"
                    placeholder={PROVIDER_PREFIXES[provider] + "…"}
                    value={current}
                    onChange={(e) =>
                      setValues((prev) => ({
                        ...prev,
                        [provider]: e.target.value,
                      }))
                    }
                    className="flex-1 rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                  />
                  {current ? (
                    <button
                      type="button"
                      onClick={() => handleForgetOne(provider)}
                      className="flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
                      title={`Forget ${PROVIDER_LABEL[provider]} key`}
                    >
                      <Trash2 className="h-3 w-3" />
                      Forget
                    </button>
                  ) : null}
                </div>
                {mismatch ? (
                  <p className="text-xs text-amber-700">
                    Looks like a {PROVIDER_LABEL[mismatch]} key. Move it to
                    that slot?
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-gray-200 pt-3">
          <button
            type="button"
            onClick={handleForgetAll}
            className="flex items-center gap-1 rounded border border-red-300 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50"
          >
            <Trash2 className="h-3 w-3" />
            Forget all keys
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700"
          >
            <Save className="h-3 w-3" />
            Save
          </button>
        </div>
      </form>
    </Modal>
  );
}
