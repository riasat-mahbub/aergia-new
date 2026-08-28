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
 *  1. Keys are held in page memory only — never localStorage or
 *     sessionStorage.
 *  2. Inputs render as ``type="password"`` with provider-specific
 *     ``autoComplete`` so password managers don't cross-fill.
 *  3. A persistent (NOT toast) security warning sits at the top of the
 *     dialog so the user sees the trade-off every save.
 *
 * Controlled-input state for the mismatch warning. The parent uses
 * ``key={open ? 1 : 0}`` (a small wrapper component) to remount the
 * tree on every open, seeding the buffer from the in-memory store.
 */
export default function LLMKeyDialog({ open, onClose }: Props) {
  return open ? (
    <LLMKeyDialogBody onClose={onClose} />
  ) : null;
}

function LLMKeyDialogBody({ onClose }: { onClose: () => void }) {
  const addToast = useToastStore((s) => s.addToast);
  const [values, setValues] = useState<LLMKeyMap>(() => loadKeys());

  const handleClose = () => {
    forgetAllKeys();
    setValues({});
    onClose();
  };

  const handleSave = (e: FormEvent) => {
    e.preventDefault();
    saveKeys(values);
    const savedProviders = Object.keys(values).filter(
      (k) => typeof values[k as LLMProviderKey] === "string"
        && (values[k as LLMProviderKey] ?? "").trim().length > 0
    );
    if (savedProviders.length === 0) {
      addToast("API keys cleared from memory.", "info");
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
    addToast("API keys cleared from memory.", "info");
  };

  const handleForgetOne = (provider: LLMProviderKey) => {
    const next = forgetKey(provider);
    setValues(next);
  };

  return (
    <Modal open onClose={handleClose}>
      <form onSubmit={handleSave} className="space-y-4">
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold text-app-ink">LLM API keys</h2>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close"
            className="rounded p-1 text-app-ink-3 hover:bg-app-surface-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="rounded border border-app-warning bg-app-warning-soft px-3 py-2 text-xs text-app-warning">
          Your API keys are stored only in memory and sent directly to the
          provider during the next import. They are NOT saved to browser
          storage or to any server.
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
                  className="block text-sm font-medium text-app-ink-2"
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
                    className="flex-1 rounded border border-app-rule-strong px-2 py-1.5 text-sm focus:border-app-primary focus:outline-none"
                  />
                  {current ? (
                    <button
                      type="button"
                      onClick={() => handleForgetOne(provider)}
                      className="flex items-center gap-1 rounded border border-app-rule-strong px-2 py-1 text-xs text-app-ink-2 hover:bg-app-surface-muted"
                      title={`Forget ${PROVIDER_LABEL[provider]} key`}
                    >
                      <Trash2 className="h-3 w-3" />
                      Forget
                    </button>
                  ) : null}
                </div>
                {mismatch ? (
                  <p className="text-xs text-app-warning">
                    Looks like a {PROVIDER_LABEL[mismatch]} key. Move it to
                    that slot?
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-app-rule pt-3">
          <button
            type="button"
            onClick={handleForgetAll}
            className="flex items-center gap-1 rounded border border-app-danger px-3 py-1.5 text-xs text-app-danger hover:bg-app-danger-soft"
          >
            <Trash2 className="h-3 w-3" />
            Forget all keys
          </button>
          <button
            type="button"
            onClick={handleClose}
            className="rounded border border-app-rule-strong px-3 py-1.5 text-xs text-app-ink-2 hover:bg-app-surface-muted"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex items-center gap-1 rounded bg-app-primary px-3 py-1.5 text-xs text-white hover:bg-app-primary-hover"
          >
            <Save className="h-3 w-3" />
            Save
          </button>
        </div>
      </form>
    </Modal>
  );
}
