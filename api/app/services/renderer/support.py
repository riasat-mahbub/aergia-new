"""Renderer capability declarations.

Every renderer declares its own :class:`RendererSupport` as a class-level
attribute. The customize panel reads it to decide which controls are
visible; the export endpoint reads it to decide whether to honour a
feature.

A :class:`SupportLevel` of:

- ``FULL`` — the renderer reliably satisfies this; the control is shown.
- ``BEST_EFFORT`` — the renderer tries but can't guarantee; the control is
  shown with a warning icon (the renderer emits a ``best-effort`` comment).
- ``NONE`` — the renderer can't satisfy this; the control is hidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SupportLevel(str, Enum):
    FULL = "FULL"
    BEST_EFFORT = "BEST_EFFORT"
    NONE = "NONE"


@dataclass(frozen=True)
class RendererSupport:
    """Capability declaration for a renderer."""

    break_before: SupportLevel = SupportLevel.FULL  # Chromium honours break-before: page
    keep_with_next: SupportLevel = SupportLevel.BEST_EFFORT
    keep_together: SupportLevel = SupportLevel.BEST_EFFORT
    heading_keeps_with_first: SupportLevel = SupportLevel.BEST_EFFORT
    feature_skills_inline: SupportLevel = SupportLevel.FULL
    feature_section_underline: SupportLevel = SupportLevel.FULL
    feature_anchor_styling: SupportLevel = SupportLevel.FULL
