/** Bidirectional transform between Lexical JSON and RichTextBlock[].

Lexical stores documents as a tree of ``SerializedLexicalNode`` objects.
Our backend stores descriptions as ``RichTextBlock[]`` (paragraphs and lists
with inline-styled runs).  This module converts between the two formats so
the editor can work with Lexical's native model while the wire format stays
backend-friendly.
*/

import type { SerializedEditorState } from "lexical";
import type { RichTextBlock, RichTextItem, TextStyle } from "../../generated/schema";
import { safeLinkUrl } from "../security/safeUrl";
import { FONT_SIZE_CSS, type FontSizeToken } from "../../styles/tokens";

// ---------------------------------------------------------------------------
// Lexical → RichTextBlock[]
// ---------------------------------------------------------------------------

/** Decode a Lexical format bitmask into a TextStyle. */
function decodeFormat(format: number): TextStyle | undefined {
  if (format === 0) return undefined;
  const style: TextStyle = {};
  if (format & 1) style.bold = true;
  if (format & 2) style.italic = true;
  if (format & 4) style.strike = true;
  if (format & 8) style.underline = true;
  return Object.keys(style).length > 0 ? style : undefined;
}

const CSS_TO_FONT_SIZE: Record<string, FontSizeToken> = Object.fromEntries(
  Object.entries(FONT_SIZE_CSS).map(([token, css]) => [css, token]),
) as Record<string, FontSizeToken>;

const SAFE_HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** Decode only the inline CSS declarations emitted by this editor.
 *
 * Lexical's style field is deliberately treated as an allowlist. Pasted or
 * legacy markup may contain arbitrary CSS, but the wire model only supports
 * the renderer's font-size tokens and safe hex colors.
 */
function decodeStyle(styleValue: unknown): TextStyle | undefined {
  if (typeof styleValue !== "string" || !styleValue) return undefined;

  const style: TextStyle = {};
  for (const declaration of styleValue.split(";")) {
    const separator = declaration.indexOf(":");
    if (separator < 0) continue;
    const property = declaration.slice(0, separator).trim().toLowerCase();
    const value = declaration.slice(separator + 1).trim();
    if (property === "font-size") {
      const token = CSS_TO_FONT_SIZE[value];
      if (token) style.font_size = token;
    } else if (property === "color" && SAFE_HEX_COLOR.test(value)) {
      style.color = value;
    }
  }
  return Object.keys(style).length > 0 ? style : undefined;
}

/** Extract text items from Lexical inline children (text nodes and link wrappers). */
function decodeChildren(children: unknown[]): RichTextItem[] {
  const items: RichTextItem[] = [];
  for (const child of children) {
    if (!child || typeof child !== "object") continue;
    const node = child as Record<string, unknown>;
    if (node.type === "text" && typeof node.text === "string") {
      const format = typeof node.format === "number" ? node.format : 0;
      const style = { ...(decodeFormat(format) ?? {}), ...(decodeStyle(node.style) ?? {}) };
      items.push({ text: node.text, ...(Object.keys(style).length > 0 ? { style } : {}) });
    } else if ((node.type === "link" || node.type === "autolink") && typeof node.url === "string") {
      // LinkNode wraps text children; propagate its `url` to every child run.
      const safeUrl = safeLinkUrl(node.url);
      const linkChildren = (node.children ?? []) as unknown[];
      for (const linkChild of linkChildren) {
        if (!linkChild || typeof linkChild !== "object") continue;
        const inner = linkChild as Record<string, unknown>;
        if (inner.type !== "text" || typeof inner.text !== "string") continue;
        const format = typeof inner.format === "number" ? inner.format : 0;
        const existing = { ...(decodeFormat(format) ?? {}), ...(decodeStyle(inner.style) ?? {}) };
        const style: TextStyle | undefined = safeUrl
          ? { ...existing, link: safeUrl }
          : Object.keys(existing).length > 0 ? existing : undefined;
        items.push({ text: inner.text, ...(style ? { style } : {}) });
      }
    }
  }
  return items;
}

/** Flatten a list node's items into a single block's items list.
 *
 * Lexical's serialized list shape is ``list → listitem → text`` (the text
 * node sits directly under the listitem). The encoder keeps that native flat
 * shape and accepts paragraph wrappers too so older editor state can still
 * be loaded. */
function flattenListItems(listNode: Record<string, unknown>): RichTextItem[] {
  const items: RichTextItem[] = [];
  const children = (listNode.children ?? []) as unknown[];
  for (const child of children) {
    if (!child || typeof child !== "object") continue;
    const item = child as Record<string, unknown>;
    const itemChildren = (item.children ?? []) as unknown[];
    const directRuns = decodeChildren(itemChildren);
    const runs = directRuns.length > 0
      ? directRuns
      : itemChildren.flatMap((paragraph) => {
          if (!paragraph || typeof paragraph !== "object") return [];
          const para = paragraph as Record<string, unknown>;
          return decodeChildren((para.children ?? []) as unknown[]);
        });
    if (runs.length === 0) continue;

    // RichTextBlock's list contract is intentionally flat: one item is one
    // saved run. If an imported/pasted Lexical item contains multiple runs,
    // retain its text and the first run's supported style rather than
    // accidentally turning one bullet into several bullets.
    const first = runs[0];
    const text = runs.map((run) => run.text).join("");
    items.push({ text, ...(first.style ? { style: first.style } : {}) });
  }
  return items;
}

