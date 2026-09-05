import { $getSelection, $isRangeSelection, $isTextNode, type LexicalEditor } from "lexical";
import { $isListNode } from "@lexical/list";
import { fontSizeFromStyle } from "./formatting";
import { linkForNode, listItemForNode, textDescendants, type RichTextSelectionState } from "./selection";

export function currentSelectionState(editor: LexicalEditor): RichTextSelectionState {
  return editor.getEditorState().read(() => {
    const selection = $getSelection();
    const empty: RichTextSelectionState = {
      bold: false,
      italic: false,
      underline: false,
      strikethrough: false,
      link: null,
      listType: null,
      fontSize: null,
    };
    if (!$isRangeSelection(selection)) return empty;

    const focusNode = selection.focus.getNode();
    const listItem = listItemForNode(focusNode);
    const textNode = $isTextNode(focusNode) ? focusNode : textDescendants(listItem ?? focusNode)[0];
    const link = textNode ? linkForNode(textNode) : linkForNode(focusNode);
    const list = listItem?.getParent();
    return {
      bold: selection.hasFormat("bold"),
      italic: selection.hasFormat("italic"),
      underline: selection.hasFormat("underline"),
      strikethrough: selection.hasFormat("strikethrough"),
      link: link?.getURL() ?? null,
      listType: $isListNode(list)
        ? list.getListType() === "number" ? "numbered" as const : "bullet" as const
        : null,
      fontSize: fontSizeFromStyle(textNode?.getStyle() ?? selection.style),
    };
  });
}
