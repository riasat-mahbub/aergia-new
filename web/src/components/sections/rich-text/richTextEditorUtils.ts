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
  type TextFormatType,
  type TextNode,
} from "lexical";
import { $isListItemNode, $isListNode, type ListItemNode } from "@lexical/list";
import { $isAutoLinkNode, $isLinkNode, type LinkNode } from "@lexical/link";
import { FONT_SIZE_CSS, FONT_SIZE_TOKENS, type FontSizeToken } from "../../../styles/tokens";

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

const FORMAT_BITS: Record<TextFormatType, number> = {
  bold: 1,
  italic: 2,
  strikethrough: 4,
  underline: 8,
  code: 16,
  subscript: 32,
  superscript: 64,
  highlight: 128,
  lowercase: 256,
  uppercase: 512,
  capitalize: 1024,
};

const CSS_TO_FONT_SIZE = Object.fromEntries(
  Object.entries(FONT_SIZE_CSS).map(([token, css]) => [css, token]),
) as Record<string, FontSizeToken>;

function nearestAncestor<T extends LexicalNode>(node: LexicalNode, predicate: (candidate: LexicalNode) => candidate is T): T | null {
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

function parseStyle(styleValue: string): Map<string, string> {
  const declarations = new Map<string, string>();
  for (const declaration of styleValue.split(";")) {
    const separator = declaration.indexOf(":");
    if (separator < 0) continue;
    const property = declaration.slice(0, separator).trim().toLowerCase();
    const value = declaration.slice(separator + 1).trim();
    if (property && value) declarations.set(property, value);
  }
  return declarations;
}

function serializeStyle(declarations: Map<string, string>): string {
  return [...declarations.entries()].map(([property, value]) => `${property}:${value}`).join(";");
}

export function fontSizeFromStyle(styleValue: string): FontSizeToken | null {
  return CSS_TO_FONT_SIZE[parseStyle(styleValue).get("font-size") ?? ""] ?? null;
}

export function setFontSizeOnText(node: TextNode, token: FontSizeToken | null): void {
  const declarations = parseStyle(node.getStyle());
  declarations.delete("font-size");
  if (token) declarations.set("font-size", FONT_SIZE_CSS[token]);
  node.setStyle(serializeStyle(declarations));
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

function updateTextFormat(node: TextNode, format: TextFormatType, enabled: boolean): void {
  const bit = FORMAT_BITS[format];
  if (!bit) return;
  const current = node.getFormat();
  node.setFormat(enabled ? current | bit : current & ~bit);
}

/**
 * Apply a format command while treating a list item as one flat wire run.
 * Returning false lets Lexical handle ordinary paragraph selections.
 */
export function normalizeListTextFormat(selection: ReturnType<typeof $getSelection>, format: TextFormatType): boolean {
  const listItems = listItemsInSelection(selection);
  if (listItems.length === 0 || !$isRangeSelection(selection)) return false;

  const textNodes = listItems.flatMap(textDescendants);
  if (textNodes.length === 0) return true;
  const enabled = !textNodes.every((node) => (node.getFormat() & FORMAT_BITS[format]) !== 0);

  // Let Lexical split/format any selected paragraph text first, then force
  // every run in each affected list item to the same value. This keeps list
  // editing intuitive even when the selection covers only part of a bullet.
  if (!selection.isCollapsed()) {
    selection.formatText(format);
  } else {
    selection.setFormat(enabled ? selection.format | FORMAT_BITS[format] : selection.format & ~FORMAT_BITS[format]);
  }
  for (const item of listItems) {
    for (const node of textDescendants(item)) updateTextFormat(node, format, enabled);
  }
  return true;
}

/** Apply a font-size token to selected text, or to the whole flat list item. */
export function applyFontSize(editor: LexicalEditor, token: FontSizeToken | null): void {
  editor.update(() => {
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return;
    const listItems = listItemsInSelection(selection);
    const listText = new Set(listItems.flatMap(textDescendants).map((node) => node.getKey()));
    for (const item of listItems) {
      for (const node of textDescendants(item)) setFontSizeOnText(node, token);
    }

    const selectedTextNodes = selection.getNodes().filter($isTextNode);
    if (selectedTextNodes.length === 0) {
      if (listItems.length === 0) {
        const nextStyle = parseStyle(selection.style);
        nextStyle.delete("font-size");
        if (token) nextStyle.set("font-size", FONT_SIZE_CSS[token]);
        selection.setStyle(serializeStyle(nextStyle));
      }
      return;
    }

    // For paragraph text, Lexical's public RangeSelection API handles
    // partial-node splits and preserves the selection points for us.
    const paragraphNodes = selectedTextNodes.filter((node) => !listText.has(node.getKey()));
    if (paragraphNodes.length === 0) return;
    if (selection.isCollapsed()) {
      const nextStyle = parseStyle(selection.style);
      nextStyle.delete("font-size");
      if (token) nextStyle.set("font-size", FONT_SIZE_CSS[token]);
      selection.setStyle(serializeStyle(nextStyle));
      return;
    }

    // The selection API has no style-only command, so use the same
    // selection boundaries and text-node splits as a normal range operation.
    const start = selection.isBackward() ? selection.focus : selection.anchor;
    const end = selection.isBackward() ? selection.anchor : selection.focus;
    const first = paragraphNodes[0];
    const last = paragraphNodes[paragraphNodes.length - 1];
    const firstOffset = start.type === "text" ? start.offset : 0;
    const endOffset = end.type === "text" ? end.offset : last.getTextContentSize();
    if (first.is(last)) {
      if (firstOffset === endOffset) return;
      const replacement = firstOffset === 0 && endOffset === first.getTextContentSize()
        ? first
        : first.splitText(firstOffset, endOffset)[firstOffset === 0 ? 0 : 1];
      setFontSizeOnText(replacement, token);
      return;
    }
    let firstSelected = first;
    if (firstOffset > 0) [, firstSelected] = first.splitText(firstOffset);
    setFontSizeOnText(firstSelected, token);
    const lastSelected = endOffset < last.getTextContentSize() ? last.splitText(endOffset)[0] : last;
    setFontSizeOnText(lastSelected, token);
    for (const node of paragraphNodes.slice(1, -1)) setFontSizeOnText(node, token);
  });
}

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
    const result = {
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
    return result;
  });
}

