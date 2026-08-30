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
from app.schema.models import (
    Customizations,
    Document,
    SectionInstance,
    TemplateManifest,
)
from app.services.cv import coerce_customizations
from app.services.renderer import build_document, resolve
from app.services.renderer._pdf_runtime import html_to_pdf
from app.services.renderer.html import HTMLDocumentRenderer
from app.services.renderer.resolve import ManifestVersionError


router = APIRouter(prefix="/render", tags=["render"])
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


def _coerce_manifest(manifest: TemplateManifest | dict | None) -> TemplateManifest | None:
    if manifest is None:
        return None
    if isinstance(manifest, TemplateManifest):
        return manifest
    return TemplateManifest.model_validate(manifest)


def _build_document_from_request(request: RenderRequest) -> tuple[Document, TemplateManifest | None, Customizations]:
    manifest_model = _coerce_manifest(request.manifest)
    customizations_model = coerce_customizations(request.customizations if not isinstance(request.customizations, Customizations) else None)

    if isinstance(request.customizations, Customizations):
        customizations_model = request.customizations

    from types import SimpleNamespace

    cv = SimpleNamespace(sections=[s.model_dump() for s in request.cv_sections])
    document = build_document(cv, manifest_model)
    return document, manifest_model, customizations_model


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
        document, _, _ = _build_document_from_request(payload)
    except ManifestVersionError as exc:
        logger.error("render_ast_rejected", extra={"exception_type": type(exc).__name__})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported template manifest") from exc
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
        document, manifest, customizations = _build_document_from_request(payload)
        renderer = HTMLDocumentRenderer()
        model = resolve(document, renderer, manifest, customizations)
        html = renderer.render(model)
        if payload.preview:
            html = strip_anchor_hrefs(html)
    except ManifestVersionError as exc:
        logger.error("render_html_rejected", extra={"exception_type": type(exc).__name__})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported template manifest") from exc
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
        document, manifest, customizations = _build_document_from_request(payload)
        renderer = HTMLDocumentRenderer()
        model = resolve(document, renderer, manifest, customizations)
        html = renderer.render(model)
        pdf_bytes = await html_to_pdf(html)
    except ManifestVersionError as exc:
        logger.error("render_pdf_rejected", extra={"exception_type": type(exc).__name__})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported template manifest") from exc
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
    return {
        field: level.value
        for field, level in vars(support).items()
    }


__all__ = ["router", "strip_anchor_hrefs"]
