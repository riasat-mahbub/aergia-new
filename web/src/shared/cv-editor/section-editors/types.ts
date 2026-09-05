import type { ReactNode } from "react";

export type SectionEditorMode = "section" | "library";

/**
 * Optional host-provided UI capabilities for entry editors.
 *
 * The editor layer deliberately knows nothing about the Library domain. A
 * builder can inject Library actions, while a library draft or another host
 * can omit them or provide a different implementation.
 */
export interface SectionEditorActions {
  renderEntryAction?: (args: {
    kind: string;
    entryId: string;
    entry: Record<string, unknown>;
    entryLabel?: string;
  }) => ReactNode;
  renderAddAction?: (args: {
    kind: string;
    onPick: (picked: Record<string, unknown> | null) => void;
  }) => ReactNode;
}

export function renderEntryActionFor<T extends { id: string }>(
  actions: SectionEditorActions | undefined,
  kind: string,
  entry: T,
  entryLabel?: string,
): ReactNode {
  return actions?.renderEntryAction?.({
    kind,
    entryId: entry.id,
    entry: entry as unknown as Record<string, unknown>,
    entryLabel,
  });
}
