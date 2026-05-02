"""Renderer backend protocol and registry."""

BACKENDS: dict[str, type] = {}


def register_backend(name: str, backend_cls: type) -> None:
    BACKENDS[name] = backend_cls


def get_backend(name: str):
    if name not in BACKENDS:
        raise ValueError(f"Unknown backend: {name}")
    return BACKENDS[name]()


from .html import HTMLBackend
from .pdf import PDFBackend

register_backend("html", HTMLBackend)
register_backend("pdf", PDFBackend)
