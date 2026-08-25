"""HTML renderer — emits a complete HTML5 document from a :class:`RenderModel`.

The renderer is almost stupid: it receives a fully resolved
:class:`RenderModel` and emits HTML. No decision logic. No defaults. No
policy resolution. The Resolver owns those.

The renderer's :class:`RendererSupport` declares the HTML renderer's
capabilities:

- ``break_before`` is ``FULL`` because Chromium honours
  ``break-before: page``.
- ``keep_with_next`` / ``keep_together`` / ``heading_keeps_with_first``
  are ``BEST_EFFORT`` because Chromium honours ``break-inside: avoid``
  and ``break-after: avoid`` only when other constraints allow it.

The renderer emits a ``<!-- best-effort: <feature> -->`` HTML comment for
each ``BEST_EFFORT`` feature it uses, so debugging the live preview and
the PDF is straightforward.

CSS knowledge lives in this module (the renderer is the source of CSS
knowledge — the manifest only carries values).
"""

from __future__ import annotations

import html as _stdlib_html
import re

from app.schema.models import (
    Entry,
    FieldBlock,
    LayoutHints,
    RenderModel,
    ResolvedZone,
    RichTextBlock,
    Section,
    SectionPolicy,
    SubsectionStyle,
    TextRun,
    TextStyle,
)
from app.services.renderer.support import RendererSupport, SupportLevel
from app.services.renderer.base import DocumentRenderer


_FONT_SIZE_TO_CSS: dict[str, str] = {
    "xs": "0.75rem",
    "small": "0.875rem",
    "normal": "1rem",
    "large": "1.125rem",
    "xl": "1.25rem",
}


