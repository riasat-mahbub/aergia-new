import { useState } from "react";
import type { ReactNode } from "react";
import { FONT_TOKEN_LABELS, FONT_TOKENS, ink, ruleDefault } from "@/styles/tokens";

export function Group({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  // The open state is intentionally local to each group so opening one group
  // does not expand the entire inspector.
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="rounded" style={{ border: `1px solid ${ruleDefault}` }}>
      <button
        type="button"
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide"
        style={{ color: ink.ink3 }}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {title}<span aria-hidden>{open ? "▾" : "▸"}</span>
      </button>
      {open && <div className="space-y-2 border-t p-3" style={{ borderColor: ruleDefault }}>{children}</div>}
    </section>
  );
}

export function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-32 text-xs" style={{ color: ink.ink3 }}>{label}</span>
      <div>{children}</div>
    </div>
  );
}

export function FontSelect({
  value,
  inherited,
  onChange,
  ariaLabel,
}: {
  value: string;
  inherited: string | null;
  onChange: (value: string) => void;
  ariaLabel: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded border px-2 py-1 text-xs"
      style={{ borderColor: ruleDefault }}
      aria-label={ariaLabel}
    >
      <option value="">Inherited ({inherited ? FONT_TOKEN_LABELS[inherited as keyof typeof FONT_TOKEN_LABELS] ?? inherited : "default"})</option>
      {FONT_TOKENS.map((tok) => <option key={tok} value={tok}>{FONT_TOKEN_LABELS[tok]}</option>)}
    </select>
  );
}
