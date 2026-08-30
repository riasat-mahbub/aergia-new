"""Phase 1 protocol fixture checks against the server-side Pydantic contract."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.tailoring import TailoringCodeExchange, TailoringEvidencePacket, TailoringPatch
from app.services.tailoring import TailoringPatchError, TailoringService, _stored_requirements


_FIXTURES = Path(__file__).parents[2] / "contracts" / "fixtures"


def test_valid_tailoring_patch_fixture_matches_protocol():
    payload = json.loads((_FIXTURES / "tailoring-patch.valid.json").read_text())
    patch = TailoringPatch.model_validate(payload)
    assert patch.protocol_version == 1
    assert [change.operation for change in patch.changes] == ["replace_description", "report_gap"]


def test_valid_evidence_fixture_matches_protocol():
    payload = json.loads((_FIXTURES / "evidence-packet.valid.json").read_text())
    evidence = TailoringEvidencePacket.model_validate(payload)
    assert evidence.protocol_version == 1
    assert evidence.cv.id == "cv-1"


def test_invalid_tailoring_operation_fixture_is_rejected():
    payload = json.loads((_FIXTURES / "tailoring-patch.invalid-operation.json").read_text())
    with pytest.raises(ValidationError):
        TailoringPatch.model_validate(payload)


def test_tailoring_patch_rejects_unknown_fields_and_versions():
    with pytest.raises(ValidationError):
        TailoringPatch.model_validate(
            {
                "protocol_version": 1,
                "unexpected": True,
                "changes": [
                    {
                        "operation": "report_gap",
                        "requirement": "Kubernetes",
                        "reason": "No evidence",
                    }
                ],
            }
        )
    with pytest.raises(ValidationError):
        TailoringPatch.model_validate(
            {
                "protocol_version": 2,
                "changes": [
                    {
                        "operation": "report_gap",
                        "requirement": "Kubernetes",
                        "reason": "No evidence",
                    }
                ],
            }
        )


def test_tailoring_exchange_requires_protocol_version():
    assert TailoringCodeExchange.model_validate({"protocol_version": 1, "code": "x" * 16}).protocol_version == 1
    with pytest.raises(ValidationError):
        TailoringCodeExchange.model_validate({"code": "x" * 16})


def test_stored_requirements_are_read_without_extraction():
    requirements = _stored_requirements(
        SimpleNamespace(
            relevance={
                "requirements": [
                    {
                        "requirement": {
                            "id": "req-1",
                            "text": "Python",
                            "normalized": "python",
                            "type": "hard_skill",
                            "required": True,
                            "weight": 1.0,
                        }
                    }
                ]
            }
        )
    )
    assert [requirement.normalized for requirement in requirements] == ["python"]


def test_phase_one_patch_is_copy_on_write_and_rejects_rich_text():
    source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [{"id": "entry-1", "description": "Original"}],
        }
    ]
    patch = TailoringPatch.model_validate(
        {
            "protocol_version": 1,
            "changes": [
                {
                    "operation": "replace_description",
                    "section_id": "experience",
                    "entry_id": "entry-1",
                    "value": "Updated",
                }
            ],
        }
    )
    updated, _operations, _gaps = TailoringService._apply_patch(source, patch)
    assert source[0]["data"][0]["description"] == "Original"
    assert updated[0]["data"][0]["description"] == "Updated"

    rich_text_source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [{"id": "entry-1", "description": []}],
        }
    ]
    with pytest.raises(TailoringPatchError):
        TailoringService._apply_patch(rich_text_source, patch)