# Brand icon table: name -> inline SVG markup (24x24, currentColor).
# Brand marks are filled paths sourced from simpleicons.org (CC0).
# https://simpleicons.org — paths fetched from the official ``simple-icons``
# package and embedded here so the renderer ships zero runtime fetch.
# ``x`` and ``twitter`` share the same X (rebrand) glyph since Twitter was
# rebranded to X; the dict keeps both keys so older CVs keep rendering.
# Generic glyphs (``globe``/``mail``/``phone``/``link``) are utility icons
# kept as hand-drawn lucide-style outlines (lucide.dev, ISC).
_SOCIAL_ICONS: dict[str, str] = {
    "github": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>',
    "x": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z"/></svg>',
    "twitter": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378 7.0301.084"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
    "mastodon": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309C3.882.692 1.496 2.518.917 5.127.64 6.412.61 7.837.661 9.143c.074 1.874.088 3.745.26 5.611.118 1.24.325 2.47.62 3.68.55 2.237 2.777 4.098 4.96 4.857 2.336.792 4.849.923 7.256.38.265-.061.527-.132.786-.213.585-.184 1.27-.39 1.774-.753a.057.057 0 0 0 .023-.043v-1.809a.052.052 0 0 0-.02-.041.053.053 0 0 0-.046-.01 20.282 20.282 0 0 1-4.709.545c-2.73 0-3.463-1.284-3.674-1.818a5.593 5.593 0 0 1-.319-1.433.053.053 0 0 1 .066-.054c1.517.363 3.072.546 4.632.546.376 0 .75 0 1.125-.01 1.57-.044 3.224-.124 4.768-.422.038-.008.077-.015.11-.024 2.435-.464 4.753-1.92 4.989-5.604.008-.145.03-1.52.03-1.67.002-.512.167-3.63-.024-5.545zm-3.748 9.195h-2.561V8"/></svg>',
    "medium": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.21 0A4.201 4.201 0 0 0 0 4.21v15.58A4.201 4.201 0 0 0 4.21 24h15.58A4.201 4.201 0 0 0 24 19.79v-1.093c-.137.013-.278.02-.422.02-2.577 0-4.027-2.146-4.09-4.832a7.592 7.592 0 0 1 .022-.708c.093-1.186.475-2.241 1.105-3.022a3.885 3.885 0 0 1 1.395-1.1c.468-.237 1.127-.367 1.664-.367h.023c.101 0 .202.004.303.01V4.211A4.201 4.201 0 0 0 19.79 0Zm.198 5.583h4.165l3.588 8.435 3.59-8.435h3.864v.146l-.019.004c-.705.16-1.063.397-1.063 1.254h-.003l.003 10.274c.06.676.424.885 1.063 1.03l.02.004v.145h-4.923v-.145l.019-.005c.639-.144.994-.353 1.054-1.03V7.267l-4.745 11.15h-.261L6.15 7.569v9.445c0 .857.358 1.094 1.063 1.253l.02.004v.147H4.405v-.147l.019-.004c.705-.16 1.065-.397 1.065-1.253V6.987c0-.857-.358-1.094-1.064-1.254l-.018-.004z"/></svg>',
    "stackoverflow": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M15.725 0l-1.72 1.277 6.39 8.588 1.716-1.277L15.725 0zm-3.94 3.418l-1.369 1.644 8.225 6.85 1.369-1.644-8.225-6.85zm-3.15 4.465l-.905 1.94 9.702 4.517.904-1.94-9.701-4.517zm-1.85 4.86l-.44 2.093 10.473 2.201.44-2.092-10.473-2.203zM1.89 15.47V24h19.19v-8.53h-2.133v6.397H4.021v-6.396H1.89zm4.265 2.133v2.13h10.66v-2.13H6.154Z"/></svg>',
    "behance": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.969 16.927a2.561 2.561 0 0 0 1.901.677 2.501 2.501 0 0 0 1.531-.475c.362-.235.636-.584.779-.99h2.585a5.091 5.091 0 0 1-1.9 2.896 5.292 5.292 0 0 1-3.091.88 5.839 5.839 0 0 1-2.284-.433 4.871 4.871 0 0 1-1.723-1.211 5.657 5.657 0 0 1-1.08-1.874 7.057 7.057 0 0 1-.383-2.393c-.005-.8.129-1.595.396-2.349a5.313 5.313 0 0 1 5.088-3.604 4.87 4.87 0 0 1 2.376.563c.661.362 1.231.87 1.668 1.485a6.2 6.2 0 0 1 .943 2.133c.194.821.263 1.666.205 2.508h-7.699c-.063.79.184 1.574.688 2.187ZM6.947 4.084a8.065 8.065 0 0 1 1.928.198 4.29 4.29 0 0 1 1.49.638c.418.303.748.711.958 1.182.241.579.357 1.203.341 1.83a3.506 3.506 0 0 1-.506 1.961 3.726 3.726 0 0 1-1.503 1.287 3.588 3.588 0 0 1 2.027 1.437c.464.747.697 1.615.67 2.494a4.593 4.593 0 0 1-.423 2.032 3.945 3.9 7.505 0 0 1-7.143 7.143"/></svg>',
    "dribbble": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 24C5.385 24 0 18.615 0 12S5.385 0 12 0s12 5.385 12 12-5.385 12-12 12zm10.12-10.358c-.35-.11-3.17-.953-6.384-.438 1.34 3.684 1.887 6.684 1.992 7.308 2.3-1.555 3.936-4.02 4.395-6.87zm-6.115 7.808c-.153-.9-.75-4.032-2.19-7.77l-.066.02c-5.79 2.015-7.86 6.025-8.04 6.4 1.73 1.358 3.92 2.166 6.29 2.166 1.42 0 2.77-.29 4-.814zm-11.62-2.58c.232-.4 3.045-5.055 8.332-6.765.135-.045.27-.084.405-.12-.26-.585-.54-1.167-.832-1.74C7.17 11.775 2.206 11.71 1.756 11.7l-.004.312c0 2.633.998 5.037 2.634 6.855zm-2.42-8.955c.46.008 4.683.026 9.477-1.248-1.698-3.018-3.53-5.558-3.8-5.928-2.868 1.35-5.01 3.99-5.676 7.17zM9.6 2.052c.282.38 2.145 2.914 3.822 6 3.645-1.365 5.19-3.44 5.373-3.702-1.81-1.61-4.19-2.586-6.795-2.586-.825 0-1.63.1-2.4.285zm10.335 3.483c-.218.29-.36.6-.424.927-.064.327-.022.66.123.96.144.3.378.554.666.726.288.172.624.262.965.262.34 0 .677-.09.965-.262.288-.172.522-.426.666-.726.145-.3.187-.633.123-.96a1.66 1.66 0 0 0-.424-.927z"/></svg>',
    "gitlab": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="m23.6004 9.5927-.0337-.0862L20.3.9814a.851.851 0 0 0-.3362-.405.8748.8748 0 0 0-.9997.0539.8748.8748 0 0 0-.29.4399l-2.2055 6.748H7.5375l-2.2057-6.748a.8573.8573 0 0 0-.29-.4412.8748.8748 0 0 0-.9997-.0537.8585.8585 0 0 0-.3362.4049L.4332 9.5015l-.0325.0862a6.0657 6.0657 0 0 0 2.0119 7.0105l.0113.0087.03.0213 4.976 3.7264 2.462 1.8633 1.4995 1.1321a1.0085 1.0085 0 0 0 1.2197 0l1.4995-1.1321 2.4619-1.8633 5.006-3.7489.0125-.01a6.0682 6.0682 0 0 0 2.0094-7.003z"/></svg>',
    "globe": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8M3.6 15h16.8M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25H4.5a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5H4.5a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z"/></svg>',
    "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"/></svg>',
}



def h(text: object) -> str:
    """HTML-escape a value for use between tags."""

    if text is None:
        return ""
    return _stdlib_html.escape(str(text))