export function unwrapLink(link: LinkNode): void {
  const parent = link.getParent();
  if (!parent) return;
  for (const child of [...link.getChildren()]) link.insertBefore(child);
  link.remove();
}

export function linksInSelection(selection: ReturnType<typeof $getSelection>): LinkNode[] {
  if (!$isRangeSelection(selection)) return [];
  const candidates = selection.getNodes();
  candidates.push(selection.anchor.getNode(), selection.focus.getNode());
  const links: LinkNode[] = [];
  const seen = new Set<string>();
  for (const node of candidates) {
    const link = linkForNode(node);
    if (link && !seen.has(link.getKey())) {
      seen.add(link.getKey());
      links.push(link);
    }
  }
  return links;
}

export function removeLinks(editor: LexicalEditor): void {
  editor.update(() => {
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return;
    for (const link of linksInSelection(selection)) unwrapLink(link);
  });
}

export function clearFormatting(editor: LexicalEditor): void {
  editor.update(() => {
    const selection = $getSelection();
    if (!$isRangeSelection(selection)) return;
    const listItems = listItemsInSelection(selection);
    const nodes = listItems.length > 0
      ? listItems.flatMap(textDescendants)
      : selection.getNodes().filter($isTextNode);
    for (const node of nodes) {
      node.setFormat(0);
      node.setStyle("");
    }
    for (const link of linksInSelection(selection)) unwrapLink(link);
  });
}

export const SUPPORTED_FONT_SIZE_TOKENS = FONT_SIZE_TOKENS;
