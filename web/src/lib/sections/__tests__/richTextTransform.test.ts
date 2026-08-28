import { describe, it, expect } from "vitest";
import { lexicalToBlocks, blocksToLexical } from "../richTextTransform";
import type { SerializedEditorState } from "lexical";

describe("lexicalToBlocks", () => {
  it("converts a single paragraph with plain text", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "paragraph",
            children: [{ type: "text", text: "Hello world", format: 0 }],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([
      { type: "paragraph", items: [{ text: "Hello world" }] },
    ]);
  });

  it("converts paragraph with bold and italic text", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "paragraph",
            children: [
              { type: "text", text: "normal ", format: 0 },
              { type: "text", text: "bold", format: 1 },
              { type: "text", text: " and ", format: 0 },
              { type: "text", text: "italic", format: 2 },
            ],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([
      {
        type: "paragraph",
        items: [
          { text: "normal " },
          { text: "bold", style: { bold: true } },
          { text: " and " },
          { text: "italic", style: { italic: true } },
        ],
      },
    ]);
  });

  it("converts a bullet list", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "list",
            listType: "bullet",
            tag: "ul",
            children: [
              {
                type: "listitem",
                children: [
                  {
                    type: "paragraph",
                    children: [{ type: "text", text: "Item 1", format: 0 }],
                  },
                ],
              },
              {
                type: "listitem",
                children: [
                  {
                    type: "paragraph",
                    children: [{ type: "text", text: "Item 2", format: 0 }],
                  },
                ],
              },
            ],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([
      {
        type: "bullet_list",
        items: [{ text: "Item 1" }, { text: "Item 2" }],
      },
    ]);
  });

  it("converts a numbered list", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "list",
            listType: "number",
            tag: "ol",
            children: [
              {
                type: "listitem",
                children: [
                  {
                    type: "paragraph",
                    children: [{ type: "text", text: "First", format: 0 }],
                  },
                ],
              },
            ],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([
      { type: "numbered_list", items: [{ text: "First" }] },
    ]);
  });

  it("converts mixed paragraph and list", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "paragraph",
            children: [{ type: "text", text: "Summary paragraph", format: 0 }],
          },
          {
            type: "list",
            listType: "bullet",
            tag: "ul",
            children: [
              {
                type: "listitem",
                children: [
                  {
                    type: "paragraph",
                    children: [{ type: "text", text: "Bullet item", format: 0 }],
                  },
                ],
              },
            ],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([
      { type: "paragraph", items: [{ text: "Summary paragraph" }] },
      { type: "bullet_list", items: [{ text: "Bullet item" }] },
    ]);
  });

  it("decodes Lexical's native list shape (list > listitem > text)", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "list",
            listType: "bullet",
            tag: "ul",
            start: 1,
            children: [
              {
                type: "listitem",
                value: 1,
                children: [{ type: "text", text: "Alpha", format: 0 }],
              },
              {
                type: "listitem",
                value: 2,
                children: [{ type: "text", text: "Beta", format: 0 }],
              },
            ],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([
      {
        type: "bullet_list",
        items: [{ text: "Alpha" }, { text: "Beta" }],
      },
    ]);
  });
  it("skips empty trailing paragraphs", () => {
    const state = {
      root: {
        type: "root",
        children: [
          { type: "paragraph", children: [{ type: "text", text: "Content", format: 0 }] },
          { type: "paragraph", children: [] },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([{ type: "paragraph", items: [{ text: "Content" }] }]);
  });

  it("returns empty array for empty root", () => {
    const state = {
      root: { type: "root", children: [] },
    } as unknown as SerializedEditorState;

    expect(lexicalToBlocks(state)).toEqual([]);
  });
});

describe("blocksToLexical", () => {
  it("converts a plain string to single paragraph", () => {
    const state = blocksToLexical("Hello world");
    expect(state.root.children).toHaveLength(1);
    const para = state.root.children[0] as any;
    expect(para.type).toBe("paragraph");
    expect(para.children[0].text).toBe("Hello world");
    expect(para.children[0].format).toBe(0);
  });

  it("converts paragraph blocks to Lexical paragraphs", () => {
    const blocks = [
      { type: "paragraph" as const, items: [{ text: "Hello " }, { text: "world", style: { bold: true } }] },
    ];
    const state = blocksToLexical(blocks);
    const para = state.root.children[0] as any;
    expect(para.type).toBe("paragraph");
    expect(para.children).toHaveLength(2);
    expect(para.children[0].text).toBe("Hello ");
    expect(para.children[0].format).toBe(0);
    expect(para.children[1].text).toBe("world");
    expect(para.children[1].format).toBe(1); // bold
  });

  it("converts bullet list blocks to Lexical lists", () => {
    const blocks = [
      { type: "bullet_list" as const, items: [{ text: "Item 1" }, { text: "Item 2" }] },
    ];
    const state = blocksToLexical(blocks);
    const list = state.root.children[0] as any;
    expect(list.type).toBe("list");
    expect(list.listType).toBe("bullet");
    expect(list.tag).toBe("ul");
    expect(list.children).toHaveLength(2);
    expect(list.children[0].type).toBe("listitem");
  });

  it("encodes a linked, sized list item as one link-wrapped run", () => {
    const state = blocksToLexical([
      {
        type: "bullet_list" as const,
        items: [{ text: "Read", style: { link: "https://example.com", font_size: "xl", italic: true } }],
      },
    ]);
    const item = (state.root.children[0] as any).children[0];
    expect(item.children).toHaveLength(1);
    expect(item.children[0].type).toBe("link");
    expect(item.children[0].url).toBe("https://example.com");
    expect(item.children[0].children[0]).toEqual(expect.objectContaining({ format: 2, style: "font-size:1.25rem" }));
  });

  it("converts numbered list blocks to Lexical numbered lists", () => {
    const blocks = [
      { type: "numbered_list" as const, items: [{ text: "First" }] },
    ];
    const state = blocksToLexical(blocks);
    const list = state.root.children[0] as any;
    expect(list.listType).toBe("number");
    expect(list.tag).toBe("ol");
  });

  it("handles empty array", () => {
    const state = blocksToLexical([]);
    // Lexical always expects at least one child
    expect(state.root.children).toHaveLength(1);
    expect((state.root.children[0] as any).type).toBe("paragraph");
  });

  it("handles null/undefined", () => {
    const state = blocksToLexical(null);
    expect(state.root.children).toHaveLength(1);
    expect((state.root.children[0] as any).type).toBe("paragraph");
  });

  it("round-trips through encode/decode", () => {
    const original = [
      { type: "paragraph" as const, items: [{ text: "Hello " }, { text: "bold", style: { bold: true } }] },
      { type: "bullet_list" as const, items: [{ text: "Item 1" }, { text: "Item 2" }] },
    ];
    const lexState = blocksToLexical(original);
    const decoded = lexicalToBlocks(lexState);
    expect(decoded).toEqual(original);
  });

  it("decodes a link wrapper into a styled item with url", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "paragraph",
            children: [
              { type: "text", text: "Visit ", format: 0 },
              {
                type: "link",
                url: "https://example.com",
                children: [{ type: "text", text: "our site", format: 1 }],
              },
            ],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    const blocks = lexicalToBlocks(state);
    expect(blocks).toEqual([
      {
        type: "paragraph",
        items: [
          { text: "Visit " },
          { text: "our site", style: { bold: true, link: "https://example.com" } },
        ],
      },
    ]);
  });

  it("decodes supported text-node sizes and colors", () => {
    const state = {
      root: {
        type: "root",
        children: [{
          type: "paragraph",
          children: [{ type: "text", text: "Large", format: 0, style: "font-size:1.125rem;color:#abc" }],
        }],
      },
    } as unknown as SerializedEditorState;

    expect(lexicalToBlocks(state)).toEqual([
      { type: "paragraph", items: [{ text: "Large", style: { font_size: "large", color: "#abc" } }] },
    ]);
  });

  it("ignores unsupported inline CSS values", () => {
    const state = {
      root: {
        type: "root",
        children: [{
          type: "paragraph",
          children: [{ type: "text", text: "Styled", format: 0, style: "font-size:22px;color:red;background:url(javascript:bad)" }],
        }],
      },
    } as unknown as SerializedEditorState;

    expect(lexicalToBlocks(state)).toEqual([{ type: "paragraph", items: [{ text: "Styled" }] }]);
  });

  it("preserves a persisted palette color through the Lexical style field", () => {
    const blocks = [{ type: "paragraph" as const, items: [{ text: "Accent", style: { color: "palette.accent" } }] }];
    const state = blocksToLexical(blocks);
    expect((state.root.children[0] as any).children[0].style).toBe("color:var(--palette-accent)");
    expect(lexicalToBlocks(state)).toEqual(blocks);
  });

  it("keeps a linked list item as one saved run", () => {
    const state = {
      root: {
        type: "root",
        children: [{
          type: "list",
          listType: "bullet",
          children: [{
            type: "listitem",
            children: [{
              type: "link",
              url: "https://example.com",
              children: [{ type: "text", text: "Read more", format: 1, style: "font-size:0.875rem" }],
            }],
          }],
        }],
      },
    } as unknown as SerializedEditorState;

    expect(lexicalToBlocks(state)).toEqual([
      { type: "bullet_list", items: [{ text: "Read more", style: { bold: true, font_size: "small", link: "https://example.com" } }] },
    ]);
  });

  it("encodes consecutive linked items as a single link wrapper", () => {
    const blocks = [
      {
        type: "paragraph" as const,
        items: [
          { text: "Visit " },
          { text: "our site", style: { link: "https://example.com" } },
          { text: " today", style: { link: "https://example.com" } },
        ],
      },
    ];
    const state = blocksToLexical(blocks);
    const para = state.root.children[0] as unknown as { children: unknown[] };
    expect(para.children).toHaveLength(2);
    const first = (para.children[0] as Record<string, unknown>);
    const second = (para.children[1] as Record<string, unknown>);
    expect(first.type).toBe("text");
    expect(second.type).toBe("link");
    expect((second as { url: string }).url).toBe("https://example.com");
    expect((second as { children: unknown[] }).children).toHaveLength(2);
  });

  it("drops an unsafe link from a legacy Lexical node while preserving its text", () => {
    const state = {
      root: {
        type: "root",
        children: [
          {
            type: "paragraph",
            children: [
              {
                type: "link",
                url: "javascript:alert(1)",
                children: [{ type: "text", text: "unsafe", format: 1 }],
              },
            ],
          },
        ],
      },
    } as unknown as SerializedEditorState;

    expect(lexicalToBlocks(state)).toEqual([
      { type: "paragraph", items: [{ text: "unsafe", style: { bold: true } }] },
    ]);
  });

  it("does not encode an unsafe persisted link into a Lexical link node", () => {
    const state = blocksToLexical([
      {
        type: "paragraph",
        items: [{ text: "unsafe", style: { link: "data:text/html,boom" } }],
      },
    ]);
    const paragraph = state.root.children[0] as unknown as { children: unknown[] };
    expect(paragraph.children).toEqual([
      expect.objectContaining({ type: "text", text: "unsafe" }),
    ]);
  });

  it("splits link wrappers when the URL changes between items", () => {
    const blocks = [
      {
        type: "paragraph" as const,
        items: [
          { text: "A", style: { link: "https://a.test" } },
          { text: "B", style: { link: "https://b.test" } },
        ],
      },
    ];
    const state = blocksToLexical(blocks);
    const para = state.root.children[0] as unknown as { children: unknown[] };
    expect(para.children).toHaveLength(2);
    expect((para.children[0] as { url: string }).url).toBe("https://a.test");
    expect((para.children[1] as { url: string }).url).toBe("https://b.test");
  });

  it("round-trips linked items back to identical blocks", () => {
    const original = [
      {
        type: "paragraph" as const,
        items: [
          { text: "See " },
          { text: "docs", style: { link: "https://docs.test", italic: true } },
        ],
      },
    ];
    const lexState = blocksToLexical(original);
    const decoded = lexicalToBlocks(lexState);
    expect(decoded).toEqual(original);
  });
});