def attr(text: object) -> str:
    """HTML-escape a value for use in a double-quoted attribute."""

    if text is None:
        return ""
    return _stdlib_html.escape(str(text), quote=True)


def _best_effort_comments(model: RenderModel, support: RendererSupport) -> str:
    if support.keep_together is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: keep_together -->"
    if support.keep_with_next is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: keep_with_next -->"
    if support.heading_keeps_with_first is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: heading_keeps_with_first -->"
    if support.break_before is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: break_before -->"


def _render_css_vars(model: RenderModel) -> str:
    if not model.css_vars:
        return ""
    lines = [f"  {k}: {v};" for k, v in model.css_vars.items() if v]
    return ":root {\n" + "\n".join(lines) + "\n}"


def _format_inline_style(decls: list[str]) -> str:
    decls = [d for d in decls if d]
    return ";".join(decls)


def _text_run_to_style(run: TextRun) -> str:
    """Build an inline-style declaration for a single ``TextRun``."""

    decls: list[str] = []
    style = run.style or TextStyle()
    if style.bold:
        decls.append("font-weight:700")
    if style.italic:
        decls.append("font-style:italic")
    if style.underline:
        decls.append("text-decoration:underline")
    if style.strike:
        decls.append("text-decoration:line-through")
        # Underline + strike both set text-decoration; later wins.
    if style.color:
        decls.append(f"color:{style.color}")
    if style.font_size and style.font_size in _FONT_SIZE_TO_CSS:
        decls.append(f"font-size:{_FONT_SIZE_TO_CSS[style.font_size]}")
    return _format_inline_style(decls)


def _render_text_run(run: TextRun) -> str:
    """Render a single text run as ``<span>…</span>`` (or ``<a>…</a>`` when linked).

    Linked runs append a trailing ``↗`` glyph as plain inline text so it is
    selectable, copy-pastable, and underlined together with the link text.
    A CSS ``::after`` pseudo-element was used previously but Chromium
    silently drops it from PDF text extraction, breaks text selection, and
    does not inherit the link's text-decoration. Keeping it inline matches
    the legacy renderer behavior.
    """

    text = h(run.text)
    style = _text_run_to_style(run)
    if run.style and run.style.link:
        href = attr(run.style.link)
        inner = f'{text}<span aria-hidden="true"> ↗</span>'
        if style:
            return f'<a href="{href}" style="{style}">{inner}</a>'
        return f'<a href="{href}">{inner}</a>'
    if style:
        return f'<span style="{style}">{text}</span>'
    return text


def _render_rich_text_blocks(blocks: list[RichTextBlock]) -> str:
    """Render a list of ``RichTextBlock`` nodes as semantic HTML.

    Paragraphs become ``<p>``, bullet lists become ``<ul><li>…</li></ul>``,
    and numbered lists become ``<ol><li>…</li></ol>``.  Each ``items`` entry
    inside a list block is its own ``<li>`` (the wire format flattens nested
    runs into one ``<li>`` each — the encoder treats them as siblings).
    """
    parts: list[str] = []
    for block in blocks:
        if block.type == "bullet_list":
            items_html = "".join(
                f"<li>{_render_text_run(TextRun(text=item.text, style=item.style))}</li>"
                for item in block.items
            )
            parts.append(f"<ul>{items_html}</ul>")
        elif block.type == "numbered_list":
            items_html = "".join(
                f"<li>{_render_text_run(TextRun(text=item.text, style=item.style))}</li>"
                for item in block.items
            )
            parts.append(f"<ol>{items_html}</ol>")
        else:
            inner = "".join(_render_text_run(TextRun(text=item.text, style=item.style)) for item in block.items)
            parts.append(f"<p>{inner}</p>")
    return "".join(parts)


