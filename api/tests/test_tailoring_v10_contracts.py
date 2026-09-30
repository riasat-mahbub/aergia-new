"""Pure protocol-v10 contract tests using synthetic candidate data."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.document_schema.capabilities import capabilities_hash, renderer_capabilities
from app.http_schemas.tailoring import (
    PROTOCOL_VERSION,
    TailoringAcceptRequest,
    TailoringCandidateCV,
    TailoringCodeExchange,
    TailoringContextResponse,
    TailoringDraftContextResponse,
    TailoringDraftReview,
    TailoringPreviewRequest,
    TailoringPreviewReservationReleaseResponse,
    TailoringPreviewReservationRequest,
    TailoringPreviewReservationResponse,
    TailoringPreviewResponse,
    TailoringReevaluateRequest,
    TailoringReevaluateResponse,
    TailoringSessionStatusResponse,
    TailoringSubmitRequest,
    TailoringSubmitResponse,
)
from app.http_schemas.tailoring_evaluation import TAILORING_EVALUATION_VERSION
from app.http_schemas.tailoring_fit_review import (
    FitReviewCompleted,
    FitReviewSkippedExplicitly,
    FitReviewUnavailable,
)
from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.service import ScannerService
from app.services.tailoring_evaluation import evaluate_tailoring


_CANDIDATE_HASH = "a" * 64
_CONTEXT_HASH = "b" * 64
_PDF_HASH = "c" * 64
_RENDER_HASH = "d" * 64
_EVALUATION_ID = "evaluation_0123456789abcdef"


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


class _FixtureExtractor:
    def extract(self, job_description: str):
        return extract_requirements_from_entities(job_description, {"entities": {}})


def _scan_and_evaluate():
    candidate = _candidate()
    scanner = ScannerService(extractor=_FixtureExtractor())
    scan = scanner.scan("Build Python APIs", candidate)
    evaluation = evaluate_tailoring(scan.requirement_extraction, scan, _CANDIDATE_HASH)
    return scan, evaluation


def _fit_review(status: str = "completed") -> dict:
    binding = {
        "version": "fit-review-v1",
        "evaluation_id": _EVALUATION_ID,
        "candidate_hash": _CANDIDATE_HASH,
        "pdf_sha256": _PDF_HASH,
    }
    if status == "completed":
        return binding | {
            "status": status,
            "mode": "fresh_agent",
            "verdict": "generic",
            "rationale": "The CV names the tools but does not connect its examples to the job's responsibilities.",
            "strong_connections": ["Python API work"],
            "weak_or_missing_connections": ["Production reliability ownership"],
            "recommended_changes": ["Connect the API example to a stated responsibility."],
        }
    return binding | {"status": status, "reason": "The host could not inspect the PDF."}


def _status(protocol_version: int) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "protocol_version": protocol_version,
        "session_id": "session-id",
        "application_id": "application-id",
        "status": "draft_ready",
        "expires_at": now,
        "created_at": now,
        "updated_at": now,
        "attempts": 1,
        "result": {"protocol_version": protocol_version, "draft_cv_id": "draft-id"},
    }


def test_v10_exchange_context_and_reservation_payloads_require_bound_ids_and_hashes():
    session_id = str(uuid4())
    exchange = TailoringCodeExchange.model_validate(
        {"protocol_version": 10, "session_id": session_id, "code": "x" * 16}
    )
    assert exchange.session_id == session_id
    assert PROTOCOL_VERSION == 10

    with pytest.raises(ValidationError):
        TailoringCodeExchange.model_validate({"protocol_version": 10, "code": "x" * 16})
    with pytest.raises(ValidationError):
        TailoringCodeExchange.model_validate(
            {"protocol_version": 10, "session_id": "not-a-uuid", "code": "x" * 16}
        )
    with pytest.raises(ValidationError):
        TailoringCodeExchange.model_validate(
            {"protocol_version": 9, "session_id": session_id, "code": "x" * 16}
        )

    capabilities = renderer_capabilities()
    scan, _evaluation = _scan_and_evaluate()
    context = TailoringContextResponse.model_validate(
        {
            "protocol_version": 10,
            "session_id": session_id,
            "application_id": "application-id",
            "source_cv_id": None,
            "source_cv_revision": None,
            "expires_at": datetime.now(timezone.utc),
            "context_hash": _CONTEXT_HASH,
            "job": {"company": "Example", "role": "Engineer", "description": "Build APIs"},
            "dossier": "Profile: Ada",
            "templates": [{"id": "minimal", "name": "Minimal", "manifest": {}}],
            "selected_template_id": "minimal",
            "selected_template_manifest": {},
            "capabilities": capabilities,
            "capabilities_hash": capabilities_hash(capabilities),
            "scanner_context": {
                "schema_version": "scanner-v1",
                "versions": scan.versions.model_dump(mode="json"),
                "requirement_extraction": scan.requirement_extraction.model_dump(mode="json"),
                "source_scan": None,
            },
            "evaluation_version": TAILORING_EVALUATION_VERSION,
        }
    )
    assert context.source_cv_revision is None
    assert context.protocol_version == 10
    with pytest.raises(ValidationError):
        TailoringContextResponse.model_validate(context.model_dump(mode="json") | {"context_hash": "short"})

    candidate = _candidate()
    reservation_request = TailoringPreviewReservationRequest.model_validate(
        {"context_hash": _CONTEXT_HASH, "candidate": candidate, "request_id": str(uuid4())}
    )
    assert reservation_request.candidate == candidate
    reservation_id = str(uuid4())
    reservation = TailoringPreviewReservationResponse.model_validate(
        {
            "reservation_id": reservation_id,
            "candidate_hash": _CANDIDATE_HASH,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=120),
        }
    )
    assert reservation.candidate_hash == _CANDIDATE_HASH
    release = TailoringPreviewReservationReleaseResponse.model_validate(
        {"reservation_id": reservation_id, "state": "already_released"}
    )
    assert release.state == "already_released"
    preview_request = TailoringPreviewRequest.model_validate(
        {"context_hash": _CONTEXT_HASH, "reservation_id": reservation_id, "candidate": candidate}
    )
    assert preview_request.reservation_id == reservation_id

    with pytest.raises(ValidationError):
        TailoringPreviewReservationRequest.model_validate(
            {"context_hash": _CONTEXT_HASH, "candidate": candidate, "request_id": "bad-id"}
        )
    with pytest.raises(ValidationError):
        TailoringPreviewRequest.model_validate(
            {"context_hash": _CONTEXT_HASH, "reservation_id": "bad-id", "candidate": candidate}
        )


def test_preview_and_submit_keep_evaluation_v2_and_pdf_binding():
    candidate = _candidate()
    scan, evaluation = _scan_and_evaluate()
    preview = TailoringPreviewResponse.model_validate(
        {
            "format": "pdf",
            "pdf_base64": "cGRm",
            "page_count": 1,
            "evaluation_id": _EVALUATION_ID,
            "candidate_hash": _CANDIDATE_HASH,
            "pdf_sha256": _PDF_HASH,
            "candidate": candidate,
            "scanner_result": scan.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
            "render_warnings": [],
        }
    )
    assert preview.pdf_sha256 == _PDF_HASH
    assert preview.evaluation.version == TAILORING_EVALUATION_VERSION

    base_submit = {
        "context_hash": _CONTEXT_HASH,
        "evaluation_id": preview.evaluation_id,
        "candidate_hash": preview.candidate_hash,
        "candidate": preview.candidate,
    }
    no_review = TailoringSubmitRequest.model_validate(base_submit)
    assert no_review.fit_review is None
    reviewed = TailoringSubmitRequest.model_validate(base_submit | {"fit_review": _fit_review()})
    assert reviewed.fit_review.verdict == "generic"
    assert reviewed.evaluation_id == preview.evaluation_id
    assert reviewed.fit_review.pdf_sha256 == preview.pdf_sha256

    with pytest.raises(ValidationError):
        TailoringSubmitRequest.model_validate(base_submit | {"candidate_hash": "x" * 64})
    with pytest.raises(ValidationError):
        TailoringPreviewResponse.model_validate(
            {
                "format": "pdf",
                "pdf_base64": "cGRm",
                "page_count": 1,
                "evaluation_id": "bad id",
                "candidate_hash": _CANDIDATE_HASH,
                "pdf_sha256": _PDF_HASH,
                "candidate": candidate,
                "scanner_result": scan.model_dump(mode="json"),
                "evaluation": evaluation.model_dump(mode="json"),
            }
        )

    response = TailoringSubmitResponse.model_validate(
        {
            "protocol_version": 10,
            "session_id": str(uuid4()),
            "application_id": "application-id",
            "draft_cv_id": "draft-id",
            "evaluation_id": _EVALUATION_ID,
            "candidate_hash": _CANDIDATE_HASH,
            "candidate": candidate,
            "scanner_result": scan.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
            "fit_review": None,
        }
    )
    assert response.fit_review is None


def test_fit_review_variants_are_bounded_strict_and_verdict_free_when_unavailable():
    completed = FitReviewCompleted.model_validate(_fit_review())
    assert completed.verdict == "generic"  # Advisory; the DTO accepts every verdict.
    unavailable = FitReviewUnavailable.model_validate(_fit_review("unavailable"))
    skipped = FitReviewSkippedExplicitly.model_validate(_fit_review("skipped_explicitly"))
    assert unavailable.status == "unavailable"
    assert skipped.status == "skipped_explicitly"

    for payload in (
        _fit_review() | {"model_secret": "must not be accepted"},
        _fit_review() | {"evaluation_id": "bad"},
        _fit_review() | {"pdf_sha256": "z" * 64},
        _fit_review() | {"recommended_changes": ["change"] * 4},
        _fit_review() | {"strong_connections": ["connection"] * 6},
        _fit_review("unavailable") | {"verdict": "tailored"},
        _fit_review("skipped_explicitly") | {"weak_or_missing_connections": []},
    ):
        with pytest.raises(ValidationError):
            TailoringSubmitRequest.model_validate(
                {
                    "context_hash": _CONTEXT_HASH,
                    "evaluation_id": _EVALUATION_ID,
                    "candidate_hash": _CANDIDATE_HASH,
                    "candidate": _candidate(),
                    "fit_review": payload,
                }
            )


def test_owner_review_and_builder_context_are_draft_scoped_and_revision_bound():
    scan, evaluation = _scan_and_evaluate()
    review = TailoringDraftReview.model_validate(
        {
            "state": "current",
            "cv_revision": 4,
            "candidate_hash": _CANDIDATE_HASH,
            "render_basis_hash": _RENDER_HASH,
            "evaluation_id": _EVALUATION_ID,
            "evaluation": evaluation.model_dump(mode="json"),
            "scanner_result": scan.model_dump(mode="json"),
            "warnings": [],
            "pdf_sha256": _PDF_HASH,
            "fit_review": _fit_review(),
            "fit_review_applicability": "current",
        }
    )
    accept = TailoringAcceptRequest.model_validate(
        {"expected_cv_revision": review.cv_revision, "candidate_hash": review.candidate_hash}
    )
    assert accept.expected_cv_revision == 4
    with pytest.raises(ValidationError):
        TailoringAcceptRequest.model_validate({"expected_cv_revision": 4, "candidate_hash": "bad"})
    with pytest.raises(ValidationError):
        TailoringReevaluateRequest.model_validate({"expected_cv_revision": -1})

    reevaluated = TailoringReevaluateResponse.model_validate(
        {
            "protocol_version": 10,
            "session_id": str(uuid4()),
            "application_id": "application-id",
            "draft_cv_id": "draft-id",
            "draft_review": review,
            "format": "pdf",
            "pdf_base64": "cGRm",
            "page_count": 1,
        }
    )
    assert reevaluated.draft_review.cv_revision == 4

    builder_context = TailoringDraftContextResponse.model_validate(
        {
            "protocol_version": 10,
            "session_id": str(uuid4()),
            "application_id": "application-id",
            "draft_cv_id": "draft-id",
            "draft_review": review,
            "job": {"company": "Example", "role": "Engineer", "description": "Build APIs"},
            "scanner_context": {
                "schema_version": "scanner-v1",
                "versions": scan.versions.model_dump(mode="json"),
                "requirement_extraction": scan.requirement_extraction.model_dump(mode="json"),
            },
        }
    )
    assert builder_context.scanner_context.schema_version == "scanner-v1"
    with pytest.raises(ValidationError):
        TailoringDraftContextResponse.model_validate(
            builder_context.model_dump(mode="json")
            | {"scanner_context": builder_context.scanner_context.model_dump(mode="json") | {"source_scan": {}}}
        )
    with pytest.raises(ValidationError):
        TailoringDraftReview.model_validate(
            {"state": "current", "cv_revision": -1, "fit_review_applicability": "not_run"}
        )


def test_protocol_4_through_9_status_results_remain_readable_without_v10_fields():
    for protocol_version in range(4, 10):
        status = TailoringSessionStatusResponse.model_validate(_status(protocol_version))
        assert status.protocol_version == protocol_version
        assert status.draft_review is None
        assert status.result["protocol_version"] == protocol_version

    status_v10 = TailoringSessionStatusResponse.model_validate(
        _status(10)
        | {
            "draft_review": {
                "state": "needs_reevaluation",
                "cv_revision": 5,
                "candidate_hash": _CANDIDATE_HASH,
                "render_basis_hash": None,
                "evaluation_id": None,
                "evaluation": None,
                "scanner_result": None,
                "warnings": [],
                "pdf_sha256": None,
                "fit_review": _fit_review("unavailable"),
                "fit_review_applicability": "earlier_version",
            }
        }
    )
    assert status_v10.draft_review.fit_review_applicability == "earlier_version"


def test_dtos_publish_fit_review_discriminator_and_v10_openapi_shapes():
    app = FastAPI()

    @app.post("/exchange", response_model=TailoringCodeExchange)
    def exchange(body: TailoringCodeExchange):
        return body

    @app.post("/submit", response_model=TailoringSubmitResponse)
    def submit(body: TailoringSubmitRequest):
        return body

    @app.post("/accept", response_model=TailoringAcceptRequest)
    def accept(body: TailoringAcceptRequest):
        return body

    schema = app.openapi()
    components = schema["components"]["schemas"]
    exchange_schema = components["TailoringCodeExchange"]
    assert "session_id" in exchange_schema["required"]
    submit_schema = components["TailoringSubmitRequest"]["properties"]["fit_review"]
    union = next(item for item in submit_schema["anyOf"] if "discriminator" in item)
    assert union["discriminator"]["propertyName"] == "status"
    assert components["TailoringAcceptRequest"]["required"] == ["expected_cv_revision", "candidate_hash"]
