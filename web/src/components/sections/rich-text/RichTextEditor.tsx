import { useCallback, useEffect, useRef } from "react";
import { LexicalComposer } from "@lexical/react/LexicalComposer";
import { RichTextPlugin } from "@lexical/react/LexicalRichTextPlugin";
import { ContentEditable } from "@lexical/react/LexicalContentEditable";
import { HistoryPlugin } from "@lexical/react/LexicalHistoryPlugin";
import { OnChangePlugin } from "@lexical/react/LexicalOnChangePlugin";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { ListNode, ListItemNode } from "@lexical/list";
import { ListPlugin } from "@lexical/react/LexicalListPlugin";
import { LinkNode } from "@lexical/link";
import { LinkPlugin } from "@lexical/react/LexicalLinkPlugin";
import type { EditorState } from "lexical";
import type { RichTextBlock } from "../../../generated/schema";
import { lexicalToBlocks, blocksToLexical } from "../../../lib/sections/richTextTransform";
import RichTextToolbar from "./RichTextToolbar";

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
};

/** Sets initial editor state from the value prop on first mount. */
function InitPlugin({ value }: { value: RichTextBlock[] | string }) {
  const [editor] = useLexicalComposerContext();
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const serialized = blocksToLexical(value);
    const state = editor.parseEditorState(serialized as any);
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
  onChangeRef.current = onChange;

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
      editor.setEditorState(editor.parseEditorState(serialized as any));
    }
  }, [editor, value]);

  return (
    <>
      <RichTextToolbar editor={editor} />
      <div className="min-h-[4.5rem] px-2 py-1 text-sm">
        <RichTextPlugin
          contentEditable={
            <ContentEditable className="outline-none" style={{ minHeight: "3rem" }} />
          }
          placeholder={
            <div className="pointer-events-none text-gray-400">{placeholder}</div>
          }
          ErrorBoundary={({ children }) => <div>{children}</div>}
        />
      </div>
      <HistoryPlugin />
      <ListPlugin />
      <LinkPlugin />
      <OnChangePlugin onChange={handleChange} />
      <InitPlugin value={value} />
    </>
  );
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = "Enter text...",
}: Props) {
  const initialConfig = {
    namespace: "CVRichText",
    theme,
    onError: (error: Error) => console.error("[RichTextEditor]", error),
    nodes: [ListNode, ListItemNode, LinkNode],
  };
  return (
    <div className="rich-text-editor rounded border border-gray-200 focus-within:border-blue-400">
      <LexicalComposer initialConfig={initialConfig}>
        <EditorInner value={value} onChange={onChange} placeholder={placeholder} />
      </LexicalComposer>
    </div>
  );
}