def _render_field_block(
    block: FieldBlock,
    extra_style: str | None = None,
    chip_keys: list[str] | None = None,
) -> str:
    # Rich text blocks: render as semantic HTML (p/ul/ol)
    if block.blocks:
        inner = _render_rich_text_blocks(block.blocks)
        style = f' style="{extra_style}"' if extra_style else ""
        return f'<div class="f-{attr(block.key)}"{style}>{inner}</div>'

    # Decide whether to hoist the URL onto the wrapper element. Only
    # social/chip fields need the icon+label (or pill) wrapped in a
    # single anchor; other fields keep the link emitted by the text-run
    # pass so the trailing ↗ glyph survives. The builder emits ``key="social"``
    # for each social link; older payloads may use indexed ``social_links.i``
    # keys — match by prefix to support both.
    wants_external_anchor = (
        block.key == "social"
        or block.key.startswith("social_links.")
        or (chip_keys is not None and block.key in chip_keys)
    )
    href: str | None = None
    show_external_marker = False
    runs = list(block.runs)
    if wants_external_anchor and block.runs:
        linked = [r for r in block.runs if r.style and r.style.link]
        if len(linked) == len(block.runs):
            href = linked[0].style.link
            if href:
                show_external_marker = True
                runs = [
                    r.model_copy(update={"style": r.style.model_copy(update={"link": None})})
                    for r in block.runs
                ]
    inner = "".join(_render_text_run(r) for r in runs)
    icon_svg = _SOCIAL_ICONS.get(block.icon) if block.icon else None
    if icon_svg:
        icon_html = f'<span class="f-icon" aria-hidden="true">{icon_svg}</span>'
        inner = f'{icon_html}<span class="f-icon-label">{inner}</span>'
    # When this field key is in the section's chip_keys list, render as an
    # inline pill span instead of a block-level div. The pill style is
    # defined as a CSS rule in the renderer's <style> block.
    if chip_keys and block.key in chip_keys:
        style = f' style="{extra_style}"' if extra_style else ""
        body = f'<span class="f-chip"{style}>{inner}</span>'
        if href:
            return f'<a href="{attr(href)}" class="f-chip-link">{body}</a>'
        return body
    # Social links render inline so adjacent icons sit side-by-side with
    # a consistent horizontal gap (see ``.f-social`` in the document CSS).
    # The block-level div layout would otherwise stack them vertically in
    # the contact row, which reads as the same column as the email/phone.
    if block.key == "social" or block.key.startswith("social_links."):
        style = f' style="{extra_style}"' if extra_style else ""
        body = f'<span class="f-social"{style}>{inner}</span>'
        if href:
            return f'<a class="f-social-link" href="{attr(href)}">{body}</a>'
        return body
    style = f' style="{extra_style}"' if extra_style else ""
    return f'<div class="f-{attr(block.key)}"{style}>{inner}</div>'


def _resolve_row_justify(subsection: SubsectionStyle | None) -> str:
    """Map a section's ``text_align`` to the flex ``justify-content`` value
    used for its field rows. ``None``/``"left"`` keep the default
    ``flex-start``; the renderer never emits an explicit left.
    """
    align = subsection.text_align if subsection else None
    if align == "center":
        return "center"
    if align == "right":
        return "right"
    return "flex-start"

def _split_title_row(
    fields: list,
    chip_keys: list[str] | None,
) -> tuple[list, tuple | None, list]:
    """Split fields into ``(title_fields, paired, rest)``.

    ``title_fields`` is the header cluster for the row's left side —
    the project name, position, degree, etc. — plus any header-group
    right-aligned field (the link) which becomes the right rail.

    ``paired`` is ``(body_field, date_field)`` when the immediate
    pattern is ``date (secondary, right) -> body_field (body)``: the
    date pairs with that body field so both render on the same row
    with body on the left and date right-aligned. ``None`` when no
    such pairing applies.

    ``rest`` is whatever remains after the title row and the paired
    row.

    Promotion isn't applicable (returns ``([], None, list(fields))``)
    when there's no header group or when the first header field is a
    chip.
    """
    if not fields:
        return [], None, list(fields)
    first = fields[0]
    if first.group != "header":
        return [], None, list(fields)
    if chip_keys and first.key in chip_keys:
        return [], None, list(fields)
    # Walk forward while we stay inside the header group. The last
    # right-aligned field within the header group becomes the right
    # rail of the title row.
    i = 1
    while i < len(fields) and fields[i].group == "header":
        if chip_keys and fields[i].key in chip_keys:
            break
        i += 1
    title_fields = list(fields[:i])
    if (
        i < len(fields)
        and fields[i].group != "header"
        and fields[i].align == "right"
        and i + 1 < len(fields)
        and fields[i + 1].group != "header"
        and not (chip_keys and fields[i + 1].key in chip_keys)
    ):
        paired = (fields[i + 1], fields[i])
        rest = list(fields[i + 2 :])
    else:
        paired = None
        rest = list(fields[i:])
    return title_fields, paired, rest


def _render_title_row(fields, chip_keys=None) -> str:
    """Render the title row with the right-aligned link pinned to the top.

    The *last* right-aligned field in the row becomes the rail (via
    ``margin-left:auto``). For project / research / cert entries this is
    the link — the project title and link share the row, with the link
    pinned to the top-right.

    The cluster's first field carries ``max-width: 70%`` and
    ``min-width: 0`` so a long title that wraps to a second line never
    pushes the link off the row. ``align-items: flex-start`` keeps the
    link aligned to the top of the title row (the first line of a
    wrapped title) instead of vertically centered against it.
    ``column-gap`` is 0 so adjacent fields sit flush; ``row-gap`` would
    only matter if the cluster wraps and pushes the rail to a new line.
    """
    right_aligned = [f for f in fields if f.align == "right"]
    rail_field = right_aligned[-1] if right_aligned else None
    base_style = (
        "display:flex;flex-wrap:wrap;align-items:flex-start;"
        "column-gap:0;row-gap:0"
    )
    if rail_field is None:
        inner = "".join(
            _render_field_block(f, chip_keys=chip_keys) for f in fields
        )
        return f'<div class="field-row" style="{base_style}">{inner}</div>'
    cluster_parts: list[str] = []
    for idx, f in enumerate(fields):
        if f is rail_field:
            continue
        extra = "max-width:70%;min-width:0" if idx == 0 else None
        cluster_parts.append(
            _render_field_block(f, extra_style=extra, chip_keys=chip_keys)
        )
    rail_html = _render_field_block(
        rail_field,
        extra_style="margin-left:auto;align-self:flex-start",
        chip_keys=chip_keys,
    )
    inner = "".join(cluster_parts) + rail_html
    return f'<div class="field-row" style="{base_style}">{inner}</div>'


