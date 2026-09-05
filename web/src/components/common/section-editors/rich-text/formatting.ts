import {
  $getSelection,
  $isRangeSelection,
  type LexicalEditor,
  type TextFormatType,
  type TextNode,
} from "lexical";
import { FONT_SIZE_CSS, FONT_SIZE_TOKENS, type FontSizeToken } from "@/styles/tokens";
import { listItemsInSelection, textDescendants } from "./selection";

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

function updateTextFormat(node: TextNode, format: TextFormatType, enabled: boolean): void {
  const bit = FORMAT_BITS[format];
  if (!bit) return;
  const current = node.getFormat();
  node.setFormat(enabled ? current | bit : current & ~bit);
}

/** Apply a format command while treating a list item as one flat wire run. */
export function normalizeListTextFormat(
  selection: ReturnType<typeof $getSelection>,
  format: TextFormatType,
): boolean {
  const listItems = listItemsInSelection(selection);
  if (listItems.length === 0 || !$isRangeSelection(selection)) return false;

  const textNodes = listItems.flatMap(textDescendants);
  if (textNodes.length === 0) return true;
  const enabled = !textNodes.every((node) => (node.getFormat() & FORMAT_BITS[format]) !== 0);
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

    const selectedTextNodes = selection.getNodes().filter((node): node is TextNode => node.getType() === "text");
    if (selectedTextNodes.length === 0) {
      if (listItems.length === 0) {
        const nextStyle = parseStyle(selection.style);
        nextStyle.delete("font-size");
        if (token) nextStyle.set("font-size", FONT_SIZE_CSS[token]);
        selection.setStyle(serializeStyle(nextStyle));
      }
      return;
    }

    const paragraphNodes = selectedTextNodes.filter((node) => !listText.has(node.getKey()));
    if (paragraphNodes.length === 0) return;
    if (selection.isCollapsed()) {
      const nextStyle = parseStyle(selection.style);
      nextStyle.delete("font-size");
      if (token) nextStyle.set("font-size", FONT_SIZE_CSS[token]);
      selection.setStyle(serializeStyle(nextStyle));
      return;
    }

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

export const SUPPORTED_FONT_SIZE_TOKENS = FONT_SIZE_TOKENS;
