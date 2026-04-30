"""Renderer package - unified IR-based rendering pipeline."""

from .ir import build_ir
from .html import ir_to_html, render_html
from .pdf import ir_to_pdf, render_pdf

__all__ = [
    "build_ir",
    "ir_to_html",
    "ir_to_pdf",
    "render_html",
    "render_pdf",
]