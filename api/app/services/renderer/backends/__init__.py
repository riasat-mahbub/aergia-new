"""Renderer backend protocol and registry."""

from abc import ABC, abstractmethod
from typing import Any
from ..types import DocumentIR


class RendererBackend(ABC):
    """Abstract base class for renderer backends."""

    @abstractmethod
    def render(self, ir: DocumentIR) -> Any:
        """Render the IR to the target format."""
        pass


# Backend registry
BACKENDS: dict[str, type[RendererBackend]] = {}


def register_backend(name: str, backend_cls: type[RendererBackend]) -> None:
    """Register a renderer backend."""
    BACKENDS[name] = backend_cls


def get_backend(name: str) -> RendererBackend:
    """Get a backend instance by name."""
    if name not in BACKENDS:
        raise ValueError(f"Unknown backend: {name}")
    return BACKENDS[name]()


# Register built-in backends
from .html import HTMLBackend
from .pdf import PDFBackend

register_backend("html", HTMLBackend)
register_backend("pdf", PDFBackend)