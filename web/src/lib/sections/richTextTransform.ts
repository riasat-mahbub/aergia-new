/** Bidirectional transform between Lexical JSON and RichTextBlock[].

Lexical stores documents as a tree of ``SerializedLexicalNode`` objects.
Our backend stores descriptions as ``RichTextBlock[]`` (paragraphs and lists
with inline-styled runs).  This module converts between the two formats so
the editor can work with Lexical's native model while the wire format stays
backend-friendly.
*/

import type { SerializedEditorState } from "lexical";
import type { RichTextBlock, RichTextItem, TextStyle } from "../../generated/schema";

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

/** Extract text items from Lexical inline children (text nodes and link wrappers). */
function decodeChildren(children: unknown[]): RichTextItem[] {
  const items: RichTextItem[] = [];
  for (const child of children) {
    if (!child || typeof child !== "object") continue;
    const node = child as Record<string, unknown>;
    if (node.type === "text" && typeof node.text === "string") {
      const format = typeof node.format === "number" ? node.format : 0;
      const style = decodeFormat(format);
      items.push({ text: node.text, ...(style ? { style } : {}) });
    } else if (node.type === "link" && typeof node.url === "string") {
      // LinkNode wraps text children; propagate its `url` to every child run.
      const linkChildren = (node.children ?? []) as unknown[];
      for (const linkChild of linkChildren) {
        if (!linkChild || typeof linkChild !== "object") continue;
        const inner = linkChild as Record<string, unknown>;
        if (inner.type !== "text" || typeof inner.text !== "string") continue;
        const format = typeof inner.format === "number" ? inner.format : 0;
        const existing = decodeFormat(format);
        const style: TextStyle = { ...(existing ?? {}), link: node.url };
        items.push({ text: inner.text, style });
      }
    }
  }
  return items;
}

/** Flatten a list node's items into a single block's items list.
 *
 * Lexical's serialized list shape is ``list → listitem → text`` (the text
 * node sits directly under the listitem). Our encoder wraps each text run in
 * a ``listitem → paragraph → text`` shape so the rendered DOM matches
 * ``<li><p>...</p></li>``; we accept both shapes on decode so we can round-
 * trip our own output as well as Lexical's native output. */
function flattenListItems(listNode: Record<string, unknown>): RichTextItem[] {
  const items: RichTextItem[] = [];
  const children = (listNode.children ?? []) as unknown[];
  for (const child of children) {
    if (!child || typeof child !== "object") continue;
    const item = child as Record<string, unknown>;
    const itemChildren = (item.children ?? []) as unknown[];
    if (itemChildren.length === 1 && (itemChildren[0] as Record<string, unknown>)?.type === "text") {
      // Native Lexical shape: listitem > text.
      items.push(...decodeChildren(itemChildren));
      continue;
    }
    // Our encoder shape: listitem > paragraph > text.
    for (const paragraph of itemChildren) {
      if (!paragraph || typeof paragraph !== "object") continue;
      const para = paragraph as Record<string, unknown>;
      const paraChildren = (para.children ?? []) as unknown[];
      items.push(...decodeChildren(paraChildren));
    }
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
    const link = item.style?.link ?? null;
    const run = {
      type: "text",
      text: item.text,
      format: encodeFormat(item.style),
      style: "",
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
    children: [
      {
        type: "text",
        text: item.text,
        format: encodeFormat(item.style),
        style: "",
        detail: 0,
        mode: "normal",
        version: 1,
      },
    ],
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
