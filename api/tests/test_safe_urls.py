"""Adversarial URL validation tests for browser and renderer inputs."""

from pydantic import ValidationError
import pytest

from app.core.safe_url import normalize_url
from app.schemas.application import ApplicationCreate
from app.schemas.profile import ProfileSocialLink, UserProfileUpdate
from app.schema.models import TextStyle


@pytest.mark.parametrize("value", [
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "\x01https://example.com",
    "https://example.com/with space",
    "https://user:pass@example.com",
])
def test_normalize_url_rejects_unsafe_values(value):
    assert normalize_url(value) == ""


def test_normalize_url_allows_http_and_optional_contact_schemes():
    assert normalize_url("  https://example.com/jobs  ") == "https://example.com/jobs"
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("mailto:ada@example.com", allowed_schemes={"mailto"}) == "mailto:ada@example.com"
    assert normalize_url("tel:+123456789", allowed_schemes={"tel"}) == "tel:+123456789"


def test_normalize_url_adds_https_to_bare_domain():
    assert normalize_url("example.com/path") == "https://example.com/path"


def test_http_only_application_and_profile_urls_reject_non_http_schemes():
    with pytest.raises(ValidationError):
        ApplicationCreate(company="Acme", role="Engineer", job_description="Work", job_url="javascript:alert(1)")

    with pytest.raises(ValidationError):
        ProfileSocialLink(label="Bad", url="data:text/html,boom", icon="link")

    with pytest.raises(ValidationError):
        UserProfileUpdate(site_url="vbscript:alert(1)")


def test_text_style_drops_unsafe_legacy_links_and_rejects_css_colors():
    assert TextStyle(link="javascript:alert(1)").link is None
    with pytest.raises(ValidationError):
        TextStyle(color='red" onmouseover="alert(1)')

