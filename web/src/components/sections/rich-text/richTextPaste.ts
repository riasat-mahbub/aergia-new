import { FONT_SIZE_CSS } from "../../../styles/tokens";
import { safeLinkUrl } from "../../../lib/security/safeUrl";

const FONT_SIZE_VALUES = new Set(Object.values(FONT_SIZE_CSS));
const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;
const ALLOWED_TAGS = new Set([
  "P", "BR", "STRONG", "B", "EM", "I", "U", "S", "STRIKE", "DEL", "A",
  "UL", "OL", "LI", "SPAN",
]);
const REMOVE_WITH_CONTENT = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED", "SVG", "MATH", "IMG", "VIDEO", "AUDIO"]);
const PARAGRAPH_TAGS = new Set(["DIV", "SECTION", "ARTICLE", "HEADER", "FOOTER", "H1", "H2", "H3", "H4", "H5", "H6"]);

function cleanStyle(value: string): string {
  const safe: string[] = [];
  for (const declaration of value.split(";")) {
    const separator = declaration.indexOf(":");
    if (separator < 0) continue;
    const property = declaration.slice(0, separator).trim().toLowerCase();
    const rawValue = declaration.slice(separator + 1).trim();
    if (property === "font-size" && FONT_SIZE_VALUES.has(rawValue)) {
      safe.push(`${property}:${rawValue}`);
    } else if (property === "color" && HEX_COLOR.test(rawValue)) {
      safe.push(`${property}:${rawValue}`);
    } else if (property === "font-weight" && /^(?:400|500|600|700|normal|bold)$/.test(rawValue)) {
      safe.push(`${property}:${rawValue}`);
    } else if (property === "font-style" && /^(?:normal|italic)$/.test(rawValue)) {
      safe.push(`${property}:${rawValue}`);
    } else if (property === "text-decoration" && /^(?:none|underline|line-through)(?:\s+(?:underline|line-through))?$/.test(rawValue)) {
      safe.push(`${property}:${rawValue}`);
    }
  }
  return safe.join(";");
}

function unwrap(element: Element): void {
  const parent = element.parentNode;
  if (!parent) return;
  while (element.firstChild) parent.insertBefore(element.firstChild, element);
  element.remove();
}

function cleanElement(element: Element): void {
  for (const child of [...element.childNodes]) {
    if (child.nodeType !== Node.ELEMENT_NODE) {
      if (child.nodeType === Node.COMMENT_NODE) child.remove();
      continue;
    }
    const childElement = child as Element;
    const tag = childElement.tagName;
    if (REMOVE_WITH_CONTENT.has(tag)) {
      childElement.remove();
      continue;
    }
    if (PARAGRAPH_TAGS.has(tag)) {
      const paragraph = childElement.ownerDocument.createElement("p");
      while (childElement.firstChild) paragraph.appendChild(childElement.firstChild);
      childElement.replaceWith(paragraph);
      cleanElement(paragraph);
      continue;
    }
    if (!ALLOWED_TAGS.has(tag)) {
      unwrap(childElement);
      continue;
    }

    if (tag === "A") {
      const safeUrl = safeLinkUrl(childElement.getAttribute("href"));
      for (const attribute of [...childElement.attributes]) childElement.removeAttribute(attribute.name);
      if (safeUrl) childElement.setAttribute("href", safeUrl);
      else {
        unwrap(childElement);
        continue;
      }
    } else {
      const style = cleanStyle(childElement.getAttribute("style") ?? "");
      for (const attribute of [...childElement.attributes]) childElement.removeAttribute(attribute.name);
      if (style) childElement.setAttribute("style", style);
    }
    cleanElement(childElement);
  }

  // A nested list would be rendered as a nested list node and cannot be
  // represented by RichTextBlock[]. Promote its items into the current flat
  // list while retaining their order.
  if (element.tagName === "UL" || element.tagName === "OL") {
    for (const item of [...element.children]) {
      if (item.tagName !== "LI") continue;
      for (const nested of [...item.children]) {
        if (nested.tagName !== "UL" && nested.tagName !== "OL") continue;
        const followingItem = item.nextElementSibling;
        for (const nestedItem of [...nested.children]) {
          if (nestedItem.tagName === "LI") element.insertBefore(nestedItem, followingItem);
        }
        nested.remove();
      }
    }
  }
}

/**
 * Sanitize pasted HTML to the small rich-text vocabulary supported by the
 * editor. The result is safe to feed into Lexical's DOM importer.
 */
export function sanitizeRichTextHtml(html: string): string {
  if (typeof DOMParser === "undefined") return "";
  const document = new DOMParser().parseFromString(html, "text/html");
  cleanElement(document.body);
  return document.body.innerHTML;
}