def _render_paired_row(body_field, date_field, chip_keys=None) -> str:
    """Render a body field (description) on the left and a date on the
    right, sharing a single row.

    Implements the visual the user wants for projects / experience:
    the link sits on the right of the title row, the date sits on the
    right of the description row — both right-aligned, both at the
    same x coordinate (no diagonal drift between link and date).

    A grid layout (1fr / auto) keeps the date pinned to the right edge
    while the body field wraps within its column. ``align-items:start``
    keeps the date at the top of the row when the body wraps.
    ``column-gap`` is 0 so the description and date sit flush against
    each other.
    """
    body_html = _render_field_block(body_field, chip_keys=chip_keys)
    date_html = _render_field_block(
        date_field,
        extra_style="text-align:right;align-self:flex-start",
        chip_keys=chip_keys,
    )
    style = (
        "display:grid;grid-template-columns:1fr auto;"
        "column-gap:0;align-items:start;"
    )
    return f'<div class="field-row paired" style="{style}">{body_html}{date_html}</div>'


def _render_entry(
    entry: Entry,
    section_subsection: SubsectionStyle | None,
    chip_keys: list[str] | None = None,
    entry_layout: str = "stack",
) -> str:
    if entry_layout == "two-column":
        return _render_entry_two_column(entry, section_subsection, chip_keys)

    # Stack entries use --spacing-subsection as the inter-field gap so
    # the template's spacing token drives the visual rhythm. Minimal
    # template maps it to 0px so adjacent fields sit flush; compact
    # gives 12px; comfortable gives 16px. Old CVs that explicitly set
    # ``spacing_after`` on a section still win, so users who widened
    # the gap explicitly aren't overridden.
    gap = (section_subsection.spacing_after if section_subsection else None) or "var(--spacing-subsection, 0px)"

    title_row, paired, rest = _split_title_row(entry.fields, chip_keys)

    rows: list[str] = []
    if title_row:
        rows.append(_render_title_row(title_row, chip_keys))
        if paired is not None:
            body_field, date_field = paired
            rows.append(_render_paired_row(body_field, date_field, chip_keys))
            tail = rest
        else:
            tail = rest
    else:
        tail = entry.fields

    # Group the remaining fields by their ``group`` value, same as
    # the legacy stack path. Each group becomes one flex row.
    current_group: str | None = None
    bucket: list[FieldBlock] = []
    justify = _resolve_row_justify(section_subsection)
    for field in tail:
        if bucket and (field.group is None or field.group != current_group):
            rows.append(_render_field_row(bucket, justify, chip_keys))
            bucket = []
        current_group = field.group
        bucket.append(field)
    if bucket:
        rows.append(_render_field_row(bucket, justify, chip_keys))

    fields_html = "".join(rows)
    return f'<div class="entry" style="display:flex;flex-direction:column;gap:{gap};">{fields_html}</div>'


# Field keys that always go in the right column of a two-column entry
# (date, plus any linked text like a project link, paper link, or
# certification link). Everything else — title, description, tech, venue,
# issuer, location, etc. — goes in the left column.
_RIGHT_COLUMN_KEYS: frozenset[str] = frozenset({"date", "link"})