/** Convert a Lexical ``SerializedEditorState`` to ``RichTextBlock[]``. */
export function lexicalToBlocks(state: SerializedEditorState): RichTextBlock[] {
  const root = state.root;
  if (!root || !Array.isArray(root.children)) return [];

  const blocks: RichTextBlock[] = [];

  for (const node of root.children) {
    if (!node || typeof node !== "object") continue;
    const n = node as Record<string, unknown>;

    if (n.type === "paragraph") {
      const children = (n.children ?? []) as unknown[];
      const items = decodeChildren(children);
      // Skip empty paragraphs (Lexical always has one trailing empty paragraph)
      if (items.length === 0 && blocks.length > 0) continue;
      blocks.push({ type: "paragraph", items });
    } else if (n.type === "list") {
      const listType = n.listType;
      const type: RichTextBlock["type"] =
        listType === "number" ? "numbered_list" : "bullet_list";
      const items = flattenListItems(n);
      if (items.length > 0) {
        blocks.push({ type, items });
      }
    }
  }

  return blocks;
}

// ---------------------------------------------------------------------------
// RichTextBlock[] → Lexical JSON
// ---------------------------------------------------------------------------

/** Encode a TextStyle into a Lexical format bitmask. */
function encodeFormat(style: TextStyle | undefined | null): number {
  if (!style) return 0;
  let format = 0;
  if (style.bold) format |= 1;
  if (style.italic) format |= 2;
  if (style.strike) format |= 4;
  if (style.underline) format |= 8;
  return format;
}

function encodeStyle(style: TextStyle | undefined | null): string {
  if (!style) return "";
  const declarations: string[] = [];
  if (style.font_size && FONT_SIZE_CSS[style.font_size]) {
    declarations.push(`font-size:${FONT_SIZE_CSS[style.font_size]}`);
  }
  if (style.color && SAFE_HEX_COLOR.test(style.color)) {
    declarations.push(`color:${style.color}`);
  }
  return declarations.join(";");
}

/** Convert RichTextItems to Lexical text/link nodes, grouping consecutive
 * linked runs under a single ``link`` wrapper. */
function encodeTextNodes(items: RichTextItem[]): unknown[] {
  const nodes: unknown[] = [];
  let pendingLink: { url: string; runs: unknown[] } | null = null;
  const flushLink = () => {
    if (!pendingLink) return;
    nodes.push({
      type: "link",
      url: pendingLink.url,
      children: pendingLink.runs,
      version: 1,
    });
    pendingLink = null;
  };
  for (const item of items) {
    const link = safeLinkUrl(item.style?.link ?? null);
    const run = {
      type: "text",
      text: item.text,
      format: encodeFormat(item.style),
      style: encodeStyle(item.style),
      detail: 0,
      mode: "normal",
      version: 1,
    };
    if (link && pendingLink && pendingLink.url === link) {
      pendingLink.runs.push(run);
    } else if (link) {
      flushLink();
      pendingLink = { url: link, runs: [run] };
    } else {
      flushLink();
      nodes.push(run);
    }
  }
  flushLink();
  return nodes;
}

/** Build a Lexical list node from a RichTextBlock. */
function encodeList(block: RichTextBlock): unknown {
  const listType = block.type === "numbered_list" ? "number" : "bullet";
  const tag = block.type === "numbered_list" ? "ol" : "ul";

  const listItems = (block.items ?? []).map((item) => ({
    type: "listitem",
    value: 1,
    checked: undefined,
    version: 1,
    // Keep each list item as exactly one text run in the Lexical tree. A
    // link wrapper is the only permitted inline container for that run.
    children: encodeTextNodes([item]),
    direction: null,
    format: "",
    indent: 0,
  }));

  return {
    type: "list",
    listType,
    start: 1,
    tag,
    children: listItems,
    direction: null,
    format: "",
    indent: 0,
    version: 1,
  };
}

/** Convert ``RichTextBlock[]`` (or a legacy plain string) to Lexical JSON. */
export function blocksToLexical(
  blocks: RichTextBlock[] | string | undefined | null
): SerializedEditorState {
  // Legacy plain string → single paragraph
  let normalized: RichTextBlock[];
  if (typeof blocks === "string") {
    normalized = blocks ? [{ type: "paragraph", items: [{ text: blocks }] }] : [];
  } else if (Array.isArray(blocks)) {
    normalized = blocks;
  } else {
    normalized = [];
  }

  const children = normalized.map((block) => {
    if (block.type === "paragraph") {
      return {
        type: "paragraph",
        children: encodeTextNodes(block.items ?? []),
        direction: "ltr",
        format: "",
        indent: 0,
        version: 1,
        textFormat: 0,
        textStyle: "",
      };
    }
    return encodeList(block);
  });

  // Lexical always expects at least one child (trailing empty paragraph)
  if (children.length === 0) {
    children.push({
      type: "paragraph",
      children: [],
      direction: "ltr",
      format: "",
      indent: 0,
      version: 1,
      textFormat: 0,
      textStyle: "",
    });
  }

  return {
    root: {
      type: "root",
      children,
      direction: "ltr",
      format: "",
      indent: 0,
      version: 1,
    },
  } as SerializedEditorState;
}
