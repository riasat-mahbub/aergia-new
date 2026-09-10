"""Render section entries and their field-row layouts."""

from __future__ import annotations

import re

from app.document_schema.models import Entry, FieldBlock, SubsectionStyle, TextRun
from .html_fields import (
    _render_field_block,
    _render_text_run,
    _text_run_to_style,
)
from .html_markup import (
    attr,
    format_inline_style as _format_inline_style,
    h,
    style_attr as _style_attr,
)
from app.services.renderer.html_values import safe_spacing as _safe_spacing


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
    base_style = "display:flex;flex-wrap:wrap;align-items:flex-start;column-gap:0;row-gap:0"
    if rail_field is None:
        inner = "".join(_render_field_block(f, chip_keys=chip_keys) for f in fields)
        return f'<div class="field-row"{_style_attr(base_style)}>{inner}</div>'
    cluster_parts: list[str] = []
    for idx, f in enumerate(fields):
        if f is rail_field:
            continue
        extra = "max-width:70%;min-width:0" if idx == 0 else None
        cluster_parts.append(_render_field_block(f, extra_style=extra, chip_keys=chip_keys))
    rail_html = _render_field_block(
        rail_field,
        extra_style="margin-left:auto;align-self:flex-start",
        chip_keys=chip_keys,
    )
    inner = "".join(cluster_parts) + rail_html
    return f'<div class="field-row"{_style_attr(base_style)}>{inner}</div>'


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
    style = "display:grid;grid-template-columns:1fr auto;column-gap:0;align-items:start;"
    return f'<div class="field-row paired"{_style_attr(style)}>{body_html}{date_html}</div>'


def _render_field_sequence(
    fields: list[FieldBlock],
    chip_keys: list[str] | None = None,
) -> str:
    """Render fields while grouping consecutive chip fields into one row.

    The AST keeps repeated values as separate ``FieldBlock`` nodes. Grouping
    happens only at this HTML boundary, preserving that schema and the source
    order while giving chip fields a wrapping flex context in both stack and
    two-column entry layouts.
    """

    parts: list[str] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        if chip_keys and field.key in chip_keys:
            chips: list[FieldBlock] = []
            while index < len(fields) and fields[index].key in chip_keys:
                chips.append(fields[index])
                index += 1
            chip_html = "".join(_render_field_block(chip, chip_keys=chip_keys) for chip in chips)
            parts.append(f'<div class="f-chip-group">{chip_html}</div>')
            continue
        parts.append(_render_field_block(field, chip_keys=chip_keys))
        index += 1
    return "".join(parts)


def _render_entry(
    entry: Entry,
    section_subsection: SubsectionStyle | None,
    chip_keys: list[str] | None = None,
    entry_layout: str = "stack",
) -> str:
    if entry_layout == "two-column":
        return _render_entry_two_column(entry, section_subsection, chip_keys)

    # Field rhythm is independent from the section's outside margin. The
    # explicit ``field_gap`` control owns this value; when it is unset the
    # template's inherited subsection rhythm remains the fallback.
    gap = (
        _safe_spacing(
            (section_subsection.field_gap if section_subsection and section_subsection.field_gap else None)
            or "var(--spacing-subsection, 0px)"
        )
        or "0px"
    )

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
    entry_style = f"display:flex;flex-direction:column;gap:{gap}"
    return f'<div class="entry"{_style_attr(entry_style)}>{fields_html}</div>'


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

    gap = (
        _safe_spacing(
            (section_subsection.field_gap if section_subsection and section_subsection.field_gap else None)
            or "var(--spacing-subsection, 0px)"
        )
        or "0px"
    )

    # Split fields by key: date + link go right, everything else goes left.
    right_fields: list[FieldBlock] = [f for f in entry.fields if f.key in _RIGHT_COLUMN_KEYS]
    left_fields: list[FieldBlock] = [f for f in entry.fields if f.key not in _RIGHT_COLUMN_KEYS]

    # Left column: stack fields vertically. Chip fields are kept together as
    # one wrapping group so the parent column's gap separates the stack from
    # the preceding field, rather than separating every individual chip.
    left_html = _render_field_sequence(left_fields, chip_keys)

    # Right column: a single right-justified block of date + link.
    # No rail logic, no row grouping — just two stacked field blocks,
    # right-aligned via align-items:flex-end on the column.
    right_parts = [_render_field_block(f, chip_keys=chip_keys) for f in right_fields]
    right_html = "".join(right_parts)

    # Keep the two-column rail anchored to the same x position regardless of
    # the user's vertical field rhythm. The field gap belongs inside each
    # column; it must not become a horizontal grid gap.
    entry_style = "display:grid;grid-template-columns:5fr 1fr;column-gap:0;align-items:start"
    left_style = f"display:flex;flex-direction:column;gap:{gap}"
    right_style = f"display:flex;flex-direction:column;gap:{gap};align-items:flex-end"
    return (
        f'<div class="entry entry-two-col"{_style_attr(entry_style)}>'
        f'<div class="entry-left"{_style_attr(left_style)}>{left_html}</div>'
        f'<div class="entry-right"{_style_attr(right_style)}>{right_html}</div>'
        f"</div>"
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
        return f'<div class="field-row"{_style_attr(base_style)}>{inner}</div>'
    inner = _render_field_sequence(fields, chip_keys)
    return f'<div class="field-row"{_style_attr(base_style + ";justify-content:" + justify)}>{inner}</div>'


_ENTRY_OPEN_RE = re.compile(r'(<div class="entry[^"]*")(?:( style="([^"]*)"))?()')


def _add_entry_metadata(entry_html: str, entry_id: str, keep_together: bool) -> str:
    """Add stable, non-visual metadata used by the live preview paginator."""

    match = re.match(r'(<div class="entry[^"]*")( style="[^"]*")?', entry_html)
    if not match:
        return entry_html
    prefix, style_attr = match.groups()
    metadata = (
        f' data-preview-entry="true"'
        f' data-preview-entry-id="{attr(entry_id)}"'
        f' data-preview-keep-together="{str(keep_together).lower()}"'
    )
    # Keep the existing style immediately after the class. The renderer's
    # break-rule merger intentionally rewrites that attribute, and placing
    # metadata between the class and style would make it emit a duplicate
    # style attribute for keep-together entries.
    return f"{prefix}{style_attr or ''}{metadata}{entry_html[match.end() :]}"


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
        return f"{prefix}{_style_attr(merged)}{entry_html[match.end() :]}"
    return f"{prefix}{entry_html[match.end() :]}"


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
                tag_spans.append(f'<span class="f-tag"{_style_attr(run_style)}>{inner}</span>')
            else:
                tag_spans.append(f'<span class="f-tag">{inner}</span>')
        if len(tag_spans) == 1:
            parts.append(tag_spans[0])
        else:
            parts.append('<span class="f-tag-sep">,</span> '.join(tag_spans))
    if not parts:
        return ""
    return f'<div class="entry f-skills-inline">{"".join(parts)}</div>'


__all__ = [
    "_add_entry_metadata",
    "_merge_entry_break_before",
    "_render_entry",
    "_render_entry_two_column",
    "_render_field_row",
    "_render_skills_inline_entry",
]
