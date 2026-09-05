import {
  $createTextNode,
  $getSelection,
  $isRangeSelection,
  $isTextNode,
  type LexicalEditor,
} from "lexical";
import { $createLinkNode, type LinkNode } from "@lexical/link";
import { linkForNode, listItemsInSelection, textDescendants } from "./selection";

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
    const listItems = listItemsInSelection(selection);
    const links = listItems.length > 0
      ? listItems.flatMap(textDescendants).map(linkForNode).filter((link): link is LinkNode => link !== null)
      : linksInSelection(selection);
    const seen = new Set<string>();
    for (const link of links) {
      if (!seen.has(link.getKey())) {
        seen.add(link.getKey());
        unwrapLink(link);
      }
    }
  });
}

/** Apply one manual or automatic URL to every affected flat list item. */
export function setListItemsLink(selection: ReturnType<typeof $getSelection>, url: string | null): boolean {
  if (!$isRangeSelection(selection)) return false;
  const listItems = listItemsInSelection(selection);
  if (listItems.length === 0) return false;
  if (url === null) {
    const links = listItems.flatMap(textDescendants).map(linkForNode).filter((link): link is LinkNode => link !== null);
    const seen = new Set<string>();
    for (const link of links) {
      if (!seen.has(link.getKey())) {
        seen.add(link.getKey());
        unwrapLink(link);
      }
    }
    return true;
  }
  for (const item of listItems) {
    const source = textDescendants(item)[0];
    const text = $createTextNode(item.getTextContent());
    if (source) text.setFormat(source.getFormat()).setStyle(source.getStyle());
    item.clear().append($createLinkNode(url, { rel: "noreferrer" }).append(text));
  }
  return true;
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
    const links = listItems.length > 0
      ? listItems.flatMap(textDescendants).map(linkForNode).filter((link): link is LinkNode => link !== null)
      : linksInSelection(selection);
    const seen = new Set<string>();
    for (const link of links) {
      if (!seen.has(link.getKey())) {
        seen.add(link.getKey());
        unwrapLink(link);
      }
    }
  });
}
