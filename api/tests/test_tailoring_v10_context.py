"""Regressions for immutable v10 authoring context and its live target guard."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.seed import SEED_TEMPLATES
from app.db.session import async_session
from app.document_schema.capabilities import SERVER_OWNED_PROFILE_FIELDS, renderer_capabilities
from app.document_schema.models import TemplateManifest
from app.http_schemas.profile import UserProfile
from app.models.application import Application
from app.models.cv import CV
from app.models.library import Library, LibraryEntry
from app.models.template import Template
from app.models.user import User
from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.service import ScannerService
from app.services import pdf as pdf_service_module
from app.services import tailoring as tailoring_service_module
from app.services.pdf import PDFService
from app.services.tailoring import TailoringService, TailoringStaleError
from app.core.auth import hash_token


class _FixtureExtractor:
    def extract(self, job_description: str):
        return extract_requirements_from_entities(job_description, {"entities": {}})


class _FixtureScanner(ScannerService):
    def __init__(self):
        super().__init__(extractor=_FixtureExtractor())


async def _no_pdf(self, _cv, _manifest=None):
    return None


async def _context_case(*, monkeypatch, include_source_cv: bool = True):
    monkeypatch.setattr(tailoring_service_module, "ScannerService", _FixtureScanner)
    monkeypatch.setattr(tailoring_service_module.TailoringService, "_render_cv_pdf", _no_pdf)
    monkeypatch.setattr(
        tailoring_service_module,
        "configured_extractor_version",
        lambda: "gliner2.5-structured-v11",
    )
    suffix = uuid4().hex
    capability = f"v10-context-{suffix}"
    user_id = str(uuid4())
    application_id = str(uuid4())
    library_id = str(uuid4())
    entry_id = str(uuid4())
    source_cv_id = str(uuid4()) if include_source_cv else None
    source_sections = [
        {
            "id": "source-profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "Ada Current", "title": "Source CV headline"},
        },
        {
            "id": "source-experience",
            "type": "experience",
            "title": "Experience",
            "enabled": True,
            "data": [
                {
                    "id": "source-role",
                    "company": "Source Only Labs",
                    "position": "Historical official title",
                    "description": "SOURCE-CV-ONLY-FACT",
                }
            ],
        },
    ]

    async with async_session() as db:
        user = User(
            id=user_id,
            email=f"tailoring-v10-context-{suffix}@example.test",
            password_hash="test-hash",
            profile_data={
                "name": "Ada Current",
                "title": "Professional headline",
                "email": f"tailoring-v10-context-{suffix}@example.test",
                "phone": "+1 902 555 0100",
                "social_links": [],
            },
        )
        library = Library(id=library_id, user_id=user_id)
        entry = LibraryEntry(
            id=entry_id,
            library_id=library_id,
            kind="experience",
            payload=[{"id": "library-role", "company": "Library Co", "position": "Engineer"}],
        )
        app = Application(
            id=application_id,
            user_id=user_id,
            cv_id=source_cv_id,
            company="Target Company",
            role="Platform Engineer",
            job_url="https://jobs.example.test/one",
            job_description="Build Python services with Linux.",
            notes="Preserve relevant evidence.",
            status="draft",
            extracted_keywords=[],
            relevance={},
            quality={},
            algorithm_version="test",
        )
        db.add_all([user, library, entry, app])
        if include_source_cv:
            db.add(
                CV(
                    id=source_cv_id,
                    user_id=user_id,
                    application_id=application_id,
                    title="Whole CV document title",
                    template_id="generic-minimal",
                    sections=source_sections,
                    customizations={},
                    extra_metadata={},
                    revision=7,
                    is_active=True,
                )
            )
        await db.flush()

        service = TailoringService(db)
        created, session = await service.create_session(application_id, user_id)
        session.status = "exchanged"
        session.capability_hash = hash_token(capability)
        await db.flush()
        context = await service.context(capability)
        session_id = session.id
        await db.commit()
        return {
            "user_id": user_id,
            "application_id": application_id,
            "library_entry_id": entry_id,
            "source_cv_id": source_cv_id,
            "source_sections": source_sections,
            "session_id": session_id,
            "capability": capability,
            "created": created,
            "context": context,
        }


@pytest.mark.asyncio
async def test_author_context_stays_frozen_after_profile_library_and_template_edits(monkeypatch):
    case = await _context_case(monkeypatch=monkeypatch)
    first = case["context"]
    assert first.source_cv_revision == 7
    assert "SOURCE-CV-ONLY-FACT" in first.dossier
    assert "Source Only Labs" in first.dossier
    assert "Historical official title" in first.dossier
    assert "Source CV document title" in first.dossier
    assert "Professional headline" in first.dossier
    assert "supplement Library history" in first.dossier

    async with async_session() as db:
        user = await db.get(User, case["user_id"])
        library_entry = await db.get(LibraryEntry, case["library_entry_id"])
        selected_template = await db.get(Template, first.selected_template_id)
        session = await db.get(tailoring_service_module.TailoringSession, case["session_id"])
        service = TailoringService(db)
        user.profile_data = {"name": "Changed Profile", "title": "Changed headline"}
        library_entry.payload = [{"id": "new-row", "company": "Changed Library"}]
        selected_template.name = "Changed template name"
        selected_template.manifest = {
            **selected_template.manifest,
            "global_styles": {**selected_template.manifest["global_styles"], "accent_color": "#abcdef"},
        }
        session.context_snapshot = {
            **session.context_snapshot,
            "evaluation_history": [{"evaluation_id": "later-evaluation"}],
        }
        await db.flush()

        second = await service.context(case["capability"])
        assert await service._context_matches(session, first.context_hash)
    assert second.context_hash == first.context_hash
    assert second.dossier == first.dossier
    frozen_template = next(template for template in first.templates if template.id == first.selected_template_id)
    returned_template = next(template for template in second.templates if template.id == second.selected_template_id)
    assert returned_template.manifest == frozen_template.manifest
    assert returned_template.name == frozen_template.name
    assert "Ada Current" in second.dossier
    assert "Library Co" in second.dossier
    assert "Changed Profile" not in second.dossier
    assert "Changed Library" not in second.dossier


@pytest.mark.asyncio
@pytest.mark.parametrize("changed_field", ["job", "notes", "source"])
async def test_live_target_guard_rejects_job_notes_and_source_changes(monkeypatch, changed_field):
    case = await _context_case(monkeypatch=monkeypatch)
    async with async_session() as db:
        application = await db.get(Application, case["application_id"])
        session = await db.get(tailoring_service_module.TailoringSession, case["session_id"])
        service = TailoringService(db)
        if changed_field == "job":
            application.job_description = "A materially different job."
        elif changed_field == "notes":
            application.notes = "A changed instruction."
        else:
            source_cv = await db.get(CV, case["source_cv_id"])
            source_cv.sections = deepcopy(source_cv.sections)
            source_cv.sections[1]["data"][0]["description"] = "Changed source fact"
            source_cv.revision += 1
        await db.flush()

        assert not await service._context_matches(session)
        with pytest.raises(TailoringStaleError, match="changed"):
            await service.context(case["capability"])


@pytest.mark.asyncio
async def test_context_without_source_cv_has_no_source_scan_or_source_revision(monkeypatch):
    case = await _context_case(monkeypatch=monkeypatch, include_source_cv=False)
    context = case["context"]
    assert context.source_cv_id is None
    assert context.source_cv_revision is None
    assert context.scanner_context.source_scan is None
    assert "## Readable source CV" not in context.dossier
    assert "Platform Engineer" in context.job.role


def test_candidate_headline_is_editable_while_fixed_contacts_are_injected():
    profile = UserProfile(
        name="Ada Lovelace",
        title="Saved professional headline",
        email="ada@example.test",
        phone="+1 902 555 0100",
        email_link=False,
        social_links=[],
    )
    candidate = {
        "title": "Target CV document title",
        "template_id": "generic-minimal",
        "sections": [
            {
                "id": "profile",
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": {
                    "name": "Fake Name",
                    "title": "Tailored professional headline",
                    "email": "fake@example.test",
                    "phone": "000",
                    "email_link": True,
                    "social_links": [],
                },
            }
        ],
        "customizations": {},
    }
    template = next(item["manifest"] for item in SEED_TEMPLATES if item["id"] == "generic-minimal")
    normalized, _ = TailoringService._normalize_candidate(
        tailoring_service_module.TailoringCandidateCV.model_validate(candidate),
        {"profile": profile, "manifest_by_id": {"generic-minimal": template}},
    )
    profile_data = normalized["sections"][0]["data"]
    assert normalized["title"] == "Target CV document title"
    assert profile_data["title"] == "Tailored professional headline"
    assert profile_data["name"] == "Ada Lovelace"
    assert profile_data["email"] == "ada@example.test"
    assert profile_data["phone"] == "+1 902 555 0100"
    assert profile_data["email_link"] is False
    assert "title" not in SERVER_OWNED_PROFILE_FIELDS
    title_capability = renderer_capabilities()["document"]["section_types"]["profile"]["fields"]["title"]
    assert title_capability["editable"] is True
    assert title_capability["server_owned"] is False


@pytest.mark.asyncio
async def test_pdf_service_renders_from_supplied_frozen_manifest_through_canonical_pipeline(monkeypatch):
    captured_html: list[str] = []

    async def fake_html_to_pdf(html: str) -> bytes:
        captured_html.append(html)
        return b"%PDF-frozen-manifest"

    monkeypatch.setattr(pdf_service_module, "render_html_pdf", fake_html_to_pdf)
    manifest = deepcopy(next(item["manifest"] for item in SEED_TEMPLATES if item["id"] == "generic-minimal"))
    frozen_manifest = TemplateManifest.model_validate(manifest)
    later_manifest = deepcopy(manifest)
    later_manifest["global_styles"]["accent_color"] = "#aabbcc"
    sections = [
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "Ada", "summary": "FROZEN-MANIFEST-PIPELINE-SENTINEL"},
        }
    ]

    service = PDFService(SimpleNamespace())
    first_pdf = await service.render_manifest_payload(frozen_manifest, sections, {})
    second_pdf = await service.render_manifest_payload(later_manifest, sections, {})
    assert first_pdf == b"%PDF-frozen-manifest"
    assert second_pdf == b"%PDF-frozen-manifest"
    assert len(captured_html) == 2
    assert "FROZEN-MANIFEST-PIPELINE-SENTINEL" in captured_html[0]
    assert captured_html[0] != captured_html[1]