def _render_entry_two_column(
    entry: Entry,
    section_subsection: SubsectionStyle | None,
    chip_keys: list[str] | None = None,
) -> str:
    """Render an entry as a two-column grid: title/description/tech/venue/etc.
    on the left, date+link on the right.

    Used for projects, research, and certifications by default. Solves three
    visual-diff bugs against the golden PDF:

    1. When a research/cert entry has a sparse secondary row (e.g. just a
       link when venue is absent), the body sits in the left column with
       no fixed vertical band between the secondary row and the body —
       they live in independent flex containers.
    2. A long title in the left column wraps inside its own block; the
       right column anchors to the entry's top, not the title's bottom.
    3. Long body text (descriptions) wrap naturally inside the left
       column, which is already constrained to 5/6 of the entry width
       by the grid layout — no extra ``max-width`` cap is needed.

    Layout: ``display:grid; grid-template-columns:5fr 1fr`` — the left
    column takes 5/6 of the entry width (title, description, tech, etc.),
    the right column takes 1/6 (date + link, right-justified).
    ``align-items:start`` so the right column pins to the entry's top
    regardless of how tall the left column gets.
    """

    gap = (section_subsection.spacing_after if section_subsection else None) or "var(--spacing-subsection, 0px)"

    # Split fields by key: date + link go right, everything else goes left.
    right_fields: list[FieldBlock] = [f for f in entry.fields if f.key in _RIGHT_COLUMN_KEYS]
    left_fields: list[FieldBlock] = [f for f in entry.fields if f.key not in _RIGHT_COLUMN_KEYS]
    # Left column: stack fields vertically. Each field's width is
    # constrained by the grid column itself (5/6 of the entry width),
    # so we don't need an extra max-width cap here — the grid does the
    # work. Chip fields (e.g. tech_stack pills) are inline spans and
    # take only as much width as their content.
    def left_extra_style(f: FieldBlock) -> str | None:
        if chip_keys and f.key in chip_keys:
            return None
        return None

    left_parts = [
        _render_field_block(f, extra_style=left_extra_style(f), chip_keys=chip_keys)
        for f in left_fields
    ]
    left_html = "".join(left_parts)

    # Right column: a single right-justified block of date + link.
    # No rail logic, no row grouping — just two stacked field blocks,
    # right-aligned via align-items:flex-end on the column.
    right_parts = [
        _render_field_block(f, chip_keys=chip_keys)
        for f in right_fields
    ]
    right_html = "".join(right_parts)

    return (
        f'<div class="entry entry-two-col" style="'
        f'display:grid;grid-template-columns:5fr 1fr;'
        f'column-gap:{gap};align-items:start;'
        f'">'
        f'<div class="entry-left" style="display:flex;flex-direction:column;gap:{gap};">{left_html}</div>'
        f'<div class="entry-right" style="display:flex;flex-direction:column;gap:0;align-items:flex-end;">{right_html}</div>'
        f'</div>'
    )


def _render_field_row(
    fields: list[FieldBlock],
    justify: str,
    chip_keys: list[str] | None = None,
) -> str:
    """Render consecutive same-group fields as one flex row.

    A right-aligned field (``align="right"``) becomes the row's right rail:
    the first such field is pushed to the right edge via ``margin-left:auto``
    and the section's text alignment is ignored for that row. Otherwise the
    row's ``justify-content`` mirrors the section's ``text_align``."""

    rail_field = next((f for f in fields if f.align == "right"), None)
    base_style = "display:flex;flex-wrap:wrap;align-items:baseline;column-gap:0;row-gap:0"
    if rail_field is not None:
        inner = "".join(
            _render_field_block(f, extra_style="margin-left:auto" if f is rail_field else None, chip_keys=chip_keys)
            for f in fields
        )
        return f'<div class="field-row" style="{base_style}">{inner}</div>'
    inner = "".join(_render_field_block(f, chip_keys=chip_keys) for f in fields)
    return f'<div class="field-row" style="{base_style};justify-content:{justify}">{inner}</div>'



def _render_heading(section: Section, policy: SectionPolicy | None) -> str:
    show = policy.show_title if policy else True
    if not show:
        return ""
    color = section.subsection.section_color if section.subsection and section.subsection.section_color else None
    has_divider = bool(policy and policy.heading_divider)
    # Without a divider we keep 2px below the text; with a divider the
    # ``border-bottom`` + ``padding-bottom`` already provide breathing
    # room, so any margin on top of that pushes the body too far from
    # the title row (a visible ~7px gap on project / research entries).
    base_margin = "0 0 0" if has_divider else "0 0 2px"
    style_parts = [f"margin:{base_margin}", "font-size:1rem", "font-weight:700"]
    if color:
        style_parts.append(f"color:{color}")
    if has_divider:
        # Legacy ``underline_section_titles`` flag: border-bottom under
        # the heading, padded so the rule does not crowd the text.
        style_parts.append("border-bottom:1px solid var(--accent,#1f2937)")
        style_parts.append("padding-bottom:4px")
    return f'<h2 style="{";".join(style_parts)};">{h(section.title)}</h2>'


def _subsection_style_decl(section: Section) -> str:
    """Inline-style declarations contributed by the section's subsection axis."""

    sub = section.subsection or SubsectionStyle()
    decls: list[str] = []
    if sub.text_align:
        decls.append(f"text-align:{sub.text_align}")
    if sub.spacing_before:
        decls.append(f"padding-top:{sub.spacing_before}")
    if sub.spacing_after:
        decls.append(f"margin-bottom:{sub.spacing_after}")
    if sub.background_color:
        decls.append(f"background-color:{sub.background_color}")
    if sub.section_color:
        decls.append(f"color:{sub.section_color}")
    return _format_inline_style(decls)


