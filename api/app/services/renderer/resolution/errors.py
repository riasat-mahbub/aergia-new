"""Errors raised while preparing renderer resolution inputs."""


class ManifestVersionError(ValueError):
    """Raised when the manifest is not v2."""


__all__ = ["ManifestVersionError"]
