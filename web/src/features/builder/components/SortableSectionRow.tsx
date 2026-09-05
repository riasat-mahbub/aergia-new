import { useRef } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { AnimatePresence, motion } from "motion/react";
import {
  GripVertical,
  ChevronDown,
  Eye,
  EyeOff,
  Pencil,
  Check,
  Trash2,
} from "lucide-react";

import type { SectionInstance } from "@/shared/cv/schema";
import { SECTION_LABELS } from "@/shared/cv/sectionCatalog";
import { isLibraryKind } from "@/features/library";
import AddFromLibraryButton from "./library/AddFromLibraryButton";
import AddToLibraryButton from "./library/AddToLibraryButton";
import SectionEditorPanel from "@/shared/cv-editor/section-editors/SectionEditorPanel";
import type { SectionEditorActions } from "@/shared/cv-editor/section-editors/types";

export interface SortableSectionRowProps {
  instance: SectionInstance;
  isExpanded: boolean;
  editingTitle: string | null;
  onToggle: (id: string) => void;
  onUpdateData: (id: string, data: unknown) => void;
  onRenameInstance: (id: string, title: string) => void;
  setEditingTitle: (id: string | null) => void;
  onRemoveInstance: (id: string) => void;
  onToggleExpand: (id: string) => void;
  cvId?: string;
}

export default function SortableSectionRow({
  instance,
  isExpanded,
  editingTitle,
  onToggle,
  onUpdateData,
  onRenameInstance,
  setEditingTitle,
  onRemoveInstance,
  onToggleExpand,
  cvId,
}: SortableSectionRowProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: instance.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const commitRename = () => {
    const next = inputRef.current?.value.trim() ?? "";
    if (next) onRenameInstance(instance.id, next);
    setEditingTitle(null);
  };

  const editorActions: SectionEditorActions | undefined = cvId
    ? {
        renderEntryAction: ({ kind, entryId, entry, entryLabel }) => {
          if (!isLibraryKind(kind)) return null;
          return (
            <AddToLibraryButton
              cvId={cvId}
              sectionId={instance.id}
              entryId={entryId}
              kind={kind}
              entryData={entry}
              entryLabel={entryLabel}
            />
          );
        },
        renderAddAction: ({ kind, onPick }) =>
          isLibraryKind(kind) ? <AddFromLibraryButton kind={kind} onPick={onPick} /> : null,
      }
    : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded border bg-app-surface ${instance.enabled ? "border-app-rule" : "border-dashed border-app-rule-strong bg-app-canvas"}`}
      data-section-id={instance.id}
    >
      <div
        className="flex cursor-pointer items-center gap-2 px-3 py-2"
        role="button"
        aria-expanded={isExpanded}
        onClick={() => onToggleExpand(instance.id)}
      >
        <button
          {...attributes}
          {...listeners}
          onClick={(event) => event.stopPropagation()}
          className="cursor-grab text-app-ink-3 hover:text-app-ink"
          title="Drag to reorder"
        >
          <GripVertical className="h-3.5 w-3.5" />
        </button>

        <div className="min-w-0 flex-1">
          {editingTitle === instance.id ? (
            <div className="flex items-center gap-1">
              <input
                ref={inputRef}
                type="text"
                defaultValue={instance.title}
                autoFocus
                className="w-full rounded border border-app-primary-soft px-1.5 py-0.5 text-sm font-medium text-app-ink"
                onBlur={commitRename}
                onKeyDown={(event) => {
                  if (event.key === "Enter") commitRename();
                }}
                onClick={(event) => event.stopPropagation()}
              />
              <button
                className="rounded bg-app-primary px-2 py-0.5 text-xs text-white"
                onClick={(event) => {
                  event.stopPropagation();
                  commitRename();
                }}
              >
                <Check className="h-3 w-3" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span
                className={`text-sm font-medium ${instance.enabled ? "text-app-ink" : "text-app-ink-3"}`}
              >
                {instance.title}
              </span>
              <span className="text-[10px] text-app-ink-3">
                {SECTION_LABELS[instance.type] || instance.type}
              </span>
            </div>
          )}
        </div>

        <button
          onClick={(event) => {
            event.stopPropagation();
            onToggle(instance.id);
          }}
          className={`rounded p-1 ${
            instance.enabled
              ? "text-app-primary hover:text-app-primary"
              : "text-app-ink-3 hover:text-app-ink"
          }`}
          title={instance.enabled ? "Disable" : "Enable"}
        >
          {instance.enabled ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
        </button>

        <button
          onClick={(event) => {
            event.stopPropagation();
            setEditingTitle(instance.id);
          }}
          className="rounded p-1 text-app-ink-3 hover:text-app-ink"
          title="Rename"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>

        <button
          onClick={(event) => {
            event.stopPropagation();
            onRemoveInstance(instance.id);
          }}
          className="rounded p-1 text-app-danger hover:text-app-danger"
          title="Delete"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>

        <button
          onClick={(event) => {
            event.stopPropagation();
            onToggleExpand(instance.id);
          }}
          className="rounded p-1 text-app-ink-3 hover:text-app-ink"
          title={isExpanded ? "Collapse" : "Expand"}
        >
          <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown className="h-3.5 w-3.5" />
          </motion.div>
        </button>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <SectionEditorPanel instance={instance} onChange={onUpdateData} actions={editorActions} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
