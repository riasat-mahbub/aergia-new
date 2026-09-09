"""Render text runs and field blocks as HTML fragments."""

from __future__ import annotations

from app.core.safe_url import normalize_url
from app.document_schema.models import FieldBlock, RichTextBlock, TextRun, TextStyle
from .html_assets import SOCIAL_ICONS as _SOCIAL_ICONS
from .html_markup import (
    attr,
    format_inline_style as _format_inline_style,
    h,
    style_attr as _style_attr,
)
from app.services.renderer.html_values import (
    FONT_SIZE_VALUES as _FONT_SIZE_TO_CSS,
    safe_color as _safe_color,
)


def _text_run_to_style(run: TextRun) -> str:
    """Build an inline-style declaration for a single ``TextRun``."""

    decls: list[str] = []
    style = run.style or TextStyle()
    if style.bold:
        decls.append("font-weight:700")
    if style.italic:
        decls.append("font-style:italic")
    # CSS text-decoration accepts multiple values separated by spaces;
    # combine underline and strike into one declaration so the browser
    # applies both instead of letting the second override the first.
    decorations: list[str] = []
    if style.underline:
        decorations.append("underline")
    if style.strike:
        decorations.append("line-through")
    if decorations:
        decls.append("text-decoration:" + " ".join(decorations))
    color = _safe_color(style.color)
    if color:
        decls.append(f"color:{color}")
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
    safe_link = normalize_url(run.style.link) if run.style and run.style.link else ""
    if safe_link:
        href = attr(safe_link)
        inner = f'{text}<span aria-hidden="true"> ↗</span>'
        if style:
            return f'<a href="{href}"{_style_attr(style)}>{inner}</a>'
        return f'<a href="{href}">{inner}</a>'
    if style:
        return f"<span{_style_attr(style)}>{text}</span>"
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
                f"<li>{_render_text_run(TextRun(text=item.text, style=item.style))}</li>" for item in block.items
            )
            parts.append(f"<ul>{items_html}</ul>")
        elif block.type == "numbered_list":
            items_html = "".join(
                f"<li>{_render_text_run(TextRun(text=item.text, style=item.style))}</li>" for item in block.items
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
        return f'<div class="f-{attr(block.key)}"{_style_attr(extra_style)}>{inner}</div>'

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
    runs = list(block.runs)
    if wants_external_anchor and block.runs:
        linked = [r for r in block.runs if r.style and r.style.link]
        if len(linked) == len(block.runs):
            href = normalize_url(linked[0].style.link)
            if href:
                runs = [r.model_copy(update={"style": r.style.model_copy(update={"link": None})}) for r in block.runs]
    inner = "".join(_render_text_run(r) for r in runs)
    icon_svg = _SOCIAL_ICONS.get(block.icon) if block.icon else None
    if icon_svg:
        icon_html = f'<span class="f-icon" aria-hidden="true">{icon_svg}</span>'
        inner = f'{icon_html}<span class="f-icon-label">{inner}</span>'
    # When this field key is in the section's chip_keys list, render as an
    # inline pill span instead of a block-level div. The pill style is
    # defined as a CSS rule in the renderer's <style> block.
    if chip_keys and block.key in chip_keys:
        body = f'<span class="f-chip"{_style_attr(extra_style)}>{inner}</span>'
        if href:
            return f'<a href="{attr(href)}" class="f-chip-link">{body}</a>'
        return body
    # Social links render inline so adjacent icons sit side-by-side with
    # a consistent horizontal gap (see ``.f-social`` in the document CSS).
    # The block-level div layout would otherwise stack them vertically in
    # the contact row, which reads as the same column as the email/phone.
    if block.key == "social" or block.key.startswith("social_links."):
        body = f'<span class="f-social"{_style_attr(extra_style)}>{inner}</span>'
        if href:
            return f'<a class="f-social-link" href="{attr(href)}">{body}</a>'
        return body
    return f'<div class="f-{attr(block.key)}"{_style_attr(extra_style)}>{inner}</div>'


__all__ = ["_render_field_block", "_render_rich_text_blocks", "_render_text_run", "_text_run_to_style"]
