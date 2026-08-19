import {
  $getSelection,
  $isRangeSelection,
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
import { $createLinkNode, $toggleLink, TOGGLE_LINK_COMMAND } from "@lexical/link";
import { $createTextNode } from "lexical";
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
  X,
} from "lucide-react";
import { safeLinkUrl } from "../../../lib/security/safeUrl";
import {
  applyFontSize,
  captureSelection,
  clearFormatting,
  currentSelectionState,
  linkForNode,
  listItemsInSelection,
  removeLinks,
  restoreSelection,
  textDescendants,
  type RichTextSelectionState,
  type SelectionSnapshot,
} from "./richTextEditorUtils";
import { FONT_SIZE_LABELS, type FontSizeToken } from "../../../styles/tokens";

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

interface LinkDialogProps {
  initialUrl: string | null;
  initialText: string;
  onApply: (url: string, displayText: string) => void;
  onCancel: () => void;
  onRemove: (() => void) | null;
}

function LinkDialog({ initialUrl, initialText, onApply, onCancel, onRemove }: LinkDialogProps) {
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

function selectionLinkContext(editor: LexicalEditor): { url: string | null; text: string } {
  return editor.getEditorState().read(() => {
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return { url: null, text: "" };
    const selectedText = selection.getTextContent();
    const link = linkForNode(selection.focus.getNode());
    return { url: link?.getURL() ?? null, text: selectedText || link?.getTextContent() || "" };
  });
}

function replaceListItemWithLink(item: ReturnType<typeof listItemsInSelection>[number], url: string, text: string): void {
  const source = textDescendants(item)[0];
  const linkedText = $createTextNode(text);
  if (source) linkedText.setFormat(source.getFormat()).setStyle(source.getStyle());
  item.clear().append($createLinkNode(url, { rel: "noreferrer" }).append(linkedText));
}

function applyLink(editor: LexicalEditor, snapshot: SelectionSnapshot | null, url: string, displayText: string): void {
  editor.update(() => {
    restoreSelection(snapshot);
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return;

    const listItems = listItemsInSelection(selection);
    if (listItems.length > 0) {
      for (const item of listItems) {
        const itemText = listItems.length === 1 ? displayText : item.getTextContent();
        replaceListItemWithLink(item, url, itemText);
      }
      return;
    }

    const existingLink = linkForNode(selection.focus.getNode());
    if (selection.isCollapsed() && existingLink) {
      const textNodes = textDescendants(existingLink);
      const first = textNodes[0];
      if (first) {
        first.setTextContent(displayText);
        for (const extra of textNodes.slice(1)) extra.remove();
      }
      existingLink.setURL(url);
      return;
    }

    if (selection.isCollapsed()) {
      const text = $createTextNode(displayText).setFormat(selection.format).setStyle(selection.style);
      selection.insertNodes([$createLinkNode(url, { rel: "noreferrer" }).append(text)]);
      return;
    }

    $toggleLink(url, { rel: "noreferrer" });
    if (selection.getTextContent() !== displayText) selection.insertText(displayText);
  });
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
      <ToolbarButton onPress={() => { editor.dispatchCommand(TOGGLE_LINK_COMMAND, null); }} disabled={!active.link} title="Remove link"><Unlink className="h-3.5 w-3.5" /></ToolbarButton>
      <span className="mx-1 h-4 w-px bg-app-surface-strong" aria-hidden="true" />
      <ToolbarButton onPress={() => editor.dispatchCommand(INSERT_UNORDERED_LIST_COMMAND, undefined)} active={active.listType === "bullet"} title="Bullet list"><List className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(INSERT_ORDERED_LIST_COMMAND, undefined)} active={active.listType === "numbered"} title="Numbered list"><ListOrdered className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(REMOVE_LIST_COMMAND, undefined)} disabled={!active.listType} title="Remove list"><ListX className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(INDENT_CONTENT_COMMAND, undefined)} disabled={!active.listType} title="Indent list item (nested lists are not supported)"><ListIndentIncrease className="h-3.5 w-3.5" /></ToolbarButton>
      <ToolbarButton onPress={() => editor.dispatchCommand(OUTDENT_CONTENT_COMMAND, undefined)} disabled={!active.listType} title="Outdent list item (nested lists are not supported)"><ListIndentDecrease className="h-3.5 w-3.5" /></ToolbarButton>
    </div>
  );
}
