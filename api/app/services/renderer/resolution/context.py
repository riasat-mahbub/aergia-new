"""Typed inputs shared by the resolver's focused resolution stages."""

from __future__ import annotations

from dataclasses import dataclass

from app.document_schema.models import Customizations, TemplateManifest
from app.services.renderer.support import RendererSupport

from .errors import ManifestVersionError

_MANIFEST_VERSION_KEY = "manifest_version"


@dataclass(frozen=True)
class ResolutionContext:
    """Validated values needed by every resolution stage."""

    support: RendererSupport
    manifest: TemplateManifest | None
    customizations: Customizations


def _coerce_manifest(
    manifest: TemplateManifest | dict | None,
) -> TemplateManifest | None:
    """Validate the supported manifest shape at the compatibility boundary."""

    if manifest is None:
        return None
    if isinstance(manifest, TemplateManifest):
        return manifest
    if isinstance(manifest, dict):
        version = manifest.get(_MANIFEST_VERSION_KEY)
        if version != 2:
            raise ManifestVersionError(
                f"Template manifest version {version!r} is not supported; expected 2."
            )
        return TemplateManifest.model_validate(manifest)
    raise ManifestVersionError("Template manifest must be a dict or TemplateManifest.")


def _coerce_customizations(
    customizations: Customizations | dict | None,
) -> Customizations:
    """Validate optional wire customizations at the compatibility boundary."""

    if customizations is None:
        return Customizations()
    if isinstance(customizations, Customizations):
        return customizations
    return Customizations.model_validate(customizations)


def prepare_context(
    support: RendererSupport,
    manifest: TemplateManifest | dict | None,
    customizations: Customizations | dict | None,
) -> ResolutionContext:
    """Convert the public resolver inputs into the typed core context."""

    return ResolutionContext(
        support=support,
        manifest=_coerce_manifest(manifest),
        customizations=_coerce_customizations(customizations),
    )


__all__ = ["ResolutionContext", "prepare_context"]
