import { useCallback, useEffect, useRef } from "react";
import { LexicalComposer } from "@lexical/react/LexicalComposer";
import { RichTextPlugin } from "@lexical/react/LexicalRichTextPlugin";
import { ContentEditable } from "@lexical/react/LexicalContentEditable";
import { HistoryPlugin } from "@lexical/react/LexicalHistoryPlugin";
import { OnChangePlugin } from "@lexical/react/LexicalOnChangePlugin";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { ListNode, ListItemNode } from "@lexical/list";
import { $isListItemNode } from "@lexical/list";
import { ListPlugin } from "@lexical/react/LexicalListPlugin";
import { AutoLinkNode, LinkNode, autoLinkEmailMatcher, autoLinkUrlMatcher } from "@lexical/link";
import { TOGGLE_LINK_COMMAND } from "@lexical/link";
import { LinkPlugin } from "@lexical/react/LexicalLinkPlugin";
import { AutoLinkPlugin } from "@lexical/react/LexicalAutoLinkPlugin";
import {
  $getSelection,
  COMMAND_PRIORITY_HIGH,
  FORMAT_TEXT_COMMAND,
  INDENT_CONTENT_COMMAND,
  OUTDENT_CONTENT_COMMAND,
  PASTE_COMMAND,
  $isRangeSelection,
  type TextFormatType,
} from "lexical";
import type { EditorState } from "lexical";
import type { RichTextBlock } from "../../../generated/schema";
import { lexicalToBlocks, blocksToLexical } from "../../../lib/sections/richTextTransform";
import { safeLinkUrl } from "../../../lib/security/safeUrl";
import RichTextToolbar from "./RichTextToolbar";
import { listItemsInSelection, normalizeListTextFormat } from "./richTextEditorUtils";
import { setListItemsLink } from "./richTextEditorUtils";
import { sanitizeRichTextHtml } from "./richTextPaste";
import { $generateNodesFromDOM } from "@lexical/html";

interface Props {
  value: RichTextBlock[] | string;
  onChange: (blocks: RichTextBlock[]) => void;
  placeholder?: string;
}

const theme = {
  paragraph: "editor-paragraph",
  text: {
    bold: "editor-text-bold",
    italic: "editor-text-italic",
    underline: "editor-text-underline",
    strikethrough: "editor-text-strikethrough",
  },
  list: {
    ul: "editor-list-ul",
    ol: "editor-list-ol",
    listitem: "editor-listitem",
  },
  link: "editor-link",
};

const safeAutoLinkMatchers = [
  (text: string) => {
    const match = autoLinkUrlMatcher(text);
    if (!match) return null;
    const url = safeLinkUrl(match.url);
    return url ? { ...match, url } : null;
  },
  (text: string) => {
    const match = autoLinkEmailMatcher(text);
    if (!match) return null;
    const url = safeLinkUrl(match.url);
    return url ? { ...match, url } : null;
  },
];

/** Sets initial editor state from the value prop on first mount. */
function InitPlugin({ value }: { value: RichTextBlock[] | string }) {
  const [editor] = useLexicalComposerContext();
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const serialized = blocksToLexical(value);
    const state = editor.parseEditorState(serialized);
    editor.setEditorState(state);
  }, [editor, value]);

  return null;
}

