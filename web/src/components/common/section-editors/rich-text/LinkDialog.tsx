import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { safeLinkUrl } from "@/lib/security/safeUrl";

interface LinkDialogProps {
  initialUrl: string | null;
  initialText: string;
  onApply: (url: string, displayText: string) => void;
  onCancel: () => void;
  onRemove: (() => void) | null;
}

export default function LinkDialog({ initialUrl, initialText, onApply, onCancel, onRemove }: LinkDialogProps) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [displayText, setDisplayText] = useState(initialText);
  const [error, setError] = useState("");

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const safeUrl = safeLinkUrl(url);
    if (!safeUrl) {
      setError("Enter a safe http(s), mailto, or tel URL.");
      return;
    }
    if (!displayText.trim()) {
      setError("Enter display text for the link.");
      return;
    }
    onApply(safeUrl, displayText);
  };

  return (
    <div className="absolute left-2 top-full z-20 mt-1 w-[min(22rem,calc(100vw-2rem))] rounded border border-app-rule bg-app-surface p-3 shadow-lg" role="dialog" aria-modal="true" aria-labelledby="rich-text-link-title">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 id="rich-text-link-title" className="text-xs font-semibold text-app-ink">{initialUrl ? "Edit link" : "Add link"}</h2>
        <button type="button" onClick={onCancel} className="rounded p-1 text-app-ink-3 hover:bg-app-surface-muted focus-visible:ring-2 focus-visible:ring-app-primary-soft" aria-label="Close link dialog" title="Close">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-2">
        <label className="block text-[11px] font-medium text-app-ink-2">
          URL
          <input
            autoFocus
            value={url}
            onChange={(event) => { setUrl(event.target.value); setError(""); }}
            placeholder="https://example.com"
            inputMode="url"
            className="mt-0.5 w-full rounded border border-app-rule px-2 py-1.5 text-xs text-app-ink outline-none focus:border-app-primary focus:ring-2 focus:ring-app-primary-soft"
            aria-invalid={Boolean(error)}
          />
        </label>
        <label className="block text-[11px] font-medium text-app-ink-2">
          Display text
          <input
            value={displayText}
            onChange={(event) => { setDisplayText(event.target.value); setError(""); }}
            placeholder="Link label"
            className="mt-0.5 w-full rounded border border-app-rule px-2 py-1.5 text-xs text-app-ink outline-none focus:border-app-primary focus:ring-2 focus:ring-app-primary-soft"
          />
        </label>
        {error && <p className="text-[11px] text-app-danger" role="alert">{error}</p>}
        <div className="flex items-center justify-end gap-1.5 pt-1">
          {onRemove && <button type="button" onClick={onRemove} className="mr-auto rounded px-2 py-1 text-[11px] text-app-danger hover:bg-app-danger-soft focus-visible:ring-2 focus-visible:ring-app-primary-soft">Remove link</button>}
          <button type="button" onClick={onCancel} className="rounded border border-app-rule px-2 py-1 text-[11px] text-app-ink-2 hover:bg-app-surface-muted focus-visible:ring-2 focus-visible:ring-app-primary-soft">Cancel</button>
          <button type="submit" className="rounded bg-app-primary px-2 py-1 text-[11px] text-white hover:bg-app-primary-hover focus-visible:ring-2 focus-visible:ring-app-primary-soft">Save link</button>
        </div>
      </form>
    </div>
  );
}
