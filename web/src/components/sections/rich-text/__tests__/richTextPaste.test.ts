import { describe, expect, it } from "vitest";
import { sanitizeRichTextHtml } from "../richTextPaste";

describe("sanitizeRichTextHtml", () => {
  it("keeps supported formatting and strips unsafe attributes", () => {
    const html = sanitizeRichTextHtml(
      '<p onclick="alert(1)"><strong>Bold</strong> <span style="font-size:1.125rem;color:#abc;position:fixed">text</span></p><script>alert(2)</script>',
    );

    expect(html).toContain("<strong>Bold</strong>");
    expect(html).toContain('style="font-size:1.125rem;color:#abc"');
    expect(html).not.toContain("onclick");
    expect(html).not.toContain("script");
    expect(html).not.toContain("position");
  });

  it("keeps safe links and unwraps unsafe links", () => {
    const html = sanitizeRichTextHtml(
      '<p><a href="https://example.com" target="_blank">safe</a> <a href="javascript:alert(1)">unsafe</a></p>',
    );

    expect(html).toContain('<a href="https://example.com">safe</a>');
    expect(html).toContain("unsafe");
    expect(html).not.toContain("javascript:");
    expect(html).not.toContain("target");
  });

  it("promotes nested list items into one flat list", () => {
    const html = sanitizeRichTextHtml(
      "<ul><li>One<ul><li>Nested</li></ul></li><li>Two</li></ul>",
    );
    const document = new DOMParser().parseFromString(html, "text/html");
    const list = document.querySelector("ul");

    expect(list).not.toBeNull();
    expect(list?.querySelector("ul")).toBeNull();
    expect([...list!.children].map((item) => item.textContent)).toEqual(["One", "Nested", "Two"]);
  });
});