function EditorInner({
  value,
  onChange,
  placeholder,
}: {
  value: RichTextBlock[] | string;
  onChange: (blocks: RichTextBlock[]) => void;
  placeholder: string;
}) {
  const [editor] = useLexicalComposerContext();
  const isInternalChange = useRef(false);
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  const handleChange = useCallback(
    (editorState: EditorState) => {
      if (isInternalChange.current) {
        isInternalChange.current = false;
        return;
      }
      const blocks = lexicalToBlocks(editorState.toJSON() as Parameters<typeof lexicalToBlocks>[0]);
      onChangeRef.current(blocks);
    },
    []
  );

  // Re-initialize editor when value changes externally
  const prevValueRef = useRef(value);
  useEffect(() => {
    if (prevValueRef.current === value) return;
    const currentBlocks = lexicalToBlocks(editor.getEditorState().toJSON() as Parameters<typeof lexicalToBlocks>[0]);
    prevValueRef.current = value;

    const incomingBlocks =
      typeof value === "string"
        ? [{ type: "paragraph" as const, items: [{ text: value }] }]
        : Array.isArray(value)
          ? value
          : [];

    if (JSON.stringify(currentBlocks) !== JSON.stringify(incomingBlocks)) {
      isInternalChange.current = true;
      const serialized = blocksToLexical(value);
      editor.setEditorState(editor.parseEditorState(serialized));
    }
  }, [editor, value]);

  return (
    <>
      <RichTextToolbar editor={editor} />
      <div className="min-h-[4.5rem] px-2 py-1 text-sm">
        <RichTextPlugin
          contentEditable={
            <ContentEditable
              className="outline-none"
              style={{ minHeight: "3rem" }}
              aria-label="Rich text editor"
              aria-multiline="true"
            />
          }
          placeholder={
            <div className="pointer-events-none text-app-ink-3">{placeholder}</div>
          }
          ErrorBoundary={({ children }) => <div>{children}</div>}
        />
      </div>
      <HistoryPlugin />
      <ListPlugin />
      <FlatListFormattingPlugin />
      <PasteCleanupPlugin />
      <LinkPlugin validateUrl={(url) => Boolean(safeLinkUrl(url))} />
      <AutoLinkPlugin matchers={safeAutoLinkMatchers} excludeParents={[$isListItemNode]} />
      <OnChangePlugin onChange={handleChange} />
      <InitPlugin value={value} />
    </>
  );
}

/** Keeps inline formatting on a flat list item as one logical run. */
function FlatListFormattingPlugin() {
  const [editor] = useLexicalComposerContext();

  useEffect(() => {
    const unregisterFormat = editor.registerCommand(
      FORMAT_TEXT_COMMAND,
      (format: TextFormatType) => normalizeListTextFormat($getSelection(), format),
      COMMAND_PRIORITY_HIGH,
    );
    const guardNestedLists = (command: typeof INDENT_CONTENT_COMMAND | typeof OUTDENT_CONTENT_COMMAND) =>
      editor.registerCommand(command, () => listItemsInSelection($getSelection()).length > 0, COMMAND_PRIORITY_HIGH);
    const unregisterIndent = guardNestedLists(INDENT_CONTENT_COMMAND);
    const unregisterOutdent = guardNestedLists(OUTDENT_CONTENT_COMMAND);
    const unregisterListLinks = editor.registerCommand(
      TOGGLE_LINK_COMMAND,
      (payload) => {
        const selection = $getSelection();
        if (listItemsInSelection(selection).length === 0) return false;
        if (payload === null) return setListItemsLink(selection, null);
        const rawUrl = typeof payload === "string" ? payload : payload.url;
        const safeUrl = safeLinkUrl(rawUrl);
        return safeUrl ? setListItemsLink(selection, safeUrl) : false;
      },
      COMMAND_PRIORITY_HIGH,
    );
    return () => {
      unregisterFormat();
      unregisterIndent();
      unregisterOutdent();
      unregisterListLinks();
    };
  }, [editor]);

  return null;
}

/** Import only the allowlisted HTML produced by the paste sanitizer. */
function PasteCleanupPlugin() {
  const [editor] = useLexicalComposerContext();

  useEffect(() => editor.registerCommand(
    PASTE_COMMAND,
    (event) => {
      const clipboard = event as ClipboardEvent;
      const html = clipboard.clipboardData?.getData("text/html");
      if (!html) return false;
      const sanitized = sanitizeRichTextHtml(html);
      if (!sanitized || typeof DOMParser === "undefined") return false;
      const document = new DOMParser().parseFromString(sanitized, "text/html");
      event.preventDefault();
      editor.update(() => {
        const selection = $getSelection();
        if (!$isRangeSelection(selection)) return;
        const nodes = $generateNodesFromDOM(editor, document);
        if (nodes.length > 0) selection.insertNodes(nodes);
      });
      return true;
    },
    COMMAND_PRIORITY_HIGH,
  ), [editor]);

  return null;
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = "Write a concise description…",
}: Props) {
  const initialConfig = {
    namespace: "CVRichText",
    theme,
    onError: (error: Error) => console.error("[RichTextEditor]", error),
    nodes: [ListNode, ListItemNode, LinkNode, AutoLinkNode],
  };
  return (
    <div className="rich-text-editor rounded border border-app-rule focus-within:border-app-primary-soft">
      <LexicalComposer initialConfig={initialConfig}>
        <EditorInner value={value} onChange={onChange} placeholder={placeholder} />
      </LexicalComposer>
    </div>
  );
}
