"""Render routes — new AST-driven pipeline.

Four endpoints replace the legacy IR pipeline:

- ``POST /render/ast`` — body: ``{ cv_sections, manifest, customizations }``.
  Returns ``{ document }``. Builds the AST without mutating CV data.
- ``POST /render/html`` — body: same. Returns ``{ html }``. When
  ``preview=true`` is set, anchor hrefs are neutered so the iframe does
  not navigate on click.
- ``POST /render/pdf`` — body: same. Returns ``{ pdf_base64 }``. PDF is
  rendered via the new HTMLDocumentRenderer + the Playwright plumbing in
  ``app.services.renderer._pdf_runtime``.
- ``GET /render/support`` — returns the HTMLDocumentRenderer's
  :class:`RendererSupport` as JSON. Used by the customize panel.
"""

from __future__ import annotations

import base64
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.models.user import User
from app.core.rate_limit import limiter
from app.core.deps import get_current_user
from app.document_schema.models import (
    Customizations,
    SectionInstance,
    TemplateManifest,
)
from app.document_schema.capabilities import capabilities_hash, renderer_capabilities
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.pipeline import (
    RenderSource,
    build_source_document,
    prepare_render_source,
    render_source_html,
    render_source_pdf,
)


router = APIRouter(prefix="/render")
logger = logging.getLogger("aergia.render")


# Matches ``href="..."`` on every <a> tag without disturbing other attributes
# or the surrounding markup. The live preview iframe must NOT have working
# links: hrefs are neutralized to "#" so anchors stay visually styled (and
# keep the .f-link arrow) but clicking never navigates the iframe away from
# the CV while editing. The exported PDF uses the raw renderer output, which
# keeps the real hrefs.
_HREF_RE = re.compile(r'(<a\b[^>]*?\bhref=")[^"]*(")', re.IGNORECASE)


def strip_anchor_hrefs(html: str) -> str:
    """Replace ``href="..."`` values with ``href="#"`` so preview anchors
    remain visually styled but don't navigate the live preview iframe."""
    return _HREF_RE.sub(r"\1#\2", html)


class RenderRequest(BaseModel):
    cv_sections: list[SectionInstance] = Field(default_factory=list, max_length=32)
    manifest: TemplateManifest | dict | None = None
    customizations: Customizations | dict | None = None
    preview: bool = False


def _build_source_from_request(request: RenderRequest) -> RenderSource:
    """Normalize the request once for any of the three render outputs."""

    return prepare_render_source(
        request.cv_sections,
        request.manifest,
        request.customizations,
    )


@router.post("/ast")
@limiter.limit("30/minute")
async def render_ast(
    request: Request,
    response: Response,
    payload: RenderRequest,
    current_user: User = Depends(get_current_user),
):
    """Build the AST without rendering."""

    try:
        document = build_source_document(_build_source_from_request(payload))
    except Exception as exc:  # noqa: BLE001
        logger.error("render_ast_failed", extra={"exception_type": type(exc).__name__})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid render request") from exc
    return {"document": document.model_dump(mode="json")}


@router.post("/html")
@limiter.limit("30/minute")
async def render_html(
    request: Request,
    response: Response,
    payload: RenderRequest,
    current_user: User = Depends(get_current_user),
):
    """Render to HTML using the new pipeline."""

    try:
        html = render_source_html(_build_source_from_request(payload))
        if payload.preview:
            html = strip_anchor_hrefs(html)
    except Exception as exc:  # noqa: BLE001
        logger.error("render_html_failed", extra={"exception_type": type(exc).__name__})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to render document") from exc
    return {"html": html}


@router.post("/pdf")
@limiter.limit("5/minute")
async def render_pdf(
    request: Request,
    response: Response,
    payload: RenderRequest,
    current_user: User = Depends(get_current_user),
):
    """Render to PDF and return it base64-encoded."""

    try:
        pdf_bytes = await render_source_pdf(_build_source_from_request(payload))
    except Exception as exc:  # noqa: BLE001
        logger.error("render_pdf_failed", extra={"exception_type": type(exc).__name__})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to export document") from exc
    return {"pdf_base64": base64.b64encode(pdf_bytes).decode("ascii")}


@router.get("/support")
async def render_support(
    current_user: User = Depends(get_current_user),
):
    """Return the HTMLDocumentRenderer's :class:`RendererSupport` as JSON."""

    support = HTMLDocumentRenderer.support
    payload = {
        field: level.value
        for field, level in vars(support).items()
    }
    # Keep the legacy flat feature flags for the editor while exposing the
    # canonical authoring descriptor consumed by tailoring agents.
    payload["capabilities"] = renderer_capabilities(support)
    payload["capabilities_hash"] = capabilities_hash(payload["capabilities"])
    return payload


__all__ = ["router", "strip_anchor_hrefs"]
