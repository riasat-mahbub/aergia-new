"""Pure protocol-v2 contract tests (no database or browser runtime)."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.document_schema.capabilities import capabilities_hash, renderer_capabilities
from app.http_schemas.profile import UserProfile
from app.http_schemas.tailoring import (
    PROTOCOL_VERSION,
    TailoringCandidateCV,
    TailoringCodeExchange,
    TailoringContextResponse,
    TailoringPreviewResponse,
    TailoringSessionStatusResponse,
    TailoringSubmitRequest,
)
from app.models.tailoring_session import TailoringSession
from app.services.tailoring import (
    TailoringConflictError,
    TailoringService,
    _application_context_snapshot,
    fresh_tailoring_sections,
)


def _candidate() -> TailoringCandidateCV:
    return TailoringCandidateCV.model_validate(
        {
            "title": "Platform CV",
            "template_id": "minimal",
            "sections": [
                {
                    "id": "profile",
                    "type": "profile",
                    "title": "Profile",
                    "enabled": True,
                    "data": {"name": "Ada", "summary": "Platform engineer"},
                    "style": {"subsection": {"text_align": "left"}},
                },
                {
                    "id": "skills",
                    "type": "skills",
                    "title": "Skills",
                    "enabled": True,
                    "data": [{"id": "skills-1", "category": "Languages", "items": ["Python"]}],
                },
            ],
            "customizations": {"accent_color": "#123456", "spacing": "compact", "flags": {"default_link_style": True}},
        }
    )


def test_protocol_v2_is_complete_candidate_only():
    candidate = _candidate()
    assert PROTOCOL_VERSION == 2
    assert candidate.customizations.accent_color == "#123456"
    assert candidate.sections[0].style is not None
    with pytest.raises(ValidationError):
        TailoringCodeExchange.model_validate({"protocol_version": 1, "code": "x" * 16})
    with pytest.raises(ValidationError):
        TailoringSubmitRequest.model_validate({"context_hash": "a" * 64, "changes": []})
    with pytest.raises(ValidationError):
        TailoringSubmitRequest.model_validate(
            {"context_hash": "a" * 64, "candidate": _candidate(), "review_notes": ["x" * 1_001]}
        )


def test_preview_feedback_and_expected_candidate_hash_are_part_of_the_tailoring_contract():
    preview = TailoringPreviewResponse.model_validate(
        {
            "format": "pdf",
            "pdf_base64": "cGRm",
            "page_count": 1,
            "candidate_hash": "b" * 64,
            "relevance": {"status": "evaluated", "score": 90},
            "warnings": ["Review length for the target role."],
        }
    )
    request = TailoringSubmitRequest.model_validate(
        {
            "context_hash": "a" * 64,
            "expected_candidate_hash": preview.candidate_hash,
            "candidate": _candidate(),
        }
    )

    assert preview.relevance["score"] == 90
    assert preview.warnings == ["Review length for the target role."]
    assert request.expected_candidate_hash == preview.candidate_hash


def test_context_and_status_contracts_are_v2_and_do_not_expose_capabilities():
    capabilities = renderer_capabilities()
    assert capabilities["version"] == 2
    assert capabilities["tailoring"]["mode"] == "complete_candidate"
    assert capabilities["tailoring"]["operations"] == ["generate_candidate"]
    assert "customizations" in capabilities["document"]
    assert capabilities["tailoring"]["candidate_content"] == "editable_except_server_owned_profile_identity"
    assert capabilities["document"]["section_types"]["experience"]["fields"]["company"]["editable"] is True
    assert capabilities["document"]["section_types"]["profile"]["fields"]["email"]["server_owned"] is True
    location = capabilities["document"]["section_types"]["profile"]["fields"]["location"]
    assert location["server_owned"] is False
    assert location["editable"] is True
    assert "location" not in capabilities["tailoring"]["server_owned_profile_fields"]
    certification_description = capabilities["document"]["section_types"]["certifications"]["fields"]["description"]
    assert certification_description["type"] == "rich_text"
    assert certification_description["editable"] is True
    context = TailoringContextResponse.model_validate(
        {
            "protocol_version": 2,
            "session_id": "session",
            "application_id": "application",
            "source_cv_id": None,
            "expires_at": datetime.now(timezone.utc),
            "context_hash": "a" * 64,
            "job": {"company": "Example", "role": "Engineer", "description": "Build APIs"},
            "profile": {"name": "Ada"},
            "previous_cv": None,
            "library": [],
            "requirements": [],
            "templates": [{"id": "minimal", "name": "Minimal", "manifest": {}}],
            "selected_template_id": "minimal",
            "selected_template_manifest": {},
            "capabilities": capabilities,
            "capabilities_hash": capabilities_hash(capabilities),
        }
    )
    assert context.previous_cv is None
    with pytest.raises(ValidationError):
        TailoringSessionStatusResponse.model_validate(
            {
                "protocol_version": 2,
                "session_id": "session",
                "application_id": "application",
                "status": "draft_ready",
                "expires_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "attempts": 1,
                "capability": "secret",
            }
        )


def test_candidate_normalization_preserves_tailored_location_and_injects_server_owned_identity():
    profile = UserProfile(
        name="Ada Lovelace",
        email="ada@example.com",
        location="42 Example Street, Halifax, NS",
    )
    candidate = _candidate()
    candidate.sections[0].data["location"] = "Halifax, NS, Canada"
    candidate.sections[0].data["phone"] = "555-0100"
    candidate.sections[0].data["social_links"] = [{"label": "LinkedIn", "url": "https://example.test/fake"}]
    candidate.sections[0].data["photo_url"] = "https://example.test/fake.png"
    parts = {
        "manifest_by_id": {"minimal": {"manifest_version": 2}},
        "profile": profile,
    }
    normalized, sections = TailoringService._normalize_candidate(candidate, parts)
    assert normalized["sections"][0]["data"]["name"] == "Ada Lovelace"
    assert normalized["sections"][0]["data"]["email"] == "ada@example.com"
    assert normalized["sections"][0]["data"]["location"] == "Halifax, NS, Canada"
    assert "phone" not in normalized["sections"][0]["data"]
    assert normalized["sections"][0]["data"]["social_links"] == []
    assert "photo_url" not in normalized["sections"][0]["data"]
    assert sections[0]["style"]["subsection"]["text_align"] == "left"


def test_no_source_scaffold_has_profile_and_empty_entry_sections():
    sections = fresh_tailoring_sections("session", {"name": "Ada"})
    assert sections[0]["enabled"] is True
    assert sections[0]["data"]["name"] == "Ada"
    assert all(section["data"] == [] for section in sections[1:])


def test_ready_draft_remains_reviewable_after_agent_capability_expiry():
    now = datetime.now(timezone.utc)
    session = TailoringSession(
        id="session",
        user_id="user",
        application_id="application",
        cv_id=None,
        draft_cv_id="draft",
        code_hash="code-hash",
        status="draft_ready",
        expires_at=now - timedelta(minutes=1),
        created_at=now - timedelta(hours=2),
        updated_at=now,
        attempts=1,
        result={"draft_cv_id": "draft"},
    )

    class _DB:
        async def execute(self, _query):
            return SimpleNamespace(scalar_one_or_none=lambda: session)

        async def flush(self):
            raise AssertionError("A ready draft must not be expired with its capability")

    status = asyncio.run(TailoringService(_DB()).session_status("session", "user"))
    assert status.status == "draft_ready"
    assert status.draft_cv_id == "draft"


def test_expired_agent_draft_still_blocks_a_second_session_until_reviewed():
    now = datetime.now(timezone.utc)
    existing = TailoringSession(
        id="session",
        user_id="user",
        application_id="application",
        code_hash="code-hash",
        status="draft_ready",
        expires_at=now - timedelta(minutes=1),
        created_at=now - timedelta(hours=2),
        updated_at=now,
    )
    application = SimpleNamespace(id="application")

    class _Result:
        def __init__(self, *, scalar=None, rows=None):
            self.scalar = scalar
            self.rows = rows or []

        def scalar_one_or_none(self):
            return self.scalar

        def scalars(self):
            return SimpleNamespace(all=lambda: self.rows)

    class _DB:
        calls = 0

        async def execute(self, _query):
            self.calls += 1
            return _Result(scalar=application) if self.calls == 1 else _Result(rows=[existing])

    with pytest.raises(TailoringConflictError, match="Finish or cancel"):
        asyncio.run(TailoringService(_DB()).create_session("application", "user"))


def test_application_cv_link_is_part_of_the_context_freshness_snapshot():
    app_before = SimpleNamespace(
        id="application",
        cv_id="source-cv",
        company="Example",
        role="Engineer",
        job_url=None,
        job_description="Build APIs",
    )
    app_after = SimpleNamespace(**{**vars(app_before), "cv_id": "new-cv"})

    assert _application_context_snapshot(app_before)["linked_cv_id"] == "source-cv"
    assert _application_context_snapshot(app_before) != _application_context_snapshot(app_after)
