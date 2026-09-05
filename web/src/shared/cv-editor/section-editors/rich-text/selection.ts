import {
  $createRangeSelection,
  $getSelection,
  $isElementNode,
  $isRangeSelection,
  $isTextNode,
  $setSelection,
  type LexicalEditor,
  type LexicalNode,
  type PointType,
  type TextNode,
} from "lexical";
import { $isListItemNode, type ListItemNode } from "@lexical/list";
import { $isAutoLinkNode, $isLinkNode, type LinkNode } from "@lexical/link";
import type { FontSizeToken } from "@/styles/tokens";

export interface SelectionSnapshot {
  anchor: Pick<PointType, "key" | "offset" | "type">;
  focus: Pick<PointType, "key" | "offset" | "type">;
}

export interface RichTextSelectionState {
  bold: boolean;
  italic: boolean;
  underline: boolean;
  strikethrough: boolean;
  link: string | null;
  listType: "bullet" | "numbered" | null;
  fontSize: FontSizeToken | null;
}

function nearestAncestor<T extends LexicalNode>(
  node: LexicalNode,
  predicate: (candidate: LexicalNode) => candidate is T,
): T | null {
  let current: LexicalNode | null = node;
  while (current) {
    if (predicate(current)) return current;
    current = current.getParent();
  }
  return null;
}

export function listItemForNode(node: LexicalNode): ListItemNode | null {
  return nearestAncestor(node, $isListItemNode);
}

export function linkForNode(node: LexicalNode): LinkNode | null {
  return nearestAncestor(node, (candidate): candidate is LinkNode =>
    $isLinkNode(candidate) || $isAutoLinkNode(candidate),
  );
}

export function textDescendants(node: LexicalNode): TextNode[] {
  if ($isTextNode(node)) return [node];
  if (!$isElementNode(node)) return [];
  return node.getChildren().flatMap(textDescendants);
}

export function listItemsInSelection(selection: ReturnType<typeof $getSelection>): ListItemNode[] {
  if (!$isRangeSelection(selection)) return [];
  const candidates = selection.getNodes();
  candidates.push(selection.anchor.getNode(), selection.focus.getNode());
  const seen = new Set<string>();
  const result: ListItemNode[] = [];
  for (const node of candidates) {
    const item = listItemForNode(node);
    if (item && !seen.has(item.getKey())) {
      seen.add(item.getKey());
      result.push(item);
    }
  }
  return result;
}

export function captureSelection(editor: LexicalEditor): SelectionSnapshot | null {
  return editor.getEditorState().read(() => {
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return null;
    return {
      anchor: { key: selection.anchor.key, offset: selection.anchor.offset, type: selection.anchor.type },
      focus: { key: selection.focus.key, offset: selection.focus.offset, type: selection.focus.type },
    };
  });
}

export function restoreSelection(snapshot: SelectionSnapshot | null): void {
  if (!snapshot) return;
  const selection = $createRangeSelection();
  selection.anchor.set(snapshot.anchor.key, snapshot.anchor.offset, snapshot.anchor.type);
  selection.focus.set(snapshot.focus.key, snapshot.focus.offset, snapshot.focus.type);
  $setSelection(selection);
}
