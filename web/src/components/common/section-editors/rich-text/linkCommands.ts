import {
  $getSelection,
  $isRangeSelection,
  type LexicalEditor,
} from "lexical";
import { $createLinkNode, $toggleLink } from "@lexical/link";
import { $createTextNode } from "lexical";
import { linkForNode, listItemsInSelection, restoreSelection, textDescendants } from "./selection";
import type { SelectionSnapshot } from "./selection";

export interface LinkContext {
  url: string | null;
  text: string;
}

export function selectionLinkContext(editor: LexicalEditor): LinkContext {
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

export function applyLink(
  editor: LexicalEditor,
  snapshot: SelectionSnapshot | null,
  url: string,
  displayText: string,
): void {
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
