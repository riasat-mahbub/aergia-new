import {
  COMMAND_PRIORITY_CRITICAL,
  FORMAT_TEXT_COMMAND,
  INDENT_CONTENT_COMMAND,
  OUTDENT_CONTENT_COMMAND,
  SELECTION_CHANGE_COMMAND,
  type LexicalEditor,
  type TextFormatType,
} from "lexical";
import {
  INSERT_ORDERED_LIST_COMMAND,
  INSERT_UNORDERED_LIST_COMMAND,
} from "@lexical/list";
import { REMOVE_LIST_COMMAND } from "@lexical/list";
import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Bold,
  Eraser,
  Italic,
  Link,
  List,
  ListIndentDecrease,
  ListIndentIncrease,
  ListOrdered,
  ListX,
  Strikethrough,
  Underline,
  Unlink,
} from "lucide-react";
import { applyFontSize } from "./formatting";
import { currentSelectionState } from "./selectionState";
import { clearFormatting, removeLinks } from "./links";
import { captureSelection, restoreSelection, type RichTextSelectionState, type SelectionSnapshot } from "./selection";
import { applyLink, selectionLinkContext } from "./linkCommands";
import LinkDialog from "./LinkDialog";
import { FONT_SIZE_LABELS, type FontSizeToken } from "@/styles/tokens";

interface Props {
  editor: LexicalEditor;
}

function ToolbarButton({
  onPress,
  active,
  disabled,
  title,
  children,
}: {
  onPress: () => void;
  active?: boolean;
  disabled?: boolean;
  title: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onMouseDown={(event) => event.preventDefault()}
      onClick={onPress}
      disabled={disabled}
      title={title}
      aria-label={title}
      aria-pressed={active === undefined ? undefined : active}
      className={`rounded p-1 text-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-app-primary-soft ${
        active ? "bg-app-primary-soft text-app-primary" : "text-app-ink-2 hover:bg-app-surface-muted"
      } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
    >
      {children}
    </button>
  );
}

export default function RichTextToolbar({ editor }: Props) {
  const [active, setActive] = useState<RichTextSelectionState>(() => currentSelectionState(editor));
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [linkContext, setLinkContext] = useState({ url: null as string | null, text: "" });
  const linkSelection = useRef<SelectionSnapshot | null>(null);
  const sizeSelection = useRef<SelectionSnapshot | null>(null);

  const refreshActive = () => setActive(currentSelectionState(editor));

  useEffect(() => {
    const unregisterSelection = editor.registerCommand(
      SELECTION_CHANGE_COMMAND,
      () => {
        refreshActive();
        return false;
      },
      COMMAND_PRIORITY_CRITICAL,
    );
    const unregisterUpdates = editor.registerUpdateListener(refreshActive);
    return () => {
      unregisterSelection();
      unregisterUpdates();
    };
  }, [editor]);

  const format = (formatType: TextFormatType) => editor.dispatchCommand(FORMAT_TEXT_COMMAND, formatType);

  const openLinkDialog = () => {
    linkSelection.current = captureSelection(editor);
    setLinkContext(selectionLinkContext(editor));
    setLinkDialogOpen(true);
  };

  const closeLinkDialog = () => {
    setLinkDialogOpen(false);
    editor.focus();
    editor.update(() => restoreSelection(linkSelection.current));
  };

  const removeLinkFromDialog = () => {
    setLinkDialogOpen(false);
    editor.focus();
    editor.update(() => restoreSelection(linkSelection.current));
    removeLinks(editor);
  };

  const applyLinkFromDialog = (url: string, displayText: string) => {
    setLinkDialogOpen(false);
    applyLink(editor, linkSelection.current, url, displayText.trim());
    editor.focus();
  };

  const restoreSizeSelection = () => {
    if (sizeSelection.current) editor.update(() => restoreSelection(sizeSelection.current));
  };

  return (
    <div className="rich-text-toolbar relative flex flex-wrap items-center gap-0.5 border-b border-app-rule-soft px-2 py-1" role="toolbar" aria-label="Rich text formatting">
      <ToolbarButton onPress={() => format("bold")} active={active.bold} title="Bold (Ctrl+B)"><Bold className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => format("italic")} active={active.italic} title="Italic (Ctrl+I)"><Italic className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => format("underline")} active={active.underline} title="Underline (Ctrl+U)"><Underline className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => format("strikethrough")} active={active.strikethrough} title="Strikethrough"><Strikethrough className="h-3.5 w-3.5" /></ToolbarButton>
      <span className="mx-1 h-4 w-px bg-app-surface-strong" aria-hidden="true" />
      <label className="sr-only" htmlFor="rich-text-font-size">Font size</label>
      <select
        id="rich-text-font-size"
        aria-label="Font size"
        value={active.fontSize ?? ""}
        onMouseDown={() => { sizeSelection.current = captureSelection(editor); }}
        onChange={(event) => {
          restoreSizeSelection();
          applyFontSize(editor, (event.target.value || null) as FontSizeToken | null);
        }}
        className="h-7 max-w-24 rounded border border-app-rule bg-app-surface px-1 text-[11px] text-app-ink-2 outline-none focus:border-app-primary focus:ring-2 focus:ring-app-primary-soft"
      >
        <option value="">Size</option>
        {(Object.keys(FONT_SIZE_LABELS) as FontSizeToken[]).map((token) => <option key={token} value={token}>{FONT_SIZE_LABELS[token]}</option>)}
      </select>
      <ToolbarButton onPress={clearFormatting.bind(null, editor)} title="Clear formatting"><Eraser className="h-3.5 w-3.5" /></ToolbarButton>
      <span className="mx-1 h-4 w-px bg-app-surface-strong" aria-hidden="true" />
      <div className="relative">
        <ToolbarButton onPress={openLinkDialog} active={Boolean(active.link)} title={active.link ? "Edit link" : "Add link"}><Link className="h-3.5 w-3.5" /></ToolbarButton>
        {linkDialogOpen && <LinkDialog initialUrl={linkContext.url} initialText={linkContext.text} onApply={applyLinkFromDialog} onCancel={closeLinkDialog} onRemove={linkContext.url ? removeLinkFromDialog : null} />}
      </div>
      <ToolbarButton onPress={() => removeLinks(editor)} disabled={!active.link} title="Remove link"><Unlink className="h-3.5 w-3.5" /></ToolbarButton>
      <span className="mx-1 h-4 w-px bg-app-surface-strong" aria-hidden="true" />
      <ToolbarButton onPress={() => editor.dispatchCommand(INSERT_UNORDERED_LIST_COMMAND, undefined)} active={active.listType === "bullet"} title="Bullet list"><List className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(INSERT_ORDERED_LIST_COMMAND, undefined)} active={active.listType === "numbered"} title="Numbered list"><ListOrdered className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(REMOVE_LIST_COMMAND, undefined)} disabled={!active.listType} title="Remove list"><ListX className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(INDENT_CONTENT_COMMAND, undefined)} disabled={!active.listType} title="Indent list item (nested lists are not supported)"><ListIndentIncrease className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(OUTDENT_CONTENT_COMMAND, undefined)} disabled={!active.listType} title="Outdent list item (nested lists are not supported)"><ListIndentDecrease className="h-3.5 w-3.5" /></ToolbarButton>
    </div>
  );
}
