"""Template rendering endpoint for the new IR-based renderer."""

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Any

from app.models.user import User
from app.core.deps import get_current_user
from app.services.renderer import render_html

router = APIRouter(prefix="/render", tags=["render"])


# Matches ``href="..."`` on every <a> tag without disturbing other attributes
# or the surrounding markup. Used to keep links visually styled (matching the
# accent color / underline) while making them non-clickable in the live preview
# iframe. A sandboxed iframe otherwise replaces its own contents when an anchor
# is clicked — the "new browser in the iframe" symptom users hit while editing.
_HREF_RE = re.compile(r'(<a\b[^>]*?\bhref=")[^"]*(")', re.IGNORECASE)


def strip_anchor_hrefs(html: str) -> str:
    """Replace ``href="..."`` values with ``href="#"`` so anchors remain styled
    but clicking no longer navigates the iframe.

    Anchors retain their class, style, target, and rel attributes — only the
    destination is neutralized. The PDF export takes a separate code path and
    keeps the real hrefs so exported PDFs still carry clickable link annotations.
    """
    return _HREF_RE.sub(r"\1#\2", html)


class RenderRequest(BaseModel):
    manifest: dict[str, Any]
    cv_data: dict[str, Any]
    customizations: dict[str, Any]
    # When True, the rendered HTML is intended for the live preview iframe.
    # Links are kept visible (so the user sees the URL text) but their
    # ``href`` is neutered — clicking no longer navigates the iframe.
    preview: bool = False


@router.post("/html")
async def render_template_html(
    request: RenderRequest,
    current_user: User = Depends(get_current_user),
):
    """Render a template to HTML using the new IR-based renderer."""
    try:
        html = render_html(
            manifest=request.manifest,
            cv_data=request.cv_data,
            customizations=request.customizations,
        )
        if request.preview:
            html = strip_anchor_hrefs(html)
        return {"html": html}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