def _layout_style_decl(section: Section) -> str:
    """Inline-style declarations contributed by the section's layout axis."""

    layout = section.layout or LayoutHints()
    decls: list[str] = []
    if layout.font_family:
        decls.append(f"font-family:{layout.font_family}")
    if layout.break_before:
        decls.append("break-before:page")
    if layout.keep_together:
        decls.append("break-inside:avoid")
    if layout.orphans:
        decls.append(f"orphans:{layout.orphans}")
    if layout.widows:
        decls.append(f"widows:{layout.widows}")
    return _format_inline_style(decls)


def _heading_keeps_with_first_decl(section: Section) -> str:
    """When ``heading_keeps_with_first`` is set, the first entry needs
    ``break-before: avoid`` to stay glued to the heading."""

    layout = section.layout or LayoutHints()
    if not layout.heading_keeps_with_first:
        return ""
    return "break-before:avoid"


_ENTRY_OPEN_RE = re.compile(r'(<div class="entry")( style="([^"]*)")?()')


def _merge_entry_break_before(entry_html: str, decl: str) -> str:
    """Merge ``decl`` (e.g. ``"break-before:avoid"``) into the entry's
    existing ``style`` attribute so we never emit two ``style=`` on one
    tag — browsers pick the first and drop the second, which used to
    strip the entry's own flex layout declarations.
    """

    match = _ENTRY_OPEN_RE.match(entry_html)
    if not match:
        return entry_html
    prefix, _existing_attr, existing_value, _empty = match.groups()
    if existing_value:
        declarations = [d for d in existing_value.split(";") if d]
    else:
        declarations = []
    if decl and decl not in declarations:
        declarations.append(decl)
    merged = _format_inline_style(declarations)
    if merged:
        return f'{prefix} style="{merged}"{entry_html[match.end():]}'
    return f'{prefix}{entry_html[match.end():]}'


def _render_skills_inline_entry(entry: Entry) -> str:
    """Render one skills entry as ``Category: tag, tag, tag`` inline text.

    Field keys follow the skills builder convention: ``category`` for the
    group label and ``tag.<i>`` for the items. Empty category or no tags
    returns an empty entry so the spacing keeps parity with the block path.

    Per-run :class:`TextStyle` is honored on every tag: the block-variant
    field-row renderer reads ``run.style``; this path used to discard it
    and emit a single concatenated ``<span>``, so user edits to a tag's
    font-size/color silently no-op. Each tag is now a separate ``<span>``
    carrying its run's inline style, so the customize panel actually
    reaches the inline (comma-separated) layout.
    """

    category_runs: list[TextRun] = []
    tag_runs: list[TextRun] = []
    for field in entry.fields:
        if field.key == "category":
            category_runs.extend(field.runs)
        elif field.key.startswith("tag."):
            tag_runs.extend(field.runs)
    parts: list[str] = []
    if category_runs:
        sep = ": " if tag_runs else ""
        category_inner = "".join(_render_text_run(r) for r in category_runs)
        parts.append(f'<span class="f-category">{category_inner}</span>{h(sep)}')
    if tag_runs:
        tag_spans: list[str] = []
        for run in tag_runs:
            inner = h(run.text)
            run_style = _text_run_to_style(run)
            if run_style:
                tag_spans.append(f'<span class="f-tag" style="{run_style}">{inner}</span>')
            else:
                tag_spans.append(f'<span class="f-tag">{inner}</span>')
        if len(tag_spans) == 1:
            parts.append(tag_spans[0])
        else:
            parts.append('<span class="f-tag-sep">,</span> '.join(tag_spans))
    if not parts:
        return ""
    return f'<div class="entry f-skills-inline">{"".join(parts)}</div>'


def _render_section(section: Section) -> str:
    policy = section.policy or SectionPolicy()
    sub_decl = _subsection_style_decl(section)
    layout_decl = _layout_style_decl(section)
    keep_first = _heading_keeps_with_first_decl(section)
    wrapper_decl_parts = [d for d in (layout_decl, sub_decl) if d]
    wrapper_decl_parts.append("margin-bottom:var(--spacing-section, 24px)")
    wrapper_style = _format_inline_style(wrapper_decl_parts)
    heading_html = _render_heading(section, policy)

    entries_html_parts: list[str] = []
    # Skills are always rendered as a comma-separated list per category
    # (e.g. ``Programming Languages: TypeScript, JavaScript, Python``).
    # The block variant — each tag as its own flex item — looked tight
    # after the entry-gap fix (gap: 0 collapsed everything flush), and
    # a comma list avoids the gap problem entirely while reading as a
    # single semantic group. The ``skill_variant`` policy is preserved
    # for API compatibility but no longer affects the layout.
    if section.type == "skills":
        for entry in section.entries:
            entries_html_parts.append(_render_skills_inline_entry(entry))
    else:
        for i, entry in enumerate(section.entries):
            chip_keys = section.layout.chip_keys if section.layout else None
            entry_html = _render_entry(
                entry, section.subsection, chip_keys,
                entry_layout=policy.entry_layout,
            )
            if i == 0 and keep_first:
                entry_html = _merge_entry_break_before(entry_html, keep_first)
            entries_html_parts.append(entry_html)
    entries_html = "".join(entries_html_parts)

    return (
        f'<section id="{attr(section.id)}" style="{wrapper_style}">'
        f"{heading_html}{entries_html}"
        f"</section>"
    )


