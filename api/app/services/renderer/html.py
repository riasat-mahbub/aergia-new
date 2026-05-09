"""HTML rendering entry point."""

from .backends.html import HTMLBackend


def render_html(manifest: dict, cv_data: dict, customizations: dict) -> str:
    """Build IR and render to HTML."""
    return HTMLBackend().render(manifest, cv_data, customizations)
