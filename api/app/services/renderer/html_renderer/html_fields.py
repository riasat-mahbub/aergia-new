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

    Linked runs keep their visible label as plain inline text. The destination
    remains clickable through the anchor, while omitting a generated arrow
    avoids exposing a stray arrow as a separate link label to PDF importers.
    """

    text = h(run.text)
    style = _text_run_to_style(run)
    safe_link = normalize_url(run.style.link) if run.style and run.style.link else ""
    if safe_link:
        href = attr(safe_link)
        # Long readable URLs must wrap inside narrow template columns rather
        # than pushing across the page or becoming visually clipped.
        anchor_style = _format_inline_style([style, "overflow-wrap:anywhere;max-width:100%"])
        if anchor_style:
            return f'<a href="{href}"{_style_attr(anchor_style)}>{text}</a>'
        return f'<a href="{href}">{text}</a>'
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

    # Decide whether to hoist the URL onto the wrapper element. Site/social/chip
    # fields need the icon+label (or pill) wrapped in one anchor; other fields
    # keep the link emitted by the text-run pass. The builder emits ``key="social"``
    # for each social link; older payloads may use indexed ``social_links.i``
    # keys — match by prefix to support both.
    wants_external_anchor = (
        block.key in {"site", "social"}
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
            return f'<a href="{attr(href)}" class="f-chip-link" style="overflow-wrap:anywhere;max-width:100%">{body}</a>'
        return body
    # Keep each social icon and label inside one clickable contact item.
    if block.key == "social" or block.key.startswith("social_links."):
        body = f'<span class="f-social"{_style_attr(extra_style)}>{inner}</span>'
        if href:
            return f'<a class="f-social-link" href="{attr(href)}" style="overflow-wrap:anywhere;max-width:100%">{body}</a>'
        return body
    if href:
        inner = f'<a href="{attr(href)}" style="overflow-wrap:anywhere;max-width:100%">{inner}</a>'
    return f'<div class="f-{attr(block.key)}"{_style_attr(extra_style)}>{inner}</div>'


__all__ = ["_render_field_block", "_render_rich_text_blocks", "_render_text_run", "_text_run_to_style"]
