import {
  FORMAT_TEXT_COMMAND,
  SELECTION_CHANGE_COMMAND,
  COMMAND_PRIORITY_CRITICAL,
  $getSelection,
  $isRangeSelection,
  type LexicalEditor,
} from "lexical";
import {
  INSERT_UNORDERED_LIST_COMMAND,
  INSERT_ORDERED_LIST_COMMAND,
} from "@lexical/list";
import { TOGGLE_LINK_COMMAND } from "@lexical/link";
import { useEffect, useState } from "react";
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  List,
  ListOrdered,
  Link,
} from "lucide-react";
import { safeLinkUrl } from "../../../lib/security/safeUrl";

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
  children: React.ReactNode;
}) {
  // Use onMouseDown + preventDefault so clicking the button does NOT steal
  // focus from the editor. The editor's selection is required for
  // FORMAT_TEXT_COMMAND and the list commands to act on the right range.
  const handleMouseDown = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    onPress();
  };

  return (
    <button
      type="button"
      onMouseDown={handleMouseDown}
      disabled={disabled}
      title={title}
      className={`rounded p-1 text-xs ${
        active ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"
      } ${disabled ? "opacity-40" : ""}`}
    >
      {children}
    </button>
  );
}

export default function RichTextToolbar({ editor }: Props) {
  const [active, setActive] = useState(() => {
    const selection = editor.getEditorState().read(() => $getSelection());
    if (!$isRangeSelection(selection)) {
      return { bold: false, italic: false, underline: false, strikethrough: false };
    }
    return {
      bold: selection.hasFormat("bold"),
      italic: selection.hasFormat("italic"),
      underline: selection.hasFormat("underline"),
      strikethrough: selection.hasFormat("strikethrough"),
    };
  });

  // Keep active-format indicators in sync with the editor's selection.
  useEffect(() => {
    return editor.registerCommand(
      SELECTION_CHANGE_COMMAND,
      () => {
        const selection = editor.getEditorState().read(() => $getSelection());
        if (!$isRangeSelection(selection)) {
          setActive({ bold: false, italic: false, underline: false, strikethrough: false });
          return false;
        }
        setActive({
          bold: selection.hasFormat("bold"),
          italic: selection.hasFormat("italic"),
          underline: selection.hasFormat("underline"),
          strikethrough: selection.hasFormat("strikethrough"),
        });
        return false;
      },
      COMMAND_PRIORITY_CRITICAL,
    );
  }, [editor]);

  // Wrap selection with a link. Empty string removes the link; cancel no-ops.
  const insertLink = () => {
    const url = window.prompt("Link URL (leave blank to remove)", "https://");
    if (url === null) return;
    if (url.trim() === "") {
      editor.dispatchCommand(TOGGLE_LINK_COMMAND, null);
      return;
    }
    const safeUrl = safeLinkUrl(url);
    if (safeUrl) editor.dispatchCommand(TOGGLE_LINK_COMMAND, safeUrl);
  };

  return (
    <div className="flex items-center gap-0.5 border-b border-gray-100 px-2 py-1">
      <ToolbarButton
        onPress={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, "bold")}
        active={active.bold}
        title="Bold (Ctrl+B)"
      >
        <Bold className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        onPress={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, "italic")}
        active={active.italic}
        title="Italic (Ctrl+I)"
      >
        <Italic className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        onPress={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, "underline")}
        active={active.underline}
        title="Underline (Ctrl+U)"
      >
        <Underline className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        onPress={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, "strikethrough")}
        active={active.strikethrough}
        title="Strikethrough"
      >
        <Strikethrough className="h-3.5 w-3.5" />
      </ToolbarButton>
      <div className="mx-1 h-4 w-px bg-gray-200" />
      <ToolbarButton onPress={insertLink} title="Link">
        <Link className="h-3.5 w-3.5" />
      </ToolbarButton>
      <div className="mx-1 h-4 w-px bg-gray-200" />
      <ToolbarButton
        onPress={() => editor.dispatchCommand(INSERT_UNORDERED_LIST_COMMAND, undefined)}
        title="Bullet List"
      >
        <List className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        onPress={() => editor.dispatchCommand(INSERT_ORDERED_LIST_COMMAND, undefined)}
        title="Numbered List"
      >
        <ListOrdered className="h-3.5 w-3.5" />
      </ToolbarButton>
    </div>
  );
}