def _render_zone(zone: ResolvedZone, sections_by_id) -> str:
    style_str = _format_inline_style([f"{k}:{v}" for k, v in zone.styles.items() if v])
    panels: list[str] = []
    for section_id in zone.section_ids:
        section = sections_by_id.get(section_id)
        if section is None:
            continue
        panels.append(_render_section(section))
    return f'<div class="zone" style="{style_str}">{"".join(panels)}</div>'


def _render_document(model: RenderModel, support: RendererSupport) -> str:
    best_effort = "\n".join(_best_effort_comments(model, support))
    css_vars_block = _render_css_vars(model)
    zones_html = "".join(_render_zone(zone, model.sections) for zone in model.zones)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
{css_vars_block}
    body {{
      margin: 0;
      padding: 0;
      font-family: {attr(model.body_font)};
      color: var(--text, #374151);
      background: var(--bg, #ffffff);
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: {attr(model.heading_font)};
    }}
    .f-name {{ font-size: 1.5rem; font-weight: 700; }}
    .f-title, .f-summary, .f-company, .f-description, .f-institution, .f-category, .f-venue, .f-issuer {{ font-size: 0.875rem; }}
    .f-contact, .f-contact-sep, .f-email, .f-phone, .f-location, .f-site, .f-date, .f-gpa, .f-link, .f-tech, .f-tag, .f-proficiency, .f-meta {{ font-size: 0.75rem; }}
    /* Social row: smaller than the other contact fields so the icon+label
       pairs read as fine metadata next to the email/phone row. */
    .f-social {{ display:inline-block; font-size: 0.83rem; }}
    .f-social:last-child {{ margin-right: 0; }}
    .f-social-link {{ margin-right: 1.5rem; }}
    .f-social-link:last-child {{ margin-right: 0; }}
    .f-position, .f-degree, .f-project, .f-certification, .f-paper, .f-category {{ font-weight: 600; }}
    /* Rich text blocks: paragraphs and lists inside description/summary fields */
    .f-description p:last-child, .f-summary p:last-child {{ margin-bottom: 0; }}
    .f-description ul, .f-description ol, .f-summary ul, .f-summary ol {{ margin: 0.25rem 0; padding-left: 1.5rem; }}
    .f-description ul, .f-summary ul {{ list-style-type: disc; }}
    .f-description ol, .f-summary ol {{ list-style-type: decimal; }}
    .f-description li, .f-summary li {{ margin: 0.125rem 0; }}

    .f-icon {{ display:inline-flex; width:0.75em; height:0.75em; margin-right:0.25em; vertical-align:-0.1em; }}
    .f-icon svg {{ width:100%; height:100%; }}
    /* Pipe separator between adjacent contact fields in the profile row
       (email | phone | location | site). Skipped on the first child so
       the row doesn't start with a dangling pipe. The profile builder
       emits f-email/f-phone/f-location/f-site (not f-contact), so the
       selectors target those classes specifically. */
    .f-email + .f-phone::before,
    .f-phone + .f-location::before,
    .f-location + .f-site::before,
    .f-email + .f-location::before,
    .f-email + .f-site::before,
    .f-phone + .f-site::before {{
      content: " | ";
      color: var(--text, #6b7280);
      margin: 0 0.35em;
    }}
    .field-row {{ display:flex; flex-wrap:wrap; align-items:baseline; column-gap:0; row-gap:0; }}
    .f-chip {{ display:inline-block; background:#eff6ff; padding:2px 6px; border-radius:4px; color:#1d4ed8; font-size:0.75rem; }}
{model.link_styles}    {model.print_styles}
  </style>
{best_effort}
</head>
<body>
  <div style="display:flex;flex-direction:row;align-items:flex-start;gap:var(--spacing-section, 16px);">
{zones_html}
  </div>
</body>
</html>"""


class HTMLDocumentRenderer(DocumentRenderer):
    """Render a :class:`RenderModel` to a complete HTML5 document."""

    support = RendererSupport()

    def render(self, model: RenderModel) -> str:
        return _render_document(model, self.support)

    def render_bytes(self, model: RenderModel) -> bytes:
        return self.render(model).encode("utf-8")


__all__ = ["HTMLDocumentRenderer"]
